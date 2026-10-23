"""One independent Atria reasoning_effort=low compatibility probe on Discovery.

This is the fixed *climax* WF prompt that previously spent all 3,100 tokens
on reasoning with zero visible content. DO NOT assume upstream Atria support
automatically implies compatibility with the Intern InkStone gateway.
No retries, no private novel/R2, no second provider or production writes.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import os
import sys
import time

from experiments.seven_literary_scenes_inkstone_ab import (
    scenarios,make_packet,stream_chat,
)

DEST=Path("wf_atria_low_reasoning_climax_probe")


def main():
    DEST.mkdir(exist_ok=False)
    scenario=next(x for x in scenarios() if x["id"]=="climax")
    _,prompt,_,_,receipt=make_packet(scenario)
    report={
        "format":"wf.experiment.atria.climax.low-reasoning.v1",
        "provider":"Intern InkStone / Discovery",
        "model":"Atria-Dawn-Preview",
        "reasoning_effort":"low",
        "max_model_calls":1,"requested_output_tokens":3100,
        "calls":0,"source_sha256":receipt["chapter1_sha256"],
        "prompt_sha256":sha256(prompt.encode()).hexdigest(),
        "sends_synthetic_story_only":True,
        "no_private_user_novel":True,
        "R2_writes":0,"canon_writes":0,
        "original_full_text_saved":False,
        "status":"INITIALIZED",
    }
    def persist(original=""):
        (DEST/"STATUS.json").write_text(
            json.dumps(report,sort_keys=True,ensure_ascii=False,indent=2),
            encoding="utf8")
        (DEST/"VISIBLE_PROSE.json").write_text(
            json.dumps({"visible_text":original,
                        "visible_sha256":sha256(original.encode()).hexdigest(),
                        "source_is_synthetic":True},
                       ensure_ascii=False,indent=2),encoding="utf8")
    persist()
    key=os.environ.get("DISCOVERY_API_KEY","")
    if len(key)<12:
        report["status"]="NO_VALID_API_KEY"
        persist()
        return 2
    report["calls"]=1
    started=time.monotonic()
    result=stream_chat(
        key,"Atria-Dawn-Preview",prompt,3100,reasoning_effort="low")
    report.update({
        "elapsed_seconds":round(time.monotonic()-started,1),
        "status":("VISIBLE_TEXT_GENERATED" if result.get("ok")
                  else "LOW_EFFORT_NOT_WORKING_FOR_THIS_PROMPT"),
        "http_status":result.get("http_status"),
        "reason":result.get("kind"),
        "finish_reason":result.get("finish_reason"),
        "done_seen":result.get("done_seen"),
        "reported_usage":result.get("usage",{}),
        "reasoning_characters":result.get("reasoning_characters",0),
        "visible_characters":len(result.get("text","")),
        "visible_han":sum(
            "\u3400"<=ch<="\u9fff" for ch in result.get("text","")),
        "original_full_text_saved":bool(result.get("ok")),
        "sse_events":result.get("sse_events",0),
    })
    persist(result.get("text",""))
    print(json.dumps({k:v for k,v in report.items() if k in (
        "status","http_status","reason","finish_reason",
        "reported_usage","reasoning_characters","visible_han",
        "elapsed_seconds","sse_events")},ensure_ascii=False))
    return 0 if result.get("ok") else 5


if __name__=="__main__":
    sys.exit(main())
