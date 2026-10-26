"""0.AP forensic replay of FOUR original DeepSeek turns, ZERO model calls.

Actions 40259961845, artifact 12624461773. Provider answers are source
bytes; never redo author text, alter quoted prose or fix bad model trace
to satisfy G. Verify all EIGHT paid DeepSeek provider wires and prompt SHAs.

This is the exact V96 G path, including the EXISTING source citation spelling
normalizer and strict check_turn -> reviewed literary-prose fallback. The
first three turns must replay identically (one original source-only debt);
T04 must survive with an explicit inherited review-only debt after 0.AP
repair, not be mislabeled as a proved causal parent. No model, R2, Canon,
literary grade or second narrative memory.
"""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import json,re

from writerforge.v96_causal_turns import (
    check_turn,review_only_model_turn,trace_failure_reviewable,
    normalize_model_source_citations,parse_turn_outline,
    V96CausalDraftError,
)
from writerforge.writing_assist import _normalize_optional_model_craft_labels

PRIOR=Path("wf0ap_existing_original_0ao")
OUT=Path("wf_0ap_four_original_writer_turns_zero_paid_replay_20261026")
REAL_SOURCE_RUN=40259961845
REAL_AUTHOR_PROVIDER_WIRES=8
REAL_SOURCE_SHA="4069722777f98ef5b9bc3b3eaea5429def9ab9b61be0a224114fae9d7ff97991"
EXPECTED_WIRES=(
    "c572853f540c069946758e7444d47a1150415698294530d911f2eddd84f288cc",
    "e62740e9885408a7910e4d38f38578af18bf18c7440c595f45187ea993bc9236",
    "8c1127c543637d943fc7ccf439f987927c523295ba8737246ede91576ae0fd13",
    "55346979417390a026dc94aa5ebe3b7eb839a7e698b0c58c895919bc8dee6486",
    "792a6e4b83f4c13a5a3fe61b88e26a388d250f93d46a29f4efc0625519fd5b05",
    "8d3f408747d5dab67aa9f81f64343f4d8fa7014dad25ff195c2f3e44e0f5a0a4",
    "564333adc670ae29d8ced126d26cf5af8f7d326711f9bddcc055e3281bdf0598",
    "50e0fe1ff0f36a02fdb127e1d82d493ac7f315e5ff0a06b7130edf84ead2344f",
)


def h(x):
    return sha256(x if isinstance(x,bytes) else x.encode("utf8")).hexdigest()


def require(value,code):
    if not value:raise RuntimeError(code)


def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2),
                    encoding="utf8")


def real_frozen_eight():
    report=json.loads((PRIOR/"STATUS.json").read_text("utf8"))
    require(report["format"]=="wf.0ao.reuse-two-real-author-plans-prose-only-g.v1"
            and report["status"]=="SOURCE_OR_NEW_AUTHOR_PROSE_HOLD_NO_RETRY"
            and report["failure_code"]==
                "WF96_SCENE_TURN_REJECTED_WF96_NONCAUSAL_PARENT_SOURCE_INVALID"
            and report["new_model_calls"]==REAL_AUTHOR_PROVIDER_WIRES
            and report["original_author_source_sha256"]==REAL_SOURCE_SHA
            and report["old_real_plan_replayed_without_model"] is True
            and report["old_real_six_event_plan_preserved"] is True
            and report["R2_reads"]==report["R2_writes"]==report["Canon_writes"]==0,
            "WF0AP_FROZEN_PRIOR_MODEL_RUN_MANIFEST_CHANGED")
    latest=next(iter(sorted((PRIOR/"g-original-plan-new-prose-only").glob(
        "auto-*/chapter-001-turn-01-raw.json"))),None)
    require(latest is not None,"WF0AP_REAL_MODEL_PROSE_FILES_NOT_FOUND")
    job=latest.parent
    require(len(list((PRIOR/"g-original-plan-new-prose-only").glob("auto-*")))==1,
            "WF0AP_MORE_THAN_ONE_PRIOR_JOB_NOT_FROZEN")
    raw_plan=(PRIOR/"frozen-six-turn-original.json").read_text("utf8")
    require(h(raw_plan)==report["original_model_turn_outline_sha256"],
            "WF0AP_REAL_MODEL_EVENT_PLAN_SHA_MISMATCH")
    plan,_=_normalize_optional_model_craft_labels(raw_plan)
    turns=parse_turn_outline(plan)
    require(len(turns)==6 and turns[2]["causal_parent"]=="t02"
            and turns[3]["causal_parent"]=="t03"
            and turns[5]["causal_parent"]=="t05",
            "WF0AP_REAL_MODEL_EVENT_CHAIN_CHANGED")
    paid=[]
    for index,old in enumerate(report["new_provider_events"],1):
        require(index==old["index"] and
                old["provider_wire_saved_before_json_validation"] is True,
                "WF0AP_ORIGINAL_EVENT_ORDER_OR_PRESERVATION_CHANGED")
        provider=(PRIOR/"provider-originals"/f"new-{index:02d}.json").read_bytes()
        require(h(provider)==EXPECTED_WIRES[index-1]==old["raw_provider_sha256"],
                "WF0AP_REAL_PROVIDER_RAW_SHA_CHANGED")
        request=json.loads((PRIOR/"new-model-requests"/
                           f"{index:02d}-request.json").read_text("utf8"))
        require(h(request["prompt"])==request["prompt_sha256"]==
                old["prompt_sha256"],
                "WF0AP_ORIGINAL_REQUEST_PROMPT_CHANGED")
        envelope=json.loads(provider)
        require(envelope["model"]=="deepseek-flash"
                and len(envelope["choices"])==1
                and envelope["choices"][0]["finish_reason"]=="stop",
                "WF0AP_PROVIDER_MODEL_OR_FINISH_CHANGED")
        decoded=json.loads(envelope["choices"][0]["message"]["content"])
        require(h(json.dumps(decoded,ensure_ascii=False,separators=(",",":")))==
                old["decoded_sha256"],
                "WF0AP_ORIGINAL_DECODED_RESPONSE_CHANGED")
        paid.append(decoded)
    for pos,idx in enumerate((1,3,5,7),1):
        source=json.loads((job/f"chapter-001-turn-{pos:02d}-raw.json").read_text("utf8"))
        require(source==paid[idx-1] and type(source.get("prose")) is str
                and type(source.get("trace")) is dict,
                "WF0AP_AUTHOR_SOURCE_NOT_MATCHING_PROVIDER_WIRE")
    return turns,tuple(paid[idx-1] for idx in (1,3,5,7)),report


def replay_real_model_wires():
    beats,raw_docs,manifest=real_frozen_eight()
    accepted=[]
    codes=[]
    for turn_index,(beat,doc) in enumerate(zip(beats,raw_docs),1):
        original=json.dumps(doc,ensure_ascii=False,separators=(",",":"))
        normalized,spelling=normalize_model_source_citations(
            original,beat,accepted=tuple(accepted))
        require(json.loads(normalized)["prose"]==doc["prose"],
                "WF0AP_NORMALIZER_CHANGED_REAL_AUTHOR_PROSE")
        try:
            item=check_turn(normalized,beat,accepted=tuple(accepted),
                            mode="causal_guard",max_prose_chars=1024)
            status="QUOTE_SOURCE_VALID_CAUSALITY_UNPROVEN"
            error=None
        except V96CausalDraftError as ex:
            error=str(ex)
            require(trace_failure_reviewable(error),
                    "WF0AP_REAL_PROSE_HARD_REJECTION_"+error)
            item=review_only_model_turn(
                normalized,beat,failure_code=error,
                accepted=tuple(accepted),max_prose_chars=1024)
            status="SOURCE_VALID_TRACE_REVIEW_UNRESOLVED"
        require(item["prose"]==doc["prose"] and
                item["receipt"]["prose_sha256"]==h(doc["prose"]) and
                item["receipt"]["causal_relation_verified"] is False and
                item["receipt"]["eligible_for_factjournal_KNOWN"] is False,
                "WF0AP_SOURCE_ONLY_FICTION_CERTIFIED_AS_TRUTH")
        accepted.append(item)
        codes.append({
            "turn_id":beat["id"],"original_prose_sha256":h(doc["prose"]),
            "source_status":status,"trace_error":error,
            "review_only":item["receipt"]["causal_check"]==
                "TRACE_REJECTED_SOURCE_PROSE_REVIEW_ONLY",
            "parent_review_only_source_sha256":item["receipt"].get(
                "parent_review_only_source_sha256"),
            "no_fact_or_canon_promotion":True,
            "model_calls_for_replay":0,
        })
    require(len(accepted)==4 and
            codes[2]["review_only"] is True and
            codes[3]["trace_error"]==
                "WF96_PARENT_REVIEW_ONLY_TRACE_REQUIRES_REVIEW" and
            codes[3]["parent_review_only_source_sha256"]==
                codes[2]["original_prose_sha256"],
            "WF0AP_REAL_4TH_LITERARY_TURN_REVIEW_DID_NOT_PROPAGATE")
    return codes


def main():
    require(not OUT.exists(),"WF0AP_NO_REPLAY_OUTPUT_OVERWRITE")
    OUT.mkdir()
    status={
        "format":"wf.0ap.four-original-provider-prose-v96-review-replay.v1",
        "source_run":REAL_SOURCE_RUN,
        "new_model_calls":0,"old_provider_wires_verified":0,
        "originals_rewritten":False,"new_fiction_written_by_host":False,
        "R2_reads":0,"R2_writes":0,"Canon_writes":0,
        "source_review_not_literary_truth":True,
        "status":"SOURCE_NOT_VERIFIED","turns":[]}
    try:
        codes=replay_real_model_wires()
        status["old_provider_wires_verified"]=8
        status["turns"]=codes
        status["status"]="FOUR_REAL_PROSE_PRESERVED_SOURCE_REVIEW_ONLY"
    except Exception as ex:
        status["status"]="REPLAY_SOURCE_RED_PRESERVED"
        status["error_code"]=str(ex)[:200]
    finally:
        save(OUT/"STATUS.json",status)
        print("WF0AP_SOURCE_REPLAY "+json.dumps({
            "status":status["status"],"new_model_calls":0,
            "wires":status["old_provider_wires_verified"],
            "turn_status":[(r["turn_id"],r["source_status"],r["trace_error"])
                           for r in status["turns"]],
            "error":status.get("error_code"),
        },ensure_ascii=False),flush=True)
    if status["status"]!="FOUR_REAL_PROSE_PRESERVED_SOURCE_REVIEW_ONLY":
        raise RuntimeError("WF0AP_REAL_SOURCE_REPLAY_HOLD")


if __name__=="__main__":
    main()
