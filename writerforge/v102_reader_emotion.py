"""V102: opt-in emotional interpretation of chapters already read by WF.

This is a source-anchored candidate interpretation of *emotions* and changed
choices, not an emotional sentiment classifier. Reuses V101 witnesses and
source-frontier checks, creates no second identity graph or CANON truth.
"""
from __future__ import annotations
from .v101_narrative_reader import (
    _witness,_words,_fields,_before,MODES,V101ReadingError,
)

FIELDS=frozenset(("actor_id","before","after","epistemic_mode",
                  "trigger","response","loss","related_event","related_relation",
                  "next_option_change","alternative_reading"))
MAX_EMOTIONS=8

def need(ok,code):
    if not ok:raise V101ReadingError(code)

def validate_read_emotions(*,source_windows,cast,plot,relationships,proposals):
    need(type(proposals) is list and len(proposals)<=MAX_EMOTIONS,
         "WF102_READER_EMOTION_COUNT_BOUND")
    people={p["id"] for p in cast}
    events={p["event_id"]:p for p in plot}
    relation_ids={p["relation_id"] for p in relationships}
    parsed=[]
    for p in proposals:
        _fields(p,FIELDS,"WF102_READER_EMOTION_SCHEMA")
        need(p["actor_id"] in people and p["epistemic_mode"] in MODES,
             "WF102_READER_ACTOR_OR_EPISTEMIC_INVALID")
        for field in ("before","after","next_option_change",
                      "alternative_reading"):
            need(_words(p[field],6,170),
                 "WF102_READER_EMOTION_"+field.upper()+"_UNBOUNDED")
        trigger=_witness(source_windows,p["trigger"])
        response=_witness(source_windows,p["response"])
        need(_before(trigger,response),
             "WF102_READER_EMOTION_REACTION_BEFORE_CAUSE")
        loss=(_witness(source_windows,p["loss"])
              if p["loss"] is not None else None)
        if loss is not None:
            need(_before(trigger,loss),
                 "WF102_READER_LOSS_BEFORE_TRIGGER")
        relation=p["related_relation"]
        need(relation is None or relation in relation_ids,
             "WF102_READER_LINK_TO_UNGROUNDED_RELATION")
        link=p["related_event"]
        need(link is None or link in events,
             "WF102_READER_LINK_TO_UNREAD_EVENT")
        if link is not None:
            # A recorded action exists: a later emotional response is
            # still a model interpretation, NOT semantic causal proof.
            need(_before(events[link]["action_anchor"],response),
                 "WF102_READER_EVENT_ACTION_AFTER_REACTION")
        parsed.append({
            "actor_id":p["actor_id"],"before_hypothesis":p["before"],
            "after_hypothesis":p["after"],
            "epistemic_mode":p["epistemic_mode"],
            "trigger_anchor":trigger,"response_anchor":response,
            "loss_anchor":loss,"related_event":link,
            "related_relation":relation,
            "next_option_change_hypothesis":p["next_option_change"],
            "alternative_reading":p["alternative_reading"],
            "emotion_semantically_verified":False,
            "loss_and_cost_semantically_verified":False,
            "choice_causality_verified":False,
        })
    return parsed
