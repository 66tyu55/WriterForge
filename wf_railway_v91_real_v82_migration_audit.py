"""V91 real V82 chapter15 R2-to-versioned-memory read-only migration proof.

Run only after synthetic cold-restore regressions pass. NEW Railway process,
Reader credential ONLY: no model API, no R2 writer, no real payload written.
Private reflection strings stay in memory and are never logged or exported.
This confirms old experience bytes -> stable V91 representation, NOT that
the snapshot has been published to a persistent lifelong store.
"""
from __future__ import annotations
import json
import os
import sys
import time

ROOT=__import__("pathlib").Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
for name in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
             "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(name,None)

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
V82_BATCH="d46ffec05927dfba3f2819089e76e79f720db2a2f3f6793b56965ac6413c177f"
V82_JOURNAL="3da56cc46115548c5198a65cb6124e3c03d9bdfdb1f0460950177735a99d1cb2"
V82_EXPERIENCE="ddbf86e87e3bf44900b4e5e4d8ffc2de99c9ed5d3c5aec98a69bfd8eb7cf2fe7"
V82_SOURCE="0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd"

def emit(doc):
    print(json.dumps(doc,sort_keys=True,ensure_ascii=False),flush=True)

print("WF91_R2_READER_ONLY_REAL_CH15_MIGRATION_START",flush=True)

def main():
    if not os.getenv("WF_API_TOKEN"):
        emit({"status":"WF91_R2_READER_TOKEN_MISSING",
              "model_calls":0,"r2_writes":0})
        return 1
    from writerforge.v79_provisional_r2_cas_journal import (
        WFProvisionalR2CASJournal)
    from writerforge.v91_experience_migration import (
        strict_roundtrip,restore_v91_experience,canonical,digest)
    examiner=WFProvisionalR2CASJournal(
        endpoint=ENDPOINT,read_only=True)
    if examiner.writer is not None or not examiner.read_only:
        raise ValueError("WF91_READER_ACQUIRED_WRITER_ROLE")
    original=examiner._get_content(V82_EXPERIENCE)
    old_batch=json.loads(examiner._get_content(V82_BATCH).decode("utf8"))
    if (old_batch.get("format")!="wf.learn.150k-batch-progress.v80"
        or old_batch.get("source_sha256")!=V82_SOURCE
        or old_batch.get("last_completed_chapter")!=15
        or old_batch.get("latest_experience_sha256")!=V82_EXPERIENCE
        or old_batch.get("journal_checkpoint_sha256")!=V82_JOURNAL
        or old_batch.get("mastery_graduation_approved") is not False):
        raise ValueError("WF91_LEGACY_V82_PROGRESS_CHAIN_INVALID")
    versioned=strict_roundtrip(original,V82_EXPERIENCE)
    cold_again=restore_v91_experience(canonical(versioned))
    if (cold_again!=versioned or
        versioned["chapter"]!=15 or
        versioned["source_sha256"]!=V82_SOURCE or
        versioned["review_status"]!="UNVERIFIED_LEGACY" or
        versioned["eligible_for_WF_WRITE"] is not False or
        versioned["skill_promotion_approved"] is not False):
        raise ValueError("WF91_LEGACY_EXPERIENCE_RESTORE_STATE_CHANGED")
    fields=versioned["reflection"]
    if sorted(fields)!=[
        "confidence_limit","next_strategy",
        "observed_weakness","open_question"]:
        raise ValueError("WF91_LEGACY_REFLECTION_FIELDS_LOST")
    emit({
        "status":"WF91_REAL_V82_CH15_CHINESE_EXPERIENCE_MIGRATED_IN_MEMORY",
        "v82_original_cas_sha256":V82_EXPERIENCE,
        "v82_checkpoint_sha256":V82_JOURNAL,
        "source_sha256":V82_SOURCE,
        "chapter":versioned["chapter"],
        "target_format":versioned["format"],
        "target_schema_version":versioned["schema_version"],
        "migration_receipt_sha256":
            versioned["migration_receipt_sha256"],
        "field_sha256":{
            k:digest(v.encode("utf8")) for k,v in fields.items()},
        "reflection_fields_survived_exact_utf8":True,
        "semantic_review_status":"UNVERIFIED_LEGACY",
        "original_r2_object_not_modified":True,
        "permanent_new_r2_memory_snapshot_published":False,
        "new_model_calls":0,"r2_writes":0,
        "v49_graduation_status":"THIRD_STRIKE_FAILED",
        "second_literary_window":"LOCKED",
        "private_reflection_or_book_prose_logged":False,
    })
    return 0

try:
    code=main()
except Exception as e:
    valid_prefix=("WF91_","WF_V79_","WF_INDEX_","WF_LEARN_")
    error=str(e)
    if not error.startswith(valid_prefix) or len(error)>110:
        error="WF91_PRIVATE_MIGRATION_FAILED_UNCLASSIFIED"
    emit({"status":"WF91_R2_READER_ONLY_MIGRATION_FAILED",
          "reason_code":error,"model_calls":0,"r2_writes":0,
          "private_data_never_logged":True})
    code=1

print("WF91_R2_READER_ONLY_MIGRATION_EXIT="+str(code),flush=True)
time.sleep(3)
raise SystemExit(code)
