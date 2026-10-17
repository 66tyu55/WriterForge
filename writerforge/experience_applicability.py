"""WF V50: candidate experience admission, NOT semantic literary scoring.

V49 failure: host Skill injected the FIRST unreviewed literary hypothesis
on every topic, including scenery-only tasks, and called it improvement.

V50 refuses to use memory unless its provenance is linked to a reviewed
source observation AND real project story state proves the intended scene is
a character-choice with a still-unknown fact. Uncertainty abstains.

All approval flags currently originate from existing WF data and are only
ATTESTATIONS, NOT verified independent-reader judgements. The runtime never
promotes a candidate or claims aesthetic improvement. No text model runs
here, and no literary prose examples are hard-coded.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
import re


class ExperienceAdmissionError(ValueError):
    pass


def _hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _decode(value, error):
    try:
        item = json.loads(value)
    except (ValueError, TypeError):
        raise ExperienceAdmissionError(error) from None
    if not isinstance(item, dict):
        raise ExperienceAdmissionError(error)
    return item


@dataclass(frozen=True)
class ExperienceAdmission:
    state: str
    cause: str
    candidate_sha: str | None = None
    applicability_sha: str | None = None
    guidance: str = ""

    def receipt(self) -> dict:
        return {
            "format": "writerforge.v50-experience-admission.v1",
            "state": self.state, "reason": self.cause,
            "candidate_sha256": self.candidate_sha,
            "applicability_sha256": self.applicability_sha,
            "advice_injected": bool(self.guidance),
            "source_review_is_only_attested": True,
            "semantic_correctness_verified": False,
            "literary_improvement_verified": False,
            "promoted": False,
        }


def choose_experience(db, row) -> ExperienceAdmission:
    """Read-only from existent WF SQLite, source trials and story state.

    Intended to be called in WRITE; no LEARN mutation, freeform examiner plan,
    new SQLite table, or auto-edit of the story. Queries are bounded.
    """
    project = row["project_id"]
    scene = row["scene_id"]
    lesson_raw = row["candidate_lesson_json"]
    if not lesson_raw:
        return ExperienceAdmission("ABSTAIN", "NO_SOURCE_LESSON")
    lesson = _decode(lesson_raw, "UNTRUSTED_SOURCE_LESSON")
    fields = {"hypothesis", "counterfactual",
              "transfer_question", "source_quote_sha256"}
    if (set(lesson) != fields or any(
            not isinstance(lesson.get(k), str) or not 12 <= len(lesson[k]) <= 800
            for k in fields - {"source_quote_sha256"}) or
            not re.fullmatch("[0-9a-f]{64}",
                             str(lesson.get("source_quote_sha256", "")))):
        return ExperienceAdmission("ABSTAIN", "SOURCE_LESSON_INVALID")

    # First check scene applicability. Scenery, environment reports and
    # dialogue-only scenes without supported character-choice state cannot
    # silently inherit character-sacrifice techniques.
    events = db.conn.execute(
        "SELECT payload_json FROM causal_events WHERE project_id=? "
        "ORDER BY event_id LIMIT 129", (project,),
    ).fetchall()
    if len(events) > 128:
        return ExperienceAdmission("ABSTAIN", "STORY_EVENT_BUDGET_EXCEEDED")
    matches = []
    for event in events:
        record = _decode(event["payload_json"], "CORRUPT_STORY_EVENT")
        if record.get("scene_id") == scene:
            matches.append(record)
    if not matches:
        return ExperienceAdmission("ABSTAIN", "NO_SCENE_FACTS")
    if len(matches) != 1:
        return ExperienceAdmission("ABSTAIN", "AMBIGUOUS_SCENE_FACTS")
    event = matches[0]
    if event.get("scene_type") != "character_choice":
        return ExperienceAdmission("ABSTAIN", "NOT_CHARACTER_CHOICE")
    if (event.get("narrative_role") not in ("setup", "decision") or
            event.get("review_status") != "confirmed"):
        return ExperienceAdmission("ABSTAIN", "UNCONFIRMED_NARRATIVE_ROLE")
    actor = event.get("actor_id")
    fact = event.get("fact_id")
    clue = event.get("clue_id")
    if not all(isinstance(x, str) and 2 <= len(x) <= 96
               for x in (actor, fact, clue)):
        return ExperienceAdmission("ABSTAIN", "MISSING_TYPED_ACTOR_OR_FACT")

    state_row = db.conn.execute(
        "SELECT state_json FROM character_state "
        "WHERE project_id=? AND character_id=?", (project, actor),
    ).fetchone()
    if not state_row:
        return ExperienceAdmission("ABSTAIN", "UNKNOWN_ACTOR_STATE")
    state = _decode(state_row["state_json"], "CORRUPT_CHARACTER_STATE")
    knowledge = state.get("knowledge")
    if not isinstance(knowledge, dict):
        return ExperienceAdmission("ABSTAIN", "NO_ACTOR_KNOWLEDGE")
    known, unknown = knowledge.get("known"), knowledge.get("unknown")
    if (not isinstance(known, list) or not isinstance(unknown, list)
            or len(known) > 48 or len(unknown) > 48 or
            not all(isinstance(x, str) and 1 <= len(x) <= 96
                    for x in known + unknown)):
        return ExperienceAdmission("ABSTAIN", "UNTRUSTED_ACTOR_KNOWLEDGE")
    if (set(known) & set(unknown)) or fact in known:
        return ExperienceAdmission("ABSTAIN", "FACT_KNOWN_OR_CONTRADICTED")
    if fact not in unknown:
        return ExperienceAdmission("ABSTAIN", "FACT_NOT_ACTUALLY_UNKNOWN")

    # A source-derived literary interpretation must be cross-checked against
    # the exact stored lesson, not blindly grab the first model explanation.
    source = db.conn.execute(
        "SELECT analysis_json,review_status,reviewer_reason "
        "FROM literary_scene_trials WHERE project_id=? AND scene_id=?",
        (project, scene),
    ).fetchone()
    if source is None:
        return ExperienceAdmission("ABSTAIN", "NO_SAME_SCENE_SOURCE_REVIEW")
    # Source learning usually uses scene_id also for production in V47.
    # Missing/invalid review => abstain; this cannot be bypassed by opt_in.
    if (source["review_status"] != "approved" or
            not source["reviewer_reason"] or
            len(source["reviewer_reason"].strip()) < 12):
        return ExperienceAdmission("ABSTAIN", "SOURCE_REVIEW_NOT_APPROVED")
    stored = _decode(source["analysis_json"], "CORRUPT_SOURCE_ANALYSIS")
    mechanisms = stored.get("mechanisms")
    if not isinstance(mechanisms, list) or len(mechanisms) > 4:
        return ExperienceAdmission("ABSTAIN", "NO_BOUNDED_SOURCE_MECHANISM")
    source_match = any(
        isinstance(m, dict)
        and all(m.get(k) == lesson[k]
                for k in ("hypothesis", "counterfactual", "transfer_question"))
        and isinstance(m.get("source_quote"), str)
        and _hash(m["source_quote"]) == lesson["source_quote_sha256"]
        for m in mechanisms
    )
    if not source_match:
        return ExperienceAdmission("ABSTAIN", "LESSON_NOT_IN_FROZEN_SOURCE")

    # An already confirmed payoff for the SAME clue cannot be retroactively
    # reassigned as a brand new setup. Disputed outcomes remain uncertain.
    for other in events:
        d = _decode(other["payload_json"], "CORRUPT_STORY_EVENT")
        if (d.get("clue_id") == clue and
                d.get("narrative_role") == "payoff" and
                d.get("review_status") == "confirmed"):
            return ExperienceAdmission("ABSTAIN", "CLUE_ALREADY_RESOLVED")

    boundary = json.dumps(
        {"actor": actor, "unknown_fact_id": fact, "clue_id": clue,
         "scene_id": scene}, ensure_ascii=False, sort_keys=True,
    )
    guidance = (
        "\n【WF仅在当前角色选择场景启用的候选经验（非文学定论）】"
        "\n适用性由既存人物知识与已确认事件状态约束："
        + boundary +
        "\n从学海保留的待验证写作策略：" +
        json.dumps({k: lesson[k] for k in
                    ("hypothesis", "counterfactual", "transfer_question")},
                   ensure_ascii=False, sort_keys=True) +
        "\n只在它适合人物当下信息时采用；不能强迫伏笔或牺牲，"
        "不能编造角色知道的事实。"
    )
    if len(guidance) > 1800:
        return ExperienceAdmission("ABSTAIN", "GUIDANCE_TOO_LARGE")
    return ExperienceAdmission(
        "ELIGIBLE_EXPERIMENT_ONLY",
        "SOURCE_AND_SCENE_STATE_MATCHED",
        _hash(lesson_raw), _hash(boundary), guidance,
    )
