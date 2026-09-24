from __future__ import annotations

from enum import IntEnum

from .lane_scheduler import Lane, highest_priority_lane


class EventPriority(IntEnum):
    """
    Source-event urgency.

    This deliberately stays much smaller than the execution lane model.
    Business code should classify *what kind of event happened* here, while
    capabilities keep ownership of *where expensive work executes*.
    """

    NONE = 0
    DISCRETE = 1
    CONTINUOUS = 2
    DEFAULT = 3
    IDLE = 4


EVENT_PRIORITY_ORDER: tuple[EventPriority, ...] = (
    EventPriority.DISCRETE,
    EventPriority.CONTINUOUS,
    EventPriority.DEFAULT,
    EventPriority.IDLE,
)


def higher_event_priority(a: EventPriority, b: EventPriority) -> EventPriority:
    if a == EventPriority.NONE:
        return b
    if b == EventPriority.NONE:
        return a
    return a if a < b else b


def lower_event_priority(a: EventPriority, b: EventPriority) -> EventPriority:
    if a == EventPriority.NONE:
        return a
    if b == EventPriority.NONE:
        return b
    return a if a > b else b


def is_higher_event_priority(a: EventPriority, b: EventPriority) -> bool:
    return a != EventPriority.NONE and (b == EventPriority.NONE or a < b)


def event_priority_to_lane(priority: EventPriority) -> Lane:
    """
    Thin source-priority -> execution-lane mapping.

    This does *not* promote every capability spawned by the event into this lane.
    Capability lanes still govern expensive work. The mapping is used for event
    ordering, interruption decisions, and tracing.
    """
    if priority == EventPriority.DISCRETE:
        return Lane.SYNC
    if priority == EventPriority.CONTINUOUS:
        return Lane.DRAFT
    if priority == EventPriority.DEFAULT:
        return Lane.REACTIVE
    if priority == EventPriority.IDLE:
        return Lane.IDLE
    return Lane.NONE


def lanes_to_event_priority(lanes: Lane) -> EventPriority:
    lane = highest_priority_lane(lanes)
    if lane == Lane.NONE:
        return EventPriority.NONE
    if lane == Lane.SYNC:
        return EventPriority.DISCRETE
    if lane == Lane.DRAFT:
        return EventPriority.CONTINUOUS
    if lane == Lane.IDLE:
        return EventPriority.IDLE
    return EventPriority.DEFAULT


DEFAULT_EVENT_PRIORITIES: dict[str, EventPriority] = {
    # Direct human/canonical decisions: react immediately.
    "user_edit": EventPriority.DISCRETE,
    "accept_candidate": EventPriority.DISCRETE,
    "commit_requested": EventPriority.DISCRETE,
    "canon_patch_requested": EventPriority.DISCRETE,

    # Repeated/stream-like foreground activity.
    "sentence_accepted": EventPriority.CONTINUOUS,
    "write_state_changed": EventPriority.CONTINUOUS,
    "stream_delta": EventPriority.CONTINUOUS,

    # Ordinary application work.
    "paragraph_boundary": EventPriority.DEFAULT,
    "scene_state_changed": EventPriority.DEFAULT,
    "scene_boundary": EventPriority.DEFAULT,
    "chapter_boundary": EventPriority.DEFAULT,
    "dependency_invalidated": EventPriority.DEFAULT,
    "draft_blocked": EventPriority.DEFAULT,
    "craft_need": EventPriority.DEFAULT,
    "dialogue_pressure": EventPriority.DEFAULT,
    "description_need": EventPriority.DEFAULT,
    "interiority_risk": EventPriority.DEFAULT,
    "narrative_restraint_risk": EventPriority.DEFAULT,
    "reader_critical_scene": EventPriority.DEFAULT,
    "reader_risk": EventPriority.DEFAULT,
    "arc_boundary": EventPriority.DEFAULT,
    "craft_review": EventPriority.DEFAULT,
    "hard_literary_choice": EventPriority.DEFAULT,
    "taste_review": EventPriority.DEFAULT,
    "literary_diagnosis": EventPriority.DEFAULT,
    "review_conflict": EventPriority.DEFAULT,

    # Background-only work.
    "learn_reader_pass": EventPriority.IDLE,
    "learn_offline": EventPriority.IDLE,
    "evolution_review": EventPriority.IDLE,
    "skill_training": EventPriority.IDLE,
    "promotion_candidate": EventPriority.IDLE,
    "idle_maintenance": EventPriority.IDLE,
}


def priority_for_event(name: str) -> EventPriority:
    return DEFAULT_EVENT_PRIORITIES.get(name, EventPriority.DEFAULT)
