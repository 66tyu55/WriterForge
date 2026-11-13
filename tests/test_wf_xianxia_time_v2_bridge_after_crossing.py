"""RED-first: author-facing timing must update after cross_frame, not cite old cave."""
from __future__ import annotations
from pathlib import Path
import sys,json,unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/".agents/skills/xianxia-time-rule/scripts"))
import time_bridge as b

def worlds():
    return json.loads((ROOT/"experiments/wf_xianxia_time_v2_frozen_world_20261113.json").read_text("utf-8"))

SIX={"kind":"advance","world_hours":6,"activities":{"P001":"cultivate","N001":"work"}}
MOVE={"kind":"cross_frame","actor_id":"P001","to_frame":"outside",
      "origin_world_hours":1,"destination_world_hours":1,
      "activities":{"N001":"work"}}

class AuthorAfterCrossingTests(unittest.TestCase):
    def test_author_recomputes_current_reference_frame_after_exit(self):
        w=b.time_window(worlds()["rate3"],[SIX,MOVE])
        self.assertEqual(w["world_hour_now"],1008)
        self.assertEqual(w["actor_current_time_frame"],"outside")
        self.assertEqual(w["actor_time_rate_subjective_per_world_hour"],"1")
        self.assertEqual(w["actor_subjective_hours_elapsed"],"22")
        self.assertEqual(w["offscreen_npc_clocks"]["N001"]["lived_subjective_hours"],"8")
        self.assertEqual(w["world_hours_left"],0)
        self.assertIn("洞外", b.concise_context(w))

    def test_time_to_train_uses_current_zone_and_deadline(self):
        w=b.time_window(worlds()["rate1"],[SIX])
        self.assertEqual(w["actor_current_time_frame"],"cave")
        self.assertEqual(w["actor_time_rate_subjective_per_world_hour"],"1")
        self.assertEqual(w["world_hours_of_continuous_training_needed"],"8")
        self.assertFalse(w["time_requirement_reachable_before_deadline"])
        z=b.time_window(worlds()["rate3"],[SIX])
        self.assertEqual(z["actor_time_rate_subjective_per_world_hour"],"3")
        self.assertEqual(z["world_hours_of_continuous_training_needed"],"0")
        self.assertTrue(z["time_requirement_reachable_before_deadline"])
        self.assertTrue(z["breakthrough_not_guaranteed"])

    def test_exiting_no_longer_uses_cave_rate_for_future_training(self):
        w=b.time_window(worlds()["rate1"],[SIX,MOVE])
        self.assertEqual(w["actor_current_time_frame"],"outside")
        self.assertEqual(w["world_hours_of_continuous_training_needed"],"8")
        self.assertFalse(w["time_requirement_reachable_before_deadline"])

    def test_writer_context_never_claims_training_alone_forces_success(self):
        w=b.time_window(worlds()["rate3"],[SIX])
        desc=b.concise_context(w)
        self.assertIn("主观",desc)
        self.assertIn("洞府",desc)
        self.assertIn("仍可能",desc)
        self.assertNotIn("必定突破",desc)

if __name__=="__main__":
    unittest.main()
