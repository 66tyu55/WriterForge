"""Preserve the REAL same-model V119 source-locked private proposal, zero calls.

The original DeepSeek's elected LOOK_BACK_NOW was authentic. Its one true
V119 proposal did write a different prose sentence but used the identical
WHOLE replacement text in action_quote and effect_quote. V96 correctly
rejected it with WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED. This script
replays the original true source, provider wire and first V119 receipt,
produces a strictly private source-locked V119 preview and verifies that
V96 STILL blocks it. Never auto-fixes the model's semantic trace, never
promotes the preview to signed V117 or reuses old chapter turn2.
"""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import json

from experiments import wf_real_opera_author_selected_v119_once_20261025 as old
from experiments.wf_real_opera_cross_source_zero_model_receipt_20261025 import source_file
from writerforge.v96_causal_turns import check_turn,V96CausalDraftError
from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v117_continuity_trace import preflight_continuation
from writerforge.v119_revision_transaction import preview_revision

SOURCE=Path("wf_prior_opera_author_selected_v119_20261025")
OUTPUT=Path("wf_real_opera_v119_model_rejected_literal_preview_20261025")
RECEIPT_PROBLEM="WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED"

def digest(x):
    return sha256(x if type(x) is bytes else x.encode("utf8")).hexdigest()

def verified_model_proposal():
    entry=json.loads(source_file(SOURCE,"STATUS.json"))
    if (entry.get("status")!="REAL_V119_UNCHANGED_OR_STRICTLY_REJECTED" or
        entry.get("new_real_provider_requests")!=1 or
        entry.get("original_author_decision")!="LOOK_BACK_NOW" or
        entry.get("old_source_sha256")!=old.TARGET_SOURCE_SHA or
        entry.get("V119_round_statuses")!=["REJECTED_AND_ROLLED_BACK"] or
        entry.get("user_accepted_source_changed") is not False or
        entry.get("V117_full_new_chapter_signed") is not False or
        type(entry.get("real_original_model_wire_receipts")) is not list or
        len(entry["real_original_model_wire_receipts"])!=1):
        raise ValueError("WF_REAL_V119_ARCHIVED_NEGATIVE_CHANGED")
    original_source=source_file(SOURCE,
        "ORIGINAL_G_FIRST_TURN_UNCHANGED.md").decode("utf8")
    decision=source_file(SOURCE,"OLDER_AUTHOR_LOOK_BACK_ORIGINAL.json")
    wire=source_file(SOURCE,"01-AUTHOR_V119_PROVIDER_WIRE.json")
    response=source_file(SOURCE,"01-AUTHOR_V119_DECODED_RESPONSE.json")
    private=source_file(SOURCE,
        "V119_SAME_AUTHOR_PRIVATE_TRANSACTION/round-01-model-proposal.json")
    receipt=json.loads(source_file(SOURCE,
        "V119_SAME_AUTHOR_PRIVATE_TRANSACTION/self-edit-receipt.json"))
    proof=entry["real_original_model_wire_receipts"][0]
    if (response!=private or digest(response)!=proof.get("decoded_sha256") or
        digest(wire)!=proof.get("original_wire_sha256") or
        proof.get("wire_saved_before_parsing") is not True or
        original_source!=entry.get("old_source_sha256") and
            digest(original_source)!=old.TARGET_SOURCE_SHA):
        raise ValueError("WF_REAL_V119_ARCHIVED_WIRE_TAMPERED")
    if (digest(original_source)!=old.TARGET_SOURCE_SHA or
        receipt.get("rounds",[{}])[0].get("reason_code")!=RECEIPT_PROBLEM or
        entry.get("original_author_reply_sha256")!=digest(decision)):
        raise ValueError("WF_REAL_V119_FAILED_SEMANTIC_SOURCE_CHANGED")
    data=json.loads(response)
    fields={
        "decision","scope","source_sha256","start","end",
        "expected_original","replacement","trace","reason","type"}
    if (type(data) is not dict or set(data)!=fields or
        data["type"]!="json_object" or data["decision"]!="REVISE" or
        data["scope"]!="sentence" or
        data["source_sha256"]!=old.TARGET_SOURCE_SHA or
        not isinstance(data["expected_original"],str) or
        original_source.count(data["expected_original"])!=1 or
        data["trace"]["action_quote"]!=data["trace"]["effect_quote"]):
        raise ValueError("WF_REAL_V119_EXPECTED_EXACT_AUTHENTIC_FAILURE")
    return entry,original_source,data,response.decode("utf8")

def main():
    if OUTPUT.exists():
        raise RuntimeError("WF_REAL_V119_FORENSICS_NEVER_OVERWRITE")
    OUTPUT.mkdir(parents=True)
    old.OUTPUT=OUTPUT/"old-source-provenance-only"
    old.OUTPUT.mkdir()
    source,decided,_,raw_decision,_=old.prior_real_writer_decision()
    entry,original,edit,old_model=verified_model_proposal()
    if (source["source"]!=original or
        decided["decision"]!="LOOK_BACK_NOW" or
        decided["source_quote"]!=edit["expected_original"]):
        raise ValueError("WF_REAL_V119_OLDER_ACTUAL_AUTHOR_DECISION_DIFFERENT")
    prior=external_temporal_step(source["seed"],
                                 cast=("江遥","宋易"))
    start=original.index(edit["expected_original"])
    preview=preview_revision(
        project_id=old.PROJECT,scene_id=old.SCENE,
        source=original,source_sha256=old.TARGET_SOURCE_SHA,
        start=start,end=start+len(edit["expected_original"]),
        expected_original=edit["expected_original"],
        replacement=edit["replacement"],
        previous_candidate_state=prior["reducer_result"]["candidate_state"],
        cast=("江遥","宋易"))
    candidate=preview.get("candidate_prose")
    if preview.get("status")!="PROVISIONAL_REVIEW" or type(candidate) is not str:
        raise ValueError("WF_REAL_V119_SOURCE_LOCKED_PREVIEW_FAILED")
    rebuilt=json.dumps({
        "prose":candidate,"trace":edit["trace"],
    },ensure_ascii=False)
    try:
        check_turn(rebuilt,source["beat"],mode="causal_guard",accepted=())
    except V96CausalDraftError as e:
        v96=str(e)
    else:
        raise RuntimeError("WF_REAL_V119_V96_MUST_STILL_REJECT_MODEL_TRACE")
    if v96!=RECEIPT_PROBLEM:
        raise ValueError("WF_REAL_V119_CHANGED_REJECTION_CODE")
    continuation=preflight_continuation(
        candidate,prior,project_id=old.PROJECT,
        chapter_index=2,cast=("江遥","宋易"))
    (OUTPUT/"TRUE_ORIGINAL_G_FIRST_TURN_A.md").write_text(
        original,encoding="utf8")
    (OUTPUT/"REJECTED_MODEL_AUTHORED_PATCH_SOURCE_PREVIEW_B.md").write_text(
        candidate,encoding="utf8")
    (OUTPUT/"EXACT_ORIGINAL_MODEL_REVISE_JSON.json").write_text(
        old_model,encoding="utf8")
    result={
        "format":"wf.real.v119.model-trace-failure.private-preview.v1",
        "source_run_id":40110957161,
        "original_author_lookback_run_id":40153456601,
        "original_rejected_v119_run_id":40155863914,
        "old_full_story_source_sha256":digest(original),
        "model_written_replacement_sha256":digest(edit["replacement"]),
        "preview_prose_sha256":digest(candidate),
        "genuine_model_private_preview_not_canon":True,
        "source_anchored_proposal":True,
        "V119_preview_status":preview["status"],
        "V96_unchanged_model_trace_rejected":v96,
        "V117_source_only_preflight_blocked":continuation["blocked"],
        "V117_source_only_preflight_needs_review":continuation["needs_review"],
        "V117_no_new_full_chapter_resume":True,
        "old_second_turn_reused":False,
        "first_turn_author_accepted":False,
        "extra_model_calls":0,"R2_writes":0,"Canon_writes":0,
        "literary_improvement_verified":False,
        "independent_human_blind_review_completed":False,
    }
    (OUTPUT/"STATUS.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True),
        encoding="utf8")
    print(json.dumps({
        "status":"AUTHENTIC_V119_PROPOSED_FICTION_SOURCE_LOCKED_V96_REJECTED",
        "V96_error":v96,
        "V119_preview":preview["status"],
        "V117_preflight_blocked":continuation["blocked"],
        "model_retries":0,
        "true_new_calls":0,
        "new_full_signed_chapter":False,
    },ensure_ascii=False),flush=True)
    return result

if __name__=="__main__":
    main()
