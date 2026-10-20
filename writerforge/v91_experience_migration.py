"""V91 durable, strict, reversible VIEW of existing V80 R2 experiences.

Preserve full Chinese reflection text PRIVATE in the migration result (not
only SHA/keywords). Never rewrite legacy R2 CAS and never turn a reflection
into an approved literary skill. Without the source R2 blob and its verified
SHA the migration MUST refuse. This is not a model weight update.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re

FORMAT="writerforge.lifelong-experience.v91"
SCHEMA_VERSION=1
LEGACY_FORMAT="wf.learn.experience.v80"
SHA=re.compile(r"[0-9a-f]{64}\Z")
REFLECTION_FIELDS=frozenset((
    "observed_weakness","next_strategy","open_question","confidence_limit"))
MAX_RAW_BYTES=16_384
MAX_REFLECTION_CHARS=200
MAX_MIGRATED_BYTES=8192


class V91ExperienceMigrationError(ValueError):
    pass


def need(condition,code):
    if not condition:
        raise V91ExperienceMigrationError(code)


def is_sha(s):
    return isinstance(s,str) and SHA.fullmatch(s) is not None


def canonical(doc):
    return json.dumps(doc,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode("utf8")


def digest(raw):
    return sha256(raw).hexdigest()


def _safe_text(value):
    if not (isinstance(value,str) and 1<=len(value)<=MAX_REFLECTION_CHARS):
        return False
    if "\ufffd" in value or "\x00" in value:
        return False
    try:
        raw=value.encode("utf8","strict")
        return raw.decode("utf8","strict")==value
    except UnicodeError:
        return False


def _unique_pairs(pairs):
    d={}
    for key,value in pairs:
        if key in d:
            raise V91ExperienceMigrationError(
                "WF91_DUPLICATE_JSON_FIELD_REJECTED")
        d[key]=value
    return d


def _reject_constant(_value):
    raise V91ExperienceMigrationError("WF91_NONFINITE_JSON_REJECTED")


def strict_json(raw):
    need(isinstance(raw,bytes) and 0<len(raw)<=MAX_RAW_BYTES,
         "WF91_PRIVATE_EXPERIENCE_BYTES_INVALID")
    try:
        text=raw.decode("utf8","strict")
        need("\ufffd" not in text,"WF91_REPLACEMENT_CHARACTER_REJECTED")
        data=json.loads(text,object_pairs_hook=_unique_pairs,
                        parse_constant=_reject_constant)
        canonical(data)
    except (UnicodeError,ValueError,TypeError,OverflowError):
        raise V91ExperienceMigrationError(
            "WF91_UTF8_OR_JSON_RESTORE_INVALID") from None
    need(isinstance(data,dict),"WF91_EXPERIENCE_NOT_OBJECT")
    return data


def _validate_reflection(value):
    need(isinstance(value,dict) and
         set(value)==REFLECTION_FIELDS and
         all(_safe_text(v) for v in value.values()),
         "WF91_EXPERIENCE_REFLECTION_GARBLED_OR_TRUNCATED")


def migrate_v80_experience(*,legacy_raw:bytes,legacy_cas_sha256:str):
    """Derive a private V91 versioned object, never mutate the old CAS blob."""
    need(is_sha(legacy_cas_sha256) and
         digest(legacy_raw)==legacy_cas_sha256,
         "WF91_LEGACY_CAS_HASH_MISMATCH")
    old=strict_json(legacy_raw)
    fields={
        "format","source_sha256","source_key_sha256","chapter",
        "analysis_sha256","previous_experience_sha256","model",
        "reflection","applied_to_next_chapter_prompts",
        "literary_quality_independently_verified"}
    need(set(old)==fields and old["format"]==LEGACY_FORMAT and
         is_sha(old["source_sha256"]) and
         is_sha(old["source_key_sha256"]) and
         is_sha(old["analysis_sha256"]) and
         (old["previous_experience_sha256"] is None or
          is_sha(old["previous_experience_sha256"])) and
         type(old["chapter"]) is int and 1<=old["chapter"]<=2000 and
         old["model"]=="deepseek-flash" and
         type(old["applied_to_next_chapter_prompts"]) is bool and
         old["literary_quality_independently_verified"] is False,
         "WF91_LEGACY_EXPERIENCE_CONTRACT_MISMATCH")
    _validate_reflection(old["reflection"])
    payload={
        "format":FORMAT,"schema_version":SCHEMA_VERSION,
        "kind":"LITERARY_EXPERIENCE_CANDIDATE",
        "original_v80_cas_sha256":legacy_cas_sha256,
        "original_v80_format":LEGACY_FORMAT,
        "source_sha256":old["source_sha256"],
        "source_key_sha256":old["source_key_sha256"],
        "chapter":old["chapter"],
        "analysis_sha256":old["analysis_sha256"],
        "previous_experience_sha256":old[
            "previous_experience_sha256"],
        "model_source":old["model"],
        "original_applied_to_next_chapter_prompts":old[
            "applied_to_next_chapter_prompts"],
        "reflection":dict(old["reflection"]),
        "review_status":"UNVERIFIED_LEGACY",
        "literary_semantics_independently_verified":False,
        "eligible_for_WF_WRITE":False,
        "skill_promotion_approved":False,
        "model_weights_updated":False,
        "conversion_is_structural_not_semantic":True,
        "source_prose_embedded":False,
    }
    raw=canonical(payload)
    need(len(raw)<=MAX_MIGRATED_BYTES,
         "WF91_MIGRATED_EXPERIENCE_OVERSIZED")
    return {**payload,"migration_receipt_sha256":digest(raw)}


def restore_v91_experience(raw:bytes):
    """Restores full reflection exactly, with explicit version rejection."""
    record=strict_json(raw)
    need(record.get("format")==FORMAT,
         "WF91_UNKNOWN_EXPERIENCE_FORMAT")
    need(type(record.get("schema_version")) is int and
         record["schema_version"]==SCHEMA_VERSION,
         "WF91_UNSUPPORTED_SCHEMA_VERSION")
    expected_fields={
        "format","schema_version","kind","original_v80_cas_sha256",
        "original_v80_format","source_sha256","source_key_sha256",
        "chapter","analysis_sha256","previous_experience_sha256",
        "model_source","original_applied_to_next_chapter_prompts",
        "reflection","review_status",
        "literary_semantics_independently_verified",
        "eligible_for_WF_WRITE","skill_promotion_approved",
        "model_weights_updated","conversion_is_structural_not_semantic",
        "source_prose_embedded","migration_receipt_sha256"}
    need(set(record)==expected_fields and
         is_sha(record["migration_receipt_sha256"]) and
         all(is_sha(record[k]) for k in (
            "source_sha256","source_key_sha256","analysis_sha256",
            "original_v80_cas_sha256")) and
         (record["previous_experience_sha256"] is None or
          is_sha(record["previous_experience_sha256"])) and
         type(record["chapter"]) is int and record["chapter"]>=1 and
         record["kind"]=="LITERARY_EXPERIENCE_CANDIDATE" and
         record["original_v80_format"]==LEGACY_FORMAT and
         record["model_source"]=="deepseek-flash" and
         type(record["original_applied_to_next_chapter_prompts"]) is bool and
         record["review_status"]=="UNVERIFIED_LEGACY" and
         record["literary_semantics_independently_verified"] is False and
         record["eligible_for_WF_WRITE"] is False and
         record["skill_promotion_approved"] is False and
         record["model_weights_updated"] is False and
         record["conversion_is_structural_not_semantic"] is True and
         record["source_prose_embedded"] is False,
         "WF91_MIGRATED_EXPERIENCE_SCHEMA_INVALID")
    _validate_reflection(record["reflection"])
    receipt=record["migration_receipt_sha256"]
    payload={k:v for k,v in record.items()
             if k!="migration_receipt_sha256"}
    need(digest(canonical(payload))==receipt,
         "WF91_MIGRATED_EXPERIENCE_HASH_MISMATCH")
    need(len(canonical(record))<=MAX_MIGRATED_BYTES,
         "WF91_MIGRATED_EXPERIENCE_TOO_LARGE")
    return record


def strict_roundtrip(legacy_raw, legacy_cas_sha256):
    record=migrate_v80_experience(
        legacy_raw=legacy_raw,legacy_cas_sha256=legacy_cas_sha256)
    reopened=restore_v91_experience(canonical(record))
    need(reopened==record,"WF91_MIGRATION_ROUNDTRIP_CHANGED")
    return reopened
