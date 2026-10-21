"""V101: zero-model preference calibration; NEVER equate taste with a hash.

A learner has to name text-grounded reasons, a serious alternative reading,
and the literary tradeoff of a rewriting, not just output GOOD or 99/100.
Uses private held-out Chinese pairs only when caller has rights and trusted
labels. The open WritingPreferenceBench is inspiration, not imported data.
"""
from __future__ import annotations
from hashlib import sha256
from .v101_narrative_reader import V101ReadingError,_words,_witness


def _require(ok,reason):
    if not ok:raise V101ReadingError(reason)


def calibrate_pair(*,a,b,learner,external_preference=None,
                   independent_reviewer_attested=False,
                   max_gap=0.10):
    _require(type(a) is str and type(b) is str and
             80<=len(a)<=12000 and 80<=len(b)<=12000 and
             type(learner) is dict and set(learner)=={
                 "preferred","a_evidence","b_evidence","why",
                 "counterfactual_tradeoff","credible_dissent"},
             "WF101_PREFERENCE_INPUT_INVALID")
    _require(learner["preferred"] in ("A","B","TIE","ABSTAIN"),
             "WF101_PREFERENCE_LABEL_INVALID")
    _require(type(max_gap) in (int,float) and not isinstance(max_gap,bool)
             and 0<=max_gap<=0.20,"WF101_LENGTH_TOLERANCE_INVALID")
    size_gap=(max(len(a),len(b))-min(len(a),len(b)))/max(len(a),len(b))
    aw=_witness((a,),learner["a_evidence"])
    bw=_witness((b,),learner["b_evidence"])
    for k in ("why","counterfactual_tradeoff","credible_dissent"):
        _require(_words(learner[k],12,240),
                 "WF101_NO_REASONED_PREFERENCE_"+k.upper())
    _require(external_preference is None or
             external_preference in ("A","B","TIE"),
             "WF101_EXTERNAL_LABEL_INVALID")
    _require(type(independent_reviewer_attested) is bool,
             "WF101_REVIEWER_STATUS_INVALID")
    # Caller-provided label is NOT proof that its claimed issuer is independent.
    eligible=size_gap<=max_gap and external_preference is not None
    agreement=(learner["preferred"]==external_preference
               if eligible and learner["preferred"]!="ABSTAIN" else None)
    return {
        "format":"wf.learn.preference-calibration.v101",
        "a_source_sha256":sha256(a.encode("utf8")).hexdigest(),
        "b_source_sha256":sha256(b.encode("utf8")).hexdigest(),
        "a_quote_anchor":aw,"b_quote_anchor":bw,
        "actual_lengths":{"A":len(a),"B":len(b)},
        "length_gap":round(size_gap,5),
        "comparable_length":size_gap<=max_gap,
        "learner_preference":learner["preferred"],
        "reason_sha256":sha256(learner["why"].encode("utf8")).hexdigest(),
        "counterfactual_sha256":sha256(
           learner["counterfactual_tradeoff"].encode("utf8")).hexdigest(),
        "dissent_sha256":sha256(
           learner["credible_dissent"].encode("utf8")).hexdigest(),
        "external_label_supplied":external_preference is not None,
        "external_reviewer_attestation_claimed":independent_reviewer_attested,
        "external_identity_cryptographically_verified":False,
        "preference_agreement_candidate":agreement,
        "eligible_for_scored_experiment":eligible,
        "model_literary_mastery_proven":False,
        "no_source_text_in_receipt":True,
        "no_new_facts_or_training_skill_graduation":True,
    }
