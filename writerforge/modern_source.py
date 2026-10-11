"""Bounded, sequential ORIGINAL Chinese modern-novel structural ingestion.

This is not model fine-tuning or independent literary criticism. Classical
sources keep their stricter 8 MiB/70-120 chapter path unchanged. This module
uses bounded per-chapter memory and per-chapter SQLite transactions.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re
import json

from .db import WriterForgeDB
from .runtime import Mode, RuntimeEngine
from .source_study import (
    Chapter, OriginalStudy, StudyError, _structural_analysis, _unitize,
    chapter_number, MAX_CHAPTER_CHARS, MAX_EXCERPT,
)

MAX_MODERN_SOURCE_BYTES = 32 * 1024 * 1024  # Also fits R2's 32 MiB source-file cap.
MAX_MODERN_CHAPTERS = 5_000
MAX_MODERN_PREAMBLE_CHARS = 500_000
# Intentionally line-anchored; prose mentioning a chapter number is not a heading.
CHAPTER_HEAD = re.compile(
    r"^第(?P<number>[0-9零〇○一二三四五六七八九十百千萬万兩两壹貳參肆伍陸柒捌玖拾佰]{1,14})章"
    r"(?:[ \t\u3000:：、.\-]+(?P<title>[^\r\n]{1,90}))?$"
)


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _encoding(path: Path) -> str:
    """Check entire stream, not just its prefix, before selecting the decoder."""
    for codec in ("utf-8-sig", "gb18030"):
        try:
            with path.open("r", encoding=codec) as handle:
                while handle.read(64 * 1024):
                    pass
            return codec
        except UnicodeError:
            continue
    raise StudyError("modern source has no supported UTF-8/GB18030 encoding")


def _chapters(path: Path, encoding: str):
    """Yield only one bounded chapter at a time, validating every ordinal."""
    number = 0
    heading = ""
    buffer: list[str] = []
    chars = 0
    preamble = 0

    def emit():
        body = "".join(buffer).strip()
        if not 100 <= len(body) <= MAX_CHAPTER_CHARS:
            raise StudyError(f"chapter {number} empty, truncated or exceeds {MAX_CHAPTER_CHARS} chars")
        return Chapter(number, heading, body)

    with path.open("r", encoding=encoding) as source:
        for line in source:
            if len(line) > MAX_CHAPTER_CHARS:
                raise StudyError("oversized physical line: malformed modern source")
            match = CHAPTER_HEAD.fullmatch(line.strip())
            if match:
                try:
                    next_number = chapter_number(match.group("number"))
                except (ValueError, StudyError) as exc:
                    raise StudyError("unsupported modern chapter numeral") from exc
                if next_number != number + 1:
                    raise StudyError(
                        f"modern chapter order malformed: expected {number+1}, got {next_number}"
                    )
                if number:
                    yield emit()
                number = next_number
                if number > MAX_MODERN_CHAPTERS:
                    raise StudyError("modern novel exceeds max chapter count")
                heading = (match.group("title") or "").strip()
                buffer.clear()
                chars = 0
            elif number:
                chars += len(line)
                if chars > MAX_CHAPTER_CHARS:
                    raise StudyError(f"modern chapter {number} exceeds chapter memory budget")
                buffer.append(line)
            else:
                preamble += len(line)
                if preamble > MAX_MODERN_PREAMBLE_CHARS:
                    raise StudyError("no plausible chapter one within bounded preamble")
        if not number:
            raise StudyError("modern source has no recognized first chapter heading")
        yield emit()


def inspect_modern_source(
    path: str | Path, *, title: str, protagonist: str,
    min_chapters: int, max_chapters: int = MAX_MODERN_CHAPTERS,
    min_bytes: int = 1, expected_sha256: str | None = None,
) -> dict:
    """Full-file SHA256 + decoding + contiguous numbered chapter preflight.

    Chapter count and file size are heuristics, not a proof that an edition is
    the official unabridged text. Never report literary learning from this.
    """
    source = Path(path)
    if not 1 <= min_chapters <= max_chapters <= MAX_MODERN_CHAPTERS:
        raise StudyError("invalid modern chapter limits")
    if (not source.is_file() or not min_bytes <= source.stat().st_size
            <= MAX_MODERN_SOURCE_BYTES):
        raise StudyError("modern source missing or outside its bounded size budget")
    source_hash = _file_sha256(source)
    if expected_sha256 is not None:
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256.lower()):
            raise StudyError("invalid pinned source SHA256")
        if source_hash != expected_sha256.lower():
            raise StudyError("modern source SHA256 differs from pinned edition")
    encoding = _encoding(source)
    with source.open("r", encoding=encoding) as handle:
        front = handle.read(120_000)
    if title not in front:
        raise StudyError("expected novel title not found in edition front matter")

    found_character = False
    count = 0
    for chapter in _chapters(source, encoding):
        count += 1
        if protagonist in chapter.text:
            found_character = True
        if count > max_chapters:
            raise StudyError("modern source has too many chapters")
    if not min_chapters <= count <= max_chapters:
        raise StudyError(f"expected {min_chapters}..{max_chapters} chapters; found {count}")
    if not found_character:
        raise StudyError("expected novel character not found in source prose")
    if _file_sha256(source) != source_hash:
        raise StudyError("source changed during structure validation")
    return {
        "sha256": source_hash,
        "bytes": source.stat().st_size,
        "encoding": encoding,
        "chapters": count,
        "structure_preflight": True,
        "full_edition_independently_verified": False,
    }


def _ingest_one(db: WriterForgeDB, work_id: str, chapter: Chapter, *, genre: str):
    """One chapter = one SQLite transaction. No novel-scale in-memory arrays."""
    conn = db.conn
    old = conn.execute(
        "SELECT chapter_sha256 FROM studied_chapters WHERE work_id=? AND chapter=?",
        (work_id, chapter.number),
    ).fetchone()
    if old:
        if old["chapter_sha256"] != chapter.fingerprint:
            raise StudyError("existing modern chapter changed: do not mix editions")
        return False
    try:
        conn.execute("BEGIN IMMEDIATE")
        parent = conn.execute(
            "SELECT id FROM snapshots WHERE status='published' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        parent_id = parent["id"] if parent else None
        cur = conn.execute(
            "INSERT INTO snapshots(parent_id,status,layout,note) VALUES(?,'staging',?,?)",
            (parent_id, "delta" if parent_id is not None else "full",
             f"{work_id}/chapter-{chapter.number:05d}"),
        )
        snapshot_id = int(cur.lastrowid)
        spans = 0
        entries = 0
        seen: set[str] = set()
        for paragraph, sentence, piece in _unitize(chapter):
            spans += 1
            tracks, craft = _structural_analysis(piece)
            excerpt = piece[:MAX_EXCERPT]
            conn.execute(
                """INSERT INTO source_spans(
                   work_id,chapter,paragraph,sentence,excerpt,source_sha256,
                   tracks_json,craft_json) VALUES(?,?,?,?,?,?,?,?)""",
                (work_id, chapter.number, paragraph, sentence, excerpt,
                 sha256(piece.encode("utf-8")).hexdigest(),
                 json.dumps(tracks, ensure_ascii=False),
                 json.dumps(craft, ensure_ascii=False)),
            )
            key = sha256((work_id + "|" + piece).encode("utf-8")).hexdigest()
            if key in seen:
                continue
            seen.add(key)
            cur = conn.execute(
                """INSERT INTO xuehai_entries(
                   snapshot_id,work_id,chapter,paragraph,sentence,text,
                   library_class,culture,genre,source_role,function,effect,
                   method_cluster,quality_weight,novelty_weight,reuse_policy,
                   source_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (snapshot_id, work_id, chapter.number, paragraph, sentence,
                 excerpt, "中国现代网络小说", "中国", genre, "core",
                 craft["sentence_function"], "unverified",
                 "modern_" + craft["sentence_function"], 1.0, 1.0,
                 "technique_only", key),
            )
            if db.fts_enabled:
                conn.execute(
                    """INSERT INTO xuehai_fts(
                       entry_id,text,function,effect,method_cluster)
                       VALUES(?,?,?,?,?)""",
                    (int(cur.lastrowid), excerpt, craft["sentence_function"],
                     "unverified", "modern_" + craft["sentence_function"]),
                )
            entries += 1
        if not spans:
            raise StudyError(f"chapter {chapter.number} has no source units")
        conn.execute("UPDATE snapshots SET status='published' WHERE id=?", (snapshot_id,))
        conn.execute(
            """INSERT INTO studied_chapters(
               work_id,chapter,chapter_sha256,heading,source_spans,
               retrieval_entries,snapshot_id) VALUES(?,?,?,?,?,?,?)""",
            (work_id, chapter.number, chapter.fingerprint, chapter.heading,
             spans, entries, snapshot_id),
        )
        conn.commit()
        return True
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise


def study_modern_source(
    path: str | Path, db: WriterForgeDB, runtime: RuntimeEngine, *,
    work_id: str, title: str, protagonist: str, genre: str, source_uri: str,
    min_chapters: int, max_chapters: int = MAX_MODERN_CHAPTERS,
    min_bytes: int = 1, expected_sha256: str | None = None,
) -> dict:
    runtime.require(Mode.LEARN)
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,79}", work_id):
        raise StudyError("unsafe modern work identifier")
    source = Path(path)
    info = inspect_modern_source(
        source, title=title, protagonist=protagonist,
        min_chapters=min_chapters, max_chapters=max_chapters,
        min_bytes=min_bytes, expected_sha256=expected_sha256,
    )
    conn = db.conn
    existing = conn.execute(
        "SELECT source_sha256,chapter_count FROM studied_works WHERE work_id=?",
        (work_id,),
    ).fetchone()
    if existing and (existing["source_sha256"] != info["sha256"]
                     or existing["chapter_count"] != info["chapters"]):
        raise StudyError("modern edition changed: use new work_id; no mixed source")
    if not existing:
        conn.execute(
            """INSERT INTO studied_works(
               work_id,title,source_uri,source_sha256,chapter_count,study_level)
               VALUES(?,?,?,?,?,'deterministic_structural')""",
            (work_id, title, source_uri, info["sha256"], info["chapters"]),
        )
        conn.commit()
    completed = 0
    for chapter in _chapters(source, info["encoding"]):
        if _ingest_one(db, work_id, chapter, genre=genre):
            completed += 1
            if completed % 100 == 0:
                print(f"STRUCTURAL PROGRESS {work_id}: {completed} new chapters", flush=True)
    if _file_sha256(source) != info["sha256"]:
        raise StudyError("modern source changed while ingesting; refuse R2 backup")
    state = OriginalStudy(db, runtime).status(work_id)
    if not state["structure_complete"] or state["studied_chapters"] != info["chapters"]:
        raise StudyError("modern source ingestion incomplete; refuse R2 backup")
    return {
        "work_id": work_id, "title": title, "source_raw_sha256": info["sha256"],
        "source_bytes": info["bytes"], "source_chapters": info["chapters"],
        "newly_studied": completed, **state,
        "study_level": "deterministic_structural_unverified",
        "full_edition_independently_verified": False,
        "literary_learning_verified": False,
        "model_training_performed": False,
        "independent_literary_review_performed": False,
    }
