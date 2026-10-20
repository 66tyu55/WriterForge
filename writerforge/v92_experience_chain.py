"""V92 incremental migration of the EXISTING fifteen V80 experience CAS chain.

No fresh model or novel source, no guesswork. The only accepted inputs are
bytes individually verified against their R2 SHA and their predecessor links.
All original Chinese reflection strings survive in each private V91 object.
The public manifest has metadata and hashes only, never literary prose.

This is an experience-chain migration, NOT a graph-wide persistent snapshot,
nor independent literary truth or WRITE approval. A missing/broken V80 link
is a hard error; do not silently skip chapters or create placeholder skills.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Callable

from .v91_experience_migration import (
    strict_roundtrip,restore_v91_experience,canonical,digest,is_sha,
)

FORMAT="writerforge.lifelong-experience-chain.v92"
SCHEMA_VERSION=1
CHAPTERS=15
MAX_MANIFEST_BYTES=65536
MAX_CHAIN_EXPERIENCE_BYTES=250000
ORIGINAL_V80_HEAD="ddbf86e87e3bf44900b4e5e4d8ffc2de99c9ed5d3c5aec98a69bfd8eb7cf2fe7"
V91_CH15_CAS="79dbfe144356d01bcd89bd237410925d838f98b1efe91e0aeab0edc3f93add4b"
V91_CH15_MANIFEST="5a8b3b78f8b68741d794f618d2e701ac653397dd2a1e74822bba63cd09c9ee0f"
V82_FINAL_BATCH="d46ffec05927dfba3f2819089e76e79f720db2a2f3f6793b56965ac6413c177f"
V82_FINAL_JOURNAL="3da56cc46115548c5198a65cb6124e3c03d9bdfdb1f0460950177735a99d1cb2"
SOURCE_SHA="0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd"
SOURCE_KEY_SHA="370400053cded15ca89e3232e7be84b28aa20ca70542150138bef6201dc7cb22"
REFLECTION_FIELDS=("observed_weakness","next_strategy","open_question","confidence_limit")


class V92ChainError(ValueError):
    pass


def need(condition,code):
    if not condition:
        raise V92ChainError(code)


def sha(raw):
    return sha256(raw).hexdigest()


def _check_exact_predecessor(row,chapter,next_known):
    need(row["chapter"]==chapter,
         "WF92_V80_EXPERIENCE_CHAPTER_MISSING_OR_REORDERED")
    prev=row["previous_experience_sha256"]
    need(prev is None if chapter==1 else is_sha(prev),
         "WF92_V80_CHAIN_WRONG_GENESIS_OR_BROKEN_LINK")
    if next_known is not None:
        need(next_known["previous_experience_sha256"]==
             row["original_v80_cas_sha256"],
             "WF92_V80_CHAIN_FORK_OR_REORDER")
    return prev


def walk_v80_chain(fetch:Callable[[str],bytes], *,
                   head:str=ORIGINAL_V80_HEAD,
                   required_source_sha:str=SOURCE_SHA,
                   required_source_key_sha:str=SOURCE_KEY_SHA):
    """Returns entries sorted 1..15 and private migrated V91 objects by chapter.

    Fully audits the chain BEFORE permitting any write. This call is
    read-only, even when fetch is backed by live R2.
    """
    need(callable(fetch) and is_sha(head) and
         is_sha(required_source_sha) and
         is_sha(required_source_key_sha),
         "WF92_FROZEN_INPUTS_INVALID")
    by_chapter={}
    private_objects={}
    cursor=head
    seen=set()
    successor=None
    total_bytes=0
    for chapter in range(CHAPTERS,0,-1):
        need(is_sha(cursor) and cursor not in seen,
             "WF92_V80_EXPERIENCE_CYCLE_OR_TRUNCATION")
        seen.add(cursor)
        try:
            raw=fetch(cursor)
        except Exception as exc:
            raise V92ChainError("WF92_V80_REMOTE_EXPERIENCE_MISSING") from exc
        need(isinstance(raw,bytes) and sha(raw)==cursor,
             "WF92_V80_CONTENT_ADDRESS_MISMATCH")
        total_bytes+=len(raw)
        need(total_bytes<=MAX_CHAIN_EXPERIENCE_BYTES,
             "WF92_V80_EXPERIENCE_CHAIN_BYTE_LIMIT")
        try:
            upgraded=strict_roundtrip(raw,cursor)
        except (ValueError,TypeError) as exc:
            raise V92ChainError(
                "WF92_V80_CHINESE_SCHEMA_OR_ENCODING_UNRECOVERABLE") from exc
        need(upgraded["source_sha256"]==required_source_sha and
             upgraded["source_key_sha256"]==required_source_key_sha,
             "WF92_V80_OTHER_BOOK_OR_SOURCE_VERSION")
        need(upgraded["chapter"]==chapter,
             "WF92_V80_CHAPTER_ORDER_CHANGED")
        previous=_check_exact_predecessor(upgraded,chapter,successor)
        migrated=canonical(upgraded)
        digest_migrated=sha(migrated)
        if chapter==15:
            need(digest_migrated==V91_CH15_CAS,
                 "WF92_ALREADY_VERIFIED_CH15_MIGRATION_CHANGED")
        by_chapter[chapter]={
            "chapter":chapter,
            "original_v80_cas_sha256":cursor,
            "previous_v80_cas_sha256":previous,
            "v91_experience_cas_sha256":digest_migrated,
            "migration_receipt_sha256":
                upgraded["migration_receipt_sha256"],
            "reflection_sha256":{
                key:sha(upgraded["reflection"][key].encode("utf8"))
                for key in REFLECTION_FIELDS},
            "v80_chapter1_mixed_pilot_not_strict_pass_a":chapter==1,
            "original_book_text_embedded":False,
            "independent_literary_quality_verified":False,
            "writer_permission":False,
        }
        private_objects[chapter]=migrated
        successor=upgraded
        cursor=previous
    need(cursor is None and len(by_chapter)==CHAPTERS,
         "WF92_V80_CHAIN_GENESIS_NOT_TERMINATED")
    records=[by_chapter[n] for n in range(1,CHAPTERS+1)]
    return records,private_objects


def make_manifest(rows):
    need(type(rows) is list and len(rows)==CHAPTERS and
         all(type(x) is dict for x in rows),
         "WF92_MANIFEST_MUST_CONTAIN_ALL_FIFTEEN")
    need([r["chapter"] for r in rows]==list(range(1,CHAPTERS+1)),
         "WF92_MANIFEST_GAPS_OR_DUPLICATE_CHAPTERS")
    prev=None
    for chapter,row in enumerate(rows,1):
        need(is_sha(row.get("original_v80_cas_sha256")) and
             is_sha(row.get("v91_experience_cas_sha256")) and
             is_sha(row.get("migration_receipt_sha256")) and
             row.get("previous_v80_cas_sha256")==prev and
             row.get("v80_chapter1_mixed_pilot_not_strict_pass_a") is
             (chapter==1) and
             row.get("independent_literary_quality_verified") is False and
             row.get("writer_permission") is False and
             row.get("original_book_text_embedded") is False and
             type(row.get("reflection_sha256")) is dict and
             set(row["reflection_sha256"])==set(REFLECTION_FIELDS) and
             all(is_sha(s) for s in row["reflection_sha256"].values()),
             "WF92_EXPERIENCE_CHAIN_ENTRY_MISSING_OR_TAMPERED")
        prev=row["original_v80_cas_sha256"]
    need(prev==ORIGINAL_V80_HEAD and
         rows[-1]["v91_experience_cas_sha256"]==V91_CH15_CAS,
         "WF92_MANIFEST_HEAD_NOT_V82_OR_V91")
    payload={
        "format":FORMAT,
        "schema_version":SCHEMA_VERSION,
        "chapter_count":CHAPTERS,
        "chapters":rows,
        "ordered_source_chain_sha256":sha(canonical(rows)),
        "old_v82_batch_sha256":V82_FINAL_BATCH,
        "old_v82_journal_sha256":V82_FINAL_JOURNAL,
        "old_v80_head_experience_sha256":ORIGINAL_V80_HEAD,
        "previous_v91_chapter15_manifest_sha256":V91_CH15_MANIFEST,
        "source_sha256":SOURCE_SHA,
        "v91_cloud_objects_include_full_chinese_experience":True,
        "old_v80_cas_objects_overwritten":False,
        "chapter1_pilot_historical_exception_preserved":True,
        "fact_journal_sqlite_graph_included":False,
        "complete_lifelong_brain_verified":False,
        "model_retraining_performed":False,
        "original_novel_prose_in_manifest":False,
        "literary_quality_independently_verified":False,
        "write_skill_promotion_permitted":False,
    }
    raw=canonical(payload)
    need(len(raw)<=MAX_MANIFEST_BYTES,
         "WF92_CHAIN_MANIFEST_SIZE_TOO_LARGE")
    return payload


def verify_manifest(raw:bytes,fetch:Callable[[str],bytes]):
    """Cold audit of all original AND migrated R2 objects, no writes."""
    need(type(raw) is bytes and 0<len(raw)<=MAX_MANIFEST_BYTES,
         "WF92_MANIFEST_BYTES_NOT_BOUNDED")
    try:
        from .v91_experience_migration import strict_json
        doc=strict_json(raw)
    except ValueError as exc:
        # V91 strict_json has 16K cap; V92 has its own 64K manifest budget.
        import json
        try:
            def pairs(values):
                result={}
                for k,v in values:
                    if k in result:
                        raise ValueError("duplicate")
                    result[k]=v
                return result
            doc=json.loads(raw.decode("utf8","strict"),
                           object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(
                               ValueError("not finite")))
        except (ValueError,UnicodeError,TypeError):
            raise V92ChainError("WF92_MANIFEST_UTF8_OR_JSON_GARBLED") from None
    # Re-run the primary chain traversal. No manifest claims are trusted
    # without independent reading of the source content-addressed objects.
    rows,migrated=walk_v80_chain(fetch)
    expected=make_manifest(rows)
    need(doc==expected,
         "WF92_COLD_MANIFEST_SOURCE_LINEAGE_OR_POLICY_CHANGED")
    for i in range(1,CHAPTERS+1):
        cas=rows[i-1]["v91_experience_cas_sha256"]
        need(fetch(cas)==migrated[i],
             "WF92_COLD_MIGRATED_CHINESE_EXPERIENCE_CHANGED")
    return {
        "status":"WF92_ALL_FIFTEEN_CAS_EXPERIENCES_COLD_VERIFIED",
        "manifest_sha256":sha(raw),
        "verified_chapters":CHAPTERS,
        "verified_legacy_experiences":CHAPTERS,
        "verified_v91_experiences":CHAPTERS,
        "chapter1_mixed_pilot_disclosure_preserved":True,
        "last_v82_original_cas_sha256":ORIGINAL_V80_HEAD,
        "old_v82_cas_untouched":True,
        "entire_factjournal_sqlite_graph_not_included":True,
        "independent_literary_success_proven":False,
        "new_model_calls":0,
        "new_r2_writes":0,
        "source_chinese_reflections_logged":False,
    }
