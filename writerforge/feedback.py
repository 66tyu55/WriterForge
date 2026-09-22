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

    def triage(self):
        rows = self.db.conn.execute(
            "SELECT reader_id,chapter_ref,category,severity,comment FROM reader_feedback WHERE project_id=?",
            (self.project_id,),
        ).fetchall()
        by_cat = defaultdict(list)
        for r in rows:
            by_cat[r["category"]].append(dict(r))
        convergent = []
        divergent = []
        for cat, items in by_cat.items():
            readers = {i["reader_id"] for i in items}
            if len(readers) >= 2:
                convergent.append(cat)
            else:
                divergent.append(cat)
        return {
            "counts": {k:len(v) for k,v in by_cat.items()},
            "convergent_signals": sorted(convergent),
            "single_reader_signals": sorted(divergent),
            "items": [dict(r) for r in rows],
        }
