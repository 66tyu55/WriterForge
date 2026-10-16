"""No-model private R2 cross-chapter evidence consolidation after v6 succeeds.

All credentials are private R2-only. No original novel, draft, model call, or
human-review implication. Old receipts remain immutable and untouched.
"""
from __future__ import annotations
from hashlib import sha256
import json,re

from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.reverse_cross_window_review import compare_existing_chapters
from scripts.run_wudong_chapter2_diagnostic_v6 import TRANSFER_TASK

SOURCE_SHA="86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28"
V5_SHA="b41e4a74895898f545af4f5424ac554cbe02215ba3f122715e8d09d38072aa66"
MODEL_ROLES={"planner":"deepseek-v4-flash-0731","writer":"glm-5.3","critic":"deepseek-v4-flash-0731"}
V5_TRIAL="cross-vendor-flash-glm53-transfer-baseline30-v5"
V6_TRIAL="cross-vendor-flash-glm53-chapter2-diagnostic-v6"
BASE="writerforge/v1/reverse-craft/wudongqiankun"

def trial_root(trial,task):
    cfg={"source":SOURCE_SHA,"task":task,"roles":MODEL_ROLES,"trial":trial,
         "creative_task_sha256":sha256(TRANSFER_TASK.encode("utf-8")).hexdigest()}
    return f"{BASE}/{trial}/{sha256(_canonical(cfg)).hexdigest()}"


def audit_and_store(r2):
    if r2.config.bucket!="writerforge-private-library":
        raise RuntimeError("PRIVATE_R2_REQUIRED")
    root5=trial_root(V5_TRIAL,"opening-chapter-1-contiguous-window-1")
    root6=trial_root(V6_TRIAL,"chapter-2-contiguous-window-1-diagnostic-only")
    prior_raw=r2._get_small(f"{root5}/snapshots/{V5_SHA}.json",32000)
    if sha256(prior_raw).hexdigest()!=V5_SHA:
        raise RuntimeError("V5_HASH_CHANGED")
    pointer=json.loads(r2._get_small(f"{root6}/completed.json",4096))
    h=pointer.get("sha256")
    if (not isinstance(h,str) or not re.fullmatch(r"[0-9a-f]{64}",h)
        or pointer.get("source_sha256")!=SOURCE_SHA):
        raise RuntimeError("V6_POINTER_INVALID")
    after_raw=r2._get_small(f"{root6}/snapshots/{h}.json",32000)
    if sha256(after_raw).hexdigest()!=h:
        raise RuntimeError("V6_RECEIPT_HASH_FAILED")
    v5,v6=json.loads(prior_raw),json.loads(after_raw)
    if v6.get("edition_sha256")!=SOURCE_SHA:
        raise RuntimeError("EDITION_CHANGED")
    report=compare_existing_chapters(v5,v6,v5_sha=V5_SHA,v6_sha=h)
    payload=_canonical(report)
    digest=sha256(payload).hexdigest()
    key=f"{root6}/cross-window-candidates/{digest}.json"
    r2._put_small_immutable(key,payload,digest)
    fresh=r2._get_small(key,8192)
    if fresh!=payload or sha256(fresh).hexdigest()!=digest:
        raise RuntimeError("CROSS_WINDOW_R2_FRESH_GET_FAILED")
    safe={
        "stage":"V28_CHAPTER2_CROSS_WINDOW_R2_EVIDENCE_VERIFIED",
        "v5_receipt":V5_SHA,"v6_receipt":h,
        "candidate_sha256":digest,
        "v6_baseline_raw_mean":report["after"]["baseline_mean"],
        "v6_enhanced_raw_mean":report["after"]["skill_mean"],
        "v6_raw_ab_delta":report["after"]["ab_delta"],
        "old_raw_ab_delta":report["before"]["ab_delta"],
        "enhanced_mean_change":report["enhanced_mean_change"],
        "ab_effect_change":report["ab_effect_change"],
        "sharp_drop_threshold_observed":report["sharp_model_rated_skill_drop_10_or_more"],
        "negative_new_ab_effect":report["negative_model_rated_new_ab_effect"],
        "mechanisms_same":report["same_mechanisms"],
        "model_calls":0,"original_downloaded":False,
        "first_window":"NOT_PASSED","second_window":"LOCKED",
        "core_promoted":False,
    }
    print(json.dumps(safe,ensure_ascii=False,sort_keys=True))
    return safe

if __name__=="__main__":
    audit_and_store(R2StudyVault(R2Config.from_environment()))
