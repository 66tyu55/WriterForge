"""V85 offline regression only. No paid model requests or remote R2 reads/writes."""
from __future__ import annotations
import json
import os
import socket
import sys
import time
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
for name in (
    "DEEPSEEK_API_KEY","WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN",
    "WF_LEARN_UPLOAD_TOKEN","DISCOVERY__API__KEY",
    "WRITERFORGE_EXPERIENCE_REVIEW_VERIFY_KEY_HEX",
    "WRITERFORGE_PROMOTION_VERIFY_KEY_HEX",
):
    os.environ.pop(name,None)

# V85 offline testing never requires connecting to a model or remote R2.
# Synthetic suites must not use HTTP even if a child fixture attempts it.
def _no_network(*args,**kwargs):
    raise RuntimeError("WF_V85_OFFLINE_OUTBOUND_NETWORK_BLOCKED")

socket.create_connection=_no_network
socket.socket.connect=_no_network

FILES=(
    "test_v85_literary_evidence_gate.py",
    "test_v85_pass_a_bridge.py",
    "test_v83_evidence_diagnostics.py",
    "test_v57_relation_foundation.py",
    "test_v59_global_ledger_clock.py",
    "test_v62_experience_negative_transfer.py",
    "test_v80_150k_batch.py",
    "test_v82_anchored_cas_restore.py",
)
suite=unittest.TestSuite()
loader=unittest.TestLoader()
for name in FILES:
    suite.addTests(loader.discover(str(ROOT/"tests"),pattern=name))
print("WF_V85_OFFLINE_TESTS_STARTED",flush=True)
result=unittest.TextTestRunner(verbosity=1,stream=sys.stdout).run(suite)
passed=result.wasSuccessful()
print(json.dumps({
    "status":"WF_V85_OFFLINE_REGRESSION_PASSED" if passed else
             "WF_V85_OFFLINE_REGRESSION_FAILED",
    "tests_run":result.testsRun,
    "failures":len(result.failures),"errors":len(result.errors),
    "model_calls":0,"r2_network_reads":0,"r2_writes":0,
    "old_v82_r2_object_mutated":False,
    "literary_quality_review_performed":False,
    "paid_next_batch_started":False,
    "v49_literary_graduation_status":"THIRD_STRIKE_FAILED",
},ensure_ascii=False,sort_keys=True),flush=True)
time.sleep(3)
raise SystemExit(0 if passed else 1)
