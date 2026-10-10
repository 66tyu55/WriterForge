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
        if self.db is None:
            self._items.append(obs)
            # The process-local fallback is bounded too; no silent infinite heap.
            del self._items[:-256]
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

    def query(self, *, tags: Iterable[str] = (), sources: Iterable[TasteSource] = (),
              limit: int = 64) -> list[TasteObservation]:
        """Rehydrate from SQLite on every DB-backed query; bounded across restarts."""
        if not 1 <= limit <= 256:
            raise ValueError("taste query limit must be 1..256")
        tagset = set(tags)
        source_set = set(sources)
        if self.db is not None:
            # Each call is a bounded read; don't grow an unbounded in-memory
            # duplicate of an already durable project preference store.
            rows = self.db.conn.execute(
                """SELECT source_type,context,preferred_id,alternative_id,
                          reasons_json,tradeoffs_json,conditions_json,confidence,tags_json
                   FROM taste_observations WHERE project_id=?
                   ORDER BY id DESC LIMIT ?""",
                (self.project_id, min(256, limit*4)),
            ).fetchall()
            candidates = [
                TasteObservation(
                    context=r["context"],preferred_id=r["preferred_id"],
                    alternative_id=r["alternative_id"],
                    reasons=tuple(json.loads(r["reasons_json"])),
                    tradeoffs=tuple(json.loads(r["tradeoffs_json"])),
                    conditions=tuple(json.loads(r["conditions_json"])),
                    source=TasteSource(r["source_type"]),
                    confidence=float(r["confidence"]),
                    tags=tuple(json.loads(r["tags_json"])),
                )
                for r in rows
            ]
        else:
            candidates = reversed(self._items)
        out: list[TasteObservation] = []
        for item in candidates:
            if source_set and item.source not in source_set:
                continue
            if tagset and not (tagset & set(item.tags)):
                continue
            out.append(item)
            if len(out) >= limit:
                break
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


@dataclass(frozen=True)
class StoryElementProfile:
    """Functional profile of a story element; surface form is only one axis."""
    form: str
    knowledge: str
    goal: str
    role: str
    functions: tuple[str, ...] = ()


@dataclass(frozen=True)
class OriginalityDiagnosis:
    changed_axes: tuple[str, ...]
    unchanged_axes: tuple[str, ...]
    missing_functions: tuple[str, ...]
    issues: tuple[str, ...]
    rule: str = "Preserve required story function while changing the default logic on one or more meaningful axes; novelty alone is not a virtue."


class OrthogonalOriginality:
    """Detects default-pattern clustering without treating familiarity itself as a defect."""

    AXES = ("form", "knowledge", "goal", "role")

    def diagnose(
        self,
        *,
        candidate: StoryElementProfile,
        default: StoryElementProfile,
        required_functions: Iterable[str] = (),
    ) -> OriginalityDiagnosis:
        changed = tuple(axis for axis in self.AXES if getattr(candidate, axis) != getattr(default, axis))
        unchanged = tuple(axis for axis in self.AXES if axis not in changed)
        missing = tuple(sorted(set(required_functions) - set(candidate.functions)))
        issues: list[str] = []
        if not changed:
            issues.append("DEFAULT_CLUSTER")
        elif changed == ("form",):
            issues.append("COSMETIC_SWAP")
        if missing:
            issues.append("FUNCTION_LOSS")
        # A protagonist-serving role plus plot-aware knowledge is a common sign that
        # the element exists only because the author needs it, regardless of surface novelty.
        if candidate.knowledge == default.knowledge and candidate.role == default.role and candidate.goal == default.goal:
            if "DEFAULT_CLUSTER" not in issues and "COSMETIC_SWAP" not in issues:
                issues.append("PLOT_SERVICE_LOGIC_UNCHANGED")
        return OriginalityDiagnosis(changed, unchanged, missing, tuple(issues))
