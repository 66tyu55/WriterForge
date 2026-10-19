"""V82: REAL WF next batch (chapters 11-15), max 150k tokens total.

Starts from PRECISE R2 CAS checkpoints of independently verified V81.
Never revisits/repays ten completed chapters. Loads the model's OWN
chapter-10 experience, feeds its "next_strategy" into chapter-11 reads.
Applies strictly complete PASS A before PASS B, each unit stored in R2
content-addressed immutable objects and locally read-back verified.
Stops if the user-agreed 150k aggregate budget or 96 requests is reached.
No GitHub Actions or automatic retries.

The independent quality/transfer experiment remains separate from the
training model's own claims; this run cannot certify literary mastery.
"""
from __future__ import annotations
import json,os,sys,time,types
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
pkg=types.ModuleType("writerforge")
pkg.__package__="writerforge"
pkg.__path__=[str(ROOT/"writerforge")]
sys.modules["writerforge"]=pkg
from writerforge.v79_provisional_r2_cas_journal import WFProvisionalR2CASJournal
from writerforge.r2_learn_journal import hexdigest

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
B00_SHA="c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4"
KEY_SHA="370400053cded15ca89e3232e7be84b28aa20ca70542150138bef6201dc7cb22"
SOURCE_SHA="0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd"
ORIGINAL_BYTES=4009069
PREV_JOURNAL="61a52125708a180b3305e28721d6e1797c0ab619df18a1bac7822988707a9c33"
PREV_BATCH="e28490de3f0b17875ed23418726a8b8692b3029c1501b30da314080f4edb0901"
PREV_EXPERIENCE="feee04808c6b14f84c16989d98b031937a897395f3d008c43e17b3449f9077e3"
START_CHAPTER=11
STOP_CHAPTER=15
MAX_TOTAL_TOKENS=150000

def emit(obj):
    print(json.dumps(obj,ensure_ascii=False,sort_keys=True),flush=True)

def main():
    for name in ("WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN","DEEPSEEK_API_KEY"):
        if not os.getenv(name):
            emit({"status":"WF_V82_MISSING_EXISTING_CREDENTIAL_NAME",
                  "credential_name":name,"model_calls":0})
            return 1
    model=None
    journal=None
    batch=None
    try:
        journal=WFProvisionalR2CASJournal(
            endpoint=ENDPOINT,checkpoint_sha=PREV_JOURNAL,progress=emit)
        journal.require_writer_ready()
        old=json.loads(journal._get_content(PREV_BATCH))
        if (old.get("format")!="wf.learn.150k-batch-progress.v80"
            or old.get("last_completed_chapter")!=10
            or old.get("source_sha256")!=SOURCE_SHA
            or old.get("journal_checkpoint_sha256")!=PREV_JOURNAL
            or old.get("latest_experience_sha256")!=PREV_EXPERIENCE):
            raise ValueError("WF_V82_PREVIOUS_BATCH_NOT_VERIFIED")
        experience=json.loads(journal._get_content(PREV_EXPERIENCE))
        if (experience.get("format")!="wf.learn.experience.v80"
            or experience.get("chapter")!=10
            or experience.get("source_sha256")!=SOURCE_SHA
            or not isinstance(experience.get("reflection"),dict)
            or not isinstance(experience["reflection"].get("next_strategy"),str)
            or len(experience["reflection"]["next_strategy"])<1):
            raise ValueError("WF_V82_LAST_EXPERIENCE_NOT_VERIFIED")
        emit({"status":"WF_V82_PRIOR_10_CHAPTERS_R2_RESTORED_NO_RETRAIN",
              "prior_batch_sha256":PREV_BATCH,
              "prior_journal_sha256":PREV_JOURNAL,
              "prior_experience_sha256":PREV_EXPERIENCE,
              "earlier_paid_chapters_will_be_reread":False,
              "new_model_calls":0,
              "no_fourth_secret":True})
        from writerforge.bulk_inbox import BulkCatalog
        from writerforge.private_reading_remote import WFPrivateReadingClient
        from writerforge.private_r2_sql_smoke import download_one_verified
        from writerforge.wf_batch_supervisor import frozen_preselection
        from writerforge.wf_self_learning_admission import _scan_document
        from writerforge.wf_charset_byte_review import byte_charset_audit
        from writerforge.v80_large_chapter_batch import WFLargeChapterBatch
        from writerforge.deepseek_flash_model import FlashBudget
        from writerforge.wf_learn_model_registry import new_wf_learn_model
        with TemporaryDirectory(prefix="wf-v82-ch11-15-") as folder:
            root=Path(folder)
            cat=BulkCatalog(root/"inventory.sqlite3")
            try:
                source=WFPrivateReadingClient(endpoint=ENDPOINT)
                inventory=source.inventory_to_catalog(cat)
                if inventory["all_folders_complete"] is not True:
                    raise ValueError("WF_V82_R2_INVENTORY_INCOMPLETE")
                rows,freeze=frozen_preselection(cat)
                if freeze["preselection_digest_sha256"]!=B00_SHA:
                    raise ValueError("WF_V82_B00_FROZEN_COHORT_CHANGED")
                row=rows["仙侠"][0]
                original_key=row["object_key"]
                if sha256(original_key.encode("utf8")).hexdigest()!=KEY_SHA:
                    raise ValueError("WF_V82_B00_SOURCE_KEY_CHANGED")
                local=root/"source.txt"
                transfer=download_one_verified(source,row,local)
                if transfer["source_sha256"]!=SOURCE_SHA or transfer["bytes"]!=ORIGINAL_BYTES:
                    raise ValueError("WF_V82_ORIGINAL_CONTENT_CHANGED")
                encode=byte_charset_audit(
                    local,expected_source_sha256=SOURCE_SHA,
                    expected_size=ORIGINAL_BYTES,expected_key_sha256=KEY_SHA)
                if (encode["plausible_distinct_decoded_texts"]!=1 or
                    "gb18030" not in encode["unique_reading_codec_aliases"]):
                    raise ValueError("WF_V82_CHARSET_REVIEW_CHANGED")
                chapters,report=_scan_document(local,"gb18030")
                if (report["boundary_rule_disagreements"]!=0 or
                    report["duplicate_printed_numbers"]!=0 or
                    len(chapters)<STOP_CHAPTER):
                    raise ValueError("WF_V82_CHAPTER_IDENTITY_CHANGED")
                budget=FlashBudget(
                    max_calls=96,max_reserved_output_tokens=MAX_TOTAL_TOKENS,
                    max_total_tokens=MAX_TOTAL_TOKENS)
                model=new_wf_learn_model(budget=budget)
                batch=WFLargeChapterBatch(
                    journal=journal,model=model,original_key=original_key,
                    source_sha=SOURCE_SHA,progress=emit,batch_id="WF-V82-CH11-15-150K")
                # Keep chain back to V81 final checkpoint, but V82 budget
                # is a NEW independent 150k batch (not accumulated tokens).
                batch.last_batch_pointer=PREV_BATCH
                batch.previous_experience_sha=PREV_EXPERIENCE
                batch.earlier_strategy=experience["reflection"]["next_strategy"]
                emit({"status":"WF_V82_CHAPTER11_READING_WITH_SAVED_EXPERIENCE",
                      "chapter_range":[START_CHAPTER,STOP_CHAPTER],
                      "prior_strategy_sha256":hexdigest(
                          batch.earlier_strategy.encode("utf8")),
                      "literary_quality_verified":False})
                # Preflight the complete chosen interval before a paid call:
                # source SHA, deterministic boundaries, and protocol budgets.
                previews=[(ch.ordinal,batch.chapter_body(local,ch))
                          for ch in chapters[START_CHAPTER-1:STOP_CHAPTER]]
                projected_first_read_calls=sum(len(units) for _,units in previews)
                projected_total_calls=projected_first_read_calls+len(previews)*3
                if projected_total_calls>budget.max_calls:
                    raise ValueError("WF_V82_BUDGET_PREFLIGHT_CALLS_TOO_LARGE")
                if len(journal.event_addresses)+projected_first_read_calls+(
                    len(previews)*2)>300:
                    raise ValueError("WF_V82_R2_CAS_EVENT_BUDGET_TOO_LARGE")
                emit({"status":"WF_V82_FIVE_COMPLETE_CHAPTERS_PRECHECKED",
                      "planned_chapters":[chapter_no for chapter_no,_ in previews],
                      "planned_first_read_units":projected_first_read_calls,
                      "planned_max_calls":projected_total_calls,
                      "real_paid_model_calls_so_far":0,
                      "source_text_or_titles_logged":False})
                for chap in chapters[START_CHAPTER-1:STOP_CHAPTER]:
                    windows=batch.chapter_body(local,chap)
                    batch.complete(chapter=chap,windows=windows)
                emit({"status":"WF_V82_CH11_TO_15_R2_BATCH_COMPLETED",
                      "new_chapters":len(batch.finished_chapters),
                      "chapter_receipts":batch.finished_chapters,
                      "final_journal_sha256":journal.checkpoint_sha,
                      "final_batch_sha256":batch.last_batch_pointer,
                      "last_experience_sha256":batch.previous_experience_sha,
                      "prior_ten_chapters_not_retrained":True,
                      "new_model_usage":model.public_usage_report(),
                      "batch_budget":budget.public_receipt(),
                      "model_literary_mastery_not_proven":True,
                      "blind_transfer_test_pending":True})
                return 0
            finally:cat.close()
    except Exception as exc:
        reason=str(exc)
        if not reason.startswith(("WF_V82_","WF_V80_","WF_V79_",
            "WF_LEARN_","WF_FLASH_","WF_USAGE_","WF_INDEX_","WF_PRIVATE_",
            "WF_V71_","WF_CHARSET_","WF_PREFIX_","BULK_")):
            reason="WF_V82_UNEXPECTED_BATCH_STOP"
        emit({"status":"WF_V82_PAUSED_WITH_R2_CHECKPOINT",
              "reason_code":reason,
              "latest_journal_sha256":journal.checkpoint_sha if journal else None,
              "latest_batch_sha256":batch.last_batch_pointer if batch else PREV_BATCH,
              "completed_new_chapters":batch.finished_chapters if batch else [],
              "model_usage":model.public_usage_report() if model else None,
              "model_calls_not_automatically_retried":True,
              "literary_grade_unchanged":True,
              "novel_prose_logged":False})
        return 1

print("WF_V82_RESUME_CH7_REAL_TRAINING_START",flush=True)
ret=main()
print("WF_V82_TRAINING_EXIT="+str(ret),flush=True)
time.sleep(6)
raise SystemExit(ret)
