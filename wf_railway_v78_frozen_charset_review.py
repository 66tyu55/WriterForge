"""WF V78 one-shot real source encoding review, from frozen B00 cohort ONLY.

Reads first precommitted 仙侠 source from user's private R2 with existing
WF_API_TOKEN. No GPT intermediary, literary model, R2 writes or new API
key. Selection is signed by B00 2026-10-19 metadata SHA and original SHA.
Review metrics, never source content or private source title, are logged.
The result is NOT automatic admission to literary learning.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import sys
import time
import types

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
for key in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
            "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(key,None)
pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg

B00_LIST_SHA="c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4"
FROZEN_KEY_SHA="370400053cded15ca89e3232e7be84b28aa20ca70542150138bef6201dc7cb22"
FROZEN_FILE_SHA="0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd"
FROZEN_SOURCE_BYTES=4009069

def emit(obj):
    print(json.dumps(obj,ensure_ascii=False,sort_keys=True),flush=True)

print("WF_V78_FROZEN_FIRST_XIANXIA_CHARSET_AUDIT_START",flush=True)

def main():
    if not os.environ.get("WF_API_TOKEN"):
        emit({"status":"WF_V78_R2_READER_MISSING","calls":0})
        return 1
    try:
        from writerforge.bulk_inbox import BulkCatalog
        from writerforge.private_reading_remote import WFPrivateReadingClient
        from writerforge.private_r2_sql_smoke import download_one_verified
        from writerforge.wf_batch_supervisor import frozen_preselection
        from writerforge.wf_self_learning_admission import admit_source
        from writerforge.wf_charset_byte_review import byte_charset_audit
        with TemporaryDirectory(prefix="wf-v78-frozen-encoding-") as directory:
            scratch=Path(directory)
            cat=BulkCatalog(scratch/"metadata.sqlite3")
            try:
                wf=WFPrivateReadingClient(
                    endpoint="https://wf-r2-api.3227482831.workers.dev")
                inventory=wf.inventory_to_catalog(cat)
                if not inventory["all_folders_complete"]:
                    raise ValueError("WF_V78_R2_SCAN_INCOMPLETE")
                selected,freeze=frozen_preselection(cat)
                if freeze["preselection_digest_sha256"]!=B00_LIST_SHA:
                    raise ValueError("WF_V78_B00_COHORT_CHANGED")
                record=selected["仙侠"][0]
                hash_key=sha256(record["object_key"].encode("utf8")).hexdigest()
                if (hash_key!=FROZEN_KEY_SHA or
                    record["size_bytes"]!=FROZEN_SOURCE_BYTES):
                    raise ValueError("WF_V78_FROZEN_SOURCE_IDENTITY_CHANGED")
                emit({"status":"WF_V78_FROZEN_BOOK_IDENTIFIED_NO_LITERARY_JUDGEMENT",
                      "b00_selection_verified":True,
                      "source_key_sha256":hash_key,
                      "novel_content_logged":False})
                local=scratch/"source.txt"
                transfer=download_one_verified(wf,record,local)
                if transfer["source_sha256"]!=FROZEN_FILE_SHA:
                    raise ValueError("WF_V78_ORIGINAL_SOURCE_HASH_CHANGED")
                result=byte_charset_audit(
                    local,expected_source_sha256=FROZEN_FILE_SHA,
                    expected_size=FROZEN_SOURCE_BYTES,
                    expected_key_sha256=FROZEN_KEY_SHA)
                audit=admit_source(
                    local,original_key=record["object_key"],
                    verified_original_sha256=FROZEN_FILE_SHA,
                    downloaded_size=FROZEN_SOURCE_BYTES,
                    source_etag=record.get("etag"))
                scan=audit["document_scan"]
                emit({
                    "status":"WF_V78_WF_BYTE_AND_DOCUMENT_REVIEW_COMPLETED",
                    "b00_frozen_sha":B00_LIST_SHA,
                    "metadata_objects":inventory["total_objects"],
                    "byte_review":result,
                    "document_candidate_chapters":scan["chapters_detected"],
                    "legacy_heading_candidates":scan["legacy_sql_heading_candidates"],
                    "heading_rule_disagreements":scan["boundary_rule_disagreements"],
                    "printed_number_collisions":scan["duplicate_printed_numbers"],
                    "printed_number_order_backward_or_equal_steps":
                        scan["printed_order_backward_or_equal_steps"],
                    "preexisting_b00_literary_gate_unchanged":True,
                    "source_bytes_downloaded":transfer["bytes"],
                    "source_sha_verified":True,
                    "source_title_or_prose_logged":False,
                    "source_edition_human_verified":False,
                    "WF_literary_genre_judged":False,
                    "first_read_pass_a_started":False,
                    "literary_chapters_completed":0,
                    "r2_writes":0,
                    "paid_model_calls":0,
                    "source_tempfiles_deleted_on_exit":True,
                })
                return 0
            finally:
                cat.close()
    except Exception as error:
        code=str(error)
        if not code.startswith(("WF_V78_","WF_CHARSET_","WF_PRIVATE_",
                                "WF_ADMISSION_","WF_V71_","BULK_")):
            code="WF_V78_SOURCE_REVIEW_UNEXPECTED_FAILURE"
        emit({"status":"WF_V78_WF_SOURCE_REVIEW_FAILED",
              "code":code,"literary_chapters_completed":0,
              "model_calls":0,"r2_writes":0,
              "source_or_credentials_logged":False})
        return 1

exitcode=main()
print("WF_V78_FROZEN_CHARSET_REVIEW_EXIT="+str(exitcode),flush=True)
time.sleep(7)
raise SystemExit(exitcode)
