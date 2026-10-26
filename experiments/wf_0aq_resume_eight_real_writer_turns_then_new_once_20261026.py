"""0.AQ: immutable 0.AO author source -> real G fifth-turn continuation.

The REAL author already paid for: historical source, chapter plan, six event
plan, four prose turns and four same-author timing decisions. Replaying those
source-locked provider messages is not authoring or an equal-prompt A/B trial.
Do not regenerate or silently edit their text. Validate all wire SHA and
original prompts; any changed instructions are recorded as prompt drift,
not misrepresented as the historical request.

The offline preflight calls no provider and must reach a NEW fifth-turn prompt
through V96/V114/V117 on the old candidate graph before an optional single
live continuation can be authorized. Live uses the same DeepSeek Flash ONLY,
bounded G self-review, and no training, R2, Canon, Railway, main or new memory.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import json,os,re

from experiments import wf_0am_real_history_same_model_g_once_20261026 as history
from experiments import wf_0ao_frozen_real_deepseek_plan_prose_once_20261026 as original
from experiments.wf_0ap_replay_four_real_g_writer_turns_20261026 import (
    EXPECTED_WIRES,
)
from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.writing_assist import AutonomousWriting,InvisibleWritingAssist
from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget
from writerforge.v114_external_story_state import external_temporal_step,require_external_runtime
from writerforge.v117_continuity_trace import make_resume,read_resume
from writerforge.narrative_core import new_graph,read_core_from_resume

OUT=Path("wf_0aq_older_eight_real_prose_restore_20261026")
PRIOR=Path("wf0aq_original_eight_provider_artifact")
PAID_RUN=40259961845
REPLAYED_CALLS=8
MAX_NEW_CALLS=9
OUTPUT_TOKENS_CAP=23000
OFFLINE=os.getenv("WF0AQ_SOURCE_ONLY_STOP_BEFORE_NEW","")=="1"


def h(s):
    return sha256(s if isinstance(s,bytes) else s.encode("utf8")).hexdigest()


def need(condition,code):
    if not condition:raise RuntimeError(code)


def save(path,body):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(body,ensure_ascii=False,sort_keys=True,indent=2),
                    encoding="utf8")


def freeze_previous_paid_eight():
    manifest=json.loads((PRIOR/"STATUS.json").read_text("utf8"))
    need(manifest["format"]=="wf.0ao.reuse-two-real-author-plans-prose-only-g.v1"
         and manifest["new_model_calls"]==REPLAYED_CALLS
         and manifest["status"]=="SOURCE_OR_NEW_AUTHOR_PROSE_HOLD_NO_RETRY"
         and manifest["failure_code"]==
             "WF96_SCENE_TURN_REJECTED_WF96_NONCAUSAL_PARENT_SOURCE_INVALID"
         and manifest["R2_reads"]==manifest["R2_writes"]==
             manifest["Canon_writes"]==0,
         "WF0AQ_ORIGINAL_EIGHT_MANIFEST_INVALID")
    rows=[]
    for i,row in enumerate(manifest["new_provider_events"],1):
        wire=(PRIOR/"provider-originals"/f"new-{i:02d}.json").read_bytes()
        need(row["index"]==i and row["raw_provider_sha256"]==
             EXPECTED_WIRES[i-1]==h(wire) and
             row["provider_wire_saved_before_json_validation"],
             "WF0AQ_IMMUTABLE_REAL_PROVIDER_SHA_INVALID")
        envelope=json.loads(wire)
        need(envelope["model"]=="deepseek-flash" and
             len(envelope["choices"])==1 and
             envelope["choices"][0]["finish_reason"]=="stop",
             "WF0AQ_PREVIOUS_MODEL_OR_FINISH_CHANGED")
        response=json.loads(envelope["choices"][0]["message"]["content"])
        serialized=json.dumps(response,ensure_ascii=False,separators=(",",":"))
        need(h(serialized)==row["decoded_sha256"],
             "WF0AQ_PREVIOUS_DECODED_SHA_DRIFT")
        recorded=json.loads((PRIOR/"new-model-requests"/
                             f"{i:02d}-request.json").read_text("utf8"))
        need(h(recorded["prompt"])==row["prompt_sha256"]==
             recorded["prompt_sha256"] and
             row["max_completion_tokens_reserved"]==recorded["max_tokens"],
             "WF0AQ_PREVIOUS_AUTHOR_PROMPT_NOT_SAME_SOURCE")
        rows.append((serialized,row,recorded))
    return rows,manifest


def same_original_task(old):
    return (
        "【已存在的同一原创写作模型旧文，仍未作者接受】\n"+old+
        "\n【源边界】这是真实旧正文，不是新小说计划："
        "申时末旧信最快明日卯时抵达；听见马蹄不证明信使已经起程，"
        "更不能证明主帅收到。旧人物心理与来源以旧文字为准。"
        "\n【后续原创任务】只写接下来发生的短时段，每个小片段200到350字。"
        "作者自行决定留白、人物动作、选择、是否回头修句；"
        "你可以不修改，无文学分数目标。"
    )


class RealPaidHistoryThenWriter:
    def __init__(self,old_plan,old_plan_event,prior_eight,secret):
        self.old_plan=old_plan
        self.old_plan_event=old_plan_event
        self.old_eight=prior_eight
        self.replayed=0
        self.prompt_comparisons=[]
        self.current=None
        self.new_events=[]
        self.budget=FlashBudget(
            max_calls=MAX_NEW_CALLS,
            max_reserved_output_tokens=OUTPUT_TOKENS_CAP,
            max_total_tokens=150000)
        self.provider=DeepSeekFlashModel(
            api_key=secret,budget=self.budget,timeout_seconds=110,
            on_response_wire=self.save_wire)

    def save_wire(self,wire):
        need(self.current is not None and type(wire) is bytes and
             self.new_events,"WF0AQ_UNEXPECTED_PAID_PROVIDER_WIRE")
        p=OUT/"new-provider-originals"/(
            f"new-{self.new_events[-1]['index']:02d}.json")
        p.parent.mkdir(parents=True,exist_ok=True)
        need(not p.exists(),"WF0AQ_NEW_ORIGINAL_WIRE_CANNOT_OVERWRITE")
        p.write_bytes(wire)
        self.new_events[-1]["wire_sha256"]=h(wire)
        self.new_events[-1]["saved_before_decode"]=True

    def ask(self,packet,*,model,api_base,max_tokens):
        need(model=="deepseek-flash" and
             type(packet.prompt) is str and len(packet.prompt)>50,
             "WF0AQ_NOT_ORIGINAL_MODEL_SOURCE")
        if self.replayed==0:
            same=(h(packet.prompt)==self.old_plan_event["prompt_sha256"]
                  and max_tokens==self.old_plan_event[
                      "max_completion_tokens_reserved"])
            need(same,"WF0AQ_REAL_CHAPTER_PLAN_REQUEST_MISMATCH")
            self.replayed=1
            return self.old_plan
        if self.replayed<=REPLAYED_CALLS:
            i=self.replayed-1
            saved,old,record=self.old_eight[i]
            comparison={
                "original_writer_request":i+1,
                "original_prompt_sha256":old["prompt_sha256"],
                "current_prompt_sha256":h(packet.prompt),
                "original_tokens":old["max_completion_tokens_reserved"],
                "current_tokens":max_tokens,
                "same_prompt_and_budget":(
                    old["prompt_sha256"]==h(packet.prompt) and
                    old["max_completion_tokens_reserved"]==max_tokens),
                "previous_author_body_preserved":True,
                "model_calls_for_replay":0,
            }
            # Preserve both prompts ONLY if changed. Never call an old
            # author response a new, identical-protocol answer if it isn't.
            if not comparison["same_prompt_and_budget"]:
                comparison["historical_response_not_a_new_model_reply"]=True
                comparison["provenance_scope"]="EXISTING_ALREADY_AUTHORED_DRAFT_ONLY"
                save(OUT/"original-vs-current-prompts"/f"{i+1:02d}.json",{
                    **comparison,"old_prompt":record["prompt"],
                    "current_prompt":packet.prompt})
            self.prompt_comparisons.append(comparison)
            self.replayed+=1
            return saved
        if OFFLINE:
            save(OUT/"first-unwritten-turn-prompt.json",{
                "prompt":packet.prompt,"prompt_sha256":h(packet.prompt),
                "max_tokens":max_tokens,
                "old_replayed_author_calls":self.replayed-1,
                "new_provider_calls":0})
            raise RuntimeError("WF0AQ_STOP_BEFORE_UNWRITTEN_FIFTH_TURN_NO_MODEL")
        need(len(self.new_events)<MAX_NEW_CALLS,
             "WF0AQ_PAID_NEW_AUTHOR_CALL_CAP")
        event={
            "index":len(self.new_events)+1,
            "prompt_sha256":h(packet.prompt),
            "max_tokens":max_tokens,
            "saved_before_decode":False,
            "wire_sha256":None,
        }
        self.new_events.append(event)
        save(OUT/"new-model-requests"/f"{event['index']:02d}.json",{
            "prompt":packet.prompt,"prompt_sha256":h(packet.prompt),
            "max_tokens":max_tokens,"writer_is_original_deepseek":True,
            "literary_grade_is_not_a_reward":True})
        self.current=event["index"]
        try:
            obj=self.provider.ask_json(
                role="self_scene_writing",
                system=history.WRITER_SYSTEM,
                user=packet.prompt,max_tokens=max_tokens)
            answer=json.dumps(obj,ensure_ascii=False,separators=(",",":"))
            event["decoded_sha256"]=h(answer)
            event["lossless_format_recovery"]=(
                self.provider.last_response_format_recovery)
            return answer
        finally:
            self.current=None


def main():
    need(not OUT.exists(),"WF0AQ_PRIVATE_REPLAY_OUTPUT_IMMUTABLE")
    OUT.mkdir(parents=True)
    status={
        "format":"wf.0aq.eight-real-author-responses-next-unwritten-turn.v1",
        "status":"NOT_STARTED",
        "old_author_source_sha256":history.EXPECTED_SOURCE_SHA,
        "prior_author_run":PAID_RUN,
        "old_real_model_replies_replayed":0,
        "new_model_calls":0,"maximum_new_model_calls":MAX_NEW_CALLS,
        "old_provider_wires_verified":0,
        "old_source_prose_changed":False,
        "new_narrative_owner_modules":0,
        "R2_reads":0,"R2_writes":0,"Canon_writes":0,
        "Railway_deployments":0,"main_modified":False,
        "author_accepted":False,"literary_improvement_proven":False,
        "existing_graph_only":True,
        "old_prompt_replay_comparisons":[],
        "new_provider_events":[],
    }
    db=None
    author=None
    try:
        need(not any(os.getenv(n) for n in (
            "DISCOVERY_API_KEY","OPENAI_API_KEY","OPENROUTER_API_KEY",
            "WRITERFORGE_R2_ACCOUNT_ID","WRITERFORGE_R2_ACCESS_KEY_ID")),
            "WF0AQ_FORBIDDEN_EXTERNAL_SOURCE_CREDENTIAL")
        old,old_wire=history.verify_old_real_source()
        chapter,turns,_,oldplanmeta,old_plan_replies=(
            original.freeze_original_model_decisions())
        old_eight,old_report=freeze_previous_paid_eight()
        need(h(old)==old_report["original_author_source_sha256"]
             and old_report["original_model_turn_outline_sha256"]==
                 original.TURN_REPLY_SHA
             and old_report["original_model_plan_sha256"]==
                 original.PLAN_REPLY_SHA
             and old_report["old_real_plan_replayed_without_model"] is True
             and old_report["old_real_six_event_plan_preserved"] is True,
             "WF0AQ_OLD_AUTHOR_HISTORY_OR_EVENT_SNAPSHOT_DRIFT")
        status["old_provider_wires_verified"]=len(old_eight)
        save(OUT/"source-identity.json",{
            "old_source_sha256":h(old),"original_model_provider_sha256":old_wire,
            "first_real_plan_sha256":original.PLAN_REPLY_SHA,
            "original_eight_real_provider_sha256s":[e["raw_provider_sha256"]
                                                   for _,e,_ in old_eight],
            "no_model_calls_for_old_source":True})
        require_external_runtime()
        cp=external_temporal_step(old,cast=history.CAST)
        graph=new_graph(project_id=history.PROJECT,scene_id=history.SCENE,
                        chapter_index=0)
        parent=make_resume(
            project_id=history.PROJECT,scene_id=history.SCENE,
            chapter_index=0,checkpoint=cp,unified_narrative_core=graph)
        db=WriterForgeDB(OUT/"local-no-canon-0aq.db")
        sid=history.local_source_only_snapshot(db,old)
        rt=RuntimeEngine()
        rt.enter_write(sid)
        assist=InvisibleWritingAssist(
            db,rt,history.PROJECT,history.SCENE,
            "继续原DeepSeek的边关历史小说事件，并保留真正未知的传令状态。",
            model="deepseek-flash",api_base="https://api.deepseek.com/v1",
            source_genre="古代白话")
        key=os.getenv("DEEPSEEK_API_KEY","wf0aq-no-model-key")
        author=RealPaidHistoryThenWriter(
            chapter,old_plan_replies[0][1],old_eight,key)
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=author.ask):
            result=AutonomousWriting(assist).run(
                outline=same_original_task(old),
                chapter_goals=history.GOALS,
                draft_mode="continuity_guard",
                resume_story_checkpoint=parent,
                frozen_turn_outlines=(turns,),
                narrative_memory_backend="local",
                self_edit_rounds=1,
                self_edit_timing="ai_decides",
                reader_first_self_review=False,
                output_dir=OUT/"g-source-authored-continuation")
        chapter=result["chapters"][0]
        prose=Path(chapter["candidate"]).read_text("utf8")
        resume=json.loads(Path(chapter[
            "v117_unreviewed_text_trace_resume"]).read_text("utf8"))
        read_resume(resume,project_id=history.PROJECT,scene_id=history.SCENE)
        core=read_core_from_resume(resume,project_id=history.PROJECT,
                                   scene_id=history.SCENE)
        link=core["source_temporal_link"]
        need(link["whole_chapter_sha256"]==h(prose)
             and link["source_assembly_verified"] is True
             and link["ancestry_fully_verified"] is True
             and resume["author_accepted"] is False
             and core["parent_sha256"]==graph["receipt_sha256"],
             "WF0AQ_REAL_G_SOURCE_CHAIN_NOT_SIGNED")
        status.update({
            "status":"UNACCEPTED_REAL_G_CHAPTER_COMPLETED_SOURCE_REVIEW_SEPARATE",
            "complete_candidate_prose_sha256":h(prose),
            "model_previous_turn_rewinds":result.get(
                "wf_self_edit_previous_turn_rewinds",0),
            "new_graph_sha256":core["receipt_sha256"],
            "new_resume_sha256":resume["receipt_sha256"],
            "author_accepted":False,
        })
    except Exception as ex:
        error=str(ex)
        status["status"]=(
            "EIGHT_REPLAYED_THROUGH_PRE_MODEL_STOP"
            if OFFLINE and error=="WF0AQ_STOP_BEFORE_UNWRITTEN_FIFTH_TURN_NO_MODEL"
            else "OLD_SOURCE_OR_NEW_WRITER_HELD_WITH_ORIGINALS")
        status["failure_code"]=(
            error if re.fullmatch(r"WF[A-Z0-9_:\-]{3,180}",error)
            else type(ex).__name__+":NO_RETRY")
    finally:
        if db is not None:db.close()
        if author is not None:
            status["old_real_model_replies_replayed"]=author.replayed
            status["old_prompt_replay_comparisons"]=author.prompt_comparisons
            status["new_model_calls"]=author.budget.calls_reserved
            status["new_provider_events"]=author.new_events
        save(OUT/"STATUS.json",status)
        print("WF0AQ_SOURCE_FIRST "+json.dumps({
            "status":status["status"],
            "old_model_replies_replayed":status["old_real_model_replies_replayed"],
            "previous_real_provider_wires_verified":
                status["old_provider_wires_verified"],
            "new_model_calls":status["new_model_calls"],
            "signed_new_prose":status.get("complete_candidate_prose_sha256"),
            "previous_turn_rewinds":status.get("model_previous_turn_rewinds"),
            "failure":status.get("failure_code"),
        },ensure_ascii=False),flush=True)
    ok=("EIGHT_REPLAYED_THROUGH_PRE_MODEL_STOP" if OFFLINE
        else "UNACCEPTED_REAL_G_CHAPTER_COMPLETED_SOURCE_REVIEW_SEPARATE")
    if status["status"]!=ok:
        raise RuntimeError("WF0AQ_OLD_SOURCE_G_REAL_WRITER_HOLD")


if __name__=="__main__":
    main()
