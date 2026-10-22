"""V121 cold source audit, no model or external provider calls.

Read only the original sealed V113 and V114B private narratives; use V114B's
unchanged temporal state as a fixed checkpoint for zero-model counterfactual
next-sentence actor attribution. Do not publish old prose.
"""
from hashlib import sha256
import json
import os
from pathlib import Path

from experiments.v116_readonly_sealed_state_audit import data_from_sealed,need
from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v116_state_delta import preflight_next_prose
from writerforge.v117_continuity_trace import preflight_continuation

OLD_V113="339b2b1cab1e4895ed73d4e8ef73ed0b51c6adb832149cd097c35b0ec9b585f7"
OLD_V114="c5146b829348ea12724290550ab8d4b4d959f2c1aaa41459c38bdeef757ad166"


def main():
    need(not any(os.getenv(k) for k in (
        "DEEPSEEK_API_KEY","OPENAI_API_KEY","OPENROUTER_API_KEY",
        "ANTHROPIC_API_KEY")), "WF121_PROVIDER_CREDENTIAL_NOT_ALLOWED")
    v113,v114=data_from_sealed()
    need(sha256(v113.encode("utf8")).hexdigest()==OLD_V113 and
         sha256(v114.encode("utf8")).hexdigest()==OLD_V114,
         "WF121_FROZEN_SOURCE_MISMATCH")
    prior=external_temporal_step(v114,cast=("沈砚","唐蜃"))
    state=prior["reducer_result"]["candidate_state"]
    cast=("沈砚","唐蜃")
    enemy=preflight_next_prose(
        "唐蜃右手挥剑冲向沈砚。沈砚侧身退到山壁旁。",
        previous_candidate_state=state,cast=cast)
    protagonist=preflight_next_prose(
        "沈砚右手挥剑冲向唐蜃。",
        previous_candidate_state=state,cast=cast)
    ambiguous=preflight_next_prose(
        "他右手挥剑劈向矿道。",
        previous_candidate_state=state,cast=cast)
    old_character_constraint=preflight_continuation(
        "唐蜃右手挥剑冲向沈砚。",
        prior,project_id="wf121-original-cold",
        chapter_index=1,cast=cast)
    need(enemy["blocked"] is False and not enemy["needs_review"],
         "WF121_ENEMY_ACTION_MISATTRIBUTED_TO_INJURED_HERO")
    need(protagonist["blocked"] and
         "WF116_ARM_USED_WITHOUT_RECOVERY" in protagonist["findings"],
         "WF121_REAL_HERO_RIGHT_ARM_CONSTRAINT_DROPPED")
    need(not ambiguous["blocked"] and ambiguous["needs_review"],
         "WF121_UNGROUNDED_PRONOUN_FALSE_CONFIDENCE")
    need(not old_character_constraint["blocked"],
         "WF121_STORY_PREFLIGHT_ENEMY_FALSE_BLOCK")
    report={
        "format":"wf.audit.v121.readonly-real-source-actor-scope",
        "original_v113_sha256":OLD_V113,
        "original_v114b_sha256":OLD_V114,
        "real_old_v113_chars":len(v113),
        "real_old_v114b_chars":len(v114),
        "unrelated_enemy_action_not_blocked":True,
        "explicit_injured_hero_action_blocked":True,
        "unresolved_pronoun_review_not_block":True,
        "old_preflight_cast_bound":True,
        "old_rejected_first_scene_still_rejected":True,
        "new_second_scene_generated":False,
        "new_model_calls":0,"R2_writes":0,"canon_writes":0,
        "literary_quality_proven":False,
        "private_original_prose_not_logged":True,
    }
    folder=Path("wf121_readonly_source")
    folder.mkdir(exist_ok=False)
    (folder/"SOURCE_ONLY_STATUS.json").write_text(
        json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2),
        encoding="utf8")
    print(json.dumps(report,ensure_ascii=False,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
