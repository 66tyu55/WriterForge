"""Explicit opt-in REAL V28 cloud A/B on existing private Wudong chapter one.

Run ONLY with permission to transfer first 2125 source characters to selected
third-party provider(s). No novel/draft body in GitHub logs or durable R2.
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
from writerforge.reverse_cloud_models import configured_cloud_roles, safe_cloud_readiness
from writerforge.reverse_cloud_ab import CloudABTrial
from writerforge.reverse_real_training import first_chapter_windows, raw_hash
from writerforge.r2_storage import R2Config, R2StudyVault, _digest, _canonical
from writerforge.single_work_runner import SingleWorkVault

SOURCE_SHA = "86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28"
SOURCE_BYTES = 8_254_079
WORK = "wudongqiankun"
PREFIX = "writerforge/v1/reverse-craft/wudongqiankun/real-cloud-ab-v1"
MAX_BYTES = 25000


def run():
    # Must be an explicitly selected workflow, with a separate affirmative
    # source-egress toggle. Ordinary pushes can never perform paid API calls.
    if os.environ.get("WF_V28_ALLOW_SOURCE_EGRESS") != "yes":
        return {"stage":"BLOCKED_EXTERNAL_SOURCE_CONSENT",
                "charged":False,"source_egress":False}
    models,budget = configured_cloud_roles()
    cfg=R2Config.from_environment()
    if cfg.bucket!="writerforge-private-library":
        raise RuntimeError("private bucket required")
    original=SingleWorkVault(cfg,work_id=WORK)
    receipt=original.verify_existing_single_work()
    if receipt is None or (receipt["utf8_sha256"],receipt["utf8_bytes"])!=(SOURCE_SHA,SOURCE_BYTES):
        raise RuntimeError("pinned original must be present in private R2")
    model_spec={role:{"provider":m.provider,"model":m.name} for role,m in models.items()}
    fingerprint=sha256(_canonical({"source_sha":SOURCE_SHA,
                     "window":"chapter1-first-half-v1","roles":model_spec,
                     "experiment_version":"ab-v1"})).hexdigest()
    prefix=f"{PREFIX}/{fingerprint}"
    vault=R2StudyVault(cfg)
    pointer=f"{prefix}/completed.json"
    if vault._head(pointer) is not None:
        raw=vault._get_small(pointer,4096)
        record=json.loads(raw)
        h=record.get("receipt_sha256")
        if not isinstance(h,str) or not re.fullmatch(r"[0-9a-f]{64}",h):
            raise RuntimeError("existing experiment pointer is invalid")
        stored=vault._get_small(f"{prefix}/snapshots/{h}.json",MAX_BYTES)
        if sha256(stored).hexdigest()!=h:
            raise RuntimeError("existing cloud AB receipt corrupted")
        return {"stage":"CACHED_CLOUD_AB_VERIFIED_NO_DUPLICATE_BILLING",
                "receipt_sha256":h,"paid_calls_this_run":0,"source_egress_this_run":False,
                "human_90_percent_verified":False}
    with TemporaryDirectory(prefix="wf-v28-cloud-ab-") as directory:
        source=Path(directory)/"original.private.txt"
        original.client.download_file(cfg.bucket,original._blob_key(WORK,SOURCE_SHA),str(source))
        if _digest(source)!=(SOURCE_SHA,SOURCE_BYTES):
            raise RuntimeError("original fresh download did not match pinned SHA")
        plan,(first,second)=first_chapter_windows(source,_encoding(source),SOURCE_SHA)
        if plan["units"][0]["start"]!=0 or plan["units"][1]["start"]!=len(first):
            raise RuntimeError("source chapter opening is not contiguous")
        output=CloudABTrial(
            planner=models["planner"],writer=models["writer"],critic=models["critic"]
        ).run(first,second,source_sha=SOURCE_SHA,window_hash=raw_hash(first))
        output["budget"]={
            "max_calls":budget.max_calls,"used_calls":budget.calls,
            "max_usd_configured":budget.max_usd,
            "worst_case_reserved_usd":round(budget.reserved_usd,6),
            "input_tokens_reported":budget.observed_input_tokens,
            "output_tokens_reported":budget.observed_output_tokens,
        }
        output["original_egress_first_window_only"]=True
        output["unverified_fiction_learning_not_promoted"]=True
        encoded=_canonical(output)
        if not 100<=len(encoded)<=MAX_BYTES:
            raise RuntimeError("redacted AB report exceeds bounded size")
        h=sha256(encoded).hexdigest()
        dest=f"{prefix}/snapshots/{h}.json"
        vault._put_small_immutable(dest,encoded,h)
        if vault._get_small(dest,MAX_BYTES)!=encoded:
            raise RuntimeError("first R2 restore differs from cloud AB report")
        if vault._head(pointer) is not None:
            raise RuntimeError("another AB run already owns this model configuration")
        latest=_canonical({"source_sha256":SOURCE_SHA,
                           "receipt_sha256":h,
                           "experiment_fingerprint":fingerprint})
        vault.client.put_object(Bucket=cfg.bucket,Key=pointer,
                                Body=latest,ContentType="application/json")
        if vault._get_small(pointer,4096)!=latest:
            raise RuntimeError("AB receipt pointer did not survive R2 fresh GET")
        return {"stage":"REAL_CLOUD_AB_PRIVATE_R2_VERIFIED",
                "receipt_sha256":h,"experiment_fingerprint":fingerprint,
                "paid_calls_this_run":budget.calls,
                "max_usd":budget.max_usd,"worst_case_reserved_usd":round(budget.reserved_usd,6),
                "baseline_and_skill_compared":True,
                "human_90_percent_verified":False,
                "second_unit_unlocked":False}


def main():
    try:
        result=run()
    except Exception as exc:
        # Never print error strings, headers, provider response or original.
        print(json.dumps({"stage":"CLOUD_AB_FAIL_CLOSED",
                          "reason_type":type(exc).__name__,
                          "quality_verified":False},ensure_ascii=False),file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a",encoding="utf-8") as writer:
            writer.write("## V28 cloud AB\nStage: "+result["stage"]+
                         "\nIndependent calibrated 90% literary quality: NOT VERIFIED\n")


if __name__=="__main__":
    main()
