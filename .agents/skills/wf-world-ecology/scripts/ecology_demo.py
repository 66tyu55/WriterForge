"""Reproducible, authored choices for SHADOW world-life demonstration.

This is NOT an LLM run: no pretend-thinking tokens, no automatic prose.
"""
from __future__ import annotations
import json
from ecology_shadow import actor_view, new_world, reader_slice, step


def person(identifier, name, place, goal, worry, resources):
    return {"id": identifier, "name": name, "place": place,
            "goal_private": goal, "worry_private": worry,
            "disposition_private": "可能因眼前情势而改变主意",
            "resources": resources, "secured": {}, "beliefs": [], "known_facts": []}


def choices(view):
    """Deterministic example policy; replace with independently billed calls later."""
    actor = view["actor_id"]
    next_goal = None
    if actor == "grain" and view["own_resources"].get("stamina", 0):
        choice = {"kind": "SECURE", "item": "rice", "quantity": 1}
    elif actor == "boat":
        choice = {"kind": "MOVE", "to": (
            "west_bank" if view["location"] == "quay" else "quay")}
        if view["location"] == "west_bank":
            next_goal = "水路若被封，就留在西岸照看孩子"
    else:
        choice = {"kind": "WAIT"}
    result = {"actor_id": actor, "action": choice,
              "private_reason": "示例测试者供应的私人决定；未调用智能模型"}
    if next_goal:
        result["next_goal"] = next_goal
    return result


def run():
    origin = new_world(
        places=["home", "market", "quay", "west_bank"],
        roads=[{"a": "home", "b": "market", "blocked_at_water": None},
               {"a": "market", "b": "quay", "blocked_at_water": None},
               {"a": "quay", "b": "west_bank", "blocked_at_water": 3}],
        actors=[
            person("azhi", "阿芷", "home", "给母亲抓药", "没拿齐工钱", {"coins": 1}),
            person("grain", "庄二", "market", "保住铺里的米", "连日雨水", {"rice": 4, "stamina": 2}),
            person("boat", "渡娘", "quay", "到西岸接孩子", "河水涨快", {"coins": 2}),
            person("clerk", "巡渠吏", "quay", "核对告示", "签错公文", {"coins": 1})])
    one = step(origin, choices, rain="HEAVY", water_delta=1)
    two = step(one["world"], choices, rain="HEAVY", water_delta=2)
    last = two["world"]
    return {"status": "SYNTHETIC_SHADOW_ONLY", "ticks": last["tick"],
            "actor_count": len(last["actors"]),
            "no_protagonist_action": True,
            "water_level": last["environment"]["water_level"],
            "merchant_secured_rice": last["actors"]["grain"]["secured"]["rice"],
            "boatwoman_actual_location": last["actors"]["boat"]["place"],
            "boatwoman_return_blocked": not two["private_receipts"][2]["accepted"],
            "boatwoman_privately_changed_goal": two["private_receipts"][2]["private_goal_changed"],
            "reader_visible_traces_if_author_selects_none": len(
                reader_slice(last, viewpoint="azhi")["narration_candidates"]),
            "offstage_world_event_count": len(last["events"]),
            "new_model_calls": 0,
            "literary_improvement_proven": False}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
