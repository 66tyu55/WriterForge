"""V71 offline synthetic regressions on the *real* Railway Python runtime.

No production R2 reads, no stored novel source, no paid model or Actions.
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
module=types.ModuleType("writerforge")
module.__path__=[str(ROOT/"writerforge")]
module.__package__="writerforge"
sys.modules["writerforge"]=module
print("WF_V71_REAL_PYTHON_SYNTHETIC_REGRESSION_STARTED",flush=True)
suite=unittest.TestSuite()
for pattern in (
    "test_v68_bulk_inbox.py",
    "test_v69_private_reading.py",
    "test_v70_private_reading_topology.py",
    "test_v71_private_r2_sql_smoke.py",
):
    suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/"tests"),
                  pattern=pattern))
run=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(suite)
print("WF_V71_SYNTHETIC_SUMMARY "+str({
    "tests":run.testsRun,"failures":len(run.failures),
    "errors":len(run.errors),"skipped":len(run.skipped),
    "passed":run.wasSuccessful(),"real_source_downloaded":False,
    "r2_operations":0,"model_calls":0,
}),flush=True)
time.sleep(8)
raise SystemExit(0 if run.wasSuccessful() else 1)
