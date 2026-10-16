"""Display-only V28 trial scale: anchor the neutral baseline at 30 points.

This is NOT a model rating, absolute literary quality, or a new 90% gate.
It applies the SAME additive offset to both arms, preserving the signed
raw mean difference. Original five-dimensional scores remain unmodified.
"""
from __future__ import annotations

DIMENSIONS = ("perception","causality","information","continuity","language")
ANCHOR = 30.0


class ScaleError(ValueError):
    pass


def baseline_30_display(comparisons: dict) -> dict:
    if not isinstance(comparisons, dict) or set(comparisons) != {"baseline","skill"}:
        raise ScaleError("two genuine raw comparison arms required")
    raw = {}
    for arm in ("baseline","skill"):
        entry = comparisons[arm]
        if not isinstance(entry,dict) or not isinstance(entry.get("dimension_review"),dict):
            raise ScaleError("raw score dimensions missing")
        dims = entry["dimension_review"]
        if set(dims) != set(DIMENSIONS):
            raise ScaleError("raw dimensions incomplete")
        scores = []
        for dim in DIMENSIONS:
            item=dims[dim]
            if not isinstance(item,dict):
                raise ScaleError("score metadata malformed")
            n=item.get("score")
            if type(n) is not int or not 0<=n<=100:
                raise ScaleError("raw scores must be integers 0..100")
            scores.append(n)
        raw[arm]=sum(scores)/len(DIMENSIONS)
    shift=ANCHOR-raw["baseline"]
    return {
        "format":"writerforge.display-only-baseline30.v1",
        "unadjusted_model_mean":raw,
        "baseline_display_score":ANCHOR,
        "skill_display_score_unclipped":round(raw["skill"]+shift,2),
        "unadjusted_signed_delta":round(raw["skill"]-raw["baseline"],2),
        "offset_applied_to_both_arms":round(shift,2),
        "synthetic_anchor_not_model_judgement":True,
        "usable_for_mastery_or_human_evaluation":False,
        "first_window_passed":False,
        "second_window_unlocked":False,
    }
