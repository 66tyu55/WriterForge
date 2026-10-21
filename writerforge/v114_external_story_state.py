"""V114 ACTUAL WriterForge integration of pinned MIT Novel Studio reducer.

This is not an external AI or a second story database. Novel Studio's
original schema/reducer check atomic, time-ordered "before -> after" state
for objects, characters and other allowed domains. The Python adapter
creates only source-anchored candidate events, with unresolved cases left
for independent review. State is passed to the NEXT WRITER TURN and stored
with the existing WF candidate receipt; zero network, zero model requests.

External source: bbaz123/novel-studio@b585a9ca4ce474fe2471bf3bb7f8c284c6e4104a
MIT license preserved in experiments/v114_fallback_novel_studio/LICENSE.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import re
import shutil
import subprocess

from .v114_continuity_memory import (
    literal_item_continuity,TRACKED,SOFT_NARRATION,packed,hashb,
)

FORMAT="wf.fallback.novel-studio.result.v114"
MAX_PACKET_BYTES=130000
NODE_TIMEOUT_SECONDS=10
SHIM=(Path(__file__).resolve().parents[1]/
      "experiments/v114_fallback_novel_studio/bridge.mjs")

class V114ExternalMemoryError(ValueError):
    pass

def need(ok,code):
    if not ok:raise V114ExternalMemoryError(code)

def _quote_for_span(text,position,length=2):
    """Exact single source sentence (not a model's 'remembered' paraphrase)."""
    delimiters="。！？；\n"
    left=max(text.rfind(mark,0,position) for mark in delimiters)+1
    endpoints=[x for m in delimiters if (x:=text.find(m,position))!=-1]
    right=min(endpoints)+1 if endpoints else len(text)
    quote=text[left:right]
    if not (3<=len(quote)<=150) or text.count(quote)!=1:
        return None
    if any(v in quote for v in SOFT_NARRATION):
        return None
    return quote,left

def _last_candidate_holders(report):
    active={}
    if report is None:return active
    need(report.get("format")=="wf.writing.candidate-literal-continuity.v114",
         "WF114_EXTERNAL_BAD_NATIVE_EVIDENCE")
    for entry in report.get("active_state",[]):
        active[entry["item"]]=entry["holder_hypothesis"]
    return active

def _state_key(item):
    return json.dumps(["item",item,"holder","author_plan",None],
                      ensure_ascii=False,separators=(",",":"))

def _prior_owners(state):
    """State transferred from original reducer; never trust writer's labels."""
    result={}
    for key,value in state.items():
        try: cell=json.loads(key)
        except (TypeError,ValueError): continue
        if (type(cell) is list and len(cell)==5 and
            cell[0]=="item" and cell[2]=="holder" and
            cell[3]=="author_plan" and type(value) is str):
            result[cell[1]]=value
    return result

def actual_item_events(prose,*,cast=(),prior_state=None):
    """Ground event claims in literal prose, retain possible false positives."""
    report=literal_item_continuity(prose,cast=cast)
    original=report["observations"]
    former=_prior_owners(prior_state or {})
    events=[]
    for i,entry in enumerate(original,1):
        item=entry["item"]
        current=entry["holder_hypothesis"]
        anchor=entry["anchor"]
        source=_quote_for_span(prose,anchor["start"])
        if source is None:continue
        quote,start=source
        old=former.get(item)
        if old==current:
            continue
        # A genuine transfer often appears in the immediately preceding
        # sentence, e.g. "取下剑穗，挂到索钩上。索钩上挂着...".
        # Join only adjacent short source clauses with the *same item*;
        # NEVER manufacture a transfer verb as a model repair.
        if old is not None and "挂到" not in quote and "扯下" not in quote:
            before=prose[:start]
            gap=max(before.rfind("。"),before.rfind("！"),
                    before.rfind("？"),before.rfind("；"))
            second_left=max(before.rfind("。",0,max(0,gap)),
                            before.rfind("！",0,max(0,gap)),
                            before.rfind("？",0,max(0,gap)),
                            before.rfind("；",0,max(0,gap)))+1
            widened=prose[second_left:start+len(quote)]
            if (widened.count(item)>=1 and 3<=len(widened)<=150
                and prose.count(widened)==1):
                quote,start=widened,second_left
        events.append({
            "id":f"v114_e_{i:03d}",
            "evidence":{"quote":quote,"start":start,
                        "end":start+len(quote),
                        "narrative":"present"},
            "ops":[{
                "type":"set",
                "cell":{"domain":"item","entityId":item,
                        "predicate":"holder","scope":"author_plan"},
                "expected":({"kind":"missing"} if old is None else
                            {"kind":"value","value":old}),
                "value":current,
            }]
        })
        former[item]=current
    return report,events

def external_temporal_step(prose,*,cast=(),prior=None,backup_required=True):
    """Use REAL upstream temporal reducer; hard failure without Node.

    A detected contradiction is never secretly auto-repaired. Without
    enough source evidence, marker remains NEEDS_REVIEW and old state stays.
    """
    need(type(prose) is str and 0<len(prose)<=20000,
         "WF114_EXTERNAL_SOURCE_BOUNDS")
    old={}
    prev_sha=None
    seq=1
    if prior is not None:
        need(type(prior) is dict and prior.get("format")==
             "wf.writing.external-temporal-checkpoint.v114"
             and prior.get("receipt_sha256")==hashb(packed({
                 k:v for k,v in prior.items() if k!="receipt_sha256"})),
             "WF114_EXTERNAL_PRIOR_CANDIDATE_HASH_MISMATCH")
        need(prior.get("semantic_truth_verified") is False and
             prior.get("canon_writes")==0,
             "WF114_EXTERNAL_CANON_WAS_FAKED")
        old=prior["reducer_result"]["candidate_state"]
        prev_sha=prior["receipt_sha256"]
        seq=prior["sequence"]+1
    report,events=actual_item_events(prose,cast=cast,prior_state=old)
    need(len(events)<=55,"WF114_EXTERNAL_EVENT_LIST_UNBOUNDED")
    packet={
        "format":"wf.fallback.novel-studio.input.v114",
        "source_prose":prose,
        "events":events,"prior_state":old,
    }
    raw=packed(packet)
    need(len(raw)<=MAX_PACKET_BYTES,
         "WF114_EXTERNAL_INPUT_TOO_LARGE")
    command=shutil.which("node")
    need(command is not None and SHIM.is_file(),
         "WF114_EXTERNAL_LICENSED_NODE_RUNTIME_UNAVAILABLE")
    try:
        p=subprocess.run(
            [command,str(SHIM)],input=raw,capture_output=True,
            timeout=NODE_TIMEOUT_SECONDS,check=False,
        )
    except (OSError,subprocess.TimeoutExpired):
        raise V114ExternalMemoryError("WF114_EXTERNAL_REDUCER_PROCESS_FAILED") from None
    need(p.returncode==0 and len(p.stdout)<=MAX_PACKET_BYTES,
         "WF114_EXTERNAL_REDUCER_FAILED_CLOSED")
    try: result=json.loads(p.stdout.decode("utf8","strict"))
    except (UnicodeError,ValueError):
        raise V114ExternalMemoryError("WF114_EXTERNAL_OUTPUT_NOT_VALID_JSON") from None
    need(result.get("format")==FORMAT and
         result.get("source_sha256")==hashb(prose.encode("utf8")) and
         result.get("canon_writes")==0 and
         result.get("model_calls")==0 and
         result.get("network_calls")==0 and
         result.get("no_automatic_canon_promotion") is True and
         result.get("literary_semantics_verified") is False,
         "WF114_EXTERNAL_REDUCER_CERTIFICATE_INVALID")
    checkpoint={
        "format":"wf.writing.external-temporal-checkpoint.v114",
        "source_sha256":hashb(prose.encode("utf8")),
        "sequence":seq,"previous_checkpoint_sha256":prev_sha,
        "original_native_candidate_report":report,
        "source_anchored_events_count":len(events),
        "reducer_result":result,
        "semantic_truth_verified":False,
        "canon_writes":0,
        "model_calls":0,
        "original_source_not_rewritten":True,
        "external_memory_core":"MIT Novel Studio exact pinned schema/reducer",
    }
    checkpoint["receipt_sha256"]=hashb(packed(checkpoint))
    return checkpoint

def temporal_prompt(checkpoint):
    need(type(checkpoint) is dict and checkpoint.get("format")==
         "wf.writing.external-temporal-checkpoint.v114",
         "WF114_EXTERNAL_PROMPT_NEEDS_RECEIPT")
    output=checkpoint["reducer_result"]
    state=_prior_owners(output["candidate_state"])
    parts=["【真实正文中的候选物件状态（Novel Studio时态归约，非已确认正典）】"]
    for item,holder in sorted(state.items()):
        parts.append(f"{item}：此前明确由{holder}持有或位于该处。"
                     "后续移动必须有实际转移过程，不能靠抒情句子改变位置。")
    for risk in output.get("risks",[])[:5]:
        parts.append("旧候选未通过来源核验："+risk["kind"]+
                     "；如无法证实，保持旧状态并标记未知。")
    for risk in checkpoint["original_native_candidate_report"]["risks"][:4]:
        parts.append("需审查的行文连续性："+risk["kind"])
    parts.append("法器、武器和法力用掉后必须有来源才能再使用。"
                 "未知、幻术、倒叙可明说，不为了修补牺牲小说自然度。")
    return "\n".join(parts)[:1450]
