"""Real Railway Python V76 independent batch supervisor tests, offline.

Uses only synthetic R2 metadata and fake model transports. All provider/R2
secrets stripped before any imports. Does NOT read the user's novels, issue
DeepSeek paid calls, or write any Cloudflare objects.
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
for name in ("WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN",
             "WF_LEARN_UPLOAD_TOKEN","DEEPSEEK_API_KEY",
             "DISCOVERY_API_KEY"):
    os.environ.pop(name,None)

pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg

print("WF_V76_EXAMINER_BATCH_TESTS_STARTED",flush=True)
tests=(
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
 "test_v76_wf_batch_supervisor.py",
 "test_v76_wf_api_usage_supervisor.py",
 "test_v78_wf_charset_byte_review.py",
 "test_v78_wf_b01_prefix.py",
 "test_v78_runner_phase_gates.py",
 "test_v79_provisional_r2_cas.py",
 "test_v80_150k_batch.py",
 "test_v80_independent_exam.py",
 "test_v81_independent_exam.py",
 "test_v81_transfer_probe.py",
 "test_v82_independent_exam.py",
)
suite=unittest.TestSuite()
for name in tests:
    suite.addTests(unittest.defaultTestLoader.discover(
        str(ROOT/"tests"),pattern=name))
result=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(suite)
print("WF_V76_EXAMINER_OFFLINE_REPORT "+str({
    "tests":result.testsRun,
    "failures":len(result.failures),
    "errors":len(result.errors),
    "skipped":len(result.skipped),
    "passed":result.wasSuccessful(),
    "model_calls":0,
    "source_read_from_real_r2":False,
    "real_r2_writes":0,
    "real_deepseek_calls":0,
    "graduation_unchanged":True,
}),flush=True)
time.sleep(6)
raise SystemExit(0 if result.wasSuccessful() else 1)
