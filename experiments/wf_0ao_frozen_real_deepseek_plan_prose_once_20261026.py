"""0.AO: REAL DeepSeek G prose on the ORIGINAL already-paid 0.AM event plan.

NO second paid outline. Author's original 0.AM chapter plan and 6-beat scene
plan came from real paid provider wires in Actions 40257489862. Verify both
envelopes, raw SHA, original prompts, decoded SHA and full original 0.AH
source BEFORE any new provider request. G uses its existing frozen outline
argument; the optional "decision" craft tag may be removed by the existing
source-quoted compatibility routine only. Author goals, IDs, role choices and
parent links must not change. The first planning ask in this exact G task is
supplied by ORIGINAL real DeepSeek answer with matching request SHA.

All NEW prose, self-review decisions, and any V119 revisions come from the
same live DeepSeek Flash provider, not WriterForge or this experiment. This
script NEVER silently corrects authored prose/trace, creates Canon or a
second memory owner, or retries model calls on failure.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import json,os,re

from experiments import wf_0am_real_history_same_model_g_once_20261026 as previous
from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.writing_assist import (
    AutonomousWriting,InvisibleWritingAssist,
    _normalize_optional_model_craft_labels)
from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget
from writerforge.v96_causal_turns import parse_turn_outline
from writerforge.v114_external_story_state import external_temporal_step,require_external_runtime
from writerforge.v117_continuity_trace import make_resume,read_resume
from writerforge.narrative_core import new_graph,read_core_from_resume

OUT=Path("wf_0ao_frozen_original_plan_real_G_prose_20261026")
PAID_PLAN=Path("wf0ao_old_real_0am_failed_plan")
ORIGINAL_MODEL_RUN=40257489862
PLAN_REPLY_SHA=("4421a0bda133991d865fb0b9bf8727beaba137a5587e23f293ccdf2da3c9ac45")
TURN_REPLY_SHA=("193e2aae6a937e56c54894c9deed24996abf3827ee10e9b38ea8464f7e736bea")
MAX_NEW_CALLS=16
MAX_RESERVED_OUTPUT_TOKENS=40000


def h(text):
    return sha256(text if type(text) is bytes else text.encode("utf8")).hexdigest()


def require(ok,code):
    if not ok:raise RuntimeError(code)


def save(path,doc):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2),
                    encoding="utf8")


def freeze_original_model_decisions():
    doc=json.loads((PAID_PLAN/"STATUS.json").read_text("utf8"))
    require(doc["format"]=="wf.0am.single-model-original-history-full-g-once.v1"
            and doc["status"]=="SOURCE_OR_WRITER_FAILED_SAFELY_NO_RETRY"
            and doc["error_code"]==
                "WF96_SCENE_TURN_REJECTED_WF96_CAUSAL_PARENT_NOT_PRIOR_EXPLICIT_ACTION"
            and doc["source_sha256"]==previous.EXPECTED_SOURCE_SHA
            and doc["model_calls"]==2
            and doc["R2_reads"]==doc["R2_writes"]==doc["canon_writes"]==0,
            "WF0AO_ORIGINAL_TWO_PAID_REPLIES_MANIFEST_CHANGED")
    replies=[]
    for idx,expected_sha in ((1,PLAN_REPLY_SHA),(2,TURN_REPLY_SHA)):
        original=doc["model_events"][idx-1]
        fn=f"{idx:02d}-real-model-wire.json"
        wire=(PAID_PLAN/"provider-originals"/fn).read_bytes()
        require(original["index"]==idx and
                original["wire_sha256"]==h(wire) and
                original["original_wire_saved_before_parsing"] is True and
                original["decoded_json_sha256"]==expected_sha,
                "WF0AO_OLD_REAL_PROVIDER_WIRE_SHA_MISMATCH")
        env=json.loads(wire)
        require(env["model"]=="deepseek-flash" and
                len(env["choices"])==1 and
                env["choices"][0]["finish_reason"]=="stop",
                "WF0AO_OLD_REAL_PROVIDER_FINISH_CHANGED")
        msg=env["choices"][0]["message"]["content"]
        decoded=json.loads(msg)
        compact=json.dumps(decoded,ensure_ascii=False,separators=(",",":"))
        require(h(compact)==expected_sha,
                "WF0AO_OLD_REAL_DECODED_CONTENT_SHA_MISMATCH")
        requests=json.loads((PAID_PLAN/"model-requests"/
                             f"{idx:02d}-request.json").read_text("utf8"))
        require(requests["prompt_sha256"]==original["prompt_sha256"]
                and h(requests["prompt"])==original["prompt_sha256"],
                "WF0AO_OLD_REAL_PROMPT_SHA_MISMATCH")
        replies.append((compact,original,requests))
    normalized,receipt=_normalize_optional_model_craft_labels(replies[1][0])
    require(receipt is not None and
            receipt["original_model_plan_sha256"]==TURN_REPLY_SHA and
            receipt["events_or_goals_unchanged"] is True and
            receipt["only_model_optional_craft_fields_adjusted"] is True,
            "WF0AO_REAL_OPTIONAL_CRAFT_SOURCE_CHANGED")
    original_plan=json.loads(replies[1][0])["turns"]
    checked=parse_turn_outline(normalized)
    require(len(checked)==6 and
            [x["id"] for x in checked]==[
                "t01","t02","t03","t04","t05","t06"] and
            checked[2]["causal_parent"]=="t02" and
            checked[5]["causal_parent"]=="t05" and
            all({k:v for k,v in old.items() if k!="craft_focus"}==
                {k:v for k,v in new.items() if k!="craft_focus"}
                for old,new in zip(original_plan,checked)),
            "WF0AO_FROZEN_REAL_EVENT_PLAN_WAS_REWRITTEN")
    return replies[0][0], normalized, receipt,doc,replies


class OriginalPlanThenSameWriter:
    def __init__(self,key,original_first_reply,old_metadata):
        self.first=original_first_reply
        self.old=old_metadata
        self.replayed_first=False
        self.current=None
        self.events=[]
        self.budget=FlashBudget(max_calls=MAX_NEW_CALLS,
                                max_reserved_output_tokens=MAX_RESERVED_OUTPUT_TOKENS,
                                max_total_tokens=150000)
        self.client=DeepSeekFlashModel(
            api_key=key,budget=self.budget,
            timeout_seconds=110,on_response_wire=self.on_original)

    def on_original(self,raw):
        require(type(raw) is bytes and self.current is not None and
                len(self.events)>0,
                "WF0AO_UNEXPECTED_REAL_AUTHOR_PROVIDER_WIRE")
        event=self.events[-1]
        path=OUT/"provider-originals"/f"new-{event['index']:02d}.json"
        path.parent.mkdir(parents=True,exist_ok=True)
        require(not path.exists() and event["raw_provider_sha256"] is None,
                "WF0AO_REAL_AUTHOR_WIRE_IMMUTABLE_NO_RETRY")
        path.write_bytes(raw)
        event["raw_provider_sha256"]=h(raw)
        event["provider_wire_saved_before_json_validation"]=True

    def ask(self,packet,*,model,api_base,max_tokens):
        require(model=="deepseek-flash" and len(packet.prompt)>40,
                "WF0AO_SAME_SOURCE_WRITER_WRONG_MODEL")
        if not self.replayed_first:
            require(h(packet.prompt)==self.old["prompt_sha256"] and
                    max_tokens==self.old["max_completion_tokens_reserved"],
                    "WF0AO_OLD_REAL_CHAPTER_PLAN_PROMPT_CHANGED")
            self.replayed_first=True
            return self.first  # Actual immutable paid source. NO new model.
        require(len(self.events)<MAX_NEW_CALLS,
                "WF0AO_BOUNDED_REAL_MODEL_CALL_COUNT")
        index=len(self.events)+1
        event={
            "index":index,"prompt_sha256":h(packet.prompt),
            "model":"deepseek-flash",
            "max_completion_tokens_reserved":max_tokens,
            "raw_provider_sha256":None,
            "provider_wire_saved_before_json_validation":False}
        self.events.append(event)
        request=OUT/"new-model-requests"/f"{index:02d}-request.json"
        save(request,{
            "format":"wf.0ao.new-same-author-request.v1",
            "prompt":packet.prompt,
            "prompt_sha256":h(packet.prompt),"max_tokens":max_tokens,
            "no_literary_truth_assumed":True})
        self.current=index
        try:
            response=self.client.ask_json(
                role="self_scene_writing",
                system=previous.WRITER_SYSTEM,
                user=packet.prompt,max_tokens=max_tokens)
            raw=json.dumps(response,ensure_ascii=False,separators=(",",":"))
            event["decoded_sha256"]=h(raw)
            event["lossless_provider_format_recovery"]=(
                self.client.last_response_format_recovery)
            return raw
        finally:
            self.current=None


def main():
    require(not OUT.exists(),"WF0AO_PRIVATE_SOURCE_JOB_ALREADY_EXISTS")
    OUT.mkdir(parents=True)
    status={
        "format":"wf.0ao.reuse-two-real-author-plans-prose-only-g.v1",
        "status":"NOT_STARTED","archived_failed_plan_run":ORIGINAL_MODEL_RUN,
        "original_writer_micro_source_run":previous.ORIGINAL_SOURCE_RUN,
        "original_author_source_sha256":previous.EXPECTED_SOURCE_SHA,
        "old_real_plan_replayed_without_model":False,
        "old_real_six_event_plan_preserved":False,
        "new_model_calls":0,"new_author_prose_only_from_deepseek":True,
        "new_acceptance_into_Canon":False,
        "V119_ai_decides_not_wf":True,"new_extra_memory_modules":0,
        "R2_reads":0,"R2_writes":0,"Canon_writes":0,
        "Railway_deployments":0,"main_modified":False,
        "literary_improvement_proven":False,
        "human_independent_grades":False,
        "new_provider_events":[]}
    model=None
    db=None
    try:
        require(not any(os.getenv(x) for x in (
            "WRITERFORGE_R2_ACCOUNT_ID","WRITERFORGE_R2_ACCESS_KEY_ID",
            "DISCOVERY_API_KEY","OPENAI_API_KEY","OPENROUTER_API_KEY")),
            "WF0AO_FORBIDDEN_OTHER_SOURCE_CREDENTIALS_PRESENT")
        old,wire_sha=previous.verify_old_real_source()
        frozen,turns,normalization,manifest,replies=freeze_original_model_decisions()
        require(h(old)==manifest["source_sha256"] and
                h((PAID_PLAN/"frozen-original-history.md").read_bytes())==h(old),
                "WF0AO_ORIGINAL_UNACCEPTED_HISTORY_NOT_IDENTICAL")
        status["old_original_wire_sha256"]=wire_sha
        status["old_real_plan_replayed_without_model"]=True
        status["old_real_six_event_plan_preserved"]=True
        status["original_model_plan_sha256"]=PLAN_REPLY_SHA
        status["original_model_turn_outline_sha256"]=TURN_REPLY_SHA
        status["only_optional_craft_tags_normalized"]=normalization
        (OUT/"frozen-original-history.md").write_text(old,encoding="utf8")
        (OUT/"frozen-chapter-plan-original.json").write_text(
            frozen,encoding="utf8")
        (OUT/"frozen-six-turn-original.json").write_text(
            replies[1][0],encoding="utf8")
        (OUT/"frozen-six-turn-optional-craft-compatibility.json").write_text(
            turns,encoding="utf8")
        require_external_runtime()
        prior_checkpoint=external_temporal_step(old,cast=previous.CAST)
        graph=new_graph(project_id=previous.PROJECT,
                        scene_id=previous.SCENE,chapter_index=0)
        root=make_resume(
            project_id=previous.PROJECT,scene_id=previous.SCENE,
            chapter_index=0,checkpoint=prior_checkpoint,
            unified_narrative_core=graph)
        require(root["author_accepted"] is False,
                "WF0AO_REAL_ROOT_NOT_UNACCEPTED")
        save(OUT/"root-verified-old-history.json",root)
        db=WriterForgeDB(OUT/"source-only-local-runtime.db")
        snapshot=previous.local_source_only_snapshot(db,old)
        rt=RuntimeEngine()
        rt.enter_write(snapshot)
        assist=InvisibleWritingAssist(
            db,rt,previous.PROJECT,previous.SCENE,
            "继续前文真实边关传令的局部人物选择和时间差，不复制任何现成作品。",
            model="deepseek-flash",api_base="https://api.deepseek.com/v1",
            source_genre="古代白话")
        secret=os.getenv("DEEPSEEK_API_KEY","")
        require(len(secret)>=16,"WF0AO_EXISTING_DEEPSEEK_KEY_MISSING")
        model=OriginalPlanThenSameWriter(secret,frozen,replies[0][1])
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=model.ask):
            final=AutonomousWriting(assist).run(
                outline=(
                    "【已存在的同一原创写作模型旧文，仍未作者接受】\n"+old+
                    "\n【源边界】这是真实旧正文，不是新小说计划："
                    "申时末旧信最快明日卯时抵达；听见马蹄不证明信使已经起程，"
                    "更不能证明主帅收到。旧人物心理与来源以旧文字为准。"
                    "\n【后续原创任务】只写接下来发生的短时段，每个小片段200到350字。"
                    "作者自行决定留白、人物动作、选择、是否回头修句；"
                    "你可以不修改，无文学分数目标."),
                chapter_goals=previous.GOALS,
                draft_mode="continuity_guard",
                resume_story_checkpoint=root,
                frozen_turn_outlines=(turns,),
                narrative_memory_backend="local",
                self_edit_rounds=1,
                self_edit_timing="ai_decides",
                reader_first_self_review=False,
                output_dir=OUT/"g-original-plan-new-prose-only")
        chapter=final["chapters"][0]
        body=Path(chapter["candidate"]).read_text("utf8")
        resume=json.loads(Path(chapter[
            "v117_unreviewed_text_trace_resume"]).read_text("utf8"))
        read_resume(resume,project_id=previous.PROJECT,scene_id=previous.SCENE)
        next_core=read_core_from_resume(
            resume,project_id=previous.PROJECT,scene_id=previous.SCENE)
        link=next_core["source_temporal_link"]
        require(link["whole_chapter_sha256"]==h(body)
                and link["source_assembly_verified"] is True
                and link["ancestry_fully_verified"] is True
                and next_core["parent_sha256"]==graph["receipt_sha256"]
                and resume["author_accepted"] is False,
                "WF0AO_REGENERATED_SOURCE_NOT_SIGNED_G_CORE")
        require((OUT/"frozen-original-history.md").read_text("utf8")==old,
                "WF0AO_OLD_AUTHOR_PROSE_CHANGED")
        status.update({
            "status":"SIGNED_NEW_G_UNACCEPTED_REAL_PROSE_COMPLETED",
            "candidate_whole_sha256":h(body),
            "candidate_prose_chars":len(body),
            "old_previous_turn_rewinds":final.get(
                "wf_self_edit_previous_turn_rewinds",0),
            "ai_actual_previous_turn_rewind_and_new_downstream":(
                final.get("wf_self_edit_previous_turn_rewinds",0)>0),
            "new_unified_core_sha256":next_core["receipt_sha256"],
            "new_V117_resume_sha256":resume["receipt_sha256"],
            "actor_acceptance":resume["author_accepted"],
        })
    except Exception as exc:
        error=str(exc)
        status["status"]="SOURCE_OR_NEW_AUTHOR_PROSE_HOLD_NO_RETRY"
        status["failure_code"]=(error if re.fullmatch(r"WF[A-Z0-9_:\-]{3,170}",
                                                   error)
                                else type(exc).__name__+":NO_RETRY")
    finally:
        if db is not None:db.close()
        if model is not None:
            status["new_model_calls"]=model.budget.calls_reserved
            status["new_provider_events"]=model.events
            status["new_model_budget"]=model.budget.public_receipt()
            status["frozen_chapter_plan_replayed_requests"]=(
                int(model.replayed_first))
        save(OUT/"STATUS.json",status)
        print("WF0AO_LIVE "+json.dumps({
            "status":status["status"],"new_model_calls":status["new_model_calls"],
            "old_real_plans_reused":status["old_real_plan_replayed_without_model"],
            "revised_previous":status.get("old_previous_turn_rewinds"),
            "new_candidate_sha":status.get("candidate_whole_sha256"),
            "error":status.get("failure_code"),
        },ensure_ascii=False),flush=True)
    if status["status"]!="SIGNED_NEW_G_UNACCEPTED_REAL_PROSE_COMPLETED":
        raise RuntimeError("WF0AO_REAL_PREVIOUS_PLAN_PROSE_FAILED_NO_RETRY")


if __name__=="__main__":
    main()
