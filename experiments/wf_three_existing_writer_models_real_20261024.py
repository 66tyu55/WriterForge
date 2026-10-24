"""One explicit opt-in, three already integrated REAL writer-model comparison.

Never train, write R2, modify Canon or deploy. No alternative reviewer model.
Each model independently writes one original scene, decides KEEP/MOVE_ON vs
LOOK_BACK_NOW, and only if it chooses to edit, is asked once for its own V119
revision. All original provider wires and rejected drafts are retained in the
private GitHub Actions artifact. No retry for any provider failure.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler
import json
import os
import re
import ssl
import sys
import time

from writerforge.verified_flow import GroundedDraftPacket
from writerforge.v96_causal_turns import check_turn, V96CausalDraftError
from writerforge.v114_external_story_state import (
    external_temporal_step, V114ExternalMemoryError,
)
from writerforge.deepseek_flash_model import (
    DeepSeekFlashModel, DeepSeekFlashError, FlashBudget,
)
from writerforge.reverse_discovery_models import MODELS as DISCOVERY_ALLOWLIST
from writerforge.writing_assist import (
    _ai_decides_when_to_revisit, _self_edit_one_turn,
)
from writerforge.verified_flow import WritingExecutionError

OUTPUT=Path("wf_three_real_writer_models_20261024")
DEEPSEEK_URL="https://api.deepseek.com/chat/completions"
DISCOVERY_ROOT="https://discovery-api.intern-ai.org.cn/v1"
MAX_REPLY_BYTES=300_000
PER_MODEL_MAX_CALLS=3
PER_MODEL_MAX_REQUESTED_TOKENS=1450+600+1800
MODELS=(
    ("deepseek-flash","deepseek"),
    ("glm-5.3","discovery"),
    ("kimi-k2.6","discovery"),
)
assert all(name in DISCOVERY_ALLOWLIST for name,provider in MODELS
           if provider=="discovery")

# Original NEW problem: not borrowed from the previous father-letter /
# fruit / bridge / novel corpus training fixtures, and no imposed ending.
SEED=(
    "寒汀渡口的渡索已有两处断股，船夫程九说天亮前最多再渡一次。"
    "女捕快顾翎左手被锁链磨得使不上力，却仍护着一页带血的旧税簿。"
    "她认得簿上的官印，但不知道是谁改过字；程九知道渡索将断，"
    "却不知道这张簿纸的来历。"
    "对岸忽然传来一声求救，雾里看不清是谁。"
)
GOAL="顾翎与程九在最后一次过河的机会前各自做出可信选择；不要替未知者宣告身份或预设正义胜利。"
OUTLINE=(
    "原创江湖悬疑/人物选择的一个完整新场景。允许安静、误判、"
    "小动作或艰难抉择，不预设谁获救；行动与代价须在实际正文中可见。"
)
BEAT={
    "id":"t01","kind":"quiet","actor":"顾翎",
    "goal":GOAL,"causal_parent":None,"craft_focus":[],
}
CAST=("顾翎","程九")
INITIAL_PROMPT=(
    "【原创小说已经发生的事实】"+SEED+
    "\n【待写场景而非已有事实】"+OUTLINE+
    "\n【人物主动选择的写作目标】"+GOAL+
    "\n自由地写一个 260–520 汉字的完整原创小说片段，"
    "以实际人物动作、对话、阻力与代价展开，不解释创作技巧。"
    "你可以让人物改变主意，不要为了表现反转而宣布未证实的结局。"
    "只返回一个严格 JSON 对象，恰好有 prose、trace 两个键；"
    "prose 是实际小说正文；trace 恰好有 action_quote、"
    "effect_quote、parent_effect_quote 三个键。"
    "安静片段允许 action_quote 和 effect_quote 都为 JSON null；"
    "否则两者必须都是实际正文唯一出现且长度 6–96 字的精确原句，"
    "动作在后果之前。parent_effect_quote 必须是 JSON null。"
    "禁止返回解释或额外字段。"
)
WRITER_SYSTEM=(
    "你是原创中文小说作者，不是旁观评分者。"
    "根据角色真实所知写一段自然具体的小说；"
    "仅输出严格JSON对象，字面字段和原句引用请精确照要求处理。"
)
MOMENT_SYSTEM=(
    "你就是刚才写这段小说的同一个作者。"
    "决定是否应该原样往下写，还是现在回头修改。"
    "必须严格输出用户文本要求的 JSON 字段；"
    "不要强制回改，不要另写小说正文，不要评分。"
)
EDIT_SYSTEM=(
    "你仍是刚才真正写出此段的同一个作者，自己判断怎么删改。"
    "只按用户文本提供的 V119 修订字段输出严格 JSON；"
    "不能凭空伪造引句，不能改动选择范围之外的字。"
)
SYSTEM_BY_TOKENS={1450:WRITER_SYSTEM,600:MOMENT_SYSTEM,1800:EDIT_SYSTEM}


def h(value):
    if isinstance(value,str):
        value=value.encode("utf8")
    return sha256(value).hexdigest()


def save_json(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,
                               indent=2),encoding="utf8")


def safe_exception(error):
    # Never log confidential HTTP response bodies, API key values, or raw
    # provider exceptions. Only type + compact WF/transport code.
    content=str(error)
    if (type(content) is str and len(content)<=140 and
        re.fullmatch(r"[A-Z][A-Z0-9_:\-]{3,139}",content)):
        return content
    return type(error).__name__


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise RuntimeError("PROVIDER_REDIRECT_BLOCKED")


def opener():
    return build_opener(_NoRedirect(),HTTPSHandler(context=ssl.create_default_context()))


def discover_models(secret):
    request=Request(DISCOVERY_ROOT+"/models",method="GET",
                    headers={"Authorization":"Bearer "+secret,
                             "Accept":"application/json"})
    try:
        with opener().open(request,timeout=40) as response:
            wire=response.read(MAX_REPLY_BYTES+1)
        if not 0<len(wire)<=MAX_REPLY_BYTES:
            raise RuntimeError("DISCOVERY_MODEL_LIST_TOO_LARGE")
        obj=json.loads(wire)
        if not isinstance(obj,dict) or not isinstance(obj.get("data"),list):
            raise RuntimeError("DISCOVERY_MODEL_LIST_INVALID")
        return {row.get("id") for row in obj["data"] if isinstance(row,dict)
                and type(row.get("id")) is str}
    except HTTPError as exc:
        raise RuntimeError("DISCOVERY_LIST_HTTP_"+str(exc.code)) from None
    except (URLError,TimeoutError,OSError,ValueError) as exc:
        raise RuntimeError("DISCOVERY_MODEL_LIST_CONNECTION_OR_JSON") from None


class ActualModel:
    def __init__(self,name,provider,secret,output):
        self.name=name
        self.provider=provider
        self.secret=secret
        self.output=output
        self.calls=0
        self.reserved=0
        self.usage={"prompt_tokens":0,"completion_tokens":0}
        self.events=[]
        self.stage=""
        self.client=None
        if provider=="deepseek":
            budget=FlashBudget(max_calls=PER_MODEL_MAX_CALLS,
                               max_reserved_output_tokens=PER_MODEL_MAX_REQUESTED_TOKENS,
                               max_total_tokens=150000)
            self.client=DeepSeekFlashModel(
                api_key=secret,budget=budget,timeout_seconds=90,
                on_response_wire=self._deepseek_wire)
            self.budget=budget

    def _deepseek_wire(self,wire):
        path=self.output/f"{self.calls:02d}-{self.stage}-provider-wire.json"
        path.write_bytes(wire)
        self.events[-1]["wire_sha256"]=h(wire)
        self.events[-1]["wire_preserved"]=True

    def _discovery_ask(self,prompt,max_tokens):
        data={
            "model":self.name,
            "messages":[
                {"role":"system","content":SYSTEM_BY_TOKENS[max_tokens]+
                 " 仅返回严格有效的JSON对象，不输出Markdown。"},
                {"role":"user","content":prompt}],
            "stream":False,"max_tokens":max_tokens,
            "response_format":{"type":"json_object"},
            "temperature":1 if self.name=="kimi-k2.6" else 0.4,
        }
        payload=json.dumps(data,ensure_ascii=False,separators=(",",":")).encode("utf8")
        if len(payload)>28_000:
            raise RuntimeError("WF_REAL_COMPARE_PROMPT_TOO_LARGE")
        request=Request(
            DISCOVERY_ROOT+"/chat/completions",data=payload,method="POST",
            headers={"Authorization":"Bearer "+self.secret,
                     "Content-Type":"application/json","Accept":"application/json"})
        try:
            with opener().open(request,timeout=95) as response:
                wire=response.read(MAX_REPLY_BYTES+1)
        except HTTPError as error:
            raise RuntimeError("DISCOVERY_HTTP_"+str(error.code)) from None
        except (URLError,TimeoutError,OSError) as error:
            raise RuntimeError("DISCOVERY_NETWORK_OR_TIMEOUT") from None
        if not 0<len(wire)<=MAX_REPLY_BYTES:
            raise RuntimeError("DISCOVERY_WIRE_SIZE_INVALID")
        (self.output/f"{self.calls:02d}-{self.stage}-provider-wire.json").write_bytes(wire)
        self.events[-1]["wire_sha256"]=h(wire)
        self.events[-1]["wire_preserved"]=True
        try:
            obj=json.loads(wire)
            choice=obj["choices"][0]
            finish=choice.get("finish_reason")
            content=choice["message"]["content"]
            usage=obj.get("usage") or {}
            for key in self.usage:
                if type(usage.get(key)) is int and usage[key]>=0:
                    self.usage[key]+=usage[key]
            self.events[-1]["finish_reason"]=finish
            if finish!="stop":
                raise RuntimeError("DISCOVERY_FINISH_NOT_STOP")
            if not isinstance(content,str) or not content.strip():
                raise RuntimeError("DISCOVERY_EMPTY_CONTENT")
            return content.strip()
        except (IndexError,KeyError,TypeError,UnicodeError,ValueError):
            raise RuntimeError("DISCOVERY_CHAT_JSON_INVALID") from None

    def ask(self,packet,*,model,api_base,max_tokens):
        if (self.calls>=PER_MODEL_MAX_CALLS or
            max_tokens not in SYSTEM_BY_TOKENS or
            self.reserved+max_tokens>PER_MODEL_MAX_REQUESTED_TOKENS):
            raise RuntimeError("WF_REAL_COMPARE_CALL_BUDGET_EXCEEDED")
        self.calls+=1
        self.reserved+=max_tokens
        self.stage={1450:"write",600:"decide",1800:"edit"}[max_tokens]
        self.events.append({
            "stage":self.stage,"requested_tokens":max_tokens,
            "prompt_sha256":h(packet.prompt),
            "status":"REQUESTED","wire_preserved":False,
        })
        if self.provider=="deepseek":
            result=self.client.ask_json(
                role="self_scene_writing",
                system=SYSTEM_BY_TOKENS[max_tokens],
                user=packet.prompt,max_tokens=max_tokens)
            content=json.dumps(result,ensure_ascii=False,separators=(",",":"))
            self.usage["prompt_tokens"]=self.budget.prompt_tokens_reported
            self.usage["completion_tokens"]=self.budget.completion_tokens_reported
        else:
            content=self._discovery_ask(packet.prompt,max_tokens)
        (self.output/f"{self.calls:02d}-{self.stage}-model-answer.json"
        ).write_text(content,encoding="utf8")
        self.events[-1]["status"]="ORIGINAL_RECEIVED"
        self.events[-1]["response_sha256"]=h(content)
        return content


def summarize(model):
    return {
        "name":model.name,"provider":model.provider,
        "calls_attempted":model.calls,
        "requested_output_tokens":model.reserved,
        "provider_usage":dict(model.usage),
        "calls":list(model.events),
        "canon_writes":0,"model_weights_trained":False,
        "literary_quality_independently_verified":False,
    }


def test_one_model(name,provider,key):
    out=OUTPUT/name
    out.mkdir(parents=True,exist_ok=False)
    model=ActualModel(name,provider,key,out)
    status={
        "model":name,"provider":provider,
        "original_new_scenario_sha256":h(SEED),
        "is_authentic_provider_attempt":True,
        "no_literary_quality_score":True,
        "original_is_synthetic_not_user_manuscript":True,
        "status":"STARTED",
    }
    try:
        packet=GroundedDraftPacket(
            scene_id="three-model-self-review-scene",
            project_id="three-model-self-review-evaluation",
            snapshot_id=0,evidence=(),craft_ids=(),
            prompt=INITIAL_PROMPT,
            prompt_sha256=h(INITIAL_PROMPT))
        original_raw=model.ask(packet,model=name,api_base=provider,
                               max_tokens=1450)
        # Store the exactly decoded original model reply independent of
        # software source validators and never silently alter its prose.
        from writerforge.writing_assist import _decode_json
        doc=_decode_json(original_raw)
        source=doc.get("prose")
        if type(source) is str and source.strip():
            (out/"ORIGINAL_MODEL_PROSE.md").write_text(source,encoding="utf8")
            status.update({
                "original_prose_sha256":h(source.strip()),
                "original_characters":len(source.strip()),
                "original_preview":source[:220],
            })
        evidence=check_turn(
            original_raw,BEAT,mode="causal_guard",accepted=())
        status["v96_original_source_validation"]="PASS"
        save_json(out/"WF_V96_ORIGINAL_RECEIPT.json",evidence["receipt"])
        prose=evidence["prose"]
        try:
            prior=external_temporal_step(prose,cast=CAST)
            status["v114_source_temporal_preflight"]="PASS"
            status["v114_open_debts"]=len(prior.get(
                "v117_open_continuity_debts",[]))
            save_json(out/"WF_V114_TEMPORAL_RECEIPT.json",{
                "source_sha256":prior["source_sha256"],
                "receipt_sha256":prior["receipt_sha256"],
                "source_anchored_events_count":prior["source_anchored_events_count"],
                "canon_writes":prior["canon_writes"]})
        except (V114ExternalMemoryError,ValueError) as error:
            status["v114_source_temporal_preflight"]=safe_exception(error)
        reflection=_ai_decides_when_to_revisit(
            raw=original_raw,beat=BEAT,accepted=(),
            turn_packet=packet,ask_model=model.ask,
            directory=out/"ai-moment")
        status["ai_choice"]=reflection["decision"]
        status["ai_why_now"]=reflection.get("reason")
        status["ai_risk_if_unchanged"]=reflection.get("risk")
        status["ai_intended_reader_effect"]=reflection.get("desired_effect")
        status["ai_source_quote"]=reflection.get("source_quote")
        status["ai_choice_receipt"]=reflection["receipt"]
        if reflection["decision"]=="LOOK_BACK_NOW":
            revised_raw,edit=_self_edit_one_turn(
                raw=original_raw,beat=BEAT,accepted=(),
                project_id=packet.project_id,scene_id=packet.scene_id,
                turn_packet=packet,ask_model=model.ask,
                round_limit=1,call_allowance=1,
                directory=out/"ai-self-edit",
                cast=CAST,
                writer_attention={
                    "reason":reflection["reason"],
                    "risk":reflection["risk"],
                    "desired_effect":reflection["desired_effect"],
                    "source_quote":reflection.get("source_quote"),
                    "focus":reflection.get("focus")})
            status["edit_receipt"]=edit
            status["ai_self_edit_statuses"]=[
                row["status"] for row in edit["rounds"]]
            revised=_decode_json(revised_raw)["prose"]
            (out/"FINAL_UNACCEPTED_CANDIDATE.md").write_text(
                revised,encoding="utf8")
            status["changed_source"]=revised!=prose
            status["final_prose_sha256"]=h(revised)
            status["final_prose_preview"]=revised[:220]
        else:
            (out/"FINAL_UNACCEPTED_CANDIDATE.md").write_text(
                prose,encoding="utf8")
            status["changed_source"]=False
            status["final_prose_sha256"]=h(prose)
        status["status"]="REAL_MODEL_EVALUATED"
    except (DeepSeekFlashError,WritingExecutionError,V96CausalDraftError,
            RuntimeError,ValueError,KeyError,TypeError,OSError) as error:
        status["status"]="REAL_MODEL_REJECTED_OR_PARTIAL"
        status["error_code"]=safe_exception(error)
        # Partial output and original full provider wire are NEVER lost.
    finally:
        status.update(summarize(model))
        save_json(out/"STATUS.json",status)
    print(json.dumps({
        "model":name,"status":status["status"],
        "error_code":status.get("error_code"),
        "calls":model.calls,
        "usage":status["provider_usage"],
        "prose_chars":status.get("original_characters",0),
        "v96":status.get("v96_original_source_validation","NOT_REACHED"),
        "ai_choice":status.get("ai_choice","NOT_REACHED"),
        "source_changed":status.get("changed_source"),
        "has_raw_wires":sum(bool(x.get("wire_preserved")) for x in model.events),
        "prose_excerpt":status.get("original_preview",""),
        "self_reason":status.get("ai_why_now",""),
    },ensure_ascii=False),flush=True)
    return status


def main():
    if OUTPUT.exists():
        raise RuntimeError("WF_REAL_COMPARE_OUTPUT_DIRECTORY_EXISTS")
    OUTPUT.mkdir(parents=True)
    # Never leak the existence, length, prefix or suffix of an actual key;
    # report only whether the selected configured path can be attempted.
    ds=os.getenv("DEEPSEEK_API_KEY")
    discovery=os.getenv("DISCOVERY_API_KEY")
    valid_ds=type(ds) is str and len(ds)>=16 and not any(x.isspace() for x in ds)
    valid_discovery=type(discovery) is str and len(discovery)>=12 and not any(
        x.isspace() for x in discovery)
    availability=None
    if valid_discovery:
        try:
            availability=discover_models(discovery)
        except Exception as exc:
            availability=set()
            print(json.dumps({
                "stage":"DISCOVERY_MODELS_FAILED",
                "error_code":safe_exception(exc),
                "models_present":False,
            }),flush=True)
    results=[]
    for name,provider in MODELS:
        key=ds if provider=="deepseek" else discovery
        if not (valid_ds if provider=="deepseek" else valid_discovery):
            item={"model":name,"provider":provider,
                  "status":"EXISTING_SECRET_UNAVAILABLE",
                  "calls_attempted":0,
                  "literary_quality_independently_verified":False}
            results.append(item)
            continue
        if provider=="discovery" and name not in (availability or ()):
            item={"model":name,"provider":provider,
                  "status":"MODEL_NOT_ON_AUTHENTICATED_DISCOVERY_LIST",
                  "calls_attempted":0,
                  "literary_quality_independently_verified":False}
            results.append(item)
            continue
        results.append(test_one_model(name,provider,key))
    output={
        "format":"wf.real-three-existing-writers-20261024.v1",
        "status":"FINISHED_WITH_AUTHENTIC_PARTIALS",
        "models_configured":[n for n,_ in MODELS],
        "tests":[{
            k:v for k,v in item.items() if k not in (
                "original_preview","final_prose_preview",
                "ai_choice_receipt","edit_receipt","calls",
                "ai_why_now","ai_risk_if_unchanged",
                "ai_intended_reader_effect","ai_source_quote")}
            for item in results],
        "total_calls_attempted":sum(row.get("calls_attempted",0)
                                    for row in results),
        "max_total_provider_calls":PER_MODEL_MAX_CALLS*len(MODELS),
        "max_requested_output_tokens_all":(
            PER_MODEL_MAX_REQUESTED_TOKENS*len(MODELS)),
        "same_new_original_scene_sha256":h(SEED),
        "independent_literary_blind_review_completed":False,
        "full_two_chapter_Studio_trial_completed":False,
        "no_automatic_retry":True,
        "no_canon_or_R2_writes":True,
    }
    save_json(OUTPUT/"STATUS.json",output)
    print(json.dumps({
        "status":output["status"],
        "actual_calls":output["total_calls_attempted"],
        "max_calls":output["max_total_provider_calls"],
        "models":[[x["model"],x["status"],x.get("ai_choice")]
                  for x in results],
        "no_model_refilled_or_forced_lookback":True,
        "literary_quality_verified":False,
    },ensure_ascii=False),flush=True)
    return 0


if __name__=="__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({
            "stage":"REAL_COMPARE_RUNNER_ERROR",
            "error_code":safe_exception(exc),
            "partial_artifacts_preserved":OUTPUT.exists(),
        },ensure_ascii=False),flush=True)
        sys.exit(2)
