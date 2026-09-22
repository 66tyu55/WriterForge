import unittest
from writerforge import CraftEngine, CraftAuditor, CraftRequest, CraftGroup, SkillScheduler


class V11CraftEngineTests(unittest.TestCase):
    def test_router_never_selects_more_than_two_groups(self):
        plan = CraftEngine().plan(CraftRequest(
            needs=("dialogue","description","interiority","scene"),
            risks=("over_explain",),
            max_groups=9,
        ))
        self.assertLessEqual(len(plan.groups), 2)

    def test_dialogue_problem_routes_to_dialogue_action(self):
        plan = CraftEngine().plan(CraftRequest(needs=("dialogue",), risks=("empty_dialogue",)))
        self.assertIn(CraftGroup.DIALOGUE_ACTION, plan.groups)

    def test_interiority_loop_routes_to_cognitive_motion(self):
        plan = CraftEngine().plan(CraftRequest(risks=("cognitive_loop","interiority")))
        self.assertIn(CraftGroup.COGNITIVE_MOTION, plan.groups)

    def test_auditor_never_auto_rewrites(self):
        findings = CraftAuditor().audit(redundant_explanations=2, reflection_tail=True)
        self.assertTrue(findings)
        self.assertTrue(all(not f.auto_rewrite for f in findings))

    def test_no_turn_is_detected_from_structured_delta(self):
        findings = CraftAuditor().audit(scene_delta={})
        self.assertTrue(any(f.code == "NO_NARRATIVE_DELTA" for f in findings))

    def test_deliberate_static_scene_is_not_auto_failed(self):
        findings = CraftAuditor().audit(scene_delta={}, deliberate_static_scene=True)
        self.assertFalse(any(f.code == "NO_NARRATIVE_DELTA" for f in findings))

    def test_craft_router_is_not_always_on(self):
        d = SkillScheduler().drafting_decision("sentence_accepted", budget=8)
        self.assertNotIn("craft_router", d.selected)
        d2 = SkillScheduler().drafting_decision("dialogue_pressure", budget=8)
        self.assertIn("craft_router", d2.selected)

    def test_craft_auditor_requires_explicit_review_event(self):
        d = SkillScheduler().boundary_decision("scene_boundary", budget=30)
        self.assertNotIn("craft_auditor", d.selected)
        d2 = SkillScheduler().boundary_decision("craft_review", budget=30)
        self.assertIn("craft_auditor", d2.selected)


if __name__ == "__main__":
    unittest.main()
