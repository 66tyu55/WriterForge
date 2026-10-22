"""V120: compare *proposed* beat changes with source-anchored prose events.

Zero-model, source-only and opt-in to WF continuity_guard. Uses V116
candidate events. The model's explanation / trace / goal NEVER supplies an
observed event. An event with no secure actor/source anchor is UNPROVEN.
A match proves only the narrow observable state subgoal, NOT scene quality,
intention, thematic success, or correctness of arbitrary literary semantics.

Inspired by temporal episode/provenance concepts, not a Graphiti dependency.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re

from .v116_state_delta import (
    extract_state_events, _segments as source_segments,
    _present as source_narrated,
)

FORMAT = "wf.writing.v120.plan-prose-source-comparison"
STATES = frozenset((
    "OBSERVED_SOURCE_SUPPORTED", "UNPROVEN", "CONTRADICTED"))
MAX_SOURCE = 20000
MAX_CAST = 10
MAX_GOAL = 220
MAX_DEBTS = 3
FRUIT = r"(?:[\u4e00-\u9fff]{0,8}(?:髓果|灵果|仙果))"
CONDITIONAL = re.compile(
    r"(?:如果|假如|若是|倘若|梦见|梦中|听说|据说|似乎|"
    r"想要|打算|计划|准备|试图|尝试|企图|假装|不曾|未能|尚未|不能|"
    r"没有|阻止|拒绝|是否|可能|考虑)")
QUIET = frozenset(("quiet", "setup", "transition", "dialogue", "aftermath"))


class PlanExecutionError(ValueError):
    pass


def _need(condition, code):
    if not condition:
        raise PlanExecutionError(code)


def _hash(x):
    if type(x) is str:
        return sha256(x.encode("utf8")).hexdigest()
    return sha256(json.dumps(x, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False)
                  .encode("utf8")).hexdigest()


def _plan_goal(beat, cast):
    """Only exact affirmative action goals with an explicitly named subject.

    Unsupported prose instructions are not turned into promises. A long goal
    may have further aims, so even a verified state is NEVER whole-goal proof.
    """
    actor = beat["actor"]
    goal = beat["goal"].strip()
    if beat["kind"] in QUIET:
        return None, "NON_STATEFUL_BEAT"
    if not goal.startswith(actor) or CONDITIONAL.search(goal):
        return None, "AMBIGUOUS_OR_NONASSERTIVE_GOAL"
    # A second named character before the physical verb makes the subject
    # ambiguous; choose abstention over a false event for the wrong actor.
    other_names = [name for name in cast if name != actor and
                   name in goal[: min(len(goal), 16)]]
    if other_names:
        # Explicit transfer is recognized only in the dedicated branch below.
        transfer_only = True
    else:
        transfer_only = False
    a = re.escape(actor)
    fruit = FRUIT

    if not transfer_only:
        # "沈砚把火髓果从齿间吐到左手心" (vs. actually swallowing).
        m = re.match(
            rf"^{a}(?:把|将)(?:那枚|这枚|一枚|那颗|这颗)?"
            rf"(?P<fruit>{fruit})从齿间吐到(?P<pos>左手心|右手心)", goal)
        if m:
            return dict(domain="item", entity=m["fruit"], predicate="holder",
                        expected=actor + m["pos"], acting_actor=actor,
                        operation="TEETH_TO_PALM"), "SUPPORTED_TYPED_INTENT"
        m = re.match(
            rf"^{a}(?:把|将)(?:那枚|这枚|一枚|那颗|这颗)?"
            rf"(?P<fruit>{fruit}).{{0,25}}?(?:吞下|吞服|吃下)", goal)
        if m:
            return dict(domain="item", entity=m["fruit"], predicate="holder",
                        expected="已消耗（" + actor + "吞服）",
                        acting_actor=actor,
                        operation="CONSUME_FRUIT"), "SUPPORTED_TYPED_INTENT"
        m = re.match(
            rf"^{a}(?:吞下|吞服|吃下)(?:那枚|这枚|一枚|那颗|这颗)?"
            rf"(?P<fruit>{fruit})", goal)
        if m:
            return dict(domain="item", entity=m["fruit"], predicate="holder",
                        expected="已消耗（" + actor + "吞服）",
                        acting_actor=actor,
                        operation="CONSUME_FRUIT"), "SUPPORTED_TYPED_INTENT"
        m = re.match(
            rf"^{a}(?:右臂|右手)(?:已经|变得|被迫)?"
            r"(?:受限|抬不起来|不听使唤|垂着)", goal)
        if m:
            return dict(domain="character", entity=actor,
                        predicate="右臂可用性", expected="受限",
                        acting_actor=actor,
                        operation="RIGHT_ARM_LIMITED"), "SUPPORTED_TYPED_INTENT"

    # Explicit hand-off requires a named recipient from the cast.
    m = re.match(
        rf"^{a}(?:把|将)(?:那枚|这枚)?(?P<fruit>{fruit})"
        rf"从(?P<pos>左手心|右手心)(?:取出|拿起)?"
        r"(?:递给|交给)(?P<recipient>[\u4e00-\u9fff]{1,8})", goal)
    if m and m["recipient"] in cast and m["recipient"] != actor:
        return dict(domain="item", entity=m["fruit"], predicate="holder",
                    expected=m["recipient"] + "手中",
                    acting_actor=actor, operation="HANDOFF_FRUIT",
                    recipient=m["recipient"]), "SUPPORTED_TYPED_INTENT"
    return None, "UNSUPPORTED_GOAL_OR_AMBIGUOUS_ACTOR"


def _safe_anchor(event, source, intent, cast):
    evidence = event.get("evidence")
    if type(evidence) is not dict:
        return None
    start, end, quote = (evidence.get("start"),
                          evidence.get("end"), evidence.get("quote"))
    if not (type(start) is int and type(end) is int and
            type(quote) is str and 3 <= len(quote) <= 150 and
            0 <= start < end <= len(source) and
            source[start:end] == quote and source.count(quote) == 1 and
            evidence.get("narrative") == "present"):
        return None
    actor = intent["acting_actor"]
    clean = quote.strip()
    # V116 is narrow but actor parsing can still be fooled by another
    # person's nearby name. Require an explicit named acting subject.
    if intent["domain"] == "item":
        if not clean.startswith(actor + "把") and not clean.startswith(actor + "将"):
            return None
        if intent["operation"] == "HANDOFF_FRUIT":
            recipient = intent["recipient"]
            if recipient not in clean:
                return None
    else:
        # V116 may assign the nearest subject in "沈砚看着唐蜃右臂垂着"
        # to 沈砚; do NOT treat such a narrated observation as his injury.
        marker = re.search(r"右臂|右手", clean)
        if not clean.startswith(actor) or marker is None:
            return None
        if any(name != actor and name in clean[:marker.start()]
               for name in cast):
            return None
        if any(term in clean for term in
               ("不再", "并非", "没有", "不曾", "尚未", "装作",
                "假装", "似乎", "好像", "仿佛", "恢复",
                "痊愈", "治好", "看着", "看见", "望着",
                "瞧见")):
            return None
    # The event quotation may use a disambiguated "果子" alias. Alias
    # resolution only comes from the existing V116 source-bound extractor.
    if not any(op.get("cell", {}).get("domain") == intent["domain"] and
               op["cell"].get("entityId") == intent["entity"] and
               op["cell"].get("predicate") == intent["predicate"] and
               op["cell"].get("scope") == "author_plan"
               for op in event.get("ops", [])):
        return None
    return {"start": start, "end": end,
            "quote_sha256": _hash(quote),
            "event_id": event.get("id")}


def _corroborating_arm_evidence(source, intent, cast):
    """Retain a fresh *source quote* even when an unchanged V116 cell emits
    no new state operation. Repeated observations are provenance, not new
    canonical events or an excuse to infer an unstated character.
    """
    if intent["operation"] != "RIGHT_ARM_LIMITED":
        return []
    actor = intent["acting_actor"]
    others = [name for name in cast if name != actor]
    rows = []
    for start, end, clause, in_speech in source_segments(source):
        if in_speech or not source_narrated(source, start, end):
            continue
        quote = clause.strip()
        if not quote.startswith(actor) or len(quote) > 150 or \
           source.count(quote) != 1:
            continue
        found = re.search(r"右臂.{0,8}(?:甩在身后|垂着|抬不起来)|"
                          r"右手.{0,8}(?:不听使唤)", quote)
        if not found:
            continue
        # "沈砚看着唐蜃右臂垂着" is not an injury of 沈砚.
        if any(name in quote[:found.start()] for name in others):
            continue
        if any(term in quote for term in
               ("不再", "并非", "没有", "不曾", "尚未", "装作", "假装",
                "似乎", "好像", "仿佛", "恢复", "痊愈", "治好",
                "看着", "看见", "望着", "瞧见")):
            continue
        offset = start + len(clause) - len(clause.lstrip())
        # Keep a source span and hash. No raw words leave the audit.
        rows.append({
            "start": offset,
            "end": offset + len(quote),
            "quote_sha256": _hash(quote),
            "event_id": "wf120_source_arm_reaffirmation",
            "observed_value": "受限",
        })
    return rows


def compare_plan_to_prose(*, project_id: str, scene_id: str,
                          beat: dict, prose: str,
                          cast: tuple[str, ...],
                          prior_candidate_state: dict | None = None) -> dict:
    """A bounded evidence receipt; never modify canon, draft or database.

    Three-valued classification applies only to typed subgoal, not full beat.
    An incompatible LAST verified source observation is CONTRADICTED;
    unsupported/ambiguous events stay UNPROVEN (not a literary failure).
    """
    _need(type(project_id) is str and 1 <= len(project_id) <= 128 and
          type(scene_id) is str and 1 <= len(scene_id) <= 128,
          "WF120_SCOPE_INVALID")
    _need(type(prose) is str and 0 < len(prose) <= MAX_SOURCE,
          "WF120_PROSE_BOUNDS")
    _need(type(cast) is tuple and 1 <= len(cast) <= MAX_CAST and
          all(type(x) is str and 1 <= len(x) <= 70 for x in cast)
          and len(set(cast)) == len(cast),
          "WF120_CAST_INVALID")
    _need(type(beat) is dict and
          all(k in beat for k in ("id", "kind", "actor", "goal", "causal_parent"))
          and type(beat["id"]) is str and 1 <= len(beat["id"]) <= 30 and
          type(beat["goal"]) is str and 1 <= len(beat["goal"]) <= MAX_GOAL and
          type(beat["actor"]) is str and beat["actor"] in cast and
          type(beat["kind"]) is str and
          (beat["causal_parent"] is None or
           type(beat["causal_parent"]) is str),
          "WF120_BEAT_INVALID")
    old = prior_candidate_state if prior_candidate_state is not None else {}
    _need(type(old) is dict and len(old) <= 36,
          "WF120_PREVIOUS_STATE_INVALID")
    intent, coverage = _plan_goal(beat, cast)
    observed = []
    source_extraction_unresolved = []
    if intent is not None:
        events = extract_state_events(prose, cast=cast, prior_state=old)
        source_extraction_unresolved = sorted(set(
            x["code"] for x in events["unresolved"] if type(x) is dict and
            type(x.get("code")) is str))[:10]
        for e in events["source_anchored_events"]:
            anchor = _safe_anchor(e, prose, intent, cast)
            if anchor is None:
                continue
            for op in e["ops"]:
                c = op.get("cell", {})
                if (c.get("domain"), c.get("entityId"),
                    c.get("predicate"), c.get("scope")) != (
                    intent["domain"], intent["entity"],
                    intent["predicate"], "author_plan"):
                    continue
                observed.append({**anchor, "observed_value": op["value"]})
        # Upstream's reducer intentionally suppresses repeated identical
        # values. A later explicitly named narrative clause can still be
        # critical independent corroboration for the actor and state.
        observed.extend(_corroborating_arm_evidence(
            prose, intent, cast))
    observed.sort(key=lambda x: (x["start"], x["end"]))
    latest = observed[-1] if observed else None
    if latest is None:
        status = "UNPROVEN"
    elif latest["observed_value"] == intent["expected"]:
        status = "OBSERVED_SOURCE_SUPPORTED"
    else:
        status = "CONTRADICTED"
    _need(status in STATES, "WF120_INVALID_STATUS")
    evidence = None
    if latest is not None:
        evidence = {
            "start": latest["start"], "end": latest["end"],
            "quote_sha256": latest["quote_sha256"],
            "event_id": latest["event_id"],
        }
    receipt = {
        "format": FORMAT,
        "project_id": project_id,
        "scene_id": scene_id,
        "beat_id": beat["id"],
        "parent_beat_id": beat["causal_parent"],
        "goal_sha256": _hash(beat["goal"]),
        "prose_sha256": _hash(prose),
        "previous_candidate_state_sha256": _hash(old),
        "status": status,
        "coverage": coverage,
        "expected_narrow_state": intent,
        "last_observed_state": (
            latest["observed_value"] if latest else None),
        "observed_anchor": evidence,
        "source_extraction_unresolved_codes": source_extraction_unresolved,
        "only_source_text_events_are_evidence": True,
        "model_trace_or_self_evaluation_ignored": True,
        "whole_beat_goal_verified": False,
        "source_based_literary_semantics_proven": False,
        "canon_writes": 0,
        "model_calls": 0,
        "automatic_retry": False,
        "author_accepted": False,
        "contains_raw_prose": False,
    }
    receipt["receipt_sha256"] = _hash(receipt)
    return receipt


def pending_dependency_hint(next_beat: dict, receipts: list[dict]) -> str:
    """Light only a *direct dependency* on a failed stateful intention.

    Never require the prose to copy a rigid plan or force a retry.
    """
    _need(type(next_beat) is dict and
          type(receipts) is list and len(receipts) <= 16,
          "WF120_DEPENDENCY_INPUT_INVALID")
    parent = next_beat.get("causal_parent")
    if parent is None:
        return ""
    for r in receipts[-MAX_DEBTS:]:
        if (r.get("format") == FORMAT and r.get("beat_id") == parent
            and r.get("coverage") == "SUPPORTED_TYPED_INTENT"
            and r.get("status") in ("UNPROVEN", "CONTRADICTED")):
            return ("\n【上一事件的计划不是已发生事实】上一因果事件的"
                    "关键状态没有得到正文证实；下一段只能以实际已写出的"
                    "状态承接。允许调整行动方向，不强迫补写原计划。")
    return ""
