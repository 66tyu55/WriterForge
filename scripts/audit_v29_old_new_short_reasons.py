"""No-model audit of bounded short blind-review notes for V29 fresh holdouts.

The A/B reviewer already redacted >=18-char verbatim overlaps with source or
manuscript. Never print raw originals, full manuscripts, source excerpt text,
free-form planner analysis or private credentials.
"""
from __future__ import annotations
import json
from hashlib import sha256
from writerforge.r2_storage import R2Config,R2StudyVault
from writerforge.v29_fresh_holdout import chosen_ids
from writerforge.reverse_cloud_ab import DIMENSIONS
from scripts.run_v29_old_new_holdout import root_for_slot

def audit_notes(store):
    if store.config.bucket!="writerforge-private-library":
        raise ValueError("PRIVATE_R2_REQUIRED")
    checked=[]
    for slot,name in enumerate(chosen_ids()):
        root=root_for_slot(slot)
        key=root+"/completed.json"
        if store._head(key) is None:
            checked.append({"slot":slot,"scenario":name,"status":"UNSCORED"})
            continue
        pointer=json.loads(store._get_small(key,4096))
        digest=pointer["sha256"]
        raw=store._get_small(root+"/snapshots/"+digest+".json",32000)
        if sha256(raw).hexdigest()!=digest:
            raise ValueError("PRIVATE_HOLDOUT_SOURCE_SHA_FAILED")
        doc=json.loads(raw)
        arms=doc["comparisons"]
        notes={}
        for arm in ("legacy","semantic"):
            scores=arms[arm]["dimensions"]
            notes[arm]={
                dim:{"score":scores[dim]["score"],"reason":scores[dim]["reason"]}
                for dim in DIMENSIONS
            }
        checked.append({
            "slot":slot,"scenario":name,"status":"UNVERIFIED_MODEL_CRITIC_SHORT_REASONS",
            "receipt_sha256":digest,
            "semantic_minus_legacy":doc["semantic_minus_legacy_model_mean"],
            "old_mechanisms":arms["legacy"]["mechanism_ids"],
            "new_mechanisms":arms["semantic"]["mechanism_ids"],
            "mechanism_choice_changed":not doc["same_host_mechanisms_selected"],
            "anonymous_scores_and_reasons":notes,
            "reviewer_uncertainty":doc["reviewer_uncertainty"],
            "human_evidence":False,
        })
    result={
        "stage":"V29_BLINDED_MODEL_REASONS_ZERO_CALLS",
        "results":checked,
        "model_calls":0,
        "original_novel_or_manuscripts_in_output":False,
        "independent_literary_validation":False,
        "new_skill_promoted":False,
    }
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return result

if __name__=="__main__":
    audit_notes(R2StudyVault(R2Config.from_environment()))
