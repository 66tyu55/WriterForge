"""V85 optional sealed-PASS-A -> literary-claim evidence bridge.

This reads the existing immutable R2-first-read chain and certified seal.
It refuses the historical V79 mixed chapter-1 pilot. It never regenerates
old model answers or invents missing exact source spans.

No paid calls. No R2 writes unless separately and explicitly calling
persist_sidecar on a non-read-only journal. Sidecars are CAS metadata only.
"""
from __future__ import annotations

from hashlib import sha256

from .r2_learn_journal import hexdigest
from .v85_literary_evidence_gate import (
    LiteraryEvidenceGate, LiteraryEvidenceError, canonical, is_sha,
)

FORMAT = "wf.learn.evidence-audit-sidecar.v85"


def need(ok, code):
    if not ok:
        raise LiteraryEvidenceError(code)


class V85SealedLearningBridge:
    def __init__(self, journal, gate: LiteraryEvidenceGate):
        need(isinstance(gate, LiteraryEvidenceGate),
             "WF_V85_GATE_REQUIRED")
        need(hasattr(journal, "fetch_event") and
             hasattr(journal, "_get_content"),
             "WF_V85_R2_READ_INTERFACE_REQUIRED")
        self.journal = journal
        self.gate = gate

    def audit_sealed_chapter(self, *, ident: dict, windows: tuple[str,...],
                             proposals: list):
        """Require every PASS-A event, source SHA, ordinal and final seal.

        PASS-A provenance is an engineering condition; semantic validity
        and real author-time remain unverified and ineligible for WRITE.
        """
        expected = {"source_key_sha256", "source_sha256",
                    "chapter", "chapter_body_sha256"}
        need(isinstance(ident, dict) and set(ident) == expected and
             is_sha(ident["source_key_sha256"]) and
             is_sha(ident["source_sha256"]) and
             is_sha(ident["chapter_body_sha256"]) and
             ident["source_sha256"] == self.gate.source_sha256 and
             type(ident["chapter"]) is int and ident["chapter"] >= 2,
             "WF_V85_IDENT_NOT_STRICT_CHAPTER")
        need(type(windows) is tuple and 2 <= len(windows) <= 80 and
             all(isinstance(w, str) and 30 <= len(w) <= 900
                 for w in windows) and
             hexdigest("".join(windows).encode("utf8")) ==
             ident["chapter_body_sha256"],
             "WF_V85_ORIGINAL_WINDOW_SOURCE_MISMATCH")
        previous = None
        for unit, text in enumerate(windows, 1):
            entry = self.journal.fetch_event(
                ident=ident, stage="first_read", unit=unit)
            need(isinstance(entry, dict) and
                 is_sha(entry.get("event_sha256")) and
                 isinstance(entry.get("doc"), dict),
                 "WF_V85_FIRST_READ_MISSING")
            row = entry["doc"]
            need(row.get("source_unit_sha256") ==
                 hexdigest(text.encode("utf8")) and
                 row.get("previous_event_sha256") == previous and
                 row.get("future_source_seen") is False and
                 row.get("chapter") == ident["chapter"] and
                 row.get("source_sha256") == ident["source_sha256"] and
                 row.get("chapter_body_sha256") ==
                 ident["chapter_body_sha256"],
                 "WF_V85_FIRST_READ_HASH_ORDER_OR_FUTURE_INVALID")
            previous = entry["event_sha256"]
        seal = self.journal.fetch_event(ident=ident, stage="seal")
        need(isinstance(seal,dict) and is_sha(seal.get("event_sha256"))
             and isinstance(seal.get("doc"),dict) and
             seal["doc"].get("units_read") == len(windows) and
             seal["doc"].get("last_first_read_sha256") == previous and
             seal["doc"].get("source_sha256") == ident["source_sha256"] and
             seal["doc"].get("chapter_body_sha256") ==
             ident["chapter_body_sha256"],
             "WF_V85_PASS_A_NOT_SEALED")
        receipt = self.gate.audit(
            proposals, source_windows=windows, chapter=ident["chapter"],
            chapter_body_sha256=ident["chapter_body_sha256"],
            first_read_seal_sha256=seal["event_sha256"],
            read_frontier=len(windows))
        # The only returned source details are source digests and offsets.
        # Character states come from the earlier frozen FactJournal head.
        return {
            "format": FORMAT,
            "audit": receipt,
            "r2_seal_sha256": seal["event_sha256"],
            "original_pass_a_chain_verified": True,
            "historical_model_answers_not_regenerated": True,
            "no_private_original_or_verbatim_quote_retained": True,
            "semantic_accuracy_independently_graduated": False,
            "writer_can_consume_this_as_verified_skill": False,
        }

    def persist_sidecar(self, receipt: dict, *, explicitly_allow_write=False):
        """Optional future immutable R2 CAS metadata write, not default.

        Caller must have a real writer role and explicitly authorize this
        one operation. Never use the old experimental CAS writer silently.
        """
        need(explicitly_allow_write is True,
             "WF_V85_SIDE_CAR_WRITE_NOT_AUTHORIZED")
        need(getattr(self.journal,"read_only",True) is False and
             bool(getattr(self.journal,"writer",None)),
             "WF_V85_SIDE_CAR_WRITER_REQUIRED")
        need(isinstance(receipt,dict) and
             set(receipt)=={"format","audit","r2_seal_sha256",
                 "original_pass_a_chain_verified",
                 "historical_model_answers_not_regenerated",
                 "no_private_original_or_verbatim_quote_retained",
                 "semantic_accuracy_independently_graduated",
                 "writer_can_consume_this_as_verified_skill"} and
             receipt["format"]==FORMAT and
             receipt["original_pass_a_chain_verified"] is True and
             receipt["writer_can_consume_this_as_verified_skill"] is False,
             "WF_V85_SIDE_CAR_RECEIPT_INVALID")
        audit=receipt["audit"]
        need(isinstance(audit,dict) and
             is_sha(audit.get("receipt_sha256")) and
             audit.get("pass_a_seal_sha256")==receipt["r2_seal_sha256"] and
             audit.get("eligible_to_direct_writing") is False and
             audit.get("literary_semantics_independently_verified") is False,
             "WF_V85_SIDE_CAR_AUDIT_UNTRUSTED")
        copy={k:v for k,v in audit.items() if k!="receipt_sha256"}
        need(sha256(canonical(copy)).hexdigest()==audit["receipt_sha256"],
             "WF_V85_SIDE_CAR_AUDIT_HASH_MISMATCH")
        raw=canonical(receipt)
        need(len(raw)<=8192,"WF_V85_SIDE_CAR_STORAGE_BUDGET_EXCEEDED")
        sha,created=self.journal._put_content(raw)
        need(sha==sha256(raw).hexdigest(),
             "WF_V85_SIDE_CAR_CAS_ROUNDTRIP_INVALID")
        return {"sidecar_sha256":sha,"created":created,
                "original_prose_written":False,
                "semantic_literary_improvement_verified":False}
