"""V43 experimental experience -> REAL production writing controls.

This is a policy execution layer, not an LLM and not literary semantic truth.
It refuses under-specified foreshadowing, freezes actor-knowledge plans BEFORE
the writing prompt is built, and supports bounded feedback-triggered rollback.
No free-text lesson is injected as an instruction and nothing is promoted.
No external model, private manuscript, or retroactive V38 rewrite.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
import re
import sqlite3

V38_CROSSWALK_SHA = "e2ed24abc352daef678165de8bee5f7c283f5709cf3a23c9fe99b9a876aeb0db"
V38_SELF_SHA = "a9d5d521b2e0adbeb416f9325b0adabaad408abb728bd978099effe328488a62"
RULE_ID = "L2_ROLE_CONFLICT_V38"
FIELDS = {
    "clue_id", "actor_id", "knowledge_before", "unknown_before",
    "observation", "decision", "decision_depends_on_clue",
    "later_reveal_target", "alternative_explanation", "uncertainty",
}
def _safe_key(value) -> bool:
    return (isinstance(value, str) and 1 <= len(value) <= 90
            and value.strip() == value and all(ch.isprintable() for ch in value)
            and not any(ch in value for ch in ("\\\\", "/", "\\x00")))


class ExperiencePolicyError(ValueError):
    pass


def _need(check: bool, code: str) -> None:
    if not check:
        raise ExperiencePolicyError(code)


def _canonical(doc) -> bytes:
    return json.dumps(doc, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(doc) -> str:
    return sha256(doc if isinstance(doc, bytes) else _canonical(doc)).hexdigest()


def _text(value, lower=6, upper=190) -> bool:
    return isinstance(value, str) and lower <= len(value.strip()) <= upper


def validate_causal_plan(plan: dict) -> dict:
    """Structural prewrite evidence only; no claim of literary correctness."""
    _need(isinstance(plan, dict) and set(plan) == FIELDS,
          "EXPERIENCE_PLAN_FIELDS_INVALID")
    for key in FIELDS:
        lo = 2 if key in ("clue_id", "actor_id") else 8
        _need(_text(plan[key], lo, 190), "EXPERIENCE_PLAN_FIELD_EMPTY_OR_UNBOUNDED")
    _need(plan["knowledge_before"] != plan["unknown_before"],
          "EXPERIENCE_KNOWLEDGE_CONTRADICTION")
    _need(plan["decision_depends_on_clue"] != plan["decision"],
          "EXPERIENCE_DECISION_DEPENDENCY_NOT_SEPARATE")
    return dict(plan)


@dataclass(frozen=True)
class PolicyDecision:
    status: str
    policy_sha256: str | None = None
    plan_sha256: str | None = None
    required_postwrite: tuple[str, ...] = ()
    prewrite: dict | None = None

    def audit(self) -> dict:
        return {
            "status": self.status,
            "policy_sha256": self.policy_sha256,
            "frozen_prewrite_sha256": self.plan_sha256,
            "postwrite_evidence_required": list(self.required_postwrite),
            "semantic_quality_proven": False,
            "official_skill_promoted": False,
        }


class ExperienceExecutor:
    """Opt-in only. DB is the EXISTING WriterForge database connection."""

    def __init__(self, connection: sqlite3.Connection, project_id: str):
        _need(_safe_key(project_id),
              "EXPERIENCE_PROJECT_ID_INVALID")
        self.conn = connection
        self.project_id = project_id
        self.conn.execute("""CREATE TABLE IF NOT EXISTS wf_experience_policies(
            project TEXT NOT NULL, rule_id TEXT NOT NULL,
            policy_sha TEXT NOT NULL, status TEXT NOT NULL,
            valid_sources TEXT NOT NULL, PRIMARY KEY(project,rule_id))""")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS wf_experience_prewrite(
            project TEXT NOT NULL, scene_id TEXT NOT NULL,
            policy_sha TEXT NOT NULL, plan_sha TEXT NOT NULL,
            plan_json TEXT NOT NULL, PRIMARY KEY(project,scene_id))""")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS wf_experience_feedback(
            project TEXT NOT NULL, rule_id TEXT NOT NULL,
            scene_id TEXT NOT NULL, outcome TEXT NOT NULL,
            report_sha TEXT NOT NULL, PRIMARY KEY(project,rule_id,scene_id))""")
        self.conn.commit()

    def install_v38_candidate(self, *, explicit_experiment_opt_in: bool) -> str:
        _need(explicit_experiment_opt_in is True,
              "EXPERIENCE_CANDIDATE_REQUIRES_EXPLICIT_OPT_IN")
        record = {
            "rule_id": RULE_ID,
            "v38_crosswalk_sha256": V38_CROSSWALK_SHA,
            "v38_selfreport_sha256": V38_SELF_SHA,
            "operation": "REQUIRE_PREWRITE_CHARACTER_KNOWLEDGE_AND_CAUSAL_LINK",
            "trigger": "setup_payoff",
            "source_conclusion": "CONTESTED_NOT_LITERARY_TRUTH",
            "formal_promoted": False,
        }
        digest = _sha(record)
        row = self.conn.execute(
            "SELECT policy_sha FROM wf_experience_policies "
            "WHERE project=? AND rule_id=?", (self.project_id, RULE_ID)
        ).fetchone()
        if row is not None:
            _need(row[0] == digest, "EXPERIENCE_POLICY_IMMUTABLE_CONFLICT")
            return digest
        with self.conn:
            self.conn.execute(
                "INSERT INTO wf_experience_policies VALUES(?,?,?,?,?)",
                (self.project_id, RULE_ID, digest, "EXPERIMENTAL_ACTIVE",
                 json.dumps(record, ensure_ascii=False, sort_keys=True)),
            )
        return digest

    def before_write(self, *, scene_id: str, concerns: tuple[str, ...],
                     causal_plan: dict | None) -> PolicyDecision:
        _need(_safe_key(scene_id),
              "EXPERIENCE_SCENE_ID_INVALID")
        _need(isinstance(concerns, tuple) and all(isinstance(x, str) for x in concerns),
              "EXPERIENCE_CONCERNS_INVALID")
        row = self.conn.execute(
            "SELECT policy_sha,status FROM wf_experience_policies "
            "WHERE project=? AND rule_id=?", (self.project_id, RULE_ID)
        ).fetchone()
        if row is None:
            _need(causal_plan is None, "EXPERIENCE_UNREGISTERED_PLAN_REJECTED")
            return PolicyDecision("NO_EXPERIMENTAL_POLICY")
        policy_sha, status = row
        if status == "PAUSED_DUE_TO_HARM":
            _need(causal_plan is None, "EXPERIENCE_PAUSED_POLICY_PLAN_REJECTED")
            return PolicyDecision("POLICY_ROLLED_BACK", policy_sha)
        _need(status == "EXPERIMENTAL_ACTIVE",
              "EXPERIENCE_POLICY_STATUS_INVALID")
        if "setup_payoff" not in concerns:
            _need(causal_plan is None, "EXPERIENCE_PLAN_ON_NONTRIGGER_SCENE")
            return PolicyDecision("NOT_APPLICABLE", policy_sha)
        # Gate is a runtime decision, NOT a sentence appended to the prompt.
        _need(causal_plan is not None,
              "EXPERIENCE_PREWRITE_KNOWLEDGE_AND_CAUSAL_TRACE_REQUIRED")
        valid = validate_causal_plan(causal_plan)
        # Consult the EXISTING durable story event state before allowing a
        # previously resolved clue to be presented as a fresh setup. This
        # catches role-ID contradictions, NOT subjective literary meaning.
        events = self.conn.execute(
            "SELECT event_id,payload_json FROM causal_events "
            "WHERE project_id=? ORDER BY event_id LIMIT 129",
            (self.project_id,),
        ).fetchall()
        _need(len(events) <= 128, "EXPERIENCE_STORY_EVENT_SCAN_BUDGET_EXCEEDED")
        for event in events:
            try:
                payload = json.loads(event["payload_json"])
            except (TypeError, ValueError):
                raise ExperiencePolicyError("EXPERIENCE_STORY_EVENT_RECORD_UNTRUSTED") from None
            if not isinstance(payload, dict):
                raise ExperiencePolicyError("EXPERIENCE_STORY_EVENT_RECORD_UNTRUSTED")
            if (payload.get("clue_id") == valid["clue_id"]
                and payload.get("narrative_role") == "payoff"
                and payload.get("review_status") == "confirmed"):
                raise ExperiencePolicyError(
                    "EXPERIENCE_ALREADY_RESOLVED_CLUE_CANNOT_BE_NEW_SETUP")
        digest = _sha(valid)
        existing = self.conn.execute(
            "SELECT policy_sha,plan_sha,plan_json FROM wf_experience_prewrite "
            "WHERE project=? AND scene_id=?", (self.project_id, scene_id)
        ).fetchone()
        if existing is not None:
            _need(existing[0] == policy_sha and existing[1] == digest
                  and existing[2].encode("utf-8") == _canonical(valid),
                  "EXPERIENCE_FROZEN_PREWRITE_CANNOT_BE_REWRITTEN")
        else:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO wf_experience_prewrite VALUES(?,?,?,?,?)",
                    (self.project_id, scene_id, policy_sha, digest,
                     _canonical(valid).decode("utf-8")),
                )
        return PolicyDecision(
            "CAUSAL_PREFLIGHT_VERIFIED_STRUCTURALLY",
            policy_sha, digest,
            ("observation", "actor_decision", "causal_consequence", "later_reveal"),
            valid,
        )

    def record_outcome(self, *, scene_id: str, outcome: str,
                       report_sha256: str, reviewer_is_independent: bool) -> dict:
        """Only provenance-labelled, distinct reviewed scenes influence rollback.

        Reviewer identity is a CALLER CLAIM, not a cryptographic independent
        literary verdict. No automatic promotion is possible.
        """
        _need(outcome in ("HELPED", "HARMED", "INCONCLUSIVE"),
              "EXPERIENCE_FEEDBACK_OUTCOME_INVALID")
        _need(reviewer_is_independent is True,
              "EXPERIENCE_SELF_REVIEW_CANNOT_UPDATE_POLICY")
        _need(isinstance(report_sha256, str)
              and re.fullmatch(r"[0-9a-f]{64}", report_sha256) is not None,
              "EXPERIENCE_FEEDBACK_REPORT_SHA_INVALID")
        earlier = self.conn.execute(
            "SELECT plan_sha FROM wf_experience_prewrite "
            "WHERE project=? AND scene_id=?", (self.project_id, scene_id)
        ).fetchone()
        _need(earlier is not None,
              "EXPERIENCE_FEEDBACK_WITHOUT_PRIOR_FROZEN_PLAN")
        current = self.conn.execute(
            "SELECT outcome,report_sha FROM wf_experience_feedback "
            "WHERE project=? AND rule_id=? AND scene_id=?",
            (self.project_id, RULE_ID, scene_id),
        ).fetchone()
        if current:
            _need(tuple(current) == (outcome, report_sha256),
                  "EXPERIENCE_FEEDBACK_APPEND_ONLY")
        else:
            with self.conn:
                self.conn.execute("INSERT INTO wf_experience_feedback VALUES(?,?,?,?,?)",
                                  (self.project_id, RULE_ID, scene_id,
                                   outcome, report_sha256))
        counts = dict(self.conn.execute(
            "SELECT outcome,COUNT(*) FROM wf_experience_feedback "
            "WHERE project=? AND rule_id=? GROUP BY outcome",
            (self.project_id, RULE_ID)).fetchall())
        if counts.get("HARMED", 0) >= 2:
            with self.conn:
                self.conn.execute(
                    "UPDATE wf_experience_policies SET status='PAUSED_DUE_TO_HARM' "
                    "WHERE project=? AND rule_id=? AND status='EXPERIMENTAL_ACTIVE'",
                    (self.project_id, RULE_ID))
        return {
            "rule_id": RULE_ID,
            "observed_helped_count": counts.get("HELPED", 0),
            "observed_harmed_count": counts.get("HARMED", 0),
            "observed_inconclusive_count": counts.get("INCONCLUSIVE", 0),
            "source_reviews_are_attested_not_semantically_verified": True,
            "active_status": self.conn.execute(
                "SELECT status FROM wf_experience_policies "
                "WHERE project=? AND rule_id=?", (self.project_id, RULE_ID)
            ).fetchone()[0],
            "automatic_promotion": False,
        }
