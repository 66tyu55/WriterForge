"""Independent WF V81 six-chapter R2 source/learning-chain examination.

Examiner runs in a fresh Railway container with only WF_API_TOKEN;
DEEPSEEK_API_KEY/WF_INDEX_UPLOAD_TOKEN are removed before WF imports.

Recompute chapters 7..12 from the verified original bytes. Re-fetch every
immutable LEARN first-read unit/seal/analysis plus every chapter experience
and cross-chapter progress pointer from R2. Verify that chapter7's previous
strategy really traces back to the V80 chapter6 experience SHA.

This proves technical provenance and that WF's analysis cites seen units;
it is NOT proof of valid literary interpretations or actual improvement.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json

from .r2_learn_journal import identity,hexdigest
from .wf_b01_prefix_prepare import _split_into_ordered_units

BATCH_ID="WF-V81-150K-20261019-CH7-12"
PREVIOUS_CH6_EXP_SHA="1d0ee736b199f9af4c04543ba4d7d620ca8e1565b31b25ca673bef610c2b2d9d"
MAX_BATCH_TOKENS=150000
FIRST=7
LAST=12

class WFNewChapterAuditError(RuntimeError):
    pass

def need(condition,code):
    if not condition:raise WFNewChapterAuditError(code)


def audit_next_chapters(*,reader,original_path,source_key,source_sha,
                        chapters,final_batch_sha,previous_experience_sha=
                        PREVIOUS_CH6_EXP_SHA):
    need(reader.read_only is True and reader.writer is None,
         "WF_V81_AUDITOR_NOT_READER_ONLY")
    need(len(chapters)>=LAST,"WF_V81_AUDITOR_NO_FROZEN_CHAPTERS")
    prev_doc=json.loads(reader._get_content(previous_experience_sha))
    need(prev_doc.get("format")=="wf.learn.experience.v80" and
         prev_doc.get("chapter")==6 and
         prev_doc.get("source_sha256")==source_sha and
         prev_doc.get("source_key_sha256")==hexdigest(source_key.encode()) and
         prev_doc.get("literary_quality_independently_verified") is False,
         "WF_V81_AUDITOR_PREVIOUS_EXPERIENCE_CHANGED")
    prev_strategy=prev_doc.get("reflection",{}).get("next_strategy")
    need(isinstance(prev_strategy,str) and len(prev_strategy)>0,
         "WF_V81_AUDITOR_CH6_REFLECTION_EMPTY")

    snapshots=[]
    ref=final_batch_sha
    visited=set()
    while ref:
        need(isinstance(ref,str) and len(ref)==64 and ref not in visited,
             "WF_V81_AUDITOR_BATCH_POINTER_INVALID")
        visited.add(ref)
        raw=reader._get_content(ref)
        doc=json.loads(raw)
        need(doc.get("format")=="wf.learn.150k-batch-progress.v80" and
             doc.get("batch_id")==BATCH_ID and
             doc.get("source_sha256")==source_sha and
             doc.get("source_key_sha256")==hexdigest(source_key.encode()) and
             doc.get("mastery_graduation_approved") is False and
             doc.get("per_batch_total_token_cap")==MAX_BATCH_TOKENS,
             "WF_V81_AUDITOR_CHECKPOINT_WRONG_SOURCE_OR_BUDGET")
        snapshots.append(doc)
        ref=doc.get("previous_batch_pointer_sha256")
        need(len(snapshots)<=6,"WF_V81_AUDITOR_MORE_THAN_SIX_CHAPTERS")
    snapshots.reverse()
    need([s["last_completed_chapter"] for s in snapshots]==
         list(range(FIRST,FIRST+len(snapshots))) and
         len(snapshots)>=1,
         "WF_V81_AUDITOR_CHAPTERS_SKIPPED")
    last=snapshots[-1]
    need(last["journal_checkpoint_sha256"]==reader.checkpoint_sha,
         "WF_V81_AUDITOR_JOURNAL_NOT_AT_FINAL_POINTER")
    total=last["reported_total_input_tokens"]+last[
        "reported_total_output_tokens"]
    need(0<=total<=MAX_BATCH_TOKENS and
         last["conservative_tokens_committed_or_held"]<=MAX_BATCH_TOKENS and
         last["reported_calls"]<=96,
         "WF_V81_AUDITOR_TOKEN_OR_CALL_CAP_INVALID")
    prior_experience=previous_experience_sha
    proofs=[]
    with Path(original_path).open(
            "r",encoding="gb18030",errors="strict",newline=None) as fp:
        for chapter_state in snapshots:
            ordinal=chapter_state["last_completed_chapter"]
            original=chapters[ordinal-1]
            receipt=chapter_state["chapter_receipt"]
            need(receipt["chapter"]==ordinal and
                 receipt["chapter_body_sha256"]==original.body_sha256 and
                 receipt["chapter_characters"]==original.body_characters and
                 receipt["previous_V79_early_analysis_flag"] is False and
                 receipt["strict_full_chapter_pass_a_before_any_pass_b"]
                    is True and
                 receipt["previous_experience_sha256_used_in_prompts"]==
                    prior_experience,
                 "WF_V81_AUDITOR_CHAPTER_OR_EXPERIENCE_MISMATCH")
            fp.seek(original.start_cookie)
            lines=[]
            while fp.tell()<original.end_cookie:
                line=fp.readline()
                need(bool(line),"WF_V81_AUDITOR_ORIGINAL_EOF")
                lines.append(line)
            original_body="".join(lines)
            need(hexdigest(original_body.encode("utf8"))==
                 original.body_sha256 and
                 len(original_body)==original.body_characters,
                 "WF_V81_AUDITOR_ORIGINAL_BODY_SHA_INVALID")
            source_units=_split_into_ordered_units(original_body)
            need(len(source_units)==receipt["unit_count"],
                 "WF_V81_AUDITOR_SOURCE_UNITS_NOT_COMPLETE")
            ident=identity(source_key=source_key,source_sha=source_sha,
                           chapter=ordinal,
                           chapter_body_sha=original.body_sha256)
            prior_unit=None
            for position,unit in enumerate(source_units,1):
                first=reader.fetch_event(
                    ident=ident,stage="first_read",unit=position)
                need(first and first["doc"]["source_unit_sha256"]==
                     hexdigest(unit.encode("utf8")) and
                     first["doc"]["previous_event_sha256"]==prior_unit and
                     first["doc"]["future_source_seen"] is False,
                     "WF_V81_AUDITOR_SOURCE_SEQUENCE_FAILED")
                prior_unit=first["event_sha256"]
            seal=reader.fetch_event(ident=ident,stage="seal")
            need(seal and
                 seal["doc"]["units_read"]==len(source_units) and
                 seal["doc"]["last_first_read_sha256"]==prior_unit and
                 seal["event_sha256"]==receipt["first_read_seal_sha256"],
                 "WF_V81_AUDITOR_FULL_FIRST_READ_NOT_SEALED")
            analysis=reader.fetch_event(ident=ident,stage="analysis")
            need(analysis and
                 analysis["doc"]["first_read_seal_sha256"]==
                     seal["event_sha256"] and
                 analysis["event_sha256"]==
                     receipt["final_chapter_analysis_sha256"],
                 "WF_V81_AUDITOR_ANALYSIS_BEFORE_PASS_A_OR_WRONG_SOURCE")
            mechs=analysis["doc"]["mechanisms"]
            need(1<=len(mechs)<=6,"WF_V81_AUDITOR_NO_MECHANISM")
            for mechanism in mechs:
                unit_idx=mechanism["unit"]-1
                need(0<=unit_idx<len(source_units) and
                     mechanism["evidence_unit_sha256"]==
                     hexdigest(source_units[unit_idx].encode("utf8")),
                     "WF_V81_AUDITOR_ANALYSIS_UNREAD_REFERENCE")
            experience=json.loads(reader._get_content(
                receipt["experience_sha256"]))
            need(experience.get("format")=="wf.learn.experience.v80" and
                 experience.get("source_sha256")==source_sha and
                 experience.get("source_key_sha256")==hexdigest(source_key.encode())
                 and experience.get("chapter")==ordinal and
                 experience.get("analysis_sha256")==
                    receipt["final_chapter_analysis_sha256"] and
                 experience.get("previous_experience_sha256")==
                    prior_experience and
                 experience.get("literary_quality_independently_verified")
                    is False,
                 "WF_V81_AUDITOR_EXPERIENCE_CARD_CHAIN_INVALID")
            next_strategy=experience.get("reflection",{}).get("next_strategy")
            need(isinstance(next_strategy,str) and next_strategy,
                 "WF_V81_AUDITOR_REFLECTION_MISSING")
            prior_experience=receipt["experience_sha256"]
            need(chapter_state["latest_experience_sha256"]==prior_experience,
                 "WF_V81_AUDITOR_BATCH_POINTER_EXPERIENCE_MISSING")
            proofs.append({
               "chapter":ordinal,
               "source_units_independently_verified":len(source_units),
               "full_source_coverage":True,
               "all_first_reads_before_analysis":True,
               "prior_experience_r2_link_verified":True,
               "experience_sha256":prior_experience,
            })
    return {
       "status":"WF_V81_FRESH_READER_ONLY_CHAPTER7_FORWARD_AUDIT_PASSED",
       "original_sha256":source_sha,
       "last_batch_sha256":final_batch_sha,
       "last_journal_sha256":reader.checkpoint_sha,
       "source_complete_new_chapters":len(proofs),
       "chapter_evidence":proofs,
       "prior_chapter6_experience_sha256":previous_experience_sha,
       "chapter7_received_previous_experience_ref":True,
       "previous_strategy_sha256":sha256(prev_strategy.encode()).hexdigest(),
       "provider_reported_total_tokens":total,
       "batch_token_budget":MAX_BATCH_TOKENS,
       "examiner_paid_api_calls":0,
       "examiner_r2_writes":0,
       "literary_quality_verified":False,
       "future_prompt_content_independently_audited":False,
       "reading_strategy_improved_by_experience":None,
       "novel_prose_exposed_in_public_report":False,
       "mastery_level_changed":False,
    }
