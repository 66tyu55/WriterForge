"""V62 fail-first: old evidence pointers, negative outcomes and policy revocation.

Everything here is synthetic except explicit public SHA pointers; there is no
R2 read, original text download, model call or creative skill promotion.
A green software assertion must not be called literary understanding.
"""
from __future__ import annotations
from tempfile import TemporaryDirectory
from pathlib import Path
from hashlib import sha256
import hmac
import json
import sqlite3
import unittest

from writerforge.db import WriterForgeDB
from writerforge.runtime import RuntimeEngine
from writerforge.experience_decision import (
    ExperienceDecisionBridge,canonical,OPERATION_GUIDANCE
)

KEY=b"synthetic-V62-attestation-key-authority"


def sha(s):
    return sha256(s.encode("utf-8")).hexdigest()


def sig(payload):
    return hmac.new(KEY,canonical(payload).encode("utf-8"),
                    "sha256").hexdigest()


class V62ExperienceFailureTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.path=Path(self.tmp.name)/"wf.sqlite3"
        self.db=WriterForgeDB(self.path)
        self.rt=RuntimeEngine()
        self.rt.enter_learn()
        self.snapshot=self.db.conn.execute(
            "INSERT INTO snapshots(status,layout,note) "
            "VALUES('published','full','v62 synthetic')").lastrowid
        source="short synthetic observation"
        self.source_sha=sha(source)
        self.db.conn.execute(
            "INSERT INTO studied_works(work_id,title,source_uri,"
            "source_sha256,chapter_count) VALUES(?,?,?,?,?)",
            ("syntheticwork","Fixture","test://fiction",
             sha("synthetic-work"),1))
        self.db.conn.execute(
            "INSERT INTO studied_chapters(work_id,chapter,chapter_sha256,"
            "heading,source_spans,retrieval_entries,snapshot_id)"
            " VALUES(?,?,?,?,?,?,?)",
            ("syntheticwork",1,sha("chapter"),"Synthetic",1,1,self.snapshot))
        self.locator={"work_id":"syntheticwork","chapter":1,
                      "paragraph":1,"sentence":1,"source_sha256":self.source_sha}
        self.db.conn.execute(
            "INSERT INTO source_spans(work_id,chapter,paragraph,sentence,"
            "excerpt,source_sha256,tracks_json,craft_json)"
            " VALUES(?,?,?,?,?,?,?,?)",
            ("syntheticwork",1,1,1,source,self.source_sha,"{}","{}"))
        self.db.conn.commit()
        self.bridge=ExperienceDecisionBridge(self.db,self.rt,reviewer_key=KEY)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def stage(self, experience_id="lesson01", *, operation_code="CHECK_KNOWLEDGE",
              supersedes_experience_id=None):
        return self.bridge.stage_candidate(
            project_id="project01",experience_id=experience_id,
            snapshot_id=self.snapshot,source_ref=self.locator,
            required_tags=("limited_knowledge",),
            forbidden_tags=("omniscient",),
            operation_code=operation_code,
            supersedes_experience_id=supersedes_experience_id)

    def approve(self, experience_id="lesson01", review_id="review01"):
        payload=self.bridge.approval_payload(
            project_id="project01",experience_id=experience_id,
            reviewer_id="external01",review_id=review_id)
        return self.bridge.approve_candidate(
            project_id="project01",experience_id=experience_id,
            reviewer_id="external01",review_id=review_id,
            signature=sig(payload))

    def write(self):
        self.rt.exit()
        self.rt.enter_write(self.snapshot)

    def learn(self):
        self.rt.exit()
        self.rt.enter_learn()

    def decide(self, attempt):
        return self.bridge.decide(
            project_id="project01",scene_id="scene01",attempt_id=attempt,
            goal="synthetic trace without copied prose",
            scene_signals={"limited_knowledge":True,"omniscient":False})

    def post(self, attempt, experience_id="lesson01", outcome="NOT_APPLIED"):
        return self.bridge.report_postwrite(
            project_id="project01",attempt_id=attempt,
            draft="角色看到错误判断的实际后果，没有凭空获得信息。",
            experience_id=experience_id,outcome=outcome)

    def test_not_applied_changes_next_decision_to_explainable_skip(self):
        self.stage();self.approve();self.write()
        first=self.decide("before01")
        self.assertEqual(first["decisions"][0]["decision"],"SELECT")
        self.post("before01")
        later=self.decide("after01")
        self.assertEqual(later["decisions"][0]["decision"],"SKIP")
        self.assertEqual(later["decisions"][0]["reason_code"],
                         "PRIOR_NOT_APPLIED")
        self.assertEqual(later["prompt_guidance"],"")
        self.assertTrue(self.bridge.read_decision(
            project_id="project01",attempt_id="before01")
            ["decisions"][0]["decision"]=="SELECT")

    def test_uncertain_self_check_quarantines_without_claiming_failure_truth(self):
        self.stage();self.approve();self.write()
        self.decide("before02")
        self.post("before02",outcome="UNCERTAIN")
        result=self.decide("after02")
        self.assertEqual(result["decisions"][0]["decision"],"UNCERTAIN")
        self.assertEqual(result["decisions"][0]["reason_code"],
                         "PRIOR_APPLICATION_UNCERTAIN")
        self.assertEqual(result["prompt_guidance"],"")
        self.assertFalse(result["literary_semantics_verified"])

    def test_only_claimed_application_never_becomes_literary_approval(self):
        self.stage();self.approve();self.write()
        self.decide("before03")
        draft="少年见钟声止歇，已知的线索只有门口足迹，因此选择退后。"
        self.bridge.report_postwrite(
            project_id="project01",attempt_id="before03",draft=draft,
            experience_id="lesson01",outcome="CLAIMED_APPLIED",
            quote="已知的线索只有门口足迹")
        later=self.decide("after03")
        self.assertEqual(later["decisions"][0]["decision"],"SELECT")
        self.assertFalse(later["literary_semantics_verified"])
        self.assertFalse(later["auto_skill_promotion"])

    def test_selected_frozen_attempt_revoked_after_failure_must_not_reactivate(self):
        self.stage();self.approve();self.write()
        saved=self.decide("before04")
        self.post("before04")
        with self.assertRaisesRegex(ValueError,"QUARANTINED"):
            self.bridge.validate_live_decision(
                project_id="project01",attempt_id="before04")
        self.assertEqual(self.bridge.read_decision(
            project_id="project01",attempt_id="before04")
            ["decision_sha256"],saved["decision_sha256"])

    def test_new_revision_requires_prior_adverse_result_and_new_signing(self):
        self.stage();self.approve()
        with self.assertRaisesRegex(ValueError,"PRIOR_FAILURE"):
            self.stage("revision01",operation_code="TRACE_CONSEQUENCE",
                       supersedes_experience_id="lesson01")
        self.write()
        self.decide("before05")
        self.post("before05")
        self.learn()
        version=self.stage("revision01",operation_code="TRACE_CONSEQUENCE",
                           supersedes_experience_id="lesson01")
        self.assertFalse(version["eligible_for_writing"])
        self.write()
        only_old=self.decide("without_revision")
        self.assertEqual([x["decision"] for x in only_old["decisions"]],
                         ["SKIP"])
        self.learn()
        self.approve("revision01","review02")
        self.write()
        fresh=self.decide("with_revision")
        states={x["experience_id"]:x["decision"] for x in fresh["decisions"]}
        self.assertEqual(states,{"lesson01":"SKIP","revision01":"SELECT"})
        self.assertIn(OPERATION_GUIDANCE["TRACE_CONSEQUENCE"],
                      fresh["prompt_guidance"])
        self.assertNotIn(OPERATION_GUIDANCE["CHECK_KNOWLEDGE"],
                         fresh["prompt_guidance"])

    def test_signed_revoke_blocks_new_use_and_previous_snapshot_reuse(self):
        self.stage();self.approve();self.write()
        old=self.decide("before06")
        self.learn()
        p=self.bridge.revocation_payload(
            project_id="project01",experience_id="lesson01",
            reviewer_id="external01",review_id="revocation01",
            reason_code="SOURCE_REVIEW_DISPUTED")
        with self.assertRaisesRegex(ValueError,"ATTESTATION"):
            self.bridge.revoke_candidate(
                project_id="project01",experience_id="lesson01",
                reviewer_id="external01",review_id="revocation01",
                reason_code="SOURCE_REVIEW_DISPUTED",signature="0"*64)
        out=self.bridge.revoke_candidate(
            project_id="project01",experience_id="lesson01",
            reviewer_id="external01",review_id="revocation01",
            reason_code="SOURCE_REVIEW_DISPUTED",signature=sig(p))
        self.assertFalse(out["eligible_for_writing"])
        self.assertTrue(self.bridge.revoke_candidate(
            project_id="project01",experience_id="lesson01",
            reviewer_id="external01",review_id="revocation01",
            reason_code="SOURCE_REVIEW_DISPUTED",signature=sig(p))["replayed"])
        self.write()
        with self.assertRaisesRegex(ValueError,"REVOKED"):
            self.bridge.validate_live_decision(
                project_id="project01",attempt_id="before06")
        later=self.decide("after06")
        self.assertEqual(later["decisions"][0]["reason_code"],
                         "EXPERIENCE_REVOKED")
        self.assertEqual(later["decisions"][0]["decision"],"SKIP")
        self.assertEqual(self.bridge.read_decision(
            project_id="project01",attempt_id="before06")
            ["decision_sha256"],old["decision_sha256"])

    def test_history_refs_are_quarantined_not_transferred_to_write(self):
        pointer=self.bridge.register_legacy_reference(
            project_id="project01",legacy_id="v38_l2_role_conflict",
            source_family="V38_L2_CONFLICT",
            source_receipt_sha256="a9d5d521b2e0adbeb416f9325b0adabaad408abb728bd978099effe328488a62",
            independent_review_sha256="e2ed24abc352daef678165de8bee5f7c283f5709cf3a23c9fe99b9a876aeb0db",
            issue_code="SEMANTIC_ROLE_DISPUTED")
        self.assertEqual(pointer["status"],"UNVERIFIED_REMOTE_POINTER")
        self.assertFalse(pointer["eligible_for_writing"])
        self.assertTrue(self.bridge.register_legacy_reference(
            project_id="project01",legacy_id="v38_l2_role_conflict",
            source_family="V38_L2_CONFLICT",
            source_receipt_sha256="a9d5d521b2e0adbeb416f9325b0adabaad408abb728bd978099effe328488a62",
            independent_review_sha256="e2ed24abc352daef678165de8bee5f7c283f5709cf3a23c9fe99b9a876aeb0db",
            issue_code="SEMANTIC_ROLE_DISPUTED")["replayed"])
        record=self.bridge.read_legacy_reference(
            project_id="project01",legacy_id="v38_l2_role_conflict")
        self.assertEqual(record["status"],"UNVERIFIED_REMOTE_POINTER")
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM experience_approvals").fetchone()[0],0)
        self.write()
        self.assertEqual(self.decide("after07")["decisions"],[])
        self.assertEqual(self.decide("after07")["prompt_guidance"],"")

    def test_legacy_metadata_tamper_and_copy_attempt_are_refused(self):
        with self.assertRaisesRegex(ValueError,"FIELDS"):
            self.bridge.register_legacy_reference(
                project_id="project01",legacy_id="bad01",
                source_family="V38_L2_CONFLICT",
                source_receipt_sha256="f"*64,
                independent_review_sha256="e"*64,
                issue_code="SEMANTIC_ROLE_DISPUTED",
                novel_excerpt="Do not copy my original prose")
        self.bridge.register_legacy_reference(
            project_id="project01",legacy_id="old01",
            source_family="V31_EXPERIMENT",
            source_receipt_sha256="cd9cfa1d6413ed84bb4d3bb18c9a77d873666df95cbcd5898d4745cfeb2e3c7c",
            independent_review_sha256=None,issue_code="SELF_REVIEW_UNVERIFIED")
        self.db.conn.execute(
            "UPDATE experience_legacy_refs SET ref_json=? "
            "WHERE legacy_id='old01'",('{"modified":"yes"}',))
        self.db.conn.commit()
        with self.assertRaisesRegex(ValueError,"TAMPERED"):
            self.bridge.read_legacy_reference(
                project_id="project01",legacy_id="old01")

    def test_restart_keeps_adverse_feedback_and_all_old_decisions(self):
        self.stage();self.approve();self.write()
        original=self.decide("before08")
        self.post("before08")
        self.db.close()
        self.db=WriterForgeDB(self.path)
        self.bridge=ExperienceDecisionBridge(self.db,self.rt,reviewer_key=KEY)
        after=self.decide("after08")
        self.assertEqual(after["decisions"][0]["decision"],"SKIP")
        self.assertEqual(self.bridge.read_decision(
            project_id="project01",attempt_id="before08")
            ["decision_sha256"],original["decision_sha256"])

    def test_corrupted_negative_receipt_fails_closed_not_ignored(self):
        self.stage();self.approve();self.write()
        self.decide("before09")
        self.post("before09")
        self.db.conn.execute(
            "UPDATE experience_postwrites SET receipt_json='{}' "
            "WHERE project_id='project01'")
        self.db.conn.commit()
        with self.assertRaisesRegex(ValueError,"TAMPERED"):
            self.decide("after09")

    def test_no_unlimited_feedback_scan_and_no_new_model_calls(self):
        self.stage();self.approve();self.write()
        self.decide("before10")
        self.post("before10")
        previous=self.db.conn.execute(
            "SELECT COUNT(*) FROM experience_postwrites").fetchone()[0]
        self.decide("after10")
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM experience_postwrites").fetchone()[0],
            previous)


if __name__=="__main__":
    unittest.main()
