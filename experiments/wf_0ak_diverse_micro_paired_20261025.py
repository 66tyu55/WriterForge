"""0.AK last batch: mundane lost-key scene and snow farewell lyric, no required twist.

Use the SAME DeepSeek Flash and author max-output-token cap for bare and
WF. Each author gets only ONE paid answer, 200-350 Chinese codepoints targeted.
Preserve actual provider envelopes *before* parsing, score with two blind
counterbalanced orders, never feed grades or reader opinions into WF.

THIS IS ONLY an experiment, not WriterForge's writer, judge, or memory.
No R2, Canon, Railway, reference books, external material, retries or source
revisions. Invalid output => frozen failure, not a convenient replacement.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import os
import re

from experiments.wf_0ad_multigenre_real_paired_writing_20261025 import (
    CRITERIA,JUDGEMENTS,parse_judge,normalize,
)
from experiments.wf_0ag_diverse_micro_paired_20261025 import (
    parse_micro_judge as _shared_source_graded_parser,
)
from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget
from writerforge.v96_causal_turns import (
    check_turn,make_turn_instructions,normalize_model_source_citations,
    V96CausalDraftError,
)
from writerforge.v116_state_delta import preflight_next_prose
from writerforge.v114_external_story_state import (
    external_temporal_step,require_external_runtime,
)

OUT=Path("wf_0ak_diverse_micro_batch4_20261025")
AUTHOR_OUTPUT_TOKENS=1400
RATER_OUTPUT_TOKENS=1600
BATCH=("daily_keys","lyrical_snow")
MAX_CALLS=4*len(BATCH)
OUTPUT_RESERVATION_CAP=len(BATCH)*(2*AUTHOR_OUTPUT_TOKENS+2*RATER_OUTPUT_TOKENS)
# Ten pre-registered original 0.AF genre tasks unchanged; ONLY the next three are paid here.
GENRES=(
    {"id":"wuxia_bridge","genre":"武侠","role":"受伤空间与选择代价",
     "actor":"周阙","kind":"action",
     "topic":"镖师周阙背着伤了腿的同行者过悬桥。木板缺损，桥索发晃，对岸有人催促。他不能突然学会新武功，身体和随身物品须符合位置及受伤限制。",
     "literary_task":"动作、空间和身体负担决定取舍；留白可以存在，但不能凭空消除伤势。"},
    {"id":"xianxia_plant","genre":"仙侠","role":"资源归属与有限认知",
     "actor":"桑蓉","kind":"decision",
     "topic":"灵植比预计提前成熟，主人公开门以前不知道是谁采摘，灵力与收成不能凭空增加。",
     "literary_task":"角色必须区分观察、怀疑和确知，采摘后的资源消耗有来处。"},
    {"id":"history_message","genre":"历史","role":"一夜传令与代价",
     "actor":"秦渊","kind":"decision",
     "topic":"边关前锋发出的文书需一夜才送抵主帅；将令的传递时间不能被压缩成瞬间。",
     "literary_task":"交代可知军情、传令限制与决策时差，不解释未来结果。"},
    {"id":"horror_flashlight","genre":"恐怖","role":"断电有限视角",
     "actor":"宋芜","kind":"quiet",
     "topic":"深夜老屋断电，宋芜手电的光只能照到狭窄一角。她听到异响，却没有看见来源；禁止从她的有限视角写出不可见的确定事实。",
     "literary_task":"以声音、误解和空间信息营造紧张，允许不揭露真相。"},
    {"id":"comedy_breakfast","genre":"喜剧","role":"错单逐渐解除误会",
     "actor":"阿桃","kind":"dialogue",
     "topic":"早餐店错把客人的订单交给熟客，误会在正常交谈中逐渐化解，不得用凭空巧合抢夺笑点。",
     "literary_task":"信息差与节奏自然，不强行反转或强迫每句有因果披露。"},
    {"id":"romance_photos","genre":"言情","role":"双方各自未知旧照片",
     "actor":"谢音","kind":"dialogue",
     "topic":"两个人签分手协议，却都不知道对方暗自保存了一张旧照片。",
     "literary_task":"保留各自动机与认知边界，避免旁白代角色宣布知道对方秘密。"},
    {"id":"daily_keys","genre":"日常","role":"钥匙与亲情摩擦",
     "actor":"田姨","kind":"quiet",
     "topic":"老人和孙女找钥匙，一番争执后钥匙在旧鞋里找到，不能凭空移入新的地点。",
     "literary_task":"细节与人物关系承载情绪，不强迫戏剧性反转。"},
    {"id":"scifi_airlock","genre":"科幻灾难","role":"压差舱门与通讯延迟",
     "actor":"唐弦","kind":"decision",
     "topic":"深空舱门出现压差，三个角色有不同延迟的通讯渠道，物理和时间限制必须成立。",
     "literary_task":"明确实际可知与不可知的信息，不用新设备解决已知限制。"},
    {"id":"strategy_ledger","genre":"计谋","role":"两张异日借据的牵制",
     "actor":"裴缙","kind":"decision",
     "topic":"盐商裴缙用两张日期不同的借据互相牵制，印章和钱款的来源必须能核对，不能把同在场的两件事误作有因果。",
     "literary_task":"因果靠证据链及动机落实，人物可以误判，却不能凭空获得信息。"},
    {"id":"lyrical_snow","genre":"抒情环境","role":"初雪夜送别",
     "actor":"乔溪","kind":"quiet",
     "topic":"初雪夜两人在路口送别，没有追逐、阴谋或必须解开的秘密。",
     "literary_task":"环境、动作和节奏承担情绪；不因缺少悬念而被误判写作失败。"},
)
SCENE_BY_ID={r["id"]:r for r in GENRES}

def h(s):
    return sha256(s.encode("utf8") if type(s) is str else s).hexdigest()

def need(ok,code):
    if not ok:
        raise RuntimeError(code)

def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2),
                    encoding="utf8")

def scene_prompt(item):
    return (
        "【冻结的原创文学任务；两组同题】类型："+item["genre"]+
        "；文学功能："+item["role"]+"；主角："+item["actor"]+
        "；情境："+item["topic"]+"；任务："+item["literary_task"]+
        "请只写一个200至350个中文字符（包含中文标点）的完整小说微段。"
        "不要写整章、题目、背景介绍或解释，也不要模仿名著人物、句子或剧情。"
        "保持人物自身行为与未说出的动机，不用结尾强制反转；输出仍为原创。"
    )

def beat(item):
    return {"id":"t01","kind":item["kind"],"actor":item["actor"],
            "goal":item["literary_task"]+"，作者独立决定具体动作与文字",
            "causal_parent":None,"craft_focus":[]}

def prompt(item,arm):
    same=scene_prompt(item)
    if arm=="bare":
        return same+'仅返回JSON对象：{"prose":"原创新写的微段正文"}。'
    return (same+"【WF来源边界，只核查已有原句和已有状态，不代写也不规定结局】"+
            make_turn_instructions(beat(item),mode="causal_guard")+
            "上述原有WF提示中的建议长度让位于本次同题的200至350字目标。")

class Model:
    def __init__(self,api_key):
        self.calls=[]
        self.task=None
        self.budget=FlashBudget(max_calls=MAX_CALLS,
                                max_reserved_output_tokens=OUTPUT_RESERVATION_CAP)
        self.client=DeepSeekFlashModel(api_key=api_key,budget=self.budget,
                                       timeout_seconds=110,
                                       on_response_wire=self.save_wire)

    def save_wire(self,data):
        need(type(data) is bytes and self.task is not None,
             "WF0AG_ORPHAN_ORIGINAL_PROVIDER_WIRE")
        record=self.calls[-1]
        need(record["raw_provider_sha256"] is None,
             "WF0AG_DUPLICATE_PROVIDER_WIRE")
        path=OUT/"provider-originals"/(self.task+".json")
        path.parent.mkdir(parents=True,exist_ok=True)
        need(not path.exists(),"WF0AK_DUPLICATE_PROVIDER_WIRE_NO_OVERWRITE")
        path.write_bytes(data) # preserve FIRST, never rewrite by retry
        record["raw_provider_sha256"]=h(data)
        record["original_wire_preserved"]=True

    def ask(self,item,task,role,question,max_tokens):
        need(self.task is None and task in (
            "bare-author","WF-author","blind-1","blind-2"),
            "WF0AG_TASK_NOT_PREDECLARED_OR_REENTRANT")
        self.task=item["id"]+"_"+task
        record={"task":self.task,"scene":item["id"],
                "role":role,"prompt_sha256":h(question),
                "max_tokens":max_tokens,"raw_provider_sha256":None,
                "original_wire_preserved":False}
        self.calls.append(record)
        try:
            result=self.client.ask_json(
                role=role,system=(
                  "你是一名中文原创文学写作者或匿名评审，只回应当前角色要求。"
                  "不能读取外部原著，不使用固定评分当生成目标，必须输出JSON对象。"),
                user=question,max_tokens=max_tokens)
            record["decoded_sha256"]=h(json.dumps(
                result,ensure_ascii=False,separators=(",",":")))
            record["response_format_recovery"]=(
                self.client.last_response_format_recovery)
            return result
        finally:
            self.task=None

def check_source(item,content):
    doc=content["WF"]
    source=doc["prose"]
    original_json=json.dumps(doc,ensure_ascii=False,separators=(",",":"))
    normalized,normalized_receipt=normalize_model_source_citations(
        original_json,beat(item),accepted=())
    need(json.loads(normalized)["prose"]==source,
         "WF0AG_SOURCE_CITATION_CHANGED_AUTHOR_PROSE")
    try:
        row=check_turn(normalized,beat(item),mode="causal_guard",
                       accepted=(),max_prose_chars=1024)
        verdict="SOURCE_QUOTES_ORDER_VERIFIED_CAUSALITY_NOT_PROVEN"
        cause_review={
            "reason":row["receipt"].get("source_causal_review_reason"),
            "review_required":row["receipt"].get("source_causal_review_required"),
            "relation_verified":row["receipt"].get("causal_relation_verified"),
        }
        v96_code=None
    except V96CausalDraftError as err:
        verdict="HELD_V96_SOURCE_OR_TRACE"
        v96_code=str(err)
        cause_review={"reason":"TRACE_HELD","review_required":True,
                      "relation_verified":False}
    p=preflight_next_prose(
        source,previous_candidate_state={},cast=(item["actor"],))
    cp=external_temporal_step(source,cast=(item["actor"],))
    need(cp["source_sha256"]==h(source),
         "WF0AG_V114_SOURCE_SHA_DRIFT")
    return {
        "V96_status":verdict,"V96_failure_code":v96_code,
        "V96_causal_relation":cause_review,
        "V116_findings":p["findings"],
        "V116_needs_review":p["needs_review"],
        "V116_review_findings":p["review_findings"],
        "V122_physical_review_pairs":p["physical_relation_review_pairs"],
        "V114_candidate_receipt_sha256":cp["receipt_sha256"],
        "source_sha256":h(source),
        "citation_normalization_receipt":normalized_receipt,
        "candidate_accepted_into_Canon":False,
        "model_or_WF_literary_truth_verified":False,
        "false_positive_count_confirmed":None,
        "false_negative_count_confirmed":None,
        "human_semantic_review_still_required":True,
    }

def parse_micro_judge(answer):
    """Reuse 0.AG's ORIGINAL scored-source parser; no separate grade truth."""
    return _shared_source_graded_parser(answer)


def judge_prompt_0ag(item,pair,order):
    # Frozen from the first actual three provider judge wires, zero prose
    # rewrites. This text MUST NOT drift on the no-author score replay.
    q=("匿名阅读同一原创微段文学任务的两个正文，五项各给0至20整数分。"
       "只根据实际文字，不猜哪篇来自WF，不把任何技术检测结果作为文学分数。"
       "五项是："+ "、".join(CRITERIA) +"。"
       "输出唯一JSON对象，ratings必须恰有甲乙，"
       "每项包含id、scores（上列五项）、reason、weakness；"
       "客观描述明显长短差异，不自行补写故事。"
       "\n【原始同题目标】"+scene_prompt(item))
    for arm,label in zip(order,("甲","乙")):
        q+="\n【匿名"+label+"】"+pair["bare" if arm=="裸模型" else "WF"]["prose"]
    return q


def judge_one(model,item,pair,order,task):
    q=judge_prompt_0ag(item,pair,order)
    parsed,representation_receipt=parse_micro_judge(
        model.ask(item,task,"craft_analysis",q,RATER_OUTPUT_TOKENS))
    return {name:{
        "score_representation_receipt":representation_receipt,
        "score":sum(parsed[label]["scores"].values()),
        "dimensions":parsed[label]["scores"],
        "model_reason":parsed[label]["reason"],
        "model_weakness":parsed[label]["weakness"],
    } for name,label in zip(order,("甲","乙"))}

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    summary={
        "format":"wf.0ak.fourth-new-diverse-micro-two-paired.v1",
        "status":"NOT_STARTED","frozen_ten_task_ids":[g["id"] for g in GENRES],
        "frozen_ten_task_spec_sha256":h(json.dumps(
            GENRES,ensure_ascii=False,sort_keys=True,separators=(",",":"))),
        "first_batch":list(BATCH),"cases":{},
        "same_model":"deepseek-flash",
        "same_author_max_tokens":AUTHOR_OUTPUT_TOKENS,
        "same_author_temperature":"adapter_default_not_overridden",
        "same_authorship_task_with_WF_provenance_intervention":True,
        "author_target_codepoints":[200,350],
        "rater_criteria":list(CRITERIA),"rater_blind_orders":len(JUDGEMENTS),
        "same_family_rater_not_human":True,
        "literary_grade_not_used_for_writer_reward":True,
        "no_second_author_call_or_retries":True,
        "no_original_book_used":True,"prior_0AD_0AE_author_calls_repeated":0,
        "R2_reads":0,"R2_writes":0,"Canon_writes":0,
        "Railway_deployments":0,"main_modified":False,
        "actual_model_calls":0,"reserved_output_cap":OUTPUT_RESERVATION_CAP,
    }
    model=None
    try:
        require_external_runtime()
        need(not any(os.getenv(name) for name in (
             "DISCOVERY_API_KEY","OPENAI_API_KEY","WRITERFORGE_R2_ACCOUNT_ID",
             "WRITERFORGE_R2_ACCESS_KEY_ID","OPENROUTER_API_KEY")),
             "WF0AG_UNNEEDED_VENDOR_OR_ORIGINAL_BOOK_CREDENTIAL")
        secret=os.getenv("DEEPSEEK_API_KEY","")
        need(len(secret)>=16,"WF0AG_MISSING_EXISTING_PROVIDER_KEY")
        model=Model(secret)
        for key in BATCH:
            item=SCENE_BY_ID[key]
            case={"genre":item["genre"],"role":item["role"],
                  "pre_registered_task_sha256":h(json.dumps(
                      item,ensure_ascii=False,sort_keys=True)),
                  "original_writer_ready":False,"scores_ready":False,
                  "source_and_causality_pre_post":{
                    "pre_existing_0AF_status":"NOT_GENERATED",
                    "after_0AG_repair":"PENDING_AUTHOR_OUTPUT",
                    "semantic_truth_verified":False},
                  "true_WF_false_positives_confirmed":None,
                  "true_WF_false_negatives_confirmed":None,
                  "actual_world_logic_errors_confirmed":None}
            summary["cases"][key]=case
            pair={}
            for arm,task in (("bare","bare-author"),("WF","WF-author")):
                try:
                    answer=model.ask(item,task,"self_scene_writing",
                                     prompt(item,arm),AUTHOR_OUTPUT_TOKENS)
                    answer=normalize(answer,("prose",) if arm=="bare"
                                     else ("prose","trace"))
                    need(type(answer["prose"]) is str,
                         "WF0AG_AUTHOR_PROVIDER_SCHEMA_INVALID")
                    prose=answer["prose"].strip()
                    pair[arm]=dict(answer)
                    pair[arm]["prose"]=prose
                    (OUT/"author-originals").mkdir(parents=True,exist_ok=True)
                    (OUT/"author-originals"/(key+"-"+arm+".md")).write_text(
                        prose,encoding="utf8")
                    case[arm+"_source_sha256"]=h(prose)
                    case[arm+"_codepoints"]=len(prose)
                    case[arm+"_within_200_350"]=200<=len(prose)<=350
                except Exception as error:
                    case["status"]="AUTHOR_FAILED_NO_RETRY"
                    case["failure_code"]=(str(error) if re.fullmatch(
                        r"WF[A-Z0-9_:\-]{3,170}",str(error))
                        else type(error).__name__+":AUTHOR_FAILED")
                    save(OUT/"PARTIAL.json",summary)
                    break
            if len(pair)!=2:
                continue
            case["original_writer_ready"]=True
            ratio=max(len(pair["bare"]["prose"]),len(pair["WF"]["prose"]))/max(
                1,min(len(pair["bare"]["prose"]),len(pair["WF"]["prose"])))
            case["author_length_ratio"]=round(ratio,3)
            case["lengths_comparable_within_15pct"]=ratio<=1.15
            try:
                case["WF_source_checks"]=check_source(item,pair)
                case["source_and_causality_pre_post"]={
                    "pre_existing_0AF_status":"NOT_GENERATED",
                    "after_0AG_repair":case["WF_source_checks"]["V96_status"],
                    "source_relation_review":case["WF_source_checks"][
                        "V96_causal_relation"],
                    "semantic_truth_verified":False}
            except Exception as error:
                case["source_verdict"]="SOURCE_AUDIT_FAILED_NO_RETRY"
                case["source_failure_code"]=(
                    str(error) if re.fullmatch(r"WF[A-Z0-9_:\-]{3,170}",str(error))
                    else type(error).__name__+":SOURCE_REVIEW")
            case["author_length_target_met"]=all(
                case.get(arm+"_within_200_350",False)
                for arm in ("bare","WF"))
            if not case["author_length_target_met"]:
                case["status"]="NOT_COMPARABLE_AUTHOR_LENGTH_OUT_OF_BOUND"
                save(OUT/"PARTIAL.json",summary)
                continue
            reviews={"裸模型":[],"WF辅助":[]}
            for order,task in zip(JUDGEMENTS,("blind-1","blind-2")):
                try:
                    out=judge_one(model,item,pair,order,task)
                    for label in reviews:
                        reviews[label].append(out[label])
                except Exception as error:
                    case["rater_failure_code"]=(
                        str(error) if re.fullmatch(
                            r"WF[A-Z0-9_:\-]{3,170}",str(error))
                        else type(error).__name__+":RATER")
                    break
            if all(len(reviews[z])==2 for z in reviews):
                case["scores_ready"]=True
                case["ratings"]={
                    label:{
                        "score_100":sum(p["score"] for p in vals)/2,
                        "order_scores":[p["score"] for p in vals],
                        "order_sensitivity":abs(vals[0]["score"]-vals[1]["score"]),
                        "dimensions_mean":{
                            axis:sum(v["dimensions"][axis] for v in vals)/2
                            for axis in CRITERIA},
                        "verbatim_rater_opinions":vals,
                    } for label,vals in reviews.items()}
                case["WF_minus_bare"]=round(
                    case["ratings"]["WF辅助"]["score_100"]-
                    case["ratings"]["裸模型"]["score_100"],2)
                max_disagreement=max(
                    case["ratings"][key]["order_sensitivity"]
                    for key in reviews)
                case["comparison_confidence"]=(
                    "NOT_COMPARABLE" if not case["lengths_comparable_within_15pct"]
                    else "LOW_CONFIDENCE" if max_disagreement>8
                    else "EXPLORATORY_SINGLE_MODEL_FAMILY_ONLY")
                case["status"]="PAIRED_SOURCE_AND_BLIND_GRADE_SAVED"
            else:
                case["status"]="ORIGINAL_SOURCES_SAVED_JUDGE_MISSING"
            save(OUT/"PARTIAL.json",summary)
        summary["status"]="FINISHED_WITH_ORIGINAL_SOURCES_OR_FAILURES"
    except Exception as err:
        summary["status"]="BOUNDED_RUN_HALTED_NO_RETRY"
        summary["failure_code"]=(
            str(err) if re.fullmatch(r"WF[A-Z0-9_:\-]{3,170}",str(err))
            else type(err).__name__+":HALTED")
    finally:
        if model is not None:
            summary["actual_model_calls"]=model.budget.calls_reserved
            summary["provider_usage"]=model.budget.public_receipt()
            summary["provider_calls"]=model.calls
        save(OUT/"STATUS.json",summary)
        print("WF0AK_MICRO_BATCH4 "+json.dumps({
            "status":summary["status"],
            "calls":summary["actual_model_calls"],
            "cases":{k:{
                "status":v.get("status"),
                "score_difference":v.get("WF_minus_bare"),
                "WF_source_status":v.get("WF_source_checks",{}).get("V96_status"),
                "WF_causal_review":v.get("WF_source_checks",{}).get(
                    "V96_causal_relation",{}).get("reason"),
                "confidence":v.get("comparison_confidence"),
            } for k,v in summary["cases"].items()},
            "book_training_calls":0,
        },ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
