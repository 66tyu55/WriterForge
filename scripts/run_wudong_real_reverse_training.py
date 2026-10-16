"""One REAL first-chapter training attempt on GitHub runner, local Ollama models.

No synthetic review, public draft, public original or fake 90%-mastery status.
R2 stores ONLY bounded, unverified training insights and provenance hashes.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import sys

from writerforge.modern_source import _encoding
from writerforge.reverse_core_vault import _validate_snapshot
from writerforge.reverse_real_training import LocalModel,RealFirstUnitTrainer,first_chapter_windows,RealTrainingError
from writerforge.r2_storage import R2Config,R2StudyVault,_canonical,_digest
from writerforge.single_work_runner import SingleWorkVault

SOURCE_SHA="86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28"
SOURCE_BYTES=8_254_079
WORK="wudongqiankun"
PREFIX="writerforge/v1/reverse-craft/wudongqiankun/real-model-first-unit-v1"
MAX_RECORD=14_000


def run():
    cfg=R2Config.from_environment()
    if cfg.bucket!="writerforge-private-library":
        raise RuntimeError("wrong R2 bucket")
    original=SingleWorkVault(cfg,work_id=WORK)
    prior=original.verify_existing_single_work()
    if prior is None or (prior["utf8_sha256"],prior["utf8_bytes"])!=(SOURCE_SHA,SOURCE_BYTES):
        raise RuntimeError("existing pinned source not verified")
    vault=R2StudyVault(cfg)
    latest=f"{PREFIX}/completed.json"
    if vault._head(latest) is not None:
        cached=vault._get_small(latest,4096)
        pointer=json.loads(cached)
        fingerprint=pointer.get("receipt_sha256")
        if not isinstance(fingerprint,str) or len(fingerprint)!=64:
            raise RuntimeError("existing first-unit R2 pointer invalid")
        remote=vault._get_small(f"{PREFIX}/snapshots/{fingerprint}.json",MAX_RECORD)
        if sha256(remote).hexdigest()!=fingerprint:
            raise RuntimeError("existing model training receipt corrupt")
        result=json.loads(remote)
        return {"stage":"previous_real_training_receipt_verified_no_replay",
                "training_performed_this_job":False,
                "status":result.get("promotion_blocked"),
                "receipt_sha256":fingerprint}
    with TemporaryDirectory(prefix="wudong-real-local-model-") as folder:
        source=Path(folder)/"source.private.txt"
        original.client.download_file(cfg.bucket,original._blob_key(WORK,SOURCE_SHA),str(source))
        if _digest(source)!=(SOURCE_SHA,SOURCE_BYTES):
            raise RuntimeError("downloaded original source SHA mismatch")
        plan,segments=first_chapter_windows(source,_encoding(source),SOURCE_SHA)
        if plan["units"][0]["start"]!=0 or plan["units"][0]["end"]!=plan["units"][1]["start"]:
            raise RuntimeError("first chapter provenance not contiguous")
        planner=LocalModel(os.getenv("WF_PLANNER_MODEL") or "qwen2.5:3b")
        writer=LocalModel(os.getenv("WF_WRITER_MODEL") or "qwen2.5:3b")
        critic=LocalModel(os.getenv("WF_CRITIC_MODEL") or "gemma3:4b")
        task=RealFirstUnitTrainer(planner,writer,critic)
        record=task.learn(segments,source_sha=SOURCE_SHA,max_attempts=2)
        record["chapter"]=1
        record["source_bytes"]=SOURCE_BYTES
        record["window_start"]=0
        record["window_end"]=plan["units"][0]["end"]
        record["first_chapter_checked"]=True
        record["runner_only_source_and_drafts"]=True
        record["critic_is_independent_model_but_not_validated_human"]=True
        record["model_provider"]="local_ollama_cpu_GitHub_Actions"
        # Don't keep actual source/draft in the durable result.
        data=_canonical(record)
        if not 100<len(data)<=MAX_RECORD:
            raise RuntimeError("abstract model receipt too large")
        fingerprint=sha256(data).hexdigest()
        key=f"{PREFIX}/snapshots/{fingerprint}.json"
        vault._put_small_immutable(key,data,fingerprint)
        fresh=vault._get_small(key,MAX_RECORD)
        if fresh!=data or sha256(fresh).hexdigest()!=fingerprint:
            raise RuntimeError("R2 first model training receipt recovery mismatch")
        if vault._head(latest) is not None:
            raise RuntimeError("concurrent first-unit model training pointer changed")
        pointer=_canonical({"format":record["format"],"receipt_sha256":fingerprint,
                            "source_sha256":SOURCE_SHA})
        vault.client.put_object(Bucket=cfg.bucket,Key=latest,
                                Body=pointer,ContentType="application/json")
        if vault._get_small(latest,4096)!=pointer:
            raise RuntimeError("model training latest receipt unreadable")
        return {"stage":"real_first_unit_critique_saved_to_private_R2",
                "training_performed_this_job":True,
                "model_calls":record["real_model_calls"],
                "attempts":len(record["attempts"]),
                "first_unit_sha256":record["first_unit_sha256"],
                "reviewer_model":critic.name,"writer_model":writer.name,
                "receipt_sha256":fingerprint,"fresh_R2_roundtrip":True,
                "status":record["promotion_blocked"],
                "independent_90_percent_verified":False,
                "second_unit_unlocked":False}


def main():
    try:
        receipt=run()
    except Exception as exc:
        # Do not expose model prompts, private original or temporary draft.
        print(json.dumps({"status":"REAL_TRAINING_BLOCKED",
                          "failure_type":type(exc).__name__,
                          "failure_code":str(exc)[:160] if isinstance(exc,RealTrainingError)
                              else "source_or_runtime_failure_redacted"},ensure_ascii=False),
              file=sys.stderr,flush=True)
        raise SystemExit(1)
    print(json.dumps(receipt,ensure_ascii=False,indent=2),flush=True)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a",encoding="utf-8") as f:
            f.write("## WriterForge V28 one-book first-unit genuine model practice\n")
            f.write("Stage: "+receipt["stage"]+"\n")
            f.write("Receipt: "+receipt["receipt_sha256"]+"\n")
            f.write("Independently calibrated 90% literary skill: NOT VERIFIED\n")


if __name__=="__main__":
    main()
