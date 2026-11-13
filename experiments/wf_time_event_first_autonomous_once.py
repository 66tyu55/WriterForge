"""Real one-shot, two-arm autonomous parameter discovery on fresh anonymous events.

This does not train weights or certify original-novel comprehension. Inputs are
human-authored paraphrases grounded in private original byte spans. The model
has no direct original text and no sealed future. Save first raw responses,
no retries or post-hoc edits. No production WF/Canon writes.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter

SEED=20261113
LIMIT=1600
MODEL_SHA256="9c9f56a391a3abbd5b89d0245bf6106081bcc3173119d4229235dd9d23253f94"
MODEL_ID="Qwen2.5-3B-Instruct-Q4_K_M"
ROOT=Path(__file__).resolve().parents[1]
FROZEN=ROOT/"experiments/wf_time_event_first_autonomous_frozen_20261113.json"
ARMS=("direct","event_first")

SYSTEM=(
 "你是一个研究小说世界时间的独立提议模型。当前材料只提供截至这一阶段已知的匿名观察。"
 "你的任务不是背小说名、预测既定剧情或强行填满预置时间分类，而是提出可验证的局部规则。"
 "明确区分观察、人物的说法、预测和未知；事件发生顺序不等于绝对日期。"
 "不能把修炼效率当做物理时间倍速，也不能认为已修炼足够时间就必然突破。"
 "你输出JSON对象，仅包含 questions 和 parameters 和 abstentions 三个数组。"
 "questions最多7个，内容是根据材料提出的事件变化问题。"
 "parameters最多10个，字段必须正好为"
 "id, evidence_ids, owner, trigger, variable, unit, update_rule, epistemic, "
 "could_change, failure_if_missing。"
 "每个参数的证据是观察编号O01等，不可指向未来；若没有可靠单位，unit必须为UNKNOWN。"
 "当无证据时宁可放弃参数，不允许补编日期、倍率、动机或结果。不要Markdown。"
)
DIRECT=(
 "请根据下面截至目前的事实，直接识别能够约束后续故事的独立时间相关规则。"
 "每条必须说明何时触发、作用对象、变化、目前能确定什么，不能确定什么。"
)
EVENT_FIRST=(
 "先从已发生的事件提出若干可被未来章节检验的问题：例如某事在什么条件下才可发生、"
 "如果人物改变行动或其他人物先行动，已知规则是否仍有约束力。"
 "针对每个问题再反向定位真正必需的条件，删除该条件是否导致答案变为未知；"
 "只将有明确观察依据和不同更新行为的条件写成参数。"
 "参数不是一个固定世界观表，也不能把社会规定写成物理定律。"
)

def sha(b:bytes)->str:return sha256(b).hexdigest()

def model_file_sha(path):
    h=sha256()
    with Path(path).open("rb") as f:
        while chunk:=f.read(1048576):h.update(chunk)
    return h.hexdigest()

def dataset():
    d=json.loads(FROZEN.read_text("utf-8"))
    assert d["format"]=="wf.xianxia.time_autodiscovery.frozen.v1"
    assert d["experiment"]["arms"]==list(ARMS)
    assert d["scope"]["sealed_chapters"]==[18,19]
    assert len(d["observations"])==11
    ids={x["id"] for x in d["observations"]}
    assert len(ids)==11
    assert all(len(x["source_ids"])>=1 and x["id"] in ids
               and isinstance(x["text"],str) for x in d["observations"])
    return d

def context(d):
    # The model receives no original SHA, novel identification, raw source,
    # rubric, heldout answer hints, or future-event counts.
    return json.dumps({
        "actors":d["actors"],"observations":[
            {"id":o["id"],"text":o["text"],"epistemic":o["epistemic"] if "epistemic" in o
             else "REPORTED_OR_OBSERVED_CANDIDATE"}
            for o in d["observations"]],
        "constraints":d["constraints"]},
        ensure_ascii=False,sort_keys=True,separators=(",",":"))

def user_prompt(d,arm):
    instruction=DIRECT if arm=="direct" else EVENT_FIRST
    return instruction+"\n观察资料（不包含后续章节）：\n"+context(d)

def preflight():
    d=dataset()
    result={
     "format":"wf.event-first-independent-autodiscovery.preflight.v1",
     "source_book_names_in_prompts":False,
     "source_original_prose_in_prompts":False,
     "source_future_or_gold_in_prompts":False,
     "human_curated_event_observation_input":True,
     "model_weight_training":False,
     "independent_human_review":False,
     "rubric_sha256_locked_before_inference":d["experiment"]["rubric_sha256"],
     "heldout_sha256_locked_before_inference":d["experiment"]["source_future_sha256"],
     "model":MODEL_ID,"model_sha256":MODEL_SHA256,
     "seed":SEED,"max_completion_tokens":LIMIT,
     "planned_actual_model_calls":2,"paid_api_calls":0,"arms":[]
    }
    for arm in ARMS:
        prompt=user_prompt(d,arm)
        assert 300<len(prompt)<6500
        result["arms"].append({"name":arm,"prompt_sha256":sha(prompt.encode()),
                               "prompt_chars":len(prompt)})
    return result

def validate_candidate(parsed,d):
    """Only a syntax/evidence-id check. NEVER a semantic correctness claim."""
    if type(parsed) is not dict or set(parsed)!={"questions","parameters","abstentions"}:
        return {"status":"MALFORMED_OR_INCOMPLETE","reason":"SCHEMA"},[]
    qs,ps,ab=parsed["questions"],parsed["parameters"],parsed["abstentions"]
    if not(type(qs) is list and len(qs)<=7 and type(ps) is list and
           len(ps)<=10 and type(ab) is list):
        return {"status":"MALFORMED_OR_INCOMPLETE","reason":"TOP_LEVEL_ARRAYS"},[]
    permitted={o["id"] for o in d["observations"]}
    valid=[]
    bad=[]
    required={"id","evidence_ids","owner","trigger","variable","unit",
              "update_rule","epistemic","could_change","failure_if_missing"}
    for p in ps:
        if type(p) is not dict or set(p)!=required:
            bad.append({"id":p.get("id") if type(p) is dict else None,
                        "reason":"PARAMETER_FIELDS"});continue
        eids=p["evidence_ids"]
        if type(eids) is not list or not eids or not all(
           type(x) is str and x in permitted for x in eids):
            bad.append({"id":p["id"],"reason":"SOURCE_ID_NOT_VISIBLE"});continue
        if not all(type(p[k]) is str and p[k].strip() for k in required-{"evidence_ids"}):
            bad.append({"id":p["id"],"reason":"PARAMETER_VALUES"});continue
        valid.append(p["id"])
    return {
     "status":"STRUCTURAL_ONLY",
     "parameter_count":len(ps),"referenced_existing_observations":len(valid),
     "rejected_claims":bad,
     "source_semantic_accuracy":"UNASSESSED",
     "future_rule_validity":"UNASSESSED",
     "corpus_training_complete":False
    },valid

def run(model_path,output_path):
    from llama_cpp import Llama
    d=dataset()
    model=Path(model_path);out=Path(output_path)
    if not model.is_file() or model_file_sha(model)!=MODEL_SHA256:
        raise RuntimeError("MODEL_NOT_PINNED")
    if out.exists():raise FileExistsError("NO_RETRY_SAME_OUTPUT")
    out.mkdir(parents=True)
    status={"preflight":preflight(),"state":"IN_PROGRESS",
            "actual_calls":0,"new_paid_calls":0,"responses":[],
            "independent_original_semantic_success":False,
            "literary_improvement_proven":False}
    def save():
        (out/"STATUS.json").write_text(
            json.dumps(status,ensure_ascii=False,indent=2),encoding="utf-8")
    save()
    llm=Llama(model_path=str(model),n_ctx=8192,n_threads=2,n_gpu_layers=0,
              verbose=False)
    for idx,arm in enumerate(ARMS,1):
        user=user_prompt(d,arm)
        wire=("<|im_start|>system\n"+SYSTEM+"\n<|im_end|>\n"
              "<|im_start|>user\n"+user+"\n<|im_end|>\n"
              "<|im_start|>assistant\n")
        name=f"{idx:02d}_{arm}"
        (out/(name+".input.json")).write_text(json.dumps(
            {"system":SYSTEM,"user":user,"wire_sha256":sha(wire.encode())},
            ensure_ascii=False,indent=2),encoding="utf-8")
        entry={"name":arm,"state":"REQUESTED","original_file":name+".raw.json"}
        status["responses"].append(entry);save()
        t=perf_counter()
        raw=llm.create_completion(prompt=wire,seed=SEED,temperature=0.0,top_p=1.0,
             max_tokens=LIMIT,stop=["<|im_end|>","</s>"])
        (out/(name+".raw.json")).write_text(
            json.dumps(raw,ensure_ascii=False,indent=2),encoding="utf-8")
        answer=raw["choices"][0]["text"]
        try:obj=json.loads(answer.strip())
        except (ValueError,TypeError):obj=None
        verdict,_=validate_candidate(obj,d)
        (out/(name+".candidate.json")).write_text(json.dumps(
            {"parsed":obj,"raw_answer":answer,"structure_check":verdict},
            ensure_ascii=False,indent=2),encoding="utf-8")
        entry.update({"state":"RETURNED_UNGRADED","answer_sha256":sha(answer.encode()),
                      "prompt_tokens":raw["usage"]["prompt_tokens"],
                      "completion_tokens":raw["usage"]["completion_tokens"],
                      "finish_reason":raw["choices"][0]["finish_reason"],
                      "elapsed_seconds":round(perf_counter()-t,2),
                      "structure_check":verdict})
        status["actual_calls"]+=1;save()
        print("WF_TIME_DISCOVERY_RESULT",arm,json.dumps(entry,ensure_ascii=False),flush=True)
        print("WF_TIME_DISCOVERY_RAW",arm,answer[:10000],flush=True)
    status["state"]="TWO_REAL_LOCAL_REPLIES_SAVED_UNGRADED"
    save()
    return status

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dry-run",action="store_true")
    p.add_argument("--model");p.add_argument("--out")
    a=p.parse_args()
    if a.dry_run:
        print(json.dumps(preflight(),ensure_ascii=False,indent=2));return
    if not a.model or not a.out:p.error("model/out required")
    print(json.dumps(run(a.model,a.out),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
