"""Read-only REAL pinned source P0 preflight; no LLM or source egress.

Print only counts/hashes and whether source paragraph selectors can be used.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
from writerforge.modern_source import _encoding
from writerforge.reverse_real_training import first_chapter_windows
from writerforge.reverse_mechanism_boundary import source_paragraphs, TECHNIQUES
from writerforge.r2_storage import R2Config, _digest
from writerforge.single_work_runner import SingleWorkVault

SOURCE_SHA="86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28"
SOURCE_BYTES=8_254_079


def main():
    cfg=R2Config.from_environment()
    if cfg.bucket!="writerforge-private-library":
        raise RuntimeError("not private R2")
    vault=SingleWorkVault(cfg,work_id="wudongqiankun")
    verified=vault.verify_existing_single_work()
    if verified is None or (verified["utf8_sha256"],verified["utf8_bytes"])!=(SOURCE_SHA,SOURCE_BYTES):
        raise RuntimeError("pinned source archive not verified")
    with TemporaryDirectory(prefix="v28-p0-preflight-") as temp:
        original=Path(temp)/"original.private"
        vault.client.download_file(cfg.bucket,vault._blob_key("wudongqiankun",SOURCE_SHA),str(original))
        if _digest(original)!=(SOURCE_SHA,SOURCE_BYTES):
            raise RuntimeError("fresh original failed hash verification")
        plan,(first,second)=first_chapter_windows(original,_encoding(original),SOURCE_SHA)
        paras=source_paragraphs(first)
        # Explicitly check the original has not been chopped to skip content
        # merely to make the P0 mechanism selector fit.
        assert plan["units"][0]["start"]==0
        assert plan["units"][0]["end"]==len(first)
        assert plan["units"][1]["start"]==len(first)
        print(json.dumps({
            "stage":"V28_P0_PINNED_SOURCE_GATE_VERIFIED",
            "source_sha256":SOURCE_SHA,
            "chapter":1,
            "first_window_sha256":plan["units"][0]["segment_sha256"],
            "first_window_chars":len(first),
            "next_window_connected":True,
            "paragraphs":len(paras),
            "max_paragraph_chars":max(len(p["text"]) for p in paras),
            "allowed_transfer_mechanisms":len(TECHNIQUES),
            "model_calls":0,
            "paid_token_usage":0,
            "novel_or_draft_text_in_logs":False,
            "literary_quality_verified":False,
        },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
