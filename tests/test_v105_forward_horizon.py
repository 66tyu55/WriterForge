"""V105 no-network future state and long-horizon debt regression.

All stories here are SYNTHETIC and never represent expert literary judgement.
No real models, billing, R2, FactJournal or user novels touched.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import json
import unittest

from writerforge.v105_forward_horizon import (
    validate_horizon,horizon_prompt,horizon_context,
    derive_open_checkpoint,open_debt_context,
    V105FutureCausalityError,digest,packed,MAX_DEBTS,
)
from test_v102_emotional_causality import accepted as old_two

STORY_SHA=sha256("新的小说大纲".encode("utf8")).hexdigest()

def requirement(key,value):
    return {"key":key,"is":value}

def change(key,value):
    return {"key":key,"becomes":value}

def debt(id="lose_power",owner="林霁",kind="RESOURCE",severity="COSTLY"):
    return {
        "id":id,"kind":kind,"owner":owner,
        "pressure":"用于驱赶危险的能源在关键时刻被关闭了",
        "if_ignored":"下一幕使用设备时可能无法获得实际动力",
        "due_after":2,"severity":severity,
    }

def step(id,*,requires=(),sets=(),future_debts=(),claims_resolved=(),
         actor="林霁",action="到现场核实闸轮是否还能运转再作选择"):
    return {
        "id":id,"actor":actor,"action":action,
        "requires":list(requires),"sets":list(sets),
        "future_debts":list(future_debts),
        "claims_resolved":list(claims_resolved),
    }

def simple_branches():
    return {"choices":[
        {"id":"path_a","steps":[
            step("cut_power",requires=[requirement("power:station","on")],
                 sets=[change("power:station","off")],
                 future_debts=[debt()]),
            step("run_drill",requires=[requirement("power:station","on")],
                 action="再启动耗电钻头制造声波"),
        ]},
        {"id":"path_b","steps":[
            step("check_battery",requires=[requirement("battery:tool","ready")],
                 action="先查是否有独立蓄电池"),
            step("power_own_tool",requires=[
                requirement("battery:tool","ready")],
                 action="用独立供电驱赶异物",
                 future_debts=[debt("battery_empty",severity="POSSIBLE")]),
        ]},
    ]}

class FutureWorldTests(unittest.TestCase):
    def test_preflight_detects_real_internal_power_dependency_threat(self):
        test=validate_horizon(simple_branches(),
                              author_pinned={"power:station":"on"})
        a,b=test["branches"]
        self.assertEqual(a["status"],"SYMBOLICALLY_BLOCKED")
        self.assertEqual(b["status"],"CONDITIONAL_OR_UNKNOWN")
        self.assertIn("THREATENS_PREVIOUS_PLANNED_EFFECT",
                      [x["kind"] for x in a["all_findings"]])
        self.assertIn("UNPROVEN_PRECONDITION",
                      [x["kind"] for x in b["all_findings"]])
        self.assertEqual(len(a["forecast_debts"]),1)
        self.assertTrue(a["forecast_debts"][0]["forecast_only"])
        self.assertTrue(test["all_proposed_future_effects_unverified"])
        self.assertFalse(test["literary_causality_proven"])
        self.assertIsNone(test["choice_selected_by_software"])
        self.assertEqual(test["model_calls_for_validation"],0)
        context=horizon_context(test)
        self.assertIn("再启动耗电钻头制造声波",context)
        self.assertIn("THREATENS_PREVIOUS_PLANNED_EFFECT",context)
        self.assertIn("未来只是假设",context)
        self.assertIn("模型不得偷偷扩充",horizon_prompt())

    def test_author_facts_are_immutable_and_unknown_is_not_false(self):
        source={"power:station":"off"}
        cases=deepcopy(simple_branches())
        result=validate_horizon(cases,author_pinned=source)
        self.assertEqual(source,{"power:station":"off"})
        self.assertIn("CONTRADICTS_PINNED_FACT",[
            z["kind"] for z in result["branches"][0]["all_findings"]])
        self.assertTrue(all(x["semantic_writing_feasibility_verified"] is False
                            for x in result["branches"]))
        without=validate_horizon(cases,author_pinned={})
        self.assertIn("UNPROVEN_PRECONDITION",[
            z["kind"] for z in without["branches"][0]["all_findings"]])
        self.assertNotEqual(
            without["pinned_author_facts_sha256"],
            result["pinned_author_facts_sha256"])

    def test_future_payment_claim_never_clears_forecast_cost(self):
        data=simple_branches()
        data["choices"][0]["steps"][1]["claims_resolved"]=["lose_power"]
        final=validate_horizon(data,author_pinned={"power:station":"on"})
        path=final["branches"][0]
        self.assertIn("FUTURE_SETTLEMENT_ONLY_NOT_YET_PAID",
                      [x["kind"] for x in path["all_findings"]])
        self.assertEqual(len(path["forecast_debts"]),1)
        self.assertTrue(final["future_debts_not_yet_paid_or_incurred"])
        text=horizon_context(final)
        self.assertIn("只是假设",text)

    def test_two_distinct_quiet_future_paths_are_permitted(self):
        obj={"choices":[
            {"id":"calm_day","steps":[step("visit_neighbor",action=
             "两人安静拜访邻居，听一段无人打断的家常话")]},
            {"id":"quiet_wait","steps":[step("wait_rain",action=
             "两人留在屋内慢慢等待雨停，不一定有损失")]}
        ]}
        report=validate_horizon(obj)
        self.assertEqual([b["status"] for b in report["branches"]],
              ["NOT_CONTRADICTED_BY_KNOWN_SYMBOLS"]*2)
        self.assertFalse(any(b["forecast_debts"] for b in report["branches"]))

    def test_reject_duplicate_future_events_and_debts_and_fake_proof(self):
        obj=simple_branches()
        obj["choices"][0]["steps"][1]["id"]="cut_power"
        with self.assertRaisesRegex(V105FutureCausalityError,"FUTURE_STEP"):
            validate_horizon(obj)
        obj=simple_branches()
        obj["choices"][0]["steps"][1]["future_debts"]=[debt()]
        with self.assertRaisesRegex(V105FutureCausalityError,"PROPOSED_DEBT_REPEATED"):
            validate_horizon(obj)
        good=validate_horizon(simple_branches())
        good["branches"][0]["status"]="NOT_CONTRADICTED_BY_KNOWN_SYMBOLS"
        with self.assertRaisesRegex(V105FutureCausalityError,"VALIDATED_FORECAST"):
            horizon_context(good)
        obj=simple_branches()
        obj["choices"][0]["steps"][1]["claims_resolved"]=["not_created"]
        with self.assertRaisesRegex(V105FutureCausalityError,
                                    "CANNOT_RESOLVE_AN_UNCREATED"):
            validate_horizon(obj)

    def test_hidden_spoilers_and_untrusted_pins_are_not_injected(self):
        instructions=horizon_prompt()
        self.assertNotIn("original novel sentence",instructions)
        self.assertIn("不能偷偷扩充",instructions)
        with self.assertRaisesRegex(V105FutureCausalityError,"PINNED_AUTHOR"):
            validate_horizon(simple_branches(),
                             author_pinned={"Power Invalid Key":"on"})
        with self.assertRaisesRegex(V105FutureCausalityError,"FORECAST_JSON"):
            validate_horizon('{"choices":[],"choices":[]}')

class CheckpointTests(unittest.TestCase):
    def test_observed_quote_cost_is_not_truth_but_open_across_three_chapters(self):
        pair=old_two()
        chain=[]
        previous=None
        for chapter in range(1,4):
            cp=derive_open_checkpoint(
                story_sha=STORY_SHA,chapter=chapter,
                accepted=pair,previous=previous)
            self.assertEqual(cp["open_debts_count"],2*chapter)
            self.assertEqual(cp["auto_debt_settlements"],0)
            self.assertEqual(cp["new_debts"],2)
            self.assertFalse(cp["literary_semantics_verified"])
            self.assertEqual(cp["canon_writes"],0)
            self.assertEqual(cp["previous_checkpoint_sha256"],
                             previous["receipt_sha256"] if previous else None)
            self.assertEqual(cp["receipt_sha256"],digest(packed(
                {k:v for k,v in cp.items() if k!="receipt_sha256"})))
            chain.append(cp)
            previous=cp
        context=open_debt_context(chain[2])
        self.assertIn("不能因一句承诺自动清零",context)
        self.assertIn("朋友仍在城中等药",context)
        self.assertNotIn("事实已得到证明",context)

    def test_forged_settlement_and_wrong_story_cannot_replay_or_resolve(self):
        one=derive_open_checkpoint(story_sha=STORY_SHA,chapter=1,
                                  accepted=old_two())
        old=deepcopy(one)
        old["open_debts"][0]["state"]="PAID"
        with self.assertRaisesRegex(V105FutureCausalityError,"CHECKPOINT_HASH"):
            derive_open_checkpoint(story_sha=STORY_SHA,chapter=2,
                                  accepted=old_two(),previous=old)
        old=deepcopy(one)
        old["literary_semantics_verified"]=True
        with self.assertRaisesRegex(V105FutureCausalityError,"WRONG_STORY"):
            derive_open_checkpoint(story_sha=STORY_SHA,chapter=2,
                                  accepted=old_two(),previous=old)
        with self.assertRaisesRegex(V105FutureCausalityError,"WRONG_STORY"):
            derive_open_checkpoint(story_sha="0"*64,chapter=2,
                                  accepted=old_two(),previous=one)
        with self.assertRaisesRegex(V105FutureCausalityError,"CHAPTER_GAP"):
            derive_open_checkpoint(story_sha=STORY_SHA,chapter=3,
                                  accepted=old_two(),previous=one)

    def test_bad_v102_prose_and_overcrowded_history_never_silently_forgot(self):
        pair=list(old_two())
        pair[0]=deepcopy(pair[0])
        pair[0]["prose"]="文稿已被改动"
        with self.assertRaisesRegex(Exception,"RECEIPT_CORRUPT"):
            derive_open_checkpoint(story_sha=STORY_SHA,chapter=1,
                                   accepted=pair)
        history=derive_open_checkpoint(story_sha=STORY_SHA,
                                      chapter=1,accepted=old_two())
        # The full debt state is never "summarized away" by projection.
        for chapter in range(2,24):
            history=derive_open_checkpoint(story_sha=STORY_SHA,
                chapter=chapter,accepted=old_two(),previous=history)
        self.assertEqual(history["open_debts_count"],46)
        self.assertIn("还有",open_debt_context(history))
        with self.assertRaisesRegex(V105FutureCausalityError,
                                    "CAPACITY_REFUSE_SILENT_FORGET"):
            derive_open_checkpoint(story_sha=STORY_SHA,
                chapter=24,accepted=old_two(),previous=history)
        self.assertEqual(len(history["open_debts"]),46)

if __name__=="__main__":
    unittest.main()
