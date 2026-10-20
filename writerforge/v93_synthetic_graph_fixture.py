"""Synthetic-only V93 lifetime graph fixture with actual WF SQLite APIs.

Never use real novel content, user names, model judgments, or actual private
disclosure signing keys. Both databases are disposable isolated files.
The test review secret is intentionally public, making the signatures useful
only for software integration tests, NOT human literature certification.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import hmac

from .db import WriterForgeDB
from .fact_journal import FactJournal
from .experience_decision import (
    ExperienceDecisionBridge, canonical as decision_canonical,
)
from .runtime import RuntimeEngine
from .v91_lifelong_checkpoint import create_checkpoint
from .v93_synthetic_graph_cloud_checkpoint import (
    FIXTURE_ID,FIXTURE_WORK_URI,FIXTURE_QUOTE,
)

SYNTHETIC_SIGNING_KEY=b"V93-PUBLIC-TEST-ONLY-NEVER-TRUST-AS-REVIEWER-KEY"
V82_ANCHORS={
    "batch":"d46ffec05927dfba3f2819089e76e79f720db2a2f3f6793b56965ac6413c177f",
    "journal":"3da56cc46115548c5198a65cb6124e3c03d9bdfdb1f0460950177735a99d1cb2",
    "experience":"ddbf86e87e3bf44900b4e5e4d8ffc2de99c9ed5d3c5aec98a69bfd8eb7cf2fe7",
}
PROJECT="v93_project"
EXPERIENCE="lesson_v93"
SCENE="scene_v93"
OLD_ATTEMPT="attempt_before_revoke"
NEW_ATTEMPT="attempt_after_revoke"
KNOWN_FACT="bridge_light"
CHECKPOINT_ID="v93_synthetic_cold"


def h(text):
    return sha256(text.encode("utf8")).hexdigest()


def signature(payload):
    return hmac.new(SYNTHETIC_SIGNING_KEY,
                    decision_canonical(payload).encode("utf8"),
                    "sha256").hexdigest()


def _choose(bridge,attempt):
    return bridge.decide(
        project_id=PROJECT,scene_id=SCENE,attempt_id=attempt,
        goal="仅合成场景：核查角色已知信息，不能当文学成功",
        scene_signals={"limited_knowledge":True,"omniscient":False})


def create_synthetic_checkpoint(parent):
    parent=Path(parent)
    parent.mkdir(parents=True,exist_ok=True)
    writer=WriterForgeDB(parent/"synthetic-writer.sqlite3")
    facts=FactJournal(parent/"synthetic-facts.sqlite3")
    runtime=RuntimeEngine()
    try:
        runtime.enter_learn()
        db=writer.conn
        snapshot=db.execute(
            "INSERT INTO snapshots(status,layout,note) "
            "VALUES('published','full','V93合成数据—不是真人文学认知')"
        ).lastrowid
        db.execute(
            "INSERT INTO studied_works(work_id,title,source_uri,"
            "source_sha256,chapter_count) VALUES(?,?,?,?,?)",
            (FIXTURE_ID,"V93纯合成示例",FIXTURE_WORK_URI,
             h("synthetic-file-v93"),3))
        db.execute(
            "INSERT INTO studied_chapters(work_id,chapter,chapter_sha256,"
            "heading,source_spans,retrieval_entries,snapshot_id)"
            " VALUES(?,?,?,?,?,?,?)",
            (FIXTURE_ID,3,h("fake-chapter"),"第3章（测试）",1,1,snapshot))
        locator={
            "work_id":FIXTURE_ID,"chapter":3,
            "paragraph":1,"sentence":1,
            "source_sha256":h(FIXTURE_QUOTE),
        }
        db.execute(
            "INSERT INTO source_spans(work_id,chapter,paragraph,sentence,"
            "excerpt,source_sha256,tracks_json,craft_json)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (FIXTURE_ID,3,1,1,FIXTURE_QUOTE,h(FIXTURE_QUOTE),"{}","{}"))
        db.commit()

        bridge=ExperienceDecisionBridge(
            writer,runtime,reviewer_key=SYNTHETIC_SIGNING_KEY)
        bridge.stage_candidate(
            project_id=PROJECT,experience_id=EXPERIENCE,
            snapshot_id=snapshot,source_ref=locator,
            required_tags=["limited_knowledge"],
            forbidden_tags=["omniscient"],
            operation_code="CHECK_KNOWLEDGE")
        approval=bridge.approval_payload(
            project_id=PROJECT,experience_id=EXPERIENCE,
            reviewer_id="synthetic_reviewer",
            review_id="synthetic_approval")
        bridge.approve_candidate(
            project_id=PROJECT,experience_id=EXPERIENCE,
            reviewer_id="synthetic_reviewer",
            review_id="synthetic_approval",
            signature=signature(approval))

        for scene,num in (("v93_chapter01",1),("v93_chapter03",3)):
            facts.register_scene(story_id=FIXTURE_ID,scene_id=scene,
                                 chapter_index=num)
            facts.bind_subject(scene_id=scene,scope="ACTOR",
                               subject_id="hero",canonical_id="v93_hero")
        facts.append({
            "event_id":"fixture_event","scene_id":"v93_chapter01",
            "actor_id":"hero","fact_id":KNOWN_FACT,
            "tick":2,"state":"KNOWN","role":"OBSERVE",
            "evidence_sha256":h("fake-observation")})
        facts.append_temporal_claim({
            "claim_id":"fixture_claim","scene_id":"v93_chapter01",
            "subject_scope":"ACTOR","subject_id":"hero",
            "fact_id":KNOWN_FACT,"story_from":2,
            "story_until":None,"knowledge_state":"KNOWN",
            "evidence_event_id":"fixture_event",
            "supersedes_id":None})
        ledger=facts.ledger_head()
        runtime.exit()
        runtime.enter_write(snapshot)
        before=_choose(bridge,OLD_ATTEMPT)
        if len(before["decisions"])!=1 or (
            before["decisions"][0]["decision"]!="SELECT"):
            raise ValueError("WF93_SYNTHETIC_PRE_REVOKE_SELECT_FAILED")
        prior_sha=before["decision_sha256"]
        runtime.exit()
        runtime.enter_learn()
        rev=bridge.revocation_payload(
            project_id=PROJECT,experience_id=EXPERIENCE,
            reviewer_id="synthetic_reviewer",review_id="synthetic_revoked",
            reason_code="SOURCE_REVIEW_DISPUTED")
        bridge.revoke_candidate(
            project_id=PROJECT,experience_id=EXPERIENCE,
            reviewer_id="synthetic_reviewer",review_id="synthetic_revoked",
            reason_code="SOURCE_REVIEW_DISPUTED",
            signature=signature(rev))
        runtime.exit()
        runtime.enter_write(snapshot)
        after=_choose(bridge,NEW_ATTEMPT)
        if len(after["decisions"])!=1 or (
            after["decisions"][0]["decision"]!="SKIP" or
            after["decisions"][0]["reason_code"]!="EXPERIENCE_REVOKED"
            or after["prompt_guidance"]!=""):
            raise ValueError("WF93_SYNTHETIC_POST_REVOKE_SKIP_FAILED")
        runtime.exit()
        root=parent/"synthetic-checkpoints"
        checkpoint=create_checkpoint(
            root=root,checkpoint_id=CHECKPOINT_ID,
            writer=writer,facts=facts,runtime=runtime,
            r2_v82_anchors=V82_ANCHORS)
        return {
            "checkpoint_root":root,
            "checkpoint_id":CHECKPOINT_ID,
            "checkpoint_manifest_sha256":checkpoint["manifest_sha256"],
            "fixture_snapshot_id":snapshot,
            "source_event_global_ledger_head":ledger,
            "prior_select_decision_sha256":prior_sha,
            "revoked_skip_decision_sha256":after["decision_sha256"],
            "synthetic_only":True,
            "review_signatures_are_public_test_fixtures":True,
        }
    finally:
        writer.close()
        facts.close()


def replay_restored_fixture(writer_db,fact_db):
    """Open original restored SQLite data, check old receipt + fresh SKIP."""
    writer=WriterForgeDB(writer_db)
    facts=FactJournal(fact_db)
    try:
        row=writer.conn.execute(
            "SELECT id FROM snapshots WHERE status='published'").fetchone()
        if row is None:
            raise ValueError("WF93_RESTORED_PUBLISHED_SNAPSHOT_MISSING")
        snapshot=row[0]
        runtime=RuntimeEngine()
        runtime.enter_write(snapshot)
        bridge=ExperienceDecisionBridge(
            writer,runtime,reviewer_key=SYNTHETIC_SIGNING_KEY)
        historical=bridge.read_decision(
            project_id=PROJECT,attempt_id=OLD_ATTEMPT)
        if (len(historical["decisions"])!=1 or
            historical["decisions"][0]["decision"]!="SELECT"):
            raise ValueError("WF93_RESTORED_PRIOR_EXPERIENCE_MISSING")
        current=bridge.read_decision(
            project_id=PROJECT,attempt_id=NEW_ATTEMPT)
        if (len(current["decisions"])!=1 or
            current["decisions"][0]["decision"]!="SKIP" or
            current["prompt_guidance"]!=""):
            raise ValueError("WF93_RESTORED_REVOKED_DECISION_NOT_SKIPPED")
        try:
            bridge.validate_live_decision(
                project_id=PROJECT,attempt_id=OLD_ATTEMPT)
        except Exception as error:
            if "REVOKED" not in str(error):
                raise
        else:
            raise ValueError("WF93_REVOKED_HISTORICAL_SELECT_REENABLED")
        outcome=_choose(bridge,"fresh_after_cloud_restore")
        if (len(outcome["decisions"])!=1 or
            outcome["decisions"][0]["decision"]!="SKIP" or
            outcome["decisions"][0]["reason_code"]!="EXPERIENCE_REVOKED"
            or outcome["prompt_guidance"]!=""):
            raise ValueError("WF93_COLD_RESTART_BEHAVIOR_REGRESSION")
        clock=facts.ledger_head()
        state=facts.temporal_view(
            scene="v93_chapter03",story_id=FIXTURE_ID,
            scope="ACTOR",subject="hero",fact=KNOWN_FACT,
            story_tick=3,as_of_ledger_seq=clock)
        unknown=facts.temporal_view(
            scene="v93_chapter03",story_id=FIXTURE_ID,
            scope="ACTOR",subject="hero",fact="unknown_future",
            story_tick=3,as_of_ledger_seq=clock)
        if state["state"]!="KNOWN" or unknown["state"]!="UNRECORDED":
            raise ValueError("WF93_ACTOR_TIME_KNOWLEDGE_CHANGED")
        return {
            "synthetic_prior_decision_sha256":historical[
                "decision_sha256"],
            "synthetic_revoked_decision_sha256":current[
                "decision_sha256"],
            "new_post_recovery_choice":"SKIP",
            "new_choice_reason":"EXPERIENCE_REVOKED",
            "known_state":"KNOWN",
            "unrecorded_state":"UNRECORDED",
            "ledger_head":clock,
            "prior_revoked_select_reuse_refused":True,
            "literary_semantics_independently_verified":False,
            "fixture_review_signature_is_not_real_literary_authority":True,
        }
    finally:
        writer.close()
        facts.close()
