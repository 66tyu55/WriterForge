"""WF V118: proactive optional literary lamps must NOT become rigid templates.

Offline, no provider, R2, new DB or external review. Validate real pinned
Novel Studio candidate state is routed through EXISTING CraftEngine with
zero extra model calls, bounded context and source-grounded risk activation.
"""
from __future__ import annotations
import json
import unittest
from pathlib import Path

from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v117_continuity_trace import audit_continuity
from writerforge.v118_lamp_scheduler import (
    plan_scene_lamps,LampDecisionError,MAX_CHARS,
)

FRUIT=(
    "沈砚看见火髓果已经发热。"
    "沈砚没应声，把果子往齿间一咬。"
    "他右手撑住炉沿要翻身，半空里忽然一麻——锁脉诀到了。"
    "灵力从肘弯往下被截断，手指头瞬间不听使唤。"
    "炉壁里的丹火忽然舔上他右前臂，烧出焦臭。"
    "沈砚把果子从齿间吐到左手心。"
)
SWORD=(
    "沈渡腰间挂着旧剑穗。叶青梧跌到索桥下方。"
    "沈渡抖出锁魂索，索头回落时钩尖上挂着湿透的旧剑穗。"
)
def beat(kind="action",actor="沈砚",goal="先避开追兵，用左手扶住石壁",focus=None):
    return {"id":"t01","kind":kind,"actor":actor,"goal":goal,
            "craft_focus":list(focus or [])}
def frame(prose=FRUIT,cast=("沈砚","唐蜃"),project="novel-z"):
    external=external_temporal_step(prose,cast=cast)
    return audit_continuity(external,project_id=project,
                            chapter_index=0,boundary="after")

def lamp(b,*,f=None,prior=None,turn=0,project="novel-z"):
    return plan_scene_lamps(
        project_id=project,chapter_index=0,turn_index=turn,beat=b,
        frame=f,previous=prior)


class LightsNotChecklist(unittest.TestCase):
    def test_no_change_quiet_scene_without_trigger_is_totally_dark(self):
        x=lamp(beat("quiet",goal="屋檐下停着一只鸟",focus=["none"]))
        self.assertEqual(x["prompt"],"")
        self.assertEqual(x["risk_lamps"],[])
        self.assertIsNone(x["craft_id"])
        self.assertTrue(x["zero_lamp_is_valid"])
        self.assertEqual(x["new_model_calls"],0)

    def test_actual_arm_limit_matches_person_not_nearby_enemy(self):
        f=frame()
        first=lamp(beat("action",actor="沈砚",focus=["action"]),f=f)
        self.assertIn("arm",first["risk_lamps"])
        self.assertIn("受限",first["risk_reason_codes"][0].lower()
              if "受限" in first["risk_reason_codes"][0] else first["prompt"])
        self.assertIn("恢复依据",first["prompt"])
        self.assertLessEqual(first["prompt_chars"],MAX_CHARS)
        self.assertFalse(first["source_text_copied_into_prompt"])
        # Adversary never receives protagonist's bodily restriction.
        other=lamp(beat("action",actor="唐蜃",goal="踢开阻碍",focus=[]),f=f)
        self.assertNotIn("arm",other["risk_lamps"])

    def test_fruit_only_illuminates_resource_when_goal_uses_it(self):
        f=frame()
        unrelated=lamp(beat("action",actor="唐蜃",goal="他绕到矿道后门",focus=[]),f=f)
        self.assertEqual(unrelated["prompt"],"")
        relevant=lamp(beat("decision",actor="沈砚",
                        goal="沈砚是否吃下火髓果补回法力",focus=[]),f=f)
        self.assertIn("resource",relevant["risk_lamps"])
        self.assertIn("资源",relevant["prompt"])
        self.assertIn("不要求解释思考过程",relevant["prompt"])
        self.assertEqual(relevant["factjournal_canon_writes"],0)

    def test_sword_unproven_old_debt_only_illuminates_relevant_goal(self):
        f=frame(SWORD,cast=("叶青梧","沈渡"))
        self.assertTrue(any(v["kind"]=="UNPROVEN_ITEM_TRANSFER"
                            for v in f["unresolved_open_debts"]))
        relevant=lamp(beat("action",actor="沈渡",
                       goal="沈渡伸手要取回剑穗",focus=[]),f=f)
        self.assertIn("transfer",relevant["risk_lamps"])
        self.assertIn("交接动作",relevant["prompt"])
        unrelated=lamp(beat("quiet",actor="沈渡",
                       goal="沈渡在桥上听雨",focus=[]),f=f)
        self.assertNotIn("transfer",unrelated["risk_lamps"])

    def test_a_single_craft_question_at_a_time_with_real_cooldown(self):
        b=beat("decision",goal="是否破釜沉舟救同伴",focus=["interiority","detail"])
        one=lamp(b)
        self.assertIsNotNone(one["craft_id"])
        self.assertEqual(one["prompt"].count("【本段至多一个"),1)
        two=lamp(b,turn=1,prior=one)
        self.assertIsNone(two["craft_id"])
        self.assertEqual(two["craft_suppression"],"CRAFT_COOLDOWN_LAST_TWO_TURNS")
        three=lamp(b,turn=2,prior=two)
        self.assertIsNone(three["craft_id"])
        four=lamp(b,turn=3,prior=three)
        self.assertIsNotNone(four["craft_id"])
        self.assertNotIn("万能模板",four["prompt"])

    def test_explicit_none_focus_is_not_overridden_by_default_decision(self):
        x=lamp(beat("decision",focus=["none"]))
        self.assertEqual(x["prompt"],"")
        self.assertIsNone(x["craft_id"])

    def test_source_knowledge_only_if_active_person_is_same_pov(self):
        f=frame()
        f["knowledge"]={"known":[],"unknown":[{"fact_key":"密令真正主人"}],
                        "suspected":[],"false_beliefs":[]}
        f["pov_character_id"]="沈砚"
        one=lamp(beat("decision",actor="沈砚",focus=["none"]),f=f)
        self.assertIn("knowledge",one["risk_lamps"])
        two=lamp(beat("decision",actor="唐蜃",focus=["none"]),f=f)
        self.assertNotIn("knowledge",two["risk_lamps"])

    def test_mutated_or_cross_novel_receipt_is_never_trusted(self):
        one=lamp(beat("decision"))
        counterfeit=json.loads(json.dumps(one))
        counterfeit["prompt"]="额外注入秘密"
        with self.assertRaises(LampDecisionError):
            lamp(beat("decision"),prior=counterfeit,turn=1)
        with self.assertRaises(LampDecisionError):
            lamp(beat("decision"),prior=one,turn=1,project="other-story")
        with self.assertRaises(LampDecisionError):
            lamp(beat("decision"),prior=one,turn=3)

    def test_existing_single_route_stays_explicit_and_no_new_llm_calls(self):
        src=(Path(__file__).resolve().parents[1]/
             "writerforge/writing_assist.py").read_text("utf8")
        # V121 keeps the old single route unchanged, while moving opt-in
        # continuity lamps into a budget-guarded packet assembly helper.
        self.assertIn('if draft_mode=="single":',src)
        self.assertIn('_prepare_guarded_turn_packet(',src)
        self.assertIn('lamps=plan_scene_lamps(',src)
        self.assertIn('"v118_event_lamp_decisions"',src)
        self.assertNotIn("openai.ChatCompletion",src)
        self.assertFalse(hasattr(plan_scene_lamps,"model"))

if __name__=="__main__":
    unittest.main()
