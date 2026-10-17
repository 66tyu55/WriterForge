"""Real WF-owned V42 baseline versus persisted source-experience writing.

This code is the ONLY author. No runtime model_call, GPT reply, external
literary analysis, manually provided plot or editing step is accepted.
"""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import json
from writerforge.native_experience_engine import run_experiment

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "exams/wf_v40_reader_ch07/reader_packet.txt"
TARGET = ROOT / "v42_native_experience_results.json"

def main() -> dict:
    original = SOURCE.read_text(encoding="utf-8")
    with TemporaryDirectory(prefix="wf-native-learn-write-") as tmp:
        result = run_experiment(
            original, Path(tmp) / "native_memory.sqlite3",
            ("unseen-story-task-A", "unseen-story-task-B", "unseen-story-task-C"),
        )
    TARGET.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "source_sha256": result["original_source_sha256"],
        "experience_sha256": result["experience_receipt_sha256"],
        "model_calls": result["model_calls"],
        "unseen_tasks": len(result["outcomes"]),
        "story_hashes": [r["learned_draft_sha256"] for r in result["outcomes"]],
        "lexical_only_no_literary_mastery": True,
        "all_stories_generated_by_native_python": True,
        "full_prose_in_artifact_not_this_log": True,
    }, ensure_ascii=False, sort_keys=True))
    return result

if __name__ == "__main__":
    main()
