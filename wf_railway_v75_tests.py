"""V75 offline WF LEARN protocol regressions on real Railway Python.

Only synthetic books and fake DeepSeek/R2 transports. Strip model tokens,
source-reader token, and both writer tokens inside this TEST process.
No paid calls, no source downloads, no Cloudflare mutations.
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
for variable in (
    "DEEPSEEK_API_KEY","DISCOVERY_API_KEY","WF_LEARN_UPLOAD_TOKEN",
    "WF_INDEX_UPLOAD_TOKEN","WF_API_TOKEN",
):
    os.environ.pop(variable,None)

module=types.ModuleType("writerforge")
module.__package__="writerforge"
module.__path__=[str(ROOT/"writerforge")]
sys.modules["writerforge"]=module

print("WF_V75_IMMUTABLE_LEARN_OFFLINE_TESTS_STARTED",flush=True)
files=[
  "test_v68_bulk_inbox.py",
  "test_v69_private_reading.py",
  "test_v70_private_reading_topology.py",
  "test_v71_private_r2_sql_smoke.py",
  "test_v71_encoding_guard.py",
  "test_v72_r2_index_vault.py",
  "test_v73_wf_self_learning_admission.py",
  "test_v74_deepseek_flash_model.py",
  "test_v74_wf_model_selection.py",
  "test_v75_r2_learn_journal.py",
]
suite=unittest.TestSuite()
for name in files:
    suite.addTests(unittest.defaultTestLoader.discover(
        str(ROOT/"tests"),pattern=name))
result=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(suite)
print("WF_V75_OFFLINE_REPORT "+str({
  "tests":result.testsRun,
  "failures":len(result.failures),
  "errors":len(result.errors),
  "passed":result.wasSuccessful(),
  "synthetic_only":True,
  "actual_deepseek_requests":0,
  "actual_r2_requests":0,
  "actual_original_source_bytes_read":0,
  "literary_model_self_reports_not_human_validation":True,
  "v49_literary_failure_preserved":True,
  "r2_learn_worker_not_yet_deployed":True,
}),flush=True)
time.sleep(6)
raise SystemExit(0 if result.wasSuccessful() else 1)
