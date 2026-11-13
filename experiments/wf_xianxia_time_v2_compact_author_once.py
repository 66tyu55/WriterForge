"""One bounded second writer trial after the preregistered V2 author-interface failure.

Two source-free prose-only local completions. Render computed time affordances
from V2 instead of dumping low-level JSON. Don't retry, tune or auto-promote.
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
import time_bridge
import time_v2

MODEL_SHA256="9c9f56a391a3abbd5b89d0245bf6106081bcc3173119d4229235dd9d23253f94"
SEED=20261113
LIMIT=2048
ARMS=("rate1","rate3")
FROZEN=ROOT/"experiments/wf_xianxia_time_v2_frozen_world_20261113.json"
SYSTEM=("你是一名真正写小说的作者。输出自然中文小说，不输出解释、标题、参数表、"
        "事件清单、括号内分析或JSON。人物不是完成任务的机器，允许失败、误判、无解。"
        "必须让事情实际发生并产生后果，不以'他必须做出选择'为结尾。"
        "目标是400至700个汉字的完整短场景。")
PREVIOUS=[
  {"kind":"advance","world_hours":6,
   "activities":{"P001":"cultivate","N001":"work"}}
]
def sha(data):return sha256(data).hexdigest()
def model_sha(path):
 h=sha256()
 with Path(path).open("rb") as f:
  while block:=f.read(1048576):h.update(block)
 return h.hexdigest()
def frozen():
 a=json.loads(FROZEN.read_text("utf-8"))
 assert a["character"]=={
  "actor_id":"P001","role":"灵田佃户","temperament":"谨慎却倔强"}
 d=time_bridge.delta(a["rate1"],a["rate3"],PREVIOUS)
 assert d["eligibility_changed"] and d["same_offscreen_clocks"]
 return a
def request(data,arm):
 state=time_bridge.time_window(data[arm],PREVIOUS)
 context=time_bridge.concise_context(state)
 return (
  "原创玄幻：沿河的灵田突降暴雨。你的主人公是一个谨慎却倔强的灵田佃户，"
  "起初在岩洞中修炼，外面有一个完全不认识他的守夜人独自修旧河堤。"
  "他已在洞中实际修炼六个世界小时，出洞时面对眼前洪水和人的命。"
  "请从此刻写起，展开具体冲突、一次困难选择和真实后果；"
  "写作可让普通人自救、无关人物说谎或主角失败，"
  "不得强行确保成功。注意区分人物不知道的事与外界已经发生的事。"
  "具体时间限制如下：" + context +
  "请写足一段有人物动作、物件与对话的故事；让主角做出并执行一个明确行动，"
  "讲述它造成的实际代价或挽救，不要只复述设定，也不要在开头罗列规则。"
 )
def preflight():
 data=frozen()
 rows=[]
 for arm in ARMS:
  q=request(data,arm)
  assert len(q)<1800 and len(q)>280
  rows.append({"arm":arm,"prompt_sha256":sha(q.encode()),"chars":len(q),
               "time_window":time_bridge.time_window(data[arm],PREVIOUS)})
 return {
  "format":"wf.xianxia-time-v2-compact-author.one-shot.v1",
  "calls_planned":2,"seed":SEED,
  "same_model":"Qwen2.5-3B-Instruct-Q4_K_M",
  "model_sha256":MODEL_SHA256,"max_completion_tokens":LIMIT,
  "changed_only_time_rate":True,"no_paid_api":True,
  "no_source_novel_data":True,"independent_literary_quality":False,
  "prompts":rows}
def run(model,out):
 from llama_cpp import Llama
 model,out=Path(model),Path(out)
 if not model.is_file() or model_sha(model)!=MODEL_SHA256:
  raise RuntimeError("LOCAL_MODEL_SHA_MISMATCH")
 if out.exists():raise RuntimeError("NO_RETRY_OUTPUT_EXISTS")
 data=frozen();out.mkdir(parents=True)
 log={"preflight":preflight(),"state":"STARTED",
      "actual_model_calls":0,"paid_calls":0,"results":[],
      "real_prose_time_consistency_independently_verified":False}
 def save():
  (out/"STATUS.json").write_text(json.dumps(log,ensure_ascii=False,indent=2),"utf8")
 save()
 llm=Llama(model_path=str(model),n_ctx=8192,n_threads=2,
          n_gpu_layers=0,verbose=False)
 for ix,arm in enumerate(ARMS,1):
  q=request(data,arm)
  wire=("<|im_start|>system\n"+SYSTEM+"\n<|im_end|>\n"
       "<|im_start|>user\n"+q+"\n<|im_end|>\n"
       "<|im_start|>assistant\n")
  prefix=f"{ix:02}_{arm}"
  (out/(prefix+"_input.json")).write_text(
   json.dumps({"system":SYSTEM,"user":q,"wire_sha256":sha(wire.encode())},
              ensure_ascii=False,indent=2),"utf8")
  entry={"arm":arm,"state":"REQUESTED","original_file":prefix+"_raw.json"}
  log["results"].append(entry);save()
  t=perf_counter()
  reply=llm.create_completion(prompt=wire,max_tokens=LIMIT,seed=SEED,
          top_p=1,temperature=0,stop=["<|im_end|>","</s>"])
  (out/(prefix+"_raw.json")).write_text(
   json.dumps(reply,ensure_ascii=False,indent=2),"utf8")
  prose=reply["choices"][0]["text"].strip()
  (out/(prefix+"_prose.txt")).write_text(prose,encoding="utf8")
  entry.update({"state":"RETURNED_UNREVIEWED",
                "chars":len(prose),
                "finish_reason":reply["choices"][0]["finish_reason"],
                "elapsed_seconds":round(perf_counter()-t,2),
                "prompt_tokens":reply["usage"]["prompt_tokens"],
                "completion_tokens":reply["usage"]["completion_tokens"],
                "prose_sha256":sha(prose.encode()),
                "writer_followed_time_rules":"NOT_INDEPENDENTLY_VERIFIED"})
  log["actual_model_calls"]+=1;save()
  print("TIME_V2_COMPACT_PROSE",arm,prose[:4000],flush=True)
  print("TIME_V2_COMPACT_META",arm,
        json.dumps({k:entry[k] for k in (
          "chars","finish_reason","prompt_tokens","completion_tokens")},
           ensure_ascii=False),flush=True)
 log["state"]="TWO_REAL_PROSE_COMPLETIONS_SAVED_UNREVIEWED";save()
 return log
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--dry-run",action="store_true")
 p.add_argument("--model");p.add_argument("--out")
 a=p.parse_args()
 if a.dry_run:
  print(json.dumps(preflight(),ensure_ascii=False,indent=2));return
 if not a.model or not a.out:p.error("model/out required")
 print(json.dumps(run(a.model,a.out),ensure_ascii=False,indent=2))
if __name__=="__main__":main()
