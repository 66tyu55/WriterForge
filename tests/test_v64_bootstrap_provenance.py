"""V64 fail-first trust-root tests. Synthetic SQLite only; no models/R2.

Trusted bootstrap protects CLAIMED skill level at initial registration, and
a signed accepted-model-provenance permit protects the *final* story COMMIT.
A permit signs host authorization metadata, NOT literary truth or human identity.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from contextlib import redirect_stdout
import hmac
import json
import sqlite3
import unittest

from writerforge.db import WriterForgeDB
from writerforge.runtime import RuntimeEngine
from writerforge.evolution import (
    CapabilityContract, SkillRegistry, SkillStatus
)
from writerforge.story_commit import (
    StoryCommitCoordinator, StoryCommitError, StoryCommitPlan,
    StoryEffect, EffectType
)
from writerforge.writing_flow import WritingFlow
from writerforge.verified_flow import (
    GroundedDraftPacket, save_candidate, accept_candidate,
    WritingExecutionError
)

BOOT_KEY=b"synthetic-v64-bootstrap-issuer-key"
AI_KEY=b"synthetic-v64-ai-commit-signer-key"
SOURCE_SHA=sha256(b"synthetic-independent-review-anchor").hexdigest()


def canonical(data):
    return json.dumps(data,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False)


def sign(data,key):
    return hmac.new(key,canonical(data).encode("utf-8"),
                    "sha256").hexdigest()


class TrustedBootstrapTests(unittest.TestCase):
    def test_unreviewed_new_level_ten_active_cannot_be_registered(self):
        r=SkillRegistry()
        with self.assertRaisesRegex((PermissionError,ValueError),
                                    "BOOTSTRAP"):
            r.register(CapabilityContract(
                "fresh_skill",10,"synthetic unverified literary mastery"))
        self.assertEqual(r.all(),[])

    def test_bootstrap_grade_cannot_be_forged_or_scope_swapped(self):
        r=SkillRegistry(scope="work01",bootstrap_verifier_key=BOOT_KEY)
        contract=CapabilityContract(
            "graded01",6,"synthetic controlled legacy grade")
        payload=r.bootstrap_attestation_payload(
            contract,source_sha256=SOURCE_SHA,
            reviewer_id="reviewer01",review_id="review01")
        with self.assertRaisesRegex((PermissionError,ValueError),
                                    "BOOTSTRAP"):
            r.register(contract,bootstrap_attestation={
                "source_sha256":SOURCE_SHA,"reviewer_id":"reviewer01",
                "review_id":"review01","signature":"0"*64})
        self.assertEqual(r.all(),[])
        signed={"source_sha256":SOURCE_SHA,"reviewer_id":"reviewer01",
                "review_id":"review01","signature":sign(payload,BOOT_KEY)}
        r.register(contract,bootstrap_attestation=signed)
        self.assertEqual(r.get("graded01").level,6)
        other=SkillRegistry(scope="work02",bootstrap_verifier_key=BOOT_KEY)
        with self.assertRaisesRegex((PermissionError,ValueError),"BOOTSTRAP"):
            other.register(contract,bootstrap_attestation=signed)
        self.assertEqual(len(other.all()),0)
        changed=replace(contract,level=7)
        other=SkillRegistry(scope="work01",bootstrap_verifier_key=BOOT_KEY)
        with self.assertRaisesRegex((PermissionError,ValueError),"BOOTSTRAP"):
            other.register(changed,bootstrap_attestation=signed)

    def test_verified_grade_receipt_persists_and_tamper_fails_closed(self):
        with TemporaryDirectory() as folder:
            db=WriterForgeDB(Path(folder)/"bootstrap.db")
            try:
                r=SkillRegistry(db=db,scope="work01",
                                bootstrap_verifier_key=BOOT_KEY)
                c=CapabilityContract("grade02",4,"controlled stored skill")
                p=r.bootstrap_attestation_payload(
                    c,source_sha256=SOURCE_SHA,
                    reviewer_id="reviewer01",review_id="receipt01")
                r.register(c,bootstrap_attestation={
                    "source_sha256":SOURCE_SHA,"reviewer_id":"reviewer01",
                    "review_id":"receipt01","signature":sign(p,BOOT_KEY)})
                self.assertEqual(r.get("grade02").status,SkillStatus.ACTIVE)
                old=SkillRegistry(db=db,scope="work01",
                                  bootstrap_verifier_key=BOOT_KEY)
                self.assertEqual(old.get("grade02").status,SkillStatus.ACTIVE)
                db.conn.execute(
                    "UPDATE skill_bootstrap_receipts SET signature=? "
                    "WHERE scope='work01'",("0"*64,))
                db.conn.commit()
                with self.assertRaisesRegex((PermissionError,ValueError),
                                            "BOOTSTRAP"):
                    SkillRegistry(db=db,scope="work01",
                                  bootstrap_verifier_key=BOOT_KEY)
            finally:
                db.close()

    def test_legacy_high_active_with_missing_proof_is_not_trusted(self):
        with TemporaryDirectory() as folder:
            db=WriterForgeDB(Path(folder)/"legacy.db")
            try:
                db.conn.execute(
                    "INSERT INTO skill_capabilities("
                    "scope,skill_name,level,status,revision,statement,"
                    "dependencies_json) VALUES(?,?,?,?,?,?,?)",
                    ("legacy","pre-v64-high",9,"active",1,
                     "preexisting unverified historical grade","{}"))
                db.conn.commit()
                r=SkillRegistry(db=db,scope="legacy",
                                bootstrap_verifier_key=BOOT_KEY)
                item=r.get("pre-v64-high")
                self.assertEqual(item.level,9)
                self.assertNotEqual(item.status,SkillStatus.ACTIVE)
                self.assertEqual(db.conn.execute(
                    "SELECT level FROM skill_capabilities "
                    "WHERE scope='legacy'").fetchone()[0],9)
                self.assertEqual(db.conn.execute(
                    "SELECT COUNT(*) FROM skill_bootstrap_receipts").fetchone()[0],0)
            finally:
                db.close()

    def test_unverified_old_high_grade_cannot_satisfy_dependencies(self):
        with TemporaryDirectory() as folder:
            db=WriterForgeDB(Path(folder)/"legacy-dependency.db")
            try:
                db.conn.execute(
                    "INSERT INTO skill_capabilities("
                    "scope,skill_name,level,status,revision,statement,"
                    "dependencies_json) VALUES(?,?,?,?,?,?,?)",
                    ("legacy","invented-master",9,"active",1,
                     "unproven old grade","{}"))
                db.conn.commit()
                r=SkillRegistry(db=db,scope="legacy",
                                bootstrap_verifier_key=BOOT_KEY)
                r.register(CapabilityContract(
                    "new-dependent",1,"depends on a grade",
                    {"invented-master":5}))
                self.assertFalse(r.bootstrap_verified("invented-master"))
                self.assertEqual(r.get("invented-master").status,
                                 SkillStatus.SHADOW)
                problems=r.lagging()
                self.assertTrue(any(x.skill=="new-dependent" and
                                    x.dependency=="invented-master"
                                    for x in problems))
            finally:
                db.close()

    def test_legitimate_signed_level_one_promotion_survives_restart(self):
        from writerforge.evolution import EvolutionEngine,UpgradeCandidate,PromotionEvidence
        key=b"synthetic-V64-verified-promotion-recovery"
        with TemporaryDirectory() as folder:
            db=WriterForgeDB(Path(folder)/"promotion.db")
            try:
                reg=SkillRegistry(db=db,scope="recovery",
                                  promotion_verifier_key=key)
                reg.register(CapabilityContract("genuine01",1,"L1 baseline"))
                engine=EvolutionEngine(registry=reg,promotion_verifier_key=key)
                candidate=UpgradeCandidate(
                    skill="genuine01",new_level=2,
                    capability_statement="synthetic verified L2 transition",
                    evidence_id="proof01",requires_human_anchor=True,
                    evidence=PromotionEvidence(
                        capability_statement="synthetic measured change",
                        heldout_success=.95,transfer_success=.85,
                        regression_success=.98,judge_stability=.97,
                        repeated_failure_reduction=.5,runtime_regression=.01,
                        human_anchor_count=1))
                signed=engine.promotion_attestation_payload(
                    candidate,reviewer_id="external64",review_id="review64")
                engine.apply_upgrade(
                    candidate,policy="manual",approved=True,
                    attestation={"reviewer_id":"external64",
                                 "review_id":"review64",
                                 "signature":sign(signed,key)})
                self.assertEqual(reg.get("genuine01").status,
                                 SkillStatus.ACTIVE)
                db.close()
                db=WriterForgeDB(Path(folder)/"promotion.db")
                revived=SkillRegistry(
                    db=db,scope="recovery",promotion_verifier_key=key)
                self.assertEqual(revived.get("genuine01").level,2)
                self.assertEqual(revived.get("genuine01").status,
                                 SkillStatus.ACTIVE)
                self.assertTrue(revived.grade_verified("genuine01"))
                # EvolutionEngine often opens the registry BEFORE binding
                # the verifier, so re-authentication must work in that path.
                recovered_engine=EvolutionEngine(
                    db=db,scope="recovery",promotion_verifier_key=key)
                self.assertEqual(
                    recovered_engine.registry.get("genuine01").status,
                    SkillStatus.ACTIVE)
                self.assertTrue(
                    recovered_engine.registry.grade_verified("genuine01"))
            finally:
                db.close()

    def test_signed_two_step_promotion_chain_cannot_hide_corrupted_history(self):
        from writerforge.evolution import EvolutionEngine,UpgradeCandidate,PromotionEvidence
        key=b"synthetic-V64-multi-step-review-recovery"
        with TemporaryDirectory() as folder:
            db=WriterForgeDB(Path(folder)/"two-steps.db")
            try:
                r=SkillRegistry(db=db,scope="chain",
                                promotion_verifier_key=key)
                r.register(CapabilityContract("skillChain",1,"L1 baseline"))
                engine=EvolutionEngine(registry=r,promotion_verifier_key=key)
                for level in (2,3):
                    candidate=UpgradeCandidate(
                        skill="skillChain",new_level=level,
                        capability_statement=f"synthetic L{level} bounded",
                        evidence_id=f"proof{level}",
                        requires_human_anchor=True,
                        evidence=PromotionEvidence(
                            capability_statement="synthetic proof",
                            heldout_success=.93,transfer_success=.86,
                            regression_success=.98,judge_stability=.96,
                            repeated_failure_reduction=.43,runtime_regression=.01,
                            human_anchor_count=1))
                    payload=engine.promotion_attestation_payload(
                        candidate,reviewer_id="external64",
                        review_id=f"review{level}")
                    engine.apply_upgrade(
                        candidate,policy="manual",approved=True,
                        attestation={"reviewer_id":"external64",
                                     "review_id":f"review{level}",
                                     "signature":sign(payload,key)})
                db.close()
                db=WriterForgeDB(Path(folder)/"two-steps.db")
                recovered=SkillRegistry(db=db,scope="chain",
                                        promotion_verifier_key=key)
                self.assertEqual(recovered.get("skillChain").level,3)
                self.assertEqual(recovered.get("skillChain").status,
                                 SkillStatus.ACTIVE)
                self.assertTrue(recovered.grade_verified("skillChain"))
                db.conn.execute(
                    "UPDATE skill_promotion_receipts SET signature=? "
                    "WHERE scope='chain' AND new_level=2",("0"*64,))
                db.conn.commit()
                with self.assertRaisesRegex(PermissionError,"PROMOTION"):
                    SkillRegistry(db=db,scope="chain",
                                  promotion_verifier_key=key)
            finally:
                db.close()

    def test_signed_high_bootstrap_then_promotion_preserves_lineage_on_reopen(self):
        from writerforge.evolution import EvolutionEngine,UpgradeCandidate,PromotionEvidence
        key=b"synthetic-V64-verified-promotion-lineage"
        with TemporaryDirectory() as folder:
            db=WriterForgeDB(Path(folder)/"lineage.db")
            try:
                reg=SkillRegistry(
                    db=db,scope="lineage",bootstrap_verifier_key=BOOT_KEY,
                    promotion_verifier_key=key)
                original=CapabilityContract("priorL4",4,"inherited certified fixture")
                raw=reg.bootstrap_attestation_payload(
                    original,source_sha256=SOURCE_SHA,
                    reviewer_id="bootstrapIssuer",review_id="boot64")
                reg.register(original,bootstrap_attestation={
                    "source_sha256":SOURCE_SHA,
                    "reviewer_id":"bootstrapIssuer","review_id":"boot64",
                    "signature":sign(raw,BOOT_KEY)})
                engine=EvolutionEngine(registry=reg,promotion_verifier_key=key)
                cand=UpgradeCandidate(
                    skill="priorL4",new_level=5,
                    capability_statement="synthetic verified progression",
                    evidence_id="manual64",requires_human_anchor=True,
                    evidence=PromotionEvidence(
                        capability_statement="synthetic progression fixture",
                        heldout_success=.95,transfer_success=.85,
                        regression_success=.98,judge_stability=.97,
                        repeated_failure_reduction=.5,runtime_regression=.01,
                        human_anchor_count=1))
                p=engine.promotion_attestation_payload(
                    cand,reviewer_id="external64",review_id="review64")
                engine.apply_upgrade(
                    cand,policy="manual",approved=True,
                    attestation={"reviewer_id":"external64",
                                 "review_id":"review64","signature":sign(p,key)})
                db.close()
                db=WriterForgeDB(Path(folder)/"lineage.db")
                loaded=SkillRegistry(
                    db=db,scope="lineage",bootstrap_verifier_key=BOOT_KEY,
                    promotion_verifier_key=key)
                self.assertEqual(loaded.get("priorL4").level,5)
                self.assertEqual(loaded.get("priorL4").status,
                                 SkillStatus.ACTIVE)
                self.assertTrue(loaded.grade_verified("priorL4"))
            finally:
                db.close()

    def test_level_one_baseline_is_not_mistaken_for_verified_literary_mastery(self):
        reg=SkillRegistry()
        reg.register(CapabilityContract("baseline01",1,"untrained minimum"))
        self.assertEqual(reg.get("baseline01").level,1)
        self.assertFalse(reg.bootstrap_verified("baseline01"))
        with self.assertRaisesRegex((ValueError,PermissionError),"BOOTSTRAP"):
            reg.register(CapabilityContract(
                "baseline02",9,"unsupported high-grade",status=SkillStatus.SHADOW))


class AIProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.path=Path(self.tmp.name)/"provenance.db"
        self.db=WriterForgeDB(self.path)
        self.sid=self.db.conn.execute(
            "INSERT INTO snapshots(status,layout,note) "
            "VALUES('published','full','V64 synthetic')").lastrowid
        self.db.conn.commit()
        self.rt=RuntimeEngine()
        self.rt.enter_write(self.sid)
        self.project="project64"
        self.scene="scene64"
        self.text="少年不声张，只将看到的脚印记在心里。"

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def commit_direct(self,origin,commit_id="commit01",permit=None):
        return WritingFlow(self.db,self.rt,self.project).accept_draft(
            commit_id,self.scene,self.text,origin=origin,
            ai_provenance=permit)

    def make_packet(self):
        prompt="Synthetic original scene with no source text."
        return GroundedDraftPacket(
            self.scene,self.project,self.sid,(),(),prompt,
            sha256(prompt.encode("utf-8")).hexdigest())

    def test_low_level_generated_prose_requires_provenance(self):
        with self.assertRaisesRegex((PermissionError,ValueError,RuntimeError),
                                    "PROVENANCE"):
            self.commit_direct("assistant_generated")
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM story_commit_receipts").fetchone()[0],0)

    def test_raw_coordinator_rejects_generated_effect_even_without_flow(self):
        plan=StoryCommitPlan(
            self.project,"rawcommit01",(
                StoryEffect(EffectType.ACCEPT_PROSE,self.scene,{
                    "body":self.text,"origin":"assistant_generated"}),))
        with self.assertRaisesRegex((PermissionError,ValueError,RuntimeError),
                                    "PROVENANCE"):
            StoryCommitCoordinator(self.db,self.rt).commit(plan)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM story_commit_receipts").fetchone()[0],0)

    def test_user_author_workflow_remains_separate_and_writable(self):
        out=self.commit_direct("author_written","human01")
        self.assertTrue(out.committed)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM story_ai_provenance").fetchone()[0],0)

    def test_signed_exact_unicode_and_dotted_scene_names(self):
        from writerforge.ai_provenance import issue_ai_commit_permit
        self.scene="第一卷.ch1.夜雨"
        digest=sha256(self.text.encode("utf-8")).hexdigest()
        permit=issue_ai_commit_permit(
            key=AI_KEY,project_id=self.project,
            scene_id=self.scene,commit_id="signed-scene01",
            snapshot_id=self.sid,body_sha256=digest,
            candidate_sha256=digest,author_approved=True)
        with patch.dict("os.environ",{
                "WRITERFORGE_AI_COMMIT_VERIFY_KEY_HEX":AI_KEY.hex()}):
            accepted=self.commit_direct(
                "assistant_generated","signed-scene01",permit)
        self.assertTrue(accepted.committed)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM story_ai_provenance").fetchone()[0],1)

    def test_signed_ai_permit_cannot_rebind_body_scene_or_commit(self):
        from writerforge.ai_provenance import (
            issue_ai_commit_permit
        )
        signed=issue_ai_commit_permit(
            key=AI_KEY,project_id=self.project,
            scene_id=self.scene,commit_id="signed01",
            snapshot_id=self.sid,body_sha256=sha256(self.text.encode()).hexdigest(),
            candidate_sha256=sha256(self.text.encode()).hexdigest(),
            author_approved=True,decision_sha256=None)
        with patch.dict("os.environ",{
                "WRITERFORGE_AI_COMMIT_VERIFY_KEY_HEX":AI_KEY.hex()}):
            with self.assertRaisesRegex((PermissionError,ValueError,RuntimeError),
                                        "PROVENANCE"):
                self.commit_direct("assistant_generated","different01",signed)
            self.assertEqual(self.db.conn.execute(
                "SELECT COUNT(*) FROM story_commit_receipts").fetchone()[0],0)
            with self.assertRaisesRegex((PermissionError,ValueError,RuntimeError),
                                        "PROVENANCE"):
                altered=dict(signed,body_sha256="f"*64)
                self.commit_direct("assistant_generated","signed01",altered)
            out=self.commit_direct("assistant_generated","signed01",signed)
        self.assertTrue(out.committed)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM story_ai_provenance").fetchone()[0],1)
        rec=self.db.conn.execute(
            "SELECT permit_sha FROM story_ai_provenance "
            "WHERE project_id=? AND commit_id=?",
            (self.project,"signed01")).fetchone()
        self.assertEqual(len(rec[0]),64)

    def test_approved_experience_requires_matching_frozen_decision_at_commit(self):
        from writerforge.experience_decision import ExperienceDecisionBridge
        from writerforge.ai_provenance import issue_ai_commit_permit
        reviewer_key=b"synthetic-V64-experience-review-key"
        excerpt="synthetic verified locator, no novel"
        source_sha=sha256(excerpt.encode("utf-8")).hexdigest()
        self.db.conn.execute(
            "INSERT INTO studied_works(work_id,title,source_uri,"
            "source_sha256,chapter_count) VALUES(?,?,?,?,?)",
            ("synthetic64","Synthetic work","test://source64",
             sha256(b"test-work64").hexdigest(),1))
        self.db.conn.execute(
            "INSERT INTO studied_chapters(work_id,chapter,chapter_sha256,"
            "heading,source_spans,retrieval_entries,snapshot_id)"
            " VALUES(?,?,?,?,?,?,?)",
            ("synthetic64",1,source_sha,"Synthetic",1,1,self.sid))
        self.db.conn.execute(
            "INSERT INTO source_spans(work_id,chapter,paragraph,sentence,"
            "excerpt,source_sha256,tracks_json,craft_json)"
            " VALUES(?,?,?,?,?,?,?,?)",
            ("synthetic64",1,1,1,excerpt,source_sha,"{}","{}"))
        self.db.conn.commit()
        learn=RuntimeEngine();learn.enter_learn()
        bridge=ExperienceDecisionBridge(
            self.db,learn,reviewer_key=reviewer_key)
        bridge.stage_candidate(
            project_id=self.project,experience_id="lesson64",
            snapshot_id=self.sid,
            source_ref={"work_id":"synthetic64","chapter":1,
                        "paragraph":1,"sentence":1,
                        "source_sha256":source_sha},
            required_tags=["knowledge_limited"],
            forbidden_tags=["omniscient"],
            operation_code="CHECK_KNOWLEDGE")
        authorization=bridge.approval_payload(
            project_id=self.project,experience_id="lesson64",
            reviewer_id="external64",review_id="review64")
        bridge.approve_candidate(
            project_id=self.project,experience_id="lesson64",
            reviewer_id="external64",review_id="review64",
            signature=sign(authorization,reviewer_key))
        h=sha256(self.text.encode("utf-8")).hexdigest()
        missing=issue_ai_commit_permit(
            key=AI_KEY,project_id=self.project,scene_id=self.scene,
            commit_id="missing64",snapshot_id=self.sid,
            body_sha256=h,candidate_sha256=h,
            author_approved=True)
        with patch.dict("os.environ",{
                "WRITERFORGE_AI_COMMIT_VERIFY_KEY_HEX":AI_KEY.hex(),
                "WRITERFORGE_EXPERIENCE_REVIEW_VERIFY_KEY_HEX":
                    reviewer_key.hex()}):
            with self.assertRaisesRegex((RuntimeError,PermissionError),
                                        "EXPERIENCE_DECISION_REQUIRED"):
                self.commit_direct("assistant_generated","missing64",missing)
            self.assertEqual(self.db.conn.execute(
                "SELECT COUNT(*) FROM story_commit_receipts"
                ).fetchone()[0],0)
            selected=ExperienceDecisionBridge(
                self.db,self.rt,reviewer_key=reviewer_key).decide(
                    project_id=self.project,scene_id=self.scene,
                    attempt_id="attempt64",goal="synthetic decision",
                    scene_signals={"knowledge_limited":True,
                                   "omniscient":False})
            self.assertEqual(selected["decisions"][0]["decision"],"SELECT")
            valid=issue_ai_commit_permit(
                key=AI_KEY,project_id=self.project,scene_id=self.scene,
                commit_id="matching64",snapshot_id=self.sid,
                body_sha256=h,candidate_sha256=h,
                author_approved=True,
                decision_sha256=selected["decision_sha256"],
                experience_attempt_id="attempt64")
            result=self.commit_direct(
                "assistant_generated","matching64",valid)
        self.assertTrue(result.committed)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM story_ai_provenance").fetchone()[0],1)

    def test_official_accept_candidate_signs_provenance_only_with_trusted_host(self):
        packet=self.make_packet()
        folder=Path(self.tmp.name)/"candidates"
        saved=save_candidate(packet,self.text,"fixture-model",folder)
        with self.assertRaisesRegex((PermissionError,ValueError,RuntimeError),
                                    "PROVENANCE|SIGN"):
            accept_candidate(
                self.db,self.rt,project_id=self.project,
                manifest_path=saved["manifest"],commit_id="official01",
                explicitly_approved=True)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM story_commit_receipts").fetchone()[0],0)
        with patch.dict("os.environ",{
                "WRITERFORGE_AI_COMMIT_VERIFY_KEY_HEX":AI_KEY.hex()}):
            out=accept_candidate(
                self.db,self.rt,project_id=self.project,
                manifest_path=saved["manifest"],commit_id="official01",
                explicitly_approved=True)
        self.assertTrue(out["accepted"])
        row=self.db.conn.execute(
            "SELECT permit_json FROM story_ai_provenance "
            "WHERE project_id=? AND commit_id=?",
            (self.project,"official01")).fetchone()
        self.assertIsNotNone(row)
        self.assertNotIn(self.text,row["permit_json"])

    def test_assistant_permit_cannot_bind_to_nonexistent_source_snapshot(self):
        from writerforge.ai_provenance import issue_ai_commit_permit
        missing=self.sid+501
        self.rt.exit()
        self.rt.enter_write(missing)
        h=sha256(self.text.encode("utf-8")).hexdigest()
        permit=issue_ai_commit_permit(
            key=AI_KEY,project_id=self.project,scene_id=self.scene,
            commit_id="unpublished01",snapshot_id=missing,
            body_sha256=h,candidate_sha256=h,author_approved=True)
        with patch.dict("os.environ",{
                "WRITERFORGE_AI_COMMIT_VERIFY_KEY_HEX":AI_KEY.hex()}):
            with self.assertRaisesRegex((PermissionError,ValueError,RuntimeError),
                                        "PROVENANCE_SOURCE_SNAPSHOT"):
                self.commit_direct("assistant_generated","unpublished01",permit)
        self.assertIsNone(self.db.conn.execute(
            "SELECT 1 FROM story_commit_receipts WHERE commit_id='unpublished01'"
        ).fetchone())

    def test_unsigned_or_unapproved_ai_permit_is_never_accepted(self):
        from writerforge.ai_provenance import issue_ai_commit_permit
        with self.assertRaisesRegex((PermissionError,ValueError),
                                    "PROVENANCE"):
            issue_ai_commit_permit(
                key=AI_KEY,project_id=self.project,
                scene_id=self.scene,commit_id="bad01",
                snapshot_id=self.sid,
                body_sha256=sha256(self.text.encode()).hexdigest(),
                candidate_sha256=sha256(self.text.encode()).hexdigest(),
                author_approved=False,decision_sha256=None)
        with self.assertRaisesRegex((PermissionError,ValueError,RuntimeError),
                                    "PROVENANCE"):
            self.commit_direct("assistant_generated","unsigned01",
                               {"origin":"assistant_generated"})

    def test_accepted_candidate_cannot_claim_author_written_origin(self):
        from writerforge.ai_provenance import issue_ai_commit_permit
        signed=issue_ai_commit_permit(
            key=AI_KEY,project_id=self.project,
            scene_id=self.scene,commit_id="human02",
            snapshot_id=self.sid,body_sha256=sha256(self.text.encode()).hexdigest(),
            candidate_sha256=sha256(self.text.encode()).hexdigest(),
            author_approved=True,decision_sha256=None)
        with patch.dict("os.environ",{
                "WRITERFORGE_AI_COMMIT_VERIFY_KEY_HEX":AI_KEY.hex()}):
            with self.assertRaisesRegex((PermissionError,ValueError,RuntimeError),
                                        "PROVENANCE"):
                self.commit_direct("author_written","human02",signed)


if __name__ == "__main__":
    unittest.main()
