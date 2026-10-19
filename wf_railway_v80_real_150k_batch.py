"""V80 REAL DeepSeek Flash training batch: 150,000 total tokens ceiling.

Continue previous V79 chapter1 at UNIT FOUR from the immutable R2 CAS
checkpoint, never repeat those first three charged units. Then train full
chapters 2–6 in exact source order with one first-read DeepSeek call per
unit, R2 immutable receipt, A-seal, evidence-linked B analysis, WF-created
experience/failure strategy card and R2 batch progress checkpoint.

This spends actual tokens gradually under the new 150k input+output cap.
No GPT reading original content, no new API keys, no Cloudflare Worker
deployment, no automatic retry, no change to literary graduation or V49.
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
pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
B00_SHA="c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4"
ORIGINAL_KEY_HASH="370400053cded15ca89e3232e7be84b28aa20ca70542150138bef6201dc7cb22"
ORIGINAL_SHA="0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd"
ORIGINAL_BYTES=4009069
PREVIOUS_V79_JOURNAL_SHA="3d12c9e555cfa7b1dd0ce5074e57ec3473bc6d22735e0677b8808b3d953f9e49"
# Frozen progress after V80's first 12 new chapter-1 units and one failed
# (but billed) analysis-schema attempt. These tokens count against SAME 150k.
V80_PRIOR_PROMPT_TOKENS=11243
V80_PRIOR_OUTPUT_TOKENS=2271
V80_PRIOR_CALLS=13
V80_PRIOR_RESERVED_OUTPUT_TOKENS=14300
MAX_CHAPTERS=6
MAX_TOTAL_TOKENS=150000

def emit(obj):
    print(json.dumps(obj,ensure_ascii=False,sort_keys=True),flush=True)

print("WF_V80_150K_REAL_LARGE_TRAINING_STARTED",flush=True)

def main():
    keys=("WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN","DEEPSEEK_API_KEY")
    if any(not os.getenv(k) for k in keys):
        emit({"status":"WF_V80_EXISTING_THREE_CREDENTIALS_MISSING",
              "model_calls":0,"source_read":False})
        return 1
    model=None
    journal=None
    batch=None
    try:
        from writerforge.v79_provisional_r2_cas_journal import (
            WFProvisionalR2CASJournal)
        journal=WFProvisionalR2CASJournal(
            endpoint=ENDPOINT,checkpoint_sha=PREVIOUS_V79_JOURNAL_SHA,
            progress=emit)
        journal.require_writer_ready()
        emit({"status":"WF_V80_RESUMING_WITH_PREVIOUS_PAID_TOKENS_ACCOUNTED",
              "previous_real_provider_requests":V80_PRIOR_CALLS,
              "previous_provider_reported_tokens":(
                  V80_PRIOR_PROMPT_TOKENS+V80_PRIOR_OUTPUT_TOKENS),
              "original_reading_units_1_to_15_already_locked":True,
              "old_sealed_V79_three_unit_evidence_preserved":True,
              "automatic_repeat_model_reads":False})
        emit({"status":"WF_V80_EXISTING_WRITER_READY_V79_CHECKPOINT_RESTORED",
              "previous_V79_checkpoint_sha256":PREVIOUS_V79_JOURNAL_SHA,
              "archived_pilot_events":len(journal.event_addresses),
              "model_calls":0,"fourth_secret_needed":False})
        from writerforge.bulk_inbox import BulkCatalog
        from writerforge.private_reading_remote import WFPrivateReadingClient
        from writerforge.private_r2_sql_smoke import download_one_verified
        from writerforge.wf_batch_supervisor import frozen_preselection
        from writerforge.wf_charset_byte_review import byte_charset_audit
        from writerforge.wf_self_learning_admission import _scan_document
        from writerforge.wf_learn_model_registry import new_wf_learn_model
        from writerforge.deepseek_flash_model import FlashBudget,DeepSeekFlashError
        from writerforge.v80_large_chapter_batch import (
            WFLargeChapterBatch,WFLargeStudyError)
        from writerforge.wf_api_usage_supervisor import WFApiUsageAuditError

        with TemporaryDirectory(prefix="wf-v80-150k-learn-") as directory:
            folder=Path(directory)
            db=BulkCatalog(folder/"catalog.sqlite3")
            try:
                wf=WFPrivateReadingClient(endpoint=ENDPOINT,timeout=60)
                scanned=wf.inventory_to_catalog(db)
                if scanned["all_folders_complete"] is not True:
                    raise WFLargeStudyError("WF_V80_R2_INVENTORY_INCOMPLETE")
                candidates,freeze=frozen_preselection(db)
                if freeze["preselection_digest_sha256"]!=B00_SHA:
                    raise WFLargeStudyError("WF_V80_FROZEN_B00_COHORT_CHANGED")
                chosen=candidates["仙侠"][0]
                key=chosen["object_key"]
                if sha256(key.encode()).hexdigest()!=ORIGINAL_KEY_HASH:
                    raise WFLargeStudyError("WF_V80_FROZEN_BOOK_SWITCHED")
                rawfile=folder/"source.txt"
                original=download_one_verified(wf,chosen,rawfile)
                if original["source_sha256"]!=ORIGINAL_SHA or (
                    original["bytes"]!=ORIGINAL_BYTES):
                    raise WFLargeStudyError("WF_V80_ORIGINAL_SHA_CHANGED")
                textshape=byte_charset_audit(
                   rawfile,expected_source_sha256=ORIGINAL_SHA,
                   expected_size=ORIGINAL_BYTES,
                   expected_key_sha256=ORIGINAL_KEY_HASH)
                if (textshape["plausible_distinct_decoded_texts"]!=1 or
                    "gb18030" not in textshape["unique_reading_codec_aliases"]):
                    raise WFLargeStudyError("WF_V80_CHARSET_CHANGED")
                chapters,scan=_scan_document(rawfile,"gb18030")
                if (scan["boundary_rule_disagreements"] or
                    scan["duplicate_printed_numbers"] or
                    scan["printed_order_backward_or_equal_steps"]):
                    raise WFLargeStudyError("WF_V80_FROZEN_CHAPTERS_CHANGED")
                emit({
                  "status":"WF_V80_FIXED_SOURCE_AND_CHAPTERS_VERIFIED",
                  "frozen_B00_selection_sha256":B00_SHA,
                  "source_sha256":ORIGINAL_SHA,
                  "chapters_detected":len(chapters),
                  "train_first_up_to_chapters":MAX_CHAPTERS,
                  "max_batch_total_input_output_tokens":MAX_TOTAL_TOKENS,
                  "model_calls_so_far":0,
                  "private_source_or_title_logged":False,
                })
                budget=FlashBudget(
                    max_calls=96,
                    max_reserved_output_tokens=MAX_TOTAL_TOKENS,
                    max_total_tokens=MAX_TOTAL_TOKENS,
                    calls_reserved=V80_PRIOR_CALLS,
                    tokens_reserved=V80_PRIOR_RESERVED_OUTPUT_TOKENS,
                    prompt_tokens_reported=V80_PRIOR_PROMPT_TOKENS,
                    completion_tokens_reported=V80_PRIOR_OUTPUT_TOKENS,
                    conservative_tokens_committed=(
                        V80_PRIOR_PROMPT_TOKENS+V80_PRIOR_OUTPUT_TOKENS),
                    calls_with_provider_usage=V80_PRIOR_CALLS,
                    calls_by_role={"first_read":12,"craft_analysis":1})
                model=new_wf_learn_model(budget=budget)
                batch=WFLargeChapterBatch(
                    journal=journal,model=model,
                    original_key=key,source_sha=ORIGINAL_SHA,
                    progress=emit)
                for chap in chapters[:MAX_CHAPTERS]:
                    windows=batch.chapter_body(rawfile,chap)
                    # Each source unit is directly verified against the
                    # exact chapter and cannot be supplied by GPT.
                    batch.complete(chapter=chap,windows=windows)
                emit({
                   "status":"WF_V80_150K_CAP_SCALED_CHAPTER_BATCH_FINISHED",
                   "requested_max_batch_tokens":MAX_TOTAL_TOKENS,
                   "completed_chapter_source_coverage_count":
                       len(batch.finished_chapters),
                   "pure_chapter_A_before_B_count":sum(
                       x["strict_full_chapter_pass_a_before_any_pass_b"]
                       for x in batch.finished_chapters),
                   "first_chapter_mixed_early_V79_analysis":True,
                   "full_literary_mastery_certified":False,
                   "source_sha256":ORIGINAL_SHA,
                   "last_journal_r2_cas_checkpoint":
                       journal.checkpoint_sha,
                   "last_batch_progress_cas_sha256":
                       batch.last_batch_pointer,
                   "last_experience_cas_sha256":
                       batch.previous_experience_sha,
                   "token_usage":model.public_usage_report(),
                   "cumulative_batch_budget":budget.public_receipt(),
                   "prior_paid_requests_included":V80_PRIOR_CALLS,
                   "original_text_ever_printed":False,
                   "R2_LEARN_native_route_deployed":False,
                   "automatic_reschedule":False,
                })
                return 0
            finally:
                db.close()
    except Exception as exc:
        code=str(exc)
        if not code.startswith((
          "WF_V80_","WF_FLASH_","WF_USAGE_","WF_LEARN_",
          "WF_V79_","WF_INDEX_","WF_PRIVATE_","WF_V71_",
          "WF_PREFIX_","WF_CHARSET_","BULK_",
        )):
            code="WF_V80_UNEXPECTED_FAILURE"
        status="WF_V80_150K_BATCH_PAUSED_WITH_DURABLE_CHECKPOINT"
        # A pure budget STOP is not a corrupt literary result. Keep previous
        # chapter checkpoint and stop; no hidden retries.
        emit({
           "status":status,"error_code":code,
           "latest_r2_journal_checkpoint_sha256":
               journal.checkpoint_sha if journal else None,
           "latest_batch_progress_checkpoint_sha256":
               batch.last_batch_pointer if batch else None,
           "finished_chapter_receipts":
               batch.finished_chapters if batch else [],
           "model_usage":model.public_usage_report() if model else None,
           "full_literary_mastery_certified":False,
           "model_retries":0,
           "original_prose_or_secret_logged":False,
        })
        return 1

result=main()
print("WF_V80_150K_TRAINING_EXIT="+str(result),flush=True)
time.sleep(8)
raise SystemExit(result)
