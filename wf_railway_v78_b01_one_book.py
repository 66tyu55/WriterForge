"""WF V78 real B01 runner: ONE frozen Xianxia, exactly three opening units.

This script is NOT auto-scheduled. It must not be used until V77 Worker
writer-ready accepts the existing WF_INDEX_UPLOAD_TOKEN. Before ANY
source download or paid call, verify the R2 LEARN append-only writer. Then
reverify the original B00 freeze/hash, use only first 3 contiguous units,
and lock PASS A on R2 unit by unit BEFORE PASS B. Four DeepSeek Flash calls
maximum, 2,000 reserved output tokens. Never expose source text or API keys
in stdout, GitHub, GPT or error messages.

A successful 3-unit experiment is NOT a complete chapter, independent
literary-quality assessment or official WF literary promotion.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
import json
import os
import sys
import time
import types

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg

WORKER="https://wf-r2-api.3227482831.workers.dev"
B00_HASH="c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4"
ORIGINAL_KEY_HASH="370400053cded15ca89e3232e7be84b28aa20ca70542150138bef6201dc7cb22"
ORIGINAL_SHA="0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd"
ORIGINAL_BYTES=4009069

def report(doc):
    print(json.dumps(doc,ensure_ascii=False,sort_keys=True),flush=True)

print("WF_V78_B01_STRICT_SINGLE_BOOK_START",flush=True)

def main():
    if not all(os.environ.get(k) for k in (
            "WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN","DEEPSEEK_API_KEY")):
        report({"status":"WF_B01_EXISTING_KEY_MISSING",
                "source_downloaded":False,"model_calls":0,"r2_writes":0})
        return 1
    # Do not import or call model until R2 writer-ready is confirmed.
    model=None
    try:
        from writerforge.r2_learn_journal import WFLearnJournal
        journal=WFLearnJournal(endpoint=WORKER)
        journal.require_writer_ready()
        report({"status":"WF_B01_EXISTING_WRITER_AUTH_AND_APPEND_ONLY_READY",
                "fourth_key_needed":False,
                "paid_model_calls_so_far":0})
        from writerforge.bulk_inbox import BulkCatalog
        from writerforge.private_reading_remote import WFPrivateReadingClient
        from writerforge.wf_batch_supervisor import frozen_preselection
        from writerforge.private_r2_sql_smoke import download_one_verified
        from writerforge.wf_b01_prefix_prepare import review_first_chapter_windows
        from writerforge.wf_learn_model_registry import new_wf_learn_model
        from writerforge.deepseek_flash_model import FlashBudget
        from writerforge.wf_sequential_learning_trial import WFSequentialLearningTrial
        with TemporaryDirectory(prefix="wf-v78-b01-frozen-") as tmp:
            root=Path(tmp)
            cat=BulkCatalog(root/"inventory.sqlite3")
            try:
                inventory=WFPrivateReadingClient(endpoint=WORKER)
                scan=inventory.inventory_to_catalog(cat)
                if not scan["all_folders_complete"]:
                    raise ValueError("WF_B01_INVENTORY_INCOMPLETE")
                candidates,proven=frozen_preselection(cat)
                if proven["preselection_digest_sha256"]!=B00_HASH:
                    raise ValueError("WF_B01_FROZEN_SELECTION_CHANGED")
                book=candidates["仙侠"][0]
                key=book["object_key"]
                if (sha256(key.encode("utf-8")).hexdigest()!=ORIGINAL_KEY_HASH
                    or book["size_bytes"]!=ORIGINAL_BYTES):
                    raise ValueError("WF_B01_SELECTED_BOOK_SWITCHED")
                temp_file=root/"source.txt"
                fetched=download_one_verified(inventory,book,temp_file)
                if fetched["source_sha256"]!=ORIGINAL_SHA:
                    raise ValueError("WF_B01_SOURCE_CONTENT_CHANGED")
                units,prefix=review_first_chapter_windows(
                    temp_file,source_sha256=ORIGINAL_SHA,
                    source_bytes=ORIGINAL_BYTES,
                    source_key_sha256=ORIGINAL_KEY_HASH,
                    unit_count=3)
                report({
                   "status":"WF_B01_ONLY_FIRST_THREE_UNITS_VERIFIED",
                   "first_chapter_body_sha256":
                       prefix["chapter_body_sha256"],
                   "prefix_sha256":prefix["prefix_sha256"],
                   "units_to_read":len(units),
                   "not_full_chapter":True,
                   "source_text_logged":False,
                   "model_calls_so_far":0,
                })
                budget=FlashBudget(
                    max_calls=4,max_reserved_output_tokens=2000)
                model=new_wf_learn_model(budget=budget)
                learner=WFSequentialLearningTrial(
                    model=model,journal=journal,original_key=key,
                    source_sha=ORIGINAL_SHA,
                    chapter=1,
                    chapter_body_sha=prefix["chapter_body_sha256"])
                pass_a=learner.first_read(units,expected_unit_count=3)
                report({
                  "status":pass_a["status"],
                  "source_sha256":ORIGINAL_SHA,
                  "r2_first_read_seal_sha256":
                      pass_a["r2_first_read_seal_sha256"],
                  "locked_units":pass_a["units_seen_in_order"],
                  "locked_events_new_this_run":
                      pass_a["first_read_events_new_this_run"],
                  "repeated_paid_reads_avoided":
                      pass_a["model_repeat_reads_avoided"],
                  "complete_chapter_claimed":False,
                  "source_text_logged":False,
                })
                pass_b=learner.analyse_after_lock()
                usage=model.public_usage_report()
                report({
                  "status":"WF_B01_THREE_UNITS_PASS_A_B_R2_LOCKED",
                  "pass_a_seal_sha256":
                      pass_a["r2_first_read_seal_sha256"],
                  "pass_b_event_sha256":
                      pass_b["pass_b_record_sha256"],
                  "first_chapter_full_units":
                      prefix["whole_chapter_unit_count"],
                  "completed_chapters":0,
                  "literary_genre_certified":False,
                  "literary_training_graduation":False,
                  "model_usage":usage,
                  "source_title_or_prose_logged":False,
                  "independent_reader_only_audit_pending":True,
                })
                return 0
            finally:
                cat.close()
    except Exception as exc:
        code=str(exc)
        if not code.startswith((
          "WF_LEARN_","WF_B01_","WF_FLASH_","WF_PREFIX_",
          "WF_CHARSET_","WF_PRIVATE_","WF_V71_","BULK_",
        )):
            code="WF_B01_UNEXPECTED_BLOCK_OR_FAILURE"
        report({
           "status":"WF_B01_PAUSED_NO_FALSE_TRAINING_CREDIT",
           "error_code":code,
           "usage_if_model_started":
             model.public_usage_report() if model is not None else None,
           "paid_call_may_have_been_billed":
             model is not None and model.budget.calls_reserved>0,
           "private_original_or_credential_logged":False,
           "completed_chapters_claimed":0,
           "literary_promotion":False,
        })
        return 1

status=main()
print("WF_V78_B01_EXEC_EXIT="+str(status),flush=True)
time.sleep(7)
raise SystemExit(status)
