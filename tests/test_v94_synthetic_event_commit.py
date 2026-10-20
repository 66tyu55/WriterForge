"""V94 cloud event lineage: synthetic-only deterministic replay redteam.

Real WriterForgeDB+FactJournal APIs, immutable FakeCAS and V93 backup
are exercised with independent new SQLite instances on every cold read.
No model API, R2 network, real literary data, or user-owned keys.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
import unittest

from writerforge.v93_synthetic_graph_fixture import (
    create_synthetic_checkpoint,
)
from writerforge.v93_synthetic_graph_cloud_checkpoint import (
    build_private_synthetic_package,publish_to_cas,
)
from writerforge import v94_synthetic_event_commit as engine


def digest(raw):
    return sha256(raw).hexdigest()


class FakeCAS:
    def __init__(self,store=None,read_only=False):
        self.store={} if store is None else store
        self.read_only=read_only
        self.writer=None if read_only else "synthetic-only-writer"
        self.new_objects=0

    def _get_content(self,key):
        raw=self.store[key]
        if digest(raw)!=key:
            raise engine.V94DurableEventError(
                "WF94_FAKE_REMOTE_CAS_HASH_CHANGED")
        return raw

    def _put_content(self,raw):
        if self.read_only or self.writer is None:
            raise engine.V94DurableEventError(
                "WF94_FAKE_CAS_READER_CANNOT_WRITE")
        key=digest(raw)
        created=key not in self.store
        if not created and self.store[key]!=raw:
            raise engine.V94DurableEventError(
                "WF94_FAKE_CAS_COLLISION")
        self.store.setdefault(key,raw)
        self.new_objects+=int(created)
        return key,created


class V94EventTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.root=Path(self.tmp.name)
        fixture=create_synthetic_checkpoint(self.root/"fixture")
        cloudraw,parts=build_private_synthetic_package(
            fixture["checkpoint_root"])
        self.r2writer=FakeCAS()
        prior=publish_to_cas(self.r2writer,
                             manifest_raw=cloudraw,parts=parts)
        # Patch ONLY the V93 synthetic base pin to the synthetic object
        # produced locally. The public production constant isn't touched.
        self.original_base=engine.BASE_GRAPH_SHA
        engine.BASE_GRAPH_SHA=prior["manifest_sha256"]
        self.reader=FakeCAS(self.r2writer.store,read_only=True)
        self.docs,self.manifest,self.state=engine.prepare_chain(
            self.reader,workdir=self.dir("first"))
        self.manifest_sha=digest(self.manifest)

    def tearDown(self):
        engine.BASE_GRAPH_SHA=self.original_base
        self.tmp.cleanup()

    def dir(self,name):
        path=self.root/name
        path.mkdir()
        return path

    def publish(self,docs=None,manifest=None,name="preflight"):
        return engine.publish_chain(
            self.r2writer,self.reader,
            event_bytes=self.docs if docs is None else docs,
            manifest_raw=self.manifest if manifest is None else manifest,
            preflight_dir=self.dir(name))

    def read(self,name="recovered",manifest=None):
        return engine.cold_replay(
            self.reader,manifest_sha=self.manifest_sha if manifest is None
                                    else manifest,
            workdir=self.dir(name))

    def test_full_sequence_can_be_published_then_cold_replayed(self):
        prior=self.publish()
        self.assertTrue(prior["manifest_created"])
        self.assertEqual(prior["committed_event_count"],7)
        self.assertFalse(prior["writer_never_promoted_literary_truth"] is False)
        self.assertEqual(prior["manifest_sha256"],self.manifest_sha)
        outcome=self.read()
        self.assertEqual(outcome["verified_cas_events"],7)
        self.assertEqual(outcome["before_revocation"],"SELECT")
        self.assertEqual(outcome["after_revocation"],"SKIP")
        self.assertEqual(outcome["original_character_state"],"KNOWN")
        self.assertEqual(outcome["latest_character_state"],"CONFLICT_UNRESOLVED")
        self.assertEqual(outcome["unknown_future_state"],"UNRECORDED")
        self.assertFalse(
            outcome["actual_production_graph_durable_write_stream_active"])
        self.assertEqual(self.state["new_global_ledger_seq"],8)

    def test_two_independent_readers_replay_same_global_clock_and_hashes(self):
        self.publish()
        a=self.read("separateReader1")
        b=self.read("separateReader2")
        self.assertEqual(a["final_state_sha256"],
                         b["final_state_sha256"])
        self.assertEqual(a["outcome_receipts_sha256"],
                         b["outcome_receipts_sha256"])
        self.assertEqual(a["latest_character_state"],"CONFLICT_UNRESOLVED")

    def test_event_only_without_last_manifest_is_uncommitted(self):
        # The first event may exist in R2 before a crash, but cannot be
        # accepted as a committed durable memory stream on its own.
        self.r2writer._put_content(self.docs[0])
        with self.assertRaises(KeyError):
            self.read()
        self.assertEqual(self.r2writer.new_objects,len(
            self.r2writer.store))
        self.assertTrue(self.r2writer.store[digest(self.docs[0])])

    def test_missing_or_corrupt_middle_event_fails_closed(self):
        self.publish()
        missing=digest(self.docs[3])
        self.r2writer.store.pop(missing)
        with self.assertRaises(KeyError):
            self.read()
        self.r2writer.store[missing]=b"invalid"
        with self.assertRaises(engine.V94DurableEventError):
            self.read("secondMissing")

    def test_changed_event_order_and_repeated_event_rejected_pre_upload(self):
        docs=self.docs.copy()
        docs[3],docs[4]=docs[4],docs[3]
        original_count=self.r2writer.new_objects
        with self.assertRaisesRegex(engine.V94DurableEventError,
                                    "EVENT_CHAIN_TAMPERED"):
            self.publish(docs,name="badOrder")
        self.assertEqual(self.r2writer.new_objects,original_count)
        docs=self.docs.copy()
        docs[1]=docs[0]
        with self.assertRaises(engine.V94DurableEventError):
            self.publish(docs,name="repeatedEvent")
        self.assertEqual(self.r2writer.new_objects,original_count)

    def test_forged_literary_or_production_flag_rejected(self):
        doc=engine._parse(self.docs[0],engine.MAX_EVENT_BYTES)
        for field in ("independent_literary_review_proven",
                      "eligible_to_direct_writing",
                      "original_work_authority_proven"):
            attack=deepcopy(doc)
            attack[field]=True
            with self.subTest(field=field):
                with self.assertRaises(engine.V94DurableEventError):
                    engine._validate_event(
                        attack,1,None)
        commit=engine._parse(self.manifest,engine.MAX_COMMIT_BYTES)
        commit["production_memory_written"]=True
        with self.assertRaisesRegex(engine.V94DurableEventError,
                                    "FALSE_APPROVAL"):
            engine._validate_manifest(engine.canonical(commit))

    def test_writer_must_preflight_replay_before_writing(self):
        changed=deepcopy(engine._parse(
            self.manifest,engine.MAX_COMMIT_BYTES))
        changed["final_state_sha256"]="f"*64
        initial=self.r2writer.new_objects
        with self.assertRaisesRegex(engine.V94DurableEventError,
                                    "REPLAY_BEFORE_UPLOAD"):
            self.publish(manifest=engine.canonical(changed),
                         name="fakeOutcome")
        self.assertEqual(self.r2writer.new_objects,initial)

    def test_exact_byte_order_and_no_raw_novel_text_in_event_receipts(self):
        serialized=b"".join(self.docs)+self.manifest
        self.assertNotIn("守桥人合上木牌".encode("utf8"),
                         serialized)
        self.assertNotIn("真正因果",serialized.decode("utf8"))
        self.assertNotIn(b"SQLite format 3",serialized)
        self.assertEqual(len(self.docs),7)
        self.assertFalse(self.state["production_user_memories_updated"])

    def test_readonly_writer_role_denied_even_with_good_manifest(self):
        with self.assertRaisesRegex(engine.V94DurableEventError,
                                    "WRITER_AND_SEPARATE_READER_REQUIRED"):
            engine.publish_chain(
                FakeCAS(read_only=True),self.reader,
                event_bytes=self.docs,manifest_raw=self.manifest,
                preflight_dir=self.dir("denied"))

    def test_repeat_publish_is_idempotent_and_preserves_old_base(self):
        self.publish(name="firstPublish")
        old_base=self.r2writer.store[engine.BASE_GRAPH_SHA]
        before=self.r2writer.new_objects
        replay=self.publish(name="secondPublish")
        self.assertFalse(replay["manifest_created"])
        self.assertEqual(self.r2writer.new_objects,before)
        self.assertEqual(self.r2writer.store[engine.BASE_GRAPH_SHA],
                         old_base)

    def test_model_supplied_arbitrary_fact_event_never_allowed(self):
        obj=engine._parse(self.docs[5],engine.MAX_EVENT_BYTES)
        obj["operation"]={
            "kind":"APPEND_DISPUTED_EVIDENCE",
            "id":"fake_model_says_someone_knew_the_future",
        }
        with self.assertRaisesRegex(engine.V94DurableEventError,
                                    "EVENT_CHAIN_TAMPERED"):
            engine._validate_event(obj,6,digest(self.docs[4]))


if __name__=="__main__":
    unittest.main()
