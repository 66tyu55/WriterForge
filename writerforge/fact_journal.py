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
import base64
import hmac
import json
import os
import re
import secrets
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
    def __init__(self, file: str | Path, *,
                 trusted_disclosure_key: bytes | None = None):
        """No R2 access. Reader attestations need an OUT-OF-BAND verifier key.

        Never read a key from the SQLite database or from a caller's claim.
        Missing verification material fails closed for READER/KNOWN only.
        """
        if trusted_disclosure_key is None:
            configured = os.environ.get("WRITERFORGE_READER_VERIFY_KEY_HEX")
            if configured is not None:
                try:
                    trusted_disclosure_key = bytes.fromhex(configured)
                except ValueError as exc:
                    raise FactLedgerError("FACT_READER_VERIFY_KEY_INVALID") from exc
        need(trusted_disclosure_key is None or (
             isinstance(trusted_disclosure_key, bytes) and
             len(trusted_disclosure_key) >= 16),
             "FACT_READER_VERIFY_KEY_INVALID")
        self._trusted_disclosure_key = trusted_disclosure_key
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
        -- Enforce no-fork atomically across SQLite connections, not only
        -- via a check-then-insert preflight susceptible to writer races.
        CREATE UNIQUE INDEX IF NOT EXISTS temporal_single_successor
            ON temporal_claims(supersedes_id) WHERE supersedes_id IS NOT NULL;
        -- V57: explicit same-story identity; never infer from chapter names.
        CREATE TABLE IF NOT EXISTS story_scenes(
            scene_id TEXT PRIMARY KEY, story_id TEXT NOT NULL,
            chapter_index INTEGER NOT NULL, binding_sha TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS story_chapter_lookup
            ON story_scenes(story_id,chapter_index);
        -- V58: a scene-local label is NOT a global character identity.
        CREATE TABLE IF NOT EXISTS story_subjects(
            scene_id TEXT NOT NULL, subject_scope TEXT NOT NULL,
            subject_id TEXT NOT NULL, canonical_id TEXT NOT NULL,
            binding_sha TEXT NOT NULL,
            PRIMARY KEY(scene_id,subject_scope,subject_id));
        CREATE INDEX IF NOT EXISTS story_subject_lookup
            ON story_subjects(canonical_id,subject_scope);
        -- HMAC attestation comes from an external trusted verifier, not
        -- from a self-labelled REVEAL event or a sha string alone.
        CREATE TABLE IF NOT EXISTS reader_disclosures(
            event_id TEXT NOT NULL, reader_subject TEXT NOT NULL,
            disclosure_tick INTEGER NOT NULL, event_sha TEXT NOT NULL,
            signature TEXT NOT NULL, receipt_sha TEXT NOT NULL,
            PRIMARY KEY(event_id,reader_subject));
        -- Ingest sequence is distinct from fiction/story time.
        CREATE TABLE IF NOT EXISTS event_import_receipts(
            recorded_seq INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE, ingest_kind TEXT NOT NULL,
            event_sha TEXT NOT NULL);
        -- Private per-journal cursor signing secret; protects API clients
        -- from forging page offset. A DB owner can still alter the journal.
        CREATE TABLE IF NOT EXISTS journal_cursor_keys(
            key_id INTEGER PRIMARY KEY CHECK(key_id=1),
            secret_hex TEXT NOT NULL);
        """)
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO journal_cursor_keys VALUES(1,?)",
                (secrets.token_hex(32),))
        record=self.db.execute(
            "SELECT secret_hex FROM journal_cursor_keys WHERE key_id=1"
        ).fetchone()
        need(record is not None and isinstance(record[0],str) and
             SHA.fullmatch(record[0]) is not None,
             "FACT_TEMPORAL_CURSOR_KEY_INVALID")
        self._cursor_key=bytes.fromhex(record[0])
        self.db.commit()

    def close(self):
        self.db.close()

    def register_scene(self, *, story_id: str, scene_id: str,
                       chapter_index: int):
        """Explicit binding, not an inference from strings or lexical hits."""
        need(key(story_id) and key(scene_id) and
             type(chapter_index) is int and 0 <= chapter_index <= 10000000,
             "FACT_STORY_BINDING_INVALID")
        binding = canonical({"story_id": story_id, "scene_id": scene_id,
                             "chapter_index": chapter_index})
        proof = digest(binding)
        prior = self.db.execute(
            "SELECT * FROM story_scenes WHERE scene_id=?", (scene_id,)
        ).fetchone()
        if prior:
            self._verify_story_binding(prior)
            need(prior["binding_sha"] == proof, "FACT_STORY_BINDING_IMMUTABLE")
            return {"binding_sha256": proof, "replayed": True}
        with self.db:
            self.db.execute(
                "INSERT INTO story_scenes VALUES(?,?,?,?)",
                (scene_id, story_id, chapter_index, proof))
        return {"binding_sha256": proof, "replayed": False}

    @staticmethod
    def _verify_story_binding(row):
        proof = digest(canonical({
            "story_id": row["story_id"], "scene_id": row["scene_id"],
            "chapter_index": row["chapter_index"]}))
        need(proof == row["binding_sha"], "FACT_STORY_BINDING_TAMPERED")

    def _bound_story(self, scene):
        row = self.db.execute(
            "SELECT * FROM story_scenes WHERE scene_id=?", (scene,)
        ).fetchone()
        if row:
            self._verify_story_binding(row)
            return row["story_id"]
        return None

    def _same_story(self, left_scene, right_scene):
        if left_scene == right_scene:
            return True
        left = self._bound_story(left_scene)
        right = self._bound_story(right_scene)
        return left is not None and left == right

    def bind_subject(self, *, scene_id: str, scope: str,
                     subject_id: str, canonical_id: str):
        """Immutable explicit identity binding, never inferred from a name."""
        need(all(key(v) for v in (scene_id, subject_id, canonical_id)) and
             scope in ("ACTOR", "READER"), "FACT_SUBJECT_BINDING_INVALID")
        need(self._bound_story(scene_id) is not None,
             "FACT_SUBJECT_SCENE_NOT_REGISTERED")
        row = {"scene_id":scene_id,"subject_scope":scope,
               "subject_id":subject_id,"canonical_id":canonical_id}
        h = digest(canonical(row))
        prior = self.db.execute(
            "SELECT * FROM story_subjects WHERE scene_id=? AND "
            "subject_scope=? AND subject_id=?",
            (scene_id,scope,subject_id)).fetchone()
        if prior:
            self._verify_subject_binding(prior)
            need(prior["binding_sha"] == h, "FACT_SUBJECT_IDENTITY_IMMUTABLE")
            return {"binding_sha256":h,"replayed":True}
        with self.db:
            self.db.execute(
                "INSERT INTO story_subjects VALUES(?,?,?,?,?)",
                (scene_id,scope,subject_id,canonical_id,h))
        return {"binding_sha256":h,"replayed":False}

    @staticmethod
    def _verify_subject_binding(row):
        record = {"scene_id":row["scene_id"],
                  "subject_scope":row["subject_scope"],
                  "subject_id":row["subject_id"],
                  "canonical_id":row["canonical_id"]}
        need(digest(canonical(record)) == row["binding_sha"],
             "FACT_SUBJECT_IDENTITY_TAMPERED")

    def _bound_subject(self, scene, scope, subject):
        row = self.db.execute(
            "SELECT * FROM story_subjects WHERE scene_id=? AND "
            "subject_scope=? AND subject_id=?",(scene,scope,subject)
        ).fetchone()
        if row:
            self._verify_subject_binding(row)
            return row["canonical_id"]
        return None

    @staticmethod
    def _disclosure_payload(event, reader_subject, disclosure_tick):
        return {"event_id":event["event_id"],
                "event_sha256":event["event_sha"],
                "reader_subject":reader_subject,
                "disclosure_tick":disclosure_tick}

    def _check_disclosure_signature(self, event, reader_subject,
                                    disclosure_tick, signature):
        need(self._trusted_disclosure_key is not None,
             "FACT_READER_ATTESTATION_KEY_MISSING")
        need(isinstance(signature,str) and
             SHA.fullmatch(signature) is not None,
             "FACT_READER_ATTESTATION_SIGNATURE_INVALID")
        message = canonical(self._disclosure_payload(
            event,reader_subject,disclosure_tick)).encode("utf-8")
        expected = hmac.new(
            self._trusted_disclosure_key,message,"sha256").hexdigest()
        need(hmac.compare_digest(expected,signature),
             "FACT_READER_ATTESTATION_SIGNATURE_INVALID")

    def register_reader_disclosure(self, *, event_id: str,
                                   reader_subject: str,
                                   disclosure_tick: int,
                                   signature: str):
        """Accept externally signed metadata; never auto-certify prose truth."""
        need(key(event_id) and key(reader_subject) and
             type(disclosure_tick) is int and
             0 <= disclosure_tick <= 10000000,
             "FACT_READER_DISCLOSURE_SCHEMA_INVALID")
        ev = self.db.execute(
            "SELECT * FROM fact_events WHERE event_id=?",(event_id,)
        ).fetchone()
        need(ev is not None,"FACT_READER_DISCLOSURE_EVENT_MISSING")
        self._assert_record_integrity(ev)
        need(ev["state"] == "KNOWN" and
             (ev["role"] == "REVEAL" or (
                 ev["role"] == "OBSERVE" and ev["actor"] == "narrator")),
             "FACT_READER_DISCLOSURE_ROLE_NOT_PUBLIC")
        need(disclosure_tick >= ev["tick"],
             "FACT_READER_KNOWS_BEFORE_EVIDENCE_EVENT")
        self._check_disclosure_signature(
            ev,reader_subject,disclosure_tick,signature)
        receipt = {"event_id":event_id,"reader_subject":reader_subject,
                   "disclosure_tick":disclosure_tick,
                   "event_sha":ev["event_sha"],"signature":signature}
        h = digest(canonical(receipt))
        prior = self.db.execute(
            "SELECT * FROM reader_disclosures "
            "WHERE event_id=? AND reader_subject=?",
            (event_id,reader_subject)).fetchone()
        if prior:
            self._verify_reader_disclosure(ev,reader_subject,disclosure_tick)
            need(prior["receipt_sha"]==h,"FACT_READER_DISCLOSURE_IMMUTABLE")
            return {"receipt_sha256":h,"replayed":True,
                    "story_truth_verified":False}
        with self.db:
            self.db.execute(
                "INSERT INTO reader_disclosures VALUES(?,?,?,?,?,?)",
                (event_id,reader_subject,disclosure_tick,ev["event_sha"],
                 signature,h))
        return {"receipt_sha256":h,"replayed":False,
                "story_truth_verified":False}

    def _verify_reader_disclosure(self, ev, reader_subject, at_tick):
        row = self.db.execute(
            "SELECT * FROM reader_disclosures "
            "WHERE event_id=? AND reader_subject=?",
            (ev["event_id"],reader_subject)).fetchone()
        need(row is not None,"FACT_READER_ATTESTATION_REQUIRED")
        original = {"event_id":row["event_id"],
                    "reader_subject":row["reader_subject"],
                    "disclosure_tick":row["disclosure_tick"],
                    "event_sha":row["event_sha"],
                    "signature":row["signature"]}
        need(digest(canonical(original))==row["receipt_sha"] and
             ev["event_sha"] == row["event_sha"],
             "FACT_READER_ATTESTATION_TAMPERED")
        self._check_disclosure_signature(
            ev,reader_subject,row["disclosure_tick"],row["signature"])
        need(at_tick >= row["disclosure_tick"],
             "FACT_READER_KNOWS_BEFORE_DISCLOSURE")

    def append_flashback(self, item, *, story_id: str):
        """Explicit out-of-order ingestion; NEVER edits old events or story time.

        Requires a pre-registered chapter/story; ordinary append() keeps V54
        strict chronological behavior. SQLite ingest sequence is independent.
        """
        checked_event(item)
        need(key(story_id) and self._bound_story(item["scene_id"]) == story_id,
             "FACT_FLASHBACK_UNREGISTERED_STORY")
        record_sha = digest(canonical(item))
        existing = self.db.execute(
            "SELECT * FROM fact_events WHERE event_id=?",
            (item["event_id"],)).fetchone()
        if existing is not None:
            self._assert_record_integrity(existing)
            need(existing["event_sha"] == record_sha,
                 "FACT_IMMUTABLE_EVENT_REPLACEMENT_FORBIDDEN")
            receipt = self.db.execute(
                "SELECT recorded_seq FROM event_import_receipts WHERE event_id=?",
                (item["event_id"],)).fetchone()
            return {"event_id": item["event_id"],
                    "event_sha256": record_sha, "replayed": True,
                    "recorded_seq": receipt[0] if receipt else None,
                    "semantic_truth_proven": False}
        with self.db:
            self.db.execute(
                "INSERT INTO fact_events VALUES(?,?,?,?,?,?,?,?,?)",
                (item["event_id"],item["scene_id"],item["actor_id"],
                 item["fact_id"],item["tick"],item["state"],item["role"],
                 item["evidence_sha256"],record_sha))
            cursor = self.db.execute(
                "INSERT INTO event_import_receipts"
                "(event_id,ingest_kind,event_sha) VALUES(?,?,?)",
                (item["event_id"],"EXPLICIT_FLASHBACK",record_sha))
        return {"event_id": item["event_id"],"event_sha256": record_sha,
                "recorded_seq": cursor.lastrowid,"replayed": False,
                "semantic_truth_proven": False}

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
            self.db.execute(
                "INSERT INTO event_import_receipts"
                "(event_id,ingest_kind,event_sha) VALUES(?,?,?)",
                (item["event_id"],"NORMAL_APPEND",record_sha))
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
        need(self._same_story(source["scene"],target["scene"]),
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
            "SELECT * FROM temporal_claims WHERE claim_id=?",
            (record["claim_id"],)).fetchone()
        if existing:
            self._verify_claim_row(existing)
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
        if record["knowledge_state"] == "KNOWN":
            need(evidence["state"] == "KNOWN",
                 "FACT_KNOWLEDGE_UNSUPPORTED_BY_EVIDENCE")
        if record["subject_scope"] == "ACTOR":
            need(evidence["actor"] == record["subject_id"],
                 "FACT_ACTOR_KNOWLEDGE_EVIDENCE_MISMATCH")
            if record["knowledge_state"] == "KNOWN":
                need(begin >= evidence["tick"],
                     "FACT_ACTOR_KNOWS_BEFORE_EVIDENCE_EVENT")
        elif record["knowledge_state"] == "KNOWN":
            need(begin >= evidence["tick"],
                 "FACT_READER_KNOWS_BEFORE_EVIDENCE_EVENT")
            # A private THINK is not REVEAL, and self-labelled REVEAL is not
            # trusted unless an independent verifier signed the event digest.
            need(evidence["role"] == "REVEAL" or
                 (evidence["actor"] == "narrator" and
                  evidence["role"] == "OBSERVE"),
                 "FACT_READER_DISCLOSURE_REQUIRED")
            self._verify_reader_disclosure(
                evidence,record["subject_id"],begin)
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
        try:
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
        except sqlite3.IntegrityError as exc:
            raise FactLedgerError("FACT_TEMPORAL_CONCURRENT_WRITE_CONFLICT") from exc
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
        if row["subject_scope"] == "READER" and row["knowledge_state"] == "KNOWN":
            self._verify_reader_disclosure(
                event,row["subject_id"],row["story_from"])

    def _temporal_source(self, *, scene, scope, subject, fact, story_id):
        """Shared SQL filter: identical identity rules for views and pages."""
        if story_id is None:
            return ("FROM temporal_claims c WHERE c.scene=? AND "
                    "c.subject_scope=? AND c.subject_id=? AND c.fact=?",
                    [scene,scope,subject,fact])
        need(key(story_id) and self._bound_story(scene) == story_id,
             "FACT_TEMPORAL_STORY_SCOPE_NOT_REGISTERED")
        # Check complete scope bindings before projection; do not silently
        # trust a modified SHA in another chapter's local identity map.
        for row in self.db.execute(
                "SELECT * FROM story_scenes WHERE story_id=?",(story_id,)):
            self._verify_story_binding(row)
        for row in self.db.execute(
                "SELECT sb.* FROM story_subjects sb JOIN story_scenes sc "
                "ON sc.scene_id=sb.scene_id WHERE sc.story_id=?",
                (story_id,)):
            self._verify_subject_binding(row)
        canonical_id = self._bound_subject(scene,scope,subject)
        if canonical_id is None:
            # Fail closed: a matching local display name is not identity.
            return ("FROM temporal_claims c WHERE 0=1", [])
        return (
            "FROM temporal_claims c "
            "JOIN story_scenes sc ON sc.scene_id=c.scene "
            "JOIN story_subjects sb ON sb.scene_id=c.scene AND "
            "sb.subject_scope=c.subject_scope AND "
            "sb.subject_id=c.subject_id "
            "WHERE sc.story_id=? AND sb.canonical_id=? AND "
            "c.subject_scope=? AND c.fact=?",
            [story_id,canonical_id,scope,fact])

    @staticmethod
    def _temporal_query_validate(scene, scope, subject, fact, story_tick,
                                 as_of_recorded_seq):
        need(all(key(v) for v in (scene,subject,fact)),
             "FACT_TEMPORAL_QUERY_ID_INVALID")
        need(scope in ("ACTOR","READER"),"FACT_TEMPORAL_QUERY_SCOPE_INVALID")
        need(type(story_tick) is int and 0 <= story_tick <= 10000000,
             "FACT_TEMPORAL_QUERY_TIME_INVALID")
        need(as_of_recorded_seq is None or (
            type(as_of_recorded_seq) is int and as_of_recorded_seq >= 0),
            "FACT_TEMPORAL_QUERY_AS_OF_INVALID")

    def _recorded_snapshot(self, as_of_recorded_seq):
        if as_of_recorded_seq is None:
            return self.db.execute(
                "SELECT COALESCE(MAX(recorded_seq),0) FROM temporal_claims"
            ).fetchone()[0]
        return as_of_recorded_seq

    def temporal_view(self, *, scene: str, scope: str, subject: str,
                      fact: str, story_tick: int,
                      as_of_recorded_seq: int | None = None,
                      story_id: str | None = None):
        """Bounded complete state, independent story/recorded clocks.

        A cross-chapter identity must be explicitly bound in EACH chapter.
        Return a result only if every relevant claim was checked; otherwise
        raise instead of creating a false 'KNOWN' from an incomplete subset.
        """
        self._temporal_query_validate(
            scene,scope,subject,fact,story_tick,as_of_recorded_seq)
        as_of_recorded_seq=self._recorded_snapshot(as_of_recorded_seq)
        source, bind = self._temporal_source(
            scene=scene,scope=scope,subject=subject,
            fact=fact,story_id=story_id)
        query = (
            "SELECT c.*, EXISTS(SELECT 1 FROM temporal_claims successor "
            "WHERE successor.supersedes_id=c.claim_id AND "
            "successor.recorded_seq<=?) AS was_superseded " + source +
            " AND c.story_from<=? AND "
            "(c.story_until IS NULL OR c.story_until>?) "
            "AND c.recorded_seq<=? ORDER BY c.recorded_seq")
        cursor = self.db.execute(
            query,[as_of_recorded_seq,*bind,story_tick,story_tick,
                   as_of_recorded_seq])
        states=set()
        active_ids,superseded_ids=[],[]
        active_count=superseded_count=scanned=0
        while True:
            batch=cursor.fetchmany(64)
            if not batch:
                break
            scanned+=len(batch)
            need(scanned<=8192,"FACT_TEMPORAL_SCAN_BUDGET_EXCEEDED")
            for claim in batch:
                self._verify_claim_row(claim)
                if claim["was_superseded"]:
                    superseded_count+=1
                    if len(superseded_ids)<64:
                        superseded_ids.append(claim["claim_id"])
                else:
                    active_count+=1
                    states.add(claim["knowledge_state"])
                    if len(active_ids)<64:
                        active_ids.append(claim["claim_id"])
        if len(states)>1 or "DISPUTED" in states:
            resolution="CONFLICT_UNRESOLVED"
        elif len(states)==1:
            resolution=next(iter(states))
        else:
            resolution="UNRECORDED"
        return {
            "format":"writerforge.v58-bitemporal-knowledge.v1",
            "scene_id":scene,"story_id":story_id,
            "scope":scope,"subject_id":subject,"fact_id":fact,
            "story_tick":story_tick,"as_of_recorded_seq":as_of_recorded_seq,
            "state":resolution,
            "active_claim_ids":active_ids,
            "superseded_claim_ids":sorted(superseded_ids),
            "active_claim_count":active_count,
            "superseded_claim_count":superseded_count,
            "claim_count_examined":scanned,
            "active_claims_truncated":active_count>64,
            "superseded_claims_truncated":superseded_count>64,
            "story_truth_verified":False,
            "reviewer_authenticity_verified":False,
            "language_model_calls":0,"eligible_to_direct_writing":False,
        }

    def _cursor_tag(self, data):
        return hmac.new(
            self._cursor_key,canonical(data).encode("utf-8"),
            "sha256").hexdigest()

    def temporal_claim_page(self, *, scene: str, scope: str, subject: str,
                            fact: str, story_tick: int,
                            story_id: str | None = None,
                            as_of_recorded_seq: int | None = None,
                            limit: int = 64,
                            cursor: str | None = None):
        """Stable keyset replay of claim metadata, NOT a full state result.

        Output never includes the source text. A cursor is tied to the exact
        query, row limit and immutable recorded-sequence snapshot. Its HMAC
        prevents outside callers from forging offsets; it is NOT authorization,
        and anyone with raw SQLite write access controls the local journal.
        """
        self._temporal_query_validate(
            scene,scope,subject,fact,story_tick,as_of_recorded_seq)
        need(type(limit) is int and 1<=limit<=64,
             "FACT_TEMPORAL_PAGE_SIZE_INVALID")
        if story_id is not None:
            need(key(story_id),"FACT_TEMPORAL_STORY_SCOPE_NOT_REGISTERED")
        if cursor is not None:
            need(isinstance(cursor,str) and 0<len(cursor)<=2048,
                 "FACT_TEMPORAL_CURSOR_INVALID")
            try:
                token=json.loads(base64.urlsafe_b64decode(
                    cursor+"="*((-len(cursor))%4)).decode("utf-8"))
            except (ValueError,UnicodeError,TypeError) as exc:
                raise FactLedgerError("FACT_TEMPORAL_CURSOR_INVALID") from exc
            need(isinstance(token,dict) and set(token)=={
                 "v","fingerprint","last_seq","asof","tag"} and
                 type(token["v"]) is int and token["v"]==1 and
                 type(token["last_seq"]) is int and token["last_seq"]>=0 and
                 type(token["asof"]) is int and token["asof"]>=0 and
                 type(token["fingerprint"]) is str and
                 type(token["tag"]) is str,
                 "FACT_TEMPORAL_CURSOR_INVALID")
            prior_asof=token["asof"]
            need(as_of_recorded_seq is None or
                 as_of_recorded_seq==prior_asof,
                 "FACT_TEMPORAL_CURSOR_SNAPSHOT_MISMATCH")
            as_of_recorded_seq=prior_asof
            proof=self._cursor_tag({
                "v":1,"fingerprint":token["fingerprint"],
                "last_seq":token["last_seq"],"asof":prior_asof})
            need(hmac.compare_digest(proof,token["tag"]),
                 "FACT_TEMPORAL_CURSOR_INVALID")
            after_seq=token["last_seq"]
        else:
            as_of_recorded_seq=self._recorded_snapshot(as_of_recorded_seq)
            after_seq=0
        fingerprint=digest(canonical({
            "scene":scene,"scope":scope,"subject":subject,"fact":fact,
            "story_id":story_id,"story_tick":story_tick,
            "asof":as_of_recorded_seq,"limit":limit}))
        if cursor is not None:
            need(token["fingerprint"]==fingerprint,
                 "FACT_TEMPORAL_CURSOR_SCOPE_MISMATCH")
        source,bind=self._temporal_source(
            scene=scene,scope=scope,subject=subject,
            fact=fact,story_id=story_id)
        query=(
            "SELECT c.*, EXISTS(SELECT 1 FROM temporal_claims successor "
            "WHERE successor.supersedes_id=c.claim_id AND "
            "successor.recorded_seq<=?) AS was_superseded " + source +
            " AND c.story_from<=? AND "
            "(c.story_until IS NULL OR c.story_until>?) "
            "AND c.recorded_seq>? AND c.recorded_seq<=? "
            "ORDER BY c.recorded_seq LIMIT ?")
        rows=self.db.execute(
            query,[as_of_recorded_seq,*bind,story_tick,story_tick,
                   after_seq,as_of_recorded_seq,limit+1]).fetchall()
        page=rows[:limit]
        claims=[]
        for row in page:
            self._verify_claim_row(row)
            claims.append({
                "claim_id":row["claim_id"],
                "scene_id":row["scene"],
                "recorded_seq":row["recorded_seq"],
                "story_from":row["story_from"],
                "story_until":row["story_until"],
                "knowledge_state":row["knowledge_state"],
                "evidence_event_id":row["evidence_event"],
                "supersedes_id":row["supersedes_id"],
                "superseded_at_snapshot":bool(row["was_superseded"]),
                "claim_sha256":row["claim_sha"],
            })
        more=len(rows)>limit
        next_cursor=None
        if more:
            next_data={"v":1,"fingerprint":fingerprint,
                       "last_seq":page[-1]["recorded_seq"],
                       "asof":as_of_recorded_seq}
            next_data["tag"]=self._cursor_tag(next_data)
            next_cursor=base64.urlsafe_b64encode(
                canonical(next_data).encode("utf-8")).decode("ascii").rstrip("=")
        return {"format":"writerforge.v58-temporal-claim-page.v1",
                "story_id":story_id,"scene_id":scene,"scope":scope,
                "subject_id":subject,"fact_id":fact,"story_tick":story_tick,
                "as_of_recorded_seq":as_of_recorded_seq,
                "page_count":len(claims),"has_more":more,
                "next_cursor":next_cursor,"claims":claims,
                "literary_truth_verified":False,
                "source_text_included":False}

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
                    need(self._same_story(record["scene"],source["scene"]),
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
