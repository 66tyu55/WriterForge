"""V91 one-time bounded private R2 persistence for a verified V82 experience.

ONLY TWO NEW IMMUTABLE CAS OBJECTS: full Chinese V91 experience and its
manifest. Legacy V82 batch, journal and chapter15 blobs stay unchanged.
No model calls, no extra credential names, no raw prose/strategy in logs.
If a write fails, the old V82 pointers remain authoritative. A new reader
process must independently cold restore before declaring cloud persistence.
"""
from __future__ import annotations

import json
import os
import sys
import time
from hashlib import sha256
from pathlib import Path

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0,str(ROOT))
os.environ.pop("DEEPSEEK_API_KEY",None)
os.environ.pop("DISCOVERY_API_KEY",None)
os.environ.pop("WF_LEARN_UPLOAD_TOKEN",None)

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"

def emit(value):
    print(json.dumps(value,sort_keys=True,ensure_ascii=False),flush=True)


def main():
    for name in ("WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN"):
        if not os.environ.get(name):
            emit({"status":"WF91_EXISTING_R2_SECRET_MISSING",
                  "name":name,"model_calls":0})
            return 1
    from writerforge.v79_provisional_r2_cas_journal import (
        WFProvisionalR2CASJournal)
    from writerforge.v91_experience_migration import (
        strict_roundtrip,restore_v91_experience,canonical,digest)
    from writerforge.v91_private_cas_manifest import (
        create_experience_manifest,validate_experience_manifest,
        V82_BATCH,V82_JOURNAL,V82_EXP,V82_SOURCE)
    written={}
    try:
        journal=WFProvisionalR2CASJournal(endpoint=ENDPOINT)
        journal.require_writer_ready()
        old_batch=json.loads(journal._get_content(V82_BATCH).decode("utf8"))
        old_exp_raw=journal._get_content(V82_EXP)
        if (old_batch.get("source_sha256")!=V82_SOURCE or
            old_batch.get("last_completed_chapter")!=15 or
            old_batch.get("latest_experience_sha256")!=V82_EXP or
            old_batch.get("journal_checkpoint_sha256")!=V82_JOURNAL or
            old_batch.get("mastery_graduation_approved") is not False):
            raise ValueError("WF91_OLD_V82_CHECKPOINT_MISMATCH")
        migrated=strict_roundtrip(old_exp_raw,V82_EXP)
        raw=canonical(migrated)
        expect_sha=digest(raw)
        actual_sha,was_created=journal._put_content(raw)
        if actual_sha!=expect_sha:
            raise ValueError("WF91_CLOUD_MIGRATED_CAS_SHA_CHANGED")
        recovered=restore_v91_experience(
            journal._get_content(actual_sha))
        if recovered!=migrated:
            raise ValueError("WF91_CLOUD_EXPERIENCE_ROUNDTRIP_CHANGED")
        written["experience"]=actual_sha
        emit({
            "status":"WF91_IMMUTABLE_CHINESE_EXPERIENCE_R2_SAVED",
            "new_experience_sha256":actual_sha,
            "new_object_created":was_created,
            "source_v80_experience_sha256":V82_EXP,
            "reflections_recovered_exactly":True,
            "model_calls":0,
            "legacy_V82_CAS_rewritten":False,
            "private_text_logged":False,
        })
        manifest=create_experience_manifest(
            migrated_raw=raw,migrated_cas_sha256=actual_sha)
        manifest_raw=canonical(manifest)
        expected_manifest_sha=digest(manifest_raw)
        manifest_sha,manifest_created=journal._put_content(manifest_raw)
        if manifest_sha!=expected_manifest_sha:
            raise ValueError("WF91_CLOUD_MANIFEST_SHA_MISMATCH")
        independent_local=validate_experience_manifest(
            manifest_raw=journal._get_content(manifest_sha),
            migrated_raw=journal._get_content(actual_sha))
        if independent_local["experience_cas_sha256"]!=actual_sha:
            raise ValueError("WF91_CLOUD_MANIFEST_LINK_BROKEN")
        written["manifest"]=manifest_sha
        emit({
            "status":"WF91_VERSIONED_PRIVATE_CAS_EXPERIENCE_MANIFEST_SAVED",
            "manifest_sha256":manifest_sha,
            "new_manifest_created":manifest_created,
            "migrated_experience_sha256":actual_sha,
            "v91_migration_receipt_sha256":
                migrated["migration_receipt_sha256"],
            "old_v82_experience_sha256":V82_EXP,
            "original_v82_checkpoint_still_authoritative":True,
            "r2_old_objects_changed":False,
            "new_private_cas_objects_tried":2,
            "full_SQLite_FactJournal_combined_checkpoint_published":False,
            "external_literary_review_performed":False,
            "skill_promotion_approved":False,
            "deepseek_calls":0,
            "source_prose_or_private_strategy_logged":False,
            "next_step":"COLD_READER_PROCESS_MUST_INDEPENDENTLY_VERIFY",
        })
        return 0
    except Exception as exc:
        msg=str(exc)
        if not msg.startswith(("WF91_","WF_V79_","WF_INDEX_",
                               "WF_LEARN_")) or len(msg)>110:
            msg="WF91_PRIVATE_CAS_WRITE_UNCLASSIFIED"
        emit({
            "status":"WF91_PRIVATE_CAS_MIGRATION_STOPPED",
            "reason_code":msg,
            "saved_sha_pointers_before_error":written,
            "original_v82_source_unchanged":True,
            "requires_reader_cold_recovery":True,
            "no_automatic_model_retry":True,
            "model_calls":0,"private_text_logged":False,
        })
        return 1


print("WF91_NEW_PRIVATE_EXPERIENCE_CAS_MIGRATION_STARTED",flush=True)
code=main()
print("WF91_NEW_PRIVATE_EXPERIENCE_CAS_MIGRATION_EXIT="+str(code),flush=True)
time.sleep(4)
raise SystemExit(code)
