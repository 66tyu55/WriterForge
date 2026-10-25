"""0.AD: four DIFFERENT original scene-types, bare vs actual WF V96/V122 assistance.

One pre-registered two-arm task per genre. Original prose comes exclusively
from existing DeepSeek Flash. No references, copywork, R2, Canon or training.
Blind two-order quality rater exists ONLY as an external evaluation experiment,
NEVER author feedback or a WriterForge self-grader. No forced edits/retries.

Do not infer literary improvement from a single 4-task model-family rater.
Report exact author provider SHA, exact WF source risks and per-task numbers.
"""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import json
import os
import re

from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget
from writerforge.v96_causal_turns import (check_turn,make_turn_instructions,
    normalize_model_source_citations,V96CausalDraftError)
from writerforge.v116_state_delta import preflight_next_prose
from writerforge.v114_external_story_state import external_temporal_step,require_external_runtime

OUT=Path("wf_0ad_multigenre_writer_pilot_20261025")
MAX_CALLS=16
MAX_OUTPUT_RESERVED=27000
GENRES=(
    {"id":"realism","genre":"现实文学","role":"安静人物心理",
     "actor":"许临",
     "kind":"quiet",
     "topic":"北方小城的夜班公交总站，清洁工许临与父亲通电话。父亲不愿承认自己看不清药盒的小字；许临明早也必须上班。用一段真实小动作显露不说破的担忧，禁突然和解和说教。",
     "literary_task":"以生活细节承载复杂情绪，而不是解释情绪。"},
    {"id":"fantasy","genre":"原创玄幻","role":"近身打斗与代价",
     "actor":"顾弦",
     "kind":"action",
     "topic":"山门雪夜，守夜学徒顾弦发现陌生人要带走用于防雪崩的古铜铃；顾弦没有高深法力。写一场短促的真实阻挡行动与当下代价，不得临时获得神功或武器。",
     "literary_task":"动作的来源、空间位置、阻力和代价都从实际文字成立。"},
    {"id":"mystery","genre":"悬疑推理","role":"现场证据与知识边界",
     "actor":"沈栀",
     "kind":"action",
     "topic":"老旅馆失窃案现场，调查员沈栀检查一张昨夜被雨打湿的值班登记表和停摆的走廊时钟。只能写确实能观察到的线索，不能直接替角色猜到犯人或凭空确定时间。",
     "literary_task":"证据让读者感到疑问，而不是由作者公布答案。"},
    {"id":"scifi","genre":"硬科幻","role":"技术约束下的伦理选择",
     "actor":"林载",
     "kind":"decision",
     "topic":"近地轨道居住舱突然出现缓慢漏气报警，维修员林载必须在检修舱门锁与等待搭档返回之间做一项具有风险的选择，不能凭空增加新设备或忽略氧气损耗。",
     "literary_task":"以可理解的技术限制逼出真实人物选择与代价。"},
)
CRITERIA=("语言自然与节制","具体细节的叙事作用","动作与因果可信度","人物心理与动机","类型目标完成程度")
JUDGEMENTS=(("裸模型","WF辅助"),("WF辅助","裸模型"))

def guard(x,code):
    if not x:raise RuntimeError(code)
def h(value):
    return sha256(value.encode("utf8") if type(value) is str else value).hexdigest()
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf8")
def normalize(value,expected):
    if type(value) is dict and set(value)==set(expected)|{"type"} and value["type"]=="json_object":
        value={k:v for k,v in value.items() if k!="type"}
    guard(type(value) is dict and set(value)==set(expected),"WF0AD_MODEL_SCHEMA_INVALID")
    return value

class BoundedModel:
    def __init__(self,key):
        self.budget=FlashBudget(max_calls=MAX_CALLS,
            max_reserved_output_tokens=MAX_OUTPUT_RESERVED)
        self.calls=[]
        self.active=None
        self.client=DeepSeekFlashModel(
            api_key=key,budget=self.budget,timeout_seconds=110,
            on_response_wire=self.on_original_wire)
    def on_original_wire(self,wire):
        guard(type(wire) is bytes and self.active is not None,
              "WF0AD_ORPHAN_PROVIDER_RESPONSE")
        # Generated fiction is our ORIGINAL content, but raw provider
        # envelopes may carry account metadata: retain only signed hash.
        self.calls[-1]["raw_provider_sha256"]=h(wire)
        path=OUT/"provider-originals"/(self.active.replace(":","_")+".json")
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(wire)
        self.calls[-1]["original_wire_preserved"]=True
    def ask(self,scene_id,task,role,prompt,tokens):
        guard(len(self.calls)<MAX_CALLS and task in (
            "bare-author","WF-author","anonymous-rater-first",
            "anonymous-rater-reversed"),"WF0AD_CALL_OUTSIDE_FROZEN_SCOPE")
        self.active=f"{scene_id}:{task}"
        self.calls.append({
            "scene":scene_id,"task":task,"prompt_sha256":h(prompt),
            "max_tokens_reserved":tokens,"raw_provider_sha256":None,
            "same_model_family":True})
        answer=self.client.ask_json(
            role=role,system=(
                "你是中文小说文本任务的写作者或独立盲评读者。"
                "严格只输出当前任务要求的 JSON 对象，不额外解释。"
                "禁止复制任何现成作品的文字和人物。"),
            user=prompt,max_tokens=tokens)
        self.calls[-1]["decoded_original_sha256"]=h(json.dumps(
            answer,ensure_ascii=False,separators=(",",":")))
        return answer

def scene_prompt(item):
    return (
        "【冻结的原创文学任务，两个写作组完全相同】"
        "类型："+item["genre"]+
        "；叙事作用："+item["role"]+
        "；目标人物："+item["actor"]+"；"
        "场景："+item["topic"]+
        "；文学要求："+item["literary_task"]+
        "只能写一个约260到340汉字的完整小说片段。"
        "必须原创，不能引用或模仿任何名著的角色、物件或原句。"
        "不得一口气写整章；人物想法、行动和未完成悬念由你自己决定。"
        "不解释写作原理，不附评价，不预测未来章节。")

def author_pair(writer,item):
    shared=scene_prompt(item)
    bare=writer.ask(item["id"],"bare-author","self_scene_writing",
        shared+"仅输出 JSON: {\"prose\":\"你真正创作的小说原文\"}。",1350)
    bare=normalize(bare,("prose",))
    raw=bare["prose"]
    guard(type(raw) is str and 130<=len(raw)<=900,
          "WF0AD_BARE_AUTHOR_PROSE_LENGTH_INVALID")
    beat={"id":"t01","kind":item["kind"],"actor":item["actor"],
          "goal":item["literary_task"]+"人物在已有场景中自行决定语言与行动",
          "causal_parent":None,"craft_focus":[]}
    wf_prompt=(shared+"\n【WF原有V96候选来源契约，仅供校验，不规定小说答案】"+
               make_turn_instructions(beat,mode="causal_guard"))
    assisted=writer.ask(item["id"],"WF-author","self_scene_writing",
                        wf_prompt,1800)
    assisted=normalize(assisted,("prose","trace"))
    original=json.dumps(assisted,ensure_ascii=False,separators=(",",":"))
    wf=assisted["prose"]
    guard(type(wf) is str and 130<=len(wf)<=1024,
          "WF0AD_WF_AUTHOR_PROSE_LENGTH_INVALID")
    # Real novelist prose is worth literary comparison EVEN IF its citation
    # trace is malformed. It must NEVER silently become a valid WF source.
    # Reuse the existing WF V96 exact-literal trace normalization instead
    # of paying the author to regenerate the same original paragraph.
    normalized,trace_receipt=normalize_model_source_citations(
        original,beat,accepted=())
    guard(json.loads(normalized)["prose"]==wf,
          "WF0AD_TRACE_NORMALIZATION_ALTERED_AUTHOR_TEXT")
    trace_status="HELD_SOURCE_TRACE_INVALID"
    trace_error=None
    receipt=None
    try:
        checked=check_turn(normalized,beat,mode="causal_guard",
                           accepted=(),max_prose_chars=1024)
        guard(checked["prose"]==wf.strip(),
              "WF0AD_V96_MODIFIED_NOVELIST_ORIGINAL")
        trace_status="EXACT_SOURCE_QUOTES_CONFIRMED"
        receipt=checked["receipt"]["causal_check"]
    except V96CausalDraftError as err:
        trace_error=str(err)
    # Independent SOURCE-level checks still run on genuine prose and may
    # HOLD an unresolved state even if action/effect trace is invalid.
    preflight=preflight_next_prose(
        wf.strip(),previous_candidate_state={},cast=(item["actor"],))
    cp=external_temporal_step(
        wf.strip(),cast=(item["actor"],))
    guard(cp["source_sha256"]==h(wf.strip()) and
          cp["v122_physical_relation_source_receipt"]["source_sha256"]==
            h(wf.strip()),"WF0AD_WRITER_SOURCE_LINEAGE_INVALID")
    return {
        "bare":{"source_sha256":h(raw),"prose":raw},
        "WF":{"source_sha256":h(wf.strip()),"prose":wf.strip(),
              "V96":receipt,
              "V96_status":trace_status,
              "V96_failure_code":trace_error,
              "V96_original_reply_sha256":h(original),
              "V96_literal_citation_normalization":trace_receipt,
              "candidate_not_accepted_if_trace_invalid":True,
              "V116_blocked":preflight["blocked"],
              "V116_hard_findings":preflight["findings"],
              "V116_needs_review":preflight["needs_review"],
              "V116_review_findings":preflight["review_findings"],
              "V122_relation_pairs":preflight["physical_relation_review_pairs"],
              "V114_candidate_sha256":cp["receipt_sha256"]},
        "stage_source_verified":True,
    }

def judge_prompt(item,pair,order):
    base=(
        "这是中文原创小说同一文学任务的匿名对照。请只评价实际正文。"
        "两个文本属于同一个类型和同一个场景目标，分别由同模型写出。"
        "禁止猜测哪一篇使用了WF或调整文学分数迎合软件。"
        "相同五个标准，每项0到20，分数整数："+
        "、".join(CRITERIA)+
        "。只论实际可见的文字，具体说明优点和一个不足。"
        "不要复制句子超过10字，不要自己补写剧情。"
        "仅返回JSON：ratings数组两条，每条对象严格id、scores、"
        "reason、weakness；scores含上列五项且每项整数0～20。"
        "\n【冻结同题任务】"+scene_prompt(item))
    for code,label in zip(order,("甲","乙")):
        base+="\n【匿名"+label+"】"+pair["bare" if code=="裸模型" else "WF"]["prose"]
    return base

def parse_judge(answer):
    answer=normalize(answer,("ratings",))
    values=answer["ratings"]
    guard(type(values) is list and len(values)==2,
          "WF0AD_JUDGE_RESULT_NOT_TWO")
    seen={}
    for v in values:
        guard(type(v) is dict and set(v)=={"id","scores","reason","weakness"}
              and type(v["id"]) is str,
              "WF0AD_JUDGE_ID_SCHEMA_INVALID")
        # JSON-only DeepSeek sometimes returns the exact harmless UI
        # prefix "匿名甲"/"匿名乙". Normalize LABEL only, never a score.
        label=v["id"][2:] if v["id"].startswith("匿名") else v["id"]
        guard(label in ("甲","乙") and label not in seen,
              "WF0AD_JUDGE_ID_SCHEMA_INVALID")
        score=v["scores"]
        guard(type(score) is dict and set(score)==set(CRITERIA) and
              all(type(n) is int and 0<=n<=20 for n in score.values()) and
              all(type(v[key]) is str and 6<=len(v[key])<=160 for key in ("reason","weakness")),
              "WF0AD_JUDGE_SCORE_OR_EXPLANATION_INVALID")
        seen[label]={**v,"id":label}
    guard(set(seen)=={"甲","乙"},"WF0AD_JUDGE_MISSING_SAMPLE")
    return seen

def judge_pair(model,item,pair):
    rows={"裸模型":[],"WF辅助":[]}
    for idx,order in enumerate(JUDGEMENTS):
        result=parse_judge(model.ask(
            item["id"],
            "anonymous-rater-first" if idx==0 else "anonymous-rater-reversed",
            "craft_analysis",judge_prompt(item,pair,order),1600))
        for key,label in zip(order,("甲","乙")):
            v=result[label]
            # Reasons are authored by the judge; these are preliminary
            # opinions, NOT a source-proven literary diagnosis of WF.
            rows[key].append({
                "score":sum(v["scores"].values()),
                "dimensions":v["scores"],
                "reason":v["reason"],"weakness":v["weakness"]})
    out={}
    for key,ratings in rows.items():
        out[key]={
            "score_100":sum(z["score"] for z in ratings)/2,
            "per_order_scores":[z["score"] for z in ratings],
            "order_sensitivity":abs(ratings[0]["score"]-ratings[1]["score"]),
            "criterion_means":{c:sum(x["dimensions"][c] for x in ratings)/2
                               for c in CRITERIA},
            "blind_reasons":ratings,
        }
    out["WF_minus_bare"]=out["WF辅助"]["score_100"]-out["裸模型"]["score_100"]
    return out

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    summary={
        "format":"wf.0ad.multigenre-real-original-writing-v1",
        "status":"NOT_STARTED",
        "cases":{},"genres":[x["genre"] for x in GENRES],
        "real_model_call_cap":MAX_CALLS,
        "real_reserved_output_token_cap":MAX_OUTPUT_RESERVED,
        "same_model_same_goal_two_arms":True,
        "blind_counterbalanced_same_model_rater":True,
        "rater_is_not_independent_human_review":True,
        "comparison_score_is_provisional_not_novel_grade":True,
        "no_preexisting_copyrighted_source_used":True,
        "no_author_forced_revisions_or_retries":True,
        "WF_literary_superiority_not_proven":True,
        "R2_reads":0,"R2_writes":0,"canon_writes":0,
        "Railway_deployments":0,"main_modified":False,
        "actual_model_calls":0,
    }
    model=None
    try:
        require_external_runtime()
        guard(not any(os.getenv(x) for x in (
            "WRITERFORGE_R2_ACCOUNT_ID","WRITERFORGE_R2_ACCESS_KEY_ID",
            "DISCOVERY_API_KEY","OPENAI_API_KEY")),
            "WF0AD_UNNEEDED_EXTRA_SOURCE_PROVIDER_CONFIGURED")
        secret=os.getenv("DEEPSEEK_API_KEY","")
        guard(len(secret)>=16,"WF0AD_WRITER_KEY_NOT_AVAILABLE")
        model=BoundedModel(secret)
        for item in GENRES:
            name=item["id"]
            row={"genre":item["genre"],"literary_role":item["role"],
                 "author_real_prose_ready":False,
                 "blind_ratings_ready":False}
            summary["cases"][name]=row
            try:
                author=author_pair(model,item)
            except Exception as exc:
                code=str(exc)
                row["status"]="REAL_AUTHOR_SOURCE_INVALID_NO_RETRY"
                row["failure_code"]=(
                    code if re.fullmatch(r"WF[A-Z0-9_:\-]{3,170}",code)
                    else type(exc).__name__+":SOURCE_INVALID")
                save(OUT/"PARTIAL.json",summary)
                continue
            row["author_real_prose_ready"]=True
            row["source_evidence"]={
                arm:{"source_sha256":author[arm]["source_sha256"],
                     "chars":len(author[arm]["prose"])}
                for arm in ("bare","WF")}
            row["WF_source_checks"]={k:v for k,v in author["WF"].items()
                                     if k not in ("prose","source_sha256")}
            # Original paragraphs are accessible as files but not program
            # generated/rewritten; the hashes tie scores to real writer wires.
            for k in ("bare","WF"):
                (OUT/(name+"-"+k+"-original.md")).write_text(
                    author[k]["prose"],encoding="utf8")
            lens=[len(author[k]["prose"]) for k in ("bare","WF")]
            row["author_length_ratio"]=round(max(lens)/min(lens),3)
            row["length_comparable_within_25_percent"]=(
                max(lens)/min(lens)<=1.25)
            try:
                row["ratings"]=judge_pair(model,item,author)
            except Exception as exc:
                code=str(exc)
                row["status"]="BLIND_RATING_INVALID_NO_RETRY"
                row["failure_code"]=(
                    code if re.fullmatch(r"WF[A-Z0-9_:\-]{3,170}",code)
                    else type(exc).__name__+":RATING_INVALID")
                save(OUT/"PARTIAL.json",summary)
                continue
            row["blind_ratings_ready"]=True
            row["status"]="REAL_MATCHED_FUNCTION_PAIR_AND_PROVISIONAL_SCORE"
            save(OUT/"PARTIAL.json",summary)
        diffs=[row["ratings"]["WF_minus_bare"]
               for row in summary["cases"].values()
               if row.get("blind_ratings_ready")]
        summary["local_mean_WF_minus_bare"]=(
            round(sum(diffs)/len(diffs),1) if diffs else None)
        summary["eligible_comparable_pairs"]=[
            key for key,row in summary["cases"].items()
            if row.get("blind_ratings_ready") and
               row.get("length_comparable_within_25_percent")]
        summary["valid_for_book_reference_rank"]=False
        summary["statistical_literary_improvement_proven"]=False
        summary["status"]=(
            "FOUR_DIVERSE_REAL_PAIRED_SCENES_PROVISIONALLY_RATED"
            if len(diffs)==len(GENRES) else
            "PARTIAL_REAL_SOURCE_OR_RATING_FAILURE_NOT_A_FULL_SCORE")
    except Exception as exc:
        problem=str(exc)
        summary["status"]="REAL_PROVIDER_OR_WF_CHECK_FAILED_NO_RETRY"
        summary["failure_code"]=(
            problem if re.fullmatch(r"WF[A-Z0-9_:\-]{3,170}",problem)
            else type(exc).__name__+":UNVERIFIED_RESULT")
    finally:
        if model is not None:
            summary["actual_model_calls"]=model.budget.calls_reserved
            summary["provider_usage"]=model.budget.public_receipt()
            summary["provider_sha_receipts"]=model.calls
        save(OUT/"STATUS.json",summary)
        print("WF0AD_REAL_DIVERSE "+json.dumps({
            "status":summary["status"],
            "actual_model_calls":summary["actual_model_calls"],
            "number_of_paired_cases":sum(
                row.get("blind_ratings_ready",False)
                for row in summary["cases"].values()),
            "genre_score_differences":{
                k:row.get("ratings",{}).get("WF_minus_bare")
                for k,row in summary["cases"].items()},
            "score_proves_WF_progress":False,
        },ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
