"""V80 WriterForge large-batch training: up to 150,000 total tokens.

WF works on the exact frozen private R2 book. The V79 first 3 units and
their early analysis are NEVER changed or paid for twice; V80 reads the
remaining chapter-1 units with a traceable mixed-history flag, then runs
chapters 2–6 from START to END under strict PASS A before any PASS B.

One DeepSeek JSON call per newly unlocked unit. Each first-read immediately
R2-CAS signed, SHA read back, and only then the next unit is unlocked.
After all chapter units, a seal and mechanisms review are R2 signed. An
experience/reflection card is stored as a separate R2 CAS event and is fed
into the NEXT chapter's WF reading prompts, establishing a real behavior
input path (not a proof of correct literary understanding).

Hard budget: <=150,000 provider input+output tokens PER V80 batch, reserved
conservatively before network, no automatic retries, no unbounded context.
A call that times out may have billed; its conservative reservation is held.

No GPT reading, no Cloudflare Worker deployment, no fourth secret, no
original novel overwrites, no fabricated full-chapter certification for the
chapter-1 mixed pilot, no V49 graduate change.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json

from .deepseek_flash_model import FlashBudget,DeepSeekFlashError
from .r2_learn_journal import (
    WFLearnJournal,identity,hexdigest,canonical,
    reaction_schema,mechanism_schema,
)
from .wf_b01_prefix_prepare import _split_into_ordered_units
from .v79_provisional_r2_cas_journal import (
    WFProvisionalR2CASJournal,
)

BATCH_ID="WF-V80-150K-20261019"
MODEL="deepseek-flash"
MAX_BATCH_TOKENS=150000
MAX_BATCH_CALLS=128
MAX_FIRST_CHAPTER=6
MIN_FIRST_CHAPTER=1
MAX_REACTIONS=80
SOURCE_NAME_PRIVATE=True
PILOT_CHAPTER=1
PILOT_UNITS=3

class WFLargeStudyError(RuntimeError):
    pass

def need(flag,reason):
    if not flag:raise WFLargeStudyError(reason)

def pack(obj):
    return json.dumps(obj,ensure_ascii=False,
                      separators=(",",":"),sort_keys=True).encode("utf8")

def hash_string(value):
    return sha256(value.encode("utf8")).hexdigest()


def chapter_reaction_prompt(*,ordinal,previous,previous_strategy,text):
    """No future unit, title, or full-book context in any first-read prompt."""
    before=""
    if previous:
        before=(
          "你之前读完的一个段落留下的疑问（不是后文内容）："+
          str(previous.get("question",""))[:120]+
          "；你之前的猜测："+str(previous.get("prediction",""))[:120]+
          "。"
        )
    strategy=(
        "上章WF自己形成的阅读检查策略：" + previous_strategy[:280]
        if previous_strategy else "")
    return (
      f"第{ordinal}个按序解锁的连续原文单位。"
      "只根据当前已经读到的材料做首次读者反应。"
      "不要复述原文，不要想象后文已经发生的事情。\n"+
      before+strategy+"\n[当前仅此一个原文单位]\n"+text
    )


FIRST_SYSTEM=(
    "你是WriterForge独立的首次阅读者。"
    "这只是模型模拟的阅读反应，不是人类心理实验。"
    "当前只能看到一个新段落以及先前已签收反应。"
    "不准假装看过未解锁的任何下一段。"
    '仅返回JSON对象，字段完整且恰好是：'
    'attention,curiosity,confusion,tension,urge_to_continue'
    '（0-5整数），question,prediction,what_changed（均不超过160字字符串）。'
)
ANALYSIS_SYSTEM=(
    "你是WF自身的后验文学分析模块，只有先读完整本章并锁定"
    "全部首读后才能分析。仅使用当前已读章节片段，"
    "不得使用未来章节、作者评价或外部搜索。"
    "不得自我宣布掌握文学技巧，也不能给自己晋级。"
    '只输出JSON对象：{"mechanisms":[{"unit":1,'
    '"mechanism":"叙事机制假说",'
    '"reader_effect":"首读效果推断",'
    '"uncertainty":"不确定来源"}]}。'
    "unit必须由你根据真实阅读自行选择，来源SHA将由WF"
    "从该unit的已验证原文计算后绑定，模型不能自行编造哈希。"
    "最多6项，不允许无证据的机制。"
)
REFLECT_SYSTEM=(
    "你是WriterForge章节复盘技能。依据本章刚保存的首读与"
    "分析假说，**独立识别可操作的错误和下一章读者提问策略**。"
    "不允许宣称文学能力提高、跨作品已经通过或人类读者给出高分。"
    '仅输出 JSON 对象：{"observed_weakness":"...","next_strategy":"...",'
    '"open_question":"...","confidence_limit":"..."}'
    "，字段只能有这4个，每个字段不超过200字符。"
)


class WFLargeChapterBatch:
    """A true WF LEARN executor; all private text stays inside Railway."""

    def __init__(self,*,journal:WFProvisionalR2CASJournal,model,
                 original_key,source_sha,batch_id=BATCH_ID,
                 progress=None):
        need(isinstance(journal,WFProvisionalR2CASJournal) and
             model.name==MODEL and
             model.budget.max_total_tokens==MAX_BATCH_TOKENS,
             "WF_V80_BATCH_OWNS_MODEL_JOURNAL_AND_CAP_REQUIRED")
        self.journal=journal
        self.model=model
        self.key=original_key
        self.source_sha=source_sha
        self.keyhash=hash_string(original_key)
        self.progress=progress
        self.batch_id=batch_id
        self.earlier_strategy=""
        self.finished_chapters=[]
        self.previous_experience_sha=None
        self.last_batch_pointer=None
        self.pilot_mixed=None

    def emit(self,stage,**data):
        if self.progress:
            self.progress({
                "status":stage,
                "source_sha256":self.source_sha,
                "r2_cas_checkpoint_sha256":self.journal.checkpoint_sha,
                "model_calls_reserved":self.model.budget.calls_reserved,
                "model_total_actual_reported_tokens":(
                    self.model.budget.prompt_tokens_reported+
                    self.model.budget.completion_tokens_reported),
                "batch_token_limit":MAX_BATCH_TOKENS,
                "private_original_prose_in_report":False,
                **data,
            })

    def chapter_body(self,original_path,chap):
        with Path(original_path).open(
            "r",encoding="gb18030",errors="strict",newline=None) as fp:
            fp.seek(chap.start_cookie)
            lines=[]
            while fp.tell()<chap.end_cookie:
                before=fp.tell()
                line=fp.readline()
                need(line and fp.tell()>before,
                     "WF_V80_CHAPTER_SOURCE_READ_FAILED")
                lines.append(line)
            need(fp.tell()==chap.end_cookie,
                 "WF_V80_CHAPTER_RANGE_NOT_EXACT")
        full="".join(lines)
        need(len(full)==chap.body_characters and
             hash_string(full)==chap.body_sha256,
             "WF_V80_SOURCE_BODY_SHA_MISMATCH")
        windows=_split_into_ordered_units(full)
        need(2<=len(windows)<=MAX_REACTIONS and
             "".join(windows)==full,
             "WF_V80_CHAPTER_UNITS_NOT_CONTIGUOUS")
        return windows

    def first_read(self,*,ident,windows,start=1,pilot=False):
        self.journal.allow_prior_pilot_tail=pilot
        prev=None
        earlier=None
        hashes=[]
        saved=0
        for unit_no in range(1,len(windows)+1):
            unit_hash=hash_string(windows[unit_no-1])
            hashes.append(unit_hash)
            existing=self.journal.fetch_event(
                ident=ident,stage="first_read",unit=unit_no)
            if existing:
                ev=existing["doc"]
                need(ev["source_unit_sha256"]==unit_hash and
                     ev["previous_event_sha256"]==prev,
                     "WF_V80_PRIOR_SIGNED_UNIT_MISMATCH")
                if unit_no>start-1 and not pilot:
                    # Valid resume, no second DeepSeek call.
                    pass
                earlier=ev["reaction"]
                prev=existing["event_sha256"]
                continue
            need(unit_no>=start,
                 "WF_V80_PILOT_OLD_UNIT_NOT_IN_R2")
            response=self.model.ask_json(
                role="first_read",system=FIRST_SYSTEM,
                user=chapter_reaction_prompt(
                    ordinal=unit_no,
                    previous=earlier,
                    previous_strategy=self.earlier_strategy,
                    text=windows[unit_no-1]),
                max_tokens=900,
            )
            need(reaction_schema(response),
                 "WF_V80_FIRST_READ_JSON_INVALID")
            record=self.journal.append_first_read(
                ident=ident,unit=unit_no,
                source_unit_sha=unit_hash,
                previous_record_sha=prev,reaction=response)
            prev=record["event_sha256"]
            earlier=response
            saved+=1
            self.emit("WF_V80_SOURCE_UNIT_READ_AND_IMMUTABLE_R2_SIGNED",
                      chapter=ident["chapter"],unit=unit_no,
                      chapter_unit_count=len(windows),
                      event_sha256=prev,
                      actual_model_calls_this_unit=1)
        need(saved>0 or len(windows)>0,
             "WF_V80_NOTHING_TO_READ")
        return hashes,prev,saved

    def analyse(self,*,ident,windows,hashes,chapter_no,
                first_read_seal_sha):
        # Every unit in this analysis prompt must have a real corresponding
        # signed PASS A event in R2, including the archived V79 first three.
        for i,h in enumerate(hashes,1):
            saved=self.journal.fetch_event(
                ident=ident,stage="first_read",unit=i)
            need(saved and
                 saved["doc"]["source_unit_sha256"]==h,
                 "WF_V80_ANALYSIS_WITHOUT_IMMUTABLE_FIRST_READ")
        source="\n".join(
          f"单位{i} / 来源SHA {h}: {text}"
          for i,(h,text) in enumerate(zip(hashes,windows),1))
        need(len(source)<=26000,
             "WF_V80_SINGLE_CHAPTER_ANALYSIS_TOO_LARGE")
        res=self.model.ask_json(
            role="craft_analysis",system=ANALYSIS_SYSTEM,
            user=(
                "本章所有单位现已读过。仅基于以下按序原文做机制"
                "与不确定性分析：\n"+source),
            max_tokens=3500,
        )
        need(isinstance(res,dict) and
             set(res)=={"mechanisms"} and
             isinstance(res["mechanisms"],list) and
             1<=len(res["mechanisms"])<=6,
             "WF_V80_ANALYSIS_RESPONSE_NOT_BOUNDED")
        mechanisms=[]
        for row in res["mechanisms"]:
            need(isinstance(row,dict) and
                 set(row) in (
                    {"unit","mechanism","reader_effect","uncertainty"},
                    {"unit","evidence_unit_sha256","mechanism",
                     "reader_effect","uncertainty"}) and
                 type(row.get("unit")) is int and
                 1<=row["unit"]<=len(hashes),
                 "WF_V80_ANALYSIS_SOURCE_UNIT_INVALID")
            index=row["unit"]-1
            trusted_hash=hashes[index]
            # WF computes provenance from source; it never copies an LLM-
            # invented SHA. An explicit wrong hash must still fail closed.
            if "evidence_unit_sha256" in row:
                need(row["evidence_unit_sha256"]==trusted_hash,
                     "WF_V80_ANALYST_FORGED_EVIDENCE_SHA")
            enriched={**row,"evidence_unit_sha256":trusted_hash}
            need(mechanism_schema(enriched),
                 "WF_V80_ANALYSIS_MECHANISM_INVALID")
            mechanisms.append(enriched)
        res={"mechanisms":mechanisms}
        if chapter_no!=PILOT_CHAPTER:
            event=self.journal.append_analysis(
                ident=ident,
                first_read_seal_sha=first_read_seal_sha,
                mechanisms=res["mechanisms"])
            analysis_sha=event["event_sha256"]
        else:
            # Chapter1 pilot already had an earlier B analysis: do NOT fake
            # having kept analysis completely after full chapter first-read.
            # Preserve that initial seal/analysis and store an additional
            # CAS-only chapter1 continuation certificate.
            payload={
              "format":"wf.learn.mixed-pilot-analysis.v80",
              "source_sha256":self.source_sha,
              "source_key_sha256":self.keyhash,
              "chapter_body_sha256":ident["chapter_body_sha256"],
              "initial_V79_three_unit_seal_sha256":first_read_seal_sha,
              "fully_read_unit_hashes":hashes,
              "mechanisms":res["mechanisms"],
              "early_pilot_analysis_preceded_final_unit":True,
              "independent_literary_mastery_verified":False,
            }
            analysis_sha,_=self.journal._put_content(pack(payload))
        self.emit("WF_V80_COMPLETE_CHAPTER_ANALYSIS_SAVED",
                  chapter=chapter_no,
                  analysis_sha256=analysis_sha,
                  pilot_early_analysis_existed=(chapter_no==1),
                  complete_chapter_source_coverage_sha=(
                      hexdigest(pack(hashes))))
        return analysis_sha,res

    def reflection(self,*,chapter_no,analysis,analysis_sha):
        """A new WF behavior strategy must be fed to the NEXT chapter."""
        res=self.model.ask_json(
            role="craft_analysis",system=REFLECT_SYSTEM,
            user=(
              "本章已保存的文学假说（没有未来原文）：\n"+
              json.dumps(analysis,ensure_ascii=False)+
              "\n请指出至少一个观察弱点、下一章如何避免、以及遗留疑问。"),
            max_tokens=1600,
        )
        expected={"observed_weakness","next_strategy",
                  "open_question","confidence_limit"}
        need(isinstance(res,dict) and set(res)==expected and
             all(isinstance(v,str) and 1<=len(v)<=200
                 for v in res.values()),
             "WF_V80_REFLECTION_NOT_BOUNDED_ACTIONABLE_JSON")
        experience={
          "format":"wf.learn.experience.v80",
          "source_sha256":self.source_sha,
          "source_key_sha256":self.keyhash,
          "chapter":chapter_no,
          "analysis_sha256":analysis_sha,
          "previous_experience_sha256":self.previous_experience_sha,
          "model":"deepseek-flash",
          "reflection":res,
          "applied_to_next_chapter_prompts":False,
          "literary_quality_independently_verified":False,
        }
        sha,_=self.journal._put_content(pack(experience))
        self.previous_experience_sha=sha
        self.earlier_strategy=res["next_strategy"]
        self.emit("WF_V80_CHAPTER_EXPERIENCE_SIGNED_IN_R2",
                  chapter=chapter_no,
                  experience_sha256=sha,
                  experience_next_strategy_sha256=hash_string(
                      res["next_strategy"]),
                  literary_mastery_verified=False)
        return sha

    def complete(self,*,chapter,windows):
        strategy_from_previous=self.previous_experience_sha
        ident=identity(
            source_key=self.key,source_sha=self.source_sha,
            chapter=chapter.ordinal,chapter_body_sha=chapter.body_sha256)
        chapter_no=chapter.ordinal
        pilot=chapter_no==PILOT_CHAPTER
        if pilot:
            initial=self.journal.fetch_event(
                ident=ident,stage="seal")
            need(initial and initial["doc"]["units_read"]==PILOT_UNITS,
                 "WF_V80_V79_MIXED_PILOT_SEAL_NOT_FOUND")
            pilot_seal_sha=initial["event_sha256"]
            self.emit("WF_V80_MIXED_PILOT_PRESERVED",
                      existing_three_units_not_rebilled=True,
                      V79_first_three_seal_sha256=pilot_seal_sha)
            hashes,last,saved=self.first_read(
                ident=ident,windows=windows,start=PILOT_UNITS+1,pilot=True)
            # Publishing a new pure PASS-A seal would be false: the V79
            # three-unit analyst ran before these remaining units.
            seal_sha=pilot_seal_sha
            strict_first_read_then_analysis=False
        else:
            hashes,last,saved=self.first_read(
                ident=ident,windows=windows,start=1,pilot=False)
            old_seal=self.journal.fetch_event(ident=ident,stage="seal")
            if old_seal:
                need(old_seal["doc"]["units_read"]==len(windows) and
                     old_seal["doc"]["last_first_read_sha256"]==last,
                     "WF_V80_RESUMED_CHAPTER_SEAL_INCONSISTENT")
                seal_sha=old_seal["event_sha256"]
            else:
                received=self.journal.seal_first_read(
                    ident=ident,units=len(windows),
                    last_record_sha=last)
                seal_sha=received["event_sha256"]
            strict_first_read_then_analysis=True
        analysis_sha,analysis=self.analyse(
            ident=ident,windows=windows,hashes=hashes,
            chapter_no=chapter_no,first_read_seal_sha=seal_sha)
        experience_sha=self.reflection(
            chapter_no=chapter_no,analysis=analysis,
            analysis_sha=analysis_sha)
        receipt={
           "chapter":chapter_no,
           "printed_chapter":chapter.printed_number,
           "chapter_body_sha256":chapter.body_sha256,
           "chapter_characters":chapter.body_characters,
           "unit_count":len(windows),
           "new_first_read_model_calls":saved,
           "original_unit_sequence_full_coverage_verified":True,
           "first_read_seal_sha256":seal_sha,
           "final_chapter_analysis_sha256":analysis_sha,
           "experience_sha256":experience_sha,
           "previous_V79_early_analysis_flag":pilot,
           "strict_full_chapter_pass_a_before_any_pass_b":
               strict_first_read_then_analysis,
           "R2_journal_native_LEARN_namespace_deployed":False,
           "previous_experience_sha256_used_in_prompts":strategy_from_previous,
           "transfer_to_next_chapter_not_quality_proof":True,
           "literary_mastery_certified":False,
        }
        # Persist a batch progress checkpoint, outside the immutable
        # chapter journal. Log its SHA to resume without redoing first reads.
        batch_state={
           "format":"wf.learn.150k-batch-progress.v80",
           "batch_id":self.batch_id,
           "source_sha256":self.source_sha,
           "source_key_sha256":self.keyhash,
           "last_completed_chapter":chapter_no,
           "chapter_receipt":receipt,
           "journal_checkpoint_sha256":self.journal.checkpoint_sha,
           "previous_batch_pointer_sha256":self.last_batch_pointer,
           "latest_experience_sha256":experience_sha,
           "reported_total_input_tokens":
               self.model.budget.prompt_tokens_reported,
           "reported_total_output_tokens":
               self.model.budget.completion_tokens_reported,
           "conservative_tokens_committed_or_held":
               self.model.budget.conservative_tokens_committed,
           "reported_calls":self.model.budget.calls_reserved,
           "per_batch_total_token_cap":MAX_BATCH_TOKENS,
           "mastery_graduation_approved":False,
        }
        batch_sha,_=self.journal._put_content(pack(batch_state))
        self.last_batch_pointer=batch_sha
        self.finished_chapters.append(receipt)
        self.emit("WF_V80_FULL_SOURCE_CHAPTER_PROCESSING_CHECKPOINT",
                  chapter=chapter_no,unit_count=len(windows),
                  chapter_progress_cas_sha256=batch_sha,
                  pilot_mixed_history=pilot,
                  proper_first_read_before_analysis=
                       strict_first_read_then_analysis)
        return receipt
