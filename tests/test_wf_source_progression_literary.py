"""Actual-source literary progression cue, not genre keyword scoring.

Author's scene goals remain optional; separate characters keep autonomous
decisions. No provider, R2, canon, or new memory.
"""
import inspect
import json
import hashlib
import unittest
from unittest.mock import patch

from writerforge.writing_assist import (
    _source_progression_literary_cue,
    _prepare_guarded_turn_packet,AutonomousWriting, WritingExecutionError,
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
        self.assertIn('literary_progression_mode:str="baseline"',source)
        self.assertNotIn('literary_progression_mode:str|None=None',source)
        self.assertNotIn('"source_progression" if draft_mode=="continuity_guard"',source)
        self.assertIn('literary_progression_mode=="source_progression"',source)
        self.assertIn("WF_LITERARY_PROGRESSION_REQUIRES_UNIFIED_SCENE",source)
        self.assertIn("_source_progression_literary_cue(",source)
        self.assertIn("creative_progression_cue=progression_cue",source)
        self.assertNotIn("dependency_hint+=progression_cue",source)
        self.assertIn('"source_progression_is_optional_craft"',source)
        self.assertNotIn("CANON_FACT_PROMOTION",source)


    def test_optional_prose_cue_cannot_evict_existing_causal_dependency(self):
        from writerforge.verified_flow import GroundedDraftPacket
        from writerforge.v96_causal_turns import canonical
        prompt="真实前史：沈砚尚未向唐蜃坦白。"
        base=GroundedDraftPacket(
            scene_id="synthetic-scene",project_id="synthetic-project",
            snapshot_id=1,evidence=(),craft_ids=(),prompt=prompt,
            prompt_sha256=hashlib.sha256(prompt.encode("utf8")).hexdigest())
        kwargs={
            "body_base":base,"plan":{"objective":"留下选择空间"},
            "hard_turn_addition":"【已写事实】沈砚尚未告知真相。",
            "facets":(),"dependency_hint":"【上段实际因果待落实】不能把尚未交换的密令当成已交付。",
            "project_id":"synthetic-project","chapter_index":2,
            "turn_index":1,
            "beat":{"id":"t02","kind":"decision","actor":"沈砚",
                    "goal":"沈砚独自决定是否告诉唐蜃真相",
                    "causal_parent":None,"craft_focus":[]},
            "frame":None,"previous_lamp_receipt":None,
        }
        new_cue="【可选文学提示】"+"此处不要重演之前事件。"*40
        with patch("writerforge.writing_assist.MAX_PROMPT_CHARS",250):
            packet,_,receipt=_prepare_guarded_turn_packet(
                **kwargs,creative_progression_cue=new_cue)
        self.assertTrue(receipt["unproven_dependency_hint_delivered"])
        self.assertTrue(receipt["creative_progression_cue_eligible"])
        self.assertFalse(receipt["creative_progression_cue_delivered"])
        self.assertIn(kwargs["dependency_hint"],packet.prompt)
        self.assertNotIn(new_cue,packet.prompt)
        self.assertEqual(
            receipt["receipt_sha256"],
            hashlib.sha256(canonical({
                k:v for k,v in receipt.items()
                if k!="receipt_sha256"})).hexdigest())
        packet2,_,rec2=_prepare_guarded_turn_packet(
            **kwargs,creative_progression_cue=new_cue)
        self.assertTrue(rec2["creative_progression_cue_delivered"])
        self.assertTrue(rec2["unproven_dependency_hint_delivered"])
        self.assertLess(packet2.prompt.index(kwargs["dependency_hint"]),
                        packet2.prompt.index(new_cue))
        self.assertEqual(rec2["creative_progression_cue_characters"],
                         len(new_cue))

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
