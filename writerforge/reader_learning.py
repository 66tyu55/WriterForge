from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from .runtime import RuntimeEngine, Mode

@dataclass
class ReaderReaction:
    attention: float
    curiosity: float
    urge_to_continue: float
    confusion: float = 0.0
    cognitive_load: float = 0.0
    fear: float = 0.0
    humor: float = 0.0
    anger: float = 0.0
    awe: float = 0.0
    sadness: float = 0.0
    warmth: float = 0.0
    disgust: float = 0.0
    excitement: float = 0.0
    tension: float = 0.0
    attachment: dict | None = None
    predictions: list | None = None
    questions: list | None = None
    first_impression: str = ""
    what_changed: str = ""
    continue_reason: str = ""
    stop_risk: str = ""

class ReaderLearningError(RuntimeError):
    pass

class ReaderLearningSession:
    """
    First-pass reader simulation for LEARN.
    Critical rule: units must be recorded in strict sequence.
    The reaction is locked before craft analysis is attached.
    """

    def __init__(self, db, runtime: RuntimeEngine, session_id: str,
                 work_id: str, snapshot_id: int, total_units: int):
        self.db = db
        self.runtime = runtime
        self.session_id = session_id
        self.work_id = work_id
        self.snapshot_id = int(snapshot_id)
        self.total_units = int(total_units)

    def start(self):
        self.runtime.require(Mode.LEARN)
        self.db.conn.execute(
            """INSERT INTO reader_learning_sessions(
                session_id,work_id,snapshot_id,total_units,next_unit,status
               ) VALUES(?,?,?,?,0,'active')""",
            (self.session_id,self.work_id,self.snapshot_id,self.total_units)
        )
        self.db.conn.commit()

    def _state(self):
        row = self.db.conn.execute(
            "SELECT * FROM reader_learning_sessions WHERE session_id=?",
            (self.session_id,)
        ).fetchone()
        if not row:
            raise ReaderLearningError("Reader learning session not started")
        return row

    def record_first_read(self, unit_index: int, unit_ref: str, reaction: ReaderReaction):
        self.runtime.require(Mode.LEARN)
        state = self._state()
        expected = int(state["next_unit"])
        if int(unit_index) != expected:
            raise ReaderLearningError(
                f"Sequential reader rule violated: expected unit {expected}, got {unit_index}"
            )
        if not (0 <= reaction.urge_to_continue <= 5):
            raise ReaderLearningError("urge_to_continue must be within 0..5")

        r = asdict(reaction)
        self.db.conn.execute(
            """INSERT INTO reader_traces(
                session_id,unit_index,unit_ref,
                attention,curiosity,urge_to_continue,confusion,cognitive_load,
                fear,humor,anger,awe,sadness,warmth,disgust,excitement,tension,
                attachment_json,predictions_json,questions_json,
                first_impression,what_changed,continue_reason,stop_risk,locked
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
            (
                self.session_id,int(unit_index),unit_ref,
                r["attention"],r["curiosity"],r["urge_to_continue"],r["confusion"],r["cognitive_load"],
                r["fear"],r["humor"],r["anger"],r["awe"],r["sadness"],r["warmth"],r["disgust"],
                r["excitement"],r["tension"],
                json.dumps(r["attachment"] or {},ensure_ascii=False),
                json.dumps(r["predictions"] or [],ensure_ascii=False),
                json.dumps(r["questions"] or [],ensure_ascii=False),
                r["first_impression"],r["what_changed"],r["continue_reason"],r["stop_risk"]
            )
        )
        self.db.conn.execute(
            "UPDATE reader_learning_sessions SET next_unit=? WHERE session_id=?",
            (expected+1,self.session_id)
        )
        self.db.conn.commit()

    def attach_craft_analysis(self, unit_index: int, observed_effect: str,
                              craft_mechanism: str, evidence_ref: str="", confidence: float=1.0):
        """
        Second pass only. Requires the first-read reaction to already exist and be locked.
        This prevents hindsight from rewriting the reader reaction.
        """
        self.runtime.require(Mode.LEARN)
        trace = self.db.conn.execute(
            "SELECT locked FROM reader_traces WHERE session_id=? AND unit_index=?",
            (self.session_id,int(unit_index))
        ).fetchone()
        if not trace or int(trace["locked"]) != 1:
            raise ReaderLearningError("Craft analysis requires a locked first-read trace")
        self.db.conn.execute(
            """INSERT INTO reader_craft_links(
                session_id,unit_index,observed_effect,craft_mechanism,evidence_ref,confidence
            ) VALUES(?,?,?,?,?,?)""",
            (self.session_id,int(unit_index),observed_effect,craft_mechanism,evidence_ref,float(confidence))
        )
        self.db.conn.commit()

    def finish(self):
        self.runtime.require(Mode.LEARN)
        state = self._state()
        if int(state["next_unit"]) != int(state["total_units"]):
            raise ReaderLearningError(
                f"Cannot finish: read {state['next_unit']} / {state['total_units']} units"
            )
        self.db.conn.execute(
            "UPDATE reader_learning_sessions SET status='complete' WHERE session_id=?",
            (self.session_id,)
        )
        self.db.conn.commit()

    def trajectory(self):
        rows = self.db.conn.execute(
            """SELECT unit_index,unit_ref,attention,curiosity,urge_to_continue,confusion,
                      cognitive_load,fear,humor,anger,awe,sadness,warmth,disgust,
                      excitement,tension,first_impression,what_changed,continue_reason,stop_risk
               FROM reader_traces
               WHERE session_id=?
               ORDER BY unit_index""",
            (self.session_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def page_turn_risks(self):
        rows = self.trajectory()
        return [
            r for r in rows
            if float(r["urge_to_continue"] or 0) <= 2
            or float(r["confusion"] or 0) >= 4
            or float(r["cognitive_load"] or 0) >= 4
        ]
