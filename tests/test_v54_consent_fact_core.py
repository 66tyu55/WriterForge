"""V54: no silent downloads and model-free typed fact/experience lifecycle."""
from __future__ import annotations

from contextlib import redirect_stdout
from hashlib import sha256
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import sqlite3
import unittest

from writerforge.cli import main
from writerforge.resource_policy import (
    offline_status, plan_r2, approved_sync, ResourcePolicyError,
)
from writerforge.fact_journal import FactJournal, FactLedgerError
from writerforge.scratch import prepare_scratch
from writerforge.r2_storage import R2Config, R2StudyVault
from writerforge import WriterForgeDB, RuntimeEngine, OriginalStudy
from test_v52_r2_native_lookup import FakeStore, SOURCE, BUCKET, LIBRARY

def original_event(i,tick,status,*,role="OBSERVE",fact="door_seal",scene="night_river"):
    return {"event_id":i, "scene_id":scene, "actor_id":"observer",
            "fact_id":fact, "tick":tick,"state":status,"role":role,
            "evidence_sha256":sha256(i.encode()).hexdigest()}


class UserResourcePolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.root=Path(self.tmp.name)
        db=self.root/"study.sqlite3"
        writer=WriterForgeDB(db)
        rt=RuntimeEngine();rt.enter_learn()
        OriginalStudy(writer,rt).ingest(
            SOURCE.read_text(encoding="utf-8"),work_id="test-user-study",
            require_hundred=False)
        writer.close()
        self.store=FakeStore()
        self.vault=R2StudyVault(R2Config(
            account_id="a"*32,bucket=BUCKET,
            access_key_id="test",secret_access_key="test"),
            client=self.store)
        self.original=self.vault.backup(database=db,library=LIBRARY)
        self.snap=self.original["snapshot"]
    def tearDown(self):
        self.tmp.cleanup()

    def test_status_and_scratch_are_offline_without_r2_or_db_creation(self):
        before=set(self.root.iterdir())
        self.assertFalse(offline_status()["automatic_corpus_download_on_install"])
        with patch("writerforge.r2_storage.R2StudyVault.restore",
                   side_effect=AssertionError("unexpected R2")):
            with redirect_stdout(StringIO()) as output:
                main(["--db",str(self.root/"unexpected.sqlite3"),"resource-status"])
            self.assertFalse(json.loads(output.getvalue())[
                "automatic_corpus_download_on_install"])
            with redirect_stdout(StringIO()) as output:
                main(["--db",str(self.root/"unexpected.sqlite3"),
                      "scratch-context","--scene","空亭","--goal",
                      "写一段完全独立原创的空亭清晨景物，没有人物或人类行动。"])
            data=json.loads(output.getvalue())
        self.assertFalse(data["private_r2_required"])
        self.assertFalse(data["download_requested"])
        self.assertEqual(set(self.root.iterdir()),before)
        self.assertFalse((self.root/"unexpected.sqlite3").exists())

    def test_download_without_explicit_consent_cannot_touch_r2(self):
        with patch("writerforge.r2_storage.R2Config.from_environment",
                   side_effect=AssertionError("should never read credentials")):
            with self.assertRaisesRegex(ResourcePolicyError,"CONSENT_REQUIRED"):
                main(["r2-sync","--library",LIBRARY,
                      "--snapshot",self.snap,
                      "--cache-dir",str(self.root/"new")])
        self.assertFalse((self.root/"new").exists())

    def test_r2_metadata_only_plan_and_download_budget_preflight(self):
        p=plan_r2(self.vault,library=LIBRARY,snapshot=self.snap,
                  cache=self.root/"other")
        self.assertGreater(p["remote_source_bytes"],0)
        self.assertFalse(p["download_performed"])
        self.assertTrue(p["requires_separate_explicit_download_approval"])
        self.assertEqual(self.store.download_count,0)
        with patch("writerforge.resource_policy.plan_r2",
                   return_value={**p,"remote_source_bytes":2*1024*1024}):
            with self.assertRaisesRegex(ResourcePolicyError,"EXCEEDS_USER_APPROVED"):
                approved_sync(self.vault,library=LIBRARY,snapshot=self.snap,
                              cache=self.root/"blocked",approved=True,
                              max_download_mib=1)
        self.assertEqual(self.store.download_count,0)
        self.assertFalse((self.root/"blocked").exists())
        # Existing tests already exercise R2StudyVault.restore and build_index.
        # This wrapper must use the SAME implementation after approval.
        success=approved_sync(self.vault,library=LIBRARY,snapshot=self.snap,
                              cache=self.root/"approved",approved=True,
                              max_download_mib=256)
        self.assertTrue(success["explicit_user_approval"])
        self.assertTrue((self.root/"approved"/LIBRARY/self.snap[:16]/
                         "corpus-index.sqlite3").is_file())
        self.assertGreater(self.store.download_count,0)

    def test_index_observer_creates_real_structural_fact_journal_without_model(self):
        from writerforge.structural_observer import observe_corpus
        approved_sync(self.vault,library=LIBRARY,snapshot=self.snap,
                      cache=self.root/"local-index",approved=True,max_download_mib=256)
        journal=self.root/"index-witness.sqlite3"
        with patch("writerforge.r2_storage.R2StudyVault.restore",
                   side_effect=AssertionError("offline observer cannot call R2")):
            a=observe_corpus(cache=self.root/"local-index",
                     library=LIBRARY,snapshot=self.snap,
                     terms=("猴王",),journal_path=journal)
            b=observe_corpus(cache=self.root/"local-index",
                     library=LIBRARY,snapshot=self.snap,
                     terms=("猴王",),journal_path=journal)
        self.assertEqual(a,b)
        self.assertGreater(a["observed_events"],0)
        self.assertTrue(a["literal_occurrence_only"])
        self.assertFalse(a["actual_original_sentences_exposed"])
        self.assertFalse(a["candidate_eligible_for_creative_execution"])
        self.assertEqual(a["temporal_order_relations"],0)
        self.assertTrue(a["index_order_is_not_story_time"])
        with sqlite3.connect(journal) as db:
            n=db.execute("SELECT COUNT(*) FROM fact_events").fetchone()[0]
            self.assertEqual(n,a["observed_events"])
            kinds=[x[0] for x in db.execute("SELECT DISTINCT actor FROM fact_events")]
            self.assertEqual(kinds,["index_witness"])
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM fact_links").fetchone()[0],
                a["temporal_order_relations"])

    def test_resource_free_scratch_writes_only_on_explicit_local_model_action(self):
        # No data download, DB, private R2 or remote API needed for a new user.
        with patch("writerforge.verified_flow.local_chat_completion",
                   return_value="独立原创场景，人物在门口选择要不要进屋。"*16):
            with redirect_stdout(StringIO()) as buf:
                main(["--db",str(self.root/"unwanted-db.sqlite3"),
                      "draft-scratch","--scene","夜间客栈",
                      "--goal","写一段全新客栈人物做出决定的原创故事，所有人物和事件必须重新构建。",
                      "--model","mock-loopback-not-real",
                      "--output-dir",str(self.root/"scratch-results")])
        result=json.loads(buf.getvalue())
        self.assertTrue(result["no_corpus_used"])
        self.assertTrue(result["not_trained_writer"])
        self.assertFalse(result["accepted"])
        self.assertTrue(Path(result["candidate"]).is_file())
        self.assertFalse((self.root/"unwanted-db.sqlite3").exists())

    def test_metadata_queries_reject_missing_or_bad_credentials_without_guessing(self):
        with self.assertRaisesRegex(ResourcePolicyError,"CONSENT_REQUIRED"):
            approved_sync(self.vault,library=LIBRARY,snapshot=self.snap,
                          cache=self.root/"no",approved=False)


class FactLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.db=FactJournal(self.root/"ledger.sqlite3")
    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_timeline_and_knowledge_conflict_are_preserved(self):
        self.db.append(original_event("looked",1,"UNKNOWN"))
        self.db.append(original_event("claimed-known",2,"KNOWN"))
        self.db.append(original_event("contrary",2,"FALSE"))
        r=self.db.state(scene="night_river",actor="observer",fact="door_seal")
        self.assertEqual(r["state"],"CONFLICT_UNRESOLVED")
        self.assertEqual(set(r["conflicting_events"]),
                         {"claimed-known","contrary"})
        previous=self.db.state(scene="night_river",actor="observer",
                               fact="door_seal",at_tick=1)
        self.assertEqual(previous["state"],"UNKNOWN")
        self.db.append(original_event("later-confirmation",3,"KNOWN",role="REVEAL"))
        self.assertEqual(self.db.state(scene="night_river",actor="observer",
                          fact="door_seal")["state"],"KNOWN")
        self.assertEqual(self.db.state(scene="night_river",actor="observer",
                          fact="door_seal",at_tick=2)["state"],
                         "CONFLICT_UNRESOLVED")

    def test_no_backdated_rewrites_or_same_id_forgery(self):
        event=original_event("evidence-01",1,"UNKNOWN")
        r=self.db.append(event)
        self.assertTrue(self.db.append(event)["idempotent_replay"])
        self.assertEqual(len(r["event_sha256"]),64)
        with self.assertRaisesRegex(FactLedgerError,"IMMUTABLE"):
            self.db.append({**event,"state":"KNOWN"})
        self.db.append(original_event("later",5,"KNOWN"))
        with self.assertRaisesRegex(FactLedgerError,"BACKDATED"):
            self.db.append(original_event("insert-into-past",3,"FALSE"))

    def test_links_require_real_matching_timeline_and_do_not_claim_causality(self):
        self.db.append(original_event("obs",1,"UNKNOWN",role="OBSERVE"))
        self.db.append(original_event("chose",2,"KNOWN",role="CHOOSE"))
        success=self.db.link("obs","chose","POTENTIAL_CAUSE")
        self.assertFalse(success["causal_semantics_verified"])
        with self.assertRaisesRegex(FactLedgerError,"TIME_ORDER"):
            self.db.link("chose","obs","POTENTIAL_CAUSE")
        with self.assertRaisesRegex(FactLedgerError,"REFERENCES_MISSING"):
            self.db.link("obs","never-existed","BEFORE")
        self.db.append(original_event("elsewhere",3,"KNOWN",scene="different"))
        with self.assertRaisesRegex(FactLedgerError,"CROSS_SCENE"):
            self.db.link("obs","elsewhere","BEFORE")

    def test_versioned_candidate_with_counterexamples_is_immutable_and_never_promoted(self):
        for e in [original_event("obs",1,"UNKNOWN"),
                  original_event("choice",2,"KNOWN"),
                  original_event("neg",3,"FALSE")]:
            self.db.append(e)
        item={"fact_id":"door_seal","scene_id":"night_river",
              "condition_state":"UNKNOWN","event_refs":["obs","choice"],
              "counterexample_refs":["neg"],"status":"PROPOSED"}
        first=self.db.add_candidate(candidate_id="pattern-case",version=1,
                                    prior_sha=None,record=item)
        self.assertFalse(first["eligible_to_change_writing"])
        self.assertTrue(self.db.add_candidate(
            candidate_id="pattern-case",version=1,
            prior_sha=None,record=item)["idempotent_replay"])
        with self.assertRaisesRegex(FactLedgerError,"REVISION_CHAIN"):
            self.db.add_candidate(candidate_id="pattern-case",version=3,
                                  prior_sha=first["candidate_sha256"],record=item)
        retired={**item,"status":"RETIRED"}
        out=self.db.add_candidate(
            candidate_id="pattern-case",version=2,
            prior_sha=first["candidate_sha256"],record=retired)
        self.assertEqual(self.db.latest_candidate("pattern-case")["status"],"RETIRED")
        with self.assertRaisesRegex(FactLedgerError,"RETIRED_IS_TERMINAL"):
            self.db.add_candidate(candidate_id="pattern-case",version=3,
                                  prior_sha=out["candidate_sha256"],
                                  record={**item,"status":"PROPOSED"})
        self.assertFalse(out["eligible_to_change_writing"])
        with self.assertRaisesRegex(FactLedgerError,"REVISION_IMMUTABLE"):
            self.db.add_candidate(candidate_id="pattern-case",version=2,
                                  prior_sha=first["candidate_sha256"],record=item)
        self.db.close()
        self.db=FactJournal(self.root/"ledger.sqlite3")
        self.assertEqual(self.db.latest_candidate("pattern-case")["version"],2)

    def test_existing_sqlite_fact_record_tampering_is_not_trusted(self):
        self.db.append(original_event("tamper-me",1,"UNKNOWN"))
        self.db.close()
        with sqlite3.connect(self.root/"ledger.sqlite3") as raw:
            raw.execute("UPDATE fact_events SET state='KNOWN' WHERE event_id='tamper-me'")
        self.db=FactJournal(self.root/"ledger.sqlite3")
        with self.assertRaisesRegex(FactLedgerError,"STORED_EVENT_TAMPERED"):
            self.db.state(scene="night_river",actor="observer",fact="door_seal")

    def test_cli_real_sqlite_records_and_reads_but_no_r2(self):
        file=self.root/"fact.json"
        file.write_text(json.dumps(original_event("first-note",1,"UNKNOWN")),
                        encoding="utf-8")
        with redirect_stdout(StringIO()) as o:
            main(["fact-record","--journal",str(self.root/"cli.sqlite3"),
                  "--file",str(file)])
        receipt=json.loads(o.getvalue())
        self.assertFalse(receipt["semantic_truth_proven"])
        with redirect_stdout(StringIO()) as o:
            main(["fact-state","--journal",str(self.root/"cli.sqlite3"),
                  "--scene","night_river","--actor","observer",
                  "--fact","door_seal"])
        data=json.loads(o.getvalue())
        self.assertEqual(data["state"],"UNKNOWN")
        self.assertFalse(data["author_intent_verified"])


if __name__=="__main__":
    unittest.main()
