"""V60 OBSERVATIONAL diagnostic probes, not acceptance tests.

All inputs synthetic. These tests intentionally confirm CURRENT architecture
gaps, not literary improvement; a green result means the gap was reproduced.
Do not rewrite historical V49 evidence, make model calls or access private R2.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import sqlite3
import unittest
from unittest.mock import patch

from writerforge.db import WriterForgeDB
from writerforge.evolution import (
    CapabilityContract, EvolutionEngine, PromotionEvidence,
    SkillRegistry, UpgradeCandidate
)
from writerforge.feedback import FeedbackStore
from writerforge.verified_flow import VerifiedWritingFlow


class V60ArchitectureDiagnostics(unittest.TestCase):

    def test_source_retrieval_changes_receipt_but_not_creative_prompt(self):
        # Use the REAL VerifiedWritingFlow.prepare(), no HTTP/model call.
        # Isolate the external dependencies so only prompt assembly is tested.
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.execute("CREATE TABLE accepted_prose("
                           "project_id TEXT,scope_id TEXT,body TEXT,"
                           "updated_at TEXT)")
        flow = VerifiedWritingFlow.__new__(VerifiedWritingFlow)
        flow.db = SimpleNamespace(conn=connection)
        flow.project_id = "synthetic_project"
        flow.runtime = SimpleNamespace(require=lambda _:None,
                                       pinned_snapshot_id=1)
        flow.begin_draft = lambda scene_id, **kw: SimpleNamespace(
            companion=SimpleNamespace(guidance=()))
        variants = [
            {"entry_id":1,"work_id":"synthetic_one","location":[1,1,1],
             "function":"dialogue","effect":"unknown"},
            {"entry_id":2,"work_id":"synthetic_two","location":[1,2,1],
             "function":"environment","effect":"unknown"}
        ]
        try:
            with patch("writerforge.verified_flow.ProseStyleStore") as style:
                style.return_value.load.return_value = None
                flow.xuehai = SimpleNamespace(query=lambda _: [variants[0]])
                first = flow.prepare("scene01","synthetic scene goal")
                flow.xuehai = SimpleNamespace(query=lambda _: [variants[1]])
                second = flow.prepare("scene01","synthetic scene goal")
            self.assertNotEqual(first.evidence,second.evidence)
            self.assertEqual(first.prompt_sha256,second.prompt_sha256)
            self.assertNotIn("synthetic_one",first.prompt)
            self.assertNotIn("synthetic_two",second.prompt)
        finally:
            connection.close()

    def test_promoter_accepts_self_asserted_metrics_without_proof(self):
        # In-memory registry ONLY. A fabricated numeric object is enough for
        # this low-level API; this is NOT evidence of network exploitability.
        reg = SkillRegistry()
        reg.register(CapabilityContract(
            "synthetic_craft",1,"synthetic baseline contract"))
        engine = EvolutionEngine(registry=reg)
        claim = PromotionEvidence(
            capability_statement="Synthetic asserted transfer improvement",
            heldout_success=1.0,transfer_success=1.0,
            regression_success=1.0,judge_stability=1.0,
            repeated_failure_reduction=1.0,runtime_regression=0.0,
            human_anchor_count=0)
        result=engine.apply_upgrade(UpgradeCandidate(
            skill="synthetic_craft",new_level=2,
            capability_statement="Synthetic unverified promotion",
            evidence_id="synthetic_unverified_receipt",
            evidence=claim,requires_human_anchor=False),
            policy="gated_auto")
        self.assertEqual(result,[])
        self.assertEqual(reg.get("synthetic_craft").level,2)

    def test_feedback_convergence_is_not_reader_authentication(self):
        # Two arbitrary caller-provided names appear as two distinct readers.
        # Do not interpret this as genuine independent reader evidence.
        with TemporaryDirectory() as tmp:
            db=WriterForgeDB(Path(tmp)/"synthetic.db")
            try:
                store=FeedbackStore(db,"synthetic_project")
                for name in ("unverified_reader_a","unverified_reader_b"):
                    store.add(reader_id=name,chapter_ref="chapter01",
                              category="continuity_concern",
                              comment="synthetic-only observation",severity=1)
                report=store.triage()
                self.assertIn("continuity_concern",
                              report["convergent_signals"])
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
