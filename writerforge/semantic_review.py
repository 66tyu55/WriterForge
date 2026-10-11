"""Read-only, bounded source-context packets for actual human semantic review.

This does not label or verify facts. The reviewer must inspect the original
context before using FictionEncyclopedia.review separately. No global literary
quality score, model parameter training, or competing datastore.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

MAX_REVIEW_BATCH = 25
MAX_CONTEXT_CHARS = 320


@dataclass(frozen=True)
class ReviewPacket:
    evidence_id: int
    work_id: str
    location: tuple[int, int, int]
    subject: str
    kind: str
    proposed_category: str
    proposed_attribute: str
    assertion: str
    quotation: str
    exact_quote_present: bool
    source_sha_matches: bool
    source_excerpt: str
    previous_excerpt: str
    next_excerpt: str
    review_questions: tuple[str, ...]
    status: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "work_id": self.work_id,
            "location": list(self.location),
            "subject": self.subject,
            "kind": self.kind,
            "proposed_category": self.proposed_category,
            "proposed_attribute": self.proposed_attribute,
            "assertion": self.assertion,
            "quotation": self.quotation,
            "exact_quote_present": self.exact_quote_present,
            "source_sha_matches": self.source_sha_matches,
            "source_excerpt": self.source_excerpt,
            "previous_excerpt": self.previous_excerpt,
            "next_excerpt": self.next_excerpt,
            "review_questions": list(self.review_questions),
            "status": self.status,
            "human_verified_by_packet": False,
            "independent_literary_evaluation_performed": False,
        }


def review_packets(db, *, work_id: str, limit: int = 10, offset: int = 0) -> list[ReviewPacket]:
    """Inspect proposed source observations without mutating approval state.

    Adjacent units are explicitly restricted to the same chapter/paragraph;
    no accidental cross-novel, cross-chapter context or unbounded source fetch.
    """
    if not isinstance(work_id, str) or not 1 <= len(work_id) <= 128:
        raise ValueError("specific work_id required")
    if not isinstance(limit, int) or not 1 <= limit <= MAX_REVIEW_BATCH:
        raise ValueError("review limit must be 1..25")
    if not isinstance(offset, int) or not 0 <= offset <= 100000:
        raise ValueError("invalid review offset")
    rows = db.conn.execute(
        """SELECT e.id,e.work_id,e.chapter,e.paragraph,e.sentence,
                  e.category_path,e.attribute,e.assertion,e.quotation,
                  e.source_unit_sha256,e.status,v.name,v.kind,
                  s.excerpt,s.source_sha256
           FROM encyclopedia_evidence e
           JOIN encyclopedia_entities v ON v.id=e.entity_id
           LEFT JOIN source_spans s ON s.work_id=e.work_id
             AND s.chapter=e.chapter AND s.paragraph=e.paragraph
             AND s.sentence=e.sentence
           WHERE e.work_id=? AND e.status='proposed'
           ORDER BY e.chapter,e.paragraph,e.sentence,e.id
           LIMIT ? OFFSET ?""",
        (work_id, limit, offset),
    ).fetchall()
    result=[]
    for row in rows:
        context=db.conn.execute(
            """SELECT sentence,excerpt FROM source_spans
               WHERE work_id=? AND chapter=? AND paragraph=?
                 AND sentence BETWEEN ? AND ?
               ORDER BY sentence""",
            (work_id,row["chapter"],row["paragraph"],
             row["sentence"]-1,row["sentence"]+1),
        ).fetchall()
        by_sentence={x["sentence"]:x["excerpt"] for x in context}
        excerpt=row["excerpt"] or ""
        result.append(ReviewPacket(
            evidence_id=row["id"],work_id=row["work_id"],
            location=(row["chapter"],row["paragraph"],row["sentence"]),
            subject=row["name"],kind=row["kind"],
            proposed_category=row["category_path"],
            proposed_attribute=row["attribute"],
            assertion=row["assertion"],quotation=row["quotation"],
            exact_quote_present=bool(excerpt and row["quotation"] in excerpt),
            source_sha_matches=bool(excerpt and row["source_unit_sha256"] == row["source_sha256"]),
            source_excerpt=excerpt[:MAX_CONTEXT_CHARS],
            previous_excerpt=by_sentence.get(row["sentence"]-1,"")[:MAX_CONTEXT_CHARS],
            next_excerpt=by_sentence.get(row["sentence"]+1,"")[:MAX_CONTEXT_CHARS],
            review_questions=(
                "引文是否确实描述该主体，而非人名、比喻、传闻或另一实体？",
                "属性和类别是否由上下文支持，而非仅靠关键词命中？",
                "这是叙述事实、人物认知、传闻还是推测？",
                "是否存在否定、反例、指代不清或其他更合理解释？",
            ),
            status="review_required" if excerpt and row["quotation"] in excerpt
                   and row["source_unit_sha256"] == row["source_sha256"]
                   else "source_integrity_failed",
        ))
    return result
