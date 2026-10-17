"""V39 optional FUTURE causal ledger: prewrite actor knowledge -> action -> reveal.

Prewrite and postwrite are separate, immutable stage envelopes. Caller must
lock the prewrite SHA in private storage BEFORE drafting; this module alone
does not verify a timestamp. Host validates text, order, IDs and hashes,
NOT literary roles or the truth of a model's causal explanations.
"""
from __future__ import annotations

from hashlib import sha256
import json


FIELDS = {
    "clue_id", "actor_id", "clue_identity", "knowledge_before",
    "expected_observation", "belief_update", "action_condition",
    "planned_action", "planned_reveal", "alternative_explanation",
}
EVIDENCE_FIELDS = {
    "clue_id", "application_status", "observation_quote",
    "action_quote", "reveal_quote", "knowledge_as_written",
    "why_action_follows", "unresolved_semantic_risk",
}
STATUS = {"CLAIMED_APPLIED", "NOT_APPLIED", "UNCERTAIN"}


class KnowledgeLedgerError(ValueError):
    pass


def canonical(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(obj) -> str:
    return sha256(canonical(obj)).hexdigest()


def require(condition, code):
    if not condition:
        raise KnowledgeLedgerError(code)


def bounded_text(value, low=6, high=230):
    return isinstance(value, str) and low <= len(value.strip()) <= high


def validate_prewrite(ledger: dict) -> dict:
    require(isinstance(ledger, dict) and set(ledger) == {"clues"}
            and isinstance(ledger["clues"], list)
            and 1 <= len(ledger["clues"]) <= 8,
            "V39_PREWRITE_LEDGER_SCHEMA_INVALID")
    ids = set()
    for cue in ledger["clues"]:
        require(isinstance(cue, dict) and set(cue) == FIELDS,
                "V39_PREWRITE_CUE_FIELDS_INVALID")
        clue_id = cue["clue_id"]
        require(isinstance(clue_id, str) and clue_id.startswith("C")
                and len(clue_id) <= 12 and clue_id[1:].isdigit()
                and clue_id not in ids,
                "V39_PREWRITE_CUE_ID_INVALID_OR_DUPLICATE")
        ids.add(clue_id)
        require(all(bounded_text(value) for key, value in cue.items()
                    if key != "clue_id"),
                "V39_PREWRITE_CHARACTER_STATE_NOT_BOUNDED")
    return {
        "format": "writerforge.v39-knowledge-action-prewrite.v1",
        "prewrite_ledger_sha256": digest(ledger),
        "clue_ids": sorted(ids),
        "must_be_committed_before_draft_by_external_stage_envelope": True,
        "semantic_truth_or_reader_effect_proven": False,
    }


def _quote_pos(story: str, quote: str) -> tuple[int, int]:
    require(isinstance(quote, str) and 10 <= len(quote) <= 100,
            "V39_POSTWRITE_QUOTE_LENGTH_INVALID")
    require(story.count(quote) == 1,
            "V39_POSTWRITE_QUOTE_MISSING_OR_REPEATED")
    start = story.find(quote)
    return (start, start + len(quote))


def verify_postwrite(*, frozen_ledger: dict, locked_sha256: str,
                     draft: str, evidence: list[dict]) -> dict:
    pre = validate_prewrite(frozen_ledger)
    require(isinstance(locked_sha256, str)
            and locked_sha256 == pre["prewrite_ledger_sha256"],
            "V39_PREWRITE_SHA_CHANGED_AFTER_DRAFT")
    require(isinstance(draft, str) and 350 <= len(draft) <= 4500,
            "V39_POSTWRITE_DRAFT_INVALID")
    require(isinstance(evidence, list)
            and len(evidence) == len(frozen_ledger["clues"]),
            "V39_POSTWRITE_CUE_COVERAGE_MISSING")
    expected = set(pre["clue_ids"])
    seen = set()
    out = []
    for item in evidence:
        require(isinstance(item, dict) and set(item) == EVIDENCE_FIELDS,
                "V39_POSTWRITE_EVIDENCE_SCHEMA_INVALID")
        clue_id = item["clue_id"]
        require(clue_id in expected and clue_id not in seen,
                "V39_POSTWRITE_CUE_ID_NOT_BOUND_OR_DUPLICATE")
        seen.add(clue_id)
        status = item["application_status"]
        require(status in STATUS,
                "V39_POSTWRITE_APPLICATION_STATUS_INVALID")
        for key in ("knowledge_as_written", "why_action_follows",
                    "unresolved_semantic_risk"):
            require(bounded_text(item[key], 12, 260),
                    "V39_POSTWRITE_CAUSAL_EXPLANATION_MISSING")
        three = (item["observation_quote"], item["action_quote"],
                 item["reveal_quote"])
        if status == "CLAIMED_APPLIED":
            positions = [_quote_pos(draft, quote) for quote in three]
            require(positions[0][1] <= positions[1][0]
                    and positions[1][1] < positions[2][0],
                    "V39_POSTWRITE_KNOWLEDGE_ACTION_REVEAL_ORDER_INVALID")
            # No single real quote can stand in for both setup and action.
            require(len(set(three)) == 3,
                    "V39_POSTWRITE_ONE_QUOTE_MULTIPLE_CAUSAL_ROLES")
            anchors = [
                {"quote_sha256": sha256(q.encode("utf-8")).hexdigest(),
                 "offset_start": p[0], "offset_end": p[1]}
                for q, p in zip(three, positions)
            ]
        else:
            require(all(q is None for q in three),
                    "V39_POSTWRITE_UNCERTAIN_MUST_NOT_FORGE_ANCHORS")
            anchors = None
        out.append({
            "clue_id": clue_id,
            "application_status": status,
            "anchored_observation_action_reveal": anchors,
            "knowledge_explanation_sha256":
                sha256(item["knowledge_as_written"].encode()).hexdigest(),
            "action_cause_explanation_sha256":
                sha256(item["why_action_follows"].encode()).hexdigest(),
            "uncertainty_explanation_sha256":
                sha256(item["unresolved_semantic_risk"].encode()).hexdigest(),
            "same_clue_and_actor_semantically_verified": False,
            "actual_action_motivated_by_clue_independently_verified": False,
        })
    require(seen == expected, "V39_POSTWRITE_CUE_COVERAGE_MISSING")
    out.sort(key=lambda x: x["clue_id"])
    return {
        "format": "writerforge.v39-causal-ledger-afterdraft.v1",
        "frozen_prewrite_ledger_sha256": locked_sha256,
        "actual_draft_sha256": sha256(draft.encode()).hexdigest(),
        "checks": out,
        "all_precommitted_clues_checked": True,
        "textual_chain_claimed_count":
            sum(x["application_status"] == "CLAIMED_APPLIED" for x in out),
        "independent_literary_semantic_validation": False,
        "cannot_promote_lesson_or_retroactively_rewrite_prewrite": True,
    }
