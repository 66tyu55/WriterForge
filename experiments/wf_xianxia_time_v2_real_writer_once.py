"""WF xianxia V2 genuine writer trial, 3 arms with a frozen random actor.

Only source-free original fiction. Same local model, seed, task, 1536-token
completion cap, no paid calls. Frozen v2 time rules are optional hypotheses,
not universal cultivation laws. Store every original response, no auto retry.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/".agents/skills/xianxia-time-rule/scripts"))
import time_v2

MODEL_SHA256="9c9f56a391a3abbd5b89d0245bf6106081bcc3173119d4229235dd9d23253f94"
MODEL_ID="Qwen2.5-3B-Instruct-Q4_K_M"
LIMIT=1536
SEED=20261113
FROZEN=ROOT/"experiments/wf_xianxia_time_v2_frozen_world_20261113.json"
ARMS=("baseline","rate1","rate3")
SYSTEM=(
 "你是中文原创玄幻小说作者，不是代码注释者。你能让人物犹豫、失败、犯错，"
 "外界事件不以主角为中心停止。必须写出带有动作、感官、选择、代价的自然小说。"
 "返回一个 JSON 对象，仅含 story、time_events、reason 三项。"
 "story 写 300-650 个中文字符，不得出现技术术语JSON、参数或'模型'；"
 "time_events 为按剧情真实发生先后记录的行动数组，必须从固定的首条修炼记录开始。"
 "reason 简短说明人物为什么采取这一选择。不要Markdown。"
)
BASE=(
 "故事相同背景：河谷灵田在暴雨中将被冲毁，河水在八小时后到来。"
 "主角是一名谨慎却倔强的灵田佃户，在一处洞府闭关修炼了六个外界小时；"
 "洞外的河堤守夜人不认识主角，独立行动。主角可以选择继续修炼、冒险突破、"
 "救人、动员村民、撤离，或因犹豫而错过机会。请从这个行动前夕写起。"
 "不许把主角突破成功或河堤得救写成预定结局。"
)
FORMAT=(
 "time_events 数组内每项采用以下格式之一："
 '{"kind":"advance","world_hours":6,"activities":{"P001":"cultivate","N001":"work"}}'
 " 或 "
 '{"kind":"attempt","actor_id":"P001","outcome":"success"}'
 " 或 "
 '{"kind":"attempt","actor_id":"P001","outcome":"failure"}'
 " 或 "
 '{"kind":"use_technique","actor_id":"P001"}'
 "。必须把首条固定为上述 advance 六小时；后面可用 advance 增加时间，"
 "不得伪造未发生的突破。角色 P001 是主角、N001 是守夜人。"
)
def hashraw(blob):
    return sha256(blob).hexdigest()

def read_frozen():
    data=json.loads(FROZEN.read_text("utf-8"))
    assert data["format"]=="wf.time-rule-v2-story-experiment.v1"
    assert data["arms"]==list(ARMS)
    assert data["random_character_seed"]==SEED
    assert data["changed_parameter_only"]=="time_frames.cave.numerator"
    time_v2.validate(data["rate1"])
    time_v2.validate(data["rate3"])
    check=time_v2.time_comparison(data["rate1"],data["rate3"],[
      {"kind":"advance","world_hours":6,
       "activities":{"P001":"cultivate","N001":"work"}},
      {"kind":"attempt","actor_id":"P001","outcome":"success"},
      {"kind":"use_technique","actor_id":"P001"}
    ])
    assert not check["original"]["accepted"] and check["altered"]["accepted"]
    return data

def request_for(data,arm):
    char=data["character"]
    identity=f"角色固定：{char['role']}；性格：{char['temperament']}。"
    if arm=="baseline":
        contract=(
            "对照组：没有输入具体的修仙时间法则。人物不能知道尚未发生的事，"
            "故事后果由合理行为与意外共同决定。"
        )
    else:
        state=data[arm]
        constraints={
          "world_clock":state["world_clock"],
          "time_frames":state["time_frames"],
          "P001":state["actors"]["P001"],
          "N001":state["actors"]["N001"],
          "advancement":state["advancement"],
          "technique":state["technique"],
          "era_history":state["era_history"],
          "parameter_units":{
             "world_clock.hour":"world_hour",
             "time_frames.cave":"subjective_hour / world_hour",
             "actors.P001.cultivation_subjective_hours":"actual subject training hours",
             "actors.P001.age_subjective_hours":"body experienced hours"
           }
        }
        contract=(
          "以下是这部原创故事唯一有效的局部时间规则，不是世界观名字表："+
          json.dumps(constraints,ensure_ascii=False,sort_keys=True,separators=(",",":"))+
          "。六个世界小时内，主角确实在洞府修炼；守夜人在洞外劳动。"
          "无论洞府主观时间变快多少，外面都只过六小时。"
          "原已有累计实修六小时，成功尝试突破必须累计达到二十个主观实修小时；"
          "达到门槛只是资格，突破可以失败或根本不尝试。"
          "护堤术至少需要第二境而且必须在世界时钟1008小时或之前使用，"
          "使用术法不保证成功。只有实修会加实修时长；工作旅行休息不会。"
          "角色的身体经历时间随本地流速增长。"
          "如果做不到，就如实让角色放弃突破、转向人工救援或承担失败。"
        )
    return identity+BASE+contract+"\n"+FORMAT

def preflight():
    data=read_frozen()
    rows=[]
    for arm in ARMS:
        q=request_for(data,arm)
        assert 250<len(q)<6000
        rows.append({"arm":arm,"chars":len(q),
                     "sha256":hashraw(q.encode("utf-8"))})
    return {
       "format":"wf.xianxia-time-v2-real-local-preregister.v1",
       "random_seed":SEED,"random_character":data["character"],
       "changed_parameter_only":data["changed_parameter_only"],
       "model":MODEL_ID,"model_sha256":MODEL_SHA256,
       "same_model_same_completion_limit":True,
       "requested_max_tokens":LIMIT,"planned_calls":len(rows),
       "paid_api_calls":0,"local_model_weight_fine_tuning":False,
       "model_prose_semantic_adjudication_independent":False,
       "prompts":rows
    }

def original_source_digest(path):
    h=sha256()
    with Path(path).open("rb") as stream:
        while block:=stream.read(1048576):
            h.update(block)
    return h.hexdigest()

def run(model,out):
    from llama_cpp import Llama
    model=Path(model);out=Path(out)
    if not model.is_file() or original_source_digest(model)!=MODEL_SHA256:
        raise RuntimeError("LOCAL_MODEL_SHA_MISMATCH")
    if out.exists():raise RuntimeError("NO_RETRY_OUTPUT_ALREADY_EXISTS")
    data=read_frozen()
    out.mkdir(parents=True)
    journal={"preflight":preflight(),"state":"STARTED","actual_calls":0,
             "new_paid_calls":0,"model_results":[],
             "literary_gain_proven":False,"prose_review_independent":False}
    def save():
        (out/"STATUS.json").write_text(
          json.dumps(journal,ensure_ascii=False,indent=2),encoding="utf-8")
    save()
    llm=Llama(model_path=str(model),n_ctx=8192,n_threads=2,
             n_gpu_layers=0,verbose=False)
    for idx,arm in enumerate(ARMS,1):
        q=request_for(data,arm)
        wire=("<|im_start|>system\n"+SYSTEM+"\n<|im_end|>\n"
              "<|im_start|>user\n"+q+"\n<|im_end|>\n"
              "<|im_start|>assistant\n")
        name=f"{idx:02d}_{arm}"
        (out/(name+"_prompt.json")).write_text(json.dumps({
            "system":SYSTEM,"user":q,
            "wire_sha256":hashraw(wire.encode())},ensure_ascii=False,indent=2),"utf8")
        result_row={"arm":arm,"state":"REQUESTED","reply_file":name+"_raw.json"}
        journal["model_results"].append(result_row);save()
        started=perf_counter()
        original=llm.create_completion(prompt=wire,temperature=0,top_p=1,
                   max_tokens=LIMIT,seed=SEED,stop=["<|im_end|>","</s>"])
        (out/(name+"_raw.json")).write_text(json.dumps(original,
               ensure_ascii=False,indent=2),"utf8")
        response=original["choices"][0]["text"]
        candidate=None
        try:
            candidate=json.loads(response.strip())
        except ValueError:
            pass
        structural=isinstance(candidate,dict) and set(candidate)=={
                   "story","time_events","reason"}
        report={
            "json_shape_valid":structural,
            "mechanical_time_status":"NO_VALID_TIME_EVENTS",
            "prose_matches_time_events":"UNREVIEWED"
        }
        if structural:
            try:
                if type(candidate["time_events"]) is not list or not candidate["time_events"]:
                    raise time_v2.TimeV2Error("EMPTY_TIME_EVENTS")
                first=candidate["time_events"][0]
                if first!={"kind":"advance","world_hours":6,
                           "activities":{"P001":"cultivate","N001":"work"}}:
                    raise time_v2.TimeV2Error("FIRST_FIXED_SESSION_MISMATCH")
                audit=time_v2.replay(data["rate1"] if arm=="baseline" else data[arm],
                                     candidate["time_events"])
                report.update({
                     "mechanical_time_status":"PASS",
                     "final_world_hour":audit["final"]["world_clock"]["hour"],
                     "final_subjective_training_hours":audit["final"]["actors"]["P001"]["cultivation_subjective_hours"],
                     "final_realm":audit["final"]["actors"]["P001"]["realm_step"],
                     "offscreen_subjective_hours":audit["final"]["actors"]["N001"]["lived_subjective_hours"],
                     "prose_matches_time_events":"UNREVIEWED",
                })
            except (time_v2.TimeV2Error,TypeError,KeyError) as exc:
                report["mechanical_time_status"]="REJECTED"
                report["mechanical_time_error"]=str(exc)[:150]
        (out/(name+"_parsed.json")).write_text(json.dumps({
          "raw_response":response,"parsed":candidate,"rule_audit":report
        },ensure_ascii=False,indent=2),"utf8")
        result_row.update({
          "state":"RETURNED","finish_reason":original["choices"][0]["finish_reason"],
          "prompt_tokens":original["usage"]["prompt_tokens"],
          "completion_tokens":original["usage"]["completion_tokens"],
          "elapsed_seconds":round(perf_counter()-started,2),
          "raw_response_sha256":hashraw(response.encode()),
          "story_chars":len(candidate.get("story","")) if structural
                        and type(candidate.get("story")) is str else 0,
          "rule_audit":report,
        })
        journal["actual_calls"]+=1;save()
        print("TIME_V2_ORIGINAL_REPLY",arm,response[:4200],flush=True)
        print("TIME_V2_RULE_AUDIT",arm,
              json.dumps(report,ensure_ascii=False),flush=True)
    journal["state"]="THREE_REAL_LOCAL_REPLIES_SAVED_UNGRADED"
    save()
    return journal

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--dry-run",action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--out")
    args=parser.parse_args()
    if args.dry_run:
        print(json.dumps(preflight(),ensure_ascii=False,indent=2))
        return
    if not args.model or not args.out:
        parser.error("--model/--out required")
    print(json.dumps(run(args.model,args.out),ensure_ascii=False,indent=2))
if __name__=="__main__":main()
