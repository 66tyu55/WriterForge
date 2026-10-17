"""Bounded later-chapter diagnostic cursor. Does not advance literary mastery.

This module is deliberately additive: V28 opening chapter APIs and previous
stored receipts are unchanged. Source SHA bytes must be verified by caller.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re

from .reverse_source_cursor import HEADING, MAX_CHAPTER, MAX_LINE, MAX_PREAMBLE
from .source_study import chapter_number, StudyError


class LaterWindowError(ValueError):
    pass


def _hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def later_chapter_diagnostic(path: str | Path, encoding: str, *, 
                             expected_source_sha256: str,
                             chapter: int = 2,
                             min_unit_chars: int = 300,
                             sampled_diagnostic: bool = False) -> tuple[dict, tuple[str,str]]:
    """Read chapter N only, in physical order, and pin both contiguous halves.

    Supports small forward diagnostics (chapters 2..3), not any skip-ahead.
    This does NOT certify a semantic boundary or unlock further study.
    Caller must first verify full original bytes/SHA256 against private R2.
    """
    if type(chapter) is not int or (not (3<=chapter<=24)
        if sampled_diagnostic else chapter not in (2,3)):
        raise LaterWindowError("UNSUPPORTED_DIAGNOSTIC_CHAPTER_SCOPE")
    if not isinstance(expected_source_sha256,str) or not re.fullmatch(
        r"[a-f0-9]{64}",expected_source_sha256):
        raise LaterWindowError("INVALID_SOURCE_SHA_PIN")
    if not 200<=min_unit_chars<=1500:
        raise LaterWindowError("INVALID_UNIT_BOUND")
    first_three=[]
    current=0
    headers=0
    content=[]
    chapter_chars=0
    preamble=0
    with Path(path).open("r",encoding=encoding) as fp:
        for line_no,line in enumerate(fp,1):
            if len(line)>MAX_LINE:
                raise LaterWindowError("OVERSIZE_PHYSICAL_LINE")
            heading=HEADING.fullmatch(line.strip())
            if heading:
                try:
                    n=chapter_number(heading.group("number"))
                except (ValueError,StudyError):
                    raise LaterWindowError("UNSUPPORTED_CHAPTER_NUMBER") from None
                if n!=current+1:
                    raise LaterWindowError("NONCONTIGUOUS_CHAPTER_SEQUENCE")
                current=n
                headers+=1
                if headers<=chapter+1:
                    first_three.append({"chapter":n,"line":line_no,"heading_sha256":_hash(line)})
                if current==chapter+1:
                    break
                continue
            if current==0:
                preamble+=len(line)
                if preamble>MAX_PREAMBLE:
                    raise LaterWindowError("PREAMBLE_TOO_LONG")
            if current==chapter:
                content.append(line)
                chapter_chars+=len(line)
                if chapter_chars>MAX_CHAPTER:
                    raise LaterWindowError("CHAPTER_TOO_LARGE")
    if current!=chapter+1 or headers!=chapter+1:
        raise LaterWindowError("CHAPTER_END_NOT_CONFIRMED")
    body="".join(content)
    if len(body)<2*min_unit_chars:
        raise LaterWindowError("CHAPTER_TOO_SHORT")
    positions=[match.end() for match in re.finditer(r"(?<=[。！？!?；;])\r?\n",body)
               if min_unit_chars<=match.end()<=len(body)-min_unit_chars]
    if not positions:
        raise LaterWindowError("NO_SAFE_CONTIGUOUS_PARAGRAPH_BOUNDARY")
    mid=len(body)//2
    boundary=min(positions,key=lambda p:(abs(p-mid),p))
    left,right=body[:boundary],body[boundary:]
    if left+right!=body or len(left)<min_unit_chars or len(right)<min_unit_chars:
        raise LaterWindowError("BOUNDARY_OR_SOURCE_INTEGRITY_FAILED")
    if len(left)>5500 or len(right)>5500:
        raise LaterWindowError("AB_INPUT_WINDOW_TOO_LARGE")
    plan={
        "format":"writerforge.chapter-diagnostic.v1",
        "work_id":"wudongqiankun",
        "source_sha256":expected_source_sha256,
        "chapter":chapter,
        "chapter_body_sha256":_hash(body),
        "chapter_body_chars":len(body),
        "contiguous_headers":first_three,
        "chapter_earlier_headings_verified":headers==chapter+1,
        "windows":[
            {"ordinal":1,"sha256":_hash(left),"chars":len(left),"start":0,"end":boundary},
            {"ordinal":2,"sha256":_hash(right),"chars":len(right),"start":boundary,"end":len(body)},
        ],
        "full_body_reconstructed":left+right==body,
        "semantic_boundary_verified":False,
        "diagnostic_only_no_mastery_progress":True,
        "sampled_diagnostic_only": bool(sampled_diagnostic),
        "first_window_literary_gate":"NOT_PASSED",
        "next_curriculum_window":"LOCKED",
    }
    return plan,(left,right)
