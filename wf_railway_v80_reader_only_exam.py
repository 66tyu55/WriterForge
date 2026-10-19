"""V80 fresh, independent R2 Reader-only examination of real 150k batch.

This is a NEW one-shot Railway container, distinct from the training
container. It strips DeepSeek and writer credentials before WF imports,
downloads only the same frozen original from R2, then uses immutable CAS
pointers to audit every previously signed chapter source unit, PASS A/B
relationship, and inter-chapter experience dependency. Never grades WF's
literary prose or promotes its V49 level.

FINAL_BATCH_POINTER is pinned only after training actually publishes one.
"""
from __future__ import annotations

import json,os,sys,time,types
from pathlib import Path
from hashlib import sha256
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
for name in (
    "DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN","DISCOVERY_API_KEY",
    "WF_LEARN_UPLOAD_TOKEN",
):
    os.environ.pop(name,None)
pkg=types.ModuleType("writerforge")
pkg.__package__="writerforge"
pkg.__path__=[str(ROOT/"writerforge")]
sys.modules["writerforge"]=pkg

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
B00_HASH="c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4"
KEY_SHA="370400053cded15ca89e3232e7be84b28aa20ca70542150138bef6201dc7cb22"
SOURCE_SHA="0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd"
SOURCE_BYTES=4009069
FINAL_BATCH_POINTER="f606f5216f82fd40a7893cfe8942e2454efe94b9f1389110bdc37f19f3a4f227"

def emit(value):
    print(json.dumps(value,ensure_ascii=False,sort_keys=True),flush=True)

print("WF_V80_FRESH_READER_ONLY_LARGE_BATCH_EXAM_STARTED",flush=True)

def main():
    if not os.getenv("WF_API_TOKEN"):
        emit({"status":"WF_V80_READER_CREDENTIAL_MISSING"})
        return 1
    try:
        from writerforge.bulk_inbox import BulkCatalog
        from writerforge.private_reading_remote import WFPrivateReadingClient
        from writerforge.private_r2_sql_smoke import download_one_verified
        from writerforge.wf_batch_supervisor import frozen_preselection
        from writerforge.wf_self_learning_admission import _scan_document
        from writerforge.v79_provisional_r2_cas_journal import (
            WFProvisionalR2CASJournal)
        from writerforge.v80_independent_exam import audit_extended_batch
        if len(FINAL_BATCH_POINTER)!=64:
            raise ValueError("WF_V80_AUDITOR_POINTER_NOT_PINNED")
        with TemporaryDirectory(prefix="wf-v80-independent-exam-") as tmp:
            scratch=Path(tmp)
            db=BulkCatalog(scratch/"inventory.sqlite3")
            try:
                client=WFPrivateReadingClient(endpoint=ENDPOINT)
                inventory=client.inventory_to_catalog(db)
                if not inventory["all_folders_complete"]:
                    raise ValueError("WF_V80_AUDITOR_INVENTORY_UNVERIFIED")
                chosen,frozen=frozen_preselection(db)
                if frozen["preselection_digest_sha256"]!=B00_HASH:
                    raise ValueError("WF_V80_AUDITOR_FROZEN_SOURCE_CHANGED")
                item=chosen["仙侠"][0]
                original=item["object_key"]
                if sha256(original.encode()).hexdigest()!=KEY_SHA:
                    raise ValueError("WF_V80_AUDITOR_SOURCE_KEY_CHANGED")
                local=scratch/"original.txt"
                copied=download_one_verified(client,item,local)
                if copied["bytes"]!=SOURCE_BYTES or copied["source_sha256"]!=SOURCE_SHA:
                    raise ValueError("WF_V80_AUDITOR_SOURCE_SHA_CHANGED")
                chapters,scan=_scan_document(local,"gb18030")
                if scan["boundary_rule_disagreements"] or scan["duplicate_printed_numbers"]:
                    raise ValueError("WF_V80_AUDITOR_CHAPTER_BOUNDARY_CHANGED")
                # Read ONLY a small batch-state object first to discover the
                # actual journal checkpoint, without touching any writer API.
                reader=WFProvisionalR2CASJournal(
                    endpoint=ENDPOINT,read_only=True)
                if reader.writer is not None:
                    raise ValueError("WF_V80_AUDITOR_WRITER_LEAK")
                info=json.loads(reader._get_content(FINAL_BATCH_POINTER))
                final_checkpoint=info.get("journal_checkpoint_sha256")
                if not isinstance(final_checkpoint,str) or len(final_checkpoint)!=64:
                    raise ValueError("WF_V80_AUDITOR_INVALID_JOURNAL_POINTER")
                reader.restore_pointer(final_checkpoint)
                proof=audit_extended_batch(
                    reader,source_path=local,
                    original_key=original,source_sha256=SOURCE_SHA,
                    chapters=chapters[:6],
                    last_batch_sha=FINAL_BATCH_POINTER)
                emit(proof)
                return 0
            finally:
                db.close()
    except Exception as exc:
        err=str(exc)
        if not err.startswith((
            "WF_V80_","WF_INDEX_","WF_V79_","WF_LEARN_",
            "WF_PRIVATE_","WF_V71_","WF_PREFIX_","BULK_",
        )):
            err="WF_V80_AUDITOR_UNEXPECTED_FAILURE"
        emit({"status":"WF_V80_INDEPENDENT_AUDIT_STOPPED",
              "error_code":err,
              "DeepSeek_calls":0,"R2_writes":0,
              "private_source_prose_printed":False,
              "literary_grade_promoted":False})
        return 1

code=main()
print("WF_V80_READER_ONLY_BATCH_EXAM_EXIT="+str(code),flush=True)
time.sleep(7)
raise SystemExit(code)
