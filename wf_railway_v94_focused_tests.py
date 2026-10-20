"""V94 event-log rehearsal: focused synthetic tests, no external network."""
from pathlib import Path
import json,os,socket,sys,unittest

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
for key in ("DEEPSEEK_API_KEY","WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN",
            "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(key,None)

def forbidden(*args,**kwargs):
    raise RuntimeError("WF94_NO_OUTBOUND_NETWORK_IN_TESTS")

socket.create_connection=forbidden
socket.socket.connect=forbidden
socket.socket.connect_ex=forbidden
print("WF94_OFFLINE_EVENT_REPLAY_TESTS_STARTED",flush=True)
suite=unittest.TestLoader().discover(
    str(ROOT/"tests"),pattern="test_v94_*.py")
result=unittest.TextTestRunner(
    stream=sys.stdout,verbosity=2).run(suite)
print(json.dumps({
    "status":"WF94_OFFLINE_EVENT_REPLAY_TESTS_PASSED" if
        result.wasSuccessful() else "WF94_OFFLINE_EVENT_REPLAY_TESTS_FAILED",
    "tests_run":result.testsRun,
    "errors":len(result.errors),"failures":len(result.failures),
    "model_calls":0,"r2_reads":0,"r2_writes":0,
    "real_production_graph_touched":False,
},sort_keys=True),flush=True)
raise SystemExit(0 if result.wasSuccessful() else 1)
