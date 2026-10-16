"""Source-safe READ ONLY audit of one real private V28 Discovery A/B report.

Print original-model SHORT ABSTRACT hypotheses and review notes only if they
have no 16-codepoint verbatim span in the pinned original. No novel or drafts
are emitted. Public Actions logs contain only vetted review annotations.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import re

from writerforge.r2_storage import R2Config, R2StudyVault, _canonical, _digest
from writerforge.single_work_runner import SingleWorkVault
from writerforge.reverse_discovery_models import ROLE_MODELS

SOURCE_SHA="86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28"
SOURCE_BYTES=8_254_079
PREFIX="writerforge/v1/reverse-craft/wudongqiankun/real-discovery-ab-v1"
DIMENSIONS=("perception","causality","information","continuity","language")
HYPOTHESIS=("trigger","perception","decision","consequence","reader_question","author_mechanism")
RECEIPT_SHA="86953525286e33e5a09f0acb4d4774e7ccfa3abafe0b5d00fe65c5f5e0c66b04"

def safe_short(note, source):
    if not isinstance(note,str) or not note.strip() or len(note)>180:
        return "[missing-or-unbounded]"
    if note.startswith("UNVERIFIED_QUOTATION_REDACTED"):
        return "[redacted-by-training]"
    cleaned=" ".join(note.split())
    # Guard against reprinting recognizably long novel passages in public logs.
    if any(cleaned[i:i+16] in source for i in range(max(0,len(cleaned)-15))):
        return "[note-overlaps-original-16-chars]"
    return cleaned

def run():
    cfg=R2Config.from_environment()
    if cfg.bucket!="writerforge-private-library":
        raise RuntimeError("WRONG_PRIVATE_BUCKET")
    vault=R2StudyVault(cfg)
    fprint=sha256(_canonical({
        "source":SOURCE_SHA,"task":"opening-chapter-1-contiguous-window-1",
        "roles":ROLE_MODELS,"trial":"real-discovery-ab-v1",
    })).hexdigest()
    root=f"{PREFIX}/{fprint}"
    marker=json.loads(vault._get_small(root+"/completed.json",4096))
    if marker.get("sha256")!=RECEIPT_SHA:
        raise RuntimeError("SOURCE_AB_SNAPSHOT_MISMATCH")
    payload=vault._get_small(root+f"/snapshots/{RECEIPT_SHA}.json",32000)
    if sha256(payload).hexdigest()!=RECEIPT_SHA:
        raise RuntimeError("IMMUTABLE_REVIEW_SHA_FAILED")
    data=json.loads(payload)
    if data.get("edition_sha256")!=SOURCE_SHA:
        raise RuntimeError("WRONG_ORIGINAL_EDITION")
    original=SingleWorkVault(cfg,work_id="wudongqiankun")
    with TemporaryDirectory(prefix="wf-ab-review-") as folder:
        source_path=Path(folder)/"origin.private"
        original.client.download_file(cfg.bucket,original._blob_key("wudongqiankun",SOURCE_SHA),str(source_path))
        if _digest(source_path)!=(SOURCE_SHA,SOURCE_BYTES):
            raise RuntimeError("REVIEW_ORIGINAL_FRESH_HASH_FAILED")
        raw=source_path.read_bytes()
        text=raw.decode("utf-8-sig") if raw.startswith(b"\xef\xbb\xbf") else None
        if text is None:
            try: text=raw.decode("utf-8")
            except UnicodeDecodeError: text=raw.decode("gb18030")
        hypothesis=data.get("hypothesis") or {}
        summary={
            "stage":"FIRST_REAL_V28_AB_CAUSAL_FEEDBACK_AUDITED",
            "source_sha256":SOURCE_SHA,"receipt_sha256":RECEIPT_SHA,
            "roles":data.get("roles"),
            "draft_text_available_for_reinspection":False,
            "notes_quote_checked_against_pinned_full_original":True,
            "initial_mechanism_hypotheses":{
                k:safe_short(hypothesis.get(k),text) for k in HYPOTHESIS
            },
            "actual_short_review_reasons":{
                kind:{
                    k:{
                        "score":data["comparisons"][kind]["dimension_review"][k]["score"],
                        "review":safe_short(data["comparisons"][kind]["dimension_review"][k]["reason"],text),
                    } for k in DIMENSIONS
                } for kind in ("baseline","skill")
            },
            "critic_caveat":safe_short(data.get("uncertainty"),text),
            "critic_inferred_reusable_method":safe_short(data.get("learned_mechanism"),text),
            "baseline_chars":data["comparisons"]["baseline"]["draft_chars"],
            "skill_chars":data["comparisons"]["skill"]["draft_chars"],
            "prototype_did_not_save_failures_to_mastery_core":True,
            "no_external_model_calls":True,
            "no_original_or_draft_prose_disclosed":True,
        }
        print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=="__main__":
    run()
