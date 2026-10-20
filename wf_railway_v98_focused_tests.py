"""V98 focused offline prose-driven causal rolling plan regressions.

Only synthetic WriterForgeDB / Xuehai and mocked localhost model replies.
No paid model, Cloudflare/R2 calls, production write acceptance or training.
"""
from __future__ import annotations
import os,socket,sys,json,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0,str(ROOT))
for key in ("WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN","DEEPSEEK_API_KEY",
            "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(key,None)
def forbidden(*args,**kwargs):
    raise RuntimeError("WF98_FOCUSED_NETWORK_FORBIDDEN")
socket.create_connection=forbidden
socket.socket.connect=forbidden
socket.socket.connect_ex=forbidden

print("WF98_ROLLING_WRITER_OFFLINE_TESTS_STARTED",flush=True)
suite=unittest.TestLoader().discover(
    str(ROOT/"tests"),pattern="test_v98_*.py")
result=unittest.TextTestRunner(stream=sys.stdout,verbosity=2).run(suite)
print(json.dumps({
    "status":"WF98_ROLLING_OFFLINE_TESTS_PASSED" if
              result.wasSuccessful() else "WF98_ROLLING_OFFLINE_TESTS_FAILED",
    "tests_run":result.testsRun,
    "failures":len(result.failures),
    "errors":len(result.errors),
    "skips":len(result.skipped),
    "real_model_calls":0,
    "r2_network_reads":0,"r2_writes":0,
    "literary_quality_independently_verified":False,
    "existing_wf_canon_changes":0,
},sort_keys=True),flush=True)
raise SystemExit(0 if result.wasSuccessful() else 1)
