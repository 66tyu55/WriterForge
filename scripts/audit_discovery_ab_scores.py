"""Read only numerical comparison scores from private immutable Discovery A/B receipt.

Does not fetch or print original prose, draft prose, notes, secrets or model
raw output. Never performs model inference.
"""
from __future__ import annotations
from hashlib import sha256
import json
from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.reverse_discovery_models import ROLE_MODELS

SOURCE_SHA="86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28"
PREFIX="writerforge/v1/reverse-craft/wudongqiankun/real-discovery-ab-v1"
DIMS=("perception","causality","information","continuity","language")

def main():
    cfg=R2Config.from_environment()
    if cfg.bucket!="writerforge-private-library":
        raise RuntimeError("WRONG_PRIVATE_BUCKET")
    vault=R2StudyVault(cfg)
    fp=sha256(_canonical({
        "source":SOURCE_SHA,"task":"opening-chapter-1-contiguous-window-1",
        "roles":ROLE_MODELS,"trial":"real-discovery-ab-v1",
    })).hexdigest()
    root=f"{PREFIX}/{fp}"
    pointer=json.loads(vault._get_small(root+"/completed.json",4096))
    h=pointer["sha256"]
    data=vault._get_small(f"{root}/snapshots/{h}.json",32000)
    if sha256(data).hexdigest()!=h:
        raise RuntimeError("SOURCE_AB_IMMUTABLE_RECEIPT_CORRUPT")
    receipt=json.loads(data)
    if (receipt.get("edition_sha256")!=SOURCE_SHA
        or receipt.get("stage")!="true_model_calls_and_private_source_AB_comparison_unverified"):
        raise RuntimeError("AB_RECEIPT_PROVENANCE_INVALID")
    scores={}
    for kind in ("baseline","skill"):
        outcome=receipt["comparisons"][kind]
        dimension=outcome["dimension_review"]
        if set(dimension)!=set(DIMS):
            raise RuntimeError("AB_DIMENSION_SET_INCOMPLETE")
        scores[kind]={
            "mean_model_critic_score_unverified":outcome["model_critic_score_unverified"],
            "dimension_scores":{k:dimension[k]["score"] for k in DIMS},
            "draft_sha256":outcome["draft_sha256"],
        }
    delta=scores["skill"]["mean_model_critic_score_unverified"]-scores["baseline"]["mean_model_critic_score_unverified"]
    print(json.dumps({
        "stage":"AUDITED_REAL_DISCOVERY_AB_NUMERIC_ONLY",
        "source":"wudongqiankun", "source_chapter":1,"unit":1,
        "receipt_sha256":h,"scores":scores,
        "skill_minus_baseline":delta,
        "one_sample_cannot_establish_literary_improvement":True,
        "independent_human_calibration_performed":False,
        "training_promotion_allowed":False,
        "original_or_draft_prose_exposed":False,
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
