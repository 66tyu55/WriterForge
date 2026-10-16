"""Only verify 1M-capable DeepSeek pair and non-thinking gateway switch.

No private novel, no draft, no stored model response; redacted numeric metadata.
One short call per model, each at most 900 tokens.
"""
from __future__ import annotations
import json,os,sys
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
import ssl
from writerforge.reverse_discovery_models import ENDPOINT

MODELS=("deepseek-v4-flash-0731","deepseek-v4-pro-0813")
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None

def main():
    key=os.environ.get("DISCOVERY_API_KEY","")
    if len(key)<12:
        print('{"stage":"SECRET_UNAVAILABLE"}');return 2
    opener=build_opener(NoRedirect(),HTTPSHandler(context=ssl.create_default_context()))
    results=[]
    # First read the authenticated /models response metadata (no inference).
    req=Request("https://discovery-api.intern-ai.org.cn/v1/models",
                headers={"Authorization":"Bearer "+key},method="GET")
    metadata={}
    try:
        with opener.open(req,timeout=35) as resp:
            payload=json.loads(resp.read(120000))
        for item in payload.get("data",[]):
            if isinstance(item,dict) and item.get("id") in MODELS:
                metadata[item["id"]]={
                    k:v for k,v in item.items()
                    if k in ("context_length","context_window",
                             "max_context_length","max_model_len",
                             "max_output_tokens","max_completion_tokens")
                    and isinstance(v,(int,float))
                }
    except Exception:
        metadata={"availability":"LISTING_METADATA_UNAVAILABLE"}
    for model in MODELS:
        request={
            "model":model,
            "messages":[{"role":"system","content":"用一句简短中文回答，不要思考过程，只输出结论。"},
                        {"role":"user","content":"为什么下雨会影响赶路？"}],
            "max_tokens":900,
            "stream":False,
            "thinking":{"type":"disabled"},
        }
        req=Request(ENDPOINT,data=json.dumps(request,ensure_ascii=False).encode(),
                    method="POST",headers={"Authorization":"Bearer "+key,
                    "Content-Type":"application/json"})
        result={"model":model}
        try:
            with opener.open(req,timeout=100) as resp:
                doc=json.loads(resp.read(65536))
            choice=doc["choices"][0]
            message=choice["message"]
            content=message.get("content")
            result.update({
                "status":"VISIBLE_RESPONSE" if isinstance(content,str) and bool(content.strip()) else "EMPTY_VISIBLE_CONTENT",
                "visible_chars":len(content) if isinstance(content,str) else 0,
                "finish_reason":choice.get("finish_reason"),
                "usage":{k:doc.get("usage",{}).get(k)
                         for k in ("prompt_tokens","completion_tokens","total_tokens")
                         if type(doc.get("usage",{}).get(k)) is int},
            })
        except HTTPError as err:
            result["status"]="HTTP_"+str(err.code)
        except Exception as err:
            result["status"]=type(err).__name__
        results.append(result)
    print(json.dumps({"stage":"DISCOVERY_1M_PAIR_METADATA_AND_THINKING_PROBE",
                      "model_metadata":metadata,"results":results,
                      "original_sent":False,"generation_content_logged":False},
                      ensure_ascii=False,indent=2))
    return 0 if all(v["status"]=="VISIBLE_RESPONSE" for v in results) else 3

if __name__=="__main__":
    sys.exit(main())
