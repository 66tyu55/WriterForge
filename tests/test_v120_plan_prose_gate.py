"""V120: the model's story plan is not evidence that the story happened."""
import hashlib
import json
import inspect
import unittest

from writerforge.v120_plan_prose_gate import (
    compare_plan_to_prose, pending_dependency_hint, PlanExecutionError,
)

CAST = ("沈砚", "唐蜃")
BITE_AND_SPIT = (
    "沈砚把火髓果往齿间一咬。"
    "沈砚把那枚果子从齿间吐到左手心。"
)


def cell(domain, entity, predicate, value):
    key = json.dumps([domain, entity, predicate, "author_plan", None],
                     ensure_ascii=False, separators=(",", ":"))
    return {key: value}


def beat(goal, actor="沈砚", kind="action", parent=None, id="t01"):
    return dict(id=id, kind=kind, actor=actor, goal=goal,
                causal_parent=parent, craft_focus=[])


def audit(goal, prose=BITE_AND_SPIT, *, actor="沈砚", kind="action",
          state=None, parent=None, id="t01", cast=CAST):
    return compare_plan_to_prose(
        project_id="test-novel", scene_id="chapter-8",
        beat=beat(goal, actor=actor, kind=kind, parent=parent, id=id),
        prose=prose, cast=cast, prior_candidate_state=state)


class PlanIsNotReality(unittest.TestCase):
    def test_real_spit_is_source_supported_even_with_alias(self):
        a = audit("沈砚把火髓果从齿间吐到左手心")
        self.assertEqual(a["status"], "OBSERVED_SOURCE_SUPPORTED")
        self.assertEqual(a["coverage"], "SUPPORTED_TYPED_INTENT")
        self.assertEqual(a["last_observed_state"], "沈砚左手心")
        self.assertIsNotNone(a["observed_anchor"])
        self.assertFalse(a["whole_beat_goal_verified"])
        self.assertFalse(a["source_based_literary_semantics_proven"])
        self.assertEqual(a["model_calls"], 0)

    def test_plan_to_swallow_does_not_make_biting_and_spitting_count(self):
        a = audit("沈砚吞下火髓果")
        self.assertEqual(a["status"], "CONTRADICTED")
        self.assertEqual(a["last_observed_state"], "沈砚左手心")
        self.assertEqual(a["expected_narrow_state"]["expected"],
                         "已消耗（沈砚吞服）")

    def test_actual_explicit_swallow_requires_source_palm_precondition(self):
        prose = "沈砚把火髓果从左手心拿起送入口中吞下。"
        old = cell("item", "火髓果", "holder", "沈砚左手心")
        a = audit("沈砚吞下火髓果", prose, state=old)
        self.assertEqual(a["status"], "OBSERVED_SOURCE_SUPPORTED")
        self.assertEqual(a["last_observed_state"], "已消耗（沈砚吞服）")
        self.assertEqual(a["prose_sha256"],
                         hashlib.sha256(prose.encode("utf8")).hexdigest())

    def test_swallow_without_prior_palm_is_not_declared_true(self):
        prose = "沈砚把火髓果从左手心拿起送入口中吞下。"
        a = audit("沈砚吞下火髓果", prose)
        self.assertEqual(a["status"], "UNPROVEN")
        self.assertIsNone(a["observed_anchor"])

    def test_wrong_actor_does_not_inherit_consumption_from_protagonist(self):
        a = audit("唐蜃吞下火髓果", actor="唐蜃")
        self.assertEqual(a["status"], "UNPROVEN")
        self.assertIsNone(a["observed_anchor"])

    def test_missing_actor_first_in_story_abstains_instead_of_misattribution(self):
        prose = "唐蜃攥紧刀，沈砚把火髓果往齿间一咬。"
        a = audit("沈砚把火髓果从齿间吐到左手心", prose)
        self.assertEqual(a["status"], "UNPROVEN")

    def test_arm_injury_does_not_jump_to_other_character(self):
        prose = "沈砚右臂垂着，却没有停步。"
        shen = audit("沈砚右臂受限", prose)
        tang = audit("唐蜃右臂受限", prose, actor="唐蜃")
        self.assertEqual(shen["status"], "OBSERVED_SOURCE_SUPPORTED")
        self.assertEqual(tang["status"], "UNPROVEN")

    def test_other_character_using_healthy_arm_does_not_mean_hero_healed(self):
        old = cell("character", "沈砚", "右臂可用性", "受限")
        prose = "唐蜃右手挥剑，沈砚用左肩撞开石门。"
        a = audit("沈砚右臂恢复", prose, state=old)
        self.assertEqual(a["status"], "UNPROVEN")
        self.assertEqual(a["coverage"], "UNSUPPORTED_GOAL_OR_AMBIGUOUS_ACTOR")

    def test_handoff_requires_known_holder_and_named_recipient(self):
        p = "沈砚把火髓果从左手心递给唐蜃。"
        g = "沈砚把火髓果从左手心递给唐蜃"
        prior = cell("item", "火髓果", "holder", "沈砚左手心")
        good = audit(g, p, state=prior)
        missing = audit(g, p)
        self.assertEqual(good["status"], "OBSERVED_SOURCE_SUPPORTED")
        self.assertEqual(good["last_observed_state"], "唐蜃手中")
        self.assertEqual(missing["status"], "UNPROVEN")

    def test_unconfirmed_handoff_is_not_magic_teleport(self):
        p = "唐蜃把火髓果从左手心递给沈砚。"
        prior = cell("item", "火髓果", "holder", "沈砚左手心")
        a = audit("沈砚把火髓果从左手心递给唐蜃",
                  p, state=prior)
        self.assertEqual(a["status"], "UNPROVEN")

    def test_quiet_is_not_called_a_literary_failure(self):
        a = audit("沈砚听雨思索旧事", kind="quiet")
        self.assertEqual(a["status"], "UNPROVEN")
        self.assertEqual(a["coverage"], "NON_STATEFUL_BEAT")
        self.assertIsNone(a["expected_narrow_state"])

    def test_hypothetical_plan_does_not_become_obligation(self):
        a = audit("沈砚试图吞下火髓果")
        self.assertEqual(a["status"], "UNPROVEN")
        self.assertEqual(a["coverage"], "AMBIGUOUS_OR_NONASSERTIVE_GOAL")

    def test_goal_can_not_materialize_an_unwritten_event(self):
        a = audit("沈砚吞下火髓果", "沈砚望着石壁，一言不发。")
        self.assertEqual(a["status"], "UNPROVEN")
        self.assertIsNone(a["last_observed_state"])

    def test_last_observation_wins_not_earlier_palm(self):
        p = BITE_AND_SPIT + "沈砚把果子从左手心拿起送入口中吞下。"
        a = audit("沈砚吞下火髓果", p)
        self.assertEqual(a["status"], "OBSERVED_SOURCE_SUPPORTED")

    def test_receipt_is_hashed_and_excludes_original_manuscript(self):
        a = audit("沈砚吞下火髓果")
        h = a["receipt_sha256"]
        obj = {k: v for k, v in a.items() if k != "receipt_sha256"}
        expected = hashlib.sha256(
            json.dumps(obj, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")).encode("utf8")).hexdigest()
        self.assertEqual(h, expected)
        self.assertFalse(a["contains_raw_prose"])
        self.assertNotIn(BITE_AND_SPIT, json.dumps(a, ensure_ascii=False))
        self.assertFalse(a["author_accepted"])
        self.assertEqual(a["canon_writes"], 0)

    def test_dependency_lamp_only_for_direct_incomplete_typed_event(self):
        a = audit("沈砚吞下火髓果")
        dep = beat("沈砚靠左手试探石门", parent="t01", id="t02")
        note = pending_dependency_hint(dep, [a])
        self.assertIn("计划不是已发生事实", note)
        self.assertIn("允许调整", note)
        self.assertEqual(pending_dependency_hint(
            beat("沈砚看雨", id="t02"), [a]), "")
        self.assertEqual(pending_dependency_hint(
            beat("沈砚看雨", id="t02", parent="t09"), [a]), "")
        ok = audit("沈砚把火髓果从齿间吐到左手心")
        self.assertEqual(pending_dependency_hint(dep, [ok]), "")

    def test_unsupported_goal_never_forces_dependency_hint(self):
        a = audit("沈砚思考唐蜃的真正动机")
        dep = beat("沈砚询问唐蜃", id="t02", parent="t01")
        self.assertEqual(a["status"], "UNPROVEN")
        self.assertEqual(pending_dependency_hint(dep, [a]), "")

    def test_stale_or_oversized_inputs_fail_closed(self):
        with self.assertRaisesRegex(PlanExecutionError, "PROSE_BOUNDS"):
            audit("沈砚吞下火髓果", "长"*20001)
        with self.assertRaisesRegex(PlanExecutionError, "CAST_INVALID"):
            audit("沈砚吞下火髓果", cast=("沈砚", "沈砚"))
        with self.assertRaisesRegex(PlanExecutionError, "PREVIOUS_STATE_INVALID"):
            audit("沈砚吞下火髓果", state={"a": 1} | {
                str(i): i for i in range(36)})

    def test_real_writing_path_is_connected_after_model_turn(self):
        from writerforge import writing_assist
        src = inspect.getsource(writing_assist.AutonomousWriting.run)
        self.assertIn("plan_execution_checks.append(execution_comparison)", src)
        self.assertIn("compare_plan_to_prose(", src)
        self.assertIn("pending_dependency_hint(", src)
        self.assertIn('"v120_plan_prose_source_receipts"', src)


if __name__ == "__main__":
    unittest.main()
