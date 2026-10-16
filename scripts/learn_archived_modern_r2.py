"""Continue modern source learning from already archived PRIVATE R2 originals.

Fail closed. Never fetch the lost 13-book bundle or use GPT/Drive for a source.
No complete text, chapter prose, secret, or source URL in stdout/artifacts.
A structural index is NOT model training nor independently verified literature.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import json
import os
import re
import sqlite3
import sys

from writerforge.db import WriterForgeDB
from writerforge.runtime import RuntimeEngine
from writerforge.modern_source import inspect_modern_source, study_modern_source, _encoding
from writerforge.source_study import chapter_number, StudyError
from writerforge.r2_storage import R2Config, R2StudyVault, _digest
from writerforge.single_work_runner import SingleWorkVault

@dataclass(frozen=True)
class Work:
    title: str
    protagonist: str
    genre: str
    source_sha256: str
    source_bytes: int
    min_chapters: int

# Pinned to 2026-10-16 CURRENT_HANDOFF; never silently substitute editions.
WORKS = {
    "fanrenxiuxian": Work("凡人修仙传", "韩立", "仙侠",
        "2fc1698410418bf136448807335c6359bf515b75e6f9c1e1d1f443a1c928e6cc",
        15079878, 1800),
    "doupo": Work("斗破苍穹", "萧炎", "玄幻",
        "8d2e617d7ea4742452b765393bb66b0b0bb8546f63b9ff88dff9d3f6a779c0f6",
        16085734, 1000),
    "wudongqiankun": Work("武动乾坤", "林动", "玄幻",
        "86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28",
        8254079, 900),
    "wanmeishijie": Work("完美世界", "石昊", "玄幻",
        "322e84872b2259d9210f84de63efd70d901a412dfefbe9bb9d52168eea56d481",
        14053175, 1500),
    "zhetian": Work("遮天", "叶凡", "玄幻",
        "9cbf8da97daceb36fbd85edd84e2874a9ceac28252c18386fecf167d5a95660b",
        13455412, 900),
    "manghuangji": Work("莽荒纪", "纪宁", "玄幻",
        "f7aee869e201b4171e40a3ff9230e794f01fdc959d372017b8982635668be3d5",
        8961764, 700),
    "qiumo": Work("求魔", "苏铭", "玄幻",
        "210acebeef123f2c369d57d95d2ea5ee5a1c15716b859db15696c48294bcd687",
        9437806, 700),
}

# Diagnostic only: broad heading matches, not a chapter-completeness proof.
DIAGNOSTIC_HEAD = re.compile(
    r"^(?:正文[\s:：]*)?第(?P<num>[0-9零〇○一二三四五六七八九十百千萬万兩两]{1,16})"
    r"[章回](?:[\s:：、.．\-]+[^\r\n]{0,90})?$"
)

def heading_audit(path: Path) -> dict:
    count = 0
    invalid_ordinals = 0
    first = last = None
    irregular = []
    encoding = _encoding(path)
    previous = None
    with path.open("r", encoding=encoding) as stream:
        for line in stream:
            if len(line) > 1000:
                continue
            match = DIAGNOSTIC_HEAD.fullmatch(line.strip())
            if not match:
                continue
            try:
                ordinal = chapter_number(match.group("num"))
            except (ValueError, StudyError):
                invalid_ordinals += 1
                continue
            count += 1
            if first is None:
                first = ordinal
            if previous is not None and ordinal != previous + 1 and len(irregular) < 30:
                irregular.append({"heading_index": count, "previous": previous, "current": ordinal})
            previous = last = ordinal
    return {
        "heading_matches_not_verified_chapter_count": count,
        "encoding": encoding,
        "first_ordinal": first,
        "last_ordinal": last,
        "invalid_numeric_headers": invalid_ordinals,
        "sequence_anomaly_sample": irregular,
        "sequential_excerpt_audit_only": True,
    }


def run(work_id: str, *, audit_only: bool) -> dict:
    spec = WORKS[work_id]
    scheme = ("volume_reset_manghuangji_pinned" if work_id == "manghuangji" else
              "volume_prefix_global" if work_id == "qiumo" else "continuous")
    config = R2Config.from_environment()
    if config.bucket != "writerforge-private-library":
        raise RuntimeError("source: WRONG_PRIVATE_R2_BUCKET")
    vault = SingleWorkVault(config, work_id=work_id)
    stage = "download"
    with TemporaryDirectory(prefix="wf-modern-runner-") as tmp:
        root = Path(tmp)
        existing = vault.verify_existing_single_work()  # verifies pointer, manifest and FRESH R2 blob read
        if existing is None:
            raise RuntimeError("source: SINGLE_WORK_NOT_ARCHIVED")
        if (existing["utf8_sha256"] != spec.source_sha256
                or existing["utf8_bytes"] != spec.source_bytes):
            raise RuntimeError("source: PINNED_EDITION_DIFFERS_FROM_R2")
        source = root / "pinned-source.txt"
        key = vault._blob_key(work_id, spec.source_sha256)
        vault.client.download_file(config.bucket, key, str(source))
        if _digest(source) != (spec.source_sha256, spec.source_bytes):
            raise RuntimeError("download: FRESH_SHA256_OR_SIZE_MISMATCH")
        stage = "chapter"
        audit = heading_audit(source)
        basic = {
            "work_id": work_id, "title": spec.title,
            "source_sha256": spec.source_sha256, "source_bytes": spec.source_bytes,
            "private_source_restore_verified": True, "chapter_audit": audit,
        }
        try:
            info = inspect_modern_source(
                source, title=spec.title, protagonist=spec.protagonist,
                min_chapters=spec.min_chapters, expected_sha256=spec.source_sha256,
                min_bytes=spec.source_bytes, chapter_scheme=scheme)
        except Exception as exc:
            # Crucial: audit evidence is visible even when older parser cannot handle the edition.
            print(json.dumps({**basic, "stage": "chapter", "structure_preflight": False,
                "error_type": type(exc).__name__, "error": str(exc)[:300],
                "structural_learning_performed": False,
                "r2_learning_db_uploaded": False}, ensure_ascii=False), flush=True)
            raise RuntimeError("chapter: STRUCTURE_PREFLIGHT_FAILED") from None
        basic["preflight_chapters"] = info["chapters"]
        basic["structure_preflight"] = True
        basic["full_edition_independently_verified"] = False
        if audit_only:
            return {**basic, "stage": "chapter_preflight_only",
                    "structural_learning_performed": False,
                    "r2_learning_db_uploaded": False}
        stage = "db"
        db_path = root / "study.sqlite3"
        db = WriterForgeDB(db_path)
        try:
            runtime = RuntimeEngine()
            runtime.enter_learn()
            learned = study_modern_source(
                source, db, runtime, work_id=work_id + "-private-original",
                title=spec.title, protagonist=spec.protagonist,
                genre=spec.genre, source_uri="private-r2/single-works/" + work_id,
                min_chapters=spec.min_chapters, min_bytes=spec.source_bytes,
                expected_sha256=spec.source_sha256,
                chapter_scheme=scheme)
        finally:
            db.close()
        if learned["studied_chapters"] != info["chapters"] or not learned["structure_complete"]:
            raise RuntimeError("db: CHAPTER_COUNT_NOT_COMPLETE")
        stage = "upload"
        library = work_id + "-private-original"
        extras = {}
        if work_id == "manghuangji":
            # Evidence record only. The archived TXT bytes and original printed
            # headings remain unchanged; verified parsing is source-specific.
            evidence = {
                "status": "source_specific_audited_heading_exceptions",
                "source_sha256": spec.source_sha256,
                "source_bytes": spec.source_bytes,
                "structural_parser": "volume_reset_manghuangji_pinned",
                "raw_text_modified": False,
                "printed_header_preserved": True,
                "exceptions": [
                    {"volume": 22, "canonical_chapter": 3,
                     "kind": "nonstandard_heading_prefix", "line": 60160,
                     "line_sha256": "8af3b3af69a68e1d2b0f72f8c541fc8a2cdb4f3e6ef324842599e2e8e74f1f9c"},
                    {"volume": 25, "canonical_chapter": 18,
                     "printed_chapter": 20, "kind": "printed_heading_misnumber",
                     "line": 69921,
                     "line_sha256": "68eefe9d8f51189dbfb795b47514e1b0fc90d34f6546147d21c487cbdaf16d9c"}
                ],
                "independent_catalogues": [
                    "https://www.99csw.com/book/4660/167000.htm",
                    "https://www.piaotia.com/html/3/3259/",
                    "https://www.kunnu.com/mhj/"
                ],
                "entire_edition_independently_compared": False,
                "model_semantic_training_verified": False
            }
            report_path = root / "chapter_audit.json"
            report_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
            extras = {"chapter_audit.json": report_path}
        backup = R2StudyVault(config).backup(
            database=db_path, library=library, source=source, extras=extras,
            edition=work_id + "-structural-v2" if work_id == "manghuangji" else work_id + "-structural-v1")
        if not backup.get("verified"):
            raise RuntimeError("upload: R2_BACKUP_NOT_VERIFIED")
        stage = "restore"
        restored = R2StudyVault(config).restore(
            library=library, destination=root / "independent-fresh-restore")
        if not restored.get("verified") or restored.get("from_local_cache"):
            raise RuntimeError("restore: NOT_FRESH_VERIFIED_RESTORE")
        with sqlite3.connect(restored["db"]) as con:
            check = con.execute("PRAGMA quick_check").fetchone()
            rows = con.execute(
                "SELECT source_sha256,chapter_count FROM studied_works WHERE work_id=?",
                (library,)).fetchone()
            n = con.execute("SELECT COUNT(*) FROM studied_chapters WHERE work_id=?",
                            (library,)).fetchone()[0]
            units = con.execute("SELECT COUNT(*) FROM source_spans WHERE work_id=?",
                                (library,)).fetchone()[0]
            if (not check or check[0] != "ok" or
                    rows != (spec.source_sha256, info["chapters"]) or
                    n != info["chapters"] or units < n):
                raise RuntimeError("restore: RECOVERED_DB_NOT_CONSISTENT")
        if not restored["source"]:
            raise RuntimeError("restore: ORIGINAL_SOURCE_MISSING_FROM_STUDY_SNAPSHOT")
        if _digest(Path(restored["source"])) != (spec.source_sha256, spec.source_bytes):
            raise RuntimeError("restore: RECOVERED_ORIGINAL_SOURCE_MISMATCH")
        return {
            **basic, "stage": "complete_structural_only", "chapters": n,
            "source_units": units, "r2_study_library": library,
            "r2_study_snapshot": backup.get("snapshot"),
            "fresh_r2_study_restore_verified": True,
            "sqlite_quick_check": "ok", "structural_learning_performed": True,
            "model_literary_deep_read_performed": False,
            "independent_reader_review_performed": False,
            "model_weight_training_performed": False,
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", choices=tuple(WORKS), required=True)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    try:
        receipt = run(args.work, audit_only=args.audit_only)
    except Exception as exc:
        # Logs are limited to failure classification, never original text or secrets.
        print(json.dumps({"work_id": args.work, "status": "failed",
            "stage_or_reason": str(exc)[:300],
            "error_type": type(exc).__name__}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as output:
            output.write("## " + receipt["title"] + " — " + receipt["stage"] + "\n")
            output.write("Original SHA256: " + receipt["source_sha256"] + "\n")
            output.write("Fresh R2 source verified: yes\n")
            output.write("Full literary model training: NO\n")
            if receipt.get("fresh_r2_study_restore_verified"):
                output.write("Structure chapters: " + str(receipt["chapters"]) + "\n")
                output.write("SQLite library fresh-restored from R2: yes\n")


if __name__ == "__main__":
    main()
