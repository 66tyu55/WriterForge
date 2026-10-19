"""V80 independent read-only examiner for the expanded WF training batch.

Never trusts model-reported self-grades: use frozen private-source SHA and
fresh R2 Reader-only CAS fetches to verify every first-read unit, ordering,
A seal, analysis evidence, and experience cards. Chapter1 has the old V79
three-unit pilot with early analysis; that exception is preserved.
Literary quality and exact future-prompt non-exposure remain unproven.
"""
from __future__ import annotations

import json
from hashlib import sha256

from .r2_learn_journal import identity,hexdigest
from .wf_b01_prefix_prepare import _split_into_ordered_units

MAX_TOKEN_BATCH=150000

class WFReadOnlyExamError(RuntimeError):
    pass

def need(ok,code):
    if not ok:
        raise WFReadOnlyExamError(code)


def audit_extended_batch(reader,*,source_path,original_key,
                         source_sha256,chapters,last_batch_sha):
    need(reader.read_only is True and reader.writer is None,
         "WF_V80_EXAM_READER_NOT_READ_ONLY")
    snapshots=[]
    seen=set()
    pointer=last_batch_sha
    while pointer:
        need(pointer not in seen and len(pointer)==64 and
             len(snapshots)<6,
             "WF_V80_EXAM_INVALID_CHECKPOINT_CHAIN")
        seen.add(pointer)
        node=json.loads(reader._get_content(pointer))
        need(node.get("format")=="wf.learn.150k-batch-progress.v80"
             and node.get("source_sha256")==source_sha256
             and node.get("source_key_sha256")==
                 hexdigest(original_key.encode("utf8"))
             and node.get("per_batch_total_token_cap")==MAX_TOKEN_BATCH
             and node.get("mastery_graduation_approved") is False,
             "WF_V80_EXAM_BATCH_IDENTITY_INVALID")
        snapshots.append(node)
        pointer=node.get("previous_batch_pointer_sha256")
    snapshots.reverse()
    need(snapshots and
         len(snapshots)<=len(chapters) and
         [v["last_completed_chapter"] for v in snapshots]==
         list(range(1,len(snapshots)+1)),
         "WF_V80_EXAM_BATCH_CHAPTERS_NOT_SEQUENTIAL")
    latest=snapshots[-1]
    need(latest["journal_checkpoint_sha256"]==reader.checkpoint_sha,
         "WF_V80_EXAM_JOURNAL_NOT_LAST_SNAPSHOT")
    need(latest["reported_total_input_tokens"]+
         latest["reported_total_output_tokens"]<=MAX_TOKEN_BATCH and
         latest["conservative_tokens_committed_or_held"]<=MAX_TOKEN_BATCH,
         "WF_V80_EXAM_TOKEN_CAP_EXCEEDED")
    summaries=[]
    earlier_exp=None
    with open(source_path,"r",encoding="gb18030",errors="strict",
              newline=None) as stream:
        for source_ch,node in zip(chapters,snapshots):
            r=node["chapter_receipt"]
            need(r["chapter"]==source_ch.ordinal and
                 r["chapter_body_sha256"]==source_ch.body_sha256 and
                 r["chapter_characters"]==source_ch.body_characters,
                 "WF_V80_EXAM_WRONG_CHAPTER_SOURCE")
            stream.seek(source_ch.start_cookie)
            lines=[]
            while stream.tell()<source_ch.end_cookie:
                line=stream.readline()
                need(bool(line),"WF_V80_EXAM_SOURCE_EOF")
                lines.append(line)
            body="".join(lines)
            need(hexdigest(body.encode("utf8"))==
                 source_ch.body_sha256,
                 "WF_V80_EXAM_CHAPTER_BODY_SHA_FAILED")
            units=_split_into_ordered_units(body)
            need(len(units)==r["unit_count"],
                 "WF_V80_EXAM_UNIT_COUNT_WRONG")
            ident=identity(
                source_key=original_key,source_sha=source_sha256,
                chapter=source_ch.ordinal,
                chapter_body_sha=source_ch.body_sha256)
            prev=None
            for i,unit in enumerate(units,1):
                event=reader.fetch_event(
                    ident=ident,stage="first_read",unit=i)
                need(event is not None and
                     event["doc"]["source_unit_sha256"]==
                         hexdigest(unit.encode("utf8")) and
                     event["doc"]["previous_event_sha256"]==prev and
                     event["doc"]["future_source_seen"] is False,
                     "WF_V80_EXAM_FIRST_READ_ORDER_OR_SOURCE_FALSE")
                prev=event["event_sha256"]
            seal=reader.fetch_event(ident=ident,stage="seal")
            need(seal and seal["event_sha256"]==
                 r["first_read_seal_sha256"],
                 "WF_V80_EXAM_SOURCE_SEAL_WRONG")
            if source_ch.ordinal==1:
                need(r["previous_V79_early_analysis_flag"] is True
                     and r["strict_full_chapter_pass_a_before_any_pass_b"]
                     is False and seal["doc"]["units_read"]==3,
                     "WF_V80_EXAM_PILOT_PURITY_FALSIFIED")
                extra=json.loads(reader._get_content(
                    r["final_chapter_analysis_sha256"]))
                need(extra.get("format")==
                     "wf.learn.mixed-pilot-analysis.v80" and
                     extra.get("early_pilot_analysis_preceded_final_unit")
                     is True and
                     extra.get("fully_read_unit_hashes")==
                     [hexdigest(unit.encode()) for unit in units],
                     "WF_V80_EXAM_PILOT_CONTINUATION_WRONG")
                analysis=extra["mechanisms"]
                pure=False
            else:
                need(seal["doc"]["units_read"]==len(units) and
                     seal["doc"]["last_first_read_sha256"]==prev and
                     r["strict_full_chapter_pass_a_before_any_pass_b"] is True,
                     "WF_V80_EXAM_FULL_FIRST_READ_NOT_SIGNED")
                b=reader.fetch_event(ident=ident,stage="analysis")
                need(b and b["event_sha256"]==
                     r["final_chapter_analysis_sha256"] and
                     b["doc"]["first_read_seal_sha256"]==
                     seal["event_sha256"],
                     "WF_V80_EXAM_LATE_ANALYSIS_NOT_SIGNED")
                analysis=b["doc"]["mechanisms"]
                pure=True
            need(analysis and len(analysis)<=6,
                 "WF_V80_EXAM_NOTHING_ANALYZED")
            for m in analysis:
                idx=m["unit"]-1
                need(0<=idx<len(units) and
                     m["evidence_unit_sha256"]==
                     hexdigest(units[idx].encode()),
                     "WF_V80_EXAM_LITERARY_EVIDENCE_FORGED")
            experience=json.loads(reader._get_content(
                r["experience_sha256"]))
            need(experience.get("format")=="wf.learn.experience.v80"
                 and experience.get("source_sha256")==source_sha256
                 and experience.get("chapter")==source_ch.ordinal
                 and experience.get("analysis_sha256")==
                     r["final_chapter_analysis_sha256"]
                 and experience.get("previous_experience_sha256")==earlier_exp,
                 "WF_V80_EXAM_EXPERIENCE_IDENTITY_BROKEN")
            if source_ch.ordinal>1:
                need(r["previous_experience_sha256_used_in_prompts"]==
                     earlier_exp,
                     "WF_V80_EXAM_NO_PREVIOUS_EXPERIENCE_TRANSFER")
            earlier_exp=r["experience_sha256"]
            summaries.append({
                "chapter":source_ch.ordinal,
                "signed_source_units":len(units),
                "all_original_source_units_accounted_for":True,
                "clean_first_read_before_any_analysis":pure,
                "model_experience_sha256":earlier_exp,
            })
    return {
        "status":"WF_V80_INDEPENDENT_R2_FULL_CHAPTER_PROVENANCE_PASSED",
        "source_sha256":source_sha256,
        "last_batch_sha256":last_batch_sha,
        "verified_chapters":summaries,
        "source_complete_chapters":len(summaries),
        "clean_pass_a_before_pass_b_chapters":sum(
            item["clean_first_read_before_any_analysis"] for item in summaries),
        "early_V79_chapter1_partial_analysis_explicitly_retained":True,
        "total_provider_reported_tokens":
            latest["reported_total_input_tokens"]+
            latest["reported_total_output_tokens"],
        "batch_budget_tokens":MAX_TOKEN_BATCH,
        "reader_only_proven":True,
        "model_calls_by_examiner":0,
        "r2_writes_by_examiner":0,
        "literary_mastery_certified":False,
        "human_reader_truth_certified":False,
        "model_prompt_future_units_independently_audited":False,
        "DeepSeek_dashboard_fee_reconciled":False,
    }
