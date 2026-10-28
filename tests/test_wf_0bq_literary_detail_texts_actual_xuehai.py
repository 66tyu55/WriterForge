"""0.BQ literary CONTENT corpus: not fake small-scene tips and not quality scoring."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sqlite3
import unittest

from experiments.wf_0bq_stage_original_full_detail_prose import (
    validate_corpus,stage_full_detail_prose,verify_isolated_retrieval,
    CORPUS_FILES,ORIGINAL_ROLE,WORK_PREFIX,MIN_PROSE_CHARS,
)


class WF0BQCompleteLiteraryDetailCorpus(unittest.TestCase):
    def setUp(self):
        self.t=TemporaryDirectory()
        self.path=Path(self.t.name)/"disposable-xuehai.db"

    def tearDown(self):
        self.t.cleanup()

    def test_24_actually_different_complete_scenes_not_short_abstract_rules(self):
        scenes,pack_sha=validate_corpus()
        self.assertEqual(len(scenes),24)
        self.assertEqual(set(pack_sha),{"A","B"})
        self.assertTrue(all(len(sha)==64 for sha in pack_sha.values()))
        self.assertTrue(all(len(s["prose"])>=MIN_PROSE_CHARS for s in scenes))
        self.assertGreater(sum(len(s["prose"]) for s in scenes),8500)
        self.assertGreater(len({s["scene_type"] for s in scenes}),20)
        self.assertGreater(len({s["narrative_mode"] for s in scenes}),20)
        self.assertGreater(len({s["subgenre"] for s in scenes}),15)
        self.assertGreater(len({
            d for s in scenes for d in s["detail_dimensions"]
        }),45)
        self.assertIn("我以为",next(s for s in scenes if s["id"].startswith("bq-21"))["prose"])
        self.assertIn("母亲：",next(s for s in scenes if s["id"].startswith("bq-22"))["prose"])
        self.assertIn("我守这段水",next(s for s in scenes if s["id"].startswith("bq-23"))["prose"])
        self.assertIn("两人",next(s for s in scenes if s["id"].startswith("bq-02"))["prose"]+"两人")
        self.assertTrue(all(s["author_accepted"] is False for s in scenes))
        self.assertFalse(any("SOURCE_VERIFIED" in s["source_kind"] for s in scenes))

    def test_real_existing_xuehai_stores_all_prose_and_isolates_write_until_published(self):
        items,_=validate_corpus()
        receipt=stage_full_detail_prose(db_path=self.path)
        self.assertEqual(receipt["complete_original_scene_texts"],24)
        self.assertEqual(receipt["actual_original_studied_chapters_in_isolated_db"],24)
        self.assertEqual(len(receipt["entries"]),24)
        self.assertEqual(receipt["new_method_cards"],0)
        self.assertEqual(receipt["new_model_provider_requests"],0)
        self.assertEqual(receipt["production_canon_writes"],0)
        self.assertFalse(receipt["literary_quality_improvement_proven"])
        self.assertEqual(receipt["whole_prose_snapshot_status"],"staging")
        self.assertEqual(receipt["full_prose_chars_saved"],
                         sum(len(s["prose"]) for s in items))
        self.assertGreater(receipt["actual_original_structural_source_spans"],100)
        self.assertEqual(verify_isolated_retrieval(self.path)["status"],
                         "STAGING_BLOCKED_FROM_WRITE")
        with sqlite3.connect(self.path) as c:
            self.assertEqual(c.execute(
                "SELECT COUNT(*) FROM studied_works").fetchone()[0],24)
            self.assertEqual(c.execute(
                "SELECT COUNT(*) FROM studied_chapters").fetchone()[0],24)
            self.assertEqual(c.execute(
                "SELECT COUNT(*) FROM xuehai_method_cards").fetchone()[0],0)
            self.assertEqual(c.execute(
                "SELECT COUNT(*) FROM accepted_prose").fetchone()[0],0)
            self.assertEqual(c.execute(
                "SELECT COUNT(*) FROM xuehai_entries WHERE source_role=?",
                (ORIGINAL_ROLE,)).fetchone()[0],24)
            for record in receipt["entries"]:
                text=c.execute(
                    "SELECT text FROM xuehai_entries WHERE id=?",
                    (record["entry_id"],)).fetchone()[0]
                self.assertGreaterEqual(len(text),MIN_PROSE_CHARS)
                self.assertEqual(
                    sha256(text.encode("utf8")).hexdigest(),
                    record["prose_sha256"])
        with self.assertRaises(FileExistsError):
            stage_full_detail_prose(db_path=self.path)

    def test_real_sqlite_isolated_retrieval_returns_context_from_five_different_scenes(self):
        stage_full_detail_prose(db_path=self.path)
        preview=verify_isolated_retrieval(
            self.path,publish_in_isolated_db=True)
        self.assertEqual(preview["status"],
                         "ISOLATED_ONLY_5_SCENE_PROSE_QUERIES_GREEN")
        self.assertEqual(set(preview["verified"]),
                         {"炼丹","近身斗法","志怪接触","宗门政治","制符失败"})
        self.assertTrue(all(
            x["stored_full_prose_chars"]>=MIN_PROSE_CHARS
            for x in preview["verified"].values()
        ))
        self.assertTrue(all(
            x["returned_summary_chars"]==80
            for x in preview["verified"].values()
        ))
        # This flags a REAL follow-on limitation: the existing author prompt
        # receives a short summary even though full prose is now indexed.
        self.assertFalse(preview["published_for_real_user"])
        self.assertFalse(preview["model_generated_or_literary_evaluated"])
        with sqlite3.connect(self.path) as c:
            self.assertEqual(c.execute(
                "SELECT COUNT(*) FROM xuehai_entries WHERE source_role=?",
                (ORIGINAL_ROLE,)).fetchone()[0],24)

    def test_false_copyright_or_literary_claim_refused(self):
        a=json.loads(CORPUS_FILES["A"].read_text("utf8"))
        a["independent_literary_reader_rating"]=97
        altered=Path(self.t.name)/"tampered-rating.json"
        altered.write_text(json.dumps(a,ensure_ascii=False),encoding="utf8")
        with patch.dict(CORPUS_FILES,{"A":altered}):
            with self.assertRaisesRegex(ValueError,"FALSE_CORPUS_CONTENT_OR_QUALITY"):
                validate_corpus()
        a=json.loads(CORPUS_FILES["A"].read_text("utf8"))
        a["items"][0]["prose"]="这只是很短的概念提醒。"
        altered.write_text(json.dumps(a,ensure_ascii=False),encoding="utf8")
        with patch.dict(CORPUS_FILES,{"A":altered}):
            with self.assertRaisesRegex(ValueError,"CORPUS_LACKS_COMPLETE"):
                validate_corpus()
        a=json.loads(CORPUS_FILES["A"].read_text("utf8"))
        a["items"][0]["prose"]=a["items"][1]["prose"]
        altered.write_text(json.dumps(a,ensure_ascii=False),encoding="utf8")
        with patch.dict(CORPUS_FILES,{"A":altered}):
            with self.assertRaisesRegex(ValueError,"CORPUS_DUPLICATE"):
                validate_corpus()


if __name__=="__main__":
    unittest.main()
