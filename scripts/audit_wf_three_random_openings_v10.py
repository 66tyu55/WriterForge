"""Read-only result audit for three randomly-selected ORIGINAL story tasks.

All three tests use exactly the same pinned original learning source window,
same writer and same independent-source-blind critic. Only original task varies.
No manuscript, original prose, model review quotes or credentials are emitted.
"""
from __future__ import annotations

from hashlib import sha256
import json,re

from writerforge.random_original_openings import (
    selected_ids,task_for_slot,sample_manifest,sample_sha256,
)
from writerforge.reverse_score_scale import baseline_30_display
from writerforge.reverse_ab_candidates import derive_unverified_candidates
from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.reverse_discovery_models import ROLE_MODELS
from scripts.run_wf_three_random_openings_v10 import (
    SOURCE_SHA,SOURCE_CHAPTER,SOURCE_FIRST_SHA,SOURCE_NEXT_SHA,
    BUDGET_PROFILE,COMMON_AB_CHARS,TRIAL,PREFIX,
)

DIMS=("perception","causality","information","continuity","language")

def _root(slot:int)->str:
    story_id=selected_ids()[slot]
    task_sha=sha256(task_for_slot(slot).encode("utf-8")).hexdigest()
    config={"source":SOURCE_SHA,"task":"three-random-original-first-chapters",
            "chapter":SOURCE_CHAPTER,"slot":slot,"sample_sha256":sample_sha256(),
            "story_id":story_id,"story_task_sha256":task_sha,
            "roles":ROLE_MODELS,"trial":TRIAL,
            "wire_profile":"glm-5.3:reasoning_effort-low:5500-7500-7000:ab-common-1070-symmetric",
            "creative_task_sha256":task_sha}
    return f"{PREFIX}/story-{slot}-{story_id}/{sha256(_canonical(config)).hexdigest()}"

def effective_task(slot:int)->str:
    """Identical neutral length constraint, matching the trial implementation."""
    return (task_for_slot(slot)+
        "\n本次A/B两组共同严格篇幅要求：含标点字符数目标"
        +str(COMMON_AB_CHARS)
        +"，允许偏差不超过8%；只完成一篇完整场景，"
        "不要增加附录、番外或第二幕。禁止凑字数重复叙述。"
    )

def collect(store:R2StudyVault, *, persist:bool=True)->dict:
    if store.config.bucket!="writerforge-private-library":
        raise ValueError("WRONG_PRIVATE_R2")
    rows=[]
    for slot,story_id in enumerate(selected_ids()):
        root=_root(slot)
        if store._head(root+"/completed.json") is None:
            rows.append({"slot":slot,"story_id":story_id,
                         "status":"UNSCORED_NO_COMPLETED_REPORT",
                         "model_rating":None,"literary_passed":False})
            continue
        pointer=json.loads(store._get_small(root+"/completed.json",4096))
        h=pointer.get("sha256")
        if (not isinstance(h,str) or re.fullmatch("[0-9a-f]{64}",h) is None or
            pointer.get("source_sha256")!=SOURCE_SHA):
            raise ValueError("INVALID_COMPLETED_POINTER")
        raw=store._get_small(f"{root}/snapshots/{h}.json",32000)
        if sha256(raw).hexdigest()!=h:
            raise ValueError("RAW_R2_DIGEST_FAILED")
        doc=json.loads(raw)
        cursor=doc.get("source_cursor_diagnostic",{})
        scenario=doc.get("story_scenario",{})
        if (doc.get("edition_sha256")!=SOURCE_SHA or
            doc.get("source_unit_sha256")!=SOURCE_FIRST_SHA or
            doc.get("next_unit_sha256")!=SOURCE_NEXT_SHA or
            doc.get("random_original_story_sample")!=sample_manifest() or
            doc.get("scenario_id")!=story_id or
            doc.get("new_original_task_sha256")!=
                sha256(task_for_slot(slot).encode("utf-8")).hexdigest() or
            doc.get("writing_task_sha256")!=
                sha256(effective_task(slot).encode("utf-8")).hexdigest() or
            scenario.get("random_original_scenarios_sha256")!=sample_sha256() or
            scenario.get("same_reference_window_for_all_slots") is not True or
            cursor.get("chapter")!=SOURCE_CHAPTER or
            cursor.get("source_window_sha256")!=SOURCE_FIRST_SHA or
            cursor.get("next_contiguous_sha256")!=SOURCE_NEXT_SHA or
            cursor.get("second_curriculum_window")!="LOCKED" or
            doc.get("critic_prompt_original_source_prose") is not False or
            doc.get("writer_prompt_source_prose_or_plot") is not False or
            doc.get("second_unit_unlocked") is not False or
            doc.get("core_automatically_promoted") is not False):
            raise ValueError("TASK_SOURCE_OR_LOCK_INTEGRITY_MISMATCH")
        if (doc.get("role_output_token_profile")!=list(BUDGET_PROFILE) or
            doc.get("neutral_common_target_chars")!=COMMON_AB_CHARS or
            doc.get("symmetric_length_revision_opt_in") is not True or
            doc.get("symmetric_revision_calls") not in (0,2) or
            doc.get("manuscripts_cropped_or_padded") is not False):
            raise ValueError("FAIR_WRITING_PROTOCOL_MISMATCH")
        scaled=baseline_30_display(doc["comparisons"])
        if doc.get("baseline_30_display")!=scaled:
            raise ValueError("RAW_SCORE_OR_DISPLAY_TAMPERED")
        evidence=derive_unverified_candidates(doc,receipt_sha256=h)
        if (evidence["writer_model"]!="glm-5.3" or
            evidence["critic_source_blind"] is not True):
            raise ValueError("WRITER_IDENTITY_OR_CRITIC_BLIND_MISMATCH")
        usage=doc.get("usage",{})
        if (not isinstance(usage,dict) or
            type(usage.get("api_calls")) is not int or
            not 4<=usage["api_calls"]<=7 or
            type(usage.get("requested_output_tokens_reserved")) is not int or
            usage["requested_output_tokens_reserved"]>50000):
            raise ValueError("MODEL_BUDGET_UNVERIFIED")
        rows.append({
            "slot":slot,"story_id":story_id,"status":"REAL_AB_R2_VERIFIED",
            "receipt_sha256":h,
            "baseline_raw_mean":scaled["unadjusted_model_mean"]["baseline"],
            "writerforge_raw_mean":scaled["unadjusted_model_mean"]["skill"],
            "raw_effect":scaled["unadjusted_signed_delta"],
            "baseline_30_display":30.0,
            "writerforge_30_display":scaled["skill_display_score_unclipped"],
            "dimension_deltas":evidence["model_deltas"],
            "all_five_negative":all(n<0 for n in evidence["model_deltas"].values()),
            "mechanisms_unreviewed":evidence["mechanism_hypotheses_unreviewed"],
            "baseline_chars":evidence["draft_chars"]["baseline"],
            "writerforge_chars":evidence["draft_chars"]["skill"],
            "symmetric_revision_calls":doc["symmetric_revision_calls"],
            "api_calls":usage["api_calls"],
            "prompt_tokens_reported":usage.get("prompt_tokens_reported"),
            "completion_tokens_reported":usage.get("completion_tokens_reported"),
            "literary_passed":False,
        })
    passed=[r for r in rows if r["status"]=="REAL_AB_R2_VERIFIED"]
    result={
        "format":"writerforge.three-random-original-openings.audit.v1",
        "source_sha256":SOURCE_SHA,
        "source_window_sha256":SOURCE_FIRST_SHA,
        "sample_sha256":sample_sha256(),
        "selected_scenarios":list(selected_ids()),
        "results":rows,
        "count_total":3,"count_scored":len(passed),
        "all_three_scored":len(passed)==3,
        "mean_effect_scored_only":(
            round(sum(r["raw_effect"] for r in passed)/len(passed),3)
            if passed else None),
        "all_three_negative":len(passed)==3 and all(r["raw_effect"]<0 for r in passed),
        "all_three_all_dimensions_negative":len(passed)==3 and all(
            r["all_five_negative"] for r in passed),
        "source_and_writer_roles_fixed":True,
        "different_original_writing_task_per_slot":True,
        "single_model_critic_not_human_validation":True,
        "original_and_generated_manuscripts_persisted":False,
        "model_calls_for_this_audit":0,
        "first_window":"NOT_PASSED","second_window":"LOCKED",
        "literary_mastery_verified":False,"core_promoted":False,
    }
    canonical=_canonical(result)
    if len(canonical)>24000:
        raise ValueError("OVERSIZE_REPORT")
    h=sha256(canonical).hexdigest()
    if persist and len(passed)==3:
        key=f"{PREFIX}/three-original-openings-audit/{h}.json"
        store._put_small_immutable(key,canonical,h)
        if store._get_small(key,24000)!=canonical:
            raise ValueError("NEW_R2_AGGREGATE_NOT_RECOVERABLE")
    print(json.dumps({"stage":"V28_THREE_RANDOM_ORIGINAL_FIRST_CHAPTER_AUDIT",
                      "aggregate_sha256":h,**result},ensure_ascii=False,sort_keys=True))
    return result

if __name__=="__main__":
    collect(R2StudyVault(R2Config.from_environment()))
