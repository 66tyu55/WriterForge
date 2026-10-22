"""V123 old 951/964 source custody + separate 20-chapter revenge checkpoint.

The original sealed model outputs DO NOT contain a newly invented revenge arc.
A separate synthetic, author-confirmed example checks that the existing
pinned MIT reducer / V117 resume can carry an open vow through 20 restarts.
No model calls, no R2 writes, no canon writes, no 20 generated novels.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path

from experiments.v116_readonly_sealed_state_audit import data_from_sealed,need
from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v117_continuity_trace import make_resume,read_resume
from writerforge.v123_long_arc import (
    register_revenge,advance_open_revenge,relevant_revenge_hint,
    read_long_arc_from_resume,audit_revenge_prose,
)

SHA113="339b2b1cab1e4895ed73d4e8ef73ed0b51c6adb832149cd097c35b0ec9b585f7"
SHA114="c5146b829348ea12724290550ab8d4b4d959f2c1aaa41459c38bdeef757ad166"
PROJECT="v123-fiction-test-only"
SCENE="fiction-episode-stream"
ORIGIN="沈砚在父亲墓前立誓向唐蜃寻仇。"
CAST=("沈砚","唐蜃","叶青梧")


def main():
    need(not any(os.getenv(k) for k in (
        "DEEPSEEK_API_KEY","OPENROUTER_API_KEY","OPENAI_API_KEY",
        "ANTHROPIC_API_KEY","INTERN_API_KEY")),
        "WF123_NO_MODEL_SECRETS_OR_USAGE_ALLOWED")
    v113,v114=data_from_sealed()
    need(len(v113)==951 and len(v114)==964 and
         sha256(v113.encode()).hexdigest()==SHA113 and
         sha256(v114.encode()).hexdigest()==SHA114,
         "WF123_ORIGINAL_SEALED_SOURCE_DRIFT")

    arc=register_revenge(
        project_id=PROJECT,scene_id=SCENE,
        origin_chapter=0,source_prose=ORIGIN,
        source_quote=ORIGIN,arc_id="revenge-vow-001",
        actor="沈砚",target="唐蜃",
        motive="父亲遇害，主角仍在追查真正的幕后黑手",
        truth_scope="CHARACTER_BELIEF",author_confirmed=True)
    original_arc_sha=arc["receipt_sha256"]
    checkpoint=external_temporal_step(ORIGIN,cast=CAST)
    for chapter in range(1,21):
        prose=(f"叶青梧第{chapter}次走过山谷，雨声渐低。"
               if chapter<20 else
               "沈砚在破庙门口重逢唐蜃，决定暂缓动手，先追问旧案真相。")
        hint=relevant_revenge_hint(
            arc,project_id=PROJECT,scene_id=SCENE,
            goal=("叶青梧巡视山路" if chapter<20
                  else "沈砚重遇唐蜃，查清复仇起因"))
        need((hint=="")==(chapter<20),
             "WF123_IRRELEVANT_LAMP_OR_REUNION_GOAL_FORGOTTEN")
        checkpoint=external_temporal_step(prose,cast=CAST,prior=checkpoint)
        arc=advance_open_revenge(
            arc,project_id=PROJECT,scene_id=SCENE,
            chapter_index=chapter,prose=prose)
        resume=make_resume(
            project_id=PROJECT,scene_id=SCENE,
            chapter_index=chapter,checkpoint=checkpoint,
            long_arc_checkpoint=arc)
        restored=json.loads(json.dumps(resume,ensure_ascii=False))
        need(read_resume(restored,project_id=PROJECT,
                         scene_id=SCENE)==checkpoint,
             "WF123_ORIGINAL_NOVEL_STUDIO_CHECKPOINT_LOST")
        arc=read_long_arc_from_resume(
            restored,project_id=PROJECT,scene_id=SCENE)
        need(arc["target"]=="唐蜃" and
             arc["last_chapter"]==chapter and
             arc["status"]=="OPEN_AUTHOR_CONFIRMED",
             "WF123_OLD_AUTHOR_ARC_LOST_DURING_RESUME")

    false_win="沈砚杀了叶青梧，大仇得报。"
    output=audit_revenge_prose(arc,project_id=PROJECT,
                               scene_id=SCENE,prose=false_win)
    need(output["needs_review"] and
         output["automatic_settlement_allowed"] is False and
         arc["status"]=="OPEN_AUTHOR_CONFIRMED" and
         arc["receipt_sha256"]!=original_arc_sha,
         "WF123_FALSE_REVENGE_WIN_AUTOCOMMITTED")
    record={
        "format":"wf.audit.v123.twenty-resumed-chapters-zero-provider",
        "sealed_v113_951_chars_sha256":SHA113,
        "sealed_v114b_964_chars_sha256":SHA114,
        "twenty_chapters_are_synthetic_not_twenty_llm_novels":True,
        "twenty_real_novel_studio_reducer_steps":20,
        "twenty_v117_resume_roundtrips":20,
        "last_chapter":arc["last_chapter"],
        "revenge_goal_remains_author_confirmed_open":True,
        "quiet_19_chapters_no_revenge_lamp":True,
        "target_return_20th_chapter_reactivated":True,
        "belief_not_promoted_to_actual_murderer":True,
        "false_wrong_target_revenge_claim_needs_review":True,
        "model_claim_did_not_autosettle_arc":True,
        "original_frozen_real_prose_not_modified":True,
        "new_model_calls":0,"R2_writes":0,"canon_writes":0,
        "longform_creative_quality_verified":False,
    }
    out=Path("wf123_source_and_20_chapters")
    out.mkdir(exist_ok=False)
    (out/"STATUS.json").write_text(json.dumps(
        record,ensure_ascii=False,sort_keys=True,indent=2),
        encoding="utf8")
    print(json.dumps(record,ensure_ascii=False,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
