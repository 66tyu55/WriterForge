"""Strict, source-traced Chinese classical fiction training catalog.

Original-language historical texts only. Every entry names one public-domain
Project Gutenberg eBook/edition and the exact Git blob checksum, so changes in
upstream sources trigger a provenance failure instead of silently altering the
corpus. No random websites or translations enter the study pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1, sha256
from pathlib import Path
import os
import re
import urllib.request

from .db import WriterForgeDB
from .runtime import RuntimeEngine, Mode
from .source_study import (
    StudyError, OriginalStudy, parse_original, MAX_DOWNLOAD_BYTES,
)


@dataclass(frozen=True)
class ClassicBook:
    key: str
    title: str
    work_id: str
    gutenberg_id: int
    source_filename: str
    git_blob_sha1: str
    expected_chapters: int
    include_prologue: bool
    literary_focus: tuple[str, ...]

    @property
    def source_url(self) -> str:
        return (
            f"https://raw.githubusercontent.com/GITenberg/---_{self.gutenberg_id}/"
            f"master/{self.source_filename}"
        )

    @property
    def source_page(self) -> str:
        return f"https://www.gutenberg.org/ebooks/{self.gutenberg_id}"

    @property
    def library(self) -> str:
        return f"{self.key}-{self.gutenberg_id}"


CATALOG: dict[str, ClassicBook] = {
    "honglou": ClassicBook(
        key="honglou",title="紅樓夢",work_id="honglou-gutenberg-24264",
        gutenberg_id=24264, source_filename="24264-0.txt",
        git_blob_sha1="4f75f649a922cb1d3576b40e5ccd15baf367b594",
        expected_chapters=120,include_prologue=False,
        literary_focus=("人物关系层次","微妙对白","家族生活","心理与细节"),
    ),
    "shuihu": ClassicBook(
        key="shuihu",title="水滸傳",work_id="shuihu-gutenberg-23863",
        gutenberg_id=23863, source_filename="23863-0.txt",
        git_blob_sha1="b8811e4ea9340b572f943842e131f2ada6b2032e",
        expected_chapters=70,include_prologue=True,
        literary_focus=("江湖人物群像","身份与冲突","行动叙事","古代对白"),
    ),
}

# Deliberate: no 50-work placeholders. Only verified full study entries count.
MIN_WORKS_FOR_CROSS_CORPUS_REVIEW = 50


def get_book(key: str) -> ClassicBook:
    if key not in CATALOG:
        raise StudyError(f"unapproved original work {key!r}; select from the verified source catalog")
    return CATALOG[key]


def verify_edition(book: ClassicBook, data: bytes) -> str:
    """Git blob SHA1 and strict chapter order: no translation or edited edition."""
    if not data or len(data)>MAX_DOWNLOAD_BYTES:
        raise StudyError("source missing or exceeds 8 MiB safety budget")
    git_header = f"blob {len(data)}\0".encode("ascii")
    actual = sha1(git_header+data).hexdigest()
    if actual!=book.git_blob_sha1:
        raise StudyError(
            f"{book.title} source content changed from cataloged original edition; "
            "do not continue training until source review"
        )
    try:
        text=data.decode("utf-8-sig")
    except UnicodeError as exc:
        raise StudyError("original text is not valid UTF-8") from exc
    chapters = parse_original(text,require_hundred=False,
                              expected_count=book.expected_chapters,
                              include_prologue=book.include_prologue)
    expected_records=book.expected_chapters+(1 if book.include_prologue else 0)
    if len(chapters)!=expected_records:
        raise StudyError("original source has unexpected chapter or prologue count")
    if not all(len(ch.text)>=100 for ch in chapters):
        raise StudyError("source chapter seems truncated")
    return text


def download_book(book: ClassicBook, output: str | Path) -> dict:
    """Stream a fixed allowlisted Chinese original, then verify before commit."""
    path=Path(output)
    path.parent.mkdir(parents=True,exist_ok=True)
    part=path.with_name(path.name+".partial")
    try:
        req=urllib.request.Request(
            book.source_url,
            headers={"User-Agent":"WriterForge-chinese-original-catalog/1"},
        )
        with urllib.request.urlopen(req,timeout=50) as remote, part.open("xb") as dest:
            total=0
            while True:
                block=remote.read(64*1024)
                if not block:
                    break
                total+=len(block)
                if total>MAX_DOWNLOAD_BYTES:
                    raise StudyError("source download exceeds safety budget")
                dest.write(block)
        data=part.read_bytes()
        verify_edition(book,data)
        if path.exists() and path.read_bytes()!=data:
            raise StudyError("existing source file differs from approved edition")
        os.replace(part,path)
        return {
            "work_id":book.work_id,"title":book.title,
            "source_path":str(path),"source_uri":book.source_page,
            "source_git_blob_sha1":book.git_blob_sha1,
            "raw_sha256":sha256(data).hexdigest(),
            "bytes":len(data),"expected_chapters":book.expected_chapters,
            "include_prologue":book.include_prologue,
        }
    finally:
        part.unlink(missing_ok=True)


def study_book(
    book: ClassicBook, source_path: str | Path, db: WriterForgeDB,
    rt: RuntimeEngine,
) -> dict:
    rt.require(Mode.LEARN)
    source=Path(source_path)
    if not source.is_file() or source.stat().st_size>MAX_DOWNLOAD_BYTES:
        raise StudyError("catalog source file missing or oversized")
    raw=source.read_bytes()
    text=verify_edition(book,raw)
    result=OriginalStudy(db,rt).ingest(
        text,work_id=book.work_id,title=book.title,
        source_uri=book.source_page,
        require_hundred=False,expected_count=book.expected_chapters,
        include_prologue=book.include_prologue,wrapped_lines=True,
    )
    return {
        **result,
        "title":book.title,
        "source_git_blob_sha1":book.git_blob_sha1,
        "source_raw_sha256":sha256(raw).hexdigest(),
        "prologue_included":book.include_prologue,
        "study_level":"deterministic_structural_unverified",
        "focus_targets_not_yet_validated":list(book.literary_focus),
    }


def catalog_progress_local(db: WriterForgeDB) -> dict:
    """Count UNIQUE fully ingested originals, not individual lines or chapters.

    This is only a readiness check. Do NOT automatically run global literary
    consolidation or optimization until at least 50 independent sources exist.
    """
    rows=db.conn.execute(
        """SELECT w.work_id,w.title,w.chapter_count,
                  COUNT(c.chapter) AS completed_chapters
           FROM studied_works w
           LEFT JOIN studied_chapters c ON c.work_id=w.work_id
           GROUP BY w.work_id,w.title,w.chapter_count ORDER BY w.work_id"""
    ).fetchall()
    works=[
        {
            "work_id":r["work_id"],"title":r["title"],
            "chapters":int(r["completed_chapters"]),
            "expected":int(r["chapter_count"]),
            "complete":int(r["completed_chapters"])==int(r["chapter_count"]),
        }
        for r in rows
    ]
    completed=sum(int(w["complete"]) for w in works)
    return {
        "complete_distinct_works":completed,
        "threshold":MIN_WORKS_FOR_CROSS_CORPUS_REVIEW,
        "remaining":max(0,MIN_WORKS_FOR_CROSS_CORPUS_REVIEW-completed),
        "cross_corpus_review_eligible":completed>=MIN_WORKS_FOR_CROSS_CORPUS_REVIEW,
        "global_assessment_performed":False,
        "works":works,
    }
