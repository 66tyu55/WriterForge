"""Only synthetic mechanical regressions; not independent original-novel training."""
from __future__ import annotations
import hashlib
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".agents/skills/wf-world-logic/scripts/worldlogic.py"
spec = importlib.util.spec_from_file_location("wf_shadow_worldlogic", SOURCE)
wl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wl)


def fixture():
    raw = "村口放哨。\n屋内隐瞒消息。\n".encode("utf-8")
    a = "村口放哨。".encode("utf-8")
    b = "屋内隐瞒消息。".encode("utf-8")
    ep = {
        "format": wl.FORMAT,
        "source": {"sha256": hashlib.sha256(raw).hexdigest(), "encoding": "utf-8",
                   "scope": [0, len(raw)]},
        "units": wl.line_units(raw, 0, len(raw)),
        "anchors": [
            {"id": "E1", "start": 0, "end": len(a), "surface": "村口放哨。", "review": "UNREVIEWED"},
            {"id": "E2", "start": len(a)+1, "end": len(a)+1+len(b), "surface": "屋内隐瞒消息。", "review": "UNREVIEWED"}],
        "places": [
            {"id": "L0", "parent_id": None, "evidence_ids": ["E1"]},
            {"id": "L1", "parent_id": "L0", "evidence_ids": ["E1"]},
            {"id": "L2", "parent_id": "L0", "evidence_ids": ["E2"]}],
        "routes": [{"id": "R12", "source": "L1", "target": "L2", "requires": ["entry"],
                    "cost": {"stamina": "2"}, "evidence_ids": ["E1", "E2"]}],
        "actors": [
            {"id": "A1", "location": "L1", "resources": {"stamina": "3"}, "access": ["entry"],
             "knows": [], "role_at_open": "guard", "evidence_ids": ["E1"]},
            {"id": "A2", "location": "L2", "resources": {"stamina": "1"}, "access": [],
             "knows": [], "role_at_open": "passerby", "evidence_ids": ["E2"]}],
        "rules": [{"id": "G1", "action_tag": "entry_exam", "evidence_ids": ["E2"],
                   "requirements": [{"kind": "access", "token": "referral"}]}],
        "facts": [
            {"id": "F1", "place_id": "L2", "epistemic": "NARRATED", "evidence_ids": ["E2"]},
            {"id": "F2", "place_id": None, "epistemic": "RUMOUR", "evidence_ids": ["E2"]}],
        "events": [{"id": "T1", "actor_id": "A2", "place_id": "L2", "evidence_ids": ["E2"],
                    "certainty": "OBSERVED", "cause_ids": [], "time_ref": None}]}
    return raw, ep


class TestSourceWorldLogic(unittest.TestCase):
    def test_byte_partition_is_not_semantic_review(self):
        raw, ep = fixture()
        x = wl.validate_source(ep, raw)
        self.assertTrue(x["byte_index_complete"])
        self.assertFalse(x["literary_one_to_one_verified"])
        self.assertEqual(x["self_reported_reviewed_bytes"], 0)

    def test_sha_and_forged_quote_rejected(self):
        raw, ep = fixture()
        with self.assertRaisesRegex(wl.EpisodeError, "SOURCE_SHA_MISMATCH"):
            wl.validate_source(ep, raw+b"x")
        ep["anchors"][0]["surface"] = "假原文"
        with self.assertRaisesRegex(wl.EpisodeError, "SOURCE_ANCHOR_MISMATCH"):
            wl.validate_source(ep, raw)

    def test_knowledge_does_not_teleport_across_places(self):
        _, ep = fixture()
        state = wl.initial_world(ep)
        bad = wl.try_proposal(state, {"kind": "witness", "actor_id": "A1", "fact_id": "F1"})
        self.assertEqual(bad["reason"], "NO_LOCAL_OBSERVATION")
        self.assertEqual(bad["state"], state)

    def test_directional_route_charges_cost_and_opaque_time(self):
        _, ep = fixture()
        state = wl.initial_world(ep)
        x = wl.try_proposal(state, {"kind": "move", "actor_id": "A1",
                                    "route_id": "R12", "time_ref": "UNKNOWN-TIME"})
        self.assertTrue(x["accepted"])
        self.assertEqual(x["state"]["actors"]["A1"]["at"], "L2")
        self.assertEqual(x["state"]["actors"]["A1"]["resources"]["stamina"], "1")
        self.assertEqual(x["state"]["history"][0]["time_ref"], "UNKNOWN-TIME")
        self.assertEqual(wl.try_proposal(x["state"], {"kind": "move", "actor_id": "A1",
                                                      "route_id": "R12"})["reason"], "WRONG_ROUTE_ORIGIN")
        self.assertEqual(state["actors"]["A1"]["resources"]["stamina"], "3")

    def test_hearing_rumour_does_not_add_truth(self):
        _, ep = fixture()
        state = wl.initial_world(ep)
        state = wl.apply_proposal(state, {"kind": "move", "actor_id": "A1", "route_id": "R12"})
        x = wl.try_proposal(state, {"kind": "tell", "actor_id": "A1", "target_id": "A2",
                                    "fact_id": "F1", "mode": "rumour"})
        self.assertTrue(x["accepted"])
        self.assertEqual(x["state"]["actors"]["A2"]["knows"], [])
        self.assertEqual(x["state"]["actors"]["A2"]["believes"][0]["mode"], "rumour")

    def test_observe_only_after_arrival_other_actor_unchanged(self):
        _, ep = fixture()
        state = wl.initial_world(ep)
        state = wl.apply_proposal(state, {"kind": "move", "actor_id": "A1", "route_id": "R12"})
        state = wl.apply_proposal(state, {"kind": "witness", "actor_id": "A1", "fact_id": "F1"})
        self.assertIn("F1", state["actors"]["A1"]["knows"])
        self.assertNotIn("F1", state["actors"]["A2"]["knows"])

    def test_unexplained_accident_is_allowed_not_inevitable(self):
        _, ep = fixture()
        state = wl.initial_world(ep)
        self.assertEqual(wl.try_proposal(state, {"kind": "accident",
                                                 "certainty": "OBSERVED"})["reason"],
                         "ACCIDENT_IS_NOT_INEVITABLE")
        x = wl.apply_proposal(state, {"kind": "accident", "certainty": "UNEXPLAINED",
                                      "effects": [{"actor_id": "A2", "field": "resource",
                                                   "key": "stamina", "delta": "-1"}]})
        self.assertEqual(x["actors"]["A2"]["resources"]["stamina"], "0")
        self.assertEqual(x["actors"]["A1"]["resources"]["stamina"], "3")
        self.assertEqual(state["history"], [])

    def test_bad_cost_is_atomic_rejection(self):
        _, ep = fixture()
        state = wl.initial_world(ep)
        x = wl.try_proposal(state, {"kind": "act", "actor_id": "A2", "cost": {"stamina": "2"}})
        self.assertFalse(x["accepted"])
        self.assertEqual(x["state"], state)

    def test_anonymized_candidate_omits_source_quotes(self):
        _, ep = fixture()
        text = str(wl.anonymized_structure(ep))
        self.assertNotIn("村口放哨", text)
        self.assertNotIn("屋内隐瞒", text)
        self.assertNotIn("sha256", text)
        self.assertIn("UNVERIFIED_LOCAL_CANDIDATE", text)

    def test_institution_gate_is_not_auto_success(self):
        _, ep = fixture()
        state = wl.initial_world(ep)
        denied = wl.try_proposal(state, {"kind": "act", "actor_id": "A2",
                                         "action_tag": "entry_exam"})
        self.assertEqual(denied["reason"], "WORLD_RULE_ACCESS_DENIED")
        state = wl.apply_proposal(state, {"kind": "act", "actor_id": "A1",
                                           "effects": [{"actor_id": "A2", "field": "access",
                                                        "key": "referral", "grant": True}]})
        x = wl.try_proposal(state, {"kind": "act", "actor_id": "A2",
                                    "action_tag": "entry_exam"})
        self.assertTrue(x["accepted"])
        self.assertNotIn("exam_success", x["state"]["actors"]["A2"])
        self.assertEqual(x["future"], "UNSPECIFIED_UNTIL_NEW_AUTHOR_ACTION")

    def test_causes_must_precede_world_events(self):
        _, ep = fixture()
        state = wl.initial_world(ep)
        self.assertEqual(wl.try_proposal(state, {"kind": "act", "actor_id": "A1",
                                                 "causes": ["EVENT_FROM_FUTURE"]})["reason"],
                         "UNWARRANTED_CAUSE")
        state = wl.apply_proposal(state, {"kind": "act", "actor_id": "A1", "id": "E-A"})
        x = wl.try_proposal(state, {"kind": "act", "actor_id": "A1", "causes": ["E-A"]})
        self.assertEqual(x["state"]["history"][-1]["causes"], ["E-A"])

    def test_changed_world_does_not_replay_old_future(self):
        _, ep = fixture()
        state = wl.initial_world(ep)
        x = wl.try_proposal(state, {"kind": "act", "actor_id": "A1", "effects": [
            {"actor_id": "A1", "field": "access", "key": "entry", "grant": False}]})
        self.assertTrue(x["accepted"])
        self.assertEqual(x["future"], "UNSPECIFIED_UNTIL_NEW_AUTHOR_ACTION")
        self.assertEqual(wl.try_proposal(x["state"], {"kind": "move", "actor_id": "A1",
                                                      "route_id": "R12"})["reason"], "ROUTE_ACCESS_DENIED")


if __name__ == "__main__":
    unittest.main()
