"""V78 fresh independent R2 READER-ONLY examiner for the ONE B01 trial.

Starts as a separate Railway deployment after B01; removes writer and
DeepSeek credentials from the process, reads one original source by freeze,
reconstructs three opening unit SHA256s, then checks each committed R2
first-read event, seal, and analysis unit source against those hashes.

Never calls a model, never alters original/index/study R2, never prints
original prose. Even when all 3 units agree, this is NOT a complete chapter,
literary mastery, or independent human-quality test.
"""
from __future__ import annotations

import json
import os
import sys
import time
import types
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
for secret in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
               "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(secret,None)
pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg

WORKER="https://wf-r2-api.3227482831.workers.dev"
FROZEN_SELECTION="c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4"
ORIGINAL_KEY_HASH="370400053cded15ca89e3232e7be84b28aa20ca70542150138bef6201dc7cb22"
ORIGINAL_SHA="0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd"
ORIGINAL_BYTES=4009069

def emit(x):
    print(json.dumps(x,ensure_ascii=False,sort_keys=True),flush=True)

print("WF_V79_PROVISIONAL_CAS_COLD_EXAM_STARTED",flush=True)

def main():
    if not os.environ.get("WF_API_TOKEN"):
        emit({"status":"WF_B01_EXAM_SOURCE_READER_MISSING"})
        return 1
    try:
        from writerforge.v79_provisional_r2_cas_journal import WFProvisionalR2CASJournal
        from writerforge.bulk_inbox import BulkCatalog
        from writerforge.private_reading_remote import WFPrivateReadingClient
        from writerforge.private_r2_sql_smoke import download_one_verified
        from writerforge.wf_batch_supervisor import (
            frozen_preselection,independently_recheck_r2_events,
            independent_claim_gate,
        )
        from writerforge.wf_b01_prefix_prepare import review_first_chapter_windows
        examiner=WFProvisionalR2CASJournal(
            endpoint=WORKER,read_only=True,
            checkpoint_sha="b7ace511e422c8973a35c0cc4d75229d0c11c7ddcefe4db97eda6b6098bc1210")
        if examiner.writer is not None:
            raise ValueError("WF_B01_EXAM_WRITER_PERMISSION_PRESENT")
        with TemporaryDirectory(prefix="wf-v78-b01-exam-") as tmp:
            root=Path(tmp)
            catalog=BulkCatalog(root/"metadata.sqlite3")
            try:
                wf=WFPrivateReadingClient(endpoint=WORKER)
                stats=wf.inventory_to_catalog(catalog)
                if stats["all_folders_complete"] is not True:
                    raise ValueError("WF_B01_EXAM_R2_INVENTORY_INCOMPLETE")
                selection,locked=frozen_preselection(catalog)
                if locked["preselection_digest_sha256"]!=FROZEN_SELECTION:
                    raise ValueError("WF_B01_EXAM_B00_SELECTION_CHANGED")
                row=selection["仙侠"][0]
                source_key=row["object_key"]
                if sha256(source_key.encode("utf-8")).hexdigest()!=ORIGINAL_KEY_HASH:
                    raise ValueError("WF_B01_EXAM_PRIVATE_KEY_CHANGED")
                original=root/"original.txt"
                data=download_one_verified(wf,row,original)
                if data["source_sha256"]!=ORIGINAL_SHA:
                    raise ValueError("WF_B01_EXAM_ORIGINAL_SHA_CHANGED")
                windows,receipt=review_first_chapter_windows(
                    original,source_sha256=ORIGINAL_SHA,
                    source_bytes=ORIGINAL_BYTES,
                    source_key_sha256=ORIGINAL_KEY_HASH,
                    unit_count=3)
                audited=independently_recheck_r2_events(
                    reader=examiner,original_key=source_key,
                    original_sha256=ORIGINAL_SHA,
                    chapter=1,
                    chapter_body_sha256=receipt["chapter_body_sha256"],
                    source_unit_hashes=receipt["trial_unit_sha256"])
                assessment=independent_claim_gate(
                    registered_source_sha=ORIGINAL_SHA,
                    self_report={
                        "source_sha256":ORIGINAL_SHA,
                        "claims_complete_chapter":False,
                        "claims_mastery":False,
                        "literary_grade_raised":False,
                    },
                    reader_receipts=audited)
                if assessment["verdict"]!="NO_COMPLETION_CLAIM":
                    raise ValueError("WF_B01_EXAM_PARTIAL_TRIAL_GATE_CHANGED")
                emit({
                   "status":"WF_V79_R2_CAS_PASS_A_B_FRESH_PROCESS_VERIFIED",
                   "evidence":audited.public_receipt(),
                   "three_original_source_unit_shas_verified":True,
                   "book_only_prior_B00_sha":FROZEN_SELECTION,
                   "pass_a_before_pass_b_remote_chain_verified":True,
                   "full_chapter_read":False,
                   "literary_mastery_verified":False,
                   "assessor_is_reader_only":True,
                   "model_calls":0,
                   "r2_writes":0,
                   "private_source_prose_or_key_logged":False,
                   "fresh_process_does_not_rely_on_training_tempfiles":True,
                   "provisional_r2_cas_checkpoint_sha256":"b7ace511e422c8973a35c0cc4d75229d0c11c7ddcefe4db97eda6b6098bc1210",
                   "native_learn_namespace_deployed":False,
                   "checkpoint_event_count":len(examiner.event_addresses),
                   "literary_model_self_reports_not_independent_quality_proof":True,
                })
                return 0
            finally:
                catalog.close()
    except Exception as exc:
        code=str(exc)
        if not code.startswith((
                "WF_B01_","WF_SUPERVISOR_","WF_PRIVATE_",
                "WF_LEARN_","WF_PREFIX_","WF_CHARSET_",
                "WF_V71_","WF_ADMISSION_","BULK_")):
            code="WF_B01_EXAM_UNEXPECTED_ERROR"
        emit({"status":"WF_B01_INDEPENDENT_R2_AUDIT_FAILED",
              "error_code":code,
              "literary_promotion":False,
              "r2_writes":0,"model_calls":0,
              "source_content_logged":False})
        return 1

status=main()
print("WF_V79_COLD_CAS_EXAM_EXIT="+str(status),flush=True)
time.sleep(6)
raise SystemExit(status)
