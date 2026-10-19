"""V70 real Railway WF metadata-only source topology audit.

This process connects to the existing deployed V69 Cloudflare Worker using
the already configured Railway WF_API_TOKEN. It scans actual R2 metadata and
classifies nested file groups; never prints private keys or novel text, never
calls a model, never modifies R2 or creates durable SQL.
"""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import sys
import time
import types

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
wf=types.ModuleType("writerforge")
wf.__path__=[str(ROOT/"writerforge")]
wf.__package__="writerforge"
sys.modules["writerforge"]=wf

def publish(payload):
    print(json.dumps(payload,ensure_ascii=False,sort_keys=True),flush=True)

def main():
    if not os.environ.get("WF_API_TOKEN"):
        publish({"status":"WF_V70_TOKEN_UNAVAILABLE",
                 "remote_requests_attempted":False})
        return 1
    try:
        from writerforge.bulk_inbox import BulkCatalog
        from writerforge.private_reading_remote import WFPrivateReadingClient
        from writerforge.private_reading_topology import analyze_private_topology
        client=WFPrivateReadingClient(
            endpoint="https://wf-r2-api.3227482831.workers.dev")
        with TemporaryDirectory(prefix="wf-v70-topology-") as scratch:
            cat=BulkCatalog(Path(scratch)/"catalog.sqlite3")
            try:
                scan=client.inventory_to_catalog(cat)
                report=analyze_private_topology(
                    cat,complete=scan["all_folders_complete"])
            finally:
                cat.close()
        # Existing validated V69 results contain only aggregate values.
        publish({
            "status":"WF_V70_REMOTE_TOPOLOGY_COMPLETED",
            "transport":"WF_PYTHON_TO_CLOUDFLARE_WORKER_TO_PRIVATE_R2",
            "inventory":scan,
            "topology":report,
            "temporary_catalog_deleted_on_exit":True,
            "persistent_sql_indexes_created":0,
            "original_prose_returned":False,
            "private_file_names_returned":False,
            "r2_writes":0,
            "model_calls":0,
        })
        return 0
    except Exception as error:
        reason=str(error)
        if not reason.startswith(("WF_PRIVATE_","WF_V70_",
                                   "WF_R2_HTTP_","BULK_")):
            reason="WF_V70_UNEXPECTED_ERROR"
        publish({"status":"WF_V70_REMOTE_TOPOLOGY_FAILED",
                 "error_code":reason,"keys_logged":False,
                 "source_text_logged":False,"token_logged":False})
        return 1

print("WF_V70_REMOTE_TOPOLOGY_STARTED",flush=True)
status=main()
print("WF_V70_TOPOLOGY_EXIT="+str(status),flush=True)
time.sleep(8)
raise SystemExit(status)
