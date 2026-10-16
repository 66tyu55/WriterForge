"""Read existing genuine Flash/GLM-5.3 V28 A/B evidence without model calls.

Logs: score dimensions and bounded notes only after checking full pinned source
for 16-character overlap. Never output original source or generated draft.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
from writerforge.r2_storage import R2Config,R2StudyVault,_canonical,_digest
from writerforge.single_work_runner import SingleWorkVault
from writerforge.reverse_discovery_models import ROLE_MODELS

SOURCE_SHA="86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28"
SOURCE_BYTES=8_254_079
TRIAL="cross-vendor-flash-glm53-50k-ab-v4"
PREFIX="writerforge/v1/reverse-craft/wudongqiankun/"+TRIAL
SHA="a2882f770e76fee4f4cedffb219d919a1a169fd731832b3d2de24e105c6a0282"
DIMS=("perception","causality","information","continuity","language")

def protected(note,source):
    if not isinstance(note,str) or not note.strip() or len(note)>180:
        return "[missing-or-unbounded]"
    if note.startswith("UNVERIFIED_QUOTATION_REDACTED"):
        return "[redacted-by-training]"
    tidy=" ".join(note.split())
    if any(tidy[k:k+16] in source for k in range(max(0,len(tidy)-15))):
        return "[source-overlap-redacted]"
    return tidy

def main():
    cfg=R2Config.from_environment()
    if cfg.bucket!="writerforge-private-library":
        raise RuntimeError("WRONG_PRIVATE_R2")
    store=R2StudyVault(cfg)
    config={"source":SOURCE_SHA,"task":"opening-chapter-1-contiguous-window-1",
            "roles":ROLE_MODELS,"trial":TRIAL}
    fingerprint=sha256(_canonical(config)).hexdigest()
    root=PREFIX+"/"+fingerprint
    pointer=json.loads(store._get_small(root+"/completed.json",4096))
    if pointer.get("sha256")!=SHA:raise RuntimeError("R2_POINTER_CHANGED")
    raw=store._get_small(root+"/snapshots/"+SHA+".json",32000)
    if sha256(raw).hexdigest()!=SHA:raise RuntimeError("REPORT_HASH_MISMATCH")
    result=json.loads(raw)
    if result.get("edition_sha256")!=SOURCE_SHA:
        raise RuntimeError("WRONG_SOURCE_EDITION")
    vault=SingleWorkVault(cfg,work_id="wudongqiankun")
    with TemporaryDirectory(prefix="wf-reason-audit-") as t:
        source_path=Path(t)/"private.txt"
        vault.client.download_file(cfg.bucket,vault._blob_key("wudongqiankun",SOURCE_SHA),str(source_path))
        if _digest(source_path)!=(SOURCE_SHA,SOURCE_BYTES):
            raise RuntimeError("SOURCE_HASH_MISMATCH")
        novel=source_path.read_bytes()
        try: text=novel.decode("utf-8-sig")
        except UnicodeDecodeError:text=novel.decode("gb18030")
        comparison={}
        for name in ("baseline","skill"):
            item=result["comparisons"][name]
            dims=item["dimension_review"]
            if set(dims)!=set(DIMS):raise RuntimeError("DIMENSIONS_INCOMPLETE")
            comparison[name]={
                "avg_model_score":item["model_critic_score_unverified"],
                "draft_characters":item["draft_chars"],
                "dimension_evidence":{key:{
                    "score":dims[key]["score"],
                    "comment":protected(dims[key]["reason"],text)}
                    for key in DIMS},
            }
        output={
            "stage":"FLASH_GLM53_V4_NUMERIC_AND_SAFE_COMMENT_AUDIT",
            "status":"VERIFIED_R2_RECEIPT",
            "receipt_sha256":SHA,
            "models":result.get("roles"),
            "unverified_model_scores":comparison,
            "skill_minus_baseline":comparison["skill"]["avg_model_score"]-comparison["baseline"]["avg_model_score"],
            "relative_draft_length_difference":round(
                abs(comparison["baseline"]["draft_characters"]-comparison["skill"]["draft_characters"])
                /max(comparison["baseline"]["draft_characters"],comparison["skill"]["draft_characters"]),4),
            "source_mechanisms":[x.get("technique_id") for x in result.get("planner_mechanisms_unreviewed",[])],
            "critic_uncertainty":protected(result.get("uncertainty"),text),
            "critic_suggested_method":protected(result.get("learned_mechanism"),text),
            "reported_usage":result.get("usage"),
            "human_literary_review":False,"mastery_90_verified":False,
            "original_or_draft_body_exposed":False,"model_calls":0,
        }
        print(json.dumps(output,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
