"""V38 real strict comparison: WF self-claimed L2 versus two examiner opinions.

Zero paid models. All inputs are R2 SHA-verified, including the WF append-only
retrospective and genuine V37d reviewer citation positions. This reports
whether opinions refer to the SAME actual sentence, not whether a real
literary payoff exists. Never publish copyrighted source, unpublished fiction
or the learner's private explanations to public Actions logs.
"""
from __future__ import annotations
import json

from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.v35_observable_trace import sha
from scripts.forensic_v37_xiyouji_L2 import frozen_evidence,sentence_menu
from scripts.append_v38_frozen_l2_selfcheck import (
    ROOT as SELF_ROOT,SESSION as SELF_SESSION,
)
from scripts.audit_v37d_exact_foreshadowing_positions import ROOT as CRITIC_ROOT

SELF_SHA="a9d5d521b2e0adbeb416f9325b0adabaad408abb728bd978099effe328488a62"
CRITIC_POSITIONS_SHA="9457ff733c4390468cae037ad3786702459ff46b6bbfedb65f9f2bf980e92433"
ROOT="writerforge/v1/examiner/v38-foreshadowing-self-vs-critics-crosscheck"

def _read(vault,key,hash_,cap):
    raw=vault._get_small(key,cap)
    if sha(raw)!=hash_:
        raise ValueError("L2_R2_CROSSCHECK_SHA_INVALID")
    return json.loads(raw)

def exact_sentence_at(menus:list,position:int)->dict:
    matches=[x for x in menus if x["start"]<=position<x["end"]]
    if len(matches)!=1:
        raise ValueError("L2_CITED_OFFSET_NOT_IN_UNIQUE_REAL_SENTENCE")
    return matches[0]

def compare(vault,*,persist=True):
    if vault.config.bucket!="writerforge-private-library":
        raise ValueError("L2_PRIVATE_R2_ONLY")
    material=frozen_evidence(vault)
    data=_read(vault,
        f"{SELF_ROOT}/{SELF_SESSION}/result-{SELF_SHA}.json",
        SELF_SHA,30000)
    earlier=_read(vault,
        f"{CRITIC_ROOT}/audits/{CRITIC_POSITIONS_SHA}.json",
        CRITIC_POSITIONS_SHA,18000)
    if (data.get("status")!="APPENDED_STRICT_TEXTUAL_EVIDENCE_ONLY"
        or data.get("source_lesson_was_precommitted")!="L2"
        or data.get("history_never_rewritten") is not True
        or data.get("original_report_had_missing_L2_coverage") is not True
        or data.get("strict_validated_aftercheck") is None
        or earlier.get("model_calls")!=0):
        raise ValueError("L2_ORIGINAL_OR_AFTERCHECK_PROVENANCE_INVALID")
    sub=data["strict_validated_aftercheck"]
    trace=sub["full_validated_aftercheck"]["learned_transfer_evidence"]
    if (sub.get("additional_check_angle")!="foreshadowing"
        or sub.get("generated_after_original_story_and_review") is not True
        or trace.get("actual_complete_draft_sha256")!=sha(material["revised_draft"])
        or trace.get("source_linked_angle_names")!=["foreshadowing"]
        or len(trace.get("evidence_claims",[]))!=1):
        raise ValueError("L2_UNVERIFIED_SELF_PROOF_NOT_LINKED_TO_FROZEN_ESSAY")
    claim=trace["evidence_claims"][0]
    status=claim["application_claim"]
    revised=material["revised_draft"]
    original=material["original_draft"]
    menus=sentence_menu(revised,"R")
    relative=claim["actual_text_positions"]
    if status=="CLAIMED_APPLIED":
        if not isinstance(relative,dict):
            raise ValueError("L2_CLAIM_WITHOUT_HOST_VERIFIED_POSITION")
        s=relative["setup_offset"];p=relative["payoff_offset"]
        if (type(s) is not int or type(p) is not int
            or not 0<=s<p<len(revised)):
            raise ValueError("L2_CLAIM_OFFSETS_NOT_ON_FROZEN_NOVEL")
        setup=exact_sentence_at(menus,s)
        payoff=exact_sentence_at(menus,p)
    else:
        setup=payoff=None
    rows=[]
    for critic in earlier["reviewer_position_evidence"]:
        cited=critic["cited_genuine_sentence_positions"]
        setup_ids=cited["revised_setup_numbers"]["indices"]
        payoff_ids=cited["revised_payoff_numbers"]["indices"]
        rows.append({
            "reviewer":critic["model"],
            "full_original_draft_review_format_valid":
                critic["draft_format_valid"],
            "reviewer_original_opinion_sha256":
                critic["draft_opinion_sha256"],
            "reviewer_source_opinion_sha256":
                critic["source_opinion_sha256"],
            "self_claim_setup_same_sentence_as_reviewer":{
                "model_cited_any_setup":bool(setup_ids),
                "same_sentence":(setup is not None and setup["id"] in
                                 {f"R{x:02d}" for x in (setup_ids or [])}),
            },
            "self_claim_payoff_same_sentence_as_reviewer":{
                "model_cited_any_payoff":bool(payoff_ids),
                "same_sentence":(payoff is not None and payoff["id"] in
                                 {f"R{x:02d}" for x in (payoff_ids or [])}),
            },
            "external_reviewer_setup_earliest_pct":
                critic["earliest_revised_setup_as_pct"],
            "external_reviewer_payoff_earliest_pct":
                critic["earliest_payoff_as_pct"],
            "reviewer_original_judgment_not_overwritten":True,
        })
    result={
        "format":"writerforge.v38-self-vs-two-examiners-exact-sentence-crosswalk.v1",
        "self_review_report_sha256":SELF_SHA,
        "external_critic_locations_sha256":CRITIC_POSITIONS_SHA,
        "frozen_original_draft_sha256":sha(original),
        "frozen_revision_sha256":sha(revised),
        "self_declared_status":status,
        "self_setup_sentence_id":setup["id"] if setup else None,
        "self_payoff_sentence_id":payoff["id"] if payoff else None,
        "self_setup_pct":(
            relative["setup_position_pct"] if relative else None),
        "self_payoff_pct":(
            relative["payoff_position_pct"] if relative else None),
        "self_setup_in_first_half":(
            relative["setup_in_first_half"] if relative else None),
        "self_payoff_after_two_thirds":(
            relative["payoff_after_two_thirds"] if relative else None),
        "examiner_overlap":rows,
        "self_application_claim_was_generated_after_draft":True,
        "word_occurrence_and_sentence_overlap_not_semantic_causation":True,
        "independent_human_reading_not_performed":True,
        "no_formal_literary_progress_inferred":True,
        "old_history_unchanged":True,
        "model_calls":0,"official_promotion":False,
    }
    blob=_canonical(result)
    if len(blob)>12000:raise ValueError("L2_CROSSWALK_PRIVATE_TOO_BIG")
    h=sha(blob)
    if persist:
        path=f"{ROOT}/audits/{h}.json"
        vault._put_small_immutable(path,blob,h)
        if vault._get_small(path,12000)!=blob:
            raise ValueError("L2_CROSSWALK_PRIVATE_READBACK_FAIL")
    safe={
        "stage":"V38_L2_SELF_VS_INDEPENDENT_CRITICS_NO_MODEL",
        "crosswalk_sha256":h,
        "self_declared_status":status,
        "self_setup_sentence_id":result["self_setup_sentence_id"],
        "self_payoff_sentence_id":result["self_payoff_sentence_id"],
        "self_setup_pct":result["self_setup_pct"],
        "self_payoff_pct":result["self_payoff_pct"],
        "examiner_overlap":rows,
        "no_literary_progress_conclusion":True,
        "model_calls":0,"formal_promotion":False,
    }
    print(json.dumps(safe,ensure_ascii=False,sort_keys=True))
    return result

if __name__=="__main__":
    compare(R2StudyVault(R2Config.from_environment()))
