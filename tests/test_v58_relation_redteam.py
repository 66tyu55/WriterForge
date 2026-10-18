"""V58 fail-first: relation identity, verified disclosure and stable pagination.

Synthetic identifiers and disposable SQLite only. Never interpret, copy or
train on novels; separate independent failures from old V56/V57 receipts.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import base64
import hmac
import json
import sqlite3
import unittest

from writerforge.fact_journal import FactJournal, FactLedgerError, canonical

TRUSTED_KEY = b"only-a-synthetic-fixture-key-not-a-runtime-secret"


def event(name, tick, *, scene="chapter01", actor="hero",
          fact="seal", state="UNKNOWN", role="OBSERVE"):
    return {"event_id":name,"scene_id":scene,"actor_id":actor,
            "fact_id":fact,"tick":tick,"state":state,"role":role,
            "evidence_sha256":sha256(("evidence:"+name).encode()).hexdigest()}


def claim(name, start, state, evidence, *, scene="chapter01",
          subject="hero", scope="ACTOR", end=None, supersedes=None):
    return {"claim_id":name,"scene_id":scene,"subject_scope":scope,
            "subject_id":subject,"fact_id":"seal","story_from":start,
            "story_until":end,"knowledge_state":state,
            "evidence_event_id":evidence,"supersedes_id":supersedes}


def receipt_signature(ev, audience, released_at, secret=TRUSTED_KEY):
    message=canonical({"event_id":ev["event_id"],
                      "event_sha256":sha256(canonical(ev).encode()).hexdigest(),
                      "reader_subject":audience,
                      "disclosure_tick":released_at}).encode("utf-8")
    return hmac.new(secret,message,"sha256").hexdigest()


class V58RedTeamTests(unittest.TestCase):
    def setUp(self):
        self.temporary=TemporaryDirectory()
        self.path=Path(self.temporary.name)/"redteam.sqlite3"
        self.db=FactJournal(self.path)

    def tearDown(self):
        self.db.close()
        self.temporary.cleanup()

    def story(self):
        for scene,idx in (("chapter01",1),("chapter02",2),
                          ("chapter03",3)):
            self.db.register_scene(story_id="novelA",scene_id=scene,
                                   chapter_index=idx)

    def view(self,scene="chapter02",at=20,asof=None):
        return self.db.temporal_view(
            scene=scene,scope="ACTOR",subject="hero",fact="seal",
            story_id="novelA",story_tick=at,as_of_recorded_seq=asof)

    def test_same_label_unbound_must_not_automatically_merge_characters(self):
        self.story()
        self.db.append(event("hero-knows-in-ch1",4,state="KNOWN"))
        self.db.append_temporal_claim(claim(
            "knowledge-in-ch1",4,"KNOWN","hero-knows-in-ch1"))
        # Matching display label 'hero' is not sufficient for shared identity.
        self.assertEqual(self.view("chapter02",10)["state"],"UNRECORDED")

    def test_explicit_different_identities_never_merge_within_same_story(self):
        self.story()
        for scene,entity in (("chapter01","character-A"),
                             ("chapter02","character-B"),
                             ("chapter03","character-A")):
            self.db.bind_subject(scene_id=scene,scope="ACTOR",
                                 subject_id="hero",canonical_id=entity)
        self.db.append(event("ch1-knows",4,state="KNOWN"))
        self.db.append_temporal_claim(claim("ch1-fact",4,"KNOWN","ch1-knows"))
        self.assertEqual(self.view("chapter02",10)["state"],"UNRECORDED")
        self.assertEqual(self.view("chapter03",10)["state"],"KNOWN")
        # Once bound, changing who a scene-local name refers to is forbidden.
        with self.assertRaisesRegex(FactLedgerError,"IDENTITY_IMMUTABLE"):
            self.db.bind_subject(scene_id="chapter03",scope="ACTOR",
                                 subject_id="hero",canonical_id="character-B")

    def test_chapter_transition_respects_intervals_and_recorded_snapshot(self):
        self.story()
        for scene in ("chapter01","chapter02","chapter03"):
            self.db.bind_subject(scene_id=scene,scope="ACTOR",
                                 subject_id="hero",canonical_id="protagonist")
        self.db.append(event("does-not-know",2,state="UNKNOWN"))
        first=self.db.append_temporal_claim(
            claim("unknown-first",2,"UNKNOWN","does-not-know",end=7))
        self.db.append(event("discovers-secret",7,scene="chapter02",
                             state="KNOWN"))
        self.db.append_temporal_claim(
            claim("known-later",7,"KNOWN","discovers-secret",
                  scene="chapter02"))
        self.assertEqual(self.view("chapter03",5)["state"],"UNKNOWN")
        self.assertEqual(self.view("chapter03",9)["state"],"KNOWN")
        self.assertEqual(self.view("chapter03",9,asof=first["recorded_seq"])
                         ["state"],"UNRECORDED")
        # Overlapping, independent contradictory versions must remain conflicted.
        self.db.append(event("denies-secret",8,scene="chapter02",state="FALSE"))
        self.db.append_temporal_claim(
            claim("still-denied",8,"FALSE","denies-secret",scene="chapter02"))
        self.assertEqual(self.view("chapter03",9)["state"],
                         "CONFLICT_UNRESOLVED")

    def test_self_labeled_reveal_is_not_authenticated_disclosure(self):
        self.db.append(event("fake-narrator-reveal",4,
                             actor="narrator",state="KNOWN",role="REVEAL"))
        with self.assertRaisesRegex(FactLedgerError,"READER_ATTESTATION"):
            self.db.append_temporal_claim(
                claim("reader-knows-unverified",4,"KNOWN",
                      "fake-narrator-reveal",
                      scope="READER",subject="general-reader"))

    def test_independently_signed_reveal_has_audience_and_time_gate(self):
        self.db.close()
        self.db=FactJournal(self.path,trusted_disclosure_key=TRUSTED_KEY)
        ev=event("signed-narrator-reveal",4,actor="narrator",
                 state="KNOWN",role="REVEAL")
        self.db.append(ev)
        with self.assertRaisesRegex(FactLedgerError,"READER_ATTESTATION"):
            self.db.register_reader_disclosure(
                event_id=ev["event_id"],reader_subject="general-reader",
                disclosure_tick=8,signature="0"*64)
        self.db.register_reader_disclosure(
            event_id=ev["event_id"],reader_subject="general-reader",
            disclosure_tick=8,signature=receipt_signature(
                ev,"general-reader",8))
        with self.assertRaisesRegex(FactLedgerError,"READER.*BEFORE"):
            self.db.append_temporal_claim(
                claim("premature-before-release",5,"KNOWN",ev["event_id"],
                      scope="READER",subject="general-reader"))
        with self.assertRaisesRegex(FactLedgerError,"READER_ATTESTATION"):
            self.db.append_temporal_claim(
                claim("wrong-audience",8,"KNOWN",ev["event_id"],
                      scope="READER",subject="other-reader"))
        self.db.append_temporal_claim(
            claim("actually-released",8,"KNOWN",ev["event_id"],
                  scope="READER",subject="general-reader"))
        self.assertEqual(self.db.temporal_view(
            scene="chapter01",scope="READER",subject="general-reader",
            fact="seal",story_tick=8)["state"],"KNOWN")
        self.db.close()
        self.db=FactJournal(self.path)
        with self.assertRaisesRegex(FactLedgerError,"READER_ATTESTATION"):
            self.db.temporal_view(
                scene="chapter01",scope="READER",subject="general-reader",
                fact="seal",story_tick=8)

    def test_replay_cursor_pins_snapshot_no_duplicates_or_cross_query_use(self):
        self.story()
        self.db.bind_subject(scene_id="chapter01",scope="ACTOR",
                             subject_id="hero",canonical_id="protagonist")
        self.db.bind_subject(scene_id="chapter02",scope="ACTOR",
                             subject_id="hero",canonical_id="protagonist")
        for i in range(131):
            ident=f"e-{i:04d}"
            self.db.append(event(ident,i+1))
            self.db.append_temporal_claim(
                claim(f"claim-{i:04d}",i+1,"UNKNOWN",ident))
        initial=self.db.temporal_claim_page(
            scene="chapter02",scope="ACTOR",subject="hero",fact="seal",
            story_id="novelA",story_tick=300,limit=47)
        self.assertEqual(initial["page_count"],47)
        self.assertTrue(initial["has_more"])
        asof=initial["as_of_recorded_seq"]
        self.db.append(event("e-later",140))
        self.db.append_temporal_claim(claim(
            "claim-added-after-snapshot",140,"UNKNOWN","e-later"))
        all_ids=[x["claim_id"] for x in initial["claims"]]
        cursor=initial["next_cursor"]
        pages=1
        while cursor:
            page=self.db.temporal_claim_page(
                scene="chapter02",scope="ACTOR",subject="hero",fact="seal",
                story_id="novelA",story_tick=300,limit=47,
                as_of_recorded_seq=asof,cursor=cursor)
            all_ids += [x["claim_id"] for x in page["claims"]]
            pages+=1
            cursor=page["next_cursor"]
            self.assertLessEqual(pages,4)
        self.assertEqual(len(all_ids),131)
        self.assertEqual(len(set(all_ids)),131)
        self.assertNotIn("claim-added-after-snapshot",all_ids)
        with self.assertRaisesRegex(FactLedgerError,"CURSOR"):
            self.db.temporal_claim_page(
                scene="chapter02",scope="ACTOR",subject="hero",
                fact="otherfact",story_id="novelA",story_tick=300,
                limit=47,as_of_recorded_seq=asof,
                cursor=initial["next_cursor"])

    def test_pagination_rejects_forged_cursor_and_detects_tampered_row(self):
        self.db.append(event("proof-source",2))
        self.db.append_temporal_claim(
            claim("first-record",2,"UNKNOWN","proof-source"))
        first=self.db.temporal_claim_page(
            scene="chapter01",scope="ACTOR",subject="hero",fact="seal",
            story_tick=10,limit=1)
        with self.assertRaisesRegex(FactLedgerError,"CURSOR"):
            self.db.temporal_claim_page(
                scene="chapter01",scope="ACTOR",subject="hero",fact="seal",
                story_tick=10,limit=1,cursor="e30")
        self.db.db.execute(
            "UPDATE temporal_claims SET knowledge_state='KNOWN'"
            " WHERE claim_id='first-record'")
        self.db.db.commit()
        with self.assertRaisesRegex(FactLedgerError,"STORED_CLAIM_TAMPERED"):
            self.db.temporal_claim_page(
                scene="chapter01",scope="ACTOR",subject="hero",fact="seal",
                story_tick=10,limit=1)


if __name__=="__main__":
    unittest.main()
