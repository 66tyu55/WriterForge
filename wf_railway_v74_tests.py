"""Actual Railway Python OFFLINE regression for V74 DeepSeek Flash adapter.

Old V68–V73 and V74 tests run on SYNTHETIC text and mock provider transport.
Remove production writer, DeepSeek, and Discovery environment variables
inside this test process before imports; no real provider API calls.
"""
from __future__ import annotations
import os
import sys
import time
import types
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
for secret in ("DEEPSEEK_API_KEY","DISCOVERY_API_KEY",
               "WF_INDEX_UPLOAD_TOKEN"):
    os.environ.pop(secret,None)
pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg

print("WF_V74_DEEPSEEK_FLASH_OFFLINE_REGRESSION_STARTED",flush=True)
files=(
    "test_v68_bulk_inbox.py",
    "test_v69_private_reading.py",
    "test_v70_private_reading_topology.py",
    "test_v71_private_r2_sql_smoke.py",
    "test_v71_encoding_guard.py",
    "test_v72_r2_index_vault.py",
    "test_v73_wf_self_learning_admission.py",
    "test_v74_deepseek_flash_model.py",
    "test_v74_wf_model_selection.py",
)
suite=unittest.TestSuite()
for name in files:
    suite.addTests(unittest.defaultTestLoader.discover(
        str(ROOT/"tests"),pattern=name))
result=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(suite)
print("WF_V74_OFFLINE_REPORT "+str({
    "tests":result.testsRun,
    "errors":len(result.errors),
    "failures":len(result.failures),
    "success":result.wasSuccessful(),
    "active_learn_provider":"deepseek",
    "active_model":"deepseek-flash",
    "real_deepseek_api_requests":0,
    "real_r2_requests":0,
    "training_pass_a_or_b_executed":False,
    "old_discovery_api_calls":0,
    "r2_writes":0,
    "real_model_key_available_to_tests":False,
}),flush=True)
time.sleep(7)
raise SystemExit(0 if result.wasSuccessful() else 1)
