"""V94 synthetic-only R2 write-ahead event commit and deterministic cold replay.

Append-only event CAS first; immutable commit manifest LAST. A cold Reader
rebuilds V93's real R2 synthetic SQLite checkpoint, replays each typed event
through EXISTING FactJournal/ExperienceDecision APIs, and checks every
expected outcome digest, current decision, known/disputed time snapshots and
recorded historical revocation.

This is a BOUNDED INTEGRATION PROOF, not live production LEARN:
- accepts only 7 frozen synthetic fixture operations and the V93 synthetic
  checkpoint, with exact static payloads; cannot ingest arbitrary model facts.
- approvals use a PUBLIC testing key, not trusted independent reviewers;
- no mutable latest pointer, writer lease or distributed transaction.
No story prose, model output, real user fact rows, or private signing key
is included in these CAS event receipts or reports.
"""
from __future__ import annotations
from contextlib import closing
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import re

from .db import WriterForgeDB
from .fact_journal import FactJournal
from .experience_decision import ExperienceDecisionBridge
from .runtime import RuntimeEngine
from .v93_synthetic_graph_cloud_checkpoint import cold_restore_from_cas
from .v93_synthetic_graph_fixture import (
    FIXTURE_ID,PROJECT,EXPERIENCE,SCENE,KNOWN_FACT,
    SYNTHETIC_SIGNING_KEY,signature,h,
)
from .v93_synthetic_graph_cloud_checkpoint import FIXTURE_QUOTE

FORMAT_EVENT="writerforge.synthetic-test-only.learn-event.v94"
FORMAT_COMMIT="writerforge.synthetic-test-only.commit.v94"
SCHEMA_VERSION=1
BASE_GRAPH_SHA="a42ada69d6d3b4d6ed90664f4b6c5607f5e0849ed1a4d178688b8d45f10b1d25"
V92_EXPERIENCE_CHAIN_SHA="bd905ae9e812fb5283f24ed7fec3bc35cf0febde7b6405476c455bba468f84db"
CHAIN_ID="v94_synthetic_learn_event_chain"
NEW_EXPERIENCE="lesson_v94"
MAX_EVENTS=7
MAX_EVENT_BYTES=4096
MAX_COMMIT_BYTES=12000
SHA=re.compile(r"[0-9a-f]{64}\Z")
META_FIELDS=frozenset((
    "format","schema_version","source_graph_manifest_sha256",
    "v92_experience_manifest_sha256","event_chain_id","seq",
    "previous_event_sha256","operation","outcome_sha256",
    "synthetic_only","original_work_authority_proven",
    "independent_literary_review_proven","eligible_to_direct_writing",
))
COMMIT_FIELDS=frozenset((
    "format","schema_version","event_chain_id",
    "source_graph_manifest_sha256","v92_experience_manifest_sha256",
    "event_refs","outcome_receipts_sha256","final_state_sha256",
    "committed_event_count","synthetic_only","all_model_calls_zero",
    "production_memory_written","original_literary_quality_proven",
    "schema_and_temporal_replay_checked_before_publish",
    "writer_eligible","old_v93_graph_unchanged",
))


class V94DurableEventError(ValueError):
    pass


def need(ok,code):
    if not ok:
        raise V94DurableEventError(code)


def is_sha(value):
    return isinstance(value,str) and SHA.fullmatch(value) is not None


def canonical(doc):
    return json.dumps(doc,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode("utf8")


def digest(raw):
    return sha256(raw).hexdigest()


def _parse(raw,limit):
    need(type(raw) is bytes and 0<len(raw)<=limit,
         "WF94_JSON_BYTE_BOUND")
    try:
        text=raw.decode("utf8","strict")
        need("\ufffd" not in text,"WF94_REPLACEMENT_CHAR_FORBIDDEN")
        def unique(pairs):
            data={}
            for k,v in pairs:
                if k in data:
                    raise ValueError("duplicate JSON field")
                data[k]=v
            return data
        data=json.loads(
            text,object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ValueError("non-finite JSON")))
        canonical(data)
    except (UnicodeError,ValueError,TypeError,OverflowError):
        raise V94DurableEventError("WF94_STRICT_JSON_DECODE_FAILED") from None
    need(type(data) is dict,"WF94_JSON_MUST_BE_OBJECT")
    return data


def _operations():
    """Fixed synthetic instructions, no caller-provided model assertions."""
    return [
      {"kind":"STAGE_TEST_CANDIDATE","id":"v94_stage_policy"},
      {"kind":"APPROVE_TEST_CANDIDATE","id":"v94_approve_policy"},
      {"kind":"BEFORE_REVOKE_DECISION","id":"v94_pre_revoke_select"},
      {"kind":"REVOKE_TEST_CANDIDATE","id":"v94_revoke_policy"},
      {"kind":"AFTER_REVOKE_DECISION","id":"v94_post_revoke_skip"},
      {"kind":"APPEND_DISPUTED_EVIDENCE","id":"v94_conflict_event"},
      {"kind":"SUPERSEDE_CHARACTER_KNOWLEDGE","id":"v94_disputed_claim"},
    ]


def _apply(kind,writer,facts,runtime,bridge):
    row=writer.conn.execute(
        "SELECT id FROM snapshots WHERE status='published'").fetchone()
    need(row is not None and type(row[0]) is int,
         "WF94_SYNTHETIC_SNAPSHOT_NOT_FOUND")
    snapshot=row[0]
    if kind=="STAGE_TEST_CANDIDATE":
        runtime.enter_learn()
        loc={"work_id":FIXTURE_ID,"chapter":3,
             "paragraph":1,"sentence":1,
             "source_sha256":h(FIXTURE_QUOTE)}
        result=bridge.stage_candidate(
            project_id=PROJECT,experience_id=NEW_EXPERIENCE,
            snapshot_id=snapshot,source_ref=loc,
            required_tags=["limited_knowledge"],
            forbidden_tags=["omniscient"],
            operation_code="TRACE_CONSEQUENCE")
        runtime.exit()
        return {"code":kind,
                "candidate_sha256":result["candidate_sha256"],
                "writer_literary_truth_proven":False}
    if kind=="APPROVE_TEST_CANDIDATE":
        runtime.enter_learn()
        payload=bridge.approval_payload(
            project_id=PROJECT,experience_id=NEW_EXPERIENCE,
            reviewer_id="synthetic_reviewer",
            review_id="v94_fixture_approval")
        result=bridge.approve_candidate(
            project_id=PROJECT,experience_id=NEW_EXPERIENCE,
            reviewer_id="synthetic_reviewer",
            review_id="v94_fixture_approval",
            signature=signature(payload))
        runtime.exit()
        return {"code":kind,
                "approval_sha256":result["approval_sha256"],
                "external_reviewer_independently_verified":False}
    if kind in ("BEFORE_REVOKE_DECISION","AFTER_REVOKE_DECISION"):
        runtime.enter_write(snapshot)
        before=kind=="BEFORE_REVOKE_DECISION"
        record=bridge.decide(
            project_id=PROJECT,scene_id=SCENE,
            attempt_id="v94_before_revoke" if before else
                       "v94_after_revoke",
            goal="仅合成场景验证可重建的实验经验撤销",
            scene_signals={"limited_knowledge":True,
                           "omniscient":False})
        runtime.exit()
        outcome={x["experience_id"]:x["decision"]
                 for x in record["decisions"]}
        need(outcome.get(EXPERIENCE)=="SKIP" and
             outcome.get(NEW_EXPERIENCE)==(
                 "SELECT" if before else "SKIP") and
             (bool(record["prompt_guidance"]) if before
              else record["prompt_guidance"]==""),
             "WF94_SYNTHETIC_REVOKE_DID_NOT_CHANGE_WRITE_CHOICE")
        return {"code":kind,"decision_sha256":record["decision_sha256"],
                "previous_revoked_policy_still_skipped":True,
                "new_policy_decision":outcome[NEW_EXPERIENCE],
                "original_prose_stored":False}
    if kind=="REVOKE_TEST_CANDIDATE":
        runtime.enter_learn()
        payload=bridge.revocation_payload(
            project_id=PROJECT,experience_id=NEW_EXPERIENCE,
            reviewer_id="synthetic_reviewer",
            review_id="v94_fixture_revocation",
            reason_code="SOURCE_REVIEW_DISPUTED")
        result=bridge.revoke_candidate(
            project_id=PROJECT,experience_id=NEW_EXPERIENCE,
            reviewer_id="synthetic_reviewer",
            review_id="v94_fixture_revocation",
            reason_code="SOURCE_REVIEW_DISPUTED",
            signature=signature(payload))
        runtime.exit()
        return {"code":kind,
                "revocation_sha256":result["revocation_sha256"],
                "signature_from_public_synthetic_fixture":True}
    if kind=="APPEND_DISPUTED_EVIDENCE":
        record={
            "event_id":"v94_conflict_event",
            "scene_id":"v93_chapter01",
            "actor_id":"hero",
            "fact_id":KNOWN_FACT,
            "tick":2,"state":"DISPUTED","role":"OBSERVE",
            "evidence_sha256":h("v94-test-only-later-disputed-evidence"),
        }
        result=facts.append(record)
        return {"code":kind,
                "event_sha256":result["event_sha256"],
                "literary_truth_verified":False}
    if kind=="SUPERSEDE_CHARACTER_KNOWLEDGE":
        claim={
            "claim_id":"v94_disputed_claim",
            "scene_id":"v93_chapter01",
            "subject_scope":"ACTOR",
            "subject_id":"hero",
            "fact_id":KNOWN_FACT,
            "story_from":2,"story_until":None,
            "knowledge_state":"DISPUTED",
            "evidence_event_id":"v94_conflict_event",
            "supersedes_id":"fixture_claim",
        }
        result=facts.append_temporal_claim(claim)
        return {"code":kind,
                "claim_sha256":result["claim_sha256"],
                "literary_truth_verified":False}
    raise V94DurableEventError("WF94_UNRECOGNIZED_TEST_OPERATION")


def _verify_final(writer,facts,bridge):
    head=facts.ledger_head()
    # The original V93 snapshot had six ledger operations. Latest view
    # may become DISPUTED, but the older as-of-ledger snapshot stays KNOWN.
    earlier=facts.temporal_view(
        scene="v93_chapter03",story_id=FIXTURE_ID,
        scope="ACTOR",subject="hero",fact=KNOWN_FACT,
        story_tick=3,as_of_ledger_seq=6)
    later=facts.temporal_view(
        scene="v93_chapter03",story_id=FIXTURE_ID,
        scope="ACTOR",subject="hero",fact=KNOWN_FACT,
        story_tick=3,as_of_ledger_seq=head)
    unknown=facts.temporal_view(
        scene="v93_chapter03",story_id=FIXTURE_ID,
        scope="ACTOR",subject="hero",fact="unobserved_future",
        story_tick=3,as_of_ledger_seq=head)
    need(earlier["state"]=="KNOWN" and
         later["state"]=="CONFLICT_UNRESOLVED" and
         unknown["state"]=="UNRECORDED" and head==8,
         "WF94_FACT_TEMPORAL_SUPERSESSION_COLD_REPLAY_CHANGED")
    records={}
    for attempt in ("v94_before_revoke","v94_after_revoke"):
        r=bridge.read_decision(project_id=PROJECT,attempt_id=attempt)
        records[attempt]=r["decision_sha256"]
    # Historical answer is preserved, but its old SELECT no longer
    # authorizes writing once the later signed synthetic revocation exists.
    runtime=bridge.runtime
    row=writer.conn.execute(
        "SELECT id FROM snapshots WHERE status='published'").fetchone()
    need(row is not None,"WF94_REPLAY_SNAPSHOT_NOT_FOUND")
    runtime.enter_write(row[0])
    try:
        try:
            bridge.validate_live_decision(
                project_id=PROJECT,attempt_id="v94_before_revoke")
        except Exception as e:
            need("REVOKED" in str(e),
                 "WF94_REVOKED_PRIOR_SELECT_WRONG_FAILURE")
        else:
            raise V94DurableEventError(
                "WF94_HISTORICAL_SELECT_REINSTATED_AFTER_REVOKE")
    finally:
        runtime.exit()
    current=bridge.read_decision(
        project_id=PROJECT,attempt_id="v94_after_revoke")
    need(current["prompt_guidance"]=="" and
         all(x["decision"]=="SKIP" for x in current["decisions"]),
         "WF94_OLD_REVOKED_WRITE_PLAN_STILL_ACTIVE")
    return {
        "source_snapshot_global_ledger_seq":6,
        "new_global_ledger_seq":head,
        "earlier_actor_fact_state":"KNOWN",
        "latest_actor_fact_state":"CONFLICT_UNRESOLVED",
        "unknown_future_fact_state":"UNRECORDED",
        "past_select_receipt_sha256":records["v94_before_revoke"],
        "current_revoked_skip_receipt_sha256":records[
            "v94_after_revoke"],
        "old_select_no_longer_authorizes_write":True,
        "false_independent_semantic_grade_never_created":True,
        "production_user_memories_updated":False,
    }


def _event_body(seq,operation,previous,outcome):
    return {
        "format":FORMAT_EVENT,
        "schema_version":SCHEMA_VERSION,
        "source_graph_manifest_sha256":BASE_GRAPH_SHA,
        "v92_experience_manifest_sha256":V92_EXPERIENCE_CHAIN_SHA,
        "event_chain_id":CHAIN_ID,
        "seq":seq,
        "previous_event_sha256":previous,
        "operation":operation,
        "outcome_sha256":digest(canonical(outcome)),
        "synthetic_only":True,
        "original_work_authority_proven":False,
        "independent_literary_review_proven":False,
        "eligible_to_direct_writing":False,
    }


def _validate_event(doc,seq,previous):
    expected=_operations()[seq-1]
    need(type(doc) is dict and set(doc)==META_FIELDS and
         doc["format"]==FORMAT_EVENT and
         type(doc["schema_version"]) is int and
         doc["schema_version"]==SCHEMA_VERSION and
         doc["source_graph_manifest_sha256"]==BASE_GRAPH_SHA and
         doc["v92_experience_manifest_sha256"]==
             V92_EXPERIENCE_CHAIN_SHA and
         doc["event_chain_id"]==CHAIN_ID and
         type(doc["seq"]) is int and doc["seq"]==seq and
         doc["previous_event_sha256"]==previous and
         doc["operation"]==expected and
         is_sha(doc["outcome_sha256"]) and
         doc["synthetic_only"] is True and
         doc["original_work_authority_proven"] is False and
         doc["independent_literary_review_proven"] is False and
         doc["eligible_to_direct_writing"] is False,
         "WF94_EVENT_CHAIN_TAMPERED_OR_NOT_SYNTHETIC")
    return doc


def _run(reader,*,working_dir,event_bytes=None):
    """Return freshly recomputed event bodies and final state.

    Caller supplies event_bytes for REPLAY. For PREPARATION, supply None and
    derive expected event body/outcome hashes from actual existing APIs.
    """
    destination=Path(working_dir)
    need(destination.exists() and destination.is_dir() and
         not any(destination.iterdir()),
         "WF94_REPLAY_WORKDIR_NOT_EMPTY")
    base=cold_restore_from_cas(
        reader,manifest_sha=BASE_GRAPH_SHA,
        restore_parent=destination)
    folder=destination/"checkpoints"/base["checkpoint_id"]
    writer=WriterForgeDB(folder/"writerforge.sqlite3")
    facts=FactJournal(folder/"fact-journal.sqlite3")
    runtime=RuntimeEngine()
    bridge=ExperienceDecisionBridge(
        writer,runtime,reviewer_key=SYNTHETIC_SIGNING_KEY)
    receipts=[]
    docs=[]
    prev=None
    try:
        for number,op in enumerate(_operations(),1):
            outcome=_apply(op["kind"],writer,facts,runtime,bridge)
            doc=_event_body(number,op,prev,outcome)
            raw=canonical(doc)
            need(len(raw)<=MAX_EVENT_BYTES,
                 "WF94_SYNTHETIC_EVENT_BYTES_UNBOUNDED")
            if event_bytes is not None:
                need(len(event_bytes)==MAX_EVENTS and
                     event_bytes[number-1]==raw,
                     "WF94_REPLAYED_OPERATION_OUTCOME_CHANGED")
                parsed=_parse(event_bytes[number-1],MAX_EVENT_BYTES)
                _validate_event(parsed,number,prev)
            receipts.append(digest(canonical(outcome)))
            docs.append(raw)
            prev=digest(raw)
        result=_verify_final(writer,facts,bridge)
    finally:
        writer.close()
        facts.close()
    return docs,receipts,result


def prepare_chain(reader,*,workdir):
    """Compute deterministic hashes with a temporary restored DB only."""
    docs,receipts,final=_run(reader,working_dir=workdir)
    refs=[{"seq":i+1,"cas_sha256":digest(raw),
           "operation_kind":_operations()[i]["kind"]}
          for i,raw in enumerate(docs)]
    manifest={
        "format":FORMAT_COMMIT,"schema_version":SCHEMA_VERSION,
        "event_chain_id":CHAIN_ID,
        "source_graph_manifest_sha256":BASE_GRAPH_SHA,
        "v92_experience_manifest_sha256":V92_EXPERIENCE_CHAIN_SHA,
        "event_refs":refs,
        "outcome_receipts_sha256":digest(canonical(receipts)),
        "final_state_sha256":digest(canonical(final)),
        "committed_event_count":MAX_EVENTS,
        "synthetic_only":True,
        "all_model_calls_zero":True,
        "production_memory_written":False,
        "original_literary_quality_proven":False,
        "schema_and_temporal_replay_checked_before_publish":True,
        "writer_eligible":False,
        "old_v93_graph_unchanged":True,
    }
    manifest_raw=canonical(manifest)
    need(len(manifest_raw)<=MAX_COMMIT_BYTES,
         "WF94_COMMIT_MANIFEST_SIZE_BUDGET")
    return docs,manifest_raw,final


def _validate_manifest(raw):
    doc=_parse(raw,MAX_COMMIT_BYTES)
    refs=doc.get("event_refs")
    need(type(doc) is dict and set(doc)==COMMIT_FIELDS and
         doc["format"]==FORMAT_COMMIT and
         type(doc["schema_version"]) is int and
         doc["schema_version"]==SCHEMA_VERSION and
         doc["event_chain_id"]==CHAIN_ID and
         doc["source_graph_manifest_sha256"]==BASE_GRAPH_SHA and
         doc["v92_experience_manifest_sha256"]==
             V92_EXPERIENCE_CHAIN_SHA and
         type(refs) is list and len(refs)==MAX_EVENTS and
         type(doc["committed_event_count"]) is int and
         doc["committed_event_count"]==MAX_EVENTS and
         is_sha(doc["outcome_receipts_sha256"]) and
         is_sha(doc["final_state_sha256"]) and
         doc["synthetic_only"] is True and
         doc["all_model_calls_zero"] is True and
         doc["production_memory_written"] is False and
         doc["original_literary_quality_proven"] is False and
         doc["schema_and_temporal_replay_checked_before_publish"] is True and
         doc["writer_eligible"] is False and
         doc["old_v93_graph_unchanged"] is True,
         "WF94_COMMIT_MANIFEST_UNSUPPORTED_OR_FALSE_APPROVAL")
    for n,ref in enumerate(refs,1):
        need(type(ref) is dict and
             set(ref)=={"seq","cas_sha256","operation_kind"} and
             type(ref["seq"]) is int and ref["seq"]==n and
             is_sha(ref["cas_sha256"]) and
             ref["operation_kind"]==_operations()[n-1]["kind"],
             "WF94_COMMIT_REORDER_OR_EVENT_REF_TAMPER")
    return doc


def publish_chain(writer,reader,*,event_bytes,manifest_raw,preflight_dir):
    """CAS events then manifest LAST, only after independent local replay.

    Writer cannot publish a forged 'successful' receipt by guessing hashes:
    each operation is re-applied to a NEW cloud-restored graph and the
    resulting hashes MUST match the proposed final commit BEFORE writing.
    """
    need(getattr(writer,"read_only",True) is False and
         bool(getattr(writer,"writer",None)) and
         getattr(reader,"read_only",False) is True and
         getattr(reader,"writer",None) is None,
         "WF94_R2_TEST_WRITER_AND_SEPARATE_READER_REQUIRED")
    manifest=_validate_manifest(manifest_raw)
    need(type(event_bytes) is list and len(event_bytes)==MAX_EVENTS,
         "WF94_REPLAY_EVENT_COUNT_NOT_SEVEN")
    previous=None
    for n,raw in enumerate(event_bytes,1):
        need(type(raw) is bytes and len(raw)<=MAX_EVENT_BYTES,
             "WF94_BAD_EVENT_RAW_BYTES")
        _validate_event(_parse(raw,MAX_EVENT_BYTES),n,previous)
        previous=digest(raw)
    rerun,outcomes,final=_run(reader,working_dir=preflight_dir,
                             event_bytes=event_bytes)
    need(rerun==event_bytes and
         digest(canonical(outcomes))==
            manifest["outcome_receipts_sha256"] and
         digest(canonical(final))==
            manifest["final_state_sha256"],
         "WF94_REPLAY_BEFORE_UPLOAD_NOT_ATTESTED")
    previous=None
    published=[]
    for n,raw in enumerate(event_bytes,1):
        doc=_validate_event(_parse(raw,MAX_EVENT_BYTES),n,previous)
        expected=manifest["event_refs"][n-1]["cas_sha256"]
        need(digest(raw)==expected,
             "WF94_PRECOMMITTED_EVENT_HASH_CHANGED")
        # Never store a mutable SQL or raw novel event; exact enum only.
        key,created=writer._put_content(raw)
        need(key==expected and reader._get_content(key)==raw,
             "WF94_EVENT_R2_WRITE_READBACK_FAILED")
        published.append({"seq":n,"event_sha256":key,"created":bool(created)})
        previous=key
    ref=digest(manifest_raw)
    key,created=writer._put_content(manifest_raw)
    need(key==ref and reader._get_content(key)==manifest_raw,
         "WF94_MANIFEST_LAST_R2_READBACK_FAILED")
    return {
        "status":"WF94_SYNTHETIC_EVENT_CAS_AND_COMMIT_PUBLISHED",
        "manifest_sha256":key,
        "committed_event_count":MAX_EVENTS,
        "event_cas_refs":published,
        "manifest_created":bool(created),
        "previous_v93_graph_snapshot_unchanged":True,
        "writer_never_promoted_literary_truth":True,
        "independent_cold_reader_pending":True,
        "synthetic_only":True,"model_calls":0,
    }


def cold_replay(reader,*,manifest_sha,workdir):
    """Independent cold reader verifies manifest and recomputes entire DB."""
    need(getattr(reader,"read_only",False) is True and
         getattr(reader,"writer",None) is None and
         is_sha(manifest_sha),
         "WF94_STRICT_COLD_READER_OR_MANIFEST_REQUIRED")
    manifest_raw=reader._get_content(manifest_sha)
    need(digest(manifest_raw)==manifest_sha,
         "WF94_COLD_MANIFEST_CONTENT_ADDRESS_INVALID")
    manifest=_validate_manifest(manifest_raw)
    docs=[]
    previous=None
    for n,ref in enumerate(manifest["event_refs"],1):
        raw=reader._get_content(ref["cas_sha256"])
        need(digest(raw)==ref["cas_sha256"],
             "WF94_COLD_EVENT_CONTENT_ADDRESS_CHANGED")
        parsed=_validate_event(_parse(raw,MAX_EVENT_BYTES),n,previous)
        docs.append(raw)
        previous=ref["cas_sha256"]
    recalculated,outcomes,final=_run(
        reader,working_dir=workdir,event_bytes=docs)
    need(recalculated==docs and
         digest(canonical(outcomes))==
           manifest["outcome_receipts_sha256"] and
         digest(canonical(final))==manifest["final_state_sha256"],
         "WF94_COLD_REPLAY_UNTRUSTED_STATE_OR_RECEIPTS")
    return {
        "status":"WF94_SYNTHETIC_R2_EVENT_COLD_REPLAY_VERIFIED",
        "manifest_sha256":manifest_sha,
        "base_v93_graph_manifest_sha256":BASE_GRAPH_SHA,
        "original_v92_experience_chain_sha256":V92_EXPERIENCE_CHAIN_SHA,
        "verified_cas_events":len(docs),
        "outcome_receipts_sha256":manifest["outcome_receipts_sha256"],
        "final_state_sha256":manifest["final_state_sha256"],
        "before_revocation":"SELECT",
        "after_revocation":"SKIP",
        "prior_revoked_select_still_invalid":True,
        "original_character_state":"KNOWN",
        "latest_character_state":"CONFLICT_UNRESOLVED",
        "unknown_future_state":"UNRECORDED",
        "knowledge_history_kept_as_of_ledger":True,
        "actual_production_graph_durable_write_stream_active":False,
        "independent_literary_semantic_judge_executed":False,
        "new_paid_model_calls":0,"r2_writes":0,
    }
