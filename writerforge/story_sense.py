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
