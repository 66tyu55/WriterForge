"""V28 offline, immutable candidate ledger from a previously saved private A/B receipt.

No model, network, R2 upload, copied novel, draft, model reason, or promotion
path exists in this module. A model-only score is never human validation.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import re
import sqlite3

from .reverse_mechanism_boundary import TECHNIQUES

SHA = re.compile(r"[0-9a-f]{64}\Z")
SAFE_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}\Z")
DIMENSIONS = ("perception", "causality", "information", "continuity", "language")
MAX_TRIALS = 128
QUALITY_REFERENCE = 90  # diagnostic gap, NOT an automatic literary pass line


class CandidateEvidenceError(ValueError):
    pass


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _hash(value: str) -> str:
    if not isinstance(value, str) or SHA.fullmatch(value) is None:
        raise CandidateEvidenceError("invalid SHA256 provenance")
    return value


def derive_unverified_candidates(receipt: dict, *, receipt_sha256: str) -> dict:
    """Turn an existing *verified-by-content-hash* A/B report into numeric facts.

    The caller must obtain the receipt from a previously saved source (e.g.
    private R2 fresh GET), not pass a score copied from a conversation.
    This validates a snapshot's bytes, NOT the truth of its model judgements.
    """
    _hash(receipt_sha256)
    if not isinstance(receipt, dict) or sha256(_canonical(receipt)).hexdigest() != receipt_sha256:
        raise CandidateEvidenceError("report digest does not match immutable receipt")
    if (receipt.get("format") != "writerforge.cloud-ab-v1"
        or receipt.get("writer_prompt_source_prose_or_plot") is not False
        or type(receipt.get("drafts_retained")) is not bool
        or receipt.get("second_unit_unlocked") is not False
        or receipt.get("core_automatically_promoted") is not False
        or receipt.get("human_blind_review_performed") is not False):
        raise CandidateEvidenceError("report is not a source-isolated unpromoted model A/B")
    # Legacy v4 reports predate the critic-source separation patch. Keep them
    # as historical observations but never retrofit them to 'critic source-blind'.
    critic_source_blind = receipt.get("critic_prompt_original_source_prose")
    if critic_source_blind not in (None, False):
        raise CandidateEvidenceError("critic original-source provenance inconsistent")
    work = receipt.get("source_work")
    if not isinstance(work, str) or SAFE_ID.fullmatch(work) is None:
        raise CandidateEvidenceError("unbounded source work identifier")
    edition = _hash(receipt.get("edition_sha256"))
    unit = _hash(receipt.get("source_unit_sha256"))
    roles = receipt.get("roles")
    if not isinstance(roles, dict) or not isinstance(roles.get("writer"), dict):
        raise CandidateEvidenceError("writer identity is missing")
    writer_model = roles["writer"].get("model")
    if not isinstance(writer_model, str) or SAFE_ID.fullmatch(writer_model) is None:
        raise CandidateEvidenceError("unsafe writer identity")
    gate = receipt.get("length_gate")
    comps = receipt.get("comparisons")
    if not isinstance(gate, dict) or not isinstance(comps, dict) or set(comps) != {"baseline", "skill"}:
        raise CandidateEvidenceError("missing comparable A/B")
    if gate.get("comparable") is not True or gate.get("max_relative_difference") != 0.15:
        raise CandidateEvidenceError("A/B was not comparably length-gated")
    counts = []
    scores = {}
    for label in ("baseline", "skill"):
        comparison = comps[label]
        if not isinstance(comparison, dict):
            raise CandidateEvidenceError("invalid comparison entry")
        chars = comparison.get("draft_chars")
        if type(chars) is not int or not 220 <= chars <= 4500:
            raise CandidateEvidenceError("invalid draft length")
        counts.append(chars)
        _hash(comparison.get("draft_sha256"))
        breakdown = comparison.get("dimension_review")
        if not isinstance(breakdown, dict) or set(breakdown) != set(DIMENSIONS):
            raise CandidateEvidenceError("incomplete review dimensions")
        scores[label] = {}
        for dimension in DIMENSIONS:
            item = breakdown[dimension]
            if not isinstance(item, dict):
                raise CandidateEvidenceError("invalid review")
            number = item.get("score")
            if type(number) is not int or not 0 <= number <= 100:
                raise CandidateEvidenceError("invalid score")
            scores[label][dimension] = number
        if comparison.get("model_critic_score_unverified") != sum(scores[label].values()) // 5:
            raise CandidateEvidenceError("review mean mismatch")
    encrypted_evidence=receipt.get("private_encrypted_manuscript_evidence")
    retained=receipt["drafts_retained"]
    if retained:
        if (not isinstance(encrypted_evidence,dict)
            or encrypted_evidence.get("format")!="writerforge.private-draft-receipt.v1"
            or encrypted_evidence.get("encrypted") is not True
            or encrypted_evidence.get("source_or_draft_plaintext_in_report") is not False
            or encrypted_evidence.get("retention_needs_explicit_cleanup") is not True
            or encrypted_evidence.get("source_unit_sha256")!=unit
            or encrypted_evidence.get("draft_sha256")!={key:comps[key]["draft_sha256"]
                                                      for key in ("baseline","skill")}
            or not isinstance(encrypted_evidence.get("receipt_sha256"),str)
            or not SHA.fullmatch(encrypted_evidence["receipt_sha256"])
            or not isinstance(encrypted_evidence.get("task_sha256"),str)
            or not SHA.fullmatch(encrypted_evidence["task_sha256"])
            or encrypted_evidence.get("task_sha256")!=receipt.get("writing_task_sha256")
            or type(encrypted_evidence.get("expires_unix")) is not int):
            raise CandidateEvidenceError("private manuscript evidence not integrity-linked")
    elif encrypted_evidence is not None:
        raise CandidateEvidenceError("unexpected encrypted draft evidence in legacy record")
    if (gate.get("baseline_chars"), gate.get("skill_chars")) != tuple(counts):
        raise CandidateEvidenceError("length provenance mismatch")
    if abs(counts[0]-counts[1]) / max(counts) > 0.15:
        raise CandidateEvidenceError("actual texts exceed length comparison gate")
    selections = receipt.get("planner_mechanisms_unreviewed")
    if not isinstance(selections, list) or not 1 <= len(selections) <= 2:
        raise CandidateEvidenceError("missing selected mechanisms")
    mechanism_ids = []
    for item in selections:
        name = item.get("technique_id") if isinstance(item, dict) else None
        if name not in TECHNIQUES or name in mechanism_ids:
            raise CandidateEvidenceError("unexpected or repeated mechanism")
        mechanism_ids.append(name)
    faults = []
    deltas = {}
    for name in DIMENSIONS:
        delta = scores["skill"][name] - scores["baseline"][name]
        deltas[name] = delta
        if scores["skill"][name] < QUALITY_REFERENCE:
            faults.append({"type": "BELOW_REFERENCE_CANDIDATE",
                           "dimension": name,
                           "gap": QUALITY_REFERENCE - scores["skill"][name]})
        if delta < 0:
            faults.append({"type": "MODEL_RATED_REGRESSION_CANDIDATE",
                           "dimension": name, "gap": -delta})
    # Only host IDs and numerical facts persist. Model-generated explanations,
    # quotations, scene details and source paragraph locations do not.
    result = {
        "format": "writerforge.reverse-ab-candidates.v1",
        "receipt_sha256": receipt_sha256,
        "work": work, "edition_sha256": edition, "unit_sha256": unit,
        "writer_model": writer_model,
        "critic_source_blind": critic_source_blind is False,
        "future_drafts_reviewable_with_separate_key":retained,
        "encrypted_draft_receipt_sha256":(
            encrypted_evidence["receipt_sha256"] if retained else None),
        "draft_retention_does_not_verify_literary_quality":True,
        "ratings_provenance": "SINGLE_MODEL_UNCALIBRATED",
        "quality_reference_not_promotion": QUALITY_REFERENCE,
        "model_scores": scores, "model_deltas": deltas,
        "draft_chars": {"baseline": counts[0], "skill": counts[1]},
        "mechanism_hypotheses_unreviewed": sorted(mechanism_ids),
        "fault_candidates_unreviewed": faults,
        "forgetting": "NOT_TESTED",
        "closed_book_transfer_independent_scenes": 0,
        "human_review": "NOT_PERFORMED",
        "literary_mastery_verified": False,
        "first_window": "NOT_PASSED",
        "second_window": "LOCKED",
        "promotable": False,
    }
    if len(_canonical(result)) > 8192:
        raise CandidateEvidenceError("candidate summary is unbounded")
    return result


class OfflineCandidateLedger:
    """Explicit local-only SQLite store with exact-receipt idempotence.

    No background collector or network client. Never write this file into the
    original book library or treat its evidence count as passing 3->6->9.
    """
    def __init__(self, file: str | Path):
        self.path = Path(file)
        if str(self.path) == ":memory:":
            raise CandidateEvidenceError("dedicated durable ledger required")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path), timeout=5)
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.execute("""CREATE TABLE IF NOT EXISTS unverified_ab_trials(
            receipt_sha256 TEXT PRIMARY KEY,
            edition_sha256 TEXT NOT NULL,
            unit_sha256 TEXT NOT NULL,
            data_json TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status='CANDIDATE_NOT_PROMOTED')
        )""")
        self.db.commit()

    def add_receipt(self, receipt: dict, *, receipt_sha256: str) -> bool:
        result = derive_unverified_candidates(receipt, receipt_sha256=receipt_sha256)
        serialized = _canonical(result).decode("utf-8")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            found = self.db.execute(
                "SELECT data_json FROM unverified_ab_trials WHERE receipt_sha256=?",
                (receipt_sha256,)).fetchone()
            if found:
                if found[0] != serialized:
                    raise CandidateEvidenceError("immutable candidate receipt conflicts")
                self.db.commit()
                return False
            n = self.db.execute("SELECT COUNT(*) FROM unverified_ab_trials").fetchone()[0]
            if n >= MAX_TRIALS:
                raise CandidateEvidenceError("bounded candidate evidence capacity reached")
            self.db.execute(
                "INSERT INTO unverified_ab_trials VALUES(?,?,?,?,'CANDIDATE_NOT_PROMOTED')",
                (receipt_sha256, result["edition_sha256"], result["unit_sha256"], serialized))
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM unverified_ab_trials").fetchone()[0]

    def close(self):
        self.db.close()
