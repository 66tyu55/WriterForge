from __future__ import annotations
import hashlib, json, math, re
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


# P0: entry-bound, source-only METHODS, never excerpts or new memory.
_METHOD_SOURCE_KINDS = frozenset((
    "AUTHOR_CREATED_DIAGNOSTIC", "AUTHOR_CREATED_ORIGINAL",
    "PUBLIC_DOMAIN_CLASSIC", "AUTHORIZED_MODERN",
))
_METHOD_KEYS = (
    "scene_type", "scene_facets", "target_genres", "style_scope",
    "signal", "mechanism", "writer_option", "applies_when", "not_when",
    "pov_limit", "counterexample", "source_kind", "source_edition",
    "rights_status", "review_status", "value_status", "review_receipt_sha256",
)
_METHOD_IMMUTABLE = (
    "entry_id", "snapshot_id", "work_id", "entry_source_hash",
    "source_uri", "source_sha256", "source_unit_sha256", "source_locator",
    "scene_type", "scene_facets_json", "target_genres_json", "style_scope",
    "signal", "mechanism", "writer_option", "applies_when", "not_when",
    "pov_limit", "counterexample", "source_kind", "source_edition",
    "rights_status", "review_status", "value_status", "review_receipt_sha256",
)
_METHOD_ALIASES = {
    "资质检测": ("测灵根", "试灵根", "测资质"),
    "闭关修炼": ("闭关", "练气打坐"),
    "炼丹": ("炼丹", "丹炉", "炼制丹药"),
    "炼器": ("炼器", "铸器", "锻打法器"),
    "阵法禁制": ("阵法", "禁制", "阵眼"),
    "破境": ("破境", "冲击境界", "突破瓶颈"),
    "灵兽驯养": ("灵兽驯养", "驯灵兽", "御兽"),
    "近身斗法": ("斗法", "近身搏杀"),
    "法宝远攻": ("远攻法宝", "飞剑追击"),
    "宗门政治": ("宗门争权", "宗门配额", "内门争权", "分药堂"),
    "坊市交易": ("坊市", "拍卖", "交易法宝", "摊主议价"),
    "秘境遗迹": ("秘境", "遗迹探险", "古殿禁制"),
    "志怪接触": ("志怪", "遇鬼", "神祇现身"),
    "师徒与家族": ("师徒", "家族旧债", "师门旧怨"),
    "伤病代价": ("负伤", "伤病", "战后伤势"),
    "边境旅途": ("边境", "旅途", "过关卡"),
}
_METHOD_GENRE_FALLBACK = {
    "丹修": ("丹修", "修真", "仙侠", "玄幻", "广义叙事"),
    "阵修": ("阵修", "修真", "仙侠", "玄幻", "广义叙事"),
    "修真": ("修真", "仙侠", "玄幻", "广义叙事"),
    "仙侠": ("仙侠", "玄幻", "广义叙事"),
    "玄幻": ("玄幻", "广义叙事"),
    "志怪": ("志怪", "古代白话", "广义叙事"),
    "古代白话": ("古代白话", "广义叙事"),
    "武侠": ("武侠", "广义叙事"),
}

def genre_lineage(genre: str) -> tuple[str, ...]:
    """Semantic parent lookup; never cross into 志怪 for a 玄幻 request."""
    return _METHOD_GENRE_FALLBACK.get(genre, (genre,))

def _method_sha(row: dict) -> str:
    payload = {key: row[key] for key in _METHOD_IMMUTABLE}
    return hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf8")).hexdigest()

def _is_digest(value) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None

def _positive_scene_facet(goal:str, facet:str) -> bool:
    """Conservative textual evidence, NOT a full semantic understanding.

    A classic technique is not relevant merely because a scene title appears.
    A concrete observed condition must be present without a nearby explicit
    negation; uncertainty returns NONE rather than injecting false advice.
    """
    start=0
    while True:
        at=goal.find(facet,start)
        if at<0:
            return False
        context=goal[max(0,at-10):at]
        if not re.search(r"(?:没有|从未|未曾|尚无|并无|不具备|不存在|缺乏|毫无|未有|无)(?:.{0,2})$",context):
            return True
        start=at+len(facet)


def _source_overlap(source: str, guidance: str, window: int = 14) -> bool:
    if not source or not guidance:
        return False
    if len(source) < window:
        return len(source) >= 8 and source in guidance
    return any(source[i:i+window] in guidance for i in range(len(source)-window+1))

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
        # New children store ONLY their own entries; ancestor lookup resolves
        # a logical view. Existing V22 'full' snapshots remain valid roots.
        cur = self.db.conn.execute(
            "INSERT INTO snapshots(parent_id,status,layout,note) VALUES(?,?,?,?)",
            (parent_id,"staging","delta" if parent_id is not None else "full",note),
        )
        sid = int(cur.lastrowid)
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

    def read_literary_reading(self, entry_id: int) -> dict:
        """Read full 古籍或原创的原文/批注/心得, not an 80-character search hit.

        Explicit only; requires a published pinned snapshot. Never
        automatically inject a classical quotation into author prose.
        """
        self.runtime.require(Mode.WRITE)
        if type(entry_id) is not int or entry_id < 1:
            raise ValueError("XUEHAI_READING_ENTRY_INVALID")
        sid=self.runtime.pinned_snapshot_id
        row=self.db.conn.execute(
            """WITH RECURSIVE lineage(id,parent_id,layout) AS (
                SELECT id,parent_id,layout FROM snapshots
                 WHERE id=? AND status='published'
                UNION ALL
                SELECT p.id,p.parent_id,p.layout FROM snapshots p
                 JOIN lineage l ON l.parent_id=p.id
                 WHERE l.layout='delta' AND p.status='published'
            )
            SELECT e.text,e.work_id,e.source_hash FROM xuehai_entries e
             JOIN lineage l ON l.id=e.snapshot_id
             WHERE e.id=? AND e.source_role IN (?,?)""",
            (sid,entry_id,"classical_original_annotation_reflection",
             "original_annotation_reflection"),
        ).fetchone()
        if row is None:
            raise ValueError("XUEHAI_READING_NOT_PUBLISHED_OR_NOT_FOUND")
        full=row["text"]
        normalized=" ".join(full.split()).strip()
        expected=hashlib.sha256((row["work_id"]+"|"+normalized).encode("utf8")).hexdigest()
        if not 200<=len(full)<=5000 or row["source_hash"]!=expected:
            raise ValueError("XUEHAI_READING_SOURCE_CHANGED")
        try:
            source_and_original,reflection=full.split("\n【心得】\n",1)
            source_original,annotations=source_and_original.split("\n【批注】\n",1)
            source,original=source_original.split("\n【原文】\n",1)
            if not source.startswith("【出处】") or not original.strip() or not reflection.strip():
                raise ValueError()
            notes=annotations.splitlines()
            if len(notes)!=3:
                raise ValueError()
        except ValueError:
            raise ValueError("XUEHAI_READING_THREE_PARTS_MISSING") from None
        return {"entry_id":entry_id,"source":source[4:],
                "original":original,"annotations":notes,"reflection":reflection}

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
        """Bounded SQL-side candidate selection over the logical snapshot.

        Legacy full snapshots are terminal ancestors. New delta descendants do
        not materialize/copy prior rows. No full-corpus .fetchall() ever runs.
        """
        if not 1 <= q.limit <= 32:
            raise ValueError("query limit must be 1..32")
        if not 1 <= q.max_per_work <= 32 or not 1 <= q.max_per_cluster <= 32:
            raise ValueError("diversity limits must be 1..32")
        sid = self.runtime.pinned_snapshot_id
        filters = ["e.quality_weight>=?"]
        where_args = [q.min_quality]
        for field, value in [
            ("genre", q.genre), ("culture", q.culture), ("function", q.function),
            ("effect", q.effect), ("source_role", q.source_role),
        ]:
            if value:
                filters.append(f"e.{field}=?")
                where_args.append(value)
        use = "0 AS use_count"
        join = ""
        if q.project_id:
            join = "LEFT JOIN retrieval_usage u ON u.entry_id=e.id AND u.project_id=?"
            use = "COALESCE(u.use_count,0) AS use_count"
            # Bound separately: JOIN placeholders precede WHERE placeholders.
        rank_parts = []
        for t in q.text_terms[:6]:
            if t and t.strip():
                rank_parts.append("CASE WHEN e.text LIKE ? THEN 4.0 ELSE 0 END")
        rank_args = ["%" + t.strip()[:48].replace("%", r"\%").replace("_", r"\_") + "%"
                     for t in q.text_terms[:6] if t and t.strip()]
        lexical = "+".join(rank_parts) if rank_parts else "0"
        # SELECT only a bounded shortlist. Query index and result memory stays
        # O(limit), rather than O(total entries across the learned novels).
        sql = f"""
          WITH RECURSIVE lineage(id,parent_id,layout) AS (
            SELECT id,parent_id,layout FROM snapshots
             WHERE id=? AND status='published'
            UNION ALL
            SELECT parent.id,parent.parent_id,parent.layout
              FROM snapshots parent JOIN lineage child ON parent.id=child.parent_id
             WHERE child.layout='delta' AND parent.status='published'
          )
          SELECT e.*, {use} FROM xuehai_entries e
          JOIN lineage l ON l.id=e.snapshot_id
          {join}
          WHERE {' AND '.join(filters)}
          ORDER BY ({lexical}) + 0.65*COALESCE(e.quality_weight,1)
                 + 0.55*COALESCE(e.novelty_weight,1) DESC,
                 e.id DESC
          LIMIT ?
        """
        # The project usage join parameter precedes WHERE parameters in SQL.
        bind = [sid] + ([q.project_id] if q.project_id else []) + where_args + rank_args
        bind.append(min(512, max(64, q.limit * 24)))
        return [dict(r) for r in self.db.conn.execute(sql, bind).fetchall()]

    def _fts_scores(self, terms: tuple[str,...]) -> dict[int, float]:
        if not self.db.fts_enabled or not terms:
            return {}
        clean = []
        for t in terms[:6]:
            t = (t or "").strip()[:48].replace('"', ' ')
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

    # --- 0.BL: reviewed, rights-gated method cards IN the existing Xuehai ---
    def add_method_card(self, entry_id: int, card: dict) -> dict:
        """LEARN-only; record a conditional method, not a quote or an approval.

        PENDING diagnostic cards may reference an unstudied diagnostic work,
        but PILOT_APPROVED requires an actual studied chapter and source span.
        The review receipt is a reference hash, never proof of independent review.
        """
        self.runtime.require(Mode.LEARN)
        if type(card) is not dict or set(card) != set(_METHOD_KEYS):
            raise ValueError("METHOD_CARD_SCHEMA_INVALID")
        if not isinstance(entry_id, int) or type(entry_id) is not int:
            raise ValueError("METHOD_ENTRY_INVALID")
        row = self.db.conn.execute(
            """SELECT e.*, s.status AS snapshot_status, w.source_uri,
                      w.source_sha256 AS source_sha256
                 FROM xuehai_entries e
                 JOIN snapshots s ON s.id=e.snapshot_id
                 LEFT JOIN studied_works w ON w.work_id=e.work_id
                WHERE e.id=?""", (entry_id,)
        ).fetchone()
        if not row or row["snapshot_status"] != "staging":
            raise ValueError("METHOD_REQUIRES_STAGING_XUEHAI_ENTRY")
        if not row["source_uri"] or not _is_digest(row["source_sha256"]):
            raise ValueError("METHOD_SOURCE_WORK_SHA_REQUIRED")
        if row["source_uri"].startswith(("r2://", "s3://")):
            raise ValueError("METHOD_PRIVATE_SOURCE_NOT_ELIGIBLE")
        for key in _METHOD_KEYS:
            if key in ("scene_facets", "target_genres"):
                val = card[key]
                if (type(val) is not list or not 1 <= len(val) <= 6 or
                    any(type(x) is not str or not 2 <= len(x.strip()) <= 24
                        for x in val) or len(set(val)) != len(val)):
                    raise ValueError("METHOD_SCENE_FACETS_INVALID")
            elif type(card[key]) is not str:
                raise ValueError("METHOD_CARD_FIELD_INVALID")
            elif key not in ("review_receipt_sha256",) and not (
                    2 <= len(card[key].strip()) <= 180):
                raise ValueError("METHOD_FIELD_UNBOUNDED")
        if (card["style_scope"] not in ("ERA_NEUTRAL", "CLASSICAL_ONLY") or
            card["source_kind"] not in _METHOD_SOURCE_KINDS or
            card["rights_status"] not in ("ORIGINAL_DIAGNOSTIC","RIGHTS_VERIFIED","RIGHTS_UNVERIFIED") or
            card["review_status"] not in ("PENDING","PILOT_APPROVED","REJECTED") or
            card["value_status"] not in ("UNVERIFIED","UNPROVEN_PILOT","NEGATIVE")):
            raise ValueError("METHOD_UNRECOGNIZED_RIGHTS_REVIEW_VALUE")
        if card["source_kind"] == "AUTHOR_CREATED_DIAGNOSTIC":
            if (card["review_status"] != "PENDING" or
                card["rights_status"] != "ORIGINAL_DIAGNOSTIC" or
                card["value_status"] != "UNVERIFIED" or
                row["source_role"] != "diagnostic_only"):
                raise ValueError("METHOD_DIAGNOSTIC_MUST_REMAIN_PENDING")
        elif card["review_status"] == "PILOT_APPROVED":
            if not _is_digest(card["review_receipt_sha256"]):
                raise ValueError("METHOD_REVIEW_RECEIPT_REQUIRED")
            if (row["source_role"] == "diagnostic_only" or
                row["reuse_policy"] != "technique_only"):
                raise ValueError("METHOD_UNAPPROVED_SOURCE_ROLE")
        if (card["source_kind"] in ("PUBLIC_DOMAIN_CLASSIC","AUTHORIZED_MODERN")
                and card["review_status"]=="PILOT_APPROVED"):
            raise ValueError("METHOD_EXTERNAL_AUTHORITIES_REQUIRED_NOT_SELF_REVIEW")
        if (card["source_kind"] == "PUBLIC_DOMAIN_CLASSIC" and
                card["source_edition"].strip() in ("", "unknown", "未知")):
            raise ValueError("METHOD_CLASSIC_EDITION_UNVERIFIED")
        span = self.db.conn.execute(
            """SELECT source_sha256, excerpt FROM source_spans
                WHERE work_id=? AND chapter=? AND paragraph=? AND sentence=?""",
            (row["work_id"],row["chapter"],row["paragraph"],row["sentence"])
        ).fetchone()
        studied = self.db.conn.execute(
            """SELECT c.chapter_sha256, c.snapshot_id, s.status AS status
                 FROM studied_chapters c JOIN snapshots s ON s.id=c.snapshot_id
                WHERE c.work_id=? AND c.chapter=?""",
            (row["work_id"], row["chapter"]),
        ).fetchone()
        # A staging method cannot bestow a study certificate by itself.
        if card["review_status"] == "PILOT_APPROVED":
            if (not span or not studied or studied["status"] != "published"
                or not _is_digest(span["source_sha256"])
                or not _is_digest(studied["chapter_sha256"])
                or span["excerpt"] != row["text"]):
                raise ValueError("METHOD_SOURCE_STUDY_REQUIRED")
            # A derived Xuehai delta is valid only if the original studied
            # chapter is a published ancestor of its staging snapshot.
            ancestor = self.db.conn.execute(
                """WITH RECURSIVE lineage(id,parent_id,layout) AS (
                       SELECT id,parent_id,layout FROM snapshots WHERE id=?
                       UNION ALL
                       SELECT p.id,p.parent_id,p.layout
                         FROM snapshots p JOIN lineage l ON l.parent_id=p.id
                        WHERE l.layout='delta' AND p.status='published'
                   ) SELECT 1 FROM lineage WHERE id=? LIMIT 1""",
                (row["snapshot_id"],studied["snapshot_id"])
            ).fetchone()
            if not ancestor:
                raise ValueError("METHOD_SOURCE_SNAPSHOT_NOT_IN_LINEAGE")
        immutable = {
            "entry_id":entry_id, "snapshot_id":row["snapshot_id"],
            "work_id":row["work_id"], "entry_source_hash":row["source_hash"],
            "source_uri":row["source_uri"], "source_sha256":row["source_sha256"],
            "source_unit_sha256":span["source_sha256"] if span else "",
            "source_locator":f"{row['chapter']}:{row['paragraph']}:{row['sentence']}",
        }
        for key in _METHOD_KEYS:
            if key == "scene_facets":
                immutable["scene_facets_json"] = json.dumps(card[key],ensure_ascii=False,separators=(",",":"))
            elif key == "target_genres":
                immutable["target_genres_json"] = json.dumps(card[key],ensure_ascii=False,separators=(",",":"))
            else:
                immutable[key] = card[key].strip()
        if (card["review_status"] == "PILOT_APPROVED" and span and
            any(_source_overlap(span["excerpt"],immutable[k]) for k in (
                "signal", "mechanism", "writer_option", "applies_when",
                "not_when", "pov_limit", "counterexample"))):
            raise ValueError("METHOD_SOURCE_QUOTATION_NOT_TRANSFERABLE")
        immutable["card_sha256"] = _method_sha(immutable)
        columns = _METHOD_IMMUTABLE + ("card_sha256",)
        self.db.conn.execute(
            f"INSERT INTO xuehai_method_cards ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
            [immutable[k] for k in columns],
        )
        self.db.conn.commit()
        return {"entry_id":entry_id, "snapshot_id":row["snapshot_id"],
                "card_sha256":immutable["card_sha256"],
                "review_status":immutable["review_status"],
                "value_status":immutable["value_status"]}

    def revoke_method_card(self, entry_id: int) -> bool:
        """Preserve card SHA and failure evidence; do not erase an old card."""
        self.runtime.require(Mode.LEARN)
        cur = self.db.conn.execute(
            "UPDATE xuehai_method_cards SET revoked_at=CURRENT_TIMESTAMP "
            "WHERE entry_id=? AND revoked_at IS NULL", (entry_id,),
        )
        self.db.conn.commit()
        return bool(cur.rowcount)

    # External signed rights/craft admission lives in the original SQLite.
    # No new memory owner or network/service is created here.
    def method_attestation_challenge(self, **kwargs):
        from .xuehai_method_admission import XuehaiMethodAdmission
        return XuehaiMethodAdmission(self).challenge(**kwargs)

    def admit_externally_attested_method(self, **kwargs):
        from .xuehai_method_admission import XuehaiMethodAdmission
        return XuehaiMethodAdmission(self).admit(**kwargs)

    def _valid_external_attestation(self, row:dict):
        from .xuehai_method_admission import XuehaiMethodAdmission
        return XuehaiMethodAdmission(self).verified_for_write(row)

    def query_methods(self, *, goal: str, genre: str,
                      limit: int = 2, max_chars: int = 300) -> dict:
        """WRITE-only. Exact scene triggers + strict genre fallback, never text retrieval.

        Cards are optional, <=2, and all conditions/provenance/review are
        rechecked on READ. No reviewed card means NONE, not a generic tip.
        """
        self.runtime.require(Mode.WRITE)
        sid = self.runtime.pinned_snapshot_id
        status = self.db.conn.execute(
            "SELECT status FROM snapshots WHERE id=?", (sid,)
        ).fetchone()
        if not status or status["status"] != "published":
            raise ValueError("Pinned snapshot is not published")
        if (type(goal) is not str or not 1 <= len(goal) <= 2000 or
            type(genre) is not str or not 1 <= len(genre) <= 64 or
            type(limit) is not int or not 1 <= limit <= 2 or
            type(max_chars) is not int or not 80 <= max_chars <= 300):
            raise ValueError("METHOD_QUERY_UNBOUNDED")
        genre_path = genre_lineage(genre)
        # Filter scenes in SQL BEFORE the 128-row safety cap: a growing
        # library of unrelated or pending cards must not starve a relevant,
        # reviewed method. Unknown custom scene labels still match exactly
        # when the author explicitly names them in the goal.
        scene_types = [
            name for name, aliases in _METHOD_ALIASES.items()
            if any(len(t) >= 2 and t in goal for t in (name,)+aliases)
        ]
        scene_filter = (
            "m.scene_type IN ("+",".join("?" for _ in scene_types)+") OR "
            if scene_types else ""
        ) + "instr(?,m.scene_type)>0"
        rows = self.db.conn.execute(
            """WITH RECURSIVE lineage(id,parent_id,layout) AS (
                 SELECT id,parent_id,layout FROM snapshots
                  WHERE id=? AND status='published'
                 UNION ALL
                 SELECT p.id,p.parent_id,p.layout FROM snapshots p
                   JOIN lineage l ON l.parent_id=p.id
                  WHERE l.layout='delta' AND p.status='published'
               )
               SELECT m.*, e.text AS source_text, e.genre AS source_genre,
                      e.source_hash AS live_entry_hash,
                      e.source_role AS source_role,
                      e.reuse_policy AS reuse_policy,
                      e.snapshot_id AS live_snapshot,
                      e.chapter AS live_chapter, e.paragraph AS live_paragraph,
                      e.sentence AS live_sentence,
                      w.source_uri AS work_uri, w.source_sha256 AS work_sha,
                      s.excerpt AS span_excerpt, s.source_sha256 AS unit_sha,
                      c.chapter_sha256 AS chapter_sha, c.snapshot_id AS study_sid
               FROM xuehai_method_cards m
               JOIN xuehai_entries e ON e.id=m.entry_id
               JOIN lineage l ON l.id=m.snapshot_id
               LEFT JOIN studied_works w ON w.work_id=m.work_id
               LEFT JOIN source_spans s ON s.work_id=m.work_id
                 AND (e.chapter=s.chapter AND e.paragraph=s.paragraph
                      AND e.sentence=s.sentence)
               LEFT JOIN studied_chapters c ON c.work_id=m.work_id
                 AND c.chapter=e.chapter AND c.snapshot_id IN (SELECT id FROM lineage)
               WHERE (""" + scene_filter + """)
               ORDER BY CASE
                   WHEN m.rights_status='RIGHTS_VERIFIED'
                    AND m.review_status='PILOT_APPROVED'
                    AND m.revoked_at IS NULL THEN 0 ELSE 1 END,
                 m.entry_id ASC LIMIT 128""",
            (sid,*scene_types,goal),
        ).fetchall()
        intro = "可选的场景认知方法（仅供参考，作者可自行选择不采用；不要复述来源、不得套写）："
        selected, rejected, choices, per_work = [], [], [], set()
        candidates = []
        for item in rows:
            r = dict(item)
            scene = r["scene_type"]
            aliases = (scene,) + _METHOD_ALIASES.get(scene, ())
            trigger = next((a for a in aliases if len(a) >= 2 and a in goal), None)
            if not trigger:
                continue
            try:
                scopes = json.loads(r["target_genres_json"])
                facets = json.loads(r["scene_facets_json"])
            except (TypeError, ValueError):
                rejected.append({"entry_id":r["entry_id"],"reason":"INVALID_FACETS"})
                continue
            match = next((g for g in genre_path if g in scopes), None)
            if match is None or (r["style_scope"] == "CLASSICAL_ONLY" and
                                 genre not in ("志怪", "古代白话")):
                rejected.append({"entry_id":r["entry_id"],"reason":"GENRE_OR_ERA_MISMATCH"})
                continue
            why = "EXACT_GENRE" if match == genre else "GENRE_PARENT_FALLBACK"
            if r["source_kind"] in ("PUBLIC_DOMAIN_CLASSIC",
                                     "AUTHORIZED_MODERN"):
                # Citable historical technique must have an explicit, positive
                # condition in the current scene. A scene-name keyword alone
                # (or a negated social commitment) cannot justify retrieval.
                signal_count=sum(
                    1 for facet in facets
                    if _positive_scene_facet(goal,facet))
                if signal_count==0:
                    rejected.append({"entry_id":r["entry_id"],
                                     "card_sha256":r["card_sha256"],
                                     "reason":"SCENE_PRECONDITION_NOT_EVIDENCED"})
                    continue
            else:
                signal_count=sum(1 for facet in facets if facet in goal)
            candidates.append((int(match == genre)*4+signal_count, r, why, trigger))
        candidates.sort(key=lambda x: (-x[0],x[1]["entry_id"]))
        for _,r,why,trigger in candidates:
            eid = r["entry_id"]
            reason = None
            # For third-party classic/modern sources, mutable status labels
            # and a bare SHA are not authority. Two detached signatures from
            # distinct externally enrolled roles must validate on EVERY read.
            third_party = r["source_kind"] in (
                "PUBLIC_DOMAIN_CLASSIC","AUTHORIZED_MODERN")
            approval_sha, approval_reason = (
                self._valid_external_attestation(r)
                if third_party else (None,"NOT_APPLICABLE"))
            if r["revoked_at"]:
                reason = "REVOKED"
            elif not (_is_digest(r["card_sha256"]) and
                      _method_sha(r) == r["card_sha256"]):
                reason = "CARD_SHA_MISMATCH"
            elif third_party and approval_sha is None:
                reason = approval_reason
            elif (not third_party and
                  (r["rights_status"] != "RIGHTS_VERIFIED" or
                   r["review_status"] != "PILOT_APPROVED" or
                   r["value_status"] != "UNPROVEN_PILOT" or
                   r["source_kind"] != "AUTHOR_CREATED_ORIGINAL")):
                reason = "RIGHTS_REVIEW_OR_VALUE_BLOCK"
            elif (r["source_role"] == "diagnostic_only" or
                  r["reuse_policy"] != "technique_only" or
                  (approval_sha is None and
                   not _is_digest(r["review_receipt_sha256"]))):
                reason = "SOURCE_ROLE_OR_REVIEW_BLOCK"
            elif (r["source_uri"].startswith(("r2://","s3://")) or
                  r["work_uri"] != r["source_uri"] or
                  r["work_sha"] != r["source_sha256"] or
                  r["live_entry_hash"] != r["entry_source_hash"] or
                  r["live_snapshot"] != r["snapshot_id"] or
                  r["source_locator"] != f"{r['live_chapter']}:{r['live_paragraph']}:{r['live_sentence']}" or
                  r["live_entry_hash"] != hashlib.sha256((r["work_id"]+"|"+ " ".join(r["source_text"].split()).strip()).encode("utf8")).hexdigest() or
                  not _is_digest(r["source_sha256"]) or
                  not _is_digest(r["source_unit_sha256"]) or
                  not _is_digest(r["unit_sha"]) or
                  r["source_unit_sha256"] != r["unit_sha"] or
                  not _is_digest(r["chapter_sha"]) or
                  not r["study_sid"] or
                  r["span_excerpt"] != r["source_text"]):
                reason = "SOURCE_PROVENANCE_FAILED"
            elif r["work_id"] in per_work:
                reason = "DIVERSITY_SAME_WORK"
            elif any(_source_overlap(r["span_excerpt"],r[k]) for k in (
                "signal", "mechanism", "writer_option", "applies_when",
                "not_when", "pov_limit", "counterexample")):
                reason = "SOURCE_QUOTATION_BLOCKED"
            if reason:
                rejected.append({"entry_id":eid,"card_sha256":r["card_sha256"],"reason":reason})
                continue
            item_text = (
                f"\n- 适用：{r['applies_when']}；线索：{r['signal']}；"
                f"机制：{r['mechanism']}；可选：{r['writer_option']}；"
                f"视角：{r['pov_limit']}；不适用：{r['not_when']}；"
                f"反例：{r['counterexample']}"
            )
            if len(intro) + len("".join(choices)) + len(item_text) > max_chars:
                rejected.append({"entry_id":eid,"card_sha256":r["card_sha256"],
                                 "reason":"PROMPT_CHARACTER_BUDGET"})
                continue
            selected.append({
                "entry_id":eid,"snapshot_id":r["snapshot_id"],
                "work_id":r["work_id"],"source_sha256":r["source_sha256"],
                "source_unit_sha256":r["source_unit_sha256"],
                "card_sha256":r["card_sha256"],
                "source_kind":r["source_kind"],"scene_type":r["scene_type"],
                "rights_status":("RIGHTS_VERIFIED" if approval_sha
                                 else r["rights_status"]),
                "review_status":("PILOT_APPROVED" if approval_sha
                                 else r["review_status"]),
                "value_status":("UNPROVEN_PILOT" if approval_sha
                                else r["value_status"]),
                "externally_signed_attestation":bool(approval_sha),
                "external_attestation_sha256":approval_sha,
                "reason":f"{why}:{trigger}",
            })
            choices.append(item_text)
            per_work.add(r["work_id"])
            if len(selected) >= limit:
                break
        prompt = intro + "".join(choices) if selected else ""
        return {
            "selected":selected, "prompt_guidance":prompt,
            "receipt":{
                "format":"wf.0bl.xuehai-methods-write.v1",
                "snapshot_id":sid,"genre_path":list(genre_path),
                "selected":selected,"rejected":rejected[:32],
                "result":"METHODS_SELECTED" if selected else "NONE",
                "chars_added":len(prompt),"max_chars":max_chars,
                "scope":"PUBLISHED_LINEAGE_ONLY",
                "source_excerpt_shown_to_model":False,
                "literary_benefit_proven":False,
                "author_may_ignore":True,
            },
        }
