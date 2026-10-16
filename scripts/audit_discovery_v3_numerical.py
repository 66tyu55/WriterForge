"""Read-only numeric audit of the newly fixed-model V28 private R2 result."""
from __future__ import annotations
from hashlib import sha256
import json
from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.reverse_discovery_models import ROLE_MODELS
from scripts.run_wudong_discovery_ab import SOURCE_SHA,PREFIX
EXPECTED_SHA="b1354316a9ca487e7e07f127be78b0ca3856855f1168d73d313ae6a99568822a"
FIELDS=("perception","causality","information","continuity","language")

def run():
    cfg=R2Config.from_environment()
    if cfg.bucket!="writerforge-private-library":
        raise RuntimeError("wrong private R2")
    r2=R2StudyVault(cfg)
    digest=sha256(_canonical({
        "source":SOURCE_SHA,"task":"opening-chapter-1-contiguous-window-1",
        "roles":ROLE_MODELS,"trial":"fixed-1m-context-50k-ab-v3",
    })).hexdigest()
    root=f"{PREFIX}/{digest}"
    pointer=json.loads(r2._get_small(root+"/completed.json",4096))
    h=pointer.get("sha256")
    if h!=EXPECTED_SHA:raise RuntimeError("unexpected v3 immutable result SHA")
    raw=r2._get_small(root+"/snapshots/"+h+".json",32000)
    if sha256(raw).hexdigest()!=h:raise RuntimeError("R2 receipt SHA invalid")
    d=json.loads(raw)
    scores={}
    for name in ("baseline","skill"):
        item=d["comparisons"][name]
        dims=item["dimension_review"]
        if set(dims)!=set(FIELDS):raise RuntimeError("missing dimension")
        scores[name]={
            "mean":item["model_critic_score_unverified"],
            "chars":item["draft_chars"],
            "dimensions":{k:dims[k]["score"] for k in FIELDS}
        }
    print(json.dumps({
        "stage":"VERIFIED_REAL_FIXED_1M_PAIR_AB_NUMERICAL_ONLY",
        "receipt_sha256":h,"scores":scores,
        "skill_minus_baseline":scores["skill"]["mean"]-scores["baseline"]["mean"],
        "length_gate":d.get("length_gate"),
        "learning_methods_chosen":[
            x.get("technique_id") for x in d.get("planner_mechanisms_unreviewed",[])
        ],
        "usage":d.get("usage"),
        "critic_human_calibrated":False,
        "source_or_generated_prose_emitted":False,
        "second_window_unlocked":False,
    },ensure_ascii=False,indent=2))
if __name__=="__main__":
    run()
