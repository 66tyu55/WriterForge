"""Exam V67: WriterForge reads its own pinned R2 original and answers a
real, independently authored textual query with evidence. No model guessing,
no fictitious source positions, no library mutation, no local corpus archive.

This is a lexical retrieval exam, NOT a validated semantic-literary ability.
"""
from __future__ import annotations

from pathlib import Path
from time import perf_counter
import json
import re

from .r2_worker_http import WFWorkerR2Client
from .source_study import parse_original


class LiteraryExamError(ValueError):
    pass


def run_literary_retrieval_exam(client: WFWorkerR2Client, *, question_path: Path) -> dict:
    if not question_path.is_file() or question_path.stat().st_size > 4096:
        raise LiteraryExamError("WF_EXAM_QUESTION_NOT_FOUND_OR_TOO_LARGE")
    data = json.loads(question_path.read_text(encoding="utf-8"))
    question = data.get("question")
    if (data.get("format") != "writerforge.independent-literary-retrieval-exam.v1"
            or not isinstance(question, str) or not 40 <= len(question) <= 300
            or data.get("model_assistance_allowed") is not False
            or data.get("evaluator_supplies_expected_answer") is not False):
        raise LiteraryExamError("WF_EXAM_QUESTION_SCHEMA_INVALID")

    # WF derives the search literal from the actual examiner question. No
    # injected result, expected chapter, or known answer is stored in the exam.
    literals = re.findall(r"“([^”]{2,24})”", question)
    if (len(literals) != 1 or "第一次" not in question
            or "哪一回" not in question):
        raise LiteraryExamError("WF_EXAM_QUESTION_NOT_SUPPORTED_AS_LEXICAL_FIRST")
    term = literals[0]
    if any(ch in term for ch in ("%","_","\\","\n","\r")):
        raise LiteraryExamError("WF_EXAM_TERM_INVALID")

    started = perf_counter()
    raw, receipt = client.pinned_laocan_original()
    try:
        original = raw.decode("utf-8-sig")
    except UnicodeError:
        raise LiteraryExamError("WF_EXAM_VERIFIED_SOURCE_DECODE_FAILED") from None

    # Reuse WriterForge's actual audited parser; it refuses missing, duplicate,
    # out-of-order and incomplete chapter sequences.
    chapters = parse_original(original, require_hundred=False, expected_count=20)
    matched_units = []
    full_occurrences = 0
    for chapter in chapters:
        count = chapter.text.count(term)
        full_occurrences += count
        if not count:
            continue
        index = chapter.text.find(term)
        left = max(0, index - 32)
        right = min(len(chapter.text), index + len(term) + 32)
        excerpt = chapter.text[left:right].replace("\r", " ").replace("\n", " ")
        position = {
            "chapter": chapter.number,
            "chapter_heading": chapter.heading[:90],
            "char_offset_in_chapter": index,
            "line_in_chapter": chapter.text[:index].count("\n") + 1,
            "evidence_excerpt": excerpt,
            "excerpt_contains_quoted_term": term in excerpt,
        }
        matched_units.append(position)

    first = matched_units[0] if matched_units else None
    took_ms = round((perf_counter() - started) * 1000, 2)
    return {
        "format": "writerforge.r2-independent-literary-exam.v1",
        "exam_id": data.get("exam_id"),
        "question": question,
        "derived_literal_by_wf": term,
        "status": "PINNED_ORIGINAL_MATCH_VERIFIED" if first else "PINNED_ORIGINAL_NO_MATCH",
        "answer": (
            f"逐回检索完整20回后，首次出现原文字词“{term}”的是第"
            f"{first['chapter']}回（{first['chapter_heading']}）。"
            if first else f"逐回检索完整20回，没有查到“{term}”。"
        ),
        "first_occurrence": first,
        "chapters_total": len(chapters),
        "chapters_actually_scanned": len(chapters),
        "chapters_containing_literal": len(matched_units),
        "total_literal_occurrences": full_occurrences,
        "source_provenance": receipt,
        "end_to_end_retrieval_and_scan_ms": took_ms,
        "search_strategy": "verified_primary_source_full_chapter_lexical_scan",
        "no_cached_model_answer": True,
        "no_model_called": True,
        "no_sql_executed": True,
        "no_source_saved_to_disk": True,
        "no_r2_writes": True,
        "semantic_literary_understanding_proven": False,
    }
