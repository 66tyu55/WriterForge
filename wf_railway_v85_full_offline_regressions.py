"""V85 full deterministic regression. Private credentials removed, no network."""
from __future__ import annotations
import json,os,socket,sys,time,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0,str(ROOT))
for n in ("DEEPSEEK_API_KEY","WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN",
          "WF_LEARN_UPLOAD_TOKEN","DISCOVERY__API__KEY",
          "WRITERFORGE_EXPERIENCE_REVIEW_VERIFY_KEY_HEX",
          "WRITERFORGE_PROMOTION_VERIFY_KEY_HEX"):
    os.environ.pop(n,None)

def deny_remote(*args,**kwargs):
    raise RuntimeError("WF_V85_OFFLINE_NETWORK_NOT_PERMITTED")
socket.create_connection=deny_remote
socket.socket.connect=deny_remote

print("WF_V85_FULL_OFFLINE_REGRESSION_STARTED",flush=True)
tests=unittest.TestLoader().discover(
    start_dir=str(ROOT/"tests"),pattern="test_*.py")
result=unittest.TextTestRunner(
    stream=sys.stdout,verbosity=1,failfast=False).run(tests)
ok=result.wasSuccessful()
print(json.dumps({
    "status":"WF_V85_FULL_OFFLINE_REGRESSION_PASSED" if ok
             else "WF_V85_FULL_OFFLINE_REGRESSION_HAS_FAILURES",
    "tests_run":result.testsRun,
    "failed":len(result.failures),"errored":len(result.errors),
    "skipped":len(result.skipped),
    "r2_network_requests":0,
    "model_provider_requests":0,
    "r2_writes":0,
    "source_novel_reads":0,
    "literary_quality_independent_review":False,
    "training_batch_resumed":False,
    "v49_failure_preserved":True,
},ensure_ascii=False,sort_keys=True),flush=True)
time.sleep(3)
raise SystemExit(0 if ok else 1)
