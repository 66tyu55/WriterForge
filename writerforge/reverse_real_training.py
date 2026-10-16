"""Real, local-model-only reverse literary practice from verified first chapter.

Do not call the synthetic reviewer authority. No numeric mastery is certified.
Novel/draft texts are held in GitHub runner ephemeral memory only. Only limited
abstract mechanisms, errors and hashes may be written to a private R2 object.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
import json
import re
import time

from .reverse_source_cursor import HEADING, digest, opening_chapter_plan

MAX_JSON_RESPONSE = 24_000
MAX_USER_PROMPT = 13_000
MAX_MODEL_CALLS = 7
NOTE_FIELDS = ("trigger", "perception", "decision", "consequence",
               "reader_question", "author_mechanism")
FAULT_FIELDS = ("perception", "causality", "information")
MAX_NOTE_CHARS = 240


class RealTrainingError(RuntimeError):
    pass


class ModelUnavailable(RealTrainingError):
    pass


def _safe_json(text: str) -> dict:
    if not isinstance(text, str) or len(text) > MAX_JSON_RESPONSE:
        raise RealTrainingError("model returned oversized/empty answer")
    try:
        result = json.loads(text)
    except ValueError as exc:
        raise RealTrainingError("model answer not JSON") from exc
    if not isinstance(result, dict):
        raise RealTrainingError("model JSON must be object")
    return result


def note(text, *, cap=MAX_NOTE_CHARS):
    if not isinstance(text,str) or not 4<=len(text.strip())<=cap:
        raise RealTrainingError("missing or oversized mechanism note")
    return text.strip()


def raw_hash(value) -> str:
    return sha256(value.encode("utf-8") if isinstance(value,str) else value).hexdigest()


@dataclass
class LocalModel:
    name: str
    base_url: str = "http://127.0.0.1:11434"

    def ask(self, system: str, user: str, *, num_predict: int = 1800) -> dict:
        parsed=urlsplit(self.base_url)
        if parsed.scheme!="http" or parsed.hostname not in ("127.0.0.1","localhost") or parsed.query:
            raise ModelUnavailable("model endpoint not local loopback")
        if not isinstance(self.name,str) or not re.fullmatch(r"[a-zA-Z0-9:._/-]{2,80}",self.name):
            raise ModelUnavailable("invalid model name")
        if not 50<=num_predict<=2400 or len(user)>MAX_USER_PROMPT:
            raise ModelUnavailable("prompt or output token cap exceeded")
        payload=json.dumps({
            "model":self.name, "stream":False,"format":"json", "think":False,
            "keep_alive":0,
            "messages":[{"role":"system","content":system},{"role":"user","content":user}],
            "options":{"num_ctx":8192,"num_predict":num_predict,"temperature":0.35},
        },ensure_ascii=False).encode("utf-8")
        req=Request(self.base_url.rstrip("/")+"/api/chat",data=payload,
                    headers={"Content-Type":"application/json"},method="POST")
        try:
            with urlopen(req,timeout=360) as res:
                data=res.read(MAX_JSON_RESPONSE*2+1)
        except Exception as exc:
            raise ModelUnavailable("local model request failed: "+type(exc).__name__) from None
        if len(data)>MAX_JSON_RESPONSE*2:
            raise ModelUnavailable("local model response exceeds memory cap")
        try:
            obj=json.loads(data)
            output=obj["message"]["content"]
        except (ValueError,TypeError,IndexError,KeyError) as exc:
            raise ModelUnavailable("local model wire response malformed") from exc
        return _safe_json(output)


def first_chapter_windows(path:Path, encoding:str, expected_sha:str):
    plan=opening_chapter_plan(path,encoding,expected_source_sha256=expected_sha)
    lines=[]
    in_first=False
    count=0
    with path.open("r",encoding=encoding) as stream:
        for line in stream:
            heading=HEADING.fullmatch(line.strip())
            if heading:
                count+=1
                if count==1:
                    in_first=True
                    continue
                if count==2:
                    break
            if in_first:
                lines.append(line)
    full="".join(lines)
    if digest(full)!=plan["chapter_body_sha256"]:
        raise RealTrainingError("chapter-one content changed during reading")
    segments=[]
    for unit in plan["units"]:
        segment=full[unit["start"]:unit["end"]]
        if digest(segment)!=unit["segment_sha256"]:
            raise RealTrainingError("segment provenance mismatch")
        segments.append(segment)
    return plan, tuple(segments)


def _limited_explanation(record:dict, fields, *, cap=MAX_NOTE_CHARS):
    if not isinstance(record,dict):
        raise RealTrainingError("missing structured interpretation")
    return {key:note(record.get(key),cap=cap) for key in fields}


def _source_copy_guard(generated:str,source:str):
    """Deny verbatim large n-gram reuse; not a comprehensive semantic plagiarism check."""
    compact=lambda t:"".join(t.split())
    original=compact(source)
    trial=compact(generated)
    if len(trial)<220 or len(trial)>3400:
        raise RealTrainingError("generated scene shorter/longer than trial budget")
    for at in range(0,max(0,len(trial)-29),10):
        if trial[at:at+30] in original:
            raise RealTrainingError("possible verbatim original reuse")


def _clean_abstract(record:dict, source:str, draft:str):
    """Reduce chance of a full source/draft being concealed in private notes."""
    clean={}
    for k,v in record.items():
        n=note(v)
        if len(n)>55 and (n in source or n in draft):
            raise RealTrainingError("unabstracted original/draft in review note")
        clean[k]=n
    return clean


class RealFirstUnitTrainer:
    def __init__(self,planner,writer,critic):
        self.planner=planner
        self.writer=writer
        self.critic=critic
        if self.writer.name==self.critic.name:
            raise RealTrainingError("critic must be a different actual model")
        self.calls=0

    def _ask(self,model,system,user,predict=1400):
        if self.calls>=MAX_MODEL_CALLS:
            raise RealTrainingError("bounded real model call budget exceeded")
        self.calls+=1
        return model.ask(system,user,num_predict=predict)

    def learn(self,segments:tuple[str,str], *, source_sha:str, max_attempts:int=2):
        if not 1<=max_attempts<=3:
            raise RealTrainingError("max attempts outside finite budget")
        first,second=segments
        if not first or not second:
            raise RealTrainingError("missing consecutive opening units")
        # Planner sees only first physical source unit; no future information.
        proposed=self._ask(self.planner,
            "你是严谨的原著细读者。仅依据已看到的片段分析人物认知和信息释放；不得杜撰作者心理、不得概括未来章节。"
            "只输出 JSON，恰含 trigger/perception/decision/consequence/reader_question/author_mechanism 六项，"
            "每项一句，80字以内。明确未知而不是补造。",
            "【源片段，绝不可照录用于练习写作】\n"+first,1600)
        concepts=_limited_explanation(proposed,NOTE_FIELDS)
        concepts=_clean_abstract(concepts,first,"")
        # Writer must not receive the original text nor its proper nouns.
        instruction={
            "setting":"完全原创的非武动乾坤世界，不使用林动、林家、青阳镇等原著角色或事件",
            "objective":"写出完整的角色感知->判断->行动->后果，使读者能推断而非被直接解释",
            "mechanism_reference":{
                "problem":concepts["trigger"],
                "perception":concepts["perception"],
                "decision":concepts["decision"],
                "author_mechanism":concepts["author_mechanism"],
            },
            "length":"700-1400汉字", "format":"严格 JSON，包含 scene 一个字符串字段",
        }
        attempts=[]
        last_faults=None
        for idx in range(1,max_attempts+1):
            task=json.dumps(instruction,ensure_ascii=False)
            if last_faults:
                task+="\n上次盲审的局限（不见原著全文）:"+json.dumps(last_faults,ensure_ascii=False)
            result=self._ask(self.writer,
                "你是原创中国幻想小说作家。以完全新的场景人物展示因果和视角。"
                "不得改写、翻译或续写参考小说。只返回 JSON：{\"scene\":\"...\"}。",task,2400)
            generated=result.get("scene")
            if not isinstance(generated,str):
                raise RealTrainingError("writer returned no real scene")
            _source_copy_guard(generated,first)
            # The *different* critic sees original and the locked scene. No next unit.
            critique=self._ask(self.critic,
                "你是独立的文学分析编辑，不是写作模型。严格比较因果机制、人物视角、信息控制；"
                "强调缺点与可观察文本依据，但不得引用整句原著，不得根据句子相似度给分。"
                "只输出 JSON，字段 faults 为 perception/causality/information 三项具体缺点，"
                "mechanism 为一句作者呈现假说，counterfactual 为一句改变呈现方式后的效果，"
                "revision 为一句可迁移修订原则。所有字符串不超120字。"
                "这仅是模型审稿假设，不是正式90%独立评审。",
                "【局部原著】\n"+first+"\n【已锁定的原创练笔】\n"+generated,1600)
            faults=_limited_explanation(critique.get("faults"),FAULT_FIELDS,cap=160)
            comments=_limited_explanation(critique,
                                         ("mechanism","counterfactual","revision"),cap=160)
            faults=_clean_abstract(faults,first,generated)
            comments=_clean_abstract(comments,first,generated)
            attempts.append({
                "attempt":idx, "draft_sha256":raw_hash(generated),
                "draft_chars":len(generated),"critic_model":self.critic.name,
                "faults":faults, "author_choice_hypothesis":comments["mechanism"],
                "counterfactual":comments["counterfactual"],
                "transfer_rule_candidate":comments["revision"],
                "quality_score":None,"independently_calibrated_90_percent":False,
            })
            last_faults=faults
            # Prevent even same-call summary from retaining the body past comparison.
            del generated, result, critique
        return {
            "format":"writerforge.reverse-real-first-unit.v1",
            "source_work":"wudongqiankun","edition_sha256":source_sha,
            "unit_ordinal":1,"first_unit_sha256":raw_hash(first),
            "next_unit_sha256":raw_hash(second),
            "planner_model":self.planner.name,"writer_model":self.writer.name,
            "critic_model":self.critic.name,"real_model_calls":self.calls,
            "initial_hypothesis":concepts,"attempts":attempts,
            "noted_failures":len(attempts),
            "real_model_training_executed":True,
            "original_full_chapters_read":False,
            "independent_human_review_performed":False,
            "mastery_90_percent_verified":False,
            "promotion_blocked":"await_independent_calibrated_blind_review",
            "second_unit_unlocked":False,
            "model_weights_updated":False,
        }
