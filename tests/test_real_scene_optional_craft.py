"""Model optional craft tags must not suppress a valid literary scene.

The native V96 source/actor/causality gates remain strict. This is metadata
compatibility only, never model-output rewriting or a literary judgement.
"""
import json
import unittest

from writerforge.writing_assist import _normalize_optional_model_craft_labels
from writerforge.v96_causal_turns import parse_turn_outline,V96CausalDraftError


def plan(tags=("interiority","decision"),second_tags=("action","detail")):
    return json.dumps({"turns":[
        {"id":"t01","kind":"decision","actor":"沈砚",
         "goal":"在摇晃的断桥上自行决定如何保护自己",
         "causal_parent":None,"craft_focus":list(tags)},
        {"id":"t02","kind":"action","actor":"唐蜃",
         "goal":"尝试切断链条迫使沈砚改变方向",
         "causal_parent":"t01","craft_focus":list(second_tags)},
    ]},ensure_ascii=False)


class ModelCraftTagCompatibility(unittest.TestCase):
    def test_decision_is_not_craft_tag_does_not_destroy_valid_plot(self):
        original=plan()
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "TURN_PLAN_FIELDS_ID_OR_CRAFT_INVALID"):
            parse_turn_outline(original)
        repaired,receipt=_normalize_optional_model_craft_labels(original)
        self.assertIsNotNone(receipt)
        self.assertEqual(len(parse_turn_outline(repaired)),2)
        self.assertTrue(receipt["only_model_optional_craft_fields_adjusted"])
        self.assertTrue(receipt["prose_not_rewritten"])
        before=json.loads(original)["turns"]
        after=json.loads(repaired)["turns"]
        for old,new in zip(before,after):
            for field in ("id","kind","actor","goal","causal_parent"):
                self.assertEqual(old[field],new[field])
        self.assertEqual(after[0]["craft_focus"],["interiority"])
        self.assertEqual(after[1]["craft_focus"],["action","detail"])
        self.assertEqual(receipt["removed"][0]["removed_optional_tags"],
                         ["decision"])
        self.assertEqual(receipt["canon_writes"],0)
        self.assertEqual(receipt["model_calls"],0)

    def test_supported_optional_craft_plan_is_byte_identical(self):
        raw=plan(("interiority","restraint"))
        same,report=_normalize_optional_model_craft_labels(raw)
        self.assertEqual(same,raw)
        self.assertIsNone(report)

    def test_schema_and_causal_parent_errors_remain_unmodified(self):
        bad=json.loads(plan())
        bad["turns"][1]["causal_parent"]="missing"
        raw=json.dumps(bad,ensure_ascii=False)
        normalized,receipt=_normalize_optional_model_craft_labels(raw)
        self.assertIsNotNone(receipt)  # only optional field may be dropped
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "CAUSAL_PARENT_NOT_PRIOR"):
            parse_turn_outline(normalized)
        before=json.loads(raw)
        after=json.loads(normalized)
        self.assertEqual(before["turns"][1]["causal_parent"],
                         after["turns"][1]["causal_parent"])

    def test_unknown_fields_and_invalid_json_are_not_laundered(self):
        data=json.loads(plan())
        data["turns"][0]["invented_fact"]=True
        raw=json.dumps(data,ensure_ascii=False)
        got,receipt=_normalize_optional_model_craft_labels(raw)
        self.assertEqual(got,raw)
        self.assertIsNone(receipt)
        duplicated='{"turns":[],"turns":[]} '
        got,receipt=_normalize_optional_model_craft_labels(duplicated)
        self.assertEqual(got,duplicated)
        self.assertIsNone(receipt)

    def test_author_frozen_outlines_cannot_be_normalized_implicitly(self):
        import inspect
        from writerforge.writing_assist import AutonomousWriting
        source=inspect.getsource(AutonomousWriting.run)
        self.assertIn('frozen_turn_outlines is None',source)
        self.assertIn('raw_turn_outline=turn_outline',source)
        self.assertIn('_normalize_optional_model_craft_labels(turn_outline)',
                      source)
        self.assertIn('unified_optional_craft_compatibility',source)

    def test_no_beat_omission_on_optional_unknown(self):
        modified,report=_normalize_optional_model_craft_labels(
            plan(("random_bad_option","another_invalid"),("action","action")))
        decoded=json.loads(modified)["turns"]
        self.assertEqual(len(decoded),2)
        self.assertEqual(decoded[0]["craft_focus"],[])
        self.assertEqual(decoded[1]["craft_focus"],["action"])
        self.assertEqual(len(parse_turn_outline(modified)),2)
        self.assertIsNotNone(report)


if __name__=="__main__":
    unittest.main()
