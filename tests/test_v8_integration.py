import unittest
from writerforge.scheduler import SkillScheduler, Priority
from writerforge.voice import fingerprint, audit
from writerforge.memory import MemoryBudget, MemoryRecord, MemoryTier
from writerforge.reviewers import reviewer_payload
from writerforge.integration_gate import evaluate_integration

class V8IntegrationTests(unittest.TestCase):
    def test_sentence_drafting_never_runs_p2_p3(self):
        d = SkillScheduler().drafting_decision("sentence_accepted", budget=8)
        forbidden = {
            "deep_continuity","causality_audit","character_audit",
            "reader_experience_review","reviewer_board","full_book_audit",
            "cross_work_compare","memory_compression","structural_rewrite_impact"
        }
        self.assertFalse(forbidden & set(d.selected))

    def test_scene_boundary_gets_p2_but_not_p3(self):
        d = SkillScheduler().boundary_decision("scene_boundary", budget=30)
        self.assertIn("deep_continuity", d.selected)
        self.assertIn("causality_audit", d.selected)
        self.assertNotIn("full_book_audit", d.selected)

    def test_draft_budget_is_bounded(self):
        d = SkillScheduler().drafting_decision("dependency_invalidated", budget=8)
        self.assertLessEqual(d.total_cost, 8)

    def test_voice_drift_is_warning_not_auto_rewrite(self):
        base = "他走到门边。雨很轻。屋里没人说话。"
        cand = "他飞快地、猛烈地、不可思议地冲到了门口！！！为什么会这样？？？"
        out = audit(base, cand, threshold=0.05)
        self.assertTrue(out["drift"])
        self.assertEqual(out["action"], "review_only")

    def test_memory_budget_prefers_current_and_unresolved(self):
        records = [
            MemoryRecord("archive", MemoryTier.ARCHIVE, "old", relevance=10),
            MemoryRecord("scene", MemoryTier.L1_SCENE, "current", relevance=1),
            MemoryRecord("promise", MemoryTier.L4_CANON, "open", relevance=1, unresolved=True),
        ]
        picked = MemoryBudget().select(records, max_items=2)
        keys = {r.key for r in picked}
        self.assertIn("promise", keys)
        self.assertIn("scene", keys)

    def test_reader_reviewer_is_isolated(self):
        available = {
            "text":"正文",
            "canon":"秘密真相",
            "future_plan":"结局",
            "author_intent_explanation":"作者解释"
        }
        payload = reviewer_payload("reader", available)
        self.assertEqual(payload, {"text":"正文"})

    def test_integration_gate_rejects_latency_regression(self):
        r = evaluate_integration(
            quality_before=0.7, quality_after=0.75,
            latency_before=1.0, latency_after=1.5,
            error_before=0.2, error_after=0.1,
            max_latency_regression=0.2
        )
        self.assertFalse(r.accepted)

    def test_integration_gate_accepts_measurable_gain(self):
        r = evaluate_integration(
            quality_before=0.70, quality_after=0.74,
            latency_before=1.0, latency_after=1.1,
            error_before=0.20, error_after=0.12
        )
        self.assertTrue(r.accepted)

if __name__ == "__main__":
    unittest.main()
