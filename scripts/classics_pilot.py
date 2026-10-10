"""Per-book execution and efficacy audit -- no simulated literary grades.

This audit answers the user's actual concern: which WriterForge components ran
for THIS original corpus, which only exist as APIs, and whether any tracked
source evidence appeared in a verifiable writing packet. It intentionally
does NOT perform global 50-work literary evaluation.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from pathlib import Path
import json
import sys
import time
import tracemalloc

from writerforge.classics_catalog import get_book, study_book
from writerforge import WriterForgeDB, RuntimeEngine, OriginalStudy, VerifiedWritingFlow


STAGES = {
    "edition_hash_and_language": "executed",
    "chapter_boundaries_and_order": "executed",
    "paragraph_and_sentence_provenance": "executed",
    "eight_tracks": "executed_heuristics_only",
    "sentence_functions": "executed_heuristics_only",
    "published_xuehai_database": "executed",
    "restart_durable_read": "executed",
    "retrieval_in_draft_context": "executed",
    "reader_first_reactions": "not_invoked",
    "deep_literary_craft_analysis": "not_implemented_in_source_pipeline",
    "craft_training_from_external_reader": "not_invoked",
    "real_human_review": "not_invoked",
    "live_litcritic_review": "not_invoked",
    "model_finetuning": "not_performed",
    "real_prose_generation": "not_performed_in_this_pilot",
    "cross_work_50_book_assessment": "deferred_until_50_distinct_works",
}


def audit_source(db: WriterForgeDB, work_id: str) -> dict:
    stats = {
        "track_nonempty":Counter(),
        "function_samples":Counter(),
        "missing_craft":0,
        "source_units":0,
        "source_chunks_over_160":0,
        "provenance_issues":0,
    }
    # Stream row-by-row; no novel-long list of JSON objects in RAM.
    rows = db.conn.execute(
        """SELECT tracks_json,craft_json,paragraph,sentence,excerpt
           FROM source_spans WHERE work_id=?
           ORDER BY chapter,paragraph,sentence""", (work_id,),
    )
    for row in rows:
        tracks=json.loads(row["tracks_json"])
        craft=json.loads(row["craft_json"])
        stats["source_units"]+=1
        for name in ("plot","object","character","environment",
                     "time","location","sense","emotion"):
            if tracks.get(name):
                stats["track_nonempty"][name]+=1
        kind=craft.get("sentence_function")
        stats["function_samples"][kind or "missing"]+=1
        if craft.get("analysis_level") != "deterministic_structural_unverified":
            stats["missing_craft"]+=1
        if row["paragraph"]<1 or row["sentence"]<1:
            stats["provenance_issues"]+=1
        if len(row["excerpt"])>160:
            stats["source_chunks_over_160"]+=1
    return {
        "source_units":stats["source_units"],
        "eight_tracks":{"nonempty_unit_counts":dict(stats["track_nonempty"]),
                        "label":"lexical cues only, NOT semantic eight-track comprehension"},
        "functions":dict(stats["function_samples"]),
        "invalid_or_missing_craft_flag":stats["missing_craft"],
        "provenance_issues":stats["provenance_issues"],
        "overlong_excerpt_count":stats["source_chunks_over_160"],
        "stages":STAGES,
        "immediate_findings":[
            "ReaderFirst first-read emotional reaction was never executed; current eight-track labels are lexical heuristics, not deep literary training.",
            "Fine-grained prose Craft/Voice/Taste/Evolution upgrade routes do NOT run in this source-learning job; count them as inactive, not successful.",
            "Source retrieval is genuinely wired to VerifiedWritingFlow, but no model is called in this evidence-only pilot.",
            "No accepted author revisions or independent editorial judgements have been collected for this study.",
        ],
        "cross_work_consolidation_performed":False,
        "threshold":50,
    }


def main():
    if len(sys.argv)!=5:
        raise SystemExit(
            "usage: python scripts/classics_pilot.py honglou|shuihu SOURCE DB OUT_DIR"
        )
    book=get_book(sys.argv[1])
    source=Path(sys.argv[2])
    db_path=Path(sys.argv[3])
    output=Path(sys.argv[4])
    output.mkdir(parents=True,exist_ok=True)
    rt=RuntimeEngine()
    rt.enter_learn()
    tracemalloc.start()
    start=time.monotonic()
    db=WriterForgeDB(db_path)
    try:
        training=study_book(book,source,db,rt)
        duration=time.monotonic()-start
        expected=book.expected_chapters+(1 if book.include_prologue else 0)
        if (not training["structure_complete"]
            or training["studied_chapters"]!=expected
            or training["new_source_spans"]<500):
            raise AssertionError("not all chapters of the correct original edition were durably studied")
        if book.include_prologue:
            prologue=db.conn.execute(
                "SELECT COUNT(*) FROM studied_chapters WHERE work_id=? AND chapter=0",
                (book.work_id,),
            ).fetchone()[0]
            if prologue!=1:
                raise AssertionError("Water Margin prologue was lost")
        audit=audit_source(db,book.work_id)
        if (audit["source_units"]!=training["studied_units"]
            or audit["invalid_or_missing_craft_flag"]
            or audit["provenance_issues"]
            or audit["overlong_excerpt_count"]):
            raise AssertionError("unverified structural evidence corrupted or incomplete")
        # Must close, reopen and use actual published work to prove durable
        # execution rather than mere in-process script memory.
        sid=db.conn.execute(
            "SELECT MAX(id) FROM snapshots WHERE status='published'"
        ).fetchone()[0]
        db.close()
        db=WriterForgeDB(db_path)
        rt.exit()
        rt.enter_write(sid)
        packet=VerifiedWritingFlow(db,rt,"audit-only-original-study").prepare(
            book.key+".first-scene",
            "创作一个原创古风故事，其中人物通过具体选择改变与他人的关系",
            concerns=("dialogue","description"),
        )
        if not packet.evidence or any(r["work_id"]!=book.work_id for r in packet.evidence):
            raise AssertionError("source evidence was not used in verifiable writing context")
        audit["stages"]["retrieval_in_draft_context"]="executed"
        audit["evidence_count_for_draft"]=len(packet.evidence)
        audit["craft_active_ids_in_context"]=list(packet.craft_ids)
        audit["published_snapshot_id"]=sid
        audit["input_sha256"]=training["source_raw_sha256"]
        audit["input_bytes"]=source.stat().st_size
        audit["elapsed_seconds"]=round(duration,2)
        audit["sqlite_bytes"]=db_path.stat().st_size
        _,peak=tracemalloc.get_traced_memory()
        tracemalloc.stop()
        audit["python_tracemalloc_peak_mib"]=round(peak/1048576,2)
        audit["work_title"]=book.title
        audit["work_id"]=book.work_id
        audit["source_page"]=book.source_page
        audit["source_git_blob_sha1"]=book.git_blob_sha1
        audit["full_chapters"]=book.expected_chapters
        audit["prologue_included"]=book.include_prologue
        audit["structurally_complete"]=True
        audit["literary_learning_verified"]=False
        # A trace of actual effects performed. Can be used for later blind
        # evaluation but does not pretend a generation model ran.
        (output/"draft_context.json").write_text(
            json.dumps({**packet.manifest(),"prompt":packet.prompt},ensure_ascii=False,indent=2),
            encoding="utf-8",
        )
        (output/"work_report.json").write_text(
            json.dumps(training,ensure_ascii=False,indent=2),encoding="utf-8",
        )
        (output/"stage_audit.json").write_text(
            json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8",
        )
        (output/"STAGE_AUDIT.md").write_text(
            f"# {book.title} 顺序学习实测报告\n\n"
            f"- Project Gutenberg 原著：{book.source_page}\n"
            f"- 实际读取原文章回：{training['studied_chapters']}（含楔子：{book.include_prologue}）\n"
            f"- 结构化单位：{audit['source_units']}\n"
            f"- 学海可查询条目：{training['retrieval_entries']}\n"
            f"- 写作阶段确实引用来源证据：{audit['evidence_count_for_draft']} 条\n"
            f"- SQLite 文件：{audit['sqlite_bytes']:,} B\n"
            f"- tracemalloc 峰值：{audit['python_tracemalloc_peak_mib']} MiB\n"
            "- ReaderFirst、文学深读、模型训练、真实审稿：未执行\n"
            "- 全语料分析与技能重构：等待至少 50 部不同作品完整学习后再进行\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "work_id":book.work_id,"studied_chapters":training["studied_chapters"],
            "source_units":audit["source_units"],"retrieval_entries":training["retrieval_entries"],
            "sqlite_bytes":audit["sqlite_bytes"],"python_peak_mib":audit["python_tracemalloc_peak_mib"],
            "verified_context_refs":len(packet.evidence),"source_raw_sha256":training["source_raw_sha256"],
            "reader_first_performed":False,
            "cross_work_review_performed":False,
        },ensure_ascii=False))
    finally:
        db.close()


if __name__=="__main__":
    main()
