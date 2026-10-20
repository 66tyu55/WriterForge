"""V95 REAL Python protocol redteam, no model/Cloudflare networking.

Includes connected V85 same-session sealed source + V89 exact quotes +
V86 independent (synthetic signed) review, as well as conditional head
concurrency simulation. Native JS Worker is a separate Node-only suite.
"""
from pathlib import Path
import json,os,socket,sys,unittest
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
for s in ("DEEPSEEK_API_KEY","WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN",
          "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(s,None)
def blocked(*_a,**_k):
    raise RuntimeError("WF95_PYTHON_OFFLINE_NETWORK_FORBIDDEN")
socket.create_connection=blocked
socket.socket.connect=blocked
socket.socket.connect_ex=blocked
print("WF95_TRUSTED_SOURCE_AND_HEAD_OFFLINE_PYTHON_START",flush=True)
suite=unittest.TestLoader().discover(
    str(ROOT/"tests"),pattern="test_v95_*.py")
result=unittest.TextTestRunner(stream=sys.stdout,verbosity=2).run(suite)
print(json.dumps({
    "status":"WF95_PYTHON_PROVENANCE_AND_CONCURRENCY_PASSED" if
             result.wasSuccessful() else "WF95_PYTHON_GATE_REGRESSION_FAILED",
    "tests_run":result.testsRun,"failures":len(result.failures),
    "errors":len(result.errors),
    "native_js_worker_tested_here":False,
    "live_conditional_head_worker_route_deployed":False,
    "production_fact_authority_granted":False,
    "model_calls":0,"r2_network_reads":0,"r2_writes":0,
},sort_keys=True),flush=True)
raise SystemExit(0 if result.wasSuccessful() else 1)
