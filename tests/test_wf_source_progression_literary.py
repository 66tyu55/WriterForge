"""Actual-source literary progression cue, not genre keyword scoring.

Author's scene goals remain optional; separate characters keep autonomous
decisions. No provider, R2, canon, or new memory.
"""
import inspect
import unittest

from writerforge.writing_assist import (
    _source_progression_literary_cue,
    AutonomousWriting, WritingExecutionError,
)


class SourceProgressionCraft(unittest.TestCase):
    def test_first_turn_does_not_receive_fake_previous_effect(self):
        self.assertEqual(_source_progression_literary_cue(()), "")

    def test_second_turn_receives_consequence_rather_than_replayed_setup(self):
        first={"beat_id":"t01","prose":"沈砚在宴上取伞，掌柜把来客当成官员。",
               "effect_quote":None}
        output=_source_progression_literary_cue((first,))
        self.assertIn("前一段已经发生",output)
        self.assertIn("新的反馈",output)
        self.assertIn("不是剧情硬命令",output)
        self.assertIn("克制与延迟",output)
        self.assertIn("仍可安静、失败、改变原计划",output)
        self.assertNotIn("必须逗笑",output)
        self.assertNotIn("必须反转",output)
        self.assertNotIn("巡察使",output)

    def test_writing_route_enabled_only_for_unified_guard_and_optional_lane(self):
        source=inspect.getsource(AutonomousWriting.run)
        self.assertIn("literary_progression_mode:str|None=None",source)
        self.assertIn('"source_progression" if draft_mode=="continuity_guard"',source)
        self.assertIn('literary_progression_mode=="source_progression"',source)
        self.assertIn("WF_LITERARY_PROGRESSION_REQUIRES_UNIFIED_SCENE",source)
        self.assertIn("_source_progression_literary_cue(",source)
        self.assertIn("if progression_cue:",source)
        self.assertIn('delivery["unproven_dependency_hint_delivered"]',source)
        self.assertIn('"source_progression_is_optional_craft"',source)
        self.assertNotIn("CANON_FACT_PROMOTION",source)

    def test_mode_opt_in_cannot_be_ignored_by_other_draft_modes(self):
        class Guard:
            project_id="synthetic"
            scene_id="synthetic"
        runner=AutonomousWriting(Guard())
        with self.assertRaisesRegex(
                WritingExecutionError,"WF_LITERARY_PROGRESSION_REQUIRES_UNIFIED_SCENE"):
            runner.run(
                outline="这是有足够长度的测试大纲，包含人物、冲突与错误观察。",
                chapter_goals=["唐蜃拒绝照原计划行动并承担后果"],
                output_dir="/tmp/do-not-create-wf-progress-test",
                draft_mode="single",literary_progression_mode="source_progression")

if __name__=="__main__":
    unittest.main()
