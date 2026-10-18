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
        -- V55 separate story-valid time and observation/recorded order.
        -- Only new typed claims use this; V54 legacy event facts are untouched.
        CREATE TABLE IF NOT EXISTS temporal_claims(
            recorded_seq INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT NOT NULL UNIQUE,
            scene TEXT NOT NULL, subject_scope TEXT NOT NULL,
            subject_id TEXT NOT NULL, fact TEXT NOT NULL,
            story_from INTEGER NOT NULL, story_until INTEGER,
            knowledge_state TEXT NOT NULL, evidence_event TEXT NOT NULL,
            supersedes_id TEXT, claim_sha TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS temporal_lookup
            ON temporal_claims(scene,subject_scope,subject_id,fact,story_from,recorded_seq);
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
            need(version==latest["version"]+1 and prior_sha==latest["body_sha"],
                 "FACT_CANDIDATE_REVISION_CHAIN_INVALID")
            need(h != latest["body_sha"],
                 "FACT_CANDIDATE_EMPTY_REVISION_IS_NOT_PROGRESS")
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


    def append_temporal_claim(self, record):
        """Bitemporal assertion. story_* is fictional valid time; recorded_seq
        is real write order. Both are needed: a flashback may be learned late.

        Caller-provided *typed facts* are inputs, not natural-language proof.
        Supersession never modifies the older claim; replay stays possible.
        """
        fields = {
            "claim_id", "scene_id", "subject_scope", "subject_id",
            "fact_id", "story_from", "story_until", "knowledge_state",
            "evidence_event_id", "supersedes_id",
        }
        need(isinstance(record, dict) and set(record) == fields,
             "FACT_TEMPORAL_SCHEMA_INVALID")
        for field in ("claim_id", "scene_id", "subject_id", "fact_id",
                      "evidence_event_id"):
            need(key(record[field]), "FACT_TEMPORAL_ID_INVALID")
        need(record["subject_scope"] in ("ACTOR", "READER"),
             "FACT_TEMPORAL_SCOPE_INVALID")
        need(record["knowledge_state"] in FACT_STATES,
             "FACT_TEMPORAL_STATE_INVALID")
        begin, end = record["story_from"], record["story_until"]
        need(type(begin) is int and 0 <= begin <= 10000000,
             "FACT_TEMPORAL_STORY_TIME_INVALID")
        need(end is None or (type(end) is int and begin < end <= 10000001),
             "FACT_TEMPORAL_INTERVAL_INVALID")
        replaced = record["supersedes_id"]
        need(replaced is None or key(replaced), "FACT_TEMPORAL_SUPERSESSION_ID_INVALID")
        content = canonical(record)
        h = digest(content)
        existing = self.db.execute(
            "SELECT recorded_seq,claim_sha FROM temporal_claims WHERE claim_id=?",
            (record["claim_id"],)).fetchone()
        if existing:
            need(existing["claim_sha"] == h, "FACT_TEMPORAL_CLAIM_IMMUTABLE")
            return {"claim_id": record["claim_id"],
                    "recorded_seq": existing["recorded_seq"],
                    "claim_sha256": h, "replayed": True,
                    "semantic_truth_verified": False}
        evidence = self.db.execute(
            "SELECT * FROM fact_events WHERE event_id=?",
            (record["evidence_event_id"],)).fetchone()
        need(evidence is not None, "FACT_TEMPORAL_EVIDENCE_MISSING")
        self._assert_record_integrity(evidence)
        need(evidence["scene"] == record["scene_id"] and
             evidence["fact"] == record["fact_id"],
             "FACT_TEMPORAL_EVIDENCE_SCOPE_MISMATCH")
        need(evidence["actor"] != "index_witness",
             "FACT_LEXICAL_INDEX_NOT_CHARACTER_KNOWLEDGE")
        if record["subject_scope"] == "ACTOR":
            need(evidence["actor"] == record["subject_id"],
                 "FACT_ACTOR_KNOWLEDGE_EVIDENCE_MISMATCH")
        if replaced is not None:
            old = self.db.execute(
                "SELECT * FROM temporal_claims WHERE claim_id=?", (replaced,)
            ).fetchone()
            need(old is not None, "FACT_TEMPORAL_SUPERSEDED_CLAIM_MISSING")
            self._verify_claim_row(old)
            need(all(old[col] == value for col,value in (
                ("scene", record["scene_id"]),
                ("subject_scope", record["subject_scope"]),
                ("subject_id", record["subject_id"]),
                ("fact", record["fact_id"]),
                ("story_from", begin), ("story_until", end))),
                "FACT_TEMPORAL_SUPERSESSION_SCOPE_OR_INTERVAL_INVALID")
            # One direct successor per claim avoids ambiguous lineage,
            # but conflicting independent observations remain possible.
            need(self.db.execute(
                "SELECT 1 FROM temporal_claims WHERE supersedes_id=?",
                (replaced,)).fetchone() is None,
                "FACT_TEMPORAL_SUPERSESSION_ALREADY_USED")
        with self.db:
            cursor = self.db.execute(
                "INSERT INTO temporal_claims("
                "claim_id,scene,subject_scope,subject_id,fact,story_from,"
                "story_until,knowledge_state,evidence_event,supersedes_id,claim_sha"
                ") VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (record["claim_id"],record["scene_id"],record["subject_scope"],
                 record["subject_id"],record["fact_id"],begin,end,
                 record["knowledge_state"],record["evidence_event_id"],
                 replaced,h))
        return {"claim_id":record["claim_id"],
                "recorded_seq":cursor.lastrowid,"claim_sha256":h,
                "replayed":False,"semantic_truth_verified":False}

    @staticmethod
    def _claim_as_record(row):
        return {
            "claim_id":row["claim_id"],"scene_id":row["scene"],
            "subject_scope":row["subject_scope"],"subject_id":row["subject_id"],
            "fact_id":row["fact"],"story_from":row["story_from"],
            "story_until":row["story_until"],
            "knowledge_state":row["knowledge_state"],
            "evidence_event_id":row["evidence_event"],
            "supersedes_id":row["supersedes_id"],
        }

    def _verify_claim_row(self,row):
        need(digest(canonical(self._claim_as_record(row))) == row["claim_sha"],
             "FACT_TEMPORAL_STORED_CLAIM_TAMPERED")
        event = self.db.execute(
            "SELECT * FROM fact_events WHERE event_id=?",
            (row["evidence_event"],)).fetchone()
        need(event is not None, "FACT_TEMPORAL_SOURCE_EVENT_LOST")
        self._assert_record_integrity(event)

    def temporal_view(self, *, scene: str, scope: str, subject: str,
                      fact: str, story_tick: int,
                      as_of_recorded_seq: int | None = None):
        """Reconstruct what records claimed at two independent time axes.

        Story time != file/import order != chapter-reading order. Does NOT
        interpret prose or infer a character actually knows a fact.
        """
        need(all(key(v) for v in (scene,subject,fact)),
             "FACT_TEMPORAL_QUERY_ID_INVALID")
        need(scope in ("ACTOR","READER"),"FACT_TEMPORAL_QUERY_SCOPE_INVALID")
        need(type(story_tick) is int and 0 <= story_tick <= 10000000,
             "FACT_TEMPORAL_QUERY_TIME_INVALID")
        need(as_of_recorded_seq is None or (
            type(as_of_recorded_seq) is int and as_of_recorded_seq >= 0),
            "FACT_TEMPORAL_QUERY_AS_OF_INVALID")
        if as_of_recorded_seq is None:
            as_of_recorded_seq = self.db.execute(
                "SELECT COALESCE(MAX(recorded_seq),0) FROM temporal_claims"
            ).fetchone()[0]
        matches = self.db.execute(
            "SELECT * FROM temporal_claims WHERE scene=? AND "
            "subject_scope=? AND subject_id=? AND fact=? AND "
            "story_from<=? AND (story_until IS NULL OR story_until>?) AND "
            "recorded_seq<=? ORDER BY recorded_seq LIMIT 65",
            (scene,scope,subject,fact,story_tick,story_tick,
             as_of_recorded_seq)).fetchall()
        need(len(matches) <= 64, "FACT_TEMPORAL_QUERY_BUDGET_EXCEEDED")
        for claim in matches: self._verify_claim_row(claim)
        superseded = {x["supersedes_id"] for x in matches if x["supersedes_id"]}
        active = [x for x in matches if x["claim_id"] not in superseded]
        states = {x["knowledge_state"] for x in active}
        if len(states)>1 or "DISPUTED" in states:
            resolution = "CONFLICT_UNRESOLVED"
        elif len(states)==1:
            resolution = next(iter(states))
        else:
            resolution = "UNRECORDED"
        return {
            "format":"writerforge.v55-bitemporal-knowledge.v1",
            "scene_id":scene,"scope":scope,"subject_id":subject,"fact_id":fact,
            "story_tick":story_tick,
            "as_of_recorded_seq":as_of_recorded_seq,
            "state":resolution,
            "active_claim_ids":[x["claim_id"] for x in active],
            "superseded_claim_ids":sorted(superseded),
            "story_truth_verified":False,
            "reviewer_authenticity_verified":False,
            "language_model_calls":0,
            "eligible_to_direct_writing":False,
        }

    def graph_neighbors(self,event_id: str, *, depth: int = 2):
        """Bounded fact-event adjacency; potential causality NEVER proof."""
        need(key(event_id),"FACT_GRAPH_EVENT_ID_INVALID")
        need(type(depth) is int and 1<=depth<=3,
             "FACT_GRAPH_DEPTH_INVALID")
        source=self.db.execute(
            "SELECT * FROM fact_events WHERE event_id=?",(event_id,)
        ).fetchone()
        need(source is not None,"FACT_GRAPH_SOURCE_EVENT_MISSING")
        self._assert_record_integrity(source)
        frontier={event_id}
        seen={event_id}
        links=[]
        for _ in range(depth):
            new=set()
            for node in sorted(frontier):
                rows=self.db.execute(
                    "SELECT * FROM fact_links WHERE source_event=? "
                    "OR target_event=? ORDER BY link_sha LIMIT 49",(node,node)
                ).fetchall()
                need(len(rows)<=48,"FACT_GRAPH_EDGE_QUERY_BUDGET_EXCEEDED")
                for edge in rows:
                    proof = digest(canonical({
                        "source":edge["source_event"],
                        "target":edge["target_event"],
                        "relation":edge["relation"]}))
                    need(proof==edge["link_sha"],
                         "FACT_GRAPH_RELATION_TAMPERED")
                    counterpart = (edge["target_event"] if
                                   edge["source_event"]==node else edge["source_event"])
                    record=self.db.execute(
                        "SELECT * FROM fact_events WHERE event_id=?",
                        (counterpart,)).fetchone()
                    need(record is not None,"FACT_GRAPH_LINK_TO_MISSING_EVENT")
                    self._assert_record_integrity(record)
                    need(record["scene"]==source["scene"],
                         "FACT_GRAPH_CROSS_SCENE_RELATION")
                    if not any(v["link_sha256"]==edge["link_sha"] for v in links):
                        links.append({"link_sha256":edge["link_sha"],
                                      "from":edge["source_event"],
                                      "to":edge["target_event"],
                                      "relation":edge["relation"],
                                      "relation_semantics_verified":False})
                    if counterpart not in seen:
                        new.add(counterpart)
            seen |= new
            frontier=new
            need(len(seen)<=64 and len(links)<=64,
                 "FACT_GRAPH_NEIGHBORHOOD_TOO_LARGE")
            if not frontier: break
        return {"format":"writerforge.v55-event-graph-neighborhood.v1",
                "root_event_id":event_id,"visited_event_ids":sorted(seen),
                "relations":links,"relation_count":len(links),
                "narrative_causality_verified":False,
                "model_calls":0,"prose_included":False}
