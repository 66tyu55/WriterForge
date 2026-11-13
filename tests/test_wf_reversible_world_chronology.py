"""Chronology tests for literal source availability, NOT fictional truth."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
import unittest
from hashlib import sha256

ROOT = (Path(__file__).resolve().parents[1] /
        ".agents/skills/reversible-world-causality/scripts")
sys.path.insert(0, str(ROOT))
import codec
import chronology


def scenario():
    text = "第一章\n甲初到旧屋。\n第二章\n乙在远城行动。\n第三章\n信使终于把消息带到。\n"
    raw = text.encode("utf-8")
    parts = [("A001", "actor", "甲"), ("A002", "actor", "乙"),
             ("A003", "message", "信使终于把消息带到")]
    anchors = []
    for aid, kind, term in parts:
        b = term.encode()
        start = raw.index(b)
        anchors.append({"id": aid, "kind": kind, "start": start,
                        "end": start + len(b), "surface": term})
    def fact(fid, evidences, rank, epi="narrated"):
        return {"id": fid, "kind": "observed_action",
                "subject_ids": evidences[:1], "evidence_ids": evidences,
                "telling_seq": rank, "story_tick": None,
                "time_axis": None, "epistemic": epi,
                "parameters": {}, "parameter_traces": {}}
    obs = {"format": codec.OBS_FORMAT,
           "source_sha256": sha256(raw).hexdigest(),
           "anchors": anchors,
           "facts": [
               fact("F001", ["A001"], 2),
               fact("F002", ["A002"], 1, "character_belief"),
               # Mentions the first actor, but interpretation requires
               # a span in the third chapter: cannot leak into chapter 1.
               fact("F003", ["A001", "A003"], 3)
           ],
           "links": [{
               "source": "F001", "target": "F002",
               "kind": "reports_to", "epistemic": "inferred",
               "evidence_ids": ["A003"]
           }]}
    return raw, obs


class ChronologyTests(unittest.TestCase):
    def test_original_ledger_is_valid_but_telling_ranks_wrong(self):
        raw, obs = scenario()
        codec.validate_observations(obs, raw, "utf-8")
        check = chronology.audit(obs, raw, "utf-8")
        self.assertEqual(check["telling_seq_mismatches"], 2)
        self.assertFalse(check["evidence_order_verified"])

    def test_normalize_without_inventing_story_tick(self):
        raw, obs = scenario()
        corrected = chronology.normalized(obs, raw, "utf-8")
        self.assertTrue(chronology.audit(corrected, raw, "utf-8")
                        ["evidence_order_verified"])
        self.assertEqual([f["telling_seq"] for f in corrected["facts"]],
                         [1, 2, 3])
        self.assertEqual([f["story_tick"] for f in corrected["facts"]],
                         [None, None, None])
        self.assertEqual([f["epistemic"] for f in corrected["facts"]],
                         [f["epistemic"] for f in obs["facts"]])

    def test_prefix_does_not_know_future_characters_or_messages(self):
        raw, obs = scenario()
        cutoff = raw.index("第二章".encode())
        prefix = chronology.available_prefix(obs, raw, "utf-8", cutoff)
        self.assertEqual(prefix["visible_fact_ids"], ["F001"])
        self.assertEqual(prefix["hidden_fact_count"], 2)
        self.assertEqual(prefix["visible_link_indices"], [])
        self.assertEqual(prefix["hidden_link_count"], 1)
        self.assertTrue(prefix["unknown_future_not_predicted"])

    def test_first_name_does_not_license_later_fact(self):
        raw, obs = scenario()
        cutoff = raw.index("第三章".encode())
        prefix = chronology.available_prefix(obs, raw, "utf-8", cutoff)
        self.assertEqual(prefix["visible_fact_ids"], ["F001", "F002"])
        self.assertEqual(prefix["visible_link_indices"], [])

    def test_prefix_releases_link_only_when_last_proof_visible(self):
        raw, obs = scenario()
        prefix = chronology.available_prefix(obs, raw, "utf-8", len(raw)-1)
        self.assertEqual(prefix["visible_fact_ids"], ["F001","F002","F003"])
        self.assertEqual(prefix["visible_link_indices"], [0])

    def test_cut_inside_unicode_character_is_rejected(self):
        raw, obs = scenario()
        within = raw.index("甲".encode()) + 1
        with self.assertRaisesRegex(codec.ReversibleError,
                                    "PREFIX_SPLITS_SOURCE_CHARACTER"):
            chronology.available_prefix(obs, raw, "utf-8", within)

    def test_wrong_source_sha_is_rejected_before_time_audit(self):
        raw, obs = scenario()
        with self.assertRaisesRegex(codec.ReversibleError, "SOURCE_SHA_MISMATCH"):
            chronology.audit(obs, raw+b"x", "utf-8")


if __name__ == "__main__":
    unittest.main()
