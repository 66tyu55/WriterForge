"""V28 reproducible random-chapter diagnostics. 3 separate R2 namespaces; no curriculum advancement.

The existing user's GitHub secret is DISCOVERY__API__KEY; GitHub workflow
maps it to DISCOVERY_API_KEY for this short-lived runner. Only one selected chapter's first
verified source window is transmitted to explicitly configured Discovery.
No whole novel or generated prose enters public logs or persistent R2.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import re
import sys

from writerforge.modern_source import _encoding
from writerforge.reverse_real_training import raw_hash
from writerforge.reverse_later_window import later_chapter_diagnostic
from writerforge.reverse_random_chapters import chosen_chapters,selection_hash
from writerforge.reverse_cloud_ab import CloudABTrial
from writerforge.reverse_score_scale import baseline_30_display
from writerforge.reverse_discovery_models import (
    DiscoveryCallBudget, DiscoveryModel, ROLE_MODELS, DiscoveryError,
    FIXED_MODEL_CONTEXT_TOKENS, DISCOVERY_GATEWAY_1M_LOAD_VERIFIED,
)
from writerforge.r2_storage import R2Config, R2StudyVault, _canonical, _digest
from writerforge.single_work_runner import SingleWorkVault

WORK = "wudongqiankun"
SOURCE_SHA = "86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28"
SOURCE_BYTES = 8_254_079
PREFIX = "writerforge/v1/reverse-craft/wudongqiankun/cross-vendor-flash-glm53-random3-v7"
TRIAL = "cross-vendor-flash-glm53-random3-v7"
TRANSFER_TASK = (
    "独立原创奇幻故事：一座悬崖驿站靠索道向山外递送信件。"
    "夜班维护学徒在初雪时发现一件与平日经验矛盾的小事。"
    "山路封闭，明早又有人需要依靠索道出行。"
    "叙述时保持有限人物视角、自然的感官与动作、清楚的时间因果。"
    "人物的选择应有真实后果，但不要套用任何原著人物、情节或旧练习内容。"
    "只写原创开篇正文，700到1400汉字。"
)
MAX_RECEIPT_BYTES = 32000

def run(*, slot:int) -> dict:
    if type(slot) is not int or not 0<=slot<3:
        raise DiscoveryError('SAMPLED_SLOT_INVALID')
    chapter=chosen_chapters()[slot]
    sample_sha=selection_hash()
    token=os.environ.get("DISCOVERY_API_KEY","")
    if not isinstance(token,str) or len(token)<12:
        raise DiscoveryError("DISCOVERY_KEY_NOT_AVAILABLE")
    cfg=R2Config.from_environment()
    if cfg.bucket!="writerforge-private-library":
        raise DiscoveryError("NOT_THE_PRIVATE_R2_BUCKET")
    r2=R2StudyVault(cfg)
    vault=SingleWorkVault(cfg,work_id=WORK)
    orig=vault.verify_existing_single_work()
    if orig is None or (orig["utf8_sha256"],orig["utf8_bytes"])!=(SOURCE_SHA,SOURCE_BYTES):
        raise DiscoveryError("PINNED_ORIGINAL_MISMATCH")
    config={"source":SOURCE_SHA,"task":"chapter-random-diagnostic-only",
            "chapter":chapter,"slot":slot,"sample_sha256":sample_sha,
            "roles":ROLE_MODELS,"trial":TRIAL,
            "creative_task_sha256":sha256(TRANSFER_TASK.encode("utf-8")).hexdigest()}
    config_sha=sha256(_canonical(config)).hexdigest()
    root=f"{PREFIX}/chapter-{chapter}/{config_sha}"
    finished=root+"/completed.json"
    if r2._head(finished) is not None:
        receipt=json.loads(r2._get_small(finished,4096))
        h=receipt.get("sha256")
        if not isinstance(h,str) or not re.fullmatch(r"[0-9a-f]{64}",h):
            raise DiscoveryError("PREVIOUS_R2_RECEIPT_INVALID")
        content=r2._get_small(f"{root}/snapshots/{h}.json",MAX_RECEIPT_BYTES)
        if sha256(content).hexdigest()!=h:
            raise DiscoveryError("PRIOR_R2_RECEIPT_CORRUPT")
        return {"stage":"CACHED_VERIFIED_NO_REPEATED_INFERENCE",
                "sample_slot":slot,"source_chapter":chapter,
                "receipt_sha256":h, "calls_this_run":0,
                "second_window_unlocked":False,"master_quality_90_verified":False}
    with TemporaryDirectory(prefix="wf-random3-diagnostic-") as directory:
        path=Path(directory)/"original.private.txt"
        vault.client.download_file(cfg.bucket,vault._blob_key(WORK,SOURCE_SHA),str(path))
        if _digest(path)!=(SOURCE_SHA,SOURCE_BYTES):
            raise DiscoveryError("FRESH_R2_DOWNLOAD_SHA_FAILED")
        plan,(first,second)=later_chapter_diagnostic(
            path,_encoding(path),expected_source_sha256=SOURCE_SHA,
            chapter=chapter,sampled_diagnostic=True)
        if (plan["chapter"]!=chapter or
            plan["windows"][0]["start"]!=0 or
            plan["windows"][0]["end"]!=plan["windows"][1]["start"] or
            plan["windows"][1]["end"]!=plan["chapter_body_chars"] or
            not plan["full_body_reconstructed"] or
            not plan["diagnostic_only_no_mastery_progress"]):
            raise DiscoveryError("RANDOM3_SOURCE_CURSOR_FAILED")
        budget=DiscoveryCallBudget(max_calls=7,max_reserved_output_tokens=50000)
        roles={role:DiscoveryModel(name=name,role=role,api_key=token,budget=budget)
               for role,name in ROLE_MODELS.items()}
        try:
            outcome=CloudABTrial(planner=roles["planner"],
                                 writer=roles["writer"],
                                 critic=roles["critic"]).run(
                first,second,source_sha=SOURCE_SHA,window_hash=raw_hash(first),
                writing_task=TRANSFER_TASK)
        except Exception as exc:
            # Failed real exercises ARE study evidence, but must not become
            # craft rules. Persist a tiny whitelisted *failure receipt*.
            # Never keep novel, draft, prompt, credentials or provider response.
            known=(
                "AB_LENGTH_MISMATCH_NOT_COMPARABLE",
                "writer failed to produce bounded original scene",
                "planner returned unrecognized analysis or plot fields",
                "planner selection count must be 1..2",
                "planner entry has untrusted fields",
                "invalid or duplicate technique ID",
                "planner cited missing source paragraph",
                "DISCOVERY_PLANNER_JSON_CONTRACT_FAILED",
                "DISCOVERY_WRITER_JSON_CONTRACT_FAILED",
                "DISCOVERY_CRITIC_JSON_CONTRACT_FAILED",
                "MODEL_CALL_OR_TOKEN_BUDGET_EXHAUSTED",
            )
            message=str(exc)
            # Discovery adapter emits static, role-specific error codes only.
            # Never write arbitrary HTTP/provider exception text to logs/R2.
            if isinstance(exc,DiscoveryError) and (
                message.startswith("DISCOVERY_") and
                len(message)<=90 and
                all(c.isupper() or c.isdigit() or c=="_" for c in message)
            ):
                failure_code=message
            else:
                failure_code=message if message in known else type(exc).__name__
            attempt={
                "format":"writerforge.reverse-ab-failure.v2",
                "status":"UNVERIFIED_FAILED_NOT_PROMOTED",
                "source_sha256":SOURCE_SHA,
                "source_window_sha256":raw_hash(first),
                "experiment_config_sha256":config_sha,
                "code":failure_code,
                "calls":budget.calls,
                "calls_by_role":dict(budget.calls_by_role),
                "response_observations":list(budget.response_observations),
                "last_requested_role":budget.last_requested_role,
                "reported_prompt_tokens":budget.total_prompt_tokens,
                "reported_completion_tokens":budget.total_completion_tokens,
                "requested_completion_token_budget":budget.reserved_output_tokens,
                "second_window_unlocked":False,
                "draft_or_source_text_saved":False,
            }
            record=_canonical(attempt)
            record_hash=sha256(record).hexdigest()
            failure_key=f"{root}/failures/{record_hash}.json"
            r2._put_small_immutable(failure_key,record,record_hash)
            if r2._get_small(failure_key,4096)!=record:
                raise DiscoveryError("FAILED_ATTEMPT_R2_ROUNDTRIP_FAILED") from None
            print(json.dumps({"stage":"REAL_AB_FAILURE_PERSISTED_TO_R2",
                              "failure_code":failure_code,
                              "calls":budget.calls,
                              "calls_by_role":dict(budget.calls_by_role),
                              "last_requested_role":budget.last_requested_role,
                              "response_observations":list(budget.response_observations),
                              "failure_sha256":record_hash,
                              "no_draft_or_original_persisted":True,
                              "literary_skill_passed":False},
                             ensure_ascii=False),flush=True)
            raise
        outcome["source_cursor_diagnostic"]={
            "chapter":chapter,"ordinal":1,"sample_slot":slot,"sample_sha256":sample_sha,
            "chapter_body_sha256":plan["chapter_body_sha256"],
            "source_window_sha256":plan["windows"][0]["sha256"],
            "next_contiguous_sha256":plan["windows"][1]["sha256"],
            "chapter_body_chars":plan["chapter_body_chars"],
            "chapter_headers_sequential":plan["chapter_earlier_headings_verified"],
            "full_body_reconstructed":plan["full_body_reconstructed"],
            "semantic_boundary_verified":False,
            "diagnostic_only_no_promotion":True,
            "earlier_first_window":"NOT_PASSED",
            "later_window_access":"TEMPORARY_DIAGNOSTIC_ONLY",
            "second_curriculum_window":"LOCKED",
        }
        outcome["baseline_30_display"]=baseline_30_display(outcome["comparisons"])
        outcome["new_original_task_sha256"]=sha256(TRANSFER_TASK.encode("utf-8")).hexdigest()
        outcome["usage"]={
            "api_calls":budget.calls,
            "calls_by_role":dict(budget.calls_by_role),
            "response_observations":list(budget.response_observations),
            "requested_output_tokens_reserved":budget.reserved_output_tokens,
            "prompt_tokens_reported":budget.total_prompt_tokens,
            "completion_tokens_reported":budget.total_completion_tokens,
        }
        outcome["context_configuration"]={
            "model_specs_official_context_tokens":dict(FIXED_MODEL_CONTEXT_TOKENS),
            "discovery_gateway_full_1m_load_verified":DISCOVERY_GATEWAY_1M_LOAD_VERIFIED,
            "per_trial_requested_completion_tokens_max":budget.max_reserved_output_tokens,
            "max_api_calls":budget.max_calls,
        }
        outcome["fixed_cross_vendor_roles"]={
            "planner_and_critic":"deepseek-v4-flash-0731",
            "writer":"glm-5.3",
            "critic_independent_of_writer":True,
            "three_distinct_models":False,
        }
        outcome["provider"]="discovery"
        outcome["source_scope"]="random_sampled_later_chapter_first_contiguous_window_only"
        outcome["random_chapter_sample"]={"protocol":"V28_RANDOM3_BEFORE_SCORE",
            "selection_sha256":sample_sha,"slot":slot,"chapter":chapter,
            "selected_chapters":list(chosen_chapters()),"randomness_pinned_before_scoring":True}
        outcome["literary_quality_status"]="UNVERIFIED_BY_INDEPENDENT_HUMANS"
        outcome["mastery_90_percent_verified"]=False
        outcome["first_window_passed"]=False
        outcome["second_window_unlocked"]=False
        outcome["model_weights_trained"]=False
        payload=_canonical(outcome)
        if len(payload)>MAX_RECEIPT_BYTES:
            raise DiscoveryError("AB_ABSTRACT_REPORT_OVERSIZE")
        h=sha256(payload).hexdigest()
        key=f"{root}/snapshots/{h}.json"
        r2._put_small_immutable(key,payload,h)
        fresh=r2._get_small(key,MAX_RECEIPT_BYTES)
        if fresh!=payload or sha256(fresh).hexdigest()!=h:
            raise DiscoveryError("AB_REPORT_REMOTE_RECOVERY_FAILED")
        if r2._head(finished) is not None:
            raise DiscoveryError("AB_REPORT_CONCURRENT_FINALIZATION")
        pointer=_canonical({"sha256":h,"source_sha256":SOURCE_SHA,
                             "config_sha256":config_sha,
                             "format":TRIAL})
        r2.client.put_object(Bucket=cfg.bucket,Key=finished,
                             Body=pointer,ContentType="application/json")
        if r2._get_small(finished,4096)!=pointer:
            raise DiscoveryError("AB_REPORT_REMOTE_POINTER_RECOVERY_FAILED")
        return {"stage":"DISCOVERY_REAL_MODEL_AB_R2_CONFIRMED",
                "sample_slot":slot,"source_chapter":chapter,
                "receipt_sha256":h,"calls_this_run":budget.calls,
                "calls_by_role":dict(budget.calls_by_role),
                "reported_prompt_tokens":budget.total_prompt_tokens,
                "reported_completion_tokens":budget.total_completion_tokens,
                "mastery_90_percent_verified":False,
                "second_window_unlocked":False,
                "raw_novel_or_draft_persisted":False}

def main():
    try:
        result=run(slot=int(os.environ.get("WF_SAMPLE_SLOT","-1")) )
    except Exception as exc:
        status=type(exc).__name__
        error= str(exc) if isinstance(exc,DiscoveryError) else "INTERNAL_RUNTIME_FAILURE"
        print(json.dumps({"stage":"REAL_DISCOVERY_AB_BLOCKED",
                          "failure_type":status,"failure_code":error[:95],
                          "mastery_verified":False},ensure_ascii=False),
              file=sys.stderr,flush=True)
        raise SystemExit(1)
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

if __name__=="__main__":
    main()
