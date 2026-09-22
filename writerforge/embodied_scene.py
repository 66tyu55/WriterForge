from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .reactive_runtime import stable_fingerprint


class PerceptualChannel(str, Enum):
    SOUND = "sound"
    TEMPERATURE = "temperature"
    TOUCH = "touch"
    SMELL = "smell"
    VISUAL = "visual"
    KINESTHETIC = "kinesthetic"
    PHYSIOLOGY = "physiology"
    BEHAVIOR = "behavior"


@dataclass(frozen=True)
class SceneEnvironment:
    """Physical scene state. Tags describe facts, not prose decorations."""

    temperature_c: float | None = None
    surface: str = ""
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class SceneEntity:
    entity_id: str
    kind: str
    traits: tuple[str, ...] = ()
    state_tags: tuple[str, ...] = ()
    # Character-specific mappings such as "anger:clipped_speech" or
    # "fear:checks_exits". Emotion alone never emits a canned body reaction.
    embodiment_hints: tuple[str, ...] = ()


@dataclass(frozen=True)
class SceneAction:
    actor_id: str
    verb: str
    target_id: str = ""
    surface: str = ""
    intensity: str = "normal"
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class PerceptionContext:
    pov_id: str = ""
    attention_tags: tuple[str, ...] = ()
    max_cues: int = 4


@dataclass(frozen=True)
class PerceptualCue:
    """A causal scene fact offered to the Writer; never pre-written prose."""

    channel: PerceptualChannel
    semantic: str
    source_id: str
    causes: tuple[str, ...]
    tags: tuple[str, ...] = ()
    salience: float = 0.5
    confidence: float = 1.0


@dataclass(frozen=True)
class EmbodiedSceneResult:
    all_cues: tuple[PerceptualCue, ...]
    selected_cues: tuple[PerceptualCue, ...]
    dependency_fingerprint: str
    rule: str = (
        "Perception is a consequence of world/entity/action state, not a five-sense checklist. "
        "The Writer may use zero or a few cues; never force one cue per sensory channel."
    )


class EmbodiedSceneResolver:
    """
    Derives perceptual affordances from physical/behavioral causality.

    This is not a prose Skill and does not write sentences. It supplies a small pool
    of causal cues to the existing Perception & Description craft domain.
    """

    _MOVEMENT = {"walk", "step", "run", "pace", "approach", "retreat"}
    _FEEDING = {"eat", "chew", "feed", "forage", "root"}
    _BOAR_KINDS = {"boar", "wild_boar", "pig", "swine"}

    _SURFACE_CUES = {
        "wood": ("wooden_footfall", PerceptualChannel.SOUND, ("footfall", "hard_surface"), 0.55),
        "stone": ("hard_footfall", PerceptualChannel.SOUND, ("footfall", "hard_surface"), 0.55),
        "tile": ("hard_footfall", PerceptualChannel.SOUND, ("footfall", "hard_surface"), 0.55),
        "gravel": ("gravel_shift_under_foot", PerceptualChannel.SOUND, ("footfall", "loose_surface"), 0.65),
        "dry_leaves": ("dry_leaf_crush_under_foot", PerceptualChannel.SOUND, ("footfall", "foliage"), 0.65),
        "snow": ("snow_compaction_under_step", PerceptualChannel.SOUND, ("footfall", "snow", "cold"), 0.55),
        "mud": ("mud_displacement_under_step", PerceptualChannel.TOUCH, ("footfall", "wet_surface"), 0.55),
        "shallow_water": ("water_displacement_from_step", PerceptualChannel.SOUND, ("footfall", "water"), 0.70),
    }

    def resolve(
        self,
        *,
        environment: SceneEnvironment,
        entities: Iterable[SceneEntity] = (),
        actions: Iterable[SceneAction] = (),
        perception: PerceptionContext | None = None,
    ) -> EmbodiedSceneResult:
        entity_list = tuple(entities)
        action_list = tuple(actions)
        entity_map = {e.entity_id: e for e in entity_list}
        cues: list[PerceptualCue] = []

        cues.extend(self._environment_cues(environment))
        for action in action_list:
            actor = entity_map.get(action.actor_id)
            cues.extend(self._action_cues(action, actor, environment))
        for entity in entity_list:
            cues.extend(self._state_cues(entity))

        # Preserve deterministic order while eliminating exact semantic duplicates.
        dedup: dict[tuple[str, str, str], PerceptualCue] = {}
        for cue in cues:
            key = (cue.channel.value, cue.semantic, cue.source_id)
            existing = dedup.get(key)
            if existing is None or cue.salience > existing.salience:
                dedup[key] = cue
        all_cues = tuple(dedup.values())
        selected = self._select(all_cues, perception)

        fingerprint = stable_fingerprint({
            "environment": environment,
            "entities": entity_list,
            "actions": action_list,
            "perception": perception,
        })
        return EmbodiedSceneResult(all_cues, selected, fingerprint)

    def _environment_cues(self, env: SceneEnvironment) -> list[PerceptualCue]:
        cues: list[PerceptualCue] = []
        tags = set(env.tags)
        if env.temperature_c is not None:
            if env.temperature_c <= 5:
                cues.append(PerceptualCue(
                    PerceptualChannel.TEMPERATURE,
                    "cold_air_exposure",
                    "environment",
                    (f"temperature_c={env.temperature_c}",),
                    ("cold", "temperature"),
                    0.50,
                ))
                if env.temperature_c <= 2:
                    cues.append(PerceptualCue(
                        PerceptualChannel.VISUAL,
                        "exhalation_condensation_possible",
                        "environment",
                        (f"temperature_c={env.temperature_c}", "warm_exhaled_air"),
                        ("cold", "breath"),
                        0.35,
                        0.75,
                    ))
            elif env.temperature_c >= 30:
                cues.append(PerceptualCue(
                    PerceptualChannel.TEMPERATURE,
                    "heat_load",
                    "environment",
                    (f"temperature_c={env.temperature_c}",),
                    ("heat", "temperature"),
                    0.50,
                ))

        if "wind" in tags and "dry_leaves" in tags:
            cues.append(PerceptualCue(
                PerceptualChannel.SOUND,
                "wind_moving_dry_foliage",
                "environment",
                ("wind", "dry_leaves"),
                ("wind", "foliage", "ambient"),
                0.45,
            ))
        if "rain" in tags and "tile_roof" in tags:
            cues.append(PerceptualCue(
                PerceptualChannel.SOUND,
                "rain_striking_tile",
                "environment",
                ("rain", "tile_roof"),
                ("rain", "roof", "ambient"),
                0.60,
            ))
        return cues

    def _action_cues(self, action: SceneAction, actor: SceneEntity | None, env: SceneEnvironment) -> list[PerceptualCue]:
        cues: list[PerceptualCue] = []
        verb = action.verb.lower().strip()
        surface = (action.surface or env.surface).lower().strip()
        actor_id = action.actor_id or "unknown"
        action_tags = set(action.tags)

        if verb in self._MOVEMENT and surface in self._SURFACE_CUES:
            semantic, channel, tags, salience = self._SURFACE_CUES[surface]
            if verb == "run":
                salience = min(1.0, salience + 0.15)
            cues.append(PerceptualCue(
                channel,
                semantic,
                actor_id,
                (f"action={verb}", f"surface={surface}"),
                tuple(tags) + ("movement",),
                salience,
            ))

        if verb in self._FEEDING:
            cues.append(PerceptualCue(
                PerceptualChannel.SOUND,
                "mastication_or_feeding_sound",
                actor_id,
                (f"action={verb}",),
                ("feeding", "mouth"),
                0.40,
            ))
            kind = actor.kind.lower() if actor else ""
            traits = set(actor.traits) if actor else set()
            if kind in self._BOAR_KINDS and (verb in {"forage", "root"} or "ground_feed" in action_tags or "snout_forager" in traits):
                cues.extend([
                    PerceptualCue(
                        PerceptualChannel.SOUND,
                        "boar_snuffling_while_feeding",
                        actor_id,
                        (f"kind={kind}", f"action={verb}", "snout_foraging"),
                        ("feeding", "boar", "breath", "ground"),
                        0.70,
                    ),
                    PerceptualCue(
                        PerceptualChannel.VISUAL,
                        "ground_disturbance_from_rooting",
                        actor_id,
                        (f"kind={kind}", f"action={verb}", "snout_contacts_ground"),
                        ("feeding", "boar", "ground", "movement"),
                        0.65,
                    ),
                ])

        if "metal_contact" in action_tags:
            cues.append(PerceptualCue(
                PerceptualChannel.SOUND,
                "metal_contact_resonance",
                actor_id,
                (f"action={verb}", "metal_contact"),
                ("metal", "impact"),
                0.70,
            ))
        if "fabric_motion" in action_tags:
            cues.append(PerceptualCue(
                PerceptualChannel.SOUND,
                "fabric_movement_rustle",
                actor_id,
                (f"action={verb}", "fabric_motion"),
                ("fabric", "movement"),
                0.35,
            ))
        return cues

    def _state_cues(self, entity: SceneEntity) -> list[PerceptualCue]:
        cues: list[PerceptualCue] = []
        states = set(entity.state_tags)
        # Emotion/state becomes perceptible only through a character-specific
        # embodiment tendency already established for this entity.
        for hint in entity.embodiment_hints:
            if ":" not in hint:
                continue
            state, effect = hint.split(":", 1)
            state = state.strip()
            effect = effect.strip()
            if not state or not effect or state not in states:
                continue
            cues.append(PerceptualCue(
                PerceptualChannel.BEHAVIOR,
                f"character_specific_expression:{effect}",
                entity.entity_id,
                (f"state={state}", f"established_tendency={effect}"),
                ("emotion_manifestation", state, effect),
                0.60,
            ))
        return cues

    @staticmethod
    def _select(cues: tuple[PerceptualCue, ...], perception: PerceptionContext | None) -> tuple[PerceptualCue, ...]:
        if not cues:
            return ()
        if perception is None:
            limit = min(4, len(cues))
            return tuple(sorted(cues, key=lambda c: (-c.salience, -c.confidence, c.semantic))[:limit])

        attention = set(perception.attention_tags)
        limit = max(0, perception.max_cues)
        if limit == 0:
            return ()

        def score(c: PerceptualCue) -> tuple[float, float, str]:
            relevance = 0.15 * len(attention & set(c.tags))
            if perception.pov_id and c.source_id == perception.pov_id:
                relevance += 0.05
            return (c.salience + relevance, c.confidence, c.semantic)

        ordered = sorted(cues, key=lambda c: (-score(c)[0], -score(c)[1], score(c)[2]))
        return tuple(ordered[:limit])
