"""V75 safe idle: official DeepSeek connected, LEARN R2 journal pending.

No model calls, R2 source reads, R2 writes, GitHub Actions or timer loops.
The new Cloudflare LEARN-only writer route and distinct secret must first be
deployed by the owner before any private chapter is sent to DeepSeek.
"""
from __future__ import annotations

import os
import json
import time

print(json.dumps({
    "status":"WF_V75_SAFE_IDLE_LEARN_JOURNAL_PENDING_DEPLOY",
    "wf_learn_model_selected":"deepseek-flash",
    "deepseek_api_key_name_present":bool(os.environ.get("DEEPSEEK_API_KEY")),
    "original_r2_reader_configured":bool(os.environ.get("WF_API_TOKEN")),
    "existing_sql_index_writer_configured":bool(
        os.environ.get("WF_INDEX_UPLOAD_TOKEN")),
    "new_learn_writer_configured":bool(os.environ.get("WF_LEARN_UPLOAD_TOKEN")),
    "cloudflare_learn_event_api_verified_live":False,
    "previous_deepseek_synthetic_probe_succeeded":True,
    "writer_ready_check_run":False,
    "paid_model_calls_this_run":0,
    "real_novel_content_sent_to_deepseek_this_run":False,
    "original_r2_source_reads_this_run":0,
    "r2_writes_this_run":0,
    "railway_volume_created":False,
    "mastery_promoted":False,
    "literary_learning_completed_chapters_this_run":0,
    "second_literary_window_locked":True,
    "credential_values_logged":False,
},ensure_ascii=False,sort_keys=True),flush=True)
time.sleep(6)
