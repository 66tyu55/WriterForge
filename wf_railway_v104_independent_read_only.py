"""V104 independent cold reader: TEN ORIGINAL SCENES with no LLM and no write.

Private CAS manifest is injected as the one literal SHA in the *separate*
one-time Railway reader service. Refuses unrelated user private novels.
Each model reply and proposal is verified against original signed run IDs.
The ten new model-created snippets are requested for user inspection, so
this opt-in reader prints their full original prose without modifications.
"""
from __future__ import annotations
import json,os,re
from writerforge.v79_provisional_r2_cas_journal import WFProvisionalR2CASJournal
from writerforge.v104_self_scene_protocol import (
    RUN_ID,MODEL,DRAFT_REQUESTS,encode,digest,
    check_plan,record_prose,reused_fragments,V104ExamError,
)

for secret in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
               "DISCOVERY_API_KEY","WF_LEARN_UPLOAD_TOKEN"):
    os.environ.pop(secret,None)

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"

def need(x,code):
    if not x:raise V104ExamError(code)

def emit(o):
    print(json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(",",":")),flush=True)

def read(cas,ptr):
    need(type(ptr) is str and re.fullmatch(r"[0-9a-f]{64}",ptr) is not None,
         "WF104_READER_CAS_POINTER_INVALID")
    blob=cas._get_content(ptr)
    need(digest(blob)==ptr,"WF104_READER_CAS_REMOTE_BYTES_CHANGED")
    try:return json.loads(blob.decode("utf8","strict"))
    except (UnicodeError,ValueError):
        raise V104ExamError("WF104_READER_CAS_NOT_JSON") from None

def cold_read():
    need(os.environ.get("WF_API_TOKEN") and
         not os.environ.get("DEEPSEEK_API_KEY") and
         not os.environ.get("WF_INDEX_UPLOAD_TOKEN"),
         "WF104_READER_NOT_READ_ONLY")
    ptr=os.environ.get("WF_V104_MANIFEST_CAS_SHA256")
    cas=WFProvisionalR2CASJournal(endpoint=ENDPOINT,read_only=True)
    need(cas.read_only is True and cas.writer is None,
         "WF104_READER_WOULD_HAVE_WRITER_ROLE")
    meta=read(cas,ptr)
    need(meta.get("format")=="wf.exam.v104.ten-self-scenes.completed"
         and meta.get("run_id")==RUN_ID
         and meta.get("total_requests")==11
         and meta.get("total_scenes_received")==10
         and meta.get("external_editor_or_critic_interference") is False
         and meta.get("no_user_private_original_books_read") is True
         and meta.get("new_factjournal_or_canon_writes")==0
         and meta.get("literary_understanding_proven") is False
         and meta.get("finished_drafts_still_unaccepted") is True,
         "WF104_READER_MANIFEST_WRONG_OR_UNSAFE")
    pre=read(cas,meta["precommit_cas_sha256"])
    need(pre.get("run_id")==RUN_ID
         and pre.get("max_calls")==11
         and pre.get("only_inference_executor")=="WF_REGISTERED_DEEPSEEK_FLASH"
         and pre.get("external_judging_models")==0
         and pre.get("assistant_written_plot_answers")==0,
         "WF104_READER_ORIGINAL_PRECOMMIT_CHANGED")
    planned=read(cas,meta["self_chosen_plan_cas_sha256"])
    need(planned["format"]=="wf.exam.v104.locked-self-chosen-premises"
         and planned["run_precommit_sha256"]==meta["precommit_cas_sha256"]
         and len(planned["all_scenes"])==10,
         "WF104_READER_SCENES_NOT_ACTUALLY_LOCKED")
    p_raw=read(cas,planned["planner_raw_response_cas_sha256"])
    need(p_raw["format"]=="wf.exam.v104.raw-one-model-answer" and
         p_raw["parent_precommit_sha256"]==meta["precommit_cas_sha256"] and
         p_raw["call_identity"]["stage"]=="self_premises" and
         p_raw["call_identity"]["slot"]==0,
         "WF104_READER_PREMISE_ANSWER_NOT_ORIGINAL")
    scenes,diff=check_plan(p_raw["answer_unmodified"])
    need(list(scenes)==list(planned["all_scenes"]),
         "WF104_READER_PLAN_MODIFIED_AFTER_PROVIDER")
    responses=meta["full_unmodified_model_reply_refs"]
    need(type(responses) is list and len(responses)==11 and
         [x["slot"] for x in responses]==list(range(11)) and
         len(meta["candidate_receipts"])==10,
         "WF104_READER_11_REPLY_CHAIN_INVALID")
    need(responses[0]["raw_cas_sha256"]==
         planned["planner_raw_response_cas_sha256"],
         "WF104_READER_PLANNER_REPLY_WRONG")
    texts=[]
    for i in range(1,11):
        scene=scenes[i-1]
        a=responses[i]
        need(a["slot"]==i and a["stage"]=="self_prose",
             "WF104_READER_SLOT_REQUEST_CHANGED")
        obj=read(cas,a["raw_cas_sha256"])
        need(obj["format"]=="wf.exam.v104.raw-one-model-answer"
             and obj["parent_precommit_sha256"]==meta["precommit_cas_sha256"]
             and obj["call_identity"]["stage"]=="self_prose"
             and obj["call_identity"]["slot"]==i
             and obj["call_identity"]["role"]=="self_scene_writing"
             and obj["call_identity"]["model"]==MODEL,
             "WF104_READER_MODEL_REPLY_IDENTITY_INVALID")
        need(digest(encode(obj["answer_unmodified"]))==
             a["actual_response_sha256"],
             "WF104_READER_UNMODIFIED_SOURCE_SHA_CHANGED")
        parsed=record_prose(obj["answer_unmodified"])
        index=meta["candidate_receipts"][i-1]
        need(index["ordinal"]==i and index["scene_id"]==scene["id"]
             and index["raw_model_response_cas_sha256"]==a["raw_cas_sha256"]
             and index["original_prose_sha256"]==parsed["prose_sha256"]
             and index["status"]==parsed["status"]
             and index["author_accepted"] is False,
             "WF104_READER_STORY_ORIGINAL_PROSE_RECEIPT_MISMATCH")
        raw_receipt=read(cas,index["candidate_receipt_cas_sha256"])
        need(raw_receipt["ordinal"]==i and
             raw_receipt["original_prose_sha256"]==parsed["prose_sha256"],
             "WF104_READER_RECEIPT_SHA_CHANGED")
        prose=parsed["prose"]
        if prose is not None:
            texts.append(prose)
        emit({
            "status":"WF104_INDEPENDENT_R2_ORIGINAL_SELF_SCENE",
            "ordinal":i,"scene_id":scene["id"],
            "self_planned_premise":scene,
            "exact_actual_characters":parsed["actual_characters"],
            "original_prose_sha256":parsed["prose_sha256"],
            "raw_prose_without_edits":prose,
            "prose_status":parsed["status"],
            "original_provider_is_not_WF_weights":True,
            "literary_judgement":"NOT_YET_ASSESSED",
            "no_real_human_eval_of_this_scene":True,
        })
    duplicates=reused_fragments(texts)
    emit({
        "status":"WF104_INDEPENDENT_R2_ALL_TEN_RAW_SCENES_VERIFIED",
        "manifest_cas_sha256":ptr,
        "original_premises_sha256":meta["self_chosen_plan_cas_sha256"],
        "actual_provider_calls":meta["total_requests"],
        "actual_model_reported_input_tokens":meta["provider_usage"]["prompt_tokens_reported"],
        "actual_model_reported_output_tokens":meta["provider_usage"]["completion_tokens_reported"],
        "all_ten_original_model_replies_exact":True,
        "fiction_char_lengths":[r["actual_characters"]
                                for r in meta["candidate_receipts"]],
        "number_of_valid_prose_strings":len(texts),
        "literal_15_character_overlap_pairs":duplicates,
        "model_calls_by_this_reader":0,
        "private_R2_mutations":0,
        "original_story_texts_human_grade":"UNDETERMINED",
        "WF_independent_model_weights":False,
        "old_training_15_chapters_unchanged":True,
    })
    return 0

if __name__=="__main__":
    emit({"status":"WF104_ONLY_READ_TEN_SCENES_START",
          "new_external_model_calls":0,"external_judge":False})
    try:rc=cold_read()
    except Exception as exc:
        message=str(exc)
        if not re.fullmatch(r"(?:WF104|WF_V79|WF_INDEX|WF_LEARN)_[A-Z0-9_]{1,170}",message):
            message="WF104_READONLY_RESTORE_FAIL_CLOSED"
        emit({"status":"WF104_ONLY_READER_PAUSED",
              "reason_code":message,"external_model_calls":0,
              "private_corpus_prose_not_exposed":True})
        rc=1
    emit({"status":"WF104_READER_EXIT","exit_code":rc})
    raise SystemExit(rc)
