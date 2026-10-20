"""V92 one-shot incremental R2 CAS migration of prior chapters 1..14.

REUSE old paid source reading and CH15 V91 CAS, never call a model. Before
writing, independently verify the COMPLETE old fifteen-object predecessor
chain and a PRE-PINNED manifest SHA obtained from a separate reader-only run.
Write fourteen new immutable Chinese experience records, then manifest LAST.
Every CAS write immediately reads back exact bytes. An interrupted run may
be manually reconciled/repeated: CAS contents are idempotent and old V82
batch/journal/experience records never change. No automatic paid retry.
"""
from __future__ import annotations
import json,os,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT);sys.path.insert(0,str(ROOT))
os.environ.pop("DEEPSEEK_API_KEY",None)
os.environ.pop("DISCOVERY_API_KEY",None)
os.environ.pop("WF_LEARN_UPLOAD_TOKEN",None)
ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
FROZEN_MANIFEST_SHA="bd905ae9e812fb5283f24ed7fec3bc35cf0febde7b6405476c455bba468f84db"

def emit(doc):
    print(json.dumps(doc,ensure_ascii=False,sort_keys=True),flush=True)


def main():
    for key in ("WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN"):
        if not os.getenv(key):
            emit({"status":"WF92_EXISTING_R2_SECRET_NOT_CONFIGURED",
                  "credential_name":key,"model_calls":0})
            return 1
    from writerforge.v79_provisional_r2_cas_journal import WFProvisionalR2CASJournal
    from writerforge.v92_experience_chain import (
        walk_v80_chain,make_manifest,verify_manifest,canonical,sha,
        V82_FINAL_BATCH,V82_FINAL_JOURNAL,ORIGINAL_V80_HEAD,
        V91_CH15_CAS,V91_CH15_MANIFEST,SOURCE_SHA,CHAPTERS)
    from writerforge.v91_private_cas_manifest import validate_experience_manifest
    journal=None
    saved=[]
    manifest_saved=None
    try:
        journal=WFProvisionalR2CASJournal(endpoint=ENDPOINT)
        journal.require_writer_ready()
        batch=json.loads(journal._get_content(V82_FINAL_BATCH).decode("utf8"))
        journal_raw=journal._get_content(V82_FINAL_JOURNAL)
        if (batch.get("last_completed_chapter")!=CHAPTERS or
            batch.get("source_sha256")!=SOURCE_SHA or
            batch.get("latest_experience_sha256")!=ORIGINAL_V80_HEAD or
            batch.get("journal_checkpoint_sha256")!=V82_FINAL_JOURNAL or
            batch.get("mastery_graduation_approved") is not False or
            not journal_raw):
            raise ValueError("WF92_WRITER_OLD_V82_ANCHOR_CHANGED")
        rows,new_objects=walk_v80_chain(journal._get_content)
        raw_manifest=canonical(make_manifest(rows))
        if (len(rows)!=CHAPTERS or
            sha(raw_manifest)!=FROZEN_MANIFEST_SHA):
            raise ValueError("WF92_PRECOMMITTED_FIFTEEN_MANIFEST_SHA_CHANGED")
        v91_15=journal._get_content(V91_CH15_CAS)
        if v91_15!=new_objects[15]:
            raise ValueError("WF92_PREVIOUS_CH15_V91_FULL_TEXT_CHANGED")
        validate_experience_manifest(
            manifest_raw=journal._get_content(V91_CH15_MANIFEST),
            migrated_raw=v91_15)
        emit({
            "status":"WF92_R2_WRITER_ALL_FIFTEEN_OLD_ORIGINALS_VERIFIED",
            "preflight_manifest_sha256":FROZEN_MANIFEST_SHA,
            "chapters_to_migrate_incrementally":list(range(1,15)),
            "reused_chapter15_v91_sha256":V91_CH15_CAS,
            "new_model_calls":0,
            "private_book_or_experience_not_logged":True,
        })
        for chapter in range(1,15):
            raw=new_objects[chapter]
            expected=rows[chapter-1]["v91_experience_cas_sha256"]
            if sha(raw)!=expected:
                raise ValueError("WF92_MIGRATED_CHINESE_BYTES_CHANGED")
            actual,created=journal._put_content(raw)
            if actual!=expected or journal._get_content(actual)!=raw:
                raise ValueError("WF92_CHAPTER_CAS_READBACK_INVALID")
            saved.append({
                "chapter":chapter,
                "v91_experience_sha256":actual,
                "new_object_created":bool(created),
                "legacy_cas_untouched":True,
            })
            emit({
                "status":"WF92_ONE_PRIOR_CHAPTER_EXPERIENCE_CAS_SAVED",
                "chapter":chapter,
                "new_v91_cas_sha256":actual,
                "created":bool(created),
                "original_v80_sha256":
                    rows[chapter-1]["original_v80_cas_sha256"],
                "real_paid_model_calls":0,
                "original_book_prose_or_chinese_experience_logged":False,
            })
        if len(saved)!=14:
            raise ValueError("WF92_NOT_ALL_PRIOR_CHAPTERS_SAVED")
        actual_manifest_sha,created_manifest=journal._put_content(
            raw_manifest)
        if (actual_manifest_sha!=FROZEN_MANIFEST_SHA or
            journal._get_content(actual_manifest_sha)!=raw_manifest):
            raise ValueError("WF92_MANIFEST_LAST_REMOTE_SHA_MISMATCH")
        manifest_saved=actual_manifest_sha
        # A successful same-process readback does NOT replace the later
        # completely independent cold Reader verification.
        report=verify_manifest(raw_manifest,journal._get_content)
        if (report["verified_chapters"]!=15 or
            report["verified_v91_experiences"]!=15):
            raise ValueError("WF92_ALL_FIFTEEN_COLD_RECHECK_MISSING")
        emit({
            "status":"WF92_COMPLETE_FIFTEEN_CHINESE_EXPERIENCES_VERSIONED_R2",
            "frozen_full_chain_manifest_sha256":actual_manifest_sha,
            "manifest_new_object_created":bool(created_manifest),
            "prior_fourteen_chapters":saved,
            "old_v80_chapter15_experience_sha256":ORIGINAL_V80_HEAD,
            "existing_v91_chapter15_sha256":V91_CH15_CAS,
            "versioned_chapter_count":15,
            "all_old_chapter_bytes_immutable":True,
            "old_chapter1_mixed_training_flag_preserved":True,
            "single_process_readback_passed":True,
            "cross_process_reader_confirmation_pending":True,
            "new_r2_object_count_at_most":15,
            "new_paid_model_calls":0,
            "full_factjournal_sqlite_graph_included":False,
            "literary_quality_independently_verified":False,
            "no_private_original_or_reflection_logged":True,
        })
        return 0
    except Exception as exc:
        reason=str(exc)
        if not reason.startswith(("WF92_","WF91_","WF_V79_",
                                  "WF_INDEX_","WF_LEARN_")) or len(reason)>115:
            reason="WF92_INCREMENTAL_MIGRATION_UNCLASSIFIED"
        emit({
            "status":"WF92_MIGRATION_PAUSED_KEEP_ALL_PREVIOUS_CAS",
            "reason_code":reason,
            "completed_new_version_objects":saved,
            "last_completed_manifest_sha256":manifest_saved,
            "original_v82_objects_never_overwritten":True,
            "resume_only_after_manual_readonly_audit":True,
            "model_calls":0,"no_private_text_logged":True,
        })
        return 1

print("WF92_INCREMENTAL_FOURTEEN_CAS_MIGRATION_STARTED",flush=True)
code=main()
print("WF92_INCREMENTAL_FOURTEEN_CAS_MIGRATION_EXIT="+str(code),flush=True)
time.sleep(3)
raise SystemExit(code)
