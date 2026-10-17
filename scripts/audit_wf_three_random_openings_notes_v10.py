"""Zero-model human-readable *model* critic notes for randomized first chapters.

Do not call any model. Only short, source-overlap-screened model comments
already saved in immutable private R2 receipts can be printed. No drafts or
original novel are persisted in GitHub/logs.
"""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
import json

from writerforge.r2_storage import R2Config,R2StudyVault,_digest
from writerforge.single_work_runner import SingleWorkVault
from writerforge.modern_source import _encoding
from writerforge.random_original_openings import selected_ids
from scripts.audit_wf_three_random_openings_v10 import _root,collect,DIMS
from scripts.audit_v28_flash_glm53_v4_r2 import protected
from scripts.run_wf_three_random_openings_v10 import SOURCE_SHA,SOURCE_BYTES

def run():
    cfg=R2Config.from_environment()
    if cfg.bucket!="writerforge-private-library":
        raise ValueError("WRONG_PRIVATE_R2")
    store=R2StudyVault(cfg)
    checked=collect(store,persist=False)
    vault=SingleWorkVault(cfg,work_id="wudongqiankun")
    record=vault.verify_existing_single_work()
    if record is None or (record["utf8_sha256"],record["utf8_bytes"])!=(SOURCE_SHA,SOURCE_BYTES):
        raise ValueError("SOURCE_NOT_PINNED")
    with TemporaryDirectory(prefix="wf-v10-critic-notes-") as d:
        path=Path(d)/"source.private.txt"
        vault.client.download_file(cfg.bucket,vault._blob_key("wudongqiankun",SOURCE_SHA),str(path))
        if _digest(path)!=(SOURCE_SHA,SOURCE_BYTES):
            raise ValueError("SOURCE_CORRUPTED_IN_R2")
        with path.open("r",encoding=_encoding(path)) as f:
            text=f.read()
        result=[]
        for row in checked["results"]:
            if row["status"]!="REAL_AB_R2_VERIFIED":
                result.append({"story_id":row["story_id"],"status":"UNSCORED_NO_COMMENTS"})
                continue
            slot=row["slot"]
            root=_root(slot)
            pointer=json.loads(store._get_small(root+"/completed.json",4096))
            sha=pointer["sha256"]
            body=store._get_small(root+f"/snapshots/{sha}.json",32000)
            if sha256(body).hexdigest()!=sha:
                raise ValueError("R2_NOTE_RECEIPT_SHA_MISMATCH")
            data=json.loads(body)
            summary={}
            for key in DIMS:
                base=data["comparisons"]["baseline"]["dimension_review"][key]
                skill=data["comparisons"]["skill"]["dimension_review"][key]
                summary[key]={
                    "baseline":base["score"],"wf":skill["score"],
                    "wf_minus_baseline":skill["score"]-base["score"],
                    "baseline_note":protected(base["reason"],text),
                    "wf_note":protected(skill["reason"],text),
                }
            result.append({
                "story_id":row["story_id"],"status":"MODEL_CRITIC_NOT_HUMAN",
                "receipt_sha256":sha,"five_dimensions":summary,
                "critic_uncertainty":protected(data.get("uncertainty"),text),
                "critic_hypothesis_unreviewed":protected(data.get("learned_mechanism"),text),
                "methods_unreviewed":row["mechanisms_unreviewed"],
                "human_review_performed":False,
            })
        output={
            "stage":"V28_RANDOM_FIRST_CHAPTERS_SAFE_CRITIC_NOTES_R2",
            "stories":result,"count_scored":checked["count_scored"],
            "source_or_full_drafts_in_output":False,"model_calls":0,
            "first_window":"NOT_PASSED","second_window":"LOCKED",
        }
        print(json.dumps(output,ensure_ascii=False,sort_keys=True))
        return output

if __name__=="__main__":
    run()
