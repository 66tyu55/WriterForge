"""One bounded source-free paid compatibility probe for GLM-5.3 low effort.

Official GLM-5.3 supports reasoning_effort=low and always reasons. This probe
only verifies whether the user's Discovery gateway accepts/preserves this
feature. No originals, generated probes or provider raw output are stored.
"""
from __future__ import annotations
import os,json
from writerforge.reverse_discovery_models import (
    DiscoveryModel, DiscoveryCallBudget, DiscoveryError)

def probe():
    budget=DiscoveryCallBudget(max_calls=2,max_reserved_output_tokens=5000)
    model=DiscoveryModel(name="glm-5.3",role="writer",
                         api_key=os.environ.get("DISCOVERY_API_KEY",""),
                         budget=budget,reasoning_effort="low")
    try:
        result=model.ask("你是中文短篇作家，只输出纯原创正文，不要分析。",
                         "请创作350至500汉字的原创日常小镇故事：一名普通工匠"
                         "冒雨去归还丢失的雨伞。写出一次行动选择与小小的结果。"
                         "不使用任何现成作品的角色。",num_predict=2500)
        txt=result["scene"]
        if len(txt)<220:
            raise DiscoveryError("LOW_EFFORT_TOO_SHORT")
    except Exception as exc:
        safe=str(exc)
        if not (isinstance(exc,DiscoveryError) and safe.startswith("DISCOVERY_")
                and all(t.isupper() or t.isdigit() or t=="_" for t in safe)):
            safe=type(exc).__name__
        print(json.dumps({"stage":"GLM53_DISCOVERY_LOW_EFFORT_PROBE_FAILED",
                          "code":safe,"calls":budget.calls,"model":"glm-5.3",
                          "source_or_prose_logged":False},ensure_ascii=False))
        raise SystemExit(1) from None
    print(json.dumps({"stage":"GLM53_DISCOVERY_LOW_EFFORT_PROBE_SUCCESS",
                      "gateway_low_reasoning_accepted":True,
                      "model":"glm-5.3","visible_chars":len(txt),
                      "actual_calls":budget.calls,
                      "completion_tokens_reported":budget.total_completion_tokens,
                      "prompt_tokens_reported":budget.total_prompt_tokens,
                      "no_source_or_prose_logged":True},ensure_ascii=False))

if __name__=="__main__":
    probe()
