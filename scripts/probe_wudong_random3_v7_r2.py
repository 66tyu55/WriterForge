"""Private R2 read-only preflight for three predetermined random later chapters."""
from __future__ import annotations
from tempfile import TemporaryDirectory
from pathlib import Path
import json

from writerforge.reverse_random_chapters import SOURCE_SHA,chosen_chapters,selection_hash
from writerforge.reverse_later_window import later_chapter_diagnostic
from writerforge.r2_storage import R2Config,_digest
from writerforge.single_work_runner import SingleWorkVault
from writerforge.modern_source import _encoding

WORK="wudongqiankun"
SOURCE_BYTES=8_254_079

def probe():
    cfg=R2Config.from_environment()
    if cfg.bucket!="writerforge-private-library":
        raise RuntimeError("NOT_PRIVATE_R2")
    vault=SingleWorkVault(cfg,work_id=WORK)
    item=vault.verify_existing_single_work()
    if item is None or (item["utf8_sha256"],item["utf8_bytes"])!=(SOURCE_SHA,SOURCE_BYTES):
        raise RuntimeError("WRONG_SOURCE_VERSION")
    output=[]
    with TemporaryDirectory(prefix="wf-random3-readonly-") as folder:
        path=Path(folder)/"private.txt"
        vault.client.download_file(cfg.bucket,vault._blob_key(WORK,SOURCE_SHA),str(path))
        if _digest(path)!=(SOURCE_SHA,SOURCE_BYTES):
            raise RuntimeError("R2_FRESH_SOURCE_MISMATCH")
        enc=_encoding(path)
        for chapter in chosen_chapters():
            plan,parts=later_chapter_diagnostic(
                path,enc,expected_source_sha256=SOURCE_SHA,chapter=chapter,
                sampled_diagnostic=True)
            if (plan["chapter"]!=chapter or
                plan["windows"][0]["sha256"]==plan["windows"][1]["sha256"] or
                plan["windows"][0]["end"]!=plan["windows"][1]["start"] or
                plan["windows"][0]["chars"]>5500 or
                not plan["full_body_reconstructed"] or
                not plan["chapter_earlier_headings_verified"] or
                not plan["diagnostic_only_no_mastery_progress"]):
                raise RuntimeError("SAMPLED_CHAPTER_WINDOW_NOT_PINNED")
            output.append({
                "chapter":chapter,"source_window_sha256":plan["windows"][0]["sha256"],
                "following_window_sha256":plan["windows"][1]["sha256"],
                "chapter_sha256":plan["chapter_body_sha256"],
                "source_first_chars":len(parts[0]),"following_chars":len(parts[1]),
                "full_chapter_chars":plan["chapter_body_chars"],
                "structural_only":True,
            })
    result={"stage":"WF_V28_RANDOM3_PRESELECTED_R2_READY","sample_sha256":selection_hash(),
            "source_sha256":SOURCE_SHA,"chapters":output,
            "count":len(output),"model_calls":0,"draft_saved":False,
            "first_window":"NOT_PASSED","second_window":"LOCKED"}
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return result
if __name__=="__main__":
    probe()
