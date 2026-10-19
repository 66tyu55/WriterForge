"""V81 independent reader-only real R2 exam after chapter7..12 training.

Completely fresh Railway process removes DeepSeek and writer environment
variables BEFORE importing WF modules. Uses original R2 source SHA and the
V81 final batch pointer to recheck all 61 source units, first-read hash
chain, A seal before B, evidence references, and actual chapter6 memory
link. No model calls, no R2 writes, no literary level promotion.
"""
from __future__ import annotations

import json
import os
import sys
import time
import types
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
for key in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
            "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(key,None)
module=types.ModuleType("writerforge")
module.__path__=[str(ROOT/"writerforge")]
module.__package__="writerforge"
sys.modules["writerforge"]=module

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
FROZEN_B00="c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4"
SOURCE_KEY_SHA="370400053cded15ca89e3232e7be84b28aa20ca70542150138bef6201dc7cb22"
SOURCE_SHA="0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd"
FINAL_V81_BATCH_SHA="TO_BE_PINNED_AFTER_REAL_TRAINING"

def emit(doc):
    print(json.dumps(doc,ensure_ascii=False,sort_keys=True),flush=True)

print("WF_V81_FRESH_READER_ONLY_CH7_TO12_EXAM_STARTED",flush=True)

def main():
    if not os.getenv("WF_API_TOKEN"):
        emit({"status":"WF_V81_EXAM_READER_KEY_MISSING"})
        return 1
    try:
        from writerforge.v79_provisional_r2_cas_journal import (
            WFProvisionalR2CASJournal)
        from writerforge.v81_independent_r2_exam import audit_next_chapters
        from writerforge.bulk_inbox import BulkCatalog
        from writerforge.private_reading_remote import WFPrivateReadingClient
        from writerforge.private_r2_sql_smoke import download_one_verified
        from writerforge.wf_batch_supervisor import frozen_preselection
        from writerforge.wf_self_learning_admission import _scan_document
        if len(FINAL_V81_BATCH_SHA)!=64:
            raise ValueError("WF_V81_EXAM_BATCH_SHA_NOT_PINNED")
        with TemporaryDirectory(prefix="wf-v81-reader-only-") as temp:
            root=Path(temp)
            catalog=BulkCatalog(root/"metadata.sqlite3")
            try:
                wf=WFPrivateReadingClient(endpoint=ENDPOINT,timeout=60)
                meta=wf.inventory_to_catalog(catalog)
                if meta["all_folders_complete"] is not True:
                    raise ValueError("WF_V81_EXAM_PRIVATE_INVENTORY_INCOMPLETE")
                choices,frozen=frozen_preselection(catalog)
                if frozen["preselection_digest_sha256"]!=FROZEN_B00:
                    raise ValueError("WF_V81_EXAM_SOURCE_COHORT_CHANGED")
                row=choices["仙侠"][0]
                key=row["object_key"]
                if sha256(key.encode()).hexdigest()!=SOURCE_KEY_SHA:
                    raise ValueError("WF_V81_EXAM_SOURCE_KEY_CHANGED")
                original=root/"original.txt"
                transferred=download_one_verified(wf,row,original)
                if transferred["source_sha256"]!=SOURCE_SHA:
                    raise ValueError("WF_V81_EXAM_ORIGINAL_SHA_CHANGED")
                chapters,source_summary=_scan_document(original,"gb18030")
                if (source_summary["boundary_rule_disagreements"]>0 or
                    source_summary["duplicate_printed_numbers"]>0):
                    raise ValueError("WF_V81_EXAM_CHAPTER_BOUNDARIES_NOT_STABLE")
                # Read final batch state before restoring large journal.
                reader=WFProvisionalR2CASJournal(
                    endpoint=ENDPOINT,read_only=True)
                if reader.writer is not None:
                    raise ValueError("WF_V81_EXAM_NOT_READ_ONLY")
                latest=json.loads(reader._get_content(FINAL_V81_BATCH_SHA))
                journal_sha=latest.get("journal_checkpoint_sha256")
                if not isinstance(journal_sha,str) or len(journal_sha)!=64:
                    raise ValueError("WF_V81_EXAM_JOURNAL_SHA_NOT_PINNED")
                reader.restore_pointer(journal_sha)
                verified=audit_next_chapters(
                    reader=reader,original_path=original,
                    source_key=key,source_sha=SOURCE_SHA,
                    chapters=chapters,
                    final_batch_sha=FINAL_V81_BATCH_SHA)
                emit(verified)
                return 0
            finally:
                catalog.close()
    except Exception as err:
        code=str(err)
        if not code.startswith((
            "WF_V81_","WF_V79_","WF_LEARN_","WF_INDEX_",
            "WF_PRIVATE_","WF_V71_","WF_PREFIX_","BULK_"
        )):
            code="WF_V81_EXAM_UNEXPECTED_FAILURE"
        emit({
            "status":"WF_V81_READER_ONLY_PROVENANCE_EXAM_STOPPED",
            "error_code":code,
            "reader_model_calls":0,"r2_writes":0,
            "private_prose_or_secret_logged":False,
            "literary_promotion":False,
        })
        return 1

code=main()
print("WF_V81_READER_ONLY_EXAM_EXIT="+str(code),flush=True)
time.sleep(7)
raise SystemExit(code)
