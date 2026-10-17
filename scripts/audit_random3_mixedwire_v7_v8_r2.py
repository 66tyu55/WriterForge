"""Read three preselected random-chapter A/B results; ch17 is explicitly v8 low reasoning. No models.

Only whitelisted numbers, host mechanism IDs and SHA provenance persist.
Do not copy model short reviews or any original/draft text.
"""
from __future__ import annotations

from hashlib import sha256
import json, re

from writerforge.reverse_random_chapters import chosen_chapters,selection_hash,SOURCE_SHA
from writerforge.reverse_score_scale import baseline_30_display
from writerforge.reverse_ab_candidates import derive_unverified_candidates
from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.reverse_discovery_models import ROLE_MODELS
from scripts.run_wudong_random3_v7 import TRIAL,PREFIX,TRANSFER_TASK
from scripts.run_wudong_random3_v8_low_effort_ch17 import (
    TRIAL as LOW_TRIAL,PREFIX as LOW_PREFIX,
)

# SHA anchors came from R2 preflight BEFORE any scores were returned.
PINS={
    3:("07d4a3cf1042dd22f9d892699e7be6e67b8869d9b99f9a5a03eaf9805a02c8be",
       "96b6363d40be7b99d5635af1346da0c04e44556fc06e32d1aab04e419e4942fa",
       "9ddcccf76a3f63d8036355c006ee20c976dacb1dd6ff250ef921f47e9221ac8e"),
    15:("b8be56f00a0e781e6d694872193da8fd92406e1b0934704e05434c6906fa138f",
        "69fe16f51960dda545cb0337336eec12455b0f00ea97085ef90e1544e38eebbb",
        "78ceeba24bdcf637caa3b520f4b4670965e56e1388fe5d0dc09b776cd72f49d0"),
    17:("f48452b17576ec907fc9b457d3f79496b8a3ba372836e1865e5ef0698e104cea",
        "696a122fdfe69622527bebc722fd724b548a7fb9840203cc9ccac2bab85e4b8d",
        "84c1305db79c5ee3b84de3b79100d9780ab2b1f0336a5f6a9f696e3e7683d6fc"),
}
DIMENSIONS=("perception","causality","information","continuity","language")

def _root(slot:int,chapter:int)->str:
    is_low=(slot==2 and chapter==17)
    config={"source":SOURCE_SHA,"task":"chapter-random-diagnostic-only",
            "chapter":chapter,"slot":slot,"sample_sha256":selection_hash(),
            "roles":ROLE_MODELS,"trial":LOW_TRIAL if is_low else TRIAL,
            "creative_task_sha256":sha256(TRANSFER_TASK.encode("utf-8")).hexdigest()}
    if is_low:
        config["wire_profile"]="glm-5.3:reasoning_effort-low:5500-8500-7000"
    prefix=LOW_PREFIX if is_low else PREFIX
    return f"{prefix}/chapter-{chapter}/{sha256(_canonical(config)).hexdigest()}"

def collect(store:R2StudyVault, *, persist:bool=True):
    if store.config.bucket!="writerforge-private-library":
        raise ValueError("wrong private bucket")
    rows=[]
    for slot,chapter in enumerate(chosen_chapters()):
        root=_root(slot,chapter)
        pointer=json.loads(store._get_small(root+"/completed.json",4096))
        h=pointer.get("sha256")
        if (not isinstance(h,str) or not re.fullmatch("[0-9a-f]{64}",h)
            or pointer.get("source_sha256")!=SOURCE_SHA):
            raise ValueError("random3 pointer unavailable or invalid")
        raw=store._get_small(root+f"/snapshots/{h}.json",32000)
        if sha256(raw).hexdigest()!=h:
            raise ValueError("random3 receipt content SHA mismatch")
        doc=json.loads(raw)
        if (doc.get("edition_sha256")!=SOURCE_SHA
            or doc.get("random_chapter_sample")!={"protocol":"V28_RANDOM3_BEFORE_SCORE",
                "selection_sha256":selection_hash(),"slot":slot,"chapter":chapter,
                "selected_chapters":list(chosen_chapters()),
                "randomness_pinned_before_scoring":True}
            or doc.get("writing_task_sha256")!=sha256(TRANSFER_TASK.encode("utf-8")).hexdigest()
            or doc.get("critic_prompt_original_source_prose") is not False):
            raise ValueError("random3 identity, writer task or critic blind guard changed")
        cursor=doc.get("source_cursor_diagnostic",{})
        pin=PINS[chapter]
        if (cursor.get("chapter")!=chapter or
            cursor.get("source_window_sha256")!=pin[1] or
            cursor.get("chapter_body_sha256")!=pin[0] or
            cursor.get("next_contiguous_sha256")!=pin[2] or
            doc.get("source_unit_sha256")!=pin[1] or
            doc.get("next_unit_sha256")!=pin[2] or
            cursor.get("semantic_boundary_verified") is not False or
            cursor.get("diagnostic_only_no_promotion") is not True or
            cursor.get("second_curriculum_window")!="LOCKED"):
            raise ValueError("pre-scored source chapter pin changed")
        measured=baseline_30_display(doc["comparisons"])
        if doc.get("baseline_30_display")!=measured:
            raise ValueError("baseline30 display or original dimensions were modified")
        candidate=derive_unverified_candidates(doc,receipt_sha256=h)
        if candidate["writer_model"]!="glm-5.3" or not candidate["critic_source_blind"]:
            raise ValueError("model identity/provenance failure")
        usage=doc.get("usage",{})
        if (not isinstance(usage,dict)
            or not 4<=usage.get("api_calls",0)<=7
            or usage.get("requested_output_tokens_reserved",0)>50000):
            raise ValueError("unverified model call or token budget")
        if slot==2:
            p=doc.get("budget_and_gateway_repair_protocol")
            if (not isinstance(p,dict) or
                p.get("glm_writer_reasoning_effort")!="low" or
                p.get("probe_action_id")!=38999272334 or
                p.get("role_output_budgets")!=[5500,8500,7000] or
                p.get("not_strictly_same_wire_settings_as_v7") is not True):
                raise ValueError("low-effort gateway protocol changed")
        scores=measured["unadjusted_model_mean"]
        raw_diff=measured["unadjusted_signed_delta"]
        dims=candidate["model_deltas"]
        rows.append({
            "slot":slot,"chapter":chapter,
            "wire_profile":"LOW_REASONING_V8" if slot==2 else "LEGACY_V7",
            "receipt_sha256":h,
            "source_window_sha256":pin[1],
            "baseline_raw_mean":scores["baseline"],
            "enhanced_raw_mean":scores["skill"],
            "enhanced_minus_baseline":raw_diff,
            "baseline_30_display":30.0,
            "wf_30_display":measured["skill_display_score_unclipped"],
            "dimension_deltas":dims,
            "all_five_negative":all(x<0 for x in dims.values()),
            "negative_effect":raw_diff<0,
            "mechanism_ids_unreviewed":candidate["mechanism_hypotheses_unreviewed"],
            "baseline_chars":candidate["draft_chars"]["baseline"],
            "enhanced_chars":candidate["draft_chars"]["skill"],
            "api_calls":usage["api_calls"],
            "tokens_prompt_reported":usage.get("prompt_tokens_reported"),
            "tokens_completion_reported":usage.get("completion_tokens_reported"),
            "not_human_review":True,
        })
    report={
        "format":"writerforge.random3-mixedwire-postscore-audit.v1",
        "source_sha256":SOURCE_SHA,"sample_sha256":selection_hash(),
        "chapters":list(chosen_chapters()),
        "results":rows,
        "count":len(rows),
        "all_three_negative_relative_to_baseline":all(x["negative_effect"] for x in rows),
        "all_three_five_dimensions_negative":all(x["all_five_negative"] for x in rows),
        "mean_wf_minus_baseline":round(sum(x["enhanced_minus_baseline"] for x in rows)/len(rows),3),
        "historical_v5_delta":7.2,"historical_v6_delta":-2.8,
        "same_writer_and_task_across_trials":True,
        "same_wire_protocol_across_trials":False,
        "strict_cross_chapter_causal_comparison_allowed":False,
        "chapter17_single_protocol_recovery":True,
        "single_critic_not_human_independent":True,
        "literary_mastery_verified":False,"first_window":"NOT_PASSED","second_window":"LOCKED",
        "core_promoted":False,"model_calls_in_this_audit":0,
    }
    payload=_canonical(report)
    if len(payload)>24576: raise ValueError("unbounded evidence report")
    h=sha256(payload).hexdigest()
    if persist:
        key=f"{LOW_PREFIX}/mixedwire-three-postscore-aggregate/{h}.json"
        store._put_small_immutable(key,payload,h)
        if store._get_small(key,24576)!=payload:
            raise ValueError("R2 random3 aggregate fresh GET mismatch")
    print(json.dumps({"stage":"V28_RANDOM3_MIXEDWIRE_R2_POSTSCORE_AUDIT",
                      "aggregate_sha256":h,**report},ensure_ascii=False,sort_keys=True))
    return report

if __name__=="__main__":
    collect(R2StudyVault(R2Config.from_environment()))
