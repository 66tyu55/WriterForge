"""V114 true V113 literary defect calibration, no model and no corpus copies.

We store only SHORT anchors from the already analyzed model-generated
V113 short story, not the entire private user novel or student corpus.
WF's generated source is never rewritten and not promoted as canonical.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from writerforge.v114_continuity_memory import (
    literal_item_continuity,validated_checkpoint,compact_status,
    V114ContinuityError,hashb,packed,
)

from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.writing_assist import (
    InvisibleWritingAssist,AutonomousWriting,WritingExecutionError,
)
from test_v26_invisible_writer import make_db,PLAN
from test_v96_causal_turns import (
    ACTION1,EFFECT1,ACTION2,EFFECT2,turns,prose1,prose2,
)
from test_v102_emotional_causality import emotional

ACTUAL_V113_QUOTES=(
    "沈渡偏头一避。就这一瞬，她看清他腰间还挂着旧剑穗——"
    "那是她三年前编的，粗糙，早该扔了。"
    "沈渡追至崖边，锁魂索被水雾吞没，再往前一步就是断崖。"
    "他收住脚，索头回落，钩尖上挂着一截湿透的旧剑穗。"
)
CAST=("叶青梧","沈渡")

class ContinuityMemoryTests(TestCase):
    def test_real_old_tassel_changed_carriers_without_transfer(self):
        report=literal_item_continuity(ACTUAL_V113_QUOTES,cast=CAST)
        issues=[v for v in report["risks"]
                if v["kind"]=="ITEM_OWNER_CHANGE_WITHOUT_TRANSFER"]
        self.assertEqual(len(issues),1)
        issue=issues[0]
        self.assertEqual(issue["item"],"剑穗")
        self.assertEqual(issue["before_holder"],"沈渡")
        self.assertEqual(issue["after_claimed_holder"],"索钩")
        self.assertFalse(report["semantic_literary_continuity_verified"])
        self.assertTrue(issue["candidate_needs_source_review"])
        self.assertEqual(report["model_calls_for_validation"],0)
        self.assertIn("索钩",compact_status(report))

    def test_a_credible_actual_transfer_has_no_false_positive(self):
        text=("沈渡腰间悬着旧剑穗。沈渡从腰间取下旧剑穗，"
              "又把剑穗挂到锁魂索钩尖上。"
              "索头回落，钩尖上挂着旧剑穗。")
        report=literal_item_continuity(text,cast=CAST)
        self.assertFalse(any(x["kind"]=="ITEM_OWNER_CHANGE_WITHOUT_TRANSFER"
                             for x in report["risks"]))

    def test_flying_sword_temporal_weapon_owner(self):
        text=("他让飞剑脱手掷出，剑尖钉进山壁。"
              "他踩过血潭又反身一剑，逼退追兵。"
              "随后他才拔出山壁上的飞剑。")
        risks=literal_item_continuity(text,cast=("沈渡",))["risks"]
        self.assertIn("WEAPON_USED_BEFORE_RETURN",
                      [r["kind"] for r in risks])
        fixed=("他让飞剑脱手掷出，钉进山壁。"
               "他先召回飞剑，才反身一剑击退追兵。")
        self.assertNotIn("WEAPON_USED_BEFORE_RETURN",
            [r["kind"] for r in literal_item_continuity(fixed)["risks"]])

    def test_ambiguous_flashback_does_not_become_present_holder(self):
        text=("沈渡腰间挂着旧剑穗。"
              "她梦见那枚旧剑穗后来挂在索钩上。"
              "沈渡仍然没有把剑穗交给任何人。")
        self.assertFalse(literal_item_continuity(text,cast=CAST)["risks"])

    def test_checkpoint_is_immutable_and_crosses_two_empty_turns(self):
        a=validated_checkpoint(
            prose="沈渡腰间挂着旧剑穗。",cast=CAST)
        b=validated_checkpoint(
            prose="云层散去，青灯渐渐熄了。",cast=CAST,previous=a)
        self.assertIn("沈渡",compact_status(b["report"]))
        c=validated_checkpoint(
            prose="索头回落，钩尖上挂着旧剑穗。",cast=CAST,previous=b)
        self.assertEqual(c["sequence"],3)
        self.assertEqual(c["previous_checkpoint_sha256"],b["receipt_sha256"])
        self.assertTrue(any(x["kind"]=="ITEM_OWNER_CHANGE_WITHOUT_TRANSFER"
                            for x in c["report"]["risks"]))
        altered=deepcopy(b)
        altered["report"]["active_state"][0]["holder_hypothesis"]="索钩"
        with self.assertRaisesRegex(V114ContinuityError,"UNTRUSTED"):
            validated_checkpoint(prose="又走三步。",cast=CAST,previous=altered)

    def test_unforeshadowed_last_minute_power_is_only_review_candidate(self):
        report=literal_item_continuity(
          "沈渡丹田空得发疼。忽然发现三颗灵果，吞下后法力回涨三成。")
        self.assertIn("LATE_POWER_SOURCE_UNESTABLISHED",
                      [r["kind"] for r in report["risks"]])
        self.assertFalse(report["semantic_literary_continuity_verified"])

class WFRealEntrypointIntegration(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.root=Path(self.tmp.name)
        dbpath=self.root/"neutral.sqlite3"
        self.snap=make_db(dbpath)
        self.db=WriterForgeDB(dbpath)
        self.runtime=RuntimeEngine();self.runtime.enter_write(self.snap)
        self.assist=InvisibleWritingAssist(
            self.db,self.runtime,"v114-synthetic-only","battle-scene",
            "两人在夜里追逐，角色必须为选择承担代价",
            model="mock-zero-billing",api_base="http://127.0.0.1:1234/v1")
    def tearDown(self):
        self.db.close();self.tmp.cleanup()

    def test_real_WF_segmented_call_flow_carries_actual_item_state(self):
        # Existing V96 quote anchoring remains unchanged. The factual
        # intermediate status is derived from actual text, not fake model.
        from test_v102_emotional_causality import note1,note2
        ans=[
            PLAN,                    # whole chapter plan
            json.dumps({"turns":turns()},ensure_ascii=False),
            json.dumps({
                "prose":prose1(),
                "trace":{"action_quote":ACTION1,"effect_quote":EFFECT1,
                         "parent_effect_quote":None}},ensure_ascii=False),
            json.dumps({
                "prose":prose2(),
                "trace":{"action_quote":ACTION2,"effect_quote":EFFECT2,
                         "parent_effect_quote":EFFECT1}},ensure_ascii=False),
        ]
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=ans) as model:
            doc=AutonomousWriting(self.assist).run(
                outline="夜雨里的一段真实追逐事件",
                chapter_goals=["两名人物必须在桥上决定如何让药送到对岸"],
                output_dir=self.root/"v114",
                draft_mode="continuity_guard",
            )
        self.assertEqual(model.call_count,4)
        second=model.call_args_list[3].args[0].prompt
        self.assertIn("物件",second)
        self.assertIn("转移",second)
        ch=doc["chapters"][0]
        self.assertEqual(ch["draft_mode"],"continuity_guard")
        self.assertFalse(ch["accepted"])
        state=json.loads(Path(ch["v114_candidate_item_memory"]).read_text("utf8"))
        self.assertEqual(state["format"],"wf.writing.continuity-checkpoint.v114")
        self.assertEqual(state["sequence"],2)
        self.assertEqual(state["canon_state_writes"],0)
        self.assertFalse(state["literary_semantics_verified"])
        self.assertIsNone(self.db.conn.execute(
            "SELECT 1 FROM accepted_prose").fetchone())
        raw=list((self.root/"v114").rglob("*-raw.json"))
        self.assertGreaterEqual(len(raw),2)

    def test_WF_default_single_route_unmodified(self):
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=[PLAN,"纯模型一次写就，未加入状态追踪的旧路径。"*40]) as model:
            doc=AutonomousWriting(self.assist).run(
                outline="夜雨里的一段真实追逐事件",
                chapter_goals=["两名人物必须在桥上决定如何让药送到对岸"],
                output_dir=self.root/"old",
                draft_mode="single")
        self.assertEqual(model.call_count,2)
        ch=doc["chapters"][0]
        self.assertNotIn("v114_candidate_item_memory",ch)

if __name__=="__main__":
    import unittest
    unittest.main()
