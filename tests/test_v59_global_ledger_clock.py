"""V59 independent fail-first global recording-clock tests.

Borrow concepts, not code, from pyeventsourcing/eventsourcing SQLite append-only
notifications, django-simple-history's historic related-object scope and
SQLAlchemy versioning. No R2, novel snippets, model training or literary review.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import hmac
import sqlite3
import unittest

from writerforge.fact_journal import (
    FactJournal, FactLedgerError, canonical, digest
)

KEY=b"synthetic-global-clock-verifier-2026"


def ev(name, clock, scene="chapter01", *, actor="hero",
       state="UNKNOWN", role="OBSERVE"):
    return {"event_id":name,"scene_id":scene,"actor_id":actor,
            "fact_id":"seal","tick":clock,"state":state,
            "role":role,"evidence_sha256":sha256(name.encode()).hexdigest()}


def cl(name, clock, state, event_name, scene="chapter01", *,
       scope="ACTOR", subject="hero"):
    return {"claim_id":name,"scene_id":scene,"subject_scope":scope,
            "subject_id":subject,"fact_id":"seal",
            "story_from":clock,"story_until":None,
            "knowledge_state":state,"evidence_event_id":event_name,
            "supersedes_id":None}


class V59GlobalClockTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.path=Path(self.temp.name)/"global-clock.sqlite3"
        self.db=FactJournal(self.path)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def register(self, scene="chapter01", story="novelA", chapter=1):
        return self.db.register_scene(
            story_id=story,scene_id=scene,chapter_index=chapter)

    def bind(self, scene="chapter01", entity="protagonist"):
        return self.db.bind_subject(
            scene_id=scene,scope="ACTOR",
            subject_id="hero",canonical_id=entity)

    def view(self, scene="chapter02", tick=20, asof=None, legacy_asof=None):
        return self.db.temporal_view(
            scene=scene,scope="ACTOR",subject="hero",
            fact="seal",story_tick=tick,story_id="novelA",
            as_of_ledger_seq=asof,as_of_recorded_seq=legacy_asof)

    def test_global_counter_records_different_mutations_atomically(self):
        self.assertEqual(self.db.ledger_head(),0)
        st=self.register()
        su=self.bind()
        self.db.append(ev("observed-earlier",3,state="KNOWN"))
        clm=self.db.append_temporal_claim(cl(
            "first-knowledge",3,"KNOWN","observed-earlier"))
        times=[st["recorded_global_seq"],su["recorded_global_seq"],
               clm["recorded_global_seq"]]
        self.assertEqual(times,sorted(times))
        self.assertEqual(len(set(times)),3)
        self.assertEqual(self.db.ledger_head(),times[-1])
        prior=self.db.ledger_head()
        self.assertTrue(self.register()["replayed"])
        self.assertTrue(self.bind()["replayed"])
        self.assertEqual(self.db.ledger_head(),prior)
        with self.assertRaisesRegex(FactLedgerError,"IMMUTABLE"):
            self.db.register_scene(story_id="novelB",
                                   scene_id="chapter01",chapter_index=1)
        self.assertEqual(self.db.ledger_head(),prior)

    def test_late_character_binding_cannot_change_old_snapshot(self):
        self.register()
        self.register("chapter02",chapter=2)
        self.bind("chapter01")
        self.db.append(ev("chapter1-knows",3,state="KNOWN"))
        first=self.db.append_temporal_claim(cl(
            "chapter1-memory",3,"KNOWN","chapter1-knows"))
        frozen=self.db.ledger_head()
        self.assertEqual(self.view(asof=frozen)["state"],"UNRECORDED")
        self.assertEqual(self.view(legacy_asof=first["recorded_seq"])["state"],
                         "UNRECORDED")
        self.bind("chapter02")
        self.assertEqual(self.view()["state"],"KNOWN")
        self.assertEqual(self.view(asof=frozen)["state"],"UNRECORDED")
        self.assertEqual(self.view(legacy_asof=first["recorded_seq"])["state"],
                         "UNRECORDED")

    def test_late_story_registration_cannot_rewrite_history(self):
        self.register()
        self.bind("chapter01")
        self.db.append(ev("old-fact",5,state="KNOWN"))
        self.db.append_temporal_claim(cl(
            "old-knowledge",5,"KNOWN","old-fact"))
        checkpoint=self.db.ledger_head()
        self.register("chapter02",chapter=2)
        self.bind("chapter02")
        self.assertEqual(self.view()["state"],"KNOWN")
        self.assertEqual(self.view(asof=checkpoint)["state"],"UNRECORDED")

    def test_reader_attestation_added_late_cannot_authorize_old_snapshot(self):
        self.db.close()
        self.db=FactJournal(self.path,trusted_disclosure_key=KEY)
        self.register()
        record=ev("public-disclosure",7,actor="narrator",
                  state="KNOWN",role="REVEAL")
        self.db.append(record)
        tampered_old=cl("before-attestation",7,"KNOWN","public-disclosure",
                        scope="READER",subject="reader-A")
        # Import an old claim from an untrusted legacy source. We do not
        # assert this raw insert is a valid public API call.
        with self.db.db:
            self.db.db.execute(
                "INSERT INTO temporal_claims("
                "claim_id,scene,subject_scope,subject_id,fact,"
                "story_from,story_until,knowledge_state,evidence_event,"
                "supersedes_id,claim_sha) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (tampered_old["claim_id"],tampered_old["scene_id"],
                 tampered_old["subject_scope"],tampered_old["subject_id"],
                 tampered_old["fact_id"],tampered_old["story_from"],
                 tampered_old["story_until"],tampered_old["knowledge_state"],
                 tampered_old["evidence_event_id"],None,
                 digest(canonical(tampered_old))))
        before=self.db.ledger_head()
        message=canonical({
            "event_id":record["event_id"],
            "event_sha256":digest(canonical(record)),
            "reader_subject":"reader-A","disclosure_tick":7
        }).encode("utf-8")
        signature=hmac.new(KEY,message,"sha256").hexdigest()
        authorized=self.db.register_reader_disclosure(
            event_id=record["event_id"],reader_subject="reader-A",
            disclosure_tick=7,signature=signature)
        self.assertGreater(authorized["recorded_global_seq"],before)
        current=self.db.temporal_view(
            scene="chapter01",scope="READER",subject="reader-A",
            fact="seal",story_tick=10)
        self.assertEqual(current["state"],"KNOWN")
        with self.assertRaisesRegex(FactLedgerError,
                                    "ATTESTATION_NOT_AVAILABLE_AS_OF"):
            self.db.temporal_view(
                scene="chapter01",scope="READER",subject="reader-A",
                fact="seal",story_tick=10,as_of_ledger_seq=before)

    def test_cursor_replay_never_inherits_late_entity_binding(self):
        self.register()
        self.register("chapter02",chapter=2)
        self.register("chapter03",chapter=3)
        self.bind("chapter01")
        self.bind("chapter02")
        for i in range(3):
            name=f"older-{i:02d}"
            self.db.append(ev(name,2+i,state="KNOWN"))
            self.db.append_temporal_claim(cl(
                f"memory-{i:02d}",2+i,"KNOWN",name))
        self.db.append(ev("hidden-third-source",8,
                          scene="chapter03",state="KNOWN"))
        self.db.append_temporal_claim(cl(
            "hidden-third-memory",8,"KNOWN",
            "hidden-third-source",scene="chapter03"))
        start=self.db.temporal_claim_page(
            scene="chapter02",scope="ACTOR",subject="hero",fact="seal",
            story_id="novelA",story_tick=15,limit=2)
        self.assertEqual(start["page_count"],2)
        self.assertTrue(start["has_more"])
        self.bind("chapter03")
        continuation=self.db.temporal_claim_page(
            scene="chapter02",scope="ACTOR",subject="hero",fact="seal",
            story_id="novelA",story_tick=15,limit=2,
            cursor=start["next_cursor"])
        self.assertEqual([x["claim_id"] for x in continuation["claims"]],
                         ["memory-02"])
        self.assertFalse(continuation["has_more"])
        latest=self.db.temporal_claim_page(
            scene="chapter02",scope="ACTOR",subject="hero",fact="seal",
            story_id="novelA",story_tick=15,limit=64)
        self.assertIn("hidden-third-memory",
                      [x["claim_id"] for x in latest["claims"]])

    def test_legacy_bootstrap_refuses_unprovable_pre_migration_order(self):
        legacy=Path(self.temp.name)/"old-writerforge.sqlite3"
        source=ev("legacy-source",3,state="KNOWN")
        item=cl("legacy-claim",3,"KNOWN","legacy-source")
        with sqlite3.connect(legacy) as sql:
            sql.executescript("""
            CREATE TABLE fact_events(
                event_id TEXT PRIMARY KEY,scene TEXT,actor TEXT,fact TEXT,
                tick INTEGER,state TEXT,role TEXT,evidence_sha TEXT,
                event_sha TEXT);
            CREATE TABLE temporal_claims(
                recorded_seq INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id TEXT UNIQUE,scene TEXT,subject_scope TEXT,
                subject_id TEXT,fact TEXT,story_from INTEGER,
                story_until INTEGER,knowledge_state TEXT,
                evidence_event TEXT,supersedes_id TEXT,claim_sha TEXT);
            CREATE TABLE story_scenes(
                scene_id TEXT PRIMARY KEY,story_id TEXT,
                chapter_index INTEGER,binding_sha TEXT);
            CREATE TABLE story_subjects(
                scene_id TEXT,subject_scope TEXT,subject_id TEXT,
                canonical_id TEXT,binding_sha TEXT,
                PRIMARY KEY(scene_id,subject_scope,subject_id));
            """)
            sql.execute("INSERT INTO fact_events VALUES(?,?,?,?,?,?,?,?,?)",
                (source["event_id"],source["scene_id"],source["actor_id"],
                 source["fact_id"],source["tick"],source["state"],
                 source["role"],source["evidence_sha256"],
                 digest(canonical(source))))
            sql.execute("INSERT INTO temporal_claims("
                "claim_id,scene,subject_scope,subject_id,fact,"
                "story_from,story_until,knowledge_state,evidence_event,"
                "supersedes_id,claim_sha) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (item["claim_id"],item["scene_id"],item["subject_scope"],
                 item["subject_id"],item["fact_id"],item["story_from"],
                 None,item["knowledge_state"],item["evidence_event_id"],
                 None,digest(canonical(item))))
            for scene,chapter in (("chapter01",1),("chapter02",2)):
                binding={"story_id":"novelA","scene_id":scene,
                         "chapter_index":chapter}
                sql.execute("INSERT INTO story_scenes VALUES(?,?,?,?)",
                    (scene,"novelA",chapter,digest(canonical(binding))))
                identity={"scene_id":scene,"subject_scope":"ACTOR",
                          "subject_id":"hero","canonical_id":"protagonist"}
                sql.execute("INSERT INTO story_subjects VALUES(?,?,?,?,?)",
                    (scene,"ACTOR","hero","protagonist",
                     digest(canonical(identity))))
        migrated=FactJournal(legacy)
        try:
            head=migrated.ledger_head()
            self.assertGreater(head,0)
            self.assertEqual(migrated.temporal_view(
                scene="chapter02",scope="ACTOR",subject="hero",
                fact="seal",story_tick=10,story_id="novelA")["state"],"KNOWN")
            with self.assertRaisesRegex(FactLedgerError,
                                        "LEGACY_ORDER_UNPROVABLE"):
                migrated.temporal_view(
                    scene="chapter02",scope="ACTOR",subject="hero",
                    fact="seal",story_tick=10,story_id="novelA",
                    as_of_ledger_seq=head-1)
            with self.assertRaisesRegex(FactLedgerError,
                                        "LEGACY_ORDER_UNPROVABLE"):
                migrated.temporal_view(
                    scene="chapter02",scope="ACTOR",subject="hero",
                    fact="seal",story_tick=10,story_id="novelA",
                    as_of_recorded_seq=1)
        finally:
            migrated.close()

    def test_ledger_clock_persists_across_reopen(self):
        x=self.register()
        stamp=x["recorded_global_seq"]
        self.db.close()
        self.db=FactJournal(self.path)
        self.assertEqual(self.db.ledger_head(),stamp)
        new=self.register("chapter02",chapter=2)
        self.assertGreater(new["recorded_global_seq"],stamp)

    def test_graph_does_not_retroactively_include_later_edge(self):
        self.register()
        self.db.append(ev("graph-source",2,state="KNOWN"))
        self.db.append(ev("graph-target",6,state="KNOWN"))
        before=self.db.ledger_head()
        self.db.link("graph-source","graph-target","BEFORE")
        self.assertEqual(self.db.graph_neighbors("graph-source",depth=1)
                         ["relation_count"],1)
        historical=self.db.graph_neighbors(
            "graph-source",depth=1,as_of_ledger_seq=before)
        self.assertEqual(historical["relation_count"],0)
        with self.assertRaisesRegex(FactLedgerError,"EVENT_NOT_AVAILABLE_AS_OF"):
            self.db.graph_neighbors("graph-target",depth=1,
                                    as_of_ledger_seq=1)

    def test_graph_cross_chapter_link_rejects_future_scope(self):
        self.db.append(ev("before-chapter",3))
        self.db.append(ev("after-chapter",8,scene="chapter02"))
        frozen=self.db.ledger_head()
        self.register()
        self.register("chapter02",chapter=2)
        self.db.link("before-chapter","after-chapter","BEFORE")
        graph=self.db.graph_neighbors(
            "before-chapter",as_of_ledger_seq=frozen)
        self.assertEqual(graph["relation_count"],0)

    def test_cli_exposes_full_global_clock_and_historical_queries(self):
        import json
        from io import StringIO
        from contextlib import redirect_stdout
        from writerforge.cli import main

        def cli(*args):
            stream=StringIO()
            with redirect_stdout(stream):
                main(list(args))
            return json.loads(stream.getvalue())

        for scene,index in (("chapter01","1"),("chapter02","2")):
            cli("fact-story-bind","--journal",str(self.path),
                "--story-id","novelA","--scene",scene,
                "--chapter-index",index)
        cli("fact-subject-bind","--journal",str(self.path),
            "--scene","chapter01","--scope","ACTOR","--subject","hero",
            "--canonical-id","protagonist")
        self.db.append(ev("cli-knowledge",3,state="KNOWN"))
        self.db.append_temporal_claim(cl(
            "cli-history",3,"KNOWN","cli-knowledge"))
        frozen=cli("fact-ledger-head","--journal",str(self.path))
        self.assertEqual(frozen["global_seq"],self.db.ledger_head())
        cli("fact-subject-bind","--journal",str(self.path),
            "--scene","chapter02","--scope","ACTOR","--subject","hero",
            "--canonical-id","protagonist")
        old=cli("fact-view","--journal",str(self.path),
                "--scene","chapter02","--story-id","novelA",
                "--scope","ACTOR","--subject","hero","--fact","seal",
                "--story-tick","9","--ledger-seq",str(frozen["global_seq"]))
        now=cli("fact-view","--journal",str(self.path),
                "--scene","chapter02","--story-id","novelA",
                "--scope","ACTOR","--subject","hero","--fact","seal",
                "--story-tick","9")
        self.assertEqual(old["state"],"UNRECORDED")
        self.assertEqual(now["state"],"KNOWN")
        page=cli("fact-page","--journal",str(self.path),
                 "--scene","chapter02","--story-id","novelA",
                 "--scope","ACTOR","--subject","hero","--fact","seal",
                 "--story-tick","9","--ledger-seq",str(frozen["global_seq"]))
        self.assertEqual(page["page_count"],0)

    def test_two_connections_observe_monotone_clock_and_rollback(self):
        other=FactJournal(self.path)
        try:
            first=self.register()
            second=other.register_scene(story_id="novelA",
                                        scene_id="chapter02",chapter_index=2)
            self.assertLess(first["recorded_global_seq"],
                            second["recorded_global_seq"])
            at=other.ledger_head()
            with self.assertRaisesRegex(FactLedgerError,"IMMUTABLE"):
                other.register_scene(story_id="otherNovel",
                                     scene_id="chapter01",chapter_index=1)
            self.assertEqual(self.db.ledger_head(),at)
            self.assertEqual(other.ledger_head(),at)
        finally:
            other.close()


if __name__=="__main__":
    unittest.main()
