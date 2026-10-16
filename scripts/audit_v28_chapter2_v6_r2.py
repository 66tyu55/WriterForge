"""Read NEW chapter-2 v6 evidence, compare with pinned prior v5 numeric result.

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
from writerforge.reverse_score_scale import baseline_30_display
from scripts.run_wudong_chapter2_diagnostic_v6 import TRANSFER_TASK

SOURCE_SHA="86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28"
SOURCE_BYTES=8_254_079
TRIAL="cross-vendor-flash-glm53-chapter2-diagnostic-v6"
PREFIX="writerforge/v1/reverse-craft/wudongqiankun/"+TRIAL

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
    config={"source":SOURCE_SHA,"task":"chapter-2-contiguous-window-1-diagnostic-only",
            "roles":ROLE_MODELS,"trial":TRIAL,
            "creative_task_sha256":sha256(TRANSFER_TASK.encode("utf-8")).hexdigest()}
    fingerprint=sha256(_canonical(config)).hexdigest()
    root=PREFIX+"/"+fingerprint
    pointer=json.loads(store._get_small(root+"/completed.json",4096))
    h=pointer.get("sha256")
    if not isinstance(h,str) or len(h)!=64 or any(ch not in "0123456789abcdef" for ch in h):
        raise RuntimeError("R2_POINTER_INVALID")
    raw=store._get_small(root+"/snapshots/"+h+".json",32000)
    if sha256(raw).hexdigest()!=h:raise RuntimeError("REPORT_HASH_MISMATCH")
    result=json.loads(raw)
    if result.get("new_original_task_sha256")!=sha256(TRANSFER_TASK.encode("utf-8")).hexdigest():
        raise RuntimeError("TRANSFER_TASK_FINGERPRINT_INVALID")
    cursor=result.get("source_cursor_diagnostic")
    if (not isinstance(cursor,dict) or cursor.get("chapter")!=2 or
        cursor.get("ordinal")!=1 or cursor.get("semantic_boundary_verified") is not False or
        cursor.get("diagnostic_only_no_promotion") is not True or
        cursor.get("earlier_first_window")!="NOT_PASSED" or
        cursor.get("second_curriculum_window")!="LOCKED" or
        result.get("source_unit_sha256")!=cursor.get("source_window_sha256") or
        result.get("next_unit_sha256")!=cursor.get("next_contiguous_sha256")):
        raise RuntimeError("LATER_SOURCE_PROVENANCE_OR_LOCK_INVALID")
    if result.get("critic_prompt_original_source_prose") is not False:
        raise RuntimeError("CRITIC_NOT_SOURCE_BLIND")
    calculated=baseline_30_display(result["comparisons"])
    if result.get("baseline_30_display")!=calculated:
        raise RuntimeError("BASELINE_30_SCALE_TAMPERED")
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
            "stage":"FLASH_GLM53_V6_CHAPTER2_NUMERIC_AND_SAFE_COMMENT_AUDIT",
            "status":"VERIFIED_R2_RECEIPT",
            "receipt_sha256":h,
            "baseline_30_display":calculated,
            "source_cursor_diagnostic":cursor,
            "historical_v5": {
                "baseline_raw_mean":82.8,
                "enhanced_raw_mean":90.0,
                "enhanced_minus_baseline":7.2,
                "source_chapter":1
            },
            "v6_vs_v5_enhanced_mean_change":round(
                calculated["unadjusted_model_mean"]["skill"]-90.0,2),
            "v6_vs_v5_delta_change":round(
                calculated["unadjusted_signed_delta"]-7.2,2),
            "sharp_decline_10_point_threshold_model_only":(
                calculated["unadjusted_model_mean"]["skill"]<=80.0),
            "causal_decline_proven":False,
            "models":result.get("roles"),
            "unverified_model_scores":comparison,
            "skill_minus_baseline_raw_integer_mean":comparison["skill"]["avg_model_score"]-comparison["baseline"]["avg_model_score"],
            "relative_draft_length_difference":round(
                abs(comparison["baseline"]["draft_characters"]-comparison["skill"]["draft_characters"])
                /max(comparison["baseline"]["draft_characters"],comparison["skill"]["draft_characters"]),4),
            "source_mechanisms":[x.get("technique_id") for x in result.get("planner_mechanisms_unreviewed",[])],
            "critic_uncertainty":protected(result.get("uncertainty"),text),
            "critic_suggested_method":protected(result.get("learned_mechanism"),text),
            "reported_usage":result.get("usage"),
            "human_literary_review":False,"mastery_90_verified":False,
            "first_window_passed":False,"second_window_unlocked":False,
            "original_or_draft_body_exposed":False,"model_calls":0,
        }
        print(json.dumps(output,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
