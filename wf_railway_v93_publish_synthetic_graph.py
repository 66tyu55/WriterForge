"""V93 one-shot SYNTHETIC graph R2 CAS checkpoint rehearsal.

NEVER uploads real user relation history or private books. Existing R2 index
Writer is used only for synthetic SQLite fixture chunks and the manifest LAST.
Old V92 fifteen-experience manifest must still exist and is NOT overwritten.
All model variables removed; no automatic retry and no new credential.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
for key in ("DEEPSEEK_API_KEY","WF_LEARN_UPLOAD_TOKEN",
            "DISCOVERY_API_KEY"):
    os.environ.pop(key,None)
ENDPOINT="https://wf-r2-api.3227482831.workers.dev"

def emit(value):
    print(json.dumps(value,sort_keys=True,ensure_ascii=False),flush=True)

def main():
    for key in ("WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN"):
        if not os.getenv(key):
            emit({"status":"WF93_EXISTING_R2_CAPABILITY_MISSING",
                  "missing_name":key,"model_calls":0,"r2_writes":0})
            return 1
    from writerforge.v79_provisional_r2_cas_journal import (
        WFProvisionalR2CASJournal)
    from writerforge.v93_synthetic_graph_fixture import (
        create_synthetic_checkpoint,replay_restored_fixture)
    from writerforge.v93_synthetic_graph_cloud_checkpoint import (
        V92_EXPERIENCE_CHAIN_SHA,build_private_synthetic_package,
        publish_to_cas,cold_restore_from_cas,
    )
    from writerforge.v92_experience_chain import FORMAT as V92_FORMAT
    from writerforge.v91_lifelong_checkpoint import verify_checkpoint
    journal=WFProvisionalR2CASJournal(endpoint=ENDPOINT)
    journal.require_writer_ready()
    prior=json.loads(journal._get_content(V92_EXPERIENCE_CHAIN_SHA))
    if (prior.get("format")!=V92_FORMAT or
        prior.get("chapter_count")!=15 or
        prior.get("literary_quality_independently_verified") is not False):
        raise ValueError("WF93_V92_PREVIOUS_EXPERIENCE_MANIFEST_CHANGED")
    with TemporaryDirectory(prefix="wf93-synthetic-state-") as temp:
        root=Path(temp)
        fixture=create_synthetic_checkpoint(root/"work")
        proof=verify_checkpoint(fixture["checkpoint_root"])
        manifest_raw,parts=build_private_synthetic_package(
            fixture["checkpoint_root"])
        # All checks MUST occur before any cloud writes. This manifest
        # embeds no full original book, user identity, production graph or
        # independent quality claim. It is a real SQLite architecture drill.
        emit({
            "status":"WF93_FROZEN_SYNTHETIC_DOUBLE_SQLITE_PRECHECKED",
            "synthetic_local_manifest_sha256":proof["manifest_sha256"],
            "cloud_manifest_sha256":__import__("hashlib").sha256(
                manifest_raw).hexdigest(),
            "bounded_compressed_chunk_count":len(parts),
            "v92_old_fifteen_experiences_still_pinned":True,
            "production_graph_used":False,
            "model_calls":0,"r2_writes_so_far":0,
            "private_source_not_logged":True,
        })
        upload=publish_to_cas(
            journal,manifest_raw=manifest_raw,parts=parts)
        # The same process may mechanically read back all cloud data;
        # final acceptance REQUIRES a second read-only Railway process.
        reader=WFProvisionalR2CASJournal(endpoint=ENDPOINT,
                                          read_only=True)
        dest=root/"verify"
        dest.mkdir()
        cold=cold_restore_from_cas(
            reader,manifest_sha=upload["manifest_sha256"],
            restore_parent=dest)
        folder=dest/"checkpoints"/cold["checkpoint_id"]
        replay=replay_restored_fixture(
            folder/"writerforge.sqlite3",
            folder/"fact-journal.sqlite3")
        if (replay["new_post_recovery_choice"]!="SKIP" or
            replay["known_state"]!="KNOWN" or
            replay["unrecorded_state"]!="UNRECORDED" or
            replay["synthetic_prior_decision_sha256"]!=
                 fixture["prior_select_decision_sha256"]):
            raise ValueError("WF93_SYNTHETIC_CLOUD_BEHAVIOR_REPLAY_FAILED")
        emit({
            **upload,
            "status":"WF93_SYNTHETIC_DUAL_SQLITE_R2_MANIFEST_LAST_VERIFIED",
            "cold_reader_same_process_checked":True,
            "different_process_reader_pending":True,
            "fact_journal_knowledge_state_recovered":True,
            "revoked_experience_still_skipped":True,
            "original_prior_select_receipt_recovered":True,
            "current_real_WF_production_graph_exists":False,
            "synthetic_reviewer_not_independent_semantic_judge":True,
            "migration_does_not_prove_literary_improvement":True,
            "model_calls":0,
            "no_original_books_written":True,
            "preexisting_v92_experience_objects_not_changed":True,
        })
        return 0

print("WF93_SYNTHETIC_CLOUD_GRAPH_WRITER_STARTED",flush=True)
try:
    rc=main()
except Exception as error:
    reason=str(error)
    if not reason.startswith(("WF93_","WF91_","WF_V79_","WF_INDEX_")) or len(reason)>120:
        reason="WF93_SYNTHETIC_WRITE_FAILED_NO_AUTO_RETRY"
    emit({
        "status":"WF93_SYNTHETIC_CAS_DRILL_STOPPED",
        "reason_code":reason,"new_paid_model_calls":0,
        "old_V92_experience_chain_always_authoritative":True,
        "no_production_graph_written":True,
        "private_source_not_logged":True,
        "must_manual_readback_before_retry":True,
    })
    rc=1

print("WF93_SYNTHETIC_CLOUD_GRAPH_EXIT="+str(rc),flush=True)
raise SystemExit(rc)
