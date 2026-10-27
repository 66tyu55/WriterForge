"""WF 0.BJ: source-verified adequacy gate BEFORE spending human review time.

This gate is NOT an AI literary grader and does NOT rejudge whether an author
chose the correct plot. It detects mechanical defects from REAL frozen local
model outputs: literal echo, identical pair, and failure to meet the 3B
runner's explicit 120-220 Chinese-character drafting instruction. It
documents prompt-only procedure variants, NOT actual WF authoring-core A/B.

A user's ONE unsigned pilot ballot is diagnostic feedback, not two
independently signed votes or a winning literary grade. If this experiment is
unusable, STOP asking a second reader, retain all source bytes and leave
the v1/v2 capsule SHADOW. Nothing is re-generated or overwritten.
"""
from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import Path
import json

from experiments.wf_0bi_genuine_blind_review_packet import (
    inspect_blind_review_sources, validate_packet_and_ballot,
)
from experiments.wf_0be_v1_v2_preflight_only import canonical

ROOT=Path(__file__).resolve().parents[1]
V1=ROOT/".agents/skills/observe-before-next-choice/capsule.json"
V2=ROOT/"experiments/wf_0bd_portable_habit_snapshots/0d43a023bc278ac12e3165e319d2acb73dcf40c0d9af453e623c786f3b476a10/capsule.json"
V1_SHA="42cad98118dea662cea472f708ef1de22f4bb139da3210b1f5c3c1f9ac12664d"
V2_SHA="0d43a023bc278ac12e3165e319d2acb73dcf40c0d9af453e623c786f3b476a10"
OUTPUT=Path("wf0bj_source_only_trial_stop")
UNFIT_REVIEW_STATUS="DORMANT_EXPERIMENT_UNFIT_FOR_LITERARY_COMPARISON"
MIN_3B_CHARS=120


def sha(data:bytes)->str:
    return sha256(data).hexdigest()


def assess_saved_trial_adequacy()->dict:
    sources=inspect_blind_review_sources()
    if len(sources)!=5:
        raise ValueError("WF0BJ_EXPECTED_ORIGINAL_FIVE_REAL_PAIRS")
    expected={
        "quiet-household-pause","asynchronous-tool-return",
        "purposeful-second-attempt","bounded-eyewitness",
        "custody-without-fulfillment"
    }
    if {x["case_id"] for x in sources}!=expected:
        raise ValueError("WF0BJ_ORIGINAL_CASE_SET_DRIFT")
    v1raw=V1.read_bytes()
    v2raw=V2.read_bytes()
    if sha(v1raw)!=V1_SHA or sha(v2raw)!=V2_SHA:
        raise ValueError("WF0BJ_PARENT_OR_CANDIDATE_CAPSULE_SHA_DRIFT")
    root=json.loads(v1raw)
    candidate=json.loads(v2raw)
    if root["lifecycle"]!="SHADOW" or candidate["lifecycle"]!="SHADOW":
        raise ValueError("WF0BJ_SOURCE_CAPSULE_ALREADY_PROMOTED")
    paired_identical=[]
    both_echo=[]
    quiet_ratio=None
    below=[]
    per_case=[]
    counts=Counter()
    for item in sources:
        cid=item["case_id"]
        group=item["host_group"]
        if group not in ("local_0bg","local_0bh"):
            raise ValueError("WF0BJ_WRONG_OR_UNKNOWN_LOCAL_MODEL_COHORT")
        prior="".join(item["prior_prose"])
        a=item["outputs"]["v1"]["text"]
        b=item["outputs"]["v2"]["text"]
        counts[group]+=2
        exact_pair=a==b
        source_echo_a=a==prior
        source_echo_b=b==prior
        if exact_pair:
            paired_identical.append(cid)
        if source_echo_a and source_echo_b:
            both_echo.append(cid)
        ratio=SequenceMatcher(None,a,b,autojunk=False).ratio()
        if cid=="quiet-household-pause":
            quiet_ratio=round(ratio,6)
        arm_lengths={}
        for arm,prose in (("v1",a),("v2",b)):
            size=len(prose)
            arm_lengths[arm]=size
            # This is a CHECK OF THE PUBLISHED PROMPT CONTRACT for the
            # Qwen2.5-3B cohort ONLY; the 0.BG Qwen3 prompt did not
            # specify 120-220 characters, so its outputs are not judged
            # against another cohort's different instruction.
            if group=="local_0bh" and size<MIN_3B_CHARS:
                below.append({"case_id":cid,"arm":arm,"characters":size})
        per_case.append({
            "case_id":cid,
            "model_cohort":group,
            "source_sha256":item["source_sha256"],
            "task_sha256":item["task_sha256"],
            "v1_original_response_sha256":
                item["outputs"]["v1"]["original_response_sha256"],
            "v2_original_response_sha256":
                item["outputs"]["v2"]["original_response_sha256"],
            "v1_characters":arm_lengths["v1"],
            "v2_characters":arm_lengths["v2"],
            "literal_outputs_equal":exact_pair,
            "v1_exact_original_source_echo":source_echo_a,
            "v2_exact_original_source_echo":source_echo_b,
            "sequence_similarity_diagnostic_only":round(ratio,6),
            "prescribed_length_for_this_cohort":
                "120-220 characters" if group=="local_0bh" else None,
        })
    if len(counts)!=2 or counts["local_0bg"]!=4 or counts["local_0bh"]!=6:
        raise ValueError("WF0BJ_REAL_LOCAL_SOURCE_CORPUS_MISMATCH")
    failed_cases={item["case_id"] for item in below}
    # Abort this pilot because it lacks enough task-compliant information
    # to justify spending a second person's time. These objective defects
    # alone DO NOT prove either version improves or worsens literature.
    stop=bool(paired_identical or both_echo or len(failed_cases)>=2)
    return {
        "format":"wf.0bj.original-local-trial-adequacy.v1",
        "status":UNFIT_REVIEW_STATUS if stop else "READY_FOR_PILOT_REVIEW_ONLY",
        "real_model_output_pairs":len(sources),
        "real_output_counts_by_cohort":dict(sorted(counts.items())),
        "source_case_ids":sorted(expected),
        "identical_completion_pairs":sorted(paired_identical),
        "both_arms_literal_source_echo_pairs":sorted(both_echo),
        "three_b_declared_min_chars":MIN_3B_CHARS,
        "three_b_underlength_arms":len(below),
        "three_b_underlength_pairs":len(failed_cases),
        "three_b_underlength_details":sorted(
            below,key=lambda x:(x["case_id"],x["arm"])),
        "high_overlap_0bg_quiet_pair":
            quiet_ratio is not None and quiet_ratio>=0.85,
        "quiet_pair_sequence_similarity":quiet_ratio,
        "diagnostic_string_similarity_is_not_literary_grade":True,
        "benchmark_type":"STATIC_PROMPT_PROCEDURE_V1_V2_ONLY",
        "actual_core_wf_authoring_executions":0,
        "bare_model_baseline_was_collected":False,
        "can_claim_wf_vs_bare_model":False,
        "mixed_model_cohorts":True,
        "quality_gate_is_post_hoc_trial_validity_not_causal_inference":True,
        "request_second_blind_reader":not stop,
        "new_model_calls":0,
        "new_paid_provider_calls":0,
        "local_model_calls_replayed":0,
        "original_v1_state":"SHADOW",
        "proposed_v2_state":"SHADOW",
        "candidate_stage":"SHADOW",
        "production_candidate_activation":False,
        "candidate_auto_promoted":False,
        "literary_quality_improved":False,
        "literary_quality_falsified":False,
        "independent_signed_reader_consensus":False,
        "no_automatic_0ay_glm_retry":True,
        "no_automatic_v3_generation":True,
        "source_checked_case_details":per_case,
    }


def assess_single_unsigned_review(packet:dict,ballot:dict, *,
                                  evidence_label:str)->dict:
    """Record that ONE ballot was received; do not call it a valid blind A/B outcome."""
    if evidence_label not in ("SYNTHETIC_TEST_ONLY",
                             "HUMAN_SELF_REPORTED_UNSIGNED"):
        raise ValueError("WF0BJ_FEEDBACK_ORIGIN_UNTRUSTED")
    result=validate_packet_and_ballot(packet,ballot)
    counts=Counter(v["choice"] for v in ballot["votes"])
    if result["valid_votes"]!=5:
        raise ValueError("WF0BJ_BALLOT_NOT_COMPLETE")
    return {
        "format":"wf.0bj.single-unverified-reader-feedback.v1",
        "status":"SINGLE_UNSIGNED_REVIEW_DIAGNOSTIC",
        "evidence_label":evidence_label,
        "packet_id":packet["packet_id"],
        "packet_sha256":sha(canonical(packet)),
        "ballot_content_sha256":sha(canonical(ballot)),
        "received_votes":len(ballot["votes"]),
        "ballot_choices":{
            key:counts.get(key,0) for key in ("A","B","TIE","BOTH_BAD")
        },
        "authenticated_independent_readers":0,
        "independent_reader_two_completed":False,
        "version_identity_in_ballot":False,
        "win_rate_computable":False,
        "literary_benefit_proven":False,
        "global_v2_disproven":False,
        "auto_promote":False,
        "candidate_stage":"SHADOW",
    }


def main(*,output:Path=OUTPUT)->dict:
    if output.exists():
        raise FileExistsError("WF0BJ_STOP_REPORT_ALREADY_EXISTS_NO_REPEAT")
    result=assess_saved_trial_adequacy()
    output.mkdir(parents=True,exist_ok=False)
    (output/"SOURCE_ONLY_NO_HUMAN_GRADE.json").write_bytes(canonical(result))
    print("WF0BJ_FIRST_HUMAN_REVIEW_NOT_WORTH_SECOND "+json.dumps({
        "status":result["status"],
        "pairs":result["real_model_output_pairs"],
        "identical_pairs":result["identical_completion_pairs"],
        "underlength_3b_arms":result["three_b_underlength_arms"],
        "bare_model_baseline_present":False,
        "new_model_calls":0,
        "literary_quality_proven":False,
    },ensure_ascii=False,sort_keys=True),flush=True)
    return result


if __name__=="__main__":
    main()
