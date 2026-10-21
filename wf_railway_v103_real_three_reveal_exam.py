"""V103 ONE-TIME WF real DeepSeek Flash literary reading and transfer exam.

FROZEN EXAMINER-ORIGINAL TEXT (not private novels). 3 ordered reveals,
then 2 same-task original prose arms. Exactly <=5 actual provider calls,
NO retries, no old chapter learning, no canonical or skill promotion.

Each original answer is put into the EXISTING PRIVATE immutable R2 CAS
immediately on return, BEFORE validating interpretation/quote accuracy.
Logs may carry bounded observations from this synthetic original exam ONLY.
A read/witness success is not human literary correctness.
"""
from __future__ import annotations

import json
import os
import re
from hashlib import sha256

from writerforge.v103_frozen_original_exam import (
    RUN_NAME,TITLE,CHAPTERS,TRANSFER_STORY,MODEL,
    MAX_CALLS,READ_MAX_OUTPUT,WRITE_MAX_OUTPUT,
    MAX_RESERVED_OUTPUT,MAX_CONSERVATIVE_REQUEST_BUDGET,
    TARGET_CHARS,MIN_CHARS,MAX_CHARS,
    precommit,encode,h,
)
from writerforge.v101_narrative_reader import _witness,V101ReadingError
from writerforge.v99_longform_quality_evidence import (
    freeze_manuscript,compare_equal_length,
)

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
READER_SYSTEM=(
    "你是WriterForge自己的小说读者，而不是文学考官。必须先读真实段落，"
    "分析人物关系、情感触发、可信与不可信的因果、现实代价、语句好坏，"
    "并预测未来。你绝不可声称见过尚未展示的后文，不能把人物撒谎"
    "当成旁白事实，不许给自己评分。只返回JSON。"
)
WRITER_SYSTEM=(
    "你是WriterForge原创小说写作者。写自然的故事而不是技巧说明书。"
    "必须以人物的需求、具体障碍和可见选择驱动情节；"
    "不得复制以前阅读的小说人物、句子、场景。"
    "只输出严格JSON对象，只有prose字段。"
)
READ_FIELDS=frozenset((
    "plot","motives","knowledge_boundary","relationship","emotion",
    "causality","literary_sentence","forecast","correction","transfer_lesson"
))
REL_FIELDS=frozenset(("before","after","why","evidence_quote"))
EMO_FIELDS=frozenset(("person","trigger_quote","reaction_quote","reading","alternative"))
CAUSE_FIELDS=frozenset(("action_quote","effect_quote","actual_cost","future_constraint"))
TASTE_FIELDS=frozenset(("quote","why_effective_or_weak",
                         "flat_rewrite","change_in_reader_effect"))
FORECAST_FIELDS=frozenset(("most_likely","alternative","uncertainty"))
REV_FIELDS=frozenset(("prior_guess","current_correction","still_unknown"))

def need(flag,code):
    if not flag:raise ValueError(code)

def printable(obj):
    print(json.dumps(obj,sort_keys=True,ensure_ascii=False,
                     separators=(",",":")),flush=True)

def clipped(x,n=140):
    return x[:n] if type(x) is str else None

def single(obj,keyset,name):
    need(type(obj) is dict and set(obj)==keyset,
         "WF103_"+name+"_SCHEMA_MISMATCH")

def words(x,limit=230):
    need(type(x) is str and 3<=len(x.strip())<=limit and
         "\ufffd" not in x and "\x00" not in x,
         "WF103_FIELD_INVALID_OR_TOO_LONG")
    return x.strip()

def quote(src,value,name,optional=False):
    if optional and value is None:
        return None
    need(type(value) is str,
         "WF103_"+name+"_SOURCE_QUOTE_NOT_STRING")
    # Use exactly the existing V101 source witness protection.
    try: return _witness((src,),{"unit":1,"quote":value})
    except V101ReadingError as ex:
        raise ValueError("WF103_"+name+"_"+str(ex)) from None

def validate_read(answer,chapter):
    """Only source-grounded syntax checks, not understanding or literature."""
    single(answer,READ_FIELDS,"READER")
    words(answer["plot"])
    words(answer["knowledge_boundary"])
    words(answer["transfer_lesson"],240)
    need(type(answer["motives"]) is dict and
         set(answer["motives"])=={"葛梨","周迦"},
         "WF103_READER_CHARACTER_MOTIVES_MISSING")
    for value in answer["motives"].values():words(value,190)
    for obj,fields,n in (
        (answer["relationship"],REL_FIELDS,"RELATION"),
        (answer["emotion"],EMO_FIELDS,"EMOTION"),
        (answer["causality"],CAUSE_FIELDS,"CAUSALITY"),
        (answer["literary_sentence"],TASTE_FIELDS,"TASTE"),
        (answer["forecast"],FORECAST_FIELDS,"FORECAST"),
        (answer["correction"],REV_FIELDS,"REVISION"),
    ):
        single(obj,fields,n)
    a=answer["relationship"]
    for key in ("before","after","why"):words(a[key])
    e=answer["emotion"]
    for key in ("reading","alternative"):words(e[key])
    # A perfectly valid Chinese given name can be only two characters.
    need(e["person"] in ("葛梨","周迦"),
         "WF103_EMOTION_CHARACTER_NOT_IN_CAST")

    ca=answer["causality"]
    for key in ("actual_cost","future_constraint"):words(ca[key])
    t=answer["literary_sentence"]
    for key in ("why_effective_or_weak","flat_rewrite","change_in_reader_effect"):
        words(t[key])
    for key in FORECAST_FIELDS: words(answer["forecast"][key])
    for key in REV_FIELDS: words(answer["correction"][key])
    witnesses={
        "relation":quote(chapter,a["evidence_quote"],"RELATION"),
        "trigger":quote(chapter,e["trigger_quote"],"TRIGGER"),
        "reaction":quote(chapter,e["reaction_quote"],"REACTION"),
        "action":quote(chapter,ca["action_quote"],"ACTION",optional=True),
        "effect":quote(chapter,ca["effect_quote"],"EFFECT",optional=True),
        "taste":quote(chapter,t["quote"],"TASTE"),
    }
    need(witnesses["trigger"]["end"]<=witnesses["reaction"]["start"],
         "WF103_EMOTION_STIMULUS_AFTER_REACTION")
    if witnesses["action"] is not None or witnesses["effect"] is not None:
        need(witnesses["action"] is not None and witnesses["effect"] is not None,
             "WF103_CAUSAL_ACTION_EFFECT_PARTIAL")
        need(witnesses["action"]["end"]<=witnesses["effect"]["start"],
             "WF103_EFFECT_BEFORE_ACTION")
    return {
        "quote_witnesses":witnesses,
        "source_sha256":h(chapter.encode("utf8")),
        "evidence_existentially_checked":True,
        "literary_semantics_independently_verified":False,
        "reader_experience_measured":False,
        "predictive_accuracy_verified":False,
    }

def clean_prior(history):
    """Only previous WF-owned answers, limited and ALWAYS marked unverified."""
    lines=["【上一段已封存的WF自己首次判断，尚未证明正确】"]
    for stage in history:
        response=stage.get("answer")
        if type(response) is not dict:
            lines.append("前一段输出不合格；不可据此确定人物意图。")
            continue
        pred=response.get("forecast") or {}
        relation=response.get("relationship") or {}
        lines.append("第"+str(stage["chapter"])+"段："+
           "剧情猜测="+clipped(pred.get("most_likely"),160) .__str__()+
           "；另一可能="+str(clipped(pred.get("alternative"),140))+
           "；关系推测="+str(clipped(relation.get("after"),130))+"。")
    raw="\n".join(lines)
    need(len(raw)<=1600,"WF103_PRIOR_WF_CONTEXT_OVER_BOUND")
    return raw

def read_prompt(chapter_no,history):
    current=CHAPTERS[chapter_no-1]
    previous=clean_prior(history)
    result=(
        "【第"+str(chapter_no)+"段，之前的所有预测已经封存】\n"+
        previous+
        "\n【你现在唯一可见的新原创小说段落（禁止检索或假装见到以后章节）】\n"+
        current+
        "\n针对本段进行真正阅读，不要只是提取关键词。"
        "人物可以做坏事同时保护他人，不能因后文一点解释就自动赦免代价。"
        "请尽量给出本段唯一出现的原文连续短引句，每句6—120字符。"
        "没有明确因果行动/可见后果时action_quote/effect_quote都填null。"
        "所有内容都必须是JSON，根键恰好为："
        '{"plot":"这一段真正发生了什么",'
        '"motives":{"葛梨":"她想要什么、恐惧什么","周迦":"她想要什么、恐惧什么"},'
        '"knowledge_boundary":"谁知道或不知道什么、哪些仅是误会",'
        '"relationship":{"before":"关系先前如何","after":"现在如何",'
        '"why":"变化原因及替代解释","evidence_quote":"本段关系变化原句"},'
        '"emotion":{"person":"葛梨或周迦","trigger_quote":"本段触发原句",'
        '"reaction_quote":"本段后发生的反应原句","reading":"情绪变化解释",'
        '"alternative":"另一种合理解释"},'
        '"causality":{"action_quote":null或本段动作原句,'
        '"effect_quote":null或之后实际后果原句,'
        '"actual_cost":"代价若未兑现必须注明尚未证实",'
        '"future_constraint":"损失对下一次选择的真实约束或未知"},'
        '"literary_sentence":{"quote":"本段6-120字真实原句",'
        '"why_effective_or_weak":"为何对人物/读者有效或无效",'
        '"flat_rewrite":"换成平铺直叙会怎样",'
        '"change_in_reader_effect":"改写损失或改善何种读者体验"},'
        '"forecast":{"most_likely":"不知道后文时你的预测",'
        '"alternative":"另一种可能","uncertainty":"证据不足之处"},'
        '"correction":{"prior_guess":"先前如何猜测或首段暂无",'
        '"current_correction":"本段新证据让你改变或维持何判断",'
        '"still_unknown":"即使此刻也不确定的真相"},'
        '"transfer_lesson":"本段抽象文学经验，不使用原著角色/地点/原句"}。'
        "不要给分数、不要声称自己受过文学训练或看过后文。"
    )
    for future in CHAPTERS[chapter_no:]:
        need(future not in result,"WF103_FORBIDDEN_FUTURE_CHAPTER_LEAK")
    need(len(result)<=10500,"WF103_ONE_READER_PROMPT_OVER_BOUND")
    return result

def prompt_to_write(history,*,informed):
    material=""
    if informed:
        # Experienced arm sees ONLY an abstract mechanism produced by WF.
        # All earlier source prose and character names are excluded.
        abstract=[x["answer"]["transfer_lesson"]
                  for x in history if x.get("verified_witness") is True]
        need(len(abstract)==3,"WF103_TRANSFER_REQUIRES_THREE_ANCHORED_READS")
        for text in abstract:
            need(all(name not in text for name in
                ("葛梨","周迦","冯叔","南塘","《归舟》","旧戏园")),
                "WF103_LESSON_LEAKED_OLD_STORY_CONTENT")
        material=(
            "\n【WF从另一篇已读文本自主提炼的待证实写作经验，不是权威范例】\n"+
            "\n".join("- "+x[:170] for x in abstract)+
            "\n你可以选择跳过不适用的经验，不能复用旧人物或事件。")
    return (
        TRANSFER_STORY+
        "\n【共同要求】正文尽可能接近800个中文含标点字符，"
        "只通过行动、对话、具体损失、人物立场变化推进。"
        "写完仍是未审核候选，不输出打分或技术说明。"+
        material+
        "\n严格返回一个JSON对象：{\"prose\":\"自然原创小说正文\"}。"
    )

def public_read_observation(i,answer,valid,error):
    if type(answer) is not dict:
        return {"chapter":i,"status":"INVALID_JSON_OBJECT","error_code":error}
    def read(path):
        o=answer
        for k in path:
            o=o.get(k) if type(o) is dict else None
        return clipped(o,155)
    return {
        "chapter":i,
        "status":"ANCHORED_CANDIDATE" if valid else "SOURCE_QUOTE_OR_SCHEMA_REJECTED",
        "error_code":error,
        "student_plot":read(("plot",)),
        "student_motives":{
            "葛梨":read(("motives","葛梨")),"周迦":read(("motives","周迦"))},
        "student_relationship":read(("relationship","after")),
        "student_emotion":read(("emotion","reading")),
        "student_cost":read(("causality","actual_cost")),
        "student_future_constraint":read(("causality","future_constraint")),
        "student_prediction":read(("forecast","most_likely")),
        "student_correction":read(("correction","current_correction")),
        "student_transfer_lesson":read(("transfer_lesson",)),
        "semantic_grade":"UNDETERMINED",
    }

def real_run():
    from writerforge.deepseek_flash_model import (
        DeepSeekFlashModel,FlashBudget,
    )
    from writerforge.v79_provisional_r2_cas_journal import (
        WFProvisionalR2CASJournal,
    )
    need(all(os.environ.get(k) for k in
             ("DEEPSEEK_API_KEY","WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN")),
         "WF103_EXISTING_THREE_SECRETS_UNAVAILABLE")
    cas=WFProvisionalR2CASJournal(endpoint=ENDPOINT)
    cas.require_writer_ready()
    frozen=encode(precommit())
    address,created=cas._put_content(frozen)
    need(h(frozen)==address and created is True,
         "WF103_EXAM_ALREADY_PRECOMMITTED_DO_NOT_REBILL")
    budget=FlashBudget(
        max_calls=MAX_CALLS,
        max_reserved_output_tokens=MAX_RESERVED_OUTPUT,
        max_total_tokens=None)
    model=DeepSeekFlashModel(budget=budget,timeout_seconds=120)
    conservative=0
    responses=[]
    receipts=[]
    def ask_save(stage,index,role,system,user,limit):
        nonlocal conservative
        # A request may bill on timeout. Budget reserved BEFORE it is sent,
        # never reset on failure, NEVER retry.
        request={"stage":stage,"index":index,"role":role,
                 "system":system,"user":user,
                 "model":MODEL,"max_tokens":limit}
        conservative+=len(encode(request))+1024+limit
        need(conservative<=MAX_CONSERVATIVE_REQUEST_BUDGET,
             "WF103_CONSERVATIVE_PROVIDER_BUDGET_REFUSED")
        answer=model.ask_json(
            role=role,system=system,user=user,max_tokens=limit)
        original={
            "format":"wf.exam.original-student-response.v103",
            "precommit_sha256":address,
            "stage":stage,"ordinal":index,
            "request_sha256":h(encode(request)),
            "answer_unmodified":answer,
            "literary_truth_unverified":True,
        }
        original_raw=encode(original)
        sha,_=cas._put_content(original_raw)
        need(cas._get_content(sha)==original_raw,
             "WF103_REAL_RAW_RESPONSE_CAS_FRESH_READBACK_FAILED")
        receipts.append({"stage":stage,"ordinal":index,
                         "raw_response_cas_sha256":sha})
        return answer

    for index in range(1,4):
        answer=ask_save("sequential_reader",index,
                        "craft_analysis",READER_SYSTEM,
                        read_prompt(index,responses),READ_MAX_OUTPUT)
        valid=False
        bad=None
        try:
            audit=validate_read(answer,CHAPTERS[index-1])
            valid=True
            audit_raw=encode({
                "format":"wf.exam.literal-reading-audit.v103",
                "source_index":index,"raw_answer_cas":receipts[-1][
                    "raw_response_cas_sha256"],
                "source_sha256":h(CHAPTERS[index-1].encode("utf8")),
                "literal_witnesses":audit,
                "semantics_independently_verified":False,
            })
            audit_sha,_=cas._put_content(audit_raw)
            need(cas._get_content(audit_sha)==audit_raw,
                 "WF103_READER_AUDIT_PRIVATE_READBACK_FAILED")
            receipts[-1]["literal_audit_cas_sha256"]=audit_sha
        except (ValueError,V101ReadingError) as exc:
            reason=str(exc)
            bad=reason if reason.startswith(("WF103_","WF101_","WF102_")) else (
                "WF103_READER_AUDIT_UNCLASSIFIED")
        responses.append({
            "chapter":index,"answer":answer,"verified_witness":valid,
            "raw_cas_sha256":receipts[-1]["raw_response_cas_sha256"],
        })
        printable({"status":"WF103_WF_REAL_CHAPTER_READ_CANDIDATE",
                   "reading":public_read_observation(index,answer,valid,bad),
                   "model_calls_so_far":budget.calls_reserved,
                   "source_chapter_body_not_logged":True,
                   "answer_original_privately_stored":True})

    drafts=[]
    for ordinal,arm in enumerate(("baseline_no_reader","reader_informed"),1):
        if arm=="reader_informed" and not all(x["verified_witness"]
                                              for x in responses):
            printable({"status":"WF103_TRANSFER_READER_ARM_BLOCKED",
                       "reason":"NOT_ALL_THREE_REAL_CHAPTERS_SOURCE_GROUNDED",
                       "auto_retry":False})
            break
        user=prompt_to_write(responses,informed=arm=="reader_informed")
        answer=ask_save(arm,ordinal,
                        "craft_analysis",WRITER_SYSTEM,user,WRITE_MAX_OUTPUT)
        raw=answer.get("prose")
        need(type(answer) is dict and set(answer)=={"prose"} and
             type(raw) is str and MIN_CHARS<=len(raw)<=MAX_CHARS,
             "WF103_WRITING_SCHEMA_OR_ACTUAL_LENGTH_REJECTED")
        freeze=freeze_manuscript(
            prose=raw,arm="single" if ordinal==1 else "rolling_causal",
            case_id="v103_experiment_new_world_transfer",
            requested_chars=TARGET_CHARS)
        drafts.append({"arm":arm,
                       "actual_characters":len(raw),
                       "prose_sha256":freeze["prose_sha256"],
                       "raw_response_cas_sha256":receipts[-1][
                           "raw_response_cas_sha256"],
                       "frozen":freeze})
        # This text is genuinely fresh examiner-owned synthetic work, and
        # user can see a small excerpt from actual model prose in logs.
        printable({"status":"WF103_REAL_ORIGINAL_TRANSFER_DRAFT_SAVED",
                   "arm":arm,"real_prose_characters":len(raw),
                   "first_100_model_written_chars":raw[:100],
                   "first_100_is_not_independent_grade":True,
                   "full_real_model_draft_private_sha256":freeze["prose_sha256"],
                   "model_calls_so_far":budget.calls_reserved})
    fairness=(compare_equal_length(samples=[d["frozen"] for d in drafts])
              if len(drafts)==2 else None)
    manifest={
        "format":"wf.exam.v103.actual-reading-transfer-manifest",
        "precommit_sha256":address,
        "reader_chapter_count":len(responses),
        "reader_literal_anchored_count":sum(
            x["verified_witness"] for x in responses),
        "model_call_receipts":receipts,
        "writing_drafts":[{k:v for k,v in x.items() if k!="frozen"}
                          for x in drafts],
        "length_fairness":fairness,
        "provider_usage":budget.public_receipt(),
        "conservative_input_output_committed":conservative,
        "real_premium_model_calls":budget.calls_reserved,
        "new_v82_training_chapters":0,"v49_preserved":True,
        "independent_human_reading_quality_grade":"NOT_PERFORMED",
        "literary_transfer_winner":"UNDETERMINED",
        "character_motives_and_costs_semantically_verified":False,
        "no_factjournal_or_canon_writes":True,
        "no_automatic_skill_promotion":True,
    }
    manifest_raw=encode(manifest)
    m_sha,_=cas._put_content(manifest_raw)
    need(cas._get_content(m_sha)==manifest_raw,
         "WF103_FINAL_R2_MANIFEST_READBACK_FAILED")
    printable({
        "status":"WF103_REAL_READING_TRANSFER_TRIAL_R2_SAVED",
        "manifest_cas_sha256":m_sha,
        "precommit_cas_sha256":address,
        "actual_model_calls":budget.calls_reserved,
        "actual_model_prompt_tokens_reported":
            budget.prompt_tokens_reported,
        "actual_model_completion_tokens_reported":
            budget.completion_tokens_reported,
        "reader_source_witness_anchored_count":manifest[
            "reader_literal_anchored_count"],
        "reader_stages":len(responses),
        "real_transfer_drafts":len(drafts),
        "actual_draft_lengths":[x["actual_characters"] for x in drafts],
        "drafts_length_comparable":(
            fairness["lengths_comparable"] if fairness else None),
        "human_literary_grade":"NOT_PERFORMED",
        "literary_winner":"UNDETERMINED",
        "original_user_private_books_sent":0,
        "old_chapter_learning_changed":False,
        "paid_future_automatic_training":False,
    })
    return 0

if __name__=="__main__":
    printable({"status":"WF103_REAL_EXAM_STARTED",
               "title":TITLE,"new_original_exam_not_user_book":True,
               "max_provider_requests":MAX_CALLS,
               "no_auto_retries":True})
    try:rc=real_run()
    except Exception as ex:
        msg=str(ex)
        if not (re.fullmatch(
                r"(?:WF103|WF101|WF102|WF_FLASH|WF_V79|WF_INDEX|WF_LEARN)_[A-Z0-9_]{1,140}",
                msg) is not None):
            msg="WF103_PAUSED_UNCLASSIFIED_DO_NOT_AUTOMATICALLY_RETRY"
        printable({"status":"WF103_EXAM_PAUSED_NO_RETRY",
                   "reason_code":msg,
                   "model_may_have_billed_if_transport_failed":True,
                   "new_training_chapters":0,
                   "full_original_model_answers_not_in_error_logs":True})
        rc=1
    printable({"status":"WF103_REAL_EXAM_EXIT","exit_code":rc})
    raise SystemExit(rc)
