"""WF 仙侠时间规则 V2 — explicitly named units, per-actor clocks, exact ratios.

This computes time and *eligibility*, not a novel, literary quality, skill
training, universal realm laws, or events the author did not choose.
Single-world/original-random-character SHADOW experiment only.
"""
from __future__ import annotations
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import json

FORMAT="wf.xianxia-time-independent-parameters.v2"
MAX_STEPS=40
MAX_ACTORS=12
ACTIVITIES={"cultivate","work","travel","rest","wait","unknown"}
MAX_HOURS_PER_EVENT=1000000
INT_MAX=1000000000

class TimeV2Error(ValueError):
    pass

def require(ok,code):
    if not ok:raise TimeV2Error(code)

def unsigned(value, *, maximum=INT_MAX):
    return type(value) is int and 0 <= value <= maximum

def rate(obj):
    require(type(obj) is dict and set(obj)=={"numerator","denominator"},
            "RATE_FIELDS_MISSING")
    n,d=obj["numerator"],obj["denominator"]
    require(type(n) is int and type(d) is int and
            1 <= n <= 100 and 1 <= d <= 100,
            "TIME_RATE_INVALID")
    return Fraction(n,d)

def rational(value):
    """Explicit value, no binary floating-point numerical training scores."""
    require(type(value) in (str,int),"PARAMETER_MUST_BE_EXACT")
    try:r=Fraction(value)
    except (ValueError,ZeroDivisionError) as exc:
        raise TimeV2Error("TIME_FRACTION_INVALID") from exc
    require(0 <= r <= INT_MAX, "TIME_FRACTION_OUT_OF_RANGE")
    return r

def show(value):
    r=Fraction(value)
    return str(r.numerator) if r.denominator==1 else (
        f"{r.numerator}/{r.denominator}")

def validate(s):
    require(type(s) is dict and set(s)=={
      "format","world_clock","time_frames","actors",
      "advancement","technique","era_history","provenance"},
      "SCHEMA_INVALID")
    require(s["format"]==FORMAT,"TIME_FORMAT_INVALID")
    w=s["world_clock"]
    require(type(w) is dict and set(w)=={"origin","unit","hour","deadline_hour"}
            and type(w["origin"]) is str and 1 <= len(w["origin"]) <= 80
            and w["unit"]=="world_hour"
            and unsigned(w["hour"]) and unsigned(w["deadline_hour"])
            and w["hour"] <= w["deadline_hour"],"WORLD_CLOCK_INVALID")
    frames=s["time_frames"]
    require(type(frames) is dict and 1 <= len(frames) <= 8,
            "TIME_FRAMES_REQUIRED")
    for k,v in frames.items():
        require(type(k) is str and 1 <= len(k) <= 40,"FRAME_ID_INVALID")
        require(rate(v)>0, "FRAME_RATE_INVALID")
    actors=s["actors"]
    require(type(actors) is dict and 1 <= len(actors) <= MAX_ACTORS,
            "ACTORS_INVALID")
    for actor,entry in actors.items():
        require(type(actor) is str and 2<=len(actor)<=24 and
                type(entry) is dict and set(entry)=={
                    "frame","age_subjective_hours","lived_subjective_hours",
                    "cultivation_subjective_hours","realm_step"},
                "ACTOR_TIME_FIELDS_INVALID")
        require(entry["frame"] in frames,"ACTOR_TIME_FRAME_UNKNOWN")
        require(all(rational(entry[x])>=0 for x in (
            "age_subjective_hours","lived_subjective_hours",
            "cultivation_subjective_hours")) and
            type(entry["realm_step"]) is int and
            1<=entry["realm_step"]<=100, "ACTOR_TIME_INVALID")
        require(rational(entry["cultivation_subjective_hours"]) <=
                rational(entry["age_subjective_hours"]),
                "CULTIVATION_EXCEEDS_AGE")
    advance=s["advancement"]
    require(type(advance) is dict and set(advance)=={
        "actor_id","from_realm","to_realm","min_cultivation_subjective_hours"},
        "ADVANCEMENT_RULE_FIELDS_INVALID")
    a=advance["actor_id"]
    require(a in actors and type(advance["from_realm"]) is int
            and actors[a]["realm_step"] in (advance["from_realm"],
                                           advance["to_realm"])
            and advance["to_realm"]==advance["from_realm"]+1
            and rational(advance["min_cultivation_subjective_hours"]) > 0,
            "ADVANCEMENT_RULE_INVALID")
    technique=s["technique"]
    require(type(technique) is dict and set(technique)=={
        "actor_id","min_realm","latest_world_hour"}
        and technique["actor_id"]==a and type(technique["min_realm"]) is int
        and technique["min_realm"]==advance["to_realm"]
        and unsigned(technique["latest_world_hour"])
        and technique["latest_world_hour"]==w["deadline_hour"],
        "TECHNIQUE_RULE_INVALID")
    eras=s["era_history"]
    require(type(eras) is dict and set(eras)=={"current","past","past_exact_hours"}
            and type(eras["current"]) is str and 1<=len(eras["current"])<=50
            and type(eras["past"]) is list and len(eras["past"])<=20
            and all(type(p) is str and 1<=len(p)<=50 and p!=eras["current"]
                    for p in eras["past"]) and
            len(set(eras["past"]))==len(eras["past"]) and
            eras["past_exact_hours"] is None,
            "ERA_UNSUPPORTED_EXACT_DATE")
    provenance=s["provenance"]
    require(type(provenance) is dict and set(provenance)=={
        "source","calibration","is_universal_law"}
        and provenance["source"]=="original_fictional_experiment"
        and provenance["calibration"]=="scenario_assumption"
        and provenance["is_universal_law"] is False,
        "PARAMETER_SOURCE_UNTRUSTED")
    return True

def parameter_dictionary():
    """Independent parameter contracts, no unnamed numeric feature vector."""
    return {
      "world_clock.hour":{
        "unit":"world_hour","scope":"all_entities",
        "update":"one global advance per event; never per actor"},
      "time_frames.*":{
        "unit":"subjective_hour/world_hour","scope":"frame",
        "update":"immutable within frozen branch; numerator/denominator exact"},
      "actors.*.age_subjective_hours":{
        "unit":"subjective_hour","scope":"actor",
        "update":"elapsed world_hours × frame rate for that actor"},
      "actors.*.lived_subjective_hours":{
        "unit":"subjective_hour","scope":"actor",
        "update":"elapsed world_hours × frame rate, independent of POV"},
      "actors.*.cultivation_subjective_hours":{
        "unit":"subjective_hour","scope":"actor",
        "update":"only explicit cultivate activity × actor frame rate"},
      "advancement.min_cultivation_subjective_hours":{
        "unit":"subjective_hour","scope":"actor",
        "update":"world-specific attempt prerequisite, never success guarantee"},
      "technique.latest_world_hour":{
        "unit":"world_hour","scope":"world",
        "update":"immutable story deadline"},
      "era_history":{
        "unit":"label_only","scope":"world_history",
        "update":"past reference does NOT imply known calendar conversion"},
    }

def apply_event(world,event):
    """Every actor advances concurrently. An unmentioned NPC is NOT frozen."""
    validate(world)
    require(type(event) is dict and "kind" in event,
            "TIME_EVENT_SCHEMA")
    out=deepcopy(world)
    k=event["kind"]
    if k=="advance":
        require(set(event)=={"kind","world_hours","activities"},
                "ADVANCE_EVENT_FIELDS")
        hours=event["world_hours"]
        require(unsigned(hours,maximum=MAX_HOURS_PER_EVENT) and hours>0,
                "ADVANCE_HOURS_INVALID")
        activities=event["activities"]
        require(type(activities) is dict and
                all(a in out["actors"] and
                    act in ACTIVITIES for a,act in activities.items()),
                "ACTIVITY_INVALID")
        out["world_clock"]["hour"]+=hours
        require(out["world_clock"]["hour"]<=INT_MAX,"WORLD_CLOCK_OVERFLOW")
        for actor,p in out["actors"].items():
            elapsed=hours*rate(out["time_frames"][p["frame"]])
            p["age_subjective_hours"]=show(rational(p["age_subjective_hours"])+elapsed)
            p["lived_subjective_hours"]=show(rational(p["lived_subjective_hours"])+elapsed)
            if activities.get(actor)=="cultivate":
                p["cultivation_subjective_hours"]=show(
                    rational(p["cultivation_subjective_hours"])+elapsed)
        return out,{
            "kind":"advance","world_hours":hours,
            "actors_advanced":sorted(out["actors"]),
            "observed_activities":activities,
            "unspecified_activity_is_unknown":True,
        }
    if k=="attempt":
        require(set(event)=={"kind","actor_id","outcome"} and
                event["outcome"] in ("success","failure"),
                "ATTEMPT_EVENT_INVALID")
        actor=event["actor_id"]
        spec=out["advancement"]
        require(actor==spec["actor_id"],"ATTEMPT_ACTOR_UNSUPPORTED")
        p=out["actors"][actor]
        require(p["realm_step"]==spec["from_realm"],
                "ADVANCEMENT_STAGE_UNSUPPORTED")
        eligible=rational(p["cultivation_subjective_hours"]) >= rational(
            spec["min_cultivation_subjective_hours"])
        if event["outcome"]=="success":
            require(eligible,"BREAKTHROUGH_NOT_TIME_ELIGIBLE")
            p["realm_step"]=spec["to_realm"]
        return out,{
            "kind":"attempt","actor_id":actor,
            "time_eligible":eligible,
            "result_declared_by_author":event["outcome"],
            "automatic_breakthrough":False
        }
    if k=="use_technique":
        require(set(event)=={"kind","actor_id"},
                "TECHNIQUE_EVENT_FIELDS")
        p=out["actors"].get(event["actor_id"])
        require(p is not None and event["actor_id"]==out["technique"]["actor_id"],
                "TECHNIQUE_ACTOR_UNKNOWN")
        require(p["realm_step"]>=out["technique"]["min_realm"],
                "TECHNIQUE_REQUIRES_REALM")
        require(out["world_clock"]["hour"]<=out["technique"]["latest_world_hour"],
                "TECHNIQUE_AFTER_DEADLINE")
        return out,{"kind":"use_technique",
                    "operation_eligible":True,
                    "narrative_consequence_guaranteed":False}
    if k=="remember_past_era":
        require(set(event)=={"kind","era"} and
                event["era"] in out["era_history"]["past"],
                "PAST_ERA_UNKNOWN")
        return out,{"kind":"remember_past_era",
                    "actual_past_time_unknown":True,
                    "world_clock_changed":False}
    raise TimeV2Error("UNKNOWN_TIME_ACTION")

def replay(world, events):
    validate(world)
    require(type(events) is list and len(events)<=MAX_STEPS,
            "EVENT_COUNT_INVALID")
    old=deepcopy(world)
    out=deepcopy(world)
    trace=[]
    for ix,evt in enumerate(events,1):
        out,meta=apply_event(out,evt)
        trace.append({"index":ix,"world_hour":out["world_clock"]["hour"],
                      "actor_clocks":{
                        a:{"subjective_hours":p["lived_subjective_hours"],
                           "age_hours":p["age_subjective_hours"],
                           "cultivation_hours":p["cultivation_subjective_hours"],
                           "realm_step":p["realm_step"]}
                        for a,p in out["actors"].items()},
                      "event":evt,"meta":meta})
    return {
        "format":"wf.xianxia-time-replay.v2",
        "initial_sha256":sha256(json.dumps(old,ensure_ascii=False,
                     sort_keys=True).encode()).hexdigest(),
        "final":out,"trace":trace,
        "mechanical_time_replay_valid":True,
        "story_prose_consistency_verified":False,
        "narrative_quality_proven":False
    }

def time_comparison(normal,altered,events):
    """Hold every event equal; change a single registered time-rate parameter."""
    validate(normal);validate(altered)
    a=deepcopy(normal)
    b=deepcopy(altered)
    require(a["time_frames"]["cave"]!=b["time_frames"]["cave"],
            "NO_PARAMETER_CHANGED")
    a["time_frames"]["cave"]=b["time_frames"]["cave"]
    require(a==b,"NOT_A_SINGLE_TIME_RATE_ABLATION")
    aa=deepcopy(normal);bb=deepcopy(altered)
    # Must not break on proposed actions: record an actual counterfactual FAIL.
    outputs=[]
    for data in (aa,bb):
        try:outputs.append({"accepted":True,"result":replay(data,events)})
        except TimeV2Error as exc:
            outputs.append({"accepted":False,"rejection":str(exc)})
    return {
      "format":"wf.time-single-parameter-ablation.v2",
      "held_fixed_events":True,
      "changed_parameter":"time_frames.cave.subjective_per_world_hour",
      "before":show(rate(normal["time_frames"]["cave"])),
      "after":show(rate(altered["time_frames"]["cave"])),
      "original":outputs[0],"altered":outputs[1],
      "story_model_followed_rule":None
    }
