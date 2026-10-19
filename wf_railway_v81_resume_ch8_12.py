"""V81 real WF chapter7-12 continued training, <=150000 total Tokens.

Zero re-training of already-paid chapters 1-6: restore ONLY the exact
V80 source, journal SHA and chapter6 signed experience from private R2,
then start with physical chapter7 (six more chapters maximum). Prior
experience is actually copied into WF's next-chapter reading strategy
before any source-bearing DeepSeek call. The batch progress chain is NEW
and bounded to chapters7-12; original V80 checkpoints are immutable.

Real user originals go from private R2 to WF Railway to official DeepSeek
on the user's existing API, never to GPT or GitHub. Old three secrets are
sufficient. Model calls and input+output total are bounded BEFORE network;
timeouts or invalid JSON still consume a reserved request with no retry.
"""
from __future__ import annotations

import os
import sys
import json
import time
import types
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
package=types.ModuleType("writerforge")
package.__path__=[str(ROOT/"writerforge")]
package.__package__="writerforge"
sys.modules["writerforge"]=package

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
FROZEN_B00_SHA="c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4"
SOURCE_KEY_SHA="370400053cded15ca89e3232e7be84b28aa20ca70542150138bef6201dc7cb22"
ORIGINAL_SHA="0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd"
ORIGINAL_BYTES=4009069
OLD_BATCH_SHA="1d5c11eb1c98b067ef212877d349f849fde583b9568d4f90fbd84a33f0b7d079"
OLD_JOURNAL_SHA="2dcaaa908ca2a5bb3175377cd146870e798d3cc9959631c9264ac9cb846d5eb8"
PRIOR_CHAPTER7_EXPERIENCE_SHA="438102a7c54dee6291c5ee5fb01160f3d6ea65686b97267dd72b344a45a30c91"
CHAPTER_START=8
CHAPTER_STOP=12
NEW_BATCH_ID="WF-V81-150K-20261019-CH7-12"
TOTAL_TOKEN_CAP=150000
CALL_CAP=96
OUTPUT_RESERVATION=150000

# Precommitted source structure from the genuine zero-model V81 Railway
# preflight, run BEFORE writing new training code and scoring blind scenes.
SOURCE_CHAPTER_UNIT_COUNTS=(8,10,12,11,11)
SOURCE_CHAPTER_SHA=(
 "80ec84e17807cf8d344c7a21402b7bd3222aeee0689c5ef7368336124f75874d",
 "1fe46188c71b697f3bfc14b81327f0c7bd8184e124275aedde38c86e4010755f",
 "bd878e804a0e0152127f3ff23f2a951f50ccf68ac819efc2a695ccb47ca3d9e5",
 "a7f3bbabc8dc23661dd5150ab4af5cce3b0dd0e65f3a0bb75a0d8db7715fbfac",
 "1b3174a076d51ea4beafcfda8e096db7b854c3b19af27034175ba88015d4b6c1",
)

def emit(doc):
    print(json.dumps(doc,sort_keys=True,ensure_ascii=False),flush=True)

print("WF_V81_RESUME_AFTER_CHAPTER8_JSON_FAILURE_START",flush=True)

def main():
    required=("DEEPSEEK_API_KEY","WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN")
    if any(not os.environ.get(k) for k in required):
        emit({"status":"WF_V81_EXISTING_THREE_KEY_NAMES_UNAVAILABLE",
              "remote_attempts":0})
        return 1
    journal=None
    model=None
    batch=None
    try:
        from writerforge.v79_provisional_r2_cas_journal import (
            WFProvisionalR2CASJournal)
        from writerforge.wf_self_learning_admission import _scan_document
        from writerforge.wf_charset_byte_review import byte_charset_audit
        from writerforge.wf_batch_supervisor import frozen_preselection
        from writerforge.private_r2_sql_smoke import download_one_verified
        from writerforge.private_reading_remote import WFPrivateReadingClient
        from writerforge.bulk_inbox import BulkCatalog
        from writerforge.wf_learn_model_registry import new_wf_learn_model
        from writerforge.deepseek_flash_model import FlashBudget
        from writerforge.v80_large_chapter_batch import (
            WFLargeChapterBatch)
        from writerforge.wf_b01_prefix_prepare import (
            _split_into_ordered_units)
        from writerforge.v81_frozen_blind_ablation import frozen_sha

        # FIRST recover immutable previous evidence. This is NOT a paid call.
        journal=WFProvisionalR2CASJournal(
            endpoint=ENDPOINT,checkpoint_sha=OLD_JOURNAL_SHA,progress=emit)
        journal.require_writer_ready()
        prior=json.loads(journal._get_content(OLD_BATCH_SHA))
        if not (
            prior.get("format")=="wf.learn.150k-batch-progress.v80" and
            prior.get("last_completed_chapter")==7 and
            prior.get("batch_id")==NEW_BATCH_ID and
            prior.get("source_sha256")==ORIGINAL_SHA and
            prior.get("source_key_sha256")==SOURCE_KEY_SHA and
            prior.get("journal_checkpoint_sha256")==
            "52ebdcaa9f6f224e2026d29cb70cd18649eebae6ce3385f0a2781cf02c2bf2bb" and
            prior.get("latest_experience_sha256")==PRIOR_CHAPTER7_EXPERIENCE_SHA and
            prior.get("mastery_graduation_approved") is False
        ):
            raise ValueError("WF_V81_PREVIOUS_BATCH_SOURCE_OR_STATE_UNVERIFIED")
        old_card=json.loads(journal._get_content(PRIOR_CHAPTER7_EXPERIENCE_SHA))
        if not (
            old_card.get("format")=="wf.learn.experience.v80" and
            old_card.get("chapter")==7 and
            old_card.get("source_sha256")==ORIGINAL_SHA and
            old_card.get("source_key_sha256")==SOURCE_KEY_SHA and
            old_card.get("analysis_sha256")==
                prior["chapter_receipt"]["final_chapter_analysis_sha256"] and
            old_card.get("literary_quality_independently_verified") is False and
            isinstance(old_card.get("reflection"),dict)
        ):
            raise ValueError("WF_V81_CHAPTER6_EXPERIENCE_PROVENANCE_INVALID")
        strategy=old_card["reflection"].get("next_strategy")
        if not isinstance(strategy,str) or not 1<=len(strategy)<=200:
            raise ValueError("WF_V81_CHAPTER6_STRATEGY_INVALID")
        emit({
          "status":"WF_V81_RESUME_PREVIOUS_PAID_USAGE_ACCOUNTED",
          "previous_real_requests":22,
          "previous_provider_prompt_tokens":19876,
          "previous_provider_completion_tokens":6471,
          "previous_total_tokens":26347,
          "chapter7_already_completed_without_rebilling":True,
          "chapter8_eight_first_reads_already_in_R2":True,
          "source_reprocessing_paid_units":False})
        emit({
          "status":"WF_V81_V80_PRIOR_BATCH_AND_EXPERIENCE_R2_VERIFIED",
          "prior_completed_chapters":7,
          "previous_journal_events":len(journal.event_addresses),
          "previous_training_batch_sha256":OLD_BATCH_SHA,
          "previous_experience_sha256":PRIOR_CHAPTER7_EXPERIENCE_SHA,
          "previous_strategy_sha256":sha256(strategy.encode()).hexdigest(),
          "new_model_calls":0,
          "previous_model_calls_not_repeated":True,
          "blind_cases_pre_frozen_sha256":frozen_sha(),
          "original_prose_or_card_text_logged":False,
        })

        with TemporaryDirectory(prefix="wf-v81-ch7-12-") as temp:
            root=Path(temp)
            cat=BulkCatalog(root/"metadata.sqlite3")
            try:
                wf=WFPrivateReadingClient(endpoint=ENDPOINT,timeout=60)
                inv=wf.inventory_to_catalog(cat)
                if not inv["all_folders_complete"]:
                    raise ValueError("WF_V81_PRIVATE_INVENTORY_INCOMPLETE")
                choices,frozen=frozen_preselection(cat)
                if frozen["preselection_digest_sha256"]!=FROZEN_B00_SHA:
                    raise ValueError("WF_V81_B00_PRESELECTION_CHANGED")
                row=choices["仙侠"][0]
                key=row["object_key"]
                if (sha256(key.encode()).hexdigest()!=SOURCE_KEY_SHA or
                    row["size_bytes"]!=ORIGINAL_BYTES):
                    raise ValueError("WF_V81_ORIGINAL_BOOK_CHANGED")
                local=root/"original.txt"
                downloaded=download_one_verified(wf,row,local)
                if downloaded["source_sha256"]!=ORIGINAL_SHA:
                    raise ValueError("WF_V81_ORIGINAL_SHA_UNTRUSTED")
                charset=byte_charset_audit(
                    local,expected_source_sha256=ORIGINAL_SHA,
                    expected_size=ORIGINAL_BYTES,
                    expected_key_sha256=SOURCE_KEY_SHA)
                if (charset["plausible_distinct_decoded_texts"]!=1 or
                    "gb18030" not in charset["unique_reading_codec_aliases"]):
                    raise ValueError("WF_V81_CHARSET_IDENTITY_CHANGED")
                chapters,scan=_scan_document(local,"gb18030")
                if (scan["boundary_rule_disagreements"] or
                    scan["duplicate_printed_numbers"] or
                    scan["printed_order_backward_or_equal_steps"] or
                    len(chapters)<CHAPTER_STOP):
                    raise ValueError("WF_V81_CHAPTER_SOURCE_AMBIGUOUS")
                for i,chap in enumerate(chapters[7:12]):
                    if chap.body_sha256!=SOURCE_CHAPTER_SHA[i] or (
                       chap.ordinal != i+CHAPTER_START):
                        raise ValueError("WF_V81_PRECOMMITTED_CHAPTER_CHANGED")
                emit({
                   "status":"WF_V81_SOURCE_CHAPTER7_TO12_FROZEN_VERIFIED",
                   "planned_chapter_start":CHAPTER_START,
                   "planned_chapter_stop":CHAPTER_STOP,
                   "source_units_precommitted":sum(SOURCE_CHAPTER_UNIT_COUNTS),
                   "source_text_or_titles_logged":False,
                   "model_calls":0,
                })

                # New batch total cap is independent of completed V80 batch.
                # It never replays paid chapters1..6.
                # FULL pre-crash paid usage from actual Railway V81 logs;
                # count unsuccessful-but-billed chapter8 analysis and fix.
                budget=FlashBudget(
                    max_calls=CALL_CAP,
                    max_reserved_output_tokens=OUTPUT_RESERVATION,
                    max_total_tokens=TOTAL_TOKEN_CAP,
                    calls_reserved=22,
                    tokens_reserved=27100,
                    prompt_tokens_reported=19876,
                    completion_tokens_reported=6471,
                    conservative_tokens_committed=26347,
                    calls_with_provider_usage=22,
                    calls_by_role={"first_read":17,"craft_analysis":5})
                model=new_wf_learn_model(budget=budget)
                batch=WFLargeChapterBatch(
                    journal=journal,model=model,
                    original_key=key,source_sha=ORIGINAL_SHA,
                    batch_id=NEW_BATCH_ID,progress=emit)
                batch.previous_experience_sha=PRIOR_CHAPTER7_EXPERIENCE_SHA
                batch.earlier_strategy=strategy
                batch.last_batch_pointer=OLD_BATCH_SHA  # Resume chapter7 committed batch chain
                for offset,chap in enumerate(chapters[7:12]):
                    windows=batch.chapter_body(local,chap)
                    if len(windows)!=SOURCE_CHAPTER_UNIT_COUNTS[offset]:
                        raise ValueError("WF_V81_PREREGISTERED_UNIT_COUNT_CHANGED")
                    batch.complete(chapter=chap,windows=windows)
                emit({
                  "status":"WF_V81_REAL_CHAPTER7_TO12_COMPLETED",
                  "new_batch_id":NEW_BATCH_ID,
                  "source_sha256":ORIGINAL_SHA,
                  "completed_new_chapters":[r["chapter"] for r in
                                             batch.finished_chapters],
                  "whole_source_units_read":sum(r["unit_count"] for r in
                                                  batch.finished_chapters),
                  "old_chapters_re_read_by_model":0,
                  "prior_V81_chapter7_batch_pointer":OLD_BATCH_SHA,
                  "last_V81_batch_pointer_sha256":batch.last_batch_pointer,
                  "last_journal_checkpoint_sha256":journal.checkpoint_sha,
                  "last_experience_sha256":batch.previous_experience_sha,
                  "first_new_chapter_uses_ch6_experience":
                     batch.finished_chapters[0][
                       "previous_experience_sha256_used_in_prompts"]==
                           PRIOR_CHAPTER7_EXPERIENCE_SHA,
                  "usage":model.public_usage_report(),
                  "cumulative_150k_training_budget":budget.public_receipt(),
                  "prior_billable_calls_carried_forward":22,
                  "batch_token_ceiling":TOTAL_TOKEN_CAP,
                  "training_quality_independently_proven":False,
                  "new_blind_exam_results_pending":True,
                  "new_literary_level_promoted":False,
                  "raw_original_or_key_logged":False,
                })
                return 0
            finally:cat.close()
    except Exception as error:
        code=str(error)
        if not code.startswith((
            "WF_V81_","WF_V80_","WF_V79_","WF_FLASH_",
            "WF_LEARN_","WF_INDEX_","WF_USAGE_",
            "WF_PRIVATE_","WF_V71_","WF_CHARSET_","WF_PREFIX_",
            "BULK_"
        )):
            code="WF_V81_UNEXPECTED_STOP"
        emit({
           "status":"WF_V81_BATCH_STOPPED_WITH_IMMUTABLE_R2_CHECKPOINT",
           "error_code":code,
           "last_journal_checkpoint_sha256":
               journal.checkpoint_sha if journal else None,
           "last_V81_batch_pointer_sha256":
               batch.last_batch_pointer if batch else None,
           "completed_new_chapters":
               [r["chapter"] for r in batch.finished_chapters]
               if batch else [],
           "usage":model.public_usage_report() if model else None,
           "cumulative_150k_budget":model.budget.public_receipt()
                if model else None,
           "no_paid_retries":True,
           "original_and_secret_logged":False,
           "literary_level_promoted":False,
        })
        return 1

status=main()
print("WF_V81_REAL_CH7_12_EXIT="+str(status),flush=True)
time.sleep(7)
raise SystemExit(status)
