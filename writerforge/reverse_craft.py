"""V28 reverse-craft trial coordinator, fail-closed and source/draft isolated.

This is a stateful engineering kernel, not an LLM and not a 90%-literary score.
All scores must arrive from a separately configured, verified reviewer adapter.
Original novel text never enters this store. Draft/retest text never persists.
"""
from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import re
import shutil
import sqlite3
import time

WORK = "wudongqiankun"
EDITION = "86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28"
MAX_UNIT_DRAFT = 9000
MAX_NOTES = 350
MAX_UNITS = 18
MAX_CORES = 128
MAX_EVIDENCE = 512
MAX_ATTEMPTS = 3
MAX_MERGE_ATTEMPTS = 2
REQUIRED = ("perception", "causality", "information")
SAFE_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}\Z")
SHA = re.compile(r"[a-f0-9]{64}\Z")

SCHEMA = """
CREATE TABLE IF NOT EXISTS rc_meta (
  project TEXT PRIMARY KEY, work TEXT NOT NULL, edition TEXT NOT NULL,
  max_chapters INTEGER NOT NULL, max_units_per_chapter INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS rc_units (
  id INTEGER PRIMARY KEY, chapter INTEGER NOT NULL, ordinal INTEGER NOT NULL,
  anchor_hash TEXT NOT NULL, context_hash TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
  draft_hash TEXT, remote_hash TEXT, core_hash TEXT,
  UNIQUE(chapter,ordinal)
);
CREATE TABLE IF NOT EXISTS rc_attempts (
  unit_id INTEGER NOT NULL, attempt INTEGER NOT NULL, draft_hash TEXT NOT NULL,
  quality INTEGER, status TEXT NOT NULL, reviewer TEXT NOT NULL,
  faults TEXT NOT NULL, hypothesis TEXT NOT NULL,
  PRIMARY KEY(unit_id,attempt)
);
CREATE TABLE IF NOT EXISTS rc_cores (
  core_hash TEXT PRIMARY KEY, spec TEXT NOT NULL, tier TEXT NOT NULL DEFAULT 'candidate'
);
CREATE TABLE IF NOT EXISTS rc_evidence (
  core_hash TEXT NOT NULL, context_hash TEXT NOT NULL,
  unit_id INTEGER NOT NULL, PRIMARY KEY(core_hash,context_hash)
);
CREATE TABLE IF NOT EXISTS rc_merges (
  pair_start INTEGER PRIMARY KEY, status TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0, draft_hash TEXT, remote_hash TEXT
);
CREATE TABLE IF NOT EXISTS rc_events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, unit_id INTEGER,
  detail TEXT NOT NULL
);
"""


class ReverseCraftError(RuntimeError):
    pass


def _hash(data: str | bytes) -> str:
    return sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def _canon(doc) -> str:
    return json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _id(value: str) -> str:
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise ReverseCraftError("unsafe project identifier")
    return value


def _sha(value: str) -> str:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ReverseCraftError("missing SHA256 provenance")
    return value


def _note(value: str, field: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= MAX_NOTES:
        raise ReverseCraftError("unbounded or missing abstract " + field)
    return value.strip()


def _core(spec: dict) -> tuple[str, str]:
    if not isinstance(spec, dict) or set(spec) != {
        "problem", "trigger", "mechanism", "effect", "scope", "counterexample"
    }:
        raise ReverseCraftError("incomplete core mechanism")
    value = {key: _note(text, key) for key, text in spec.items()}
    raw = _canon(value)
    if len(raw) > 1600:
        raise ReverseCraftError("core too large")
    return _hash(raw), raw


class ReverseCraftCoordinator:
    """One-project, one-book coordinator. The caller owns the reviewer adapter.

    The reviewer must be out-of-band and verified by authority.verify(...).
    No authority -> REVIEW_BLOCKED. Synthetic authorities are valid ONLY in
    offline regression tests; never treat them as literary evidence.
    """
    def __init__(self, path: str | Path, project: str, *,
                 create: bool = False, max_chapters: int = 3,
                 max_units_per_chapter: int = 6, scratch: str | Path | None = None):
        self.project = _id(project)
        self.path = Path(path)
        if self.path == Path(":memory:"):
            raise ReverseCraftError("durable DB required, not :memory:")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA cache_size=-4096")
        self.conn.execute("PRAGMA temp_store=FILE")
        self.conn.executescript(SCHEMA)
        existing = self.conn.execute("SELECT * FROM rc_meta").fetchall()
        if create:
            if existing or not 1 <= max_chapters <= 3 or not 1 <= max_units_per_chapter <= 6:
                raise ReverseCraftError("existing project or unsafe max bounds")
            self.conn.execute(
                "INSERT INTO rc_meta VALUES(?,?,?,?,?)",
                (self.project, WORK, EDITION, max_chapters, max_units_per_chapter))
            self.conn.commit()
        elif len(existing) != 1 or existing[0]["project"] != self.project or (
            existing[0]["edition"] != EDITION or existing[0]["work"] != WORK
        ):
            raise ReverseCraftError("missing or mismatched pinned trial")
        self.scratch = Path(scratch) if scratch else self.path.parent / ".reverse-scratch"
        self.scratch.mkdir(parents=True, exist_ok=True)

    def close(self):
        self.conn.close()

    def _event(self, kind, unit_id, detail=""):
        self.conn.execute("INSERT INTO rc_events(kind,unit_id,detail) VALUES(?,?,?)",
                          (kind, unit_id, detail[:MAX_NOTES]))

    def _unit(self, unit_id):
        row = self.conn.execute("SELECT * FROM rc_units WHERE id=?", (unit_id,)).fetchone()
        if row is None:
            raise ReverseCraftError("unit not found")
        return row

    def open_unit(self, chapter: int, ordinal: int, anchor_hash: str,
                  context_hash: str) -> int:
        _sha(anchor_hash); _sha(context_hash)
        meta = self.conn.execute("SELECT * FROM rc_meta").fetchone()
        if not (type(chapter) is int and 1 <= chapter <= meta["max_chapters"] and
                type(ordinal) is int and 1 <= ordinal <= meta["max_units_per_chapter"]):
            raise ReverseCraftError("chapter or unit budget exceeded")
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            rows = self.conn.execute("SELECT * FROM rc_units ORDER BY id").fetchall()
            if len(rows) >= MAX_UNITS:
                raise ReverseCraftError("total source unit budget exhausted")
            if rows:
                previous = rows[-1]
                if previous["status"] != "PASS":
                    raise ReverseCraftError("previous unit has not passed")
                if len(rows) % 2 == 0:
                    pair = self.conn.execute(
                        "SELECT status FROM rc_merges WHERE pair_start=?", (previous["id"]-1,)
                    ).fetchone()
                    if not pair or pair[0] != "MERGED_PASS":
                        raise ReverseCraftError("two units require merged story pass")
                if (chapter, ordinal) <= (previous["chapter"], previous["ordinal"]):
                    raise ReverseCraftError("source units not ordered")
            cur = self.conn.execute(
                "INSERT INTO rc_units(chapter,ordinal,anchor_hash,context_hash,status) VALUES(?,?,?,?,'READY')",
                (chapter, ordinal, anchor_hash, context_hash))
            unit_id = int(cur.lastrowid)
            self._event("OPEN", unit_id)
            self.conn.commit()
            return unit_id
        except Exception:
            self.conn.rollback()
            raise

    @contextmanager
    def _ephemeral(self, prose: str):
        if not isinstance(prose, str) or not 100 <= len(prose) <= MAX_UNIT_DRAFT:
            raise ReverseCraftError("draft exceeds bounded short-term size")
        with TemporaryDirectory(prefix="rc-", dir=self.scratch) as folder:
            path = Path(folder) / "transient.txt"
            path.write_text(prose, encoding="utf-8")
            yield path
        # TemporaryDirectory removes the source on both success and exceptions.

    @staticmethod
    def _review(report, model_id: str, authority, *, transfer: bool) -> tuple[int, dict, str]:
        if authority is None or not callable(getattr(authority, "verify", None)):
            raise ReverseCraftError("REVIEW_BLOCKED: no independent authority")
        if not isinstance(report, dict) or not authority.verify(report):
            raise ReverseCraftError("REVIEW_BLOCKED: unverified reviewer receipt")
        if report.get("independent") is not True or report.get("copy_risk") is not False:
            raise ReverseCraftError("REVIEW_BLOCKED: independent/copy guard failed")
        reviewer = _id(report.get("reviewer", ""))
        if reviewer == model_id:
            raise ReverseCraftError("REVIEW_BLOCKED: model self-scoring disallowed")
        scores = report.get("dimensions")
        if not isinstance(scores, dict) or set(scores) != set(REQUIRED):
            raise ReverseCraftError("REVIEW_BLOCKED: missing required dimensions")
        if any(type(v) is not int or not 0 <= v <= 100 for v in scores.values()):
            raise ReverseCraftError("REVIEW_BLOCKED: scores invalid")
        score = report.get("transfer_score" if transfer else "quality_score")
        if type(score) is not int or not 0 <= score <= 100:
            raise ReverseCraftError("REVIEW_BLOCKED: invalid quality score")
        if not isinstance(report.get("blind"), bool) or report["blind"] is not True:
            raise ReverseCraftError("REVIEW_BLOCKED: blind comparison missing")
        # These are not evidence of real literary ability until the concrete
        # authority has been externally validated (not provided in V28 core).
        passed = score >= 90 and min(scores.values()) >= 85
        return score, {"passed": passed, "dimensions": scores}, reviewer

    def practice(self, unit_id: int, prose: str, *, writer: str, report: dict,
                 core: dict, fault: str, hypothesis: str, authority) -> str:
        writer = _id(writer)
        info = self._unit(unit_id)
        if info["status"] not in ("READY", "RETRY"):
            raise ReverseCraftError("unit state does not permit new attempt")
        if info["attempts"] >= MAX_ATTEMPTS:
            raise ReverseCraftError("attempt budget exhausted")
        key, core_raw = _core(core)
        fault, hypothesis = _note(fault, "fault"), _note(hypothesis, "hypothesis")
        # No persistent DB column holds prose. All reviewer work sees only the
        # ephemeral file and cannot mutate rc_core directly.
        with self._ephemeral(prose) as path:
            draft_hash = _hash(path.read_bytes())
            try:
                score, verdict, reviewer = self._review(report, writer, authority, transfer=False)
                new_status = "PERSIST_PENDING" if verdict["passed"] else (
                    "BLOCKED" if info["attempts"]+1 >= MAX_ATTEMPTS else "RETRY")
            except ReverseCraftError:
                score, reviewer, new_status = None, "unverified", "REVIEW_BLOCKED"
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                latest = self._unit(unit_id)
                if (latest["status"] != info["status"] or latest["attempts"] != info["attempts"]):
                    raise ReverseCraftError("concurrent attempt changed")
                self.conn.execute(
                    "INSERT INTO rc_attempts VALUES(?,?,?,?,?,?,?,?)",
                    (unit_id, info["attempts"]+1, draft_hash, score, new_status,
                     reviewer, fault, hypothesis))
                if new_status == "PERSIST_PENDING":
                    n = self.conn.execute("SELECT COUNT(*) FROM rc_cores").fetchone()[0]
                    if n >= MAX_CORES and not self.conn.execute(
                        "SELECT 1 FROM rc_cores WHERE core_hash=?", (key,)).fetchone():
                        raise ReverseCraftError("core cardinality exhausted")
                    self.conn.execute("INSERT OR IGNORE INTO rc_cores VALUES(?,?,'candidate')",
                                      (key, core_raw))
                self.conn.execute(
                    "UPDATE rc_units SET status=?,attempts=attempts+1,draft_hash=?,core_hash=? WHERE id=?",
                    (new_status, draft_hash,
                     key if new_status=="PERSIST_PENDING" else None, unit_id))
                self._event("ATTEMPT", unit_id, new_status)
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise
        return new_status

    def snapshot(self, *, unit_id: int | None = None,
                 target: str | None = None,
                 merge_id: int | None = None) -> bytes:
        """Canonical snapshot of the future committed state (no draft prose).

        When storing a checkpoint we stage the expected state before moving
        the local DB, so a clean R2 restore has PASS/MERGED_PASS too.
        """
        tables=("rc_meta","rc_units","rc_attempts","rc_cores","rc_evidence","rc_merges")
        result={"format":"writerforge.reverse-core.v1","project":self.project,
                "tables":{}}
        for table in tables:
            # This project DB is bounded by strict per-unit cardinality caps.
            rows=self.conn.execute("SELECT * FROM "+table+" ORDER BY rowid").fetchall()
            result["tables"][table]=[dict(row) for row in rows]
        if unit_id is not None:
            if target not in ("RETEST_READY","PASS"):
                raise ReverseCraftError("invalid prospective checkpoint state")
            unit=next((r for r in result["tables"]["rc_units"] if r["id"]==unit_id),None)
            if not unit:
                raise ReverseCraftError("prospective unit missing")
            expected=("PERSIST_PENDING" if target=="RETEST_READY"
                      else "RETEST_PERSIST_PENDING")
            if unit["status"]!=expected:
                raise ReverseCraftError("prospective checkpoint state differs")
            unit["status"]=target
            unit["remote_hash"]=None  # self-referential digest is impossible
            if target=="PASS":
                pairs=result["tables"]["rc_evidence"]
                if not any(r["core_hash"]==unit["core_hash"]
                           and r["context_hash"]==unit["context_hash"] for r in pairs):
                    pairs.append({"core_hash":unit["core_hash"],
                                  "context_hash":unit["context_hash"],"unit_id":unit_id})
                core=next(r for r in result["tables"]["rc_cores"]
                          if r["core_hash"]==unit["core_hash"])
                count=sum(r["core_hash"]==unit["core_hash"] for r in pairs)
                core["tier"]=("generalized_9" if count>=9 else
                               "retested_6" if count>=6 else
                               "recurrent_3" if count>=3 else "candidate")
        if merge_id is not None:
            if target!="MERGED_PASS" or unit_id is not None:
                raise ReverseCraftError("invalid prospective merged state")
            record=next((r for r in result["tables"]["rc_merges"]
                         if r["pair_start"]==merge_id),None)
            if record is None or record["status"]!="PERSIST_PENDING":
                raise ReverseCraftError("pending merge not found")
            record["status"]="MERGED_PASS"
            record["remote_hash"]=None
        encoded=_canon(result).encode("utf-8")
        if len(encoded)>512*1024:
            raise ReverseCraftError("core snapshot exceeds 512 KiB cap")
        return encoded

    @classmethod
    def restore_snapshot(cls, path: str | Path, project: str, payload: bytes,
                         *, scratch: str | Path | None = None):
        """Restore a verified payload into a NEW DB, without source/draft prose.

        Caller must first read/verify it through ReverseCoreVault; this method
        additionally validates format, pinned book and strict table keys.
        """
        target=Path(path)
        if target.exists():
            raise ReverseCraftError("refuse to overwrite an existing project DB")
        if not isinstance(payload,bytes) or len(payload)>512*1024:
            raise ReverseCraftError("invalid restore payload")
        try:
            data=json.loads(payload)
        except (ValueError,UnicodeError) as exc:
            raise ReverseCraftError("core payload is not JSON") from exc
        expected={"rc_meta","rc_units","rc_attempts","rc_cores","rc_evidence","rc_merges"}
        if (data.get("format")!="writerforge.reverse-core.v1" or
            data.get("project")!=_id(project) or
            set(data.get("tables",{}))!=expected):
            raise ReverseCraftError("invalid reverse core snapshot")
        info=data["tables"]["rc_meta"]
        if (len(info)!=1 or info[0].get("work")!=WORK
            or info[0].get("project")!=project or info[0].get("edition")!=EDITION):
            raise ReverseCraftError("reverse core edition mismatch")
        target.parent.mkdir(parents=True,exist_ok=True)
        conn=sqlite3.connect(str(target))
        try:
            conn.executescript(SCHEMA)
            conn.execute("BEGIN IMMEDIATE")
            for table in ("rc_meta","rc_units","rc_attempts","rc_cores",
                          "rc_evidence","rc_merges"):
                fields=[x[1] for x in conn.execute("PRAGMA table_info("+table+")")]
                rows=data["tables"][table]
                if not isinstance(rows,list) or len(rows)>MAX_EVIDENCE:
                    raise ReverseCraftError("oversized snapshot table")
                for record in rows:
                    if not isinstance(record,dict) or set(record)!=set(fields):
                        raise ReverseCraftError("invalid snapshot schema")
                    conn.execute("INSERT INTO "+table+"("+",".join(fields)+") VALUES("+
                        ",".join(["?"]*len(fields))+")", [record[k] for k in fields])
            conn.commit()
            if conn.execute("PRAGMA quick_check").fetchone()[0]!="ok":
                raise ReverseCraftError("restored core SQLite integrity failed")
        except Exception:
            conn.rollback()
            conn.close()
            target.unlink(missing_ok=True)
            raise
        conn.close()
        return cls(target,project,scratch=scratch)

    def checkpoint(self, unit_id: int, vault) -> str:
        row = self._unit(unit_id)
        if row["status"] not in ("PERSIST_PENDING", "RETEST_PERSIST_PENDING"):
            raise ReverseCraftError("not waiting for a durable checkpoint")
        target = "RETEST_READY" if row["status"]=="PERSIST_PENDING" else "PASS"
        payload = self.snapshot(unit_id=unit_id, target=target)
        snap_hash = _hash(payload)
        # A real implementation must fresh-download and verify returned bytes.
        receipt = vault.store_and_restore(payload, work=WORK, project=self.project, edition=EDITION)
        if receipt != snap_hash:
            raise ReverseCraftError("core remote checkpoint not independently verified")
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            latest = self._unit(unit_id)
            if latest["status"] != row["status"] or latest["attempts"] != row["attempts"]:
                raise ReverseCraftError("stale remote checkpoint; refusing adoption")
            self.conn.execute(
                "UPDATE rc_units SET status=?,remote_hash=? WHERE id=?",
                (target,snap_hash,unit_id))
            if target=="PASS":
                core_hash = latest["core_hash"]
                if not self.conn.execute(
                    "SELECT 1 FROM rc_evidence WHERE core_hash=? AND context_hash=?",
                    (core_hash, latest["context_hash"])).fetchone():
                    n=self.conn.execute("SELECT COUNT(*) FROM rc_evidence").fetchone()[0]
                    if n >= MAX_EVIDENCE:
                        raise ReverseCraftError("core evidence budget exhausted")
                    self.conn.execute(
                        "INSERT INTO rc_evidence VALUES(?,?,?)",
                        (core_hash, latest["context_hash"], unit_id))
                count = self.conn.execute("SELECT COUNT(*) FROM rc_evidence WHERE core_hash=?",
                                          (core_hash,)).fetchone()[0]
                tier=("generalized_9" if count>=9 else "retested_6" if count>=6
                      else "recurrent_3" if count>=3 else "candidate")
                self.conn.execute("UPDATE rc_cores SET tier=? WHERE core_hash=?",(tier,core_hash))
            self._event("CHECKPOINT",unit_id,target)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return target

    def retest(self, unit_id:int, unseen_prose:str, *, writer:str,
               report:dict, authority) -> str:
        row=self._unit(unit_id)
        if row["status"]!="RETEST_READY":
            raise ReverseCraftError("blind retest requires durable core and deleted draft")
        with self._ephemeral(unseen_prose) as path:
            _ = _hash(path.read_bytes())
            try:
                score, verdict, reviewer=self._review(report,_id(writer),authority,transfer=True)
                result="RETEST_PERSIST_PENDING" if verdict["passed"] else "BLOCKED"
            except ReverseCraftError:
                result="REVIEW_BLOCKED"
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                if self._unit(unit_id)["status"]!="RETEST_READY":
                    raise ReverseCraftError("stale retest")
                self.conn.execute("UPDATE rc_units SET status=? WHERE id=?",(result,unit_id))
                self._event("RETEST",unit_id,result)
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise
        return result

    def open_pair_merge(self, first_id:int) -> None:
        a,b=self._unit(first_id),self._unit(first_id+1)
        if (a["status"],b["status"])!=("PASS","PASS") or first_id%2!=1:
            raise ReverseCraftError("adjacent passed units required")
        if (a["chapter"],a["ordinal"])>(b["chapter"],b["ordinal"]):
            raise ReverseCraftError("merge chronology invalid")
        self.conn.execute(
            "INSERT INTO rc_merges VALUES(?,'READY',0,NULL,NULL)",(first_id,))
        self._event("MERGE_READY",first_id)
        self.conn.commit()

    def merge(self, first_id:int, text:str, *, writer:str,
              report:dict, authority, vault) -> str:
        row=self.conn.execute("SELECT * FROM rc_merges WHERE pair_start=?",
                              (first_id,)).fetchone()
        if row is None or row["status"] not in ("READY","RETRY"):
            raise ReverseCraftError("merge state invalid")
        if row["attempts"]>=MAX_MERGE_ATTEMPTS:
            raise ReverseCraftError("merge attempt cap exceeded")
        with self._ephemeral(text) as path:
            digest=_hash(path.read_bytes())
            try:
                _,verdict,_=self._review(report,_id(writer),authority,transfer=True)
                state="PERSIST_PENDING" if verdict["passed"] else (
                    "BLOCKED" if row["attempts"]+1>=MAX_MERGE_ATTEMPTS else "RETRY")
            except ReverseCraftError:
                state="REVIEW_BLOCKED"
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                latest=self.conn.execute(
                    "SELECT * FROM rc_merges WHERE pair_start=?", (first_id,)).fetchone()
                if latest["status"]!=row["status"] or latest["attempts"]!=row["attempts"]:
                    raise ReverseCraftError("concurrent merge mutation")
                self.conn.execute(
                    "UPDATE rc_merges SET status=?,attempts=attempts+1,draft_hash=? WHERE pair_start=?",
                    (state,digest,first_id))
                self._event("MERGE_ATTEMPT",first_id,state)
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise
        if state!="PERSIST_PENDING":
            return state
        payload=self.snapshot(merge_id=first_id,target="MERGED_PASS")
        h=_hash(payload)
        if vault.store_and_restore(payload,work=WORK,project=self.project,edition=EDITION)!=h:
            raise ReverseCraftError("merged checkpoint verification failed")
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            if self.conn.execute("SELECT status FROM rc_merges WHERE pair_start=?",
                                 (first_id,)).fetchone()[0]!="PERSIST_PENDING":
                raise ReverseCraftError("merge changed during backup")
            self.conn.execute(
                "UPDATE rc_merges SET status='MERGED_PASS',remote_hash=? WHERE pair_start=?",
                (h,first_id))
            self._event("MERGED_PASS",first_id)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return "MERGED_PASS"

    def inspect(self) -> dict:
        units = self.conn.execute(
            "SELECT id,chapter,ordinal,status,attempts,remote_hash FROM rc_units ORDER BY id"
        ).fetchall()
        merges = self.conn.execute("SELECT pair_start,status,attempts FROM rc_merges ORDER BY pair_start").fetchall()
        return {"project":self.project,"work":WORK,"units":[dict(x) for x in units],
                "merges":[dict(x) for x in merges],"literary_quality_verified":False,
                "real_model_called":False,"real_independent_reviewer_configured":False}

    def cleanup_stale_scratch(self, *, max_age_seconds: int = 3600) -> int:
        """Delete only owned scratch folders after checking age and symlink status."""
        if max_age_seconds < 60:
            raise ReverseCraftError("cleanup TTL too short")
        count=0
        now=time.time()
        for child in self.scratch.iterdir():
            if (not child.name.startswith("rc-") or child.is_symlink() or
                    not child.is_dir() or now-child.stat().st_mtime < max_age_seconds):
                continue
            # Only paths within the allocated scratch root are eligible.
            if child.resolve().parent != self.scratch.resolve():
                continue
            shutil.rmtree(child)
            count+=1
        return count
