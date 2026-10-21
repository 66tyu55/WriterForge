"""V113 independent read-only cold recovery after original writing finished.

The PAID V113 job completed four provider requests, sealed immutable private
CAS, then its blind export failed due to an import typo. Never rerun it.
This script does NOT possess DEEPSEEK_API_KEY and never calls any model.

It only reads exact V113 CAS addresses from original run logs:
 - original precommit and manifest
 - original anonymous index
 - failed bare model original decoded response

The immutable original FAILED status never changes. The two successfully
produced anonymous full original manuscripts are exported without owner keys.
"""
from __future__ import annotations
import json,os,re
from pathlib import Path
from experiments.v113_github_r2_cas import GitHubS3CAS
from experiments.v113_equal_length_three_arm import (
    TASK,EXAM,ARMS,freeze,skill_original,prose_observation,digest,
    length_fairness_by_arm,
)
from experiments.v113_export_blind_stories import export as export_anonymous

PRECOMMIT="2cbfee89fe38b8d962e9aec3f9b8b7b185c45723eab7c16a02ca51f78f38f2cd"
MANIFEST="4dd25ee40a90eec7ff9e67b184720903a145df9f54918f4eb68ea52f3a3af67f"
BLIND="0e41de611b032036782c21db8b200a0d60bf90806eaabebde8094224ff041e2f"
FAILED_BARE_DECODED="301b3720ea3e58a5f8bf891ef8c59658e9f3bdf9787036658c626c016da40241"

def need(ok,code):
    if not ok:raise ValueError(code)

def load(cas,pointer):
    need(type(pointer) is str and re.fullmatch(r"[0-9a-f]{64}",pointer),
         "WF113C_UNKNOWN_OR_INVALID_POINTER")
    return json.loads(cas._get_content(pointer).decode("utf8","strict"))

class StrictReadOnlyCAS(GitHubS3CAS):
    def _put_content(self,*args,**kwargs):
        raise RuntimeError("WF113C_R2_WRITE_FORBIDDEN_IN_COLD_READER")


def recover():
    need(not os.environ.get("DEEPSEEK_API_KEY") and
         not os.environ.get("DEEPSEEK") and
         all(os.environ.get(k) for k in (
             "WRITERFORGE_R2_ACCOUNT_ID",
             "WRITERFORGE_R2_BUCKET",
             "WRITERFORGE_R2_ACCESS_KEY_ID",
             "WRITERFORGE_R2_SECRET_ACCESS_KEY")),
         "WF113C_R2_READER_ONLY_CREDENTIAL_BOUNDARY")
    cas=StrictReadOnlyCAS()
    original_pre=load(cas,PRECOMMIT)
    need(original_pre.get("experiment")==EXAM
         and original_pre.get("max_provider_calls")==4
         and original_pre.get("exact_common_user_question")==TASK
         and original_pre.get("peer_skill_isolated_from_WF_writing") is True,
         "WF113C_HISTORICAL_PRECOMMIT_NOT_THIS_EXAM")
    need(original_pre==freeze(skill_original()[0]),
         "WF113C_OLD_SOURCE_FROZEN_CONTRACT_CHANGED")
    manifest=load(cas,MANIFEST)
    need(manifest.get("format")==
         "wf.eval.v113.three-arm-original-model-experiment"
         and manifest.get("precommit_cas_sha256")==PRECOMMIT
         and manifest.get("model_request_count")==4
         and manifest.get("independent_blind_review_index_cas_sha256")==BLIND
         and manifest.get("all_three_prose_length_comparable") is False
         and manifest.get("no_auto_retry_or_llm_rewrite") is True
         and manifest.get("qualified_literary_winner")=="UNDETERMINED",
         "WF113C_ORIGINAL_MANIFEST_OR_METHOD_STATES_CHANGED")
    summaries=manifest["arms"]
    need(type(summaries) is list and
         [s["arm"] for s in summaries]==list(ARMS) and
         [s["status"] for s in summaries]==["WRITTEN","WRITTEN","FAILED"]
         and [s.get("real_codepoints") for s in summaries[:2]]==[951,1010],
         "WF113C_ORIGINAL_ARM_RECEIPTS_NOT_EXPECTED")
    refs=manifest["raw_provider_request_receipts"]
    need(len(refs)==4 and refs[3]["stage"]=="BARE_PROSE" and
         refs[3]["decoded_cas_sha256"]==FAILED_BARE_DECODED,
         "WF113C_FAILED_RAW_BARE_RESPONSE_NOT_LINKED")
    rejected=load(cas,FAILED_BARE_DECODED)
    need(rejected["format"]=="wf.eval.v113.one-unmodified-model-answer"
         and rejected["precommit_sha256"]==PRECOMMIT
         and rejected["not_manually_corrected"] is True,
         "WF113C_BARE_IS_NOT_ORIGINAL_DECODED_MODEL_RESPONSE")
    full_reply=rejected["original_answer"]
    inspected=prose_observation(full_reply)
    # Original failure status is durable regardless of this diagnostic.
    diagnose={
        "status":"WF113C_ORIGINAL_BARE_MODEL_REPLY_DIAGNOSED_NOT_REPAIRED",
        "original_full_reply_cas_sha256":FAILED_BARE_DECODED,
        "original_arm_status":"FAILED",
        "decoded_reply_type":type(full_reply).__name__,
        "decoded_object_keys":sorted(full_reply) if type(full_reply) is dict
            else None,
        "decoded_value_types":{k:type(v).__name__ for k,v in full_reply.items()}
            if type(full_reply) is dict else None,
        "literal_prose_if_schema_valid":inspected["actual_codepoints"],
        "reason_if_schema_invalid":inspected["status"],
        "original_bare_status_remains_failed":True,
        "new_model_requests":0,
        "original_answer_not_rewritten":True,
    }
    print(json.dumps(diagnose,ensure_ascii=False,sort_keys=True),flush=True)

    index=load(cas,BLIND)
    need(index.get("format")=="wf.eval.v113.blind-original-fantasy-review-index"
         and index.get("judging_stage")=="NOT_PERFORMED"
         and index.get("blind_method_identity_hidden") is True
         and len(index.get("packets",[]))==2,
         "WF113C_TWO_ORIGINAL_ANONYMOUS_PACKETS_NOT_SIGNED")
    # Verify all blinded originals are exact CAS before exporting.
    blind_lengths=[]
    for i,record in enumerate(index["packets"],1):
        need(record["label"]==f"匿名作品{i:02d}",
             "WF113C_BLIND_ORDER_MODIFIED")
        wrapped=load(cas,record["full_prose_cas_sha256"])
        need(wrapped["label"]==record["label"]
             and wrapped["shared_task"]==TASK
             and wrapped["literary_quality_judged"]=="NOT_PERFORMED"
             and type(wrapped["prose"]) is str,
             "WF113C_BLIND_BODY_OR_SOURCE_INVALID")
        blind_lengths.append(len(wrapped["prose"]))
    need(sorted(blind_lengths)==[951,1010],
         "WF113C_BLIND_LENGTHS_NOT_ORIGINAL")
    pair_gap=(max(blind_lengths)-min(blind_lengths))/max(blind_lengths)
    need(pair_gap<=0.1,"WF113C_PAIRWISE_LENGTH_COMPARISON_NOT_ELIGIBLE")
    handoff={
        "format":"wf.eval.v113.github-actions-export-pointers",
        "manifest_cas_sha256":MANIFEST,
        "blind_index_cas_sha256":BLIND,
        "available_anonymous_packets":2,
        "author_accepted":False,
    }
    path=Path(os.environ["WF113_LOCAL_RESULT_FILE"])
    path.write_text(json.dumps(handoff,ensure_ascii=False,
                               sort_keys=True),encoding="utf8")
    artifact=Path(os.environ["WF113_BLIND_ARTIFACT_DIR"])
    result=export_anonymous(cas=cas)
    need(result==0 and (artifact/"anonymous_01.txt").is_file() and
         (artifact/"anonymous_02.txt").is_file(),
         "WF113C_EXPORT_DID_NOT_RECOVER_TWO_FULL_ORIGINAL_STORIES")
    (artifact/"nonconforming_third_arm.json").write_text(
        json.dumps(diagnose,ensure_ascii=False,indent=2),
        encoding="utf8")
    (artifact/"pairwise_length_context.json").write_text(
        json.dumps({
            "format":"wf.eval.v113.author-review-pairwise-only",
            "original_complete_three_arm_comparison_valid":False,
            "two_existing_originals_actual_lengths":sorted(blind_lengths),
            "pairwise_relative_length_gap":round(pair_gap,6),
            "pairwise_length_criteria_satisfied":True,
            "original_third_arm_was_schema_rejected":True,
            "R2_prose_still_unmodified":True,
            "literary_human_review":"NOT_PERFORMED",
            "no_model_calls_for_recovery":True,
        },ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps({
        "status":"WF113C_TWO_ANONYMOUS_ORIGINAL_PROSE_ARTIFACTS_RECOVERED",
        "original_precommit":PRECOMMIT,"original_manifest":MANIFEST,
        "anonymous_full_story_count":2,
        "original_story_lengths":sorted(blind_lengths),
        "pairwise_relative_length_gap":round(pair_gap,6),
        "three_way_length_eligible":False,
        "bare_original_remains_FAILED":True,
        "all_previous_model_calls_unmodified":True,
        "new_provider_calls":0,
        "R2_writes":0,
        "literary_grade":"NOT_PERFORMED",
    },ensure_ascii=False,sort_keys=True),flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(recover())
