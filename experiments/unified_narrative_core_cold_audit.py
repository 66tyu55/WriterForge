"""Cold actual-R2 identity plus 300 simulated longhook chapters (zero models).

The 951/964-character historical novel texts are checked byte-exact and left
untouched. The 300 follow-up scenes are deterministic synthetic fixture prose,
NOT literary generations or evidence of full-model writing improvement.
"""
from __future__ import annotations
import json
import os
from hashlib import sha256
from pathlib import Path

from experiments.v116_readonly_sealed_state_audit import data_from_sealed,need
from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v117_continuity_trace import make_resume,read_resume
from writerforge.narrative_core import (
    new_graph,advance_graph,schedule,keyed_diff,knows,read_core_from_resume,
)

SHA113="339b2b1cab1e4895ed73d4e8ef73ed0b51c6adb832149cd097c35b0ec9b585f7"
SHA114="c5146b829348ea12724290550ab8d4b4d959f2c1aaa41459c38bdeef757ad166"
P="wf-unified-300-cold-fixture"
S="story"
FACT="沈砚把密令藏在井底。"
THREAD="沈砚对唐蜃立誓，迟早追查旧案。"
PROSE=FACT+THREAD

def evt(quote,kind,**kw):
    return {"id":kw.pop("id",kind),"kind":kind,
            "quote":quote,"start":PROSE.index(quote),
            "author_confirmed":True,**kw}

def main():
    need(not any(os.getenv(k) for k in (
        "DEEPSEEK_API_KEY","OPENROUTER_API_KEY",
        "OPENAI_API_KEY","ANTHROPIC_API_KEY","INTERN_API_KEY")),
        "WFCORE_NO_PROVIDER_KEYS")
    src113,src114=data_from_sealed()
    need(len(src113)==951 and len(src114)==964 and
         sha256(src113.encode()).hexdigest()==SHA113 and
         sha256(src114.encode()).hexdigest()==SHA114,
         "WFCORE_FROZEN_ORIGINAL_HASH_CHANGED")
    source_checkpoint=external_temporal_step(
        src114,cast=("沈砚","唐蜃"))
    frame=new_graph(project_id=P,scene_id=S,chapter_index=0)
    seed_resume=make_resume(
        project_id=P,scene_id=S,chapter_index=0,
        checkpoint=source_checkpoint,
        unified_narrative_core=frame)
    restored=json.loads(json.dumps(seed_resume,ensure_ascii=False))
    need(read_resume(restored,project_id=P,scene_id=S)==source_checkpoint,
         "WFCORE_COLD_MIT_REDUCER_LOST")
    frame=read_core_from_resume(restored,project_id=P,scene_id=S)
    frame=advance_graph(
        frame,project_id=P,scene_id=S,chapter_index=1,
        prose=PROSE,events=(
            evt(FACT,"FACT",id="f",fact_id="well",
                name="密令藏在井底",visibility="SECRET"),
            evt(THREAD,"THREAD_OPEN",id="t",
                thread_id="hidden-case",thread_kind="FORESHADOW",
                owner="沈砚",target="唐蜃",
                premise="旧案背后的人物尚未查明",
                truth_scope="CHARACTER_BELIEF")))
    first_size=len(json.dumps(frame,ensure_ascii=False))
    for chapter in range(2,302):
        prior=frame
        frame=advance_graph(
            frame,project_id=P,scene_id=S,chapter_index=chapter,
            prose=f"第{chapter}章，山雨仍在。")
        need(keyed_diff(prior,frame)["dirty_nodes"]==[],
             "WFCORE_DIRTY_NODES_GROW_WITH_UNRELATED_CHAPTER")
        hint=schedule(
            frame,project_id=P,scene_id=S,chapter_index=chapter+1,
            beat={"kind":"quiet","actor":"沈砚",
                  "goal":"山雨寂静，无关旧事"})["required_context"]
        need(hint=="","WFCORE_300_CHAPTER_UNRELATED_LAMPS_SPAM")
    final=schedule(
        frame,project_id=P,scene_id=S,chapter_index=302,
        beat={"kind":"decision","actor":"沈砚",
              "goal":"沈砚与唐蜃重逢并追查旧案"})
    need("旧案背后的人物尚未查明" in final["required_context"],
         "WFCORE_300_CHAPTER_FORESHADOW_MISSING")
    need(knows(frame,character="唐蜃",fact_id="well")=="NOT_ESTABLISHED",
         "WFCORE_UNWITNESSED_NPC_KNOWLEDGE_FABRICATED")
    need(len(json.dumps(frame,ensure_ascii=False))-first_size<600,
         "WFCORE_300_CHAPTER_GRAPH_MEMORY_UNBOUNDED")
    result={
        "format":"wf.audit.unified-narrative-300-chapter-incremental",
        "original_v113_sha256":SHA113,
        "original_v114b_sha256":SHA114,
        "sealed_original_source_unchanged":True,
        "original_mit_novel_studio_reducer_check":True,
        "first_checkpoint_resume_roundtrip":True,
        "synthetic_unrelated_incremental_chapters":300,
        "single_narrative_graph_over_300_chapters":True,
        "no_spurious_dirty_nodes":True,
        "no_npc_knowledge_from_contact_or_story_mentions":True,
        "300th_chapter_thread_reactivated":True,
        "model_story_generation_calls":0,"canon_writes":0,"R2_writes":0,
        "independent_literary_quality_proven":False,
    }
    folder=Path("wf_unified_narrative_core_cold_audit")
    folder.mkdir(exist_ok=False)
    (folder/"SOURCE_ONLY_STATUS.json").write_text(
        json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2),
        encoding="utf8")
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
