"""Balanced manuscript length controller for WF's fixed examiner questions.

Targets 1120 characters including punctuation, BOTH arms within 950..1300
and each other within 15%. Bounded symmetric edit passes: no truncation,
padding, one-sided rewriting, scores or access to the opposite arm's text.
"""
from __future__ import annotations
import json
from .v33_exam_contracts import TARGET,MIN_CHARS,MAX_CHARS,RELATIVE_CAP, fair_pair,ExamContractError
from .v31_autonomous_core import writer_instruction

INITIAL_TOKENS=7500
REVISION_TOKENS=6000

def controlled_pair(writer,task:str,memory:tuple[dict,...],*,
                    max_revision_cycles:int=1,
                    initial_tokens:int=INITIAL_TOKENS,
                    revision_tokens:int=REVISION_TOKENS)->tuple[dict,dict]:
    if (type(max_revision_cycles) is not int or max_revision_cycles not in (1,2)
        or type(initial_tokens) is not int or not 4000<=initial_tokens<=8500
        or type(revision_tokens) is not int or not 3500<=revision_tokens<=8500):
        raise ExamContractError("WRITER_LENGTH_RECOVERY_BUDGET_INVALID")
    answers={}
    packets={}
    for arm,cards in (("control",()),("wf_memory",memory)):
        packet=json.loads(writer_instruction(task,cards))
        packet["requested_characters_including_punctuation"]=[MIN_CHARS,MAX_CHARS]
        packet["exact_character_target_including_punctuation"]=TARGET
        packets[arm]=json.dumps(packet,ensure_ascii=False,separators=(",",":"))
        value=writer.ask(
            "你是原创中文小说作家。严格写完所给题目的第一章，不要提纲、"
            "章节标题或结尾总结；正文含标点精确目标1120字符，"
            "950至1300字符是不可放宽的范围。"
            "开头与结尾都应完整，必须有可回查的伏笔和人物实际行动代价。",
            packets[arm],num_predict=initial_tokens)
        result=value.get("scene") if isinstance(value,dict) else None
        if not isinstance(result,str):
            raise ExamContractError("WRITER_INITIAL_RESPONSE_NOT_PROSE")
        answers[arm]=result
    initial=fair_pair(answers)
    revision_count=0
    revision_history=[]
    for cycle in range(max_revision_cycles):
        before=fair_pair(answers)
        if before["pass"]:
            break
        revised={}
        for arm in ("control","wf_memory"):
            old=answers[arm]
            count=before["arms"][arm]["chars"]
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
                "revision_cycle":cycle+1,
                "hard_character_count_is_enforced_after_rewrite":True,
            }
            response=writer.ask(
                "你是原创小说责任编辑。只看到自己的本轮稿，不知道另一稿。"
                "重新写成950至1300个含标点字符，尽量接近1120。"
                "尤其注意保证足够余量，不要恰好贴住950或1300的边缘。"
                "上一次稿件的精确字符数已给出，请按目标所需差值补写"
                "或缩写自然段，保持人物目标、实际代价、伏笔及完整结尾。"
                "不能用重复句子、标题、标点或生硬截断来凑字数。"
                "只输出完整修订后的小说正文。",
                json.dumps(info,ensure_ascii=False,separators=(",",":")),
                num_predict=revision_tokens)
            result=response.get("scene") if isinstance(response,dict) else None
            if not isinstance(result,str):
                raise ExamContractError("WRITER_SYMMETRIC_REVISION_NO_PROSE")
            revised[arm]=result
            revision_count+=1
        answers=revised
        revision_history.append(fair_pair(answers))
    final=fair_pair(answers)
    receipt={
        "format":"writerforge.v33-balanced-length-control.v1",
        "initial":initial,"final":final,
        "symmetric_revision_calls":revision_count,
        "symmetric_revision_cycles":revision_count//2,
        "safe_revision_length_history":revision_history,
        "no_one_sided_revision":revision_count in (0,2,4),
        "hard_length_pass":final["absolute_both_valid"],
        "relative_fairness_pass":final["relative_valid"],
        "overall_eligible_for_blind_grading":final["pass"],
        "manuscripts_cropped_or_padded":False,
        "writer_saw_other_arm_draft_or_length":False,
    }
    return answers,receipt
