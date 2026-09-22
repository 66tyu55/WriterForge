from __future__ import annotations
import json

class ReaderEffectLibrary:
    """
    Query first-read reactions + second-pass craft links.
    WRITE receives effect-method evidence, not hindsight analysis of future plot.
    """
    def __init__(self, db):
        self.db = db

    def query(self, *, effect: str, min_continue: float=0.0, limit: int=8):
        rows = self.db.conn.execute(
            """SELECT
                 t.session_id,t.unit_index,t.unit_ref,
                 t.urge_to_continue,t.curiosity,t.tension,t.fear,t.humor,t.anger,t.awe,
                 t.first_impression,t.what_changed,t.continue_reason,
                 c.craft_mechanism,c.evidence_ref,c.confidence
               FROM reader_traces t
               JOIN reader_craft_links c
                 ON c.session_id=t.session_id AND c.unit_index=t.unit_index
               WHERE c.observed_effect=?
                 AND t.urge_to_continue>=?
               ORDER BY c.confidence DESC,t.urge_to_continue DESC,t.curiosity DESC
               LIMIT ?""",
            (effect,float(min_continue),int(limit))
        ).fetchall()
        return [dict(r) for r in rows]
