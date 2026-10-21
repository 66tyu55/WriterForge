"""V114D zero-model genuine author-state coverage audit of rejected 964-char WF.

The MIT Novel Studio reducer can check source-anchored EVENTS, but if WF's
upstream extractor emits no events for a novel-specific object, the reducer
cannot remember that object. This script tests actual end-to-end coverage,
not merely software-schema PASS. Never reaccept, crop or rewrite old prose.
"""
from __future__ import annotations
import json,os
from pathlib import Path
from writerforge.v114_continuity_memory import literal_item_continuity,TRACKED
from writerforge.v114_external_story_state import external_temporal_step
from experiments.v114c_readonly_rejected_first_scene import (
    StrictReadOnlyCAS,SCENE_ORIGINAL,PRECOMMIT,load,need,
)

def run():
    need(not os.getenv("DEEPSEEK_API_KEY") and not os.getenv("DEEPSEEK"),
         "WF114D_NO_AI_MODEL_ALLOWED")
    cas=StrictReadOnlyCAS()
    model_original=load(cas,SCENE_ORIGINAL)
    answer=model_original["student_unmodified_answer"]
    need(type(answer) is dict and type(answer.get("prose")) is str,
         "WF114D_ORIGINAL_STUDENT_PROSE_REQUIRED")
    prose=answer["prose"]
    need(len(prose)==964 and "火髓果" in prose and "右臂" in prose,
         "WF114D_ACTUAL_ORIGINAL_STORY_MISMATCH")
    cast=("沈砚","唐蜃")
    builtin=literal_item_continuity(prose,cast=cast)
    external=external_temporal_step(prose,cast=cast)
    candidate=external["reducer_result"]
    dynamic=external["dynamic_source_entity_candidates"]
    dynamic_terms={row["term"] for row in dynamic["mentions"]}
    fields={
        "fire_fruit_explicitly_in_original":prose.count("火髓果"),
        "fruit_alias_in_original":prose.count("果子"),
        "right_arm_injury_mentions":prose.count("右臂"),
        "fruit_exact_name_present_in_native_tracked_vocab":"火髓果" in TRACKED,
        "original_prose_characters":len(prose),
        "native_item_observation_count":builtin["items_seen"],
        "external_exact_verified_event_count":candidate["verified_events"],
        "external_candidate_state_cell_count":len(candidate["candidate_state"]),
        "external_risks":candidate["risks"],
        "full_fruit_position_or_injury_semantics_verified":False,
        "dynamic_fire_fruit_mentioned": "火髓果" in dynamic_terms,
        "dynamic_right_arm_mentioned": "右臂" in dynamic_terms,
        "dynamic_mentions_not_made_into_canon":dynamic["canon_writes"]==0,
    }
    fields["critical_story_entities_not_tracked"]=(
        fields["fruit_exact_name_present_in_native_tracked_vocab"] is False and
        "火髓果" not in json.dumps(candidate["candidate_state"],ensure_ascii=False)
    )
    result={
        "format":"wf.exam.v114d.real-model-prose-coverage-red.v1",
        "origin_precommit_cas_sha256":PRECOMMIT,
        "source_rejected_first_scene_original_cas_sha256":SCENE_ORIGINAL,
        "first_scene_v96_was_rejected_for_length_only":True,
        "original_student_prose_preserved":True,
        "original_first_scene_schema_remains_REJECTED":True,
        "candidate_memory_semantic_proof":False,
        "real_original_coverages":fields,
        "coverage_pass":fields["dynamic_fire_fruit_mentioned"] and
                        fields["dynamic_right_arm_mentioned"] and
                        fields["dynamic_mentions_not_made_into_canon"],
        "new_model_calls":0,"R2_writes":0,
        "expected_long_term_extraction_repair_needed":False,
        "holder_and_injury_truth_still_unverified":True,
        "not_novel_studio_reducer_software_bug":True,
    }
    out=Path("wf114d_readonly_real_memory_coverage")
    out.mkdir(exist_ok=False)
    (out/"ACTUAL_WF_STORY_MEMORY_COVERAGE.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps({
        "status":"WF114D_REAL_PROSE_MEMORY_COVERAGE_EXAM_COMPLETE",
        "native_observations":builtin["items_seen"],
        "Novel_Studio_applied_source_events":candidate["verified_events"],
        "critical_fire_fruit_not_tracked":fields["critical_story_entities_not_tracked"],
        "dynamic_fire_fruit_mentioned":fields["dynamic_fire_fruit_mentioned"],
        "dynamic_right_arm_mentioned":fields["dynamic_right_arm_mentioned"],
        "coverage_pass":result["coverage_pass"],
        "prose_chars":len(prose),
        "literary_memory_proven":False,
        "new_model_calls":0,"R2_writes":0,
    },ensure_ascii=False,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(run())
