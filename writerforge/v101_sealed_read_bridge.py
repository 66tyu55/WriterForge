"""V101 opt-in real WF post-PASS-A comprehension using EXISTING R2 CAS.

Every actual LLM call costs a bounded, preregistered request. This code never
runs from V80 legacy batches unless explicitly called in LEARN. Raw model
answers are saved privately BEFORE validation, with no network retries.
"""
from __future__ import annotations
from hashlib import sha256
import json
import re

from .runtime import RuntimeEngine,Mode
from .r2_learn_journal import identity
from .v101_narrative_reader import (
    SYSTEM,MAX_HISTORY,MAX_CONTEXT_CHARS,packed,digest,
    validate_narrative,reader_context,check_history,model_reading_prompt,
    V101ReadingError,
)

SHA=re.compile(r"[0-9a-f]{64}\Z")
MODEL_CAP=4100
MAX_PRIVATE_RESPONSE=21000
MAX_PROMPT_CHARS=90000
MAX_FIRST_READ_UNITS=80


def require(ok,code):
    if not ok:
        raise V101ReadingError(code)


def _json(raw):
    try:
        def pairs_unique(pairs):
            doc={}
            for name,value in pairs:
                if name in doc:raise ValueError("duplicate key")
                doc[name]=value
            return doc
        result=json.loads(raw.decode("utf8","strict"),
            object_pairs_hook=pairs_unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("bad constant")))
        require(type(result) is dict,"WF101_PRIOR_RECEIPT_NOT_OBJECT")
        return result
    except (UnicodeError,ValueError,TypeError):
        raise V101ReadingError("WF101_PRIOR_RECEIPT_INVALID_JSON") from None


def _history_from_cas(*,journal,pointer,story_id,source_sha256,next_chapter):
    require(pointer is None or (type(pointer) is str and
            SHA.fullmatch(pointer) is not None),
            "WF101_PREVIOUS_POINTER_INVALID")
    seen=set()
    newest=[]
    cur=pointer
    newest_chapter=next_chapter
    while cur is not None and len(newest)<MAX_HISTORY:
        require(cur not in seen,"WF101_CAS_HISTORY_CYCLE")
        seen.add(cur)
        raw=journal._get_content(cur)
        require(digest(raw)==cur,"WF101_CAS_HISTORY_SHA_MISMATCH")
        old=_json(raw)
        require(old.get("format")=="wf.learn.narrative-comprehension.v101"
                and old.get("story_id")==story_id
                and old.get("source_sha256")==source_sha256
                and type(old.get("chapter")) is int
                and 1<=old["chapter"]<newest_chapter
                and old.get("new_canonical_facts")==0
                and old.get("literary_graduation") is False,
                "WF101_PRIOR_STORY_OR_READING_FRONTIER_INVALID")
        newest.append(old)
        newest_chapter=old["chapter"]
        cur=old.get("previous_reader_receipt_sha256")
    history=tuple(reversed(newest))
    check_history(history,story_id=story_id,
        source_sha256=source_sha256,before_chapter=next_chapter)
    return history


def reader_memory_from_private_cas(*,journal,pointer,story_id,
                                   source_sha256,next_chapter):
    """Derive a bounded conditional hypothesis view from signed private CAS."""
    hist=_history_from_cas(journal=journal,pointer=pointer,
        story_id=story_id,source_sha256=source_sha256,
        next_chapter=next_chapter)
    return reader_context(history=hist,story_id=story_id,
        source_sha256=source_sha256,before_chapter=next_chapter)


def read_sealed_narrative(*,batch,chapter,windows,runtime,story_id,
                          previous_reader_receipt_sha256=None):
    """One manual LEARN call per newly sealed chapter, zero implicit retry.

    Existing WriterForge WFLargeChapterBatch.complete() is NOT called here.
    This function never changes original V80/V92 records or FactJournal.
    """
    from .v80_large_chapter_batch import WFLargeChapterBatch
    from .v79_provisional_r2_cas_journal import WFProvisionalR2CASJournal
    require(isinstance(runtime,RuntimeEngine),
            "WF101_EXPLICIT_RUNTIME_REQUIRED")
    runtime.require(Mode.LEARN)
    require(isinstance(batch,WFLargeChapterBatch) and
            isinstance(batch.journal,WFProvisionalR2CASJournal) and
            batch.model.budget.max_total_tokens==150000,
            "WF101_REAL_LEARN_OWNER_OR_BUDGET_MISSING")
    require(type(story_id) is str and re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_-]{1,79}",story_id) is not None,
            "WF101_STORY_ID_INVALID")
    require(hasattr(chapter,"ordinal") and type(chapter.ordinal) is int and
            chapter.ordinal>=2 and hasattr(chapter,"body_sha256"),
            "WF101_CHAPTER_ONE_MIXED_PILOT_NOT_ELIGIBLE")
    require(type(windows) in (tuple,list) and 1<=len(windows)<=MAX_FIRST_READ_UNITS
            and all(type(w) is str for w in windows),
            "WF101_SOURCE_WINDOWS_NOT_READ")
    require(any(r["chapter"]==chapter.ordinal and
                r["chapter_body_sha256"]==chapter.body_sha256
                for r in batch.finished_chapters),
            "WF101_NOT_NEWLY_COMPLETED_WF_CHAPTER")
    ident=identity(source_key=batch.key,source_sha=batch.source_sha,
                  chapter=chapter.ordinal,chapter_body_sha=chapter.body_sha256)
    journal=batch.journal
    journal.require_writer_ready()
    # Keep the older V80 strict source chain as the only reading authority.
    prior=None
    for unit_no,body in enumerate(windows,1):
        read=journal.fetch_event(ident=ident,stage="first_read",unit=unit_no)
        require(read is not None and
                read["doc"].get("source_unit_sha256")==
                    digest(body.encode("utf8"))
                and read["doc"].get("previous_event_sha256")==prior,
                "WF101_PASS_A_UNSEALED_OR_SOURCE_CHANGED")
        prior=read["event_sha256"]
    seal=journal.fetch_event(ident=ident,stage="seal")
    require(seal is not None and
            seal["doc"].get("units_read")==len(windows) and
            seal["doc"].get("last_first_read_sha256")==prior and
            seal["doc"].get("future_source_seen") is False,
            "WF101_PASS_A_CURRENT_FULL_SEAL_MISSING")
    history=_history_from_cas(journal=journal,
        pointer=previous_reader_receipt_sha256,
        story_id=story_id,source_sha256=batch.source_sha,
        next_chapter=chapter.ordinal)
    # Previous reader results are hypotheses, not retrospective truth.
    context=reader_context(history=history,story_id=story_id,
        source_sha256=batch.source_sha,before_chapter=chapter.ordinal)
    prompt=model_reading_prompt(source_windows=windows,prior_context=context)
    require(len(prompt)<=MAX_PROMPT_CHARS,
            "WF101_MODEL_READING_PROMPT_BUDGET_EXCEEDED")
    pre={
        "format":"wf.learn.narrative-comprehension-authorization.v101",
        "story_id":story_id,"source_sha256":batch.source_sha,
        "source_key_sha256":batch.keyhash,
        "chapter":chapter.ordinal,
        "chapter_body_sha256":chapter.body_sha256,
        "first_read_seal_sha256":seal["event_sha256"],
        "previous_reader_receipt_sha256":previous_reader_receipt_sha256,
        "prompt_sha256":digest(prompt.encode("utf8")),
        "model_name":batch.model.name,
        "max_reserved_model_output_tokens":MODEL_CAP,
        "no_auto_retry":True,"auto_training_off":True,
        "model_calls_before_this_precommit":batch.model.budget.calls_reserved,
        "self_literary_grade_disallowed":True,
        "no_canonical_or_factjournal_writes":True,
    }
    pre_raw=packed(pre)
    pre_sha,created=journal._put_content(pre_raw)
    require(created,"WF101_PRECOMMIT_ALREADY_EXISTS_REFUSE_REPEAT_MODEL_COST")
    # This is a genuinely NEW model request when explicitly opted in.
    # DeepSeekFlashModel reserves its own real 150k shared budget before HTTP.
    response=batch.model.ask_json(role="craft_analysis",system=SYSTEM,
                                   user=prompt,max_tokens=MODEL_CAP)
    response_raw=packed({
        "format":"wf.learn.unmodified-reader-model-answer.v101",
        "precommit_sha256":pre_sha,
        "original_response":response,
        "unvalidated_before_persistence":True,
    })
    require(len(response_raw)<=MAX_PRIVATE_RESPONSE+4096,
            "WF101_MODEL_ANSWER_TOO_LONG_NO_RETRY")
    raw_sha,_=journal._put_content(response_raw)
    require(journal._get_content(raw_sha)==response_raw,
            "WF101_MODEL_ANSWER_PRIVATE_CAS_READBACK_FAILED")
    note=validate_narrative(story_id=story_id,
        source_sha256=batch.source_sha,chapter=chapter.ordinal,
        source_windows=windows,model_output=response,prior_history=history)
    note.update({
        "first_read_seal_sha256":seal["event_sha256"],
        "precommit_sha256":pre_sha,
        "raw_answer_cas_sha256":raw_sha,
        "independent_human_literary_review":"NOT_PERFORMED",
        "model_calls_this_opt_in_reader":1,
    })
    note_raw=packed(note)
    note_sha,_=journal._put_content(note_raw)
    require(journal._get_content(note_sha)==note_raw,
            "WF101_NARRATIVE_NOTE_PRIVATE_CAS_READBACK_FAILED")
    return {
        "status":"WF101_WF_OWN_NARRATIVE_READING_CANDIDATE_SAVED",
        "reader_receipt_cas_sha256":note_sha,
        "precommit_cas_sha256":pre_sha,
        "model_raw_answer_cas_sha256":raw_sha,
        "characters_observed":len(note["cast"]),
        "relation_hypotheses":len(note["relationships"]),
        "plot_hypotheses":len(note["plot"]),
        "prose_quality_hypotheses":len(note["craft"]),
        "future_chapter_source_seen":False,
        "human_literary_verified":False,"model_calls":1,
        "original_source_text_not_in_log":True,
        "previous_15_chapters_unchanged":True,
    }
