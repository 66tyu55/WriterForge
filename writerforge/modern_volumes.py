"""Strict volume-aware chapter grammar for two independently audited modern editions.

No re-numbering of published chapter ordinals: the chapter record gets a unique
global database index, and its original volume/local/global ordinal is retained
in its heading metadata. Gaps, duplicates and missing volume transitions fail.
This is deterministic *structural* parsing, never semantic model training.
"""
from __future__ import annotations

from pathlib import Path
from hashlib import sha256
import re
from .source_study import Chapter, StudyError, chapter_number, MAX_CHAPTER_CHARS

NUMBER = r"[0-9零〇○一二三四五六七八九十百千萬万兩两]{1,14}"
VOLUME_LINE = re.compile(
    r"^第(?P<volume>" + NUMBER + r")卷(?:[ \t\u3000:：]+[^\r\n]{0,100})?$"
)
LOCAL_CHAPTER = re.compile(
    r"^第(?P<chapter>" + NUMBER + r")章(?:[ \t\u3000:：、.．\-]+(?P<title>[^\r\n]{1,90}))?$"
)
COUPLED_CHAPTER = re.compile(
    r"^第(?P<volume>" + NUMBER + r")卷[^\r\n]{0,60}?"
    r"第(?P<chapter>" + NUMBER + r")章(?:[^\r\n]{0,95})?$"
)

MAX_PREAMBLE = 500_000
MAX_CHAPTERS = 5_000
MANGHUANGJI_PINNED_SHA = "f7aee869e201b4171e40a3ff9230e794f01fdc959d372017b8982635668be3d5"
# Source-specific corrections are evidence-gated. Never edit the raw text.
# TOCs: https://www.99csw.com/book/4660/167000.htm
#       https://www.piaotia.com/html/3/3259/
MANG_HIDDEN_V22_C3_LINE_SHA = "8af3b3af69a68e1d2b0f72f8c541fc8a2cdb4f3e6ef324842599e2e8e74f1f9c"
MANG_MISPRINT_V25_C18_LINE_SHA = "68eefe9d8f51189dbfb795b47514e1b0fc90d34f6546147d21c487cbdaf16d9c"
MANG_HIDDEN_HEADER = re.compile(r"^.{0,8}?第(?P<chapter>" + NUMBER + r")章(?:.{0,110})?$")

def _source_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()



def volume_chapters(path: Path, encoding: str, *, scheme: str):
    """Stream full chapters in physical source order, with original numbering checks.

    volume_reset: numbered volume markers on their own lines; chapters reset to
        1 only on new consecutive volumes.
    volume_prefix_global: every heading has a printed volume and *global*
        chapter number; volume transitions and global chapter order must agree.
    """
    if scheme not in ("volume_reset", "volume_prefix_global", "volume_reset_manghuangji_pinned"):
        raise StudyError("unsupported modern volume grammar")
    pinned = scheme == "volume_reset_manghuangji_pinned"
    if pinned and _source_hash(Path(path)) != MANGHUANGJI_PINNED_SHA:
        raise StudyError("source-specific grammar refused for different edition")
    applied = set()
    prior_volume = 0
    current_volume = None
    prior_local = 0
    chapter_count = 0
    heading = ""
    buffer: list[str] = []
    chars = preamble = 0

    def emit():
        body = "".join(buffer).strip()
        if not 100 <= len(body) <= MAX_CHAPTER_CHARS:
            raise StudyError(
                f"volume chapter physical ordinal {chapter_count} too short, too large or empty"
            )
        return Chapter(chapter_count, heading, body)

    with Path(path).open("r", encoding=encoding) as source:
        for line in source:
            if len(line) > MAX_CHAPTER_CHARS:
                raise StudyError("oversized physical source line")
            item = line.strip()
            if scheme in ("volume_reset", "volume_reset_manghuangji_pinned"):
                marker = VOLUME_LINE.fullmatch(item)
                if marker:
                    ordinal = chapter_number(marker.group("volume"))
                    if not 1 <= ordinal <= MAX_CHAPTERS:
                        raise StudyError("invalid numbered volume")
                    if current_volume is not None and ordinal != current_volume + 1:
                        raise StudyError(
                            f"volume numbering malformed: expected {current_volume+1}, got {ordinal}"
                        )
                    current_volume = ordinal
                    # The next chapter must start at 1; never reinterpret a
                    # mis-numbered local chapter as a globally numbered one.
                    prior_local = 0
                    continue
                match = LOCAL_CHAPTER.fullmatch(item)
                raw_line_sha = sha256(line.encode("utf-8")).hexdigest() if pinned else None
                # The actual V22 C3 is prefixed by an editorial marker.
                if (pinned and not match and current_volume == 22 and prior_local == 2
                        and raw_line_sha == MANG_HIDDEN_V22_C3_LINE_SHA):
                    loose = MANG_HIDDEN_HEADER.fullmatch(item)
                    if not loose or chapter_number(loose.group("chapter")) != 3 or "一柄剑" not in item:
                        raise StudyError("pinned volume 22 chapter 3 witness changed")
                    match = loose
                    applied.add("v22_c3")
                if match:
                    if current_volume is None:
                        raise StudyError("chapter appears before a volume marker")
                    local = chapter_number(match.group("chapter"))
                    # Printed as 20 in this original; independent catalogues
                    # confirm '花光了' is chapter 18. Raw heading is retained.
                    if (pinned and current_volume == 25 and prior_local == 17
                            and local == 20 and raw_line_sha == MANG_MISPRINT_V25_C18_LINE_SHA
                            and "花光了" in item):
                        local = 18
                        applied.add("v25_c18")
                    if local != prior_local + 1:
                        raise StudyError(
                            f"chapter gap in volume {current_volume}: expected {prior_local+1}, got {local}"
                        )
                    prior_local = local
                    current_heading = item
                else:
                    current_heading = None
            else:
                match = COUPLED_CHAPTER.fullmatch(item)
                if match:
                    vol = chapter_number(match.group("volume"))
                    local = chapter_number(match.group("chapter"))
                    if vol < 1 or vol > MAX_CHAPTERS:
                        raise StudyError("invalid numbered coupled volume")
                    if current_volume is None:
                        if vol != 1:
                            raise StudyError("coupled original does not start in volume one")
                    elif vol not in (current_volume, current_volume + 1):
                        raise StudyError(
                            f"coupled volume out of order: current {current_volume}, got {vol}"
                        )
                    if local != chapter_count + 1:
                        raise StudyError(
                            f"coupled chapter ordinal malformed: expected {chapter_count+1}, got {local}"
                        )
                    current_volume = vol
                    current_heading = item
                else:
                    current_heading = None
            if current_heading is not None:
                if chapter_count:
                    yield emit()
                chapter_count += 1
                if chapter_count > MAX_CHAPTERS:
                    raise StudyError("modern volume novel over chapter safety budget")
                heading = current_heading[:160]
                buffer.clear()
                chars = 0
            elif chapter_count:
                chars += len(line)
                if chars > MAX_CHAPTER_CHARS:
                    raise StudyError(f"chapter {chapter_count} exceeds memory cap")
                buffer.append(line)
            else:
                preamble += len(line)
                if preamble > MAX_PREAMBLE:
                    raise StudyError("first chapter not found in bounded preamble")
    if pinned and applied != {"v22_c3", "v25_c18"}:
        raise StudyError("source-specific errata witnesses incomplete")
    if not chapter_count:
        raise StudyError("no actual volume-qualified chapters found")
    yield emit()
