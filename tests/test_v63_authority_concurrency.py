"""V63 fail-first authority, atomic registry, two-writer SQLite adversarial tests.

No private manuscripts, R2, online model, new literary evaluation or promotion
of real WriterForge capability. Synthetic-only keys and source records.
"""
from __future__ import annotations
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import hmac
import json
import sqlite3
import unittest

from writerforge.db import WriterForgeDB
from writerforge.runtime import RuntimeEngine
from writerforge.evolution import (
    CapabilityContract, EvolutionEngine, PromotionEvidence,
    SkillRegistry, SkillStatus, UpgradeCandidate
)
from writerforge.experience_decision import ExperienceDecisionBridge, canonical
from writerforge.verified_flow import (
    VerifiedWritingFlow, WritingExecutionError,
    save_candidate, accept_candidate
)

REVIEW_KEY=b"synthetic-V63-revision-safety-key"
PROMOTION_KEY=b"synthetic-V63-promotion-key"


def sig(payload,key=REVIEW_KEY):
    return hmac.new(key,canonical(payload).encode("utf-8"),
                    "sha256").hexdigest()


def make_candidate(skill, level, evidence_id="review01"):
    return UpgradeCandidate(
        skill=skill,new_level=level,
        capability_statement="synthetic externally controlled upgrade",
        evidence_id=evidence_id,
        evidence=PromotionEvidence(
            capability_statement="synthetic nonliterary test",
            heldout_success=.91,transfer_success=.81,
            regression_success=.99,judge_stability=.97,
            repeated_failure_reduction=.45,runtime_regression=.01,
            human_anchor_count=1),
        requires_human_anchor=True)


def signed(engine,cand,review_id="external01"):
    payload=engine.promotion_attestation_payload(
        cand,reviewer_id="independent01",review_id=review_id)
    return {"reviewer_id":"independent01","review_id":review_id,
            "signature":sig(payload,PROMOTION_KEY)}


class SkillAuthorityTests(unittest.TestCase):
    def test_direct_public_promote_rejected_without_signed_review(self):
        registry=SkillRegistry()
        registry.register(CapabilityContract("craft01",1,"baseline"))
        with self.assertRaisesRegex(PermissionError,"PROMOTION"):
            registry.promote("craft01",new_level=2,
                             statement="unverified",evidence_id="self-scored")
        self.assertEqual(registry.get("craft01").level,1)

    def test_same_name_register_must_not_replace_past_capability(self):
        registry=SkillRegistry()
        registry.register(CapabilityContract("craft02",1,"original"))
        with self.assertRaisesRegex((ValueError,PermissionError),"IMMUTABLE|EXISTS"):
            registry.register(CapabilityContract("craft02",1,"unreviewed replacement"))
        self.assertEqual(registry.get("craft02").level,1)

    def test_get_and_all_cannot_mutate_live_registry_or_be_persisted(self):
        registry=SkillRegistry()
        registry.register(CapabilityContract("craft03",1,"original"))
        for observable in (registry.get("craft03"),registry.all()[0]):
            try:
                observable.level=9
            except (AttributeError,TypeError):
                pass
        self.assertEqual(registry.get("craft03").level,1)
        self.assertEqual(registry.all()[0].level,1)

    def test_revalidate_cannot_reactivate_shadow_from_caller_boolean(self):
        registry=SkillRegistry()
        registry.register(CapabilityContract(
            "craft04",1,"unverified",status=SkillStatus.SHADOW))
        with self.assertRaisesRegex(PermissionError,"REVALIDATION"):
            registry.revalidate("craft04",passed=True)
        self.assertEqual(registry.get("craft04").status,SkillStatus.SHADOW)

    def test_verified_manual_promotion_is_atomic_on_event_insert_failure(self):
        with TemporaryDirectory() as tmp:
            db=WriterForgeDB(Path(tmp)/"skills.sqlite3")
            try:
                registry=SkillRegistry(db=db,scope="synthetic")
                registry.register(CapabilityContract(
                    "base01",1,"baseline"))
                registry.register(CapabilityContract(
                    "dependent01",1,"depends",{"base01":1}))
                engine=EvolutionEngine(
                    registry=registry,promotion_verifier_key=PROMOTION_KEY)
                candidate=make_candidate("base01",2)
                with db.conn:
                    db.conn.execute(
                        "CREATE TRIGGER fail_signed_promotion "
                        "BEFORE INSERT ON skill_upgrade_events "
                        "BEGIN SELECT RAISE(ABORT,'synthetic rollback'); END")
                with self.assertRaises(sqlite3.IntegrityError):
                    engine.apply_upgrade(candidate,policy="manual",
                        approved=True,attestation=signed(engine,candidate))
                self.assertEqual(registry.get("base01").level,1)
                self.assertEqual(registry.get("dependent01").status,
                                 SkillStatus.ACTIVE)
                db.conn.execute("DROP TRIGGER fail_signed_promotion")
                db.conn.commit()
                reload=SkillRegistry(db=db,scope="synthetic")
                self.assertEqual(reload.get("base01").level,1)
                self.assertEqual(reload.get("dependent01").status,
                                 SkillStatus.ACTIVE)
                self.assertEqual(db.conn.execute(
                    "SELECT COUNT(*) FROM skill_upgrade_events").fetchone()[0],0)
            finally:
                db.close()

    def test_two_connections_reject_stale_skill_version(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"version.sqlite3"
            a=WriterForgeDB(path); b=WriterForgeDB(path)
            try:
                ra=SkillRegistry(db=a,scope="synthetic")
                ra.register(CapabilityContract("base02",1,"original"))
                rb=SkillRegistry(db=b,scope="synthetic")
                ea=EvolutionEngine(registry=ra,promotion_verifier_key=PROMOTION_KEY)
                eb=EvolutionEngine(registry=rb,promotion_verifier_key=PROMOTION_KEY)
                ca=make_candidate("base02",2,"proof01")
                cb=make_candidate("base02",2,"proof02")
                ea.apply_upgrade(ca,policy="manual",approved=True,
                                 attestation=signed(ea,ca,"independent01"))
                with self.assertRaisesRegex((ValueError,RuntimeError),
                                             "STALE|CONCURRENT|REVISION"):
                    eb.apply_upgrade(cb,policy="manual",approved=True,
                                     attestation=signed(eb,cb,"independent02"))
                refreshed=SkillRegistry(db=b,scope="synthetic")
                self.assertEqual(refreshed.get("base02").level,2)
                self.assertEqual(a.conn.execute(
                    "SELECT COUNT(*) FROM skill_upgrade_events").fetchone()[0],1)
            finally:
                a.close(); b.close()


class ExperienceRaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.path=Path(self.temp.name)/"experience.sqlite3"
        self.db=WriterForgeDB(self.path)
        self.rt=RuntimeEngine()
        self.rt.enter_learn()
        source="synthetic metadata only"
        unit=sha256(source.encode()).hexdigest()
        self.sid=self.db.conn.execute(
            "INSERT INTO snapshots(status,layout,note) "
            "VALUES('published','full','V63')").lastrowid
        self.db.conn.execute(
            "INSERT INTO studied_works(work_id,title,source_uri,"
            "source_sha256,chapter_count) VALUES(?,?,?,?,?)",
            ("synthetic63","synthetic","test://synthetic",
             sha256(b"only-a-synthetic-work").hexdigest(),1))
        self.db.conn.execute(
            "INSERT INTO studied_chapters(work_id,chapter,chapter_sha256,"
            "heading,source_spans,retrieval_entries,snapshot_id)"
            " VALUES(?,?,?,?,?,?,?)",
            ("synthetic63",1,unit,"fixture",1,1,self.sid))
        self.db.conn.execute(
            "INSERT INTO source_spans(work_id,chapter,paragraph,sentence,"
            "excerpt,source_sha256,tracks_json,craft_json)"
            " VALUES(?,?,?,?,?,?,?,?)",
            ("synthetic63",1,1,1,source,unit,"{}","{}"))
        self.db.conn.commit()
        self.bridge=ExperienceDecisionBridge(
            self.db,self.rt,reviewer_key=REVIEW_KEY)
        self.bridge.stage_candidate(
            project_id="project63",experience_id="lesson63",
            snapshot_id=self.sid,
            source_ref={"work_id":"synthetic63","chapter":1,
                        "paragraph":1,"sentence":1,"source_sha256":unit},
            required_tags=["bounded_knowledge"],
            forbidden_tags=["omniscient"],operation_code="CHECK_KNOWLEDGE")
        approval=self.bridge.approval_payload(
            project_id="project63",experience_id="lesson63",
            reviewer_id="external63",review_id="review63")
        self.bridge.approve_candidate(
            project_id="project63",experience_id="lesson63",
            reviewer_id="external63",review_id="review63",
            signature=sig(approval))
        self.rt.exit()
        self.rt.enter_write(self.sid)
        self.other=WriterForgeDB(self.path)
        self.other.conn.execute("PRAGMA busy_timeout=50")
        self.learn_rt=RuntimeEngine();self.learn_rt.enter_learn()
        self.write_rt=RuntimeEngine();self.write_rt.enter_write(self.sid)
        self.review_bridge=ExperienceDecisionBridge(
            self.other,self.learn_rt,reviewer_key=REVIEW_KEY)
        self.write_bridge=ExperienceDecisionBridge(
            self.other,self.write_rt,reviewer_key=REVIEW_KEY)

    def tearDown(self):
        self.other.close()
        self.db.close()
        self.temp.cleanup()

    def decide(self,ident):
        return self.bridge.decide(
            project_id="project63",scene_id="scene63",
            attempt_id=ident,goal="check bounded knowledge",
            scene_signals={"bounded_knowledge":True,"omniscient":False})

    def revoke(self):
        p=self.review_bridge.revocation_payload(
            project_id="project63",experience_id="lesson63",
            reviewer_id="external63",review_id="revoke63",
            reason_code="AUTHORITY_WITHDRAWN")
        return self.review_bridge.revoke_candidate(
            project_id="project63",experience_id="lesson63",
            reviewer_id="external63",review_id="revoke63",
            reason_code="AUTHORITY_WITHDRAWN",
            signature=sig(p))

    def test_revocation_cannot_commit_between_policy_read_and_decision(self):
        original=self.bridge._revocation_state
        signal={"blocked":False,"committed":False}
        def intervene(*args):
            old=original(*args)
            try:
                self.revoke()
                signal["committed"]=True
            except sqlite3.OperationalError as err:
                signal["blocked"]="locked" in str(err).lower()
            return old
        with patch.object(self.bridge,"_revocation_state",side_effect=intervene):
            first=self.decide("first63")
        self.assertTrue(signal["blocked"],
                        "Revocation slipped between SELECT checks and commit")
        self.assertFalse(signal["committed"])
        self.assertEqual(first["decisions"][0]["decision"],"SELECT")
        self.revoke()
        self.assertEqual(self.decide("after63")["decisions"][0]["decision"],
                         "SKIP")
        with self.assertRaisesRegex(ValueError,"REVOKED"):
            self.bridge.validate_live_decision(
                project_id="project63",attempt_id="first63")

    def test_adverse_postwrite_cannot_commit_during_fresh_decision(self):
        self.decide("prior63")
        original=self.bridge._feedback_state
        outcome={"blocked":False,"committed":False}
        def intervene(*args):
            old=original(*args)
            try:
                self.write_bridge.report_postwrite(
                    project_id="project63",attempt_id="prior63",
                    experience_id="lesson63",outcome="NOT_APPLIED",
                    draft="合成文本仅用于验证写前的证据状态和竞态。")
                outcome["committed"]=True
            except sqlite3.OperationalError as exc:
                outcome["blocked"]="locked" in str(exc).lower()
            return old
        with patch.object(self.bridge,"_feedback_state",side_effect=intervene):
            current=self.decide("during63")
        self.assertTrue(outcome["blocked"],
                        "Adverse feedback committed after read before SELECT")
        self.assertFalse(outcome["committed"])
        self.assertEqual(current["decisions"][0]["decision"],"SELECT")
        self.write_bridge.report_postwrite(
            project_id="project63",attempt_id="prior63",
            experience_id="lesson63",outcome="NOT_APPLIED",
            draft="合成文本仅用于验证写前的证据状态和竞态。")
        self.assertEqual(self.decide("after63")["decisions"][0]["decision"],
                         "SKIP")

    def test_accept_candidate_rechecks_after_concurrent_revoke(self):
        flow=VerifiedWritingFlow(
            self.db,self.rt,"project63",experience_review_key=REVIEW_KEY)
        fake=[{"entry_id":1,"work_id":"synthetic63","location":[1,1,1],
               "function":"narration","effect":"unverified"}]
        with patch.object(flow.xuehai,"query",return_value=fake):
            packet=flow.prepare(
                "scene63","check bounded knowledge",
                experience_attempt_id="first63",
                scene_signals={"bounded_knowledge":True,"omniscient":False})
        saved=save_candidate(
            packet,"合成原创片段：人物因缺少资料而需要谨慎行动。",
            "synthetic-local-model",Path(self.temp.name)/"candidates")
        original=ExperienceDecisionBridge.validate_live_decision
        triggered={"revoke_count":0}
        def race(instance,*,project_id,attempt_id):
            approved=original(
                instance,project_id=project_id,attempt_id=attempt_id)
            if triggered["revoke_count"]==0:
                triggered["revoke_count"]+=1
                self.revoke()  # commit AFTER first validation
            return approved
        import os
        with patch.dict(os.environ,{
            "WRITERFORGE_EXPERIENCE_REVIEW_VERIFY_KEY_HEX":
                REVIEW_KEY.hex()}):
            with patch.object(
                    ExperienceDecisionBridge,"validate_live_decision",
                    race):
                with self.assertRaisesRegex(
                        WritingExecutionError,"EXPERIENCE"):
                    accept_candidate(
                        self.db,self.rt,project_id="project63",
                        manifest_path=saved["manifest"],commit_id="commit63",
                        explicitly_approved=True)
        self.assertEqual(triggered["revoke_count"],1)
        self.assertIsNone(self.db.conn.execute(
            "SELECT 1 FROM story_commit_receipts "
            "WHERE project_id='project63'").fetchone())


if __name__=="__main__":
    unittest.main()
