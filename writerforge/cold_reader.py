from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ColdReaderInput:
    visible_text: str
    chapter_ref: str = ""
    prior_reader_questions: tuple[str, ...] = ()

def build_cold_reader_payload(*, text_so_far: str, chapter_ref: str="",
                              prior_reader_questions=()):
    """
    Deliberately excludes:
    - canon truth
    - future outline
    - author explanation
    - hidden character state
    - source-study analysis
    """
    return {
        "visible_text": text_so_far,
        "chapter_ref": chapter_ref,
        "prior_reader_questions": list(prior_reader_questions),
        "allowed_judgments": [
            "attention",
            "curiosity",
            "urge_to_continue",
            "confusion",
            "emotional_resonance",
            "character_attachment",
            "current_predictions",
            "current_questions",
            "stop_risk"
        ]
    }
