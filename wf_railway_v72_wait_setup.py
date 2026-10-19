"""V72 safe idle after local-only regression. No network, no cloud mutations."""
from __future__ import annotations
import json,os,sys,time
from pathlib import Path
root=Path(__file__).resolve().parent
script_ready=(root/"writerforge"/"r2_index_vault.py").is_file()
ready=bool(os.getenv("WF_INDEX_UPLOAD_TOKEN")) and bool(os.getenv("WF_API_TOKEN"))
print(json.dumps({
  "status":"WF_V72_AWAITING_OWNER_R2_INDEX_WRITER_SETUP",
  "r2_index_client_file_present":script_ready,
  "read_token_name_configured":bool(os.getenv("WF_API_TOKEN")),
  "separate_writer_token_name_configured":bool(os.getenv("WF_INDEX_UPLOAD_TOKEN")),
  "cloudflare_worker_routes_verified_live":False,
  "index_written_to_real_r2":False,
  "network_attempted":False,
  "originals_downloaded":0,
  "cloudflare_mutations":0,
  "railway_volume_created":False,
  "token_values_printed":False,
  "automatic_retries":False,
},sort_keys=True),flush=True)
time.sleep(6)
raise SystemExit(0 if script_ready else 1)
