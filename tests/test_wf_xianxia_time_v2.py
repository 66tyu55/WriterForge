"""Test xianxia time V2: independent parameter units and real rule effects."""
from __future__ import annotations
from pathlib import Path
from copy import deepcopy
import json,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/".agents/skills/xianxia-time-rule/scripts"))
import time_v2 as t

FIXTURE=ROOT/"experiments/wf_xianxia_time_v2_frozen_world_20261113.json"

def frozen():
    return json.loads(FIXTURE.read_text("utf-8"))

def step(hours=6,activity="cultivate"):
    return {"kind":"advance","world_hours":hours,
            "activities":{"P001":activity,"N001":"work"}}


class XianxiaTimeV2Tests(unittest.TestCase):
    def test_pinned_single_change_and_units(self):
        doc=frozen()
        x,y=doc["rate1"],doc["rate3"]
        self.assertTrue(t.validate(x))
        self.assertTrue(t.validate(y))
        self.assertEqual(set(t.parameter_dictionary()),{
            "world_clock.hour","time_frames.*",
            "actors.*.age_subjective_hours",
            "actors.*.lived_subjective_hours",
            "actors.*.cultivation_subjective_hours",
            "advancement.min_cultivation_subjective_hours",
            "technique.latest_world_hour","era_history"
        })
        z=deepcopy(x)
        z["time_frames"]["cave"]["numerator"]=3
        self.assertEqual(z,y)
        self.assertEqual(doc["random_character_seed"],20261113)

    def test_clock_exactly_separates_world_subjective_cultivation(self):
        doc=frozen()
        a=t.replay(doc["rate1"],[step()])["final"]
        b=t.replay(doc["rate3"],[step()])["final"]
        self.assertEqual(a["world_clock"]["hour"],1006)
        self.assertEqual(b["world_clock"]["hour"],1006)
        self.assertEqual(a["actors"]["P001"]["cultivation_subjective_hours"],"12")
        self.assertEqual(b["actors"]["P001"]["cultivation_subjective_hours"],"24")
        self.assertEqual(a["actors"]["P001"]["lived_subjective_hours"],"6")
        self.assertEqual(b["actors"]["P001"]["lived_subjective_hours"],"18")
        self.assertEqual(a["actors"]["N001"]["lived_subjective_hours"],"6")
        self.assertEqual(b["actors"]["N001"]["lived_subjective_hours"],"6")
        self.assertEqual(b["actors"]["N001"]["cultivation_subjective_hours"],"0")

    def test_single_parameter_changes_ability_not_the_outside_clock(self):
        doc=frozen()
        events=[step(),{"kind":"attempt","actor_id":"P001","outcome":"success"},
                {"kind":"use_technique","actor_id":"P001"}]
        ab=t.time_comparison(doc["rate1"],doc["rate3"],events)
        self.assertFalse(ab["original"]["accepted"])
        self.assertEqual(ab["original"]["rejection"],"BREAKTHROUGH_NOT_TIME_ELIGIBLE")
        self.assertTrue(ab["altered"]["accepted"])
        y=ab["altered"]["result"]
        self.assertEqual(y["final"]["world_clock"]["hour"],1006)
        self.assertEqual(y["final"]["actors"]["P001"]["realm_step"],2)
        self.assertEqual(y["final"]["actors"]["N001"]["age_subjective_hours"],"220006")
        self.assertEqual(ab["changed_parameter"],
                         "time_frames.cave.subjective_per_world_hour")

    def test_eligible_is_not_auto_success_and_early_failure_is_allowed(self):
        s=frozen()["rate3"]
        advanced=t.replay(s,[step()])
        self.assertEqual(advanced["final"]["actors"]["P001"]["realm_step"],1)
        failed=t.replay(s,[step(),
             {"kind":"attempt","actor_id":"P001","outcome":"failure"}])
        self.assertEqual(failed["final"]["actors"]["P001"]["realm_step"],1)
        early=t.replay(frozen()["rate1"],[step(),
             {"kind":"attempt","actor_id":"P001","outcome":"failure"}])
        self.assertEqual(early["final"]["actors"]["P001"]["realm_step"],1)

    def test_npc_not_named_in_activity_still_ages_no_false_training(self):
        a=t.replay(frozen()["rate3"],[{
            "kind":"advance","world_hours":6,"activities":{"P001":"cultivate"}}])
        self.assertEqual(a["final"]["actors"]["N001"]["age_subjective_hours"],"220006")
        self.assertEqual(a["final"]["actors"]["N001"]["cultivation_subjective_hours"],"0")
        self.assertTrue(a["trace"][0]["meta"]["unspecified_activity_is_unknown"])

    def test_non_cultivation_time_does_not_accumulate_credit(self):
        for activity in ("work","travel","rest","wait","unknown"):
            with self.subTest(activity=activity):
                r=t.replay(frozen()["rate3"],[step(activity=activity)])
                self.assertEqual(r["final"]["actors"]["P001"]["cultivation_subjective_hours"],"6")

    def test_world_does_not_stop_at_deadline(self):
        w=frozen()["rate3"]
        result=t.replay(w,[step(12)])
        self.assertEqual(result["final"]["world_clock"]["hour"],1012)
        with self.assertRaisesRegex(t.TimeV2Error,"TECHNIQUE_AFTER_DEADLINE"):
            t.replay(w,[step(12),
              {"kind":"attempt","actor_id":"P001","outcome":"success"},
              {"kind":"use_technique","actor_id":"P001"}])

    def test_false_time_free_rate_and_unregistered_zone_are_rejected(self):
        w=frozen()["rate3"]
        w["time_frames"]["cave"]={"numerator":0,"denominator":1}
        with self.assertRaisesRegex(t.TimeV2Error,"TIME_RATE_INVALID"):
            t.validate(w)
        w=frozen()["rate3"]
        w["actors"]["P001"]["frame"]="unearned_heaven"
        with self.assertRaisesRegex(t.TimeV2Error,"ACTOR_TIME_FRAME_UNKNOWN"):
            t.validate(w)

    def test_no_floating_point_magic_number_or_missing_units(self):
        w=frozen()["rate3"]
        w["advancement"]["min_cultivation_subjective_hours"]=20.0
        with self.assertRaisesRegex(t.TimeV2Error,"PARAMETER_MUST_BE_EXACT"):
            t.validate(w)
        w=frozen()["rate3"]
        del w["world_clock"]["unit"]
        with self.assertRaisesRegex(t.TimeV2Error,"WORLD_CLOCK_INVALID"):
            t.validate(w)

    def test_known_era_does_not_rewind_world(self):
        w=frozen()["rate1"]
        r=t.replay(w,[{"kind":"remember_past_era","era":"旧纪元"}])
        self.assertEqual(r["final"]["world_clock"]["hour"],1000)
        self.assertIsNone(r["final"]["era_history"]["past_exact_hours"])
        self.assertTrue(r["trace"][0]["meta"]["actual_past_time_unknown"])

    def test_cultivation_subjective_time_cannot_exceed_age(self):
        w=frozen()["rate3"]
        w["actors"]["P001"]["cultivation_subjective_hours"]="150001"
        with self.assertRaisesRegex(t.TimeV2Error,"CULTIVATION_EXCEEDS_AGE"):
            t.validate(w)

    def test_tampering_multiple_params_rejected_as_one_parameter_ablation(self):
        w=frozen()
        corrupted=deepcopy(w["rate3"])
        corrupted["advancement"]["min_cultivation_subjective_hours"]="18"
        with self.assertRaisesRegex(t.TimeV2Error,"NOT_A_SINGLE_TIME_RATE_ABLATION"):
            t.time_comparison(w["rate1"],corrupted,[step()])

    def test_fractional_frame_is_exact(self):
        w=frozen()["rate1"]
        w["time_frames"]["cave"]={"numerator":3,"denominator":2}
        final=t.replay(w,[step(1)])["final"]
        self.assertEqual(final["actors"]["P001"]["lived_subjective_hours"],"3/2")
        self.assertEqual(final["actors"]["P001"]["cultivation_subjective_hours"],"15/2")
        self.assertEqual(final["world_clock"]["hour"],1001)


if __name__=="__main__":unittest.main()
