from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
from typing import Callable, Iterable


class TasteSource(str, Enum):
    SOURCE = "source_taste"
    ACTUAL_READER = "actual_reader"
    PROJECT = "project_taste"
    BETA_READER = "beta_reader"


TASTE_DIMENSIONS = (
    "reader_effect",
    "character_truth",
    "narrative_pressure",
    "specificity",
    "restraint",
    "surprise_inevitability",
    "voice",
    "aftertaste",
    "novelty",
    "long_term_echo",
)


@dataclass(frozen=True)
class TasteObservation:
    context: str
    preferred_id: str
    alternative_id: str
    reasons: tuple[str, ...]
    tradeoffs: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()
    source: TasteSource = TasteSource.PROJECT
    confidence: float = 0.5
    tags: tuple[str, ...] = ()


class TasteMemory:
    """Stores conditional preferences, never universal rules."""

    def __init__(self, db=None, project_id: str = "__system__"):
        self._items: list[TasteObservation] = []
        self.db = db
        self.project_id = project_id

    def add(self, obs: TasteObservation) -> None:
        self._items.append(obs)
        if self.db is not None:
            self.db.conn.execute(
                """INSERT INTO taste_observations(
                    project_id, source_type, context, preferred_id, alternative_id,
                    reasons_json, tradeoffs_json, conditions_json, confidence, tags_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    self.project_id, obs.source.value, obs.context, obs.preferred_id,
                    obs.alternative_id, json.dumps(obs.reasons, ensure_ascii=False),
                    json.dumps(obs.tradeoffs, ensure_ascii=False),
                    json.dumps(obs.conditions, ensure_ascii=False), float(obs.confidence),
                    json.dumps(obs.tags, ensure_ascii=False),
                ),
            )
            self.db.conn.commit()

    def query(self, *, tags: Iterable[str] = (), sources: Iterable[TasteSource] = ()) -> list[TasteObservation]:
        tagset = set(tags)
        source_set = set(sources)
        out = []
        for item in self._items:
            if source_set and item.source not in source_set:
                continue
            if tagset and not (tagset & set(item.tags)):
                continue
            out.append(item)
        return out


@dataclass(frozen=True)
class PairwiseJudgment:
    winner: str  # "A", "B", or "TIE"
    reasons: tuple[str, ...]
    confidence: float = 0.5


@dataclass(frozen=True)
class TasteDecision:
    stable: bool
    preferred_id: str | None
    reasons: tuple[str, ...]
    confidence: float
    warning: str | None = None


JudgeFn = Callable[[str, str, str], PairwiseJudgment]


class LiteraryTasteEngine:
    """
    Pairwise literary judgment, not absolute scoring.

    The judge runs twice with candidate order swapped. A flip is treated as judge
    instability and must not be promoted into Taste Memory.
    """

    @staticmethod
    def _original_winner(judgment: PairwiseJudgment, *, swapped: bool, a_id: str, b_id: str) -> str | None:
        w = judgment.winner.upper()
        if w == "TIE":
            return None
        if w not in {"A", "B"}:
            raise ValueError("winner must be A, B, or TIE")
        if not swapped:
            return a_id if w == "A" else b_id
        return b_id if w == "A" else a_id

    def compare(
        self,
        *,
        candidate_a_id: str,
        candidate_a: str,
        candidate_b_id: str,
        candidate_b: str,
        context: str,
        judge: JudgeFn,
    ) -> TasteDecision:
        first = judge(candidate_a, candidate_b, context)
        second = judge(candidate_b, candidate_a, context)
        first_winner = self._original_winner(first, swapped=False, a_id=candidate_a_id, b_id=candidate_b_id)
        second_winner = self._original_winner(second, swapped=True, a_id=candidate_a_id, b_id=candidate_b_id)

        if first_winner != second_winner:
            return TasteDecision(
                stable=False,
                preferred_id=None,
                reasons=tuple(first.reasons + second.reasons),
                confidence=min(first.confidence, second.confidence),
                warning="JUDGE_UNSTABLE: preference changed when candidate order was swapped",
            )

        return TasteDecision(
            stable=True,
            preferred_id=first_winner,
            reasons=tuple(first.reasons + second.reasons),
            confidence=min(first.confidence, second.confidence),
        )

    @staticmethod
    def can_learn(decision: TasteDecision, *, min_confidence: float = 0.60) -> bool:
        return bool(decision.stable and decision.preferred_id and decision.confidence >= min_confidence)
