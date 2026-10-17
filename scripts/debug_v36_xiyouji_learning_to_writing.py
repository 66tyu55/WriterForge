"""V36 zero-model debugger for the actual V35 Xi You Ji learning->writing trace.

Reloads ALL original immutable reading/lesson/prewrite/draft stages from the
user's PRIVATE R2 and the strictly additive V35 after-writing recovery. It
checks factual cross-stage pointers and exact text anchors without pretending
that lexical matches prove causal or literary understanding.

Public output is metadata only: never publish private original prose, generated
story, prewriting decisions, explanations, literary quotes, credentials or
reviewer commentary. The full inputs remain retrievable ONLY privately.
"""
from __future__ import annotations
from collections import Counter
from difflib import SequenceMatcher
from hashlib import sha256
import json,re

from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.v35_observable_trace import (
    canonical,sha,validate_read,validate_lessons,validate_plan,
    validate_draft,validate_after,TraceContractError,
)
from writerforge.v35_xiyouji_exam import manifest,manifest_sha,task
from scripts.run_v35_xiyouji_decision_trace import restore_stage,STAGES
from scripts.recover_v35_afterdraft_only import PREFIX as AFTER_PREFIX
from scripts.recover_v35_afterdraft_only import SESSION as AFTER_SESSION
from scripts.recover_v35_afterdraft_only import _quote_menu

EXPECTED_ORIGINAL_SHA=(
    "125f8ce4305991beacdcfbdf36708b55adc523d62780a7bbd4f02e2dab1063b7",
    "3d7d951af61116b8bd68512f76bfb67654e7c7935c967171bccd8d0f7fdc12e8",
    "c96c926c58481818538e2d8f5ed11b212394421ed21db6834cc2b30fed5d102e",
    "a268aa596cf3c98328eeeb785ea026d65ba666ca41a226ef3b023e50d6894895",
    "9c3a671ed8c588019a0f46b0613641b59441282983bce4bb0882c20ebcfafe70",
    "605fc022f59a87e3eb4d199ed7ef0c9898c1ce52edfa03a2674a8db0d80d0acf",
)
AFTER_SHA="412b6ceb09d8513c72d4df58d9792d483d5bb6b5b36a8ea955e74812afee595d"
AFTER_EXAMINER_SHA="910f2495624038194d7f020fd34eff4ccdf18033589ab70d137828d2152ab454"
REPORT_PREFIX="writerforge/v1/examiner/v36-xiyouji-trace-debugger"
REPORT_CAP=22000

class TraceDebugError(ValueError):
    pass

def _require(expr:bool,code:str)->None:
    if not expr:raise TraceDebugError(code)

def _read_exact(vault,key:str,hash_:str,cap:int)->dict:
    raw=vault._get_small(key,cap)
    _require(sha(raw)==hash_,"IMMUTABLE_PRIVATE_OBJECT_HASH_MISMATCH")
    value=json.loads(raw)
    _require(isinstance(value,dict),"IMMUTABLE_PRIVATE_OBJECT_NOT_JSON")
    return value

def _after_key(label:str,digest:str)->str:
    return (f"{AFTER_PREFIX}/{AFTER_SESSION}/"
            f"{label}-{digest}.json")

def _long_overlap(source:str,candidate:str,size:int=24)->bool:
    compact_source="".join(source.split())
    compact_candidate="".join(candidate.split())
    if len(compact_candidate)<size:return False
    return any(compact_candidate[i:i+size] in compact_source
               for i in range(len(compact_candidate)-size+1))

def analyze(vault, *, persist:bool=True)->dict:
    if vault.config.bucket!="writerforge-private-library":
        raise TraceDebugError("PRIVATE_R2_ONLY")
    stages=[]
    previous=None
    for i,wanted in enumerate(EXPECTED_ORIGINAL_SHA):
        result=restore_stage(vault,i,previous)
        _require(result is not None,"MISSING_HISTORICAL_STAGE")
        record,h=result
        _require(h==wanted,"HISTORICAL_ORIGINAL_STAGE_CHANGED")
        stages.append(record["payload"])
        previous=h

    source,reading,learned,prewrite,first,correction=stages
    _require(source["original_chapters_verified"]==100 and
             source["actual_model_read_chapters"]==[1,2] and
             source["model_did_not_read_all_hundred_chapters"] is True,
             "SOURCE_WINDOW_OR_SCOPE_NOT_VERIFIED")
    windows={int(k):v for k,v in source["actual_model_read_windows"].items()}
    _require(set(windows)=={1,2} and
             all(len(v)==2000 for v in windows.values()),
             "INCOMPLETE_TWO_SOURCE_WINDOWS")
    read=validate_read({"observations":reading["observations"]},windows)
    _require(read["observations"]==reading["observations"],
             "FIRST_READING_RECONSTRUCTION_DIFFERS")
    raw_lessons=[{k:v for k,v in row.items() if k!="id"}
                 for row in learned["lessons"]]
    lessons=validate_lessons({"lessons":raw_lessons},len(read["observations"]))
    _require(lessons["lessons"]==learned["lessons"],
             "LESSON_ID_OR_SOURCE_OBSERVATION_DIFFERS")
    eligible={x["id"] for x in lessons["lessons"]}
    plan=validate_plan({"decisions":prewrite["plan"]["decisions"]},eligible)
    _require(plan["decisions"]==prewrite["plan"]["decisions"] and
             prewrite["frozen_before_any_glm_writer_call"] is True and
             prewrite["exam"]["manifest"]==manifest() and
             prewrite["exam"]["manifest_sha256"]==manifest_sha() and
             prewrite["exam"]["examiner_task"]==task(),
             "PREWRITE_OR_EXAM_HAD_BEEN_CHANGED")
    original=validate_draft(first["body"],windows)
    _require(original==first,"ORIGINAL_MANUSCRIPT_SHA_OR_LENGTH_DIFFERENT")
    _require(correction["retained_original_draft_stage_sha256"]==sha(canonical(first))
             and correction["did_not_overwrite_first_draft"] is True,
             "ORIGINAL_MANUSCRIPT_NOT_PRESERVED")
    final=(correction["edited_draft"]["body"] if correction["edited"]
           else original["body"])
    rebuilt=validate_draft(final,windows)
    _require(rebuilt["body_sha256"]==correction["final_body_sha256"]
             and rebuilt["characters_including_punctuation"]==
                 correction["final_characters"] and
             correction["final_valid_absolute_length"] is True and
             rebuilt["within_absolute_length_bounds"] is True,
             "FINAL_MANUSCRIPT_PROVENANCE_OR_BOUNDS_CHANGED")
    after=_read_exact(vault,_after_key("valid-retrospective",AFTER_SHA),
                      AFTER_SHA,36000)
    examiner=_read_exact(vault,_after_key("append-only-examiner-audit",
                                         AFTER_EXAMINER_SHA),
                         AFTER_EXAMINER_SHA,36000)
    checked=validate_after(
        {"checks":after["checks"],"biggest_mistake":after["biggest_mistake"]},
        final,plan)
    menu=_quote_menu(final)
    _require(all(x["actual_draft_quote"] in menu.values()
                 for x in checked["checks"]),
             "POSTWRITE_QUOTE_NOT_IN_MECHANICAL_MENU")
    # Independent explicit assertions isolate exactly which bridge is broken.
    _require(after.get("original_frozen_final_draft_sha256")==sha(final),
             "RECOVERED_REVIEW_REFERENCES_DIFFERENT_MANUSCRIPT")
    _require(after.get("source_manifest_sha256")==manifest_sha(),
             "RECOVERED_REVIEW_QUESTION_MANIFEST_CHANGED")
    _require(after.get("original_frozen_prewrite_sha256")==EXPECTED_ORIGINAL_SHA[3],
             "RECOVERED_REVIEW_PREWRITE_SNAPSHOT_CHANGED")
    _require(after.get("repair_did_not_change_story_or_preplan") is True,
             "RECOVERED_REVIEW_CLAIMS_TO_HAVE_REWRITTEN_HISTORY")
    _require(after.get("original_v35_bad_quote_attempt_already_recorded") is True,
             "ORIGINAL_POSTWRITE_QUOTE_FAILURE_NOT_ACKNOWLEDGED")
    _require(examiner.get("new_visible_retrospective_record_sha256")==AFTER_SHA,
             "EXAMINER_REVIEW_POINTER_CHANGED")
    _require(examiner.get("frozen_original_essay_sha256")==sha(final),
             "EXAMINER_REFERENCES_DIFFERENT_MANUSCRIPT")
    _require(examiner.get("frozen_prewrite_sha256")==EXPECTED_ORIGINAL_SHA[3],
             "EXAMINER_REFERENCES_DIFFERENT_PREWRITE")
    _require(examiner.get("real_source_and_draft_quotes_machine_verified") is True,
             "EXAMINER_QUOTE_CHECK_MISSING")
    _require(examiner.get("official_core_promoted") is False,
             "UNVERIFIED_LEARNING_PROMOTED")
    observed={row["angle"]:row for row in checked["checks"]}
    _require(len(observed)==len(checked["checks"]),
             "DUPLICATE_AFTERCHECK_ANGLE_NOT_UNIQUELY_TRACEABLE")
    lesson_by_id={x["id"]:x for x in learned["lessons"]}
    decisions=[]
    for decision in plan["decisions"]:
        angle=decision["angle"]
        lesson_id=decision["learned_lesson_id"]
        _require(lesson_id=="NONE" or lesson_id in lesson_by_id,
                 "DRAFT_PLAN_REFERENCES_UNKNOWN_LESSON")
        after_row=observed.get(angle)
        cite=(after_row["actual_draft_quote"] if after_row else None)
        decisions.append({
            "angle":angle,
            "source_learned_lesson_id":lesson_id,
            "linked_source_observation_index":(
                lesson_by_id[lesson_id]["source_observation_index"]
                if lesson_id!="NONE" else None),
            "plan_chosen_approach_sha256":sha(decision["chosen_approach"]),
            "plan_reason_sha256":sha(decision["reason"]),
            "plan_rejected_alternative_sha256":sha(decision["rejected_alternative"]),
            "expected_reader_effect_sha256":sha(decision["expected_story_effect"]),
            "has_append_only_aftercheck":after_row is not None,
            "self_claim_followed":(
                after_row["followed_prewrite_plan"] if after_row else None),
            "checked_quote_sha256":sha(cite) if cite else None,
            "checked_quote_begin_in_final_draft":final.find(cite) if cite else None,
            "quote_found_in_original_first_draft":(
                cite in original["body"] if cite else None),
            "quote_found_in_final_draft":cite in final if cite else None,
            "human_verified_that_approach_succeeded":False,
        })

    # This cannot measure semantic transfer, but it can catch a literal
    # source-copy accident in supposedly *abstract* learning statements.
    analysis_text="".join(
        r[k] for r in learned["lessons"]
        for k in ("technique","why","use_when","avoid_when","verification_question"))
    analysis_leaked=any(_long_overlap(w,analysis_text) for w in windows.values())
    plan_text="".join(
        r[k] for r in plan["decisions"]
        for k in ("chosen_approach","reason","rejected_alternative","expected_story_effect"))
    plan_leaked=any(_long_overlap(w,plan_text) for w in windows.values())

    first_text=original["body"]
    revision_opcodes=SequenceMatcher(None,first_text,final,autojunk=False).get_opcodes()
    retained_count=sum(i2-i1 for tag,i1,i2,j1,j2 in revision_opcodes
                       if tag=="equal")
    self_claims=Counter(
        "followed" if x["followed_prewrite_plan"] else "not_followed"
        for x in checked["checks"])
    learned_linked={d["angle"] for d in decisions
                    if d["source_learned_lesson_id"]!="NONE"}
    learned_checked=learned_linked.intersection(observed)
    # An exact quote from a non-source-linked angle does not show the WF
    # applied its newly extracted Xi You Ji craft lesson in the novel.
    learned_coverage_status=(
        "NO_LEARNED_TECHNIQUE_REFERENCED_IN_PREWRITE"
        if not learned_linked else
        "SOURCE_LINKED_DECISIONS_NOT_CHECKED_IN_POSTWRITE"
        if not learned_checked else
        "SOURCE_LINKED_DECISIONS_SELF_CHECKED_BUT_NOT_SEMANTICALLY_VERIFIED")
    report={
        "format":"writerforge.v36-xiyouji-trace-debugger.v1",
        "source_original_stage_sha256":list(EXPECTED_ORIGINAL_SHA),
        "recovered_after_sha256":AFTER_SHA,
        "recovered_examiner_audit_sha256":AFTER_EXAMINER_SHA,
        "verifications":{
            "all_original_six_stage_sha_checked":True,
            "real_source_chapters_pinned":100,
            "actual_model_read_chapters":[1,2],
            "actual_window_characters":[len(windows[1]),len(windows[2])],
            "exact_source_quotes_revalidated":len(read["observations"]),
            "lesson_source_indices_revalidated":len(learned["lessons"]),
            "exam_task_precommitted_and_unseen_until_after_learning":True,
            "prewrite_frozen_before_first_draft":True,
            "original_first_draft_hash_and_bounds_checked":True,
            "final_draft_hash_and_bounds_checked":True,
            "aftercheck_quotes_in_same_frozen_final_draft":len(checked["checks"]),
            "unreviewed_semantic_truth_cannot_be_proven_from_quotes":True,
        },
        "transfer_trace":{
            "lesson_ids_created":sorted(eligible),
            "prewrite_angle_count":len(plan["decisions"]),
            "prewrite_angles":sorted(x["angle"] for x in plan["decisions"]),
            "plan_decisions_referencing_source_lessons":sum(
                d["source_learned_lesson_id"]!="NONE" for d in decisions),
            "plan_decisions_not_using_a_source_lesson":sum(
                d["source_learned_lesson_id"]=="NONE" for d in decisions),
            "lesson_ids_referenced_in_prewrite":sorted({
                d["source_learned_lesson_id"] for d in decisions
                if d["source_learned_lesson_id"]!="NONE"}),
            "source_linked_prewrite_angles":sorted(learned_linked),
            "source_linked_prewrite_angles_checked_after_drafting":
                sorted(learned_checked),
            "source_linked_angles_missing_postwrite_evidence":
                sorted(learned_linked-set(observed)),
            "actual_literary_transfer_observability_status":learned_coverage_status,
            "learned_technique_literary_effect_verified":False,
            "aftercheck_count":len(checked["checks"]),
            "self_reported_followed":self_claims["followed"],
            "self_reported_not_followed":self_claims["not_followed"],
            "unexamined_prewrite_angles":sorted(
                set(d["angle"] for d in decisions)-set(observed)),
            "per_angle_immutable_bridge":decisions,
            "abstract_lesson_contains_24char_exact_source_copy":analysis_leaked,
            "prewrite_decisions_contain_24char_exact_source_copy":plan_leaked,
        },
        "draft_rewrite":{
            "original_first_draft_chars":len(first_text),
            "final_draft_chars":len(final),
            "final_characters_added_net":len(final)-len(first_text),
            "identical_character_count_in_matching_blocks":retained_count,
            "initial_characters_retained_in_exact_matching_blocks_pct":
                round(retained_count/max(1,len(first_text))*100,2),
            "revision_treated_as_separate_artifact_not_rewriting_history":True,
        },
        "original_failed_retrospect_still_failed":True,
        "recovered_review_is_append_only_not_original_stage6":True,
        "selected_story_quality_independently_verified":False,
        "semantic_transfer_from_classic_independently_verified":False,
        "hidden_model_reasoning_not_retrievable":True,
        "any_external_model_in_this_debugger":False,
        "first_window":"NOT_PASSED",
        "second_window":"LOCKED",
        "official_skill_promoted":False,
    }
    payload=_canonical(report)
    _require(len(payload)<=REPORT_CAP,"DEBUGGER_REPORT_EXCEEDS_BUDGET")
    digest=sha(payload)
    if persist:
        key=f"{REPORT_PREFIX}/audits/{digest}.json"
        vault._put_small_immutable(key,payload,digest)
        _require(vault._get_small(key,REPORT_CAP)==payload,
                 "DEBUGGER_PRIVATE_R2_ROUNDTRIP_FAILED")
    return {"stage":"V36_XIYOUJI_REAL_TRACE_DEBUGGER_NO_MODEL_CALLS",
            "new_debugger_report_sha256":digest,
            "private_full_report_saved":bool(persist),
            **report}

if __name__=="__main__":
    vault=R2StudyVault(R2Config.from_environment())
    print(json.dumps(analyze(vault),ensure_ascii=False,sort_keys=True))
