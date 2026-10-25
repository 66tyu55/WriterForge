"""0.V replay of actual DeepSeek B writing: ZERO model requests and no book read.

Authenticate the first genuine 0.T paired provider wires with their frozen
hashes, then run NEW V122/V116/V114/V117/V119 on those same unchanged bytes.
This is an engineering truth check, not another A/B literary model experiment.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import json

from experiments.wf_0t_real_B_reader_repair_downstream_20261025 import (
    PRIOR,PRIOR_B_FIRST,PRIOR_B_SECOND,PRIOR_WIRES,PRIOR_REFERENCE_SHA,PRIOR_RUN,
)
from experiments.wf_fanren_staged_source_ab_0t import PROJECT,BEATS,CAST
from writerforge.v96_causal_turns import check_turn
from writerforge.v114_external_story_state import external_temporal_step,require_external_runtime
from writerforge.v117_continuity_trace import preflight_continuation,make_resume,read_resume
from writerforge.v116_state_delta import preflight_next_prose
from writerforge.v119_revision_transaction import prepare_source_repair_contract
from writerforge.writing_assist import _physical_relation_source_hold

OUT=Path("wf_0v_real_B_physical_source_replay_20261025")


def sha(raw):
    return hashlib.sha256(raw.encode("utf8") if isinstance(raw,str) else raw).hexdigest()


def valid(condition,error):
    if not condition:
        raise RuntimeError(error)


def original_model_b():
    manifest=json.loads((PRIOR/"STATUS.json").read_text("utf8"))
    valid(manifest.get("format")=="wf.0t.fanren-private-readonly-staged-ab.v1"
          and manifest.get("complete_anonymous_pair") is True
          and manifest.get("same_model_actual_provider_calls")==6
          and manifest.get("reference",{}).get("reference_window_sha256")==
                list(PRIOR_REFERENCE_SHA)
          and manifest.get("reference",{}).get("book_source_sha256")==
                "2fc1698410418bf136448807335c6359bf515b75e6f9c1e1d1f443a1c928e6cc",
          "WF0V_OLD_REAL_SOURCE_MANIFEST_NOT_VERIFIED")
    signals={x["label"]:x for x in
             manifest["provider_calls_with_private_wire_hash"]}
    raws=[]; source_hashes=[]
    for stage,(label,expected) in enumerate(zip(PRIOR_WIRES,
                                                (PRIOR_B_FIRST,PRIOR_B_SECOND)),1):
        p=PRIOR/"B"/f"stage-{stage:02d}-real-author-prose.md"
        prose=p.read_text("utf8")
        valid(sha(prose)==expected,"WF0V_REAL_AUTHOR_SOURCE_SHA_DRIFT")
        wire=(PRIOR/"B"/"provider-originals"/(label+".json")).read_bytes()
        valid(sha(wire)==PRIOR_WIRES[label] and
              signals[label]["provider_wire_sha256"]==sha(wire),
              "WF0V_REAL_PROVIDER_WIRE_SHA_DRIFT")
        response=json.loads(wire)
        valid(response.get("model")=="deepseek-flash" and
              response["choices"][0]["finish_reason"]=="stop",
              "WF0V_AUTHENTIC_PROVIDER_FINISH_INVALID")
        author=json.loads(response["choices"][0]["message"]["content"])
        valid(type(author) is dict and set(author)=={"prose","trace"}
              and author["prose"].strip()==prose,
              "WF0V_TRUE_PROVIDER_PROSE_DISAGREES")
        raw=json.dumps(author,ensure_ascii=False,separators=(",",":"))
        valid(signals[label]["decoded_model_reply_sha256"]==sha(raw),
              "WF0V_DECODED_PROVIDER_SHA_CHANGED")
        raws.append(raw);source_hashes.append(sha(prose))
    valid(source_hashes==[PRIOR_B_FIRST,PRIOR_B_SECOND],
          "WF0V_FALSE_MODEL_PROSE_SOURCE")
    return raws,manifest


def run():
    require_external_runtime()
    raws,manifest=original_model_b()
    first=check_turn(raws[0],BEATS[0],mode="causal_guard",
                     accepted=(),max_prose_chars=1024)
    second=check_turn(raws[1],BEATS[1],mode="causal_guard",
                      accepted=(first,),max_prose_chars=1024)
    checkpoint=external_temporal_step(first["prose"],cast=CAST)
    reviewed=preflight_next_prose(
        second["prose"],previous_candidate_state=checkpoint[
            "reducer_result"]["candidate_state"],cast=CAST,
        previous_relation_receipt=checkpoint.get(
            "v122_physical_relation_source_receipt"))
    valid(not reviewed["blocked"] and reviewed["needs_review"] and
          "NEEDS_SOURCE_RELATION_REVIEW" in reviewed["review_findings"],
          "WF0V_REAL_B_RELATION_FAILED_TO_TRIGGER_REVIEW")
    before=preflight_continuation(
        second["prose"],checkpoint,
        project_id=PROJECT,chapter_index=1,cast=CAST)
    valid(before["needs_review"] and
          before["physical_relation_must_not_be_fact_or_downstream_parent"],
          "WF0V_REAL_B_V117_DID_NOT_FLAG_UNKNOWN_PHYSICAL_RELATION")
    hold=_physical_relation_source_hold(prose=second["prose"],preflight=reviewed)
    valid(hold is not None and
          hold["status"]=="HELD_NEEDS_SOURCE_RELATION_REVIEW",
          "WF0V_REAL_B_NOT_HELD_AS_SOURCE_CANDIDATE")
    pairs=hold["current_conflicting_source_quote_pairs"]
    valid(len(pairs)==1 and
          pairs[0]["first_source_quote"]=="绳结还系在木桩上" and
          pairs[0]["second_source_quote"]=="只是绳子被人从桩头解下来",
          "WF0V_NOT_THE_ACTUAL_ORIGINAL_B_CONFUSION")
    # Original source-first fix contract is computed, but NOT fed to a model:
    # no forced rewrite and no invented reason for the author's old MOVE_ON.
    guide=prepare_source_repair_contract(
        source=second["prose"],source_sha256=PRIOR_B_SECOND,
        beat=BEATS[1],accepted=(first,),
        original_trace=json.loads(raws[1])["trace"],
        previous_candidate_state=checkpoint[
            "reducer_result"]["candidate_state"],cast=CAST)
    valid(guide["physical_relation_source_evidence"]["source_quote_pairs"]
          ==pairs and guide["actual_previous_effect_quote"]==
             first["effect_quote"],
          "WF0V_ORIGINAL_WF_REPAIR_GUIDE_NOT_SOURCE_ALIGNED")
    latest=external_temporal_step(second["prose"],cast=CAST,prior=checkpoint)
    signed=make_resume(project_id=PROJECT,scene_id="staged-0t-b",
                       chapter_index=1,checkpoint=latest)
    read_resume(signed,project_id=PROJECT,scene_id="staged-0t-b")
    valid(latest["v122_physical_relation_source_receipt"][
              "current_source_needs_review"] and
          latest["v122_relation_review_not_a_reducer_cell"] is True,
          "WF0V_V114_PHYSICAL_UNCERTAINTY_NOT_SIGNED")
    return {
        "format":"wf.0v.original-deepseek-B-source-replay.v1",
        "original_provider_run_id":PRIOR_RUN,
        "real_model_original_prose_sha256":[PRIOR_B_FIRST,PRIOR_B_SECOND],
        "real_model_original_prose_rewritten":False,
        "old_historical_result_unchanged":manifest["arms"]["B"]["status"],
        "new_zero_model_v116_review":reviewed["review_findings"],
        "new_zero_model_v117_needs_review":before["needs_review"],
        "new_relation_review_status":hold["status"],
        "review_pair_sources":[{
            "first_source_quote":p["first_source_quote"],
            "first_source_quote_sha256":p["first_source_quote_sha256"],
            "second_source_quote":p["second_source_quote"],
            "second_source_quote_sha256":p["second_source_quote_sha256"],
            "item_identity_evidence":p["item_identity_evidence"],
            "contact_identity_evidence":p["contact_identity_evidence"]
        } for p in pairs],
        "source_first_repair_contract_sha256":guide["receipt_sha256"],
        "signed_v114_unaccepted_resume_sha256":signed["receipt_sha256"],
        "physical_state_promoted_to_canon":False,
        "same_author_was_not_reasked":True,
        "new_provider_requests":0,"extra_literary_critics":0,
        "new_accepted_revision":0,"new_written_downstream":0,
        "R2_reads":0,"R2_writes":0,
        "Canon_writes":0,"Railway_deployments":0,
        "production_main_changed":False,
        "literary_quality_improvement_proven":False
    }


def main():
    OUT.mkdir(parents=True,exist_ok=False)
    try:
        data=run()
        data["status"]="REAL_ORIGINAL_B_REPLAYED_AND_SOURCE_RELATION_HELD"
    except Exception as exc:
        code=str(exc)
        data={"status":"FAILED_NO_MODEL_RETRY",
              "code":(code if code.startswith("WF0V_")
                      else type(exc).__name__),
              "new_provider_requests":0,"R2_writes":0,
              "Canon_writes":0,"literary_quality_improvement_proven":False}
    (OUT/"STATUS.json").write_text(json.dumps(
        data,ensure_ascii=False,sort_keys=True,indent=2),encoding="utf8")
    print("WF0V_ORIGINAL_B_REPLAY "+json.dumps({
        "status":data["status"],"new_provider_requests":0,
        "real_original_prose_changed":False,
        "literary_improvement_verified":False},
        ensure_ascii=False),flush=True)


if __name__=="__main__":
    main()
