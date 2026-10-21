"""WriterForge V117: extend existing MIT Novel Studio trace across chapters.

One existing v114/V116 source-anchored reducer checkpoint, not a second
long-term memory DB. Pinned MIT source supplies chapter-time, POV, explicit
knowledge-boundary, and prop-chain deterministic checks. A caller may pass
a small confirmed-reference view; absent rows are UNKNOWN, not "passed".
No model calls, R2 writes, source repair or canon promotion.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json
import re
import shutil
import subprocess

from .v114_continuity_memory import packed, hashb
from .v116_state_delta import preflight_next_prose

NODE=(Path(__file__).resolve().parents[1]/
      "experiments/v117_novel_studio/bridge.mjs")
REF="wf.continuity.v117.pinned-oss-temporal-view"
RESUME="wf.writing.v117.unreviewed-resume"
MAX_BYTES=160000
MAX_PROMPT_CHARS=900
SHA=re.compile(r"^[0-9a-f]{64}$")

class ContinuityTraceError(ValueError):
    pass

def need(ok,msg):
    if not ok: raise ContinuityTraceError(msg)

def digest(x):
    return sha256(x.encode("utf8")).hexdigest()

def _checkpoint(old):
    need(type(old) is dict and
         old.get("format")=="wf.writing.external-temporal-checkpoint.v114" and
         old.get("semantic_truth_verified") is False and
         old.get("canon_writes")==0 and
         old.get("model_calls")==0 and
         type(old.get("sequence")) is int and
         1<=old["sequence"]<=1000000,
         "WF117_UNTRUSTED_EXTERNAL_STATE")
    tag=old.get("receipt_sha256")
    need(type(tag) is str and SHA.fullmatch(tag) and
         tag==hashb(packed({k:v for k,v in old.items()
                           if k!="receipt_sha256"})),
         "WF117_PREVIOUS_CHECKPOINT_HASH_MISMATCH")
    result=old.get("reducer_result")
    need(type(result) is dict and
         result.get("format")=="wf.fallback.novel-studio.result.v114" and
         result.get("error_code") is None and
         result.get("canon_writes")==0 and
         result.get("literary_semantics_verified") is False and
         type(result.get("candidate_state")) is dict and
         len(result["candidate_state"])<=64 and
         len(packed(old))<=MAX_BYTES,
         "WF117_REDUCER_INVALID_OR_UNBOUNDED")
    return result

def _safe_ref(records):
    """Only machine-readable references already received from WF/author.

    No assumption that absence of a character knowledge card means known.
    """
    need(records is None or type(records) is dict,
         "WF117_REFERENCE_OBJECT_REQUIRED")
    src=records or {}
    need(set(src).issubset({
         "facts","timeline","knowledge","characters","prop_chains","pov_character_id"}),
         "WF117_REFERENCE_UNKNOWN_FIELD")
    for key,limit in (("facts",256),("timeline",128),("knowledge",256),
                      ("characters",36),("prop_chains",36)):
        val=src.get(key,[])
        need(type(val) is list and len(val)<=limit,
             "WF117_REFERENCE_TOO_LARGE_"+key.upper())
    need(len(packed(src))<=64000,"WF117_REFERENCE_BYTE_LIMIT")
    return src

def audit_continuity(checkpoint, *, project_id, chapter_index,
                     boundary="before", reference=None,next_prose=None):
    base=_checkpoint(checkpoint)
    need(type(project_id) is str and 0<len(project_id)<=128,
         "WF117_PROJECT_SCOPE_REQUIRED")
    need(type(chapter_index) is int and 0<=chapter_index<=1000000,
         "WF117_CHAPTER_INDEX_REQUIRED")
    ref=_safe_ref(reference)
    need(next_prose is None or
         type(next_prose) is str and len(next_prose)<=20000,
         "WF117_NEXT_PROSE_BOUNDS")
    need(boundary in ("before","after"),"WF117_BOUNDARY_INVALID")
    inp={
        "mode":"audit",
        "project_id":project_id,
        "chapter_index":chapter_index,
        "boundary":boundary,
        "source_checkpoint_sha256":checkpoint["receipt_sha256"],
        "candidate_state":base["candidate_state"],
        "next_prose":next_prose,
        **ref,
    }
    raw=packed(inp)
    need(len(raw)<=MAX_BYTES,"WF117_BRIDGE_INPUT_BOUNDS")
    node=shutil.which("node")
    need(node is not None and NODE.is_file(),
         "WF117_NODE_VENDOR_RUNTIME_MISSING")
    try:
        result=subprocess.run([node,str(NODE)],input=raw,capture_output=True,
                              timeout=12,check=False)
    except (OSError,subprocess.TimeoutExpired):
        raise ContinuityTraceError("WF117_BRIDGE_TIMED_OUT") from None
    need(result.returncode==0 and 0<len(result.stdout)<=MAX_BYTES,
         "WF117_BRIDGE_FAILED_CLOSED:"+result.stderr.decode(
             "utf8","replace")[:100])
    try:
        out=json.loads(result.stdout.decode("utf8","strict"))
    except (UnicodeError,ValueError):
        raise ContinuityTraceError("WF117_BAD_BRIDGE_JSON") from None
    need(type(out) is dict and
         out.get("format")==REF and
         out.get("project_id")==project_id and
         out.get("chapter_index")==chapter_index and
         out.get("source_checkpoint_sha256")==checkpoint["receipt_sha256"] and
         out.get("no_new_database") is True and
         out.get("no_model_call") is True and
         out.get("literary_truth_verified") is False and
         out.get("state_has_no_auto_canon_promotion") is True,
         "WF117_BRIDGE_RECEIPT_INVALID")
    return out

def compact_context(frame):
    need(type(frame) is dict and frame.get("format")==REF and
         frame.get("literary_truth_verified") is False,
         "WF117_PROMPT_FROM_UNTRUSTED_FRAME")
    lines=["【跨章节文本追踪·未确认候选不等于正文正典】"]
    for row in frame["confirmed_visible"][:6]:
        lines.append("已确认但仍需依原文遵守："+str(row["entity_id"])+
                     " "+str(row["predicate"])+"："+str(row["value"]))
    for row in frame["unreviewed_reducer_candidates"][:8]:
        name=str(row["entity_id"]); pred=str(row["predicate"])
        lines.append("历史候选状态："+name+" "+pred+"="+
                     str(row["value"])[:70]+"（未经作者确认，不能凭空改写）")
    for row in frame["prop_verdicts"][:3]:
        if not row["ok"]:
            lines.append("物件链需复核："+str(row["entity"])+" "+
                         str(row["code"]))
    for row in frame["chronology"]["order_conflicts"][:2]:
        lines.append("事件先后存在显式冲突："+row["code"])
    k=frame["knowledge"]
    if "pov_not_set" not in k:
        for row in k["unknown"][:3]:
            lines.append("当前视角未获知："+row["fact_key"])
        for row in k["suspected"][:3]:
            lines.append("当前视角只怀疑："+row["fact_key"])
        for row in k["false_beliefs"][:2]:
            lines.append("当前视角仍误信："+row["fact_key"])
    omissions=frame.get("omitted",{})
    if any(v>0 for k,v in omissions.items()
           if k not in ("outside_time","filtered_by_pov")):
        lines.append("还有部分已登记状态未装入本段，不能当成已消失；"
                     "需要时从原追踪快照按实体查询。")
    coverage=frame["coverage"]
    if not coverage["knowledge_coverage_proven"]:
        lines.append("人物知识尚未全面登记：不能声称所有知识越界已经排除。")
    if not coverage["time_coverage_proven"]:
        lines.append("完整时间线未登记：不能声称所有因果顺序已经检查。")
    lines.append("不要写出没有经过动作交接的物品移动、伤势痊愈或资源回满；"
                 "不得把后文秘密提前交给角色；未知保留未知。")
    return "\n".join(lines)[:MAX_PROMPT_CHARS]

def preflight_continuation(next_prose,checkpoint,*,project_id,chapter_index,
                           reference=None):
    old=_checkpoint(checkpoint)
    fast=preflight_next_prose(next_prose,
        previous_candidate_state=old["candidate_state"],
        previous_risks=old.get("risks",[])+
        checkpoint.get("original_native_candidate_report",{}).get("risks",[]))
    frame=audit_continuity(checkpoint,project_id=project_id,
         chapter_index=chapter_index,boundary="before",
         reference=reference,next_prose=next_prose)
    # Lexical knowledge hits cannot prove who actually said or knew the fact.
    # They are NEEDS_REVIEW, not categorical literary errors.
    return {
      "format":"wf.writing.v117.continuation-preflight",
      "next_prose_sha256":digest(next_prose),
      "hard_source_state_conflict":fast["blocked"],
      "state_findings":fast["findings"],
      "temporal_order_conflicts":frame["chronology"]["order_conflicts"],
      "knowledge_needs_review":frame["knowledge_warnings"],
      "prop_chain_findings":[x for x in frame["prop_verdicts"] if not x["ok"]],
      "needs_review":bool(frame["chronology"]["order_conflicts"] or
                          frame["knowledge_warnings"] or
                          any(not x["ok"] for x in frame["prop_verdicts"])),
      "blocked":fast["blocked"],
      "source_only":True,
      "no_model_call":True,
      "canon_writes":0,
    }

def make_resume(*,project_id,scene_id,chapter_index,checkpoint):
    _checkpoint(checkpoint)
    need(type(project_id) is str and 0<len(project_id)<=128 and
         type(scene_id) is str and 0<len(scene_id)<=128 and
         type(chapter_index) is int and 0<=chapter_index<=1000000,
         "WF117_RESUME_SCOPE_INVALID")
    p={
        "format":RESUME,"project_id":project_id,"scene_id":scene_id,
        "chapter_index":chapter_index,
        "source_checkpoint_sha256":checkpoint["receipt_sha256"],
        "source_prose_sha256":checkpoint["source_sha256"],
        "unreviewed_story_state_checkpoint":checkpoint,
        "author_accepted":False,
        "literary_truth_verified":False,
        "canon_writes":0,"model_calls":0,
    }
    need(len(packed(p))<=MAX_BYTES,"WF117_RESUME_TOO_BIG")
    p["receipt_sha256"]=hashb(packed(p))
    return p

def read_resume(value,*,project_id,scene_id):
    need(type(value) is dict and value.get("format")==RESUME and
         value.get("project_id")==project_id and
         value.get("scene_id")==scene_id and
         value.get("author_accepted") is False and
         value.get("literary_truth_verified") is False and
         value.get("canon_writes")==0 and
         type(value.get("chapter_index")) is int and
         0<=value["chapter_index"]<=1000000 and
         type(value.get("receipt_sha256")) is str and
         SHA.fullmatch(value["receipt_sha256"]) and
         value["receipt_sha256"]==hashb(packed({
           k:v for k,v in value.items() if k!="receipt_sha256"})) and
         len(packed(value))<=MAX_BYTES,
         "WF117_RESUME_SCOPE_OR_HASH_MISMATCH")
    old=value.get("unreviewed_story_state_checkpoint")
    _checkpoint(old)
    need(old["receipt_sha256"]==value.get("source_checkpoint_sha256") and
         old["source_sha256"]==value.get("source_prose_sha256"),
         "WF117_RESUME_EVENT_SOURCE_MISMATCH")
    return old
