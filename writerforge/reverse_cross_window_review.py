"""Hash-verified cross-window comparison of two already-saved V28 A/B receipts.

Pure analysis. No models, source prose, drafts, free-form critiques, or promotion.
"""
from __future__ import annotations
from hashlib import sha256
import json

from .reverse_ab_candidates import derive_unverified_candidates, CandidateEvidenceError
from .reverse_score_scale import baseline_30_display

def _canon(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False,
                      allow_nan=False).encode("utf-8")

def compare_existing_chapters(v5:dict,v6:dict,*,v5_sha:str,v6_sha:str) -> dict:
    old=derive_unverified_candidates(v5,receipt_sha256=v5_sha)
    new=derive_unverified_candidates(v6,receipt_sha256=v6_sha)
    cursor=v6.get("source_cursor_diagnostic")
    if (not isinstance(cursor,dict) or cursor.get("chapter")!=2 or
        cursor.get("ordinal")!=1 or cursor.get("diagnostic_only_no_promotion") is not True or
        cursor.get("earlier_first_window")!="NOT_PASSED" or
        cursor.get("second_curriculum_window")!="LOCKED" or
        cursor.get("chapter_headers_sequential") is not True or
        cursor.get("full_body_reconstructed") is not True or
        cursor.get("source_window_sha256") != v6.get("source_unit_sha256") or
        cursor.get("next_contiguous_sha256") != v6.get("next_unit_sha256") or
        cursor.get("chapter_body_sha256") !=
        "46acf29ea47e63b0a47a18413260a689bcaf9a9f1284338a2cebc4771428956e"):
        raise CandidateEvidenceError("missing later-window diagnostic provenance")
    if (old["work"]!=new["work"] or old["edition_sha256"]!=new["edition_sha256"]
        or old["writer_model"]!=new["writer_model"] or
        old["unit_sha256"]==new["unit_sha256"]):
        raise CandidateEvidenceError("not same book/model with distinct source window")
    if not old["critic_source_blind"] or not new["critic_source_blind"]:
        raise CandidateEvidenceError("critic must be source-blind for both")
    if (v5.get("writing_task_sha256") != v6.get("writing_task_sha256")
        or v5.get("writing_task_sha256") is None):
        raise CandidateEvidenceError("original writing assignment changed")
    if old["mechanism_hypotheses_unreviewed"]!=sorted(
        x["technique_id"] for x in v5["planner_mechanisms_unreviewed"]):
        raise CandidateEvidenceError("old mechanisms changed")
    a=baseline_30_display(v5["comparisons"])
    b=baseline_30_display(v6["comparisons"])
    old_effect=a["unadjusted_signed_delta"]
    new_effect=b["unadjusted_signed_delta"]
    old_skill=a["unadjusted_model_mean"]["skill"]
    new_skill=b["unadjusted_model_mean"]["skill"]
    old_base=a["unadjusted_model_mean"]["baseline"]
    new_base=b["unadjusted_model_mean"]["baseline"]
    dims={}
    for dim in ("perception","causality","information","continuity","language"):
        dims[dim]={
            "baseline_shift":new["model_scores"]["baseline"][dim]-old["model_scores"]["baseline"][dim],
            "skill_shift":new["model_scores"]["skill"][dim]-old["model_scores"]["skill"][dim],
            "ab_delta_shift":new["model_deltas"][dim]-old["model_deltas"][dim],
        }
    result={
        "format":"writerforge.cross-chapter-unverified-diagnostic.v1",
        "old_receipt_sha256":v5_sha,"new_receipt_sha256":v6_sha,
        "edition_sha256":old["edition_sha256"],
        "task_sha256":v6["writing_task_sha256"],
        "old_unit_sha256":old["unit_sha256"],
        "new_unit_sha256":new["unit_sha256"],
        "source_chapter_old":1,"source_chapter_new":2,
        "writer_model":new["writer_model"],
        "same_task_and_model":True,
        "before":{"baseline_mean":old_base,"skill_mean":old_skill,"ab_delta":old_effect},
        "after":{"baseline_mean":new_base,"skill_mean":new_skill,"ab_delta":new_effect},
        "enhanced_mean_change":round(new_skill-old_skill,2),
        "baseline_mean_change":round(new_base-old_base,2),
        "ab_effect_change":round(new_effect-old_effect,2),
        "dimension_changes":dims,
        "selected_mechanisms_before":old["mechanism_hypotheses_unreviewed"],
        "selected_mechanisms_after":new["mechanism_hypotheses_unreviewed"],
        "same_mechanisms":old["mechanism_hypotheses_unreviewed"]==new["mechanism_hypotheses_unreviewed"],
        "sharp_model_rated_skill_drop_10_or_more":new_skill<=old_skill-10,
        "negative_model_rated_new_ab_effect":new_effect<0,
        "only_single_repeat_no_causal_conclusion":True,
        "cannot_prove_cross_chapter_long_term_memory":True,
        "new_source_held_for_diagnostic_not_curriculum_unlock":True,
        "first_window_passed":False,"second_window_unlocked":False,
        "human_review_performed":False,"core_promoted":False,
        "retain_previous_evidence_immutable":True,
        "new_chapter_mechanisms_quarantined_pending_independent_review":True,
    }
    if len(_canon(result))>8192:
        raise CandidateEvidenceError("bounded cross-chapter report too large")
    return result
