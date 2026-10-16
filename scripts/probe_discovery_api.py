"""Authenticated, redacted capability probe for Intern InkStone Discovery API.

Uses a pre-existing GitHub Actions Secret DISCOVERY_API_KEY. Never logs its
value, request headers, provider error bodies or non-test user content.
Exactly one tiny text-generation call after an authenticated /models listing.
No novels, prompts, or R2 data are sent.
"""
from __future__ import annotations

import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler
import ssl

BASE = "https://discovery-api.intern-ai.org.cn/v1"
MAX_RESPONSE_BYTES = 196608
MAX_COMPLETION_TOKENS = 512

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError("REDIRECT_REFUSED")

def call(path: str, key: str, *, data: dict | None = None):
    if path not in ("/models", "/chat/completions"):
        raise ValueError("UNAPPROVED_PATH")
    url=BASE+path
    headers={"Authorization":"Bearer "+key, "Accept":"application/json"}
    if data is not None:
        headers["Content-Type"]="application/json"
    packed=json.dumps(data,ensure_ascii=False).encode("utf-8") if data is not None else None
    request=Request(url,data=packed,headers=headers,
                    method="POST" if data is not None else "GET")
    opener=build_opener(NoRedirect(),HTTPSHandler(context=ssl.create_default_context()))
    try:
        with opener.open(request,timeout=50) as response:
            raw=response.read(MAX_RESPONSE_BYTES+1)
            status=response.status
    except HTTPError as exc:
        # Never log provider response or credential-bearing headers.
        return {"ok":False,"http_status":exc.code}
    except (TimeoutError,OSError,URLError,RuntimeError) as exc:
        return {"ok":False,"error_type":type(exc).__name__}
    if len(raw)>MAX_RESPONSE_BYTES:
        return {"ok":False,"error_type":"RESPONSE_TOO_LARGE"}
    try:
        parsed=json.loads(raw)
    except (ValueError,UnicodeError):
        return {"ok":False,"error_type":"INVALID_JSON"}
    if not isinstance(parsed,dict):
        return {"ok":False,"error_type":"INVALID_DOCUMENT"}
    return {"ok":True,"http_status":status,"body":parsed}

def model_ids(doc: dict) -> list[str]:
    payload=doc.get("data",[])
    if not isinstance(payload,list):
        return []
    ids=[]
    for item in payload:
        if not isinstance(item,dict):
            continue
        ident=item.get("id")
        if isinstance(ident,str) and len(ident)<=110 and len(ids)<250:
            ids.append(ident)
    return ids

def choose_model(ids: list[str]) -> str | None:
    preferred=(
        # Prefer fast text model for a tiny completion probe; thinking
        # variants may spend their whole output allowance on reasoning.
        "deepseek-v4-flash-0731", "kimi-k2.6", "glm-5.3",
        "intern-s2", "intern-latest", "intern-s1-pro",
    )
    for candidate in preferred:
        if candidate in ids:
            return candidate
    # If platform exposes unexpected models, don't pick an arbitrary,
    # possibly costly or inappropriate version.
    return None

def main():
    key=os.environ.get("DISCOVERY_API_KEY")
    # GitHub resolves an inaccessible/mis-scoped Secret expression as an
    # empty string. Distinguish that from an actually present but malformed
    # value; never print, hash, prefix, suffix or length of credentials.
    if key is None:
        print(json.dumps({"status":"KEY_NOT_EXPORTED_TO_PROCESS",
            "secret_name":"DISCOVERY_API_KEY","model_call_performed":False,
            "diagnosis":"workflow_env_missing"}))
        return 2
    if key == "":
        print(json.dumps({"status":"GITHUB_ACTIONS_SECRET_RESOLVED_EMPTY",
            "secret_name":"DISCOVERY_API_KEY","model_call_performed":False,
            "diagnosis":"scope_or_permissions_or_name_mismatch"}))
        return 2
    if len(key)<12 or any(c.isspace() for c in key):
        print(json.dumps({"status":"KEY_PRESENT_BUT_FORMAT_CHECK_FAILED",
            "secret_name":"DISCOVERY_API_KEY","model_call_performed":False,
            "diagnosis":"format_check_only"}))
        return 2
    listing=call("/models",key)
    if not listing["ok"]:
        print(json.dumps({"stage":"GET_MODELS_FAILED",**listing,
                          "model_call_performed":False}))
        return 3
    ids=model_ids(listing["body"])
    target=choose_model(ids)
    result={"stage":"AUTHENTICATED_MODELS", "model_count":len(ids),
            "models":ids[:40],
            "selected_probe_model":target,
            "model_call_performed":False}
    if not target:
        result["status"]="MODEL_SELECTION_REQUIRED"
        print(json.dumps(result,ensure_ascii=False))
        return 4
    question=("请用不超过50个汉字说明：写小说时，为什么人物的注意力"
              "会受到其当下目标影响？不要引用任何作品。")
    trial=call("/chat/completions",key,data={
        "model":target,
        "messages":[{"role":"user","content":question}],
        "max_tokens":MAX_COMPLETION_TOKENS,
        "stream":False,
    })
    if not trial["ok"]:
        result.update({"stage":"GENERATION_FAILED",
            "completion_status":{k:v for k,v in trial.items() if k!="body"},
            "model_call_performed":True,"novel_text_sent":False})
        print(json.dumps(result,ensure_ascii=False))
        return 5
    body=trial["body"]
    choices=body.get("choices") or []
    message=choices[0].get("message",{}) if choices and isinstance(choices[0],dict) else {}
    output=message.get("content") if isinstance(message,dict) else None
    usage=body.get("usage") if isinstance(body.get("usage"),dict) else {}
    clean_usage={k:v for k,v in usage.items()
                 if k in ("prompt_tokens","completion_tokens","total_tokens")
                 and type(v) is int and 0<=v<=1000000}
    result.update({"stage":"DISCOVERY_REAL_GENERATION_PROBE",
        "model_call_performed":True,"novel_text_sent":False,
        "probe_generated_text":bool(isinstance(output,str) and output.strip()),
        "probe_response_characters":len(output) if isinstance(output,str) else 0,
        "usage":clean_usage,
        "finish_reason":choices[0].get("finish_reason") if choices and isinstance(choices[0],dict) else None,
        "provider_model":str(body.get("model",""))[:100]})
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result["probe_generated_text"] else 6

if __name__=="__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"stage":"PROBE_EXCEPTION",
                          "error_type":type(exc).__name__,
                          "original_or_draft_sent":False}))
        sys.exit(7)
