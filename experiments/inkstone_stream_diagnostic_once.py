"""Real Intern InkStone ChatCompletions streaming diagnostic, 1 request only.

Unlike high-reasoning defaults, Atria yielded actual visible short text but
its earlier nonstreaming ~900-han prose request timed out after 115s.
This isolated test checks SSE for the SAME tested model, without using any
private manuscript, and writes a full reproducibility receipt with NO raw
secrets or stream content printed in CI logs. Never retries itself.
"""
from __future__ import annotations

from pathlib import Path
from hashlib import sha256
from urllib.request import Request,build_opener,HTTPSHandler,HTTPRedirectHandler
from urllib.error import HTTPError,URLError
import json,os,ssl,sys,time

from experiments.seven_literary_scenes_inkstone_ab import scenarios,make_packet

BASE="https://discovery-api.intern-ai.org.cn/v1"
MODEL="Atria-Dawn-Preview"
OUT=Path("wf_inkstone_stream_diagnostic")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None


def main():
    OUT.mkdir(exist_ok=False)
    case=scenarios()[0]
    bare,_,_,_,prompt_receipt=make_packet(case)
    key=os.environ.get("DISCOVERY_API_KEY","")
    result={
        "format":"wf.intern.atria.streaming-single-request-diagnostic",
        "model":MODEL,"url_base":BASE,
        "input_prompt_sha256":sha256(bare.encode()).hexdigest(),
        "max_requests":1,"requests_attempted":0,
        "max_completion_tokens":3100,"scenario":"剧情",
        "stream":True,"contains_user_original_prose":False,
        "R2_writes":0,"canon_writes":0,
        "visible_characters":0,"visible_han":0,
        "finish_reason":None,"reasoning_characters_seen":0,
        "status":"INITIALIZED",
        "wf_prompt_packet_verified":prompt_receipt[
            "wf_prompt_verified_hard_context"],
    }
    text_parts=[]
    def save():
        (OUT/"STATUS.json").write_text(json.dumps(
            result,ensure_ascii=False,sort_keys=True,indent=2),encoding="utf8")
        (OUT/"VISIBLE_ORIGINAL.json").write_text(json.dumps(
            {"original_text":"".join(text_parts),
             "synthetic_only":True,
             "source_seed_sha256":prompt_receipt["chapter1_sha256"]},
            ensure_ascii=False,indent=2),encoding="utf8")
    save()
    if len(key)<12:
        result["status"]="NO_CREDENTIAL"
        save()
        return 2
    req_data={
        "model":MODEL,
        "messages":[
            {"role":"system","content":
             "原创中文小说作家。只输出小说正文；无解释、无标题、无写作方法说明。"},
            {"role":"user","content":bare}],
        "temperature":0.7,"stream":True,"max_tokens":3100,
        "stream_options":{"include_usage":True},
    }
    req=Request(BASE+"/chat/completions",method="POST",
                headers={"Authorization":"Bearer "+key,
                         "Content-Type":"application/json",
                         "Accept":"text/event-stream"},
                data=json.dumps(req_data,ensure_ascii=False).encode())
    opener=build_opener(NoRedirect(),HTTPSHandler(context=ssl.create_default_context()))
    t=time.monotonic()
    result["requests_attempted"]=1
    result["status"]="REQUEST_STARTED"
    save()
    seen_bytes=0
    events=0
    saw_done=False
    try:
        with opener.open(req,timeout=245) as response:
            result["http_status"]=response.status
            for raw in response:
                seen_bytes+=len(raw)
                if seen_bytes>1600000:
                    result["status"]="STREAM_TOTAL_BYTES_EXCEEDED"
                    break
                if time.monotonic()-t>270:
                    result["status"]="STREAM_DEADLINE"
                    break
                line=raw.decode("utf8","replace").strip()
                if not line.startswith("data:"):
                    continue
                payload=line[5:].strip()
                if payload=="[DONE]":
                    saw_done=True
                    break
                if not payload:
                    continue
                try:
                    event=json.loads(payload)
                except ValueError:
                    result["sse_parse_errors"]=result.get("sse_parse_errors",0)+1
                    continue
                events+=1
                result["usage"]=event.get("usage") if type(
                    event.get("usage")) is dict else result.get("usage")
                choices=event.get("choices") or []
                if type(choices) is not list:
                    continue
                for choice in choices[:1]:
                    if type(choice) is not dict:
                        continue
                    delta=choice.get("delta") or {}
                    if type(delta) is not dict:
                        continue
                    frag=delta.get("content")
                    if type(frag) is str:
                        text_parts.append(frag)
                    elif type(frag) is list:
                        text_parts.extend(p.get("text","") for p in frag
                                          if type(p) is dict and
                                          type(p.get("text")) is str)
                    for rk in ("reasoning_content","reasoning"):
                        v=delta.get(rk)
                        if type(v) is str:
                            result["reasoning_characters_seen"]+=len(v)
                    finish=choice.get("finish_reason")
                    if finish is not None:
                        result["finish_reason"]=finish
    except HTTPError as exc:
        result["http_status"]=exc.code
        result["status"]="HTTP_ERROR"
    except (TimeoutError,URLError,OSError) as exc:
        result["status"]="TRANSPORT_ERROR"
        result["exception_type"]=type(exc).__name__
    result["elapsed_seconds"]=round(time.monotonic()-t,1)
    visible="".join(text_parts)
    result["visible_characters"]=len(visible)
    result["visible_han"]=sum("\u3400"<=ch<="\u9fff" for ch in visible)
    result["sse_events"]=events
    result["done_seen"]=saw_done
    result["visible_sha256"]=sha256(visible.encode()).hexdigest()
    if result["visible_han"]>=650 and result["status"]=="REQUEST_STARTED":
        result["status"]="STREAMING_SUBSTANTIVE_ORIGINAL_COMPLETED"
    elif result["status"]=="REQUEST_STARTED":
        result["status"]="STREAM_NO_SUFFICIENT_VISIBLE_PROSE"
    save()
    print(json.dumps({
        k:result[k] for k in (
            "status","http_status","elapsed_seconds",
            "visible_han","visible_characters","sse_events",
            "finish_reason","done_seen","reasoning_characters_seen"
        ) if k in result},ensure_ascii=False))
    return 0 if result["status"]=="STREAMING_SUBSTANTIVE_ORIGINAL_COMPLETED" else 4


if __name__=="__main__":
    sys.exit(main())
