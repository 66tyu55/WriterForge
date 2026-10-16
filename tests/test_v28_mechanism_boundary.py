"""V28 P0: no copyrighted source plot or model-prose reaches Writer.

All test paragraphs are synthetic. This is an engineering boundary check,
not a proof of literary skill or semantic understanding.
"""
from __future__ import annotations

import json
import unittest
from writerforge.reverse_mechanism_boundary import (
    MechanismBoundaryError, source_paragraphs, proposal_prompt,
    parse_selections, build_writer_packet, report_evidence, TECHNIQUES,
)
from writerforge.reverse_cloud_ab import CloudABTrial,ABTrialError
from writerforge.reverse_real_training import raw_hash


SOURCE=("某学徒在陌生村庄醒来，他并不知道路口的危险。\n"
        "同行人沉默片刻，把自己的午餐让给了他。\n"
        "学徒看见路上的新脚印，于是改变了过桥计划。\n")*5
PLAN={"selections":[
    {"id":"GOAL_FILTERS_ATTENTION","evidence_ids":["P0"]},
    {"id":"COST_VISIBLE_IN_ACTION","evidence_ids":["P1"]},
]}
SCENE_A=("枫树下的信使听见钟楼里传来陌生声响。他原想赶在入夜前"
         "送到最后一封信，却突然意识到铃声与往日不同。于是改变路线。")*10
SCENE_B=("河上的测绘员望着潮水，注意到桥墩旁出现此前没有的刻痕。"
         "他必须决定是否继续绘图。他选择折返村庄，把风险告知同伴。")*10


class FakeAgent:
    def __init__(self,name,answer,role):
        self.provider="fixture"
        self.name=name
        self.answer=answer
        self.role=role
        self.requests=[]
    def ask(self,system,user,num_predict):
        self.requests.append(user)
        if self.role=="writer":
            return {"scene": SCENE_A if len(self.requests)==1 else SCENE_B}
        return self.answer


class P0LeakageTests(unittest.TestCase):
    def test_writer_receives_only_host_operations_not_source_data(self):
        paragraphs=source_paragraphs(SOURCE)
        selection=parse_selections(PLAN,paragraphs)
        packet=build_writer_packet(selection,enhanced=True,writing_task="写一段原创片段")
        serialized=json.dumps(packet,ensure_ascii=False)
        self.assertIn("GOAL_FILTERS_ATTENTION",serialized)
        self.assertIn("COST_VISIBLE_IN_ACTION",serialized)
        self.assertNotIn("某学徒",serialized)
        self.assertNotIn("同行人",serialized)
        self.assertNotIn("桥墩",serialized)
        self.assertNotIn("evidence_ids",serialized)
        self.assertNotIn("P0",serialized)
        self.assertFalse("mechanism" in packet)
        self.assertEqual(len(report_evidence(selection,paragraphs)),2)

    def test_proposal_rejects_original_character_plot_fields(self):
        paragraphs=source_paragraphs(SOURCE)
        plot_pollution={
            "selections":[{"id":"GOAL_FILTERS_ATTENTION","evidence_ids":["P0"]}],
            "perception":"林动因为被林山打伤，想起林啸的修炼资源"
        }
        with self.assertRaisesRegex(MechanismBoundaryError,"unrecognized"):
            parse_selections(plot_pollution,paragraphs)
        with self.assertRaisesRegex(MechanismBoundaryError,"untrusted fields"):
            parse_selections({
                "selections":[{"id":"GOAL_FILTERS_ATTENTION","evidence_ids":["P0"],
                               "event":"某学徒得到了父亲拿出来的药材"}]
            },paragraphs)

    def test_missing_or_out_of_order_evidence_fails_closed(self):
        paragraphs=source_paragraphs(SOURCE)
        with self.assertRaisesRegex(MechanismBoundaryError,"missing source paragraph"):
            parse_selections({"selections":[{"id":"COST_VISIBLE_IN_ACTION",
                            "evidence_ids":["P999"]}]},paragraphs)
        with self.assertRaisesRegex(MechanismBoundaryError,"invalid or duplicate technique"):
            parse_selections({"selections":[{"id":"PROSE_COPY",
                            "evidence_ids":["P0"]}]},paragraphs)

    def test_ab_does_not_let_old_planner_free_text_go_to_writer(self):
        bad={
            "trigger":"林动被林山打昏后醒来",
            "perception":"林动感知到父亲林啸受伤",
            "decision":"母亲柳妍眼眶通红",
            "consequence":"林动得到赤参",
            "reader_question":"林啸为什么受伤",
            "author_mechanism":"林动的家族秘密被埋下伏笔",
        }
        p=FakeAgent("planner",bad,"planner")
        w=FakeAgent("writer",{},"writer")
        c=FakeAgent("critic",{},"critic")
        with self.assertRaises(MechanismBoundaryError):
            CloudABTrial(planner=p,writer=w,critic=c).run(
                SOURCE,"下一段相接",source_sha="a"*64,window_hash=raw_hash(SOURCE))
        self.assertEqual(len(w.requests),0)
        self.assertEqual(len(c.requests),0)

    def test_unequal_length_is_blocked_before_critic(self):
        class UnequalWriter(FakeAgent):
            def ask(self,system,user,num_predict):
                self.requests.append(user)
                return {"scene":SCENE_A if len(self.requests)==1 else SCENE_B*2}
        p=FakeAgent("planner",PLAN,"planner")
        w=UnequalWriter("writer",{},"writer")
        c=FakeAgent("critic",{},"critic")
        with self.assertRaisesRegex(ABTrialError,"LENGTH_MISMATCH"):
            CloudABTrial(planner=p,writer=w,critic=c).run(
                SOURCE,"下一段相接",source_sha="a"*64,window_hash=raw_hash(SOURCE))
        self.assertEqual(len(w.requests),2)
        self.assertEqual(len(c.requests),0)


if __name__=="__main__":
    unittest.main()
