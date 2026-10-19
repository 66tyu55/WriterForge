"""V71 runtime-only diagnostic. NO R2 request, source, SQL or model."""
import json,os,sys,time
from pathlib import Path
root=Path(__file__).resolve().parent
report={
  "status":"WF_V71_BOOT_SANITY_OK",
  "python_version":sys.version.split()[0],
  "real_entry_exists":(root/"wf_railway_v71_one_source.py").is_file(),
  "runtime_module_exists":(root/"writerforge"/"private_r2_sql_smoke.py").is_file(),
  "auth_token_name_configured":bool(os.getenv("WF_API_TOKEN")),
  "network_attempted":False,
  "r2_writes":0,
  "user_text_read":False,
}
print(json.dumps(report,sort_keys=True),flush=True)
sys.stderr.write("WF_V71_DIAGNOSTIC_STDERR_MARKER\n")
sys.stderr.flush()
time.sleep(8)
raise SystemExit(0 if all((
    report["real_entry_exists"],report["runtime_module_exists"],
    report["auth_token_name_configured"])) else 1)
