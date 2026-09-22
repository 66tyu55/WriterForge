from __future__ import annotations
import json
from dataclasses import dataclass

@dataclass
class Finding:
    code: str
    severity: str
    message: str
    ref: str = ""

class ValidatorSuite:
    def __init__(self, db, project_id: str):
        self.db = db
        self.project_id = project_id

    def validate_causality(self):
        out = []
        rows = self.db.conn.execute(
            "SELECT event_id,payload_json FROM causal_events WHERE project_id=?", (self.project_id,)
        ).fetchall()
        required = ["cause","trigger","character_choice","immediate_result"]
        for r in rows:
            p = json.loads(r["payload_json"])
            missing = [k for k in required if not p.get(k)]
            if missing:
                out.append(Finding("MISSING_TRIGGER","blocking",
                    f"Causal event {r['event_id']} missing: {', '.join(missing)}",r["event_id"]))
        return out

    def validate_promises(self):
        out = []
        meta = self.db.conn.execute(
            "SELECT current_chapter FROM project_meta WHERE project_id=?", (self.project_id,)
        ).fetchone()
        current_chapter = int(meta["current_chapter"]) if meta else 1
        rows = self.db.conn.execute(
            "SELECT promise_id,payload_json,status FROM promises WHERE project_id=?", (self.project_id,)
        ).fetchall()
        for r in rows:
            p = json.loads(r["payload_json"])
            if r["status"] == "open" and p.get("importance") == "high" and not p.get("expected_window_end"):
                out.append(Finding("PROMISE_WINDOW_MISSING","warning",
                    f"High-importance promise {r['promise_id']} has no expected window",r["promise_id"]))
            end = p.get("expected_window_end")
            if r["status"] == "open" and isinstance(end, int) and current_chapter > end:
                out.append(Finding("PROMISE_FORGOTTEN","blocking",
                    f"Promise {r['promise_id']} passed expected chapter {end}; current={current_chapter}",r["promise_id"]))
        return out

    def validate_knowledge(self):
        out = []
        rows = self.db.conn.execute(
            "SELECT character_id,state_json FROM character_state WHERE project_id=?", (self.project_id,)
        ).fetchall()
        for r in rows:
            s = json.loads(r["state_json"])
            k = s.get("knowledge", {})
            knows = set(k.get("knows", []))
            does_not = set(k.get("does_not_know", []))
            for fact in knows & does_not:
                out.append(Finding("KNOWLEDGE_CONFLICT","blocking",
                    f"{r['character_id']} both knows and does not know {fact}",r["character_id"]))
        return out

    def validate_dead_character_actions(self):
        out = []
        states = {}
        for r in self.db.conn.execute(
            "SELECT character_id,state_json FROM character_state WHERE project_id=?", (self.project_id,)
        ):
            states[r["character_id"]] = json.loads(r["state_json"])
        for a in self.db.conn.execute(
            "SELECT actor_id,time_index,action,ref FROM story_actions WHERE project_id=?", (self.project_id,)
        ):
            s = states.get(a["actor_id"], {})
            death = s.get("death_time_index")
            alive = s.get("alive", True)
            if (alive is False and death is None) or (isinstance(death, int) and a["time_index"] > death):
                out.append(Finding("DEAD_CHARACTER_ACTION","blocking",
                    f"{a['actor_id']} acts at {a['time_index']} after death",a["ref"] or a["actor_id"]))
        return out

    def validate_pov(self):
        out = []
        for r in self.db.conn.execute(
            "SELECT * FROM narrative_claims WHERE project_id=?", (self.project_id,)
        ):
            if r["access_type"] == "internal_thought" and r["accessed_character"] != r["pov_character"]:
                out.append(Finding("POV_LEAK","blocking",
                    f"POV {r['pov_character']} accesses {r['accessed_character']}'s internal thought",
                    r["ref"] or r["scene_id"]))
        return out

    def validate_items(self):
        out = []
        rows = self.db.conn.execute(
            """SELECT item_id,time_index,COUNT(DISTINCT COALESCE(holder,'') || '|' || COALESCE(location,'')) AS variants
               FROM item_claims WHERE project_id=?
               GROUP BY item_id,time_index HAVING variants>1""",
            (self.project_id,)
        ).fetchall()
        for r in rows:
            out.append(Finding("ITEM_LOCATION_CONFLICT","blocking",
                f"Item {r['item_id']} has conflicting location/holder claims at time {r['time_index']}",
                r["item_id"]))
        return out

    def validate_timeline(self):
        out = []
        rows = [dict(r) for r in self.db.conn.execute(
            "SELECT * FROM timeline_presence WHERE project_id=? ORDER BY character_id,start_index",
            (self.project_id,)
        )]
        for r in rows:
            if r["start_index"] > r["end_index"]:
                out.append(Finding("TIMELINE_RANGE_INVALID","blocking",
                    f"{r['character_id']} has inverted time range",r["ref"] or r["character_id"]))
        by_char = {}
        for r in rows:
            by_char.setdefault(r["character_id"], []).append(r)
        for char, spans in by_char.items():
            for i in range(len(spans)):
                for j in range(i+1, len(spans)):
                    a,b = spans[i],spans[j]
                    overlap = max(a["start_index"],b["start_index"]) <= min(a["end_index"],b["end_index"])
                    if overlap and a["location"] != b["location"]:
                        out.append(Finding("TIMELINE_LOCATION_CONFLICT","blocking",
                            f"{char} occupies {a['location']} and {b['location']} in overlapping time",
                            b["ref"] or char))
        return out

    def validate_world_rules(self):
        out = []
        rules = {
            r["rule_key"]: r["expected_value"]
            for r in self.db.conn.execute("SELECT * FROM world_rules WHERE project_id=?", (self.project_id,))
        }
        for a in self.db.conn.execute(
            "SELECT rule_key,asserted_value,ref FROM world_assertions WHERE project_id=?", (self.project_id,)
        ):
            if a["rule_key"] in rules and a["asserted_value"] != rules[a["rule_key"]]:
                out.append(Finding("WORLD_RULE_CONFLICT","blocking",
                    f"{a['rule_key']} expected {rules[a['rule_key']]} but text asserts {a['asserted_value']}",
                    a["ref"] or a["rule_key"]))
        return out

    def run_all(self):
        return (
            self.validate_causality()
            + self.validate_promises()
            + self.validate_knowledge()
            + self.validate_dead_character_actions()
            + self.validate_pov()
            + self.validate_items()
            + self.validate_timeline()
            + self.validate_world_rules()
        )
