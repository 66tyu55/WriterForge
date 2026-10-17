"""Balanced manuscript length controller for WF's fixed examiner questions.

Targets 1120 characters including punctuation, BOTH arms within 950..1300
and each other within 15%. Only one symmetric edit pass: no truncation,
padding, one-sided rewriting, scores or access to the opposite arm's text.
"""
from __future__ import annotations
import json
from .v33_exam_contracts import TARGET,MIN_CHARS,MAX_CHARS,RELATIVE_CAP, fair_pair,ExamContractError
from .v31_autonomous_core import writer_instruction

INITIAL_TOKENS=7500
REVISION_TOKENS=6000

def controlled_pair(writer,task:str,memory:tuple[dict,...])->tuple[dict,dict]:
    answers={}
    packets={}
    for arm,cards in (("control",()),("wf_memory",memory)):
        packets[arm]=writer_instruction(task,cards)
        value=writer.ask(
            "你是原创中文小说作家。严格写完所给题目的第一章，不要提纲、"
            "章节标题或结尾总结；正文含标点精确目标1120字符，"
            "950至1300字符是不可放宽的范围。"
            "开头与结尾都应完整，必须有可回查的伏笔和人物实际行动代价。",
            packets[arm],num_predict=INITIAL_TOKENS)
        result=value.get("scene") if isinstance(value,dict) else None
        if not isinstance(result,str):
            raise ExamContractError("WRITER_INITIAL_RESPONSE_NOT_PROSE")
        answers[arm]=result
    initial=fair_pair(answers)
    revision_count=0
    if not initial["pass"]:
        revised={}
        for arm in ("control","wf_memory"):
            old=answers[arm]
            count=initial["arms"][arm]["chars"]
            info={
                "question_and_own_writing_instruction":packets[arm],
                "own_first_draft_only":old,
                "own_exact_characters_including_punctuation":count,
                "common_target_characters":TARGET,
                "required_self_change":TARGET-count,
                "hard_minimum":MIN_CHARS,
                "hard_maximum":MAX_CHARS,
                "other_answer_is_never_available":True,
                "no_cropping_or_padding":True,
            }
            response=writer.ask(
                "你是这篇原创小说的责任编辑。你只见自己的草稿，不知道另一稿。"
                "重新写成950-1300个含标点字符，目标1120，正文自然完整。"
                "必须保留人物目标、关键决策、实际代价和可回查的结尾伏笔。"
                "按给出的当前真实字符数缩写或补足，不许直接截断结尾、"
                "复制重复句子、用标题/说明/标点填空。"
                "仅输出完整修订后的小说正文。",
                json.dumps(info,ensure_ascii=False,separators=(",",":")),
                num_predict=REVISION_TOKENS)
            result=response.get("scene") if isinstance(response,dict) else None
            if not isinstance(result,str):
                raise ExamContractError("WRITER_SYMMETRIC_REVISION_NO_PROSE")
            revised[arm]=result
            revision_count+=1
        answers=revised
    final=fair_pair(answers)
    receipt={
        "format":"writerforge.v33-balanced-length-control.v1",
        "initial":initial,"final":final,
        "symmetric_revision_calls":revision_count,
        "no_one_sided_revision":revision_count in (0,2),
        "hard_length_pass":final["absolute_both_valid"],
        "relative_fairness_pass":final["relative_valid"],
        "overall_eligible_for_blind_grading":final["pass"],
        "manuscripts_cropped_or_padded":False,
        "writer_saw_other_arm_draft_or_length":False,
    }
    return answers,receipt
