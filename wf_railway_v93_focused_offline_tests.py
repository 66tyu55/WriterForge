"""V93 focused SQLite/R2-CAS synthetic integration regressions only."""
from __future__ import annotations
import json,os,socket,sys,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
for k in ("DEEPSEEK_API_KEY","WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN",
          "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(k,None)
def blocked(*args,**kwargs):
    raise RuntimeError("WF93_FOCUSED_NETWORK_FORBIDDEN")
socket.create_connection=blocked
socket.socket.connect=blocked
print("WF93_OFFLINE_FOCUSED_TESTS_STARTED",flush=True)
suite=unittest.TestLoader().discover(
    str(ROOT/"tests"),pattern="test_v93_*.py")
result=unittest.TextTestRunner(stream=sys.stdout,verbosity=2).run(suite)
print(json.dumps({
    "status":"WF93_OFFLINE_FOCUSED_PASSED" if result.wasSuccessful()
             else "WF93_OFFLINE_FOCUSED_FAILED",
    "tests_run":result.testsRun,
    "failures":len(result.failures),"errors":len(result.errors),
    "model_calls":0,"r2_network_reads":0,"r2_writes":0,
    "production_graph_migrated":False,
},sort_keys=True),flush=True)
raise SystemExit(0 if result.wasSuccessful() else 1)
