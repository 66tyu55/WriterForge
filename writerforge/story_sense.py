from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


_SCOPE_WEIGHT = {"line": 1.0, "paragraph": 1.2, "scene": 1.6, "chapter": 2.0, "arc": 2.6, "book": 3.2}


@dataclass(frozen=True)
class LiterarySignal:
    code: str
    domain: str
    severity: int
    scope: str
    evidence: str
    confidence: float = 0.7


@dataclass(frozen=True)
class StorySenseDecision:
    primary: LiterarySignal | None
    supporting: tuple[LiterarySignal, ...]
    deferred: tuple[LiterarySignal, ...]
    rule: str = "Diagnose the dominant literary problem; do not activate every valid critique at once."


class StorySenseRouter:
    """Chooses one dominant literary intervention instead of checklist overload."""

    def diagnose(self, signals: Iterable[LiterarySignal], *, max_supporting: int = 2) -> StorySenseDecision:
        items = list(signals)
        if not items:
            return StorySenseDecision(None, (), ())

        def score(s: LiterarySignal) -> float:
            return max(0, s.severity) * max(0.0, min(1.0, s.confidence)) * _SCOPE_WEIGHT.get(s.scope, 1.0)

        ordered = sorted(items, key=lambda s: (-score(s), s.domain, s.code))
        primary = ordered[0]
        supporting = tuple(ordered[1:1 + max(0, max_supporting)])
        deferred = tuple(ordered[1 + max(0, max_supporting):])
        return StorySenseDecision(primary, supporting, deferred)


@dataclass(frozen=True)
class EndingBacktraceInput:
    """Evidence about whether an ending grows from the story that actually preceded it."""
    central_question_resolved: bool
    protagonist_choice_drives_resolution: bool
    payoff_elements: tuple[str, ...] = ()
    established_setups: tuple[str, ...] = ()
    opens_new_major_questions: int = 0
    explicit_theme_explanation: bool = False
    final_image_echo: bool = False
    route_subverts_surface_expectation: bool = False
    irreversible_cost_or_change: bool = True


@dataclass(frozen=True)
class EndingBacktraceResult:
    traceable: bool
    surprising: bool
    resonant: bool
    missing_setups: tuple[str, ...]
    issues: tuple[str, ...]
    rule: str = "Trace the ending backward through promises, character choice, and established causes; fix upstream when the ending has no roots."


class EndingBacktraceAnalyzer:
    """Diagnoses ending failures without inventing or choosing an ending."""

    def analyze(self, evidence: EndingBacktraceInput) -> EndingBacktraceResult:
        setup = set(evidence.established_setups)
        missing = tuple(sorted(x for x in evidence.payoff_elements if x not in setup))
        issues: list[str] = []
        if missing:
            issues.append("PAYOFF_WITHOUT_SETUP")
        if not evidence.protagonist_choice_drives_resolution:
            issues.append("UNEARNED_RESOLUTION")
        if not evidence.central_question_resolved:
            issues.append("CORE_QUESTION_UNRESOLVED")
        if evidence.opens_new_major_questions > 0:
            issues.append("ENDING_EXPANDS")
        if evidence.explicit_theme_explanation:
            issues.append("ENDING_OVEREXPLAINS")
        if not evidence.irreversible_cost_or_change:
            issues.append("ENDING_WITHOUT_IRREVERSIBLE_CHANGE")

        traceable = not missing and evidence.protagonist_choice_drives_resolution and evidence.central_question_resolved
        surprising = bool(evidence.route_subverts_surface_expectation)
        resonant = bool(evidence.final_image_echo or evidence.irreversible_cost_or_change)
        return EndingBacktraceResult(traceable, surprising, resonant, missing, tuple(issues))
