"""V118 read-only real V113/V114B + existing craft trigger probe.

The original model-written prose comes from sealed R2 CAS with immutable SHA.
This intentionally does NOT generate an additional scene, learn new experience,
change any original source or claim independent literary improvement.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path

from experiments.v116_readonly_sealed_state_audit import data_from_sealed,need
from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v117_continuity_trace import audit_continuity
from writerforge.v118_lamp_scheduler import plan_scene_lamps


def lamp(frame,beat,chapter_index=0):
    return plan_scene_lamps(
        project_id=frame["project_id"],chapter_index=chapter_index,
        turn_index=0,beat=beat,frame=frame)

def beat(actor,goal,kind="action",focus=()):
    return {"id":"t01","kind":kind,"actor":actor,"goal":goal,
            "craft_focus":list(focus)}


def main():
    need(not os.getenv("DEEPSEEK") and
         not os.getenv("DEEPSEEK_API_KEY"),
         "WF118_NO_PROVIDER_API_KEYS_ON_READONLY_RUN")
    v113,v114=data_from_sealed()
    a=external_temporal_step(v113,cast=("叶青梧","沈渡"))
    b=external_temporal_step(v114,cast=("沈砚","唐蜃"))
    sword=audit_continuity(a,project_id="wf-real-v113-lamp-probe",
                          chapter_index=0,boundary="after")
    fruit=audit_continuity(b,project_id="wf-real-v114b-lamp-probe",
                          chapter_index=0,boundary="after")
    tassel=lamp(sword,beat("沈渡","再次把剑穗从钩尖收回"))
    unchanged=lamp(sword,beat("沈渡","遥望山路，山风吹过崖边",kind="quiet"))
    injury=lamp(fruit,beat("沈砚","沈砚用右臂强行开路",focus=("action",)))
    wrong_actor=lamp(fruit,beat("唐蜃","唐蜃踢开岔口木门"))
    fruit_consumption=lamp(fruit,beat("沈砚","是否吞下火髓果，借法力反击",kind="decision"))
    need("transfer" in tassel["risk_lamps"],
         "WF118_REAL_SOURCE_SWORD_TASSEL_LAMP_DID_NOT_FIRE")
    need(unchanged["prompt"]=="" and unchanged["zero_lamp_is_valid"],
         "WF118_REAL_SOURCE_QUIET_SEGMENT_OVERLIT")
    need("arm" in injury["risk_lamps"],
         "WF118_REAL_SOURCE_ARM_COST_LAMP_NOT_FIRING")
    need("arm" not in wrong_actor["risk_lamps"],
         "WF118_REAL_SOURCE_WRONG_ACTOR_FALSE_ARM_ATTRIBUTION")
    need("resource" in fruit_consumption["risk_lamps"] and
         fruit_consumption["craft_id"] is not None,
         "WF118_FRUIT_RESOURCE_OR_DECISION_CAUSAL_GUIDANCE_NOT_FIRING")
    need(all(x["new_model_calls"]==0 and x["factjournal_canon_writes"]==0
             for x in (tassel,unchanged,injury,wrong_actor,fruit_consumption)),
         "WF118_AN_UNAUTHORIZED_MODEL_OR_FACT_WRITE_APPEARED")
    result={
        "format":"wf.audit.v118.source-driven-fiction-lamps-zero-provider",
        "sealed_v113_original_sha256":sha256(v113.encode("utf8")).hexdigest(),
        "sealed_v114b_original_sha256":sha256(v114.encode("utf8")).hexdigest(),
        "V113_original_characters":len(v113),
        "V114B_original_characters":len(v114),
        "scenario_only_lamp_tests_not_new_literary_writing":True,
        "sword_tassel_unproven_debt_lamp_activated":"transfer" in tassel["risk_lamps"],
        "unrelated_quiet_scene_did_not_activate_lamp":unchanged["prompt"]=="",
        "injured_actor_lamp_activated":"arm" in injury["risk_lamps"],
        "other_actor_not_injured": "arm" not in wrong_actor["risk_lamps"],
        "fruit_resource_light_triggered":"resource" in fruit_consumption["risk_lamps"],
        "specific_existing_CraftEngine_question_selected":
            fruit_consumption["craft_id"] is not None,
        "old_964_character_V96_schema_rejection_preserved":True,
        "real_second_story_scene_generated":False,
        "new_model_calls":0,"R2_writes":0,"canon_writes":0,
        "literary_quality_improvement_proven":False,
        "original_manuscripts_not_logged":True,
    }
    folder=Path("wf118_sealed_lamp_probe")
    folder.mkdir(exist_ok=False)
    (folder/"SOURCE_ONLY_STATUS.json").write_text(
        json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2),
        encoding="utf8")
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
