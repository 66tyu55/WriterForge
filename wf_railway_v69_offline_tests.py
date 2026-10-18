"""One-shot REAL V69 Python unit tests on Railway, no R2, no book contents.

Not GitHub Actions. The tests are synthetic, and do not claim a real remote
private-reading scan or source understanding.
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
print("WF_V69_OFFLINE_REAL_PYTHON_TESTS_STARTED",flush=True)
suite=unittest.TestSuite()
loader=unittest.defaultTestLoader
for pattern in ("test_v68_bulk_inbox.py","test_v69_private_reading.py"):
    suite.addTests(loader.discover(str(ROOT/"tests"),pattern=pattern,
                                   top_level_dir=str(ROOT)))
res=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(suite)
print("WF_V69_OFFLINE_SUMMARY "+str({
    "tests_run":res.testsRun,
    "failures":len(res.failures),
    "errors":len(res.errors),
    "skipped":len(res.skipped),
    "passed":res.wasSuccessful(),
    "real_R2_requests":0,
    "real_originals_read":0,
    "model_calls":0,
    "remote_writes":0,
}),flush=True)
time.sleep(8)
raise SystemExit(0 if res.wasSuccessful() else 1)
