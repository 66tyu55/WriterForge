"""Railway real Python V73 synthetic admission regression; no user texts/R2."""
from __future__ import annotations
import os,sys,time,types,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg
print("WF_V73_SELF_LEARN_OFFLINE_TEST_STARTED",flush=True)
testfiles=[
 "test_v68_bulk_inbox.py",
 "test_v69_private_reading.py",
 "test_v70_private_reading_topology.py",
 "test_v71_private_r2_sql_smoke.py",
 "test_v71_encoding_guard.py",
 "test_v72_r2_index_vault.py",
 "test_v73_wf_self_learning_admission.py",
]
s=unittest.TestSuite()
for f in testfiles:
    s.addTests(unittest.defaultTestLoader.discover(
       str(ROOT/"tests"),pattern=f))
r=unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(s)
print("WF_V73_SELF_LEARN_OFFLINE_RESULT "+str({
   "tests":r.testsRun,
   "errors":len(r.errors),"failures":len(r.failures),
   "success":r.wasSuccessful(),
   "real_r2_reads":0,"r2_writes":0,
   "model_calls":0,"literary_learning_claimed":False,
}),flush=True)
time.sleep(6)
raise SystemExit(0 if r.wasSuccessful() else 1)
