"""V91 additive private R2 CAS manifest for one REAL legacy experience.

The R2 payload is immutable and content-addressed. It does not replace the
old V82 checkpoint/journal or claim to snapshot WriterForgeDB+FactJournal.
Semantic review and WRITE authority remain explicitly FALSE.
"""
from __future__ import annotations

from hashlib import sha256
from .v91_experience_migration import (
    strict_json,canonical,restore_v91_experience,is_sha,
)

FORMAT="writerforge.lifelong-experience.private-cas-manifest.v91"
SCHEMA_VERSION=1
V82_BATCH="d46ffec05927dfba3f2819089e76e79f720db2a2f3f6793b56965ac6413c177f"
V82_JOURNAL="3da56cc46115548c5198a65cb6124e3c03d9bdfdb1f0460950177735a99d1cb2"
V82_EXP="ddbf86e87e3bf44900b4e5e4d8ffc2de99c9ed5d3c5aec98a69bfd8eb7cf2fe7"
V82_SOURCE="0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd"
MAX_MANIFEST_BYTES=8192


class V91CloudManifestError(ValueError):
    pass


def need(cond,reason):
    if not cond:
        raise V91CloudManifestError(reason)


def digest(raw):
    return sha256(raw).hexdigest()


def create_experience_manifest(*,migrated_raw,migrated_cas_sha256):
    need(is_sha(migrated_cas_sha256) and
         digest(migrated_raw)==migrated_cas_sha256,
         "WF91_MIGRATED_CAS_NOT_CONTENT_ADDRESSED")
    obj=restore_v91_experience(migrated_raw)
    need(obj["original_v80_cas_sha256"]==V82_EXP and
         obj["source_sha256"]==V82_SOURCE and
         obj["chapter"]==15 and
         obj["eligible_for_WF_WRITE"] is False,
         "WF91_MIGRATION_NOT_FROZEN_CH15")
    payload={
        "format":FORMAT,
        "schema_version":SCHEMA_VERSION,
        "source_sha256":V82_SOURCE,
        "chapter":15,
        "original_v80_batch_sha256":V82_BATCH,
        "original_v80_journal_sha256":V82_JOURNAL,
        "original_v80_experience_sha256":V82_EXP,
        "v91_experience_cas_sha256":migrated_cas_sha256,
        "v91_migration_receipt_sha256":
            obj["migration_receipt_sha256"],
        "immutable_old_r2_objects_preserved":True,
        "legacy_chapter_training_reused_not_repeated":True,
        "next_chapter_automatically_unlocked":False,
        "local_sqlite_memory_snapshot_included":False,
        "fact_journal_migrated_to_cloud":False,
        "external_literary_review_performed":False,
        "literary_skill_approved":False,
        "writer_eligible":False,
        "model_api_calls_for_migration":0,
        "original_novel_prose_embedded":False,
    }
    need(len(canonical(payload))<=MAX_MANIFEST_BYTES,
         "WF91_CLOUD_MANIFEST_TOO_LARGE")
    return payload


def validate_experience_manifest(*,manifest_raw,migrated_raw):
    need(isinstance(manifest_raw,bytes) and
         0<len(manifest_raw)<=MAX_MANIFEST_BYTES,
         "WF91_CLOUD_MANIFEST_BOUNDED_BYTES_REQUIRED")
    doc=strict_json(manifest_raw)
    need(type(doc.get("schema_version")) is int and
         doc["schema_version"]==SCHEMA_VERSION and
         doc.get("format")==FORMAT,
         "WF91_CLOUD_MANIFEST_UNKNOWN_VERSION_OR_FORMAT")
    expected=create_experience_manifest(
        migrated_raw=migrated_raw,
        migrated_cas_sha256=digest(migrated_raw))
    need(doc==expected,
         "WF91_CLOUD_MANIFEST_RECORDS_CHANGED_OR_FALSE_PROMOTION")
    return {
        "status":"WF91_PRIVATE_CAS_MANIFEST_AND_FULL_CHINESE_EXPERIENCE_VERIFIED",
        "manifest_sha256":digest(manifest_raw),
        "experience_cas_sha256":digest(migrated_raw),
        "original_v80_experience_sha256":V82_EXP,
        "migration_receipt_sha256":
            expected["v91_migration_receipt_sha256"],
        "source_chapter":15,
        "full_experience_text_read_back_privately":True,
        "external_literary_quality_independently_verified":False,
        "cross_db_sqlite_snapshot_included":False,
        "can_auto_promote_skills":False,
        "may_trigger_new_chapter_training":False,
        "novel_text_or_private_strategy_in_report":False,
    }
