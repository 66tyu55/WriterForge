"""Real POV-learning diagnostic against preserved 3-chapter WF source.

One previous genuine DeepSeek chapter plan and two beats are frozen from
Actions run 39976958906. The prior writer leaked exact "灰袋三十" into
陶筠's dialogue despite a source saying 简洛 had NOT told her. This
diagnostic adds source-anchored FACT+UNKNOWN to the EXISTING unified graph
and writes just ONE new candidate chapter (two actual model prose calls).

No new memory or prompt templates, no automatic retry, no user manuscripts,
no canon/Railway, no re-summarizing/copying original prose as new fiction.
This is one exploratory retest, not a statistically balanced A/B winner.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path

from experiments import wf_three_chapter_real_continuity_pilot as pilot
from experiments import wf_real_self_scene_diagnostics as diag
from experiments import wf_source_progression_ab as ab
from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget
from writerforge.v96_causal_turns import parse_turn_outline
from writerforge.writing_assist import _normalize_optional_model_craft_labels
from writerforge.narrative_core import new_graph,advance_graph,schedule,audit_candidate
from experiments.wf_real_self_scene_diagnostics import source_event
from writerforge.v114_external_story_state import require_external_runtime

ROOT=Path("wf_real_three_chapter_frozen_sources")
OUTPUT=Path("wf_pov_unknown_real_prose_results")
HISTORICAL_RUN=39976958906
ORIGINAL_SHA={
    "CHAPTER_001_ORIGINAL_SEED.md":"b312f8530c9b10ccac816c5a13f4408a8269db8b3b19691cecd1711ec8f1d292",
    "CHAPTER_002/raw_provider/CHAPTER_PLAN-decoded-original.json":
        "0b7e109d1112836bf9730c628a96231c189be05ef1eedec2d2778acba053cf97",
    "CHAPTER_002/raw_provider/SELF_BEAT_PLAN-decoded-original.json":
        "aa86bfbdda011e02731746278e6c47af04736e5fd8d4937bb8074420bb8232f5",
    "CHAPTER_002/ORIGINAL_WF_CANDIDATE.md":
        "f0bf9d71a8ca0d5cff04ed5a11d93ae99860051b46958b527047a1fd8e496bdf",
}
CASE="unknown-source"
SECRET_QUOTE=(
    "简洛捡到一张盖着模糊蓝印的运货单，上面只有“灰袋三十”，"
    "没有收货地点；他没告诉陶筠。"
)
# The old narrator's quoted inscription cannot itself be an event anchor:
# do NOT bypass the strict spoken/hypothetical source guard. This explicit
# synthetic author clarification adds no secret outcome, only a POV limit,
# and is reported as a changed source (not byte-equal A/B).
AUTHOR_SOURCE_CLARIFICATION=(
    "陶筠从未见过简洛藏起的运货单，也不知道上面写着灰袋三十。"
)


def h(value):
    return hashlib.sha256(
        value.encode("utf8") if isinstance(value,str) else value).hexdigest()


def original_text(relative):
    expected=ORIGINAL_SHA[relative]
    data=(ROOT/relative).read_bytes()
    if h(data)!=expected:
        raise RuntimeError("WF_POV_OLD_ORIGINAL_SHA_CHANGED")
    return data.decode("utf8")


def case_with_author_known_unknown():
    if pilot.SOURCE.count(SECRET_QUOTE)!=1:
        raise RuntimeError("WF_POV_EXACT_SECRET_SOURCE_MISSING")
    return {
        "genre":pilot.GENRE,
        "seed":pilot.SOURCE+AUTHOR_SOURCE_CLARIFICATION,
        "cast":pilot.CAST,
        "goal":pilot.CHAPTER_GOALS[0],
        "outline":pilot.OUTLINE,
        "event_quotes":list(pilot.EVENTS)+[
            ("FACT",AUTHOR_SOURCE_CLARIFICATION,
             {"fact_id":"blue-shipping-note","name":"灰袋三十",
              "visibility":"SECRET"}),
            ("UNKNOWN",AUTHOR_SOURCE_CLARIFICATION,
             {"actor":"陶筠","fact_id":"blue-shipping-note"}),
        ],
    }


def main():
    if not os.getenv("DEEPSEEK_API_KEY"):
        raise RuntimeError("WF_POV_EXISTING_MODEL_KEY_MISSING")
    require_external_runtime()
    OUTPUT.mkdir(parents=True,exist_ok=False)
    old_seed=original_text("CHAPTER_001_ORIGINAL_SEED.md")
    if old_seed!=pilot.SOURCE:
        raise RuntimeError("WF_POV_SEED_DRIFT")
    old_chapter=original_text("CHAPTER_002/ORIGINAL_WF_CANDIDATE.md")
    if "灰袋三十" not in old_chapter or "陶筠" not in old_chapter:
        raise RuntimeError("WF_POV_OLD_LEAK_NOT_REPRODUCED")
    original_plan=original_text(
        "CHAPTER_002/raw_provider/CHAPTER_PLAN-decoded-original.json")
    old_beats=original_text(
        "CHAPTER_002/raw_provider/SELF_BEAT_PLAN-decoded-original.json")
    beats,compat=_normalize_optional_model_craft_labels(old_beats)
    plan=parse_turn_outline(beats)
    if len(plan)!=2 or plan[0]["actor"]!="陶筠":
        raise RuntimeError("WF_POV_OLD_ACTOR_PLAN_NOT_AS_EXPECTED")
    case=case_with_author_known_unknown()
    diag.CASES[CASE]=case
    assert ab.CASES is diag.CASES
    ab.TARGET=OUTPUT
    project="wf-source-literary-ab-experiment"
    scene="scene-"+CASE
    graph=new_graph(project_id=project,scene_id=scene)
    graph=advance_graph(
        graph,project_id=project,scene_id=scene,
        chapter_index=1,prose=case["seed"],
        events=[source_event(case["seed"],i,event)
                for i,event in enumerate(case["event_quotes"],1)])
    reminder=schedule(graph,project_id=project,scene_id=scene,
                      chapter_index=2,beat=plan[0])
    if ("人物尚未知情的来源底线" not in reminder["required_context"]
        or "灰袋三十" not in reminder["required_context"]
        or reminder["author_unknown_proactive_chosen"]!=1):
        raise RuntimeError("WF_POV_UNKNOWN_HARD_REMINDER_NOT_DELIVERABLE")
    old_review=audit_candidate(
        graph,project_id=project,scene_id=scene,
        prose=old_chapter,cast=pilot.CAST)
    if "WFCORE_UNREVIEWED_UNKNOWN_FACT_MENTION" not in old_review[
            "review_findings"]:
        raise RuntimeError("WF_POV_ORIGINAL_LEAK_NOT_IDENTIFIED")
    # The new experiment retains the same plan even though that older plan
    # embeds a faulty assumption: any progress must come from actual source
    # constraints in current writer prompts, not hand-written prose fixes.
    budget=FlashBudget(max_calls=2,max_reserved_output_tokens=2900,
                       max_total_tokens=150000)
    model=DeepSeekFlashModel(budget=budget,timeout_seconds=120)
    pair={
        "model_plan":original_plan,"model_beats":beats,
        "model_optional_craft_recovery":compat,
    }
    receipts=[]
    result=ab._runner(
        CASE,mode="baseline",blind_id="NEW_SOURCE_GUARD",
        plans=pair,root=OUTPUT,client=model,calls=receipts)
    result["old_original_chapter_sha256"]=h(old_chapter)
    result["original_source_seed_sha256"]=h(old_seed)
    result["supplemented_source_seed_sha256"]=h(case["seed"])
    result["one_explicit_author_clarification_added"]=True
    result["not_byte_identical_story_seed_comparison"]=True
    result["old_original_leak_review_codes"]=old_review["review_findings"]
    result["proactive_unknown_guard_in_first_writer_beat"]=True
    result["new_paid_model_requests"]=budget.calls_reserved
    result["expected_max_model_requests"]=2
    result["no_model_retries"]=True
    result["no_model_or_author_auto_knowledge_commit"]=True
    result["is_not_conclusive_literary_quality_evaluation"]=True
    (OUTPUT/"PILOT_STATUS.json").write_text(json.dumps(
        result,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf8")
    print("WF_POV_REAL_PROSE_PROBE "+json.dumps({
        "status":result["status"],
        "new_model_calls":budget.calls_reserved,
        "old_authored_source_correctly_flagged":True,
        "new_han_chars":result.get("han_chars"),
        "new_model_trace_reviews":len(result.get(
            "model_trace_review_failures",[])),
        "no_user_canon_writes":True,
    },ensure_ascii=False,separators=(",",":")),flush=True)


if __name__=="__main__":
    main()
