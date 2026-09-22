from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ReviewerSpec:
    name: str
    receives: tuple[str, ...]
    forbidden: tuple[str, ...]
    purpose: str

REVIEWERS = (
    ReviewerSpec(
        "continuity",
        ("text","canon","character_state","timeline","items"),
        ("author_intent_explanation","other_reviewer_opinions"),
        "Find factual/state contradictions only."
    ),
    ReviewerSpec(
        "causality",
        ("text","causal_events","scene_contract"),
        ("author_intent_explanation","other_reviewer_opinions"),
        "Find missing triggers, consequences and coincidence dependence."
    ),
    ReviewerSpec(
        "reader",
        ("text",),
        ("canon","future_plan","author_intent_explanation","other_reviewer_opinions"),
        "Simulate a cold reader; report attention, questions and confusion."
    ),
    ReviewerSpec(
        "aesthetic",
        ("text","project_taste","voice_baseline"),
        ("future_plan","other_reviewer_opinions"),
        "Judge selection, rhythm, voice drift and over-completion."
    ),
)

def reviewer_payload(name: str, available: dict) -> dict:
    spec = next(r for r in REVIEWERS if r.name == name)
    return {k: available[k] for k in spec.receives if k in available}
