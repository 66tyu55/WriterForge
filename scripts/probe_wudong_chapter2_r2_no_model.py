"""Read-only chapter TWO layout probe from pinned private R2; zero paid models.

Only numeric sizes, booleans, chapter indices and SHA hashes are printed.
"""
from __future__ import annotations
from tempfile import TemporaryDirectory
from pathlib import Path
import json
from writerforge.reverse_later_window import later_chapter_diagnostic
from writerforge.modern_source import _encoding
from writerforge.r2_storage import R2Config,_digest
from writerforge.single_work_runner import SingleWorkVault
from scripts.run_wudong_chapter2_diagnostic_v6 import WORK,SOURCE_SHA,SOURCE_BYTES


def run():
    cfg=R2Config.from_environment()
    if cfg.bucket!="writerforge-private-library":
        raise RuntimeError("NOT_PRIVATE_BUCKET")
    vault=SingleWorkVault(cfg,work_id=WORK)
    orig=vault.verify_existing_single_work()
    if orig is None or (orig["utf8_sha256"],orig["utf8_bytes"])!=(SOURCE_SHA,SOURCE_BYTES):
        raise RuntimeError("PINNED_SOURCE_CHANGED")
    with TemporaryDirectory(prefix="wf-c2-no-model-") as directory:
        source_path=Path(directory)/"private.txt"
        vault.client.download_file(cfg.bucket,vault._blob_key(WORK,SOURCE_SHA),str(source_path))
        if _digest(source_path)!=(SOURCE_SHA,SOURCE_BYTES):
            raise RuntimeError("FRESH_R2_SOURCE_SHA_FAILED")
        plan,segments=later_chapter_diagnostic(
            source_path,_encoding(source_path),expected_source_sha256=SOURCE_SHA,chapter=2)
        if plan["chapter"]!=2 or len(segments[0])!=plan["windows"][0]["chars"]:
            raise RuntimeError("UNVERIFIED_DIAGNOSTIC_CURSOR")
        result={
            "stage":"CHAPTER2_R2_SOURCE_DIAGNOSTIC_READY",
            "source_sha256":SOURCE_SHA,
            "chapter":2,"chapter_body_sha256":plan["chapter_body_sha256"],
            "chapter_body_chars":plan["chapter_body_chars"],
            "first_window":plan["windows"][0],
            "next_contiguous_window":plan["windows"][1],
            "full_body_reconstructed":plan["full_body_reconstructed"],
            "sequential_headings":plan["chapter_earlier_headings_verified"],
            "semantic_boundary_verified":False,
            "original_download_only_no_new_archive":True,
            "model_calls":0,"first_chapter_literary_gate":"NOT_PASSED",
            "second_curriculum_window":"LOCKED",
        }
        print(json.dumps(result,sort_keys=True,ensure_ascii=False))
        return result


if __name__=="__main__":
    run()
