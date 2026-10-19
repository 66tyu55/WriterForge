"""V72 synthetic R2 index durability, resumability and read/write authority.

These tests never contact R2. Byte fixtures are synthetic. They exercise
real WriterForge SQLite index generation and the real protocol adapter with
a bounded mocked Worker that enforces immutable keys.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sqlite3
import unittest

from writerforge.bulk_inbox import BulkCatalog
from writerforge.r2_index_vault import (
    R2IndexVault,R2IndexError,BASE,SCHEMA,chunk_key,key_sha,manifest_key,
    validate_manifest,digest,canonical,
)
SOURCE_KEY="writerforge/v1/private-reading/科幻/模拟作品/正文.txt"
READER="synthetic-existing-reader-token-valid-123"
WRITER="synthetic-separate-index-writer-token-456"

class FakeVault(R2IndexVault):
    def __init__(self,objects,*,writer=True):
        super().__init__(
          endpoint="https://wf-r2-api.3227482831.workers.dev",
          read_token=READER,write_token=WRITER if writer else None)
        self.objects=objects
        self.writes=[]
        self.fail_at_new_write=None
    def _call(self,path,args,*,method="GET",body=None,
              write=False,cap=65536):
        if path=="/r2/index/refs":
            h=args["source_key_sha"]
            prefix=BASE+"refs/"+h+"/"
            matches=sorted(k for k in self.objects
                           if k.startswith(prefix))
            manifest=[{"manifest_sha256":k.rsplit("/",1)[1][:-5],
                       "size":len(self.objects[k])} for k in matches]
            value={"ok":True,"read_only":True,
                   "format":"writerforge.index-ref-list.v1",
                   "source_key_sha256":h,
                   "manifests":manifest,"complete":True,
                   "next_cursor":None}
            return {},canonical(value)
        key=args["key"]
        if not key.startswith(BASE):
            raise R2IndexError("WF_INDEX_OUTSIDE_WRITABLE_NAMESPACE")
        if path=="/r2/index/write":
            if not write or self.write_token is None or method!="PUT":
                raise R2IndexError("WF_INDEX_NO_WRITE_AUTHORIZATION")
            if len(body)>1024*1024:
                raise R2IndexError("WF_INDEX_WRITER_SIZE_EXCEEDED")
            h=sha256(body).hexdigest()
            if not key.endswith("/"+h+".bin") and not key.endswith("/"+h+".json"):
                raise R2IndexError("WF_INDEX_WRITER_HASH_WRONG")
            if self.fail_at_new_write is not None and len(self.writes)>=self.fail_at_new_write:
                raise R2IndexError("WF_INDEX_SIMULATED_NETWORK_INTERRUPTION")
            old=self.objects.get(key)
            if old is not None and old!=body:
                raise R2IndexError("WF_INDEX_IMMUTABLE_COLLISION")
            if old is None:
                self.objects[key]=body
                self.writes.append(key)
            result={"ok":True,"sha256":h,"size":len(body),
                    "created":old is None,"immutable":True}
            return {},canonical(result)
        if path!="/r2/index/object":
            raise R2IndexError("WF_INDEX_UNKNOWN_ROUTE")
        if key not in self.objects:
            raise R2IndexError("WF_INDEX_OBJECT_NOT_FOUND")
        raw=self.objects[key]
        headers={"Content-Length":str(len(raw)),
                 "X-WF-Object-Size":str(len(raw)),
                 "ETag":'"synthetic-etag"'}
        if method=="HEAD":
            return headers,b""
        if "offset" in args:
            offset=args["offset"]
            length=args["length"]
            if offset+length>len(raw):
                raise R2IndexError("WF_INDEX_SIMULATED_BAD_RANGE")
            headers["Content-Length"]=str(length)
            headers["Content-Range"]=f"bytes {offset}-{offset+length-1}/{len(raw)}"
            return headers,raw[offset:offset+length]
        return headers,raw

class V72PersistentIndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.objects={}
        self.catalog=BulkCatalog(self.root/"meta.sqlite3")
        self.text=("第一章 云层\n" + "远方城镇传来钟鸣声，风吹动荒野上的沙尘。\n"*260
                   +"第二章 荒野\n"+"旅人经过废弃的空间站，听见机器逐渐停止的声音。\n"*240)
        self.source=self.root/"original.txt"
        self.source.write_bytes(self.text.encode("utf-8"))
        self.content=self.source.read_bytes()
        self.catalog.register([{"key":SOURCE_KEY,
             "size":len(self.content),"etag":'"original-etag"'}])
        self.result=self.catalog.index_text_file(
            SOURCE_KEY,self.source,self.root/"shards")
        self.shard=self.root/"shards"/(self.result["book_id"]+".sqlite3")
        self.original_hash=sha256(self.content).hexdigest()
        self.record={"key":SOURCE_KEY,"size":len(self.content),
                     "etag":'"original-etag"'}
    def tearDown(self):
        self.catalog.close()
        self.tmp.cleanup()
    def publish(self,vault):
        return vault.publish(
          index_file=self.shard,original_key=SOURCE_KEY,
          source_sha256=self.original_hash,
          source_size=len(self.content),
          source_etag='"original-etag"',category="科幻",
          encoding="utf-8",provisional_legacy=False,
          units=self.result["units_indexed"],
          chapters=self.result["chapters_detected"])

    def test_writer_credential_never_equals_read_credential(self):
        with self.assertRaisesRegex(R2IndexError,
                                    "TOKEN_UNSAFE_OR_SHARED"):
            R2IndexVault(
              endpoint="https://wf-r2-api.3227482831.workers.dev",
              read_token=READER,write_token=READER)
        client=FakeVault({},writer=False)
        with self.assertRaisesRegex(R2IndexError,
                                     "UPLOAD_TOKEN_NOT_CONFIGURED"):
            self.publish(client)

    def test_real_sql_roundtrip_via_r2_and_new_reader_instance(self):
        sender=FakeVault(self.objects)
        receipt=self.publish(sender)
        self.assertTrue(receipt["manifest_created"])
        self.assertTrue(receipt["stored_in_r2"])
        self.assertGreater(receipt["chunks"],0)
        self.assertEqual(self.content,self.source.read_bytes())
        self.assertTrue(all(k.startswith(BASE) for k in self.objects))
        reader=FakeVault(self.objects,writer=False) # New restarted WF process.
        refs=reader.manifest_refs(key_sha(SOURCE_KEY))
        self.assertEqual(refs,[receipt["manifest_sha256"]])
        ready=reader.find_matching(self.record)
        self.assertEqual(len(ready),1)
        with reader.restore(self.record,refs[0]) as (db,manifest):
            self.assertEqual(db.execute("PRAGMA query_only").fetchone()[0],1)
            self.assertGreater(db.execute(
                "SELECT COUNT(*) FROM units").fetchone()[0],0)
            self.assertEqual(manifest["source_sha256"],self.original_hash)
            self.assertEqual(manifest["units"],self.result["units_indexed"])
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM units WHERE instr(normalized,?)>0",
                ("钟鸣声",)).fetchone()[0],260)
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("DELETE FROM units")
        self.assertEqual(self.catalog.ready_count(),1)

    def test_second_publish_is_idempotent_without_rewrites(self):
        vault=FakeVault(self.objects)
        first=self.publish(vault)
        written=len(vault.writes)
        again=self.publish(vault)
        self.assertEqual(first["manifest_sha256"],again["manifest_sha256"])
        self.assertEqual(len(vault.writes),written)
        self.assertEqual(again["new_chunks"],0)
        self.assertFalse(again["manifest_created"])

    def test_partial_upload_has_no_visible_manifest_and_resume(self):
        sender=FakeVault(self.objects)
        sender.fail_at_new_write=1
        with self.assertRaisesRegex(R2IndexError,"SIMULATED_NETWORK"):
            self.publish(sender)
        self.assertFalse(any("/refs/" in k for k in self.objects))
        sender.fail_at_new_write=None
        receipt=self.publish(sender)
        self.assertEqual(sender.manifest_refs(key_sha(SOURCE_KEY)),
                         [receipt["manifest_sha256"]])
        with FakeVault(self.objects,writer=False).restore(
                self.record,receipt["manifest_sha256"]) as (conn,_):
            self.assertGreater(conn.execute("SELECT COUNT(*) FROM units").fetchone()[0],0)

    def test_chunk_mutation_fails_closed(self):
        sender=FakeVault(self.objects)
        receipt=self.publish(sender)
        name=next(k for k in self.objects if "/chunks/" in k)
        raw=self.objects[name]
        self.objects[name]=bytes([raw[0]^0xff])+raw[1:]
        with self.assertRaisesRegex(R2IndexError,"PART_SHA_FAILED"):
            with FakeVault(self.objects,writer=False).restore(
                self.record,receipt["manifest_sha256"]):
                pass

    def test_original_etag_change_disables_stale_index(self):
        sender=FakeVault(self.objects)
        receipt=self.publish(sender)
        changed={**self.record,"etag":'"new-source-etag"'}
        self.assertEqual(sender.find_matching(changed),[])
        with self.assertRaisesRegex(R2IndexError,"ORIGINAL_OBJECT_CHANGED"):
            with sender.restore(changed,receipt["manifest_sha256"]):
                pass

    def test_truncated_manifest_and_manifest_sha_mismatch_refused(self):
        sender=FakeVault(self.objects)
        receipt=self.publish(sender)
        key=manifest_key(key_sha(SOURCE_KEY),receipt["manifest_sha256"])
        self.objects[key]=self.objects[key]+b" "
        with self.assertRaisesRegex(R2IndexError,"MANIFEST_SHA_MISMATCH"):
            sender.read_manifest(SOURCE_KEY,receipt["manifest_sha256"])

    def test_manifest_cannot_embed_original_prose_or_wrong_book_id(self):
        sender=FakeVault(self.objects)
        receipt=self.publish(sender)
        m=sender.read_manifest(SOURCE_KEY,receipt["manifest_sha256"])
        with self.assertRaisesRegex(R2IndexError,"FIELDS_INVALID"):
            validate_manifest({**m,"source_excerpt":"private prose"})
        with self.assertRaisesRegex(R2IndexError,"SCHEMA_INVALID"):
            validate_manifest({**m,"book_id":"b_"+"0"*32})

    def test_identity_and_source_key_must_match(self):
        sender=FakeVault(self.objects)
        receipt=self.publish(sender)
        doc=sender.read_manifest(SOURCE_KEY,receipt["manifest_sha256"])
        with self.assertRaisesRegex(R2IndexError,"OTHER_SOURCE"):
            validate_manifest(doc,original_key=
               "writerforge/v1/private-reading/科幻/别的/正文.txt")

if __name__=="__main__":
    unittest.main()
