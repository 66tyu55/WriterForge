"""V28 boundedness, +3 evidence and memory regression (synthetic only)."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import gc
import sqlite3
import tracemalloc
import unittest

from writerforge.reverse_craft import (
    ReverseCraftCoordinator, ReverseCraftError, _hash
)
from tests.test_v28_reverse_craft import (
    FakeR2, SyntheticTestAuthority, CORE, DRAFT, report
)
from writerforge.reverse_core_vault import ReverseCoreVault
from writerforge.r2_storage import R2Config


class LongRunningSyntheticRegression(unittest.TestCase):
    def test_evidence_counts_independent_contexts_not_retry_count(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            run=ReverseCraftCoordinator(root/"core.db","stress",create=True,
                                        scratch=root/"scratch")
            vault=ReverseCoreVault(
                R2Config(account_id="b"*32,bucket="writerforge-private-library",
                         access_key_id="synthetic",secret_access_key="synthetic"),
                client=FakeR2())
            authority=SyntheticTestAuthority()
            try:
                for i in range(1,10):
                    unit=run.open_unit(1,i if i<=6 else 6,  # third chapter for remaining
                                       _hash("source-"+str(i)),_hash("context-"+str(i))) if i<=6 else None
                    # Max per chapter is six: new chapter for 7+.
                    if i>=7:
                        unit=run.open_unit(2,i-6,_hash("source-"+str(i)),
                                           _hash("context-"+str(i)))
                    state=run.practice(
                        unit,DRAFT,writer="writer",report=report(),
                        core=CORE,fault="缺少角色认知与目的的联系",
                        hypothesis="该信息可能通过视角限制制造悬念",
                        authority=authority)
                    self.assertEqual(state,"PERSIST_PENDING")
                    self.assertEqual(run.checkpoint(unit,vault),"RETEST_READY")
                    self.assertEqual(run.retest(unit,DRAFT,writer="writer",
                                               report=report(94,transfer=True),
                                               authority=authority),
                                     "RETEST_PERSIST_PENDING")
                    self.assertEqual(run.checkpoint(unit,vault),"PASS")
                    if i%2==0:
                        run.open_pair_merge(unit-1)
                        self.assertEqual(run.merge(
                            unit-1,DRAFT,writer="writer",
                            report=report(91,transfer=True),
                            authority=authority,vault=vault),"MERGED_PASS")
                    state=run.conn.execute("SELECT tier FROM rc_cores").fetchone()[0]
                    if i==3:self.assertEqual(state,"recurrent_3")
                    if i==6:self.assertEqual(state,"retested_6")
                    if i==9:self.assertEqual(state,"generalized_9")
                self.assertEqual(run.conn.execute(
                    "SELECT COUNT(*) FROM rc_evidence").fetchone()[0],9)
                self.assertEqual(run.conn.execute(
                    "SELECT COUNT(*) FROM rc_cores").fetchone()[0],1)
            finally:
                run.close()

    def test_scratch_memory_peak_bounded_under_repetition(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            run=ReverseCraftCoordinator(root/"trial.db","ram",create=True,
                                        scratch=root/"scratch")
            try:
                tracemalloc.start()
                for _ in range(2000):
                    with run._ephemeral(DRAFT) as location:
                        self.assertTrue(location.is_file())
                    self.assertEqual(list((root/"scratch").iterdir()),[])
                gc.collect()
                current,peak=tracemalloc.get_traced_memory()
                tracemalloc.stop()
                # This is a synthetic transient-file memory bound, not an
                # exhaustive test of a real running language model.
                self.assertLess(current,2*1024*1024)
                self.assertLess(peak,8*1024*1024)
            finally:
                run.close()

    def test_no_evergrowing_units_or_unbounded_chapter_scope(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            run=ReverseCraftCoordinator(root/"trial.db","bounds",create=True,
                                        max_chapters=1, max_units_per_chapter=1)
            try:
                with self.assertRaises(ReverseCraftError):
                    run.open_unit(1,2,_hash("a"),_hash("b"))
                with self.assertRaises(ReverseCraftError):
                    run.open_unit(2,1,_hash("a"),_hash("b"))
                u=run.open_unit(1,1,_hash("a"),_hash("b"))
                with self.assertRaises(ReverseCraftError):
                    run.open_unit(1,1,_hash("c"),_hash("d"))
            finally:run.close()


if __name__ == "__main__":
    unittest.main()
