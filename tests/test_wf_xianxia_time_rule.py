"""Time-axis tests: causal rules must change outcomes, not just decorate prompts."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

ROOT=(Path(__file__).resolve().parents[1] /
      ".agents/skills/xianxia-time-rule/scripts")
sys.path.insert(0,str(ROOT))
from time_kernel import (
    TimeParameters,TimeWorldRule,TimeRuleError,apply,replay,
    audit_candidate,random_character,parameter_fingerprint
)


def start():
    return TimeParameters(world_day=100,cultivation_days=4,
                          bodily_age_days=6120,era="第七纪",realm_step=1)

def policy(required=12):
    return TimeWorldRule(required_training_days_for_next_stage=required,
                         deadline_world_day=115)

def advance_then_breakthrough():
    return [
        {"kind":"work","days":2},
        {"kind":"cultivate","days":8},
        {"kind":"attempt_breakthrough","days":0,"outcome":"success"},
        {"kind":"activate_barrier","days":0}
    ]


class XianxiaTimeRuleTests(unittest.TestCase):
    def test_actor_random_seed_is_frozen_not_chosen_to_fit_story(self):
        person=random_character(20261113)
        self.assertEqual(person["role"],"灵田佃户")
        self.assertEqual(person["temperament"],"谨慎却倔强")
        self.assertEqual(person,random_character(20261113))

    def test_independent_clocks_and_no_automatic_breakthrough(self):
        result=replay(policy(),start(),[
            {"kind":"work","days":3},
            {"kind":"travel","days":2},
            {"kind":"cultivate","days":7},
            {"kind":"rest","days":1}])
        final=result["final"]
        self.assertEqual(final["world_day"],113)
        self.assertEqual(final["cultivation_days"],11)
        self.assertEqual(final["bodily_age_days"],6133)
        self.assertEqual(final["era"],"第七纪")
        self.assertEqual(final["realm_step"],1)
        self.assertFalse(result["story_text_consistency_independently_proven"])

    def test_alter_one_time_parameter_changes_same_actions_eligibility(self):
        original=advance_then_breakthrough()
        yes=replay(policy(12),start(),original)
        self.assertEqual(yes["final"]["realm_step"],2)
        self.assertEqual(yes["final"]["world_day"],110)
        self.assertEqual(yes["final"]["cultivation_days"],12)
        with self.assertRaisesRegex(TimeRuleError,"BREAKTHROUGH_TOO_EARLY"):
            replay(policy(24),start(),original)
        self.assertNotEqual(parameter_fingerprint(policy(12),start()),
                            parameter_fingerprint(policy(24),start()))

    def test_world_time_passes_during_travel_but_not_training(self):
        s,_=apply(start(),{"kind":"travel","days":12},policy())
        self.assertEqual(s.cultivation_days,4)
        self.assertEqual(s.world_day,112)
        with self.assertRaisesRegex(TimeRuleError,"BREAKTHROUGH_TOO_EARLY"):
            apply(s,{"kind":"attempt_breakthrough","days":0,
                     "outcome":"success"},policy())

    def test_training_eligibility_does_not_force_breakthrough(self):
        s,_=apply(start(),{"kind":"cultivate","days":11},policy())
        self.assertEqual(s.cultivation_days,15)
        self.assertEqual(s.realm_step,1)
        failed,_=apply(s,{"kind":"attempt_breakthrough","days":0,
                          "outcome":"failure"},policy())
        self.assertEqual(failed.realm_step,1)

    def test_unrelated_era_transition_is_explicit_and_not_a_time_jump(self):
        trace=replay(policy(),start(),[
            {"kind":"remember_past_era","days":0,"past_era":"远古纪"},
            {"kind":"era_shift","days":0,"era_name":"第八纪"}])
        self.assertEqual(trace["final"]["world_day"],100)
        self.assertEqual(trace["final"]["cultivation_days"],4)
        self.assertEqual(trace["final"]["era"],"第八纪")
        self.assertIsNone(trace["trace"][0]["rule_note"]["past_era_exact_distance_days"])

    def test_breakthrough_after_deadline_cannot_use_barrier_earlier(self):
        with self.assertRaisesRegex(TimeRuleError,"BARRIER_AFTER_DEADLINE"):
            replay(policy(),start(),[
                {"kind":"cultivate","days":16},
                {"kind":"attempt_breakthrough","days":0,
                 "outcome":"success"},
                {"kind":"activate_barrier","days":0}])

    def test_unearned_barrier_and_unneeded_era_auto_transition_rejected(self):
        with self.assertRaisesRegex(TimeRuleError,"BARRIER_REQUIRES_ADVANCEMENT"):
            replay(policy(),start(),[
                {"kind":"activate_barrier","days":0}])
        with self.assertRaisesRegex(TimeRuleError,
                                    "ERA_SHIFT_REQUIRES_EXPLICIT_NEW_ERA"):
            replay(policy(),start(),[
                {"kind":"era_shift","days":0,"era_name":"第七纪"}])

    def test_model_time_claims_must_match_replayed_time(self):
        example={"story":"山中洪水将至，佃户先去修渠，又在田边练功数日。即使修为已经达到尝试的条件，他仍可以选择暂时不突破。夜里他听说邻村的人已经挪走谷仓，不肯立即出手相助，但洪水并不会因为谁的犹豫而停下。",
                 "time_events":[
                   {"kind":"work","days":2,"world_day_after":102,
                    "cultivation_days_after":4},
                   {"kind":"cultivate","days":8,"world_day_after":110,
                    "cultivation_days_after":12},
                   {"kind":"attempt_breakthrough","days":0,"outcome":"failure",
                    "world_day_after":110,"cultivation_days_after":12}]}
        result=audit_candidate(policy(),start(),example)
        self.assertEqual(result["mechanical_time_gate"],"PASS")
        self.assertEqual(result["realm_step"],1)
        bad={"story":example["story"],"time_events":[dict(x) for x in example["time_events"]]}
        bad["time_events"][1]["cultivation_days_after"]=20
        with self.assertRaisesRegex(TimeRuleError,"MODEL_TRAINING_TIME_MISMATCH"):
            audit_candidate(policy(),start(),bad)

    def test_negative_days_and_model_fraud(self):
        with self.assertRaisesRegex(TimeRuleError,"ACTION_DURATION_INVALID"):
            replay(policy(),start(),[{"kind":"cultivate","days":-1}])
        with self.assertRaisesRegex(TimeRuleError,"INSTANT_ACTION_MUST_NOT_SKIP_TIME"):
            replay(policy(),start(),[{"kind":"attempt_breakthrough",
                                      "days":8,"outcome":"success"}])
        with self.assertRaisesRegex(TimeRuleError,"ACTION_KIND_INVALID"):
            replay(policy(),start(),[{"kind":"time_travel_reset","days":0}])

    def test_name_and_temperament_do_not_change_clock_math(self):
        roles=[random_character(20261113),random_character(20261114)]
        self.assertNotEqual(roles[0]["role"],roles[1]["role"])
        outcome1=replay(policy(),start(),advance_then_breakthrough())
        outcome2=replay(policy(),start(),advance_then_breakthrough())
        self.assertEqual(outcome1["final"],outcome2["final"])


if __name__=="__main__":
    unittest.main()
