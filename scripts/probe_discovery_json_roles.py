"""Real small JSON-compatibility probe for 3 verified high-capacity roles.

Never sends private original text or saves generated probes.
"""
from __future__ import annotations
import json
import os
import sys
from writerforge.reverse_discovery_models import DiscoveryCallBudget,DiscoveryModel,ROLE_MODELS

def main():
    key=os.environ.get("DISCOVERY_API_KEY","")
    if len(key)<12:
        print(json.dumps({"status":"KEY_EMPTY_IN_JOB","inference_calls":0}))
        return 2
    budget=DiscoveryCallBudget(max_calls=3,max_reserved_output_tokens=4200)
    results=[]
    for role,name in ROLE_MODELS.items():
        model=DiscoveryModel(name=name,role=role,api_key=key,budget=budget)
        try:
            out=model.ask(
                "只返回一个合法JSON对象；不要Markdown代码块。结构必须为 {"
                "\"reason\":\"一句简短原因\",\"conclusion\":\"一个词\"}。",
                "请简单描述：人在暴雨里为什么会更注意脚下的积水？",
                num_predict=1400)
            result={"role":role,"model":name,"result":"JSON_OK",
                    "keys":sorted(out.keys()),"has_text":bool(out)}
        except Exception as exc:
            from writerforge.reverse_discovery_models import DiscoveryError
            result={"role":role,"model":name,
                    "result":str(exc)[:80] if isinstance(exc,DiscoveryError)
                        else type(exc).__name__}
        results.append(result)
    print(json.dumps({"stage":"DISCOVERY_REAL_JSON_CAPABILITY_PROBE",
                      "models":results,"calls":budget.calls,
                      "prompt_tokens":budget.total_prompt_tokens,
                      "completion_tokens":budget.total_completion_tokens,
                      "private_original_sent":False},ensure_ascii=False,indent=2))
    return 0 if all(r["result"]=="JSON_OK" for r in results) else 3

if __name__=="__main__":
    sys.exit(main())
