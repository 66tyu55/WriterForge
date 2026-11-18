"""V39 zero-model audit of the *frozen* V35/V38 L2 case.

Reads original R2 evidence with immutable SHA checks. This is not a literary
classifier. A later quote is not automatically a payoff, and a sentence
between two quotes is not automatically a character decision. Never log
unpublished prose, author explanations, source excerpts or API credentials.
"""
from __future__ import annotations

import json

from writerforge.r2_storage import R2Config, R2StudyVault, _canonical
from writerforge.v35_observable_trace import sha
from scripts.forensic_v37_xiyouji_L2 import frozen_evidence, sentence_menu
from scripts.audit_v38_l2_student_vs_critics import (
    compare as prior_crosswalk, exact_sentence_at, _read,
    SELF_ROOT, SELF_SESSION, SELF_SHA,
)

ROOT = "writerforge/v1/examiner/v39-frozen-L2-knowledge-causality"
REVIEW_IDS = (
    "R02", "R29", "R34", "R35", "R37", "R38", "R39",
    "R40", "R41", "R42", "R43", "R44",
)
MAX_BYTES = 18000


class CausalAuditError(ValueError):
    pass


def structural_timeline(original: str, revised: str,
                        setup_offset: int, payoff_offset: int) -> dict:
    """Host-proven ordering and quote identity, NO semantic inference."""
    if type(setup_offset) is not int or type(payoff_offset) is not int:
        raise CausalAuditError("V39_OFFSETS_NOT_INTEGERS")
    if not 0 <= setup_offset < payoff_offset < len(revised):
        raise CausalAuditError("V39_OFFSETS_NOT_IN_FROZEN_ORDER")
    revised_menu = sentence_menu(revised, "R")
    setup = exact_sentence_at(revised_menu, setup_offset)
    payoff = exact_sentence_at(revised_menu, payoff_offset)
    if setup["id"] == payoff["id"]:
        raise CausalAuditError("V39_SAME_SENTENCE_NOT_SETUP_AND_PAYOFF")
    number = {x["id"]: i for i, x in enumerate(revised_menu)}
    if number[setup["id"]] >= number[payoff["id"]]:
        raise CausalAuditError("V39_REVISED_SENTENCE_ORDER_INVALID")
    originals = sentence_menu(original, "I")
    original_texts = [x["text"] for x in originals]
    anchors = []
    for ident in REVIEW_IDS:
        if ident not in number:
            continue
        s = revised_menu[number[ident]]
        anchors.append({
            "sentence_id": ident,
            "sentence_sha256": s["text_sha256"],
            "character_start": s["start"],
            "character_end": s["end"],
            "found_as_exact_sentence_in_original_draft": s["text"] in original_texts,
            "before_R39": s["start"] < setup["start"],
            "after_R39": s["start"] > setup["start"],
            "is_R43_or_later": s["start"] >= payoff["start"],
        })
    between = [x["id"] for x in revised_menu
               if setup["end"] <= x["start"] and x["end"] <= payoff["start"]]
    return {
        "revised_draft_sha256": sha(revised),
        "original_draft_sha256": sha(original),
        "setup_id": setup["id"],
        "payoff_id": payoff["id"],
        "setup_offset": setup_offset,
        "payoff_offset": payoff_offset,
        "sentences_strictly_between": between,
        "candidate_anchor_sentence_metadata": anchors,
        "host_confirmed_sentence_identity_and_order": True,
        "same_clue_identity_proven": False,
        "knowledge_before_setup_proven": False,
        "knowledge_changed_at_setup_proven": False,
        "decision_caused_by_setup_proven": False,
        "R43_resolves_R39_rather_than_earlier_clue_proven": False,
        "semantic_status": "UNDETERMINED_REQUIRES_PRIVATE_CLOSE_READING",
    }


def audit(vault, *, persist: bool = True) -> dict:
    if vault.config.bucket != "writerforge-private-library":
        raise CausalAuditError("V39_PRIVATE_R2_ONLY")
    frozen = frozen_evidence(vault)
    cross = prior_crosswalk(vault, persist=False)
    self_record = _read(
        vault, f"{SELF_ROOT}/{SELF_SESSION}/result-{SELF_SHA}.json",
        SELF_SHA, 30000,
    )
    if (self_record.get("status") != "APPENDED_STRICT_TEXTUAL_EVIDENCE_ONLY"
            or self_record.get("history_never_rewritten") is not True
            or cross.get("self_review_report_sha256") != SELF_SHA
            or cross.get("self_setup_sentence_id") != "R39"
            or cross.get("self_payoff_sentence_id") != "R43"):
        raise CausalAuditError("V39_FROZEN_SELF_CROSSWALK_MISMATCH")
    claim = self_record["strict_validated_aftercheck"][
        "full_validated_aftercheck"]["learned_transfer_evidence"]["evidence_claims"][0]
    if (claim.get("application_claim") != "CLAIMED_APPLIED"
            or claim.get("source_lesson_id") != "L2"
            or claim.get("frozen_plan_angle") != "foreshadowing"):
        raise CausalAuditError("V39_NOT_THE_SAME_SOURCE_LINKED_L2")
    times = claim["actual_text_positions"]
    timeline = structural_timeline(
        frozen["original_draft"], frozen["revised_draft"],
        times["setup_offset"], times["payoff_offset"],
    )
    if (timeline["setup_id"] != "R39" or timeline["payoff_id"] != "R43"
            or timeline["revised_draft_sha256"] !=
            cross["frozen_revision_sha256"]):
        raise CausalAuditError("V39_REAL_CITATIONS_CHANGED")
    valid_critic_conflicts = cross["source_linked_learning_role_conflict"][
        "valid_reviewers_who_label_self_setup_as_payoff"]
    incomplete_critic_conflicts = cross["source_linked_learning_role_conflict"][
        "incomplete_reviewers_same_sentence_conflict"]
    if (valid_critic_conflicts != ["deepseek-v4-pro-0813"]
            or "minimax-m3" not in incomplete_critic_conflicts):
        raise CausalAuditError("V39_OLD_REVIEWER_STATUS_CHANGED")
    result = {
        "format": "writerforge.v39-frozen-L2-causal-knowledge-audit.v1",
        "original_v38_self_report_sha256": SELF_SHA,
        "original_v38_crosswalk_sha256":
            "e2ed24abc352daef678165de8bee5f7c283f5709cf3a23c9fe99b9a876aeb0db",
        "frozen_original_stage_sha256s": frozen["stage_sha256s"],
        "original_v38_student_claim": "R39_SETUP_R43_PAYOFF",
        "full_protocol_valid_reviewers_label_R39_as_payoff":
            valid_critic_conflicts,
        "incomplete_protocol_reviewers_label_R39_as_payoff_for_reference":
            incomplete_critic_conflicts,
        "timeline": timeline,
        "prewrite_L2_foreshadowing_decision_exists": True,
        "prewrite_typed_actor_clue_action_ledger_exists": False,
        "retrospective_knowledge_explanation_sha256":
            claim["character_knowledge_explanation_sha256"],
        "retrospective_cause_explanation_sha256":
            claim["causal_connection_explanation_sha256"],
        "retrospective_explanations_are_NOT_prewrite_or_semantic_proof": True,
        "unresolved_questions": [
            "IS_THE_CLUE_ALREADY_INTRODUCED_BEFORE_R39",
            "WHICH_CHARACTER_KNEW_WHAT_BEFORE_R39",
            "DOES_R39_CHANGE_AN_OBSERVABLE_BELIEF_OR_CHOICE",
            "WHICH_EXACT_ACTION_FOLLOWS_FROM_THAT_CHANGE",
            "DOES_R43_RESOLVE_R39_OR_AN_EARLIER_CLUE",
            "CAN_R39_BE_PAYOFF_AND_NEW_SETUP_SIMULTANEOUSLY",
        ],
        "allowed_semantic_roles": [
            "SETUP", "PAYOFF", "REPETITION", "BOTH", "UNDETERMINED"
        ],
        "role_adjudication": "CONTESTED_NOT_RESOLVED",
        "human_semantic_reading_performed": False,
        "model_calls": 0,
        "paid_retraining": False,
        "historical_evidence_mutated": False,
        "first_window": "NOT_PASSED",
        "second_window": "LOCKED",
        "formal_skill_promoted": False,
    }
    raw = _canonical(result)
    if len(raw) > MAX_BYTES:
        raise CausalAuditError("V39_PRIVATE_AUDIT_TOO_LARGE")
    digest = sha(raw)
    if persist:
        key = f"{ROOT}/audits/{digest}.json"
        vault._put_small_immutable(key, raw, digest)
        if vault._get_small(key, MAX_BYTES) != raw:
            raise CausalAuditError("V39_R2_IMMUTABLE_READBACK_FAILED")
    public = {
        "stage": "V39_R39_R43_ACTUAL_ZERO_MODEL_KNOWLEDGE_CAUSALITY_AUDIT",
        "private_report_sha256": digest,
        "persisted": persist,
        "frozen_essay_sha256": timeline["revised_draft_sha256"],
        "self_claim": ["R39", "R43"],
        "intervening_sentence_ids": timeline["sentences_strictly_between"],
        "role_adjudication": result["role_adjudication"],
        "knowledge_change_proven": False,
        "action_causation_proven": False,
        "R43_target_proven": False,
        "old_history_unchanged": True,
        "model_calls": 0,
        "formal_promotion": False,
    }
    print(json.dumps(public, ensure_ascii=False, sort_keys=True))
    return result


if __name__ == "__main__":
    audit(R2StudyVault(R2Config.from_environment()))
