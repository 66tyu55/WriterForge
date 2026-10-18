"""V57 adversarial regression: explicit provenance, cross-chapter scope, budgets.

Only synthetic identifiers in throwaway SQLite. No LLM, R2 or literary training.
The frozen V56 audit is intentionally never edited or retroactively re-scored.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from writerforge.fact_journal import FactJournal, FactLedgerError


def event(name, tick, *, scene="chapter01", actor="hero",
          fact="seal", state="UNKNOWN", role="OBSERVE"):
    return {"event_id": name, "scene_id": scene, "actor_id": actor,
            "fact_id": fact, "tick": tick, "state": state, "role": role,
            "evidence_sha256": sha256(name.encode()).hexdigest()}


def claim(name, tick, state, evidence, *, scene="chapter01",
          subject="hero", scope="ACTOR", fact="seal",
          supersedes=None, until=None):
    return {"claim_id": name, "scene_id": scene, "subject_scope": scope,
            "subject_id": subject, "fact_id": fact, "story_from": tick,
            "story_until": until, "knowledge_state": state,
            "evidence_event_id": evidence, "supersedes_id": supersedes}


class V57RelationFoundationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.path = Path(self.temp.name) / "synthetic.sqlite3"
        self.db = FactJournal(self.path)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def view(self, scene="chapter01", at=25, story_id=None, asof=None):
        return self.db.temporal_view(
            scene=scene, story_id=story_id, scope="ACTOR",
            subject="hero", fact="seal", story_tick=at,
            as_of_recorded_seq=asof)

    def test_future_reader_reveal_rejected_even_with_valid_narrator(self):
        self.db.append(event("future-reveal", 20, actor="narrator",
                             role="REVEAL", state="KNOWN"))
        with self.assertRaisesRegex(FactLedgerError, "READER_KNOWS_BEFORE"):
            self.db.append_temporal_claim(claim(
                "early-reader", 3, "KNOWN", "future-reveal",
                scope="READER", subject="general-reader"))
        self.assertEqual(self.db.temporal_view(
            scene="chapter01",scope="READER",subject="general-reader",
            fact="seal",story_tick=3)["state"], "UNRECORDED")

    def test_private_thought_must_have_explicit_disclosure(self):
        self.db.append(event("secret", 4, state="KNOWN", role="THINK"))
        with self.assertRaisesRegex(FactLedgerError, "READER_DISCLOSURE"):
            self.db.append_temporal_claim(claim(
                "illegal-secret", 4, "KNOWN", "secret",
                scope="READER",subject="general-reader"))
        self.db.append(event("public-reveal", 8, state="KNOWN", role="REVEAL"))
        self.db.append_temporal_claim(claim(
            "legal-disclosure", 8, "KNOWN", "public-reveal",
            scope="READER",subject="general-reader"))
        self.assertEqual(self.db.temporal_view(
            scene="chapter01",scope="READER",subject="general-reader",
            fact="seal",story_tick=8)["state"], "KNOWN")

    def test_unknown_or_false_source_cannot_certify_known(self):
        for name, state in (("unclear","UNKNOWN"), ("denied","FALSE")):
            self.db.append(event(name, 3, state=state))
            with self.assertRaisesRegex(FactLedgerError, "KNOWLEDGE_UNSUPPORTED"):
                self.db.append_temporal_claim(
                    claim("illegal-"+name, 3, "KNOWN", name))
        self.assertEqual(self.view()["state"], "UNRECORDED")

    def test_cross_chapter_requires_registered_same_story(self):
        self.db.append(event("clue", 4, state="KNOWN"))
        self.db.append(event("payoff", 21, scene="chapter03",state="KNOWN"))
        with self.assertRaisesRegex(FactLedgerError, "CROSS_SCENE"):
            self.db.link("clue","payoff","BEFORE")
        self.db.register_scene(story_id="novelA",scene_id="chapter01",
                               chapter_index=1)
        self.db.register_scene(story_id="novelA",scene_id="chapter03",
                               chapter_index=3)
        self.db.link("clue","payoff","BEFORE")
        graph = self.db.graph_neighbors("clue")
        self.assertEqual(graph["relation_count"],1)
        self.assertEqual(graph["relations"][0]["relation"],"BEFORE")
        self.assertFalse(graph["narrative_causality_verified"])
        self.db.append_temporal_claim(claim("chapter1-knows",4,"KNOWN","clue"))
        view = self.view(scene="chapter03",at=22,story_id="novelA")
        self.assertEqual(view["state"],"KNOWN")
        self.assertEqual(view["active_claim_ids"],["chapter1-knows"])
        # Old scene-local API still does not leak knowledge into other chapters.
        self.assertEqual(self.view(scene="chapter03",at=22)["state"],
                         "UNRECORDED")

    def test_other_story_never_joins_even_with_same_fact(self):
        self.db.register_scene(story_id="novelA",scene_id="chapter01",
                               chapter_index=1)
        self.db.register_scene(story_id="novelB",scene_id="different03",
                               chapter_index=3)
        self.db.append(event("event-a",4,state="KNOWN"))
        self.db.append(event("event-b",5,state="KNOWN",scene="different03"))
        self.db.append_temporal_claim(claim("a-knows",4,"KNOWN","event-a"))
        with self.assertRaisesRegex(FactLedgerError,"CROSS_SCENE"):
            self.db.link("event-a","event-b","BEFORE")
        self.assertEqual(self.view(scene="different03",story_id="novelB")["state"],
                         "UNRECORDED")
        with self.assertRaisesRegex(FactLedgerError,"STORY_SCOPE"):
            self.view(scene="different03",story_id="novelA")

    def test_registered_story_mapping_is_immutable_and_tamper_checked(self):
        self.db.register_scene(story_id="novelA",scene_id="chapter01",
                               chapter_index=1)
        with self.assertRaisesRegex(FactLedgerError,"BINDING_IMMUTABLE"):
            self.db.register_scene(story_id="novelB",scene_id="chapter01",
                                   chapter_index=1)
        self.db.db.execute("UPDATE story_scenes SET story_id='novelB'")
        self.db.db.commit()
        with self.assertRaisesRegex(FactLedgerError,"BINDING_TAMPERED"):
            self.view(story_id="novelB")

    def test_flashback_import_is_explicit_and_keeps_event_record_order(self):
        self.db.register_scene(story_id="novelA",scene_id="chapter01",
                               chapter_index=1)
        self.db.append(event("later-event",20,state="KNOWN"))
        with self.assertRaisesRegex(FactLedgerError,"BACKDATED_REVISION"):
            self.db.append(event("earlier-event",3))
        with self.assertRaisesRegex(FactLedgerError,"UNREGISTERED_STORY"):
            self.db.append_flashback(event("earlier-event",3),story_id="novelB")
        row=self.db.append_flashback(event("earlier-event",3),story_id="novelA")
        self.assertGreater(row["recorded_seq"],1)
        self.assertFalse(row["replayed"])
        self.assertTrue(self.db.append_flashback(
            event("earlier-event",3),story_id="novelA")["replayed"])
        self.assertEqual(self.db.db.execute(
            "SELECT tick FROM fact_events WHERE event_id='earlier-event'"
        ).fetchone()[0],3)
        self.db.close()
        self.db=FactJournal(self.path)
        self.assertTrue(self.db.append_flashback(
            event("earlier-event",3),story_id="novelA")["replayed"])

    def test_corrected_legitimate_no_fork_fixture(self):
        self.db.append(event("old-proof",2,state="UNKNOWN"))
        self.db.append(event("new-proof",8,state="FALSE"))
        self.db.append_temporal_claim(claim(
            "original",2,"UNKNOWN","old-proof",until=6))
        self.db.append_temporal_claim(claim(
            "amendment-1",2,"FALSE","new-proof",
            supersedes="original",until=6))
        with self.assertRaisesRegex(FactLedgerError, "SUPERSESSION_ALREADY_USED"):
            self.db.append_temporal_claim(claim(
                "amendment-2",2,"FALSE","new-proof",
                supersedes="original",until=6))
        self.assertEqual(self.view(at=4)["state"],"FALSE")

    def test_more_than_64_independent_claims_stream_without_losing_conflicts(self):
        for i in range(68):
            name=f"evt-{i:03}"
            self.db.append(event(name,i+1))
            self.db.append_temporal_claim(claim(
                f"clm-{i:03}",i+1,"UNKNOWN",name))
        result=self.view(at=100)
        self.assertEqual(result["state"],"UNKNOWN")
        self.assertEqual(result["claim_count_examined"],68)
        self.assertEqual(result["active_claim_count"],68)
        self.assertEqual(len(result["active_claim_ids"]),64)
        self.assertTrue(result["active_claims_truncated"])
        self.db.append(event("conflict-evidence",70,state="FALSE"))
        self.db.append_temporal_claim(claim(
            "real-conflict",70,"FALSE","conflict-evidence"))
        result=self.view(at=100)
        self.assertEqual(result["state"],"CONFLICT_UNRESOLVED")
        self.assertEqual(result["active_claim_count"],69)

    def test_old_record_snapshot_survives_long_supersession_chain(self):
        self.db.append(event("initial",1))
        first=self.db.append_temporal_claim(
            claim("version-000",1,"UNKNOWN","initial",until=100))
        parent="version-000"
        for i in range(1,70):
            e=f"update-evt-{i:03}"
            c=f"version-{i:03}"
            self.db.append(event(e,1+i,state="FALSE"))
            self.db.append_temporal_claim(
                claim(c,1,"FALSE",e,supersedes=parent,until=100))
            parent=c
        self.assertEqual(self.view(at=25,asof=first["recorded_seq"])["state"],
                         "UNKNOWN")
        now=self.view(at=25)
        self.assertEqual(now["state"],"FALSE")
        self.assertEqual(now["active_claim_count"],1)
        self.assertEqual(now["claim_count_examined"],70)
        self.assertEqual(now["active_claim_ids"],["version-069"])

    def test_cli_full_path_binding_cross_chapter_view_and_flashback(self):
        # Tests actual WF commands, not only Python methods.
        import json
        from io import StringIO
        from contextlib import redirect_stdout
        from writerforge.cli import main

        def call(*args):
            output=StringIO()
            with redirect_stdout(output):
                main(list(args))
            return json.loads(output.getvalue())

        for n,chapter in (("chapter01","1"),("chapter02","2")):
            receipt=call("fact-story-bind","--journal",str(self.path),
                         "--story-id","novelA","--scene",n,
                         "--chapter-index",chapter)
            self.assertIn("binding_sha256",receipt)
        self.db.append(event("hero-learned",4,state="KNOWN"))
        self.db.append_temporal_claim(claim(
            "hero-history",4,"KNOWN","hero-learned"))
        view=call("fact-view","--journal",str(self.path),
                  "--scene","chapter02","--story-id","novelA",
                  "--scope","ACTOR","--subject","hero",
                  "--fact","seal","--story-tick","15")
        self.assertEqual(view["state"],"KNOWN")

        self.db.append(event("hero-later",20,state="KNOWN"))
        p=Path(self.temp.name)/"typed-flashback.json"
        p.write_text(json.dumps(event("hero-earlier",3)),encoding="utf-8")
        ingest=call("fact-flashback","--journal",str(self.path),
                    "--story-id","novelA","--file",str(p))
        self.assertFalse(ingest["replayed"])
        self.assertGreater(ingest["recorded_seq"],0)
        again=call("fact-flashback","--journal",str(self.path),
                   "--story-id","novelA","--file",str(p))
        self.assertTrue(again["replayed"])


    def test_database_unique_index_prevents_concurrent_successor_fork(self):
        # V56 no_fork fixture was invalid. This checks the DB itself, not
        # merely Python's sequential preflight.
        from writerforge.fact_journal import canonical, digest
        self.db.append(event("primary-proof",2))
        self.db.append(event("correction-proof",8,state="FALSE"))
        self.db.append_temporal_claim(claim(
            "primary-claim",2,"UNKNOWN","primary-proof",until=6))
        self.db.append_temporal_claim(claim(
            "accepted-correction",2,"FALSE","correction-proof",
            supersedes="primary-claim",until=6))
        forged=claim("parallel-correction",2,"FALSE","correction-proof",
                     supersedes="primary-claim",until=6)
        with sqlite3.connect(self.path) as independent_writer:
            with self.assertRaises(sqlite3.IntegrityError):
                independent_writer.execute(
                    "INSERT INTO temporal_claims("
                    "claim_id,scene,subject_scope,subject_id,fact,story_from,"
                    "story_until,knowledge_state,evidence_event,supersedes_id,claim_sha)"
                    " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (forged["claim_id"],forged["scene_id"],
                     forged["subject_scope"],forged["subject_id"],forged["fact_id"],
                     forged["story_from"],forged["story_until"],
                     forged["knowledge_state"],forged["evidence_event_id"],
                     forged["supersedes_id"],digest(canonical(forged))))
        self.assertEqual(self.view(at=4)["active_claim_ids"],
                         ["accepted-correction"])


if __name__ == "__main__":
    unittest.main()
