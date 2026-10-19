"""V80 final safe idle after the 150,000-token-cap training batch.

One shot prints stored historical verified receipts and no source content.
It NEVER starts a model call, reads private novels, accesses R2, or loops.
"""
from __future__ import annotations
import json,os,time

print(json.dumps({
  "status":"WF_V80_SAFE_IDLE_150K_LIMIT_APPLIED",
  "model":"deepseek-flash",
  "requested_single_batch_total_input_output_token_ceiling":150000,
  "last_real_batch_chapters_with_full_source_coverage":6,
  "last_real_batch_clean_pass_a_before_pass_b_chapters":5,
  "last_real_batch_prior_chapter1_mixed_early_analysis":True,
  "last_real_batch_provider_calls":73,
  "last_real_batch_prompt_tokens":67494,
  "last_real_batch_completion_tokens":15869,
  "last_real_batch_total_tokens":83363,
  "last_real_batch_total_stayed_below_cap":True,
  "last_batch_cas_pointer_sha256":
      "f606f5216f82fd40a7893cfe8942e2454efe94b9f1389110bdc37f19f3a4f227",
  "last_journal_cas_checkpoint_sha256":
      "0b24a62a697b11e140477225728375fc406cd035fe921ad8ca5476b48a674240",
  "deepseek_key_name_configured":bool(os.getenv("DEEPSEEK_API_KEY")),
  "r2_reader_name_configured":bool(os.getenv("WF_API_TOKEN")),
  "r2_existing_writer_name_configured":bool(
       os.getenv("WF_INDEX_UPLOAD_TOKEN")),
  "fourth_secret_needed":False,
  "api_requests_this_idle_run":0,
  "private_source_downloaded_this_idle_run":False,
  "r2_writes_this_idle_run":0,
  "automatic_next_batch_started":False,
  "provider_charge_portal_independently_reconciled":False,
  "model_self_evaluation_not_human_validation":True,
  "v49_graduation_failure_preserved":True,
  "literary_second_window_stays_locked":True,
},ensure_ascii=False,sort_keys=True),flush=True)
time.sleep(5)
