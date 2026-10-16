"""First-chapter-first, contiguous private-source cursor for V28.

Source location/provenance ONLY. Candidate boundaries are not semantic scene
understanding; no original text is returned, persisted, or printed.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re

from .source_study import chapter_number, StudyError

MAX_LINE = 180_000
MAX_CHAPTER = 180_000
MAX_PREAMBLE = 250_000
MAX_HEADINGS = 4
HEADING = re.compile(
    r"^(?:正文[ \t\u3000:：]*)?第(?P<number>[0-9零〇○一二三四五六七八九十百千萬万兩两]{1,14})章"
    r"(?:[ \t\u3000:：、.．\-]+[^\r\n]{0,100})?$"
)


class CursorError(ValueError):
    pass


def digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def opening_chapter_plan(path: str | Path, encoding: str, *,
                         expected_source_sha256: str,
                         min_unit_chars: int = 200) -> dict:
    """Validate first THREE actual headings in source physical order.

    Divide chapter 1 only at a real existing newline following terminal
    punctuation. Both proposed windows share one boundary and cover 100% of
    chapter body. Review must still confirm a meaningful causal scene boundary.
    """
    if not isinstance(expected_source_sha256, str) or not re.fullmatch(
        r"[a-f0-9]{64}", expected_source_sha256
    ):
        raise CursorError("invalid pinned SHA")
    if not 100 <= min_unit_chars <= 1500:
        raise CursorError("unsafe minimum training window")
    headings = []
    chapter1 = []
    chars = 0
    preamble = 0
    current = 0
    with Path(path).open("r", encoding=encoding) as stream:
        for line_no, line in enumerate(stream, 1):
            if len(line) > MAX_LINE:
                raise CursorError("source physical line above cap")
            head = HEADING.fullmatch(line.strip())
            if head:
                try:
                    number = chapter_number(head.group("number"))
                except (ValueError, StudyError) as exc:
                    raise CursorError("unsupported chapter number") from exc
                # Only evidence about the OPENING, not whole-edition claim.
                if number != current + 1:
                    raise CursorError(
                        f"opening sequence malformed: expected {current+1}, got {number}"
                    )
                current = number
                headings.append({"number":number, "line":line_no,
                                 "heading_sha256":digest(line)})
                if current >= MAX_HEADINGS:
                    break
                continue
            if current == 1:
                chapter1.append(line)
                chars += len(line)
                if chars > MAX_CHAPTER:
                    raise CursorError("first chapter exceeds bounded memory")
            elif current == 0:
                preamble += len(line)
                if preamble > MAX_PREAMBLE:
                    raise CursorError("first chapter not found within preamble limit")
    if len(headings) < 3:
        raise CursorError("need first three consecutive physical source chapter headers")
    body = "".join(chapter1)
    if not 2 * min_unit_chars <= len(body) <= MAX_CHAPTER:
        raise CursorError("chapter one too short/long for two sequential windows")
    boundaries = []
    # The newline stays with the previous candidate, so no source char drops.
    for found in re.finditer(r"(?<=[。！？!?；;])\r?\n", body):
        b = found.end()
        if min_unit_chars <= b <= len(body)-min_unit_chars:
            boundaries.append(b)
    if not boundaries:
        raise CursorError("no safe paragraph boundary; semantic splitting needed")
    midpoint = len(body) // 2
    boundary = min(boundaries, key=lambda p: (abs(midpoint-p),p))
    left, right = body[:boundary], body[boundary:]
    if left+right != body or not left or not right:
        raise CursorError("non-contiguous source units")
    chapter_hash = digest(body)
    first_hash = digest(left)
    second_hash = digest(right)
    result = {
        "stage":"opening_layout_candidate_only",
        "work_id":"wudongqiankun",
        "source_sha256": expected_source_sha256,
        "chapter":1,
        "chapter_body_sha256":chapter_hash,
        "chapter_body_chars":len(body),
        "preamble_chars":preamble,
        "first_three_chapter_headers":headings[:3],
        "coverage_exact":True,
        "starts_at_chapter_one":True,
        "semantic_scene_boundary_verified":False,
        "cause_effect_understanding_performed":False,
        "writer_model_called":False,
        "reader_review_performed":False,
        "units":[
            {"ordinal":1,"chapter":1,"start":0,"end":boundary,
             "chars":len(left),"segment_sha256":first_hash,
             "context_before_sha256":digest("chapter-one-start:"+expected_source_sha256),
             "prior_unit_sha256":None},
            {"ordinal":2,"chapter":1,"start":boundary,"end":len(body),
             "chars":len(right),"segment_sha256":second_hash,
             "context_before_sha256":first_hash,
             "prior_unit_sha256":first_hash}
        ],
        "continuity":{
            "first_unit_end_equals_second_start": True,
            "full_chapter_reconstructed_sha256":digest(left+right),
            "no_skipped_prose":True,
            "semantic_handoff_review_required":True,
        }
    }
    return result
