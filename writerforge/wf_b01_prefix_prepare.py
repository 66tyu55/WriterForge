"""WF V78 controlled B01 prefix-only sample preparation, no literary answer.

Reads a verified first chapter inside WriterForge's own Railway process. The
first 2-3 source windows are drawn contiguously from the chapter's opening
characters decoded with a reversible codec, never from a keyword SQL search.
Source SHA, chapter body SHA, line positions and unit hashes bind the text.
Only hashes/lengths leave the module in a report. Text stays in-process.

This is a separately versioned B01 protocol-only trial eligibility check;
it does not retroactively change V76 B00 strict admission or literary level.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from .wf_self_learning_admission import _scan_document
from .wf_charset_byte_review import byte_charset_audit

MIN_UNIT_CHARS = 30
TARGET_UNIT_CHARS = 440
MAX_UNIT_CHARS = 900
MAX_CHAPTER_CHARACTERS = 180_000
BREAKS = frozenset("。！？；!?;\n")
ALLOWED_ENCODINGS = frozenset(("utf-8","utf-8-sig","gb18030"))
B01_POLICY="writerforge.b01-prefix-protocol-only.v78"


class WFPrefixReviewError(ValueError):
    pass


def check(yes, code):
    if not yes:raise WFPrefixReviewError(code)


def text_sha(txt):
    return sha256(txt.encode("utf-8")).hexdigest()


def _split_into_ordered_units(body):
    """Partition the entire chapter exactly; never drop blank lines."""
    check(isinstance(body,str) and 60<=len(body)<=MAX_CHAPTER_CHARACTERS,
          "WF_PREFIX_BODY_EMPTY_OR_OVERSIZED")
    out=[]
    start=0
    while start<len(body):
        remain=len(body)-start
        if remain<=TARGET_UNIT_CHARS:
            end=len(body)
        else:
            tentative=min(start+TARGET_UNIT_CHARS,len(body))
            search_start=start+max(MIN_UNIT_CHARS,140)
            candidates=[i+1 for i in range(search_start,tentative)
                        if body[i] in BREAKS]
            end=candidates[-1] if candidates else tentative
            if len(body)-end<MIN_UNIT_CHARS and len(body)-start<=MAX_UNIT_CHARS:
                end=len(body)
        check(start<end<=len(body) and
              MIN_UNIT_CHARS<=end-start<=MAX_UNIT_CHARS,
              "WF_PREFIX_UNSAFE_UNIT_BOUNDARY")
        out.append(body[start:end])
        start=end
        check(len(out)<=2000,"WF_PREFIX_TOO_MANY_UNITS")
    check("".join(out)==body,
          "WF_PREFIX_LOST_OR_REORDERED_SOURCE_TEXT")
    return out


def review_first_chapter_windows(path,*,source_sha256,source_bytes,
                                 source_key_sha256,unit_count=3):
    """Return private source windows and metadata-only provenance receipt.

    Caller must never log the source units; only the receipt leaves Railway.
    """
    check(type(unit_count) is int and 2<=unit_count<=3,
          "WF_PREFIX_ONLY_TWO_TO_THREE_UNITS")
    charset=byte_charset_audit(
        path,expected_source_sha256=source_sha256,
        expected_size=source_bytes,
        expected_key_sha256=source_key_sha256)
    aliases=charset["unique_reading_codec_aliases"]
    check(charset["plausible_distinct_decoded_texts"]==1,
          "WF_PREFIX_CHARSET_ALTERNATE_READING_REVIEW_REQUIRED")
    code=next((x for x in ("gb18030","utf-8-sig","utf-8")
               if x in aliases),None)
    check(code in ALLOWED_ENCODINGS,
          "WF_PREFIX_REVERSIBLE_DECODER_NOT_SUPPORTED")
    chapters,summary=_scan_document(path,code)
    first=chapters[0]
    check(first.ordinal==1 and first.body_characters>0 and
          first.body_characters<=MAX_CHAPTER_CHARACTERS,
          "WF_PREFIX_FIRST_CHAPTER_NOT_POSITIONALLY_VALID")
    check(summary["boundary_rule_agreement"] is True and
          summary["boundary_rule_disagreements"]==0 and
          summary["duplicate_printed_numbers"]==0 and
          summary["printed_order_backward_or_equal_steps"]==0 and
          summary["printed_order_forward_gaps"]==0 and
          not summary["prelude_requires_review"] and
          summary["chapters_with_unverified_numerals"]==0,
          "WF_PREFIX_DOCUMENT_STRUCTURE_NOT_AGREED")
    with Path(path).open("r",encoding=code,errors="strict",
                         newline=None) as stream:
        stream.seek(first.start_cookie)
        body=[]
        while stream.tell()<first.end_cookie:
            before=stream.tell()
            line=stream.readline()
            check(bool(line) and stream.tell()>before,
                  "WF_PREFIX_SOURCE_READER_STOPPED_EARLY")
            body.append(line)
        check(stream.tell()==first.end_cookie,
              "WF_PREFIX_CHAPTER_END_NOT_EXACT")
        chapter_body="".join(body)
    check(len(chapter_body)==first.body_characters and
          text_sha(chapter_body)==first.body_sha256,
          "WF_PREFIX_CHAPTER_CONTENT_MISMATCH")
    all_units=_split_into_ordered_units(chapter_body)
    check(len(all_units)>unit_count,
          "WF_PREFIX_NOT_ENOUGH_DISTINCT_UNITS_FOR_PARTIAL_TRIAL")
    chosen=all_units[:unit_count]
    check(chapter_body.startswith("".join(chosen)),
          "WF_PREFIX_OPENING_NOT_CONTIGUOUS")
    receipt={
       "status":"WF_B01_PREFIX_PREPARED_NO_PAID_MODEL",
       "format":B01_POLICY,
       "source_sha256":source_sha256,
       "source_key_sha256":source_key_sha256,
       "chapter_body_sha256":first.body_sha256,
       "first_chapter_source_line":first.source_line,
       "first_chapter_end_line":first.source_end_line,
       "printed_chapter_number":first.printed_number,
       "first_chapter_characters":first.body_characters,
       "whole_chapter_unit_count":len(all_units),
       "small_trial_units":unit_count,
       "trial_unit_characters":[len(u) for u in chosen],
       "trial_unit_sha256":[text_sha(u) for u in chosen],
       "prefix_sha256":text_sha("".join(chosen)),
       "chapter_coverage_is_100_percent":False,
       "chapters_claimed_fully_read":0,
       "source_edition_human_confirmed":False,
       "charset_has_one_strict_reversible_reading":True,
       "charset_variants_identical":aliases,
       "frozen_B00_admission_standard_unchanged":True,
       "wf_literary_genre_classified":False,
       "deepseek_model_requests":0,
       "r2_learn_events_written":0,
       "source_text_or_title_in_receipt":False,
    }
    return tuple(chosen),receipt
