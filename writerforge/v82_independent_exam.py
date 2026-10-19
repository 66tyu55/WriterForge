"""V82 independent R2-only examiner for full chapters 7-10.

This examiner gets source chapter units directly from the original frozen
private R2 novel, verifies each first-read immutable CAS JSON and R2 SHA,
each PASS A seal and source-bound PASS B, and every cross-chapter experience
chain. Its R2 journal is explicitly read-only and its production process
must remove DeepSeek and writer credentials before import.

The V82 first checkpoint MUST attach to V81's independently verified
chapter-10 progress and prior experience. V82 is an independent token batch:
the 150,000 maximum does NOT mean the two budgets are summed.

A model's self-reported question, reaction, craft effect and next_strategy
are NOT scientific truth or a quality grade. Event hashes cannot alone prove
the actual external model prompts excluded future chapter content, and a
linked strategy does NOT prove literary transfer.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import re

from .r2_learn_journal import identity,hexdigest
from .wf_b01_prefix_prepare import _split_into_ordered_units

FORMAT="wf.learn.150k-batch-progress.v80"
BATCH_ID="WF-V82-CH11-15-150K"
EXPERIENCE_FORMAT="wf.learn.experience.v80"
MAX_TOTAL_TOKENS=150000
MAX_CALLS=96
START_CHAPTER=11
END_CHAPTER=15
SHA=re.compile(r"^[a-f0-9]{64}$")


class WFV82ExamError(ValueError):
    pass


def require(flag,reason):
    if not flag:
        raise WFV82ExamError(reason)


def _sha(value):
    return isinstance(value,str) and SHA.fullmatch(value) is not None


def _json_from_r2(reader,sha):
    require(_sha(sha),"WF_V82_EXAM_POINTER_NOT_SHA256")
    raw=reader._get_content(sha)  # verifies real R2 HEAD/Range + SHA
    try:
        doc=json.loads(raw.decode("utf-8"))
    except (ValueError,UnicodeError):
        raise WFV82ExamError("WF_V82_EXAM_R2_JSON_INVALID") from None
    require(isinstance(doc,dict),
            "WF_V82_EXAM_R2_JSON_NOT_OBJECT")
    return doc


def examine_v82(*,reader,original_key,source_sha,source_path,
                source_chapters,final_batch_pointer,prior_v81_batch_pointer,
                prior_v81_journal_pointer,prior_chapter10_experience,
                expected_start=START_CHAPTER,expected_end=END_CHAPTER,
                source_encoding="gb18030"):
    """Return metadata-only independent verification, not a literary grade."""
    require(reader.read_only is True and reader.writer is None,
            "WF_V82_EXAM_NOT_READER_ONLY")
    require(_sha(source_sha) and
            all(_sha(s) for s in (
                final_batch_pointer,prior_v81_batch_pointer,
                prior_v81_journal_pointer,prior_chapter10_experience)),
            "WF_V82_EXAM_INVALID_ORIGINAL_OR_POINTER_SHA")
    require(type(expected_start) is int and type(expected_end) is int and
            expected_start==START_CHAPTER and
            expected_start<=expected_end<=END_CHAPTER and
            len(source_chapters)>=expected_end,
            "WF_V82_EXAM_FROZEN_CHAPTER_RANGE_CHANGED")
    require(source_encoding in ("gb18030","utf-8","utf-8-sig"),
            "WF_V82_EXAM_ENCODING_NOT_VERIFIED")
    key_sha=hexdigest(original_key.encode("utf8"))
    prior=_json_from_r2(reader,prior_v81_batch_pointer)
    require(prior.get("format")==FORMAT and
            prior.get("last_completed_chapter")==10 and
            prior.get("source_sha256")==source_sha and
            prior.get("source_key_sha256")==key_sha and
            prior.get("journal_checkpoint_sha256")==prior_v81_journal_pointer and
            prior.get("latest_experience_sha256")==prior_chapter10_experience and
            prior.get("mastery_graduation_approved") is False,
            "WF_V82_EXAM_V81_CHAPTER10_ANCHOR_INVALID")
    prior_exp=_json_from_r2(reader,prior_chapter10_experience)
    require(prior_exp.get("format")==EXPERIENCE_FORMAT and
            prior_exp.get("source_sha256")==source_sha and
            prior_exp.get("chapter")==10 and
            prior_exp.get("literary_quality_independently_verified") is False and
            isinstance(prior_exp.get("reflection"),dict) and
            isinstance(prior_exp["reflection"].get("next_strategy"),str) and
            len(prior_exp["reflection"]["next_strategy"])>0,
            "WF_V82_EXAM_PREVIOUS_EXPERIENCE_UNVERIFIED")

    snapshots=[]
    cursor=final_batch_pointer
    seen=set()
    while cursor!=prior_v81_batch_pointer:
        require(_sha(cursor) and cursor not in seen and
                len(snapshots)<(expected_end-expected_start+1),
                "WF_V82_EXAM_BATCH_CHAIN_BROKEN_OR_CYCLE")
        seen.add(cursor)
        state=_json_from_r2(reader,cursor)
        require(state.get("format")==FORMAT and
                state.get("batch_id")==BATCH_ID and
                state.get("source_sha256")==source_sha and
                state.get("source_key_sha256")==key_sha and
                state.get("per_batch_total_token_cap")==MAX_TOTAL_TOKENS and
                state.get("mastery_graduation_approved") is False,
                "WF_V82_EXAM_BATCH_WRONG_ID_OR_SOURCE")
        snapshots.append(state)
        cursor=state.get("previous_batch_pointer_sha256")
    snapshots.reverse()
    chapter_ids=list(range(expected_start,expected_end+1))
    require([v.get("last_completed_chapter") for v in snapshots]==chapter_ids,
            "WF_V82_EXAM_BATCH_CHAPTER_MISSING_OR_REORDERED")
    final=snapshots[-1]
    require(final.get("journal_checkpoint_sha256")==reader.checkpoint_sha,
            "WF_V82_EXAM_FINAL_R2_JOURNAL_POINTER_MISMATCH")
    counted=final.get("reported_total_input_tokens")
    generated=final.get("reported_total_output_tokens")
    held=final.get("conservative_tokens_committed_or_held")
    calls=final.get("reported_calls")
    require(all(type(x) is int and x>=0 for x in
                (counted,generated,held,calls)) and
            counted+generated<=MAX_TOTAL_TOKENS and
            held<=MAX_TOTAL_TOKENS and calls<=MAX_CALLS,
            "WF_V82_EXAM_150K_BUDGET_INVALID")
    previous_input=previous_output=previous_calls=0
    for state in snapshots:
        p=state.get("reported_total_input_tokens")
        o=state.get("reported_total_output_tokens")
        c=state.get("reported_calls")
        require(all(type(x) is int for x in (p,o,c)) and
                p>=previous_input and o>=previous_output and
                c>=previous_calls and
                p+o<=MAX_TOTAL_TOKENS,
                "WF_V82_EXAM_TOKEN_COUNTER_NONMONOTONIC")
        previous_input,previous_output,previous_calls=p,o,c

    results=[]
    earlier_exp=prior_chapter10_experience
    with Path(source_path).open(
        "r",encoding=source_encoding,errors="strict",newline=None
    ) as source:
        for chap_no,state in zip(chapter_ids,snapshots):
            chapter=source_chapters[chap_no-1]
            rec=state.get("chapter_receipt")
            require(isinstance(rec,dict) and
                    chapter.ordinal==chap_no and
                    rec.get("chapter")==chap_no and
                    rec.get("chapter_body_sha256")==chapter.body_sha256 and
                    rec.get("chapter_characters")==chapter.body_characters,
                    "WF_V82_EXAM_CHAPTER_SOURCE_SHA_OR_METADATA_MISMATCH")
            source.seek(chapter.start_cookie)
            lines=[]
            while source.tell()<chapter.end_cookie:
                line=source.readline()
                require(line,"WF_V82_EXAM_SOURCE_EOF")
                lines.append(line)
            require(source.tell()==chapter.end_cookie,
                    "WF_V82_EXAM_CHAPTER_SOURCE_RANGE_WRONG")
            body="".join(lines)
            require(len(body)==chapter.body_characters and
                    hexdigest(body.encode("utf8"))==chapter.body_sha256,
                    "WF_V82_EXAM_CHAPTER_ORIGINAL_CONTENT_CHANGED")
            units=_split_into_ordered_units(body)
            require(len(units)==rec.get("unit_count"),
                    "WF_V82_EXAM_UNIT_COUNT_NOT_COMPLETE")
            ident=identity(source_key=original_key,source_sha=source_sha,
                           chapter=chap_no,
                           chapter_body_sha=chapter.body_sha256)
            previous_event_sha=None
            for number,unit in enumerate(units,1):
                saved=reader.fetch_event(
                    ident=ident,stage="first_read",unit=number)
                require(saved is not None and
                        saved["doc"].get("source_unit_sha256")==
                        hexdigest(unit.encode("utf-8")) and
                        saved["doc"].get("previous_event_sha256")==
                        previous_event_sha and
                        saved["doc"].get("future_source_seen") is False,
                        "WF_V82_EXAM_FIRST_READ_SKIPPED_FORGED_OR_REORDERED")
                previous_event_sha=saved["event_sha256"]
            seal=reader.fetch_event(ident=ident,stage="seal")
            require(seal is not None and
                    seal["doc"].get("units_read")==len(units) and
                    seal["doc"].get("last_first_read_sha256")==
                    previous_event_sha and
                    seal["event_sha256"]==rec.get("first_read_seal_sha256") and
                    rec.get("strict_full_chapter_pass_a_before_any_pass_b") is True and
                    rec.get("previous_V79_early_analysis_flag") is False,
                    "WF_V82_EXAM_PASS_A_NOT_SEALED_BEFORE_B")
            analysis=reader.fetch_event(ident=ident,stage="analysis")
            require(analysis is not None and
                    analysis["doc"].get("first_read_seal_sha256")==
                    seal["event_sha256"] and
                    analysis["event_sha256"]==
                    rec.get("final_chapter_analysis_sha256"),
                    "WF_V82_EXAM_ANALYSIS_UNLINKED_FROM_SEAL")
            mechanisms=analysis["doc"].get("mechanisms")
            require(isinstance(mechanisms,list) and
                    1<=len(mechanisms)<=6,
                    "WF_V82_EXAM_NO_BOUNDED_CRAFT_EVIDENCE")
            for m in mechanisms:
                idx=m["unit"]-1
                require(0<=idx<len(units) and
                        m["evidence_unit_sha256"]==
                        hexdigest(units[idx].encode("utf8")),
                        "WF_V82_EXAM_CRAFT_CITATION_NOT_READ_FROM_SOURCE")
            experience=_json_from_r2(reader,rec["experience_sha256"])
            require(experience.get("format")==EXPERIENCE_FORMAT and
                    experience.get("source_sha256")==source_sha and
                    experience.get("chapter")==chap_no and
                    experience.get("analysis_sha256")==
                    analysis["event_sha256"] and
                    experience.get("previous_experience_sha256")==earlier_exp and
                    experience.get("literary_quality_independently_verified") is False and
                    rec.get("previous_experience_sha256_used_in_prompts")==
                    earlier_exp and
                    state.get("latest_experience_sha256")==
                    rec["experience_sha256"],
                    "WF_V82_EXAM_EXPERIENCE_CHAIN_OR_CROSS_CHAPTER_LINK_MISSING")
            earlier_exp=rec["experience_sha256"]
            results.append({
                "chapter":chap_no,
                "units_independently_matched":len(units),
                "all_source_units_present":True,
                "immutable_pass_a_then_pass_b_seal":True,
                "experience_link_to_prior_chapter":True,
                "experience_sha256":earlier_exp,
                "independent_literary_accuracy":False,
            })
    return {
        "status":"WF_V82_INDEPENDENT_R2_CH11_TO_15_PROVENANCE_PASSED",
        "training_source_sha256":source_sha,
        "training_source_key_sha256":key_sha,
        "v81_anchor_sha256":prior_v81_batch_pointer,
        "v82_batch_final_sha256":final_batch_pointer,
        "r2_journal_final_sha256":reader.checkpoint_sha,
        "v82_last_experience_sha256":earlier_exp,
        "examined_chapters":results,
        "full_chapters_source_covered":len(results),
        "source_units_verified":sum(r["units_independently_matched"] for r in results),
        "strict_pass_a_before_pass_b_chapters":len(results),
        "chapter10_experience_link_verified":True,
        "source_experience_continuity_proven":True,
        "actual_experience_improved_literary_quality_proven":False,
        "future_text_not_leaked_to_provider_independently_verified":False,
        "independent_literary_transfer_exam_passed":False,
        "model_calls_by_examiner":0,
        "r2_writes_by_examiner":0,
        "provider_input_tokens_from_r2_progress":counted,
        "provider_output_tokens_from_r2_progress":generated,
        "token_batch_ceiling":MAX_TOTAL_TOKENS,
        "provider_billing_portal_reconciled":False,
        "v49_literary_promotion_approved":False,
    }
