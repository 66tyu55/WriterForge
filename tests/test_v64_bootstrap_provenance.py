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
