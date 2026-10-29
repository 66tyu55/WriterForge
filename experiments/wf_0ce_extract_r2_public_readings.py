"""0.CE: READ ONLY obtain two already-stored and pinned public-domain R2 classics.

This is strictly public-domain source research, not a read of the author's
private modern titles. Source files remain runner-local. Only the bounded
source text windows become a private GitHub Actions artifact for human close
reading, with upstream edition SHA checks. Never R2 PUT/DELETE or model API.
"""
from __future__ import annotations

from hashlib import sha1, sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys

from writerforge.classics_catalog import CATALOG, verify_edition
from writerforge.r2_storage import R2Config, R2StudyVault, R2StorageError

CHOSEN={
    "laocanyouji":(("白妞","黑妞","王小玉"),("黃河","黄河","冰")),
    "sanguo":(("空城","司馬懿","司马懿"),("長坂","长坂","張飛","张飞")),
}
WINDOW_LEFT=1150
WINDOW_RIGHT=1500


def capture_source_windows(vault, *, output:Path):
    if vault.config.bucket!="writerforge-private-library":
        raise R2StorageError("WF0CE_UNEXPECTED_PRIVATE_BUCKET")
    entries=[]
    with TemporaryDirectory(prefix="wf0ce-verified-public-classics-") as temp:
        for key,topics in CHOSEN.items():
            book=CATALOG[key]
            verified=vault.restore(
                library=book.library,snapshot=None,destination=Path(temp))
            if not verified.get("verified") or not verified.get("source"):
                raise R2StorageError("WF0CE_R2_PUBLIC_CLASSIC_MISSING")
            raw=Path(verified["source"]).read_bytes()
            prose=verify_edition(book,raw)
            source_sha=sha256(raw).hexdigest()
            for group in topics:
                anchors=[(prose.find(term),term) for term in group]
                anchors=[(idx,term) for idx,term in anchors if idx>=0]
                if not anchors:
                    raise ValueError("WF0CE_LITERARY_MOTIF_NOT_FOUND_"+key)
                pos,anchor=min(anchors,key=lambda x:x[0])
                start=max(0,pos-WINDOW_LEFT)
                end=min(len(prose),pos+WINDOW_RIGHT)
                entries.append({
                    "work":book.key,
                    "published_title":book.title,
                    "source_edition":book.source_page,
                    "gutenberg_id":book.gutenberg_id,
                    "r2_public_catalog_library":book.library,
                    "source_sha256":source_sha,
                    "source_git_blob_sha1":book.git_blob_sha1,
                    "window_start_char":start,
                    "window_end_char":end,
                    "anchor":anchor,
                    "original_contiguous_window":prose[start:end],
                    "literary_quality_verified":False,
                })
    if len(entries)!=4:
        raise ValueError("WF0CE_FOUR_PUBLIC_WINDOWS_REQUIRED")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({
        "format":"wf.0ce.r2-pinned-public-domain-source-windows.v1",
        "r2_real_public_book_restores":2,
        "legacy_prose_reprinted_with_only_public_source_authority":True,
        "new_paid_model_calls":0,
        "r2_source_modifications":0,
        "original_modern_novel_accesses":0,
        "original_literary_gain_proven":False,
        "windows":entries,
    },ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    # Never echo original text or keys in public CI log.
    print(json.dumps({
        "status":"WF0CE_REAL_R2_TWO_PUBLIC_CLASSICS_SOURCE_VERIFIED",
        "source_restore_count":2,
        "source_windows":len(entries),
        "original_text_echoed_to_action_logs":False,
        "private_modern_novel_downloaded":False,
        "r2_writes":0,"model_calls":0,
    },ensure_ascii=False))


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("USAGE: python -m experiments.wf_0ce_extract_r2_public_readings /tmp/out.json")
    vault=R2StudyVault(R2Config.from_environment())
    capture_source_windows(vault,output=Path(sys.argv[1]))
