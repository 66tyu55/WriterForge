"""V78: WF prepares exact three opening source units from FROZEN B00 R2 book.

Reads one 4,009,069-byte original TXT via existing authenticated reader.
No model/Writer credential, no R2 writes. Emits only per-unit SHA and lengths.
The three private source-unit strings never reach GitHub/ChatGPT; the
future B01 small paid trial remains gated on live Worker writer-ready.
"""
from __future__ import annotations

import json,os,sys,time,types
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
for secret in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
               "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(secret,None)
pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg

B00_SELECTION="c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4"
FROZEN_KEY="370400053cded15ca89e3232e7be84b28aa20ca70542150138bef6201dc7cb22"
FROZEN_SOURCE="0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd"
FROZEN_SIZE=4009069

def emit(x):
    print(json.dumps(x,ensure_ascii=False,sort_keys=True),flush=True)

print("WF_V78_B01_PREFIX_ORIGINAL_ONLY_START",flush=True)

def main():
    if not os.getenv("WF_API_TOKEN"):
        emit({"status":"WF_V78_ORIGINAL_READER_UNAVAILABLE"})
        return 1
    try:
        from writerforge.bulk_inbox import BulkCatalog
        from writerforge.private_reading_remote import WFPrivateReadingClient
        from writerforge.wf_batch_supervisor import frozen_preselection
        from writerforge.private_r2_sql_smoke import download_one_verified
        from writerforge.wf_b01_prefix_prepare import review_first_chapter_windows
        client=WFPrivateReadingClient(
            endpoint="https://wf-r2-api.3227482831.workers.dev")
        with TemporaryDirectory(prefix="wf-v78-only-opening-") as tmp:
            base=Path(tmp)
            catalog=BulkCatalog(base/"metadata.sqlite3")
            try:
                scanned=client.inventory_to_catalog(catalog)
                if not scanned["all_folders_complete"]:
                    raise ValueError("WF_V78_INVENTORY_PARTIAL")
                chosen,freeze=frozen_preselection(catalog)
                if freeze["preselection_digest_sha256"]!=B00_SELECTION:
                    raise ValueError("WF_V78_PRESELECTED_B00_LIST_CHANGED")
                row=chosen["仙侠"][0]
                if (sha256(row["object_key"].encode("utf8")).hexdigest()!=FROZEN_KEY
                        or row["size_bytes"]!=FROZEN_SIZE):
                    raise ValueError("WF_V78_PRESELECTED_SOURCE_CHANGED")
                source=base/"source.txt"
                result=download_one_verified(client,row,source)
                if result["source_sha256"]!=FROZEN_SOURCE:
                    raise ValueError("WF_V78_ORIGINAL_SHA_CHANGED")
                units,receipt=review_first_chapter_windows(
                    source,source_sha256=FROZEN_SOURCE,
                    source_bytes=FROZEN_SIZE,source_key_sha256=FROZEN_KEY,
                    unit_count=3)
                assert len(units)==3
                emit({
                   "status":"WF_V78_B01_THREE_CONTIGUOUS_PRIVATE_UNITS_PREPARED",
                   "b00_preselection_sha256":B00_SELECTION,
                   "metadata_objects_seen":scanned["total_objects"],
                   "source_bytes_read":result["bytes"],
                   "prefix_receipt":receipt,
                   "R2_learn_writer_live_ready":False,
                   "real_deepseek_model_calls":0,
                   "r2_learner_writes":0,
                   "source_or_title_logged":False,
                   "original_source_untouched":True,
                   "source_transferred_to_GPT":False,
                   "automatic_paid_training_started":False,
                })
                return 0
            finally:
                catalog.close()
    except Exception as e:
        status=str(e)
        if not status.startswith(("WF_V78_","WF_PREFIX_",
                                  "WF_CHARSET_","WF_PRIVATE_",
                                  "WF_V71_","WF_ADMISSION_","BULK_")):
            status="WF_V78_PREFIX_UNEXPECTED_FAILURE"
        emit({"status":"WF_V78_B01_PREFIX_REJECTED",
              "error_code":status,
              "paid_calls":0,"R2_writes":0,
              "source_or_keys_logged":False})
        return 1

result=main()
print("WF_V78_PREFIX_RUN_EXIT="+str(result),flush=True)
time.sleep(7)
raise SystemExit(result)
