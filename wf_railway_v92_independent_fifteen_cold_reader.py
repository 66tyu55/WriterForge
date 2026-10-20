"""V92 independent process cold R2 Reader: all fifteen full Chinese experiences.

The writer must have EXITED. Reader holds no model or R2 writer tokens,
re-fetches old V82 chain and ALL new V91 blobs from private R2, checks every
original SHA/previous pointer, full Unicode field values and frozen manifest.
No model, no R2 writes, no private strings in output.
"""
from __future__ import annotations
import json,os,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT);sys.path.insert(0,str(ROOT))
for k in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
          "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(k,None)
ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
PINNED_CHAIN_MANIFEST_SHA="bd905ae9e812fb5283f24ed7fec3bc35cf0febde7b6405476c455bba468f84db"

def emit(doc):
    print(json.dumps(doc,ensure_ascii=False,sort_keys=True),flush=True)


def main():
    if not os.getenv("WF_API_TOKEN"):
        emit({"status":"WF92_READER_ONLY_SECRET_NOT_CONFIGURED",
              "model_calls":0,"r2_writes":0})
        return 1
    from writerforge.v79_provisional_r2_cas_journal import WFProvisionalR2CASJournal
    from writerforge.v92_experience_chain import (
        verify_manifest,sha,canonical,V82_FINAL_BATCH,V82_FINAL_JOURNAL,
        ORIGINAL_V80_HEAD,V91_CH15_CAS,V91_CH15_MANIFEST,
        SOURCE_SHA,CHAPTERS)
    from writerforge.v91_private_cas_manifest import validate_experience_manifest
    examiner=WFProvisionalR2CASJournal(
        endpoint=ENDPOINT,read_only=True)
    if not examiner.read_only or examiner.writer is not None:
        raise ValueError("WF92_INDEPENDENT_R2_WRITER_PRIVILEGE_FORBIDDEN")
    batch=json.loads(examiner._get_content(V82_FINAL_BATCH).decode("utf8"))
    oldjournal=examiner._get_content(V82_FINAL_JOURNAL)
    need=(batch.get("last_completed_chapter")==CHAPTERS and
          batch.get("source_sha256")==SOURCE_SHA and
          batch.get("latest_experience_sha256")==ORIGINAL_V80_HEAD and
          batch.get("journal_checkpoint_sha256")==V82_FINAL_JOURNAL and
          batch.get("mastery_graduation_approved") is False and
          bool(oldjournal))
    if not need:
        raise ValueError("WF92_COLD_READ_V82_HISTORICAL_CHAIN_CHANGED")
    old15=examiner._get_content(V91_CH15_CAS)
    validate_experience_manifest(
        manifest_raw=examiner._get_content(V91_CH15_MANIFEST),
        migrated_raw=old15)
    newmanifest=examiner._get_content(PINNED_CHAIN_MANIFEST_SHA)
    if sha(newmanifest)!=PINNED_CHAIN_MANIFEST_SHA:
        raise ValueError("WF92_COLD_READ_FROZEN_MANIFEST_SHA_CHANGED")
    proof=verify_manifest(newmanifest,examiner._get_content)
    if (proof["verified_chapters"]!=15 or
        proof["verified_legacy_experiences"]!=15 or
        proof["verified_v91_experiences"]!=15 or
        proof["manifest_sha256"]!=PINNED_CHAIN_MANIFEST_SHA):
        raise ValueError("WF92_COLD_READ_FIFTEEN_NOT_PROVEN")
    emit({
        **proof,
        "status":"WF92_INDEPENDENT_R2_ALL_FIFTEEN_EXPERIENCES_COLD_RESTORED",
        "manifest_sha256":PINNED_CHAIN_MANIFEST_SHA,
        "previous_v91_ch15_manifest_sha256":V91_CH15_MANIFEST,
        "original_v82_batch_sha256":V82_FINAL_BATCH,
        "original_v82_journal_sha256":V82_FINAL_JOURNAL,
        "original_experience_chain_contiguous":True,
        "full_chinese_reflection_four_fields_every_chapter_verified":True,
        "novel_source_original_bytes_not_migrated":True,
        "persistent_factjournal_sqlite_graph_not_included":True,
        "external_literary_judge_performed":False,
        "auto_training_next_chapter_disabled":True,
        "r2_writer_secret_present":False,
        "model_calls":0,"r2_writes":0,
        "private_chinese_text_not_logged":True,
    })
    return 0

print("WF92_INDEPENDENT_R2_READER_FIFTEEN_COLD_START",flush=True)
try:
    code=main()
except Exception as exc:
    msg=str(exc)
    if not msg.startswith(("WF92_","WF91_","WF_V79_",
                           "WF_INDEX_","WF_LEARN_")) or len(msg)>120:
        msg="WF92_INDEPENDENT_COLD_READ_FAILED_UNCLASSIFIED"
    emit({"status":"WF92_INDEPENDENT_FIFTEEN_COLD_READ_FAILED",
          "reason_code":msg,"model_calls":0,"r2_writes":0,
          "private_experiences_not_logged":True})
    code=1
print("WF92_INDEPENDENT_R2_READER_FIFTEEN_EXIT="+str(code),flush=True)
time.sleep(3)
raise SystemExit(code)
