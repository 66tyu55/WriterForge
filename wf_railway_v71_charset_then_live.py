"""One-shot V71: strict synthetic encoding tests, THEN one bounded R2 index.

The actual source is read by WF's Railway Python process via user's
authenticated Worker, never by ChatGPT or GitHub Actions. Output shows only
machine evidence and counts; no source text, key or query term.
"""
from __future__ import annotations
import json
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

def emit(obj):
    print(json.dumps(obj,ensure_ascii=False,sort_keys=True),flush=True)

print("WF_V71_CHARSET_GATE_AND_REAL_SQL_STARTED",flush=True)
def main():
    cases=unittest.TestSuite()
    for pattern in ("test_v68_bulk_inbox.py",
                    "test_v69_private_reading.py",
                    "test_v70_private_reading_topology.py",
                    "test_v71_private_r2_sql_smoke.py",
                    "test_v71_encoding_guard.py"):
        cases.addTests(unittest.defaultTestLoader.discover(
            str(ROOT/"tests"),pattern=pattern))
    tests=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(cases)
    emit({"status":"WF_V71_STRICT_ENCODING_TEST_GATE",
          "cases":tests.testsRun,"failures":len(tests.failures),
          "errors":len(tests.errors),"passed":tests.wasSuccessful(),
          "actual_r2_requests_during_tests":0})
    if not tests.wasSuccessful():
        return 1
    if not os.getenv("WF_API_TOKEN"):
        emit({"status":"WF_V71_TOKEN_MISSING_AFTER_TESTS",
              "r2_request_attempted":False})
        return 1
    try:
        from writerforge.private_r2_sql_smoke import index_one_real_source
        def progress(s):
            emit({"status":s,"raw_source_or_key_logged":False})
        report=index_one_real_source(
            "https://wf-r2-api.3227482831.workers.dev",progress=progress)
        emit({"status":"WF_V71_REAL_R2_ONE_SOURCE_INDEXED_TEMPORARILY",
              **report})
        return 0
    except Exception as exc:
        error=str(exc)
        if not error.startswith((
            "WF_V71_","WF_PRIVATE_","WF_V70_",
            "BULK_","WF_R2_HTTP_")):
            error="WF_V71_UNEXPECTED_ERROR"
        emit({"status":"WF_V71_REAL_R2_SOURCE_INDEX_FAILED",
              "error_code":error,
              "source_or_private_key_logged":False})
        return 1

code=main()
print("WF_V71_ENCODING_RUN_EXIT="+str(code),flush=True)
time.sleep(8)
raise SystemExit(code)
