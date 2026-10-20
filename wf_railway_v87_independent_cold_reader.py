"""V87 independent process: R2 Reader reconstructs exact two random excerpts.

Read-only and no paid LLM. The examiner does not accept the training
process's claimed source units: it downloads both originals again, hashes
their raw bytes, independently decodes them, and recomputes source-selected
offsets and visible/future unit hashes from the frozen seed.
No original sentence or private R2 path is printed.
"""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import json,os,sys,time

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
for name in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
             "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(name,None)

def emit(value):
    print(json.dumps(value,ensure_ascii=False,sort_keys=True),flush=True)

def main():
    if not os.getenv("WF_API_TOKEN"):
        emit({"status":"WF87_COLD_READER_TOKEN_MISSING",
              "model_calls":0,"r2_writes":0})
        return 1
    from writerforge.bulk_inbox import BulkCatalog
    from writerforge.private_reading_remote import WFPrivateReadingClient
    from writerforge.private_r2_sql_smoke import download_one_verified
    from writerforge.wf_charset_byte_review import byte_charset_audit
    from writerforge.v87_random_holdout import (
        metadata_only_plan,inventory_metadata_only,recover_key_by_sha,
    )
    from writerforge.v87_frozen_random_draw import (
        PLAN_SHA256,CATALOG_SHA256,FROZEN_DRAWS,
    )
    from writerforge.v87_pinned_random_cases import (
        FROZEN_CASES,FIRST_AUDIT_RECEIPT_SHA256,
    )
    from writerforge.v87_contiguous_passage import choose_passage
    validated=[]
    total_bytes=0
    with TemporaryDirectory(prefix="wf87-cold-exam-") as tmp:
        root=Path(tmp)
        catalog=BulkCatalog(root/"catalog.sqlite3")
        try:
            client=WFPrivateReadingClient(
                endpoint="https://wf-r2-api.3227482831.workers.dev",
                timeout=80)
            inventory_metadata_only(client,catalog)
            current=metadata_only_plan(catalog)
            if (current["plan_sha256"]!=PLAN_SHA256 or
                current["frozen_catalog_sha256"]!=CATALOG_SHA256 or
                len(FROZEN_CASES)!=2):
                raise ValueError("WF87_COLD_EXAM_DRAW_CHANGED")
            allowed={genre:set(candidates)
                     for genre,candidates in FROZEN_DRAWS}
            for i,reference in enumerate(FROZEN_CASES):
                genre=reference["genre_hint"]
                key_sha=reference["source_key_sha256"]
                if key_sha not in allowed.get(genre,set()):
                    raise ValueError("WF87_COLD_EXAM_KEY_NOT_FROZEN")
                row=recover_key_by_sha(catalog,key_sha)
                if row["category"]!=genre:
                    raise ValueError("WF87_COLD_EXAM_GENRE_SCOPE_CHANGED")
                path=root/f"cold-{i}.txt"
                fresh=download_one_verified(client,row,path)
                total_bytes+=fresh["bytes"]
                if (fresh["source_sha256"]!=reference["source_sha256"]
                    or fresh["bytes"]!=reference["bytes"]):
                    raise ValueError("WF87_COLD_EXAM_ORIGINAL_SHA_CHANGED")
                codecs=byte_charset_audit(
                    path,expected_source_sha256=reference["source_sha256"],
                    expected_size=reference["bytes"],
                    expected_key_sha256=key_sha)
                if codecs["plausible_distinct_decoded_texts"]!=1:
                    raise ValueError("WF87_COLD_EXAM_CHARSET_AMBIGUOUS")
                aliases=codecs["unique_reading_codec_aliases"]
                codec=next((c for c in ("gb18030","utf-8-sig","utf-8")
                            if c in aliases),None)
                if codec is None:
                    raise ValueError("WF87_COLD_EXAM_CODEC_NOT_CONFIRMED")
                raw=path.read_bytes()
                text=raw.decode(codec,"strict")
                if text.encode(codec,"strict")!=raw:
                    raise ValueError("WF87_COLD_EXAM_BYTE_ROUNDTRIP_FAILED")
                proof=choose_passage(
                    text,key_sha256=key_sha,
                    source_sha256=fresh["source_sha256"])
                for field in ("fragment_start_char","fragment_end_char",
                    "fragment_sha256","fragment_unit_count",
                    "first_read_visible_unit_sha256",
                    "sealed_unread_unit_sha256"):
                    if proof.get(field)!=reference[field]:
                        raise ValueError("WF87_COLD_EXAM_PASSAGE_FINGERPRINT_CHANGED")
                if proof["precise_chapter_identity_verified"] is not False:
                    raise ValueError("WF87_COLD_EXAM_FAKE_FULL_CHAPTER")
                validated.append({
                    "genre_hint":genre,
                    "source_key_sha256":key_sha,
                    "source_sha256":fresh["source_sha256"],
                    "fragment_sha256":proof["fragment_sha256"],
                    "visible_unit_hashes_recomputed":2,
                    "sealed_future_unit_hash_recomputed":True,
                    "original_bytes_verified":fresh["bytes"],
                    "model_or_prose_logged":False,
                })
                del text,raw,proof
                path.unlink(missing_ok=True)
            emit({
                "status":"WF87_INDEPENDENT_R2_TWO_RANDOM_PASSAGES_VERIFIED",
                "prior_initial_source_receipt_sha256":FIRST_AUDIT_RECEIPT_SHA256,
                "frozen_random_draw_sha256":PLAN_SHA256,
                "accepted_cases":validated,
                "source_original_sha_distinct":
                  len({x["source_sha256"] for x in validated})==2,
                "all_original_source_sha_recomputed":True,
                "r2_bytes_read_by_examiner":total_bytes,
                "r2_writer_secret_present":False,
                "paid_model_calls":0,
                "r2_writes":0,
                "student_has_not_seen_hidden_unit":True,
                "independent_literary_semantic_grader_executed":False,
                "novel_titles_prose_and_keys_logged":False,
                "graduation_unmodified":True,
            })
            return 0
        finally:
            catalog.close()

print("WF87_INDEPENDENT_COLD_READER_STARTED",flush=True)
try:
    status=main()
except Exception as e:
    code=str(e)
    if not code.startswith(("WF87_","WF_PRIVATE_","WF_V71_")):
        code="WF87_INDEPENDENT_COLD_READER_UNEXPECTED_FAILURE"
    emit({
        "status":"WF87_INDEPENDENT_R2_RANDOM_PASSAGES_FAILED",
        "error_code":code,"model_calls":0,"r2_writes":0,
        "no_original_or_secret_logged":True,
    })
    status=1
print("WF87_INDEPENDENT_COLD_READER_EXIT="+str(status),flush=True)
time.sleep(4)
raise SystemExit(status)
