"""V93 independent cold Reader: real R2 synthetic SQLite relational memory.

This must run in a SEPARATE Railway deployment after the writer exits.
It never reads any real novel or model answer. It pins a synthetic-only R2
manifest SHA from an earlier deployment, reconstructs BOTH SQLite files,
recomputes all V91 byte/schema/table digests, recovers signed revocation and
temporal known/unknown state, and replays SKIP after former SELECT.
No model or R2 Writer credentials, no R2 mutations or new training.
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
for key in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
            "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(key,None)
ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
PINNED_V93_MANIFEST_SHA="__PIN_AFTER_REAL_SYNTHETIC_UPLOAD__"


def emit(document):
    print(json.dumps(document,sort_keys=True,
                     ensure_ascii=False),flush=True)


def main():
    from writerforge.v79_provisional_r2_cas_journal import (
        WFProvisionalR2CASJournal)
    from writerforge.v93_synthetic_graph_cloud_checkpoint import (
        cold_restore_from_cas,V92_EXPERIENCE_CHAIN_SHA)
    from writerforge.v93_synthetic_graph_fixture import (
        create_synthetic_checkpoint,replay_restored_fixture)
    from writerforge.v92_experience_chain import FORMAT as V92_FORMAT
    reader=WFProvisionalR2CASJournal(
        endpoint=ENDPOINT,read_only=True)
    if not reader.read_only or reader.writer is not None or (
         os.getenv("DEEPSEEK_API_KEY") or
         os.getenv("WF_INDEX_UPLOAD_TOKEN")):
        raise ValueError("WF93_READER_NOT_STRICTLY_READ_ONLY")
    old=json.loads(reader._get_content(V92_EXPERIENCE_CHAIN_SHA))
    if (old.get("format")!=V92_FORMAT or old.get("chapter_count")!=15
        or old.get("literary_quality_independently_verified") is not False):
        raise ValueError("WF93_REAL_V92_EXPERIENCE_CHAIN_DID_NOT_SURVIVE")
    if (len(PINNED_V93_MANIFEST_SHA)!=64 or
        PINNED_V93_MANIFEST_SHA.startswith("__")):
        raise ValueError("WF93_MANIFEST_PIN_NOT_SEALED")
    with TemporaryDirectory(prefix="wf93-cold-reader-") as temp:
        root=Path(temp)
        cloud_dir=root/"from-cloud"
        cloud_dir.mkdir()
        verified=cold_restore_from_cas(
            reader,manifest_sha=PINNED_V93_MANIFEST_SHA,
            restore_parent=cloud_dir)
        where=cloud_dir/"checkpoints"/verified["checkpoint_id"]
        recovered=replay_restored_fixture(
            where/"writerforge.sqlite3",
            where/"fact-journal.sqlite3")
        # Reproduce the synthetic fixture locally in this new process:
        # comparison does not trust claims made by the upload process.
        baseline=create_synthetic_checkpoint(root/"fresh-independent-fixture")
        if (recovered["synthetic_prior_decision_sha256"]!=
              baseline["prior_select_decision_sha256"] or
            recovered["synthetic_revoked_decision_sha256"]!=
              baseline["revoked_skip_decision_sha256"] or
            recovered["ledger_head"]!=
              baseline["source_event_global_ledger_head"] or
            recovered["new_post_recovery_choice"]!="SKIP" or
            recovered["known_state"]!="KNOWN" or
            recovered["unrecorded_state"]!="UNRECORDED" or
            recovered["prior_revoked_select_reuse_refused"] is not True):
            raise ValueError("WF93_INDEPENDENT_REPLAY_DIFFERS_FROM_FIXTURE")
        emit({
            "status":"WF93_INDEPENDENT_CLOUD_SYNTHETIC_GRAPH_AND_BEHAVIOR_VERIFIED",
            "synthetic_r2_cas_manifest_sha256":
                PINNED_V93_MANIFEST_SHA,
            "existing_v92_fifteen_experience_manifest_sha256":
                V92_EXPERIENCE_CHAIN_SHA,
            "actual_sqlite_cold_files_verified":
                verified["sqlite_files_restored"],
            "critical_sqlite_tables_verified":
                verified["critical_tables_verified"],
            "synthetic_prior_SELECT_sha256":
                recovered["synthetic_prior_decision_sha256"],
            "synthetic_after_revocation_SKIP_sha256":
                recovered["synthetic_revoked_decision_sha256"],
            "fresh_after_cold_start":"SKIP",
            "past_revoked_SELECT_fails_current_authorization":True,
            "cross_chapter_actor_known_state":"KNOWN",
            "unknown_information_remains":"UNRECORDED",
            "synthetic_global_ledger_seq_recovered":
                recovered["ledger_head"],
            "comparison_against_separately_created_fixture_passed":True,
            "student_training_chapters_new":0,
            "actual_production_factjournal_migrated":False,
            "signed_review_is_public_test_fixture_not_literary_truth":True,
            "original_v92_memory_unchanged":True,
            "paid_model_calls":0,
            "r2_reads_limited_to_pinned_objects":True,
            "r2_writes":0,
            "private_source_or_model_output_logged":False,
        })
        return 0


print("WF93_INDEPENDENT_R2_GRAPH_COLD_READER_STARTED",flush=True)
try:
    exitcode=main()
except Exception as e:
    reason=str(e)
    if not reason.startswith(("WF93_","WF91_","WF_V79_",
                              "WF_INDEX_")) or len(reason)>125:
        reason="WF93_COLD_SYNTHETIC_RESTORE_ABORTED"
    emit({
        "status":"WF93_INDEPENDENT_SYNTHETIC_CLOUD_GRAPH_RESTORE_FAILED",
        "error_code":reason,
        "paid_model_calls":0,"r2_writes":0,
        "no_real_user_state_claimed":True,
    })
    exitcode=1

print("WF93_INDEPENDENT_R2_GRAPH_RESTORE_EXIT="+str(exitcode),flush=True)
raise SystemExit(exitcode)
