"""V61 small typed LEARN -> approved experiment -> frozen WRITE decision bridge.

This is NOT literary understanding, independent reviewer authenticity or a
fine-tuned model. SQLite records source locators+hashes and decisions, never
copies original source prose into the creative prompt. Only an externally
configured verifier can permit *controlled experimental* use. No skill level
promotion occurs here. Uses existing WriterForgeDB and RuntimeEngine.
"""
from __future__ import annotations

from hashlib import sha256
import hmac
import json
import re
from typing import Mapping

from .runtime import Mode

ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,79}\Z")
TAG = re.compile(r"[a-z][a-z0-9_]{1,31}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")

# Bounded system-owned ACTIONS, not snippets retrieved from novels.
# These are software templates, not independently validated writing skills.
OPERATION_GUIDANCE = {
    "CHECK_KNOWLEDGE": "创作前核对人物已掌握的具体信息，不得凭作者全知替人物作判断。",
    "TRACE_CONSEQUENCE": "人物作出选择后，需要出现可由前述行动追溯的具体后果。",
    "DEFER_REVELATION": "尚未公开的信息不得提前转给读者或不知情人物。",
    "TRACK_PROMISE": "本场景若涉及既有承诺，核对它的期限、代价与兑现状态。",
    "VERIFY_FALSE_BELIEF": "人物可以误判，但后续行动必须受其当时信念和可见事实约束。",
}

MAX_POLICIES = 8
MAX_SELECTED = 2


class ExperiencePolicyError(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise ExperiencePolicyError(reason)


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def digest(obj):
    return sha256(canonical(obj).encode("utf-8")).hexdigest()


def is_id(s):
    return isinstance(s, str) and ID.fullmatch(s) is not None


def key_guard(key):
    need(key is None or (isinstance(key, bytes) and len(key) >= 16),
         "EXPERIENCE_VERIFIER_KEY_INVALID")


class ExperienceDecisionBridge:
    def __init__(self, db, runtime, *, reviewer_key: bytes | None = None):
        self.db = db
        self.runtime = runtime
        key_guard(reviewer_key)
        self._reviewer_key = reviewer_key

    def _source_verified(self, locator, snapshot_id):
        need(type(snapshot_id) is int and snapshot_id >= 1,
             "EXPERIENCE_SOURCE_SNAPSHOT_INVALID")
        r = self.db.conn.execute(
            "SELECT status FROM snapshots WHERE id=?",(snapshot_id,)
        ).fetchone()
        need(r is not None and r["status"] == "published",
             "EXPERIENCE_SOURCE_SNAPSHOT_NOT_PUBLISHED")
        need(isinstance(locator, dict) and set(locator)=={
            "work_id","chapter","paragraph","sentence","source_sha256"},
            "EXPERIENCE_SOURCE_REFERENCE_INVALID")
        need(is_id(locator["work_id"]) and
             all(type(locator[k]) is int and locator[k]>=1
                 for k in ("chapter","paragraph","sentence")) and
             isinstance(locator["source_sha256"],str) and
             SHA.fullmatch(locator["source_sha256"]) is not None,
             "EXPERIENCE_SOURCE_REFERENCE_INVALID")
        row=self.db.conn.execute(
            "SELECT source_sha256 FROM source_spans "
            "WHERE work_id=? AND chapter=? AND paragraph=? AND sentence=?",
            (locator["work_id"],locator["chapter"],
             locator["paragraph"],locator["sentence"])).fetchone()
        need(row is not None and row["source_sha256"]==locator["source_sha256"],
             "EXPERIENCE_SOURCE_SHA_NOT_VERIFIED")
        chapter=self.db.conn.execute(
            "SELECT snapshot_id FROM studied_chapters "
            "WHERE work_id=? AND chapter=?",
            (locator["work_id"],locator["chapter"])).fetchone()
        need(chapter is not None,"EXPERIENCE_SOURCE_CHAPTER_MISSING")
        # A published child snapshot may depend on an ancestor's source work.
        visited=set()
        sid=snapshot_id
        for _ in range(128):
            need(sid not in visited,"EXPERIENCE_SOURCE_SNAPSHOT_CYCLE")
            visited.add(sid)
            if sid==chapter["snapshot_id"]:
                return
            parent=self.db.conn.execute(
                "SELECT parent_id FROM snapshots WHERE id=?",(sid,)
            ).fetchone()
            sid=parent["parent_id"] if parent else None
            if sid is None:
                break
        raise ExperiencePolicyError("EXPERIENCE_SOURCE_NOT_IN_PINNED_SNAPSHOT")

    @staticmethod
    def _verify_tags(tags, *, required):
        need(isinstance(tags,(tuple,list)) and
             len(tags) <= 6 and (not required or len(tags)>=1) and
             len(tags)==len(set(tags)) and
             all(isinstance(t,str) and TAG.fullmatch(t) for t in tags),
             "EXPERIENCE_TAGS_INVALID")
        return sorted(tags)

    @staticmethod
    def _candidate_view(row):
        data=json.loads(row["candidate_json"])
        need(digest(data)==row["candidate_sha"],
             "EXPERIENCE_CANDIDATE_TAMPERED")
        need(data["project_id"]==row["project_id"] and
             data["experience_id"]==row["experience_id"],
             "EXPERIENCE_CANDIDATE_TAMPERED")
        return data

    def stage_candidate(self, *, project_id, experience_id, snapshot_id,
                        source_ref, required_tags, forbidden_tags,
                        operation_code):
        self.runtime.require(Mode.LEARN)
        need(is_id(project_id) and is_id(experience_id),
             "EXPERIENCE_ID_INVALID")
        req=self._verify_tags(required_tags,required=True)
        deny=self._verify_tags(forbidden_tags,required=False)
        need(not (set(req)&set(deny)),
             "EXPERIENCE_TAGS_CONTRADICTORY")
        need(operation_code in OPERATION_GUIDANCE,
             "EXPERIENCE_OPERATION_NOT_ALLOWED")
        self._source_verified(source_ref,snapshot_id)
        record={"project_id":project_id,"experience_id":experience_id,
                "source_snapshot_id":snapshot_id,"source_ref":dict(source_ref),
                "required_tags":req,"forbidden_tags":deny,
                "operation_code":operation_code,
                "source_semantics_verified":False,
                "status":"HYPOTHESIS_ONLY"}
        h=digest(record)
        prior=self.db.conn.execute(
            "SELECT * FROM experience_candidates "
            "WHERE project_id=? AND experience_id=?",
            (project_id,experience_id)).fetchone()
        if prior:
            self._candidate_view(prior)
            need(prior["candidate_sha"]==h,
                 "EXPERIENCE_CANDIDATE_IMMUTABLE")
            return {"candidate_sha256":h,"replayed":True,
                    "eligible_for_writing":False}
        with self.db.conn:
            self.db.conn.execute(
                "INSERT INTO experience_candidates("
                "project_id,experience_id,candidate_sha,candidate_json)"
                " VALUES(?,?,?,?)",
                (project_id,experience_id,h,canonical(record)))
        return {"candidate_sha256":h,"replayed":False,
                "eligible_for_writing":False}

    def _lookup_candidate(self, project_id, experience_id):
        row=self.db.conn.execute(
            "SELECT * FROM experience_candidates WHERE "
            "project_id=? AND experience_id=?",
            (project_id,experience_id)).fetchone()
        need(row is not None,"EXPERIENCE_CANDIDATE_MISSING")
        return row,self._candidate_view(row)

    def approval_payload(self, *, project_id, experience_id,
                         reviewer_id, review_id):
        need(all(is_id(x) for x in (
             project_id,experience_id,reviewer_id,review_id)),
             "EXPERIENCE_REVIEW_ID_INVALID")
        row,data=self._lookup_candidate(project_id,experience_id)
        return {"contract":"writerforge.v61-controlled-experience-approval",
                "project_id":project_id,"experience_id":experience_id,
                "candidate_sha256":row["candidate_sha"],
                "reviewer_id":reviewer_id,"review_id":review_id,
                "permission":"CONTROLLED_WRITE_EXPERIMENT",
                "literary_truth_verified":False}

    def _check_signature(self,payload,signature):
        need(self._reviewer_key is not None,
             "EXPERIENCE_REVIEW_ATTESTATION_KEY_REQUIRED")
        need(isinstance(signature,str) and
             SHA.fullmatch(signature) is not None,
             "EXPERIENCE_REVIEW_ATTESTATION_INVALID")
        expected=hmac.new(self._reviewer_key,
                          canonical(payload).encode("utf-8"),
                          "sha256").hexdigest()
        need(hmac.compare_digest(signature,expected),
             "EXPERIENCE_REVIEW_ATTESTATION_INVALID")

    def approve_candidate(self, *, project_id, experience_id,
                          reviewer_id, review_id, signature):
        self.runtime.require(Mode.LEARN)
        payload=self.approval_payload(project_id=project_id,
                                      experience_id=experience_id,
                                      reviewer_id=reviewer_id,
                                      review_id=review_id)
        self._check_signature(payload,signature)
        review={"payload":payload,"signature":signature}
        h=digest(review)
        prior=self.db.conn.execute(
            "SELECT * FROM experience_approvals WHERE "
            "project_id=? AND experience_id=?",
            (project_id,experience_id)).fetchone()
        if prior:
            self._verify_approval(prior)
            need(prior["approval_sha"]==h,
                 "EXPERIENCE_APPROVAL_IMMUTABLE")
            return {"approval_sha256":h,"replayed":True,
                    "independent_literary_quality_proven":False}
        with self.db.conn:
            self.db.conn.execute(
                "INSERT INTO experience_approvals("
                "project_id,experience_id,reviewer_id,review_id,"
                "approval_sha,signature) VALUES(?,?,?,?,?,?)",
                (project_id,experience_id,reviewer_id,review_id,h,signature))
        return {"approval_sha256":h,"replayed":False,
                "independent_literary_quality_proven":False}

    def _verify_approval(self,row):
        payload=self.approval_payload(
            project_id=row["project_id"],experience_id=row["experience_id"],
            reviewer_id=row["reviewer_id"],review_id=row["review_id"])
        self._check_signature(payload,row["signature"])
        need(digest({"payload":payload,"signature":row["signature"]})==
             row["approval_sha"],"EXPERIENCE_APPROVAL_TAMPERED")
        return payload

    def has_approved(self, *, project_id):
        need(is_id(project_id),"EXPERIENCE_PROJECT_INVALID")
        return bool(self.db.conn.execute(
            "SELECT 1 FROM experience_approvals WHERE project_id=? LIMIT 1",
            (project_id,)).fetchone())

    @staticmethod
    def _check_signals(signals):
        need(isinstance(signals,Mapping) and len(signals)<=20,
             "EXPERIENCE_SCENE_SIGNALS_INVALID")
        need(all(isinstance(k,str) and TAG.fullmatch(k) and
                 (v is None or type(v) is bool)
                 for k,v in signals.items()),
             "EXPERIENCE_SCENE_SIGNALS_INVALID")
        return {k:signals[k] for k in sorted(signals)}

    def read_decision(self, *, project_id, attempt_id):
        need(is_id(project_id) and is_id(attempt_id),
             "EXPERIENCE_DECISION_ID_INVALID")
        row=self.db.conn.execute(
            "SELECT * FROM experience_decisions WHERE "
            "project_id=? AND attempt_id=?",
            (project_id,attempt_id)).fetchone()
        need(row is not None,"EXPERIENCE_DECISION_NOT_FOUND")
        plan=json.loads(row["plan_json"])
        need(digest(plan)==row["plan_sha"],
             "EXPERIENCE_DECISION_TAMPERED")
        need(plan["project_id"]==project_id and
             plan["attempt_id"]==attempt_id and
             plan["request_sha256"]==row["request_sha"],
             "EXPERIENCE_DECISION_TAMPERED")
        return {**plan,"decision_sha256":row["plan_sha"]}

    def validate_live_decision(self, *, project_id,attempt_id):
        """Auditing a frozen receipt is distinct from reusing it for prose.

        Before ANY fresh model generation or acceptance, recheck that every
        approved decision still refers to the immutable source and that the
        verifier key still authenticates the approval. The old frozen record
        remains readable after revocation or source failure for forensics.
        """
        self.runtime.require(Mode.WRITE)
        plan=self.read_decision(project_id=project_id,attempt_id=attempt_id)
        need(plan["source_snapshot_id"]==self.runtime.pinned_snapshot_id,
             "EXPERIENCE_SOURCE_SNAPSHOT_STALE")
        for detail in plan["decisions"]:
            row,candidate=self._lookup_candidate(
                project_id,detail["experience_id"])
            need(row["candidate_sha"]==detail["candidate_sha256"],
                 "EXPERIENCE_CANDIDATE_IMMUTABLE")
            review=self.db.conn.execute(
                "SELECT * FROM experience_approvals "
                "WHERE project_id=? AND experience_id=?",
                (project_id,detail["experience_id"])).fetchone()
            need(review is not None and
                 review["approval_sha"]==detail["approval_sha256"],
                 "EXPERIENCE_APPROVAL_MISSING_OR_CHANGED")
            self._verify_approval(review)
            self._source_verified(candidate["source_ref"],
                                  plan["source_snapshot_id"])
        return plan

    def decide(self, *, project_id,scene_id,attempt_id,goal,
               scene_signals,enabled=True):
        self.runtime.require(Mode.WRITE)
        need(all(is_id(x) for x in (project_id,scene_id,attempt_id)),
             "EXPERIENCE_DECISION_ID_INVALID")
        need(type(goal) is str and 1<=len(goal)<=2000 and
             type(enabled) is bool,"EXPERIENCE_DECISION_ARGUMENTS_INVALID")
        pinned=self.runtime.pinned_snapshot_id
        need(type(pinned) is int and pinned>0,"EXPERIENCE_PINNED_SNAPSHOT_MISSING")
        values=self._check_signals(scene_signals)
        request={"project_id":project_id,"scene_id":scene_id,
                 "attempt_id":attempt_id,"goal_sha256":sha256(goal.encode("utf-8")).hexdigest(),
                 "scene_signals":values,"enabled":enabled,
                 "source_snapshot_id":pinned}
        request_hash=digest(request)
        prior=self.db.conn.execute(
            "SELECT request_sha FROM experience_decisions "
            "WHERE project_id=? AND attempt_id=?",
            (project_id,attempt_id)).fetchone()
        if prior:
            need(prior["request_sha"]==request_hash,
                 "EXPERIENCE_DECISION_IMMUTABLE")
            return self.validate_live_decision(
                project_id=project_id,attempt_id=attempt_id)
        rows=self.db.conn.execute(
            "SELECT c.*,a.approval_sha,a.reviewer_id,a.review_id,"
            "a.signature FROM experience_candidates c "
            "JOIN experience_approvals a ON a.project_id=c.project_id "
            "AND a.experience_id=c.experience_id "
            "WHERE c.project_id=? ORDER BY c.experience_id LIMIT ?",
            (project_id,MAX_POLICIES+1)).fetchall()
        need(len(rows)<=MAX_POLICIES,"EXPERIENCE_POLICY_LIMIT_EXCEEDED")
        decisions=[]
        selection=[]
        for row in rows:
            self._verify_approval(row)
            candidate=self._candidate_view(row)
            need(candidate["source_snapshot_id"]==pinned,
                 "EXPERIENCE_SOURCE_SNAPSHOT_STALE")
            self._source_verified(candidate["source_ref"],pinned)
            req=candidate["required_tags"]
            banned=candidate["forbidden_tags"]
            if not enabled:
                outcome,why="SKIP","OPERATOR_DISABLED"
            elif any(values.get(x) is False for x in req) or any(
                    values.get(x) is True for x in banned):
                outcome,why="SKIP","SCENE_CONTRAINDICATED"
            elif any(values.get(x) is not True for x in req) or any(
                    values.get(x) is not False for x in banned):
                outcome,why="UNCERTAIN","SCENE_FACTS_NOT_VERIFIED"
            elif len(selection)>=MAX_SELECTED:
                outcome,why="SKIP","SELECTED_POLICY_CAP"
            else:
                outcome,why="SELECT","CONDITIONS_CONFIRMED"
                selection.append(candidate["operation_code"])
            decisions.append({
                "experience_id":candidate["experience_id"],
                "candidate_sha256":row["candidate_sha"],
                "approval_sha256":row["approval_sha"],
                "operation_code":candidate["operation_code"],
                "decision":outcome,"reason_code":why,
                "source_ref":candidate["source_ref"]})
        # The only behavior-changing prompt text consists of system-owned
        # abstract actions, never source passages, reviewer prose, or scores.
        guidance="\n".join(OPERATION_GUIDANCE[code] for code in selection)
        plan={**request,"request_sha256":request_hash,
              "decisions":decisions,"approved_count":len(decisions),
              "prompt_guidance":guidance,
              "literary_semantics_verified":False,
              "auto_skill_promotion":False,
              "source_prose_stored":False}
        h=digest(plan)
        try:
            with self.db.conn:
                self.db.conn.execute(
                    "INSERT INTO experience_decisions("
                    "project_id,attempt_id,request_sha,plan_sha,plan_json)"
                    " VALUES(?,?,?,?,?)",
                    (project_id,attempt_id,request_hash,h,canonical(plan)))
        except Exception as exc:
            # Concurrent writer may have created same attempt. Either exact
            # replay or collision is determined by the immutable row.
            again=self.db.conn.execute(
                "SELECT request_sha FROM experience_decisions "
                "WHERE project_id=? AND attempt_id=?",
                (project_id,attempt_id)).fetchone()
            if again:
                need(again["request_sha"]==request_hash,
                     "EXPERIENCE_DECISION_IMMUTABLE")
                return self.read_decision(project_id=project_id,
                                          attempt_id=attempt_id)
            raise
        return {**plan,"decision_sha256":h}

    def report_postwrite(self, *, project_id,attempt_id,draft,
                         experience_id,outcome,quote=None):
        self.runtime.require(Mode.WRITE)
        need(isinstance(draft,str) and 1<=len(draft)<=100000,
             "EXPERIENCE_DRAFT_INVALID")
        need(is_id(experience_id) and outcome in (
             "CLAIMED_APPLIED","NOT_APPLIED","UNCERTAIN"),
             "EXPERIENCE_POSTWRITE_STATUS_INVALID")
        record=self.read_decision(
            project_id=project_id,attempt_id=attempt_id)
        decisions=[r for r in record["decisions"]
                   if r["experience_id"]==experience_id]
        need(len(decisions)==1 and decisions[0]["decision"]=="SELECT",
             "EXPERIENCE_POSTWRITE_NOT_SELECTED")
        if outcome=="CLAIMED_APPLIED":
            need(isinstance(quote,str) and 8<=len(quote)<=120 and
                 quote in draft,
                 "EXPERIENCE_POSTWRITE_QUOTE_NOT_IN_DRAFT")
        else:
            need(quote is None,"EXPERIENCE_POSTWRITE_QUOTE_UNEXPECTED")
        receipt={"project_id":project_id,"attempt_id":attempt_id,
                 "decision_sha256":record["decision_sha256"],
                 "experience_id":experience_id,"outcome":outcome,
                 "draft_sha256":sha256(draft.encode("utf-8")).hexdigest(),
                 "quote_sha256":sha256(quote.encode("utf-8")).hexdigest()
                    if quote is not None else None,
                 "literary_effect_verified":False,
                 "source_text_not_stored":True}
        h=digest(receipt)
        prior=self.db.conn.execute(
            "SELECT receipt_sha,receipt_json FROM experience_postwrites "
            "WHERE project_id=? AND attempt_id=? AND experience_id=?",
            (project_id,attempt_id,experience_id)).fetchone()
        if prior:
            need(prior["receipt_sha"]==digest(json.loads(prior["receipt_json"])),
                 "EXPERIENCE_POSTWRITE_TAMPERED")
            need(prior["receipt_sha"]==h,
                 "EXPERIENCE_POSTWRITE_IMMUTABLE")
            return {**receipt,"receipt_sha256":h,"replayed":True}
        with self.db.conn:
            self.db.conn.execute(
                "INSERT INTO experience_postwrites("
                "project_id,attempt_id,experience_id,receipt_sha,receipt_json)"
                " VALUES(?,?,?,?,?)",
                (project_id,attempt_id,experience_id,h,canonical(receipt)))
        return {**receipt,"receipt_sha256":h,"replayed":False}
