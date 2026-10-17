"""Read-only status of successfully completed random3 receipts; never infer missing scores."""
from __future__ import annotations
from hashlib import sha256
import json,re

from writerforge.r2_storage import R2Config,R2StudyVault
from writerforge.reverse_random_chapters import chosen_chapters,SOURCE_SHA
from writerforge.reverse_score_scale import baseline_30_display
from scripts.audit_wudong_random3_v7_r2 import _root,PINS

def audit():
    cfg=R2Config.from_environment()
    if cfg.bucket!="writerforge-private-library":
        raise RuntimeError("PRIVATE_R2_REQUIRED")
    vault=R2StudyVault(cfg)
    visible=[]
    for slot,chapter in enumerate(chosen_chapters()):
        root=_root(slot,chapter)
        if vault._head(root+"/completed.json") is None:
            visible.append({"chapter":chapter,"status":"NO_VERIFIED_COMPLETE_RECEIPT_YET","raw_score":None})
            continue
        pointer=json.loads(vault._get_small(root+"/completed.json",4096))
        h=pointer.get("sha256")
        if (not isinstance(h,str) or not re.fullmatch(r"[a-f0-9]{64}",h)
            or pointer.get("source_sha256")!=SOURCE_SHA):
            raise RuntimeError("SCORE_POINTER_INVALID")
        raw=vault._get_small(root+f"/snapshots/{h}.json",32000)
        if sha256(raw).hexdigest()!=h:
            raise RuntimeError("SNAPSHOT_SHA_MISMATCH")
        doc=json.loads(raw)
        if (doc.get("source_unit_sha256")!=PINS[chapter][1] or
            doc.get("critic_prompt_original_source_prose") is not False or
            doc.get("edition_sha256")!=SOURCE_SHA):
            raise RuntimeError("SOURCE_OR_CRITIC_ISOLATION_FAILED")
        scale=baseline_30_display(doc["comparisons"])
        visible.append({
            "chapter":chapter,"status":"GENUINE_A_B_VERIFIED",
            "receipt_sha256":h,
            "unadjusted":scale["unadjusted_model_mean"],
            "wf_minus_baseline":scale["unadjusted_signed_delta"],
            "display_baseline_30":30.0,
            "display_wf":scale["skill_display_score_unclipped"],
            "mechanism_ids":[x["technique_id"] for x in doc["planner_mechanisms_unreviewed"]],
            "draft_chars":doc["length_gate"],
            "literary_mastery":False,
        })
    out={"stage":"V28_RANDOM3_STATUS_READ_ONLY","chapters":visible,
         "number_scored":sum(x["status"]=="GENUINE_A_B_VERIFIED" for x in visible),
         "all_three_scored":all(x["status"]=="GENUINE_A_B_VERIFIED" for x in visible),
         "model_calls":0,"second_window":"LOCKED"}
    print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    return out

if __name__=="__main__":
    audit()
