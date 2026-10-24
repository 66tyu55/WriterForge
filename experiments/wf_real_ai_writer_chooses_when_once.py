"""Actual WriterForge AI-decided look-back TIMING, same model, no mock prose.

Runs WriterForge's actual G continuity writer with one voluntary self-revision
chance after EACH original model-created scene turn. The same DeepSeek Flash
writes and makes its own decision: KEEP, DELETE, REVISE or REPLACE_SCENE.
We never force an edit for a green score, never retry provider failure, and
never pretend model self-judgment proves literary quality.

Only the private synthetic psychology seed from existing genuine evidence
is used. Original model wire + before/after drafts and failed proposals are
attached to GitHub Actions, never Canon, main, Railway, user's corpus or R2.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os
import re

from experiments.v111_peer.neutral_bridge import fresh_neutral_published_snapshot
from experiments.wf_real_self_scene_diagnostics import (
    CASES, SYSTEMS, TOKENS, source_event,h,dump,
)
from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget
from writerforge.writing_assist import AutonomousWriting,InvisibleWritingAssist
from writerforge.narrative_core import new_graph,advance_graph,record_chapter_memory
from writerforge.v114_external_story_state import (
    require_external_runtime,external_temporal_step,
)
from writerforge.v117_continuity_trace import make_resume

CASE=CASES["psychology"]
OUTPUT=Path("wf_real_writer_chooses_when")
PROJECT="wf-voluntary-original-self-editor-test"
SCENE="old-letter-self-editor"
MAX_CALLS=8
MAX_RESERVED=650+1450+2*1450+2*600+2*1800


def run():
    require_external_runtime()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise RuntimeError("WF_REAL_SELF_EDIT_EXISTING_MODEL_KEY_MISSING")
    OUTPUT.mkdir(parents=True,exist_ok=False)
    seed=CASE["seed"]
    (OUTPUT/"source-first-chapter.md").write_text(seed,encoding="utf8")
    budget=FlashBudget(
        max_calls=MAX_CALLS,max_reserved_output_tokens=MAX_RESERVED,
        max_total_tokens=150000)
    calls=[]
    state={"plans":0,"prose":0,"self_edit":0,"moments":0}
    def save_wire(raw):
        if (not isinstance(raw,bytes) or len(raw)>2*1024*1024 or
            not calls):
            raise RuntimeError("WF_REAL_SELF_EDIT_PROVIDER_WIRE_BAD")
        record=calls[-1]
        (OUTPUT/f"{len(calls):02d}-{record['stage']}-wire.json").write_bytes(raw)
        record["original_wire_sha256"]=h(raw)
    client=DeepSeekFlashModel(
        budget=budget,timeout_seconds=120,on_response_wire=save_wire)
    status={
        "format":"wf.experiment.actual-writer-internal-self-edit.v1",
        "same_model_writes_and_self_edits":"deepseek-flash",
        "max_provider_calls":MAX_CALLS,
        "max_reserved_output_tokens":MAX_RESERVED,
        "no_automatic_model_retry":True,
        "self_edit_rounds_per_prose_turn":1,
        "ai_owns_look_back_decision":True,
        "timing_mode":"ai_decides",
        "literary_quality_unverified":True,
        "all_canon_writes":0,
        "old_A_to_F_modes_unchanged":True,
        "user_novels_not_used":True,
        "status":"NOT_STARTED",
    }
    def adapter(packet,*,model,api_base,max_tokens,**kw):
        if (model!="deepseek-flash" or
            api_base!="https://api.deepseek.com" or kw or
            len(calls)>=MAX_CALLS):
            raise RuntimeError("WF_REAL_SELF_EDIT_UNEXPECTED_PROVIDER")
        if max_tokens==650:
            if state["plans"]!=0:
                raise RuntimeError("WF_REAL_SELF_EDIT_REPEAT_CHAPTER_PLAN")
            stage="CHAPTER_PLAN"
            state["plans"]=1
            system=SYSTEMS["CHAPTER_PLAN"]
        elif max_tokens==1450 and state["plans"]==1 and (
                state["prose"]==0 and state["self_edit"]==0 and
                not any(x["stage"]=="SELF_BEAT_PLAN" for x in calls)):
            stage="SELF_BEAT_PLAN"
            system=SYSTEMS["SELF_BEAT_PLAN"]
        elif max_tokens==1450 and state["plans"]==1:
            state["prose"]+=1
            if state["prose"]>2:
                raise RuntimeError("WF_REAL_SELF_EDIT_MORE_THAN_TWO_PROSE_TURNS")
            stage="PROSE_"+str(state["prose"])
            system=SYSTEMS["PROSE"]
        elif max_tokens==600:
            state["moments"]+=1
            if state["moments"]>2:
                raise RuntimeError("WF_REAL_AI_MOMENT_MORE_THAN_TWO_DECISIONS")
            stage="AI_MOMENT_"+str(state["moments"])
            system=(
                "你是与刚才写小说完全相同的作者模型，不是打分器。"
                "你此时自己选择继续写，或者回头修自己写过的原文。"
                "严格按提示输出 JSON：MOVE_ON 或 LOOK_BACK_NOW，"
                "写明真正原文里你觉得不合适的片段、为什么现在改、"
                "不改将影响什么、想保留的读者感受。"
                "小说的情节判断完全由你作出，WF 只验实际引用。"
            )
        elif max_tokens==1800:
            state["self_edit"]+=1
            if state["self_edit"]>2:
                raise RuntimeError("WF_REAL_SELF_EDIT_MORE_THAN_TWO_REVIEWS")
            stage="SELF_EDIT_"+str(state["self_edit"])
            system=(
                "你仍是正在写作的同一个小说作者。"
                "现在读自己刚写完的文字，决定真正保留、删除一句、修改一段"
                "或推翻重写本场景。只输出用户提示中约定的严格 JSON。"
                "不要为了凑修改强行改变好作品，也不能为获得高评分作弊。"
                "选择 KEEP、DELETE、REVISE、REPLACE_SCENE，"
                "标注原文源码 SHA 与实际字符偏移。"
            )
        else:
            raise RuntimeError("WF_REAL_SELF_EDIT_WRONG_MODEL_BUDGET_OR_ORDER")
        record={
            "stage":stage,"max_tokens":max_tokens,
            "prompt_sha256":h(packet.prompt),
            "source_prompt_preserved":True,"provider_status":"REQUESTED",
        }
        calls.append(record)
        value=client.ask_json(
            role="self_scene_writing",system=system,
            user=packet.prompt,max_tokens=max_tokens)
        raw=json.dumps(value,ensure_ascii=False,separators=(",",":"))
        (OUTPUT/f"{len(calls):02d}-{stage}-original-model.json").write_text(
            raw,encoding="utf8")
        record["provider_status"]="RECEIVED"
        record["decoded_response_sha256"]=h(raw)
        return raw

    with TemporaryDirectory(prefix="wf-real-author-self-editor-") as td:
        root=Path(td)
        snap=fresh_neutral_published_snapshot(root/"neutral.sqlite")
        db=WriterForgeDB(root/"neutral.sqlite")
        try:
            db.conn.execute(
                "UPDATE xuehai_entries SET genre=? WHERE work_id=?",
                (CASE["genre"],"v111-neutral-fixture"))
            db.conn.commit()
            rt=RuntimeEngine()
            rt.enter_write(snap)
            graph=new_graph(project_id=PROJECT,scene_id=SCENE)
            graph=advance_graph(
                graph,project_id=PROJECT,scene_id=SCENE,
                chapter_index=1,prose=seed,
                events=[source_event(seed,i,event)
                        for i,event in enumerate(
                            CASE.get("event_quotes",()),1)])
            graph=record_chapter_memory(
                graph,project_id=PROJECT,scene_id=SCENE,
                chapter_index=1,source_path=str(
                    OUTPUT/"source-first-chapter.md"),prose=seed)
            state0=external_temporal_step(
                seed,cast=("沈砚","唐蜃","叶青梧"))
            resume=make_resume(
                project_id=PROJECT,scene_id=SCENE,chapter_index=1,
                checkpoint=state0,unified_narrative_core=graph)
            helper=InvisibleWritingAssist(
                db,rt,PROJECT,SCENE,CASE["goal"],
                model="deepseek-flash",api_base="https://api.deepseek.com",
                source_genre=CASE["genre"])
            try:
                with patch("writerforge.writing_assist.local_chat_completion",
                           side_effect=adapter):
                    result=AutonomousWriting(helper).run(
                        outline=CASE["outline"]+
                                "\n此前实际已写源事实："+seed,
                        chapter_goals=[CASE["goal"]],
                        output_dir=root/"private-fresh-candidates",
                        draft_mode="continuity_guard",
                        resume_story_checkpoint=resume,
                        literary_progression_mode="baseline",
                        self_edit_rounds=1,
                        self_edit_timing="ai_decides")
                chapter=result["chapters"][0]
                prose=Path(chapter["candidate"]).read_text("utf8")
                (OUTPUT/"FINAL_UNACCEPTED_WF_PROSE.md").write_text(
                    prose,encoding="utf8")
                evidence=json.loads(Path(chapter["turn_evidence"]).read_text(
                    encoding="utf8"))
                notes=evidence["wf_self_edit_receipts"]
                moments=evidence["wf_ai_self_review_moment_receipts"]
                status.update({
                    "status":"WF_REAL_SELF_EDIT_CANDIDATE_SAVED",
                    "final_prose_sha256":h(prose),
                    "han_characters":sum("\u3400"<=c<="\u9fff" for c in prose),
                    "self_edit_model_calls":result["wf_self_edit_model_calls"],
                    "ai_moment_decisions":[
                        m.get("decision") for m in moments],
                    "ai_moment_model_calls":sum(
                        m.get("model_calls",0) for m in moments),
                    "self_edit_decisions":[
                        [row.get("status") for row in v["rounds"]]
                        for v in notes],
                    "source_review_codes":chapter.get(
                        "unified_scene_function_review_findings",[]),
                    "raw_planning_prose_preserved":True,
                })
                (OUTPUT/"SELF_EDIT_TURN_EVIDENCE.json").write_text(
                    json.dumps(notes,ensure_ascii=False,indent=2),
                    encoding="utf8")
                (OUTPUT/"AI_WRITER_WHEN_AND_WHY_RECEIPTS.json").write_text(
                    json.dumps(moments,ensure_ascii=False,indent=2),
                    encoding="utf8")
                all_private_edit_dirs=sorted(
                    list((root/"private-fresh-candidates").glob(
                        "auto-*/chapter-*-turn-*-self-edits"))+
                    list((root/"private-fresh-candidates").glob(
                        "auto-*/chapter-*-turn-*-ai-moment")))
                for i,folder in enumerate(all_private_edit_dirs,1):
                    target=OUTPUT/f"PRIVATE_WRITER_DRAFTS_{i:02d}"
                    target.mkdir()
                    for file in folder.iterdir():
                        if file.is_file():
                            (target/file.name).write_bytes(file.read_bytes())
            except Exception as exc:
                reason=str(exc)
                if not re.fullmatch(r"[A-Z][A-Z0-9_:\-,.]{3,200}",reason):
                    reason=type(exc).__name__+":SELF_EDIT_LIVE_RUN_FAILED"
                status.update({
                    "status":"WF_REAL_SELF_EDIT_RUN_REJECTED",
                    "error_code":reason})
        finally:
            status["actual_provider_calls"]=budget.calls_reserved
            status["provider_call_receipts"]=calls
            status["provider_usage"]=budget.public_receipt()
            status["accepted_prose_rows"]=db.conn.execute(
                "SELECT COUNT(*) FROM accepted_prose").fetchone()[0]
            status["trained_literary_weights_updated"]=False
            dump(OUTPUT/"STATUS.json",status)
            print("WF_REAL_SELF_EDITOR_STATUS "+json.dumps({
                "status":status["status"],
                "model_calls":budget.calls_reserved,
                "self_edit_model_calls":status.get("self_edit_model_calls",0),
                "ai_moment_decisions":status.get("ai_moment_decisions",[]),
                "self_edit_decisions":status.get("self_edit_decisions",[]),
                "candidate_saved":(
                    status["status"]=="WF_REAL_SELF_EDIT_CANDIDATE_SAVED"),
                "no_canon":status["accepted_prose_rows"]==0,
                "quality_unverified":True,
            },ensure_ascii=False,separators=(",",":")),flush=True)
            db.close()


if __name__=="__main__":
    run()
