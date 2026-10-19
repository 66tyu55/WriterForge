"""WF V74 official DeepSeek Flash connection probe, SYNTHETIC TEXT ONLY.

The user selected DeepSeek. This probes one tiny paid API response only if
their own Railway service has DEEPSEEK_API_KEY. The source is an invented
JSON handshake, no R2 work, no private novel data or site credential logged.

Neither this successful probe nor a model's JSON proves literary learning.
"""
from __future__ import annotations

import json
import os
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
wf = types.ModuleType("writerforge")
wf.__path__ = [str(ROOT/"writerforge")]
wf.__package__ = "writerforge"
sys.modules["writerforge"] = wf


def emit(data):
    print(json.dumps(data, ensure_ascii=False,sort_keys=True),flush=True)

print("WF_V74_DEEPSEEK_FLASH_SYNTHETIC_API_PROBE_STARTED",flush=True)

def main():
    from writerforge.wf_learn_model_registry import (
        model_status,new_wf_learn_model,
    )
    from writerforge.deepseek_flash_model import (
        DeepSeekFlashError,FlashBudget,
    )
    setup=model_status()
    emit({
      "status":"WF_V74_WF_LEARN_MODEL_SELECTED",
      "provider":setup["WF_LEARN_PROVIDER"],
      "model":setup["WF_LEARN_MODEL"],
      "credential_name":setup["key_variable_name"],
      "key_present":setup["key_present"],
      "discovery_used":False,
      "private_source_uploaded_to_provider":False,
      "paid_training_auto_started":False,
    })
    if not setup["key_present"]:
        emit({
          "status":"WF_V74_WAITING_FOR_DEEPSEEK_API_KEY",
          "no_network_requests":True,
          "model_calls":0,
          "originals_sent_to_deepseek":False,
          "R2_mutations":0,
          "literary_learning_proven":False,
        })
        return 0
    try:
        budget=FlashBudget(max_calls=1,max_reserved_output_tokens=160)
        model=new_wf_learn_model(budget=budget)
        output=model.ask_json(
            role="genre_classification",
            system=(
                "你在执行WriterForge自己的联网健康检查，"
                "输入为合成内容，不涉及用户原著。"
                "只返回 JSON 对象，格式为"
                ' {"probe":"ready","synthetic_only":true}。'
            ),
            user=(
                '合成探针：请返回 JSON {"probe":"ready",'
                '"synthetic_only":true}，不要分析任何真实小说。'
            ),
            max_tokens=120,
        )
        if output.get("probe")!="ready" or output.get("synthetic_only") is not True:
            raise DeepSeekFlashError("WF_FLASH_SYNTHETIC_CONTRACT_UNMET")
        emit({
            "status":"WF_V74_DEEPSEEK_FLASH_REAL_API_PROBE_OK",
            "provider":"deepseek",
            "model":"deepseek-flash",
            "synthetic_only":True,
            "actual_api_requests":budget.calls_reserved,
            "api_usage":budget.public_receipt(),
            "real_private_novel_prose_sent":False,
            "R2_source_reads":0,
            "R2_writes":0,
            "WF_first_read_R2_journal_ready":False,
            "WF_literary_study_started":False,
        })
        return 0
    except Exception as exc:
        error=str(exc)
        if not error.startswith("WF_FLASH_"):
            error="WF_FLASH_UNEXPECTED_PROVIDER_FAILURE"
        emit({
            "status":"WF_V74_DEEPSEEK_FLASH_PROBE_FAILED",
            "error_code":error,
            "source_text_logged":False,
            "secret_logged":False,
            "literary_study_started":False,
        })
        return 1

ret=main()
print("WF_V74_DEEPSEEK_PROBE_EXIT="+str(ret),flush=True)
time.sleep(7)
raise SystemExit(ret)
