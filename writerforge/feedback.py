from __future__ import annotations
from collections import Counter, defaultdict

class FeedbackStore:
    def __init__(self, db, project_id: str):
        self.db = db
        self.project_id = project_id

    def add(self, *, reader_id: str, chapter_ref: str, category: str, comment: str, severity: int=1):
        self.db.conn.execute(
            """INSERT INTO reader_feedback(project_id,reader_id,chapter_ref,category,severity,comment)
               VALUES(?,?,?,?,?,?)""",
            (self.project_id, reader_id, chapter_ref, category, int(severity), comment),
        )
        self.db.conn.commit()

    def triage(self, *, limit: int = 200):
        """SQL-level aggregate across all history; bounded sample in memory."""
        if not 1 <= limit <= 500:
            raise ValueError("feedback window must be 1..500")
        counts = list(self.db.conn.execute(
            """SELECT category,COUNT(*) AS n,COUNT(DISTINCT reader_id) AS readers
               FROM reader_feedback WHERE project_id=? GROUP BY category""",
            (self.project_id,),
        ))
        rows = self.db.conn.execute(
            """SELECT reader_id,chapter_ref,category,severity,comment
               FROM reader_feedback WHERE project_id=?
               ORDER BY id DESC LIMIT ?""",
            (self.project_id,limit),
        ).fetchall()
        return {
            "counts":{r["category"]:int(r["n"]) for r in counts},
            "convergent_signals":sorted(r["category"] for r in counts if r["readers"]>=2),
            "single_reader_signals":sorted(r["category"] for r in counts if r["readers"]<2),
            "items":[dict(r) for r in rows],
            "items_truncated":sum(r["n"] for r in counts)>len(rows),
        }
