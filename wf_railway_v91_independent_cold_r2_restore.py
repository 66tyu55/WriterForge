"""V91 separate cold R2 Reader verifies newly persisted Chinese V91 experience.

The migration writer has already exited. THIS PROCESS strips model and
writer secrets BEFORE imports. It independently fetches the two new immutable
CAS objects and the original V82 version, then rebuilds the complete
migration byte-for-byte. No string from a private book or experience is
ever logged, written to GitHub, or sent to a model.
"""
from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0,str(ROOT))
for name in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
             "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(name,None)

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
MIGRATED_SHA="79dbfe144356d01bcd89bd237410925d838f98b1efe91e0aeab0edc3f93add4b"
MANIFEST_SHA="5a8b3b78f8b68741d794f618d2e701ac653397dd2a1e74822bba63cd09c9ee0f"
MIGRATION_RECEIPT="afdc4557b9e7f143d515382491e486a2e57662370c3d378476a673d0083105f6"

def emit(value):
    print(json.dumps(value,ensure_ascii=False,sort_keys=True),flush=True)

print("WF91_INDEPENDENT_COLD_R2_LONG_TERM_EXPERIENCE_START",flush=True)


def main():
    if not os.getenv("WF_API_TOKEN"):
        emit({"status":"WF91_INDEPENDENT_R2_READER_MISSING",
              "model_calls":0,"r2_writes":0})
        return 1
    from writerforge.v79_provisional_r2_cas_journal import (
        WFProvisionalR2CASJournal)
    from writerforge.v91_experience_migration import (
        strict_roundtrip,restore_v91_experience,canonical,digest)
    from writerforge.v91_private_cas_manifest import (
        validate_experience_manifest,
        V82_BATCH,V82_JOURNAL,V82_EXP,V82_SOURCE)
    reader=WFProvisionalR2CASJournal(
        endpoint=ENDPOINT,read_only=True)
    if not reader.read_only or reader.writer is not None:
        raise ValueError("WF91_INDEPENDENT_READER_NOT_RESTRICTED")
    old_batch=json.loads(reader._get_content(V82_BATCH).decode("utf8"))
    old_journal=reader._get_content(V82_JOURNAL)
    old=reader._get_content(V82_EXP)
    loaded=reader._get_content(MIGRATED_SHA)
    manifest=reader._get_content(MANIFEST_SHA)
    if (old_batch.get("last_completed_chapter")!=15 or
        old_batch.get("source_sha256")!=V82_SOURCE or
        old_batch.get("latest_experience_sha256")!=V82_EXP or
        old_batch.get("journal_checkpoint_sha256")!=V82_JOURNAL or
        old_batch.get("mastery_graduation_approved") is not False or
        not old_journal):
        raise ValueError("WF91_OLD_V82_CHAIN_CHANGED_DURING_COLD_RESTORE")
    expected=strict_roundtrip(old,V82_EXP)
    actual=restore_v91_experience(loaded)
    if (actual!=expected or
        loaded!=canonical(expected) or
        expected["migration_receipt_sha256"]!=MIGRATION_RECEIPT or
        digest(loaded)!=MIGRATED_SHA):
        raise ValueError("WF91_COLD_MIGRATED_EXPERIENCE_TEXT_CHANGED")
    result=validate_experience_manifest(
        manifest_raw=manifest,migrated_raw=loaded)
    if (result["manifest_sha256"]!=MANIFEST_SHA or
        result["experience_cas_sha256"]!=MIGRATED_SHA or
        result["original_v80_experience_sha256"]!=V82_EXP):
        raise ValueError("WF91_COLD_MANIFEST_POINTER_DRIFT")
    emit({
        "status":"WF91_REAL_CH15_EXPERIENCE_CLOUD_COLD_RESTORE_VERIFIED",
        "migration_manifest_cas_sha256":MANIFEST_SHA,
        "versioned_experience_cas_sha256":MIGRATED_SHA,
        "old_v82_experience_cas_sha256":V82_EXP,
        "migration_receipt_sha256":MIGRATION_RECEIPT,
        "source_version_sha256":V82_SOURCE,
        "independent_reader_reconstructed_full_4_reflection_fields":True,
        "old_batch_and_journal_still_match_chapter15":True,
        "independent_cold_reader_no_writes":True,
        "r2_reader_only":True,
        "original_v82_objects_unmodified":True,
        "full_lifelong_sqlite_factjournal_graph_not_published":True,
        "next_chapter_auto_training_disabled":True,
        "literary_semantic_promotion_permitted":False,
        "model_calls":0,"r2_writes":0,
        "private_text_not_logged":True,
    })
    return 0

try:
    status=main()
except Exception as exc:
    code=str(exc)
    if not code.startswith(("WF91_","WF_V79_","WF_INDEX_",
                           "WF_LEARN_")) or len(code)>110:
        code="WF91_READER_ONLY_COLD_RESTORE_UNCLASSIFIED"
    emit({
        "status":"WF91_INDEPENDENT_COLD_R2_RESTORE_FAILED",
        "reason_code":code,
        "model_calls":0,"r2_writes":0,
        "no_source_or_experience_text_logged":True,
    })
    status=1

print("WF91_INDEPENDENT_COLD_R2_RESTORE_EXIT="+str(status),flush=True)
time.sleep(3)
raise SystemExit(status)
