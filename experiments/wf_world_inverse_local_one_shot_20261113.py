"""Run a one-shot, no-API inverse experiment with a pinned local open-weight model.

Sources are two privately reviewed originals; only generic, anonymous derived
relations are in this repository. Not model-weight training or literary proof.
Never retry failed completions, save originals even if JSON parse fails.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

MODEL_SHA256 = "9c9f56a391a3abbd5b89d0245bf6106081bcc3173119d4229235dd9d23253f94"
MODEL_ID = "Qwen2.5-3B-Instruct-Q4_K_M"
SEED = 20261113
LIMIT = 920
CASES = Path(__file__).with_name("wf_world_inverse_anonymous_cases_20261113.json")
SYSTEM = (
    "你是独立的匿名世界结构解码者，只能看见当前输入。"
    "不要猜原著名字、原著人物或任何原作剧情。"
    "观察与推断必须分开；不可把同时发生等同于因果，不可把偶然抹掉。"
    "无信息支持时明确说未知。输出一个有效 JSON 对象，字段恰好为"
    "reconstruction (80-250字), observed (最多5条), inferred (最多5条), "
    "unjustified (最多4条), after_change (60-150字)。不要Markdown。"
)

def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()

def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as file:
        while block := file.read(1048576):
            h.update(block)
    return h.hexdigest()

def load_cases():
    data = json.loads(CASES.read_text(encoding="utf-8"))
    assert data["format"] == "wf.anonymous-real-source-structure-pilot.v1"
    assert data["gold_not_in_this_file"] is True
    assert data["frozen_arms"] == [
        ["world_a","numeric_only"],["world_a","typed"],
        ["world_b","bare"],["world_b","transfer"]
    ]
    assert data["max_completion_tokens_per_call"] == LIMIT
    return data

def prompt(data, case, arm):
    source = data["cases"][case]["numeric" if arm == "numeric_only" else "typed"]
    learned = (data["learned_habit_from_world_a"] + "\n") if arm == "transfer" else ""
    return (learned + "匿名关系参数（不含原文）：\n" +
            json.dumps(source,ensure_ascii=False,sort_keys=True,separators=(",",":")) +
            "\n要求：" + data["cases"][case]["question"])

def preflight(data):
    rows = []
    for case,arm in data["frozen_arms"]:
        query = prompt(data,case,arm)
        assert 200 < len(query) < 6500
        rows.append({"case":case,"arm":arm,"prompt_chars":len(query),
                     "prompt_sha256":digest_bytes(query.encode("utf-8"))})
    return {
        "format":"wf.real-world-inverse-4arm-local.preflight.v1",
        "source_novel_prose_in_model_prompt":False,
        "source_gold_in_model_prompt":False,
        "model_weight_training":False,"in_context_method_trial_only":True,
        "model":MODEL_ID,"model_sha256":MODEL_SHA256,
        "fixed_seed":SEED,"fixed_completion_cap":LIMIT,
        "calls_planned":len(rows),"prompts":rows,
        "semantics_independently_reviewed":False
    }

def run(model_file, output):
    from llama_cpp import Llama
    data = load_cases()
    model_file,output = Path(model_file),Path(output)
    if not model_file.is_file() or sha_file(model_file) != MODEL_SHA256:
        raise RuntimeError("MODEL_NOT_PINNED")
    if output.exists():
        raise FileExistsError("TRIAL_EXISTS_NO_RETRY")
    output.mkdir(parents=True)
    ledger = {"preflight":preflight(data),"status":"IN_PROGRESS",
              "new_paid_api_calls":0,"actual_local_calls":0,
              "responses":[],"independent_semantic_grade":"NOT_PERFORMED",
              "literary_transfer_proven":False}
    def save():
        (output/"STATUS.json").write_text(
            json.dumps(ledger,ensure_ascii=False,indent=2),encoding="utf-8")
    save()
    engine=Llama(model_path=str(model_file),n_ctx=8192,n_threads=2,
                 n_gpu_layers=0,verbose=False)
    for idx,(case,arm) in enumerate(data["frozen_arms"],start=1):
        query=prompt(data,case,arm)
        wire=("<|im_start|>system\n"+SYSTEM+"\n<|im_end|>\n"
              "<|im_start|>user\n"+query+"\n<|im_end|>\n"
              "<|im_start|>assistant\n")
        basename=f"{idx:02d}_{case}_{arm}"
        (output/(basename+".prompt.json")).write_text(
            json.dumps({"system":SYSTEM,"user":query,
                        "wire_sha256":digest_bytes(wire.encode())},
                       ensure_ascii=False,indent=2),encoding="utf-8")
        rec={"case":case,"arm":arm,"status":"CALLING",
             "raw_reply":basename+".raw.json"}
        ledger["responses"].append(rec);save()
        started=perf_counter()
        raw=engine.create_completion(prompt=wire,max_tokens=LIMIT,seed=SEED,
                                     temperature=0.0,top_p=1.0,
                                     stop=["<|im_end|>","</s>"])
        (output/(basename+".raw.json")).write_text(
            json.dumps(raw,ensure_ascii=False,indent=2),encoding="utf-8")
        response=raw["choices"][0]["text"]
        parsed=None
        try:
            parsed=json.loads(response.strip())
        except ValueError:
            pass
        valid=(isinstance(parsed,dict) and
               set(parsed)=={"reconstruction","observed","inferred",
                             "unjustified","after_change"})
        (output/(basename+".answer.json")).write_text(
            json.dumps({"case":case,"arm":arm,"parsed":parsed,
                        "raw_text":response},ensure_ascii=False,indent=2),
            encoding="utf-8")
        rec.update({"status":"RETURNED_UNGRADED",
                    "elapsed_s":round(perf_counter()-started,2),
                    "finish_reason":raw["choices"][0]["finish_reason"],
                    "prompt_tokens":raw["usage"]["prompt_tokens"],
                    "completion_tokens":raw["usage"]["completion_tokens"],
                    "json_valid":valid,
                    "answer_sha256":digest_bytes(response.encode()),
                    "answer_chars":len(response)})
        ledger["actual_local_calls"]+=1;save()
        print("WF_ONE_SHOT_ACTUAL",case,arm,
              rec["completion_tokens"],rec["finish_reason"],
              "json_valid",valid,flush=True)
        print("WF_ONE_SHOT_REPLY",basename,response[:2600],flush=True)
    ledger["status"]="FOUR_ORIGINAL_LOCAL_REPLIES_COMPLETE_UNGRADED"
    save()
    return ledger

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dry-run",action="store_true")
    p.add_argument("--model")
    p.add_argument("--out")
    args=p.parse_args()
    data=load_cases()
    if args.dry_run:
        print(json.dumps(preflight(data),ensure_ascii=False,indent=2))
        return
    if not args.model or not args.out:
        p.error("--model and --out required")
    print(json.dumps(run(args.model,args.out),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
