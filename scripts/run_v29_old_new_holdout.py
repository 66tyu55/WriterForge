"""One real model old-vs-semantic WF A/B on one pre-registered unseen task.

True snapshot from pinned private R2. Separate immutable output namespace
for each held-out task, never mutate old A/B receipts. No draft/source text
or provider prompts are logged or persistently saved.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json,os,re,sys

from writerforge.modern_source import _encoding
from writerforge.reverse_real_training import raw_hash
from writerforge.reverse_later_window import later_chapter_diagnostic
from writerforge.v29_fresh_holdout import chosen_ids,task,manifest,manifest_sha
from writerforge.v29_old_new_trial import (
    compare_old_vs_semantic,SemanticTrialAbstained,LengthUnscorable,
    BUDGET_PROFILE,
)
from writerforge.reverse_discovery_models import (
    DiscoveryCallBudget, DiscoveryModel, DiscoveryError, ROLE_MODELS)
from writerforge.r2_storage import R2Config,R2StudyVault,_canonical,_digest
from writerforge.single_work_runner import SingleWorkVault

SOURCE_SHA="86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28"
SOURCE_BYTES=8_254_079
SOURCE_UNIT_SHA="96b6363d40be7b99d5635af1346da0c04e44556fc06e32d1aab04e419e4942fa"
FOLLOWING_UNIT_SHA="9ddcccf76a3f63d8036355c006ee20c976dacb1dd6ff250ef921f47e9221ac8e"
PREFIX="writerforge/v1/reverse-craft/wudongqiankun/v29-old-vs-semantic-fresh-holdout"
TRIAL="v29-sourceblind-old-vs-semantic-two-arm"
MAX_REPORT_BYTES=32000

def root_for_slot(slot:int)->str:
    if type(slot) is not int or slot not in (0,1,2):
        raise DiscoveryError("INVALID_FRESH_HOLDOUT_SLOT")
    configuration={
        "experiment":TRIAL,"source_sha256":SOURCE_SHA,
        "source_unit_sha256":SOURCE_UNIT_SHA,
        "slot":slot,"scenario":chosen_ids()[slot],
        "task_sha256":raw_hash(task(slot)),
        "seed_manifest_sha256":manifest_sha(),
        "models":ROLE_MODELS,"role_tokens":list(BUDGET_PROFILE),
        "wire_profile":"glm5.3-low-thought-sourceblind-legacy-semantic",
    }
    h=sha256(_canonical(configuration)).hexdigest()
    return f"{PREFIX}/slot-{slot}-{chosen_ids()[slot]}/{h}"

def run(*,slot:int)->dict:
    root=root_for_slot(slot)
    token=os.environ.get("DISCOVERY_API_KEY","")
    if len(token)<12:
        raise DiscoveryError("DISCOVERY_API_KEY_UNAVAILABLE")
    cfg=R2Config.from_environment()
    if cfg.bucket!="writerforge-private-library":
        raise DiscoveryError("PRIVATE_R2_BUCKET_REQUIRED")
    store=R2StudyVault(cfg)
    pointer_key=root+"/completed.json"
    if store._head(pointer_key) is not None:
        pointer=json.loads(store._get_small(pointer_key,4096))
        h=pointer.get("sha256")
        if not isinstance(h,str) or not re.fullmatch(r"[a-f0-9]{64}",h):
            raise DiscoveryError("INVALID_EXISTING_HOLDOUT_POINTER")
        raw=store._get_small(root+"/snapshots/"+h+".json",MAX_REPORT_BYTES)
        if sha256(raw).hexdigest()!=h:
            raise DiscoveryError("EXISTING_HOLDOUT_R2_HASH_MISMATCH")
        return {"stage":"CACHED_HOLDOUT_NO_NEW_MODEL_CALLS",
                "slot":slot,"scenario":chosen_ids()[slot],
                "receipt_sha256":h,"calls_now":0}
    vault=SingleWorkVault(cfg,work_id="wudongqiankun")
    record=vault.verify_existing_single_work()
    if (record is None or
        (record["utf8_sha256"],record["utf8_bytes"])!=(SOURCE_SHA,SOURCE_BYTES)):
        raise DiscoveryError("PINNED_ORIGINAL_CHANGED")
    with TemporaryDirectory(prefix="writerforge-v29-holdout-") as temp:
        path=Path(temp)/"source.private.txt"
        vault.client.download_file(cfg.bucket,
            vault._blob_key("wudongqiankun",SOURCE_SHA),str(path))
        if _digest(path)!=(SOURCE_SHA,SOURCE_BYTES):
            raise DiscoveryError("NEW_DOWNLOAD_SOURCE_HASH_BAD")
        plan,(first,following)=later_chapter_diagnostic(
            path,_encoding(path),expected_source_sha256=SOURCE_SHA,
            chapter=3,sampled_diagnostic=True)
        if (plan["windows"][0]["sha256"]!=SOURCE_UNIT_SHA or
            plan["windows"][1]["sha256"]!=FOLLOWING_UNIT_SHA or
            not plan["full_body_reconstructed"]):
            raise DiscoveryError("PINNED_FIRST_SOURCE_WINDOW_BAD")
        budget=DiscoveryCallBudget(max_calls=7,max_reserved_output_tokens=50000)
        roles={role:DiscoveryModel(
                 name=name,role=role,api_key=token,budget=budget,
                 reasoning_effort="low" if role=="writer" else None)
               for role,name in ROLE_MODELS.items()}
        try:
            report=compare_old_vs_semantic(
                planner=roles["planner"],writer=roles["writer"],critic=roles["critic"],
                first=first,second=following,source_sha=SOURCE_SHA,
                source_window_sha=raw_hash(first),writing_task=task(slot))
        except SemanticTrialAbstained as exc:
            data={
                "format":"writerforge.v29-abstention.v1",
                "stage":"SEMANTIC_ADAPTER_ABSTAINED_NOT_SCORED",
                "slot":slot,"scenario":chosen_ids()[slot],
                "source_sha256":SOURCE_SHA,"source_window_sha256":SOURCE_UNIT_SHA,
                "task_sha256":raw_hash(task(slot)),
                "precommitted_manifest_sha256":manifest_sha(),
                "candidate":exc.safe_candidate,
                "calls_used":budget.calls,
                "no_old_vs_new_quality_score":True,
                "no_core_promotion":True,
            }
            blob=_canonical(data)
            h=sha256(blob).hexdigest()
            key=root+"/abstentions/"+h+".json"
            store._put_small_immutable(key,blob,h)
            if store._get_small(key,8192)!=blob:
                raise DiscoveryError("ABSTENTION_R2_READBACK_FAILED")
            return {"stage":"SEMANTIC_ABSTENTION_REAL_R2_RECORDED",
                    "slot":slot,"scenario":chosen_ids()[slot],
                    "receipt_sha256":h,"calls_used":budget.calls,
                    "model_literary_score":None}
        except Exception as exc:
            # Never save model prompt/prose/HTTP response in error evidence.
            safe=str(exc)
            if safe not in (
                "OLD_NEW_AB_LENGTH_MISMATCH_UNSCORABLE",
                "UNVERIFIED_AB_CRITIC_SCHEMA",
                "SEMANTIC_EVIDENCE_NOT_IN_SOURCE",
                "SEMANTIC_PLANNER_SCHEMA_INVALID",
                "SEMANTIC_SELECTION_COUNT_INVALID",
                "SEMANTIC_UNSUPPORTED_OR_OVERSIZE_EXPLANATION",
                "SEMANTIC_EVIDENCE_PARAGRAPH_NOT_FOUND",
                "WRITER_DRAFT_NOT_BOUNDED",
                "SYMMETRIC_MANUSCRIPT_REVISION_INVALID",
                "MODEL_CALL_OR_TOKEN_BUDGET_EXHAUSTED",
                "DISCOVERY_WRITER_OUTPUT_TRUNCATED",
                "DISCOVERY_WRITER_EMPTY_VISIBLE_TEXT",
                "DISCOVERY_PLANNER_JSON_CONTRACT_FAILED",
                "DISCOVERY_CRITIC_JSON_CONTRACT_FAILED",
            ):
                if not (isinstance(exc,DiscoveryError)
                        and safe.startswith("DISCOVERY_")
                        and len(safe)<=90
                        and all(x.isupper() or x.isdigit() or x=="_" for x in safe)):
                    safe=type(exc).__name__
            failure={
                "format":"writerforge.v29-holdout-failure.v1",
                "slot":slot,"scenario":chosen_ids()[slot],
                "task_sha256":raw_hash(task(slot)),
                "source_unit_sha256":SOURCE_UNIT_SHA,
                "experiment":TRIAL,"code":safe,
                "model_calls":budget.calls,"calls_by_role":dict(budget.calls_by_role),
                "observations":list(budget.response_observations),
                "drafts_or_source_persisted":False,
                "safe_length_diagnostics":(
                    exc.safe_lengths if isinstance(exc,LengthUnscorable) else None),
                "score":None,"promotable":False,
            }
            blob=_canonical(failure)
            h=sha256(blob).hexdigest()
            key=root+"/failures/"+h+".json"
            store._put_small_immutable(key,blob,h)
            if store._get_small(key,8192)!=blob:
                raise DiscoveryError("FAILURE_R2_READBACK_FAILED")
            print(json.dumps({"stage":"REAL_V29_HOLDOUT_FAILED_WITH_PRIVATE_R2",
               "slot":slot,"failure_code":safe,"calls":budget.calls,
               "failure_sha256":h,"no_draft_source_persisted":True},ensure_ascii=False))
            raise
        report["slot"]=slot
        report["scenario"]=chosen_ids()[slot]
        report["heldout_manifest"]=manifest()
        report["heldout_manifest_sha256"]=manifest_sha()
        report["original_task_sha256"]=raw_hash(task(slot))
        report["model_usage"]={
            "calls":budget.calls,"by_role":dict(budget.calls_by_role),
            "prompt_tokens_reported":budget.total_prompt_tokens,
            "completion_tokens_reported":budget.total_completion_tokens,
            "reserved_output_tokens":budget.reserved_output_tokens,
            "observations":list(budget.response_observations),
        }
        raw=_canonical(report)
        if len(raw)>MAX_REPORT_BYTES:
            raise DiscoveryError("HOLDOUT_REPORT_TOO_LARGE")
        h=sha256(raw).hexdigest()
        key=root+"/snapshots/"+h+".json"
        store._put_small_immutable(key,raw,h)
        if store._get_small(key,MAX_REPORT_BYTES)!=raw:
            raise DiscoveryError("HOLDOUT_R2_FRESH_READBACK_FAILED")
        pointer=_canonical({"sha256":h,"source_sha256":SOURCE_SHA,
                "task_sha256":raw_hash(task(slot)),"trial":TRIAL})
        if store._head(pointer_key) is not None:
            raise DiscoveryError("CONCURRENT_HOLDOUT_FINALIZATION")
        store.client.put_object(Bucket=cfg.bucket,Key=pointer_key,
                                Body=pointer,ContentType="application/json")
        if store._get_small(pointer_key,4096)!=pointer:
            raise DiscoveryError("HOLDOUT_POINTER_READBACK_FAILED")
        return {"stage":"REAL_OLD_NEW_WF_R2_BLIND_A_B_VERIFIED",
                "slot":slot,"scenario":chosen_ids()[slot],
                "receipt_sha256":h,"calls":budget.calls,
                "prompt_tokens_reported":budget.total_prompt_tokens,
                "completion_tokens_reported":budget.total_completion_tokens,
                "old_mean":report["comparisons"]["legacy"]["model_mean"],
                "new_mean":report["comparisons"]["semantic"]["model_mean"],
                "delta":report["semantic_minus_legacy_model_mean"],
                "no_literary_promotion":True}

if __name__=="__main__":
    try:
        result=run(slot=int(os.environ.get("WF_HOLDOUT_SLOT","-1")))
        print(json.dumps(result,ensure_ascii=False,sort_keys=True),flush=True)
    except Exception as exc:
        safe=str(exc) if isinstance(exc,DiscoveryError) else type(exc).__name__
        print(json.dumps({"stage":"V29_HOLDOUT_NOT_PASSED","code":safe[:90],
                          "no_claim_of_literary_progress":True},ensure_ascii=False),
              file=sys.stderr,flush=True)
        raise SystemExit(1)
