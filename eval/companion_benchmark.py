"""Deterministic workload + informal timing for bounded WriterForge companion cost.

These microbenchmarks do NOT measure model throughput or literary quality.
"""
import json
from pathlib import Path
import tempfile
from time import perf_counter

from writerforge import RuntimeEngine, WriterForgeDB, WritingFlow


def main():
    with tempfile.TemporaryDirectory() as folder:
        db = WriterForgeDB(Path(folder) / "bench.sqlite3")
        runtime = RuntimeEngine()
        runtime.enter_write(1)
        flow = WritingFlow(db, runtime, "bench")
        start_writing = perf_counter()
        # Longer than the 32-scene active-memory window.
        for i in range(256):
            flow.accept_draft(
                f"commit-{i}", f"chapter-{i // 16}.scene-{i}",
                f"第{i}场。风压低了檐角，他接过那盏灯，没有多说一个字。",
                origin="author_edited" if i % 5 == 0 else "accepted",
            )
        written_secs = perf_counter() - start_writing

        start_context = perf_counter()
        for _ in range(5000):
            frame = flow.begin_draft("chapter-16.scene-1", concerns=("dialogue",))
        read_secs = perf_counter() - start_context
        active = db.conn.execute(
            "SELECT COUNT(*) n FROM writer_companion_samples WHERE project_id='bench'"
        ).fetchone()["n"]
        profile = db.conn.execute(
            "SELECT accepted_revisions,authored_scopes FROM writer_companion_profiles WHERE project_id='bench'"
        ).fetchone()
        result = {
            "scenario": "256 changed scenes + 5000 same-scene draft context requests",
            "accepted_commits": profile["accepted_revisions"],
            "active_samples": active,
            "active_author_scopes": profile["authored_scopes"],
            "cache_hits": flow.companion.cache_hits,
            "profile_loads": flow.companion.profile_loads,
            "cached_contexts": flow.companion.cached_context_count,
            "prompt_chars": len(frame.companion_guidance),
            "accepted_commits_seconds": round(written_secs, 4),
            "repeated_context_seconds": round(read_secs, 4),
            "microbenchmark_note": "Python/SQLite overhead only; not LLM generation speed or reader quality.",
        }
        assert active <= 32
        assert result["prompt_chars"] <= 768
        assert result["profile_loads"] == 1
        assert result["cache_hits"] >= 4999
        db.close()
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
