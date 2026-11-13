"""Offline SHADOW kernel for source-anchored fictional space, actors and change.

Not a novel parser, LLM trainer or proof of causal truth. Original passages and
identity crosswalks stay in private ledgers. Time semantics remain external.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any

FORMAT = "wf.source-world-episode.v1"
EPISTEMIC = {"NARRATED", "CHARACTER_BELIEF", "RUMOUR", "HYPOTHESIS", "UNKNOWN", "UNEXPLAINED"}


class EpisodeError(ValueError):
    pass


def require(test: bool, code: str) -> None:
    if not test:
        raise EpisodeError(code)


def amount(value: Any) -> Decimal:
    require(isinstance(value, str), "RESOURCE_MUST_BE_DECIMAL_STRING")
    try:
        n = Decimal(value)
    except InvalidOperation as exc:
        raise EpisodeError("BAD_RESOURCE") from exc
    require(n.is_finite(), "NONFINITE_RESOURCE")
    return n


def line_units(raw: bytes, start: int, end: int) -> list[dict]:
    """Byte-exhaustive chapter partition, but each unit starts PENDING."""
    require(0 <= start <= end <= len(raw), "BAD_SCOPE")
    units, cursor = [], start
    while cursor < end:
        boundary = raw.find(b"\n", cursor, end)
        nxt = end if boundary < 0 else boundary + 1
        units.append({"start": cursor, "end": nxt, "status": "PENDING", "claim_ids": []})
        cursor = nxt
    return units


def _unique(items: list[dict], label: str) -> dict[str, dict]:
    found = {}
    for item in items:
        ident = item.get("id")
        require(isinstance(ident, str) and ident and ident not in found, "DUPLICATE_OR_BAD_" + label)
        found[ident] = item
    return found


def validate_source(episode: dict, raw: bytes) -> dict:
    require(episode.get("format") == FORMAT, "BAD_FORMAT")
    source = episode.get("source", {})
    require(source.get("sha256") == sha256(raw).hexdigest(), "SOURCE_SHA_MISMATCH")
    codec = source.get("encoding")
    require(codec in ("utf-8", "utf-8-sig", "gb18030"), "BAD_ENCODING")
    start, end = source.get("scope", (None, None))
    require(isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(raw), "BAD_SCOPE")
    raw[start:end].decode(codec, "strict")

    units, cursor = episode.get("units", []), start
    for unit in units:
        require(unit.get("start") == cursor and isinstance(unit.get("end"), int), "SOURCE_UNIT_GAP")
        cursor = unit["end"]
        require(cursor <= end, "UNIT_OUTSIDE_SCOPE")
        require(unit.get("status") in ("PENDING", "REVIEWED", "NON_NARRATIVE"), "BAD_UNIT_STATUS")
        if unit["status"] == "REVIEWED":
            require(bool(unit.get("claim_ids")), "REVIEWED_WITH_NO_CLAIMS")
    require(cursor == end, "SOURCE_UNIT_GAP")

    anchors = _unique(episode.get("anchors", []), "ANCHOR")
    for a in anchors.values():
        lo, hi = a.get("start"), a.get("end")
        require(isinstance(lo, int) and isinstance(hi, int) and start <= lo < hi <= end, "ANCHOR_OUTSIDE_SCOPE")
        require(raw[lo:hi].decode(codec, "strict") == a.get("surface"), "SOURCE_ANCHOR_MISMATCH")
        require(a.get("review") in ("UNREVIEWED", "PROVISIONAL", "INDEPENDENT_APPROVED"), "BAD_REVIEW_STATE")

    places = _unique(episode.get("places", []), "PLACE")
    actors = _unique(episode.get("actors", []), "ACTOR")
    routes = _unique(episode.get("routes", []), "ROUTE")
    rules = _unique(episode.get("rules", []), "RULE")
    facts = _unique(episode.get("facts", []), "FACT")
    events = _unique(episode.get("events", []), "EVENT")
    objects = (list(places.values()) + list(actors.values()) + list(routes.values()) +
               list(rules.values()) + list(facts.values()) + list(events.values()))
    for obj in objects:
        evidence = obj.get("evidence_ids")
        require(isinstance(evidence, list) and evidence and all(e in anchors for e in evidence),
                "MISSING_SOURCE_EVIDENCE")
    for p in places.values():
        parent = p.get("parent_id")
        require(parent is None or parent in places, "UNKNOWN_PARENT_PLACE")
        seen = {p["id"]}
        while parent is not None:
            require(parent not in seen, "PLACE_CONTAINMENT_CYCLE")
            seen.add(parent)
            parent = places[parent].get("parent_id")
    for r in routes.values():
        require(r.get("source") in places and r.get("target") in places, "BAD_DIRECTED_ROUTE")
        for v in r.get("cost", {}).values():
            require(amount(v) >= 0, "NEGATIVE_TRAVEL_COST")
    for a in actors.values():
        require(a.get("location") is None or a["location"] in places, "BAD_ACTOR_PLACE")
        for v in a.get("resources", {}).values():
            require(amount(v) >= 0, "NEGATIVE_INITIAL_RESOURCE")
        require(all(x in facts for x in a.get("knows", [])), "UNKNOWN_KNOWLEDGE_FACT")
    for rule in rules.values():
        require(isinstance(rule.get("action_tag"), str) and rule["action_tag"], "BAD_RULE_SCOPE")
        require(isinstance(rule.get("requirements", []), list), "BAD_RULE_REQUIREMENTS")
    for f in facts.values():
        require(f.get("epistemic") in EPISTEMIC, "BAD_EPISTEMIC_AUTHORITY")
        require(f.get("place_id") is None or f["place_id"] in places, "BAD_FACT_PLACE")
    by_reveal = []
    for ev in events.values():
        require(ev.get("actor_id") is None or ev["actor_id"] in actors, "UNKNOWN_EVENT_ACTOR")
        require(ev.get("place_id") is None or ev["place_id"] in places, "UNKNOWN_EVENT_PLACE")
        require(all(x in events for x in ev.get("cause_ids", [])), "UNKNOWN_CAUSAL_REFERENCE")
        by_reveal.append(min(anchors[a]["start"] for a in ev["evidence_ids"]))
        require(ev.get("certainty") in ("OBSERVED", "POSSIBLE", "UNEXPLAINED"),
                "BAD_EVENT_CERTAINTY")
    # Text presentation order is not world-event time.
    require(by_reveal == sorted(by_reveal), "REVEAL_ORDER_NOT_SOURCE_ORDER")
    for u in units:
        for claim_id in u.get("claim_ids", []):
            require(claim_id in places or claim_id in actors or claim_id in routes or
                    claim_id in rules or claim_id in facts or claim_id in events,
                    "UNIT_REFERENCES_UNKNOWN_CLAIM")

    total = sum(u["end"] - u["start"] for u in units)
    reviewed = sum(u["end"] - u["start"] for u in units
                   if u["status"] in ("REVIEWED", "NON_NARRATIVE"))
    approved = sum(1 for a in anchors.values() if a["review"] == "INDEPENDENT_APPROVED")
    # Even all review markers cannot prove 1:1 fictional meaning.
    return {"byte_index_complete": total == end - start,
            "self_reported_reviewed_bytes": reviewed, "scope_bytes": total,
            "literary_one_to_one_verified": False,
            "approved_anchors": approved, "total_anchors": len(anchors),
            "source_sha256": source["sha256"]}


def anonymized_structure(episode: dict) -> dict:
    """For LOCAL candidate testing only, not safe for public release or author context."""
    out = {"format": FORMAT, "review_gate": "UNVERIFIED_LOCAL_CANDIDATE"}
    for k in ("places", "actors", "routes", "rules", "facts", "events"):
        out[k] = []
        for obj in episode.get(k, []):
            out[k].append({key: deepcopy(val) for key, val in obj.items()
                           if key not in ("evidence_ids", "surface", "name", "source_title",
                                          "source_sha256", "original_text", "private_note")})
    return out


def initial_world(episode: dict) -> dict:
    """Explicit fictional state; not a source-truth claim."""
    return {
        "places": {p["id"]: deepcopy(p) for p in episode.get("places", [])},
        "routes": {r["id"]: deepcopy(r) for r in episode.get("routes", [])},
        "rules": {r["id"]: deepcopy(r) for r in episode.get("rules", [])},
        "facts": {f["id"]: deepcopy(f) for f in episode.get("facts", [])},
        "actors": {a["id"]: {"at": a.get("location"),
                              "resources": {k: str(amount(v)) for k, v in
                                            a.get("resources", {}).items()},
                              "access": list(a.get("access", [])),
                              "knows": list(a.get("knows", [])),
                              "believes": list(a.get("believes", [])),
                              "role_at_open": a.get("role_at_open", "unspecified"),
                              "attributes": deepcopy(a.get("attributes", {}))}
                   for a in episode.get("actors", [])},
        "history": [],
    }


def _charge(resources: dict, costs: dict) -> None:
    for item, value in costs.items():
        debit = amount(value)
        require(debit >= 0, "NEGATIVE_COST")
        balance = amount(resources.get(item, "0"))
        require(balance >= debit, "INSUFFICIENT_RESOURCE")
        resources[item] = str(balance - debit)


def check_rule(actor: dict, rule: dict) -> None:
    """World rules bound feasibility, never force action or a result."""
    for req in rule.get("requirements", []):
        kind = req.get("kind")
        if kind == "access":
            require(req.get("token") in actor["access"], "WORLD_RULE_ACCESS_DENIED")
        elif kind == "resource_min":
            require(amount(actor["resources"].get(req.get("key"), "0")) >= amount(req.get("value")),
                    "WORLD_RULE_RESOURCE_DENIED")
        elif kind == "knows":
            require(req.get("fact_id") in actor["knows"], "WORLD_RULE_KNOWLEDGE_DENIED")
        elif kind == "at_place":
            require(actor["at"] == req.get("place_id"), "WORLD_RULE_PLACE_DENIED")
        elif kind == "attribute_equals":
            require(actor["attributes"].get(req.get("key")) == req.get("value"),
                    "WORLD_RULE_ATTRIBUTE_DENIED")
        else:
            raise EpisodeError("UNKNOWN_WORLD_REQUIREMENT")


def apply_proposal(world: dict, proposal: dict) -> dict:
    """One atomic author-chosen action, no automatically replayed story future."""
    next_world = deepcopy(world)
    kind = proposal.get("kind")
    actor_id = proposal.get("actor_id")
    actors = next_world["actors"]
    require(kind in ("move", "witness", "tell", "act", "accident"), "UNKNOWN_EVENT_KIND")
    if kind != "accident":
        require(actor_id in actors, "UNKNOWN_ACTOR")
    actor = actors.get(actor_id)
    causes = list(proposal.get("causes", []))
    require(all(isinstance(c, str) and c in {h["id"] for h in next_world["history"]}
                for c in causes), "UNWARRANTED_CAUSE")
    event_id = proposal.get("id", "EV%04d" % (len(next_world["history"]) + 1))
    require(isinstance(event_id, str) and event_id and
            event_id not in {h["id"] for h in next_world["history"]}, "DUPLICATE_WORLD_EVENT")

    if kind == "move":
        route = next_world["routes"].get(proposal.get("route_id"))
        require(route is not None, "NO_EVIDENCED_ROUTE")
        require(actor["at"] == route["source"], "WRONG_ROUTE_ORIGIN")
        require(set(route.get("requires", [])).issubset(actor["access"]), "ROUTE_ACCESS_DENIED")
        _charge(actor["resources"], route.get("cost", {}))
        actor["at"] = route["target"]  # reverse edge needs separate evidence

    elif kind == "witness":
        fact = next_world["facts"].get(proposal.get("fact_id"))
        require(fact is not None and fact["epistemic"] == "NARRATED", "NOT_A_VERIFIED_WORLD_FACT")
        require(fact.get("place_id") is not None and actor["at"] == fact["place_id"],
                "NO_LOCAL_OBSERVATION")
        if proposal["fact_id"] not in actor["knows"]:
            actor["knows"].append(proposal["fact_id"])

    elif kind == "tell":
        target = actors.get(proposal.get("target_id"))
        require(target is not None, "UNKNOWN_RECIPIENT")
        require(actor["at"] is not None and actor["at"] == target["at"],
                "NO_COMMUNICATION_CHANNEL")
        fact_id = proposal.get("fact_id")
        require(fact_id in next_world["facts"], "UNKNOWN_TOLD_FACT")
        mode = proposal.get("mode")
        require(mode in ("truthful", "rumour", "lie"), "UNKNOWN_TESTIMONY_MODE")
        if mode == "truthful":
            require(fact_id in actor["knows"], "SENDER_DOES_NOT_KNOW")
        claim = {"fact_id": fact_id, "heard_from": actor_id, "mode": mode}
        if claim not in target["believes"]:
            target["believes"].append(claim)  # never auto-upgrade hearsay to truth

    else:  # act or accident
        if kind == "act":
            for rule in next_world.get("rules", {}).values():
                if rule["action_tag"] == proposal.get("action_tag"):
                    check_rule(actor, rule)
            require(set(proposal.get("needs_known", [])).issubset(actor["knows"]),
                    "ACTOR_CANNOT_USE_HIDDEN_KNOWLEDGE")
            _charge(actor["resources"], proposal.get("cost", {}))
        for effect in proposal.get("effects", []):
            target = actors.get(effect.get("actor_id"))
            require(target is not None, "UNKNOWN_EFFECT_TARGET")
            field = effect.get("field")
            if field == "resource":
                key = effect.get("key")
                require(isinstance(key, str) and key, "BAD_RESOURCE_KEY")
                before = amount(target["resources"].get(key, "0"))
                after = before + amount(effect.get("delta"))
                require(after >= 0, "NEGATIVE_RESOURCE_BALANCE")
                target["resources"][key] = str(after)
            elif field == "access":
                token = effect.get("key")
                require(isinstance(token, str) and token, "BAD_ACCESS_TOKEN")
                if effect.get("grant") is True and token not in target["access"]:
                    target["access"].append(token)
                elif effect.get("grant") is False and token in target["access"]:
                    target["access"].remove(token)
                else:
                    require(effect.get("grant") in (True, False), "BAD_ACCESS_EFFECT")
            else:
                raise EpisodeError("UNRECOGNIZED_EFFECT")

    require(not (causes and proposal.get("certainty") == "UNEXPLAINED"),
            "UNEXPLAINED_WITH_CLAIMED_CAUSE")
    if kind == "accident":
        require(proposal.get("certainty") in ("UNEXPLAINED", "POSSIBLE"),
                "ACCIDENT_IS_NOT_INEVITABLE")
    next_world["history"].append({"id": event_id, "kind": kind, "actor_id": actor_id,
                                  "time_ref": proposal.get("time_ref"),
                                  "causes": causes,
                                  "certainty": proposal.get("certainty", "POSSIBLE")})
    return next_world


def try_proposal(world: dict, proposal: dict) -> dict:
    try:
        return {"accepted": True, "state": apply_proposal(world, proposal),
                "future": "UNSPECIFIED_UNTIL_NEW_AUTHOR_ACTION"}
    except EpisodeError as exc:
        return {"accepted": False, "reason": str(exc), "state": deepcopy(world),
                "future": "UNSPECIFIED_UNTIL_NEW_AUTHOR_ACTION"}
