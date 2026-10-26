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
from .v115_dynamic_entity_candidates import (
    discover_candidates,compact_entity_context,
)
from .v116_state_delta import (
    extract_state_events,compact_verified_delta_context,
)
from .v117_continuity_debts import merge_open_debts,compact_debts

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

def require_external_runtime():
    binary=shutil.which("node")
    need(binary is not None and SHIM.is_file(),
         "WF114_EXTERNAL_LICENSED_NODE_RUNTIME_UNAVAILABLE")
    return binary


def external_temporal_step(prose,*,cast=(),prior=None):
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
    named_candidates=discover_candidates(prose)
    dynamic_delta=extract_state_events(prose,cast=cast,prior_state=old)
    # V122 audits all known item cells rather than the first fruit and
    # source-verifies any additional actor-bound transfer *before* allowing
    # the unchanged pinned MIT reducer to apply expected-old-value ops.
    from .v122_item_provenance import (
        audit_item_provenance,supplemental_reducer_events)
    multi_item=audit_item_provenance(
        prose=prose,previous_candidate_state=old,cast=cast)
    # Same V114 signed checkpoint carries V122's source-only relation review.
    # No relation is written into the reducer's item holder/knowledge cells.
    from .v122_item_provenance import audit_physical_relation_sources
    prior_relation=(prior.get("v122_physical_relation_source_receipt")
                    if prior is not None else None)
    relation_review=audit_physical_relation_sources(
        prose=prose,previous_relation_receipt=prior_relation)
    supplemental=supplemental_reducer_events(
        prose=prose,audit=multi_item,
        earlier_events=events+dynamic_delta["source_anchored_events"])
    # One PINNED reducer, one candidate state. Existing V116 events win
    # duplicates; V122 fills only gaps in explicit time-ordered transfers.
    events=sorted(events+dynamic_delta["source_anchored_events"]+
                  supplemental,key=lambda e:e["evidence"]["start"])
    need(len(events)<=30,"WF116_EXTERNAL_EVENT_LIST_UNBOUNDED")
    packet={
        "format":"wf.fallback.novel-studio.input.v114",
        "source_prose":prose,
        "events":events,"prior_state":old,
    }
    raw=packed(packet)
    need(len(raw)<=MAX_PACKET_BYTES,
         "WF114_EXTERNAL_INPUT_TOO_LARGE")
    command=require_external_runtime()
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
    # Upstream can refuse an entire atomic batch on a stale expected value.
    # Do not pretend that state verification succeeded or move to the next
    # draft on a silent no-op. Old V113 UNPROVEN transfer is a separate,
    # reportable, non-fatal unresolved risk (not reducer error_code).
    need(result.get("error_code") is None,
         "WF116_NOVEL_STUDIO_PRECONDITION_OR_REDUCER_FAILED_CLOSED")
    checkpoint={
        "format":"wf.writing.external-temporal-checkpoint.v114",
        "source_sha256":hashb(prose.encode("utf8")),
        "sequence":seq,"previous_checkpoint_sha256":prev_sha,
        "original_native_candidate_report":report,
        "dynamic_source_entity_candidates":named_candidates,
        "v116_anchored_state_delta":dynamic_delta,
        "v122_item_provenance_audit":multi_item,
        "v122_physical_relation_source_receipt":relation_review,
        "v122_relation_review_not_a_reducer_cell":True,
        "v122_extra_reducer_source_events":supplemental,
        "v122_extra_reducer_events_count":len(supplemental),
        "v122_model_guess_not_source_evidence":True,
        "dynamic_entity_mentions_are_not_events":True,
        "source_anchored_events_count":len(events),
        "reducer_result":result,
        "semantic_truth_verified":False,
        "canon_writes":0,
        "model_calls":0,
        "original_source_not_rewritten":True,
        "external_memory_core":"MIT Novel Studio exact pinned schema/reducer",
    }
    checkpoint["v117_open_continuity_debts"]=merge_open_debts(
        prior,checkpoint)
    checkpoint["receipt_sha256"]=hashb(packed(checkpoint))
    return checkpoint

def temporal_prompt(checkpoint):
    need(type(checkpoint) is dict and checkpoint.get("format")==
         "wf.writing.external-temporal-checkpoint.v114",
         "WF114_EXTERNAL_PROMPT_NEEDS_RECEIPT")
    output=checkpoint["reducer_result"]
    state=_prior_owners(output["candidate_state"])
    parts=["【真实正文中的候选物件状态（Novel Studio时态归约，非已确认正典）】"]
    open_debts=compact_debts(checkpoint)
    if open_debts:parts.append(open_debts)
    custody=(checkpoint.get("v122_physical_relation_source_receipt") or {})
    pending=custody.get("document_custody_open_source_reviews",[])
    if pending:
        # SOURCE-anchored question inside the original signed V114/V122
        # checkpoint. It does not assert that two booklet descriptions
        # refer to the same object, that off-page return is impossible,
        # or that the author must revise. Only the writing AI chooses.
        item=pending[-1]
        parts.append(
            "【前文实物去向待来源复核，非已判文学错误】"
            +"先前写到「"+item["earlier_source_quote"][:65]
            +"」，后来写到「"+item["later_source_quote"][:65]
            +"」。可能是另一本、回叙或省略的交还；"
            "这些解释均未被软件证明。"
            "后续如依赖此物件的归属，先保留未知，不要凭空认定归还。"
            "文学留白或改写由原作者自行判断。")
    if checkpoint.get("v116_anchored_state_delta"):
        parts.append(compact_verified_delta_context(
            checkpoint["v116_anchored_state_delta"],output))
    for item,holder in sorted(state.items()):
        parts.append(f"{item}：此前明确由{holder}持有或位于该处。"
                     "后续移动必须有实际转移过程，不能靠抒情句子改变位置。")
    for risk in output.get("risks",[])[:5]:
        parts.append("旧候选未通过来源核验："+risk["kind"]+
                     "；如无法证实，保持旧状态并标记未知。")
    for risk in checkpoint["original_native_candidate_report"]["risks"][:4]:
        if risk["kind"]=="ITEM_OWNER_CHANGE_WITHOUT_TRANSFER":
            parts.append("连续性未核验："+str(risk["item"])+"此前由"+
                str(risk["before_holder"])+"持有，本段却声称出现在"+
                str(risk["after_claimed_holder"])+
                "；并无已证的转移过程，下一段不能把这次移动当事实。")
        else:
            parts.append("需审查的行文连续性："+risk["kind"])
    if checkpoint.get("dynamic_source_entity_candidates"):
        parts.append(compact_entity_context(
            checkpoint["dynamic_source_entity_candidates"]))
    parts.append("法器、武器和法力用掉后必须有来源才能再使用。"
                 "未知、幻术、倒叙可明说，不为了修补牺牲小说自然度。")
    return "\n".join(parts)[:1450]



def replay_revised_source_checkpoint(
        *,source_before,checkpoint_before,v119_preview_receipt,
        corrected_source,parent_checkpoint=None,cast=()):
    """Rebuild a NEW, signed V114 candidate from a real V119 text edit.

    Do not append the edited prose to the OLD candidate state. The old
    checkpoint and every derived later checkpoint remain a DIFFERENT draft
    branch and must not be reused as descendants of this revised source.
    The V119 preview's surgical source proof is checked *before* re-running
    the original pinned reducer; neither the host nor a model can erase
    unresolved debt by declaring a rewrite successful. No Canon/R2 calls.
    """
    from collections import Counter
    from .v119_revision_transaction import (
        FORMAT as REVISION_FORMAT,_digest_json,
    )
    from .v122_item_provenance import (
        audit_physical_relation_sources,physical_relation_issue_keys,
    )
    need(type(source_before) is str and
         type(corrected_source) is str and
         1<=len(source_before)<=20000 and
         1<=len(corrected_source)<=20000 and
         type(v119_preview_receipt) is dict and
         v119_preview_receipt.get("format")==REVISION_FORMAT and
         v119_preview_receipt.get("status")=="PROVISIONAL_REVIEW" and
         v119_preview_receipt.get("receipt_sha256")==_digest_json({
             k:v for k,v in v119_preview_receipt.items()
             if k!="receipt_sha256"}),
         "WF114_REVISION_TRANSACTION_NOT_PROVEN")
    original_sha=hashb(source_before.encode("utf8"))
    revised_sha=hashb(corrected_source.encode("utf8"))
    need(type(checkpoint_before) is dict and
         checkpoint_before.get("format")==
             "wf.writing.external-temporal-checkpoint.v114" and
         checkpoint_before.get("receipt_sha256")==hashb(packed({
             k:v for k,v in checkpoint_before.items()
             if k!="receipt_sha256"}) ) and
         checkpoint_before.get("source_sha256")==original_sha and
         v119_preview_receipt.get("source_sha256")==original_sha and
         v119_preview_receipt.get("candidate_sha256")==revised_sha and
         v119_preview_receipt.get("only_declared_selection_changed") is True,
         "WF114_REVISION_WRONG_SOURCE_OR_SIGNED_CHECKPOINT")
    selection=v119_preview_receipt.get("selection")
    need(type(selection) is list and len(selection)==2 and
         all(type(n) is int for n in selection) and
         0<=selection[0]<selection[1]<=len(source_before),
         "WF114_REVISION_INVALID_SELECTED_SPAN")
    start,end=selection
    prefix,selected,suffix=(
        source_before[:start],source_before[start:end],source_before[end:])
    need(corrected_source.startswith(prefix) and
         corrected_source.endswith(suffix) and
         len(corrected_source)>=len(prefix)+len(suffix),
         "WF114_REVISION_UNRELATED_TEXT_CHANGED")
    new_end=(len(corrected_source)-len(suffix)
             if suffix else len(corrected_source))
    replacement=corrected_source[start:new_end]
    need(hashb(selected.encode("utf8"))==
             v119_preview_receipt.get("expected_selection_sha256") and
         hashb(replacement.encode("utf8"))==
             v119_preview_receipt.get("replacement_sha256") and
         hashb(prefix.encode("utf8"))==
             v119_preview_receipt.get("untouched_prefix_sha256") and
         hashb(suffix.encode("utf8"))==
             v119_preview_receipt.get("untouched_suffix_sha256"),
         "WF114_REVISION_SELECTED_TEXT_NOT_SOURCE_LOCKED")
    if parent_checkpoint is None:
        need(checkpoint_before.get("sequence")==1 and
             checkpoint_before.get("previous_checkpoint_sha256") is None,
             "WF114_REVISION_MISSING_OR_WRONG_PARENT")
    else:
        need(type(parent_checkpoint) is dict and
             parent_checkpoint.get("receipt_sha256")==hashb(packed({
                 k:v for k,v in parent_checkpoint.items()
                 if k!="receipt_sha256"}) ) and
             checkpoint_before.get("previous_checkpoint_sha256")==
                 parent_checkpoint.get("receipt_sha256") and
             checkpoint_before.get("sequence")==
                 parent_checkpoint.get("sequence",0)+1,
             "WF114_REVISION_MISSING_OR_WRONG_PARENT")
    old_physical=checkpoint_before.get(
        "v122_physical_relation_source_receipt")
    need(type(old_physical) is dict and
         old_physical.get("source_sha256")==original_sha and
         old_physical.get("receipt_sha256")==
             hashb(packed({
                 k:v for k,v in old_physical.items()
                 if k!="receipt_sha256"})),
         "WF114_REVISION_OLD_RELATION_SOURCE_UNTRUSTED")
    # A generic warning "NEEDS_SOURCE_RELATION_REVIEW" is not a
    # per-object identity; use source-key multiplicities instead.
    old_keys=physical_relation_issue_keys(old_physical)
    rebuilt=external_temporal_step(
        corrected_source,cast=cast,prior=parent_checkpoint)
    fresh_physical=rebuilt["v122_physical_relation_source_receipt"]
    new_keys=physical_relation_issue_keys(fresh_physical)
    retired=sorted((Counter(old_keys)-Counter(new_keys)).elements())
    newly_detected=sorted((Counter(new_keys)-Counter(old_keys)).elements())
    old_prior=[
        x for x in old_physical.get("open_relation_reviews",[])
        if x.get("origin_source_sha256")!=original_sha]
    fresh_open=fresh_physical["open_relation_reviews"]
    def identity(row):
        return (row["origin_source_sha256"],
                row["first_source_quote_sha256"],
                row["second_source_quote_sha256"])
    # Older chapters are immutable: editing the current chapter must not
    # magically cancel a prior unrelated source debt.
    need(all(any(identity(p)==identity(row) for p in fresh_open)
                 for row in old_prior),
         "WF114_REVISION_DROPPED_PREVIOUS_SOURCE_DEBT")
    return {
        "format":"wf.v114.v119-signed-revised-source-replay.v1",
        "status":"SOURCE_CHANGED_REQUIRES_DOWNSTREAM_REPLAY",
        "old_source_sha256":original_sha,
        "revised_source_sha256":revised_sha,
        "original_checkpoint_sha256":checkpoint_before["receipt_sha256"],
        "rebuilt_checkpoint_sha256":rebuilt["receipt_sha256"],
        "author_v119_preview_sha256":v119_preview_receipt["receipt_sha256"],
        "retired_old_source_relation_count":len(retired),
        "new_source_relation_count":len(fresh_open),
        "new_relation_issues_from_edit":newly_detected,
        "remaining_relation_review_count":len(fresh_open),
        "all_old_derived_downstream_invalidated":True,
        "no_old_downstream_may_be_reused_on_revised_branch":True,
        "existing_parent_source_debt_kept":True,
        "recomputed_unaccepted_v114_checkpoint":rebuilt,
        "source_state_semantics_not_fully_verified":True,
        "author_accepted":False,"literary_improvement_verified":False,
        "automatic_story_generation":False,
        "model_calls":0,"R2_writes":0,"canon_writes":0,
    }
