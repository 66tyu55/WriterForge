"""V107 independent read-only forensic of FAILED V106 one-call precommit.

This examines ONLY exactly computable private CAS content-addressed objects,
never lists or retrieves the user's private novel corpus. NO MODEL, NO WRITES.
The original decoded JSON is an *orphan* unless its CAS SHA is separately
indexed or logged. Do not invent its missing pointer or "repair" V106.
"""
from __future__ import annotations
import json,os,re

for k in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
          "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(k,None)

from writerforge.v79_provisional_r2_cas_journal import WFProvisionalR2CASJournal
from writerforge.v104_self_scene_protocol import encode,digest
from wf_railway_v106_real_e_f_smoke_once import (
    ENDPOINT,EXAM,MODEL,ROLE,PLANNER_SYS,make_outline_request,freeze,
)

def need(ok,code):
    if not ok:raise ValueError(code)

def emit(record):
    print(json.dumps(record,sort_keys=True,ensure_ascii=False,
                     separators=(",",":")),flush=True)

def forensic():
    need(os.environ.get("WF_API_TOKEN") and
         not os.environ.get("DEEPSEEK_API_KEY") and
         not os.environ.get("WF_INDEX_UPLOAD_TOKEN"),
         "WF107_FOR_FORENSIC_READER_PERMISSIONS_INVALID")
    reader=WFProvisionalR2CASJournal(endpoint=ENDPOINT,read_only=True)
    need(reader.read_only and reader.writer is None,
         "WF107_FOR_READ_ONLY_VAULT_REQUIRED")
    frozen=encode(freeze())
    pre_sha=digest(frozen)
    existing=reader._get_content(pre_sha)
    need(existing==frozen and
         json.loads(existing).get("id")==EXAM,
         "WF107_FOR_ORIGINAL_PRECOMMIT_R2_NOT_VERIFIED")
    intent={
        "format":"wf.exam.v106.before-model-request",
        "precommit_sha256":pre_sha,
        "call_no":1,"stage":"frozen_shared_turn_outline",
        "arm":"both",
        "prompt_sha256":digest(make_outline_request().encode("utf8")),
        "system_sha256":digest(PLANNER_SYS.encode("utf8")),
        "max_output_tokens":1450,
        "role":ROLE,
        "no_auto_retry":True,
    }
    attempt_sha=digest(encode(intent))
    old=reader._get_content(attempt_sha)
    need(old==encode(intent),
         "WF107_FOR_ORIGINAL_FIRST_REQUEST_ATTEMPT_CHANGED")
    emit({
        "status":"WF107_V106_ORIGINAL_PRECOMMIT_AND_REQUEST_COLD_VERIFIED",
        "source_run":EXAM,
        "original_precommit_cas_sha256":pre_sha,
        "original_first_paid_request_intent_cas_sha256":attempt_sha,
        "known_first_paid_request_stage":"frozen_shared_turn_outline",
        "original_run_railway_error_code":"WF96_TURN_PLAN_FIELDS_ID_OR_CRAFT_INVALID",
        "first_provider_response_schema_was_rejected":True,
        "original_provider_response_cas_sha256":
            None,
        "reason_original_reply_cas_unindexable":
            "SHA_NOT_LOGGED_BEFORE_V96_EXCEPTION;NO_REVERSE_INDEX",
        "original_answer_not_forged_or_guessed":True,
        "original_V106_one_shot_not_replayed":True,
        "new_paid_model_calls":0,
        "R2_writes":0,
        "old_fifteen_chapters_modified":False,
    })
    return 0

if __name__=="__main__":
    emit({"status":"WF107_V106_READONLY_FOR_STARTED",
          "new_model_calls":0,"R2_writes":0})
    try:result=forensic()
    except Exception as exc:
        code=str(exc)
        if not re.fullmatch(r"(?:WF107|WF106|WF_V79|WF_INDEX)_[A-Z0-9_]{1,160}",code):
            code="WF107_FOR_FORENSIC_FAILED_CLOSED"
        emit({"status":"WF107_V106_FORENSIC_PAUSED",
              "reason_code":code,
              "new_paid_model_calls":0,"R2_writes":0})
        result=1
    emit({"status":"WF107_V106_READONLY_FORENSIC_EXIT","code":result})
    raise SystemExit(result)
