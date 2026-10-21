"""V104 ONE-SHOT WF self-directed ten-scene original writing examination.

Runs solely in a separate manually selected Railway job (not original WF
production service). Only inference actor: WF's own DeepSeekFlashModel.
The single language model selects all 10 premises AND writes all 10 raw
scenes. No second generator/judge/critic/research tool, no human scene
ideas, no V92 unapproved lesson or previous generated prose in later prompts.

Original paid model JSON is privately CAS-persisted and read back BEFORE
the app validates prose or treats any string as an accepted candidate.
The experiment owns NO formal training/promotion and cannot prove WF
independent of the underlying provider's pretrained capabilities.
"""
from __future__ import annotations
from hashlib import sha256
import json,os,re,traceback
from writerforge.v104_self_scene_protocol import (
    RUN_ID,MODEL,MAX_CALLS,GENRE_REQUESTS,DRAFT_REQUESTS,
    PLAN_MAX_OUTPUT_TOKENS,DRAFT_MAX_OUTPUT_TOKENS,
    MAX_RESERVED_OUTPUT,MAX_CONSERVATIVE_TOKENS,
    TARGET_CHARACTERS,PLANNER_SYSTEM,PLANNER_TASK,WRITER_SYSTEM,
    precommit,encode,digest,check_plan,prompt_scene,
    record_prose,reused_fragments,V104ExamError,
)
from writerforge.deepseek_flash_model import (
    DeepSeekFlashModel,FlashBudget,
)
from writerforge.v79_provisional_r2_cas_journal import (
    WFProvisionalR2CASJournal,
)

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
SECRETS=("DEEPSEEK_API_KEY","WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN")
MAX_SOURCE_PROMPT=11000
MAX_RECEIPT_BYTES=68000

def need(ok,code):
    if not ok:raise V104ExamError(code)

def publish(report):
    print(json.dumps(report,ensure_ascii=False,sort_keys=True,
                     separators=(",",":")),flush=True)

def private_write(cas,content,code):
    need(type(content) is bytes and len(content)<=250000,
         "WF104_R2_BLOB_TOO_LARGE")
    pointer,_=cas._put_content(content)
    need(pointer==digest(content) and cas._get_content(pointer)==content,code)
    return pointer

def run():
    need(all(os.environ.get(s) for s in SECRETS),
         "WF104_THREE_EXISTING_CREDENTIALS_REQUIRED")
    cas=WFProvisionalR2CASJournal(endpoint=ENDPOINT)
    cas.require_writer_ready()
    original_pre=encode(precommit())
    pre_sha,is_new=cas._put_content(original_pre)
    need(digest(original_pre)==pre_sha and is_new is True,
         "WF104_ALREADY_RESERVED_NO_NEW_MODEL_CALLS")
    need(cas._get_content(pre_sha)==original_pre,
         "WF104_PRECOMMIT_R2_READBACK_FAILED")
    budget=FlashBudget(
        max_calls=MAX_CALLS,
        max_reserved_output_tokens=MAX_RESERVED_OUTPUT,
        max_total_tokens=None)
    model=DeepSeekFlashModel(budget=budget,timeout_seconds=120)
    held_budget=0
    paid_attempt_log=[]
    raw_records=[]
    results=[]
    completed=[]

    def request(kind,index,sys_text,prompt,out_limit):
        nonlocal held_budget
        need(kind in ("self_premises","self_prose"),
             "WF104_UNKNOWN_STUDENT_REQUEST")
        need(len(prompt)<=MAX_SOURCE_PROMPT and
             type(sys_text) is str and len(sys_text)<2000 and
             "JSON" in sys_text,
             "WF104_INPUT_PROMPT_CONTRACT_INVALID")
        call={
            "format":"wf.exam.v104.one-provider-request-identity",
            "run_id":RUN_ID,"slot":index,"stage":kind,
            "model":MODEL,"role":"self_scene_writing",
            "system_sha256":digest(sys_text.encode("utf8")),
            "prompt_sha256":digest(prompt.encode("utf8")),
            "output_max_tokens":out_limit,
            "any_other_generator_or_reviewer":False,
        }
        hold=len(encode(call))+len(prompt.encode("utf8"))+len(sys_text.encode("utf8"))+2048+out_limit
        need(held_budget+hold<=MAX_CONSERVATIVE_TOKENS,
             "WF104_TOTAL_CONSERVATIVE_TOKEN_BUDGET_EXCEEDED")
        held_budget+=hold
        # Once the provider has been contacted, the charged slot is never
        # automatically replayed even if transport times out.
        paid_attempt_log.append({
            "stage":kind,"slot":index,"request_sha256":digest(encode(call))})
        answer=model.ask_json(
            role="self_scene_writing",system=sys_text,user=prompt,
            max_tokens=out_limit)
        # Model unmodified answer first; no validation/filtering before R2.
        raw={
            "format":"wf.exam.v104.raw-one-model-answer",
            "parent_precommit_sha256":pre_sha,
            "call_identity":call,
            "answer_unmodified":answer,
            "no_feedback_or_retry_from_external_judge":True,
        }
        content=encode(raw)
        sha=private_write(cas,content,
                          "WF104_ORIGINAL_RAW_MODEL_REPLY_NOT_R2_RECOVERABLE")
        raw_records.append({"stage":kind,"slot":index,
                            "call_identity_sha256":digest(encode(call)),
                            "raw_cas_sha256":sha,
                            "actual_response_sha256":digest(encode(answer))})
        return answer,sha

    plan,plan_response_sha=request(
        "self_premises",0,PLANNER_SYSTEM,PLANNER_TASK,
        PLAN_MAX_OUTPUT_TOKENS)
    proposals,plan_checks=check_plan(plan)
    all_concepts_sha=digest(encode(plan))
    plan_manifest={
        "format":"wf.exam.v104.locked-self-chosen-premises",
        "run_precommit_sha256":pre_sha,
        "planner_raw_response_cas_sha256":plan_response_sha,
        "scene_list_sha256":all_concepts_sha,
        "all_scenes":proposals,
        "lexical_plan_checks":plan_checks,
        "any_preprovided_story_ideas_or_endings":False,
        "independent_literary_diversity_evaluation":False,
    }
    plan_sha=private_write(
        cas,encode(plan_manifest),"WF104_SELF_PROPOSED_SCENE_PLAN_NOT_LOCKED")
    publish({"status":"WF104_WF_SELF_CHOSEN_TEN_PREMISES_SEALED",
             "r2_precommit_sha256":pre_sha,
             "frozen_self_scene_plan_cas_sha256":plan_sha,
             "planner_actual_model_calls":budget.calls_reserved,
             "all_scenes_origin":"WF_SINGLE_REGISTERED_PROVIDER_INFERENCE",
             "ten_semantically_distinct_unverified":True})

    for idx,scene in enumerate(proposals,1):
        # Each essay prompt sees ONLY its own scene, never the other 9 plans,
        # old prose, student critiques, external references or book excerpts.
        user=prompt_scene(scene)
        answer,answer_sha=request("self_prose",idx,WRITER_SYSTEM,
                                  user,DRAFT_MAX_OUTPUT_TOKENS)
        rec=record_prose(answer)
        entry={
            "format":"wf.exam.v104.raw-independent-scene-candidate",
            "ordinal":idx,"scene_id":scene["id"],
            "self_scene_plan_sha256":digest(encode(scene)),
            "raw_model_response_cas_sha256":answer_sha,
            "status":rec["status"],
            "actual_characters":rec["actual_characters"],
            "original_prose_sha256":rec["prose_sha256"],
            "automatic_repair_calls":0,
            "source_or_prior_student_text_in_prompt":False,
            "corpus_retrieval_or_human_prose_template":False,
            "independent_literary_judge_applied":False,
            "author_accepted":False,"WF_skill_improvement_proven":False,
        }
        result_sha=private_write(cas,encode(entry),
                    "WF104_CANDIDATE_METADATA_NOT_PRIVATE_R2")
        entry["candidate_receipt_cas_sha256"]=result_sha
        results.append(entry)
        if rec["prose"] is not None:
            completed.append(rec["prose"])
        publish({
            "status":"WF104_ONE_RAW_STUDENT_SCENE_R2_SEALED",
            "ordinal":idx,"scene_id":scene["id"],
            "self_idea":scene,
            "real_characters":rec["actual_characters"],
            "source_literal_prose_sha256":rec["prose_sha256"],
            "raw_response_sha256":answer_sha,
            "writer_status":rec["status"],
            "provider_requests_so_far":budget.calls_reserved,
            "previous_scenes_not_shown_to_model":True,
            "independent_literary_quality_judged":False,
        })
    repeated=reused_fragments(completed)
    manifest={
        "format":"wf.exam.v104.ten-self-scenes.completed",
        "run_id":RUN_ID,
        "precommit_cas_sha256":pre_sha,
        "self_chosen_plan_cas_sha256":plan_sha,
        "full_unmodified_model_reply_refs":raw_records,
        "candidate_receipts":results,
        "total_requests":budget.calls_reserved,
        "expected_max_requests":MAX_CALLS,
        "provider_usage":budget.public_receipt(),
        "conservative_tokens_held":held_budget,
        "human_or_external_judge_model_calls":0,
        "total_scenes_received":len(results),
        "prose_texts_valid_string_count":len(completed),
        "repeated_literal_text_flags":repeated,
        "all_10_scenes_semantically_distinct_proven":False,
        "copying_or_collage_proven":False,
        "literary_understanding_proven":False,
        "literary_quality_winner":"UNDETERMINED",
        "original_15_training_chapters_touched":0,
        "v97_v103_history_overwritten":False,
        "new_factjournal_or_canon_writes":0,
        "external_editor_or_critic_interference":False,
        "no_user_private_original_books_read":True,
        "finished_drafts_still_unaccepted":True,
    }
    result_raw=encode(manifest)
    need(len(result_raw)<MAX_RECEIPT_BYTES,
         "WF104_FINAL_EXAM_MANIFEST_LIMIT")
    msha=private_write(cas,result_raw,
                       "WF104_FINAL_MANIFEST_NOT_REMOTE_RECOVERABLE")
    publish({
        "status":"WF104_REAL_TEN_SELF_DIRECTED_STORIES_R2_SEALED",
        "run_precommit_sha256":pre_sha,
        "frozen_student_plan_sha256":plan_sha,
        "final_manifest_cas_sha256":msha,
        "provider":MODEL,
        "actual_paid_requests":budget.calls_reserved,
        "actual_reported_prompt_tokens":budget.prompt_tokens_reported,
        "actual_reported_completion_tokens":budget.completion_tokens_reported,
        "ten_original_response_receipts_saved":len(results)==10,
        "actual_prose_count":len(completed),
        "lengths":[d["actual_characters"] for d in results],
        "all_stories_independent_of_previous_raw_prose":True,
        "external_model_evaluators":0,
        "actual_original_generator_is_underlying_provider":True,
        "model_independent_WF_literary_mind_proven":False,
        "graded_by_trusted_reviewer":False,
        "skill_graduation":"LOCKED",
        "old_training_unchanged":True})
    return 0

if __name__=="__main__":
    publish({"status":"WF104_START_REAL_TEN_WF_SELF_SCENES",
             "planned_actual_provider_calls":MAX_CALLS,
             "no_paid_auto_retries":True,
             "only_inference_provider":MODEL,
             "explicitly_no_second_critic_model":True})
    try: rc=run()
    except Exception as exc:
        issue=str(exc)
        if not re.fullmatch(
            r"(?:WF104|WF_FLASH|WF_LEARN|WF_V79|WF_INDEX)_[A-Z0-9_]{1,140}",
            issue):
            issue="WF104_FAIL_CLOSED_UNCLASSIFIED_POSSIBLY_BILLED"
        publish({"status":"WF104_EXAM_PARTIAL_FAILED_NO_AUTO_REPEAT",
                 "error_code":issue,
                 "one_time_precommit_was_not_reset":True,
                 "no_user_original_books_used":True,
                 "no_literary_graduation":True,
                 "provider_may_have_billed_on_transport_error":True})
        rc=1
    publish({"status":"WF104_RUN_EXIT","exit_code":rc})
    raise SystemExit(rc)
