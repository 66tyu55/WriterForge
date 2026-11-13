"""One fresh random-role action->time-rule->prose trial, no paid providers.

Previous 20261113 river scenario is frozen and NOT reused. Novel story is
original; no author can see source-gold or other arm's raw response. Actor
autonomously proposes an action; our time kernel accepts or rejects it;
author receives only its own action + rule outcome before writing prose.
Two arms x (one decision, one prose) = exactly four real local calls maximum.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import argparse,json,sys
from pathlib import Path
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/".agents/skills/xianxia-time-rule/scripts"))
import time_v2 as t
import time_bridge as b

FROZEN=ROOT/"experiments/wf_xianxia_time_v2_fresh_crossover_case_20261113.json"
MODEL_SHA256="9c9f56a391a3abbd5b89d0245bf6106081bcc3173119d4229235dd9d23253f94"
SEED=20261114
ARM_IDS=("world_rate1","world_rate3")
PLAN_BUDGET=420
PROSE_BUDGET=1400

def sha(raw):return sha256(raw).hexdigest()

def file_sha(path):
 h=sha256()
 with Path(path).open("rb") as f:
  while piece:=f.read(1048576):h.update(piece)
 return h.hexdigest()

def frozen():
 doc=json.loads(FROZEN.read_text("utf-8"))
 assert doc["format"]=="wf.xianxia-time-fresh-movement-story.v1"
 assert doc["seed"]==SEED
 assert doc["character"]["role"]=="山门守钟人"
 assert doc["character"]["temperament"]=="多疑但重诺"
 delta=t.time_comparison(doc[ARM_IDS[0]],doc[ARM_IDS[1]],
   doc["common_events"]+[
     {"kind":"attempt","actor_id":"P001","outcome":"success"},
     {"kind":"use_technique","actor_id":"P001"}
   ])
 assert delta["original"]["accepted"] is False
 assert delta["altered"]["accepted"] is True
 return doc

def window(doc,arm):
 return b.time_window(doc[arm],doc["common_events"])

def scene_context(doc,arm):
 w=window(doc,arm)
 return (
  "这是全新原创故事：一座雪山山门的冰桥正在开裂，过桥避难队可能在"
  "世界第2012小时失去通道。主角是多疑但重诺的山门守钟人，"
  "他答应为桥下行人敲钟示警，曾独自进静钟洞修炼六个世界小时，"
  "随后花两个世界小时穿越洞内外时间边界来到山门。"
  "山门有一位不认识他修炼状况的挑水老人，仍在按自己的意愿劳作；"
  "老者不可能凭空知道主角是否突破。"
  "普通敲钟、求援、撤离都可以尝试，修炼秘术需要第二境。"
  "现在的时间约束来自独立内核："+
  b.concise_context(w,deadline_event="冰桥封闭",other_actors="挑水老人")+
  "故事不要求主角成功，也允许他承诺落空，因误解错失救援。"
 )

def plan_prompt(doc,arm):
 return (
  scene_context(doc,arm)+
  "你是作者。根据人物性格自主选择这一个时刻真正采取的下一步行动，"
  "不许因为你希望他成功就无视时间限制。"
  "只回一个JSON对象，字段为choice, outcome, world_hours, reason。"
  "choice 只能从 try_breakthrough / ring_manual_bell / warn_travellers / hide 选择；"
  "try_breakthrough 的 outcome 只能 success/failure，其他choice的outcome只能 none；"
  "try_breakthrough 的 world_hours必须0，其余行动需花1到4世界小时。"
  "reason简短解释决定。修炼资格满足也不保证人物必须突破。"
 )

def decode_decision(text):
 try:
  d=json.loads(text.strip())
 except ValueError:
  return None,"DECISION_NOT_JSON"
 if type(d) is not dict or set(d)!={"choice","outcome","world_hours","reason"}:
  return None,"DECISION_FIELDS_INVALID"
 if type(d["choice"]) is not str or d["choice"] not in {
     "try_breakthrough","ring_manual_bell","warn_travellers","hide"}:
  return None,"DECISION_CHOICE_INVALID"
 if type(d["reason"]) is not str or len(d["reason"].strip())<3:
  return None,"DECISION_REASON_INVALID"
 if type(d["world_hours"]) is not int:
  return None,"DECISION_DURATION_INVALID"
 if d["choice"]=="try_breakthrough":
  if d["outcome"] not in ("success","failure") or d["world_hours"]!=0:
   return None,"DECISION_ATTEMPT_INVALID"
 else:
  if d["outcome"]!="none" or not (1<=d["world_hours"]<=4):
   return None,"DECISION_ACTIVITY_INVALID"
 return d,None

def action_from_decision(decision):
 if decision["choice"]=="try_breakthrough":
  return {"kind":"attempt","actor_id":"P001",
          "outcome":decision["outcome"]}
 activity=({
   "ring_manual_bell":"work",
   "warn_travellers":"travel",
   "hide":"wait"
 })[decision["choice"]]
 return {"kind":"advance","world_hours":decision["world_hours"],
         "activities":{"P001":activity}}

def check_decision(doc,arm,decision):
 if decision is None:
  return {"accepted":False,"reason":"NO_VALID_DECISION",
          "world_after":None}
 event=action_from_decision(decision)
 try:
  output=t.replay(doc[arm],doc["common_events"]+[event])
  return {"accepted":True,"reason":"TIME_RULE_ACCEPTED",
          "world_after":output["final"]["world_clock"]["hour"],
          "final_realm":output["final"]["actors"]["P001"]["realm_step"],
          "npc_world_time_continues":True,
          "attempt_outcome_not_automatic":True,
          "source_action":event}
 except t.TimeV2Error as exc:
  return {"accepted":False,"reason":str(exc),"world_after":None,
          "source_action":event}

def prose_prompt(doc,arm,decision,audit):
 why=("作者的原始决定是："+json.dumps(decision,ensure_ascii=False)+
      "；时间引擎审查："+json.dumps(audit,ensure_ascii=False))
 if decision is None:
  why="你上一步没有提供有效行动，必须如实承认无法验证行动，不能假装既定事情发生。"
 elif not audit["accepted"]:
  why+=(
    "。这意味着原定动作在该时刻无法按宣称结果执行；"
    "请让人物自行面对失败、转向普通救援或承受代价，"
    "不得偷偷写成同样成功。"
  )
 else:
  why+=(
    "。该动作在计时上可行，但这不证明人物一定救得了所有人。"
  )
 return (
  scene_context(doc,arm)+why+
  "请继续写一个约350-600汉字的自然小说场景，"
  "要有至少一次人物实际行动与其具体后果、人物对话、物件和真实代价。"
  "不要在小说中写字段名、参数、审查报告或结论说明。"
  "人物可以不理性，不能因主角不在场就让其他人完全静止。"
 )

def make_request(llm,system,user,max_tokens):
 wire=("<|im_start|>system\n"+system+"\n<|im_end|>\n"
       "<|im_start|>user\n"+user+"\n<|im_end|>\n"
       "<|im_start|>assistant\n")
 raw=llm.create_completion(prompt=wire,seed=SEED,temperature=0.0,
      top_p=1.0,max_tokens=max_tokens,stop=["<|im_end|>","</s>"])
 return raw,wire

def preflight():
 doc=frozen();rows=[]
 for arm in ARM_IDS:
  w=window(doc,arm)
  assert w["world_hour_now"]==2008 and w["world_hours_left"]==4
  assert w["offscreen_npc_clocks"]["N001"]["lived_subjective_hours"]=="8"
  assert w["actor_current_time_frame"]=="outside"
  assert w["actor_time_rate_subjective_per_world_hour"]=="1"
  rows.append({"arm":arm,
     "prompt_sha256":sha(plan_prompt(doc,arm).encode()),
     "attempt_time_eligible":w["could_succeed_if_attempted_now"],
     "time_state":w})
 assert rows[0]["attempt_time_eligible"] is False
 assert rows[1]["attempt_time_eligible"] is True
 return {"format":"wf.time-fresh-action-feedback-trial.v1",
  "model":"Qwen2.5-3B-Instruct-Q4_K_M",
  "pinned_model_sha256":MODEL_SHA256,
  "character_seed":SEED,
  "original_fiction_only":True,
  "new_paid_model_calls":0,
  "model_weight_training":False,
  "decisions_per_arm":1,"prose_per_arm":1,
  "max_total_real_model_calls":4,
  "no_result_conditioned_retry":True,
  "model_literary_quality_independent_review":False,"arms":rows}

def run(model_file,out_dir):
 from llama_cpp import Llama
 model_file,out_dir=Path(model_file),Path(out_dir)
 if not model_file.is_file() or file_sha(model_file)!=MODEL_SHA256:
  raise ValueError("LOCAL_MODEL_SHA_MISMATCH")
 if out_dir.exists():raise ValueError("NO_RETRY_OUTPUT_EXISTS")
 out_dir.mkdir(parents=True)
 doc=frozen()
 state={"preflight":preflight(),"status":"IN_PROGRESS",
        "actual_model_calls":0,"paid_model_calls":0,"cases":[],
        "literary_improvement_proven":False}
 def save():
  (out_dir/"STATUS.json").write_text(
   json.dumps(state,ensure_ascii=False,sort_keys=True,indent=2),encoding="utf8")
 save()
 llm=Llama(model_path=str(model_file),n_ctx=8192,n_threads=2,
           n_gpu_layers=0,verbose=False)
 for ix,arm in enumerate(ARM_IDS,1):
  case={"arm":arm,"status":"STARTED","calls":[]}
  state["cases"].append(case);save()
  plan_user=plan_prompt(doc,arm)
  first,wire=make_request(llm,
      "你是原创中文玄幻小说作者，需要自己选择行动；只输出符合指定结构的JSON，不要Markdown。",
      plan_user,420)
  name=f"{ix:02}_{arm}_plan"
  (out_dir/(name+"_raw.json")).write_text(
    json.dumps(first,ensure_ascii=False,indent=2),"utf8")
  (out_dir/(name+"_prompt.json")).write_text(
    json.dumps({"user":plan_user,"wire_sha256":sha(wire.encode())},
               ensure_ascii=False,indent=2),"utf8")
  response=first["choices"][0]["text"]
  decision,error=decode_decision(response)
  audit=check_decision(doc,arm,decision)
  case["plan"]={"decision":decision,"parse_error":error,
                 "rule_audit":audit,"raw_answer":response}
  case["calls"].append({
      "phase":"plan","prompt_tokens":first["usage"]["prompt_tokens"],
      "completion_tokens":first["usage"]["completion_tokens"],
      "finish_reason":first["choices"][0]["finish_reason"]})
  state["actual_model_calls"]+=1;save()
  story_user=prose_prompt(doc,arm,decision,audit)
  second,wire=make_request(llm,
      "你是原创中文玄幻小说作者，写自然完整的故事，不要格式、说明、Markdown或JSON。",
      story_user,1400)
  name=f"{ix:02}_{arm}_prose"
  (out_dir/(name+"_raw.json")).write_text(
    json.dumps(second,ensure_ascii=False,indent=2),"utf8")
  (out_dir/(name+"_prompt.json")).write_text(
    json.dumps({"user":story_user,"wire_sha256":sha(wire.encode())},
               ensure_ascii=False,indent=2),"utf8")
  prose=second["choices"][0]["text"].strip()
  (out_dir/(name+".txt")).write_text(prose,"utf8")
  case["calls"].append({
      "phase":"prose","prompt_tokens":second["usage"]["prompt_tokens"],
      "completion_tokens":second["usage"]["completion_tokens"],
      "finish_reason":second["choices"][0]["finish_reason"]})
  case["prose"]={
     "sha256":sha(prose.encode()),"chars":len(prose),
     "story_rule_and_knowledge_consistency":"NOT_INDEPENDENTLY_REVIEWED",
     "prose_filename":name+".txt"}
  state["actual_model_calls"]+=1
  case["status"]="REAL_MODEL_REPLIED_UNGRADED";save()
  print("WF_TIME_FRESH_PLAN",arm,json.dumps(case["plan"],ensure_ascii=False),flush=True)
  print("WF_TIME_FRESH_PROSE",arm,prose[:3500],flush=True)
 state["status"]="FOUR_REAL_LOCAL_CALLS_SAVED_UNGRADED";save()
 return state

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--dry-run",action="store_true")
 p.add_argument("--model");p.add_argument("--out")
 a=p.parse_args()
 if a.dry_run:print(json.dumps(preflight(),ensure_ascii=False,indent=2));return
 if not (a.model and a.out):p.error("--model and --out needed")
 print(json.dumps(run(a.model,a.out),ensure_ascii=False,indent=2))
if __name__=="__main__":
 main()
