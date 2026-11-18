"""WF living ecology SHADOW: actor-private choice / POV disclosure boundaries.

No LLM, author decisions, semantic inference, canon writes or additional store.
Pure, auditable envelope for integrating independently generated actor decisions.
"""
from __future__ import annotations

import hashlib
import json

MODES = frozenset(("WAIT", "ACT", "RECONSIDER", "DECLINE"))
VISIBILITY = frozenset(("PUBLIC", "WITNESSED", "PRIVATE"))
MAX_ACTORS = 12


class EcologyError(ValueError):
    pass


def _need(ok, reason):
    if not ok:
        raise EcologyError(reason)


def _hash(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode("utf-8")).hexdigest()


def validate(world):
    _need(type(world) is dict and set(world) == {"actors", "events", "clock_ref"},
          "WORLD_SCHEMA")
    _need(type(world["clock_ref"]) is str and world["clock_ref"], "CLOCK_MISSING")
    actors = world["actors"]
    _need(type(actors) is dict and 1 <= len(actors) <= MAX_ACTORS,
          "ACTOR_SET")
    for aid, actor in actors.items():
        _need(type(aid) is str and aid and type(actor) is dict
              and set(actor) == {"location", "concern", "knows", "believes",
                                 "private_plan", "resources", "constraints"},
              "ACTOR_SCHEMA")
        _need(type(actor["location"]) is str and actor["location"],
              "LOCATION_INVALID")
        _need(type(actor["concern"]) is str and bool(actor["concern"]),
              "CONCERN_INVALID")
        for field in ("knows", "believes", "resources", "constraints"):
            _need(type(actor[field]) is list and len(actor[field]) <= 24
                  and all(type(x) is str and x for x in actor[field]),
                  "ACTOR_LIST_INVALID")
        _need(type(actor["private_plan"]) is str, "PRIVATE_PLAN_INVALID")
    events = world["events"]
    _need(type(events) is list and len(events) <= 36, "EVENT_SET")
    for e in events:
        _need(type(e) is dict and set(e) == {"id", "actor", "place",
                                            "outcome", "visibility", "witnesses"},
              "EVENT_SCHEMA")
        _need(type(e["id"]) is str and e["id"]
              and type(e["outcome"]) is str and e["outcome"]
              and type(e["place"]) is str and e["place"],
              "EVENT_CONTENT")
        _need(e["actor"] is None or e["actor"] in actors, "UNKNOWN_EVENT_ACTOR")
        _need(e["visibility"] in VISIBILITY
              and type(e["witnesses"]) is list
              and all(w in actors for w in e["witnesses"]),
              "EVENT_VISIBILITY")
    _need(len({e["id"] for e in events}) == len(events), "DUPLICATE_EVENTS")
    return True


def actor_view(world, actor_id):
    """Strict single-actor packet; no other actor's thoughts or plans."""
    validate(world)
    _need(actor_id in world["actors"], "ACTOR_NOT_FOUND")
    a = world["actors"][actor_id]
    visible = [e for e in world["events"]
               if e["visibility"] == "PUBLIC"
               or actor_id in e["witnesses"]]
    return {"actor_id": actor_id, "clock_ref": world["clock_ref"],
            "location": a["location"], "concern": a["concern"],
            "knows": list(a["knows"]), "believes": list(a["believes"]),
            "private_plan": a["private_plan"],
            "resources": list(a["resources"]),
            "constraints": list(a["constraints"]),
            "visible_events": [dict(id=e["id"], outcome=e["outcome"],
                                    place=e["place"]) for e in visible]}


def submit_choice(world, actor_id, *, mode, intent, observed, result,
                  evidence_refs):
    """One provided choice; NOT automatically generated or successful.

    observed is an actual-world event candidate, never invisible intent.
    Caller owns deciding whether the result happened.
    """
    validate(world)
    _need(actor_id in world["actors"], "ACTOR_NOT_FOUND")
    _need(mode in MODES and type(intent) is str and bool(intent)
          and type(result) is str and bool(result),
          "DECISION_INVALID")
    _need(type(evidence_refs) is list and evidence_refs
          and all(type(s) is str and s for s in evidence_refs),
          "EVIDENCE_REQUIRED")
    _need(type(observed) is list and len(observed) <= 3
          and all(type(e) is dict for e in observed),
          "OBSERVED_EVENTS_INVALID")
    if mode in ("WAIT", "DECLINE"):
        _need(not observed, "NO_AUTOMATIC_EVENT_FOR_INACTION")
    added = {e["id"] for e in world["events"]}
    clone = json.loads(json.dumps(world, ensure_ascii=False))
    for e in observed:
        _need(set(e) == {"id", "place", "outcome", "visibility", "witnesses"},
              "PROPOSAL_EVENT_SCHEMA")
        _need(e["id"] not in added, "EVENT_REUSE")
        added.add(e["id"])
        clone["events"].append({"actor": actor_id, **e})
    validate(clone)
    # Intent, private reasoning and failure details stay on caller's private side.
    # Only actually supplied observable events cross to world/POV.
    return clone


def writer_view(world, pov_actor_id):
    """Writer gets only proven-visible outcomes, NEVER secret plans.

    Returns a compact object; the prose writer may ignore any event.
    No directive to hint or 'pay off' each off-screen activity.
    """
    validate(world)
    _need(pov_actor_id in world["actors"], "ACTOR_NOT_FOUND")
    visible = [e for e in world["events"]
               if e["visibility"] == "PUBLIC"
               or pov_actor_id in e["witnesses"]]
    return {"clock_ref": world["clock_ref"], "pov_actor_id": pov_actor_id,
            "visible_events": [dict(id=e["id"], place=e["place"],
                                    outcome=e["outcome"]) for e in visible],
            "other_characters_private_intentions_included": False,
            "offscreen_events_must_appear_in_prose": False,
            "model_calls": 0}


def example():
    return {
        "clock_ref": "rain-day-3",
        "actors": {
            "A": {"location": "茶棚", "concern": "母亲药费",
                  "knows": ["欠半份工钱"], "believes": ["掌柜明天可能给钱"],
                  "private_plan": "明天讨钱",
                  "resources": ["修壶手艺"], "constraints": ["药钱不足"]},
            "B": {"location": "茶棚", "concern": "生意和债",
                  "knows": ["自己只付了一半"], "believes": ["可能封渡"],
                  "private_plan": "先压成本，未决定明天营业",
                  "resources": ["茶棚"], "constraints": ["现金不足"]},
            "C": {"location": "渡口", "concern": "亲人能否登船",
                  "knows": ["河水上涨"], "believes": ["西岸航道未必可走"],
                  "private_plan": "考虑浅水道",
                  "resources": ["小船"], "constraints": ["天气不稳"]},
            "D": {"location": "米铺", "concern": "防潮",
                  "knows": ["货架底部会进水"], "believes": ["可能继续下雨"],
                  "private_plan": "准备搬高米袋",
                  "resources": ["门板"], "constraints": ["人手不足"]}
        },
        "events": [
            {"id": "rain", "actor": None, "place": "渡口",
             "outcome": "第三天仍下雨", "visibility": "PUBLIC", "witnesses": []}
        ]
    }


def demo():
    world = example()
    before = _hash(writer_view(world, "A"))
    world = submit_choice(world, "C", mode="ACT", intent="改走浅水道",
         observed=[{"id":"depart","place":"渡口","outcome":"小船沿芦苇离岸",
                    "visibility":"WITNESSED","witnesses":["A"]}],
         result="离岸，抵达未知", evidence_refs=["fiction-example/C"])
    world = submit_choice(world, "D", mode="ACT", intent="防潮",
         observed=[{"id":"raise","place":"米铺","outcome":"把一块门板架在长凳上",
                    "visibility":"WITNESSED","witnesses":["A"]}],
         result="搬板完成，存粮是否安全未知",
         evidence_refs=["fiction-example/D"])
    world = submit_choice(world, "B", mode="WAIT", intent="暂不结清工钱",
         observed=[], result="没有向 A 新支付款项",
         evidence_refs=["fiction-example/B"])
    return {"format":"wf.living-ecology.shadow.v1","actors":len(world["actors"]),
            "events_after":len(world["events"]),
            "writer_visible":len(writer_view(world,"A")["visible_events"]),
            "before_view_sha256":before,
            "after_view_sha256":_hash(writer_view(world,"A")),
            "private_motives_disclosed":False,
            "choices_generated_by_model":False,
            "literary_gain_verified":False}


if __name__ == "__main__":
    print(json.dumps(demo(), ensure_ascii=False, indent=2))
