"""Real WF source -> simulated R2 -> immutable disk sync -> offline compare.

Zero model calls, source text never placed in WRITE prompt, raw historical
evidence remains unchanged. No literary competence claim from lexical index.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO
import json
import sqlite3
import unittest

from test_v52_r2_native_lookup import FakeStore, LIBRARY, BUCKET, SOURCE
from writerforge import WriterForgeDB,RuntimeEngine,OriginalStudy,VerifiedWritingFlow
from writerforge.r2_storage import R2Config,R2StudyVault
from writerforge.corpus_foundation import (
    sync_r2,search_disk,build_index,CorpusIndexError,clean,
)
from writerforge.candidate_patterns import PatternLedger
from writerforge.verified_flow import WritingExecutionError
from writerforge.cli import main


class WFOfflineFoundationTests(unittest.TestCase):
    def setUp(self):
        self.t=TemporaryDirectory()
        self.root=Path(self.t.name)
        self.dbpath=self.root/"source.sqlite3"
        self.db=WriterForgeDB(self.dbpath)
        self.runtime=RuntimeEngine()
        self.runtime.enter_learn()
        OriginalStudy(self.db,self.runtime).ingest(
            SOURCE.read_text(encoding="utf-8"),work_id="test-book",
            require_hundred=False)
        self.db.close()
        self.s3=FakeStore()
        self.vault=R2StudyVault(
            R2Config(account_id="a"*32,bucket=BUCKET,
                     access_key_id="a",secret_access_key="b"),client=self.s3)
        self.backup=self.vault.backup(database=self.dbpath,library=LIBRARY)
        self.snapshot=self.backup["snapshot"]
        self.cache=self.root/"cache"
    def tearDown(self):
        self.t.cleanup()
    def sync(self):
        return sync_r2(self.vault,library=LIBRARY,snapshot=self.snapshot,
                       cache=self.cache)
    def lookup(self,terms=("猴王",),limit=6):
        return search_disk(self.cache,library=LIBRARY,snapshot=self.snapshot,
                           terms=terms,limit=limit)

    def test_stream_normalize_dedup_and_query_no_network(self):
        one=self.sync()
        self.assertFalse(one["already_indexed"])
        self.assertGreater(one["total_units"],0)
        self.assertLessEqual(one["unique_units"],one["total_units"])
        before=self.s3.download_count
        with patch.object(self.s3,"download_file",side_effect=AssertionError("query network")):
            with patch.object(self.s3,"get_object",side_effect=AssertionError("query network")):
                result=self.lookup()
        self.assertEqual(self.s3.download_count,before)
        self.assertTrue(result["full_sha_verified_at_sync_not_on_each_lookup"])
        self.assertEqual(result["per_lookup_cache_check"],"manifest_sha_and_source_file_stat")
        self.assertGreater(result["match_count"],0)
        self.assertFalse(result["source_prose_sent_to_writer"])
        self.assertTrue(result["unverified_lexical_comparison_only"])
        self.assertTrue(all("source_excerpt" not in p and "text" not in p
                            for p in result["matches"]))
        again=self.sync()
        self.assertTrue(again["already_indexed"])
        index=next(self.cache.glob("*/*/corpus-index.sqlite3"))
        con=sqlite3.connect(f"file:{index}?mode=ro",uri=True)
        try:
            self.assertEqual(con.execute("PRAGMA quick_check").fetchone()[0],"ok")
            self.assertEqual(con.execute(
                "SELECT COUNT(*) FROM units").fetchone()[0],one["unique_units"])
        finally:
            con.close()
        self.assertEqual(clean(" \u200b老  殘\n"),"老殘")

    def test_offline_search_requires_explicit_sync_and_snapshot(self):
        with self.assertRaisesRegex(CorpusIndexError,"NOT_SYNCED|NOT_INDEXED|MISSING"):
            self.lookup()
        self.sync()
        for term in ("%", "?", " a ", ""):
            with self.subTest(term=term),self.assertRaises(CorpusIndexError):
                self.lookup((term,))
        no_match=self.lookup(("完全不存在的极其生僻组合",))
        self.assertEqual(no_match["match_count"],0)
        self.assertTrue(no_match["unverified_lexical_comparison_only"])

    def test_tamper_original_or_index_refused(self):
        self.sync()
        path=next(self.cache.glob("*/*/study.sqlite3"))
        with path.open("ab") as f:
            f.write(b"tamper")
        with self.assertRaisesRegex(CorpusIndexError,"SOURCE_CHANGED|SQLITE_CHANGED"):
            self.lookup()

    def test_derived_pattern_ledger_stores_no_prose_and_no_promotion(self):
        self.sync()
        report=self.lookup()
        store=self.root/"patterns.sqlite3"
        led=PatternLedger(store)
        try:
            first=led.observe(report)
            second=led.observe(report)
            self.assertEqual(first,second)
            self.assertEqual(first["status"],"STRUCTURAL_OBSERVATION_ONLY")
            self.assertFalse(first["eligible_to_guide_writing"])
            with sqlite3.connect(store) as conn:
                row=conn.execute(
                    "SELECT evidence_json,contrast_json FROM comparison_candidates"
                ).fetchone()
                self.assertNotIn("猴王",row[0])
                self.assertIn('"semantic_causality_verified":false',row[1])
        finally:
            led.close()

    def test_real_write_entry_rejects_remote_research_and_quotes(self):
        db=WriterForgeDB(self.root/"project.sqlite3")
        try:
            rt=RuntimeEngine();rt.enter_learn()
            OriginalStudy(db,rt).ingest(
                SOURCE.read_text(encoding="utf-8"),work_id="project",
                require_hundred=False)
            snap=db.conn.execute("SELECT MAX(id) FROM snapshots WHERE status='published'").fetchone()[0]
            rt.exit();rt.enter_write(int(snap))
            wf=VerifiedWritingFlow(db,rt,"project-id")
            with self.assertRaisesRegex(
                    WritingExecutionError,"R2_RESEARCH_IS_NOT_WRITING_CONTEXT"):
                wf.prepare("one-scene","原创场景",r2_library=LIBRARY,
                           r2_snapshot=self.snapshot,r2_terms=("猴王",))
            p=wf.prepare("one-scene","原创场景")
            self.assertNotIn("R2已验证原著出处",p.prompt)
            self.assertNotIn("原文短引",p.prompt)
            self.assertEqual(p.manifest()["r2_source_lookup"]["references"],[])
        finally:
            db.close()

    def test_cli_now_splits_remote_sync_and_local_find(self):
        with patch("writerforge.r2_storage.R2StudyVault",return_value=self.vault):
            # Console constructs client from configuration; test the typed
            # gateway directly rather than authorise any real secret.
            pass
        self.sync()
        with redirect_stdout(StringIO()) as o:
            main(["corpus-find","--library",LIBRARY,"--snapshot",self.snapshot,
                  "--term","猴王","--cache-dir",str(self.cache),
                  "--record-candidate",str(self.root/"fromcli.sqlite3")])
        data=json.loads(o.getvalue())
        self.assertEqual(data["network_calls"],0)
        self.assertGreater(data["match_count"],0)
        self.assertEqual(data["comparison_candidate"]["status"],
                         "STRUCTURAL_OBSERVATION_ONLY")
        with redirect_stdout(StringIO()) as proof_out:
            main(["corpus-verify","--library",LIBRARY,"--snapshot",self.snapshot,
                  "--cache-dir",str(self.cache)])
        verified=json.loads(proof_out.getvalue())
        self.assertTrue(verified["all_r2_blob_sha256_and_sqlite_valid"])
        self.assertEqual(verified["r2_network_calls"],0)
        with redirect_stdout(StringIO()) as o:
            main(["r2-query","--library",LIBRARY,"--snapshot",self.snapshot,
                  "--term","猴王","--cache-dir",str(self.cache)])
        self.assertFalse(json.loads(o.getvalue())["source_prose_sent_to_writer"])


if __name__=="__main__":
    unittest.main()
