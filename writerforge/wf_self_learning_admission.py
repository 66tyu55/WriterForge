"""V73 WF-owned intake for sequential learning, not an external tutor.

R2 is storage, SQL is evidence location, WF LEARN owns book selection,
classification, chapter numbering, first read, analysis and its own
checkpoint. This module performs ONLY model-free document admission.

It NEVER claims learning/mastery from extracted headings or lexical SQL
matches. Without an actual WF model + durable, immutable LEARN evidence
journal it stops before first-read, rather than asking ChatGPT to invent it.

Each Railway invocation processes at most ONE book. Any source bytes stay
inside the Railway WF process; only bounded hashed receipts leave it.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
import re

from .bulk_inbox import PRIVATE_READING,parse_key,CHAPTER as LEGACY_CHAPTER_RULE
from .source_study import chapter_number,StudyError
from .source_encoding_guard import detect_decoding_for_index,SourceEncodingError
from .runtime import Mode,RuntimeEngine

MAX_ONE_SOURCE=16*1024*1024
MAX_CHAPTERS=2000
MAX_CHAPTER_CHARS=180_000
MAX_PROLOGUE_CHARS=250_000
FIRST_READ_WINDOW_CHARS=4600
MAX_PUBLIC_ERRORS=80

# Only headings at physical line boundaries, never guessed literary meaning.
CHAPTER_LINE=re.compile(
    r"^\s*第(?P<printed>[0-9一二三四五六七八九十百千万零〇○两兩]{1,15})"
    r"(?P<kind>章|回|节|節)\s*(?P<title>.{0,120})\s*$"
)
ALTERNATE_LINE=re.compile(r"^\s*(序章|楔子|尾声|尾聲|终章|終章)\s*$")
HASH=re.compile(r"[a-f0-9]{64}\Z")

class WFLearnAdmissionError(ValueError):
    pass

def need(flag,code):
    if not flag:raise WFLearnAdmissionError(code)

def _printed_integer(value):
    # Deliberately refuse unknown Chinese-number spellings rather than
    # silently guessing ordinal from a printed label.
    try:
        return chapter_number(value)
    except StudyError:
        return None

@dataclass(frozen=True)
class SourceChapter:
    ordinal:int
    source_line:int
    source_end_line:int
    printed_number:int|None
    heading_sha256:str
    body_sha256:str
    body_characters:int
    paragraphs:int
    start_cookie:int
    end_cookie:int

    def safe_receipt(self):
        return {
           "ordinal":self.ordinal,
           "source_line":self.source_line,
           "source_end_line":self.source_end_line,
           "printed_number":self.printed_number,
           "heading_sha256":self.heading_sha256,
           "body_sha256":self.body_sha256,
           "body_characters":self.body_characters,
           "paragraphs":self.paragraphs,
        }

def _is_heading(line):
    # Chapter detection is intentionally lexical: *candidate boundary*.
    raw=line.strip()
    match=CHAPTER_LINE.fullmatch(raw)
    if match:
        return _printed_integer(match.group("printed"))
    if ALTERNATE_LINE.fullmatch(raw):
        return None
    return False

def _scan_document(path,encoding):
    """Single-pass bounded chapter outline and positional evidence.

    Text decoding uses errors=strict. No future text enters a model prompt,
    classifier response, study entry or public log in this phase.
    """
    chapters=[]
    seen_printed=set()
    prelude_chars=0
    physical_lines=0
    total_chars=0
    chapter=None
    legacy_candidate_headings=0
    boundary_rule_disagreements=0
    disagreement_heading_hashes=[]
    with Path(path).open("r",encoding=encoding,errors="strict",
                         newline=None) as stream:
        while True:
            cookie=stream.tell()
            line=stream.readline()
            if not line:break
            physical_lines+=1
            total_chars+=len(line)
            need(total_chars<=MAX_ONE_SOURCE*2,
                 "WF_ADMISSION_DECODED_TEXT_OVER_BUDGET")
            need(len(line)<=MAX_CHAPTER_CHARS,
                 "WF_ADMISSION_PHYSICAL_LINE_OVER_BUDGET")
            printed=_is_heading(line)
            legacy=bool(LEGACY_CHAPTER_RULE.fullmatch(line.strip()))
            current=printed is not False
            if legacy:
                legacy_candidate_headings+=1
            if legacy != current:
                boundary_rule_disagreements+=1
                if len(disagreement_heading_hashes)<8:
                    disagreement_heading_hashes.append(
                        sha256(line.strip().encode("utf-8")).hexdigest())
            if current:
                if chapter is not None:
                    chapter["end_cookie"]=cookie
                    chapter["source_end_line"]=physical_lines-1
                    chapters.append(_seal(chapter))
                need(len(chapters)<MAX_CHAPTERS,
                     "WF_ADMISSION_TOO_MANY_CHAPTER_HEADERS")
                heading=line.strip()
                if printed is not None:
                    need(printed not in seen_printed,
                         "WF_ADMISSION_DUPLICATE_PRINTED_CHAPTER")
                    seen_printed.add(printed)
                chapter={
                    "ordinal":len(chapters)+1,
                    "source_line":physical_lines,
                    "printed_number":printed,
                    "heading_sha256":sha256(heading.encode("utf-8")).hexdigest(),
                    "hash":sha256(),
                    "body_characters":0,
                    "paragraphs":0,
                    "start_cookie":stream.tell(),
                }
                continue
            if chapter is None:
                prelude_chars+=len(line)
                need(prelude_chars<=MAX_PROLOGUE_CHARS,
                     "WF_ADMISSION_PRELUDE_OVER_BUDGET")
                continue
            # Stable per-chapter verification of the exact decoded text,
            # not copied excerpts, emotions, or learned literary effects.
            chapter["hash"].update(line.encode("utf-8"))
            chapter["body_characters"]+=len(line)
            if line.strip():chapter["paragraphs"]+=1
            need(chapter["body_characters"]<=MAX_CHAPTER_CHARS,
                 "WF_ADMISSION_CHAPTER_OVER_BUDGET")
        if chapter is not None:
            chapter["end_cookie"]=stream.tell()
            chapter["source_end_line"]=physical_lines
            chapters.append(_seal(chapter))
    need(bool(chapters),"WF_ADMISSION_NO_UNAMBIGUOUS_CHAPTER_HEADINGS")
    need(len(chapters)>=2,"WF_ADMISSION_ONLY_ONE_BOUNDARY_NEEDS_REVIEW")
    # Only numeric printed labels enforce monotonic known ordinals. Chinese
    # headings without a verified numeral map remain unknown, not invented.
    numeric=[c.printed_number for c in chapters
             if c.printed_number is not None]
    if numeric:
        need(all(a<b for a,b in zip(numeric,numeric[1:])),
             "WF_ADMISSION_PRINTED_CHAPTER_ORDER_NONMONOTONIC")
        need(all(b==a+1 for a,b in zip(numeric,numeric[1:])),
             "WF_ADMISSION_NONCONSECUTIVE_PRINTED_CHAPTERS")
    for ch in chapters:
        need(ch.body_characters>0,"WF_ADMISSION_EMPTY_CHAPTER")
    return chapters,{
       "physical_lines":physical_lines,
       "chapters_detected":len(chapters),
       "numbered_chapters":len(numeric),
       "chapters_with_unverified_numerals":len(chapters)-len(numeric),
       "prelude_characters":prelude_chars,
       "prelude_requires_review":prelude_chars>1200,
       "ordinal_numbers_are_internal_not_source_authentication":True,
       "chapter_boundaries_are_structural_candidates":True,
       "legacy_sql_heading_candidates":legacy_candidate_headings,
       "boundary_rule_disagreements":boundary_rule_disagreements,
       "boundary_rule_agreement":boundary_rule_disagreements==0,
       "disagreement_heading_hashes":disagreement_heading_hashes,
       "no_parser_is_claimed_as_literary_ground_truth":True,
    }

def _seal(row):
    return SourceChapter(
        ordinal=row["ordinal"],
        source_line=row["source_line"],
        source_end_line=row["source_end_line"],
        printed_number=row["printed_number"],
        heading_sha256=row["heading_sha256"],
        body_sha256=row["hash"].hexdigest(),
        body_characters=row["body_characters"],
        paragraphs=row["paragraphs"],
        start_cookie=row["start_cookie"],
        end_cookie=row["end_cookie"],
    )

def admit_source(path,*,original_key,verified_original_sha256,
                 downloaded_size,source_etag=None,
                 runtime=None):
    """Called by WF, not its examiner. Never persists a 'trained' mark."""
    rt=runtime if runtime is not None else RuntimeEngine()
    rt.enter_learn()
    try:
        metadata=parse_key(original_key)
        need(original_key.startswith(PRIVATE_READING) and
             metadata["ext"]==".txt",
             "WF_ADMISSION_NOT_APPROVED_PRIVATE_TXT")
        source=Path(path)
        need(source.is_file() and
             type(downloaded_size) is int and
             1024<=downloaded_size<=MAX_ONE_SOURCE and
             source.stat().st_size==downloaded_size,
             "WF_ADMISSION_SOURCE_SIZE_OR_FILE_INVALID")
        need(isinstance(verified_original_sha256,str) and
             HASH.fullmatch(verified_original_sha256),
             "WF_ADMISSION_SOURCE_SHA_UNAVAILABLE")
        whole=sha256()
        with source.open("rb") as fh:
            for chunk in iter(lambda:fh.read(1024*1024),b""):
                whole.update(chunk)
        need(whole.hexdigest()==verified_original_sha256,
             "WF_ADMISSION_SOURCE_CHANGED_SINCE_DOWNLOAD")
        guard=detect_decoding_for_index(source)
        chapters,scan=_scan_document(source,guard["encoding"])
        first=chapters[0]
        manifest={
           "format":"writerforge.wf-own-admission.v1",
           "work_id":"b_"+verified_original_sha256[:32],
           "source_sha256":verified_original_sha256,
           "source_bytes":downloaded_size,
           "source_key_sha256":sha256(original_key.encode("utf-8")).hexdigest(),
           "hint_from_r2_folder_only":metadata["category"],
           "WF_genre_classification":"UNDECIDED",
           "WF_genre_classification_evidence":False,
           "WF_visible_future_chapters_during_first_read":False,
           "source_edition_human_confirmed":False,
           "decoding":guard["encoding"],
           "decoding_provisional":bool(guard["provisional_legacy_decoding"]),
           "document_scan":scan,
           "first_chapter":first.safe_receipt(),
           "chapter_outline_sha256":sha256(json.dumps(
               [c.safe_receipt() for c in chapters],
               sort_keys=True,ensure_ascii=False,
               separators=(",",":")).encode("utf-8")).hexdigest(),
           # All important assertions below are FALSE until WF's own LEARN
           # engine calls a real model, saves PASS A before PASS B to private
           # R2, independently verifies the evidence, and records learning.
           "source_text_returned_to_examiner":False,
           "assistant_selected_work":False,
           "WF_first_read_executed":False,
           "WF_literary_classification_executed":False,
           "WF_craft_analysis_executed":False,
           "WF_learning_checkpoint_persisted_to_r2":False,
           "WF_skill_upgrade_certified":False,
           "learned_chapters":0,
           "model_calls":0,
           "remote_writes":0,
           "status":"WF_DOCUMENT_ADMITTED_LEARN_ENGINE_PENDING",
        }
        reasons=[]
        if scan["boundary_rule_disagreements"]>0:
            reasons.append("WF_CHAPTER_BOUNDARY_PARSERS_DISAGREE")
        if guard["provisional_legacy_decoding"]:
            reasons.append("PROVISIONAL_ENCODING_REQUIRES_VERIFICATION")
        if scan["prelude_requires_review"]:
            reasons.append("PRELUDE_BOUNDARY_REQUIRES_REVIEW")
        if scan["chapters_with_unverified_numerals"]>0:
            reasons.append("PRINTED_CHAPTER_NUMERALS_NEED_WF_REVIEW")
        reasons.append("WAITING_FOR_WF_MODEL_AND_IMMUTABLE_LEARN_JOURNAL")
        manifest["training_gate_reasons"]=reasons
        manifest["training_gate"]=reasons[0]
        if len(reasons)>1:
            manifest["status"]="WF_DOCUMENT_ADMISSION_REVIEW_REQUIRED"
        return manifest
    except SourceEncodingError as e:
        raise WFLearnAdmissionError(str(e)) from None
    finally:
        rt.exit()
