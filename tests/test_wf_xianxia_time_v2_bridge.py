"""Author-facing time constraints must change only with one time parameter."""
from __future__ import annotations
from pathlib import Path
from copy import deepcopy
import json,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/".agents/skills/xianxia-time-rule/scripts"))
import time_bridge as b
import time_v2 as t

def frozen():
    return json.loads((ROOT/"experiments/wf_xianxia_time_v2_frozen_world_20261113.json").read_text("utf-8"))

def six():
    return [{"kind":"advance","world_hours":6,
             "activities":{"P001":"cultivate","N001":"work"}}]

class AuthorTimeWindowTests(unittest.TestCase):
    def test_one_changed_time_rate_changes_author_feasible_choice(self):
        d=frozen()
        diff=b.delta(d["rate1"],d["rate3"],six())
        self.assertTrue(diff["same_world_time"])
        self.assertTrue(diff["same_offscreen_clocks"])
        self.assertTrue(diff["eligibility_changed"])
        self.assertEqual(diff["normal"]["remaining_required_subjective_hours"],"8")
        self.assertEqual(diff["altered"]["remaining_required_subjective_hours"],"0")
        self.assertEqual(diff["normal"]["actor_real_cultivation_hours"],"12")
        self.assertEqual(diff["altered"]["actor_real_cultivation_hours"],"24")
        self.assertFalse(diff["normal"]["technique_can_be_used_now"])
        self.assertFalse(diff["altered"]["technique_can_be_used_now"])

    def test_time_window_has_no_names_or_predicted_ending(self):
        d=frozen()
        w=b.time_window(d["rate3"],six())
        text=b.concise_context(w)
        self.assertIn("已满足突破尝试",text)
        self.assertIn("外界还剩2小时",text)
        self.assertNotIn("必将突破",text)
        self.assertNotIn("河堤一定得救",text)
        self.assertTrue(w["breakthrough_not_guaranteed"])
        self.assertTrue(w["no_automatic_plot_event"])
        self.assertEqual(w["offscreen_npc_clocks"]["N001"]["lived_subjective_hours"],"6")

    def test_no_cultivation_during_wait(self):
        d=frozen()
        events=[{"kind":"advance","world_hours":6,
                 "activities":{"P001":"rest","N001":"work"}}]
        w=b.time_window(d["rate3"],events)
        self.assertEqual(w["actor_real_cultivation_hours"],"6")
        self.assertEqual(w["remaining_required_subjective_hours"],"14")

    def test_passed_deadline_does_not_stop_world(self):
        d=frozen()
        w=b.time_window(d["rate3"],[{"kind":"advance","world_hours":15,
             "activities":{"P001":"cultivate"}}])
        self.assertTrue(w["world_deadline_already_passed"])
        self.assertEqual(w["world_hours_left"],0)
        self.assertFalse(w["technique_can_be_used_now"])
        self.assertEqual(w["offscreen_npc_clocks"]["N001"]["lived_subjective_hours"],"15")

    def test_multiple_changes_cannot_be_called_one_parameter(self):
        d=frozen()
        bad=deepcopy(d["rate3"])
        bad["world_clock"]["deadline_hour"]=1007
        bad["technique"]["latest_world_hour"]=1007
        with self.assertRaisesRegex(t.TimeV2Error,"NOT_SINGLE_CAVE_RATE_DELTA"):
            b.delta(d["rate1"],bad,six())

if __name__=="__main__":unittest.main()
