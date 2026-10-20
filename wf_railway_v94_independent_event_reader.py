"""V94 independent NEW R2 Reader cold replay of frozen synthetic event log.

Run ONLY after writer exits and the immutable event manifest CAS SHA is
pinned in GitHub. This process drops the model and R2 writer secrets,
reconstructs V93 synthetic-only dual SQLite base, replays all 7 V94 events
through actual FactJournal+ExperienceDecision with a fresh SQL workspace,
and recomputes all operation/terminal SHA receipts.
No real production memory and no literary grading.
"""
from __future__ import annotations
import json,os,sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
for name in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
             "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(name,None)

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
PINNED_V94_EVENT_MANIFEST_SHA="__PIN_V94_EVENT_MANIFEST_AFTER_REAL_WRITE__"


def emit(doc):
    print(json.dumps(doc,sort_keys=True,
                     ensure_ascii=False),flush=True)


def main():
    if not os.getenv("WF_API_TOKEN") or (
       os.getenv("WF_INDEX_UPLOAD_TOKEN") or
       os.getenv("DEEPSEEK_API_KEY")):
        raise ValueError("WF94_COLD_READER_ROLE_NOT_ISOLATED")
    from writerforge.v79_provisional_r2_cas_journal import (
        WFProvisionalR2CASJournal)
    from writerforge.v94_synthetic_event_commit import (
        BASE_GRAPH_SHA,V92_EXPERIENCE_CHAIN_SHA,
        cold_replay,is_sha,
    )
    from writerforge.v92_experience_chain import FORMAT as V92_FORMAT
    if not is_sha(PINNED_V94_EVENT_MANIFEST_SHA):
        raise ValueError("WF94_COLD_READER_MANIFEST_NOT_PINNED")
    reader=WFProvisionalR2CASJournal(
        endpoint=ENDPOINT,read_only=True)
    if not reader.read_only or reader.writer is not None:
        raise ValueError("WF94_COLD_READER_WRITER_ROLE_DETECTED")
    v92=json.loads(reader._get_content(V92_EXPERIENCE_CHAIN_SHA))
    if (v92.get("format")!=V92_FORMAT or
        v92.get("chapter_count")!=15 or
        v92.get("literary_quality_independently_verified") is not False):
        raise ValueError("WF94_SOURCE_V92_EXPERIENCE_CHAIN_CHANGED")
    with TemporaryDirectory(prefix="wf94-event-cold-replay-") as tmp:
        path=Path(tmp)/"restored"
        path.mkdir()
        outcome=cold_replay(
            reader,manifest_sha=PINNED_V94_EVENT_MANIFEST_SHA,
            workdir=path)
        if (outcome["verified_cas_events"]!=7 or
            outcome["before_revocation"]!="SELECT" or
            outcome["after_revocation"]!="SKIP" or
            outcome["original_character_state"]!="KNOWN" or
            outcome["latest_character_state"]!="CONFLICT_UNRESOLVED" or
            outcome["unknown_future_state"]!="UNRECORDED" or
            outcome["actual_production_graph_durable_write_stream_active"]
                is not False or
            outcome["base_v93_graph_manifest_sha256"]!=BASE_GRAPH_SHA):
            raise ValueError("WF94_INDEPENDENT_REPLAY_EXPECTATION_MISMATCH")
        emit({
            **outcome,
            "status":"WF94_INDEPENDENT_R2_EVENT_AND_BEHAVIOR_REPLAY_VERIFIED",
            "private_synthetic_graph_reconstructed_from_v93":True,
            "all_seven_event_outcome_shas_recomputed":True,
            "production_Learn_stream_active":False,
            "independent_literary_review_completed":False,
            "model_api_calls":0,"r2_writes":0,
            "old_v92_fifteen_literary_experiences_unchanged":True,
            "private_originals_and_model_text_logged":False,
        })
        return 0


print("WF94_COLD_R2_EVENT_REPLAY_STARTED",flush=True)
try:
    result=main()
except Exception as exc:
    code=str(exc)
    if not code.startswith(("WF94_","WF93_","WF91_",
                            "WF_V79_","WF_INDEX_")) or len(code)>115:
        code="WF94_UNVERIFIED_EVENT_COLD_REPLAY"
    emit({"status":"WF94_INDEPENDENT_R2_EVENT_COLD_REPLAY_FAILED",
          "reason_code":code,
          "model_calls":0,"r2_writes":0,
          "no_production_memory_claimed":True})
    result=1

print("WF94_COLD_R2_EVENT_REPLAY_EXIT="+str(result),flush=True)
raise SystemExit(result)
