"""V25: source-grounded, multi-facet, lossless *evidence* encyclopedia.

Identity is (work, kind, name), never a global fuzzy merge. Evidence is
many-to-one: the same 妖兽/人物/地点/设定 can have arbitrarily many distinct,
independently locatable original mentions, including conflicting portrayals.
Source spans are the single text store; encyclopedia stores short verbatim
fragments and source hashes, NOT complete copyrighted books.

Most crucially, lexical/model candidates are NEVER automatically certified
as semantic truth. A reviewer must approve a specific occurrence with a
reason, and generative writing can retrieve verified observations only.
No global 50-book style optimization happens in this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import re

from .db import WriterForgeDB
from .runtime import Mode, RuntimeEngine


ROOTS = frozenset({
    "外貌", "性格", "地点", "设定", "人物", "生物", "能力",
    "武学", "物品", "事件", "势力", "关系", "行为", "语言",
    "声音", "情绪", "感官", "叙事", "习性",
})
KINDS = frozenset({
    "character", "creature", "place", "artifact", "skill",
    "realm", "system", "event", "organization", "concept",
})
# An impossible major category/entity pairing is a validation error, not an
# automatically classified paragraph. This addresses cases such as putting
# a fantasy beast into the '地点/独特地点' shelf.
ALLOWED_KINDS_BY_ROOT = {
    "外貌": {"character", "creature", "place", "artifact", "organization"},
    "性格": {"character", "creature"},
    "地点": {"place"},
    "人物": {"character"},
    "生物": {"creature"},
    "武学": {"skill"},
    "物品": {"artifact"},
    "事件": {"event"},
    "势力": {"organization"},
    "习性": {"creature", "character"},
    "语言": {"character", "creature"},
    "情绪": {"character", "creature"},
    "关系": {"character", "creature", "organization"},
    "能力": {"character", "creature", "skill", "artifact", "realm"},
    "声音": {"character", "creature", "place", "artifact", "event", "skill"},
}
CANDIDATE_ORIGINS = frozenset({"manual", "model_candidate", "rule_candidate"})
CLAIM_TYPES = frozenset({"observed", "rumored", "character_belief", "inferred"})
MAX_QUOTE_CHARS = 160
MAX_EXPLANATION_CHARS = 240
MAX_PAGE_SIZE = 100


class EncyclopediaError(ValueError):
    pass


def _bounded_name(value: str, label: str, *, maximum: int = 100) -> str:
    if (not isinstance(value, str) or value != value.strip()
        or not 1 <= len(value) <= maximum or any(ord(ch) < 32 for ch in value)
        or "/" in value or "\\" in value):
        raise EncyclopediaError(f"invalid {label}: requires 1..{maximum} clean characters")
    return value


def validate_category_path(value: str) -> str:
    if not isinstance(value, str) or len(value) > 160:
        raise EncyclopediaError("category path is too large")
    parts = value.split("/")
    if not 1 <= len(parts) <= 6:
        raise EncyclopediaError("category path depth must be 1..6")
    for part in parts:
        _bounded_name(part,"category segment",maximum=40)
        if "%" in part or "_" in part:  # can act as SQL LIKE wildcards
            raise EncyclopediaError("category path contains SQL wildcard characters")
    if parts[0] not in ROOTS:
        raise EncyclopediaError(f"unknown top-level category {parts[0]!r}")
    return "/".join(parts)


@dataclass(frozen=True)
class FacetQuery:
    category_path: str | None = None
    entity_name: str | None = None
    kind: str | None = None
    work_id: str | None = None
    genre: str | None = None
    status: Literal["verified", "proposed", "rejected", "all"] = "verified"
    limit: int = 25
    offset: int = 0


class FictionEncyclopedia:
    def __init__(self, db: WriterForgeDB, runtime: RuntimeEngine | None = None):
        self.db, self.runtime = db, runtime

    def _require_learn(self):
        if self.runtime is not None:
            self.runtime.require(Mode.LEARN)

    def entity(self, *, work_id: str, name: str, kind: str,
               genre: str) -> int:
        """Idempotent entity identity, scoped to one actual studied work."""
        self._require_learn()
        work_id=_bounded_name(work_id,"work_id",maximum=128)
        name=_bounded_name(name,"entity name",maximum=100)
        genre=_bounded_name(genre,"genre",maximum=48)
        if kind not in KINDS:
            raise EncyclopediaError("unknown subject type")
        if not self.db.conn.execute(
            "SELECT 1 FROM studied_works WHERE work_id=?", (work_id,)
        ).fetchone():
            raise EncyclopediaError("no studied source for work_id")
        self.db.conn.execute(
            """INSERT OR IGNORE INTO encyclopedia_entities(work_id,name,kind,genre)
               VALUES(?,?,?,?)""", (work_id,name,kind,genre),
        )
        row=self.db.conn.execute(
            "SELECT id,genre FROM encyclopedia_entities WHERE work_id=? AND kind=? AND name=?",
            (work_id,kind,name),
        ).fetchone()
        if row["genre"]!=genre:
            raise EncyclopediaError("entity genre conflicts with registered book taxonomy")
        self.db.conn.commit()
        return int(row["id"])

    def alias(self, entity_id: int, alias: str) -> None:
        self._require_learn()
        alias=_bounded_name(alias,"alias",maximum=100)
        if not self.db.conn.execute(
            "SELECT 1 FROM encyclopedia_entities WHERE id=?", (entity_id,)
        ).fetchone():
            raise EncyclopediaError("unknown entity for alias")
        self.db.conn.execute(
            "INSERT OR IGNORE INTO encyclopedia_aliases(entity_id,alias) VALUES(?,?)",
            (entity_id,alias),
        )
        self.db.conn.commit()

    def observe(
        self, *, entity_id: int, chapter: int, paragraph: int, sentence: int,
        category_path: str, attribute: str, quotation: str,
        explanation: str = "", origin: str = "manual",
        assertion: str = "observed",
    ) -> int:
        """Store an UNVERIFIED observation, tied to an actual immutable source unit.

        A mere token match never automatically becomes an approved creature,
        character trait, place description or invented setting. If a model
        finds the right entity but wrong attribute, a reviewer rejects it.
        """
        self._require_learn()
        path=validate_category_path(category_path)
        attribute=_bounded_name(attribute,"attribute",maximum=60)
        if origin not in CANDIDATE_ORIGINS or assertion not in CLAIM_TYPES:
            raise EncyclopediaError("invalid origin or assertion type")
        if (not isinstance(quotation,str) or not 1 <= len(quotation) <= MAX_QUOTE_CHARS
            or quotation != quotation.strip()):
            raise EncyclopediaError("quotation must be 1..160 exact original characters")
        if not isinstance(explanation,str) or len(explanation)>MAX_EXPLANATION_CHARS:
            raise EncyclopediaError("explanation exceeds 240 characters")
        if not all(isinstance(x,int) and x>=0 for x in (chapter,paragraph,sentence)):
            raise EncyclopediaError("invalid source location")
        entity=self.db.conn.execute(
            "SELECT * FROM encyclopedia_entities WHERE id=?", (entity_id,)
        ).fetchone()
        if not entity:
            raise EncyclopediaError("unknown entity")
        permitted=ALLOWED_KINDS_BY_ROOT.get(path.split("/",1)[0])
        if permitted is not None and entity["kind"] not in permitted:
            raise EncyclopediaError(
                "category/entity mismatch: this kind cannot be stored under that top-level shelf"
            )
        source=self.db.conn.execute(
            """SELECT excerpt,source_sha256 FROM source_spans
               WHERE work_id=? AND chapter=? AND paragraph=? AND sentence=?""",
            (entity["work_id"],chapter,paragraph,sentence),
        ).fetchone()
        if source is None or quotation not in source["excerpt"]:
            raise EncyclopediaError(
                "quotation not found at the specified original source position"
            )
        self.db.conn.execute(
            """INSERT OR IGNORE INTO encyclopedia_evidence(
               entity_id,work_id,chapter,paragraph,sentence,category_path,
               attribute,quotation,source_unit_sha256,explanation,assertion,origin,status
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'proposed')""",
            (entity_id,entity["work_id"],chapter,paragraph,sentence,path,
             attribute,quotation,source["source_sha256"],explanation,
             assertion,origin),
        )
        row=self.db.conn.execute(
            """SELECT id FROM encyclopedia_evidence
               WHERE entity_id=? AND chapter=? AND paragraph=? AND sentence=?
                 AND category_path=? AND attribute=? AND quotation=?""",
            (entity_id,chapter,paragraph,sentence,path,attribute,quotation),
        ).fetchone()
        self.db.conn.commit()
        return int(row["id"])

    def review(self, evidence_id: int, *, approved: bool,
               reason: str, reviewer_confirmed: bool) -> str:
        """Explicit author/editor gate: never automatically certify a model."""
        self._require_learn()
        if not reviewer_confirmed:
            raise EncyclopediaError("explicit human review confirmation is required")
        reason=_bounded_name(reason,"review reason",maximum=320)
        item=self.db.conn.execute(
            """SELECT e.*,s.excerpt AS current_excerpt,
                      s.source_sha256 AS current_sha
               FROM encyclopedia_evidence e
               JOIN source_spans s ON s.work_id=e.work_id AND s.chapter=e.chapter
                AND s.paragraph=e.paragraph AND s.sentence=e.sentence
               WHERE e.id=?""", (evidence_id,),
        ).fetchone()
        if item is None:
            raise EncyclopediaError("unknown or orphaned source evidence")
        if (item["quotation"] not in item["current_excerpt"]
            or item["source_unit_sha256"] != item["current_sha"]):
            raise EncyclopediaError("source was revised; cannot approve stale quotation")
        status="verified" if approved else "rejected"
        self.db.conn.execute(
            """UPDATE encyclopedia_evidence
               SET status=?,reviewer_reason=?,reviewed_at=CURRENT_TIMESTAMP
               WHERE id=?""",(status,reason,evidence_id),
        )
        self.db.conn.commit()
        return status

    def relation(self, *, source_entity_id: int, target_entity_id: int,
                 relation: str, evidence_id: int) -> int:
        """One source-anchored relation, not a fabricated setting graph edge."""
        self._require_learn()
        relation=_bounded_name(relation,"relation",maximum=60)
        source=self.db.conn.execute(
            "SELECT work_id FROM encyclopedia_entities WHERE id=?", (source_entity_id,),
        ).fetchone()
        target=self.db.conn.execute(
            "SELECT work_id FROM encyclopedia_entities WHERE id=?", (target_entity_id,),
        ).fetchone()
        proof=self.db.conn.execute(
            "SELECT entity_id,status FROM encyclopedia_evidence WHERE id=?", (evidence_id,),
        ).fetchone()
        if (source is None or target is None or source["work_id"]!=target["work_id"]
            or proof is None or proof["status"]!="verified"
            or proof["entity_id"] not in (source_entity_id,target_entity_id)):
            raise EncyclopediaError("cross-work or unverified entity relation is prohibited")
        self.db.conn.execute(
            """INSERT OR IGNORE INTO encyclopedia_relations(
               source_entity_id,target_entity_id,relation,evidence_id
               ) VALUES(?,?,?,?)""",
            (source_entity_id,target_entity_id,relation,evidence_id),
        )
        row=self.db.conn.execute(
            """SELECT id FROM encyclopedia_relations
               WHERE source_entity_id=? AND target_entity_id=? AND relation=? AND evidence_id=?""",
            (source_entity_id,target_entity_id,relation,evidence_id),
        ).fetchone()
        self.db.conn.commit()
        return int(row["id"])

    def query(self, q: FacetQuery) -> dict:
        """Browse ALL matches by pagination; no hidden per-beast diversity cap.

        Default only returns human-verified and source-matching observations.
        More than a hundred examples means several pages, NOT overwritten data.
        """
        if not 1 <= q.limit <= MAX_PAGE_SIZE or not 0 <= q.offset <= 1_000_000:
            raise EncyclopediaError("browse window must be limit 1..100, offset 0..1m")
        if q.kind and q.kind not in KINDS:
            raise EncyclopediaError("invalid entity kind")
        if q.status not in {"verified","proposed","rejected","all"}:
            raise EncyclopediaError("invalid evidence status")
        wheres = [
            "s.source_sha256=e.source_unit_sha256",
            "instr(s.excerpt,e.quotation)>0",
        ]
        args: list = []
        if q.category_path:
            path=validate_category_path(q.category_path)
            wheres.append("(e.category_path=? OR e.category_path LIKE ? ESCAPE '\\')")
            args.extend((path,path+"/%"))
        if q.entity_name:
            name=_bounded_name(q.entity_name,"entity name")
            wheres.append(
                """(v.name=? OR EXISTS(
                    SELECT 1 FROM encyclopedia_aliases a
                    WHERE a.entity_id=v.id AND a.alias=?
                ))"""
            )
            args.extend((name,name))
        for field,value in (("v.kind",q.kind),("v.work_id",q.work_id),("v.genre",q.genre)):
            if value:
                wheres.append(field+"=?")
                args.append(value)
        if q.status!="all":
            wheres.append("e.status=?")
            args.append(q.status)
        joins = """FROM encyclopedia_evidence e
            JOIN encyclopedia_entities v ON v.id=e.entity_id
            JOIN source_spans s ON s.work_id=e.work_id AND s.chapter=e.chapter
             AND s.paragraph=e.paragraph AND s.sentence=e.sentence
            JOIN studied_works w ON w.work_id=e.work_id"""
        where=" AND ".join(wheres)
        count=self.db.conn.execute(
            f"SELECT COUNT(*) AS n {joins} WHERE {where}",args,
        ).fetchone()["n"]
        rows=self.db.conn.execute(
            f"""SELECT e.id,e.entity_id,e.work_id,v.name,v.kind,v.genre,
                       w.title,w.source_uri,e.chapter,e.paragraph,e.sentence,
                       e.category_path,e.attribute,e.quotation,e.explanation,
                       e.assertion,e.origin,e.status,e.reviewer_reason,
                       e.source_unit_sha256
                {joins} WHERE {where}
                ORDER BY e.work_id,e.chapter,e.paragraph,e.sentence,e.id
                LIMIT ? OFFSET ?""", [*args,q.limit,q.offset],
        ).fetchall()
        return {
            "total_matches":int(count),
            "offset":q.offset,"returned":len(rows),
            "has_more":q.offset+len(rows)<count,
            "next_offset":q.offset+len(rows) if q.offset+len(rows)<count else None,
            "items":[dict(r) for r in rows],
            "evaluation_performed":False,
            "provenance":"source-span-bound original excerpt",
        }

    def entity_overview(self, *, kind: str | None = None,
                        work_id: str | None = None,
                        limit: int = 50, offset: int = 0) -> dict:
        """Sorted subject catalogue; every mention is preserved in evidence."""
        if not 1 <= limit <= MAX_PAGE_SIZE or not 0 <= offset <= 1_000_000:
            raise EncyclopediaError("invalid entity pagination")
        if kind and kind not in KINDS:
            raise EncyclopediaError("invalid entity kind")
        filters=[];args=[]
        if kind:
            filters.append("v.kind=?");args.append(kind)
        if work_id:
            filters.append("v.work_id=?");args.append(work_id)
        where="WHERE "+" AND ".join(filters) if filters else ""
        count=self.db.conn.execute(
            f"SELECT COUNT(*) FROM encyclopedia_entities v {where}", args,
        ).fetchone()[0]
        rows=self.db.conn.execute(
            f"""SELECT v.id,v.work_id,v.name,v.kind,v.genre,
                       COUNT(e.id) AS occurrences,
                       COALESCE(SUM(CASE WHEN e.status='verified' THEN 1 ELSE 0 END),0)
                       AS verified_occurrences
                FROM encyclopedia_entities v
                LEFT JOIN encyclopedia_evidence e ON e.entity_id=v.id
                {where} GROUP BY v.id
                ORDER BY v.work_id,v.kind,v.name LIMIT ? OFFSET ?""",
            [*args,limit,offset],
        ).fetchall()
        return {
            "total_entities":count,"offset":offset,
            "has_more":offset+len(rows)<count,
            "entities":[dict(row) for row in rows],
        }
