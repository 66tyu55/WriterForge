"""V54 deterministic fact / timeline / contradiction / candidate foundation.

No LLM calls and no fictional prose generation. The event journal is an
append-only local SQLite database that holds typed identifiers and SHA
references, not original chapters or host-written technique paragraphs.

The engine can prove facts ABOUT ITS OWN RECORDS (same ID, timeline order,
contradicting status, linked-event references). It CANNOT prove that a
natural-language author's intent, motive or literary causal relation is true.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import re
import sqlite3

ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,79}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
FACT_STATES = frozenset(("KNOWN", "UNKNOWN", "DISPUTED", "FALSE"))
EVENT_ROLES = frozenset(("OBSERVE", "THINK", "CHOOSE", "CONSEQUENCE", "REVEAL"))
RELATIONS = frozenset(("BEFORE", "POTENTIAL_CAUSE", "CONTRADICTS"))
CANDIDATE_STATES = frozenset(("PROPOSED", "PAUSED", "RETIRED"))


class FactLedgerError(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise FactLedgerError(reason)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def digest(value):
    return sha256(value.encode("utf-8")).hexdigest()


def key(value):
    return isinstance(value, str) and ID.fullmatch(value) is not None


def checked_event(value):
    need(isinstance(value, dict) and set(value) == {
        "event_id", "scene_id", "actor_id", "fact_id",
        "tick", "state", "role", "evidence_sha256"},
        "FACT_EVENT_FIELDS_INVALID")
    for field in ("event_id", "scene_id", "actor_id", "fact_id"):
        need(key(value[field]), "FACT_EVENT_ID_INVALID")
    need(type(value["tick"]) is int and 0 <= value["tick"] <= 10000000,
         "FACT_TICK_INVALID")
    need(value["state"] in FACT_STATES and value["role"] in EVENT_ROLES,
         "FACT_TYPED_STATE_OR_ROLE_INVALID")
    need(isinstance(value["evidence_sha256"], str) and
         SHA.fullmatch(value["evidence_sha256"]),
         "FACT_EVIDENCE_DIGEST_INVALID")
    return value


class FactJournal:
    def __init__(self, file: str | Path):
        """Only explicit use creates local metadata storage. No R2 access."""
        self.db = sqlite3.connect(str(file), cached_statements=32)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA cache_size=-1024")
        self.db.execute("PRAGMA temp_store=FILE")
        self.db.execute("PRAGMA max_page_count=16384")  # ~64 MiB with 4KiB pages
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS fact_events(
            event_id TEXT PRIMARY KEY, scene TEXT NOT NULL,
            actor TEXT NOT NULL, fact TEXT NOT NULL,
            tick INTEGER NOT NULL, state TEXT NOT NULL,
            role TEXT NOT NULL, evidence_sha TEXT NOT NULL,
            event_sha TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS fact_lookup
            ON fact_events(scene,actor,fact,tick);
        CREATE TABLE IF NOT EXISTS fact_links(
            link_sha TEXT PRIMARY KEY,
            source_event TEXT NOT NULL, target_event TEXT NOT NULL,
            relation TEXT NOT NULL, relation_claim_status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS pattern_versions(
            candidate_id TEXT NOT NULL, version INTEGER NOT NULL,
            previous_sha TEXT, body_sha TEXT NOT NULL,
            body_json TEXT NOT NULL,
            PRIMARY KEY(candidate_id,version));
        """)
        self.db.commit()

    def close(self):
        self.db.close()

    def append(self, item):
        checked_event(item)
        record_sha = digest(canonical(item))
        existing = self.db.execute(
            "SELECT event_sha FROM fact_events WHERE event_id=?",
            (item["event_id"],)).fetchone()
        if existing is not None:
            need(existing["event_sha"] == record_sha,
                 "FACT_IMMUTABLE_EVENT_REPLACEMENT_FORBIDDEN")
            return {"event_id": item["event_id"], "event_sha256": record_sha,
                    "idempotent_replay": True, "semantic_truth_proven": False}
        last = self.db.execute(
            "SELECT MAX(tick) AS tick FROM fact_events "
            "WHERE scene=? AND actor=? AND fact=?",
            (item["scene_id"], item["actor_id"], item["fact_id"])
        ).fetchone()["tick"]
        need(last is None or item["tick"] >= last,
             "FACT_BACKDATED_REVISION_FORBIDDEN")
        with self.db:
            self.db.execute(
                "INSERT INTO fact_events VALUES(?,?,?,?,?,?,?,?,?)",
                (item["event_id"], item["scene_id"], item["actor_id"],
                 item["fact_id"], item["tick"], item["state"],
                 item["role"], item["evidence_sha256"], record_sha))
        return {"event_id": item["event_id"], "event_sha256": record_sha,
                "idempotent_replay": False, "semantic_truth_proven": False}

    @staticmethod
    def _assert_record_integrity(row):
        original = {
            "event_id": row["event_id"], "scene_id": row["scene"],
            "actor_id": row["actor"], "fact_id": row["fact"],
            "tick": row["tick"], "state": row["state"],
            "role": row["role"], "evidence_sha256": row["evidence_sha"],
        }
        need(digest(canonical(original)) == row["event_sha"],
             "FACT_STORED_EVENT_TAMPERED")
        return original

    def state(self, *, scene: str, actor: str, fact: str, at_tick: int | None = None):
        need(all(key(x) for x in (scene, actor, fact)), "FACT_QUERY_KEY_INVALID")
        need(at_tick is None or type(at_tick) is int and 0 <= at_tick <= 10000000,
             "FACT_QUERY_TIME_INVALID")
        q = (
            "SELECT event_id,scene,actor,fact,tick,state,role,evidence_sha,event_sha FROM fact_events "
            "WHERE scene=? AND actor=? AND fact=? "
        )
        bind = [scene,actor,fact]
        if at_tick is not None:
            q += "AND tick<=? "
            bind.append(at_tick)
        q += "ORDER BY tick DESC,event_id LIMIT 65"
        rows = list(self.db.execute(q,bind))
        need(len(rows) <= 64, "FACT_QUERY_HISTORY_BUDGET_EXCEEDED")
        for row in rows:
            self._assert_record_integrity(row)
        if not rows:
            return {"format":"WF.fact-state.v1",
                    "scene":scene, "actor":actor,"fact":fact,
                    "state":"UNRECORDED","latest_tick":None,
                    "evidence_events":[],"conflicting_events":[],
                    "author_intent_verified":False}
        last=rows[0]["tick"]
        newest=[x for x in rows if x["tick"]==last]
        statuses={x["state"] for x in newest}
        conflicted = len(statuses) > 1 or "DISPUTED" in statuses
        return {
            "format":"WF.fact-state.v1",
            "scene":scene,"actor":actor,"fact":fact,
            "state":"CONFLICT_UNRESOLVED" if conflicted else newest[0]["state"],
            "latest_tick":last,
            "evidence_events":[x["event_id"] for x in newest],
            "conflicting_events":[x["event_id"] for x in newest] if conflicted else [],
            "historical_version_count_examined":len(rows),
            "history_truncated":len(rows)==64,
            "author_intent_verified":False,
        }

    def link(self, source_event: str, target_event: str, relation: str):
        need(key(source_event) and key(target_event) and
             source_event != target_event and relation in RELATIONS,
             "FACT_LINK_INVALID")
        records = self.db.execute(
            "SELECT event_id,scene,actor,fact,tick,state,role,evidence_sha,event_sha FROM fact_events "
            "WHERE event_id IN (?,?)", (source_event,target_event)).fetchall()
        need(len(records)==2, "FACT_LINK_REFERENCES_MISSING")
        for row in records:
            self._assert_record_integrity(row)
        source = next(x for x in records if x["event_id"]==source_event)
        target = next(x for x in records if x["event_id"]==target_event)
        need(source["scene"]==target["scene"],
             "FACT_LINK_CROSS_SCENE_FORBIDDEN")
        if relation in ("BEFORE","POTENTIAL_CAUSE"):
            need(source["tick"] < target["tick"],
                 "FACT_LINK_TIME_ORDER_INVALID")
        raw = canonical({"source":source_event,"target":target_event,"relation":relation})
        h = digest(raw)
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO fact_links VALUES(?,?,?,?,?)",
                (h,source_event,target_event,relation,"CLAIMED_UNVERIFIED"))
        return {"link_sha256":h,"relation":relation,
                "source_event":source_event,"target_event":target_event,
                "causal_semantics_verified":False}

    def add_candidate(self, *, candidate_id:str, version:int,
                      prior_sha:str|None, record:dict):
        """Append-only revisions. No candidate can auto-generate prose."""
        need(key(candidate_id) and type(version) is int and 1 <= version <= 100,
             "FACT_CANDIDATE_VERSION_INVALID")
        need(isinstance(record,dict) and set(record)=={
            "fact_id","scene_id","condition_state","event_refs",
            "counterexample_refs","status"},
            "FACT_CANDIDATE_SCHEMA_INVALID")
        need(key(record["fact_id"]) and key(record["scene_id"]) and
             record["condition_state"] in FACT_STATES and
             record["status"] in CANDIDATE_STATES,
             "FACT_CANDIDATE_CONDITION_INVALID")
        for field in ("event_refs","counterexample_refs"):
            refs=record[field]
            need(isinstance(refs,list) and 0 < len(refs) <= 8 and
                 len(refs)==len(set(refs)) and all(key(x) for x in refs),
                 "FACT_CANDIDATE_EVENT_REFS_INVALID")
            existing=self.db.execute(
                "SELECT event_id FROM fact_events WHERE event_id IN (" +
                ",".join("?" for _ in refs) + ")",refs).fetchall()
            need(len(existing)==len(refs),
                 "FACT_CANDIDATE_EVIDENCE_NOT_IN_JOURNAL")
        raw = canonical(record)
        h = digest(raw)
        existing = self.db.execute(
            "SELECT body_sha,previous_sha FROM pattern_versions "
            "WHERE candidate_id=? AND version=?", (candidate_id,version)
        ).fetchone()
        if existing:
            need(existing["body_sha"]==h and existing["previous_sha"]==prior_sha,
                 "FACT_CANDIDATE_REVISION_IMMUTABLE")
            return {"candidate_sha256":h, "idempotent_replay":True,
                    "eligible_to_change_writing":False}
        latest=self.db.execute(
            "SELECT version,body_sha,body_json FROM pattern_versions "
            "WHERE candidate_id=? ORDER BY version DESC LIMIT 1",
            (candidate_id,)).fetchone()
        if latest:
            need(digest(latest["body_json"])==latest["body_sha"],
                 "FACT_CANDIDATE_PRIOR_VERSION_TAMPERED")
            previous=json.loads(latest["body_json"])
            need(previous["status"]!="RETIRED",
                 "FACT_CANDIDATE_RETIRED_IS_TERMINAL")
            need(h != latest["body_sha"],
                 "FACT_CANDIDATE_EMPTY_REVISION_IS_NOT_PROGRESS")
            need(version==latest["version"]+1 and prior_sha==latest["body_sha"],
                 "FACT_CANDIDATE_REVISION_CHAIN_INVALID")
        else:
            need(version==1 and prior_sha is None,
                 "FACT_CANDIDATE_MISSING_GENESIS")
        with self.db:
            self.db.execute(
                "INSERT INTO pattern_versions VALUES(?,?,?,?,?)",
                (candidate_id,version,prior_sha,h,raw))
        return {"candidate_sha256":h,"idempotent_replay":False,
                "version":version,"status":record["status"],
                "eligible_to_change_writing":False,
                "semantic_truth_proven":False}

    def latest_candidate(self, candidate_id):
        need(key(candidate_id), "FACT_CANDIDATE_KEY_INVALID")
        row=self.db.execute(
            "SELECT version,body_sha,body_json FROM pattern_versions "
            "WHERE candidate_id=? ORDER BY version DESC LIMIT 1",
            (candidate_id,)).fetchone()
        if row is None:
            return {"candidate_id":candidate_id,"state":"NOT_FOUND"}
        need(digest(row["body_json"])==row["body_sha"],
             "FACT_CANDIDATE_LEDGER_TAMPERED")
        record=json.loads(row["body_json"])
        return {"candidate_id":candidate_id,"version":row["version"],
                "status":record["status"],
                "record_sha256":row["body_sha"],
                "applicable_only_as_unreviewed_comparison":True,
                "eligible_to_change_writing":False}
