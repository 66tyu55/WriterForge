"""0.BM: classical source provenance, conditional method quality, no promotion.

Read the EXISTING real local public-domain chapter in a disposable SQLite DB,
never Wikisource raw text or a private original archive. Git blob is pinned.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from writerforge import WriterForgeDB, RuntimeEngine, XuehaiStore, VerifiedWritingFlow, WritingExecutionError
from experiments.wf_0bm_stage_first_classical_method_candidates import (
    validate_catalog,stage_isolated_classical_methods,CANDIDATES,OWNED_FIXTURE
)


class WF0BMClassicsMethodSourceFirst(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.root=Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_four_source_specific_mechanisms_are_unverified_and_conditional(self):
        pack,catalog_sha,fixture_sha=validate_catalog()
        self.assertEqual(len(pack["cards"]),4)
        self.assertEqual(len(set(card["id"] for card in pack["cards"])),4)
        self.assertEqual({x["work"] for x in pack["sources"]},{"西游记","史记"})
        self.assertEqual(len(catalog_sha),64)
        self.assertEqual(fixture_sha,sha256(OWNED_FIXTURE.read_bytes()).hexdigest())
        for card in pack["cards"]:
            self.assertNotEqual(card["applies_when"],card["not_when"])
            self.assertNotEqual(card["mechanism"],card["writer_option"])
            self.assertEqual(card["rights_status"],"RIGHTS_UNVERIFIED")
            self.assertEqual(card["review_status"],"PENDING")
            self.assertEqual(card["value_status"],"UNVERIFIED")
            self.assertEqual(card["review_receipt_sha256"],"")
            self.assertNotIn("必须照搬",card["writer_option"])
        self.assertEqual(pack["allowed_production_method_imports"],0)

    def test_real_original_fixture_learn_then_pending_cards_still_not_write(self):
        path=self.root/"no-publish-methods.sqlite3"
        result=stage_isolated_classical_methods(output=path)
        self.assertEqual(result["local_structurally_studied_chapters_in_isolated_db"],1)
        self.assertEqual(result["original_scene_method_cards_staging"],2)
        self.assertEqual(result["original_classics_reference_only_not_ingested"],2)
        self.assertEqual(result["production_eligible_classical_method_cards"],0)
        self.assertEqual(result["new_author_model_calls"],0)
        self.assertEqual(result["private_r2_reads_or_writes"],0)
        self.assertEqual(result["production_canon_writes"],0)
        self.assertFalse(result["literary_gain_proven"])
        self.assertTrue(result["local_fixture_is_not_claimed_equivalent_to_wikisource"])
        db=WriterForgeDB(path)
        try:
            cards=db.conn.execute(
                "SELECT rights_status,review_status,value_status,source_sha256,card_sha256 "
                "FROM xuehai_method_cards"
            ).fetchall()
            self.assertEqual(len(cards),2)
            self.assertTrue(all(c["rights_status"]=="RIGHTS_UNVERIFIED" and
                                c["review_status"]=="PENDING" and
                                c["value_status"]=="UNVERIFIED" for c in cards))
            self.assertTrue(all(len(c["source_sha256"])==64 and
                                len(c["card_sha256"])==64 for c in cards))
            self.assertEqual(db.conn.execute(
                "SELECT COUNT(*) FROM studied_chapters").fetchone()[0],1)
            self.assertEqual(db.conn.execute(
                "SELECT COUNT(*) FROM studied_works WHERE work_id LIKE '%shiji%'"
            ).fetchone()[0],0)
            self.assertEqual(db.conn.execute(
                "SELECT COUNT(*) FROM accepted_prose"
            ).fetchone()[0],0)
            rt=RuntimeEngine()
            rt.enter_write(result["published_source_study_snapshot"])
            x=XuehaiStore(db,rt)
            matched=x.query_methods(goal="秘境遗迹探险，群体承诺要兑现",genre="玄幻")
            self.assertEqual(matched["selected"],[])
            self.assertEqual(matched["receipt"]["result"],"NONE")
            rt.exit()
            rt.enter_write(result["pending_staging_snapshot"])
            with self.assertRaisesRegex(ValueError,"published"):
                x.query_methods(goal="秘境遗迹探险",genre="玄幻")
            with self.assertRaises(WritingExecutionError):
                VerifiedWritingFlow(db,rt,"test-local")
        finally:
            db.close()
        with self.assertRaises(FileExistsError):
            stage_isolated_classical_methods(output=path)

    def test_cannot_forge_verified_rights_or_literary_gain_from_a_candidate(self):
        pack=json.loads(CANDIDATES.read_text("utf8"))
        pack["cards"][0]["rights_status"]="RIGHTS_VERIFIED"
        path=self.root/"fake_rights.json"
        path.write_text(json.dumps(pack,ensure_ascii=False),encoding="utf8")
        with self.assertRaisesRegex(ValueError,"AUTO_APPROVAL"):
            validate_catalog(path)
        pack=json.loads(CANDIDATES.read_text("utf8"))
        pack["literary_quality_proven"]=True
        path.write_text(json.dumps(pack,ensure_ascii=False),encoding="utf8")
        with self.assertRaisesRegex(ValueError,"FALSE_PRODUCTION"):
            validate_catalog(path)
        pack=json.loads(CANDIDATES.read_text("utf8"))
        pack["allowed_production_method_imports"]=1
        path.write_text(json.dumps(pack,ensure_ascii=False),encoding="utf8")
        with self.assertRaisesRegex(ValueError,"FALSE_PRODUCTION"):
            validate_catalog(path)

    def test_anchor_or_local_text_change_rejected_before_import(self):
        pack=json.loads(CANDIDATES.read_text("utf8"))
        pack["cards"][0]["source_anchor"]="假古文并非真史"
        path=self.root/"false-anchor.json"
        path.write_text(json.dumps(pack,ensure_ascii=False),encoding="utf8")
        with self.assertRaisesRegex(ValueError,"ANCHOR_SHA"):
            validate_catalog(path)
        different=self.root/"different-chapter.txt"
        different.write_bytes(OWNED_FIXTURE.read_bytes()+b"\nmore fictional text")
        with self.assertRaisesRegex(ValueError,"GIT_BLOB_SHA"):
            validate_catalog(fixture=different)

    def test_different_wikisource_revision_and_internal_fixture_are_not_equated(self):
        pack=json.loads(CANDIDATES.read_text("utf8"))
        self.assertEqual(pack["sources"][0]["oldid"],2562136)
        self.assertEqual(pack["sources"][1]["oldid"],5978360)
        self.assertIsNone(pack["sources"][0]["full_page_sha256"])
        self.assertIsNone(pack["sources"][1]["local_fixture"])
        self.assertEqual(pack["source_raw_page_bytes_in_repo"],0)
        tampered=json.loads(json.dumps(pack,ensure_ascii=False))
        tampered["sources"][0]["identity"]="SOURCE_WEB_AND_FIXTURE_IDENTICAL"
        f=self.root/"false-edition.json"
        f.write_text(json.dumps(tampered,ensure_ascii=False),encoding="utf8")
        with self.assertRaisesRegex(ValueError,"MIXED_EDITION"):
            validate_catalog(f)


if __name__=="__main__":
    unittest.main()
