"""V95 execute native Cloudflare Worker JavaScript CAS test offline in Railway.

No HTTP network, provider calls or real R2. Node must exist; if missing,
report UNTESTED and fail instead of pretending the Worker was validated.
"""
from pathlib import Path
import json,os,shutil,subprocess,sys,socket
ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
for key in ("DEEPSEEK_API_KEY","WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN",
            "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(key,None)
def forbidden(*_args,**_kwargs):
    raise RuntimeError("WF95_NO_EXTERNAL_NETWORK_IN_NODE_TEST")
socket.create_connection=forbidden
socket.socket.connect=forbidden
node=shutil.which("node")
if not node:
    print(json.dumps({"status":"WF95_NATIVE_JS_WORKER_UNTESTED_NODE_MISSING",
                      "tests_run":0,"model_calls":0,"r2_writes":0}),
          flush=True)
    raise SystemExit(2)
print(json.dumps({"status":"WF95_NODE_WORKER_CONDITIONAL_HEAD_STARTED",
                  "node_binary_found":True,"model_calls":0}),
      flush=True)
try:
    proc=subprocess.run(
        [node,"--test","tests/v95_worker_conditional_head.test.mjs"],
        cwd=ROOT,capture_output=True,text=True,timeout=90,
        env={k:v for k,v in os.environ.items()
             if k not in ("WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN",
                          "DEEPSEEK_API_KEY")})
    # Only synthetic failure descriptions are in the native test.
    print((proc.stdout or "")[-18000:],flush=True)
    print((proc.stderr or "")[-4500:],flush=True)
    rc=proc.returncode
except subprocess.TimeoutExpired:
    print("WF95_NODE_TEST_EXCEEDED_90_SECONDS",flush=True)
    rc=3
print(json.dumps({"status":"WF95_WORKER_ATOMIC_CONDITIONAL_TESTS_PASSED"
                  if rc==0 else "WF95_WORKER_ATOMIC_CONDITIONAL_TESTS_FAILED",
                  "process_exit":rc,"paid_model_calls":0,
                  "real_cloudflare_worker_modified":False,
                  "r2_network_requests":0,"r2_writes":0}),flush=True)
raise SystemExit(0 if rc==0 else 1)
