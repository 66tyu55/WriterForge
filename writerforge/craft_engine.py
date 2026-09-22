from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping, Any

from .reactive_runtime import stable_fingerprint


class CraftGroup(str, Enum):
    DIALOGUE_ACTION = "dialogue_action"
    PERCEPTION_DESCRIPTION = "perception_description"
    COGNITIVE_MOTION = "cognitive_motion"
    NARRATIVE_RESTRAINT = "narrative_restraint"
    SCENE_TURN_RHYTHM = "scene_turn_rhythm"


@dataclass(frozen=True)
class TechniqueCard:
    id: str
    group: CraftGroup
    purpose: str
    use_when: tuple[str, ...]
    avoid_when: tuple[str, ...] = ()
    review_question: str = ""


@dataclass
class CraftRequest:
    needs: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    desired_effects: tuple[str, ...] = ()
    max_groups: int = 2


@dataclass
class CraftPlan:
    groups: list[CraftGroup]
    techniques: list[TechniqueCard]
    questions: list[str]
    rule: str = "Use the smallest craft intervention that changes reader experience; do not auto-rewrite prose."


@dataclass(frozen=True)
class SceneCraftContract:
    scene_id: str
    contract_id: str
    technique_ids: tuple[str, ...]
    questions: tuple[str, ...]
    dependency_fingerprint: str
    rule: str = "Select once for the scene; keep active until relevant dependencies change."


TECHNIQUES: tuple[TechniqueCard, ...] = (
    TechniqueCard(
        "dialogue_as_action", CraftGroup.DIALOGUE_ACTION,
        "Treat each important line as an attempt to probe, conceal, bargain, threaten, deflect, reassure, test, or change the other person.",
        ("dialogue", "empty_dialogue", "transcript_risk", "subtext"),
        review_question="What does this line try to change, and what changes because it was said?",
    ),
    TechniqueCard(
        "public_private_goal_gap", CraftGroup.DIALOGUE_ACTION,
        "Create subtext from the gap between what a character publicly seeks and privately wants.",
        ("subtext", "concealment", "relationship_pressure"),
        review_question="Is the character saying the goal, or pursuing it indirectly?",
    ),
    TechniqueCard(
        "telling_detail", CraftGroup.PERCEPTION_DESCRIPTION,
        "Choose one or two details that reveal place, status, history, danger, or character instead of inventorying the scene.",
        ("description", "place", "character_entrance", "white_room"),
        review_question="Why would this POV notice this detail now, and what does it imply beyond appearance?",
    ),
    TechniqueCard(
        "perception_motivation", CraftGroup.PERCEPTION_DESCRIPTION,
        "Filter description through the POV character's current goal, fear, task, and narrative distance.",
        ("description", "psychic_distance", "pov", "character_entrance"),
        review_question="What is the POV looking for, avoiding, or misreading right now?",
    ),
    TechniqueCard(
        "reaction_dilemma_decision", CraftGroup.COGNITIVE_MOTION,
        "Move interiority from reaction to dilemma to a changed decision or action tendency.",
        ("interiority", "rumination", "cognitive_loop", "decision"),
        review_question="After thinking, what belief, option, or intended action is different?",
    ),
    TechniqueCard(
        "self_awareness_ceiling", CraftGroup.COGNITIVE_MOTION,
        "Allow partial awareness, false explanations, and self-deception instead of instant perfect psychological insight.",
        ("over_self_aware", "hidden_motive", "self_deception"),
        review_question="Would this character really know this about themselves yet?",
    ),
    TechniqueCard(
        "trust_the_reader", CraftGroup.NARRATIVE_RESTRAINT,
        "Stop after the concrete action, image, consequence, or silence when it already carries the meaning.",
        ("over_explain", "duplicate_commentary", "stating_moral", "reflection_tail"),
        review_question="If the explanation is removed, has the scene already made the point?",
    ),
    TechniqueCard(
        "delay_explanation", CraftGroup.NARRATIVE_RESTRAINT,
        "Keep uncertainty alive until a character has reason, evidence, and consequence for resolving it.",
        ("premature_explanation", "mystery", "reveal"),
        review_question="Does explaining this now create a new decision, or only reduce tension?",
    ),
    TechniqueCard(
        "scene_delta", CraftGroup.SCENE_TURN_RHYTHM,
        "Require a meaningful change in fact, goal, belief, relationship, risk, promise, or reader question.",
        ("scene", "no_turn", "stagnation", "padding"),
        review_question="What is different at the end that was not true at the start?",
    ),
    TechniqueCard(
        "leave_after_turn", CraftGroup.SCENE_TURN_RHYTHM,
        "Once the scene's decisive work lands, avoid the automatic reflection tail unless it creates a new turn.",
        ("reflection_tail", "slow_exit", "overstay"),
        review_question="Is this aftermath new narrative work, or only commentary on work already done?",
    ),
    TechniqueCard(
        "rhythm_by_function", CraftGroup.SCENE_TURN_RHYTHM,
        "Vary sentence and paragraph rhythm according to scene function instead of chasing variety for its own sake.",
        ("flat_rhythm", "choppy", "prose_rhythm"),
        review_question="Does the syntax support pressure, hesitation, texture, or impact here?",
    ),
    TechniqueCard(
        "narrative_magnification", CraftGroup.SCENE_TURN_RHYTHM,
        "Choose deliberately between scene, summary, and omission so page-time matches narrative importance.",
        ("scene_summary", "omission", "pacing", "magnification"),
        review_question="Does this moment deserve real-time scene treatment, compression, or omission?",
    ),
    TechniqueCard(
        "strategic_reversal", CraftGroup.SCENE_TURN_RHYTHM,
        "Build reversals from established rules, assumptions, and hidden leverage so surprise remains fair in hindsight.",
        ("reversal", "setup_payoff", "surprise_inevitability"),
        review_question="Was the leverage available before the reversal, and does hindsight make it feel earned?",
    ),
    TechniqueCard(
        "punctuation_as_performance", CraftGroup.SCENE_TURN_RHYTHM,
        "Use pause, interruption, withholding, and sentence breaks only when they enact the character's pressure or voice.",
        ("punctuation", "hesitation", "interruption", "micro_rhythm"),
        review_question="Is the punctuation performing a real hesitation/pressure shift, or manufacturing drama?",
    ),
    TechniqueCard(
        "detail_utility", CraftGroup.PERCEPTION_DESCRIPTION,
        "Prefer details that perform more than decoration: character, relation, world, atmosphere, plot, or foreshadowing.",
        ("detail_utility", "description", "specificity"),
        review_question="What narrative work does this detail do besides looking vivid?",
    ),
    TechniqueCard(
        "free_indirect_voice", CraftGroup.PERCEPTION_DESCRIPTION,
        "Let third-person narration selectively absorb the POV character's diction and judgment without constant thought tags.",
        ("free_indirect", "voice", "psychic_distance", "interiority"),
        review_question="Does this judgment belong to the POV consciousness rather than a generic narrator?",
    ),
    TechniqueCard(
        "motif_return", CraftGroup.PERCEPTION_DESCRIPTION,
        "Return an established object/image under changed pressure so its meaning evolves instead of being explained as a symbol.",
        ("motif", "long_term_echo", "symbol", "object_return"),
        review_question="What has changed around this recurring image, and therefore changed what it means?",
    ),
)


_GROUP_TRIGGER_MAP = {
    CraftGroup.DIALOGUE_ACTION: {"dialogue", "empty_dialogue", "transcript_risk", "subtext", "concealment", "relationship_pressure"},
    CraftGroup.PERCEPTION_DESCRIPTION: {"description", "place", "character_entrance", "white_room", "psychic_distance", "pov", "detail_utility", "specificity", "free_indirect", "voice", "motif", "long_term_echo", "symbol", "object_return"},
    CraftGroup.COGNITIVE_MOTION: {"interiority", "rumination", "cognitive_loop", "decision", "over_self_aware", "hidden_motive", "self_deception"},
    CraftGroup.NARRATIVE_RESTRAINT: {"over_explain", "duplicate_commentary", "stating_moral", "reflection_tail", "premature_explanation", "mystery", "reveal"},
    CraftGroup.SCENE_TURN_RHYTHM: {"scene", "no_turn", "stagnation", "padding", "slow_exit", "overstay", "flat_rhythm", "choppy", "prose_rhythm", "scene_summary", "omission", "pacing", "magnification", "reversal", "setup_payoff", "surprise_inevitability", "punctuation", "hesitation", "interruption", "micro_rhythm"},
}


class CraftEngine:
    """A small router, not a giant prompt stack. Select at most two craft groups."""

    def plan(self, request: CraftRequest) -> CraftPlan:
        signals = set(request.needs) | set(request.risks) | set(request.desired_effects)
        scored: list[tuple[int, CraftGroup]] = []
        for group, triggers in _GROUP_TRIGGER_MAP.items():
            score = len(signals & triggers)
            if score:
                scored.append((score, group))
        scored.sort(key=lambda x: (-x[0], x[1].value))
        limit = max(1, min(request.max_groups, 2))
        groups = [g for _, g in scored[:limit]]

        techniques: list[TechniqueCard] = []
        for group in groups:
            candidates = [t for t in TECHNIQUES if t.group == group]
            candidates.sort(key=lambda t: -len(signals & set(t.use_when)))
            if candidates:
                techniques.append(candidates[0])

        questions = [t.review_question for t in techniques if t.review_question]
        return CraftPlan(groups=groups, techniques=techniques, questions=questions)

    def compile_scene_contract(self, *, scene_id: str, request: CraftRequest, dependencies: Mapping[str, Any]) -> SceneCraftContract:
        plan = self.plan(request)
        dep_fp = stable_fingerprint(dict(dependencies))
        contract_id = stable_fingerprint({
            "scene_id": scene_id,
            "techniques": [t.id for t in plan.techniques],
            "dependencies": dep_fp,
        })[:20]
        return SceneCraftContract(
            scene_id=scene_id,
            contract_id=contract_id,
            technique_ids=tuple(t.id for t in plan.techniques),
            questions=tuple(plan.questions),
            dependency_fingerprint=dep_fp,
        )


@dataclass(frozen=True)
class CraftFinding:
    code: str
    severity: str
    message: str
    auto_rewrite: bool = False


class CraftAuditor:
    """Review structured craft evidence. It flags; it never auto-rewrites."""

    DELTA_KEYS = ("fact", "goal", "belief", "relationship", "risk", "promise", "reader_question", "world")

    def audit(self, *, scene_delta: dict[str, int | float] | None = None,
              redundant_explanations: int = 0,
              repeated_thought_clusters: int = 0,
              dialogue_lines_without_function: int = 0,
              reflection_tail: bool = False,
              deliberate_static_scene: bool = False) -> list[CraftFinding]:
        findings: list[CraftFinding] = []

        if scene_delta is not None and not deliberate_static_scene:
            if all(float(scene_delta.get(k, 0) or 0) == 0 for k in self.DELTA_KEYS):
                findings.append(CraftFinding(
                    "NO_NARRATIVE_DELTA", "high",
                    "Scene ends without a measurable change in fact, goal, belief, relationship, risk, promise, reader question, or world state."
                ))

        if redundant_explanations > 0:
            findings.append(CraftFinding(
                "REDUNDANT_EXPLANATION", "medium",
                "Meaning is being explained after action/dialogue/detail may already have carried it; verify necessity before keeping the explanation."
            ))

        if repeated_thought_clusters > 0:
            findings.append(CraftFinding(
                "COGNITIVE_LOOP", "medium",
                "Interiority repeats the same conclusion without changing belief, dilemma, or intended action."
            ))

        if dialogue_lines_without_function > 0:
            findings.append(CraftFinding(
                "EMPTY_DIALOGUE", "medium",
                "Dialogue lines have no identifiable action, relationship, voice, pacing, or information function."
            ))

        if reflection_tail:
            findings.append(CraftFinding(
                "REFLECTION_TAIL", "low",
                "The scene may be lingering after its turn; keep the aftermath only if it performs new narrative work."
            ))

        return findings
