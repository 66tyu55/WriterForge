from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from collections import Counter, defaultdict
import json
from typing import Iterable


class SkillStatus(str, Enum):
    ACTIVE = "active"
    NEEDS_REVALIDATION = "needs_revalidation"
    SHADOW = "shadow"
    RETIRED = "retired"


@dataclass
class CapabilityContract:
    name: str
    level: int
    statement: str
    depends_on: dict[str, int] = field(default_factory=dict)
    status: SkillStatus = SkillStatus.ACTIVE
    revision: int = 1

    def __post_init__(self):
        if not 1 <= int(self.level) <= 10:
            raise ValueError("capability level must be 1..10")
        if not self.statement.strip():
            raise ValueError("capability statement is required")


@dataclass(frozen=True)
class CapabilityLag:
    skill: str
    dependency: str
    required_level: int
    actual_level: int | None


class SkillRegistry:
    """Tracks qualitative capability levels and propagates revalidation only to dependents."""

    def __init__(self, db=None, scope: str = "__system__"):
        self._skills: dict[str, CapabilityContract] = {}
        self.db = db
        self.scope = scope

    def register(self, contract: CapabilityContract) -> None:
        self._skills[contract.name] = contract
        self._persist(contract)

    def get(self, name: str) -> CapabilityContract:
        return self._skills[name]

    def all(self) -> list[CapabilityContract]:
        return list(self._skills.values())

    def promote(self, name: str, *, new_level: int, statement: str, evidence_id: str) -> list[str]:
        item = self._skills[name]
        if new_level != item.level + 1:
            raise ValueError("maturity promotion must advance exactly one level")
        old_level = item.level
        item.level = new_level
        item.statement = statement
        item.revision += 1
        item.status = SkillStatus.ACTIVE
        affected = []
        for other in self._skills.values():
            if name in other.depends_on:
                other.status = SkillStatus.NEEDS_REVALIDATION
                other.revision += 1
                affected.append(other.name)
                self._persist(other)
        self._persist(item)
        if self.db is not None:
            self.db.conn.execute(
                """INSERT INTO skill_upgrade_events(scope, skill_name, old_level, new_level, evidence_id, statement)
                   VALUES(?,?,?,?,?,?)""",
                (self.scope, name, old_level, new_level, evidence_id, statement),
            )
            self.db.conn.commit()
        return sorted(affected)

    def revalidate(self, name: str, *, passed: bool) -> None:
        item = self._skills[name]
        item.status = SkillStatus.ACTIVE if passed else SkillStatus.SHADOW
        item.revision += 1
        self._persist(item)

    def lagging(self) -> list[CapabilityLag]:
        out: list[CapabilityLag] = []
        for skill in self._skills.values():
            for dep, minimum in skill.depends_on.items():
                actual = self._skills.get(dep)
                if actual is None or actual.level < minimum:
                    out.append(CapabilityLag(skill.name, dep, minimum, None if actual is None else actual.level))
        return out

    def _persist(self, item: CapabilityContract) -> None:
        if self.db is None:
            return
        self.db.conn.execute(
            """INSERT INTO skill_capabilities(scope, skill_name, level, status, revision, statement, dependencies_json)
               VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(scope, skill_name) DO UPDATE SET
                 level=excluded.level, status=excluded.status, revision=excluded.revision,
                 statement=excluded.statement, dependencies_json=excluded.dependencies_json,
                 updated_at=CURRENT_TIMESTAMP""",
            (
                self.scope, item.name, item.level, item.status.value, item.revision,
                item.statement, json.dumps(item.depends_on, ensure_ascii=False, sort_keys=True),
            ),
        )
        self.db.conn.commit()


@dataclass(frozen=True)
class FailureEvent:
    skill: str
    code: str
    context: str
    severity: int = 1
    genre: str = ""
    evidence_ref: str = ""


@dataclass(frozen=True)
class FailureCluster:
    skill: str
    code: str
    count: int
    examples: tuple[str, ...]
    genres: tuple[str, ...]


class FailureClusterer:
    def cluster(self, events: Iterable[FailureEvent], *, min_count: int = 3) -> list[FailureCluster]:
        groups: dict[tuple[str, str], list[FailureEvent]] = defaultdict(list)
        for event in events:
            groups[(event.skill, event.code)].append(event)
        out = []
        for (skill, code), items in groups.items():
            if len(items) < min_count:
                continue
            out.append(FailureCluster(
                skill=skill,
                code=code,
                count=len(items),
                examples=tuple(i.context for i in items[:5]),
                genres=tuple(sorted({i.genre for i in items if i.genre})),
            ))
        return sorted(out, key=lambda x: (-x.count, x.skill, x.code))


@dataclass(frozen=True)
class TrainingScenario:
    scenario_id: str
    capability: str
    split: str  # train | heldout | transfer
    relationship: str
    pressure: str
    information_pattern: str
    task: str
    success_evidence: tuple[str, ...]


class CurriculumPlanner:
    """Builds frontier-style literary exercises without writing the answer itself."""

    RELATIONSHIPS = ("mentor_student", "siblings", "partners", "rivals", "strangers", "ruler_subject")
    PRESSURES = ("betrayal", "shame", "grief", "jealousy", "duty", "survival")
    INFO = ("mutual_concealment", "one_sided_secret", "false_belief", "dramatic_irony", "shared_goal_value_conflict")

    def design(self, cluster: FailureCluster, *, count: int = 8) -> list[TrainingScenario]:
        scenarios: list[TrainingScenario] = []
        for i in range(max(3, count)):
            if i < max(1, count - 3):
                split = "train"
            elif i < count - 1:
                split = "heldout"
            else:
                split = "transfer"
            rel = self.RELATIONSHIPS[i % len(self.RELATIONSHIPS)]
            pressure = self.PRESSURES[(i + 1) % len(self.PRESSURES)]
            info = self.INFO[(i + 2) % len(self.INFO)]
            task = (
                f"Exercise {cluster.skill}/{cluster.code}: write or plan a scene where {rel} face {pressure}; "
                f"information pattern={info}. Demonstrate the capability without naming the technique or explaining the answer."
            )
            scenarios.append(TrainingScenario(
                scenario_id=f"{cluster.skill}:{cluster.code}:{i+1}",
                capability=cluster.skill,
                split=split,
                relationship=rel,
                pressure=pressure,
                information_pattern=info,
                task=task,
                success_evidence=(
                    "observable story-state or reader-effect change",
                    "no answer leakage from training examples",
                    "capability transfers across relationship/context",
                ),
            ))
        return scenarios


@dataclass(frozen=True)
class SkillSignature:
    diagnosis: frozenset[str]
    intervention: frozenset[str]
    failure_modes: frozenset[str]


@dataclass(frozen=True)
class SkillBirthDecision:
    create_new_skill: bool
    merge_target: str | None
    reason: str


class SkillBirthGate:
    """Prevents skill-library bloat by merging near-duplicate literary mechanisms."""

    @staticmethod
    def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
        if not a and not b:
            return 1.0
        return len(a & b) / max(1, len(a | b))

    def decide(self, candidate: SkillSignature, existing: dict[str, SkillSignature], *, merge_threshold: float = 0.65) -> SkillBirthDecision:
        best_name, best = None, -1.0
        for name, sig in existing.items():
            score = (
                self._jaccard(candidate.diagnosis, sig.diagnosis)
                + self._jaccard(candidate.intervention, sig.intervention)
                + self._jaccard(candidate.failure_modes, sig.failure_modes)
            ) / 3.0
            if score > best:
                best_name, best = name, score
        if best_name is not None and best >= merge_threshold:
            return SkillBirthDecision(False, best_name, f"overlap={best:.2f}; upgrade/merge existing skill")
        return SkillBirthDecision(True, None, f"distinct mechanism; max overlap={max(0.0,best):.2f}")


@dataclass(frozen=True)
class PromotionEvidence:
    capability_statement: str
    heldout_success: float
    transfer_success: float
    regression_success: float
    judge_stability: float
    repeated_failure_reduction: float
    runtime_regression: float
    human_anchor_count: int = 0


@dataclass(frozen=True)
class PromotionDecision:
    accepted: bool
    reasons: tuple[str, ...]


class PromotionGate:
    def evaluate(self, evidence: PromotionEvidence, *, requires_human_anchor: bool = False) -> PromotionDecision:
        reasons: list[str] = []
        if not evidence.capability_statement.strip():
            reasons.append("missing qualitative capability statement")
        if evidence.heldout_success < 0.80:
            reasons.append("held-out success below 0.80")
        if evidence.transfer_success < 0.75:
            reasons.append("transfer success below 0.75")
        if evidence.regression_success < 0.95:
            reasons.append("regression preservation below 0.95")
        if evidence.judge_stability < 0.90:
            reasons.append("pairwise judge stability below 0.90")
        if evidence.repeated_failure_reduction < 0.30:
            reasons.append("target failure did not fall enough")
        if evidence.runtime_regression > 0.20:
            reasons.append("runtime regression exceeds 20%")
        if requires_human_anchor and evidence.human_anchor_count < 1:
            reasons.append("literary/taste promotion requires at least one human or real-reader anchor")
        if not reasons:
            reasons.append("passes held-out, transfer, regression, stability, failure-reduction, and runtime gates")
        return PromotionDecision(not any(r for r in reasons if not r.startswith("passes ")), tuple(reasons))


WRITER_MATURITY_LEVELS = {
    1: "Can produce fiction text but has little long-form control.",
    2: "Maintains basic character/world/plot continuity.",
    3: "Plans and completes coherent chapters and story arcs.",
    4: "Characters act from bounded knowledge, goals, fear, beliefs, and relationships rather than plot puppetry.",
    5: "Selects scene-level literary techniques intentionally instead of rendering every scene the same way.",
    6: "Learns functional literary mechanisms from full works and real-reader evidence and transfers them to unfamiliar stories.",
    7: "Controls long-range echoes: arcs, promises, motifs, voice, memory, and cumulative meaning across long fiction.",
    8: "Has story sense: diagnoses the dominant literary problem and knows which otherwise-valid rules do not matter now.",
    9: "Finds its own literary weaknesses, designs targeted exercises, upgrades dependent skills, and proves transfer with external anchors.",
    10: "Sustains high-quality long-form fiction with independent work-specific judgment rather than fixed formulas.",
}

@dataclass(frozen=True)
class UpgradeCandidate:
    skill: str
    new_level: int
    capability_statement: str
    evidence_id: str
    evidence: PromotionEvidence
    requires_human_anchor: bool = False


class EvolutionEngine:
    """Controlled literary self-improvement. It may propose; production promotion requires an explicit gate and approval."""

    def __init__(self, *, registry: SkillRegistry | None = None, db=None, scope: str = "__system__"):
        self.registry = registry or SkillRegistry(db=db, scope=scope)
        self.db = db
        self.scope = scope
        self.failures: list[FailureEvent] = []
        self.clusterer = FailureClusterer()
        self.curriculum = CurriculumPlanner()
        self.promotion_gate = PromotionGate()

    def record_failure(self, event: FailureEvent) -> None:
        self.failures.append(event)
        if self.db is not None:
            self.db.conn.execute(
                """INSERT INTO evolution_failures(scope, skill_name, code, context, severity, genre, evidence_ref)
                   VALUES(?,?,?,?,?,?,?)""",
                (self.scope, event.skill, event.code, event.context, event.severity, event.genre, event.evidence_ref),
            )
            self.db.conn.commit()

    def failure_clusters(self, *, min_count: int = 3) -> list[FailureCluster]:
        return self.clusterer.cluster(self.failures, min_count=min_count)

    def design_curriculum_for(self, *, skill: str, code: str, count: int = 8, min_count: int = 3) -> list[TrainingScenario]:
        for cluster in self.failure_clusters(min_count=min_count):
            if cluster.skill == skill and cluster.code == code:
                return self.curriculum.design(cluster, count=count)
        return []

    def evaluate_upgrade(self, candidate: UpgradeCandidate) -> PromotionDecision:
        current = self.registry.get(candidate.skill)
        if candidate.new_level != current.level + 1:
            return PromotionDecision(False, ("upgrade must advance exactly one capability level",))
        return self.promotion_gate.evaluate(candidate.evidence, requires_human_anchor=candidate.requires_human_anchor)

    def apply_upgrade(self, candidate: UpgradeCandidate, *, policy: str = "gated_auto", approved: bool = False) -> list[str]:
        """
        Apply a candidate only after the Promotion Gate.

        policy:
        - gated_auto: offline Evolution Engine may self-promote after all gates pass;
        - manual: additionally requires approved=True;
        - shadow_only: keep the candidate out of production even when it passes.

        Subjective literary capabilities should set requires_human_anchor=True, so
        gated_auto still cannot pass on self-judgment alone.
        """
        decision = self.evaluate_upgrade(candidate)
        if not decision.accepted:
            raise ValueError("promotion gate failed: " + "; ".join(decision.reasons))
        if policy == "shadow_only":
            return []
        if policy == "manual" and not approved:
            raise PermissionError("manual promotion policy requires explicit approval")
        if policy not in {"gated_auto", "manual"}:
            raise ValueError("policy must be gated_auto, manual, or shadow_only")
        return self.registry.promote(
            candidate.skill,
            new_level=candidate.new_level,
            statement=candidate.capability_statement,
            evidence_id=candidate.evidence_id,
        )
