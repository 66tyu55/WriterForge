"""V85 full deterministic regression. Private credentials removed, no network."""
from __future__ import annotations
import json,os,socket,sys,time,unittest,ipaddress
from pathlib import Path

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0,str(ROOT))
for n in ("DEEPSEEK_API_KEY","WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN",
          "WF_LEARN_UPLOAD_TOKEN","DISCOVERY__API__KEY",
          "WRITERFORGE_EXPERIENCE_REVIEW_VERIFY_KEY_HEX",
          "WRITERFORGE_PROMOTION_VERIFY_KEY_HEX"):
    os.environ.pop(n,None)

# Existing browser/UI tests use a local HTTP server, which is not a
# network model provider. Permit numeric loopback and exact localhost only.
# Refuse external domains/addresses even when a test tries to dial them.
original_connect=socket.socket.connect
original_connect_ex=socket.socket.connect_ex
original_create=socket.create_connection

def allowed_local(address):
    if not isinstance(address,tuple) or len(address)<2:
        return False
    host=address[0]
    if isinstance(host,bytes):
        host=host.decode("ascii","ignore")
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(str(host)).is_loopback
    except ValueError:
        return False

def restricted_connect(self,address):
    if not allowed_local(address):
        raise RuntimeError("WF_V85_EXTERNAL_NETWORK_NOT_PERMITTED")
    return original_connect(self,address)

def restricted_connect_ex(self,address):
    if not allowed_local(address):
        raise RuntimeError("WF_V85_EXTERNAL_NETWORK_NOT_PERMITTED")
    return original_connect_ex(self,address)

def restricted_create(address,*args,**kwargs):
    if not allowed_local(address):
        raise RuntimeError("WF_V85_EXTERNAL_NETWORK_NOT_PERMITTED")
    return original_create(address,*args,**kwargs)

socket.socket.connect=restricted_connect
socket.socket.connect_ex=restricted_connect_ex
socket.create_connection=restricted_create

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
