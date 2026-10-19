"""V81 independent R2-reader-only restoration of blind two-arm comparison.

The training/comparison process writes a precommitted control/exposure order
and each model response as immutable content-addressed CAS objects. This
examiner must read all three by SHA using ONLY WF_API_TOKEN; it independently
recomputes the first two held-out units from a different private R2 work,
verifies model-response JSON and exact source hashes, and recomputes the
paired comparison. Cannot read API billing platform or judge literary truth.

PAIR_SHA must be pinned from the genuine first run before executing.
"""
from __future__ import annotations

import json,os,sys,time,types
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
for key in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
            "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(key,None)
pkg=types.ModuleType("writerforge")
pkg.__package__="writerforge"
pkg.__path__=[str(ROOT/"writerforge")]
sys.modules["writerforge"]=pkg

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
B00_SHA="c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4"
TRAINED_SOURCE_SHA="0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd"
TRAINED_EXPERIENCE_SHA="feee04808c6b14f84c16989d98b031937a897395f3d008c43e17b3449f9077e3"

PAIR_SHA="TO_BE_PINNED_FROM_ACTUAL_RESULT"


def emit(doc):
    print(json.dumps(doc,ensure_ascii=False,sort_keys=True),flush=True)


print("WF_V81_BLIND_DIFFERENT_BOOK_INDEPENDENT_EXAM_START",flush=True)


def main():
    if not os.getenv("WF_API_TOKEN"):
        emit({"status":"WF_V81_BLIND_EXAM_READER_MISSING",
              "model_calls":0,"r2_writes":0})
        return 1
    try:
        from writerforge.bulk_inbox import BulkCatalog
        from writerforge.private_reading_remote import WFPrivateReadingClient
        from writerforge.private_r2_sql_smoke import download_one_verified
        from writerforge.wf_batch_supervisor import frozen_preselection
        from writerforge.wf_charset_byte_review import byte_charset_audit
        from writerforge.v79_provisional_r2_cas_journal import (
            WFProvisionalR2CASJournal)
        from writerforge.v81_transfer_probe import (
            prepare_heldout,validate_model_proposal,compare_arms,canonical)

        if len(PAIR_SHA)!=64:
            raise ValueError("WF_V81_BLIND_EXAM_PAIR_SHA_NOT_PINNED")
        reader=WFProvisionalR2CASJournal(
            endpoint=ENDPOINT,read_only=True)
        if reader.writer is not None:
            raise ValueError("WF_V81_BLIND_EXAM_WRITER_LEAK")
        paired=json.loads(reader._get_content(PAIR_SHA))
        if paired.get("format")!="wf.exam.paired-contrast.v81":
            raise ValueError("WF_V81_BLIND_EXAM_WRONG_RESULT_FORMAT")
        pc=paired["precommit_sha256"]
        plan=json.loads(reader._get_content(pc))
        if (plan.get("format")!="wf.exam.precommit.v81" or
            plan.get("trained_original_sha256")!=TRAINED_SOURCE_SHA or
            plan.get("trained_experience_sha256")!=TRAINED_EXPERIENCE_SHA or
            plan.get("source_complete_book_not_trained") is not True):
            raise ValueError("WF_V81_BLIND_EXAM_NOT_PRECOMMITTED")
        with TemporaryDirectory(prefix="wf-v81-blind-reader-") as tmp:
            cat=BulkCatalog(Path(tmp)/"metadata.sqlite3")
            try:
                r2=WFPrivateReadingClient(endpoint=ENDPOINT)
                inv=r2.inventory_to_catalog(cat)
                if inv.get("all_folders_complete") is not True:
                    raise ValueError("WF_V81_BLIND_EXAM_INVENTORY_PARTIAL")
                selected,freeze=frozen_preselection(cat)
                if freeze["preselection_digest_sha256"]!=B00_SHA:
                    raise ValueError("WF_V81_BLIND_EXAM_B00_CHANGED")
                record=selected["历史"][0]
                file=Path(tmp)/"holdout.txt"
                received=download_one_verified(r2,record,file)
                key_hash=sha256(record["object_key"].encode("utf8")).hexdigest()
                status=byte_charset_audit(
                    file,expected_source_sha256=received["source_sha256"],
                    expected_size=received["bytes"],expected_key_sha256=key_hash)
                if status["plausible_distinct_decoded_texts"]!=1:
                    raise ValueError("WF_V81_BLIND_EXAM_AMBIGUOUS_DECODING")
                codec=next((c for c in
                    ("gb18030","utf-8-sig","utf-8") if
                    c in status["unique_reading_codec_aliases"]),None)
                if codec is None:
                    raise ValueError("WF_V81_BLIND_EXAM_DECODER_NOT_SUPPORTED")
                units,proof=prepare_heldout(
                    file,original_sha=received["source_sha256"],
                    source_key_sha=key_hash,encoding=codec,
                    trained_experience_sha=TRAINED_EXPERIENCE_SHA)
                if plan.get("holdout")!=proof:
                    raise ValueError("WF_V81_BLIND_EXAM_HELDOUT_NOT_THE_SAME")
                arms={}
                for name in ("baseline","experience"):
                    sha=paired.get(name+"_record_sha256")
                    entry=json.loads(reader._get_content(sha))
                    if (entry.get("format")!="wf.exam.arm.v81" or
                        entry.get("arm")!=name or
                        entry.get("precommit_sha256")!=pc or
                        entry.get("source_sha256")!=received["source_sha256"] or
                        entry.get("trained_experience_sha256")!=
                        TRAINED_EXPERIENCE_SHA):
                        raise ValueError("WF_V81_BLIND_EXAM_ARM_RECORD_FORGED")
                    result=entry.get("raw_model_proposal")
                    check=validate_model_proposal(
                        result,source_units=units)
                    if check!=entry.get("technical_schema_validation"):
                        raise ValueError("WF_V81_BLIND_EXAM_FALSE_SCHEMA_RECEIPT")
                    arms[name]=result
                recomputed=compare_arms(
                    arms["baseline"],arms["experience"])
                if recomputed!=paired.get("comparison"):
                    raise ValueError("WF_V81_BLIND_EXAM_COMPARISON_MISMATCH")
                usage=paired.get("model_usage",{})
                if (usage.get("reserved_requests")!=2 or
                    usage.get("event_count")!=2 or
                    usage.get("model")!="deepseek-flash"):
                    raise ValueError("WF_V81_BLIND_EXAM_MODEL_USAGE_MISMATCH")
                emit({
                    "status":"WF_V81_BLIND_TRANSFER_R2_READER_EXAM_PASSED",
                    "paired_r2_cas_sha256":PAIR_SHA,
                    "precommitted_source_sha256":proof["original_sha256"],
                    "trained_experience_sha256":TRAINED_EXPERIENCE_SHA,
                    "same_two_unseen_source_units_both_arms":True,
                    "both_arm_cas_shas_verified":True,
                    "source_excerpt_shas_independently_matched":True,
                    "arm_order_was_precommitted":True,
                    "mechanical_comparison":recomputed,
                    "DeepSeek_calls_by_examiner":0,
                    "R2_writes_by_examiner":0,
                    "independent_literary_transfer_improvement_proven":False,
                    "content_of_original_or_model_answers_logged":False,
                })
                return 0
            finally:
                cat.close()
    except Exception as error:
        code=str(error)
        if not code.startswith(("WF_V81_","WF_INDEX_","WF_LEARN_",
            "WF_V79_","WF_PRIVATE_","WF_V71_","WF_CHARSET_",
            "WF_PREFIX_","BULK_")):
            code="WF_V81_BLIND_EXAM_UNEXPECTED_FAILURE"
        emit({"status":"WF_V81_BLIND_TRANSFER_INDEPENDENT_EXAM_FAILED",
              "error_code":code,"model_calls":0,
              "r2_writes":0,"private_text_or_keys_logged":False})
        return 1

exitcode=main()
print("WF_V81_BLIND_TRANSFER_EXAM_EXIT="+str(exitcode),flush=True)
time.sleep(6)
raise SystemExit(exitcode)
