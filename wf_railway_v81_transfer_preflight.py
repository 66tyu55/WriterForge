"""V81 preflight the blind OTHER-WORK transfer comparison with zero model calls.

This source is selected deterministically from the PRE-REGISTERED B00
历史 list, first eligible TXT only (no selection from content or model
results). It has not been used to train the Xianxia learner. We verify
its original SHA, entire byte/charset plausibility, first chapter source
SHA and exactly two contiguous units before any DeepSeek call.

Note B00 historical source chapter numbers had parser conflicts, so this is
a *limited blind excerpt transfer probe*, NOT proof of a complete or
canonical history work; a text probe cannot be counted as trained chapters.
"""
from __future__ import annotations

import json,os,sys,time,types
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
for name in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
             "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(name,None)
pkg=types.ModuleType("writerforge")
pkg.__package__="writerforge"
pkg.__path__=[str(ROOT/"writerforge")]
sys.modules["writerforge"]=pkg

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
B00_SHA="c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4"
V81_EXPERIENCE_SHA="feee04808c6b14f84c16989d98b031937a897395f3d008c43e17b3449f9077e3"
SOURCE_TRAINING_SHA="0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd"


def emit(x):
    print(json.dumps(x,ensure_ascii=False,sort_keys=True),flush=True)


print("WF_V81_HELDOUT_HISTORY_PREFLIGHT_STARTED",flush=True)


def main():
    if not os.getenv("WF_API_TOKEN"):
        emit({"status":"WF_V81_TRANSFER_READER_UNAVAILABLE","model_calls":0})
        return 1
    try:
        from writerforge.bulk_inbox import BulkCatalog
        from writerforge.private_reading_remote import WFPrivateReadingClient
        from writerforge.private_r2_sql_smoke import download_one_verified
        from writerforge.wf_batch_supervisor import frozen_preselection
        from writerforge.wf_charset_byte_review import byte_charset_audit
        from writerforge.v81_transfer_probe import prepare_heldout
        from writerforge.v79_provisional_r2_cas_journal import WFProvisionalR2CASJournal

        reader=WFProvisionalR2CASJournal(
            endpoint=ENDPOINT,read_only=True)
        old=json.loads(reader._get_content(V81_EXPERIENCE_SHA))
        if (old.get("format")!="wf.learn.experience.v80" or
            old.get("source_sha256")!=SOURCE_TRAINING_SHA or
            old.get("chapter")!=10 or
            old.get("literary_quality_independently_verified") is not False):
            raise ValueError("WF_V81_TRANSFER_CH10_EXPERIENCE_INVALID")

        with TemporaryDirectory(prefix="wf-v81-unseen-") as folder:
            root=Path(folder)
            cat=BulkCatalog(root/"inventory.sqlite3")
            try:
                r2=WFPrivateReadingClient(endpoint=ENDPOINT)
                scan=r2.inventory_to_catalog(cat)
                if scan.get("all_folders_complete") is not True:
                    raise ValueError("WF_V81_TRANSFER_R2_INVENTORY_PARTIAL")
                shortlist,freeze=frozen_preselection(cat)
                if freeze["preselection_digest_sha256"]!=B00_SHA:
                    raise ValueError("WF_V81_TRANSFER_PRESELECTED_B00_CHANGED")
                options=shortlist["历史"]
                if not options:
                    raise ValueError("WF_V81_TRANSFER_NO_FROZEN_HISTORY_TXT")
                selected=options[0]
                key=selected["object_key"]
                key_hash=sha256(key.encode("utf8")).hexdigest()
                file=root/"holdout.txt"
                original=download_one_verified(r2,selected,file)
                if original["source_sha256"]==SOURCE_TRAINING_SHA:
                    raise ValueError("WF_V81_TRANSFER_TRAINING_SOURCE_LEAK")
                charset=byte_charset_audit(
                    file,expected_source_sha256=original["source_sha256"],
                    expected_size=original["bytes"],
                    expected_key_sha256=key_hash)
                aliases=charset["unique_reading_codec_aliases"]
                if charset["plausible_distinct_decoded_texts"]!=1:
                    raise ValueError("WF_V81_TRANSFER_MULTIPLE_DECODINGS")
                encoding=next((x for x in
                    ("gb18030","utf-8-sig","utf-8") if x in aliases),None)
                if encoding is None:
                    raise ValueError("WF_V81_TRANSFER_NO_SUPPORTED_DECODER")
                windows,prepared=prepare_heldout(
                    file,original_sha=original["source_sha256"],
                    source_key_sha=key_hash,encoding=encoding,
                    trained_experience_sha=V81_EXPERIENCE_SHA)
                assert len(windows)==2
                emit({
                    "status":"WF_V81_HELDOUT_DIFFERENT_BOOK_PRECOMMITTED",
                    "b00_frozen_selection_sha256":B00_SHA,
                    "source_kind_hint_only":"历史",
                    "file_full_sha256":original["source_sha256"],
                    "file_source_key_sha256":key_hash,
                    "file_source_bytes":original["bytes"],
                    "encoding_roundtrip_candidates":aliases,
                    "blind_excerpt_receipt":prepared,
                    "trained_source_is_different":True,
                    "reader_has_model_or_writer_keys":False,
                    "private_text_or_book_title_emitted":False,
                    "paid_deepseek_requests":0,
                    "r2_writes":0,
                    "literary_quality_certified":False,
                })
                return 0
            finally:
                cat.close()
    except Exception as error:
        reason=str(error)
        if not reason.startswith((
            "WF_V81_","WF_PRIVATE_","WF_V71_","WF_CHARSET_",
            "WF_ADMISSION_","WF_PREFIX_","WF_INDEX_","WF_V79_","BULK_",
        )):
            reason="WF_V81_TRANSFER_PREFLIGHT_UNEXPECTED_STOP"
        emit({"status":"WF_V81_HELDOUT_PREFLIGHT_PAUSED",
              "error_code":reason,
              "model_calls":0,"r2_writes":0,
              "source_or_token_logged":False})
        return 1

ret=main()
print("WF_V81_HELDOUT_PREFLIGHT_EXIT="+str(ret),flush=True)
time.sleep(6)
raise SystemExit(ret)
