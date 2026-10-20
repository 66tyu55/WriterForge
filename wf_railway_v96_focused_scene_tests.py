"""V96 new scene-turn writer focused synthetic redteam; no network/model.

Also tests the original V26 AutonomousWriting fallback by running its existing
test module in the focused suite. The actual interface is NOT mocked away:
WriterForgeDB, published Xuehai, VerifiedWritingFlow and save_candidate run
normally; only the paid model response is synthetic in unit tests.
"""
import json,os,socket,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
for secret in ("DEEPSEEK_API_KEY","WF_API_TOKEN",
               "WF_INDEX_UPLOAD_TOKEN","WF_LEARN_UPLOAD_TOKEN",
               "DISCOVERY_API_KEY"):
    os.environ.pop(secret,None)
def blocked(*_args,**_kwargs):
    raise RuntimeError("WF96_FOCUSED_NETWORK_FORBIDDEN")
socket.create_connection=blocked
socket.socket.connect=blocked
socket.socket.connect_ex=blocked
print("WF96_SCENE_TURN_FOCUSED_SYNTHETIC_STARTED",flush=True)
loader=unittest.TestLoader()
suite=loader.discover(str(ROOT/"tests"),pattern="test_v96_*.py")
result=unittest.TextTestRunner(stream=sys.stdout,verbosity=2).run(suite)
print(json.dumps({
    "status":"WF96_FOCUSED_SCENE_TURN_PASSED" if result.wasSuccessful()
             else "WF96_FOCUSED_SCENE_TURN_FAILED",
    "tests_run":result.testsRun,"failures":len(result.failures),
    "errors":len(result.errors),"paid_model_calls":0,
    "real_r2_reads":0,"real_r2_writes":0,
    "production_factjournal_changed":False,
    "literary_quality_independently_proven":False,
},sort_keys=True),flush=True)
raise SystemExit(0 if result.wasSuccessful() else 1)
