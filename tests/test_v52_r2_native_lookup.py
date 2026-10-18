"""V52 test EXACT current WF R2 protocol with an in-memory S3 backend.

No real secrets, no hidden model, no fake literary promotion. Restore an actual
OriginalStudy SQLite via R2StudyVault.backup/restore and query the EXACT
Xuehai evidence by read-only connection. Tamper/unknown term fail closed.
"""
from __future__ import annotations
from contextlib import redirect_stdout
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from hashlib import sha256
import json
import sqlite3
import unittest

from writerforge import WriterForgeDB,RuntimeEngine,OriginalStudy,VerifiedWritingFlow
from writerforge.r2_storage import R2StudyVault,R2Config,R2StorageError
from writerforge.r2_retrieval import R2SourceGateway,R2RetrievalError
from writerforge.cli import main

SOURCE=Path(__file__).parent/"fixtures"/"xiyouji_chapter_001_original_zh.txt"
BUCKET="writerforge-private-library"
LIBRARY="xiyouji-23962"

class Missing(Exception):
    response={"Error":{"Code":"404"}}

class FakeStore:
    def __init__(self):
        self.objects={}
        self.download_count=0
    def head_object(self, *, Bucket, Key):
        if (Bucket,Key) not in self.objects: raise Missing()
        raw,meta=self.objects[Bucket,Key]
        return {"ContentLength":len(raw),"Metadata":meta}
    def put_object(self, *, Bucket, Key, Body, ContentType=None, Metadata=None):
        self.objects[Bucket,Key]=(bytes(Body),Metadata or {})
    def get_object(self, *, Bucket, Key):
        if (Bucket,Key) not in self.objects: raise Missing()
        return {"Body":BytesIO(self.objects[Bucket,Key][0])}
    def upload_file(self, source,bucket,key,ExtraArgs=None,Config=None):
        self.objects[bucket,key]=(Path(source).read_bytes(),
                                  (ExtraArgs or {}).get("Metadata",{}))
    def download_file(self,bucket,key,dest):
        self.download_count+=1
        Path(dest).write_bytes(self.objects[bucket,key][0])

class R2GenuineNativeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.dbpath=self.root/"work.sqlite3"
        self.db=WriterForgeDB(self.dbpath)
        rt=RuntimeEngine();rt.enter_learn()
        OriginalStudy(self.db,rt).ingest(
            SOURCE.read_text(encoding="utf-8"),
            work_id="xiyouji-gutenberg-23962",require_hundred=False)
        self.db.close()
        self.store=FakeStore()
        self.config=R2Config(
            account_id="a"*32,bucket=BUCKET,
            access_key_id="synthetic",secret_access_key="synthetic")
        self.vault=R2StudyVault(self.config,client=self.store)
        self.backup=self.vault.backup(database=self.dbpath,library=LIBRARY)
        self.snap=self.backup["snapshot"]
        self.gateway=R2SourceGateway(self.vault)
        self.cache=self.root/"cache"
    def tearDown(self):
        self.tmp.cleanup()
    def search(self, terms=("猴王",),snapshot=None):
        return self.gateway.search(library=LIBRARY,
            snapshot=snapshot if snapshot is not None else self.snap,
            terms=terms,cache_dir=self.cache,limit=6)

    def test_existing_wf_source_can_be_searched_after_actual_r2_roundtrip(self):
        result=self.search()
        self.assertGreater(len(result.matches),0)
        self.assertEqual(result.snapshot,self.snap)
        self.assertFalse(result.from_local_cache)
        self.assertTrue(all("猴王" in x["source_excerpt"] for x in result.matches))
        self.assertTrue(all(x["evidence_class"]=="PINNED_ORIGINAL_SOURCE_LEXICAL_ONLY"
                            for x in result.matches))
        self.assertTrue(all(len(x["work_original_sha256"])==64
                            and len(x["source_unit_sha256"])==64 for x in result.matches))
        self.assertFalse(result.public()["literary_experience_semantics_verified"])
        self.assertEqual(result.public()["match_count"],len(result.matches))
        cached=self.search()
        self.assertTrue(cached.from_local_cache)
        self.assertEqual(cached.matches,result.matches)
        self.assertEqual(self.store.download_count,1)
        with sqlite3.connect(Path(self.cache)/LIBRARY/self.snap[:16]/"study.sqlite3") as db:
            self.assertEqual(db.execute("PRAGMA quick_check").fetchone()[0],"ok")
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM retrieval_usage").fetchone()[0],0)

    def test_no_exact_match_is_honest_not_a_fake_literary_recommendation(self):
        result=self.search(("無從找到的造作獨特詞",))
        self.assertEqual(result.matches,())
        self.assertFalse(result.public()["skill_learning_promoted"])

    def test_tampered_immutable_restore_file_is_rejected(self):
        result=self.search()
        local=Path(self.cache)/LIBRARY/self.snap[:16]/"study.sqlite3"
        with local.open("ab") as out:out.write(b"tamper")
        with self.assertRaisesRegex(R2StorageError,"modified|checksum|match"):
            self.search()

    def test_modified_remote_blob_is_rejected_by_full_hash(self):
        snap=self.backup["snapshot"]
        self.store.objects.clear()
        self.vault.backup(database=self.dbpath,library=LIBRARY)
        for (bucket,key),(data,meta) in list(self.store.objects.items()):
            if "/blobs/" in key and data.startswith(b"SQLite format 3"):
                self.store.objects[bucket,key]=(data[:-1]+b"x",meta)
        with self.assertRaises(R2StorageError):
            self.search()

    def test_scope_bounds_and_unsafe_search_terms(self):
        for terms in [(),("%hacker",),("a",),("猎物_越权",),("a"*40,),tuple(["猴王"]*5)]:
            with self.subTest(terms=terms),self.assertRaises(R2RetrievalError):
                self.search(terms)
        with self.assertRaises(R2RetrievalError):
            self.search(snapshot="latest")
        bad=R2Config(account_id="a"*32,bucket="not-the-private-wf-bucket",
                     access_key_id="x",secret_access_key="y")
        with self.assertRaisesRegex(R2RetrievalError,"PRIVATE_LIBRARY"):
            R2SourceGateway(R2StudyVault(bad,client=self.store))

    def test_actual_production_draft_will_use_only_explicit_sha_pinned_lookup(self):
        project=self.root/"project.sqlite3"
        db=WriterForgeDB(project)
        try:
            rt=RuntimeEngine();rt.enter_learn()
            OriginalStudy(db,rt).ingest(SOURCE.read_text(encoding="utf-8"),
              work_id="local-source",require_hundred=False)
            sid=db.conn.execute(
                "SELECT MAX(id) id FROM snapshots WHERE status='published'"
            ).fetchone()["id"]
            rt.exit();rt.enter_write(int(sid))
            flow=VerifiedWritingFlow(db,rt,"r2-test")
            with self.assertRaisesRegex(Exception,"R2_WRITING_REQUIRES_PINNED"):
                flow.prepare("scene-1","写一个原创角色的场景",r2_library=LIBRARY,
                             r2_terms=("猴王",))
            with patch("writerforge.r2_retrieval.R2SourceGateway.from_environment",
                       return_value=self.gateway):
                packet=flow.prepare("scene-1","写一个原创角色的场景",
                    r2_library=LIBRARY,r2_snapshot=self.snap,r2_terms=("猴王",),
                    r2_cache_dir=self.cache)
            self.assertGreater(len(packet.r2_verified_sources),0)
            self.assertIn("R2已验证原著出处",packet.prompt)
            receipt=packet.manifest()["r2_source_lookup"]
            self.assertEqual(receipt["snapshot_sha256"],self.snap)
            self.assertFalse(receipt["literary_method_verified"])
            self.assertNotIn("学会",str(receipt))
        finally:
            db.close()

    def test_r2_cli_does_not_create_default_project_database(self):
        with patch("writerforge.r2_retrieval.R2SourceGateway.from_environment",
                   return_value=self.gateway):
            with redirect_stdout(StringIO()) as output:
                main(["--db",str(self.root/"should-not-create.sqlite3"),
                      "r2-query","--library",LIBRARY,"--snapshot",self.snap,
                      "--term","猴王","--cache-dir",str(self.cache)])
        result=json.loads(output.getvalue())
        self.assertGreater(result["match_count"],0)
        self.assertEqual(result["provider"],"Cloudflare R2")
        self.assertFalse((self.root/"should-not-create.sqlite3").exists())


if __name__=="__main__":
    unittest.main()
