"""Real Python offline regression runner for V68/V69/V70 on Railway.

All content is SYNTHETIC. No real R2, models, user originals or GitHub
Actions. The earlier V69 failure/success receipts are not overwritten.
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
pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg
print("WF_V70_OFFLINE_REGRESSION_STARTED",flush=True)
tests=unittest.TestSuite()
for name in ("test_v68_bulk_inbox.py","test_v69_private_reading.py",
             "test_v70_private_reading_topology.py"):
    tests.addTests(unittest.defaultTestLoader.discover(
        str(ROOT/"tests"),pattern=name))
result=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(tests)
print("WF_V70_OFFLINE_SUMMARY "+str({
  "tested":result.testsRun,"failures":len(result.failures),
  "errors":len(result.errors),"skipped":len(result.skipped),
  "success":result.wasSuccessful(),
  "real_r2_requests":0,"literary_model_calls":0,
  "private_source_bytes_loaded":0,"r2_writes":0,
}),flush=True)
time.sleep(8)
raise SystemExit(0 if result.wasSuccessful() else 1)
