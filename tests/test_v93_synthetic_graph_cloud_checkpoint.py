"""V93 synthetic local-to-CAS-to-cold-R2-equivalent regressions.

Uses actual WriterForgeDB, FactJournal, V61/V62 sign/revoke/SELECT/SKIP,
V91 SQLite file and logical hashes, V93 zlib/chunk envelopes. FakeCAS
simulates immutable remote chunks, forcing every read to re-verify SHA.
No model or real R2 access; production data upload must be rejected.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
import json
import sqlite3
import unittest

from writerforge.v93_synthetic_graph_cloud_checkpoint import (
    build_private_synthetic_package,publish_to_cas,cold_restore_from_cas,
    _validate_envelope,_inflate,V93CloudGraphError,
    canonical,FILE_ORDER,MAX_FILE_BYTES,
)
from writerforge.v93_synthetic_graph_fixture import (
    create_synthetic_checkpoint,replay_restored_fixture,
)


def digest(raw):
    return sha256(raw).hexdigest()


class FakeCAS:
    def __init__(self,store=None,read_only=False):
        self.store={} if store is None else store
        self.read_only=read_only
        self.writer=None if read_only else "fictional-test-writer"
        self.write_count=0

    def _get_content(self,sha):
        raw=self.store[sha]
        if digest(raw)!=sha:
            raise V93CloudGraphError("WF93_FAKE_CAS_CORRUPTED")
        return raw

    def _put_content(self,raw):
        if self.read_only or self.writer is None:
            raise V93CloudGraphError("WF93_CAS_READ_ONLY")
        key=digest(raw)
        created=key not in self.store
        if not created and self.store[key]!=raw:
            raise V93CloudGraphError("WF93_CAS_IMMUTABLE_COLLISION")
        self.store.setdefault(key,raw)
        self.write_count+=int(created)
        return key,created


class V93GraphCloudTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.folder=Path(self.temp.name)
        self.fixture=create_synthetic_checkpoint(
            self.folder/"user-free-synthetic")
        self.raw,self.chunks=build_private_synthetic_package(
            self.fixture["checkpoint_root"])
        self.manifest=_validate_envelope(self.raw)
        self.writer=FakeCAS()

    def tearDown(self):
        self.temp.cleanup()

    def publish(self):
        return publish_to_cas(
            self.writer,manifest_raw=self.raw,parts=self.chunks)

    def read(self,suffix="restored"):
        cold_reader=FakeCAS(self.writer.store,read_only=True)
        restored=self.folder/suffix
        restored.mkdir()
        receipt=cold_restore_from_cas(
            cold_reader,manifest_sha=digest(self.raw),
            restore_parent=restored)
        checkpoint=restored/"checkpoints"/receipt["checkpoint_id"]
        behavior=replay_restored_fixture(
            checkpoint/"writerforge.sqlite3",
            checkpoint/"fact-journal.sqlite3")
        return receipt,behavior

    def test_two_sqlite_cold_recovery_keeps_revoked_skip_and_actor_clock(self):
        upload=self.publish()
        self.assertTrue(upload["new_manifest_created"])
        self.assertFalse(upload["production_graph_migrated"])
        self.assertTrue(upload["only_synthetic_data"])
        reader,behavior=self.read()
        self.assertEqual(reader["sqlite_files_restored"],2)
        self.assertFalse(reader["production_graph_migrated"])
        self.assertEqual(behavior["new_post_recovery_choice"],"SKIP")
        self.assertEqual(behavior["known_state"],"KNOWN")
        self.assertEqual(behavior["unrecorded_state"],"UNRECORDED")
        self.assertTrue(behavior["prior_revoked_select_reuse_refused"])
        self.assertEqual(behavior["synthetic_prior_decision_sha256"],
                         self.fixture["prior_select_decision_sha256"])
        self.assertEqual(behavior["synthetic_revoked_decision_sha256"],
                         self.fixture["revoked_skip_decision_sha256"])
        self.assertEqual(behavior["ledger_head"],
                         self.fixture["source_event_global_ledger_head"])

    def test_two_readers_can_recover_same_immutable_manifest(self):
        self.publish()
        r1,b1=self.read("cold-process1")
        r2,b2=self.read("cold-process2")
        self.assertEqual(r1["manifest_sha256"],r2["manifest_sha256"])
        self.assertEqual(b1["new_post_recovery_choice"],
                         b2["new_post_recovery_choice"])
        self.assertEqual(self.writer.write_count,
                         len(self.chunks)+1)

    def test_manual_idempotent_publish_never_rewrites_existing(self):
        a=self.publish()
        before=self.writer.store.copy()
        b=self.publish()
        self.assertTrue(a["new_manifest_created"])
        self.assertFalse(b["new_manifest_created"])
        self.assertEqual(self.writer.store,before)

    def test_missing_or_changed_cloud_chunk_refuses_recovery(self):
        self.publish()
        sha=self.manifest["files"][FILE_ORDER[0]]["parts"][0]["sha256"]
        self.writer.store.pop(sha)
        with self.assertRaises(KeyError):
            self.read()
        self.writer.store[sha]=b"deliberately wrong bytes"
        with self.assertRaisesRegex(V93CloudGraphError,"CORRUPTED"):
            self.read("restoredagain")

    def test_reader_only_cannot_publish(self):
        reader=FakeCAS(read_only=True)
        with self.assertRaisesRegex(V93CloudGraphError,
                                    "CLOUD_WRITER_ROLE_REQUIRED"):
            publish_to_cas(reader,manifest_raw=self.raw,parts=self.chunks)
        self.assertEqual(reader.write_count,0)

    def test_tampered_schema_false_promotion_and_file_manifest_rejected(self):
        for case in ("future_version","fake_production","fake_literary",
                     "bad_part_hash","missing_file"):
            doc=deepcopy(self.manifest)
            if case=="future_version":
                doc["schema_version"]=93
            if case=="fake_production":
                doc["production_graph_migrated"]=True
            if case=="fake_literary":
                doc["literary_semantics_verified"]=True
            if case=="bad_part_hash":
                doc["files"][FILE_ORDER[0]]["parts"][0]["sha256"]="x"*64
            if case=="missing_file":
                del doc["files"][FILE_ORDER[1]]
            with self.subTest(case=case):
                with self.assertRaises(V93CloudGraphError):
                    _validate_envelope(canonical(doc))

    def test_bounded_decompress_rejects_bomb_and_trailing_data(self):
        payload=b"x"*(MAX_FILE_BYTES+200)
        import zlib
        compressed=zlib.compress(payload,level=9)
        specs={"compressed_bytes":len(compressed),
               "compressed_sha256":digest(compressed),
               "plain_bytes":len(payload),"plain_sha256":digest(payload)}
        with self.assertRaisesRegex(V93CloudGraphError,"DECOMPRESSION_LIMIT"):
            _inflate(compressed,specs)
        raw=zlib.compress(b"hello")+b"trailing attack"
        specs={"compressed_bytes":len(raw),
               "compressed_sha256":digest(raw),
               "plain_bytes":5,"plain_sha256":digest(b"hello")}
        with self.assertRaisesRegex(V93CloudGraphError,"TRAILING_DATA"):
            _inflate(raw,specs)

    def test_real_user_db_contamination_must_not_upload(self):
        source=self.fixture["checkpoint_root"]
        checkpoint=source/"checkpoints"/self.fixture["checkpoint_id"]
        db_file=checkpoint/"writerforge.sqlite3"
        db=sqlite3.connect(db_file)
        db.execute("INSERT INTO studied_works(work_id,title,source_uri,"
                   "source_sha256,chapter_count) VALUES(?,?,?,?,?)",
                   ("real_actual_user","private book", "file://real",
                    "1"*64,1))
        db.commit()
        db.close()
        with self.assertRaises(V93CloudGraphError):
            build_private_synthetic_package(source)
        self.assertEqual(self.writer.write_count,0)

    def test_missing_or_mismatched_v91_local_checkpoint_refused(self):
        local=self.fixture["checkpoint_root"]
        checkpoint=local/"checkpoints"/self.fixture["checkpoint_id"]
        (checkpoint/"manifest.json").write_bytes(
            b'{"format":"wrong"}')
        with self.assertRaises(V93CloudGraphError):
            build_private_synthetic_package(local)

    def test_private_sqlite_not_stored_as_cleartext_cas_chunks(self):
        cloud,_=build_private_synthetic_package(
            self.fixture["checkpoint_root"])
        self.assertNotIn("守桥人合上木牌",cloud.decode("utf8"))
        self.assertTrue(all(b"SQLite format 3" not in chunk
                            for chunk in self.chunks.values()))
        self.assertFalse(self.manifest["production_graph_migrated"])
        self.assertFalse(self.manifest["literary_semantics_verified"])


if __name__=="__main__":
    unittest.main()
