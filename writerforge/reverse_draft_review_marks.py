"""Review-mark provenance for a PRIVATE, decrypted original A/B draft pair.

This module only accepts human/model-authored *observations* tied to exact
character offsets. It never itself reads the original novel or auto-scores.
All quoted spans are converted to SHA256; exported candidate summaries
contain NO actual fiction lines, only bounded reason labels and hashes.
Original draft text stays in the already opt-in private encrypted vault.

The reviewer type is a self-declared provenance label, not proof a reviewer is
human or independent. No evidence is ever auto-promoted to a craft technique.
"""
from __future__ import annotations
from hashlib import sha256
import json,re

SHA=re.compile(r"[a-f0-9]{64}\Z")
DIMS={"perception","causality","information","continuity","language"}
CATEGORIES={"CHARACTER_KNOWLEDGE","CAUSE_EFFECT_GAP","DISCONNECTED_CLUE",
            "SCENE_CONTINUITY","EXCESSIVE_EXPLANATION","LANGUAGE_RHYTHM",
            "NATURAL_SOUND_OR_SENSE","UNSUPPORTED_TWIST"}
FIELDS={"arm","dimension","category","start","end","observation","revision_hint"}
MAX_MARKS=32

class DraftReviewError(ValueError):
    pass

def review_marks(drafts:dict,marks:list,*,reviewer_kind:str="unverified_reader",
                 draft_receipt_sha256:str)->dict:
    if (not isinstance(drafts,dict) or set(drafts)!={"baseline","skill"}
        or any(not isinstance(d,str) or not 220<=len(d)<=4500 for d in drafts.values())
        or not isinstance(marks,list) or not 1<=len(marks)<=MAX_MARKS
        or not isinstance(draft_receipt_sha256,str) or
        SHA.fullmatch(draft_receipt_sha256) is None
        or reviewer_kind not in ("human_claim_unverified","model_critic_unverified",
                                 "unverified_reader")):
        raise DraftReviewError("INVALID_DRAFT_REVIEW_INPUT")
    output=[]
    for item in marks:
        if not isinstance(item,dict) or set(item)!=FIELDS:
            raise DraftReviewError("INVALID_REVIEW_MARK_SCHEMA")
        arm=item["arm"]
        if arm not in drafts or item["dimension"] not in DIMS or item["category"] not in CATEGORIES:
            raise DraftReviewError("REVIEW_DIMENSION_OR_CATEGORY_INVALID")
        start,end=item["start"],item["end"]
        if (type(start) is not int or type(end) is not int or
            not 0<=start<end<=len(drafts[arm]) or
            not 3<=end-start<=100):
            raise DraftReviewError("REVIEW_SPAN_NOT_IN_MANUSCRIPT")
        for field in ("observation","revision_hint"):
            content=item[field]
            if not isinstance(content,str) or not 10<=len(content.strip())<=220:
                raise DraftReviewError("REVIEW_REASON_NOT_GROUNDED_OR_OVERSIZE")
        excerpt=drafts[arm][start:end]
        if not excerpt.strip():
            raise DraftReviewError("EMPTY_REVIEW_EXCERPT")
        output.append({
            "arm":arm,"dimension":item["dimension"],
            "category":item["category"],"start":start,"end":end,
            "exact_span_sha256":sha256(excerpt.encode("utf-8")).hexdigest(),
            "manuscript_sha256":sha256(drafts[arm].encode("utf-8")).hexdigest(),
            "reason_sha256":sha256(item["observation"].encode("utf-8")).hexdigest(),
            "repair_hint_sha256":sha256(item["revision_hint"].encode("utf-8")).hexdigest(),
            "reviewer_kind_claim":reviewer_kind,
            "excerpt_and_reasons_exported":False,
            "independently_literary_verified":False,
        })
    summary={
        "format":"writerforge.private-draft-review-marks.v1",
        "encrypted_draft_receipt_sha256":draft_receipt_sha256,
        "annotated_count":len(output),
        "marks":output,
        "human_identity_verified":False,
        "independence_verified":False,
        "literary_mastery_verified":False,
        "eligible_for_core_promotion":False,
    }
    if len(json.dumps(summary,ensure_ascii=False))>14500:
        raise DraftReviewError("REVIEW_MARKS_TOO_LARGE")
    return summary
