"""V98 synthetic 800/1600/3200/6400-character rolling causal stress.

NOT model-generated prose; measures quote/parent integrity with long drafts,
not literary quality or a universal 1000-character failure threshold.
"""
from __future__ import annotations
import json
import unittest
from writerforge.v96_causal_turns import parse_turn_outline,check_turn
from writerforge.v98_rolling_causal_planner import (
    validate_replan,V98RollingPlanError,
)

def plan(n=12):
    return parse_turn_outline(json.dumps({"turns":[{
        "id":f"t{i:02d}","kind":"action","actor":"行者",
        "goal":f"第{i}幕处理上一段封路带来的选择问题和新阻力",
        "causal_parent":None if i==1 else f"t{i-1:02d}",
        "craft_focus":["action"],
    } for i in range(1,n+1)]},ensure_ascii=False))

def sample(i,parent=None):
    a=f"行者把第{i}块旧木牌交给了山口守卫"
    e=f"山口守卫暂时封住第{i}条下山小路"
    context="山雾潮湿，行者忧心药箱迟到，但不清楚守卫为什么封路。伙伴催他确认危险与时间代价。"
    prose=(context*18)[:575]+a+"。众人尚未了解封锁的真正原因。"+e+"。"
    return json.dumps({"prose":prose,"trace":{
        "action_quote":a,"effect_quote":e,
        "parent_effect_quote":parent,
    }},ensure_ascii=False),e

def rolling(seed,parent):
    return json.dumps({
        "next_turn":{**seed,
           "goal":f"第{seed['id']}幕改按前一次实际封路安排查证和绕行"},
        "basis_effect_quote":parent,
        "pressure_quote":None,"cost_quote":None,
        "unresolved_question":"守卫为什么封路仍没有得到原文证实。",
        "reason_for_shift":"上一段实际出现封路，新的选择必须考虑前述真实后果。",
    },ensure_ascii=False)

class V98RollingLongStress(unittest.TestCase):
    def test_synthetic_chain_spans_all_length_thresholds(self):
        beats=plan()
        accepted=[];actual=[];effect=None;total=0
        reached={800:False,1600:False,3200:False,6400:False}
        for i,seed in enumerate(beats,1):
            if i>1:
                beat,receipt=validate_replan(
                    rolling(seed,effect),accepted=tuple(accepted),
                    accepted_beats=tuple(actual),
                    seed_next_beat=seed,allowed_actor_names=("行者",))
                self.assertTrue(receipt["changed_from_frozen_seed"])
            else:beat=seed
            raw,new_effect=sample(i,effect)
            done=check_turn(raw,beat,mode="causal_guard",
                            accepted=tuple(accepted))
            accepted.append(done);actual.append(beat)
            effect=new_effect
            total+=len(done["prose"])+2
            for threshold in reached:
                if total>=threshold:reached[threshold]=True
        self.assertTrue(all(reached.values()),reached)
        self.assertGreaterEqual(total,6400)
        self.assertEqual(len(accepted),12)
        self.assertTrue(all(not t["receipt"][
            "literary_causality_independently_verified"] for t in accepted))

    def test_after_1000_chars_forged_prior_effect_fails(self):
        beats=plan(4); accepted=[];last=None
        for i in (1,2):
            raw,last=sample(i,last)
            accepted.append(check_turn(
                raw,beats[i-1],mode="causal_guard",
                accepted=tuple(accepted)))
        self.assertGreater(sum(len(x["prose"]) for x in accepted),1000)
        forged=rolling(beats[2],"传说行者早已查出了所有凶手")
        with self.assertRaisesRegex(V98RollingPlanError,
                                    "NOT_ANCHORED_TO_ACTUAL_EFFECT"):
            validate_replan(forged,accepted=tuple(accepted),
                accepted_beats=beats[:2],seed_next_beat=beats[2],
                allowed_actor_names=("行者",))

if __name__=="__main__":
    unittest.main()
