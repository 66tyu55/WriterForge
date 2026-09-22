from __future__ import annotations
from dataclasses import dataclass
from .xuehai import XuehaiStore, Query

@dataclass
class Delta:
    path: str
    old: object
    new: object

class ReactiveMiddleware:
    def __init__(self, xuehai: XuehaiStore, project_id: str=""):
        self.xuehai = xuehai
        self.project_id = project_id
        self.last_state: dict = {}

    def diff(self, new_state: dict):
        out = []
        keys = set(self.last_state) | set(new_state)
        for k in sorted(keys):
            old, new = self.last_state.get(k), new_state.get(k)
            if old != new:
                out.append(Delta(k, old, new))
        self.last_state = dict(new_state)
        return out

    def intents_for(self, deltas):
        intents = []
        for d in deltas:
            common = {"project_id": self.project_id or None}
            if d.path == "scene.location":
                intents.append(Query(function="environment", text_terms=(str(d.new),), **common))
            elif d.path == "scene.tension":
                intents.append(Query(function="pacing", text_terms=(str(d.new),), **common))
            elif d.path == "character.emotional_state":
                intents.append(Query(function="emotion_expression", text_terms=(str(d.new),), **common))
            elif d.path == "paragraph.micro_goal":
                intents.append(Query(function="transition", text_terms=(str(d.new),), **common))
            elif d.path == "draft.blocked" and d.new is True:
                intents.append(Query(function="sentence_transition", **common))
        return intents

    def react(self, new_state: dict):
        deltas = self.diff(new_state)
        results = []
        for q in self.intents_for(deltas):
            results.extend(self.xuehai.query(q))
        uniq = {}
        for r in results:
            uniq[r["entry_id"]] = r
        return {
            "deltas": [d.__dict__ for d in deltas],
            "guidance_evidence": list(uniq.values()),
        }

    def accept_guidance(self, entry_id: int):
        if not self.project_id:
            raise ValueError("project_id required to track usage")
        self.xuehai.mark_used(entry_id, self.project_id)
