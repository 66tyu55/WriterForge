"""Strict volume-aware chapter grammar for two independently audited modern editions.

No re-numbering of published chapter ordinals: the chapter record gets a unique
global database index, and its original volume/local/global ordinal is retained
in its heading metadata. Gaps, duplicates and missing volume transitions fail.
This is deterministic *structural* parsing, never semantic model training.
"""
from __future__ import annotations

from pathlib import Path
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


def volume_chapters(path: Path, encoding: str, *, scheme: str):
    """Stream full chapters in physical source order, with original numbering checks.

    volume_reset: numbered volume markers on their own lines; chapters reset to
        1 only on new consecutive volumes.
    volume_prefix_global: every heading has a printed volume and *global*
        chapter number; volume transitions and global chapter order must agree.
    """
    if scheme not in ("volume_reset", "volume_prefix_global"):
        raise StudyError("unsupported modern volume grammar")
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
            if scheme == "volume_reset":
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
                if match:
                    if current_volume is None:
                        raise StudyError("chapter appears before a volume marker")
                    local = chapter_number(match.group("chapter"))
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
    if not chapter_count:
        raise StudyError("no actual volume-qualified chapters found")
    yield emit()
