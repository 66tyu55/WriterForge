"""0.BR content checks: 24 literal classical narratives in SAME Xuehai as 24 original.

These tests do not grade literary talent or call models. With a pinned source
directory they verify byte-exact passages and whole in-DB prose. Otherwise
ordinary offline suite tests the 24 persisted prose texts themselves.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os
import sqlite3
import unittest

from experiments.wf_0br_merge_three_classics_with_original_xuehai import (
    load_curated_classical_texts, verify_pinned_files,
    add_classics_to_actual_xuehai, read_real_literary_mix_in_isolated_xuehai,
    PUBLIC_CLASSIC_ROLE, ORIGINAL_ROLE, CORPUS,
)


class WF0BRRealClassicalLiteraryContent(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.path=Path(self.temp.name)/"one-real-xuehai.db"
        self.source_dir=Path(os.environ.get(
            "WF0BR_PINNED_PUBLIC_SOURCE_DIR",self.temp.name))

    def tearDown(self):
        self.temp.cleanup()

    def test_three_real_books_24_contiguous_literary_details_not_methods(self):
        pack=load_curated_classical_texts()
        self.assertEqual(len(pack["sources"]),3)
        self.assertEqual(len(pack["excerpts"]),24)
        self.assertEqual(pack["excerpt_total_characters"],10626)
        self.assertEqual(
            {b["gutenberg_id"] for b in pack["sources"]},
            {23962,24264,23863})
        self.assertEqual(
            {b["title"] for b in pack["sources"]},
            {"西游记","红楼梦","水浒传"})
        self.assertEqual(len({x["detail_domain"] for x in pack["excerpts"]}),24)
        self.assertTrue(all(len(x["excerpt"])>=280 for x in pack["excerpts"]))
        self.assertTrue(all(x["anchor"] in x["excerpt"] for x in pack["excerpts"]))
        self.assertTrue(all(x["author_accepted"] is False
                            for x in pack["excerpts"]))
        # Demonstrate genuinely different narrative modes:
        by_id={x["id"]:x for x in pack["excerpts"]}
        self.assertIn("我等即拜他為王",by_id["x03"]["excerpt"])
        self.assertIn("黛玉",by_id["h04"]["excerpt"])
        self.assertIn("雪",by_id["s07"]["excerpt"])
        self.assertIn("衣飯",by_id["s03"]["excerpt"])
        self.assertFalse(pack["material_generated_by_chatgpt"])
        self.assertFalse(pack["literary_improvement_proven"])
        self.assertEqual(pack["published_method_cards"],0)

    def test_false_prose_or_permission_claim_not_accepted(self):
        pack=json.loads(CORPUS.read_text("utf8"))
        new=Path(self.temp.name)/"change.json"
        pack["literary_improvement_proven"]=True
        new.write_text(json.dumps(pack,ensure_ascii=False),encoding="utf8")
        with self.assertRaisesRegex(ValueError,"NOT_REAL_CURATED"):
            load_curated_classical_texts(new)
        pack=json.loads(CORPUS.read_text("utf8"))
        pack["excerpts"][0]["excerpt"]="写作的时候应当多一些细节和氛围。"
        new.write_text(json.dumps(pack,ensure_ascii=False),encoding="utf8")
        with self.assertRaisesRegex(ValueError,"MISSING_FULL"):
            load_curated_classical_texts(new)

    def test_actual_pinned_books_and_one_48_text_xuehai_retrieval(self):
        if not os.environ.get("WF0BR_PINNED_PUBLIC_SOURCE_DIR"):
            self.skipTest("only dedicated pinned public source CI downloads real originals")
        pack=load_curated_classical_texts()
        verified=verify_pinned_files(pack,self.source_dir)
        self.assertEqual(set(verified),{"xiyou","honglou","shuihu"})
        for item in pack["excerpts"]:
            t=verified[item["work_key"]]
            start,end=item["normalized_source_start"],item["normalized_source_end"]
            self.assertEqual(t[start:end],item["excerpt"])
        receipt=add_classics_to_actual_xuehai(
            db_path=self.path,source_dir=self.source_dir)
        self.assertEqual(receipt["existing_original_xuanhuan_scenes"],24)
        self.assertEqual(receipt["new_actual_classical_prose_passages"],24)
        self.assertEqual(receipt["total_complete_prose_passages"],48)
        self.assertEqual(receipt["original_prose_chars"],9208)
        self.assertEqual(receipt["real_classical_prose_chars"],10626)
        self.assertEqual(receipt["total_prose_chars"],19834)
        self.assertEqual(receipt["xuehai_snapshot_status"],"staging")
        self.assertEqual(receipt["new_classic_method_cards"],0)
        self.assertEqual(receipt["actual_full_classic_chapters_studied"],0)
        self.assertEqual(receipt["new_paid_author_model_requests"],0)
        self.assertEqual(receipt["production_canon_writes"],0)
        self.assertFalse(receipt["real_literary_improvement_proven"])
        with sqlite3.connect(self.path) as c:
            self.assertEqual(c.execute(
                "SELECT COUNT(*) FROM studied_chapters").fetchone()[0],24)
            self.assertEqual(c.execute(
                "SELECT COUNT(*) FROM xuehai_entries WHERE source_role=?",
                (PUBLIC_CLASSIC_ROLE,)).fetchone()[0],24)
            self.assertEqual(c.execute(
                "SELECT COUNT(*) FROM xuehai_entries WHERE source_role=?",
                (ORIGINAL_ROLE,)).fetchone()[0],24)
            self.assertEqual(c.execute(
                "SELECT COUNT(*) FROM xuehai_method_cards").fetchone()[0],0)
            self.assertEqual(c.execute(
                "SELECT COUNT(*) FROM accepted_prose").fetchone()[0],0)
            for r in receipt["entries"]:
                text=c.execute(
                    "SELECT text FROM xuehai_entries WHERE id=?",
                    (r["entry_id"],)).fetchone()[0]
                self.assertEqual(len(text),r["excerpt_chars"])
                self.assertEqual(
                    sha256(text.encode("utf8")).hexdigest(),r["excerpt_sha256"])
        self.assertFalse(self.path.is_dir())
        with self.assertRaises(FileExistsError):
            add_classics_to_actual_xuehai(
                db_path=self.path,source_dir=self.source_dir)
        view=read_real_literary_mix_in_isolated_xuehai(db_path=self.path)
        self.assertEqual(
            view["status"],"SIX_ACTUAL_FULL_PROSE_QUERIES_FROM_MIXED_XUEHAI_GREEN")
        self.assertEqual(len(view["queries"]),6)
        self.assertEqual(len({
            q["source_role"] for q in view["queries"]}),2)
        self.assertTrue(all(
            q["full_prose_chars_stored"]>=280 for q in view["queries"]))
        self.assertTrue(all(
            q["retrieval_excerpt_preview_chars"]<=80 for q in view["queries"]))
        self.assertFalse(view["published_in_real_user_xuehai"])


if __name__=="__main__":
    unittest.main()
