"""Small time->author contract bridge, derived only from executable V2 state.

No plot templates, model scores or automatic prose rewrite. This is an
informational constraint sheet for an autonomous author, not its decision.
"""
from __future__ import annotations

try:
    from .time_v2 import replay, validate, rational, show, rate, require, TimeV2Error
except ImportError:
    from time_v2 import replay, validate, rational, show, rate, require, TimeV2Error

def time_window(world, observed_events):
    validate(world)
    outcome=replay(world,observed_events)
    state=outcome["final"]
    limit=state["world_clock"]["deadline_hour"]
    hour=state["world_clock"]["hour"]
    actor=state["advancement"]["actor_id"]
    person=state["actors"][actor]
    req=rational(state["advancement"]["min_cultivation_subjective_hours"])
    practiced=rational(person["cultivation_subjective_hours"])
    gap=max(req-practiced,0)
    current_frame=person["frame"]
    current_rate=rate(state["time_frames"][current_frame])
    required_world_hours=gap/current_rate
    can_reach_before_deadline=(hour<=limit and required_world_hours<=limit-hour)
    can_attempt_success=(person["realm_step"]>=state["advancement"]["to_realm"] or
                         gap==0)
    npc_clocks={
        ident:{"lived_subjective_hours":p["lived_subjective_hours"],
               "cultivation_known_hours":p["cultivation_subjective_hours"]}
        for ident,p in state["actors"].items() if ident!=actor
    }
    return {
      "format":"wf.time-author-window.v2",
      "actor_id":actor,
      "world_hour_now":hour,
      "world_hour_deadline":limit,
      "world_hours_left":max(limit-hour,0),
      "world_deadline_already_passed":hour>limit,
      "actor_current_time_frame":current_frame,
      "actor_time_rate_subjective_per_world_hour":show(current_rate),
      "world_hours_of_continuous_training_needed":show(required_world_hours),
      "time_requirement_reachable_before_deadline":can_reach_before_deadline,
      "actor_subjective_hours_elapsed":person["lived_subjective_hours"],
      "actor_real_cultivation_hours":person["cultivation_subjective_hours"],
      "minimum_cultivation_for_possible_success":show(req),
      "remaining_required_subjective_hours":show(gap),
      "could_succeed_if_attempted_now":can_attempt_success,
      "breakthrough_not_guaranteed":True,
      "technique_requires_realm":state["technique"]["min_realm"],
      "technique_can_be_used_now":(
          person["realm_step"]>=state["technique"]["min_realm"] and hour<=limit),
      "npcs_world_hours_also_advanced":True,
      "offscreen_npc_clocks":npc_clocks,
      "no_automatic_plot_event":True,
      "not_a_proof_of_good_writing":True,
    }

def concise_context(window, *, deadline_event="截止事件", other_actors="其他人物"):
    require(all(type(s) is str and 1 <= len(s) <= 60 and "\\n" not in s
                and "\\r" not in s for s in (deadline_event,other_actors)),
            "TIME_CONTEXT_LABEL_INVALID")
    require(type(window) is dict and window.get("format") ==
            "wf.time-author-window.v2","AUTHOR_TIME_WINDOW_INVALID")
    eligible = ("实修时间已满足突破尝试的最低条件，但失败或放弃仍可能。"
                if window["could_succeed_if_attempted_now"] else
                "实修时间还未满足成功突破的最低条件，不能直接写成已经突破。")
    frame_name = {"cave": "洞府", "outside": "洞外"}.get(
        window["actor_current_time_frame"],window["actor_current_time_frame"])
    return (
      f"现在位于{frame_name}，当前时间流速为"
      f"{window['actor_time_rate_subjective_per_world_hour']}主观小时/世界小时；"
      f"现在是世界第{window['world_hour_now']}小时；"
      f"故事的{deadline_event}时限是第{window['world_hour_deadline']}小时，"
      f"外界还剩{window['world_hours_left']}小时。"
      f"主角亲身经历{window['actor_subjective_hours_elapsed']}主观小时，"
      f"已有实修{window['actor_real_cultivation_hours']}主观小时；"
      f"本世界此次突破资格至少需{window['minimum_cultivation_for_possible_success']}实修小时。"
      f"若持续修炼，按目前所在位置的流速还需"
      f"{window['world_hours_of_continuous_training_needed']}个世界小时满足最低时间资格。"
      + eligible +
      f"{other_actors}的时间也已经推进，相关人物的未知想法和行动不能由主角凭空知道。"
      "作者可以自由写出救人、退让、冒险、误判、偶然或失败；"
      "必须给每个真正发生的行动付出时间，不预设突破成功或事件圆满解决。"
    )

def delta(normal,altered,events):
    from copy import deepcopy
    validate(normal);validate(altered)
    a=deepcopy(normal)
    a["time_frames"]["cave"]=deepcopy(altered["time_frames"]["cave"])
    require(a==altered,"NOT_SINGLE_CAVE_RATE_DELTA")
    x=time_window(normal,events)
    y=time_window(altered,events)
    require(x["world_hour_now"]==y["world_hour_now"] and
            x["world_hours_left"]==y["world_hours_left"] and
            x["offscreen_npc_clocks"]==y["offscreen_npc_clocks"],
            "OUTSIDE_WORLD_INCORRECTLY_ACCELERATED")
    return {"same_world_time":True,
            "same_offscreen_clocks":True,
            "eligibility_changed":x["could_succeed_if_attempted_now"] !=
                                  y["could_succeed_if_attempted_now"],
            "normal":x,"altered":y}
