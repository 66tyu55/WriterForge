"""V89 append-only mechanical source-anchor failures using existing WF SQLite.

A record is created ONLY by re-running the genuine source validator against
the actual visible units. A caller cannot submit a made-up failure code or
self-assign an independent literary NEGATIVE verdict. Signed V86 semantic
reviews remain separate from this mechanical QA journal.

No copyrighted text or model answer is persisted: only hashes, scope IDs,
contract version and bounded machine code. Explicit LEARN mode is required.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
import sqlite3

from .runtime import Mode,RuntimeEngine
from .db import WriterForgeDB
from .v88_frozen_blind_exam import validate_wf_answer,WF88BlindError,canonical
from .v89_source_anchor_gate import (
    resolve_quote_only_answer,WF89AnchorError,_visible_attested,valid_sha,
)

ID=re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,79}\Z")
CODE=re.compile(r"(?:WF88|WF89)_[A-Z0-9_]{1,130}\Z")
CONTRACTS=frozenset(("LEGACY_V88_OFFSETS","V89_QUOTE_ONLY"))
ARMS=frozenset(("baseline","experience"))
CATEGORIES=frozenset(("历史","科幻","仙侠"))
MAX_PAGE=64


class V89FailureJournalError(ValueError):
    pass


def require(ok,code):
    if not ok: raise V89FailureJournalError(code)


def digest(obj):
    return sha256(canonical(obj)).hexdigest()


class V89FailureJournal:
    def __init__(self,db:WriterForgeDB,runtime:RuntimeEngine):
        require(isinstance(db,WriterForgeDB) and
                isinstance(runtime,RuntimeEngine),
                "WF89_TYPED_EXISTING_DB_AND_RUNTIME_REQUIRED")
        self.db=db
        self.runtime=runtime

    def _ensure_source(self,*,source_sha256,pinned_visible_unit_sha256,
                       visible_units):
        require(valid_sha(source_sha256),
                "WF89_ORIGINAL_SOURCE_SHA_INVALID")
        _visible_attested(visible_units,pinned_visible_unit_sha256)

    @staticmethod
    def _body(*,run_id,raw_answer,source_sha256,genre_hint,arm,
              failure_contract,failure_code):
        require(isinstance(run_id,str) and ID.fullmatch(run_id),
                "WF89_FAILURE_RUN_ID_INVALID")
        require(valid_sha(source_sha256) and
                genre_hint in CATEGORIES and arm in ARMS and
                failure_contract in CONTRACTS and
                isinstance(failure_code,str) and
                CODE.fullmatch(failure_code) is not None,
                "WF89_FAILURE_RECEIPT_FIELDS_INVALID")
        require(isinstance(raw_answer,dict) and
                len(canonical(raw_answer))<=10000,
                "WF89_FAILURE_RAW_MODEL_INPUT_UNBOUNDED")
        return {
            "run_id":run_id,
            "original_answer_sha256":sha256(canonical(raw_answer)).hexdigest(),
            "source_sha256":source_sha256,
            "genre_hint":genre_hint,
            "arm":arm,
            "failure_contract":failure_contract,
            "failure_code":failure_code,
        }

    def capture_v88_failure(self,*,run_id,raw_answer,visible_units,
                            pinned_visible_unit_sha256,
                            source_sha256,genre_hint,arm):
        """Reverify old exact-offset contract; old failure cannot be cured.

        A retrospective 'host could locate quote' is not a modification of
        the old V88 answer and cannot erase this receipt.
        """
        self.runtime.require(Mode.LEARN)
        self._ensure_source(
            source_sha256=source_sha256,
            pinned_visible_unit_sha256=pinned_visible_unit_sha256,
            visible_units=visible_units)
        try:
            validate_wf_answer(raw_answer,visible_units=visible_units)
        except WF88BlindError as error:
            code=str(error)
        else:
            raise V89FailureJournalError(
                "WF89_VALID_V88_ANSWER_CANNOT_BE_RECORDED_AS_FAILURE")
        return self._insert(self._body(
            run_id=run_id,raw_answer=raw_answer,source_sha256=source_sha256,
            genre_hint=genre_hint,arm=arm,
            failure_contract="LEGACY_V88_OFFSETS",
            failure_code=code))

    def capture_v89_failure(self,*,run_id,raw_answer,visible_units,
                            pinned_visible_unit_sha256,
                            original_source_sha256,
                            frozen_fragment_sha256,
                            sealed_future_unit_sha256,genre_hint,arm):
        self.runtime.require(Mode.LEARN)
        try:
            resolve_quote_only_answer(
                raw_answer,visible_units=visible_units,
                pinned_visible_unit_sha256=pinned_visible_unit_sha256,
                original_source_sha256=original_source_sha256,
                frozen_fragment_sha256=frozen_fragment_sha256,
                sealed_future_unit_sha256=sealed_future_unit_sha256)
        except WF89AnchorError as error:
            code=str(error)
            # A changed source pin is an infra integrity failure, not an
            # error of the WF student's literary analysis. Stop, don't
            # contaminate its error statistics or future learning.
            require(code not in (
                "WF89_VISIBLE_SOURCE_CHANGED_FROM_COLD_PIN",
                "WF89_PINNED_VISIBLE_SHA_MISSING",
                "WF89_TRUSTED_SOURCE_BINDING_INVALID",
                "WF89_TWO_BOUNDED_VISIBLE_SOURCE_UNITS_REQUIRED"),
                "WF89_INFRA_SOURCE_FAULT_NOT_STUDENT_ERROR")
        else:
            raise V89FailureJournalError(
                "WF89_VALID_SOURCE_CANDIDATE_CANNOT_BE_MARKED_FAILED")
        return self._insert(self._body(
            run_id=run_id,raw_answer=raw_answer,
            source_sha256=original_source_sha256,
            genre_hint=genre_hint,arm=arm,
            failure_contract="V89_QUOTE_ONLY",
            failure_code=code))

    def _insert(self,body):
        # The only write is a fixed bounded source-free receipt under
        # existing WriterForgeDB. Never touch the old R2/CAS event archive.
        h=digest(body)
        key=(body["run_id"],body["original_answer_sha256"])
        conn=self.db.conn
        with conn:
            old=conn.execute(
                "SELECT * FROM wf_anchor_failure_receipts "
                "WHERE run_id=? AND original_answer_sha256=?",
                key).fetchone()
            if old is not None:
                prior={k:old[k] for k in body}
                require(prior==body and old["receipt_sha256"]==h,
                        "WF89_FAILURE_IMMUTABLE_REPLAY_MISMATCH")
                return {**body,"receipt_sha256":h,"replayed":True,
                        "source_prose_stored":False,
                        "authoritative_literary_review":False}
            try:
                conn.execute(
                    "INSERT INTO wf_anchor_failure_receipts("
                    "run_id,original_answer_sha256,source_sha256,"
                    "genre_hint,arm,failure_contract,failure_code,"
                    "receipt_sha256) VALUES(?,?,?,?,?,?,?,?)",
                    tuple(body[k] for k in (
                        "run_id","original_answer_sha256","source_sha256",
                        "genre_hint","arm","failure_contract",
                        "failure_code","receipt_sha256"))+(h,))
            except sqlite3.IntegrityError as exc:
                raise V89FailureJournalError(
                    "WF89_FAILURE_CONCURRENT_WRITE_CONFLICT") from exc
        return {**body,"receipt_sha256":h,"replayed":False,
                "source_prose_stored":False,
                "authoritative_literary_review":False}

    def read(self,*,run_id,original_answer_sha256):
        require(isinstance(run_id,str) and ID.fullmatch(run_id)
                and valid_sha(original_answer_sha256),
                "WF89_FAILURE_LOOKUP_INVALID")
        row=self.db.conn.execute(
            "SELECT * FROM wf_anchor_failure_receipts "
            "WHERE run_id=? AND original_answer_sha256=?",
            (run_id,original_answer_sha256)).fetchone()
        require(row is not None,"WF89_FAILURE_RECEIPT_MISSING")
        payload={k:row[k] for k in (
            "run_id","original_answer_sha256","source_sha256",
            "genre_hint","arm","failure_contract","failure_code")}
        require(row["receipt_sha256"]==digest(payload),
                "WF89_FAILURE_RECEIPT_CORRUPTED")
        return {**payload,"receipt_sha256":row["receipt_sha256"],
                "eligible_for_WF_write":False,
                "may_be_imported_as_V86_independent_review":False,
                "literary_quality_independently_verified":False}

    def bounded_page(self,*,run_id,limit=MAX_PAGE):
        require(isinstance(run_id,str) and ID.fullmatch(run_id) and
                type(limit) is int and 1<=limit<=MAX_PAGE,
                "WF89_FAILURE_PAGE_BUDGET_INVALID")
        rows=self.db.conn.execute(
            "SELECT original_answer_sha256 FROM wf_anchor_failure_receipts "
            "WHERE run_id=? ORDER BY original_answer_sha256 LIMIT ?",
            (run_id,limit+1)).fetchall()
        require(len(rows)<=limit,"WF89_FAILURE_PAGE_MORE_RECORDS_UNREAD")
        return [self.read(
            run_id=run_id,original_answer_sha256=x[0]) for x in rows]
