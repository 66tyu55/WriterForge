"""V94 real R2 CAS synthetic event-commit drill, no model or user memories.

First cold-restore immutable V93 SYNTHETIC_ONLY graph, compute and
independently re-run 7 tightly whitelisted FactJournal/ExperienceDecision
synthetic events, then upload 7 immutable CAS event blobs one by one and
publish commit manifest LAST. No raw novels or real user facts. Every CAS
block is read back byte-for-byte before the next write. On failure preserve
the previous V93 + V92 immutable graph/experience snapshots; do not retry.
"""
from __future__ import annotations

import json,os,sys
from tempfile import TemporaryDirectory
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
for k in ("DEEPSEEK_API_KEY","WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(k,None)
ENDPOINT="https://wf-r2-api.3227482831.workers.dev"


def emit(obj):
    print(json.dumps(obj,sort_keys=True,
                     ensure_ascii=False),flush=True)


def main():
    for k in ("WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN"):
        if not os.getenv(k):
            emit({"status":"WF94_EXISTING_R2_WRITER_NOT_READY",
                  "required":k,"model_calls":0})
            return 1
    from writerforge.v79_provisional_r2_cas_journal import (
        WFProvisionalR2CASJournal)
    from writerforge.v92_experience_chain import FORMAT as V92_FORMAT
    from writerforge.v94_synthetic_event_commit import (
        BASE_GRAPH_SHA,V92_EXPERIENCE_CHAIN_SHA,
        prepare_chain,publish_chain,digest,
    )
    writer=WFProvisionalR2CASJournal(endpoint=ENDPOINT)
    writer.require_writer_ready()
    reader=WFProvisionalR2CASJournal(endpoint=ENDPOINT,read_only=True)
    if not reader.read_only or reader.writer is not None:
        raise ValueError("WF94_READER_HAS_WRITER_ROLE")
    v92=json.loads(reader._get_content(V92_EXPERIENCE_CHAIN_SHA))
    if (v92.get("format")!=V92_FORMAT or
        v92.get("chapter_count")!=15 or
        v92.get("literary_quality_independently_verified") is not False):
        raise ValueError("WF94_V92_LEGACY_SOURCE_REFS_CHANGED")
    written=None
    with TemporaryDirectory(prefix="wf94-synthetic-event-drill-") as tmp:
        root=Path(tmp)
        prepare_dir=root/"prepare"
        prepare_dir.mkdir()
        event_docs,manifest,final=prepare_chain(
            reader,workdir=prepare_dir)
        expected=digest(manifest)
        emit({
            "status":"WF94_SYNTHETIC_SEVEN_EVENT_PRECOMMIT_READY",
            "prior_v93_synthetic_graph_sha256":BASE_GRAPH_SHA,
            "original_v92_fifteen_experience_sha256":
                V92_EXPERIENCE_CHAIN_SHA,
            "precommitted_event_count":len(event_docs),
            "expected_manifest_sha256":expected,
            "source_ledger_seq":final["source_snapshot_global_ledger_seq"],
            "new_ledger_seq":final["new_global_ledger_seq"],
            "prior_state":"KNOWN",
            "latest_state":"CONFLICT_UNRESOLVED",
            "before_revocation":"SELECT",
            "after_revocation":"SKIP",
            "real_user_graph_touched":False,
            "r2_writes_so_far":0,
            "paid_model_calls":0,
        })
        dry_dir=root/"independent_preflight"
        dry_dir.mkdir()
        written=publish_chain(
            writer,reader,event_bytes=event_docs,
            manifest_raw=manifest,preflight_dir=dry_dir)
        emit({
            **written,
            "status":"WF94_SEVEN_SYNTHETIC_R2_EVENTS_AND_COMMIT_SAVED",
            "v94_event_commit_sha256":written["manifest_sha256"],
            "all_events_content_addressed_and_readback":True,
            "r2_commit_is_manifest_last":True,
            "prior_v93_snapshot_still_authoritative_if_uncommitted":True,
            "independent_separate_process_cold_replay_pending":True,
            "production_graph_and_actual_literary_review_not_verified":True,
            "no_new_training_chapters":True,
            "paid_model_calls":0,
            "private_novel_and_model_output_logged":False,
        })
    return 0

print("WF94_R2_SYNTHETIC_EVENT_COMMIT_WRITER_STARTED",flush=True)
try:
    status=main()
except Exception as exc:
    message=str(exc)
    if not message.startswith(("WF94_","WF93_","WF91_","WF_V79_",
                               "WF_INDEX_")) or len(message)>110:
        message="WF94_SYNTHETIC_EVENT_COMMIT_PAUSED_UNCLASSIFIED"
    emit({
        "status":"WF94_CAS_WRITE_STOPPED_KEEP_OLD_SNAPSHOT",
        "reason_code":message,
        "no_automatic_retry":True,
        "existing_v92_v93_object_trees_never_overwritten":True,
        "paid_model_calls":0,
        "production_knowledge_graph_not_modified":True,
    })
    status=1
print("WF94_R2_SYNTHETIC_EVENT_COMMIT_EXIT="+str(status),flush=True)
raise SystemExit(status)
