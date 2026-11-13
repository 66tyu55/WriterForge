"""Run a frozen source-free real model inverse for WriterForge (NO original prose).

A/B provide source-anchored but NOT independently verified calibration habits.
D is a previously unused complete original's first-chapter anonymized prefix.
All D future chapters and their private grading key are absent. Model weights are
not updated. The only actual model effects are these one-shot completions.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter

MODEL_SHA = "9c9f56a391a3abbd5b89d0245bf6106081bcc3173119d4229235dd9d23253f94"
MODEL_NAME = "Qwen2.5-3B-Instruct-Q4_K_M"
SEED = 20261113
CONFIG = Path(__file__).with_name("wf_nontime_fresh_D_20261113_frozen.json")
SYSTEM = (
  "你是原著结构的独立匿名反推测试读者，只有当次给的参数。"
  "请分析真实世界的物质条件、空间边界、人物知情范围、世界独立运行的压力和偶然性。"
  "人物的信念不等于叙述世界真值，角色选择不等于必然成功，后续未出现的事不能编成已发生。"
  "不猜原著名字和原著剧情。只输出有效JSON，键名严格为"
  "world,directed_links,epistemic,offscreen,counterfactual,unproved。"
  "world,directed_links,epistemic,offscreen,unproved为短字符串数组，counterfactual为1个短字符串，不要Markdown。"
)

def digest(buf: bytes) -> str:
    return sha256(buf).hexdigest()

def sha_file(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        while part := f.read(1 << 20):
            h.update(part)
    return h.hexdigest()

def load_case():
    case = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert case["format"] == "wf.non-time-original-source-inverse.v4"
    assert case["arms"] == ["baseline", "original_A_B_reading"]
    assert case["original_prose_embedded"] is False
    assert case["independent_semantic_review"] is False
    assert case["model_weights_trained"] is False
    assert len(case["observations"]) == 38
    assert all(x[0] == "D%03d" % i for i,x in enumerate(case["observations"], 1))
    assert all(e["ids"] and all(t.startswith(("A","B")) for t in e["ids"])
               for e in case["calibration"])
    assert case["max_completion_tokens"] == 1450
    # Refuse accidental copied original characters or known future-gold field.
    raw = CONFIG.read_text(encoding="utf-8")
    for prohibited in ("林动", "韩立", "秦羽", "秦德", "林啸", "苏铭", "求魔", "阿公", "武动乾坤",
                       "星辰变", "凡人修仙传", "future_original", "heldout_gold", "future_answers"):
        assert prohibited not in raw, "PRIVATE_LEAK_"+prohibited
    return case

def prompt(case, arm):
    question = {
      "test":{"role_legend":case["role_legend"],"observations":case["observations"],"questions":case["questions"]},
      "read_these_first":"The observations cover a contiguous source prefix only; unseen future is withheld.",
      "epistemic_contract":"Report UNKNOWN for unobserved concrete outcomes and a CHARACTER_BELIEF for a character's conclusion.",
    }
    if arm == "original_A_B_reading":
        question["learning_from_two_other_originals"] = case["calibration"]
    else:
        question["learning_from_two_other_originals"] = None
    return json.dumps(question, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def preflight(case):
    arms = []
    for arm in case["arms"]:
        query = prompt(case,arm)
        assert 2500 < len(query) < 25000
        arms.append({"arm":arm,"prompt_chars":len(query),
                     "prompt_sha256":digest(query.encode("utf8"))})
    return {"model":MODEL_NAME,"model_sha256":MODEL_SHA,"seed":SEED,
            "weights_finetuned":False,"paid_api_calls":0,"independent_review":False,
            "full_original_training_complete":False,
            "source_gold_passed_to_model":False,"calibration_source_disjoint":True,
            "prompt_preflight":arms,"frozen_case_sha256":sha_file(CONFIG)}

def run(model_path, directory):
    from llama_cpp import Llama
    case = load_case()
    out = Path(directory)
    if out.exists():
        raise FileExistsError("EXPERIMENT_ALREADY_EXISTS_NO_RETRY")
    model = Path(model_path)
    if not model.is_file() or sha_file(model) != MODEL_SHA:
        raise RuntimeError("WRONG_OR_UNPINNED_MODEL")
    out.mkdir(parents=True)
    ledger = {"preflight":preflight(case),"status":"RUNNING","actual_calls":0,
              "responses":[],"review":"NOT_YET_INDEPENDENTLY_GRADED"}
    def persist():
        (out/"STATUS.json").write_text(json.dumps(ledger,ensure_ascii=False,indent=2),
                                        encoding="utf8")
    persist()
    engine = Llama(model_path=str(model),n_ctx=8192,n_threads=2,
                   n_gpu_layers=0,verbose=False)
    for i,arm in enumerate(case["arms"],1):
        q = prompt(case,arm)
        wire = "<|im_start|>system\n"+SYSTEM+"\n<|im_end|>\n"+\
               "<|im_start|>user\n"+q+"\n<|im_end|>\n<|im_start|>assistant\n"
        filename = "%02d_%s" % (i,arm)
        (out/(filename+".prompt.json")).write_text(json.dumps(
            {"system":SYSTEM,"user":q,"wire_sha256":digest(wire.encode("utf8"))},
             ensure_ascii=False,indent=2),encoding="utf8")
        record={"arm":arm,"status":"SENT","file":filename+".raw.json"}
        ledger["responses"].append(record)
        persist()
        start = perf_counter()
        raw = engine.create_completion(prompt=wire,max_tokens=case["max_completion_tokens"],
                                       seed=SEED,temperature=0,top_p=1,
                                       stop=["<|im_end|>","</s>"])
        (out/(filename+".raw.json")).write_text(
            json.dumps(raw,ensure_ascii=False,indent=2),encoding="utf8")
        reply = raw["choices"][0]["text"].strip()
        try:
            answer = json.loads(reply)
        except ValueError:
            answer = None
        valid = (isinstance(answer,dict) and
                 set(answer) == set(case["output_keys"]) and
                 all(isinstance(answer.get(k),list) for k in
                     ("world","directed_links","epistemic","offscreen","unproved")) and
                 isinstance(answer.get("counterfactual"),str))
        (out/(filename+".answer.json")).write_text(json.dumps(
            {"arm":arm,"raw_text":reply,"parsed":answer,"schema_valid":valid},
             ensure_ascii=False,indent=2),encoding="utf8")
        record.update({"status":"RETURNED_UNGRADED",
                       "reply_sha256":digest(reply.encode("utf8")),
                       "elapsed_s":round(perf_counter()-start,1),
                       "json_valid":valid,
                       "completion_tokens":raw["usage"]["completion_tokens"],
                       "prompt_tokens":raw["usage"]["prompt_tokens"],
                       "finish_reason":raw["choices"][0]["finish_reason"]})
        ledger["actual_calls"]+=1
        persist()
        print("REAL_ANON_INVERSE",arm,
              "tokens",record["prompt_tokens"],record["completion_tokens"],
              "valid_json",valid,flush=True)
        print("RAW_ANSWER",filename,reply[:4200],flush=True)
    ledger["status"]="TWO_REAL_REPLIES_COMPLETE_UNGRADED"
    persist()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--dry-run",action="store_true")
    p.add_argument("--model")
    p.add_argument("--out")
    args=p.parse_args()
    case=load_case()
    if args.dry_run:
        print(json.dumps(preflight(case),ensure_ascii=False,indent=2))
    else:
        if not args.model or not args.out:
            p.error("--model and --out required")
        run(args.model,args.out)
