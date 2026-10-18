"""V55 temporal and event graph tests: real append-only WF SQLite, no models.

The synthetic typed assertions below do NOT stand in for novel-semantic truth.
They verify state chronology, as-of-record reconstruction and fail-closed edges.
"""
from __future__ import annotations
import json
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
from writerforge.fact_journal import FactJournal, FactLedgerError


def event(identifier, clock, state="UNKNOWN", *,
          actor="witness", scene="storyscene", fact="door"):
    return {
        "event_id":identifier,"scene_id":scene,"actor_id":actor,
        "fact_id":fact,"tick":clock,"state":state,
        "role":"OBSERVE",
        "evidence_sha256":sha256(identifier.encode()).hexdigest(),
    }


def claim(identifier, beginning, state, evidence_id, *,
          ending=None, scope="ACTOR", subject="witness", supersedes=None):
    return {
        "claim_id":identifier,"scene_id":"storyscene",
        "subject_scope":scope,"subject_id":subject,
        "fact_id":"door","story_from":beginning,
        "story_until":ending,"knowledge_state":state,
        "evidence_event_id":evidence_id,"supersedes_id":supersedes,
    }


class V55TemporalProjectionTests(unittest.TestCase):
    def setUp(self):
        self.working=TemporaryDirectory()
        self.path=Path(self.working.name)/"story-facts.sqlite3"
        self.db=FactJournal(self.path)
    def tearDown(self):
        self.db.close()
        self.working.cleanup()
    def view(self, tick, *, scope="ACTOR", subject="witness", asof=None):
        return self.db.temporal_view(
            scene="storyscene",scope=scope,subject=subject,
            fact="door",story_tick=tick,as_of_recorded_seq=asof)

    def test_two_time_axes_late_correction_and_as_of_replay(self):
        self.db.append(event("seen-first",2))
        one=self.db.append_temporal_claim(
            claim("old-belief",2,"UNKNOWN","seen-first",ending=8))
        self.assertEqual(one["recorded_seq"],1)
        self.assertEqual(self.view(5,asof=1)["state"],"UNKNOWN")
        self.db.append(event("later-evidence",9,"KNOWN"))
        # A late journal entry can explicitly revise a historical interval;
        # the past remains queryable with the earlier recorded_seq.
        two=self.db.append_temporal_claim(
            claim("correct-old-time",2,"FALSE","later-evidence",
                  ending=8,supersedes="old-belief"))
        self.assertEqual(two["recorded_seq"],2)
        self.assertEqual(self.view(5,asof=1)["state"],"UNKNOWN")
        now=self.view(5)
        self.assertEqual(now["state"],"FALSE")
        self.assertIn("old-belief",now["superseded_claim_ids"])
        self.assertEqual(self.view(9)["state"],"UNRECORDED")
        self.assertEqual(self.db.append_temporal_claim(
            claim("correct-old-time",2,"FALSE","later-evidence",
                  ending=8,supersedes="old-belief"))["replayed"],True)
        self.db.close()
        self.db=FactJournal(self.path)
        self.assertEqual(self.view(5,asof=1)["state"],"UNKNOWN")
        self.assertEqual(self.view(5)["state"],"FALSE")

    def test_same_story_time_two_independent_opinions_stay_conflicted(self):
        self.db.append(event("aa",3,"KNOWN"))
        self.db.append(event("bb",3,"FALSE"))
        self.db.append_temporal_claim(claim("c1",3,"KNOWN","aa"))
        self.db.append_temporal_claim(claim("c2",3,"FALSE","bb"))
        self.assertEqual(self.view(4)["state"],"CONFLICT_UNRESOLVED")
        self.assertEqual(set(self.view(4)["active_claim_ids"]),{"c1","c2"})
        self.assertFalse(self.view(4)["story_truth_verified"])

    def test_reader_and_character_knowledge_are_not_merged(self):
        # V58 security-contract migration of this V55 positive fixture.
        # Historical V55/V57 branches remain byte-for-byte untouched.
        import hmac
        from writerforge.fact_journal import canonical, digest
        verifier_key=b"synthetic-V55-fixture-verifier-key-not-production"
        self.db.close()
        self.db=FactJournal(self.path,trusted_disclosure_key=verifier_key)
        disclosure=event("reader-note",5,"KNOWN",actor="narrator")
        self.db.append(disclosure)
        payload={"event_id":disclosure["event_id"],
                 "event_sha256":digest(canonical(disclosure)),
                 "reader_subject":"reader-general","disclosure_tick":5}
        signature=hmac.new(verifier_key,canonical(payload).encode("utf-8"),
                           "sha256").hexdigest()
        self.db.register_reader_disclosure(
            event_id=disclosure["event_id"],reader_subject="reader-general",
            disclosure_tick=5,signature=signature)
        self.db.append(event("character-note",6,"UNKNOWN"))
        self.db.append_temporal_claim(claim(
            "reader-sees",5,"KNOWN","reader-note",
            scope="READER",subject="reader-general"))
        self.db.append_temporal_claim(claim("character-unaware",6,"UNKNOWN",
                                           "character-note"))
        self.assertEqual(self.view(7,scope="READER",subject="reader-general")["state"],
                         "KNOWN")
        self.assertEqual(self.view(7)["state"],"UNKNOWN")
        self.assertEqual(self.view(7,scope="READER",subject="another-reader")["state"],
                         "UNRECORDED")

    def test_future_knowledge_and_index_witness_cannot_claim_literary_knowledge(self):
        self.db.append(event("futuristic-reveal",12,"KNOWN"))
        with self.assertRaisesRegex(FactLedgerError,"KNOWS_BEFORE_EVIDENCE"):
            self.db.append_temporal_claim(claim("premature",3,"KNOWN",
                                                "futuristic-reveal"))
        self.db.append(event("source-observation",1,"KNOWN",
                             actor="index_witness"))
        with self.assertRaisesRegex(FactLedgerError,"LEXICAL_INDEX"):
            self.db.append_temporal_claim(claim("source-not-character",1,
                "KNOWN","source-observation",scope="READER",subject="reader-general"))

    def test_supersession_must_keep_same_identity_and_interval(self):
        self.db.append(event("first-evidence",2))
        self.db.append(event("second-evidence",6))
        self.db.append_temporal_claim(claim("first-version",2,"UNKNOWN",
                                           "first-evidence",ending=6))
        with self.assertRaisesRegex(FactLedgerError,"SCOPE_OR_INTERVAL"):
            self.db.append_temporal_claim(claim("change-boundary",2,"FALSE",
                  "second-evidence",ending=7,supersedes="first-version"))
        self.db.append_temporal_claim(claim("second-version",2,"FALSE",
                  "second-evidence",ending=6,supersedes="first-version"))
        with self.assertRaisesRegex(FactLedgerError,"ALREADY_USED"):
            self.db.append_temporal_claim(claim("third-version",2,"DISPUTED",
                  "second-evidence",ending=6,supersedes="first-version"))
        with self.assertRaisesRegex(FactLedgerError,"CLAIM_IMMUTABLE"):
            self.db.append_temporal_claim(claim("second-version",2,"KNOWN",
                  "second-evidence",ending=6,supersedes="first-version"))

    def test_graph_neighbors_have_real_edge_and_do_not_assert_causality(self):
        self.db.append(event("aa",1))
        self.db.append(event("bb",2,"KNOWN"))
        self.db.append(event("cc",3,"FALSE"))
        self.db.link("aa","bb","BEFORE")
        self.db.link("bb","cc","POTENTIAL_CAUSE")
        result=self.db.graph_neighbors("aa",depth=2)
        self.assertEqual(result["relation_count"],2)
        self.assertEqual(result["visited_event_ids"],["aa","bb","cc"])
        self.assertFalse(result["narrative_causality_verified"])
        self.assertTrue(all(not v["relation_semantics_verified"]
                            for v in result["relations"]))
        with self.assertRaisesRegex(FactLedgerError,"DEPTH_INVALID"):
            self.db.graph_neighbors("aa",depth=100)
        with sqlite3.connect(self.path) as raw:
            raw.execute("UPDATE fact_links SET relation='CONTRADICTS' "
                        "WHERE source_event='aa'")
        with self.assertRaisesRegex(FactLedgerError,"RELATION_TAMPERED"):
            self.db.graph_neighbors("aa")

    def test_stored_claim_state_tampering_detected_during_read(self):
        self.db.append(event("tt",2,"UNKNOWN"))
        self.db.append_temporal_claim(claim("genuine",2,"UNKNOWN","tt"))
        with sqlite3.connect(self.path) as raw:
            raw.execute("UPDATE temporal_claims SET knowledge_state='KNOWN' "
                        "WHERE claim_id='genuine'")
        with self.assertRaisesRegex(FactLedgerError,"STORED_CLAIM_TAMPERED"):
            self.view(3)

    def test_standard_cli_uses_same_journal_for_two_clock_and_graph_queries(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from writerforge.cli import main
        self.db.append(event("learned-by-actor",4,"KNOWN"))
        p=Path(self.working.name)/"explicit-claim.json"
        p.write_text(json.dumps(
            claim("recorded-knowledge",4,"KNOWN","learned-by-actor"),
            ensure_ascii=False),encoding="utf-8")
        with redirect_stdout(StringIO()) as buf:
            main(["fact-claim","--journal",str(self.path),
                  "--file",str(p)])
        receipt=json.loads(buf.getvalue())
        self.assertFalse(receipt["semantic_truth_verified"])
        with redirect_stdout(StringIO()) as buf:
            main(["fact-view","--journal",str(self.path),
                  "--scene","storyscene","--scope","ACTOR",
                  "--subject","witness","--fact","door",
                  "--story-tick","4","--recorded-seq","1"])
        result=json.loads(buf.getvalue())
        self.assertEqual(result["state"],"KNOWN")
        with redirect_stdout(StringIO()) as buf:
            main(["fact-graph","--journal",str(self.path),
                  "--event","learned-by-actor","--depth","1"])
        graph=json.loads(buf.getvalue())
        self.assertEqual(graph["root_event_id"],"learned-by-actor")
        self.assertFalse(graph["narrative_causality_verified"])

    def test_unstructured_text_cannot_be_accepted_as_fact(self):
        with self.assertRaisesRegex(FactLedgerError,"TEMPORAL_SCHEMA_INVALID"):
            self.db.append_temporal_claim({"raw_novel_sentence":"She opened the door"})
        self.assertEqual(self.view(2)["state"],"UNRECORDED")


if __name__ == "__main__":
    unittest.main()
