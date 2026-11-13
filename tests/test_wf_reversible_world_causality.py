"""Source-free, adversarial tests for the standalone reversible world Skill."""
from __future__ import annotations

from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

SKILL = (Path(__file__).resolve().parents[1] /
         ".agents/skills/reversible-world-causality/scripts/codec.py")
spec = spec_from_file_location("world_codec", SKILL)
codec = module_from_spec(spec)
spec.loader.exec_module(codec)


def fixture(text, encoding="utf-8"):
    raw = text.encode(encoding)
    pieces = ["年轻人", "旧屋", "三日", "集市"]
    if "甲" in text:
        pieces = ["甲", "屋", "三日", "市"]
    anchors = []
    for i, term in enumerate(pieces, 1):
        term_bytes = term.encode("utf-8" if encoding == "utf-8-sig" else encoding)
        start = raw.index(term_bytes)
        anchors.append({"id": f"A{i:03}", "kind": (
            "actor" if i == 1 else
            "space" if i in (2, 4) else "time"),
            "start": start, "end": start + len(term_bytes),
            "surface": term})
    fact1 = {
        "id": "F001", "kind": "resource_pressure",
        "subject_ids": ["A001"], "evidence_ids": ["A001", "A002"],
        "telling_seq": 1, "story_tick": None, "time_axis": None,
        "epistemic": "narrated", "parameters": {"influence": "-0.0129"}
    }
    fact2 = {
        "id": "F002", "kind": "unexpected_choice",
        "subject_ids": ["A001"], "evidence_ids": ["A003", "A004"],
        "telling_seq": 2, "story_tick": None, "time_axis": None,
        "epistemic": "contingent", "parameters": {"change": "0.145"}
    }
    return {"format": codec.OBS_FORMAT, "source_sha256": sha256(raw).hexdigest(),
            "anchors": anchors, "facts": [fact1, fact2],
            "links": [{"source": "F001", "target": "F002",
                       "kind": "influences", "epistemic": "inferred",
                       "evidence_ids": ["A001"]}]}


class ReversibleWorldTests(unittest.TestCase):
    def test_full_inverse_in_both_codecs(self):
        for text, enc in [
            ("年轻人进入旧屋，三日后去了集市。", "utf-8"),
            ("年轻人进入旧屋，三日后去了集市。", "gb18030"),
            ("年轻人进入旧屋，三日后去了集市。", "utf-8-sig"),
        ]:
            with self.subTest(encoding=enc), TemporaryDirectory() as td:
                root = Path(td)
                source = root / "original.txt"
                source.write_bytes(text.encode(enc))
                annotations = root / "observations.json"
                observations = fixture(text, enc)
                annotations.write_text(json.dumps(observations, ensure_ascii=False),
                                       encoding="utf-8")
                result = codec.pack(source, annotations, root / "bundle")
                self.assertEqual(result["source_byte_roundtrip"], "PASS")
                self.assertEqual(result["graph_projection_inverse"], "PASS")
                self.assertEqual(result["semantic_truth"], "NOT_INDEPENDENTLY_TESTED")
                restored = root / "restored.txt"
                codec.recover(root / "bundle", restored, allow_private_original=True)
                self.assertEqual(restored.read_bytes(), source.read_bytes())
                anon = json.loads((root / "bundle/anonymous.json").read_text("utf-8"))
                self.assertNotIn("年轻人", json.dumps(anon, ensure_ascii=False))
                self.assertNotIn("旧屋", json.dumps(anon, ensure_ascii=False))

    def test_wrong_offsets_and_source_swap_are_rejected(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            source = root / "orig.txt"
            source.write_text("年轻人进入旧屋，三日后去了集市。", encoding="utf-8")
            obs = fixture(source.read_text("utf-8"))
            bad = json.loads(json.dumps(obs))
            bad["anchors"][0]["start"] += 1
            with self.assertRaisesRegex(codec.ReversibleError,
                                        "ANCHOR_NOT_IN_ORIGINAL|ANCHOR_CUTS_CHARACTER"):
                codec.validate_observations(bad, source.read_bytes(), "utf-8")
            with self.assertRaisesRegex(codec.ReversibleError, "SOURCE_SHA_MISMATCH"):
                codec.validate_observations(obs, b"unrelated", "utf-8")

    def test_forged_weight_and_missing_evidence_rejected(self):
        raw = "年轻人进入旧屋，三日后去了集市。".encode()
        obs = fixture(raw.decode())
        obs["facts"][0]["parameters"]["influence"] = "NaN"
        with self.assertRaisesRegex(codec.ReversibleError, "PARAMETER_NOT_CANONICAL"):
            codec.validate_observations(obs, raw, "utf-8")
        obs = fixture(raw.decode())
        obs["facts"][1]["evidence_ids"] = ["A999"]
        with self.assertRaisesRegex(codec.ReversibleError, "FACT_EVIDENCE_MISSING"):
            codec.validate_observations(obs, raw, "utf-8")

    def test_explicit_story_clock_contradiction_is_rejected(self):
        raw = "年轻人进入旧屋，三日后去了集市。".encode()
        obs = fixture(raw.decode())
        obs["facts"][0]["story_tick"] = 8
        obs["facts"][0]["time_axis"] = "local"
        obs["facts"][1]["story_tick"] = 3
        obs["facts"][1]["time_axis"] = "local"
        obs["links"][0]["kind"] = "precedes"
        with self.assertRaisesRegex(codec.ReversibleError,
                                    "EXPLICIT_CHRONOLOGY_CONTRADICTION"):
            codec.validate_observations(obs, raw, "utf-8")

    def test_mismatched_public_or_private_record_fails_closed(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            source = root / "original.txt"
            text = "年轻人进入旧屋，三日后去了集市。"
            source.write_text(text, encoding="utf-8")
            obs = root / "obs.json"
            obs.write_text(json.dumps(fixture(text), ensure_ascii=False), "utf-8")
            codec.pack(source, obs, root / "bundle")
            public = root / "bundle/anonymous.json"
            public.write_bytes(public.read_bytes() + b"x")
            with self.assertRaisesRegex(codec.ReversibleError, "ANONYMOUS_HASH"):
                codec.verify(root / "bundle")

    def test_renamed_world_keeps_abstract_fact_graph_only(self):
        # Relabeling surfaces preserves factual shape; modifying traits
        # is NOT presumed to preserve choices or outcomes.
        original = fixture("年轻人进入旧屋，三日后去了集市。")
        renamed = fixture("甲进入屋，三日后去了市。")
        self.assertNotEqual(original["source_sha256"], renamed["source_sha256"])
        self.assertEqual(original["facts"], renamed["facts"])
        self.assertEqual(original["links"], renamed["links"])
        self.assertNotEqual(original["anchors"][0]["surface"],
                            renamed["anchors"][0]["surface"])
        self.assertFalse(codec.projection(renamed)
                         ["causal_inference_from_params_alone_proven"])


if __name__ == "__main__":
    unittest.main()
