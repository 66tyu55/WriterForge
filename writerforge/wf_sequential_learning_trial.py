"""V75 WF owns a bounded sequential LEARN trial, NOT ChatGPT.

It processes exactly one *verified* chapter-window at a time. PASS A feeds
DeepSeek Flash only the currently unlocked unit; after every response the
private R2 journal must confirm an immutable event. PASS A is sealed in R2
before PASS B receives any source units or emits craft hypotheses.

This is a small protocol trial (2-3 source units), not a full chapter or
validated literary achievement. Full-book training remains blocked on
the V73 chapter conflict review and verified external data-transfer scope.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Iterable

from .deepseek_flash_model import DeepSeekFlashModel,DeepSeekFlashError
from .r2_learn_journal import (
    WFLearnJournal, WFLearnJournalError, hexdigest, reaction_schema,
    mechanism_schema, event_doc, identity,
)
from .runtime import RuntimeEngine, Mode

MAX_TRIAL_UNITS = 3
MAX_UNIT_CHARACTERS = 1700
MAX_ANALYST_PROMPT_CHARS = 8000

class WFSequentialLearnError(RuntimeError):
    pass

def require(ok,code):
    if not ok:raise WFSequentialLearnError(code)


class WFSequentialLearningTrial:
    """Host-level execution protocol; WF's DeepSeek client makes decisions."""

    def __init__(self,*,model:DeepSeekFlashModel,journal:WFLearnJournal,
                 original_key,source_sha,chapter,chapter_body_sha,
                 runtime=None):
        require(isinstance(model,DeepSeekFlashModel) and
                isinstance(journal,WFLearnJournal),
                "WF_LEARN_TRIAL_OWN_COMPONENTS_REQUIRED")
        self.model=model
        self.journal=journal
        self.rt=runtime if runtime is not None else RuntimeEngine()
        self.ident=identity(
            source_key=original_key,source_sha=source_sha,
            chapter=chapter,chapter_body_sha=chapter_body_sha)
        self._seal_sha=None
        self._unit_hashes=[]
        self._unit_texts=[]
        self._first_receipts=[]

    def first_read(self,units:Iterable[str],*,expected_unit_count:int):
        require(self._seal_sha is None and
                type(expected_unit_count) is int and
                2<=expected_unit_count<=MAX_TRIAL_UNITS,
                "WF_LEARN_TRIAL_SIZE_OR_STATE_INVALID")
        # Must authenticate a dedicated append-only R2 writer BEFORE asking
        # DeepSeek to process any portion of the private original.
        self.journal.require_writer_ready()
        self.rt.enter_learn()
        prev=None
        newly_written=0
        iterator=iter(units)
        try:
            for ordinal in range(1,expected_unit_count+1):
                try:piece=next(iterator)
                except StopIteration:
                    raise WFSequentialLearnError("WF_LEARN_TRIAL_SOURCE_MISSING") from None
                require(isinstance(piece,str) and
                        30<=len(piece)<=MAX_UNIT_CHARACTERS,
                        "WF_LEARN_TRIAL_SOURCE_WINDOW_INVALID")
                source_unit_sha=hexdigest(piece.encode("utf-8"))
                old=self.journal.fetch_event(
                    ident=self.ident,stage="first_read",unit=ordinal)
                if old is not None:
                    locked=old["doc"]
                    require(
                        locked["source_unit_sha256"]==source_unit_sha and
                        locked["previous_event_sha256"]==prev,
                        "WF_LEARN_RESUME_EXISTING_UNIT_SOURCE_CHANGED")
                    # R2 event is already sealed individually. Never ask the
                    # model to 'read for the first time' again after restart.
                    receipt={
                        "event_sha256":old["event_sha256"],
                        "unit":ordinal,"created":False,
                        "r2_reader_readback_verified":True,
                    }
                else:
                    # Only the CURRENT unlocked source unit goes to DeepSeek.
                    response=self.model.ask_json(
                        role="first_read",
                        system=(
                            "你是WriterForge自己的首次阅读者。"
                            "这仅是阅读片段试验，不是正式人类读者测量。"
                            "你只允许看当前一段，不得推断或杜撰未来章节。"
                            '仅输出JSON对象，必须恰好具有'
                            ' attention,curiosity,confusion,tension,'
                            'urge_to_continue 五个0至5整数，及'
                            ' question,prediction,what_changed 三个不超过160字字符串。'
                        ),
                        user=(
                            f"这是本章按序解锁的第{ordinal}段；"
                            "以下内容不可复述或复制到外部日志：\\n"+
                            piece
                        ),
                        max_tokens=400,
                    )
                    require(reaction_schema(response),
                            "WF_LEARN_TRIAL_FIRST_REACTION_INVALID")
                    receipt=self.journal.append_first_read(
                        ident=self.ident,unit=ordinal,
                        source_unit_sha=source_unit_sha,
                        previous_record_sha=prev,reaction=response)
                    newly_written+=1
                prev=receipt["event_sha256"]
                self._unit_hashes.append(source_unit_sha)
                self._unit_texts.append(piece)
                self._first_receipts.append(receipt)
            try:
                next(iterator)
            except StopIteration:
                pass
            else:
                raise WFSequentialLearnError("WF_LEARN_TRIAL_EXTRA_SOURCE_UNSEEN")
            old_seal=self.journal.fetch_event(
                ident=self.ident,stage="seal")
            if old_seal is None:
                sealed=self.journal.seal_first_read(
                    ident=self.ident,units=expected_unit_count,
                    last_record_sha=prev)
                self._seal_sha=sealed["event_sha256"]
            else:
                locked=old_seal["doc"]
                require(locked["units_read"]==expected_unit_count and
                        locked["last_first_read_sha256"]==prev,
                        "WF_LEARN_RESUME_SEAL_SOURCE_CHANGED")
                self._seal_sha=old_seal["event_sha256"]
            return {
               "status":"WF_LEARN_PASS_A_R2_LOCKED",
               "units_seen_in_order":len(self._unit_hashes),
               "first_read_events_stored":len(self._first_receipts),
               "first_read_events_new_this_run":newly_written,
               "model_repeat_reads_avoided":len(self._first_receipts)-newly_written,
               "r2_first_read_seal_sha256":self._seal_sha,
               "model_calls":self.model.budget.calls_reserved,
               "reader_reactions_are_model_self_reports":True,
               "human_literary_mastery_verified":False,
               "full_chapter_read":False,
               "r2_first_read_checkpoint_verified":True,
               "writer_permission_preflight_passed":True,
            }
        finally:
            self.rt.exit()

    def analyse_after_lock(self):
        require(self._seal_sha is not None and
                len(self._unit_hashes)>=2 and
                self.rt.mode==Mode.IDLE,
                "WF_LEARN_PASS_A_NOT_SEALED")
        # Re-confirm immutable R2 lock using READ authority, not only a local
        # Python boolean. If it is missing, do not send source to analyst.
        seal=event_doc(
            stage="seal",ident=self.ident,
            units_read=len(self._unit_hashes),
            last_first_read_sha256=self._first_receipts[-1]["event_sha256"],
            future_source_seen=False)
        self.journal.read(seal,expect_sha=self._seal_sha)
        existing_b=self.journal.fetch_event(
            ident=self.ident,stage="analysis")
        if existing_b is not None:
            require(existing_b["doc"]["first_read_seal_sha256"]==
                    self._seal_sha,
                    "WF_LEARN_RESUME_ANALYSIS_WRONG_PASS_A_SEAL")
            return {
                "status":"WF_LEARN_PASS_B_ALREADY_LOCKED",
                "pass_a_seal_sha256":self._seal_sha,
                "pass_b_record_sha256":existing_b["event_sha256"],
                "model_calls_total":self.model.budget.calls_reserved,
                "paid_model_analysis_repeated":False,
                "full_chapter_completed":False,
                "literary_skill_promotion_allowed":False,
            }
        self.rt.enter_learn()
        try:
            excerpts="\n".join(
                f"Unit {i}: source_hash={h} content={text}"
                for i,(h,text) in enumerate(
                    zip(self._unit_hashes,self._unit_texts),1))
            require(len(excerpts)<=MAX_ANALYST_PROMPT_CHARS,
                    "WF_LEARN_ANALYST_SOURCE_TOO_LARGE")
            reply=self.model.ask_json(
                role="craft_analysis",
                system=(
                    "你是WriterForge自己的后验文学分析模块。"
                    "PASS A 已签收，当前才能比较本段证据与叙事机制。"
                    "不要引用未来章节，不得自我宣布学会或毕业。"
                    '仅输出JSON对象：{"mechanisms":[{"unit":1,'
                    '"evidence_unit_sha256":"64位SHA256",'
                    '"mechanism":"描述推测技法",'
                    '"reader_effect":"首次阅读假说",'
                    '"uncertainty":"证据的局限"}]}。'
                    "总共1至6项，每项长度不超过160字。"
                ),
                user="仅对以下已经锁定首读的合成/受限章节片段分析：\n"+excerpts,
                max_tokens=750,
            )
            require(isinstance(reply,dict) and set(reply)=={"mechanisms"} and
                    isinstance(reply["mechanisms"],list) and
                    1<=len(reply["mechanisms"])<=6,
                    "WF_LEARN_ANALYSIS_RESPONSE_INVALID")
            mechanisms=reply["mechanisms"]
            require(all(mechanism_schema(m) and
                   m["unit"]<=len(self._unit_hashes) and
                   m["evidence_unit_sha256"]==self._unit_hashes[m["unit"]-1]
                   for m in mechanisms),
                   "WF_LEARN_ANALYSIS_SOURCE_EVIDENCE_INVALID")
            saved=self.journal.append_analysis(
                ident=self.ident,first_read_seal_sha=self._seal_sha,
                mechanisms=mechanisms)
            return {
               "status":"WF_LEARN_PASS_B_HYPOTHESES_R2_STORED",
               "pass_a_seal_sha256":self._seal_sha,
               "pass_b_record_sha256":saved["event_sha256"],
               "hypotheses":len(mechanisms),
               "r2_analysis_record_readback_verified":True,
               "model_calls_total":self.model.budget.calls_reserved,
               "review_status":"UNREVIEWED",
               "full_chapter_completed":False,
               "literary_skill_promotion_allowed":False,
            }
        finally:
            self.rt.exit()
