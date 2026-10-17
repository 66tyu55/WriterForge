"""WF V33: strict length and structured-grading contracts with zero invented scores.

Only client-side validation: no truncating/padding fiction, no filling missing
scores and no averaging incompatible reviewer results. Equal treatment for
the two blinded writer arms. This module contains no model credentials.
"""
from __future__ import annotations
import json,re

DIMENSIONS=("perception","causality","information","continuity","language")
TARGET=1120
MIN_CHARS=950
MAX_CHARS=1300
RELATIVE_CAP=.15
MAX_DRAFT_CHARS=4500
JSON_WRAPPER_KEYS=("result","review","grades","ratings","evaluation","data")

class ExamContractError(ValueError):
    pass

def length_state(text:str)->dict:
    if not isinstance(text,str) or not 220<=len(text)<=MAX_DRAFT_CHARS:
        raise ExamContractError("WRITER_DRAFT_NOT_BOUNDED")
    n=len(text)
    return {"chars":n,"target":TARGET,"within_hard_range":MIN_CHARS<=n<=MAX_CHARS,
            "missing_or_excess":TARGET-n}

def fair_pair(texts:dict)->dict:
    if not isinstance(texts,dict) or set(texts)!={"control","wf_memory"}:
        raise ExamContractError("MISSING_FAIRNESS_PAIR")
    states={k:length_state(texts[k]) for k in ("control","wf_memory")}
    a,b=states["control"]["chars"],states["wf_memory"]["chars"]
    relative=round(abs(a-b)/max(a,b),6)
    return {"arms":states,"relative_difference":relative,
            "relative_cap":RELATIVE_CAP,
            "absolute_both_valid":all(x["within_hard_range"] for x in states.values()),
            "relative_valid":relative<=RELATIVE_CAP,
            "pass":relative<=RELATIVE_CAP and all(
                x["within_hard_range"] for x in states.values())}

def grade_prompt(task:str,anonymous:dict,*,correction:bool=False)->str:
    if not isinstance(task,str) or not 95<=len(task)<=490:
        raise ExamContractError("INVALID_EXAM_TASK")
    if not isinstance(anonymous,dict) or set(anonymous)!={"A","B"}:
        raise ExamContractError("INVALID_BLIND_ARMS")
    for text in anonymous.values():
        length_state(text)
    examples={d:{"score":75,"reason":"明确说明该项的具体文本优缺点，但不要引用正文长句。"}
              for d in DIMENSIONS}
    # Example numbers are ONLY schema demonstrations; not a hint to assign 75.
    return json.dumps({
        "task":task,"anonymous_drafts":anonymous,
        "rubric":{
            "perception":"角色有限知识与自然感官，不堆砌物件",
            "causality":"人物目标、判断、行动与实际代价",
            "information":"先前线索可供回查而非结尾凭空出现",
            "continuity":"人物、时间、地点与行为连续",
            "language":"语言与对话流畅、不过度独白",
        },
        "required_top_level_keys":["A","B","uncertainty"],
        "each_arm_keys":list(DIMENSIONS),
        "each_dimension_fields":["score","reason"],
        "score_type":"integer 0..100",
        "reason_type":"4..180 characters",
        "uncertainty_type":"4..180 characters",
        "json_example_shape":{ "A":examples,"B":examples,
            "uncertainty":"评阅存在模型主观偏差，不代表真实读者的文学认证。"},
        "json_retry_if_previous_format_was_invalid":correction,
        "instruction":"严格返回一个JSON对象；不要markdown、解释、统计均分、"
                      "角色标签、scores包装、章节内容或其他多余字段。"
                      "json_example_shape是输出字段示例，分数必须独立依据正文评价。",
    },ensure_ascii=False,separators=(",",":"))

def strict_grade(value:dict)->tuple[dict,str]:
    if not isinstance(value,dict):
        raise ExamContractError("GRADER_JSON_OBJECT_REQUIRED")
    object_=value
    wrappers=[]
    for _ in range(2):
        if set(object_)=={"A","B","uncertainty"}:
            break
        if len(object_)!=1:
            raise ExamContractError("GRADER_JSON_TOP_LEVEL_KEYS_INVALID")
        name=next(iter(object_))
        if name not in JSON_WRAPPER_KEYS or not isinstance(object_[name],dict):
            raise ExamContractError("GRADER_JSON_WRAPPER_UNSUPPORTED")
        wrappers.append(name)
        object_=object_[name]
    if set(object_)!={"A","B","uncertainty"}:
        raise ExamContractError("GRADER_JSON_MISSING_REQUIRED_KEYS")
    for arm in ("A","B"):
        dimensions=object_[arm]
        if not isinstance(dimensions,dict) or set(dimensions)!=set(DIMENSIONS):
            raise ExamContractError("GRADER_JSON_DIMENSIONS_INCOMPLETE")
        for dimension in DIMENSIONS:
            v=dimensions[dimension]
            if not isinstance(v,dict) or set(v)!={"score","reason"}:
                raise ExamContractError("GRADER_JSON_DIMENSION_OBJECT_INVALID")
            if type(v["score"]) is not int or not 0<=v["score"]<=100:
                raise ExamContractError("GRADER_JSON_SCORE_NOT_INTEGER")
            if not isinstance(v["reason"],str) or not 4<=len(v["reason"].strip())<=180:
                raise ExamContractError("GRADER_JSON_REASON_INVALID")
    if not isinstance(object_["uncertainty"],str) or not 4<=len(object_["uncertainty"].strip())<=180:
        raise ExamContractError("GRADER_JSON_UNCERTAINTY_INVALID")
    return object_,("DIRECT_EXACT" if not wrappers else "UNAMBIGUOUS_ENVELOPE_"+"/".join(wrappers))

def grade_with_one_repair(grader,task:str,anonymous:dict,*,budget_first:int=5300,
                          budget_retry:int=5300)->tuple[dict,dict]:
    """Same anonymous text re-submitted only if FIRST call schema-invalid.

    No choosing a nicer score from two valid responses; never fabricate a
    missing grade or hide the failed first attempt. At most two model.ask
    calls, although the transport adapter may itself charge bounded retries.
    """
    errors=[]
    for attempt in range(2):
        ans=grader.ask(
            "你是完全匿名的文学考官，不知道学生是否使用WF记忆。"
            "仅根据实际的两篇小说客观评价，严查人物因果、信息回查、"
            "场景连续和语言缺点。不计算平均分作为通过依据。"
            "必须输出且只输出约定的完整JSON。",
            grade_prompt(task,anonymous,correction=bool(attempt)),
            num_predict=budget_first if attempt==0 else budget_retry)
        try:
            normalized,parse_path=strict_grade(ans)
        except ExamContractError as e:
            errors.append(str(e))
            if attempt:raise ExamContractError("GRADER_JSON_FAILED_AFTER_ONE_CORRECTION") from None
            continue
        return normalized,{
            "attempted_calls":attempt+1,
            "format_error_first_attempt":errors[0] if errors else None,
            "parsing_path":parse_path,
            "no_grade_was_synthesized":True,
        }
    raise ExamContractError("GRADER_JSON_FAILED_AFTER_ONE_CORRECTION")
