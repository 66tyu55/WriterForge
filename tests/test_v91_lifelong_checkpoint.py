"""V91 real SQLite cold snapshots, fault injection, and behavior replay.

Synthetic novels only. Two existing DBs (WriterForgeDB and FactJournal)
are backed up with SQLite's WAL-safe API; their original files are not
renamed, reset or overwritten. No model or R2 access.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import hmac
import json
import shutil
import sqlite3
import unittest
from unittest.mock import patch

from writerforge.db import WriterForgeDB
from writerforge.fact_journal import FactJournal
from writerforge.runtime import RuntimeEngine
from writerforge.experience_decision import (
    ExperienceDecisionBridge,canonical as decision_canonical,
)
from writerforge.v91_lifelong_checkpoint import (
    create_checkpoint,verify_checkpoint,restore_workspace,
    V91MemoryCheckpointError,canonical,
)

APPROVAL_KEY=b"synthetic-lifelong-upgrade-test-key-32bytes"
R2_ANCHORS={
    "batch":"a"*64,
    "journal":"b"*64,
    "experience":"c"*64,
}


def h(value):
    return sha256(value.encode("utf8")).hexdigest()


def sign(packet):
    return hmac.new(APPROVAL_KEY,
        decision_canonical(packet).encode("utf8"),"sha256").hexdigest()


class V91ColdCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        folder=Path(self.temp.name)
        self.writerpath=folder/"working.sqlite3"
        self.factpath=folder/"facts.sqlite3"
        self.root=folder/"private-memory"
        self.writer=WriterForgeDB(self.writerpath)
        self.facts=FactJournal(self.factpath)
        self.runtime=RuntimeEngine()
        self.runtime.enter_learn()
        db=self.writer.conn
        self.snapshot=db.execute(
            "INSERT INTO snapshots(status,layout,note) "
            "VALUES('published','full','V91中文恢复测试')").lastrowid
        db.execute(
            "INSERT INTO studied_works(work_id,title,source_uri,"
            "source_sha256,chapter_count) VALUES(?,?,?,?,?)",
            ("novelA","测试章节","test://v91",h("synthetic-work"),3))
        db.execute(
            "INSERT INTO studied_chapters(work_id,chapter,chapter_sha256,"
            "heading,source_spans,retrieval_entries,snapshot_id)"
            " VALUES(?,?,?,?,?,?,?)",
            ("novelA",3,h("chapter03"),"第3章",1,1,self.snapshot))
        self.quote="守桥人突然收起木牌，少年停止了冒险，不能因此断言真正因果。"
        self.locator={
            "work_id":"novelA","chapter":3,
            "paragraph":1,"sentence":1,
            "source_sha256":h(self.quote),
        }
        db.execute(
            "INSERT INTO source_spans(work_id,chapter,paragraph,sentence,"
            "excerpt,source_sha256,tracks_json,craft_json)"
            " VALUES(?,?,?,?,?,?,?,?)",
            ("novelA",3,1,1,self.quote,h(self.quote),"{}","{}"))
        db.commit()

        self.bridge=ExperienceDecisionBridge(
            self.writer,self.runtime,reviewer_key=APPROVAL_KEY)
        self.bridge.stage_candidate(
            project_id="project01",experience_id="lesson01",
            snapshot_id=self.snapshot,source_ref=self.locator,
            required_tags=["limited_knowledge"],
            forbidden_tags=["omniscient"],
            operation_code="CHECK_KNOWLEDGE")
        approval=self.bridge.approval_payload(
            project_id="project01",experience_id="lesson01",
            reviewer_id="auditor01",review_id="approval01")
        self.bridge.approve_candidate(
            project_id="project01",experience_id="lesson01",
            reviewer_id="auditor01",review_id="approval01",
            signature=sign(approval))

        self.facts.register_scene(
            story_id="novelA",scene_id="chapter01",chapter_index=1)
        self.facts.register_scene(
            story_id="novelA",scene_id="chapter03",chapter_index=3)
        for scene in ("chapter01","chapter03"):
            self.facts.bind_subject(
                scene_id=scene,scope="ACTOR",
                subject_id="hero",canonical_id="heroA")
        self.facts.append({
            "event_id":"hero-saw-bridge","scene_id":"chapter01",
            "actor_id":"hero","fact_id":"bridge_light",
            "tick":2,"state":"KNOWN","role":"OBSERVE",
            "evidence_sha256":h("fictional-evidence")})
        self.facts.append_temporal_claim({
            "claim_id":"claim_bridge_known","scene_id":"chapter01",
            "subject_scope":"ACTOR","subject_id":"hero",
            "fact_id":"bridge_light","story_from":2,
            "story_until":None,"knowledge_state":"KNOWN",
            "evidence_event_id":"hero-saw-bridge",
            "supersedes_id":None,
        })
        self.ledger_head=self.facts.ledger_head()

        self.runtime.exit()
        self.runtime.enter_write(self.snapshot)
        before=self.decide("before-revoke")
        self.assertEqual(before["decisions"][0]["decision"],"SELECT")
        self.frozen_before=before["decision_sha256"]
        self.runtime.exit()
        self.runtime.enter_learn()
        revocation=self.bridge.revocation_payload(
            project_id="project01",experience_id="lesson01",
            reviewer_id="auditor01",review_id="revocation01",
            reason_code="SOURCE_REVIEW_DISPUTED")
        self.bridge.revoke_candidate(
            project_id="project01",experience_id="lesson01",
            reviewer_id="auditor01",review_id="revocation01",
            reason_code="SOURCE_REVIEW_DISPUTED",
            signature=sign(revocation))
        self.runtime.exit()
        self.runtime.enter_write(self.snapshot)
        result=self.decide("before-checkpoint")
        self.assertEqual(result["decisions"][0]["decision"],"SKIP")
        self.assertEqual(result["decisions"][0]["reason_code"],
                         "EXPERIENCE_REVOKED")
        self.runtime.exit()

    def tearDown(self):
        self.writer.close()
        self.facts.close()
        self.temp.cleanup()

    def decide(self, attempt,bridge=None):
        x=bridge if bridge is not None else self.bridge
        return x.decide(
            project_id="project01",scene_id="scene01",attempt_id=attempt,
            goal="检查人物已知信息，不复述原著",
            scene_signals={"limited_knowledge":True,"omniscient":False})

    def checkpoint(self,id="checkpoint01",**kwargs):
        return create_checkpoint(
            root=self.root,checkpoint_id=id,
            writer=self.writer,facts=self.facts,
            runtime=self.runtime,r2_v82_anchors=R2_ANCHORS,
            **kwargs)

    def test_cold_restore_two_real_sqlite_dbs_preserves_negatives(self):
        first=self.checkpoint()
        self.assertEqual(first["status"],
                         "WF91_COLD_CHECKPOINT_CONTENT_VERIFIED")
        self.assertEqual(first["files_verified"],2)
        self.assertTrue(first["r2_anchors_pinned_not_fetched"])
        self.assertTrue(first["cross_db_atomicity_not_proven"])
        copied=restore_workspace(
            root=self.root,destination=Path(self.temp.name)/"recovered")
        self.assertTrue(copied["source_bundle_unmodified"])
        folder=Path(self.temp.name)/"recovered"
        new_writer=WriterForgeDB(folder/"writerforge.sqlite3")
        new_facts=FactJournal(folder/"fact-journal.sqlite3")
        try:
            fresh_rt=RuntimeEngine()
            fresh_rt.enter_write(self.snapshot)
            fresh_bridge=ExperienceDecisionBridge(
                new_writer,fresh_rt,reviewer_key=APPROVAL_KEY)
            after=self.decide("after-cold-restart",fresh_bridge)
            self.assertEqual(after["decisions"][0]["decision"],"SKIP")
            self.assertEqual(after["decisions"][0]["reason_code"],
                             "EXPERIENCE_REVOKED")
            self.assertEqual(after["prompt_guidance"],"")
            prior=fresh_bridge.read_decision(
                project_id="project01",attempt_id="before-revoke")
            self.assertEqual(prior["decision_sha256"],self.frozen_before)
            self.assertEqual(prior["decisions"][0]["decision"],"SELECT")
            with self.assertRaisesRegex(ValueError,"REVOKED"):
                fresh_bridge.validate_live_decision(
                    project_id="project01",attempt_id="before-revoke")
            actor=new_facts.temporal_view(
                scene="chapter03",story_id="novelA",
                scope="ACTOR",subject="hero",fact="bridge_light",
                story_tick=3,as_of_ledger_seq=self.ledger_head)
            self.assertEqual(actor["state"],"KNOWN")
            self.assertEqual(new_facts.ledger_head(),self.ledger_head)
        finally:
            new_writer.close()
            new_facts.close()
        self.assertEqual(first["manifest_sha256"],
                         verify_checkpoint(self.root)["manifest_sha256"])

    def test_previous_pointer_survives_interrupted_publish(self):
        old=self.checkpoint()
        with self.assertRaisesRegex(V91MemoryCheckpointError,
                                    "TEST_INJECTED_BEFORE_MANIFEST"):
            self.checkpoint("checkpoint02",failpoint="BEFORE_MANIFEST")
        self.assertEqual(verify_checkpoint(self.root)["checkpoint_id"],
                         "checkpoint01")
        with self.assertRaisesRegex(V91MemoryCheckpointError,
                                    "TEST_INJECTED_BEFORE_POINTER"):
            self.checkpoint("checkpoint03",
                failpoint="AFTER_DIRECTORY_BEFORE_CURRENT")
        self.assertEqual(verify_checkpoint(self.root)["manifest_sha256"],
                         old["manifest_sha256"])
        newer=self.checkpoint("checkpoint04")
        self.assertNotEqual(newer["manifest_sha256"],
                            old["manifest_sha256"])
        manifest=json.loads((self.root/"checkpoints"/"checkpoint04"/
                             "manifest.json").read_text("utf8"))
        self.assertEqual(manifest["previous_manifest_sha256"],
                         old["manifest_sha256"])

    def test_bad_file_sha_and_missing_bundle_fail_closed(self):
        self.checkpoint()
        folder=self.root/"checkpoints"/"checkpoint01"
        p=folder/"writerforge.sqlite3"
        data=p.read_bytes()
        p.write_bytes(data[:-1]+bytes([data[-1]^0xFF]))
        with self.assertRaisesRegex(V91MemoryCheckpointError,
                                    "SQLITE_BYTE_SHA_CHANGED"):
            verify_checkpoint(self.root)
        with self.assertRaises(V91MemoryCheckpointError):
            restore_workspace(root=self.root,
                              destination=Path(self.temp.name)/"bad")

    def test_unknown_manifest_version_and_invalid_utf8_refused(self):
        self.checkpoint()
        path=self.root/"checkpoints"/"checkpoint01"/"manifest.json"
        data=json.loads(path.read_text("utf8"))
        data["schema_version"]=99
        path.write_bytes(canonical(data))
        with self.assertRaisesRegex(V91MemoryCheckpointError,
                                    "UNSUPPORTED_CHECKPOINT_VERSION"):
            verify_checkpoint(self.root)
        path.write_bytes(b"\xff\xfeinvalid")
        with self.assertRaisesRegex(V91MemoryCheckpointError,
                                    "RESTORE_JSON_INVALID_OR_GARBLED"):
            verify_checkpoint(self.root)

    def test_changed_pointer_and_replay_attempt_are_rejected(self):
        first=self.checkpoint()
        with self.assertRaisesRegex(V91MemoryCheckpointError,
                                    "IMMUTABLE_CHECKPOINT_ALREADY_EXISTS"):
            self.checkpoint()
        current=self.root/"CURRENT"
        current.write_bytes(b'{"format":"invalid"}')
        with self.assertRaisesRegex(V91MemoryCheckpointError,
                                    "CURRENT_POINTER_INVALID"):
            verify_checkpoint(self.root)

    def test_checkpoint_rejects_active_writers_and_bad_r2_pointers(self):
        self.runtime.enter_learn()
        with self.assertRaisesRegex(RuntimeError,"requires Mode.IDLE"):
            self.checkpoint()
        self.runtime.exit()
        with self.assertRaisesRegex(V91MemoryCheckpointError,
                                    "EXTERNAL_R2_ANCHORS_INVALID"):
            create_checkpoint(
                root=self.root,checkpoint_id="checkpoint01",
                writer=self.writer,facts=self.facts,runtime=self.runtime,
                r2_v82_anchors={"batch":"0"*63})
        self.writer.conn.execute("BEGIN")
        with self.assertRaisesRegex(V91MemoryCheckpointError,
                                    "WRITERS_NOT_QUIESCENT"):
            self.checkpoint()
        self.writer.conn.rollback()

    def test_replacement_character_is_not_silent_in_durable_memory(self):
        self.writer.conn.execute(
            "INSERT INTO experience_legacy_refs("
            "project_id,legacy_id,ref_sha,ref_json) VALUES(?,?,?,?)",
            ("project01","badlegacy","f"*64,"已乱码\ufffd不可继续"))
        self.writer.conn.commit()
        with self.assertRaisesRegex(V91MemoryCheckpointError,
                                    "SQLITE_REPLACEMENT_CHARACTER"):
            self.checkpoint()

    def test_cold_restore_never_overwrites_existing_workspace(self):
        self.checkpoint()
        dest=Path(self.temp.name)/"destination"
        dest.mkdir()
        (dest/"keep.txt").write_text("旧版必须保留",encoding="utf8")
        with self.assertRaisesRegex(V91MemoryCheckpointError,
                                    "DESTINATION_ALREADY_EXISTS"):
            restore_workspace(root=self.root,destination=dest)
        self.assertEqual((dest/"keep.txt").read_text("utf8"),
                         "旧版必须保留")

if __name__=="__main__":
    unittest.main()
