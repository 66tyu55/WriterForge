"""Tiny real gateway schema probe: NO novel, manuscripts, R2 or training.

Tests both independent examiner models against exact grading JSON
contracts. Only fixed synthetic sample texts used; no preselected exam is
seen and no scores are presented as literary evidence.
"""
from __future__ import annotations
import json,os,sys
from writerforge.reverse_discovery_models import (
    DiscoveryModel, DiscoveryCallBudget, DiscoveryError,
)
from writerforge.v33_exam_contracts import grade_prompt,strict_grade,grade_with_one_repair,ExamContractError

UNIT="学习者发现路口木牌松动，于是先检查碎裂的绳索，再通知等候的同伴。"
SCENE_A=UNIT*16
SCENE_B=(UNIT.replace("通知等候的同伴","记录自己亲眼确认的裂痕"))*16
TASK=("这是固定、完全虚构的格式联调题：一个人看见桥边的木牌松动，"
      "作出行动判断并把线索告诉同伴。两份正文均为机械合成的样例，"
      "仅测试评语JSON字段能否正确输出，不测试任何文学优劣。"
      "禁止从本测试得出WF文学进步的结论。")
MODELS=("deepseek-v4-pro-0813","minimax-m3")
def run():
    key=os.environ.get("DISCOVERY_API_KEY","")
    if not isinstance(key,str) or len(key)<12:
        raise DiscoveryError("JSON_PROBE_KEY_UNAVAILABLE")
    budget=DiscoveryCallBudget(max_calls=4,max_reserved_output_tokens=23000)
    results=[]
    for model in MODELS:
        x=DiscoveryModel(name=model,role="critic",api_key=key,budget=budget)
        prev=budget.calls
        try:
            normalized,meta=grade_with_one_repair(
                x,TASK,{"A":SCENE_A,"B":SCENE_B},budget_first=5200,budget_retry=5200)
            result={"model":model,"status":"REAL_JSON_SCHEMA_VALID",
                    "calls_used":budget.calls-prev,
                    "parsing_path":meta["parsing_path"],
                    "did_retry_format":meta["attempted_calls"]>1,
                    "five_dimensions_complete":True,"human_literary_review":False}
        except (ExamContractError,DiscoveryError) as exc:
            message=str(exc)
            if not message or not all(ch.isupper() or ch.isdigit() or ch=="_" for ch in message):
                message=type(exc).__name__
            result={"model":model,"status":"JSON_SCHEMA_PROBE_FAILED",
                    "error_code":message[:90],"calls_used":budget.calls-prev,
                    "human_literary_review":False}
        results.append(result)
    safe={
        "stage":"V33_REAL_NONFICTIONAL_JSON_GATEWAY_COMPATIBILITY",
        "probe":results,
        "all_models_valid":all(r["status"]=="REAL_JSON_SCHEMA_VALID" for r in results),
        "total_api_requests":budget.calls,
        "reported_input_tokens":budget.total_prompt_tokens,
        "reported_output_tokens":budget.total_completion_tokens,
        "no_novel_or_exam_source_exposed":True,"literary_pass":False,
    }
    print(json.dumps(safe,ensure_ascii=False,sort_keys=True),flush=True)
    if not safe["all_models_valid"]:
        raise RuntimeError("MODEL_JSON_COMPATIBILITY_NOT_VALIDATED")
    return safe
if __name__=="__main__":
    try:run()
    except Exception as exc:
        print(json.dumps({"stage":"V33_JSON_PROBE_UNVERIFIED",
                          "code":type(exc).__name__,"no_literary_pass":True}),file=sys.stderr)
        raise SystemExit(1)
