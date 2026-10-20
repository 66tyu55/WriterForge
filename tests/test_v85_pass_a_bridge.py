"""V85: existing R2 schema PASS-A provenance checks with fake CAS/FactJournal."""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from writerforge.fact_journal import FactJournal
from writerforge.r2_learn_journal import identity, event_doc, canonical
from writerforge.v85_literary_evidence_gate import (
    LiteraryEvidenceGate, LiteraryEvidenceError,
)
from writerforge.v85_pass_a_bridge import V85SealedLearningBridge

def h(s):
    return sha256(s.encode("utf8")).hexdigest()

WINDOWS=(
    "暮色压住旧桥，少年看见守桥人悄悄熄灭了灯，却没有告诉同行的妹妹。",
    "桥外远远传来钟声，少年收起渡河的木牌，决定今晚先等待，不贸然走近。",
)
SOURCE=h("sample-book")
KEY="writerforge/v1/private-reading/仙侠/example/source.txt"
CHAPTER=h("".join(WINDOWS))
REACTION={
    "attention":1,"curiosity":2,"confusion":0,"tension":1,
    "urge_to_continue":2,"question":"","prediction":"","what_changed":""
}

class FakeJournal:
    def __init__(self,ident):
        self.read_only=True
        self.writer=None
        self.events={}
        self.writes=0
        previous=None
        for number,part in enumerate(WINDOWS,1):
            doc=event_doc(stage="first_read",ident=ident,unit=number,
                source_unit_sha256=h(part),previous_event_sha256=previous,
                future_source_seen=False,reaction=dict(REACTION))
            previous=sha256(canonical(doc)).hexdigest()
            self.events[("first_read",number)]={
                "event_sha256":previous,"doc":doc}
        seal=event_doc(stage="seal",ident=ident,units_read=len(WINDOWS),
                       last_first_read_sha256=previous,future_source_seen=False)
        self.events[("seal",None)]={
            "event_sha256":sha256(canonical(seal)).hexdigest(),"doc":seal}
    def fetch_event(self,*,ident,stage,unit=None):
        return self.events.get((stage,unit))
    def _get_content(self,sha):
        raise AssertionError("unexpected remote read")
    def _put_content(self,raw):
        self.writes+=1
        return sha256(raw).hexdigest(),True

class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.fact=FactJournal(Path(self.tmp.name)/"facts.sqlite3")
        self.fact.register_scene(story_id="novelA",scene_id="chapter03",
                                 chapter_index=3)
        self.fact.bind_subject(scene_id="chapter03",scope="ACTOR",
                               subject_id="hero",canonical_id="heroA")
        self.ident=identity(source_key=KEY,source_sha=SOURCE,
                            chapter=3,chapter_body_sha=CHAPTER)
        self.journal=FakeJournal(self.ident)
        self.gate=LiteraryEvidenceGate(
            self.fact,story_id="novelA",scene_id="chapter03",
            source_sha256=SOURCE,ledger_seq=self.fact.ledger_head())
        self.bridge=V85SealedLearningBridge(self.journal,self.gate)

    def tearDown(self):
        self.fact.close()
        self.tmp.cleanup()

    def test_real_r2_format_all_units_and_seal_abstention(self):
        result=self.bridge.audit_sealed_chapter(
            ident=self.ident,windows=WINDOWS,proposals=[])
        self.assertTrue(result["original_pass_a_chain_verified"])
        self.assertEqual(result["audit"]["result"],"ABSTAIN_NO_CLAIMS")
        self.assertFalse(result["writer_can_consume_this_as_verified_skill"])
        self.assertEqual(self.journal.writes,0)
        with self.assertRaisesRegex(LiteraryEvidenceError,"NOT_AUTHORIZED"):
            self.bridge.persist_sidecar(result)

    def test_missing_unit_and_broken_previous_sha_refused(self):
        self.journal.events.pop(("first_read",2))
        with self.assertRaisesRegex(LiteraryEvidenceError,"FIRST_READ_MISSING"):
            self.bridge.audit_sealed_chapter(
                ident=self.ident,windows=WINDOWS,proposals=[])
        self.journal=FakeJournal(self.ident)
        self.bridge=V85SealedLearningBridge(self.journal,self.gate)
        self.journal.events[("first_read",2)]["doc"][
            "previous_event_sha256"]=h("different-event")
        with self.assertRaisesRegex(LiteraryEvidenceError,"HASH_ORDER"):
            self.bridge.audit_sealed_chapter(
                ident=self.ident,windows=WINDOWS,proposals=[])

    def test_false_seal_and_wrong_chapter_source_refused(self):
        self.journal.events[("seal",None)]["doc"]["units_read"]=1
        with self.assertRaisesRegex(LiteraryEvidenceError,"NOT_SEALED"):
            self.bridge.audit_sealed_chapter(
                ident=self.ident,windows=WINDOWS,proposals=[])
        alternate=dict(self.ident,chapter=1)
        with self.assertRaisesRegex(LiteraryEvidenceError,"NOT_STRICT_CHAPTER"):
            self.bridge.audit_sealed_chapter(
                ident=alternate,windows=WINDOWS,proposals=[])

    def test_v80_real_executor_exposes_explicit_only_gate(self):
        from writerforge.v80_large_chapter_batch import WFLargeChapterBatch
        # Existing V80 constructor remains unchanged; bind the same sealed
        # synthetic first-read R2 journal used by the normal tests.
        batch=object.__new__(WFLargeChapterBatch)
        batch.journal=self.journal
        batch.key=KEY
        batch.source_sha=SOURCE
        class Chapter:
            ordinal=3
            body_sha256=CHAPTER
        result=batch.audit_sealed_literary_claims(
            chapter=Chapter(),windows=list(WINDOWS),
            gate=self.gate,proposals=[])
        self.assertTrue(result["original_pass_a_chain_verified"])
        self.assertEqual(self.journal.writes,0)
        self.assertFalse(result["writer_can_consume_this_as_verified_skill"])
        class Pilot:
            ordinal=1
            body_sha256=CHAPTER
        with self.assertRaisesRegex(ValueError,"MIXED_PILOT"):
            batch.audit_sealed_literary_claims(
                chapter=Pilot(),windows=list(WINDOWS),
                gate=self.gate,proposals=[])

    def test_storage_requires_writer_and_prevents_tampered_receipt(self):
        result=self.bridge.audit_sealed_chapter(
            ident=self.ident,windows=WINDOWS,proposals=[])
        with self.assertRaisesRegex(LiteraryEvidenceError,"WRITER_REQUIRED"):
            self.bridge.persist_sidecar(result,explicitly_allow_write=True)
        self.journal.read_only=False
        self.journal.writer="synthetic-writer"
        altered=dict(result)
        altered["audit"]=dict(result["audit"],claims_count=2)
        with self.assertRaisesRegex(LiteraryEvidenceError,"HASH_MISMATCH"):
            self.bridge.persist_sidecar(
                altered,explicitly_allow_write=True)
        got=self.bridge.persist_sidecar(
            result,explicitly_allow_write=True)
        self.assertEqual(self.journal.writes,1)
        self.assertFalse(got["original_prose_written"])

if __name__=="__main__":
    unittest.main()
