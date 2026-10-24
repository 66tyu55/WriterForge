"""Re-evaluate EXACT old REAL AI V119 reply with zero new paid model calls.

Original source remains anchored to genuine provider run #40094106486.
Original reader + author + rejected V119 reply remains anchored to genuine
provider run #40108836214. The sole format-only compatibility for
"type":"json_object" and unique literal offset recovery are the ONLY
changes from first rejection. V96/114/NarrativeCore still refuse malformed
temporal or causal trace. Preview never commits or auto-selects fiction.
"""
from __future__ import annotations

from pathlib import Path
from hashlib import sha256
import json
import sys

from experiments.wf_real_deepseek_blind_source_replay_20261024 import (
    verified_prior_source,REAL_PROSE_SHA,packet_for_review,
)
from experiments.wf_three_existing_writer_models_real_20261024 import (
    SEED,BEAT,CAST,
)
from writerforge.writing_assist import (
    _self_edit_one_turn, _decode_json,
)
from writerforge.v119_revision_transaction import preview_revision
from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v96_causal_turns import check_turn

ORIGINAL_READER_ROOT=Path("wf_prior_reader_first_20261024")
OUTPUT=Path("wf_real_reader_first_v119_replay_zero_model_20261024")

def h(content):
    if type(content) is str:
        content=content.encode("utf8")
    return sha256(content).hexdigest()

def save(path,doc):
    path.write_text(json.dumps(doc,ensure_ascii=False,
                               indent=2,sort_keys=True),encoding="utf8")

def verify_actual_revision_provenance(root=ORIGINAL_READER_ROOT):
    paths=(
        "STATUS.json",
        "03-AUTHOR_V119_REVISION-decoded.json",
        "03-AUTHOR_V119_REVISION-provider-wire.json",
        "original-AI-V119-change/round-01-model-proposal.json",
        "original-AI-V119-change/self-edit-receipt.json",
        "OLD_PROVIDER_ORIGINAL_UNTOUCHED.md",
    )
    if any(not (root/x).is_file() or (root/x).is_symlink()
           for x in paths):
        raise ValueError("WF_REAL_V119_PREVIOUS_ORIGINAL_MISSING")
    state=json.loads((root/"STATUS.json").read_text("utf8"))
    if (state.get("status")!="GENUINE_AI_READER_AND_AUTHOR_REVIEW_COMPLETED" or
        state.get("source_sha256")!=REAL_PROSE_SHA or
        state.get("same_AI_author_decision")!="LOOK_BACK_NOW" or
        state.get("new_actual_provider_calls")!=3 or
        state.get("written_candidate_changed") is not False or
        state.get("writer_V119_revision_receipt",{}).get(
            "rounds",[{}])[0].get("reason_code")!="WF_SELF_EDIT_SCHEMA_INVALID"):
        raise ValueError("WF_REAL_V119_HISTORIC_FAILURE_CHANGED")
    source=(root/"OLD_PROVIDER_ORIGINAL_UNTOUCHED.md").read_bytes()
    if h(source)!=REAL_PROSE_SHA:
        raise ValueError("WF_REAL_V119_ORIGINAL_SOURCE_TAMPERED")
    events=state.get("provider_original_wire_evidence",[])
    if type(events) is not list or len(events)!=3 or any(
        not x.get("provider_wire_preserved_before_decode")
        for x in events):
        raise ValueError("WF_REAL_V119_NO_AUTHENTIC_THIRD_REPLY")
    raw=(root/"03-AUTHOR_V119_REVISION-decoded.json").read_bytes()
    wire=(root/"03-AUTHOR_V119_REVISION-provider-wire.json").read_bytes()
    private=(root/"original-AI-V119-change/round-01-model-proposal.json"
             ).read_bytes()
    if (raw!=private or
        h(raw)!=events[2].get("decoded_reply_sha256") or
        h(wire)!=events[2].get("wire_sha256")):
        raise ValueError("WF_REAL_V119_WRITER_PROPOSAL_CHANGED")
    report=json.loads((root/"original-AI-V119-change/"
                       "self-edit-receipt.json").read_text("utf8"))
    if report.get("rounds",[{}])[0].get(
            "reason_code")!="WF_SELF_EDIT_SCHEMA_INVALID":
        raise ValueError("WF_REAL_V119_FIRST_RED_NOT_PRESERVED")
    return private.decode("utf8"),state

def main():
    proof=verified_prior_source()
    model_reply,state=verify_actual_revision_provenance()
    original=proof["source"]
    choice=json.loads(model_reply)
    if choice.get("type")!="json_object":
        raise RuntimeError("WF_REAL_V119_EXPECTED_EXACT_TYPE_WRAPPER")
    expected=choice.get("expected_original")
    if (not isinstance(expected,str) or original.count(expected)!=1 or
        choice.get("source_sha256")!=REAL_PROSE_SHA):
        raise RuntimeError("WF_REAL_V119_SOURCE_NOT_UNIQUE")
    OUTPUT.mkdir(parents=True,exist_ok=False)
    (OUTPUT/"EXACT_OLD_AUTHOR_REVISION.json").write_text(
        model_reply,encoding="utf8")
    (OUTPUT/"ORIGINAL_UNMODIFIED.md").write_text(original,encoding="utf8")
    prior=external_temporal_step(SEED,cast=CAST)
    old=prior["reducer_result"]["candidate_state"]
    proposals=[]
    def read_saved_reply(packet,*,model,api_base,max_tokens):
        if model is not None or api_base is not None or max_tokens!=1800:
            raise RuntimeError("WF_REAL_V119_REPLAY_REQUEST_CHANGED")
        proposals.append(packet.prompt_sha256)
        return model_reply
    actual,receipt=_self_edit_one_turn(
        raw=proof["original_model_raw"],beat=BEAT,
        accepted=(),project_id="wf-original-reader-first",
        scene_id="river-original",turn_packet=packet_for_review(),
        ask_model=read_saved_reply,round_limit=1,call_allowance=1,
        directory=OUTPUT/"old-model-replayed-with-current-source-guards",
        cast=CAST,previous_candidate_state=old,
        current_external_story_checkpoint=prior,
        story_chapter_index=2)
    if len(proposals)!=1:
        raise RuntimeError("WF_REAL_V119_REPLAY_NOT_EXACTLY_ONCE")
    if _decode_json(actual)["prose"].strip()!=original:
        raise RuntimeError("WF_REAL_V119_REPLAY_FALSELY_ACCEPTED")
    finding=receipt["rounds"][0]
    # Inspect the original AI replacement as a PRIVATE model proposal,
    # not as an accepted rewrite: every prefix/suffix is mechanically
    # unchanged. Never override a real V96 source/parent trace failure.
    start=original.index(expected)
    preview=preview_revision(
        project_id="wf-original-reader-first",scene_id="river-original",
        source=original,source_sha256=REAL_PROSE_SHA,
        start=start,end=start+len(expected),
        expected_original=expected,replacement=choice["replacement"],
        previous_candidate_state=old,cast=CAST)
    preview_valid=(preview["status"]=="PROVISIONAL_REVIEW" and
                   isinstance(preview.get("candidate_prose"),str))
    if preview_valid:
        # Explicitly private, deliberately unaccepted, and NOT the output
        # of the original Wf validated self-edit path.
        (OUTPUT/"REJECTED_PRIVATE_SOURCE_LOCKED_PATCH_PREVIEW.md").write_text(
            preview["candidate_prose"],encoding="utf8")
    state={
        "format":"wf.real.reader-first-v119-original-reply-offline-replay.v1",
        "source_sha256":REAL_PROSE_SHA,
        "old_provider_originals_unchanged":True,
        "real_original_v119_run":40108836214,
        "real_original_v119_source_sha256":h(model_reply),
        "model_calls_in_replay":0,
        "old_billed_provider_calls_not_recharged":3,
        "original_v119_failure":"WF_SELF_EDIT_SCHEMA_INVALID",
        "after_strict_mechanical_wrapper_and_quote_offset":
            finding.get("reason_code"),
        "format_wrapper_only_removed":finding.get(
            "format_wrapper_only_removed"),
        "source_offset_recovered_exactly":finding.get(
            "source_offset_recovered_exactly"),
        "source_unique_anchor_found":True,
        "private_model_proposed_source_preview_allowed":preview_valid,
        "private_preview_status":preview["status"],
        "private_preview_not_an_accepted_candidate":True,
        "V96_semantic_and_trace_guard_kept":True,
        "revised_accepted_source":False,
        "user_canon_writes":0,"R2_writes":0,
        "literary_quality_verified":False,
    }
    save(OUTPUT/"STATUS.json",state)
    print(json.dumps({
        "stage":"REAL_ORIGINAL_V119_REPLAYED_ZERO_MODEL",
        "calls":0,
        "source_unique":True,
        "format_wrapper_removed":state["format_wrapper_only_removed"],
        "offsets_recovered":state["source_offset_recovered_exactly"],
        "remaining_reason":state["after_strict_mechanical_wrapper_and_quote_offset"],
        "private_model_preview":preview_valid,
        "real_source_changed":False,
    },ensure_ascii=False),flush=True)
    return state

if __name__=="__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({
            "stage":"REAL_V119_NO_MODEL_REPLAY_BLOCKED",
            "error_type":type(error).__name__,
            "model_calls":0,
        },ensure_ascii=False),flush=True)
        sys.exit(2)
