"""Single real provider capability check: Intern-S2 with thinking_mode false.

No copyrighted original, draft, or provider-generated prose in public logs.
"""
from __future__ import annotations
import json
import os
import sys
from writerforge.reverse_discovery_models import DiscoveryCallBudget,DiscoveryModel,DiscoveryError

def main():
    key=os.environ.get("DISCOVERY_API_KEY","")
    if not key:
        print('{"status":"NO_KEY_VISIBLE"}');return 2
    budget=DiscoveryCallBudget(max_calls=1,max_reserved_output_tokens=1200)
    model=DiscoveryModel(name="intern-s2",role="planner",api_key=key,budget=budget)
    try:
        result=model.ask(
            "你只负责选一个通用的写作技巧 ID，不需要长篇推理。"
            "仅回答JSON对象，包含id/evidence_ids。",
            "这是一段完全虚构的练习：行人在雨中为避开危险，优先检查"
            "路口的泥印。请选择GOAL_FILTERS_ATTENTION。段落是P0。",
            num_predict=1000)
        passed=(result.get("id")=="GOAL_FILTERS_ATTENTION"
                and isinstance(result.get("evidence_ids"),list))
        print(json.dumps({"status":"S2_THINKING_OFF_PROBE",
            "json_complete":bool(passed),
            "model_calls":budget.calls,
            "response_observations":budget.response_observations,
            "prompt_tokens":budget.total_prompt_tokens,
            "completion_tokens":budget.total_completion_tokens,
            "private_novel_sent":False},ensure_ascii=False))
        return 0 if passed else 3
    except DiscoveryError as exc:
        print(json.dumps({"status":"S2_THINKING_OFF_PROBE_BLOCKED",
            "error_type":str(exc)[:90],"response_observations":budget.response_observations,
            "private_novel_sent":False},ensure_ascii=False))
        return 4

if __name__=="__main__":
    sys.exit(main())
