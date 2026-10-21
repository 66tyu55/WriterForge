"""V117 actual sealed V113 / V114B longform text continuity cold audit.

Proves the MIT chapter-time / prop / POV wrapper can consume ORIGINAL
private R2 source-anchored WF state without any new inference. Genuine
manuscripts are never printed or uploaded; JSON artifact has SHA/flags only.
"""
from __future__ import annotations
import json
import os
from hashlib import sha256
from pathlib import Path
from experiments.v116_readonly_sealed_state_audit import data_from_sealed,need
from writerforge.v114_external_story_state import external_temporal_step,temporal_prompt
from writerforge.v117_continuity_trace import (
    audit_continuity,compact_context,preflight_continuation,
    make_resume,read_resume,
)

def digest(x):return sha256(x.encode("utf8")).hexdigest()

def run():
    need(not os.environ.get("DEEPSEEK") and
         not os.environ.get("DEEPSEEK_API_KEY"),
         "WF117_PROVIDER_CREDENTIAL_MUST_BE_ABSENT")
    sword,fruit=data_from_sealed()
    first=external_temporal_step(sword,cast=("叶青梧","沈渡"))
    second=external_temporal_step(fruit,cast=("沈砚","唐蜃"))
    result=second["reducer_result"]
    need(result.get("error_code") is None and
         result["verified_events"]>=4,
         "WF117_REAL_STATE_DELTA_MUST_BE_VERIFIED_BY_OSS_REDUCER")
    frame=audit_continuity(second,project_id="wf-v114b-verified-source-probe",
         chapter_index=0,boundary="after")
    need(frame["coverage"]["state_cells"]>=3 and
         frame["coverage"]["knowledge_coverage_proven"] is False and
         frame["coverage"]["time_coverage_proven"] is False,
         "WF117_REAL_PROSE_UNREGISTERED_TIMELINE_CAN_NOT_LAUNDER")
    context=compact_context(frame)
    need("火髓果" in context and "右臂" in context,
         "WF117_NEXT_SCENE_CONTEXT_OMITS_ACTUAL_RESOURCES_OR_HARM")
    historical=make_resume(project_id="wf-v114b-verified-source-probe",
         scene_id="xianxia-chase",chapter_index=0,checkpoint=second)
    restored=read_resume(json.loads(json.dumps(historical,ensure_ascii=False)),
         project_id="wf-v114b-verified-source-probe",scene_id="xianxia-chase")
    frame2=audit_continuity(restored,
         project_id="wf-v114b-verified-source-probe",
         chapter_index=1,boundary="before")
    need(frame2["source_checkpoint_sha256"]==frame["source_checkpoint_sha256"],
         "WF117_LONGTERM_RESTORED_SOURCE_DRIFTED")
    safe=("沈砚右臂仍垂着，左手攥紧火髓果，以肩膀撞开岔路石门。"
          "他失血却尚在逃，唐蜃仍在身后追赶。")
    impossible=("沈砚右臂挥剑反杀唐蜃，火髓果仍含在齿间。"
                "灵力凭空恢复，受伤再无影响。")
    good=preflight_continuation(safe,restored,
          project_id="wf-v114b-verified-source-probe",chapter_index=1)
    bad=preflight_continuation(impossible,restored,
          project_id="wf-v114b-verified-source-probe",chapter_index=1)
    need(not good["blocked"] and bad["blocked"],
         "WF117_CROSS_RESTART_REAL_PRIOR_WRONG_WRITING_NOT_BLOCKED")
    sword_frame=audit_continuity(first,project_id="wf-v113-source-probe",
           chapter_index=0,boundary="after")
    need("UNPROVEN_ITEM_TRANSFER" in [x["kind"] for x in
         first["reducer_result"]["risks"]] and
         "沈渡" in compact_context(sword_frame) and
         "索钩" in temporal_prompt(first),
         "WF117_REAL_SWORD_TASSEL_UNPROVEN_CAUSAL_DEBT_LOST")
    out={
        "format":"wf.audit.v117.real-old-sealed-no-model-longform-continuity",
        "real_V113_source_sha256":digest(sword),
        "real_V114B_source_sha256":digest(fruit),
        "real_V113_chars":len(sword),"real_V114B_chars":len(fruit),
        "real_V113_sword_tassel_unproven_transfer_preserved":True,
        "V114B_5_proposed_reducer_events":result["verified_events"],
        "original_V114B_rejected_964_over_950":True,
        "original_V114B_second_scene_exists":False,
        "candidate_arm_and_fruit_in_next_prompt":True,
        "source_checkpoint_cold_restart_sha256":restored["receipt_sha256"],
        "next_chapter_wrong_bodily_action_blocked":bad["blocked"],
        "next_chapter_safe_movement_allowed":not good["blocked"],
        "novel_studio_temporal_version_pinned":frame["upstream_commit"],
        "independent_full_knowledge_registry_coverage_proven":False,
        "independent_full_timeline_coverage_proven":False,
        "new_model_calls":0,"R2_writes":0,"canonical_fact_writes":0,
        "no_original_prose_logged_or_uploaded":True,
        "WF_literary_improvement_proven":False,
        "no_paid_test_authorized":True,
    }
    folder=Path("wf117_readonly_sealed_trace_audit")
    folder.mkdir(exist_ok=False)
    (folder/"AUDIT_SUMMARY_NO_SOURCE_PROSE.json").write_text(
        json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2),
        encoding="utf8")
    print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(run())
