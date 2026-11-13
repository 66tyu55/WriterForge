"""Small independent xianxia time rules, NOT a world-model replacement.

Track only clocks and time eligibility. No automatic realm upgrade, personality
decision, fate or story outline. No persistence or private books required.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from hashlib import sha256
import json
import random
from typing import Any


class TimeRuleError(ValueError):
    pass


def need(condition: bool, code: str):
    if not condition:
        raise TimeRuleError(code)


def strict_int(value, min_value=0, max_value=100000000):
    return type(value) is int and min_value <= value <= max_value


@dataclass(frozen=True)
class TimeParameters:
    """Independent axes. Training days are NOT elapsed world days."""
    world_day: int
    cultivation_days: int
    bodily_age_days: int
    era: str
    realm_step: int

    def validate(self):
        need(strict_int(self.world_day), "WORLD_CLOCK_INVALID")
        need(strict_int(self.cultivation_days), "CULTIVATION_CLOCK_INVALID")
        need(strict_int(self.bodily_age_days), "AGE_CLOCK_INVALID")
        need(isinstance(self.era, str) and 1 <= len(self.era) <= 32,
             "ERA_LABEL_INVALID")
        need(strict_int(self.realm_step, 1, 100), "REALM_STEP_INVALID")
        return self


@dataclass(frozen=True)
class TimeWorldRule:
    """World-local requirement, not a universal xianxia breakthrough law."""
    required_training_days_for_next_stage: int
    deadline_world_day: int
    current_stage: int = 1
    next_stage: int = 2

    def validate(self):
        need(strict_int(self.required_training_days_for_next_stage, 1, 1000000),
             "MIN_TRAINING_INVALID")
        need(strict_int(self.deadline_world_day), "DEADLINE_INVALID")
        need(strict_int(self.current_stage, 1, 100), "INITIAL_STAGE_INVALID")
        need(self.next_stage == self.current_stage + 1,
             "NEXT_STAGE_NOT_DEFINED")
        return self


ACTIVITIES = frozenset(("cultivate", "work", "rest", "travel", "wait"))
INSTANT = frozenset(("attempt_breakthrough", "activate_barrier",
                     "era_shift", "remember_past_era"))
KINDS = ACTIVITIES | INSTANT
MAX_ACTIONS = 24


def apply(state: TimeParameters, action: dict, rule: TimeWorldRule):
    """Return new state; error is an actual rule violation, not literary criticism."""
    state.validate()
    rule.validate()
    need(type(action) is dict and
         set(action).issubset({
             "kind", "days", "outcome", "era_name", "past_era"
         }) and {"kind", "days"} <= set(action),
         "ACTION_SCHEMA_INVALID")
    kind, days = action["kind"], action["days"]
    need(type(kind) is str and kind in KINDS, "ACTION_KIND_INVALID")
    need(strict_int(days, 0, 100000), "ACTION_DURATION_INVALID")
    if kind in ACTIVITIES:
        need(days >= 1, "POSITIVE_DURATION_REQUIRED")
        need("outcome" not in action and "era_name" not in action
             and "past_era" not in action, "ACTIVITY_FIELD_MISMATCH")
        next_state = replace(
            state,
            world_day=state.world_day + days,
            cultivation_days=(state.cultivation_days + days
                              if kind == "cultivate" else state.cultivation_days),
            bodily_age_days=state.bodily_age_days + days,
        )
        return next_state.validate(), {
            "kind":kind, "days":days, "automatic_breakthrough":False
        }

    need(days == 0, "INSTANT_ACTION_MUST_NOT_SKIP_TIME")
    if kind == "attempt_breakthrough":
        need(set(action) == {"kind", "days", "outcome"},
             "BREAKTHROUGH_EVENT_SCHEMA")
        need(action["outcome"] in ("success", "failure"),
             "BREAKTHROUGH_OUTCOME_REQUIRED")
        need(state.realm_step == rule.current_stage,
             "UNDEFINED_FURTHER_REALM_TIME_RULE")
        if action["outcome"] == "success":
            need(state.cultivation_days >=
                 rule.required_training_days_for_next_stage,
                 "BREAKTHROUGH_TOO_EARLY")
            return replace(state, realm_step=rule.next_stage).validate(), {
                "kind":kind, "days":0, "declared_outcome":"success",
                "eligibility_not_guarantee":True,
            }
        return state, {
            "kind":kind,"days":0,"declared_outcome":"failure",
            "eligibility_not_guarantee":True
        }

    if kind == "activate_barrier":
        need(set(action) == {"kind", "days"}, "BARRIER_EVENT_SCHEMA")
        need(state.realm_step >= rule.next_stage, "BARRIER_REQUIRES_ADVANCEMENT")
        need(state.world_day <= rule.deadline_world_day,
             "BARRIER_AFTER_DEADLINE")
        return state, {"kind":kind,"days":0,"barrier_used_before_deadline":True}

    if kind == "era_shift":
        need(set(action) == {"kind","days","era_name"} and
             type(action["era_name"]) is str and
             1 <= len(action["era_name"]) <= 32 and
             action["era_name"] != state.era,
             "ERA_SHIFT_REQUIRES_EXPLICIT_NEW_ERA")
        return replace(state,era=action["era_name"]).validate(), {
            "kind":kind,"days":0,"explicit_era_transition":True
        }

    need(kind == "remember_past_era", "UNKNOWN_INSTANT_KIND")
    need(set(action) == {"kind","days","past_era"} and
         type(action["past_era"]) is str and
         1 <= len(action["past_era"]) <= 32 and
         action["past_era"] != state.era,
         "PAST_ERA_REFERENCE_INVALID")
    return state, {"kind":kind,"days":0,"past_era_not_now":True,
                   "past_era_exact_distance_days":None}


def replay(rule: TimeWorldRule, initial: TimeParameters, actions: list[dict]):
    """Pure replay. The author chooses events; only elapsed time is computed."""
    rule.validate()
    current = initial.validate()
    need(current.realm_step == rule.current_stage,
         "INITIAL_STAGE_RULE_MISMATCH")
    need(current.world_day <= rule.deadline_world_day,
         "DEADLINE_PRECEDES_START")
    need(type(actions) is list and 0 <= len(actions) <= MAX_ACTIONS,
         "ACTION_COUNT_INVALID")
    trace = []
    for index, event in enumerate(actions):
        current, info = apply(current, event, rule)
        trace.append({
            "step": index + 1, "kind": info["kind"],
            "day": current.world_day,
            "cultivation_days": current.cultivation_days,
            "bodily_age_days": current.bodily_age_days,
            "era": current.era,
            "realm_step": current.realm_step,
            "rule_note": info
        })
    return {"initial":initial.__dict__, "final":current.__dict__,
            "trace":trace, "mechanical_time_consistency":True,
            "story_text_consistency_independently_proven":False,
            "causal_training_performed":False}


def audit_candidate(rule:TimeWorldRule, initial:TimeParameters, candidate:dict):
    """Evaluate model-generated bookkeeping without silently repairing prose."""
    need(type(candidate) is dict and
         set(candidate) == {"story","time_events"},
         "CANDIDATE_SCHEMA_INVALID")
    story=candidate["story"]
    need(type(story) is str and 80 <= len(story) <= 2000,
         "STORY_LENGTH_INVALID")
    events=candidate["time_events"]
    need(type(events) is list, "EVENTS_REQUIRED")
    actions=[]
    for event in events:
        need(type(event) is dict and
             {"kind","days","world_day_after","cultivation_days_after"} <= set(event) and
             set(event).issubset({"kind","days","world_day_after",
                                  "cultivation_days_after","outcome",
                                  "era_name","past_era"}),
             "MODEL_EVENT_SCHEMA")
        need(strict_int(event["world_day_after"]) and
             strict_int(event["cultivation_days_after"]),
             "MODEL_EVENT_CLOCK_INVALID")
        actions.append({key:value for key,value in event.items()
                        if key not in {"world_day_after","cultivation_days_after"}})
    result=replay(rule,initial,actions)
    for event, trace in zip(events,result["trace"]):
        need(event["world_day_after"]==trace["day"],
             "MODEL_WORLD_TIME_MISMATCH")
        need(event["cultivation_days_after"]==trace["cultivation_days"],
             "MODEL_TRAINING_TIME_MISMATCH")
    return {"mechanical_time_gate":"PASS", "actions":len(actions),
            "world_day":result["final"]["world_day"],
            "trained_days":result["final"]["cultivation_days"],
            "realm_step":result["final"]["realm_step"],
            "era":result["final"]["era"],
            "narrative_time_alignment":"UNREVIEWED",
            "story_quality":"NOT_JUDGED"}


ROLES = ("驿道信使","山门守钟人","灵田佃户","废矿巡夜人",
         "药房学徒","边镇驯兽人","渡口记账人","古道修桥匠")
TEMPERAMENTS = ("谨慎却倔强","多疑但重诺","心软而畏险","精于算计却怕孤独")


def random_character(seed:int):
    need(strict_int(seed), "RANDOM_SEED_INVALID")
    rng=random.Random(seed)
    return {"role":rng.choice(ROLES),"temperament":rng.choice(TEMPERAMENTS),
            "seed":seed, "anonymous_actor_id":"P001"}


def parameter_fingerprint(rule:TimeWorldRule, initial:TimeParameters):
    data={"rule":rule.__dict__,"initial":initial.__dict__}
    return sha256(json.dumps(data,ensure_ascii=False,sort_keys=True,
                            separators=(",",":")).encode()).hexdigest()
