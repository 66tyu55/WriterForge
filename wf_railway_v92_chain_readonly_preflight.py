"""V92 first stage: real private R2 READ-ONLY full V80 experience ancestry.

Freeze the 1..15 existing V80 source CAS chain and all new V91 SHA values
BEFORE any R2 writes. No model calls, no new reader/writer keys, no novel
prose, no user-facing Chinese experience strings. Fail on a missing early
chapter instead of declaring a 15-item success with a partial history.
"""
from __future__ import annotations
import json,os,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT);sys.path.insert(0,str(ROOT))
for name in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
             "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(name,None)
ENDPOINT="https://wf-r2-api.3227482831.workers.dev"

def emit(v):
    print(json.dumps(v,sort_keys=True,ensure_ascii=False),flush=True)


def main():
    if not os.getenv("WF_API_TOKEN"):
        emit({"status":"WF92_EXISTING_R2_READER_MISSING","model_calls":0})
        return 1
    from writerforge.v79_provisional_r2_cas_journal import WFProvisionalR2CASJournal
    from writerforge.v92_experience_chain import (
        walk_v80_chain,make_manifest,canonical,sha,V82_FINAL_BATCH,
        V82_FINAL_JOURNAL,ORIGINAL_V80_HEAD,V91_CH15_CAS,
        V91_CH15_MANIFEST,SOURCE_SHA,CHAPTERS)
    from writerforge.v91_private_cas_manifest import validate_experience_manifest

    reader=WFProvisionalR2CASJournal(
        endpoint=ENDPOINT,read_only=True)
    if not reader.read_only or reader.writer is not None:
        raise ValueError("WF92_R2_WRITER_PRESENT_DURING_PREFLIGHT")
    batch=json.loads(reader._get_content(V82_FINAL_BATCH).decode("utf8"))
    journal_bytes=reader._get_content(V82_FINAL_JOURNAL)
    if (batch.get("last_completed_chapter")!=15 or
        batch.get("source_sha256")!=SOURCE_SHA or
        batch.get("latest_experience_sha256")!=ORIGINAL_V80_HEAD or
        batch.get("journal_checkpoint_sha256")!=V82_FINAL_JOURNAL or
        batch.get("mastery_graduation_approved") is not False or
        not journal_bytes):
        raise ValueError("WF92_V82_15_CHAPTER_ANCHOR_CHANGED")
    entries,private_objects=walk_v80_chain(reader._get_content)
    manifest=make_manifest(entries)
    old_v91=reader._get_content(V91_CH15_CAS)
    old_manifest=reader._get_content(V91_CH15_MANIFEST)
    validate_experience_manifest(
        manifest_raw=old_manifest,migrated_raw=old_v91)
    if private_objects[CHAPTERS]!=old_v91:
        raise ValueError("WF92_V91_CHAPTER15_PERSISTED_BYTES_DIFFER")
    emit({
        "status":"WF92_REAL_R2_FIFTEEN_LEGACY_EXPERIENCE_CHAIN_PRECHECKED",
        "verified_count":len(entries),
        "completed_chapters":[x["chapter"] for x in entries],
        "old_cas_shas_per_chapter":[
            x["original_v80_cas_sha256"] for x in entries],
        "proposed_new_v91_cas_shas_per_chapter":[
            x["v91_experience_cas_sha256"] for x in entries],
        "precommitted_full_chain_manifest_sha256":
            sha(canonical(manifest)),
        "preexisting_chapter15_v91_cas_sha256":V91_CH15_CAS,
        "chapter1_pilot_non_strict_exception_preserved":True,
        "all_old_original_chinese_reflection_fields_recovered":True,
        "future_r2_writes_planned_if_allowed":14+1,
        "r2_writes_now":0,"model_calls":0,
        "legacy_training_retained":True,
        "private_originals_or_strategy_in_output":False,
        "independent_literary_mastery_proven":False,
    })
    return 0

print("WF92_READONLY_EXISTING_FIFTEEN_EXPERIENCES_START",flush=True)
try:
    code=main()
except Exception as exc:
    reason=str(exc)
    if not reason.startswith(("WF92_","WF91_","WF_V79_",
                              "WF_INDEX_","WF_LEARN_")) or len(reason)>110:
        reason="WF92_READONLY_PREFLIGHT_FAILED_UNCLASSIFIED"
    emit({"status":"WF92_READONLY_CHAIN_PRECHECK_ABORTED",
          "reason_code":reason,"model_calls":0,"r2_writes":0,
          "private_originals_or_experiences_not_logged":True})
    code=1
print("WF92_READONLY_CHAIN_PRECHECK_EXIT="+str(code),flush=True)
time.sleep(3)
raise SystemExit(code)
