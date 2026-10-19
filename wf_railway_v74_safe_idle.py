"""WF V74 safe idle. Selected learner = official DeepSeek Flash.

Railway can hold both user R2 secrets and the new DEEPSEEK_API_KEY. This
script only reports boolean configuration status. It does NOT call DeepSeek,
read original novels, upload any SQL, or auto-launch literary learning.
"""
from __future__ import annotations

import json
import os
import sys
import time
import types
from pathlib import Path

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg

from writerforge.wf_learn_model_registry import model_status

source=model_status()
print(json.dumps({
  "status":"WF_V74_SAFE_IDLE_DEEPSEEK_FLASH_SELECTED",
  "WF_LEARN_PROVIDER":source["WF_LEARN_PROVIDER"],
  "WF_LEARN_MODEL":source["WF_LEARN_MODEL"],
  "official_deepseek_key_present":source["key_present"],
  "discovery_model_selected":False,
  "WF_first_read_immutable_r2_journal_ready":False,
  "new_WF_learn_sessions_auto_started":False,
  "paid_model_calls":0,
  "real_source_books_read":0,
  "source_text_uploaded_to_third_party":False,
  "R2_writes":0,
  "Railway_volume_created":False,
  "v49_literary_failure_preserved":True,
  "second_literary_window_locked":True,
  "credential_values_logged":False,
},ensure_ascii=False,sort_keys=True),flush=True)
time.sleep(7)
