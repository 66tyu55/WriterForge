from __future__ import annotations
import hashlib, math, re
from dataclasses import dataclass
from .runtime import RuntimeEngine, Mode
from .db import WriterForgeDB

@dataclass
class Query:
    genre: str | None = None
    culture: str | None = None
    function: str | None = None
    effect: str | None = None
    source_role: str | None = None
    text_terms: tuple[str, ...] = ()
    project_id: str | None = None
    limit: int = 8
    max_per_work: int = 2
    max_per_cluster: int = 2
    min_quality: float = 0.0

class XuehaiStore:
    def __init__(self, db: WriterForgeDB, runtime: RuntimeEngine):
        self.db = db
        self.runtime = runtime

    def create_staging_snapshot(self, parent_id: int | None = None, note: str = "") -> int:
        self.runtime.require(Mode.LEARN)
        if parent_id is not None:
            p = self.db.conn.execute(
                "SELECT status FROM snapshots WHERE id=?", (parent_id,)
            ).fetchone()
            if not p or p["status"] != "published":
                raise ValueError("Parent snapshot must be published")
        cur = self.db.conn.execute(
            "INSERT INTO snapshots(parent_id,status,note) VALUES(?,?,?)",
            (parent_id, "staging", note),
        )
        sid = int(cur.lastrowid)

        # Version snapshots are complete views, not deltas.
        if parent_id is not None:
            old_rows = self.db.conn.execute(
                "SELECT * FROM xuehai_entries WHERE snapshot_id=?", (parent_id,)
            ).fetchall()
            for r in old_rows:
                self._insert_row_copy(sid, dict(r))
        self.db.conn.commit()
        return sid

    def _insert_row_copy(self, sid: int, r: dict):
        cur = self.db.conn.execute(
            """INSERT INTO xuehai_entries(
                snapshot_id,work_id,chapter,paragraph,sentence,text,library_class,culture,genre,
                source_role,function,effect,method_cluster,quality_weight,novelty_weight,reuse_policy,source_hash
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (sid,r["work_id"],r["chapter"],r["paragraph"],r["sentence"],r["text"],
             r["library_class"],r["culture"],r["genre"],r["source_role"],r["function"],r["effect"],
             r["method_cluster"],r["quality_weight"],r["novelty_weight"],r["reuse_policy"],r["source_hash"])
        )
        new_id = int(cur.lastrowid)
        self._fts_insert(new_id, r["text"], r["function"], r["effect"], r["method_cluster"])

    def _fts_insert(self, entry_id: int, text: str, function: str, effect: str, method_cluster: str):
        if not self.db.fts_enabled:
            return
        self.db.conn.execute(
            "INSERT INTO xuehai_fts(entry_id,text,function,effect,method_cluster) VALUES(?,?,?,?,?)",
            (entry_id, text or "", function or "", effect or "", method_cluster or "")
        )

    def add_entry(self, snapshot_id: int, *, work_id: str, text: str,
                  chapter: int | None = None, paragraph: int | None = None, sentence: int | None = None,
                  library_class: str = "", culture: str = "", genre: str = "",
                  source_role: str = "auxiliary", function: str = "", effect: str = "",
                  method_cluster: str = "", quality_weight: float = 1.0,
                  novelty_weight: float = 1.0, reuse_policy: str = "technique_only") -> int:
        self.runtime.require(Mode.LEARN)
        status = self.db.conn.execute("SELECT status FROM snapshots WHERE id=?", (snapshot_id,)).fetchone()
        if not status or status["status"] != "staging":
            raise ValueError("Entries may only be added to a staging snapshot")
        normalized = " ".join(text.split()).strip()
        source_hash = hashlib.sha256((work_id+"|"+normalized).encode("utf-8")).hexdigest()
        dup = self.db.conn.execute(
            "SELECT id FROM xuehai_entries WHERE snapshot_id=? AND source_hash=?",
            (snapshot_id, source_hash),
        ).fetchone()
        if dup:
            return int(dup["id"])
        cur = self.db.conn.execute(
            """INSERT INTO xuehai_entries(
                snapshot_id,work_id,chapter,paragraph,sentence,text,library_class,culture,genre,
                source_role,function,effect,method_cluster,quality_weight,novelty_weight,reuse_policy,source_hash
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (snapshot_id,work_id,chapter,paragraph,sentence,text,library_class,culture,genre,
             source_role,function,effect,method_cluster,quality_weight,novelty_weight,reuse_policy,source_hash),
        )
        entry_id = int(cur.lastrowid)
        self._fts_insert(entry_id, text, function, effect, method_cluster)
        self.db.conn.commit()
        return entry_id

    def publish(self, snapshot_id: int) -> None:
        self.runtime.require(Mode.LEARN)
        row = self.db.conn.execute("SELECT status FROM snapshots WHERE id=?", (snapshot_id,)).fetchone()
        if not row or row["status"] != "staging":
            raise ValueError("Snapshot must exist and be staging")
        self.db.conn.execute("UPDATE snapshots SET status='published' WHERE id=?", (snapshot_id,))
        self.db.conn.commit()

    def latest_published(self) -> int | None:
        row = self.db.conn.execute(
            "SELECT id FROM snapshots WHERE status='published' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return int(row["id"]) if row else None

    def mark_used(self, entry_id: int, project_id: str) -> None:
        self.runtime.require(Mode.WRITE)
        self.db.conn.execute(
            """INSERT INTO retrieval_usage(project_id,entry_id,use_count)
               VALUES(?,?,1)
               ON CONFLICT(project_id,entry_id)
               DO UPDATE SET use_count=use_count+1,last_used_at=CURRENT_TIMESTAMP""",
            (project_id, entry_id)
        )
        self.db.conn.commit()

    def _candidate_rows(self, q: Query):
        sid = self.runtime.pinned_snapshot_id
        where = ["e.snapshot_id=?", "e.quality_weight>=?"]
        args = [sid, q.min_quality]
        for field, value in [
            ("genre", q.genre), ("culture", q.culture), ("function", q.function),
            ("effect", q.effect), ("source_role", q.source_role)
        ]:
            if value:
                where.append(f"e.{field}=?")
                args.append(value)

        usage_join = ""
        select_usage = "0 AS use_count"
        if q.project_id:
            usage_join = "LEFT JOIN retrieval_usage u ON u.entry_id=e.id AND u.project_id=?"
            args = [q.project_id] + args
            select_usage = "COALESCE(u.use_count,0) AS use_count"

        sql = f"""
            SELECT e.*, {select_usage}
            FROM xuehai_entries e
            {usage_join}
            WHERE {' AND '.join(where)}
        """
        rows = [dict(r) for r in self.db.conn.execute(sql, args).fetchall()]
        return rows

    def _fts_scores(self, terms: tuple[str,...]) -> dict[int, float]:
        if not self.db.fts_enabled or not terms:
            return {}
        clean = []
        for t in terms:
            t = (t or "").strip().replace('"', ' ')
            if t:
                clean.append(f'"{t}"')
        if not clean:
            return {}
        query = " OR ".join(clean)
        try:
            rows = self.db.conn.execute(
                "SELECT entry_id, bm25(xuehai_fts) AS rank FROM xuehai_fts WHERE xuehai_fts MATCH ? LIMIT 200",
                (query,)
            ).fetchall()
        except Exception:
            return {}
        out = {}
        for r in rows:
            # bm25 lower is better; map to bounded positive score.
            rank = float(r["rank"])
            out[int(r["entry_id"])] = 1.0 / (1.0 + max(0.0, rank + 10.0))
        return out

    def query(self, q: Query):
        self.runtime.require(Mode.WRITE)
        sid = self.runtime.pinned_snapshot_id
        row = self.db.conn.execute("SELECT status FROM snapshots WHERE id=?", (sid,)).fetchone()
        if not row or row["status"] != "published":
            raise ValueError("Pinned snapshot is not published")

        rows = self._candidate_rows(q)
        terms = tuple(t.lower().strip() for t in q.text_terms if t and t.strip())
        fts = self._fts_scores(q.text_terms)

        def score(r):
            hay = " ".join([
                r.get("text",""), r.get("function",""), r.get("effect",""),
                r.get("method_cluster",""), r.get("genre",""), r.get("culture","")
            ]).lower()
            lexical = sum(1.0 for t in terms if t in hay)
            fts_score = 2.0 * fts.get(int(r["id"]), 0.0)
            quality = 0.65 * float(r.get("quality_weight") or 1.0)
            novelty = 0.55 * float(r.get("novelty_weight") or 1.0)
            usage_penalty = 0.85 * math.log1p(float(r.get("use_count") or 0))
            return lexical + fts_score + quality + novelty - usage_penalty

        rows.sort(key=score, reverse=True)

        # Diversity governor: prevent one work / one method cluster from dominating.
        per_work, per_cluster = {}, {}
        selected = []
        for r in rows:
            work = r.get("work_id") or ""
            cluster = r.get("method_cluster") or ""
            if per_work.get(work, 0) >= q.max_per_work:
                continue
            if cluster and per_cluster.get(cluster, 0) >= q.max_per_cluster:
                continue
            selected.append((r, score(r)))
            per_work[work] = per_work.get(work, 0) + 1
            if cluster:
                per_cluster[cluster] = per_cluster.get(cluster, 0) + 1
            if len(selected) >= q.limit:
                break

        out = []
        for r, s in selected:
            out.append({
                "entry_id": r["id"],
                "work_id": r["work_id"],
                "location": [r["chapter"], r["paragraph"], r["sentence"]],
                "function": r["function"],
                "effect": r["effect"],
                "method_cluster": r["method_cluster"],
                "quality_weight": r["quality_weight"],
                "novelty_weight": r["novelty_weight"],
                "usage_count": int(r.get("use_count") or 0),
                "score": round(float(s), 4),
                "reuse_policy": r["reuse_policy"],
                # Safety adapter: never give WRITE a long source passage.
                "evidence_excerpt": r["text"][:80],
            })
        return out
