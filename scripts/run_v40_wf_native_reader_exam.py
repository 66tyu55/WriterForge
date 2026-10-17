"""V40: execute the existing WF chapter-reader ONLY, never write examiner answers.

This is a capability probe, not a semantic model simulation. No credential,
model, web lookup, critic, prefilled reaction or generated draft is permitted.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import socket
import tempfile
import urllib.request

from writerforge.db import WriterForgeDB
from writerforge.runtime import RuntimeEngine
from writerforge.source_study import OriginalStudy, parse_original, _unitize, MAX_EXCERPT

EXAM = Path(__file__).resolve().parents[1] / "exams" / "wf_v40_reader_ch07"
DISALLOWED_KEYS = (
    "DISCOVERY_API_KEY", "DISCOVERY__API__KEY", "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY",
)


class ReaderExamError(RuntimeError):
    pass


def _load_package(root: Path):
    m = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    packet = (root / "reader_packet.txt").read_bytes()
    if m.get("exam_id") != "WF-V40-NO-MODEL-READER-001":
        raise ReaderExamError("EXAM_ID_CHANGED")
    blob_hash = hashlib.sha1(f"blob {len(packet)}\0".encode("ascii") + packet).hexdigest()
    if blob_hash != m["integrity"]["reader_packet_git_blob_sha1"]:
        raise ReaderExamError("CHAPTER_PACKET_BLOB_SHA1_MISMATCH")
    text = packet.decode("utf-8")
    if len(text) != m["integrity"]["characters"]:
        raise ReaderExamError("CHAPTER_PACKET_CHARACTERS_CHANGED")
    ch = parse_original(text, require_hundred=False, expected_count=1)
    if len(ch) != 1 or ch[0].number != 1 or len(ch[0].text) < 5000:
        raise ReaderExamError("CHAPTER_PACKET_NOT_NATIVE_READABLE")
    if m["source"]["original_chapter_number"] != 7:
        raise ReaderExamError("CHAPTER_ORIGINAL_ID_CHANGED")
    if not m["native_parser"]["slot_is_not_original_chapter_number"]:
        raise ReaderExamError("EXAM_SLOT_MISREPRESENTED_AS_ORIGINAL_NUMBER")
    return m, text, ch[0]


def run(*, root: Path = EXAM) -> dict:
    if any(os.getenv(key) for key in DISALLOWED_KEYS):
        raise ReaderExamError("MODEL_CREDENTIALS_PRESENT_IN_NO_MODEL_EXAM")
    # Block accidental network inside this examination process; no new
    # provider transport or original-book download is allowed.
    original_socket_connect = socket.socket.connect
    original_urlopen = urllib.request.urlopen
    def deny(*args, **kwargs):
        raise ReaderExamError("EXTERNAL_NETWORK_OR_MODEL_CALL_FORBIDDEN")
    socket.socket.connect = deny
    urllib.request.urlopen = deny
    try:
        manifest, text, chapter = _load_package(root)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        source_unit_texts = [piece for _, _, piece in _unitize(chapter, wrapped_lines=True)]
        truncated_units = sum(len(piece) > MAX_EXCERPT for piece in source_unit_texts)
        with tempfile.TemporaryDirectory(prefix="wf-v40-selfreader-") as folder:
            dbpath = Path(folder) / "isolated.sqlite3"
            db = WriterForgeDB(dbpath)
            rt = RuntimeEngine()
            rt.enter_learn()
            work_id = "wf-v40-exam-laocan-original-ch07-isolated"
            try:
                learned = OriginalStudy(db, rt).ingest(
                    text, work_id=work_id, title="老殘遊記第七回（试卷槽位一）",
                    source_uri=manifest["source"]["source_page"],
                    require_hundred=False, expected_count=1,
                    wrapped_lines=True,
                )
                rows = db.conn.execute(
                    "SELECT COUNT(*) n FROM source_spans WHERE work_id=?",
                    (work_id,),
                ).fetchone()["n"]
                chapters = db.conn.execute(
                    "SELECT chapter_sha256 FROM studied_chapters WHERE work_id=?",
                    (work_id,),
                ).fetchall()
                observed = db.conn.execute(
                    "SELECT COUNT(*) n FROM xuehai_entries WHERE work_id=?",
                    (work_id,),
                ).fetchone()["n"]
            finally:
                db.close()
            reopened = WriterForgeDB(dbpath)
            try:
                after_restart = reopened.conn.execute(
                    "SELECT COUNT(*) n FROM source_spans WHERE work_id=?",
                    (work_id,),
                ).fetchone()["n"]
                chapter_count = reopened.conn.execute(
                    "SELECT COUNT(*) n FROM studied_chapters WHERE work_id=?",
                    (work_id,),
                ).fetchone()["n"]
            finally:
                reopened.close()

        if (learned["newly_studied"] != 1
            or len(chapters) != 1
            or chapters[0]["chapter_sha256"] != chapter.fingerprint
            or observed < 1 or rows != after_restart
            or chapter_count != 1):
            raise ReaderExamError("WF_READER_REAL_STORAGE_OR_RECOVERY_FAILED")
        result = {
            "format": "writerforge.v40-native-unassisted-reader-receipt.v1",
            "exam_id": manifest["exam_id"],
            "source_work": manifest["source"]["work_title"],
            "original_chapter": 7,
            "internal_native_parse_slot": 1,
            "packet_sha256": digest,
            "original_body_sha256": chapter.fingerprint,
            "source_body_characters": len(chapter.text),
            "real_source_units": len(source_unit_texts),
            "sqlite_source_spans": rows,
            "sqlite_xuehai_retrievable_excerpt_entries": observed,
            "verified_after_process_restart": after_restart == rows,
            "source_units_over_160_characters_truncated_in_sqlite_excerpts": truncated_units,
            "unmodified_full_original_remains_in_external_input_packet": True,
            "stages": {
                "R_IO_chapter_parsing": "PASS",
                "R_IO_ordered_structural_ingestion": "PASS",
                "R_IO_sqlite_recovery": "PASS",
                "R_TRACE_independent_first_read_reactions": "BLOCKED_NEEDS_SEMANTIC_RESPONDER",
                "R_ANALYZE_character_knowledge_and_causality": "BLOCKED_NEEDS_SEMANTIC_RESPONDER",
                "R_CRAFT_literary_mechanism_hypotheses": "BLOCKED_NEEDS_SEMANTIC_RESPONDER",
                "W_CLOSED_independent_original_prose": "BLOCKED_NO_MODEL_FREE_PROSE_GENERATOR",
                "R_REVIEW_independent_literary_selfcritique": "BLOCKED_NO_SEMANTIC_DRAFT",
            },
            "reason": (
                "OriginalStudy performs structural segmentation and lexical tagging. "
                "ReaderLearningSession records caller-supplied reactions; "
                "SceneLiteraryStudy.run requires a model_call argument; "
                "VerifiedWritingFlow prepares prompts but does not synthesize prose. "
                "Without a WF-attached semantic engine, never invent notes, "
                "knowledge-chain reasoning or creative writing."
            ),
            "model_calls": 0,
            "examiner_answers_supplied": False,
            "full_literary_understanding_proven": False,
            "skill_promotion": False,
        }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return result
    finally:
        socket.socket.connect = original_socket_connect
        urllib.request.urlopen = original_urlopen


if __name__ == "__main__":
    run()
