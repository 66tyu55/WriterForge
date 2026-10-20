"""V86 end-to-end synthetic WF LEARN/REVIEW/WRITE regression.

Uses REAL WriterForgeDB and FactJournal SQLite, an in-memory sealed R2-shaped
PASS-A journal, and off-model synthetic reviewer/approval signatures.
No model API, real R2, private books or real literary judges participate.
"""
from __future__ import annotations
import hmac
import json
import sqlite3
import unittest
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from writerforge.db import WriterForgeDB
from writerforge.runtime import RuntimeEngine,RuntimeErrorState
from writerforge.fact_journal import FactJournal
from writerforge.experience_decision import (
    ExperienceDecisionBridge,OPERATION_GUIDANCE,
    canonical as exp_canonical
)
from writerforge.r2_learn_journal import (
    identity,event_doc,canonical as event_canonical
)
from writerforge.v85_literary_evidence_gate import LiteraryEvidenceGate
from writerforge.v85_pass_a_bridge import V85SealedLearningBridge
from writerforge.v86_controlled_review_loop import V86ControlledReviewLoop
from writerforge.v86_review_contract import (
    V86ReviewError,canonical as review_canonical,
)

REVIEW_KEY=b"synthetic-v86-reviewer-only-key-32bytes-dont-share"
APPROVAL_KEY=b"synthetic-v86-experiment-approval-key-32bytes"
ORIGINAL=("暮色压住旧桥，少年看见守桥人悄悄熄灭了灯，却没有告诉同行的妹妹。",
          "桥外远远传来钟声，少年收起渡河的木牌，决定今晚先等待，不贸然走近。")
SOURCE_KEY="writerforge/v1/private-reading/仙侠/fictional/novel.txt"

def h(s):
    return sha256(s.encode("utf-8")).hexdigest()

def anchor(unit,phrase):
    start=ORIGINAL[unit-1].index(phrase)
    return dict(unit=unit,start=start,end=start+len(phrase),quote=phrase)

QUOTE="守桥人悄悄熄灭了灯"
REACTION=dict(attention=3,curiosity=2,confusion=1,tension=2,
              urge_to_continue=3,question="",prediction="",what_changed="")

class SyntheticSealedR2:
    read_only=True
    writer=None
    def __init__(self,ident):
        self.events={}
        previous=None
        for number,unit in enumerate(ORIGINAL,1):
            doc=event_doc(stage="first_read",ident=ident,unit=number,
                source_unit_sha256=h(unit),previous_event_sha256=previous,
                future_source_seen=False,reaction=REACTION)
            previous=sha256(event_canonical(doc)).hexdigest()
            self.events[("first_read",number)]={
                "event_sha256":previous,"doc":doc}
        seal=event_doc(stage="seal",ident=ident,units_read=len(ORIGINAL),
                       last_first_read_sha256=previous,
                       future_source_seen=False)
        self.events[("seal",None)]={
            "event_sha256":sha256(event_canonical(seal)).hexdigest(),
            "doc":seal}
    def fetch_event(self,*,ident,stage,unit=None):
        return self.events.get((stage,unit))
    def _get_content(self,*args,**kwargs):
        raise AssertionError("no real R2 content accessed")

class V86LiteraryLoopTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        folder=Path(self.temp.name)
        self.fact=FactJournal(folder/"fact.sqlite3")
        self.db=WriterForgeDB(folder/"writer.sqlite3")
        self.rt=RuntimeEngine()
        self.rt.enter_learn()
        self.snapshot=self.db.conn.execute(
            "INSERT INTO snapshots(status,layout,note)"
            " VALUES('published','full','v86 synthetic')").lastrowid
        self.source_sha=h("synthetic-frozen-novel-version")
        self.book="novelA"
        self.db.conn.execute(
            "INSERT INTO studied_works(work_id,title,source_uri,"
            "source_sha256,chapter_count) VALUES(?,?,?,?,?)",
            (self.book,"Synthetic fixture","test://v86",
             self.source_sha,3))
        self.chapter_sha=h("".join(ORIGINAL))
        self.db.conn.execute(
            "INSERT INTO studied_chapters(work_id,chapter,chapter_sha256,"
            "heading,source_spans,retrieval_entries,snapshot_id)"
            " VALUES(?,?,?,?,?,?,?)",
            (self.book,3,self.chapter_sha,"Chapter 3",1,1,self.snapshot))
        self.locator=dict(work_id=self.book,chapter=3,paragraph=1,
                          sentence=1,source_sha256=h(QUOTE))
        self.db.conn.execute(
            "INSERT INTO source_spans(work_id,chapter,paragraph,sentence,"
            "excerpt,source_sha256,tracks_json,craft_json)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (self.book,3,1,1,QUOTE,h(QUOTE),"{}","{}"))
        self.db.conn.commit()
        for scene,num in (("chapter01",1),("chapter03",3)):
            self.fact.register_scene(story_id=self.book,
                                     scene_id=scene,chapter_index=num)
            self.fact.bind_subject(scene_id=scene,scope="ACTOR",
                                   subject_id="hero",canonical_id="heroA")
        self.fact.append(dict(event_id="seen-light",scene_id="chapter01",
                              actor_id="hero",fact_id="bridge_light",tick=2,
                              state="KNOWN",role="OBSERVE",
                              evidence_sha256=h("fictional-observation")))
        self.fact.append_temporal_claim(dict(
            claim_id="bridge-known",scene_id="chapter01",
            subject_scope="ACTOR",subject_id="hero",
            fact_id="bridge_light",story_from=2,story_until=None,
            knowledge_state="KNOWN",evidence_event_id="seen-light",
            supersedes_id=None))
        self.ident=identity(source_key=SOURCE_KEY,source_sha=self.source_sha,
                            chapter=3,chapter_body_sha=self.chapter_sha)
        self.sealed_journal=SyntheticSealedR2(self.ident)
        self.gate=LiteraryEvidenceGate(
            self.fact,story_id=self.book,scene_id="chapter03",
            source_sha256=self.source_sha,
            ledger_seq=self.fact.ledger_head())
        self.sealed=V85SealedLearningBridge(
            self.sealed_journal,self.gate,runtime=self.rt)
        self.claim=dict(
            claim_id="claim01",source_sha256=self.source_sha,chapter=3,
            kind="CAUSAL",actor_id="hero",fact_id="bridge_light",
            story_tick=3,claimed_knowledge_state="KNOWN",
            observation=anchor(1,QUOTE),
            consequence=anchor(2,"少年收起渡河的木牌"),
            hypothesis="少年可能因看到守桥人的异常行为而修改过桥决定。",
            alternative="少年也可能单纯因为夜色太深与钟声突然响起才选择等待。",
            falsifier="如果后续证据证明木牌已经失效，当前因果解释就应被推翻。",
            uncertainty="此时无法独立确认哪一个具体原因最终驱动少年的决定。")
        self.receipt=self.sealed.audit_sealed_chapter(
            ident=self.ident,windows=ORIGINAL,
            proposals=[self.claim])
        self.experience=ExperienceDecisionBridge(
            self.db,self.rt,reviewer_key=APPROVAL_KEY,
            literary_review_key=REVIEW_KEY)
        self.loop=V86ControlledReviewLoop(self.experience,self.sealed)

    def tearDown(self):
        self.db.close()
        self.fact.close()
        self.temp.cleanup()

    def learn(self):
        self.rt.exit()
        self.rt.enter_learn()

    def write(self):
        self.rt.exit()
        self.rt.enter_write(self.snapshot)

    def stage(self,name="lesson01",supersedes=None,
              operation="CHECK_KNOWLEDGE",receipt=None,quote=QUOTE,
              claim_id="claim01"):
        return self.loop.stage_from_sealed(
            project_id="project01",experience_id=name,
            snapshot_id=self.snapshot,source_ref=self.locator,
            source_quote=quote,receipt=receipt or self.receipt,
            claim_id=claim_id,producer_id="wf_student",
            operation_code=operation,required_tags=["limited_knowledge"],
            forbidden_tags=["omniscient"],
            supersedes_experience_id=supersedes)

    def approve(self,name="lesson01",review_id="approve01"):
        p=self.experience.approval_payload(
            project_id="project01",experience_id=name,
            reviewer_id="authority01",review_id=review_id)
        sig=hmac.new(APPROVAL_KEY,exp_canonical(p).encode(),
                     "sha256").hexdigest()
        return self.experience.approve_candidate(
            project_id="project01",experience_id=name,
            reviewer_id="authority01",review_id=review_id,
            signature=sig)

    def review(self,name="lesson01",verdict="SUPPORTED_FOR_EXPERIMENT",
               reason="SOURCE_SUPPORTS_TRIAL",review_id="semantic01"):
        p=self.loop.review_payload(
            project_id="project01",experience_id=name,
            reviewer_id="external_fixture",review_id=review_id,
            verdict=verdict,reason_code=reason)
        sig=hmac.new(REVIEW_KEY,review_canonical(p).encode(),
                     "sha256").hexdigest()
        return self.loop.append_external_review(payload=p,signature=sig)

    def choose(self,attempt):
        return self.experience.decide(
            project_id="project01",scene_id="scene01",
            attempt_id=attempt,goal="fictional controlled experiment",
            scene_signals={"limited_knowledge":True,"omniscient":False})

    def test_linked_review_approval_negative_revision_changes_behavior(self):
        self.stage()
        self.approve()
        self.write()
        no_review=self.choose("attempt01")
        self.assertEqual(no_review["decisions"][0]["decision"],"UNCERTAIN")
        self.assertEqual(no_review["decisions"][0]["reason_code"],
                         "LITERARY_REVIEW_REQUIRED")
        self.assertEqual(no_review["prompt_guidance"],"")
        self.learn()
        self.review()
        self.write()
        before=self.choose("attempt02")
        self.assertEqual(before["decisions"][0]["decision"],"SELECT")
        self.assertIn(OPERATION_GUIDANCE["CHECK_KNOWLEDGE"],
                      before["prompt_guidance"])
        self.learn()
        self.review(verdict="NEGATIVE",reason="UNSUPPORTED_CAUSAL_CHAIN",
                    review_id="semantic02")
        self.write()
        after=self.choose("attempt03")
        self.assertEqual(after["decisions"][0]["decision"],"SKIP")
        self.assertEqual(after["decisions"][0]["reason_code"],
                         "INDEPENDENT_NEGATIVE_REVIEW")
        self.assertEqual(after["prompt_guidance"],"")
        with self.assertRaisesRegex(ValueError,"(REVIEW_STALE|QUARANTINED)"):
            self.experience.validate_live_decision(
                project_id="project01",attempt_id="attempt02")
        self.assertEqual(self.experience.read_decision(
            project_id="project01",attempt_id="attempt02"
        )["decision_sha256"],before["decision_sha256"])
        self.learn()
        with self.assertRaisesRegex(V86ReviewError,
                                    "REVISION_REQUIRES_NEW_SEALED_CLAIM"):
            self.stage("revision_same_source",supersedes="lesson01",
                       operation="TRACE_CONSEQUENCE")
        revised_claim=dict(self.claim,
                           claim_id="revision_claim01",
                           hypothesis="少年改变过桥决定也可能来自钟声与木牌异常的共同影响。",
                           falsifier="如果后续证明少年从未听见钟声，这个新假说应立即撤销。")
        revised_receipt=self.sealed.audit_sealed_chapter(
            ident=self.ident,windows=ORIGINAL,
            proposals=[revised_claim])
        revision=self.stage(
            "revision01",supersedes="lesson01",
            operation="TRACE_CONSEQUENCE",
            receipt=revised_receipt,claim_id="revision_claim01")
        self.assertFalse(revision["experiment_approved"])
        self.write()
        still_blocked=self.choose("attempt04")
        self.assertEqual([i["decision"] for i in
                          still_blocked["decisions"]],["SKIP"])
        self.learn()
        self.review(name="revision01",review_id="semantic03")
        self.approve("revision01","approve02")
        self.write()
        renewed=self.choose("attempt05")
        states={x["experience_id"]:x["decision"]
                for x in renewed["decisions"]}
        self.assertEqual(states,{"lesson01":"SKIP",
                                 "revision01":"SELECT"})
        self.assertIn(OPERATION_GUIDANCE["TRACE_CONSEQUENCE"],
                      renewed["prompt_guidance"])
        self.assertNotIn(OPERATION_GUIDANCE["CHECK_KNOWLEDGE"],
                         renewed["prompt_guidance"])
        self.assertFalse(renewed["literary_semantics_verified"])
        self.assertFalse(renewed["auto_skill_promotion"])

    def test_fake_semantic_reviewer_and_source_crosswalk_rejected(self):
        self.stage()
        payload=self.loop.review_payload(
            project_id="project01",experience_id="lesson01",
            reviewer_id="external_fixture",review_id="semantic01",
            verdict="SUPPORTED_FOR_EXPERIMENT",
            reason_code="SOURCE_SUPPORTS_TRIAL")
        with self.assertRaisesRegex(V86ReviewError,"SIGNATURE_INVALID"):
            self.loop.append_external_review(
                payload=payload,signature="0"*64)
        bad=dict(payload,reviewer_id="wf_student")
        with self.assertRaisesRegex(V86ReviewError,"REVIEWER_NOT_SEPARATE"):
            self.loop.append_external_review(payload=bad,signature="0"*64)
        with self.assertRaisesRegex(V86ReviewError,"SOURCE_QUOTE_NOT_BOUND"):
            self.stage("different01",quote="看见另外一条完全不同的线索")
        altered=dict(self.receipt,audit=dict(
            self.receipt["audit"],claims_count=200))
        with self.assertRaisesRegex(ValueError,"SESSION_NOT_VERIFIED"):
            self.stage("fake01",receipt=altered)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM experience_candidates"
        ).fetchone()[0],1)

    def test_review_is_append_only_tamper_checked_replay_safe(self):
        self.stage()
        first=self.review()
        self.assertFalse(first["replayed"])
        repeated=self.review()
        self.assertTrue(repeated["replayed"])
        self.db.conn.execute(
            "UPDATE experience_literary_reviews SET "
            "review_json='{}' WHERE review_id='semantic01'")
        self.db.conn.commit()
        with self.assertRaisesRegex(V86ReviewError,
                                    "REVIEW_RECORD_IMMUTABILITY"):
            self.loop.status(project_id="project01",
                             experience_id="lesson01")

    def test_untrusted_review_key_fails_closed_after_restart(self):
        self.stage()
        self.approve()
        self.write()
        disconnected=ExperienceDecisionBridge(
            self.db,self.rt,reviewer_key=APPROVAL_KEY)
        with self.assertRaisesRegex(V86ReviewError,"VERIFIER_UNAVAILABLE"):
            disconnected.decide(
                project_id="project01",scene_id="scene01",
                attempt_id="must_not_persist",goal="test",
                scene_signals={"limited_knowledge":True,"omniscient":False})
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM experience_decisions "
            "WHERE attempt_id='must_not_persist'").fetchone()[0],0)

    def test_v85_unknown_character_claim_never_staged(self):
        self.claim["fact_id"]="missing_fact"
        self.claim["claimed_knowledge_state"]="UNRECORDED"
        receipt=self.sealed.audit_sealed_chapter(
            ident=self.ident,windows=ORIGINAL,proposals=[self.claim])
        with self.assertRaisesRegex(V86ReviewError,"UNRESOLVED"):
            self.stage("unknown01",receipt=receipt)

if __name__=="__main__":
    unittest.main()
