"""V117 persistent pending continuity debts INSIDE existing signed checkpoint.

A rejected transfer, missing resource, or other anchored risk is not erased
simply because a new chapter starts. No "auto-resolve"; only a later
authorized explicit review/adoption could settle it. Bounded with fail-closed
quota; historical checkpoint SHA forms immutable lineage, not a second DB.
"""
from __future__ import annotations
from hashlib import sha256
import json
import re

FORMAT="wf.continuity.v117.open-source-evidence-debt"
MAX_DEBTS=96
SHA=re.compile(r"^[0-9a-f]{64}$")

def _need(ok,code):
    if not ok: raise ValueError(code)

def _risk_rows(checkpoint):
    native=checkpoint.get("original_native_candidate_report") or {}
    reducer=checkpoint.get("reducer_result") or {}
    rows=[]
    for origin,riskset in (("novel_studio",reducer.get("risks",[])),
                           ("wf_literal",native.get("risks",[]))):
        _need(type(riskset) is list and len(riskset)<=55,
              "WF117_DEBT_SOURCE_RISK_BOUNDS")
        for r in riskset:
            if type(r) is dict and type(r.get("kind")) is str:
                rows.append((origin,r))
    return rows

def _origin_debts(checkpoint):
    source=checkpoint.get("source_sha256")
    _need(type(source) is str and SHA.fullmatch(source),
          "WF117_DEBT_SOURCE_HASH_REQUIRED")
    seq=checkpoint.get("sequence")
    _need(type(seq) is int and seq>=1,
          "WF117_DEBT_SEQUENCE_INVALID")
    result=[]
    for origin,r in _risk_rows(checkpoint):
        item=str(r.get("item") or r.get("item_sha256") or
                 r.get("resource") or r.get("code") or "unknown")
        kind=r["kind"][:80]
        # Stable per-source diagnostic identity; exclude incidental counters.
        material=json.dumps([source,seq,origin,kind,item,
               r.get("prior_disposal_start"),
               r.get("suspect_action_anchor",{}).get("start")
                 if type(r.get("suspect_action_anchor")) is dict else None],
               ensure_ascii=False,separators=(",",":"))
        rid=sha256(material.encode("utf8")).hexdigest()
        result.append({
            "format":FORMAT,
            "id":rid,
            "origin":origin,
            "kind":kind,
            "item_key":item[:90],
            "first_source_sha256":source,
            "first_sequence":seq,
            "status":"OPEN_UNRESOLVED_CANDIDATE",
            "automatically_cleared":False,
            "literary_truth_verified":False,
        })
    return result

def _validate_old(rows):
    _need(type(rows) is list and len(rows)<=MAX_DEBTS,
          "WF117_OLD_DEBT_CAPACITY_OR_SCHEMA")
    ids=set()
    for r in rows:
        _need(type(r) is dict and
              r.get("format")==FORMAT and
              type(r.get("id")) is str and SHA.fullmatch(r["id"]) and
              r["id"] not in ids and
              type(r.get("first_source_sha256")) is str and
              SHA.fullmatch(r["first_source_sha256"]) and
              type(r.get("first_sequence")) is int and
              r["first_sequence"]>=1 and
              r.get("status")=="OPEN_UNRESOLVED_CANDIDATE" and
              r.get("automatically_cleared") is False and
              r.get("literary_truth_verified") is False and
              type(r.get("item_key")) is str and
              1<=len(r["item_key"])<=90 and
              type(r.get("kind")) is str and
              1<=len(r["kind"])<=80,
              "WF117_OLD_DEBT_TAMPERED_OR_DUPLICATED")
        ids.add(r["id"])
    return ids

def merge_open_debts(prior,checkpoint):
    """Replay any prior unresolved evidence, then append this step's risks.

    A prior V114/V116 checkpoint lacking the V117 field is migrated without
    changing its immutable SHA: its original risk arrays are read and tagged.
    """
    rows=[]
    if prior is not None:
        if "v117_open_continuity_debts" in prior:
            rows=list(prior["v117_open_continuity_debts"])
        else:
            rows=_origin_debts(prior)
    ids=_validate_old(rows)
    for r in _origin_debts(checkpoint):
        if r["id"] in ids:continue
        if len(rows)>=MAX_DEBTS:
            raise ValueError("WF117_OPEN_CONTINUITY_DEBT_CAPACITY_REFUSE_FORGET")
        ids.add(r["id"])
        rows.append(r)
    return rows

def compact_debts(checkpoint, max_items=4):
    debt=checkpoint.get("v117_open_continuity_debts",[])
    _validate_old(debt)
    if not debt:return ""
    parts=[f"【此前仍有{len(debt)}条未解决的因果/状态候选冲突】"]
    for x in debt[-max_items:]:
        parts.append(x["kind"]+"："+x["item_key"]+"（最初见于段序"+
                     str(x["first_sequence"])+"，尚未证实已解决）")
    if len(debt)>max_items:
        parts.append(f"尚有{len(debt)-max_items}条未展开，保存在完整有哈希的旧快照中。")
    parts.append("新一段看似解决问题，不等于旧冲突自动消失；只有明确复核才能关闭。")
    return "\n".join(parts)[:500]
