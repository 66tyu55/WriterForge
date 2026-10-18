"""V64 fail-first trust-root tests. No model, R2, prose learning.

Security boundary: library API cannot certify arbitrary host DB writes, but
assistant_generated writing must not masquerade as a trusted human draft.
"""
from __future__ import annotations
import hmac
import json
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from hashlib import sha256

from writerforge.evolution import SkillRegistry, CapabilityContract, SkillStatus
from writerforge.db import WriterForgeDB
from writerforge.runtime import RuntimeEngine
from writerforge.writing_flow import WritingFlow
from writerforge.story_commit import StoryCommitCoordinator, StoryCommitPlan, StoryEffect, EffectType
from writerforge.verified_flow import VerifiedWritingFlow, save_candidate, accept_candidate
from writerforge.experience_decision import ExperienceDecisionBridge,canonical

ROOT_KEY=b"v64-synthetic-bootstrap-reviewer-key"
EXPERIENCE_KEY=b"v64-synthetic-experience-signature"


def mac(key,payload):
    return hmac.new(key,canonical(payload).encode(),"sha256").hexdigest()


class V64BootstrapTests(unittest.TestCase):
    def test_new_level_10_active_requires_credible_bootstrap(self):
        reg=SkillRegistry()
        with self.assertRaisesRegex(PermissionError,"BOOTSTRAP"):
            reg.register(CapabilityContract("fresh10",10,"no independent record",
                                            status=SkillStatus.ACTIVE))
        self.assertEqual(len(reg.all()),0)

    def test_new_level_one_is_baseline_not_literary_promotion(self):
        reg=SkillRegistry()
        reg.register(CapabilityContract("new01",1,"synthetic baseline"))
        self.assertEqual(reg.get("new01").level,1)

    def test_unverified_legacy_high_level_is_shadow_only(self):
        reg=SkillRegistry()
        registered=reg.import_legacy_capability(
            CapabilityContract("old10",10,"historical claim",
                               status=SkillStatus.ACTIVE),
            provenance="unverified_old_release")
        self.assertEqual(reg.get("old10").level,10)
        self.assertEqual(reg.get("old10").status,SkillStatus.SHADOW)
        self.assertFalse(registered["literary_mastery_verified"])

    def test_signed_baseline_can_register_but_never_proves_literary_quality(self):
        reg=SkillRegistry(bootstrap_verifier_key=ROOT_KEY)
        cap=CapabilityContract("trusted10",10,"synthetic preexisting release")
        payload=reg.bootstrap_payload(cap,reviewer_id="external01",
                                      review_id="bootstrap01")
        accepted=reg.register_verified(
            cap,reviewer_id="external01",review_id="bootstrap01",
            signature=mac(ROOT_KEY,payload))
        self.assertEqual(reg.get("trusted10").level,10)
        self.assertFalse(accepted["literary_mastery_verified"])
        with self.assertRaisesRegex(PermissionError,"BOOTSTRAP"):
            reg.register_verified(CapabilityContract(
                "bad09",9,"unverified"),reviewer_id="external01",
                review_id="bootstrap02",signature="0"*64)

    def test_database_restart_retains_shadow_unreviewed_legacy(self):
        with TemporaryDirectory() as t:
            db=WriterForgeDB(Path(t)/"caps.db")
            try:
                reg=SkillRegistry(db=db,scope="synthetic")
                reg.import_legacy_capability(
                    CapabilityContract("old09",9,"import old",
                                       status=SkillStatus.ACTIVE),
                    provenance="unverified_old_release")
                restarted=SkillRegistry(db=db,scope="synthetic")
                self.assertEqual(restarted.get("old09").level,9)
                self.assertEqual(restarted.get("old09").status,SkillStatus.SHADOW)
            finally:
                db.close()


class V64OriginTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.path=Path(self.temp.name)/"wf.db"
        self.db=WriterForgeDB(self.path)
        self.mode=RuntimeEngine()
        self.mode.enter_learn()
        source="synthetic only"
        evidence=sha256(source.encode()).hexdigest()
        self.sid=self.db.conn.execute(
            "INSERT INTO snapshots(status,layout,note) "
            "VALUES('published','full','synthetic')").lastrowid
        self.db.conn.execute(
            "INSERT INTO studied_works(work_id,title,source_uri,source_sha256,"
            "chapter_count) VALUES(?,?,?,?,?)",
            ("source01","Synthetic","synthetic://fixture",
             sha256(b"source-fixture").hexdigest(),1))
        self.db.conn.execute(
            "INSERT INTO studied_chapters(work_id,chapter,chapter_sha256,"
            "heading,source_spans,retrieval_entries,snapshot_id)"
            " VALUES(?,?,?,?,?,?,?)",
            ("source01",1,evidence,"Synthetic",1,1,self.sid))
        self.db.conn.execute(
            "INSERT INTO source_spans(work_id,chapter,paragraph,sentence,"
            "excerpt,source_sha256,tracks_json,craft_json)"
            " VALUES(?,?,?,?,?,?,?,?)",
            ("source01",1,1,1,source,evidence,"{}","{}"))
        self.db.conn.commit()
        self.bridge=ExperienceDecisionBridge(
            self.db,self.mode,reviewer_key=EXPERIENCE_KEY)
        self.bridge.stage_candidate(
            project_id="project01",experience_id="lesson01",
            snapshot_id=self.sid,
            source_ref={"work_id":"source01","chapter":1,
                        "paragraph":1,"sentence":1,
                        "source_sha256":evidence},
            required_tags=["knowledge_limited"],
            forbidden_tags=["omniscient"],operation_code="CHECK_KNOWLEDGE")
        proof=self.bridge.approval_payload(
            project_id="project01",experience_id="lesson01",
            reviewer_id="external01",review_id="review01")
        self.bridge.approve_candidate(
            project_id="project01",experience_id="lesson01",
            reviewer_id="external01",review_id="review01",
            signature=mac(EXPERIENCE_KEY,proof))
        self.mode.exit()
        self.mode.enter_write(self.sid)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_low_level_flow_denies_model_origin_without_checked_receipt(self):
        flow=WritingFlow(self.db,self.mode,"project01")
        with self.assertRaisesRegex(PermissionError,"ORIGIN|ASSISTANT"):
            flow.accept_draft("c01","s01","synthetic generated body",
                              origin="assistant_generated")
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM story_commit_receipts").fetchone()[0],0)

    def test_raw_story_coordinator_denies_model_origin_without_checked_receipt(self):
        coordinator=StoryCommitCoordinator(self.db,self.mode)
        plan=StoryCommitPlan("project01","c02",(
            StoryEffect(EffectType.ACCEPT_PROSE,"s02",{
                "body":"synthetic text",
                "origin":"assistant_generated"}),))
        with self.assertRaisesRegex(PermissionError,"ORIGIN|ASSISTANT"):
            coordinator.commit(plan)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM story_commit_receipts").fetchone()[0],0)

    def test_trusted_author_body_remains_supported(self):
        flow=WritingFlow(self.db,self.mode,"project01")
        result=flow.accept_draft("c03","s03","an original human text",
                                 origin="author_written")
        self.assertTrue(result.committed)

    def test_verified_candidate_acceptance_preserves_workflow(self):
        from unittest.mock import patch
        flow=VerifiedWritingFlow(
            self.db,self.mode,"project01",
            experience_review_key=EXPERIENCE_KEY)
        fake=[{"entry_id":1,"work_id":"source01","location":[1,1,1],
               "function":"narration","effect":"unverified"}]
        with patch.object(flow.xuehai,"query",return_value=fake):
            packet=flow.prepare(
                "s04","synthetic investigation",
                experience_attempt_id="attempt04",
                scene_signals={"knowledge_limited":True,"omniscient":False})
        saved=save_candidate(packet,"original synthetic fiction line",
                             "synthetic-model",
                             Path(self.temp.name)/"candidates")
        with patch.dict("os.environ",{
            "WRITERFORGE_EXPERIENCE_REVIEW_VERIFY_KEY_HEX":
                EXPERIENCE_KEY.hex()}):
            out=accept_candidate(
                self.db,self.mode,project_id="project01",
                manifest_path=saved["manifest"],
                commit_id="c04",explicitly_approved=True)
        self.assertTrue(out["accepted"])

if __name__=="__main__":
    unittest.main()
