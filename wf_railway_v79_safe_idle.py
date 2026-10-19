"""V79 safe idle AFTER first real DeepSeek B01 + R2 CAS evidence restored.

Training has already completed for the opening 3/15 source units:
  3 paid first-reads + 1 analysis; 4 calls, 3257 reported total tokens.
  5 immutable R2 content-addressed LEARN events; a separate reader-only
  Railway process verified their source binding and order.

This script does NO DeepSeek calls, no R2 access and no autoscheduling.
User's three pre-existing secrets are sufficient for the small trial.
"""
from __future__ import annotations
import json,os,time

print(json.dumps({
  "status":"WF_V79_SAFE_IDLE_REAL_B01_3_UNITS_CONFIRMED",
  "existing_three_secret_names_present":{
     "DeepSeek":bool(os.environ.get("DEEPSEEK_API_KEY")),
     "R2_reader":bool(os.environ.get("WF_API_TOKEN")),
     "R2_existing_index_writer":bool(
         os.environ.get("WF_INDEX_UPLOAD_TOKEN")),
  },
  "fourth_secret_required":False,
  "real_b01_first_read_units":3,
  "real_b01_craft_analysis_events":1,
  "paid_model_calls_in_completed_trial":4,
  "reported_input_tokens_in_completed_trial":2526,
  "reported_output_tokens_in_completed_trial":731,
  "full_chapters_literarily_completed":0,
  "permanent_r2_cas_checkpoint_sha256":
     "b7ace511e422c8973a35c0cc4d75229d0c11c7ddcefe4db97eda6b6098bc1210",
  "native_learn_namespace_deployed":False,
  "reader_only_cold_restore_verified":True,
  "independent_literary_quality_certified":False,
  "paid_model_calls_this_idle_run":0,
  "r2_reads_this_idle_run":0,
  "r2_writes_this_idle_run":0,
  "auto_paid_batch_enabled":False,
  "v49_third_strike_failed_preserved":True,
  "second_literary_window_locked":True,
  "private_text_or_secret_logged":False,
},ensure_ascii=False,sort_keys=True),flush=True)
time.sleep(6)
