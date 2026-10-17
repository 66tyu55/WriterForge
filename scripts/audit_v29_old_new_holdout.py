"""Zero-model SHA-verified readback of actual V29 old-vs-semantic trials.

Three pre-committed unseen writing prompts, same source and same models.
Missing, failed, or abstained trials are NEVER given a numeric score.
This diagnostic explicitly refuses to certify literary improvement without
a separate independent reviewer and wider replication.
"""
from __future__ import annotations
from hashlib import sha256
import json,re
from writerforge.v29_fresh_holdout import chosen_ids,manifest,manifest_sha,task
from writerforge.reverse_cloud_ab import DIMENSIONS
from writerforge.reverse_discovery_models import ROLE_MODELS
from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from scripts.run_v29_old_new_holdout import (
    SOURCE_SHA,SOURCE_UNIT_SHA,FOLLOWING_UNIT_SHA,TRIAL,PREFIX,root_for_slot,
)

def audit(store,*,persist=True):
    if store.config.bucket!="writerforge-private-library":
        raise ValueError("PRIVATE_R2_ONLY")
    rows=[]
    for slot,scenario in enumerate(chosen_ids()):
        root=root_for_slot(slot)
        key=root+"/completed.json"
        if store._head(key) is None:
            rows.append({"slot":slot,"scenario":scenario,
                         "status":"NO_GENUINE_SCORABLE_REPORT",
                         "old_score":None,"new_score":None,"delta":None})
            continue
        pointer=json.loads(store._get_small(key,4096))
        h=pointer.get("sha256")
        if (not isinstance(h,str) or re.fullmatch(r"[a-f0-9]{64}",h) is None
            or pointer.get("source_sha256")!=SOURCE_SHA
            or pointer.get("trial")!=TRIAL):
            raise ValueError("INVALID_SHA_POINTER_OR_TRIAL")
        raw=store._get_small(root+"/snapshots/"+h+".json",32000)
        if sha256(raw).hexdigest()!=h:
            raise ValueError("IMMUTABLE_RECEIPT_SHA_CHANGED")
        doc=json.loads(raw)
        if (doc.get("format")!="writerforge.old-vs-semantic-a-b.v29"
            or doc.get("source_sha256")!=SOURCE_SHA
            or doc.get("source_unit_sha256")!=SOURCE_UNIT_SHA
            or doc.get("following_unit_sha256")!=FOLLOWING_UNIT_SHA
            or doc.get("writing_task_sha256")!=sha256(task(slot).encode()).hexdigest()
            or doc.get("heldout_manifest_sha256")!=manifest_sha()
            or doc.get("heldout_manifest")!=manifest()
            or doc.get("scenario")!=scenario or doc.get("slot")!=slot
            or doc.get("source_sent_to_writer_or_critic") is not False
            or doc.get("raw_manuscripts_saved") is not False
            or doc.get("human_independent_review") is not False
            or doc.get("core_promoted") is not False
            or doc.get("second_window")!="LOCKED"):
            raise ValueError("SOURCE_BLIND_SAME_TASK_OR_UNLOCK_PROVENANCE_FAILED")
        roles=doc.get("model_roles")
        if roles!=ROLE_MODELS:
            raise ValueError("WRITER_OR_CRITIC_CHANGED")
        arms=doc.get("comparisons")
        if not isinstance(arms,dict) or set(arms)!={"legacy","semantic"}:
            raise ValueError("MISSING_COMPARABLE_OLD_NEW_DRAFTS")
        dims={}
        vals={}
        for arm in ("legacy","semantic"):
            sample=arms[arm]
            if (not isinstance(sample,dict)
                or not isinstance(sample.get("draft_sha256"),str)
                or not re.fullmatch(r"[a-f0-9]{64}",sample["draft_sha256"])
                or not isinstance(sample.get("draft_chars"),int)
                or not 220<=sample["draft_chars"]<=4500
                or set(sample.get("dimensions",{}))!=set(DIMENSIONS)):
                raise ValueError("INVALID_OLD_OR_NEW_TEXT_METADATA")
            nums={d:sample["dimensions"][d]["score"] for d in DIMENSIONS}
            if any(type(v) is not int or not 0<=v<=100 for v in nums.values()):
                raise ValueError("INVALID_UNCALIBRATED_MODEL_DIMENSIONS")
            mean=sum(nums.values())/5
            if abs(mean-sample.get("model_mean",-999))>1e-6:
                raise ValueError("MODEL_MEAN_DOES_NOT_MATCH_DIMENSIONS")
            vals[arm]=mean
            dims[arm]=nums
        if abs(vals["legacy"]-vals["semantic"])/1e9>1:
            raise ValueError("IMPOSSIBLE_MEAN")
        diff=round(vals["semantic"]-vals["legacy"],2)
        if abs(diff-doc.get("semantic_minus_legacy_model_mean",-999))>1e-6:
            raise ValueError("FALSE_MODEL_IMPROVEMENT_DELTA")
        c1=arms["legacy"]["draft_chars"]
        c2=arms["semantic"]["draft_chars"]
        if abs(c1-c2)/max(c1,c2)>.15:
            raise ValueError("COMPARISON_LENGTH_NOT_FAIR")
        usage=doc.get("model_usage",{})
        if (not isinstance(usage,dict)
            or type(usage.get("calls")) is not int or
            not 5<=usage["calls"]<=7 or
            type(usage.get("reserved_output_tokens")) is not int or
            usage["reserved_output_tokens"]>50000):
            raise ValueError("MODEL_BUDGET_NOT_VERIFIED")
        rows.append({
            "slot":slot,"scenario":scenario,"status":"BLIND_OLD_NEW_R2_VERIFIED",
            "receipt_sha256":h,
            "old_score":vals["legacy"],"new_score":vals["semantic"],"delta":diff,
            "per_dimension_new_minus_old":{
                d:dims["semantic"][d]-dims["legacy"][d] for d in DIMENSIONS},
            "all_five_negative":all(
                dims["semantic"][d]<dims["legacy"][d] for d in DIMENSIONS),
            "mechanisms_old":arms["legacy"]["mechanism_ids"],
            "mechanisms_new":arms["semantic"]["mechanism_ids"],
            "mechanisms_same":doc["same_host_mechanisms_selected"],
            "symmetric_revision_calls":doc["symmetric_revision_calls"],
            "draft_chars_old":c1,"draft_chars_new":c2,
            "model_calls":usage["calls"],
            "semantic_anchor_reviewed_by_human":False,
        })
    good=[r for r in rows if r["status"]=="BLIND_OLD_NEW_R2_VERIFIED"]
    pos=sum(r["delta"]>0 for r in good)
    neg=sum(r["delta"]<0 for r in good)
    result={
        "format":"writerforge.v29-heldout-old-new-model-observation.v1",
        "selected_scenarios":list(chosen_ids()),
        "manifest_sha256":manifest_sha(),
        "source_window_sha256":SOURCE_UNIT_SHA,
        "results":rows,"attempted_scenarios":3,
        "valid_graded_scenarios":len(good),
        "positive_count":pos,"negative_count":neg,
        "mean_new_minus_old_scored_only":(
            round(sum(r["delta"] for r in good)/len(good),3) if good else None),
        "predeclared_sign_rule":(
            ">=2_of_3_positive_and_no_dimension_regression_is_exploratory_signal_only"),
        "overall_status":(
            "MODEL_SUGGESTS_IMPROVEMENT_NOT_PROVEN"
            if len(good)==3 and pos>=2 and neg==0
            else "MODEL_SUGGESTS_REGRESSION_NOT_PROVEN"
            if len(good)==3 and neg>=2
            else "INSUFFICIENT_OR_MIXED_MODEL_EVIDENCE"),
        "human_independent_literary_review":False,
        "causal_improvement_proven":False,
        "model_weights_updated":False,
        "first_window":"NOT_PASSED","second_window":"LOCKED",
        "model_calls_in_audit":0,"core_promoted":False,
    }
    blob=_canonical(result)
    if len(blob)>17000:
        raise ValueError("R2_HOLDOUT_AGGREGATE_BOUNDEDNESS_FAIL")
    h=sha256(blob).hexdigest()
    if persist and len(good)==3:
        key=f"{PREFIX}/three-slot-holdout-audit/{h}.json"
        store._put_small_immutable(key,blob,h)
        if store._get_small(key,17000)!=blob:
            raise ValueError("HOLDOUT_AGGREGATE_R2_FRESH_GET_FAILED")
    print(json.dumps({"stage":"V29_OLD_NEW_FRESH_HOLDOUT_PRIVATE_R2_AUDIT",
                      "audit_sha256":h,**result},ensure_ascii=False,sort_keys=True))
    return result
if __name__=="__main__":
    audit(R2StudyVault(R2Config.from_environment()))
