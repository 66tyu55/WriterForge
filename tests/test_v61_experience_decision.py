"""V61 independent fail-first synthetic LEARN -> gated policy -> WRITE tests.

No LLM, R2, copyrighted source, external judge or literary score.
These verify software contracts only, not literary efficacy or authorial intent.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import hmac
import json
import unittest

from writerforge.db import WriterForgeDB
from writerforge.runtime import RuntimeEngine, Mode
from writerforge.verified_flow import VerifiedWritingFlow, WritingExecutionError
from writerforge.evolution import (
    SkillRegistry, CapabilityContract, EvolutionEngine, UpgradeCandidate,
    PromotionEvidence
)

KEY=b"synthetic-experience-review-key-v61"
PROMOTION_KEY=b"synthetic-independent-promotion-key-v61"


def hash_text(value):
    return sha256(value.encode("utf-8")).hexdigest()


def canon(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False)


class V61ExperienceDecisionTests(unittest.TestCase):
    def setUp(self):
        # Import inside individual fresh test setup so first red run records
        # distinct cases instead of silently skipping missing functionality.
        from writerforge.experience_decision import ExperienceDecisionBridge
        self.Bridge=ExperienceDecisionBridge
        self.temp=TemporaryDirectory()
        self.path=Path(self.temp.name)/"synthetic.sqlite3"
        self.db=WriterForgeDB(self.path)
        self.runtime=RuntimeEngine()
        self.runtime.enter_learn()
        self.source="synthetic original source unit for verification only"
        self.source_sha=hash_text(self.source)
        cur=self.db.conn.execute(
            "INSERT INTO snapshots(status,layout,note) VALUES('published','full','V61 fixture')")
        self.snapshot=int(cur.lastrowid)
        self.db.conn.execute(
            "INSERT INTO studied_works("
            "work_id,title,source_uri,source_sha256,chapter_count) "
            "VALUES(?,?,?,?,?)",
            ("synthetic_work","SYNTHETIC","synthetic://source",
             hash_text("synthetic-work"),1))
        self.db.conn.execute(
            "INSERT INTO studied_chapters("
            "work_id,chapter,chapter_sha256,heading,source_spans,"
            "retrieval_entries,snapshot_id) VALUES(?,?,?,?,?,?,?)",
            ("synthetic_work",1,self.source_sha,"fixture",1,1,self.snapshot))
        self.db.conn.execute(
            "INSERT INTO source_spans("
            "work_id,chapter,paragraph,sentence,excerpt,source_sha256,"
            "tracks_json,craft_json) VALUES(?,?,?,?,?,?,?,?)",
            ("synthetic_work",1,1,1,self.source,self.source_sha,"{}","{}"))
        self.db.conn.commit()
        self.locator={"work_id":"synthetic_work","chapter":1,
                      "paragraph":1,"sentence":1,"source_sha256":self.source_sha}
        self.bridge=self.Bridge(self.db,self.runtime,reviewer_key=KEY)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def stage(self, *, ident="lesson-01", require=("limited_knowledge",),
              avoid=("omniscient",), operation="CHECK_KNOWLEDGE",
              source_ref=None):
        return self.bridge.stage_candidate(
            project_id="project01",experience_id=ident,
            snapshot_id=self.snapshot,
            source_ref=self.locator if source_ref is None else source_ref,
            required_tags=require,forbidden_tags=avoid,
            operation_code=operation)

    def approve(self, ident="lesson-01", *, signature=None):
        payload=self.bridge.approval_payload(
            experience_id=ident,project_id="project01",
            reviewer_id="external01",review_id="review-01")
        signature=signature or hmac.new(
            KEY,canon(payload).encode("utf-8"),"sha256").hexdigest()
        return self.bridge.approve_candidate(
            project_id="project01",experience_id=ident,
            reviewer_id="external01",review_id="review-01",
            signature=signature)

    def write(self):
        self.runtime.exit()
        self.runtime.enter_write(self.snapshot)

    def decide(self,*,attempt="attempt01",signals=None,enabled=True):
        if signals is None:
            signals={"limited_knowledge":True,"omniscient":False}
        return self.bridge.decide(
            project_id="project01",scene_id="scene01",
            attempt_id=attempt,goal="synthetic investigation",
            scene_signals=signals,enabled=enabled)

    def test_candidate_requires_exact_pinned_source_no_raw_prose(self):
        bad=dict(self.locator,source_sha256="0"*64)
        with self.assertRaisesRegex(ValueError,"SOURCE"):
            self.stage(source_ref=bad)
        with self.assertRaisesRegex(ValueError,"OPERATION"):
            self.stage(operation="COPY_SOURCE_PARAGRAPH")
        with self.assertRaisesRegex(ValueError,"TAGS"):
            self.stage(require=("limited_knowledge","limited_knowledge"))
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM experience_candidates").fetchone()[0],0)

    def test_unsigned_or_self_proposed_lesson_cannot_guide_writing(self):
        self.stage()
        self.write()
        result=self.decide()
        self.assertFalse(any(x["decision"]=="SELECT" for x in result["decisions"]))
        self.assertEqual(result["approved_count"],0)
        self.assertNotIn(self.source,result["prompt_guidance"])

    def test_signature_wrong_key_tampered_or_stale_source_fails(self):
        self.stage()
        with self.assertRaisesRegex(ValueError,"ATTESTATION"):
            self.approve(signature="0"*64)
        self.approve()
        self.db.conn.execute(
            "UPDATE source_spans SET source_sha256=? "
            "WHERE work_id='synthetic_work'",("f"*64,))
        self.db.conn.commit()
        self.write()
        with self.assertRaisesRegex(ValueError,"SOURCE"):
            self.decide()
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM experience_decisions").fetchone()[0],0)

    def test_select_skip_uncertain_are_distinct_and_only_select_guides(self):
        self.stage()
        self.approve()
        self.write()
        selected=self.decide()
        self.assertEqual(selected["decisions"][0]["decision"],"SELECT")
        self.assertIn("已掌握",selected["prompt_guidance"])
        self.assertNotIn(self.source,selected["prompt_guidance"])
        skipped=self.decide(attempt="attempt02",
                            signals={"limited_knowledge":True,
                                     "omniscient":True})
        self.assertEqual(skipped["decisions"][0]["decision"],"SKIP")
        self.assertEqual(skipped["prompt_guidance"],"")
        uncertain=self.decide(attempt="attempt03",
                              signals={"limited_knowledge":None,
                                       "omniscient":False})
        self.assertEqual(uncertain["decisions"][0]["decision"],"UNCERTAIN")
        self.assertEqual(uncertain["prompt_guidance"],"")
        disabled=self.decide(attempt="attempt04",enabled=False)
        self.assertEqual(disabled["decisions"][0]["decision"],"SKIP")
        self.assertEqual(disabled["prompt_guidance"],"")

    def test_frozen_attempt_survives_restart_rejects_input_replacement(self):
        self.stage()
        self.approve()
        self.write()
        first=self.decide()
        self.db.close()
        self.db=WriterForgeDB(self.path)
        self.bridge=self.Bridge(self.db,self.runtime,reviewer_key=KEY)
        again=self.decide()
        self.assertEqual(first,again)
        stored=self.bridge.read_decision(
            project_id="project01",attempt_id="attempt01")
        self.assertEqual(stored["decision_sha256"],first["decision_sha256"])
        with self.assertRaisesRegex(ValueError,"IMMUTABLE"):
            self.decide(signals={"limited_knowledge":False,
                                 "omniscient":False})
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM experience_decisions").fetchone()[0],1)

    def test_postwrite_claim_requires_actual_quote_and_nonselected_is_blocked(self):
        self.stage()
        self.approve()
        self.write()
        self.decide()
        draft="少年握紧纸条，已知的线索只有渡口的钟声，便决定先去查证。"
        with self.assertRaisesRegex(ValueError,"QUOTE"):
            self.bridge.report_postwrite(
                project_id="project01",attempt_id="attempt01",
                draft=draft,experience_id="lesson-01",
                outcome="CLAIMED_APPLIED",quote="从未出现在文章里的引文")
        result=self.bridge.report_postwrite(
            project_id="project01",attempt_id="attempt01",
            draft=draft,experience_id="lesson-01",
            outcome="CLAIMED_APPLIED",quote="已知的线索只有渡口的钟声")
        self.assertFalse(result["literary_effect_verified"])
        self.assertTrue(result["source_text_not_stored"])
        self.assertTrue(self.bridge.report_postwrite(
            project_id="project01",attempt_id="attempt01",
            draft=draft,experience_id="lesson-01",
            outcome="CLAIMED_APPLIED",quote="已知的线索只有渡口的钟声")["replayed"])
        with self.assertRaisesRegex(ValueError,"IMMUTABLE"):
            self.bridge.report_postwrite(
                project_id="project01",attempt_id="attempt01",
                draft=draft,experience_id="lesson-01",
                outcome="NOT_APPLIED")
        self.decide(attempt="attempt02",signals={"limited_knowledge":False,
                                                 "omniscient":False})
        with self.assertRaisesRegex(ValueError,"NOT_SELECTED"):
            self.bridge.report_postwrite(
                project_id="project01",attempt_id="attempt02",
                draft=draft,experience_id="lesson-01",
                outcome="CLAIMED_APPLIED",quote="已知的线索只有渡口的钟声")

    def test_write_only_phase_cannot_stage_or_approve(self):
        self.stage()
        self.write()
        with self.assertRaises(Exception):
            self.stage(ident="lesson-02")
        with self.assertRaises(Exception):
            self.approve()

    def test_old_frozen_receipt_cannot_be_reused_if_source_is_tampered(self):
        self.stage()
        self.approve()
        self.write()
        frozen=self.decide()
        self.db.conn.execute(
            "UPDATE source_spans SET source_sha256=? "
            "WHERE work_id='synthetic_work'",("f"*64,))
        self.db.conn.commit()
        # Historical readback is valid; authorization for a new generation
        # must recheck the actual source and fail closed.
        self.assertEqual(self.bridge.read_decision(
            project_id="project01",attempt_id="attempt01")
            ["decision_sha256"],frozen["decision_sha256"])
        with self.assertRaisesRegex(ValueError,"SOURCE"):
            self.decide()

    def test_accept_candidate_refuses_missing_or_edited_frozen_receipt(self):
        from unittest.mock import patch as mocked
        from writerforge.verified_flow import save_candidate, accept_candidate
        self.stage()
        self.approve()
        self.write()
        flow=VerifiedWritingFlow(self.db,self.runtime,"project01",
                                 experience_review_key=KEY)
        fake=[{"entry_id":1,"work_id":"synthetic_work",
               "location":[1,1,1],"function":"narration",
               "effect":"unverified"}]
        with mocked.object(flow.xuehai,"query",return_value=fake):
            packet=flow.prepare("scene01","synthetic investigation",
                experience_attempt_id="attempt01",
                scene_signals={"limited_knowledge":True,
                               "omniscient":False})
        saved=save_candidate(packet,"少年看见前路犹豫。","synthetic-model",
                             Path(self.temp.name)/"candidate")
        manifest=Path(saved["manifest"])
        original=json.loads(manifest.read_text(encoding="utf-8"))
        forged=dict(original)
        forged["experience_decision"]=dict(original["experience_decision"],
                                          decision_sha256="a"*64)
        def accept():
            return accept_candidate(
                self.db,self.runtime,project_id="project01",
                manifest_path=manifest,commit_id="commit01",
                explicitly_approved=True)
        with mocked.dict("os.environ",{
                "WRITERFORGE_EXPERIENCE_REVIEW_VERIFY_KEY_HEX":KEY.hex()}):
            manifest.write_text(json.dumps(forged),encoding="utf-8")
            with self.assertRaisesRegex(WritingExecutionError,"EXPERIENCE"):
                accept()
            forged["experience_decision"]=None
            manifest.write_text(json.dumps(forged),encoding="utf-8")
            with self.assertRaisesRegex(WritingExecutionError,"EXPERIENCE"):
                accept()
        self.assertIsNone(self.db.conn.execute(
            "SELECT 1 FROM story_commit_receipts "
            "WHERE project_id='project01' AND commit_id='commit01'"
        ).fetchone())

    def test_actual_verified_writing_prepare_includes_frozen_policy(self):
        # Test production prep path without HTTP, novel text or R2.
        self.stage()
        self.approve()
        self.write()
        flow=VerifiedWritingFlow(self.db,self.runtime,"project01",
                                 experience_review_key=KEY)
        fake=[{"entry_id":1,"work_id":"synthetic_work",
               "location":[1,1,1],"function":"narration","effect":"unverified"}]
        with patch.object(flow.xuehai,"query",return_value=fake):
            with self.assertRaisesRegex(WritingExecutionError,"EXPERIENCE_DECISION_REQUIRED"):
                flow.prepare("scene01","synthetic investigation")
            packet=flow.prepare(
                "scene01","synthetic investigation",
                experience_attempt_id="attempt01",
                scene_signals={"limited_knowledge":True,
                               "omniscient":False})
            self.assertIn("已掌握",packet.prompt)
            self.assertIn("decision_sha256",packet.experience_decision_receipt)
            self.assertEqual(packet.manifest()["experience_decision"]
                             ["decision_sha256"],
                             packet.experience_decision_receipt["decision_sha256"])
            other=flow.prepare(
                "scene01","synthetic investigation",
                experience_attempt_id="attempt02",
                scene_signals={"limited_knowledge":False,
                               "omniscient":False})
            self.assertNotIn("已掌握",other.prompt)
            self.assertNotEqual(packet.prompt_sha256,other.prompt_sha256)
            self.assertNotIn(self.source,packet.prompt)


class V61PromotionBoundaryTests(unittest.TestCase):
    def make(self):
        reg=SkillRegistry()
        reg.register(CapabilityContract("dialogue_craft",1,
                                        "synthetic initial skill"))
        engine=EvolutionEngine(registry=reg,promotion_verifier_key=PROMOTION_KEY)
        cand=UpgradeCandidate(
            skill="dialogue_craft",new_level=2,
            capability_statement="synthetic improvement not independently proven",
            evidence_id="external-report-01",
            evidence=PromotionEvidence(
                capability_statement="synthetic bounded test",
                heldout_success=.9,transfer_success=.82,
                regression_success=.99,judge_stability=.95,
                repeated_failure_reduction=.4,runtime_regression=.01,
                human_anchor_count=1),requires_human_anchor=False)
        return reg,engine,cand

    def test_no_attestation_or_faked_metrics_cannot_promote(self):
        reg,engine,cand=self.make()
        with self.assertRaisesRegex(PermissionError,"ATTESTATION"):
            engine.apply_upgrade(cand,policy="gated_auto")
        with self.assertRaisesRegex(PermissionError,"ATTESTATION"):
            engine.apply_upgrade(cand,policy="manual",approved=True)
        self.assertEqual(reg.get(cand.skill).level,1)

    def test_valid_external_signature_needs_explicit_manual_authorization(self):
        reg,engine,cand=self.make()
        payload=engine.promotion_attestation_payload(
            cand,reviewer_id="external01",review_id="independent01")
        signature=hmac.new(PROMOTION_KEY,canon(payload).encode("utf-8"),
                           "sha256").hexdigest()
        receipt={"reviewer_id":"external01","review_id":"independent01",
                 "signature":signature}
        with self.assertRaisesRegex(PermissionError,"MANUAL"):
            engine.apply_upgrade(cand,policy="gated_auto",attestation=receipt)
        with self.assertRaisesRegex(PermissionError,"APPROVAL"):
            engine.apply_upgrade(cand,policy="manual",attestation=receipt)
        self.assertEqual(reg.get(cand.skill).level,1)
        engine.apply_upgrade(cand,policy="manual",approved=True,
                             attestation=receipt)
        self.assertEqual(reg.get(cand.skill).level,2)

    def test_signed_receipt_cannot_be_reused_for_modified_scores(self):
        reg,engine,cand=self.make()
        payload=engine.promotion_attestation_payload(
            cand,reviewer_id="external01",review_id="independent01")
        signature=hmac.new(PROMOTION_KEY,canon(payload).encode("utf-8"),
                           "sha256").hexdigest()
        receipt={"reviewer_id":"external01","review_id":"independent01",
                 "signature":signature}
        from dataclasses import replace
        modified=replace(cand,evidence=replace(cand.evidence,heldout_success=1.0))
        with self.assertRaisesRegex(PermissionError,"ATTESTATION"):
            engine.apply_upgrade(modified,policy="manual",approved=True,
                                 attestation=receipt)
        self.assertEqual(reg.get(cand.skill).level,1)


if __name__=="__main__":
    unittest.main()
