"""V72: one-shot real Railway Python synthetic index-vault regression.

NO R2 or user originals accessed; no Cloudflare write permission configured;
the test fake simulates an R2 object store to verify that a fresh WF reader
can restore SQLite from published immutable chunks after the first process
exits. Do not replace a real remote write receipt with this test.
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
package=types.ModuleType("writerforge")
package.__path__=[str(ROOT/"writerforge")]
package.__package__="writerforge"
sys.modules["writerforge"]=package
print("WF_V72_PERSISTENT_R2_INDEX_SYNTHETIC_STARTED",flush=True)

suite=unittest.TestSuite()
for pat in (
  "test_v68_bulk_inbox.py",
  "test_v69_private_reading.py",
  "test_v70_private_reading_topology.py",
  "test_v71_private_r2_sql_smoke.py",
  "test_v71_encoding_guard.py",
  "test_v72_r2_index_vault.py",
):
    suite.addTests(unittest.defaultTestLoader.discover(
        str(ROOT/"tests"),pattern=pat))
result=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(suite)
print("WF_V72_SYNTHETIC_REPORT "+str({
   "tests":result.testsRun,"failed":len(result.failures),
   "errors":len(result.errors),"skipped":len(result.skipped),
   "passed":result.wasSuccessful(),"real_r2_writes":0,
   "real_r2_reads":0,"novel_text_logged":False,
   "new_worker_routes_deployed":False,
   "index_writer_token_configured":False,
   "railway_volume_created":False,
   "literary_models_called":0,
}),flush=True)
time.sleep(8)
raise SystemExit(0 if result.wasSuccessful() else 1)
