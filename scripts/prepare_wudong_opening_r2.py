"""READ-ONLY private original -> sequential opening candidates -> metadata R2.

No original text in public GitHub, log, artifact, or model conversation.
No writing/review is performed at this stage.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys

from writerforge.modern_source import _encoding
from writerforge.reverse_source_cursor import opening_chapter_plan
from writerforge.r2_storage import R2Config, R2StudyVault, _canonical, _digest
from writerforge.single_work_runner import SingleWorkVault

WORK = "wudongqiankun"
SOURCE_SHA = "86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28"
SOURCE_BYTES = 8_254_079
METADATA_PREFIX = "writerforge/v1/reverse-craft/wudongqiankun/opening-source"


def main() -> None:
    cfg = R2Config.from_environment()
    if cfg.bucket != "writerforge-private-library":
        raise RuntimeError("source: wrong private R2 bucket")
    vault = SingleWorkVault(cfg, work_id=WORK)
    receipt = vault.verify_existing_single_work()
    if (receipt is None or receipt["utf8_sha256"] != SOURCE_SHA
        or receipt["utf8_bytes"] != SOURCE_BYTES):
        raise RuntimeError("source: pinned R2 original mismatched")
    with TemporaryDirectory(prefix="wf-wudong-start-") as folder:
        source = Path(folder) / "private-source.txt"
        vault.client.download_file(cfg.bucket, vault._blob_key(WORK,SOURCE_SHA), str(source))
        if _digest(source) != (SOURCE_SHA,SOURCE_BYTES):
            raise RuntimeError("download: first private download SHA mismatch")
        plan = opening_chapter_plan(
            source, _encoding(source), expected_source_sha256=SOURCE_SHA,
        )
        plan["source_bytes"]=SOURCE_BYTES
        plan["source_fresh_restored_sha256_verified"]=True
        serialized = _canonical(plan)
        if len(serialized)>32_768:
            raise RuntimeError("plan exceeds safe metadata size")
        digest=sha256(serialized).hexdigest()
        key=f"{METADATA_PREFIX}/{digest}.json"
        # Fail closed if R2 writes or future reads are tampered; never log
        # the novel's original prose or raw decrypted content.
        reader=R2StudyVault(cfg)
        reader._put_small_immutable(key,serialized,digest)
        recovered=reader._get_small(key,32768)
        if recovered!=serialized or sha256(recovered).hexdigest()!=digest:
            raise RuntimeError("restore: opening metadata fresh GET hash mismatch")
        print(json.dumps({
            "work_id":WORK,
            "status":"opening_layout_metadata_private_r2_verified",
            "source_sha256":SOURCE_SHA,
            "source_bytes":SOURCE_BYTES,
            "first_three_chapter_headers":plan["first_three_chapter_headers"],
            "chapter1_chars":plan["chapter_body_chars"],
            "windows":plan["units"],
            "windows_contiguous":plan["continuity"]["no_skipped_prose"],
            "semantic_scene_boundary_verified":False,
            "model_writing_executed":False,
            "independent_critic_executed":False,
            "metadata_r2_key":key,
            "metadata_sha256":digest,
            "fresh_r2_metadata_recovery":True,
        },ensure_ascii=False,indent=2))


if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status":"fail_closed","stage":"source_window_or_R2_metadata",
                          "error_type":type(exc).__name__,
                          "error":str(exc)[:180]},ensure_ascii=False),file=sys.stderr)
        raise SystemExit(1)
