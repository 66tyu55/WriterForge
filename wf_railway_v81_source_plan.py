"""V81 WF fixed-source larger training plan, no model or R2 mutation.

WF examines already precommitted B00 Xianxia source and the next five
physical chapters via its own strict charset/heading parser, printing only
hash/size/unit counts. This reveals safe batch size BEFORE any paid call.
No full novel prose leaves R2/Railway, no GPT selection of source lines.
"""
from __future__ import annotations
import json,os,sys,time,types
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
for key in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(key,None)
pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg

B00_SHA="c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4"
SOURCE_KEY_SHA="370400053cded15ca89e3232e7be84b28aa20ca70542150138bef6201dc7cb22"
SOURCE_SHA="0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd"
SOURCE_BYTES=4009069

def emit(doc):print(json.dumps(doc,ensure_ascii=False,sort_keys=True),flush=True)

def main():
    if not os.getenv("WF_API_TOKEN"):
        emit({"status":"WF_V81_READER_TOKEN_MISSING","model_calls":0})
        return 1
    try:
        from writerforge.bulk_inbox import BulkCatalog
        from writerforge.private_reading_remote import WFPrivateReadingClient
        from writerforge.private_r2_sql_smoke import download_one_verified
        from writerforge.wf_batch_supervisor import frozen_preselection
        from writerforge.wf_charset_byte_review import byte_charset_audit
        from writerforge.wf_self_learning_admission import _scan_document
        from writerforge.wf_b01_prefix_prepare import _split_into_ordered_units
        endpoint="https://wf-r2-api.3227482831.workers.dev"
        with TemporaryDirectory(prefix="wf-v80-prebudget-") as folder:
            root=Path(folder)
            catalog=BulkCatalog(root/"catalog.sqlite3")
            try:
                client=WFPrivateReadingClient(endpoint=endpoint)
                inventory=client.inventory_to_catalog(catalog)
                if not inventory["all_folders_complete"]:
                    raise ValueError("WF_V81_INVENTORY_UNVERIFIED")
                choices,receipt=frozen_preselection(catalog)
                if receipt["preselection_digest_sha256"]!=B00_SHA:
                    raise ValueError("WF_V81_FROZEN_COHORT_CHANGED")
                row=choices["仙侠"][0]
                if (sha256(row["object_key"].encode("utf8")).hexdigest()!=SOURCE_KEY_SHA
                    or row["size_bytes"]!=SOURCE_BYTES):
                    raise ValueError("WF_V81_ORIGINAL_OBJECT_SWITCHED")
                source=root/"original.txt"
                dl=download_one_verified(client,row,source)
                if dl["source_sha256"]!=SOURCE_SHA:
                    raise ValueError("WF_V81_SOURCE_BYTES_CHANGED")
                plausible=byte_charset_audit(
                    source,expected_source_sha256=SOURCE_SHA,
                    expected_size=SOURCE_BYTES,expected_key_sha256=SOURCE_KEY_SHA)
                if plausible["plausible_distinct_decoded_texts"]!=1 or (
                    "gb18030" not in plausible["unique_reading_codec_aliases"]
                ):
                    raise ValueError("WF_V81_CHARSET_UNVERIFIED")
                chapters,scan=_scan_document(source,"gb18030")
                if scan["boundary_rule_disagreements"] or (
                    scan["duplicate_printed_numbers"]):
                    raise ValueError("WF_V81_CHAPTER_BOUNDARIES_CHANGED")
                counts=[]
                with source.open("r",encoding="gb18030",errors="strict",newline=None) as f:
                    for ch in chapters[6:12]:
                        f.seek(ch.start_cookie)
                        lines=[]
                        while f.tell()<ch.end_cookie:
                            lines.append(f.readline())
                        body="".join(lines)
                        if sha256(body.encode()).hexdigest()!=ch.body_sha256:
                            raise ValueError("WF_V81_CHAPTER_SOURCE_SHA_CHANGED")
                        units=_split_into_ordered_units(body)
                        counts.append({
                           "chapter":ch.ordinal,
                           "printed_chapter":ch.printed_number,
                           "body_characters":ch.body_characters,
                           "chapter_sha256":ch.body_sha256,
                           "source_units":len(units),
                           "min_unit_characters":min(map(len,units)),
                           "max_unit_characters":max(map(len,units)),
                           "all_units_exactly_reconstruct_original":True,
                        })
                emit({
                  "status":"WF_V81_LARGE_BATCH_SOURCE_PLAN_VERIFIED",
                  "frozen_selection_sha256":B00_SHA,
                  "file_sha256":SOURCE_SHA,
                  "total_detected_chapters":len(chapters),
                  "inspected_next_chapters":counts,
                  "first_chapter_to_train":7,
                  "last_chapter_to_train":12,
                  "previous_finished_chapters":6,
                  "previous_cas_batch_pointer":
                      "f606f5216f82fd40a7893cfe8942e2454efe94b9f1389110bdc37f19f3a4f227",
                  "requested_batch_ceiling_input_plus_output_tokens":150000,
                  "existing_V80_journal_sha256":
                      "0b24a62a697b11e140477225728375fc406cd035fe921ad8ca5476b48a674240",
                  "original_text_in_log":False,
                  "model_calls":0,"r2_writes":0,
                })
                return 0
            finally:catalog.close()
    except Exception as exc:
        code=str(exc)
        if not code.startswith(("WF_V81_","WF_PRIVATE_",
                 "WF_V71_","WF_CHARSET_","WF_PREFIX_","BULK_")):
            code="WF_V81_PREBUDGET_PLAN_UNEXPECTED_ERROR"
        emit({"status":"WF_V81_LARGE_BATCH_PLAN_FAILED","error_code":code,
              "paid_calls":0,"r2_writes":0,"source_logged":False})
        return 1

print("WF_V81_SOURCE_PLAN_STARTED",flush=True)
code=main()
print("WF_V81_SOURCE_PLAN_EXIT="+str(code),flush=True)
time.sleep(5)
raise SystemExit(code)
