"""0.AB evidence-grounded assessment of the 0.AA SCORE MEASUREMENT itself.

This module is in experiments/, NOT in the WriterForge author core.
It never edits author prose, produces literary judgments or allows an
unchallenged score to become a training reward. Its frozen sample annotations
are review hypotheses tied to exact observed sample SHA, not "plot truth".
"""
from __future__ import annotations
from pathlib import Path
import json

SOURCE_SHA="2fc1698410418bf136448807335c6359bf515b75e6f9c1e1d1f443a1c928e6cc"
FROZEN_WINDOWS={
    "1":{
        "A":"d731acb0c5940191bee7e929edc672a9d3459a87b4e96a422c4f05c5ab774cbc",
        "B":"15e09f04cea060e6567760aa172df8157cdfb2eeca80a5f11e6bf4ba223b449e",
        "R":"636172c9a580c1d18b3d15ec48ed4ff22e688e2e95f1b2d0d1343130128da0f1",
    },
    "2":{
        "A":"0366730b6a1cc2ba1a13b8ae99e6aecd8b1fbe3475d4b1bb8908048f3169ba9c",
        "B":"a02019ba500881ad28db87bd320f84679f0e79c77a89f5ec66aee41edf050629",
        "R":"ad3f85a17cba44bc73dbb593689d808ed382633a6e9d0249b0134233410064bb",
    },
}
# Locked AFTER the first real score result and based on observed narrative
# functions of actual old original/source, not automatically chosen by WF.
# More scoring cannot rectify this original research design retroactively.
NARRATIVE_FUNCTION_CANDIDATES={
    "1":{"R":"家庭环境与人物生存背景",
         "A":"异常发现与具象风险","B":"异常发现与物件伏笔"},
    "2":{"R":"城镇与地方环境交代",
         "A":"行动后果与承担代价","B":"现场调查与悬念推进"},
}
FLAGS=(
    "DIFFERENT_NARRATIVE_FUNCTIONS",
    "STAGE_2_WINDOW_LENGTH_MISMATCH",
    "NO_BARE_MODEL_CONTROL",
    "SAME_MODEL_FAMILY_RATER",
    "ONLY_TWO_WINDOWS",
    "NO_INDEPENDENT_HUMAN_REVIEW",
)

def guard(ok,code):
    if not ok: raise RuntimeError(code)

def audit_comparability(score):
    guard(type(score) is dict and
          score.get("format")==
              "wf.0aa.frozen-first-two-stages-reference-score.v1" and
          score.get("status")==
              "PROVISIONAL_TWO_STAGE_LOW_CONFIDENCE_MODEL_RATINGS" and
          score.get("source_reference_sha256")==SOURCE_SHA and
          score.get("selected_window_sha256")==FROZEN_WINDOWS,
          "WF0AB_REFERENCE_WINDOW_SHA_DRIFT")
    guard(score.get("same_judge_model_family_as_original_writer") is True and
          score.get("this_is_not_human_blind_review") is True and
          score.get("cannot_attribute_change_to_WF_in_this_AB_design") is True
          and score.get("original_book_prose_in_public_artifacts") is False
          and score.get("r2_writes")==score.get("canon_writes")==0
          and score.get("paid_rating_calls")==4 and
          score.get("sample_count")==6,
          "WF0AB_INDEPENDENT_SCORE_EVIDENCE_NOT_PROVEN")
    ratings=score.get("overall_average_scores")
    guard(type(ratings) is dict and set(ratings)=={"R","A","B"}
          and all(type(x) in (int,float) and 0<=x<=100
                  for x in ratings.values()),
          "WF0AB_SCORE_RANGE_OR_PROVENANCE_INVALID")
    lengths=score.get("sample_character_counts")
    guard(type(lengths) is dict and set(lengths)=={"1","2"} and
          all(type(vals) is dict and set(vals)=={"R","A","B"} and
              all(type(count) is int and 170<=count<=230
                  for count in vals.values())
              for vals in lengths.values()),
          "WF0AB_COMPARISON_SAMPLE_LENGTH_NOT_PROVEN")
    second=list(lengths["2"].values())
    ratio=max(second)/min(second)
    # A fair one-to-one writing-function comparison cannot treat a quiet
    # village description as the same task as a plot decision or puzzle.
    # This is a score-MEASUREMENT failure, not the original author's defect.
    different_modes=any(
        len(set(modes.values()))>1
        for modes in NARRATIVE_FUNCTION_CANDIDATES.values())
    guard(different_modes and ratio>1.20,
          "WF0AB_EXPECTED_FIRST_PILOT_DEFECT_NOT_REPRODUCED")
    return {
        "format":"wf.0ab.literary-score-measurement-validity.v1",
        "underlying_rating_run":40182718487,
        "rubric_is_subjective_model_rating":True,
        "scores_from_real_provider_not_fabricated":True,
        "raw_local_excerpt_score_100":{
            k:float(ratings[k]) for k in ("R","A","B")},
        "raw_B_minus_A":round(ratings["B"]-ratings["A"],1),
        "raw_A_minus_reference":round(ratings["A"]-ratings["R"],1),
        "raw_B_minus_reference":round(ratings["B"]-ratings["R"],1),
        "stage_2_char_length_ratio":round(ratio,3),
        "frozen_narrative_function_hypotheses":NARRATIVE_FUNCTION_CANDIDATES,
        "flags":list(FLAGS),
        "valid_progression_signal":False,
        "comparable_literary_level_score":None,
        "proves_WF_improvement":False,
        "proves_original_literary_level_surpassed":False,
        "cannot_use_as_WF_training_reward":True,
        "literary_reference_does_not_need_a_hardcoded_100":True,
        "WF_author_prose_changed":False,
        "WF_literary_grading_or_prompt_policy_changed":False,
        "need_next_match_on_narrative_function":True,
        "need_bare_model_same_task_control":True,
        "need_separate_structural_source_integrity_gate":True,
        "source_based_B2_physical_relation_review_run":40167612081,
        "source_and_schema_verified":True,
        "R2_reads":0,"R2_writes":0,"canon_writes":0,
        "new_model_calls":0,
    }

def main():
    src=Path("wf0aa_frozen_ratings/STATUS.json")
    out=Path("wf0ab_rating_method_audit")
    out.mkdir(parents=True,exist_ok=False)
    score=json.loads(src.read_text("utf8"))
    audit=audit_comparability(score)
    (out/"STATUS.json").write_text(json.dumps(
        audit,ensure_ascii=False,sort_keys=True,indent=2),encoding="utf8")
    print("WF0AB_BENCHMARK_VALIDITY "+json.dumps({
        "raw_scores":audit["raw_local_excerpt_score_100"],
        "valid_literary_progression_signal":False,
        "flags":audit["flags"],
        "new_model_calls":0,
    },ensure_ascii=False))

if __name__=="__main__":
    main()
