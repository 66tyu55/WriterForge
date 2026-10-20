"""V87.1: recheck PRECOMMITTED R2 random sources as contiguous excerpts.

No paid inference or R2 writes. Reads only the pre-pinned metadata candidate
order: two genre-folder hints, max four source candidates per hint. The
training work and the old V81 heldout work are excluded by full source SHA.
No author/model/GPT sees unpublished passages. Output is metadata-only.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json,os,sys,time

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
for n in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
          "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(n,None)

def emit(obj):
    print(json.dumps(obj,ensure_ascii=False,sort_keys=True),flush=True)

def fail(code):
    raise ValueError(code)

def main():
    if not os.getenv("WF_API_TOKEN"):
        emit({"status":"WF87_READER_NOT_CONFIGURED",
              "paid_calls":0,"r2_writes":0})
        return 1
    from writerforge.bulk_inbox import BulkCatalog
    from writerforge.private_reading_remote import WFPrivateReadingClient
    from writerforge.private_r2_sql_smoke import download_one_verified
    from writerforge.wf_charset_byte_review import byte_charset_audit
    from writerforge.v87_contiguous_passage import choose_passage
    from writerforge.v87_random_holdout import (
        metadata_only_plan,inventory_metadata_only,
        recover_key_by_sha,chapter_order,sha,canonical,MAX_SOURCE_BYTES,
    )
    from writerforge.v87_frozen_random_draw import (
        PLAN_SHA256,CATALOG_SHA256,SEED_SHA256,FROZEN_DRAWS,
        EXCLUDE_ALREADY_USED_SOURCE_SHA256,
    )
    statuses=[]
    total_read=0
    accepted=[]
    with TemporaryDirectory(prefix="wf87-random-holdout-") as tmp:
        root=Path(tmp)
        catalog=BulkCatalog(root/"catalog.sqlite3")
        try:
            reader=WFPrivateReadingClient(
                endpoint="https://wf-r2-api.3227482831.workers.dev",
                timeout=80)
            meta=inventory_metadata_only(reader,catalog)
            plan=metadata_only_plan(catalog)
            if (plan["plan_sha256"]!=PLAN_SHA256 or
                plan["frozen_catalog_sha256"]!=CATALOG_SHA256 or
                plan["draw_seed_sha256"]!=SEED_SHA256 or
                tuple((d["genre_hint"],tuple(
                    d["predeclared_fallback_key_sha256"]))
                    for d in plan["draws"])!=FROZEN_DRAWS):
                fail("WF87_DRAW_CHANGED_AFTER_PRECOMMIT")
            emit({"status":"WF87_FROZEN_ANONYMOUS_DRAW_READBACK_VERIFIED",
                  "metadata_plan_sha256":PLAN_SHA256,
                  "eligible_count":plan["eligible_source_count"],
                  "sampled_genres":[x[0] for x in FROZEN_DRAWS],
                  "source_bytes_downloaded_so_far":0,
                  "model_calls":0,"r2_writes":0})
            for genre,candidate_hashes in FROZEN_DRAWS:
                attempts=[]
                winner=None
                for candidate_i,anonymous_key_sha in enumerate(
                        candidate_hashes,1):
                    record={"genre_hint":genre,
                            "candidate_index":candidate_i,
                            "anonymous_key_sha256":anonymous_key_sha}
                    target=root/f"source-{len(statuses)+1}.txt"
                    try:
                        row=recover_key_by_sha(catalog,anonymous_key_sha)
                        if (row["category"]!=genre or
                            row["size_bytes"]>MAX_SOURCE_BYTES):
                            fail("WF87_PINNED_CANDIDATE_SCOPE_OR_SIZE_CHANGED")
                        saved=download_one_verified(reader,row,target)
                        total_read+=saved["bytes"]
                        if saved["source_sha256"] in EXCLUDE_ALREADY_USED_SOURCE_SHA256:
                            fail("WF87_OLD_TRAINED_OR_HELDOUT_BOOK_EXCLUDED")
                        if any(x["original_sha256"]==saved["source_sha256"]
                               for x in accepted):
                            fail("WF87_DUPLICATE_BOOK_ACROSS_SELECTED_GENRES")
                        charset=byte_charset_audit(
                            target,
                            expected_source_sha256=saved["source_sha256"],
                            expected_size=saved["bytes"],
                            expected_key_sha256=anonymous_key_sha)
                        if charset["plausible_distinct_decoded_texts"]!=1:
                            fail("WF87_SOURCE_DECODING_AMBIGUOUS")
                        codecs=charset["unique_reading_codec_aliases"]
                        codec=next((c for c in (
                            "gb18030","utf-8-sig","utf-8") if c in codecs),None)
                        if codec is None:
                            fail("WF87_SOURCE_DECODING_UNSUPPORTED")
                        raw=target.read_bytes()
                        decoded=raw.decode(codec,"strict")
                        if decoded.encode(codec,"strict")!=raw:
                            fail("WF87_PASSAGE_ENCODING_ROUNDTRIP_CHANGED")
                        # V87.1 deliberately drops the chapter-boundary
                        # requirement; this is a passage experiment ONLY.
                        selection=choose_passage(
                            decoded,key_sha256=anonymous_key_sha,
                            source_sha256=saved["source_sha256"])
                        del raw,decoded
                        record.update({
                            "status":"ACCEPTED_SOURCE_VERIFIED",
                            "original_sha256":saved["source_sha256"],
                            "original_bytes":saved["bytes"],
                            "original_encoding_reversibly_checked":True,
                            "chapter_identity_verified":False,
                            "holdout":selection,
                        })
                        winner=record
                        attempts.append(record)
                        break
                    except Exception as e:
                        code=str(e)
                        if not code.startswith(("WF87_","WF_V71_",
                            "WF_CHARSET_","WF_PREFIX_","WF_PRIVATE_")):
                            code="WF87_PRIVATE_SOURCE_STRUCTURE_REJECTED"
                        record.update({"status":"REJECTED_BY_FROZEN_GATE",
                                       "reason_code":code})
                        attempts.append(record)
                    finally:
                        target.unlink(missing_ok=True)
                item={"genre_folder_hint":genre,
                      "attempts":attempts,
                      "accepted":winner is not None}
                statuses.append(item)
                if winner is not None:
                    accepted.append(winner)
            result={
                "format":"wf.v87.random-heldout-real-contiguous-passage.v1",
                "frozen_draw_plan_sha256":PLAN_SHA256,
                "r2_metadata_snapshot_sha256":CATALOG_SHA256,
                "sampled_genres":[x[0] for x in FROZEN_DRAWS],
                "target_two_distinct_works":2,
                "accepted_distinct_works":len(accepted),
                "all_source_shas_unique":len({
                    x["original_sha256"] for x in accepted})==len(accepted),
                "results":statuses,
                "total_r2_source_bytes_read":total_read,
                "new_model_calls":0,
                "r2_writes":0,
                "private_titles_object_paths_prose_logged":False,
                "reviewer_quality_grade":None,
                "literary_improvement_proven":False,
                "training_history_before_chapter16_intact":True,
                "future_source_exposed_to_wf_student":False,
            }
            result["receipt_sha256"]=sha(canonical(result))
            emit({"status":"WF87_RANDOM_PRIVATE_PASSAGE_AUDIT_COMPLETED",
                  "report":result})
            return 0 if len(accepted)==2 else 2
        finally:
            catalog.close()

print("WF87_RANDOM_SOURCE_VERIFY_STARTED",flush=True)
try:
    ret=main()
except Exception as e:
    code=str(e)
    if not code.startswith(("WF87_","WF_PRIVATE_","WF_V71_")):
        code="WF87_UNEXPECTED_READER_ONLY_ABORT"
    emit({"status":"WF87_RANDOM_SOURCE_VERIFY_FAILED",
          "reason_code":code,"model_calls":0,"r2_writes":0,
          "private_originals_not_logged":True})
    ret=1
print("WF87_RANDOM_SOURCE_VERIFY_EXIT="+str(ret),flush=True)
time.sleep(4)
raise SystemExit(ret)
