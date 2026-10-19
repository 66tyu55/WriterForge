"""V81 fresh reader-only audit of the pre-registered blind ablation.

Fetches each model reply and examiner rubric from immutable R2 content-
addressed blobs and independently recomputes exact evidence, category
labels and group deltas. Does not trust WF's self-report and cannot score
literary mastery from three toy questions.

A separate deployed Railway process has ONLY WF_API_TOKEN, no DeepSeek
key and no index/R2 writer token. No paid inference in this audit.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
import sys
import time
import types
from pathlib import Path

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
for secret in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
               "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(secret,None)
pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
BLIND_SUMMARY_SHA256="TO_BE_PINNED_AFTER_BLIND_TRIAL"

def emit(data):
    print(json.dumps(data,ensure_ascii=False,sort_keys=True),flush=True)

print("WF_V81_BLIND_TEST_INDEPENDENT_READER_START",flush=True)

def main():
    if not os.getenv("WF_API_TOKEN"):
        emit({"status":"WF_V81_BLIND_AUDIT_READER_MISSING"})
        return 1
    try:
        from writerforge.v79_provisional_r2_cas_journal import (
            WFProvisionalR2CASJournal)
        from writerforge.v81_frozen_blind_ablation import (
            CASES,frozen_sha,grade_case,decision_summary)
        from writerforge.r2_learn_journal import canonical
        if len(BLIND_SUMMARY_SHA256)!=64:
            raise ValueError("WF_V81_BLIND_AUDIT_FROZEN_SUMMARY_NOT_PINNED")
        reader=WFProvisionalR2CASJournal(endpoint=ENDPOINT,read_only=True)
        if reader.writer is not None:
            raise ValueError("WF_V81_BLIND_AUDIT_HAS_WRITER")
        raw=reader._get_content(BLIND_SUMMARY_SHA256)
        doc=json.loads(raw)
        if (doc.get("format")!="wf.exam.result.blind.ablation.v81" or
            doc.get("frozen_exam_sha256")!=frozen_sha() or
            doc.get("literary_level_promoted") is not False):
            raise ValueError("WF_V81_BLIND_AUDIT_SUMMARY_NOT_VALID")
        pairs=doc.get("cases")
        if not isinstance(pairs,list) or len(pairs)!=6:
            raise ValueError("WF_V81_BLIND_AUDIT_SIX_RESPONSES_MISSING")
        verified=[]
        for item in pairs:
            case=next((c for c in CASES
                       if c["id"]==item.get("case_id")),None)
            if case is None or item.get("arm") not in (
                    "without_experience","with_experience"):
                raise ValueError("WF_V81_BLIND_AUDIT_CASE_ID_CHANGED")
            event=json.loads(reader._get_content(
                item["response_event_sha256"]))
            if (event.get("format")!="wf.exam.response.blind.ablation.v81" or
                event.get("case_id")!=case["id"] or
                event.get("arm")!=item["arm"] or
                event.get("frozen_exam_sha256")!=frozen_sha() or
                event.get("literary_mastery_verified") is not False or
                event.get("output_sha256")!=
                 sha256(canonical(event["model_response"])).hexdigest()):
                raise ValueError("WF_V81_BLIND_AUDIT_RESPONSE_REPLACED")
            grade=grade_case(case,event["model_response"])
            if grade!=item["grade"] or grade!=event["examiner_rubric"]:
                raise ValueError("WF_V81_BLIND_AUDIT_RUBRIC_CHANGED_AFTER_RESPONSE")
            verified.append(item)
        recomputed=decision_summary(verified)
        if recomputed!=doc.get("examiner_deterministic_verdict"):
            raise ValueError("WF_V81_BLIND_AUDIT_DECISION_MATH_CHANGED")
        tokens=doc.get("model_usage",{})
        if tokens.get("reserved_requests")!=6 or (
            tokens.get("model")!="deepseek-flash"):
            raise ValueError("WF_V81_BLIND_AUDIT_USAGE_WRONG")
        emit({
           "status":"WF_V81_INDEPENDENT_FROZEN_ABLATION_R2_AUDIT_PASSED",
           "summary_cas_sha256":BLIND_SUMMARY_SHA256,
           "rechecked_model_responses":6,
           "frozen_case_sha256":frozen_sha(),
           "source_exact_quote_and_rubric_recomputed":True,
           "paired_results":recomputed,
           "usage_calls":tokens.get("reserved_requests"),
           "usage_prompt_tokens":tokens.get("prompt_tokens_reported"),
           "usage_completion_tokens":tokens.get("completion_tokens_reported"),
           "reader_only":True,
           "r2_writes":0,
           "DeepSeek_api_calls":0,
           "no_mastery_graduation":True,
           "tiny_ablation_not_proof_of_literary_skill":True,
        })
        return 0
    except Exception as err:
        code=str(err)
        if not code.startswith((
            "WF_V81_","WF_LEARN_","WF_V79_","WF_INDEX_"
        )):
            code="WF_V81_BLIND_AUDIT_UNKNOWN_FAILURE"
        emit({
           "status":"WF_V81_INDEPENDENT_BLIND_AUDIT_STOPPED",
           "error_code":code,"r2_writes":0,"model_calls":0,
           "literary_level_promoted":False,
        })
        return 1

result=main()
print("WF_V81_BLIND_READER_EXAM_EXIT="+str(result),flush=True)
time.sleep(7)
raise SystemExit(result)
