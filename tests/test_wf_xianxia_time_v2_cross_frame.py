"""RED-first xianxia time V2 movement regression, not another world module.

A real bug: time_v2 fixes actor.frame for life. Once someone leaves a
3x-time cave, merely setting story text to 'outside' does NOT change their
clock. The new cross_frame time action must account for a physical crossing,
both frames, and every offscreen actor's concurrent life.
"""
from __future__ import annotations
from pathlib import Path
import json,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/".agents/skills/xianxia-time-rule/scripts"))
import time_v2 as t

def seed_world():
    return json.loads((ROOT/"experiments/wf_xianxia_time_v2_frozen_world_20261113.json").read_text("utf-8"))["rate3"]

def cultivate():
    return {"kind":"advance","world_hours":6,
            "activities":{"P001":"cultivate","N001":"work"}}

def exit_cave(origin=1,destination=1,**extra):
    return {"kind":"cross_frame","actor_id":"P001","to_frame":"outside",
            "origin_world_hours":origin,"destination_world_hours":destination,
            "activities":{"N001":"work"},**extra}

class CrossFrameTimeTests(unittest.TestCase):
    def test_crossing_real_frames_uses_two_rates_and_charges_npc_time(self):
        end=t.replay(seed_world(),[cultivate(),exit_cave()])["final"]
        self.assertEqual(end["world_clock"]["hour"],1008)
        self.assertEqual(end["actors"]["P001"]["frame"],"outside")
        self.assertEqual(end["actors"]["P001"]["lived_subjective_hours"],"22")
        self.assertEqual(end["actors"]["P001"]["age_subjective_hours"],"150022")
        self.assertEqual(end["actors"]["P001"]["cultivation_subjective_hours"],"24")
        self.assertEqual(end["actors"]["N001"]["lived_subjective_hours"],"8")
        self.assertEqual(end["actors"]["N001"]["age_subjective_hours"],"220008")

    def test_after_leaving_cave_ordinary_outside_hours_stop_tripling(self):
        outcome=t.replay(seed_world(),[cultivate(),exit_cave(),
            {"kind":"advance","world_hours":1,"activities":{"P001":"work"}}])
        end=outcome["final"]
        self.assertEqual(end["world_clock"]["hour"],1009)
        self.assertEqual(end["actors"]["P001"]["lived_subjective_hours"],"23")
        self.assertEqual(end["actors"]["N001"]["lived_subjective_hours"],"9")
        self.assertEqual(end["actors"]["P001"]["cultivation_subjective_hours"],"24")

    def test_cave_exit_is_not_instant_teleport(self):
        with self.assertRaisesRegex(t.TimeV2Error,"CROSSING_REQUIRES_ELAPSED_WORLD_TIME"):
            t.replay(seed_world(),[exit_cave(0,0)])
        with self.assertRaisesRegex(t.TimeV2Error,"CROSSING_TARGET_UNKNOWN"):
            t.replay(seed_world(),[exit_cave(1,1,to_frame="nonexistent")])

    def test_move_does_not_create_cultivation_credit(self):
        end=t.replay(seed_world(),[cultivate(),exit_cave(2,1)])["final"]
        self.assertEqual(end["actors"]["P001"]["cultivation_subjective_hours"],"24")
        self.assertEqual(end["actors"]["P001"]["lived_subjective_hours"],"25")
        self.assertEqual(end["world_clock"]["hour"],1009)

    def test_ordinary_npc_can_cultivate_while_actor_crosses(self):
        e=exit_cave(1,1)
        e["activities"]={"N001":"cultivate"}
        end=t.replay(seed_world(),[cultivate(),e])["final"]
        self.assertEqual(end["actors"]["N001"]["cultivation_subjective_hours"],"2")
        self.assertEqual(end["actors"]["N001"]["lived_subjective_hours"],"8")

    def test_cave_return_only_after_reverse_crossing(self):
        rev={"kind":"cross_frame","actor_id":"P001","to_frame":"cave",
             "origin_world_hours":1,"destination_world_hours":1,
             "activities":{"N001":"work"}}
        end=t.replay(seed_world(),[cultivate(),exit_cave(),rev,
            {"kind":"advance","world_hours":1,"activities":{"P001":"cultivate"}}])["final"]
        self.assertEqual(end["actors"]["P001"]["frame"],"cave")
        self.assertEqual(end["actors"]["P001"]["lived_subjective_hours"],"29")
        self.assertEqual(end["actors"]["P001"]["cultivation_subjective_hours"],"27")
        self.assertEqual(end["actors"]["N001"]["lived_subjective_hours"],"11")

    def test_world_deadline_still_passes_during_crossing(self):
        events=[cultivate(),exit_cave(),
                {"kind":"attempt","actor_id":"P001","outcome":"success"},
                {"kind":"use_technique","actor_id":"P001"}]
        output=t.replay(seed_world(),events)["final"]
        self.assertEqual(output["world_clock"]["hour"],1008)
        with self.assertRaisesRegex(t.TimeV2Error,"TECHNIQUE_AFTER_DEADLINE"):
            t.replay(seed_world(),events[:3]+[
                {"kind":"advance","world_hours":1,"activities":{}},
                events[3]])

    def test_actor_cannot_fraud_teleport_or_claim_unknown_crossing_training(self):
        e=exit_cave()
        e["activities"]["P001"]="cultivate"
        with self.assertRaisesRegex(t.TimeV2Error,"CROSSING_ACTOR_MUST_TRAVEL"):
            t.replay(seed_world(),[e])
        with self.assertRaisesRegex(t.TimeV2Error,"CROSSING_ALREADY_IN_FRAME"):
            w=seed_world()
            w["actors"]["P001"]["frame"]="outside"
            t.replay(w,[exit_cave()])

if __name__=="__main__":
    unittest.main()
