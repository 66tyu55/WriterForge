"""Fresh new-character action feedback: rule changes valid choices before prose."""
from __future__ import annotations
import unittest
from experiments.wf_xianxia_time_v2_fresh_action_trial_once import (
    frozen,preflight,window,plan_prompt,decode_decision,
    check_decision,prose_prompt,ARM_IDS
)

class FreshTimeAuthorTrialTests(unittest.TestCase):
    def test_is_new_heldout_character_with_shared_world(self):
        d=frozen()
        self.assertEqual(d["character"]["role"],"山门守钟人")
        self.assertEqual(d["character"]["temperament"],"多疑但重诺")
        self.assertEqual(d["seed"],20261114)
        info=preflight()
        self.assertEqual(info["max_total_real_model_calls"],4)
        self.assertEqual([x["arm"] for x in info["arms"]],list(ARM_IDS))
        self.assertFalse(info["arms"][0]["attempt_time_eligible"])
        self.assertTrue(info["arms"][1]["attempt_time_eligible"])

    def test_same_author_success_proposal_rejected_only_by_time(self):
        d=frozen()
        proposal={"choice":"try_breakthrough","outcome":"success",
                  "world_hours":0,"reason":"想兑现守钟的承诺"}
        n=check_decision(d,"world_rate1",proposal)
        y=check_decision(d,"world_rate3",proposal)
        self.assertFalse(n["accepted"])
        self.assertEqual(n["reason"],"BREAKTHROUGH_NOT_TIME_ELIGIBLE")
        self.assertTrue(y["accepted"])
        self.assertEqual(y["final_realm"],2)
        self.assertEqual(y["world_after"],2008)

    def test_author_can_choose_manual_warning_in_both_conditions(self):
        d=frozen()
        proposal={"choice":"ring_manual_bell","outcome":"none",
                  "world_hours":1,"reason":"宁可先敲普通钟通知路人"}
        for arm in ARM_IDS:
            result=check_decision(d,arm,proposal)
            self.assertTrue(result["accepted"])
            self.assertEqual(result["world_after"],2009)

    def test_no_unlabelled_teleport_and_npcs_keep_clock(self):
        d=frozen()
        for arm in ARM_IDS:
            w=window(d,arm)
            self.assertEqual(w["world_hour_now"],2008)
            self.assertEqual(w["world_hours_left"],4)
            self.assertEqual(w["actor_current_time_frame"],"outside")
            self.assertEqual(w["actor_time_rate_subjective_per_world_hour"],"1")
            self.assertEqual(w["offscreen_npc_clocks"]["N001"]["lived_subjective_hours"],"8")
            text=plan_prompt(d,arm)
            self.assertIn("洞内外时间边界",text)
            self.assertIn("冰桥封闭",text)
            self.assertNotIn("河水预计",text)
            self.assertNotIn('"world_clock"',text)

    def test_bad_plan_is_explicitly_rejected_without_autocorrect(self):
        d=frozen()
        plan,error=decode_decision('{"choice":"try_breakthrough","outcome":"success","world_hours":2,"reason":"答应救人"}')
        self.assertIsNone(plan)
        self.assertEqual(error,"DECISION_ATTEMPT_INVALID")
        report=check_decision(d,"world_rate3",plan)
        self.assertEqual(report["reason"],"NO_VALID_DECISION")
        prose=prose_prompt(d,"world_rate3",plan,report)
        self.assertIn("不能假装既定事情发生",prose)

    def test_invalid_plan_cannot_invent_time_or_fake_outcome(self):
        cases=[
            '{"choice":"ring_manual_bell","outcome":"success","world_hours":1,"reason":"救人"}',
            '{"choice":"hide","outcome":"none","world_hours":0,"reason":"害怕"}',
            '{"choice":"ring_manual_bell","outcome":"none","world_hours":true,"reason":"救人"}',
            '{"choice":"use_technique","outcome":"success","world_hours":0,"reason":"救人"}',
        ]
        for raw in cases:
            with self.subTest(raw=raw):
                decision,err=decode_decision(raw)
                self.assertIsNone(decision)
                self.assertIsNotNone(err)


    def test_second_stage_must_use_post_action_clock_if_action_committed(self):
        d=frozen()
        choice={"choice":"ring_manual_bell","outcome":"none",
                "world_hours":1,"reason":"先把桥下旅人叫醒"}
        result=check_decision(d,"world_rate1",choice)
        self.assertTrue(result["accepted"])
        prompt=prose_prompt(d,"world_rate1",choice,result)
        self.assertIn("现在是世界第2009小时",prompt)
        self.assertIn("外界还剩3小时",prompt)
        self.assertNotIn("现在是世界第2008小时",prompt)

    def test_rejected_action_must_not_advance_world_clock(self):
        d=frozen()
        choice={"choice":"try_breakthrough","outcome":"success",
                "world_hours":0,"reason":"急于兑现敲钟承诺"}
        result=check_decision(d,"world_rate1",choice)
        self.assertFalse(result["accepted"])
        prompt=prose_prompt(d,"world_rate1",choice,result)
        self.assertIn("现在是世界第2008小时",prompt)
        self.assertIn("无法按宣称结果执行",prompt)

if __name__=="__main__":
 unittest.main()
