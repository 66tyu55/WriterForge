"""WF 0.BL Xuehai original scene-atlas STAGING only.

No external model calls, no legacy paid training, no user's private R2, no
modern copyrighted fiction, and absolutely no claim of literary improvement.
This tests the existing WriterForgeDB + XuehaiStore rather than inventing a
parallel retrieval memory or auto-publishing unverified generated examples.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sqlite3
import unittest

from writerforge import WriterForgeDB,RuntimeEngine,XuehaiStore
from writerforge.xuehai import Query
from experiments.wf_0bl_stage_original_xuanhuan_xuehai import (
    stage_original_diagnostic,validate_seed,SEED
)

ROOT=Path(__file__).resolve().parents[1]
CLASSICS=ROOT/"experiments/wf_0bl_classical_provenance_reference_catalog_20261028.json"


class WF0BLStudyPlanAndSceneAtlas(unittest.TestCase):
    def setUp(self):
        self.dir=TemporaryDirectory()
        self.root=Path(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def test_16_distinct_original_micro_scene_details_have_unverified_origin(self):
        pack,digest=validate_seed()
        self.assertEqual(len(pack["cards"]),16)
        self.assertEqual(len({c["scene_type"] for c in pack["cards"]}),16)
        self.assertEqual(len(digest),64)
        self.assertTrue(all(c["rights"]=="NEW_ORIGINAL_NO_THIRD_PARTY_QUOTE"
                            for c in pack["cards"]))
        self.assertTrue(all(c["evidence_state"]==
                            "UNVERIFIED_CANDIDATE_NOT_LEARNED"
                            for c in pack["cards"]))
        self.assertTrue(all(c["scene_is_author_accepted"] is False
                            for c in pack["cards"]))
        self.assertFalse(pack["not_independently_literary_graded"] is False)
        self.assertEqual(pack["max_production_imports"],0)

    def test_originals_reach_existing_SQLite_Xuehai_LEARN_but_remain_STAGING(self):
        target=self.root/"atlas.sqlite3"
        evidence=stage_original_diagnostic(output=target)
        self.assertEqual(evidence["new_original_diagnostic_entries"],16)
        self.assertEqual(evidence["published_snapshots"],0)
        self.assertEqual(evidence["studied_novel_chapters_claimed"],0)
        self.assertEqual(evidence["actual_modern_copyright_novels_ingested"],0)
        self.assertEqual(evidence["new_model_calls"],0)
        self.assertEqual(evidence["r2_private_reads_or_writes"],0)
        self.assertFalse(evidence["literary_quality_proven"])
        db=WriterForgeDB(target)
        try:
            rows=db.conn.execute(
                "SELECT genre,function,source_role,reuse_policy,COUNT(*) AS n "
                "FROM xuehai_entries GROUP BY genre,function,source_role,reuse_policy"
            ).fetchall()
            self.assertEqual(len(rows),16)
            self.assertTrue(all(x["genre"]=="玄幻" for x in rows))
            self.assertTrue(all(x["source_role"]=="diagnostic_only" for x in rows))
            self.assertTrue(all(x["reuse_policy"]=="technique_only" for x in rows))
            staged=db.conn.execute("SELECT id,status FROM snapshots").fetchone()
            self.assertEqual(staged["status"],"staging")
            self.assertEqual(db.conn.execute(
                "SELECT COUNT(*) FROM studied_chapters").fetchone()[0],0)
            self.assertEqual(db.conn.execute(
                "SELECT source_uri,study_level FROM studied_works"
            ).fetchone()["source_uri"],
                             "wf-original-diagnostic://0bl/scene-atlas-v1")
            rt=RuntimeEngine();rt.enter_write(staged["id"])
            xuehai=XuehaiStore(db,rt)
            with self.assertRaisesRegex(ValueError,"not published"):
                xuehai.query(Query(genre="玄幻",limit=5))
        finally:
            db.close()
        with self.assertRaises(FileExistsError):
            stage_original_diagnostic(output=target)

    def test_tampering_rights_and_fabricating_literary_proof_fails_before_DB(self):
        base=json.loads(SEED.read_text("utf8"))
        changed=json.loads(json.dumps(base,ensure_ascii=False))
        changed["cards"][0]["rights"]="UNLICENSED_ONLINE_NOVEL"
        file=self.root/"tampered.json"
        file.write_text(json.dumps(changed,ensure_ascii=False),encoding="utf8")
        with self.assertRaisesRegex(ValueError,"UNTRUSTED_OR_FALSELY_QUALIFIED"):
            stage_original_diagnostic(output=self.root/"blocked.sqlite3",
                                      seed=file)
        self.assertFalse((self.root/"blocked.sqlite3").exists())
        changed=json.loads(json.dumps(base,ensure_ascii=False))
        changed["cards"][1]["scene_type"]=changed["cards"][0]["scene_type"]
        file.write_text(json.dumps(changed,ensure_ascii=False),encoding="utf8")
        with self.assertRaisesRegex(ValueError,"UNTRUSTED_OR_FALSELY_QUALIFIED"):
            validate_seed(file)

    def test_classical_pages_are_references_not_fake_ingested_originals(self):
        book=json.loads(CLASSICS.read_text("utf8"))
        self.assertEqual(book["status"],
            "REFERENCE_FOR_STAGED_VERIFICATION_NOT_INGESTED")
        self.assertEqual(book["actual_classical_passages_stored"],0)
        self.assertFalse(book["source_licenses_verified_for_all_editorial_layers"])
        self.assertEqual(len(book["items"]),5)
        self.assertTrue(all(row["url"].startswith(
            "https://zh.wikisource.org/") for row in book["items"]))
        self.assertTrue(any(row["read_state"]=="INDEX_ONLY_NO_PASSAGE_YET"
                            for row in book["items"]))
        self.assertTrue(all(row["work"] not in ("斗破苍穹","凡人修仙传")
                            for row in book["items"]))


if __name__=="__main__":
    unittest.main()
