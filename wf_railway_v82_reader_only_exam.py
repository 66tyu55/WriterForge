"""V82 real independent R2 cold audit after completed chapters 7-10.

Runs in a NEW Railway Python process, removes all model and write secrets
before any WF import, and pins both final V82 CAS pointers from the genuine
training deployment b1596b80-43c9-49c8-8d00-a86d44f91102.

No API model request or R2 write; all original content remains inside
private R2 and the ephemeral Railway container; public output only hashes,
source coverage, pass A/B sequence and failed checks. Does not grade literary
quality or pretend provider billing has been independently reconciled.
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
for secret in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
               "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(secret,None)
pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
B00_SHA="c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4"
KEY_SHA="370400053cded15ca89e3232e7be84b28aa20ca70542150138bef6201dc7cb22"
SOURCE_SHA="0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd"
SOURCE_SIZE=4009069

PRIOR_BATCH="e28490de3f0b17875ed23418726a8b8692b3029c1501b30da314080f4edb0901"
PRIOR_JOURNAL="61a52125708a180b3305e28721d6e1797c0ab619df18a1bac7822988707a9c33"
PRIOR_EXPERIENCE="feee04808c6b14f84c16989d98b031937a897395f3d008c43e17b3449f9077e3"

V82_BATCH="d46ffec05927dfba3f2819089e76e79f720db2a2f3f6793b56965ac6413c177f"
V82_JOURNAL="3da56cc46115548c5198a65cb6124e3c03d9bdfdb1f0460950177735a99d1cb2"
V82_EXPERIENCE="ddbf86e87e3bf44900b4e5e4d8ffc2de99c9ed5d3c5aec98a69bfd8eb7cf2fe7"


def emit(value):
    print(json.dumps(value,sort_keys=True,ensure_ascii=False),flush=True)


print("WF_V82_INDEPENDENT_COLD_EXAM_START",flush=True)


def main():
    if not os.getenv("WF_API_TOKEN"):
        emit({"status":"WF_V82_EXAM_MISSING_R2_READER_TOKEN",
              "DeepSeek_calls":0,"R2_writes":0})
        return 1
    try:
        from writerforge.bulk_inbox import BulkCatalog
        from writerforge.private_reading_remote import WFPrivateReadingClient
        from writerforge.private_r2_sql_smoke import download_one_verified
        from writerforge.wf_batch_supervisor import frozen_preselection
        from writerforge.wf_self_learning_admission import _scan_document
        from writerforge.v79_provisional_r2_cas_journal import (
            WFProvisionalR2CASJournal,
        )
        from writerforge.v82_independent_exam import examine_v82

        examiner=WFProvisionalR2CASJournal(
            endpoint=ENDPOINT,read_only=True)
        restored=examiner.restore_anchored_suffix(
            final_checkpoint_sha=V82_JOURNAL,
            independently_verified_prior_sha=PRIOR_JOURNAL,
            first_new_chapter=11,
            last_new_chapter=15)
        emit(restored)
        if examiner.writer is not None or not examiner.read_only:
            raise ValueError("WF_V82_EXAM_READER_ROLE_HAS_WRITER")
        emit({
            "status":"WF_V82_R2_READER_ONLY_RECOVERED",
            "r2_journal_checkpoint_sha256":V82_JOURNAL,
            "restored_event_count":len(examiner.event_addresses),
            "model_or_writer_keys_available":False,
            "original_prose_logged":False,
        })
        with TemporaryDirectory(prefix="wf-v82-cold-audit-") as directory:
            root=Path(directory)
            catalog=BulkCatalog(root/"catalog.sqlite3")
            try:
                r2=WFPrivateReadingClient(endpoint=ENDPOINT,timeout=70)
                inventory=r2.inventory_to_catalog(catalog)
                if inventory.get("all_folders_complete") is not True:
                    raise ValueError("WF_V82_EXAM_INVENTORY_INCOMPLETE")
                shortlisted,freeze=frozen_preselection(catalog)
                if freeze["preselection_digest_sha256"]!=B00_SHA:
                    raise ValueError("WF_V82_EXAM_B00_SELECTION_CHANGED")
                original=shortlisted["仙侠"][0]
                key=original["object_key"]
                if (sha256(key.encode("utf8")).hexdigest()!=KEY_SHA or
                    original["size_bytes"]!=SOURCE_SIZE):
                    raise ValueError("WF_V82_EXAM_SELECTED_SOURCE_CHANGED")
                file=root/"original.txt"
                fetched=download_one_verified(r2,original,file)
                if (fetched["source_sha256"]!=SOURCE_SHA or
                    fetched["bytes"]!=SOURCE_SIZE):
                    raise ValueError("WF_V82_EXAM_SOURCE_BYTES_CHANGED")
                chapters,scan=_scan_document(file,"gb18030")
                if (len(chapters)<15 or
                    scan["boundary_rule_disagreements"]!=0 or
                    scan["duplicate_printed_numbers"]!=0 or
                    scan["printed_order_backward_or_equal_steps"]!=0):
                    raise ValueError("WF_V82_EXAM_CHAPTER_BOUNDARY_CHANGED")
                report=examine_v82(
                    reader=examiner,
                    original_key=key,source_sha=SOURCE_SHA,
                    source_path=file,source_chapters=chapters,
                    final_batch_pointer=V82_BATCH,
                    prior_v81_batch_pointer=PRIOR_BATCH,
                    prior_v81_journal_pointer=PRIOR_JOURNAL,
                    prior_chapter10_experience=PRIOR_EXPERIENCE,
                )
                if report["v81_last_experience_sha256"]!=V82_EXPERIENCE:
                    raise ValueError("WF_V82_EXAM_LAST_EXPERIENCE_CHANGED")
                emit(report)
                return 0
            finally:
                catalog.close()
    except Exception as e:
        # Never log exception repr or original prose. Only the exception
        # TYPE and sanitized Python function/line reference for diagnosis.
        import traceback
        stack=traceback.extract_tb(e.__traceback__)
        suspect=stack[-1] if stack else None
        emit({
            "status":"WF_V82_READONLY_AUDITOR_SAFE_DIAGNOSTIC",
            "exception_class":type(e).__name__,
            "code_location_file":Path(suspect.filename).name if suspect else None,
            "code_location_function":suspect.name if suspect else None,
            "code_location_line":suspect.lineno if suspect else None,
            "private_original_or_secret_emitted":False,
            "paid_model_calls":0,"r2_writes":0,
        })
        code=str(e)
        if not code.startswith((
            "WF_V82_","WF_V80_","WF_V79_","WF_LEARN_",
            "WF_INDEX_","WF_PRIVATE_","WF_V71_","WF_PREFIX_",
            "WF_CHARSET_","BULK_",
        )):
            code="WF_V82_EXAM_UNEXPECTED_FAILURE"
        emit({
           "status":"WF_V82_INDEPENDENT_AUDIT_FAILED",
           "error_code":code,
           "DeepSeek_model_calls":0,
           "R2_write_calls":0,
           "original_or_secrets_logged":False,
           "literary_level_promoted":False,
        })
        return 1


ret=main()
print("WF_V82_INDEPENDENT_COLD_EXAM_EXIT="+str(ret),flush=True)
time.sleep(6)
raise SystemExit(ret)
