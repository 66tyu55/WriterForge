"""V89: trusted host locates model-proposed quotations; model never guesses offsets.

Only independently frozen V87 visible units may be inspected. A quoted phrase
must occur EXACTLY ONCE across the complete two-unit visible window, in the
claimed unit. Exact Unicode match only: no fuzzy search, spelling correction,
normalization, text generation, near-match or hidden-future lookup.

Coordinate correction is an ENGINEERING operation, not evidence that the
model's causality/character-knowledge interpretation is true. No WRITE
permission, literary promotion, original-prose persistence or R2 mutation.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import re

from .v88_frozen_blind_exam import (
    ANSWER_KEYS, MIN_TEXT, MAX_QUOTE, MAX_RESPONSE_BYTES, _text,
    validate_wf_answer, WF88BlindError, canonical,
)

SHA = re.compile(r"[0-9a-f]{64}\Z")
QUOTE_ONLY_FIELDS = frozenset(("unit","quote"))
CLAIM_ANCHORS = ("observation","consequence")
SOURCE_UNIT_COUNT = 2


class WF89AnchorError(ValueError):
    pass


def require(ok,code):
    if not ok:
        raise WF89AnchorError(code)


def digest(value):
    return sha256(value).hexdigest()


def valid_sha(value):
    return isinstance(value,str) and SHA.fullmatch(value) is not None


def _find_quote(anchor, visible_units):
    require(type(anchor) is dict and set(anchor)==QUOTE_ONLY_FIELDS,
            "WF89_MODEL_MUST_SUPPLY_ONLY_UNIT_AND_EXACT_QUOTE")
    unit=anchor["unit"]
    quote=anchor["quote"]
    require(type(unit) is int and 1<=unit<=SOURCE_UNIT_COUNT,
            "WF89_CLAIMED_UNIT_NOT_VISIBLE")
    require(isinstance(quote,str) and MIN_TEXT<=len(quote)<=MAX_QUOTE and
            "\x00" not in quote and
            not any(ord(c)<32 for c in quote),
            "WF89_QUOTE_LENGTH_OR_CONTROL_INVALID")
    counts=[source.count(quote) for source in visible_units]
    require(sum(counts)>0,"WF89_QUOTE_NOT_IN_VISIBLE_SOURCE")
    require(counts[unit-1]>0,"WF89_QUOTE_IN_WRONG_UNIT")
    require(sum(counts)==1,"WF89_QUOTE_NOT_GLOBALLY_UNIQUE")
    start=visible_units[unit-1].find(quote)
    require(start>=0,"WF89_SOURCE_SEARCH_INCONSISTENT")
    return {"unit":unit,"start":start,"end":start+len(quote),
            "quote":quote}


def _check_distinct_order(first,second):
    # Forward local-text reading only. Reversed or overlapping narrative
    # claims require manual temporal adjudication; this does NOT mean a
    # flashback is semantically false.
    a=(first["unit"],first["start"])
    b=(second["unit"],second["start"])
    require(a!=b,"WF89_SAME_SOURCE_EVENT_AS_TWO_ANCHORS")
    if first["unit"]==second["unit"]:
        require(first["end"]<=second["start"] or
                second["end"]<=first["start"],
                "WF89_OVERLAPPING_SOURCE_ANCHORS")
    require(a<b,"WF89_BACKWARD_NARRATIVE_ORDER_NEEDS_REVIEW")


def _visible_attested(units, expected_hashes):
    require(type(units) is tuple and len(units)==SOURCE_UNIT_COUNT and
            all(isinstance(u,str) and 30<=len(u)<=900 for u in units),
            "WF89_TWO_BOUNDED_VISIBLE_SOURCE_UNITS_REQUIRED")
    require(type(expected_hashes) in (tuple,list) and
            len(expected_hashes)==SOURCE_UNIT_COUNT and
            all(valid_sha(x) for x in expected_hashes),
            "WF89_PINNED_VISIBLE_SHA_MISSING")
    computed=[digest(v.encode("utf8")) for v in units]
    require(computed==list(expected_hashes),
            "WF89_VISIBLE_SOURCE_CHANGED_FROM_COLD_PIN")
    return computed


def quote_only_question_contract():
    """Future WF prompts may copy this contract; never patch old V88 prompts."""
    return (
        "请你自己依据只给你的两个原文单位提出假说或弃权。"
        "JSON字段为status,claim_id,question,observation,consequence,"
        "character_knowledge,hypothesis,alternative,falsifier,uncertainty。"
        "observation/consequence只允许JSON对象{unit:1,quote:'原文短句'}，"
        "unit为1或2，quote为原文完全一致的8到72字符片段，"
        "请不要输出start/end，也不要猜测字符偏移。"
        "没有可靠引句或需要未读后文时选择ABSTAIN。"
        "因果推论、替代解释、可反证条件仍必须独立思考。"
        "模型不证明因果、不能自己评分，严格JSON。"
    )


def resolve_quote_only_answer(answer, *, visible_units,
                              pinned_visible_unit_sha256,
                              original_source_sha256,
                              frozen_fragment_sha256,
                              sealed_future_unit_sha256):
    """Return a SOURCE-ONLY no-prose candidate receipt; fail closed.

    The original source and frozen fragment SHA are supplied by an
    independently audited caller, not from the model response.
    Hidden text is not passed to this function at all.
    """
    require(all(valid_sha(x) for x in (
                original_source_sha256,frozen_fragment_sha256,
                sealed_future_unit_sha256)),
            "WF89_TRUSTED_SOURCE_BINDING_INVALID")
    source_hashes=_visible_attested(
        visible_units,pinned_visible_unit_sha256)
    require(type(answer) is dict and set(answer)==ANSWER_KEYS and
            len(canonical(answer))<=MAX_RESPONSE_BYTES,
            "WF89_MODEL_ANSWER_CONTRACT_INVALID")
    answer_sha=digest(canonical(answer))
    status=answer.get("status")
    require(status in ("HYPOTHESIS","ABSTAIN"),
            "WF89_STATUS_INVALID")
    proposal=deepcopy(answer)
    if status=="HYPOTHESIS":
        require(_text(proposal.get("question")) and
                _text(proposal.get("hypothesis")) and
                _text(proposal.get("alternative")) and
                _text(proposal.get("falsifier")) and
                _text(proposal.get("uncertainty")),
                "WF89_LITERARY_HYPOTHESIS_FIELDS_UNBOUNDED")
        resolved=[_find_quote(proposal[k],visible_units)
                  for k in CLAIM_ANCHORS]
        _check_distinct_order(*resolved)
        for k,value in zip(CLAIM_ANCHORS,resolved):
            proposal[k]=value
    else:
        require(proposal.get("observation") is None and
                proposal.get("consequence") is None,
                "WF89_ABSTENTION_CANNOT_CITE_SOURCE")
    try:
        validated=validate_wf_answer(
            proposal,visible_units=visible_units)
    except WF88BlindError as err:
        raise WF89AnchorError(
            "WF89_WF88_NON_LOCATION_CONTRACT_"+str(err)) from None
    # Store and transmit ONLY bounded hash/offset metadata, not a rewritten
    # literal quote or old model answer. The source remains temporary.
    receipt={
        "format":"wf.learn.host-source-anchor.v89",
        "original_source_sha256":original_source_sha256,
        "frozen_fragment_sha256":frozen_fragment_sha256,
        "sealed_future_unit_sha256":sealed_future_unit_sha256,
        "visible_unit_sha256":source_hashes,
        "raw_model_answer_sha256":answer_sha,
        "model_answer_status":status,
        "mechanical_result":"SOURCE_GROUNDED_CANDIDATE_ONLY"
                             if status=="HYPOTHESIS" else
                             "ABSTAIN_NO_INFERENCE",
        "located_anchor_meta":validated.get("source_anchors",[]),
        "model_numeric_offsets_not_used":True,
        "source_query_is_exact_unique_visible_quote_only":True,
        "literary_semantics_independently_verified":False,
        "causality_is_not_proven_by_source_order":True,
        "character_knowledge_semantics_not_verified":True,
        "eligible_to_direct_writing":False,
        "skill_promotion_approved":False,
        "r2_writes":0,"model_calls":0,
        "original_prose_and_model_explanations_retained":False,
    }
    receipt["receipt_sha256"]=digest(canonical(receipt))
    return receipt


def diagnose_existing_v88_answer(answer,*,visible_units,
                                 pinned_visible_unit_sha256,
                                 original_source_sha256,
                                 frozen_fragment_sha256,
                                 sealed_future_unit_sha256):
    """Retrospective diagnostic ONLY. The historical V88 verdict stays FAILED.

    The old answer contains unreliable model-computed start/end. Remove those
    locally to see if the host-only policy would have yielded a SOURCE
    candidate, but never store a repaired historical response or upgrade it.
    """
    _visible_attested(visible_units,pinned_visible_unit_sha256)
    require(type(answer) is dict and set(answer)==ANSWER_KEYS,
            "WF89_LEGACY_ANSWER_INVALID")
    raw_sha=digest(canonical(answer))
    candidate=deepcopy(answer)
    if candidate.get("status")=="HYPOTHESIS":
        for field in CLAIM_ANCHORS:
            row=candidate.get(field)
            if not isinstance(row,dict) or not {"unit","quote"}<=set(row):
                return {"legacy_raw_answer_sha256":raw_sha,
                        "retrospective_code":"WF89_LEGACY_ANCHOR_NOT_QUOTE",
                        "legacy_schema_originally_failed":True,
                        "old_answer_never_modified":True,
                        "literary_truth_verified":False}
            candidate[field]={"unit":row["unit"],"quote":row["quote"]}
    try:
        receipt=resolve_quote_only_answer(
            candidate,visible_units=visible_units,
            pinned_visible_unit_sha256=pinned_visible_unit_sha256,
            original_source_sha256=original_source_sha256,
            frozen_fragment_sha256=frozen_fragment_sha256,
            sealed_future_unit_sha256=sealed_future_unit_sha256)
        status="RETROSPECTIVE_SOURCE_QUOTE_ONLY_MATCH"
        reason=None
        anchor_count=len(receipt["located_anchor_meta"])
    except WF89AnchorError as exc:
        status="RETROSPECTIVE_SOURCE_QUOTE_REJECTED"
        reason=str(exc)
        anchor_count=0
    return {
        "format":"wf.learn.retrospective-evidence-diagnostic.v89",
        "legacy_raw_answer_sha256":raw_sha,
        "original_v88_schema_valid":False,
        "retrospective_result":status,
        "reason_code":reason,
        "candidate_anchor_count":anchor_count,
        "historical_answer_rewritten":False,
        "can_be_used_for_v86_approval":False,
        "can_be_used_for_WF_write":False,
        "independent_literary_truth_verified":False,
        "model_calls":0,"r2_writes":0,
        "private_source_or_model_response_in_report":False,
    }
