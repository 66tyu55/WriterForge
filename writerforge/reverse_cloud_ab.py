"""V28 cloud A/B: same original window, two different original drafts.

Both drafts are ephemeral; only source and draft SHA, bounded interpretations,
comparative model observations and budgets may persist. 90% is NOT verified.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from .reverse_real_training import (
    RealTrainingError, raw_hash, _source_copy_guard, _limited_explanation,
    _clean_abstract, NOTE_FIELDS, FAULT_FIELDS, MAX_NOTE_CHARS,
)

MAX_AB_CALLS = 4
DIMENSIONS = ("perception","causality","information","continuity","language")
MAX_AB_DRAFT = 4500
BASE_TASK = (
    "创作全新的中国幻想故事开篇场景，主人公在压力中发现异样、"
    "作出有代价的选择，并留下真实的未解问题。使用原创人名与世界设定，"
    "不要续写、翻译、改写任何现成小说。要求视角清楚、场景因果连续、"
    "事件对主人公产生后果。长度700到1400汉字。"
)


class ABTrialError(RealTrainingError):
    pass


def _brief(value, key):
    if not isinstance(value,str) or not 4<=len(value.strip())<=180:
        raise ABTrialError("missing or unbounded literary evaluation: "+key)
    return value.strip()


def _choice_score(doc, draft, source):
    if not isinstance(doc,dict) or set(doc)!=set(DIMENSIONS):
        raise ABTrialError("comparison dimensions incomplete")
    result={}
    for name in DIMENSIONS:
        item=doc[name]
        if not isinstance(item,dict) or set(item)!={"score","reason"}:
            raise ABTrialError("invalid comparison dimension")
        n=item["score"]
        if type(n) is not int or not 0<=n<=100:
            raise ABTrialError("unbounded comparison score")
        reason=_brief(item["reason"], name)
        if len(reason)>55 and (reason in source or reason in draft):
            reason="UNVERIFIED_QUOTATION_REDACTED_"+raw_hash(reason)[:18]
        result[name]={"score":n,"reason":reason}
    return result


class CloudABTrial:
    """One window; no automatic threshold promotion or multiple generations.

    Uses three independent roles with cloud rate/call budgets; critic sees
    anonymized A/B drafts in a reproducible order. No human score asserted.
    """
    def __init__(self, *, planner, writer, critic):
        if (writer.provider,writer.name)==(critic.provider,critic.name):
            raise ABTrialError("writer cannot critique same identity")
        self.planner,self.writer,self.critic=planner,writer,critic

    def run(self, first:str, second:str, *, source_sha:str, window_hash:str):
        if not 300<=len(first)<=5500 or not second:
            raise ABTrialError("source is not a real bounded first chapter window")
        if raw_hash(first)!=window_hash:
            raise ABTrialError("first window no longer matches R2 pin")
        source_context="【当前第一窗口】\n"+first
        p=self.planner.ask(
            "只阅读给定的当前原著片段，具体解释人物的有限感知和动作因果、"
            "叙述者为什么此时呈现这一细节、以及读者仍不知什么。"
            "不要推测未来内容，不要引用或复述大段原文。"
            "仅返回含 trigger/perception/decision/consequence/reader_question/author_mechanism 的JSON。",
            source_context,num_predict=1700)
        hypothesis=_limited_explanation(p, NOTE_FIELDS,cap=MAX_NOTE_CHARS)
        hypothesis=_clean_abstract(hypothesis,first,"")
        neutral={"writing_task":BASE_TASK,"return_json":{"scene":"string"}}
        enhanced={
            "writing_task":BASE_TASK,
            "technique_constraints":{
                "attention":hypothesis["perception"],
                "decision_causality":hypothesis["decision"],
                "narrative_function":hypothesis["author_mechanism"],
            },
            "return_json":{"scene":"string"},
        }
        outputs={}
        for kind, instruction in (("baseline",neutral),("skill",enhanced)):
            response=self.writer.ask(
                "你是原创小说作家。只返回严格JSON对象，唯一字段 scene。"
                "不得使用参考作品人物、世界观、对话和情节。",
                json.dumps(instruction,ensure_ascii=False),
                num_predict=3200)
            draft=response.get("scene")
            if not isinstance(draft,str) or not 220<=len(draft)<=MAX_AB_DRAFT:
                raise ABTrialError("writer failed to produce bounded original scene")
            _source_copy_guard(draft,first)
            outputs[kind]=draft
        # Blind ordering is fixed by *draft hashes* before seeing evaluation,
        # so the critic never receives which prompt included the learned rule.
        ordered=sorted(outputs, key=lambda k:raw_hash(outputs[k]))
        masked={"A":outputs[ordered[0]],"B":outputs[ordered[1]]}
        comparison=self.critic.ask(
            "你是独立的文学批评模型。对以下两篇匿名原创稿按相同任务盲评，"
            "侧重主人公感知合理性、行为因果、信息释放、前后连续性及语言质量。"
            "仅返回 JSON：{A:{perception:{score:整数,reason:短句},causality:...,"
            "information:...,continuity:...,language:...},B:同结构,"
            "uncertainty:短句,learned_mechanism:短句}。"
            "评论必须能指出真实文本差异，不能默认有技巧约束的稿子一定更好。"
            "不得引用大段原著或练习稿；分数只是模型未经校准的观察，"
            "不能视为专家90分证明。",
            json.dumps({"task":BASE_TASK,"source_context":first,
                        "A":masked["A"],"B":masked["B"]},ensure_ascii=False),
            num_predict=1800)
        if not isinstance(comparison,dict) or set(comparison)!={
            "A","B","uncertainty","learned_mechanism"
        }:
            raise ABTrialError("critic returned incomplete blinded AB comparison")
        review={
            "A":_choice_score(comparison["A"],masked["A"],first),
            "B":_choice_score(comparison["B"],masked["B"],first),
        }
        neutral_note={}
        for key in ("uncertainty","learned_mechanism"):
            value=_brief(comparison[key],key)
            if len(value)>55 and (value in first or any(value in d for d in outputs.values())):
                value="UNVERIFIED_QUOTATION_REDACTED_"+raw_hash(value)[:18]
            neutral_note[key]=value
        def mean(name):
            return sum(review[name][k]["score"] for k in DIMENSIONS)//len(DIMENSIONS)
        labels={v:k for k,v in enumerate(ordered)}
        display={label:{
            "source_prompt":"skill" if label=="skill" else "baseline",
            "draft_sha256":raw_hash(outputs[label]),
            "draft_chars":len(outputs[label]),
            "anonymized_critic_label":"A" if ordered[0]==label else "B",
            "model_critic_score_unverified":mean("A" if ordered[0]==label else "B"),
            "dimension_review":review["A" if ordered[0]==label else "B"],
        } for label in ("baseline","skill")}
        return {
            "format":"writerforge.cloud-ab-v1",
            "source_work":"wudongqiankun","edition_sha256":source_sha,
            "source_unit_sha256":window_hash,"next_unit_sha256":raw_hash(second),
            "stage":"true_model_calls_and_private_source_AB_comparison_unverified",
            "roles":{"planner":{"provider":self.planner.provider,"model":self.planner.name},
                     "writer":{"provider":self.writer.provider,"model":self.writer.name},
                     "critic":{"provider":self.critic.provider,"model":self.critic.name}},
            "hypothesis":hypothesis,"comparisons":display,
            **neutral_note,
            "model_call_count_nominal":4,
            "drafts_retained":False,"human_blind_review_performed":False,
            "literal_master_quality_90pct_verified":False,
            "second_unit_unlocked":False,"core_automatically_promoted":False,
        }
