"""V115 one paid, unique, SOURCE EVENT EXTRACTION using actual MIT Novel Studio.

Source is original 964-char WF DeepSeek first scene preserved at V114B.
No new prose generated. Same connected DeepSeekFlashModel proposes unaccepted
events with direct text quotations. Original MIT parser and reducer validate
them, with state scoped only to author_plan, never FactJournal KNOWN.

Every provider HTTP byte/JSON and original event proposal is sealed to an
independent V115 R2 immutable CAS. No other models, no retries, no Railway.
"""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import json,os,re,shutil,subprocess
from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget
from writerforge.v104_self_scene_protocol import encode,digest
from experiments.v114_github_r2_cas import GitHubS3CAS as OldCAS
from experiments.v115_novel_studio_r2_cas import GitHubS3CAS as NewCAS

EXAM="WF-V115-EXTRACT-NOVEL-STUDIO-FROM-REAL-WF-20261021"
SOURCE_CAS="c49198a29fed64d8883393b3a2168e37011a09de32a9899986edfc148a499e88"
SOURCE_SHA="c5146b829348ea12724290550ab8d4b4d959f2c1aaa41459c38bdeef757ad166"
OLD_V114B_PRECOMMIT="c48ec7b4d20c346567f4639c51c987c0ab00cd131b75ddcbe9b82a631441a539"
UPSTREAM_COMMIT="b585a9ca4ce474fe2471bf3bb7f8c284c6e4104a"
MODEL="deepseek-flash"
ROLE="self_scene_writing"
MAX_CALLS=1
MAX_OUTPUT=2400
MAX_TOTAL=150000
BRIDGE=Path(__file__).resolve().parent/"v115_novel_studio"/"bridge.mjs"
MAX_WIRE=230000

class OriginalReadOnlyCAS(OldCAS):
    def _put_content(self,*args,**kwargs):
        raise RuntimeError("WF115_OLD_ORIGINAL_WRITE_FORBIDDEN")

def need(ok,code):
    if not ok:raise ValueError(code)
def emit(o):
    print(json.dumps(o,ensure_ascii=False,sort_keys=True,
                     separators=(",",":"),allow_nan=False),flush=True)
def exact(cas,ptr):
    need(type(ptr) is str and re.fullmatch(r"[0-9a-f]{64}",ptr) is not None,
         "WF115_UNTRUSTED_CAS_POINTER")
    raw=cas._get_content(ptr)
    need(digest(raw)==ptr,"WF115_PRIVATE_R2_CAS_BYTES_CHANGED")
    return raw
def newstore(cas,b,err):
    need(type(b) is bytes and 0<len(b)<=260000,"WF115_CAS_OBJECT_TOO_LARGE")
    ptr,_=cas._put_content(b)
    need(exact(cas,ptr)==b,err)
    return ptr
def node_call(payload):
    need(BRIDGE.is_file() and shutil.which("node") is not None,
         "WF115_PINNED_EXTRACTION_RUNTIME_NOT_INSTALLED")
    data=encode(payload)
    need(len(data)<=170000,"WF115_NODE_INPUT_TOO_LARGE")
    try:
        r=subprocess.run([shutil.which("node"),str(BRIDGE)],input=data,
                         capture_output=True,timeout=15,check=False)
    except (OSError,subprocess.TimeoutExpired):
        raise ValueError("WF115_ORIGINAL_NODE_EXTRACTOR_TIMEOUT") from None
    need(r.returncode==0 and 0<len(r.stdout)<=220000,
         "WF115_ORIGINAL_NODE_EXTRACTOR_REFUSED_INPUT")
    try:return json.loads(r.stdout.decode("utf8","strict"))
    except (UnicodeError,ValueError):
        raise ValueError("WF115_NODE_RETURNED_NON_JSON") from None

def precommit():
    return {
        "format":"wf.exam.v115.one-source-extraction.preregister",
        "exam":EXAM,
        "old_original_WF_model_source_cas_sha256":SOURCE_CAS,
        "old_original_WF_prose_sha256":SOURCE_SHA,
        "old_model_attempts_replayed":False,
        "original_V114B_precommit":OLD_V114B_PRECOMMIT,
        "only_current_user_registered_provider":MODEL,
        "only_one_model_request":True,
        "max_model_calls":MAX_CALLS,
        "max_reserved_completion_tokens":MAX_OUTPUT,
        "conservative_exact_total_token_budget":MAX_TOTAL,
        "MIT_extractor_temporal_upstream_commit":UPSTREAM_COMMIT,
        "all_pinned_extractor_sources_original":True,
        "no_editor_model_or_human_supplied_plot_answers":True,
        "source_text_contains_new_made_up_noun_to_discover":True,
        "real_source_includes_arm_injury_and_fruit_handoff":True,
        "state_scoped_to_author_plan_only":True,
        "raw_provider_wire_private_CAS_before_JSON":True,
        "raw_decoded_answer_private_CAS_before_event_validation":True,
        "validate_event_source_quotes_and_before_values":True,
        "no_auto_retry_or_model_correction":True,
        "experiment_does_not_rewrite_old_original_prose":True,
        "literary_continuity_improvement_unproven":True,
        "author_acceptance_and_promotion":"LOCKED",
        "old_V49_failure_and_real15chapters_unchanged":True,
    }

def run():
    need(all(os.environ.get(k) for k in (
        "DEEPSEEK_API_KEY","WRITERFORGE_R2_ACCOUNT_ID",
        "WRITERFORGE_R2_BUCKET","WRITERFORGE_R2_ACCESS_KEY_ID",
        "WRITERFORGE_R2_SECRET_ACCESS_KEY")),
        "WF115_EXISTING_GITHUB_SECRET_NOT_SET")
    old=OriginalReadOnlyCAS()
    original=json.loads(exact(old,SOURCE_CAS).decode("utf8","strict"))
    need(original.get("format")=="wf.exam.v114.one-model-decoded-original" and
         original.get("source_precommit_sha256")==OLD_V114B_PRECOMMIT and
         type(original.get("student_unmodified_answer",{}).get("prose")) is str,
         "WF115_OLD_REAL_SOURCE_NOT_GENUINE")
    prose=original["student_unmodified_answer"]["prose"]
    need(len(prose)==964 and digest(prose.encode("utf8"))==SOURCE_SHA,
         "WF115_OLD_REAL_WF_PROSE_HASH_OR_LENGTH_CHANGED")
    prompt=node_call({"mode":"prompt","source_prose":prose,"prior_state":{}})
    need(prompt.get("source_sha256")==SOURCE_SHA and
         prompt.get("coverage",{}).get("complete") is True and
         prompt.get("coverage",{}).get("truncated") is False and
         "JSON" in prompt["system"],
         "WF115_UPSTREAM_ORIGINAL_PROMPT_DOES_NOT_COVER_SOURCE")
    cas=NewCAS()
    frozen=encode(precommit())
    pre,created=cas._put_content(frozen)
    need(created is True and pre==digest(frozen) and
         exact(cas,pre)==frozen,
         "WF115_EXPERIMENT_ALREADY_RESERVED_NEVER_REBILL")
    request={
        "format":"wf.exam.v115.one-actual-WF-memory-extraction-request",
        "precommit_sha256":pre,
        "system_prompt_sha256":digest(prompt["system"].encode("utf8")),
        "user_prompt_sha256":digest(prompt["user"].encode("utf8")),
        "source_sha256":SOURCE_SHA,
        "max_output_tokens":MAX_OUTPUT,
        "role":ROLE,"model":MODEL,
        "no_other_models":True,"no_retry":True,
    }
    raw_request=encode(request)
    ptr,request_is_new=cas._put_content(raw_request)
    need(request_is_new and exact(cas,ptr)==raw_request,
         "WF115_PAID_REQUEST_ALREADY_RESERVED")
    emit({"status":"WF115_EXTRACTOR_REQUEST_INTENT_PRIVATE_CAS_RESERVED",
          "experiment_cas_sha256":pre,"attempt_cas_sha256":ptr,
          "model_calls_so_far":0})
    budget=FlashBudget(max_calls=1,max_reserved_output_tokens=MAX_OUTPUT,
                       max_total_tokens=MAX_TOTAL)
    wire_hash={"value":None}
    def wire(content):
        need(wire_hash["value"] is None and type(content) is bytes and
             0<len(content)<=MAX_WIRE,
             "WF115_PROVIDER_WIRE_NOT_SINGLE_OR_SIZE")
        addr=newstore(cas,content,"WF115_HTTP_WIRE_NOT_CAS_VERIFIED")
        wire_hash["value"]=addr
        emit({"status":"WF115_ACTUAL_PROVIDER_WIRE_SAVED_BEFORE_JSON",
              "raw_response_cas_sha256":addr,
              "original_prose_not_in_log":True})
    model=DeepSeekFlashModel(budget=budget,timeout_seconds=120,
                            on_response_wire=wire)
    raw_answer=None
    decoded_sha=None
    result=None
    try:
        raw_answer=model.ask_json(role=ROLE,system=prompt["system"],
                                  user=prompt["user"],max_tokens=MAX_OUTPUT)
        need(wire_hash["value"] is not None,
             "WF115_PROVIDER_SUCCESS_NO_WIRE")
        decoded_sha=newstore(cas,encode({
            "format":"wf.exam.v115.original-unmodified-model-extraction",
            "precommit_sha256":pre,"request_cas_sha256":ptr,
            "wire_cas_sha256":wire_hash["value"],
            "source_prose_sha256":SOURCE_SHA,
            "original_model_JSON":raw_answer,
            "not_human_or_software_repaired":True,
        }),"WF115_ORIGINAL_EXTRACTION_JSON_NOT_CAS_VERIFIED")
        emit({"status":"WF115_RAW_EXTRACTION_JSON_SAVED_BEFORE_NOVEL_STUDIO_VALIDATION",
              "decoded_cas_sha256":decoded_sha})
        evaluation=node_call({"mode":"validate","source_prose":prose,
                              "prior_state":{},"model_output":raw_answer})
        need(evaluation.get("source_sha256")==SOURCE_SHA
             and evaluation.get("factjournal_canon_writes")==0
             and evaluation.get("independently_proven_literary_truth") is False,
             "WF115_UPSTREAM_REDUCER_NOT_ISOLATED")
        report_sha=newstore(cas,encode(evaluation),
                            "WF115_NATIVE_EXTRACTION_REDUCER_RESULT_NOT_SAVED")
        docs=json.dumps(evaluation["candidate_state"],ensure_ascii=False)
        items=[z.get("entity_ids",[]) for z in evaluation["anchored_candidate_events"]]
        fruit=any("火髓果" in item for pair in items for item in pair)
        injury="右臂" in docs or "右臂" in json.dumps(
            evaluation["anchored_candidate_events"],ensure_ascii=False)
        result={
            "status":"SOURCE_EVENT_EXTRACTION_COMPLETED_CANDIDATE_ONLY",
            "original_model_answer_cas_sha256":decoded_sha,
            "original_novel_studio_result_cas_sha256":report_sha,
            "proposed_events":evaluation["raw_proposal_event_count"],
            "anchored_events":evaluation["source_anchored_candidate_event_count"],
            "unresolved_count":len(evaluation["unresolved"]),
            "novel_specific_fire_fruit_anchored_candidate":fruit,
            "right_arm_injury_anchored_candidate":injury,
            "semantic_literary_memory_proven":False,
            "need_authored_story_next_turn_to_test_transfer":True,
        }
    except Exception as ex:
        reason=str(ex)
        if not re.fullmatch(r"(?:WF115|WF_FLASH)_[A-Z0-9_]{1,160}",reason):
            reason="WF115_ORIGINAL_EXTRACTION_OR_NODE_FAILED"
        result={
            "status":"EXTRACTION_FAILED_PRESERVE_ACTUAL_SOURCE",
            "code":reason,
            "original_provider_wire_cas_sha256":wire_hash["value"],
            "model_answer_decoded_cas_sha256":decoded_sha,
            "no_retry":True,
        }
    receipt={
        "format":"wf.exam.v115.real-novel-studio-extraction-final",
        "precommit_sha256":pre,
        "old_original_WF_prose_cas_sha256":SOURCE_CAS,
        "same_original_WF_short_story_sha256":SOURCE_SHA,
        "model_calls_reserved":budget.calls_reserved,
        "provider_usage":budget.public_receipt(),
        "source_validation_with_original_MIT_upstream":True,
        "provider_wire_cas_sha256":wire_hash["value"],
        "decoded_original_cas_sha256":decoded_sha,
        "result":result,
        "official_model_unmodified":True,
        "literary_continuity_quality_verified":False,
        "user_original_novels_not_read":True,
        "historical_failure_records_unchanged":True,
        "no_new_WF_training_chapter":True,
    }
    manifest=newstore(cas,encode(receipt),"WF115_MANIFEST_R2_NOT_COLD_VERIFIED")
    emit({"status":"WF115_REAL_NOVEL_STUDIO_EXTRACTION_SEALED",
          "precommit_cas_sha256":pre,
          "manifest_cas_sha256":manifest,
          "request_count":budget.calls_reserved,
          "reported_input_tokens":budget.prompt_tokens_reported,
          "reported_output_tokens":budget.completion_tokens_reported,
          "result":result,
          "no_second_model":True,"old_WF_original_text_untouched":True})
    return 0

if __name__=="__main__":
    emit({"status":"WF115_ONE_SOURCE_EXTRACT_EXAM_START",
          "max_new_model_calls":MAX_CALLS,
          "source_real_prose_existing":True,
          "no_regeneration_of_older_models":True})
    try:rc=run()
    except Exception as e:
        why=str(e)
        if not re.fullmatch(r"(?:WF115|WF_FLASH)_[A-Z0-9_]{1,150}",why):
            why="WF115_UNCLASSIFIED_STOP_NO_RETRY"
        emit({"status":"WF115_ABORT_NO_RETRY","reason_code":why,
              "may_have_sent_model_request":True})
        rc=1
    raise SystemExit(rc)
