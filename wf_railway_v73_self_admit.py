"""WF V73: one private-R2 book, self-directed LEARN admission ONLY.

This real Python process follows WF's own source selection and structural
checks, not an assistant-selected title, chapter, genre or quote. It never
pretends a local chapter parser equals reader-first literary learning.

Actual autonomous literary training is blocked unless WF has an independently
connected, budgeted LEARN model and an immutable R2 progress/evidence journal.
Those capabilities are not configured on this Railway service today.

No model requests, original text logging, remote R2 writes or public uploads.
"""
from __future__ import annotations
import json,os,sys,time,types
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg

def report(value):
    print(json.dumps(value,ensure_ascii=False,sort_keys=True),flush=True)

print("WF_V73_SELF_OWNED_LEARN_ADMISSION_STARTED",flush=True)
def main():
    reader=os.getenv("WF_API_TOKEN")
    if not reader:
        report({"status":"WF_V73_READ_TOKEN_UNAVAILABLE",
                "network_attempted":False})
        return 1
    # Even though Railway owns a R2 index writer token, literary admission
    # may not write records and has no authority to promote source-derived
    # index facts to WF literary experience.
    os.environ.pop("WF_INDEX_UPLOAD_TOKEN",None)
    try:
        from writerforge.bulk_inbox import BulkCatalog
        from writerforge.private_reading_remote import WFPrivateReadingClient
        from writerforge.private_r2_sql_smoke import (
            candidate_sources,download_one_verified,
        )
        from writerforge.wf_self_learning_admission import admit_source
        client=WFPrivateReadingClient(
            endpoint="https://wf-r2-api.3227482831.workers.dev",timeout=60)
        with TemporaryDirectory(prefix="wf-v73-learn-admission-") as workdir:
            root=Path(workdir)
            catalog=BulkCatalog(root/"metadata.sqlite3")
            try:
                info=client.inventory_to_catalog(catalog)
                if info["all_folders_complete"] is not True:
                    raise RuntimeError("WF_V73_R2_DISCOVERY_INCOMPLETE")
                source=candidate_sources(catalog)[0]
                report({
                    "status":"WF_V73_SELF_SOURCE_SELECTED",
                    "assistant_selected_book":False,
                    "source_genre_not_declared_by_examiner":True,
                    "candidate_count":len(candidate_sources(catalog)),
                    "real_private_source_text_logged":False,
                })
                raw_file=root/"source.txt"
                transferred=download_one_verified(client,source,raw_file)
                admitted=admit_source(
                    raw_file,original_key=source["object_key"],
                    verified_original_sha256=transferred["source_sha256"],
                    downloaded_size=transferred["bytes"],
                    source_etag=source["etag"],
                )
                admitted.update({
                    "actual_WF_model_connection_available":False,
                    "writer_secret_disabled_for_this_process":True,
                    "original_txt_stays_private":True,
                    "only_one_book_admitted":True,
                    "source_bytes_read_for_preflight":transferred["bytes"],
                    "remote_source_writes":0,
                    "source_rewritten":False,
                    "source_or_title_printed":False,
                    "Railway_temp_source_survives_process":False,
                    "new_literary_skill_verified":False,
                })
                report(admitted)
                return 0
            finally:
                catalog.close()
    except Exception as err:
        value=str(err)
        if not value.startswith((
            "WF_ADMISSION_","WF_V73_","WF_PRIVATE_",
            "WF_V71_","WF_R2_HTTP_","BULK_")):
            value="WF_V73_UNEXPECTED_ADMISSION_FAILURE"
        report({
           "status":"WF_V73_SELF_OWNED_ADMISSION_STOPPED",
           "code":value,"learned_chapters":0,
           "novel_text_or_token_logged":False,
           "model_calls":0,"r2_writes":0,
        })
        return 1

result=main()
print("WF_V73_ADMISSION_EXIT="+str(result),flush=True)
time.sleep(6)
raise SystemExit(result)
