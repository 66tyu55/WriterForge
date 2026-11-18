"""WriterForge living-world ecology SHADOW pilot.

Separate actor observations -> independent decisions -> feasible world deltas ->
optional reader traces. No LLM API, no long-term database, no Canon/R2 writes.
The decision callback is an *interface*, not proof that NPCs truly reasoned.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Callable

FORMAT = "wf.world.ecology.shadow.v0.1"
ACTIONS = frozenset({"WAIT", "MOVE", "SECURE", "OFFER", "ACCEPT", "DECLINE", "TELL"})
MAX_ACTORS = 16
MAX_EVENTS = 96
MAX_TICKS = 32
MAX_STRING = 160


class EcologyError(ValueError):
    pass


def _need(ok: bool, why: str) -> None:
    if not ok:
        raise EcologyError(why)


def _digest(obj) -> str:
    return sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")).hexdigest()


def _seal(state: dict) -> dict:
    state = deepcopy(state)
    state["head_sha256"] = _digest({k: v for k, v in state.items()
                                    if k != "head_sha256"})
    return state


def _is_text(x, maximum=MAX_STRING):
    return type(x) is str and 0 < len(x) <= maximum and "\x00" not in x


def new_world(*, places: list[str], roads: list[dict], actors: list[dict],
              water_level: int = 0) -> dict:
    """All opening facts are scenario-author supplied; no discovered truths."""
    _need(1 <= len(places) <= 24 and len(places) == len(set(places)) and
          all(_is_text(x, 60) for x in places), "PLACES_INVALID")
    _need(0 <= water_level <= 9 and type(water_level) is int,
          "WATER_LEVEL_INVALID")
    _need(1 <= len(actors) <= MAX_ACTORS, "ACTOR_CAP_INVALID")
    _need(len(roads) <= 40, "ROUTE_CAP_INVALID")
    for road in roads:
        _need(set(road) == {"a", "b", "blocked_at_water"} and
              road["a"] in places and road["b"] in places and
              road["a"] != road["b"] and
              (road["blocked_at_water"] is None or
               (type(road["blocked_at_water"]) is int and
                1 <= road["blocked_at_water"] <= 9)),
              "ROAD_INVALID")
    by_id = {}
    for a in actors:
        _need(set(a) == {"id", "name", "place", "goal_private", "worry_private",
                           "disposition_private", "resources", "secured", "beliefs",
                           "known_facts"}, "ACTOR_SCHEMA")
        _need(_is_text(a["id"], 40) and _is_text(a["name"], 40) and
              a["id"] not in by_id and a["place"] in places and
              all(_is_text(a[k], 120) for k in (
                  "goal_private", "worry_private", "disposition_private")),
              "ACTOR_ID_OR_PLACE_INVALID")
        _need(type(a["resources"]) is dict and len(a["resources"]) <= 16 and
              all(_is_text(k, 45) and type(v) is int and 0 <= v <= 1000
                  for k, v in a["resources"].items()), "RESOURCES_INVALID")
        _need(type(a["secured"]) is dict and
              set(a["secured"]).issubset(a["resources"]) and
              all(type(v) is int and 0 <= v <= a["resources"][k]
                  for k, v in a["secured"].items()), "SECURED_INVALID")
        _need(type(a["beliefs"]) is list and len(a["beliefs"]) <= 16 and
              all(type(x) is dict and set(x) == {"source", "claim", "status"}
                  and x["status"] == "HEARSAY_NOT_KNOWN"
                  and _is_text(x["source"], 40)
                  and _is_text(x["claim"], 120) for x in a["beliefs"]),
              "BELIEFS_INVALID")
        _need(type(a["known_facts"]) is list and len(a["known_facts"]) <= 24
              and all(_is_text(x, 120) for x in a["known_facts"]),
              "KNOWN_FACTS_INVALID")
        by_id[a["id"]] = deepcopy(a)
    return _seal({"format": FORMAT, "tick": 0, "previous_sha256": None,
                  "places": list(places), "roads": deepcopy(roads),
                  "actor_order": list(by_id), "actors": by_id,
                  "environment": {"water_level": water_level,
                                  "rain": "UNKNOWN"},
                  "events": [], "offers": [], "model_calls": 0, "canon_writes": 0,
                  "semantic_truth_verified": False,
                  "author_review_required": True})


def validate(state: dict) -> bool:
    _need(type(state) is dict and state.get("format") == FORMAT and
          type(state.get("head_sha256")) is str and
          state["head_sha256"] == _digest({k: v for k, v in state.items()
                                           if k != "head_sha256"}),
          "SEALED_STATE_INVALID")
    _need(type(state["tick"]) is int and 0 <= state["tick"] <= MAX_TICKS and
          state["model_calls"] == 0 and state["canon_writes"] == 0 and
          state["semantic_truth_verified"] is False and
          state["author_review_required"] is True and
          type(state["actor_order"]) is list and
          list(state["actors"]) == state["actor_order"] and
          1 <= len(state["actor_order"]) <= MAX_ACTORS,
          "STATE_SCOPE_INVALID")
    _need(type(state["events"]) is list and len(state["events"]) <= MAX_EVENTS and
          type(state.get("offers")) is list and len(state["offers"]) <= 24 and
          type(state["environment"]["water_level"]) is int and
          0 <= state["environment"]["water_level"] <= 9,
          "EVENT_OR_ENVIRONMENT_INVALID")
    _need(len(json.dumps(state, ensure_ascii=False)) <= 100000,
          "STATE_TOO_LARGE")
    return True


def _local_routes(state: dict, location: str) -> list[dict]:
    edges = []
    for road in state["roads"]:
        target = (road["b"] if road["a"] == location else
                  road["a"] if road["b"] == location else None)
        if target is None:
            continue
        threshold = road["blocked_at_water"]
        edges.append({"to": target,
                      "passable_now": (threshold is None or
                                       state["environment"]["water_level"] < threshold)})
    return edges


def actor_view(state: dict, actor_id: str) -> dict:
    """The only payload permitted to an actor's external thinker.

    Excludes other NPC's private plans, fears, resources, beliefs and distant
    activities. 'In sight' is a possible observation, not telepathy.
    """
    validate(state)
    _need(actor_id in state["actors"], "UNKNOWN_ACTOR")
    a = state["actors"][actor_id]
    local = a["place"]
    visible = [state["actors"][k]["name"] for k in state["actor_order"]
               if k != actor_id and state["actors"][k]["place"] == local]
    nearby_events = [
        {"id": x["id"], "tick": x["tick"], "type": x["kind"],
         "physical_trace": x["trace"]}
        for x in state["events"] if actor_id in x["potential_witnesses"]
        and x["kind"] not in ("ENVIRONMENT",)
    ][-6:]
    return deepcopy({"actor_id": actor_id, "name": a["name"],
                     "tick": state["tick"], "location": local,
                     "own_goal": a["goal_private"],
                     "own_worry": a["worry_private"],
                     "own_disposition": a["disposition_private"],
                     "own_resources": a["resources"],
                     "own_secured": a["secured"],
                     "my_beliefs_are_not_verified_facts": a["beliefs"],
                     "known_facts": a["known_facts"],
                     "offers_to_me": [
                         {"offer_id": o["id"], "by": o["from"],
                          "item": o["item"], "quantity": o["quantity"]}
                         for o in state["offers"]
                         if o["to"] == actor_id and o["status"] == "PENDING"],
                     "weather_observed": state["environment"]["rain"],
                     "water_level_if_at_quay": (
                         state["environment"]["water_level"]
                         if local in ("quay", "west_bank") else None),
                     "routes_from_here": _local_routes(state, local),
                     "other_people_here": visible,
                     "potentially_seen_recent_actions": nearby_events,
                     "unknown_future_and_other_minds": True})


def _witnesses(state, places: set[str]) -> list[str]:
    return [k for k in state["actor_order"]
            if state["actors"][k]["place"] in places]


def _event(state, *, kind, actor, locations, trace, viewers=None):
    _need(len(state["events"]) < MAX_EVENTS, "EVENT_CAPACITY_REACHED")
    witnesses = (_witnesses(state, set(locations)) if viewers is None else viewers)
    state["events"].append({
        "id": f"E{state['tick']:02d}-{len(state['events'])+1:03d}",
        "tick": state["tick"], "kind": kind, "actor": actor,
        "locations": list(locations), "trace": trace,
        "potential_witnesses": list(dict.fromkeys(witnesses)),
        "source_class": "SYNTHETIC_WORLD_TRANSITION_NOT_NOVEL_CANON",
    })


def _perform(state: dict, actor_id: str, action: dict) -> str:
    """Commit a feasible *action*, not a motivation or future result."""
    a = state["actors"][actor_id]
    _need(type(action) is dict and type(action.get("kind")) is str and
          action["kind"] in ACTIONS and len(action) <= 5,
          "ACTION_SCHEMA_INVALID")
    kind = action["kind"]
    loc = a["place"]
    if kind == "WAIT":
        return "WAITED_NO_PUBLIC_TRACE"
    if kind == "MOVE":
        _need(set(action) == {"kind", "to"}, "MOVE_SCHEMA")
        route = next((r for r in _local_routes(state, loc)
                      if r["to"] == action["to"]), None)
        _need(route is not None, "ROUTE_DOES_NOT_EXIST")
        _need(route["passable_now"], "ROUTE_CURRENTLY_BLOCKED")
        viewers = _witnesses(state, {loc, action["to"]})
        old = a["place"]
        a["place"] = action["to"]
        _event(state, kind=kind, actor=actor_id,
               locations=[old, a["place"]],
               trace=f"{a['name']}离开{old}，到了{a['place']}",
               viewers=viewers)
        return "MOVED"
    if kind == "SECURE":
        _need(set(action) == {"kind", "item", "quantity"}, "SECURE_SCHEMA")
        item, qty = action["item"], action["quantity"]
        _need(_is_text(item, 45) and type(qty) is int and 1 <= qty <= 100,
              "SECURE_AMOUNT_INVALID")
        reserved = sum(o["quantity"] for o in state["offers"]
                       if o["from"] == actor_id and o["item"] == item
                       and o["status"] == "PENDING")
        _need(a["resources"].get(item, 0) - a["secured"].get(item, 0)
              - reserved >= qty, "NOT_ENOUGH_EXPOSED_STOCK")
        _need(a["resources"].get("stamina", 0) >= 1,
              "NO_STAMINA_FOR_WORK")
        a["secured"][item] = a["secured"].get(item, 0) + qty
        a["resources"]["stamina"] -= 1
        _event(state, kind=kind, actor=actor_id,
               locations=[loc], trace=f"{a['name']}在{loc}收好了一些{item}")
        return "STOCK_SECURED_WITH_COST"
    if kind == "OFFER":
        _need(set(action) == {"kind", "target", "item", "quantity"},
              "OFFER_SCHEMA")
        target = action["target"]
        item, qty = action["item"], action["quantity"]
        _need(target in state["actors"] and target != actor_id and
              state["actors"][target]["place"] == loc,
              "OFFER_TARGET_NOT_PRESENT")
        _need(_is_text(item, 45) and type(qty) is int and 1 <= qty <= 100,
              "OFFER_AMOUNT_INVALID")
        reserved = sum(o["quantity"] for o in state["offers"]
                       if o["from"] == actor_id and o["item"] == item
                       and o["status"] == "PENDING")
        _need(a["resources"].get(item, 0) - a["secured"].get(item, 0)
              - reserved >= qty, "OFFER_RESOURCE_NOT_AVAILABLE")
        _need(len(state["offers"]) < 24, "OFFER_CAPACITY")
        offer_id = f"O{state['tick']:02d}-{len(state['offers'])+1:03d}"
        state["offers"].append({"id": offer_id, "from": actor_id,
                                "to": target, "item": item,
                                "quantity": qty, "place": loc,
                                "status": "PENDING"})
        _event(state, kind=kind, actor=actor_id, locations=[loc],
               trace=f"{a['name']}提出给{state['actors'][target]['name']}一些{item}，对方尚未答应")
        return "OFFER_PENDING_NOT_TRANSFERRED"
    if kind in ("ACCEPT", "DECLINE"):
        _need(set(action) == {"kind", "offer_id"}, "OFFER_REPLY_SCHEMA")
        offer = next((o for o in state["offers"] if o["id"] == action["offer_id"]), None)
        _need(offer is not None and offer["to"] == actor_id and
              offer["status"] == "PENDING", "NO_PENDING_OFFER_FOR_ACTOR")
        giver = state["actors"][offer["from"]]
        _need(giver["place"] == a["place"] == offer["place"],
              "PARTICIPANTS_NOT_PRESENT")
        if kind == "ACCEPT":
            item, qty = offer["item"], offer["quantity"]
            _need(giver["resources"].get(item, 0) >= qty,
                  "SOURCE_STOCK_MISSING")
            _need(a["resources"].get(item, 0) + qty <= 1000,
                  "RECIPIENT_CAPACITY")
            giver["resources"][item] -= qty
            a["resources"][item] = a["resources"].get(item, 0) + qty
        offer["status"] = "ACCEPTED" if kind == "ACCEPT" else "DECLINED"
        _event(state, kind=kind, actor=actor_id, locations=[loc],
               trace=(f"{a['name']}接下了{giver['name']}递来的{offer['item']}"
                      if kind == "ACCEPT" else
                      f"{a['name']}拒绝了{giver['name']}的提议"))
        return "OFFER_" + offer["status"]
    if kind == "TELL":
        _need(set(action) == {"kind", "target", "claim"}, "TELL_SCHEMA")
        target, claim = action["target"], action["claim"]
        _need(target in state["actors"] and target != actor_id and
              state["actors"][target]["place"] == loc,
              "TELL_TARGET_NOT_PRESENT")
        _need(_is_text(claim, 120), "TELL_CLAIM_INVALID")
        receiver = state["actors"][target]
        _need(len(receiver["beliefs"]) < 16, "BELIEF_INBOX_FULL")
        receiver["beliefs"].append({"source": actor_id, "claim": claim,
                                    "status": "HEARSAY_NOT_KNOWN"})
        # A private conversation is not automatically visible to bystanders.
        _event(state, kind=kind, actor=actor_id, locations=[loc],
               trace=f"{a['name']}与{receiver['name']}低声交谈",
               viewers=[actor_id, target])
        return "HEARSAY_DELIVERED_NOT_FACT"
    raise EcologyError("ACTION_UNREACHABLE")


def step(state: dict, chooser: Callable[[dict], dict], *,
         rain: str = "NONE", water_delta: int = 0) -> dict:
    """At each tick, all NPCs see one snapshot, decide once, then commit.

    No hidden retry, no model use by engine; chooser is user-supplied and
    might be a future LLM adapter with *separate bounded actor input*.
    Invalid proposals don't become true, and don't mutate prior world.
    """
    validate(state)
    _need(state["tick"] < MAX_TICKS, "TICK_CAPACITY")
    _need(rain in ("NONE", "LIGHT", "HEAVY") and
          type(water_delta) is int and -2 <= water_delta <= 3,
          "ENVIRONMENT_DELTA_INVALID")
    _need(0 <= state["environment"]["water_level"] + water_delta <= 9,
          "WORLD_WATER_BOUNDS")
    next_state = deepcopy(state)
    next_state["previous_sha256"] = state["head_sha256"]
    next_state["tick"] += 1
    next_state["environment"]["rain"] = rain
    next_state["environment"]["water_level"] += water_delta
    if water_delta:
        _event(next_state, kind="ENVIRONMENT", actor=None,
               locations=["quay"] if "quay" in next_state["places"] else [next_state["places"][0]],
               trace="河水涨落，岸边地形发生变化")
    # Every chooser call receives a detached, same-moment *private* viewpoint.
    frozen = _seal(next_state)
    proposed = []
    for actor_id in frozen["actor_order"]:
        input_view = actor_view(frozen, actor_id)
        response = chooser(deepcopy(input_view))
        _need(type(response) is dict and set(response).issubset(
              {"actor_id", "action", "next_goal", "private_reason"}) and
              response.get("actor_id") == actor_id and
              type(response.get("action")) is dict and
              _is_text(response.get("private_reason", ""), 240),
              "DECIDER_RETURN_INVALID")
        if "next_goal" in response:
            _need(_is_text(response["next_goal"], 120),
                  "GOAL_UPDATE_INVALID")
        proposed.append(deepcopy(response))
    receipts = []
    # Resolve in fixed fair, inspectable order. Rejected actions have no
    # physical side effect; their *attempt* stays a private receipt.
    for response in proposed:
        actor_id = response["actor_id"]
        candidate = deepcopy(next_state)
        # Private cognition is owned by the character. Even when a *physical*
        # action fails, a change of mind is real to that character; it is never
        # silently promoted to a public-world outcome.
        goal_changed = "next_goal" in response
        if goal_changed:
            next_state["actors"][actor_id]["goal_private"] = response["next_goal"]
            candidate["actors"][actor_id]["goal_private"] = response["next_goal"]
        accepted = True
        try:
            outcome = _perform(candidate, actor_id, response["action"])
        except EcologyError as exc:
            accepted = False
            outcome = str(exc)
        if accepted:
            next_state = candidate
        receipts.append({"actor_id": actor_id, "accepted": accepted,
                         "outcome": outcome,
                         "private_goal_changed": goal_changed,
                         "private_decision_sha256": _digest(response),
                         "private_reason_not_in_reader": True})
    next_state = _seal(next_state)
    validate(next_state)
    return {"world": next_state, "private_receipts": receipts,
            "model_calls_executed_by_engine": 0,
            "literary_quality_tested": False}


def reader_slice(state: dict, *, viewpoint: str,
                 selected_event_ids: tuple[str, ...] = ()) -> dict:
    """Only author-selected, possibly seen traces. Zero traces is valid.

    Even a potentially visible event need not appear in prose. Never output
    other character's goals, fears, beliefs or failed private proposals.
    """
    validate(state)
    _need(viewpoint in state["actors"] and
          type(selected_event_ids) is tuple and len(selected_event_ids) <= 12 and
          len(set(selected_event_ids)) == len(selected_event_ids),
          "READER_SELECTION_INVALID")
    accessible = {e["id"]: e for e in state["events"]
                  if viewpoint in e["potential_witnesses"]}
    _need(set(selected_event_ids).issubset(accessible),
          "OFFSCREEN_INFORMATION_LEAK_REFUSED")
    return {"viewpoint": viewpoint,
            "narration_candidates": [{"tick": accessible[x]["tick"],
                                      "trace": accessible[x]["trace"]}
                                     for x in selected_event_ids],
            "author_can_omit_every_trace": True,
            "not_actual_prose": True,
            "no_explanation_of_private_motives": True}
