"""Build and measure a real 100-chapter classical-Chinese study artifact in CI.

No model weights are updated. All spans are structurally segmented in chapter
order; subjective literary study remains explicitly unverified.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from time import perf_counter
import json
import sqlite3
import sys
import tracemalloc

from writerforge import WriterForgeDB, RuntimeEngine, OriginalStudy, VerifiedWritingFlow
from writerforge.source_study import WORK_ID


def main():
    if len(sys.argv)!=4:
        raise SystemExit("usage: python scripts/xiyouji_pilot.py SOURCE_TXT DB OUT_DIR")
    source=Path(sys.argv[1])
    db_path=Path(sys.argv[2])
    out=Path(sys.argv[3])
    out.mkdir(parents=True,exist_ok=True)
    content=source.read_text(encoding="utf-8-sig")
    rt=RuntimeEngine()
    rt.enter_learn()
    tracemalloc.start()
    start=perf_counter()
    db=WriterForgeDB(db_path)
    try:
        result=OriginalStudy(db,rt).ingest(content)
        seconds=perf_counter()-start
        if result["studied_chapters"]!=100 or not result["structure_complete"]:
            raise AssertionError(f"100 chapters were not durably studied: {result}")
        if result["literary_reader_first_complete"]:
            raise AssertionError("structural signals must not be labelled deep literary learning")
        snapshot_rows=db.conn.execute(
            "SELECT id,layout,parent_id FROM snapshots WHERE status='published' ORDER BY id"
        ).fetchall()
        if len(snapshot_rows)!=100 or (
            [x["layout"] for x in snapshot_rows].count("full")!=1
            or [x["layout"] for x in snapshot_rows].count("delta")!=99
        ):
            raise AssertionError("snapshots are not O(chapters) incremental overlays")
        counts=db.conn.execute(
            "SELECT COUNT(*) AS n FROM xuehai_entries"
        ).fetchone()["n"]
        if counts!=result["retrieval_entries"]:
            raise AssertionError("physical retrieval row count diverges from logical corpus entries")
        # Reopen before drafting to prove persistence is not process-local.
        db.close()
        db=WriterForgeDB(db_path)
        rt.exit()
        rt.enter_write(int(snapshot_rows[-1]["id"]))
        flow=VerifiedWritingFlow(db,rt,"xiyouji-training-proof")
        first=flow.prepare(
            "first-original-draft","原创武侠：少年在古渡口为了救人放弃通行符",
            concerns=("dialogue","description"),
        )
        if not first.evidence:
            raise AssertionError("source learning did not enter the writing context")
        (out/"verified_draft_context.json").write_text(
            json.dumps({**first.manifest(),"prompt":first.prompt},
                       ensure_ascii=False,indent=2),encoding="utf-8"
        )
        _,peak=tracemalloc.get_traced_memory()
        tracemalloc.stop()
        result.update(
            source_filename=source.name,
            corpus_bytes=source.stat().st_size,
            sqlite_bytes=db_path.stat().st_size,
            elapsed_seconds=round(seconds,3),
            python_tracemalloc_peak_mib=round(peak/1048576,2),
            published_snapshots=len(snapshot_rows),
            actual_published_context=True,
            retrieved_entries_for_draft=len(first.evidence),
            model_generation_performed=False,
            independent_litcritic_performed=False,
        )
        (out/"training_report.json").write_text(
            json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8"
        )
        (out/"TRAINING_STATUS.md").write_text(
            "# 《西遊記》100回真实原文学习存储报告\n\n"
            f"- 学习来源：GITenberg / Project Gutenberg #23962\n"
            f"- 原文 SHA256：{result['source_sha256']}\n"
            f"- 原文章节：{result['studied_chapters']}/100\n"
            f"- 逐句八轨结构化源单位：{result['studied_units']}\n"
            f"- 可查询原文功能条目：{result['retrieval_entries']}\n"
            f"- 快照：1 个根 + 99 个增量\n"
            f"- SQLite 文件：{result['sqlite_bytes']:,} 字节\n"
            f"- Python tracemalloc 峰值：{result['python_tracemalloc_peak_mib']} MiB\n"
            f"- 已验证重新打开数据库后能生成学海检索上下文\n"
            "- 尚未进行模型参数微调/真人首读文学深度标注\n"
            "- 尚未调用创作模型，尚未用真实 lit-critic 模型评价\n"
            "- 不能将此结构化入库称为文学水平提升\n",
            encoding="utf-8",
        )
        print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    finally:
        db.close()


if __name__=="__main__":
    main()
