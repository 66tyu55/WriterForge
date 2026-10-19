"""V79 real WF B01: 1 frozen book, first 3 source units, 4 DeepSeek calls.

NO Cloudflare Worker deployment and NO FOURTH SECRET are needed for this
bounded protocol experiment. Instead of claiming the new LEARN namespace
exists, preserve small immutable LEARN records as content-addressed JSON
blobs under the EXISTING R2 index chunks/v1 store. The last checkpoint SHA
is logged to permit independent cold restore later. This DOES NOT update
any SQL index manifest or original TXT and must not be called a full
production LEARN journal or completed book/chapter.

Read original via WF_API_TOKEN; write proof blobs only via already
configured WF_INDEX_UPLOAD_TOKEN; DeepSeek via DEEPSEEK_API_KEY.
Paid budget: three first-read calls + one analyst, 2,000 reserved output
tokens maximum. A negative writer preflight prevents ANY source transfer.
"""
from __future__ import annotations

import json
import os
import sys
import time
import types
from pathlib import Path
from hashlib import sha256
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
FROZEN_SELECTION="c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4"
ORIGINAL_KEY_SHA="370400053cded15ca89e3232e7be84b28aa20ca70542150138bef6201dc7cb22"
ORIGINAL_SHA="0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd"
ORIGINAL_BYTES=4009069
FROZEN_PREFIX_SHA="9a4e2126b13aa1f368c8b58d3860a119f144d1f2149dca6614c8df417b141a13"
EXPECTED_UNIT_SHA=(
 "139a0b323ec0226c21ff8e01e7e940abdce73ee6fc6dd797352ef5e8fecf92a4",
 "82c5c264fee2a843c774c6227da009ff4eefe8908cf525dfe9b148340f697152",
 "231ec9f1fcd138dcf419bb4f2dd0ab259448432580d13eff9946429e320d05ee",
)


def emit(doc):
    print(json.dumps(doc,ensure_ascii=False,sort_keys=True),flush=True)

print("WF_V79_REAL_PAID_B01_START",flush=True)

def main():
    required=("DEEPSEEK_API_KEY","WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN")
    if any(not os.environ.get(k) for k in required):
        emit({"status":"WF_V79_ONLY_EXISTING_THREE_KEYS_REQUIRED",
              "r2_source_downloaded":False,"model_calls":0})
        return 1
    model=None
    journal=None
    try:
        from writerforge.v79_provisional_r2_cas_journal import (
            WFProvisionalR2CASJournal,
        )
        journal=WFProvisionalR2CASJournal(
            endpoint=ENDPOINT,progress=emit,
            checkpoint_sha=os.getenv("WF_V79_RESUME_CHECKPOINT_SHA") or None,
        )
        journal.require_writer_ready()
        emit({"status":"WF_V79_EXISTING_INDEX_WRITER_AUTH_OK",
              "fourth_secret_needed":False,
              "real_private_source_sent_to_model_yet":False,
              "model_calls":0,"r2_probe_writes":0})
        from writerforge.bulk_inbox import BulkCatalog
        from writerforge.private_reading_remote import WFPrivateReadingClient
        from writerforge.wf_batch_supervisor import frozen_preselection
        from writerforge.private_r2_sql_smoke import download_one_verified
        from writerforge.wf_b01_prefix_prepare import review_first_chapter_windows
        from writerforge.wf_sequential_learning_trial import WFSequentialLearningTrial
        from writerforge.wf_learn_model_registry import new_wf_learn_model
        from writerforge.deepseek_flash_model import FlashBudget
        with TemporaryDirectory(prefix="wf-v79-real-b01-") as rootstr:
            root=Path(rootstr)
            cat=BulkCatalog(root/"catalog.sqlite3")
            try:
                source=WFPrivateReadingClient(endpoint=ENDPOINT,timeout=60)
                info=source.inventory_to_catalog(cat)
                if info.get("all_folders_complete") is not True:
                    raise ValueError("WF_V79_SOURCE_INVENTORY_NOT_COMPLETE")
                selected,frozen=frozen_preselection(cat)
                if frozen["preselection_digest_sha256"]!=FROZEN_SELECTION:
                    raise ValueError("WF_V79_PRECOMMITTED_B00_COHORT_CHANGED")
                row=selected["仙侠"][0]
                original_key=row["object_key"]
                if (sha256(original_key.encode("utf8")).hexdigest()!=
                    ORIGINAL_KEY_SHA or row["size_bytes"]!=ORIGINAL_BYTES):
                    raise ValueError("WF_V79_PRESELECTED_SOURCE_CHANGED")
                raw_path=root/"source.txt"
                transferred=download_one_verified(source,row,raw_path)
                if transferred["source_sha256"]!=ORIGINAL_SHA:
                    raise ValueError("WF_V79_ORIGINAL_SOURCE_SHA_INVALID")
                units,prepared=review_first_chapter_windows(
                    raw_path,source_sha256=ORIGINAL_SHA,
                    source_bytes=ORIGINAL_BYTES,
                    source_key_sha256=ORIGINAL_KEY_SHA,unit_count=3)
                if prepared["prefix_sha256"]!=FROZEN_PREFIX_SHA or tuple(
                    prepared["trial_unit_sha256"])!=EXPECTED_UNIT_SHA:
                    raise ValueError("WF_V79_PRECOMMITTED_READING_UNITS_CHANGED")
                emit({"status":"WF_V79_FIRST_THREE_SOURCE_UNITS_READY",
                      "source_key_sha256":ORIGINAL_KEY_SHA,
                      "first_chapter_sha256":prepared["chapter_body_sha256"],
                      "trial_unit_count":3,
                      "full_chapter_unit_count":prepared["whole_chapter_unit_count"],
                      "source_title_and_prose_logged":False,
                      "source_text_sent_to_external_model_yet":False})
                budget=FlashBudget(
                    max_calls=4,max_reserved_output_tokens=2000)
                model=new_wf_learn_model(budget=budget)
                learner=WFSequentialLearningTrial(
                    model=model,journal=journal,
                    original_key=original_key,source_sha=ORIGINAL_SHA,
                    chapter=1,
                    chapter_body_sha=prepared["chapter_body_sha256"])
                result_a=learner.first_read(units,expected_unit_count=3)
                emit({"status":"WF_V79_PASS_A_3_UNITS_REAL_R2_CAS_LOCKED",
                      "first_read_seal_sha256":result_a["r2_first_read_seal_sha256"],
                      "checkpoint_sha256":journal.checkpoint_sha,
                      "model_calls_so_far":budget.calls_reserved,
                      "first_read_events":result_a["first_read_events_stored"],
                      "new_model_reads":result_a["first_read_events_new_this_run"],
                      "completed_whole_chapters":0})
                result_b=learner.analyse_after_lock()
                emit({
                    "status":"WF_V79_B01_REAL_DEEPSEEK_AND_R2_CAS_COMPLETED",
                    "source_sha256":ORIGINAL_SHA,
                    "source_key_sha256":ORIGINAL_KEY_SHA,
                    "prefix_sha256":FROZEN_PREFIX_SHA,
                    "pass_a_seal_sha256":result_a["r2_first_read_seal_sha256"],
                    "pass_b_sha256":result_b["pass_b_record_sha256"],
                    "latest_checkpoint_sha256":journal.checkpoint_sha,
                    "events_in_r2_cas":len(journal.event_addresses),
                    "model_usage":model.public_usage_report(),
                    "source_original_edited":False,
                    "third_party_model_received_exact_opening_units":True,
                    "full_original_chapters_learned":0,
                    "source_classification_verified":False,
                    "literary_mastery_graduated":False,
                    "r2_storage_native_learn_namespace":False,
                    "r2_storage_provisional_cas_checkpoint":True,
                    "independent_reader_only_restore_needed":True,
                    "private_prose_or_title_emitted":False,
                })
                return 0
            finally:
                cat.close()
    except Exception as exc:
        status=str(exc)
        if not status.startswith((
            "WF_V79_","WF_FLASH_","WF_LEARN_",
            "WF_INDEX_","WF_V71_","WF_PREFIX_",
            "WF_PRIVATE_","BULK_","WF_CHARSET_",
            "WF_SUPERVISOR_",
        )):
            status="WF_V79_UNKNOWN_FAILURE_NO_SOURCE_LOG"
        emit({
          "status":"WF_V79_B01_STOPPED_WITH_REAL_RECEIPT",
          "error_code":status,
          "latest_r2_cas_checkpoint_sha256":
              journal.checkpoint_sha if journal else None,
          "r2_cas_events_existing":len(journal.event_addresses)
              if journal else 0,
          "model_usage":model.public_usage_report() if model else None,
          "full_chapters_learned":0,
          "original_text_or_secret_logged":False,
          "automatic_retries":0,
        })
        return 1

status=main()
print("WF_V79_REAL_B01_EXIT="+str(status),flush=True)
time.sleep(8)
raise SystemExit(status)
