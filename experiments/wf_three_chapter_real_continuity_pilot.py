"""Three ACTUAL consecutive new novel chapters, WF writes all their prose.

A single DeepSeek Flash + existing AutonomousWriting.continuity_guard:
  new synthetic published neutral software bridge (NO literary corpus),
  one source-anchored author-confirmed chapter-zero/one factual seed,
  three distinct one-chapter runs linked by each real V117 unified resume.
No new memory/skill, no external critic, no revisions, no retry, no Railway,
no canon write. Never mistake model plan/effect quotes for actual payoff.
Each story chapter: 1 model-generated chapter plan, 1 model-generated
two-beat plan, 2 ORIGINAL model-generated prose segments. Max 12 requests.
All provider wires and decoded originals persist BEFORE host validation.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import os
import re
import time

from experiments.v111_peer.neutral_bridge import fresh_neutral_published_snapshot
from experiments.wf_real_self_scene_diagnostics import SYSTEMS, source_event
from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget
from writerforge.writing_assist import AutonomousWriting,InvisibleWritingAssist
from writerforge.v114_external_story_state import (
    require_external_runtime,external_temporal_step,
)
from writerforge.narrative_core import (
    new_graph,advance_graph,record_chapter_memory,read_core_from_resume,
    recall_original,
)
from writerforge.v117_continuity_trace import make_resume,read_resume

OUTPUT=Path("wf_three_chapter_real_results")
PROJECT="wf-real-three-chapter-original-pilot-20261023"
STREAM="riverside-old-printshop"
MODEL="deepseek-flash"
SOURCE=(
    "北塘镇旧印坊要在入冬前拆掉后院库房。"
    "陶筠守着一套旧铅活字模，已经把字模箱搬到二楼窗下，"
    "但楼梯第四级踏板裂了。"
    "简洛捡到一张盖着模糊蓝印的运货单，上面只有“灰袋三十”，"
    "没有收货地点；他没告诉陶筠。"
    "采访记者闻遥刚拿到匿名举报信，指控印坊夜里运走污染土；"
    "她没有证据证明信是真的。"
    "镇里的封院通知写的是明日午后，尚未有任何人来验库。"
    "陶筠上周答应工友，封院以前会把工资账公开给每个人看。"
    "陶筠担心工人领不到工资，也怕旧铅活字被当废料毁掉。"
    "简洛还有一个等学费的妹妹，不愿因一份不明来历的运货单丢掉工作。"
    "闻遥坚持在报道前找到两份互相独立的证据。"
    "印坊东门木锁从上个夜班起就卡住，但还没有人说明原因。"
)
CAST=("陶筠","简洛","闻遥")
GENRE="现实悬疑"
OUTLINE=(
    "原创小说《北塘旧印坊》。连续三个新章节、每章约两个自然事件。"
    "工人工资、旧铅活字、无日期运输凭单与一封匿名举报信形成现实利益冲突。"
    "让人物自行决定是否相信他人、公开或隐瞒线索、承担何种代价，"
    "不指定幕后真相或最终好坏人；读者不应在没有来源时早于角色得知确定事实。"
    "小说要有日常质地、具体行动与自然心理，不要连续三章只讨论计划。"
)
CHAPTER_GOALS=(
    "封院之前，陶筠与简洛清点搬迁物件，闻遥来印坊询问举报信，三人可以拒绝合作或改变调查方向。",
    "接续上一章真正写出的行动与代价，在封院期限逼近时，陶筠、简洛和闻遥分别根据已知事实作出新选择。",
    "延续前两章实际发生的物件与关系变化，封院当天三个人面对工人生计和不确证据，作有代价的决定。",
)
EVENTS=(
    ("THREAD_OPEN",
     "陶筠上周答应工友，封院以前会把工资账公开给每个人看。",
     {"thread_id":"wage-account-promise","thread_kind":"PROMISE",
      "owner":"陶筠","target":"简洛",
      "premise":"公开工资账的承诺尚未由真实正文证实兑现",
      "truth_scope":"AUTHOR_ASSERTED"}),
    ("CHARACTER_REFLECT",
     "陶筠担心工人领不到工资，也怕旧铅活字被当废料毁掉。",
     {"actor":"陶筠","dimension":"fear",
      "value":"工人领不到工资也怕活字被毁",
      "evidence_scope":"NARRATED_INNER"}),
    ("CHARACTER_REFLECT",
     "闻遥坚持在报道前找到两份互相独立的证据。",
     {"actor":"闻遥","dimension":"value",
      "value":"报道前找到两份独立证据",
      "evidence_scope":"NARRATED_INNER"}),
)
TOKENS=(650,1450,1450,1450)
STAGES=("CHAPTER_PLAN","SELF_BEAT_PLAN","PROSE_1","PROSE_2")
MAX_CALLS=12
MAX_RESERVED=3*sum(TOKENS)
MAX_JSON_WIRE=2*1024*1024


def h(value):
    return sha256(value.encode("utf8") if type(value) is str
                  else value).hexdigest()


def persist_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(
        json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2),
        encoding="utf8")


def structural_preflight():
    assert len(CHAPTER_GOALS)==3 and len(CAST)==3
    assert 12==MAX_CALLS and MAX_RESERVED==15000
    assert len(SOURCE)<2200 and len(OUTLINE)<1800
    assert len(set(CAST))==3
    assert all(name in SOURCE for name in CAST)
    assert not any(name in SOURCE for name in ("沈砚","唐蜃","叶青梧"))
    assert "没有证据证明信是真的" in SOURCE
    assert "没有收货地点" in SOURCE
    assert all(SOURCE.count(event[1])==1 for event in EVENTS)
    return True


def main():
    structural_preflight()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise RuntimeError("WF_REAL_THREE_EXISTING_MODEL_KEY_MISSING")
    require_external_runtime()
    OUTPUT.mkdir(parents=True,exist_ok=False)
    source_path=OUTPUT/"CHAPTER_001_ORIGINAL_SEED.md"
    source_path.write_text(SOURCE,encoding="utf8")
    # Neutral fixture meets the published SOURCE gate only;
    # it is NOT evidence of actual learned literary methods.
    snapshot=fresh_neutral_published_snapshot(
        OUTPUT/"neutral-writer-bridge.sqlite")
    db=WriterForgeDB(OUTPUT/"neutral-writer-bridge.sqlite")
    rt=RuntimeEngine()
    rt.enter_write(snapshot)
    db.conn.execute(
        "UPDATE xuehai_entries SET genre=? WHERE work_id=?",
        (GENRE,"v111-neutral-fixture"))
    db.conn.commit()
    graph=new_graph(project_id=PROJECT,scene_id=STREAM)
    graph=advance_graph(
        graph,project_id=PROJECT,scene_id=STREAM,
        chapter_index=1,prose=SOURCE,
        events=[source_event(SOURCE,n,event)
                for n,event in enumerate(EVENTS,1)])
    graph=record_chapter_memory(
        graph,project_id=PROJECT,scene_id=STREAM,chapter_index=1,
        source_path=str(source_path),prose=SOURCE)
    prior_temporal=external_temporal_step(SOURCE,cast=CAST)
    resume=make_resume(
        project_id=PROJECT,scene_id=STREAM,chapter_index=1,
        checkpoint=prior_temporal,unified_narrative_core=graph)
    persist_json(OUTPUT/"CHAPTER_001_SEED_RESUME.json",resume)
    budget=FlashBudget(
        max_calls=MAX_CALLS,
        max_reserved_output_tokens=MAX_RESERVED,
        max_total_tokens=150000)
    invocation={"chapter":0,"phase":None,"stage":None}
    attempts=[]
    chapters=[]
    start=time.monotonic()
    status={
        "format":"wf.experiment.source-first-three-real-chapters.v1",
        "source_initial_sha256":h(SOURCE),
        "genre":GENRE,"project_id":PROJECT,"scene_id":STREAM,
        "provider_model":MODEL,"scenario_is_new_synthetic_fiction":True,
        "original_user_novels_used":False,
        "neutral_bridge_is_not_real_literary_training":True,
        "actual_full_WF_continuity_guard":True,
        "core_memory_owner":"UNIFIED_NARRATIVE_CORE",
        "max_provider_calls":MAX_CALLS,
        "max_reserved_output_tokens":MAX_RESERVED,
        "rewrites":0,"provider_retries":0,
        "literary_progression_mode":"baseline",
        "chapter_count_completed":0,
        "status":"NOT_STARTED",
        "canon_writes":0,
        "railway_deployed":False,
    }

    def wire_sink(raw):
        if (type(raw) is not bytes or not 0<len(raw)<=MAX_JSON_WIRE or
            invocation["chapter"] not in (2,3,4) or
            invocation["stage"] not in STAGES):
            raise RuntimeError("WF_REAL_THREE_ORIGINAL_WIRE_INVALID")
        directory=OUTPUT/f"CHAPTER_{invocation['chapter']:03d}"/"raw_provider"
        directory.mkdir(parents=True,exist_ok=True)
        destination=directory/f"{invocation['stage']}-wire.json"
        with destination.open("xb") as out:
            out.write(raw)
        attempts[-1]["provider_wire_sha256"]=h(raw)
        attempts[-1]["wire_saved_before_decoding"]=True
        attempts[-1]["stage"]="WIRE_SAVED_BEFORE_VALIDATION"

    model=DeepSeekFlashModel(
        budget=budget,timeout_seconds=120,
        on_response_wire=wire_sink)
    helper=InvisibleWritingAssist(
        db,rt,PROJECT,STREAM,OUTLINE,
        model=MODEL,api_base="https://api.deepseek.com",
        source_genre=GENRE)

    def adapter(packet,*,model,api_base,max_tokens,**kwargs):
        if (model!=MODEL or api_base!="https://api.deepseek.com" or
            kwargs or invocation["stage"] not in STAGES or
            len(attempts)>=MAX_CALLS):
            raise RuntimeError("WF_REAL_THREE_PROVIDER_ROUTING_CHANGED")
        stage=invocation["stage"]
        slot=STAGES.index(stage)
        if TOKENS[slot]!=max_tokens:
            raise RuntimeError("WF_REAL_THREE_CALL_SCHEDULE_CHANGED")
        n=len(attempts)+1
        item={
            "slot":n,"chapter_index":invocation["chapter"],
            "stage_name":stage,
            "prompt_sha256":h(packet.prompt),
            "max_tokens":max_tokens,
            "model_reply":"NOT_YET_RECEIVED",
        }
        attempts.append(item)
        system=(SYSTEMS["PROSE"] if slot in (2,3)
                else SYSTEMS[stage])
        original=model.ask_json(
            role="self_scene_writing",system=system,
            user=packet.prompt,max_tokens=max_tokens)
        payload=json.dumps(original,ensure_ascii=False,
                           separators=(",",":"))
        original_path=(OUTPUT/f"CHAPTER_{invocation['chapter']:03d}"/
                       "raw_provider"/f"{stage}-decoded-original.json")
        with original_path.open("x",encoding="utf8") as out:
            out.write(payload)
        item.update({
            "model_reply":"DECODED_ORIGINAL_SAVED_BEFORE_WF_VALIDATION",
            "decoded_response_sha256":h(payload),
            "exact_json_tail_recovery":model.last_response_format_recovery,
        })
        return payload

    def progress(index,total,stage):
        # Observable boundaries only. The original fixed source is never
        # rewritten between runs by a fabricated human acceptance.
        if index!=1 or total!=1:
            raise RuntimeError("WF_REAL_THREE_EXPECTED_ONE_CHAPTER_PER_RUN")
        if stage=="planning":
            invocation["phase"]="planning"
            invocation["stage"]="CHAPTER_PLAN"
        elif stage=="drafting":
            invocation["phase"]="drafting"
            invocation["stage"]="SELF_BEAT_PLAN"
        elif stage=="saved":
            invocation["phase"]="saved"
            invocation["stage"]=None

    # Capture exact turn name without editing host. The first planning call
    # occurs on planning phase, second upon drafting phase, third/fourth
    # distinguish by prior attempts already saved for this chapter.
    def stage_adapter(packet,*,model,api_base,max_tokens,**kwargs):
        slot=len([x for x in attempts
                  if x["chapter_index"]==invocation["chapter"]])
        if slot>=4:
            raise RuntimeError("WF_REAL_THREE_EXCESS_CHAPTER_MODEL_REQUESTS")
        invocation["stage"]=STAGES[slot]
        return adapter(packet,model=model,api_base=api_base,
                       max_tokens=max_tokens,**kwargs)

    try:
        from unittest.mock import patch
        for chapter_index,goal in enumerate(CHAPTER_GOALS,2):
            # One-chapter run is necessary: the upstream WF segmented host
            # has an intentional two-chapter-per-job bound. Never loosen it.
            invocation.update({"chapter":chapter_index,
                               "stage":"CHAPTER_PLAN"})
            chapter_dir=OUTPUT/f"CHAPTER_{chapter_index:03d}"
            chapter_dir.mkdir(parents=True,exist_ok=False)
            try:
                with patch("writerforge.writing_assist.local_chat_completion",
                           side_effect=stage_adapter):
                    result=AutonomousWriting(helper).run(
                        outline=OUTLINE,chapter_goals=[goal],
                        output_dir=chapter_dir/"candidate_history",
                        draft_mode="continuity_guard",
                        resume_story_checkpoint=resume,
                        literary_progression_mode="baseline",
                        progress=progress)
                report=result["chapters"][0]
                candidate=Path(report["candidate"])
                prose=candidate.read_text(encoding="utf8")
                if len(prose)<150:
                    raise RuntimeError("WF_REAL_THREE_ACTUAL_BODY_TOO_SHORT")
                copied=chapter_dir/"ORIGINAL_WF_CANDIDATE.md"
                with copied.open("x",encoding="utf8") as out:
                    out.write(prose)
                trace=Path(report["turn_evidence"]).read_text(encoding="utf8")
                v117=Path(report["v117_unreviewed_text_trace_resume"])
                recovered=json.loads(v117.read_text(encoding="utf8"))
                from writerforge.v117_continuity_trace import read_resume
                read_resume(recovered,project_id=PROJECT,scene_id=STREAM)
                core=read_core_from_resume(
                    recovered,project_id=PROJECT,scene_id=STREAM)
                if (core["chapter_index"]!=chapter_index or
                    core["memory"]["last_recorded_chapter"]!=chapter_index or
                    core["canon_writes"]!=0):
                    raise RuntimeError("WF_REAL_THREE_CHAPTER_RESUME_BAD")
                original=recall_original(
                    core,project_id=PROJECT,scene_id=STREAM,
                    chapter_index=chapter_index)
                if original!=prose:
                    raise RuntimeError("WF_REAL_THREE_REREAD_ORIGINAL_CHANGED")
                # Cross-chapter relationship/scene states are OPEN until
                # actually author-reviewed; never claim auto payoff.
                trace_data=json.loads(trace)
                info={
                    "chapter_index":chapter_index,
                    "story_chapter_index_after_seed":chapter_index,
                    "prose_sha256":h(prose),
                    "han_chars":sum("\u3400"<=c<="\u9fff" for c in prose),
                    "prose_codepoints":len(prose),
                    "goal_sha256":h(goal),
                    "model_response_slots":[item["slot"] for item in attempts
                                            if item["chapter_index"]==chapter_index],
                    "new_model_requests":4,
                    "unified_core_receipt_sha256":core["receipt_sha256"],
                    "unified_memory_hot":len(core["memory"]["hot"]),
                    "unified_memory_warm":len(core["memory"]["warm"]),
                    "unified_memory_cold":core["memory"]["cold_count"],
                    "source_reread_byte_equal":True,
                    "model_trace_review_count":len(trace_data.get(
                        "unified_model_trace_review_failures",[])),
                    "scene_delivery_reviews":report.get(
                        "unified_scene_function_review_findings",[]),
                    "character_self_decision_independently_verified":False,
                    "literary_quality_independently_verified":False,
                    "all_chapters_remain_candidates":True,
                    "canon_writes":0,
                }
                persist_json(chapter_dir/"CHAPTER_STATUS.json",info)
                chapters.append(info)
                status["chapter_count_completed"]=len(chapters)
                resume=recovered
                persist_json(chapter_dir/"V117_ORIGINAL_RESUME.json",resume)
                # The old actual source itself is the following chapter's
                # input; never feed a model-made SUMMARY as already true.
                print("WF_REAL_THREE_CHAPTER_SAVED "+
                      json.dumps({
                          "chapter":chapter_index,
                          "prose_sha256":info["prose_sha256"],
                          "han_chars":info["han_chars"],
                          "model_trace_reviews":info["model_trace_review_count"],
                          "real_source_reread":True,
                      },ensure_ascii=False,separators=(",",":")),flush=True)
            except Exception as error:
                reason=str(error)
                if not re.fullmatch(r"(?:WF|WFCORE)[A-Z0-9_:\-,.]{4,150}",reason):
                    reason=type(error).__name__+":REAL_CHAPTER_FAILED"
                status.update({
                    "status":"CHAPTER_FAILED_NO_MODEL_RETRY",
                    "first_failed_chapter":chapter_index,
                    "failure_code":reason,
                })
                break
        else:
            status["status"]="THREE_CHAPTERS_ORIGINAL_CANDIDATES_SAVED"
        status["real_written_chapters"]=chapters
    finally:
        status["actual_model_call_count"]=budget.calls_reserved
        status["actual_provider_usage"]=budget.public_receipt()
        status["model_call_receipts"]=attempts
        status["elapsed_seconds"]=round(time.monotonic()-start,2)
        status["no_unreviewed_story_promoted_to_canon"]=True
        status["accepted_prose_rows"]=db.conn.execute(
            "SELECT COUNT(*) FROM accepted_prose").fetchone()[0]
        persist_json(OUTPUT/"STATUS.json",status)
        print("WF_REAL_THREE_FINAL_STATUS "+json.dumps({
            "result":status["status"],"chapters_completed":
                status["chapter_count_completed"],
            "real_model_calls":budget.calls_reserved,
            "no_auto_retry":True,
            "no_canon_writes":status["accepted_prose_rows"]==0,
            "script_is_not_literary_evaluator":True,
        },ensure_ascii=False,separators=(",",":")),flush=True)
        db.close()
    return 0


if __name__=="__main__":
    main()
