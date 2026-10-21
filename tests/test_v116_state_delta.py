"""V116 zero-inference end-to-end event->MIT reducer->next-write preflight.

Synthetic fixtures only; separate V116 sealed runner cold reads genuine R2
manuscripts with immutable SHA checks. Never writes facts or charges tokens.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from writerforge.v116_state_delta import (
    extract_state_events,preflight_next_prose,compact_verified_delta_context,
)
from writerforge.v114_external_story_state import external_temporal_step,temporal_prompt

CAST=("沈砚","唐蜃")
SOURCE=(
    "沈砚看见火髓果已经发热。"
    "沈砚没应声，把果子往齿间一咬，苦味涌上舌尖。"
    "他右手撑住炉沿要翻身，半空里忽然一麻——锁脉诀到了。"
    "灵力从肘弯往下被截断，手指头瞬间不听使唤，整个人斜栽。"
    "炉壁里的丹火忽然舔上他右前臂，烧出焦臭。"
    "唐蜃收诀了。"
    "沈砚左手一撑灰堆，右臂甩在身后像条死口袋。"
    "唐蜃大叫：“你右臂废了也敢跑。”"
    "沈砚把果子从齿间吐到左手心，攥紧。"
    "右臂垂着，他不敢再用它支撑身体。"
)


def cells(state):
    out={}
    for key,value in state.items():
        domain,entity,predicate,scope,_=json.loads(key)
        out[(domain,entity,predicate,scope)]=value
    return out


class ActualPinnedTemporalBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("node"):
            raise RuntimeError("WF116_NODE_22_REQUIRED")

    def test_chinese_fruit_hold_handoff_arm_disability_and_burn(self):
        proposal=extract_state_events(SOURCE,cast=CAST)
        events=proposal["source_anchored_events"]
        self.assertEqual(proposal["model_calls"],0)
        self.assertEqual(proposal["canonical_fact_writes"],0)
        self.assertGreaterEqual(len(events),4,events)
        self.assertFalse(any(op["cell"]["entityId"]=="唐蜃"
            for ev in events for op in ev["ops"] if
            op["cell"]["domain"]=="character"),events)
        self.assertTrue(all(SOURCE.count(e["evidence"]["quote"])==1 for e in events))
        fruit=[e for e in events if e["ops"][0]["cell"]["entityId"]=="火髓果"]
        self.assertEqual(len(fruit),2,fruit)
        self.assertEqual(fruit[0]["ops"][0]["expected"],{"kind":"missing"})
        self.assertEqual(fruit[0]["ops"][0]["value"],"沈砚齿间")
        self.assertEqual(fruit[1]["ops"][0]["expected"],
                         {"kind":"value","value":"沈砚齿间"})
        self.assertEqual(fruit[1]["ops"][0]["value"],"沈砚左手心")
        self.assertNotIn("已消耗",str(events))
        self.assertNotIn("永久",str(events))
        temporal=external_temporal_step(SOURCE,cast=CAST)
        output=temporal["reducer_result"]
        self.assertGreaterEqual(output["verified_events"],4,output)
        status=cells(output["candidate_state"])
        self.assertEqual(status[("item","火髓果","holder","author_plan")],
                         "沈砚左手心")
        self.assertEqual(status[("character","沈砚","右臂可用性","author_plan")],
                         "受限")
        self.assertEqual(status[("character","沈砚","右臂伤情","author_plan")],
                         "丹火灼及右前臂")
        self.assertNotIn(("item","火髓果","consumption","author_plan"),status)
        self.assertIn("右臂",temporal_prompt(temporal))
        self.assertIn("左手心",temporal_prompt(temporal))
        self.assertEqual(temporal["canon_writes"],0)
        self.assertFalse(temporal["semantic_truth_verified"])

    def test_next_scene_without_resource_or_healing_cannot_magically_pass(self):
        earlier=external_temporal_step(SOURCE,cast=CAST)
        state=earlier["reducer_result"]["candidate_state"]
        invalid=("沈砚右臂挥剑冲向唐蜃，火髓果还在齿间。"
                 "他法力忽然回涨三成，旧伤顷刻消失。")
        failure=preflight_next_prose(invalid,previous_candidate_state=state)
        self.assertTrue(failure["blocked"])
        self.assertIn("WF116_ARM_USED_WITHOUT_RECOVERY",failure["findings"])
        self.assertIn("WF116_ENERGY_RECOVERY_WITHOUT_SOURCE",failure["findings"])
        allowed=("沈砚将火髓果紧攥在左手心，用肩膀撞开旧石门。"
                 "右臂依然垂着，手腕上的血沿布条渗下，他仍在逃。")
        ok=preflight_next_prose(allowed,previous_candidate_state=state)
        self.assertFalse(ok["blocked"],ok)

    def test_real_novel_studio_checks_wrong_before_and_preserves_state(self):
        first=external_temporal_step(SOURCE,cast=CAST)
        next_text=("沈砚把火髓果从左手心送入口中，咬碎吞下。"
                   "右臂仍然灼痛，他只用左手扶着石壁前进。")
        later=extract_state_events(next_text,cast=CAST,
            prior_state=first["reducer_result"]["candidate_state"])
        self.assertTrue(any(
            op["cell"]["predicate"]=="consumption" for e in later["source_anchored_events"]
            for op in e["ops"]),later)
        accepted=external_temporal_step(next_text,cast=CAST,prior=first)
        status=cells(accepted["reducer_result"]["candidate_state"])
        self.assertEqual(status[("item","火髓果","holder","author_plan")],
                         "已消耗（沈砚吞服）")
        self.assertEqual(status[("item","火髓果","consumption","author_plan")],
                         "明确吞服")
        self.assertEqual(accepted["canon_writes"],0)
        bad_prose="唐蜃从沈砚左手心夺走火髓果。"
        packet={
          "format":"wf.fallback.novel-studio.input.v114",
          "source_prose":bad_prose,
          "prior_state":first["reducer_result"]["candidate_state"],
          "events":[{
            "id":"bad_old",
            "evidence":{"quote":bad_prose,"start":0,"end":len(bad_prose),
                        "narrative":"present"},
            "ops":[{"type":"set",
                   "cell":{"domain":"item","entityId":"火髓果",
                           "predicate":"holder","scope":"author_plan"},
                   "expected":{"kind":"value","value":"唐蜃手中"},
                   "value":"唐蜃手中"}],
          }],
        }
        shim=Path(__file__).resolve().parents[1]/"experiments"/"v114_fallback_novel_studio"/"bridge.mjs"
        result=subprocess.run(["node",str(shim)],
              input=json.dumps(packet,ensure_ascii=False),
              capture_output=True,text=True,timeout=10,check=True)
        wrong=json.loads(result.stdout)
        self.assertEqual(wrong["error_code"],"PRECONDITION_FAILED",wrong)
        self.assertEqual(wrong["candidate_state"],
                         first["reducer_result"]["candidate_state"])

    def test_dialogue_dream_and_mentions_never_count_as_consumption(self):
        alleged=("沈砚捡到火髓果。唐蜃说道：“沈砚把果子吞了。”"
                 "沈砚梦见自己把果子往齿间一咬，法力恢复了。"
                 "醒来后他望着右臂，完全想不起先前发生了什么。")
        row=extract_state_events(alleged,cast=CAST)
        self.assertFalse(any(e["ops"][0]["cell"]["domain"]=="item"
                             for e in row["source_anchored_events"]),row)
        self.assertEqual(row["canonical_fact_writes"],0)

    def test_sword_tassel_old_holder_not_erased_by_unsupported_position(self):
        src=("沈渡腰间挂着旧剑穗。"
             "叶青梧跌下栈道。沈渡抖出锁魂索。"
             "索头回落，钩尖上挂着一截湿透的旧剑穗。")
        report=external_temporal_step(src,cast=("叶青梧","沈渡"))
        self.assertIn("UNPROVEN_ITEM_TRANSFER",
                      [x["kind"] for x in report["reducer_result"]["risks"]])
        self.assertIn("沈渡",str(report["reducer_result"]["candidate_state"]))
        self.assertNotIn("索钩",str(report["reducer_result"]["candidate_state"]))
        self.assertFalse(report["semantic_truth_verified"])
        self.assertEqual(report["canon_writes"],0)

if __name__=="__main__":
    unittest.main()
