"""V81 real independent R2 cold audit after completed chapters 7-10.

Runs in a NEW Railway Python process, removes all model and write secrets
before any WF import, and pins both final V81 CAS pointers from the genuine
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

PRIOR_BATCH="f606f5216f82fd40a7893cfe8942e2454efe94b9f1389110bdc37f19f3a4f227"
PRIOR_JOURNAL="0b24a62a697b11e140477225728375fc406cd035fe921ad8ca5476b48a674240"
PRIOR_EXPERIENCE="1d0ee736b199f9af4c04543ba4d7d620ca8e1565b31b25ca673bef610c2b2d9d"

V81_BATCH="e28490de3f0b17875ed23418726a8b8692b3029c1501b30da314080f4edb0901"
V81_JOURNAL="61a52125708a180b3305e28721d6e1797c0ab619df18a1bac7822988707a9c33"
V81_EXPERIENCE="feee04808c6b14f84c16989d98b031937a897395f3d008c43e17b3449f9077e3"


def emit(value):
    print(json.dumps(value,sort_keys=True,ensure_ascii=False),flush=True)


print("WF_V81_INDEPENDENT_COLD_EXAM_START",flush=True)


def main():
    if not os.getenv("WF_API_TOKEN"):
        emit({"status":"WF_V81_EXAM_MISSING_R2_READER_TOKEN",
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
        from writerforge.v81_independent_exam import examine_v81

        examiner=WFProvisionalR2CASJournal(
            endpoint=ENDPOINT,read_only=True,
            checkpoint_sha=V81_JOURNAL)
        if examiner.writer is not None or not examiner.read_only:
            raise ValueError("WF_V81_EXAM_READER_ROLE_HAS_WRITER")
        emit({
            "status":"WF_V81_R2_READER_ONLY_RECOVERED",
            "r2_journal_checkpoint_sha256":V81_JOURNAL,
            "restored_event_count":len(examiner.event_addresses),
            "model_or_writer_keys_available":False,
            "original_prose_logged":False,
        })
        with TemporaryDirectory(prefix="wf-v81-cold-audit-") as directory:
            root=Path(directory)
            catalog=BulkCatalog(root/"catalog.sqlite3")
            try:
                r2=WFPrivateReadingClient(endpoint=ENDPOINT,timeout=70)
                inventory=r2.inventory_to_catalog(catalog)
                if inventory.get("all_folders_complete") is not True:
                    raise ValueError("WF_V81_EXAM_INVENTORY_INCOMPLETE")
                shortlisted,freeze=frozen_preselection(catalog)
                if freeze["preselection_digest_sha256"]!=B00_SHA:
                    raise ValueError("WF_V81_EXAM_B00_SELECTION_CHANGED")
                original=shortlisted["仙侠"][0]
                key=original["object_key"]
                if (sha256(key.encode("utf8")).hexdigest()!=KEY_SHA or
                    original["size_bytes"]!=SOURCE_SIZE):
                    raise ValueError("WF_V81_EXAM_SELECTED_SOURCE_CHANGED")
                file=root/"original.txt"
                fetched=download_one_verified(r2,original,file)
                if (fetched["source_sha256"]!=SOURCE_SHA or
                    fetched["bytes"]!=SOURCE_SIZE):
                    raise ValueError("WF_V81_EXAM_SOURCE_BYTES_CHANGED")
                chapters,scan=_scan_document(file,"gb18030")
                if (len(chapters)<10 or
                    scan["boundary_rule_disagreements"]!=0 or
                    scan["duplicate_printed_numbers"]!=0 or
                    scan["printed_order_backward_or_equal_steps"]!=0):
                    raise ValueError("WF_V81_EXAM_CHAPTER_BOUNDARY_CHANGED")
                report=examine_v81(
                    reader=examiner,
                    original_key=key,source_sha=SOURCE_SHA,
                    source_path=file,source_chapters=chapters,
                    final_batch_pointer=V81_BATCH,
                    prior_v80_batch_pointer=PRIOR_BATCH,
                    prior_v80_journal_pointer=PRIOR_JOURNAL,
                    prior_chapter6_experience=PRIOR_EXPERIENCE,
                )
                if report["v81_last_experience_sha256"]!=V81_EXPERIENCE:
                    raise ValueError("WF_V81_EXAM_LAST_EXPERIENCE_CHANGED")
                emit(report)
                return 0
            finally:
                catalog.close()
    except Exception as e:
        code=str(e)
        if not code.startswith((
            "WF_V81_","WF_V80_","WF_V79_","WF_LEARN_",
            "WF_INDEX_","WF_PRIVATE_","WF_V71_","WF_PREFIX_",
            "WF_CHARSET_","BULK_",
        )):
            code="WF_V81_EXAM_UNEXPECTED_FAILURE"
        emit({
           "status":"WF_V81_INDEPENDENT_AUDIT_FAILED",
           "error_code":code,
           "DeepSeek_model_calls":0,
           "R2_write_calls":0,
           "original_or_secrets_logged":False,
           "literary_level_promoted":False,
        })
        return 1


ret=main()
print("WF_V81_INDEPENDENT_COLD_EXAM_EXIT="+str(ret),flush=True)
time.sleep(6)
raise SystemExit(ret)
