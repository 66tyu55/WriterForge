"""V119: source-locked surgical revisions; never let model prose edit the rest.

This is a candidate-only, zero-model, zero-storage *transaction preview*. It does
not certify narrative quality, intent satisfaction, or unrestricted semantics.
"""
from __future__ import annotations

from hashlib import sha256
from collections import Counter
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
    # Distinguish RELATION IDENTITY from a generic risk CODE. Otherwise a
    # V119 rewrite that exchanges a bad copper-box relation for a NEW bad
    # silver-box relation would show the same review warning and pass as if
    # no new problem was introduced.
    from .v122_item_provenance import (
        audit_physical_relation_sources,physical_relation_issue_keys)
    baseline_relation=audit_physical_relation_sources(prose=source)
    candidate_relation=audit_physical_relation_sources(prose=candidate)
    old_relation_keys=physical_relation_issue_keys(baseline_relation)
    new_relation_keys=physical_relation_issue_keys(candidate_relation)
    new_relation_issue_keys=sorted(
        (Counter(new_relation_keys)-Counter(old_relation_keys)).elements())
    retired_relation_issue_keys=sorted(
        (Counter(old_relation_keys)-Counter(new_relation_keys)).elements())
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
        "baseline_review_findings": (
            prior_report["review_findings"] if prior_report else []),
        "baseline_physical_relation_source_sha256":baseline_relation["source_sha256"],
        "candidate_physical_relation_source_sha256":candidate_relation["source_sha256"],
        "baseline_source_relation_issue_keys":old_relation_keys,
        "candidate_source_relation_issue_keys":new_relation_keys,
        "new_source_relation_issue_keys":new_relation_issue_keys,
        "retired_source_relation_issue_keys":retired_relation_issue_keys,
        "relationship_identity_checked_independently_of_warning_code":True,
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



def prepare_source_repair_contract(
        *, source: str, source_sha256: str, beat: dict,
        accepted=(), original_trace=None, writer_attention=None,
        previous_candidate_state=None, cast=()) -> dict:
    """WF helps the original novelist through FACTS and constraints, not prose.

    This is the bounded, source-backed plan for a ONE-TURN edit. Existing
    V116 provides hard/review findings; V96 provides causal parent and
    model-authored exact action/effect quotes. Literary dissatisfaction is
    the same author's own unverified reason, never invented by WF.
    Returns a deterministic, inspectable repair contract that can be sent
    to that same writer without any extra model calls.
    """
    _need(type(source) is str and 80<=len(source)<=MAX_DOCUMENT and
          type(source_sha256) is str and
          SHA.fullmatch(source_sha256) is not None and
          _hash(source)==source_sha256,
          "WF119_REPAIR_ORIGINAL_SOURCE_INVALID")
    _need(type(beat) is dict and
          type(beat.get("id")) is str and
          beat.get("kind") in ("quiet","action","decision","reversal",
                              "setup","dialogue","aftermath","transition")
          and "causal_parent" in beat,
          "WF119_REPAIR_BEAT_INVALID")
    _need(type(accepted) in (list,tuple) and len(accepted)<=16 and
          all(type(x) is dict for x in accepted),
          "WF119_REPAIR_PREVIOUS_TURNS_INVALID")
    _need(original_trace is None or
          (type(original_trace) is dict and
           set(original_trace)=={
               "action_quote","effect_quote","parent_effect_quote"}),
          "WF119_REPAIR_OLD_TRACE_INVALID")
    _need(writer_attention is None or type(writer_attention) is dict,
          "WF119_REPAIR_WRITER_INTENT_INVALID")
    _need(type(cast) in (tuple,list) and len(cast)<=10 and
          all(type(x) is str and 1<=len(x)<=70 for x in cast),
          "WF119_REPAIR_CHARACTER_SCOPE_INVALID")
    _need(previous_candidate_state is None or
          (type(previous_candidate_state) is dict and
           len(previous_candidate_state)<=36),
          "WF119_REPAIR_PRIOR_STATE_UNTRUSTED")
    parent=beat["causal_parent"]
    previous_effect=None
    previous_pending_action=None
    previous_temporal_source=None
    # The same V96/V98 source integrity owns decision-outcome-pending:
    # a writer can repair an observed decision before its consequence is
    # observed. Do not force the child to fabricate a previous effect.
    if parent is not None:
        matches=[x for x in accepted if x.get("beat_id")==parent]
        _need(len(matches)==1,"WF119_REPAIR_PARENT_SOURCE_MISSING")
        original_parent=matches[0]
        prior_effect=original_parent.get("effect_quote")
        if type(prior_effect) is str and prior_effect:
            _need(type(original_parent.get("prose")) is str and
                  original_parent["prose"].count(prior_effect)==1,
                  "WF119_REPAIR_PARENT_SOURCE_MISSING")
            previous_effect=prior_effect
        else:
            prior_receipt=original_parent.get("receipt")
            if (type(prior_receipt) is dict and
                    prior_receipt.get("outcome_pending_source_only") is True):
                from .v98_rolling_causal_planner import (
                    latest_source_basis_for_replan,V98RollingPlanError)
                try:
                    found,quote,kind=latest_source_basis_for_replan(
                        (original_parent,))
                except V98RollingPlanError:
                    raise RevisionTransactionError(
                        "WF119_REPAIR_PARENT_PENDING_SOURCE_INVALID") from None
                _need(found.get("beat_id")==parent and
                      kind=="DECISION_ACTION_ONLY_OUTCOME_PENDING",
                      "WF119_REPAIR_PARENT_PENDING_SOURCE_INVALID")
                previous_pending_action=quote
            else:
                # Dialogues or quiet scenes without a reported effect can
                # precede a revision without becoming a causal fact. Use
                # the ORIGINAL V96 signed source rather than an invented
                # predecessor result or a second temporal memory module.
                from .v96_causal_turns import (
                    _verified_noncausal_temporal_parent,
                    V96CausalDraftError)
                try:
                    previous_temporal_source=(
                        _verified_noncausal_temporal_parent(original_parent))
                except V96CausalDraftError:
                    raise RevisionTransactionError(
                        "WF119_REPAIR_PARENT_TEMPORAL_SOURCE_INVALID") from None
    decision_pending=(beat["kind"]=="decision" and
                      type(original_trace) is dict and
                      type(original_trace.get("action_quote")) is str and
                      original_trace.get("effect_quote") is None)
    if decision_pending:
        # Do not trust just the author's claim that its effect is absent.
        # Re-run the EXISTING V96 literal source, polarity and parent
        # checks. No literary causality or future state becomes KNOWN.
        from .v96_causal_turns import (
            check_turn,V96CausalDraftError)
        try:
            checked=check_turn(
                json.dumps({"prose":source,"trace":original_trace},
                           ensure_ascii=False,separators=(",",":")),
                beat,mode="causal_guard",accepted=accepted,
                max_prose_chars=1024)
        except V96CausalDraftError:
            raise RevisionTransactionError(
                "WF119_REPAIR_DECISION_PENDING_TRACE_INVALID") from None
        _need(checked["receipt"]["outcome_pending_source_only"] is True and
              checked["receipt"]["causal_relation_verified"] is False,
              "WF119_REPAIR_DECISION_PENDING_TRACE_INVALID")
    raw_focus=(writer_attention or {}).get("source_quote")
    focus=raw_focus if (type(raw_focus) is str and
                        6<=len(raw_focus)<=160 and
                        source.count(raw_focus)==1) else None
    intent={}
    for key in ("reason","risk","desired_effect","focus"):
        value=(writer_attention or {}).get(key)
        if type(value) is str and 1<=len(value)<=260:
            intent[key]=value
    source_before=None
    if previous_candidate_state is not None:
        # Use the EXISTING reducer's source-only risks, not a new semantic
        # literary validator. An uncertain finding does not prove an error.
        from .v116_state_delta import preflight_next_prose
        source_before=preflight_next_prose(
            source,previous_candidate_state=previous_candidate_state,
            cast=cast)
    # Reuse the original V122 source-bound physical relation evidence.
    # The host supplies two actual quotes and an uncertainty, not a verdict
    # about which story-world interpretation or rewrite would be better.
    from .v122_item_provenance import audit_physical_relation_sources
    relation_evidence=audit_physical_relation_sources(prose=source)
    _need(relation_evidence["source_sha256"]==source_sha256,
          "WF119_RELATION_EVIDENCE_SOURCE_SHA_MISMATCH")
    # Bounded projection of already available V114/V116 state cells:
    # not a new memory store and never a permanent fact assertion.
    # If a long state was truncated, the omission is EXPLICIT so that
    # a model cannot treat omitted items/injuries as gone.
    source_rows=[]
    if previous_candidate_state is not None:
        for key,value in sorted(previous_candidate_state.items(),
                                key=lambda pair:str(pair[0])):
            try:
                domain,entity,predicate,scope,_=json.loads(key)
            except (ValueError,TypeError):
                continue
            if (scope!="author_plan" or
                domain not in ("item","character") or
                type(entity) is not str or type(predicate) is not str or
                len(entity)>70 or len(predicate)>70 or
                type(value) not in (str,int,bool)):
                continue
            source_rows.append({
                "domain":domain,"entity":entity,
                "predicate":predicate,
                "previous_candidate_value":str(value)[:120],
                "source_is_unaccepted_v114_candidate_not_canon":True,
            })
    basic={
        "format":"wf.writing.v119.source-first-repair-guide.v1",
        "source_sha256":source_sha256,
        "beat_id":beat["id"],"beat_kind":beat["kind"],
        "author_model_selected_focus_quote":focus,
        "author_model_selected_focus_offset":(
            source.index(focus) if focus is not None else None),
        "author_intent_not_a_verified_fact":intent,
        "previous_causal_parent_id":parent,
        "actual_previous_effect_quote":previous_effect,
        "actual_previous_pending_action_quote":previous_pending_action,
        "previous_parent_effect_unobserved":previous_pending_action is not None,
        "previous_parent_temporal_link_unverified":previous_temporal_source is not None,
        "actual_previous_temporal_source_sha256":previous_temporal_source,
        "original_model_trace":original_trace,
        "baseline_hard_findings":(
            source_before["findings"] if source_before is not None else []),
        "baseline_review_only_findings":(
            source_before["review_findings"] if source_before is not None else []),
        "baseline_state_coverage":(
            "V116_SOURCE_ONLY_NARROW" if source_before is not None
            else "NO_PREVIOUS_CANDIDATE_STATE"),
        "physical_relation_source_evidence":{
            "source_sha256":relation_evidence["source_sha256"],
            "source_receipt_sha256":relation_evidence["receipt_sha256"],
            "review_status":relation_evidence["review_status"],
            "source_quote_pairs":relation_evidence["review_pairs"],
            "physical_identity_or_contact_may_differ":True,
            "source_quotes_only_not_a_literary_verdict":True,
            "unverified_relation_cannot_become_downstream_fact":True,
            "writer_may_keep_unrevealed_actor_and_meaning":True,
            "writer_chooses_keep_delete_local_edit_or_scene_rewrite":True,
        },
        "prior_source_candidate_state":source_rows[:8],
        "prior_item_character_rows_omitted":max(0,len(source_rows)-8),
        "other_prior_state_domains_not_in_this_small_view":True,
        "omission_does_not_mean_state_was_erased":True,
        "source_action_quote_required":beat["kind"] in (
            "action","decision","reversal"),
        "decision_effect_unobserved_source_only":decision_pending,
        "source_action_effect_required":beat["kind"] in (
            "action","decision","reversal") and not decision_pending,
        "repair_paths_owned_by_author":[
            "KEEP_IF_THIS_IS_DELIBERATELY_UNWRITTEN_AND_COHERENT",
            "REVISE_EXACT_SOURCE_SPAN_AND_REVIEW_CAUSE_AND_EFFECT",
            "DELETE_SOURCE_SPAN_ONLY_IF_CAUSAL_LINKS_STILL_HOLD",
            "REPLACE_SCENE_IF_SOURCE_ONLY_LOCAL_REPAIR_IS_INADEQUATE",
        ],
        "must_preserve":[
            "UNEDITED_SOURCE_PREFIX_AND_SUFFIX",
            "PREVIOUS_AUTHENTIC_CAUSAL_PARENT_OR_NULL",
            "ONLY_STORY_ACTIONS_ACTUALLY_WRITTEN",
            "NO_UNPROVEN_ITEM_TRANSFER_OR_NEW_CHARACTER_KNOWLEDGE",
            "TWO_DISTINCT_ORDERED_ACTION_EFFECT_QUOTES_WHEN_REQUIRED",
        ],
        "evaluation_after_revision":[
            "V119_EXACT_SELECTION_AND_LOCKED_SURROUNDINGS",
            "V96_SEPARATE_ORDERED_SOURCE_CAUSAL_QUOTES",
            "V116_PREVIOUS_VS_NEW_STRUCTURAL_RISKS",
            "V114_V117_TEMPORAL_AND_SOURCE_REPLAY",
            "DOWNSTREAM_DERIVED_TURNS_INVALIDATED_UNTIL_REGENERATED",
        ],
        "downstream_after_change":"MUST_REGENERATE_FROM_REVISED_SOURCE",
        "no_literary_grade_or_host_authored_text":True,
        "any_author_intent_fulfillment_still_unproven":True,
        "new_model_calls":0,"canon_writes":0,
    }
    basic["receipt_sha256"]=_digest_json(basic)
    return basic


def compare_source_repair_impact(*,preview_receipt:dict) -> dict:
    """Compare known state WARNINGS before/after a V119 edit.

    A smaller warning list does not prove literary merit or that the
    author's own problem was fixed. New REVIEW flags cannot silently be
    dismissed as clean; hold the candidate privately for author/source
    reconsideration rather than progressing downstream on mere optimism.
    """
    _need(type(preview_receipt) is dict and
          preview_receipt.get("format")==FORMAT and
          type(preview_receipt.get("receipt_sha256")) is str and
          preview_receipt["receipt_sha256"]==_digest_json({
              k:v for k,v in preview_receipt.items()
              if k!="receipt_sha256"}),
          "WF119_REPAIR_IMPACT_RECEIPT_TAMPERED")
    def arr(key):
        val=preview_receipt.get(key)
        _need(type(val) is list and len(val)<=32 and
              all(type(x) is str for x in val),
              "WF119_REPAIR_IMPACT_WARNINGS_INVALID")
        return set(val)
    old_hard=arr("baseline_preflight_warnings")
    new_hard=arr("revision_preflight_warnings")
    introduced=set(arr("new_preflight_warnings"))
    _need(introduced==new_hard-old_hard,
          "WF119_REPAIR_IMPACT_DELTA_INCONSISTENT")
    review_introduced=arr("new_preflight_review_flags")
    def issue_keys(field):
        value=preview_receipt.get(field)
        _need(type(value) is list and len(value)<=MAX_LOCKS and
              all(type(x) is str and SHA.fullmatch(x) is not None
                  for x in value),
              "WF119_RELATION_ISSUE_IDENTITY_MISSING_OR_INVALID")
        return Counter(value)
    old_relation_keys=issue_keys("baseline_source_relation_issue_keys")
    new_relation_keys=issue_keys("candidate_source_relation_issue_keys")
    introduced_relation=issue_keys("new_source_relation_issue_keys")
    retired_relation=issue_keys("retired_source_relation_issue_keys")
    _need(introduced_relation==new_relation_keys-old_relation_keys and
          retired_relation==old_relation_keys-new_relation_keys and
          preview_receipt.get("baseline_physical_relation_source_sha256")==
              preview_receipt["source_sha256"] and
          preview_receipt.get("candidate_physical_relation_source_sha256")==
              preview_receipt["candidate_sha256"],
          "WF119_RELATION_ISSUE_DELTA_SOURCE_INCONSISTENT")
    remaining_relation=bool(new_relation_keys)
    _need(review_introduced.issubset(
        arr("revision_review_findings")),
          "WF119_REPAIR_IMPACT_REVIEW_DELTA_INCONSISTENT")
    if introduced:
        status="BLOCKED_NEW_HARD_SOURCE_RISK"
    elif review_introduced or introduced_relation:
        status="HELD_NEW_UNVERIFIED_SOURCE_RISK"
    elif remaining_relation:
        # A model cannot make its own contradictory position claims valid
        # merely by rewording an unrelated sentence.
        status="HELD_EXISTING_SOURCE_RELATION_RISK"
    else:
        status="NO_NEW_DETECTED_STRUCTURAL_RISK_ONLY"
    impact={
        "format":"wf.writing.v119.before-after-guarded-impact.v1",
        "source_sha256":preview_receipt["source_sha256"],
        "candidate_sha256":preview_receipt["candidate_sha256"],
        "status":status,
        "baseline_hard_findings":sorted(old_hard),
        "candidate_hard_findings":sorted(new_hard),
        "removed_hard_findings":sorted(old_hard-new_hard),
        "new_hard_findings":sorted(introduced),
        "candidate_review_only_findings":sorted(
            arr("revision_review_findings")),
        "new_unverified_review_findings":sorted(review_introduced),
        "new_source_relation_issue_keys":sorted(
            introduced_relation.elements()),
        "retired_source_relation_issue_keys":sorted(
            retired_relation.elements()),
        "still_open_source_relation_issue_keys":sorted(
            (new_relation_keys & old_relation_keys).elements()),
        "existing_physical_relation_review_remaining":remaining_relation,
        "source_relation_risk_cannot_be_cleared_by_prose_without_evidence":True,
        "previously_existing_hard_findings_remain":sorted(
            old_hard & new_hard),
        "one_fix_may_create_another_error":True,
        "author_literary_goal_satisfied":"UNVERIFIED",
        "verified_code_only_not_complete_story_truth":True,
        "subsequent_turns_require_new_source_prose":True,
        "never_automatically_repair_or_promote_to_canon":True,
        "new_model_calls":0,"canon_writes":0,
    }
    impact["receipt_sha256"]=_digest_json(impact)
    return impact


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
