from __future__ import annotations
import json
from .runtime import RuntimeEngine, Mode
from .db import WriterForgeDB

class CanonPatchRequired(RuntimeError):
    pass

class StoryStore:
    def __init__(self, db: WriterForgeDB, runtime: RuntimeEngine, project_id: str):
        self.db = db
        self.runtime = runtime
        self.project_id = project_id

    def _event(self, event_type, path, old, new):
        self.db.conn.execute(
            "INSERT INTO story_events(project_id,event_type,path,old_json,new_json) VALUES(?,?,?,?,?)",
            (self.project_id, event_type, path, json.dumps(old,ensure_ascii=False), json.dumps(new,ensure_ascii=False)),
        )

    def set_project_position(self, current_chapter: int, current_scene: str=""):
        self.runtime.require(Mode.WRITE)
        self.db.conn.execute(
            """INSERT INTO project_meta(project_id,current_chapter,current_scene) VALUES(?,?,?)
               ON CONFLICT(project_id) DO UPDATE SET
               current_chapter=excluded.current_chapter,current_scene=excluded.current_scene""",
            (self.project_id, int(current_chapter), current_scene)
        )
        self.db.conn.commit()

    def set_character(self, character_id: str, state: dict):
        self.runtime.require(Mode.WRITE)
        row = self.db.conn.execute(
            "SELECT state_json FROM character_state WHERE project_id=? AND character_id=?",
            (self.project_id, character_id),
        ).fetchone()
        old = json.loads(row["state_json"]) if row else None
        self.db.conn.execute(
            """INSERT INTO character_state(project_id,character_id,state_json)
               VALUES(?,?,?)
               ON CONFLICT(project_id,character_id) DO UPDATE SET state_json=excluded.state_json,updated_at=CURRENT_TIMESTAMP""",
            (self.project_id, character_id, json.dumps(state, ensure_ascii=False)),
        )
        self._event("character_changed", f"character.{character_id}", old, state)
        self.db.conn.commit()

    def add_canon(self, canon_id: str, type_: str, statement: str, status: str="immutable", established_at: str=""):
        self.runtime.require(Mode.WRITE)
        old = self.db.conn.execute(
            "SELECT statement,status FROM canon WHERE project_id=? AND canon_id=?",
            (self.project_id, canon_id)
        ).fetchone()
        if old and old["status"] == "immutable" and old["statement"] != statement:
            raise CanonPatchRequired(f"Immutable canon {canon_id} requires patch_canon()")
        self.db.conn.execute(
            """INSERT INTO canon(project_id,canon_id,type,statement,status,established_at)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(project_id,canon_id) DO UPDATE SET
               type=excluded.type,statement=excluded.statement,status=excluded.status,established_at=excluded.established_at""",
            (self.project_id, canon_id, type_, statement, status, established_at),
        )
        self._event("canon_changed", f"canon.{canon_id}", dict(old) if old else None, {"statement":statement,"status":status})
        self.db.conn.commit()

    def patch_canon(self, canon_id: str, new_statement: str, reason: str):
        self.runtime.require(Mode.WRITE)
        old = self.db.conn.execute(
            "SELECT statement FROM canon WHERE project_id=? AND canon_id=?",
            (self.project_id, canon_id)
        ).fetchone()
        if not old:
            raise KeyError(canon_id)
        self.db.conn.execute(
            "INSERT INTO canon_patches(project_id,canon_id,old_statement,new_statement,reason) VALUES(?,?,?,?,?)",
            (self.project_id, canon_id, old["statement"], new_statement, reason)
        )
        self.db.conn.execute(
            "UPDATE canon SET statement=? WHERE project_id=? AND canon_id=?",
            (new_statement, self.project_id, canon_id)
        )
        self._event("canon_patched", f"canon.{canon_id}", old["statement"], new_statement)
        self.db.conn.commit()

    def set_promise(self, promise_id: str, payload: dict, status: str="open"):
        self.runtime.require(Mode.WRITE)
        self.db.conn.execute(
            """INSERT INTO promises(project_id,promise_id,payload_json,status)
               VALUES(?,?,?,?)
               ON CONFLICT(project_id,promise_id) DO UPDATE SET payload_json=excluded.payload_json,status=excluded.status""",
            (self.project_id, promise_id, json.dumps(payload,ensure_ascii=False), status),
        )
        self._event("promise_changed", f"promise.{promise_id}", None, {"payload":payload,"status":status})
        self.db.conn.commit()

    def set_reader_state(self, payload: dict):
        self.runtime.require(Mode.WRITE)
        row = self.db.conn.execute("SELECT payload_json FROM reader_state WHERE project_id=?", (self.project_id,)).fetchone()
        old = json.loads(row["payload_json"]) if row else None
        self.db.conn.execute(
            """INSERT INTO reader_state(project_id,payload_json) VALUES(?,?)
               ON CONFLICT(project_id) DO UPDATE SET payload_json=excluded.payload_json""",
            (self.project_id, json.dumps(payload,ensure_ascii=False)),
        )
        self._event("reader_changed", "reader", old, payload)
        self.db.conn.commit()

    def add_causal_event(self, event_id: str, payload: dict):
        self.runtime.require(Mode.WRITE)
        self.db.conn.execute(
            """INSERT INTO causal_events(project_id,event_id,payload_json) VALUES(?,?,?)
               ON CONFLICT(project_id,event_id) DO UPDATE SET payload_json=excluded.payload_json""",
            (self.project_id, event_id, json.dumps(payload,ensure_ascii=False)),
        )
        self._event("causal_changed", f"causal.{event_id}", None, payload)
        self.db.conn.commit()

    def add_story_action(self, actor_id: str, time_index: int, action: str, ref: str=""):
        self.runtime.require(Mode.WRITE)
        self.db.conn.execute(
            "INSERT INTO story_actions(project_id,actor_id,time_index,action,ref) VALUES(?,?,?,?,?)",
            (self.project_id, actor_id, int(time_index), action, ref)
        )
        self.db.conn.commit()

    def add_narrative_claim(self, scene_id: str, pov_character: str, accessed_character: str,
                            access_type: str, text: str="", ref: str=""):
        self.runtime.require(Mode.WRITE)
        self.db.conn.execute(
            """INSERT INTO narrative_claims(project_id,scene_id,pov_character,accessed_character,access_type,text,ref)
               VALUES(?,?,?,?,?,?,?)""",
            (self.project_id, scene_id, pov_character, accessed_character, access_type, text, ref)
        )
        self.db.conn.commit()

    def add_item_claim(self, item_id: str, time_index: int, holder: str|None=None,
                       location: str|None=None, ref: str=""):
        self.runtime.require(Mode.WRITE)
        self.db.conn.execute(
            "INSERT INTO item_claims(project_id,item_id,time_index,holder,location,ref) VALUES(?,?,?,?,?,?)",
            (self.project_id, item_id, int(time_index), holder, location, ref)
        )
        self.db.conn.commit()

    def add_presence(self, character_id: str, start_index: int, end_index: int, location: str, ref: str=""):
        self.runtime.require(Mode.WRITE)
        self.db.conn.execute(
            """INSERT INTO timeline_presence(project_id,character_id,start_index,end_index,location,ref)
               VALUES(?,?,?,?,?,?)""",
            (self.project_id, character_id, int(start_index), int(end_index), location, ref)
        )
        self.db.conn.commit()

    def set_world_rule(self, rule_key: str, expected_value: str, statement: str=""):
        self.runtime.require(Mode.WRITE)
        self.db.conn.execute(
            """INSERT INTO world_rules(project_id,rule_key,expected_value,statement) VALUES(?,?,?,?)
               ON CONFLICT(project_id,rule_key) DO UPDATE SET
               expected_value=excluded.expected_value,statement=excluded.statement""",
            (self.project_id, rule_key, expected_value, statement)
        )
        self.db.conn.commit()

    def assert_world_rule(self, rule_key: str, asserted_value: str, ref: str=""):
        self.runtime.require(Mode.WRITE)
        self.db.conn.execute(
            "INSERT INTO world_assertions(project_id,rule_key,asserted_value,ref) VALUES(?,?,?,?)",
            (self.project_id, rule_key, asserted_value, ref)
        )
        self.db.conn.commit()

    def add_learning_gap(self, capability: str, context: str="", priority: str="medium"):
        self.runtime.require(Mode.WRITE)
        self.db.conn.execute(
            "INSERT INTO learning_gaps(project_id,capability,context,priority) VALUES(?,?,?,?)",
            (self.project_id, capability, context, priority),
        )
        self.db.conn.commit()

    def snapshot(self) -> dict:
        cur = self.db.conn
        chars = {
            r["character_id"]: json.loads(r["state_json"])
            for r in cur.execute("SELECT * FROM character_state WHERE project_id=?", (self.project_id,))
        }
        canon = [dict(r) for r in cur.execute("SELECT * FROM canon WHERE project_id=?", (self.project_id,))]
        promises = [
            {"promise_id":r["promise_id"], "status":r["status"], **json.loads(r["payload_json"])}
            for r in cur.execute("SELECT * FROM promises WHERE project_id=?", (self.project_id,))
        ]
        rr = cur.execute("SELECT payload_json FROM reader_state WHERE project_id=?", (self.project_id,)).fetchone()
        reader = json.loads(rr["payload_json"]) if rr else {}
        causal = [
            {"event_id":r["event_id"], **json.loads(r["payload_json"])}
            for r in cur.execute("SELECT * FROM causal_events WHERE project_id=?", (self.project_id,))
        ]
        return {"characters":chars, "canon":canon, "promises":promises, "reader":reader, "causal":causal}
