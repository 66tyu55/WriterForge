"""V85 strict LEARN evidence boundary; reuses FactJournal, not a second graph.

A source locator and bitemporal KNOWLEDGE record are necessary checks, not
proof of literary meaning. Proposals arrive only in a trusted, sealed PASS-B
context, with the exact already-read private source windows held in memory.
Persisted receipts contain hashes/offsets and SHA of explanations, not prose.

This module does not write FactJournal, R2, Writer prompts or skill levels.
The caller owns source verification, PASS-A sealing and optional immutable
CAS sidecar storage. Legacy reading is unchanged until explicitly opted in.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re

from .fact_journal import FactJournal

FORMAT = "wf.learn.literary-evidence.v85"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,79}\Z")
KINDS = frozenset(("CAUSAL", "FORESHADOWING", "CHARACTER"))
STATES = frozenset(("KNOWN", "UNKNOWN", "FALSE", "DISPUTED",
                    "UNRECORDED", "CONFLICT_UNRESOLVED"))
CLAIM_FIELDS = frozenset((
    "claim_id", "source_sha256", "chapter", "kind", "actor_id",
    "fact_id", "story_tick", "claimed_knowledge_state", "observation",
    "consequence", "hypothesis", "alternative", "falsifier", "uncertainty"
))
ANCHOR_FIELDS = frozenset(("unit", "start", "end", "quote"))
MAX_UNITS = 80
MAX_CLAIMS = 6
MAX_EXPLANATION = 240
MAX_AUDIT_JSON_BYTES = 8192


class LiteraryEvidenceError(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise LiteraryEvidenceError(code)


def is_sha(value):
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def is_id(value):
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def digest_text(value):
    return sha256(value.encode("utf-8")).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _explanation(value, field):
    need(isinstance(value, str) and
         12 <= len(value.strip()) <= MAX_EXPLANATION and
         "\x00" not in value and
         not any(ord(c) < 32 and c not in "\n\r\t" for c in value),
         "WF_V85_" + field.upper() + "_UNBOUNDED")
    return digest_text(value.strip())


def _anchor(value, windows, read_frontier):
    need(type(value) is dict and set(value) == ANCHOR_FIELDS,
         "WF_V85_ANCHOR_SCHEMA_INVALID")
    unit, start, end, quote = (
        value["unit"], value["start"], value["end"], value["quote"])
    need(type(unit) is int and 1 <= unit <= read_frontier and
         type(start) is int and type(end) is int and
         isinstance(quote, str) and 8 <= len(quote) <= 120,
         "WF_V85_ANCHOR_FUTURE_OR_BOUNDS")
    original = windows[unit - 1]
    need(0 <= start < end <= len(original) and
         end - start == len(quote) and original[start:end] == quote,
         "WF_V85_ANCHOR_NOT_EXACT_SOURCE_SPAN")
    return {
        "unit": unit,
        "source_unit_sha256": digest_text(original),
        "start": start, "end": end,
        "span_sha256": digest_text(quote),
    }


class LiteraryEvidenceGate:
    """A frozen read-only FactJournal snapshot, scoped to one story/scene.

    ledger_seq MUST be captured before the planner sees new prose; a
    later disclosure cannot upgrade an earlier character's knowledge.
    Textual reasoning is never converted into a VERIFIED claim by this gate.
    """

    def __init__(self, journal: FactJournal, *, story_id: str,
                 scene_id: str, source_sha256: str, ledger_seq: int):
        need(isinstance(journal, FactJournal),
             "WF_V85_FACT_JOURNAL_REQUIRED")
        need(is_id(story_id) and is_id(scene_id) and
             is_sha(source_sha256), "WF_V85_SOURCE_ID_INVALID")
        need(type(ledger_seq) is int and 1 <= ledger_seq <= journal.ledger_head(),
             "WF_V85_LEDGER_SNAPSHOT_INVALID")
        need(journal._bound_story(scene_id) == story_id,
             "WF_V85_UNREGISTERED_OR_OTHER_STORY")
        self.journal = journal
        self.story_id = story_id
        self.scene_id = scene_id
        self.source_sha256 = source_sha256
        self.ledger_seq = ledger_seq

    def audit(self, proposals, *, source_windows: tuple[str, ...],
              chapter: int, chapter_body_sha256: str,
              first_read_seal_sha256: str, read_frontier: int):
        need(type(chapter) is int and 1 <= chapter <= 2000 and
             is_sha(chapter_body_sha256) and
             is_sha(first_read_seal_sha256),
             "WF_V85_CHAPTER_OR_SEAL_INVALID")
        need(type(source_windows) is tuple and
             2 <= len(source_windows) <= MAX_UNITS and
             all(isinstance(x, str) and 30 <= len(x) <= 900
                 for x in source_windows) and
             digest_text("".join(source_windows)) == chapter_body_sha256,
             "WF_V85_CHAPTER_SOURCE_MISMATCH")
        need(type(read_frontier) is int and
             read_frontier == len(source_windows),
             "WF_V85_PASS_A_FRONTIER_NOT_SEALED")
        need(isinstance(proposals, list) and
             len(proposals) <= MAX_CLAIMS,
             "WF_V85_CLAIM_COUNT_UNBOUNDED")
        results = []
        seen = set()
        for proposal in proposals:
            need(type(proposal) is dict and
                 set(proposal) == CLAIM_FIELDS,
                 "WF_V85_CLAIM_SCHEMA_INVALID")
            claim_id = proposal["claim_id"]
            need(is_id(claim_id) and claim_id not in seen,
                 "WF_V85_CLAIM_ID_REPEATED_OR_INVALID")
            seen.add(claim_id)
            need(proposal["source_sha256"] == self.source_sha256 and
                 type(proposal["chapter"]) is int and
                 proposal["chapter"] == chapter,
                 "WF_V85_CLAIM_CROSS_SOURCE_OR_CHAPTER")
            need(isinstance(proposal["kind"],str) and
                 proposal["kind"] in KINDS and
                 is_id(proposal["actor_id"]) and
                 is_id(proposal["fact_id"]) and
                 type(proposal["story_tick"]) is int and
                 0 <= proposal["story_tick"] <= 10000000 and
                 isinstance(proposal["claimed_knowledge_state"],str) and
                 proposal["claimed_knowledge_state"] in STATES,
                 "WF_V85_CLAIM_TIME_OR_ID_INVALID")
            # Explicit canonical actor identity prevents unrelated chapters
            # or a different novel's identically named actor being imported.
            need(self.journal._bound_subject(
                self.scene_id, "ACTOR", proposal["actor_id"]) is not None,
                "WF_V85_CHARACTER_IDENTITY_NOT_BOUND")
            observation = _anchor(
                proposal["observation"], source_windows, read_frontier)
            consequence = proposal["consequence"]
            if proposal["kind"] in ("CAUSAL", "FORESHADOWING"):
                need(consequence is not None,
                     "WF_V85_SECOND_ANCHOR_REQUIRED")
            if consequence is not None:
                consequence = _anchor(
                    consequence, source_windows, read_frontier)
                need((observation["unit"], observation["start"],
                      observation["end"]) !=
                     (consequence["unit"], consequence["start"],
                      consequence["end"]),
                     "WF_V85_SAME_ANCHOR_CANNOT_PROVE_LINK")
            # Recorded order and fictional story time are not interchangeable.
            # Existing graph links are POSSIBLE, not semantic proof.
            state = self.journal.temporal_view(
                scene=self.scene_id, story_id=self.story_id,
                scope="ACTOR", subject=proposal["actor_id"],
                fact=proposal["fact_id"],
                story_tick=proposal["story_tick"],
                as_of_ledger_seq=self.ledger_seq)
            need(state["as_of_ledger_seq"] == self.ledger_seq,
                 "WF_V85_LEDGER_SNAPSHOT_CHANGED")
            need(state["state"] == proposal["claimed_knowledge_state"],
                 "WF_V85_ACTOR_KNOWLEDGE_CONTRADICTS_FROZEN_LEDGER")
            explanations = {field + "_sha256": _explanation(
                proposal[field], field)
                for field in ("hypothesis", "alternative", "falsifier",
                              "uncertainty")}
            actual = state["state"]
            results.append({
                "claim_id": claim_id, "kind": proposal["kind"],
                "source_sha256": self.source_sha256, "chapter": chapter,
                "observation": observation, "consequence": consequence,
                "actor_id": proposal["actor_id"],
                "fact_id": proposal["fact_id"],
                "story_tick_claimed_by_model": proposal["story_tick"],
                "story_time_independently_verified": False,
                "actor_knowledge_state_as_of_snapshot": actual,
                "actor_knowledge_source_claim_ids": state["active_claim_ids"],
                "actor_knowledge_is_a_typed_claim_not_literary_truth": True,
                "evidence_relation_kind": "SOURCE_ANCHORED_HYPOTHESIS_ONLY",
                "context_status": (
                    "UNRESOLVED_OR_ABSTAIN" if actual in (
                        "UNRECORDED", "UNKNOWN", "DISPUTED",
                        "CONFLICT_UNRESOLVED")
                    else "TYPED_CONTEXT_PRESENT_SEMANTIC_UNVERIFIED"),
                "source_order_proves_causality": False,
                "future_reveal_verified": False,
                "falsifier_future_test_performed": False,
                **explanations,
            })
        audit = {
            "format": FORMAT, "source_sha256": self.source_sha256,
            "chapter": chapter, "chapter_body_sha256": chapter_body_sha256,
            "pass_a_seal_sha256": first_read_seal_sha256,
            "story_id": self.story_id, "scene_id": self.scene_id,
            "ledger_snapshot_seq": self.ledger_seq,
            "claims": results,
            "claims_count": len(results),
            "result": "PROVISIONAL_CLAIMS" if results else "ABSTAIN_NO_CLAIMS",
            "exact_source_anchor_checked": True,
            "original_prose_or_explanations_retained": False,
            "frozen_actor_knowledge_view_used": True,
            "literary_semantics_independently_verified": False,
            "eligible_to_direct_writing": False,
            "skill_promotion_approved": False,
            "paid_model_calls": 0,
            "reader_future_prose_exposure_independently_verified": False,
        }
        raw = canonical(audit)
        need(len(raw) <= MAX_AUDIT_JSON_BYTES,
             "WF_V85_RECEIPT_TOO_LARGE")
        return {**audit, "receipt_sha256": sha256(raw).hexdigest()}
