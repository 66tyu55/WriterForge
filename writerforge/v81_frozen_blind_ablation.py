"""V81 independent mini blind-transfer ablation, frozen BEFORE chapter7 training.

This examiner file must NEVER be imported by the WF learning runner and its
three toy scenarios never appear in the training prompts. They were written
before testing and do NOT quote any user's R2 original. They represent three
distinct mechanisms, but are too small to certify literary mastery.

The examiner compares two independent calls per scene with identical
candidate mechanism choices and scene, changing ONLY whether a previous WF
R2 experience strategy is supplied. Outputs are judged by the deterministic
source-anchor/choice rules below. Do not ask GPT or DeepSeek to score itself.

All scenes and independent rubric are frozen in GitHub before training starts.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

EXAM_VERSION="wf.blind-transfer-ablation.v81.20261019"
VALID_CHOICES=("sound_environment","knowledge_gap","causal_inference")
CASES=(
 {
   "id":"A",
   "scene":"深夜的古桥上，一位巡夜人听见第三次钟声。钟楼的铁门却锁着，钟摆早在白天已经拆走。桥下的水忽然静了，岸边的人都望向没有灯火的山坡。",
   "focus":"sound_environment",
 },
 {
   "id":"B",
   "scene":"驿站老板告诉客人，信使午后才会来。柜台后的学徒早晨亲眼见过信使的马被牵进后院，却怕丢掉差事，没有提醒客人。客人一直站在门口等待。",
   "focus":"knowledge_gap",
 },
 {
   "id":"C",
   "scene":"仓库守门人坚称整夜没有人进去。清晨账本却多了两行昨夜的入库记录，而门前积雪只有一串通往仓库的新脚印。调查者尚不能确定是谁留下了记录。",
   "focus":"causal_inference",
 },
)
MAX_EXAM_CALLS=6
MAX_MODEL_RESPONSE_TOKENS=450
MAX_EXAM_OUTPUT_RESERVATION=2700
MAX_EXPERIENCE_CHARS=200


def frozen_sha():
    doc={
      "version":EXAM_VERSION,
      "cases":CASES,
      "choices":VALID_CHOICES,
      "rubric":"exact_quote+mechanism_match+bounded_uncertainty",
      "no_exam_answers_in_model_prompt":True,
      "exam_is_not_literary_qualification":True,
    }
    return sha256(json.dumps(
        doc,sort_keys=True,ensure_ascii=False,
        separators=(",",":")).encode("utf-8")).hexdigest()


def prompt_for_case(case,*,experience_strategy=None):
    # The same system/user task is used in both arms; prior experience is
    # the sole manipulated causal variable (no prior/source summary).
    assert case in CASES
    if experience_strategy is None:
        memory="本次没有附加的历史阅读策略。"
    else:
        assert 1<=len(experience_strategy)<=MAX_EXPERIENCE_CHARS
        memory="WF在别的作品章节形成的阅读注意策略："+experience_strategy
    system=(
      "你是WriterForge的独立小型阅读检查器，不是自己的考官。"
      "这是全新的人造片段，从未作为WF训练章节材料。"
      "仅根据当前提供的文字作判断，不使用不存在的后文。"
      '严格输出JSON对象且只含四字段：'
      '{"mechanism":"sound_environment或knowledge_gap或causal_inference",'
      '"evidence":"精确复制当前片段连续的6至60个字",'
      '"reader_question":"读者可能提出的一个未解问题",'
      '"uncertainty":"哪里还无法判断"}。'
      "没有证据就不要编造原文或声称掌握写作。"
    )
    user=(
      "上轮WF阅读策略上下文："+memory+
      "\n本次待检查的全新片段：\n"+case["scene"]+
      "\n判断最能解释读者关注点的一种机制，并贴出原文证据。"
    )
    return system,user


def grade_case(case,model_output):
    """Examiner-coded exact source anchor + frozen focus, NO model scoring."""
    if not isinstance(model_output,dict) or set(model_output)!={
        "mechanism","evidence","reader_question","uncertainty"
    }:
        return {"score":0,"shape_valid":False,
                "source_exact":False,"focus_match":False}
    m=model_output.get("mechanism")
    quote=model_output.get("evidence")
    question=model_output.get("reader_question")
    uncertainty=model_output.get("uncertainty")
    shape=(m in VALID_CHOICES and
           isinstance(quote,str) and 6<=len(quote)<=60 and
           isinstance(question,str) and 4<=len(question)<=160 and
           isinstance(uncertainty,str) and 4<=len(uncertainty)<=160)
    exact=bool(shape and quote in case["scene"])
    focus=(m==case["focus"])
    score=int(exact)+int(focus)+int(shape)
    return {
        "score":score,
        "shape_valid":bool(shape),
        "source_exact":exact,
        "focus_match":focus,
        "literary_quality_or_training_transfer_proven":False,
    }


def decision_summary(case_results):
    """Three cases x two arms, bound to the pre-frozen GitHub rubric."""
    assert len(case_results)==6
    grouped={"without_experience":[],"with_experience":[]}
    for row in case_results:
        assert row["arm"] in grouped
        grouped[row["arm"]].append(row)
    assert all(len(v)==3 for v in grouped.values())
    baseline=sum(row["grade"]["score"] for row in grouped["without_experience"])
    carried=sum(row["grade"]["score"] for row in grouped["with_experience"])
    changed=sum(
      1 for case in CASES
      if next(r["output_sha256"] for r in grouped["without_experience"]
              if r["case_id"]==case["id"]) !=
         next(r["output_sha256"] for r in grouped["with_experience"]
              if r["case_id"]==case["id"])
    )
    return {
       "exam_format":EXAM_VERSION,
       "frozen_exam_sha256":frozen_sha(),
       "number_of_blind_scenarios":3,
       "official_deepseek_inference_requests":6,
       "baseline_rubric_points":baseline,
       "with_experience_rubric_points":carried,
       "rubric_max_each_arm":9,
       "different_outputs_in_paired_cases":changed,
       "measured_ablation_delta":carried-baseline,
       "claims_literary_mastery":False,
       "conclusion":("ONE_SMALL_BLIND_ABLATION_NOT_A_QUALIFICATION"),
       "human_literary_judge_involved":False,
       "future_prompt_content_audit_not_proven":True,
    }
