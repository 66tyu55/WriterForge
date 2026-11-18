"""WF living-ecology mechanical tests; no independent NPC intelligence claim."""
import importlib.util
from pathlib import Path
import unittest


SOURCE = (Path(__file__).resolve().parents[1] / ".agents" / "skills"
          / "wf-living-ecology" / "scripts" / "ecology_shadow.py")
spec = importlib.util.spec_from_file_location("wf_living_ecology_shadow", SOURCE)
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


class LivingEcologyShadowTests(unittest.TestCase):
    def test_actor_plan_is_private_to_other_actor(self):
        w = lab.example()
        view = lab.actor_view(w, "A")
        self.assertNotIn("先压成本", str(view))
        self.assertNotIn("考虑浅水道", str(view))
        self.assertIn("明天讨钱", str(view))

    def test_writer_only_sees_visible_outcomes(self):
        w = lab.example()
        w = lab.submit_choice(w, "C", mode="ACT", intent="走芦苇水路",
             observed=[{"id":"boat","place":"渡口","outcome":"船离岸",
                        "visibility":"PRIVATE","witnesses":[]}],
             result="离岸，未证实抵达", evidence_refs=["test-source"])
        self.assertNotIn("船离岸", str(lab.writer_view(w, "A")))
        self.assertNotIn("亲人能否登船", str(lab.writer_view(w, "A")))
        self.assertFalse(lab.writer_view(w,"A")["offscreen_events_must_appear_in_prose"])

    def test_public_and_witnessed_distinct(self):
        w = lab.example()
        w = lab.submit_choice(w, "D", mode="ACT", intent="保米",
             observed=[{"id":"sacks","place":"米铺","outcome":"搬米袋",
                        "visibility":"WITNESSED","witnesses":["B"]}],
             result="搬米袋完成", evidence_refs=["test-source"])
        self.assertNotIn("搬米袋", str(lab.writer_view(w,"A")))
        self.assertIn("搬米袋", str(lab.writer_view(w,"B")))

    def test_wait_does_not_magically_publish_outcome(self):
        w = lab.example()
        newer = lab.submit_choice(w, "B", mode="WAIT", intent="暂不营业",
            observed=[], result="没有行动", evidence_refs=["test-source"])
        self.assertEqual(len(newer["events"]), len(w["events"]))
        with self.assertRaisesRegex(lab.EcologyError,"NO_AUTOMATIC_EVENT_FOR_INACTION"):
            lab.submit_choice(w, "B", mode="WAIT", intent="暂不营业",
                observed=[{"id":"fake","place":"茶棚","outcome":"营业",
                           "visibility":"PUBLIC","witnesses":[]}],
                result="营业", evidence_refs=["test-source"])

    def test_duplicate_and_unidentified_witness_rejected(self):
        w = lab.example()
        for bad in [
            {"id":"rain","place":"渡口","outcome":"换告示",
             "visibility":"PUBLIC","witnesses":[]},
            {"id":"x","place":"渡口","outcome":"换告示",
             "visibility":"WITNESSED","witnesses":["UNKNOWN"]},
        ]:
            with self.assertRaises(lab.EcologyError):
                lab.submit_choice(w,"C",mode="ACT",intent="行动",
                                  observed=[bad],result="候选",
                                  evidence_refs=["test-source"])

    def test_anonymous_protagonist_is_not_required_for_offscreen_actions(self):
        w = lab.example()
        w = lab.submit_choice(w, "C", mode="ACT", intent="出船",
             observed=[{"id":"out","place":"渡口","outcome":"船离岸",
                        "visibility":"PRIVATE","witnesses":[]}],
             result="离岸", evidence_refs=["test-source"])
        self.assertEqual([e["id"] for e in w["events"]],["rain","out"])
        self.assertEqual(len(lab.writer_view(w,"A")["visible_events"]),1)

    def test_demo_no_model_or_literary_claim(self):
        r = lab.demo()
        self.assertEqual(r["actors"], 4)
        self.assertEqual(r["events_after"],3)
        self.assertEqual(r["writer_visible"],3)
        self.assertFalse(r["choices_generated_by_model"])
        self.assertFalse(r["literary_gain_verified"])


if __name__ == "__main__":
    unittest.main()
