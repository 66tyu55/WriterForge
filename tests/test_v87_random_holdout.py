"""V87 seeded random draw: deterministic, metadata-only selection rules."""
from __future__ import annotations
import unittest
from unittest.mock import patch
from writerforge import v87_random_holdout as draw

def sample():
    return [
        {"object_key":f"writerforge/v1/private-reading/{g}/case{i}/book.txt",
         "category":g,"size_bytes":65536+i*3000,"etag":f"t{i}"}
        for g in ("仙侠","历史","科幻") for i in range(1,5)
    ]

class V87RandomTests(unittest.TestCase):
    def test_draw_is_stable_and_independent_of_catalog_order(self):
        rows=sample()
        with patch.object(draw,"candidate_sources",return_value=rows):
            first=draw.metadata_only_plan(None)
        with patch.object(draw,"candidate_sources",return_value=list(reversed(rows))):
            second=draw.metadata_only_plan(None)
        self.assertEqual(first,second)
        self.assertEqual(first["sample_size"],2)
        self.assertEqual(len({x["genre_hint"] for x in first["draws"]}),2)
        self.assertEqual(len(first["plan_sha256"]),64)
        self.assertEqual(len(first["draw_seed_sha256"]),64)
        self.assertEqual(first["source_text_or_keys_in_output"],False)
        self.assertNotIn("case1",repr(first))

    def test_fixed_fallback_and_eligibility_requirements(self):
        with patch.object(draw,"candidate_sources",return_value=sample()):
            first=draw.metadata_only_plan(None)
        self.assertTrue(all(len(d["predeclared_fallback_key_sha256"])==4
                            for d in first["draws"]))
        only_one=[x for x in sample() if x["category"]=="历史"]
        with patch.object(draw,"candidate_sources",return_value=only_one):
            with self.assertRaisesRegex(draw.WF87HoldoutError,
                                        "DISTINCT_SOURCE_GENRES"):
                draw.metadata_only_plan(None)

    def test_seed_precommitted_and_no_private_key_in_receipt(self):
        self.assertIn("2026-10-20T05:18:01Z",draw.ANCHOR)
        with patch.object(draw,"candidate_sources",return_value=sample()):
            plan=draw.metadata_only_plan(None)
        serialized=draw.canonical(plan).decode("utf8")
        self.assertNotIn("private-reading/",serialized)
        self.assertNotIn("book.txt",serialized)
        self.assertEqual(
            draw.sha(draw.canonical({k:v for k,v in plan.items()
                                    if k!="plan_sha256"})),
            plan["plan_sha256"])

if __name__=="__main__":
    unittest.main()
