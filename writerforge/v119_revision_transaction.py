"""V119: source-locked surgical revisions; never let model prose edit the rest.

This is a candidate-only, zero-model, zero-storage *transaction preview*. It does
not certify narrative quality, intent satisfaction, or unrestricted semantics.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re

FORMAT = "wf.writing.v119.surgical-revision-preview"
MAX_DOCUMENT = 20_000
MAX_PATCH = 1_800
MAX_LOCKS = 12
MAX_LOCK_CHARS = 160
SHA = re.compile(r"[0-9a-f]{64}\Z")


class RevisionTransactionError(ValueError):
    """Malformed/stale or out-of-scope edit; no fallback to whole rewrite."""


def _need(condition: bool, reason: str) -> None:
    if not condition:
        raise RevisionTransactionError(reason)


def _hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _digest_json(document: dict) -> str:
    return sha256(json.dumps(document, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode("utf-8")).hexdigest()


def _validate_source(*, source: str, source_sha256: str,
                     project_id: str, scene_id: str,
                     start: int, end: int, expected_original: str,
                     pinned_quotes: tuple[str, ...]) -> tuple[str, str]:
    _need(type(project_id) is str and 1 <= len(project_id) <= 128 and
          type(scene_id) is str and 1 <= len(scene_id) <= 128,
          "WF119_REVISION_SCOPE_INVALID")
    _need(type(source) is str and 1 <= len(source) <= MAX_DOCUMENT,
          "WF119_SOURCE_SIZE_INVALID")
    _need(type(source_sha256) is str and SHA.fullmatch(source_sha256) is not None
          and _hash(source) == source_sha256,
          "WF119_STALE_SOURCE_HASH_REJECTED")
    _need(type(start) is int and type(end) is int and
          0 <= start < end <= len(source) and end-start <= MAX_PATCH,
          "WF119_SELECTED_SPAN_INVALID")
    _need(type(expected_original) is str and expected_original == source[start:end],
          "WF119_SOURCE_SPAN_NO_LONGER_MATCHES")
    _need(type(pinned_quotes) is tuple and len(pinned_quotes) <= MAX_LOCKS,
          "WF119_LOCKS_INVALID")
    for q in pinned_quotes:
        _need(type(q) is str and 1 <= len(q) <= MAX_LOCK_CHARS and
              source.count(q) == 1,
              "WF119_PINNED_QUOTE_INVALID")
        pos = source.index(q)
        _need(pos + len(q) <= start or pos >= end,
              "WF119_PINNED_QUOTE_OVERLAPS_EDIT")
    return source[:start], source[end:]


def preview_revision(*, project_id: str, scene_id: str, source: str,
                     source_sha256: str, start: int, end: int,
                     expected_original: str, replacement: str,
                     pinned_quotes: tuple[str, ...] = (),
                     previous_candidate_state: dict | None = None,
                     previous_risks: tuple[dict, ...] = (),
                     cast: tuple[str, ...] = ()) -> dict:
    """Build candidate by replacing exactly one verified slice of SOURCE.

    Unedited prefix/suffix are impossible for a model to alter. A new
    deterministic V116 warning forbids provisional use; never silently repair.
    Preflight can overflag some ambiguous agents, so even a clean preview is
    unreviewed, and a flagged one is review-only rather than auto-canon.
    """
    prefix, suffix = _validate_source(
        source=source, source_sha256=source_sha256, project_id=project_id,
        scene_id=scene_id, start=start, end=end,
        expected_original=expected_original, pinned_quotes=pinned_quotes)
    _need(type(replacement) is str and len(replacement) <= MAX_PATCH,
          "WF119_REPLACEMENT_SIZE_INVALID")
    _need(replacement != expected_original,
          "WF119_NO_TEXT_CHANGE")
    candidate = prefix + replacement + suffix
    _need(1 <= len(candidate) <= MAX_DOCUMENT and candidate != source,
          "WF119_REVISED_DOCUMENT_BOUNDS")
    for quote in pinned_quotes:
        _need(candidate.count(quote) == 1,
              "WF119_PINNED_QUOTE_REPLICATED")
    _need(type(previous_risks) is tuple and len(previous_risks) <= 32 and
          all(type(r) is dict for r in previous_risks),
          "WF119_PRIOR_RISK_SCHEMA_INVALID")
    _need(type(cast) is tuple and len(cast) <= 10 and
          all(type(name) is str and 1 <= len(name) <= 70
              for name in cast) and len(set(cast)) == len(cast),
          "WF119_CHARACTER_CAST_INVALID")
    prior_report = None
    revised_report = None
    introduced = []
    review_introduced = []
    if previous_candidate_state is not None:
        _need(type(previous_candidate_state) is dict and
              len(previous_candidate_state) <= 36,
              "WF119_PRIOR_STATE_INVALID")
        from .v116_state_delta import preflight_next_prose
        prior_report = preflight_next_prose(
            source, previous_candidate_state=previous_candidate_state,
            previous_risks=previous_risks,cast=cast)
        revised_report = preflight_next_prose(
            candidate, previous_candidate_state=previous_candidate_state,
            previous_risks=previous_risks,cast=cast)
        introduced = sorted(set(revised_report["findings"])
                            - set(prior_report["findings"]))
        # Actor-uncertain prose is not an automatic hard contradiction. It
        # must nevertheless be VISIBLE in the local edit receipt.
        review_introduced = sorted(
            set(revised_report.get("review_findings",[]))
            - set(prior_report.get("review_findings",[])))
    status = "BLOCKED_NEW_STATE_WARNING" if introduced else "PROVISIONAL_REVIEW"
    receipt = {
        "format": FORMAT, "project_id": project_id, "scene_id": scene_id,
        "source_sha256": source_sha256,
        "candidate_sha256": _hash(candidate),
        "selection": [start, end],
        "expected_selection_sha256": _hash(expected_original),
        "replacement_sha256": _hash(replacement),
        "untouched_prefix_sha256": _hash(prefix),
        "untouched_suffix_sha256": _hash(suffix),
        "locked_quote_sha256s": [_hash(q) for q in pinned_quotes],
        "status": status,
        "new_preflight_warnings": introduced,
        "new_preflight_review_flags": review_introduced,
        "preflight_actor_scope": (
            revised_report.get("arm_actor_scope")
            if revised_report else "NO_PRIOR_STATE_PROVIDED"),
        "preflight_coverage": ("V116_SOURCE_ONLY_NARROW"
                               if previous_candidate_state is not None else
                               "NO_PRIOR_STATE_PROVIDED"),
        "baseline_preflight_warnings": (
            prior_report["findings"] if prior_report else []),
        "revision_preflight_warnings": (
            revised_report["findings"] if revised_report else []),
        "revision_review_findings": (
            revised_report["review_findings"] if revised_report else []),
        "only_declared_selection_changed": True,
        "model_justification_was_not_evidence": True,
        "intent_fulfillment_verified": False,
        "literary_quality_verified": False,
        "canon_writes": 0, "model_calls": 0, "automatic_retry": False,
        "author_accepted": False,
        "raw_manuscript_in_receipt": False,
    }
    receipt["receipt_sha256"] = _digest_json(receipt)
    return {
        "status": status,
        "candidate_prose": candidate if not introduced else None,
        "receipt": receipt,
    }


def inspect_whole_rewrite(*, proposed_whole_text: str, project_id: str,
                          scene_id: str, source: str, source_sha256: str,
                          start: int, end: int, expected_original: str,
                          pinned_quotes: tuple[str, ...] = (),
                          previous_candidate_state: dict | None = None,
                          previous_risks: tuple[dict, ...] = (),
                          cast: tuple[str, ...] = ()) -> dict:
    """Strictly reject whole-output model edits outside the declared span.

    Models may return a complete manuscript instead of the requested fragment.
    This gate verifies exact Unicode-codepoint identity of all out-of-scope
    text, including punctuation and whitespace, before preview.
    """
    prefix, suffix = _validate_source(
        source=source, source_sha256=source_sha256,
        project_id=project_id, scene_id=scene_id, start=start, end=end,
        expected_original=expected_original, pinned_quotes=pinned_quotes)
    _need(type(proposed_whole_text) is str and
          1 <= len(proposed_whole_text) <= MAX_DOCUMENT,
          "WF119_WHOLE_REWRITE_BOUNDS")
    _need(proposed_whole_text.startswith(prefix) and
          proposed_whole_text.endswith(suffix) and
          len(proposed_whole_text) >= len(prefix) + len(suffix),
          "WF119_UNRELATED_TEXT_CHANGED_REJECTED")
    middle_end = (len(proposed_whole_text)-len(suffix)
                  if suffix else len(proposed_whole_text))
    replacement = proposed_whole_text[len(prefix):middle_end]
    return preview_revision(
        project_id=project_id, scene_id=scene_id,
        source=source, source_sha256=source_sha256,
        start=start, end=end, expected_original=expected_original,
        replacement=replacement, pinned_quotes=pinned_quotes,
        previous_candidate_state=previous_candidate_state,
        previous_risks=previous_risks,cast=cast,
    )
