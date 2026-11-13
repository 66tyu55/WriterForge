"""Event-first original-time parameter locator (SHADOW; source private).

DOES NOT automate understanding of fiction. Evidence-anchored manual event
claims enter as candidates. Parameters are needed only relative to preregistered
questions; dropping a needed fact must change a *representable* answer to
UNKNOWN. This is NOT blind causal validation or complete-book learning.
No original text, names, evidence spans or human gold in public repository.
"""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
from pathlib import Path
import json


class EvidenceError(ValueError):
    pass


def _sha(blob):
    return sha256(blob).hexdigest()


def read_source(path):
    raw = Path(path).read_bytes()
    for codec in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = raw.decode(codec, errors="strict")
        except UnicodeError:
            continue
        if text.encode(codec) == raw:
            return raw, text, codec
    raise EvidenceError("SOURCE_ENCODING_NOT_REVERSIBLE")


def validate(package, raw=None, codec=None):
    if package.get("format") != "wf.event-first.time-invariants.v1":
        raise EvidenceError("FORMAT")
    evidence = package["evidence"]
    facts = package["facts"]
    questions = package["questions"]
    emap = {x["id"]: x for x in evidence}
    fmap = {x["id"]: x for x in facts}
    if len(emap) != len(evidence) or len(fmap) != len(facts):
        raise EvidenceError("DUPLICATE_IDS")
    if raw is not None:
        left, right = (package.get("source_scope_byte_start"),
                       package.get("source_scope_byte_end"))
        if (package.get("source_scope_verified") is not True or
                type(left) is not int or type(right) is not int or
                not 0 <= left < right <= len(raw)):
            raise EvidenceError("UNVERIFIED_CHAPTER_SCOPE")
        if _sha(raw) != package["source_sha256"]:
            raise EvidenceError("SOURCE_SHA_MISMATCH")
        for ev in evidence:
            a, b = ev["start"], ev["end"]
            if (type(a) is not int or type(b) is not int or
                    not left <= a < b <= right):
                raise EvidenceError("EVIDENCE_OUTSIDE_CHAPTER")
            span = raw[a:b]
            if _sha(span) != ev["span_sha256"]:
                raise EvidenceError("EVIDENCE_TAMPERED")
            try:
                span.decode(codec, errors="strict")
            except UnicodeError as exc:
                raise EvidenceError("EVIDENCE_SPLITS_CHARACTER") from exc
    for fact in facts:
        if (not fact["evidence_ids"] or
                any(x not in emap for x in fact["evidence_ids"])):
            raise EvidenceError("FACT_LACKS_SOURCE")
        if fact["scope"] != "this_story_only":
            raise EvidenceError("FALSE_UNIVERSAL_LAW")
        if (fact["state"] not in
                {"REPORTED","OBSERVED","INFERRED","UNKNOWN","FORECAST","SCHEDULED"}):
            raise EvidenceError("EPISTEMIC_STATUS_INVALID")
        value = fact["value"]
        if value is not None:
            if type(value) is not str or fact["unit"] is None:
                raise EvidenceError("NUMBER_UNIT_MISSING")
            try:
                Fraction(value)
            except (ValueError, ZeroDivisionError) as exc:
                raise EvidenceError("NON_EXACT_NUMBER") from exc
    for q in questions:
        if not q["requires"] or any(x not in fmap for x in q["requires"]):
            raise EvidenceError("QUESTION_USES_NONEXISTENT_FACT")
    return True


def query(package, question_id, *, removed=()):
    """Never replace a missing evidence premise with a typical xianxia trope."""
    q = next(x for x in package["questions"] if x["id"] == question_id)
    fm = {f["id"]:f for f in package["facts"] if f["id"] not in removed}
    if any(x not in fm for x in q["requires"]):
        return {"state":"UNKNOWN", "reason":"NECESSARY_EVIDENCE_REMOVED"}
    op = q["operation"]
    fs = [fm[x] for x in q["requires"]]
    if op == "conditional_window":
        period, expiration, prognosis = fs
        if (period["unit"] != expiration["unit"] or
                period["value"] != expiration["value"] or
                prognosis["state"] not in {"FORECAST","REPORTED"}):
            return {"state":"UNKNOWN","reason":"TIME_WINDOW_NOT_GROUNDED"}
        return {"state":"CONDITIONAL_RISK","after":period["value"],
                "unit":period["unit"],"certain_event":False}
    if op == "divide":
        total, per_action = fs
        if (total["unit"] != per_action["unit"] or
                Fraction(per_action["value"]) == 0):
            return {"state":"UNKNOWN","reason":"INCOMPATIBLE_COST_UNITS"}
        return {"state":"CONDITIONAL_ARITHMETIC","value":str(
            Fraction(total["value"])/Fraction(per_action["value"])),
            "unit":q["unit"],
            "assumptions":q.get("assumptions",[]),
            "action_count_directly_observed":False}
    if op == "reported_bound":
        f = fs[0]
        return {"state":"REPORTED_BOUND","value":f["value"],
                "unit":f["unit"],"bound":f["qualifier"],
                "death_at_exact_time_proven":False}
    if op == "scheduled":
        f = fs[0]
        return {"state":"PLANNED_NOT_CONFIRMED","after":f["value"],
                "unit":f["unit"]}
    if op == "promise_window":
        f = fs[0]
        return {"state":"REPORTED_NORMATIVE_RESTRICTION",
                "duration":f["value"],"unit":f["unit"],
                "breach_possible":True,"attack_after_expiry_certain":False}
    if op == "deadline_consequence":
        due, conditional_penalty, institution = fs
        if (due["state"] not in {"FORECAST","REPORTED"} or
                conditional_penalty["state"] != "FORECAST"):
            return {"state":"UNKNOWN","reason":"DEADLINE_NOT_ESTABLISHED"}
        return {"state":"CONDITIONAL_INSTITUTIONAL_CONSEQUENCE",
                "after":due["value"],"unit":due["unit"],
                "automatic_result":False,"policy_may_change":True}
    raise EvidenceError("UNSUPPORTED_QUERY_OPERATION")


def ablation(package):
    """Representational indispensability on FROZEN questions, NOT true causality."""
    validate(package)
    base = {q["id"]:query(package,q["id"]) for q in package["questions"]}
    needed,unused = [],[]
    for fact in package["facts"]:
        changes = [qid for qid,before in base.items()
                   if query(package,qid,removed=(fact["id"],)) != before]
        (needed if changes else unused).append({
            "fact_id":fact["id"],"changed_questions":changes})
    return {
        "format":"wf.event-first.time-ablation.v1",
        "candidate_fact_count":len(package["facts"]),
        "frozen_question_count":len(package["questions"]),
        "needed_within_current_questions":needed,
        "not_needed_yet_keep_for_more_questions":unused,
        "results":base,
        "source_facts_independently_reviewed":False,
        "causal_identification_proven":False,
        "full_novel_time_model_complete":False,
    }


def private_anchor(raw, codec, literal, left, right):
    span = literal.encode(codec)
    a = raw.find(span, left, right)
    if a < 0 or raw.find(span,a+1,right)>=0:
        raise EvidenceError("ANCHOR_MISSING_OR_NONUNIQUE_WITHIN_WINDOW")
    return a,a+len(span),_sha(span)


def freeze_private(original, spec):
    """Only local trust-boundary code; NEVER commit returned source literals."""
    raw, text, codec = read_source(original)
    start_marker, end_marker = spec["private_scope"]["start_marker"], spec["private_scope"]["end_marker"]
    a = text.find(start_marker)
    b = text.find(end_marker,a+len(start_marker)) if a>=0 else -1
    if a<0 or b<0 or text.find(start_marker,a+1)>=0:
        raise EvidenceError("SOURCE_SCOPE_MARKERS_INVALID")
    left = len(text[:a].encode(codec))
    right = len(text[:b].encode(codec))
    ev = []
    for e in spec["evidence"]:
        x,y,h = private_anchor(raw,codec,e["literal"],left,right)
        ev.append({"id":e["id"],"start":x,"end":y,
                   "span_sha256":h,"source_literal_PRIVATE":e["literal"]})
    package = {k:v for k,v in spec.items() if k not in {"evidence","private_scope"}}
    package.update({
        "format":"wf.event-first.time-invariants.v1",
        "evidence":ev,"source_sha256":_sha(raw),
        "source_scope_verified":True,"source_scope_byte_start":left,
        "source_scope_byte_end":right,
        "source_bytes":len(raw),"source_encoding":codec
    })
    validate(package,raw,codec)
    return package
