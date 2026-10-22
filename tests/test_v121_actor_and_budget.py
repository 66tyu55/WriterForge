"""V121: source actor binding and optional guidance under bounded prompts.

No literary model, network, R2 or canon writes. The revisions must not make
a model's intention or a generic body-part phrase into source evidence.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import inspect
import unittest

from writerforge.v116_state_delta import preflight_next_prose
from writerforge.v118_lamp_scheduler import (
    plan_scene_lamps, LampDecisionError, MAX_CHARS, checked_previous,
    CANONICAL_PHRASES,
)
from writerforge.writing_assist import (
    _prepare_guarded_turn_packet, AutonomousWriting, WritingExecutionError,
)
from writerforge.verified_flow import MAX_PROMPT_CHARS, GroundedDraftPacket

import json


def cell(name, value="受限"):
    key=json.dumps(["character",name,"右臂可用性","author_plan",None],
                   ensure_ascii=False,separators=(",",":"))
    return {key:value}


def check(text, prior=None, cast=("沈砚","唐蜃")):
    return preflight_next_prose(
        text,previous_candidate_state=prior or cell("沈砚"),cast=cast)


def beat(actor="沈砚",focus=("interiority",),kind="decision"):
    return {"id":"t01","kind":kind,"actor":actor,
            "goal":"沈砚怎样避开追兵并保护受伤右臂",
            "craft_focus":list(focus)}


def frame():
    return {
        "format":"wf.continuity.v117.pinned-oss-temporal-view",
        "project_id":"novel-z","chapter_index":0,
        "state_has_no_auto_canon_promotion":True,
        "no_model_call":True,"literary_truth_verified":False,
        "unreviewed_reducer_candidates":[{
            "domain":"character","entity_id":"沈砚",
            "predicate":"右臂可用性","value":"受限"}],
        "unresolved_open_debts":[],"knowledge":{},
    }


def draft_packet(text):
    return GroundedDraftPacket(
        scene_id="chapter-8",project_id="novel-z",
        snapshot_id=1,evidence=(),craft_ids=(),prompt=text,
        prompt_sha256=sha256(text.encode("utf8")).hexdigest())


def under_pressure_packet(hard,headroom):
    # _enrich adds one newline and "\\n【本章当前事件】"+hard.
    minimal="\n【本章当前事件】"+hard
    size=MAX_PROMPT_CHARS-1-len(minimal)-headroom
    assert size>0
    return draft_packet("B"*size)


def prepare(base,hard="沈砚右臂受限，恢复必须有来源。",
            plan=None,debt="",prior=None,turn=0):
    return _prepare_guarded_turn_packet(
        base,plan=plan or {"objective":"沈砚应尽力冲出围堵"},
        hard_turn_addition=hard,facets=(),dependency_hint=debt,
        project_id="novel-z",chapter_index=0,turn_index=turn,
        beat=beat(),frame=frame(),previous_lamp_receipt=prior)


class SourceActorBoundaries(unittest.TestCase):
    def test_other_actor_using_right_arm_does_not_trip_hero_state(self):
        result=check("唐蜃右手挥剑攻来，沈砚侧身避开。")
        self.assertFalse(result["blocked"],result)
        self.assertEqual(result["findings"],[])
        self.assertEqual(result["review_findings"],[])
        self.assertEqual(result["arm_actor_scope"],
                         "EXPLICIT_SOURCE_SUBJECT_ONLY")

    def test_explicit_injured_actor_still_rejected(self):
        result=check("沈砚右手挥剑砍向唐蜃。")
        self.assertTrue(result["blocked"])
        self.assertIn("WF116_ARM_USED_WITHOUT_RECOVERY",
                      result["findings"])

    def test_injury_in_same_sentence_binds_implicit_action(self):
        result=check("沈砚右臂受伤后，右手挥剑砍向唐蜃。")
        self.assertTrue(result["blocked"])
        self.assertIn("WF116_ARM_USED_WITHOUT_RECOVERY",
                      result["findings"])

    def test_other_named_subject_closer_than_earlier_watcher(self):
        result=check("沈砚看着唐蜃右手挥剑，脚下不敢停。")
        self.assertFalse(result["blocked"])
        self.assertFalse(result["needs_review"],result)

    def test_pronoun_cannot_be_hard_assigned_but_is_reviewable(self):
        result=check("他右手挥剑砍向洞口的黑影。")
        self.assertFalse(result["blocked"])
        self.assertTrue(result["needs_review"])
        self.assertIn("WF121_RIGHT_ARM_ACTION_ACTOR_UNRESOLVED",
                      result["review_findings"])

    def test_named_enemy_can_be_the_only_injured_one(self):
        result=check("沈砚右手挥剑刺向唐蜃。",
                     prior=cell("唐蜃"))
        self.assertFalse(result["blocked"])
        self.assertFalse(result["needs_review"])

    def test_unproven_healing_of_other_actor_does_not_heal_hero(self):
        result=check("唐蜃右臂在丹药作用下恢复。"
                     "沈砚右手挥剑，刀光划破黑暗。")
        self.assertTrue(result["blocked"])
        self.assertIn("WF116_ARM_USED_WITHOUT_RECOVERY",
                      result["findings"])

    def test_named_healing_claim_without_source_is_still_blocked(self):
        result=check("沈砚右臂恢复了。沈砚右手挥剑。")
        self.assertTrue(result["blocked"])
        self.assertIn("WF116_ARM_RECOVERY_WITHOUT_SOURCE",
                      result["findings"])

    def test_named_healing_with_source_is_review_not_proven(self):
        result=check("沈砚右臂经丹药治疗恢复。沈砚右手挥剑。")
        self.assertFalse(result["blocked"])
        self.assertTrue(result["needs_review"])
        self.assertIn("WF116_ARM_RECOVERY_CLAIM_NEEDS_REVIEW",
                      result["review_findings"])

    def test_negation_and_attempt_are_not_completed_use(self):
        for sentence in ("沈砚右手没有挥剑。",
                         "沈砚右手想要挥剑，却被锁住。"):
            with self.subTest(sentence=sentence):
                result=check(sentence)
                self.assertFalse(result["blocked"],result)

    def test_dialogue_and_dreams_are_not_source_action(self):
        for sentence in ("唐蜃喝道：“沈砚右手挥剑！”",
                         "沈砚梦见自己右手挥剑，醒后仍麻木。"):
            with self.subTest(sentence=sentence):
                result=check(sentence)
                self.assertFalse(result["blocked"])
                self.assertFalse(result["needs_review"])

    def test_two_injured_characters_not_conflated(self):
        previous={**cell("沈砚"),**cell("唐蜃")}
        result=check("唐蜃右手挥剑，沈砚侧身躲开。",
                     prior=previous)
        self.assertTrue(result["blocked"])
        self.assertIn("WF116_ARM_USED_WITHOUT_RECOVERY",
                      result["findings"])

    def test_old_json_string_like_false_cell_not_considered_injury(self):
        previous={json.dumps(["item","沈砚右臂可用性","holder","author_plan",None],
                             ensure_ascii=False):"受限"}
        result=check("沈砚右手挥剑。",prior=previous)
        self.assertFalse(result["blocked"])


class BoundedOptionalPrompt(unittest.TestCase):
    def test_v118_zero_budget_drops_craft_without_cooldown(self):
        first=plan_scene_lamps(
            project_id="novel-z",chapter_index=0,turn_index=0,
            beat=beat(),frame=frame(),max_prompt_chars=0)
        self.assertEqual(first["prompt"],"")
        self.assertIsNone(first["craft_id"])
        self.assertTrue(first["budget_suppressed_craft"])
        self.assertTrue(first["budget_suppressed_risks"])
        self.assertTrue(first["zero_lamp_is_valid"])
        checked_previous(first,"novel-z",0)
        second=plan_scene_lamps(
            project_id="novel-z",chapter_index=0,turn_index=1,
            beat=beat(),frame=frame(),previous=first)
        self.assertIsNotNone(second["craft_id"])
        self.assertIsNone(second["craft_suppression"])

    def test_preserve_risk_lamp_before_literary_question(self):
        risk_only=len("【只在确实涉及该变化时遵守的前文约束】\n"+
                      CANONICAL_PHRASES["arm"])
        x=plan_scene_lamps(
            project_id="novel-z",chapter_index=0,turn_index=0,
            beat=beat(),frame=frame(),max_prompt_chars=risk_only)
        self.assertLessEqual(len(x["prompt"]),risk_only)
        self.assertIn("arm",x["risk_lamps"])
        self.assertIsNone(x["craft_id"])
        self.assertTrue(x["budget_suppressed_craft"])
        self.assertFalse(x["budget_suppressed_risks"])

    def test_tiny_context_keeps_true_constraints_without_lamps(self):
        hard="沈砚右臂受限，恢复必须有来源。"
        base=under_pressure_packet(hard,headroom=12)
        packet,lamps,delivery=prepare(
            base,hard=hard,
            debt="\n【未证因果】下一段必须从真正写出的事实接起。")
        self.assertEqual(len(packet.prompt)<=MAX_PROMPT_CHARS,True)
        self.assertIn(hard,packet.prompt)
        self.assertEqual(lamps["prompt"],"")
        self.assertFalse(delivery["provisional_plan_included"])
        self.assertFalse(delivery["unproven_dependency_hint_delivered"])
        self.assertFalse(delivery["lamp_prompt_delivered"])
        self.assertEqual(delivery["delivered_prompt_sha256"],
                         packet.prompt_sha256)
        self.assertTrue(delivery["hard_context_preserved"])
        self.assertTrue(delivery["no_model_call_for_prompt_scheduling"])

    def test_proposed_chapter_plan_is_optional_not_continuity_source(self):
        hard="【真正的物件与人物状态】火髓果在沈砚左掌，不能当已吞服。"
        p,lamps,d=prepare(under_pressure_packet(hard,headroom=25),hard=hard,
                          plan={"objective":"x"*400})
        self.assertIn(hard,p.prompt)
        self.assertNotIn("x"*400,p.prompt)
        self.assertTrue(d["provisional_plan_dropped_due_to_budget"])

    def test_ordinary_context_still_includes_plan_lamps_and_debt(self):
        hint="\n【上段计划未被正文证实】只以真实情节为准。"
        p,lamps,d=prepare(draft_packet("正文基础约束。"),debt=hint)
        self.assertTrue(d["provisional_plan_included"])
        self.assertTrue(d["unproven_dependency_hint_delivered"])
        self.assertIn(hint,p.prompt)
        self.assertTrue(d["lamp_prompt_delivered"])
        self.assertIn("【原创章计划】",p.prompt)
        self.assertLessEqual(len(p.prompt),MAX_PROMPT_CHARS)

    def test_hard_context_too_large_is_explicit_failure(self):
        hard="【剧情硬约束】前文受伤不允许凭空痊愈。"
        base=under_pressure_packet(hard,headroom=0)
        bad=replace(base,prompt=base.prompt+"x"*6)
        with self.assertRaisesRegex(
                WritingExecutionError,"exceeds size limit"):
            prepare(bad,hard=hard)

    def test_signed_lamp_cannot_be_modified_to_fake_delivery(self):
        first=plan_scene_lamps(
            project_id="novel-z",chapter_index=0,turn_index=0,
            beat=beat(),frame=frame(),max_prompt_chars=0)
        forged=dict(first)
        forged["last_active_craft_id"]="fake"
        with self.assertRaises(LampDecisionError):
            plan_scene_lamps(
                project_id="novel-z",chapter_index=0,turn_index=1,
                beat=beat(),frame=frame(),previous=forged)

    def test_main_writing_path_calls_bounded_packet_and_cast_preflight(self):
        source=inspect.getsource(AutonomousWriting.run)
        self.assertIn("_prepare_guarded_turn_packet(",source)
        self.assertIn("reference=continuity_reference,\n                                cast=cast)",source)
        self.assertIn('"v121_prompt_delivery_receipts"',source)


if __name__=="__main__":
    unittest.main()
