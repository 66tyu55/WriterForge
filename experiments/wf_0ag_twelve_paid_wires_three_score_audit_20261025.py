"""0.AG forensic-only 12 true model provider wires → verified 3x2 blind grades.

First paid run 40198761026: 6 author + 3 first-order rater originals.
Second paid run 40199709409: 3 reverse rater originals (all saved despite
response-format failures). NEVER repeat any model request in this script.
All original wire SHA and original prompt SHA must match before scoring.
"""
from __future__ import annotations
from pathlib import Path
import json

from experiments.wf_0ag_diverse_micro_paired_20261025 import (
    BATCH,JUDGEMENTS,SCENE_BY_ID,CRITERIA,parse_micro_judge,
    judge_prompt_0ag,h,save,need,
)
from experiments.wf_0ag_replay_three_real_micro_scores_only_20261025 import (
    replay_old_first_once,original_provider_response,combine,FROZEN_RUN,
)

SECOND_SOURCE=Path("wf0ag_paid_reverse_three_artifact")
SECOND_RUN=40199709409
OUT=Path("wf_0ag_twelve_original_wire_full_three_score_audit_20261025")


def replay_twelve():
    old,first_manifest,first_events=replay_old_first_once()
    second=json.loads((SECOND_SOURCE/"STATUS.json").read_text("utf8"))
    need(second.get("format")==
         "wf.0ag.real-three-micro-first-ratings-lossless-recovery.v1"
         and second["replayed_old_first_paid_run"]==FROZEN_RUN
         and second["new_model_calls"]==3
         and second["new_writer_requests"]==0
         and second["R2_reads"]==second["R2_writes"]==
         second["Canon_writes"]==0,
         "WF0AG_TWELVE_SECOND_PAID_SOURCE_MANIFEST_INVALID")
    reverse_events={}
    for row in second["new_provider_calls"]:
        key=row["scene"]
        need(key not in reverse_events and row["task"]=="blind-2" and
             row["max_tokens"]==1600 and
             row["original_provider_wire_preserved"],
             "WF0AG_TWELVE_REVERSE_RATER_CALLS_DUPLICATED_OR_CHANGED")
        reverse_events[key]=row
    need(set(reverse_events)==set(BATCH),
         "WF0AG_TWELVE_EXPECTED_THREE_REVERSED_ORIGINALS")
    results={}
    for key in BATCH:
        original=old[key]
        item=SCENE_BY_ID[key]
        pair=original["pair"]
        event=reverse_events[key]
        need(event["prompt_sha256"]==
             h(judge_prompt_0ag(item,pair,JUDGEMENTS[1])),
             "WF0AG_TWELVE_SECOND_BLIND_SOURCE_PROMPT_SHA_DRIFT")
        response=original_provider_response(
            SECOND_SOURCE/"reverse-provider-originals"/
            (key+"_blind-2.json"),
            {**event,"decoded_sha256":event["decoded_original_sha256"],
             "original_wire_preserved":
                 event["original_provider_wire_preserved"]})
        reverse,receipt=parse_micro_judge(response)
        reverse_rows={
            arm:{
                "score":sum(reverse[label]["scores"].values()),
                "dimensions":reverse[label]["scores"],
                "model_reason":reverse[label]["reason"],
                "model_weakness":reverse[label]["weakness"],
                "score_representation_receipt":receipt,
            } for arm,label in zip(JUDGEMENTS[1],("甲","乙"))}
        scores,diff=combine(original["first_ratings"],reverse_rows)
        lengths={arm:len(pair[arm]["prose"]) for arm in ("bare","WF")}
        ratio=max(lengths.values())/min(lengths.values())
        worst=max(s["order_sensitivity"] for s in scores.values())
        comparison=(
            "NOT_COMPARABLE_LENGTH_MISMATCH" if ratio>1.15 else
            "LOW_CONFIDENCE_ORDER_SENSITIVITY" if worst>8 else
            "EXPLORATORY_SAME_MODEL_FAMILY_NOT_HUMAN")
        case={
            "genre":item["genre"],
            "first_writer_paid_source_run":FROZEN_RUN,
            "reverse_judger_paid_source_run":SECOND_RUN,
            "author_original_unchanged":{
                arm:{"sha256":h(pair[arm]["prose"]),
                     "codepoints":lengths[arm]} for arm in lengths},
            "original_first_rater_wire_sha256":
                original["original_first_rater_wire_sha256"],
            "original_reverse_rater_wire_sha256":
                event["raw_provider_sha256"],
            "first_and_reverse_model_blind_scores":scores,
            "WF_minus_bare_points":diff,
            "codepoint_length_ratio":round(ratio,3),
            "within_15pct_length_ratio":ratio<=1.15,
            "grade_confidence":comparison,
            "V96_source_verification":original[
                "source_verified_again_without_model"],
            "first_real_WF_source_checks":first_manifest[
                "cases"][key]["WF_source_checks"],
            "valid_original_provider_wire_count":4,
            "literary_logic_errors_independently_verified":False,
            "confirmed_WF_false_negative_count":None,
            "confirmed_WF_false_positive_count":None,
            "new_model_calls_in_this_recovery":0,
            "model_prose_generated_by_WF":False,
            "human_independent_literary_assessment":False,
            "model_scores_are_exploratory_not_writer_reward":True,
        }
        results[key]=case
        originals=OUT/"author-originals"
        originals.mkdir(parents=True,exist_ok=True)
        for arm in ("bare","WF"):
            (originals/(key+"-"+arm+".md")).write_text(
                pair[arm]["prose"],encoding="utf8")
    return results,first_manifest,second


def main():
    OUT.mkdir(parents=True,exist_ok=False)
    summary={
        "format":"wf.0ag.true-twelve-original-wires-3x2-genre-ratings.v1",
        "status":"SOURCE_NOT_VERIFIED",
        "first_paid_run":FROZEN_RUN,
        "second_paid_reverse_run":SECOND_RUN,
        "new_model_calls":0,"new_writer_calls":0,
        "new_grade_calls":0,
        "original_author_wire_count":6,
        "original_blind_judge_wire_count":6,
        "original_provider_wire_count":12,
        "R2_reads":0,"R2_writes":0,"Canon_writes":0,
        "Railway_deployments":0,"main_modified":False,
        "three_original_short_story_pairs_modified":False,
        "independent_human_literary_grades":False,
        "literary_improvement_proven":False,
        "scores_should_not_retrain_or_auto_rewrite":True,
        "cases":{},
    }
    try:
        cases,first,second=replay_twelve()
        summary["cases"]=cases
        summary["status"]="TWELVE_TRUE_SHA_LOCKED_WIRES_THREE_DOUBLE_BLIND_SCORES_RECOVERED"
    except Exception as e:
        summary["status"]="FORENSIC_HOLD_NO_APPROXIMATE_SCORES"
        summary["failure_code"]=str(e)[:120]
        raise
    finally:
        save(OUT/"STATUS.json",summary)
        print("WF0AG_TRUE_12_WIRES "+json.dumps({
            "status":summary["status"],
            "new_model_calls":0,
            "cases":{k:{
                "bare":v["first_and_reverse_model_blind_scores"][
                    "裸模型"]["score_100"],
                "WF":v["first_and_reverse_model_blind_scores"][
                    "WF辅助"]["score_100"],
                "delta":v["WF_minus_bare_points"],
                "confidence":v["grade_confidence"],
                "original_prose_shas":v["author_original_unchanged"],
                } for k,v in summary["cases"].items()},
        },ensure_ascii=False),flush=True)


if __name__=="__main__":
    main()
