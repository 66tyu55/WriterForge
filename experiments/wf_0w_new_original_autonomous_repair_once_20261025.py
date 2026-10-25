"""WriterForge 0.W: a truly NEW tiny-fiction autonomous revision pilot.

Only existing DeepSeek Flash novelist, no imported literary source, R2,
second reviewer model, Canon or production deployments. The model authors
every initial/edited/continuation sentence, and chooses KEEP or LOOK_BACK.
WF checks V96/V114/V116/V117/V119 and unified signed candidate sources.
This is a capped actual provider attempt, NOT training or a literary grade.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import os

from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget
from writerforge.verified_flow import GroundedDraftPacket
from writerforge.v96_causal_turns import (
    check_turn,make_turn_instructions,parse_turn_outline,
)
from writerforge.v114_external_story_state import (
    require_external_runtime,external_temporal_step,
)
from writerforge.v117_continuity_trace import preflight_continuation,make_resume,read_resume
from writerforge.v116_state_delta import preflight_next_prose
from writerforge.writing_assist import (
    _ai_decides_when_to_revisit,_reader_separates_written_and_inferred,
    _self_edit_one_turn,_physical_relation_source_hold,
)
from writerforge.narrative_core import (
    new_graph,advance_graph,record_chapter_memory,
)

OUT=Path("wf_0w_new_original_author_repair_20261025")
PROJECT="wf-0w-new-original-staged-literary"
SCENE="fresh-rain-ledger"
MAX_NEW_CALLS=8
MAX_OUTPUT_RESERVED=11400
CAST=("姜岚","许槐")
SEED=(
    "《雨册》是一部完全原创的中文现实悬疑小说，背景是靠河道防洪的一座古城。"
    "年轻的姜岚在堤上的水尺房记潮汛，许槐掌管旧档房，两人并不互相信任。"
    "一本可能影响开闸决定的旧记录与城里居民的安全有关，但谁知道什么、"
    "物件从哪里来，只有实际写出的场景才算故事前因。"
    "你自己决定人物的行动、个性、代价和悬念，故事不要复刻《潮簿》或任何名著剧情。"
    "所有小说句子和作家判断都由你本人生成。WF 只是保护已经真正写出的事实。"
    "不要一次性写完第一章；这次只写两三个自然短片段。"
)
BEATS=(
    {"id":"t01","kind":"action","actor":"姜岚",
     "goal":"在夜间防汛值守中作出有阻力的实际行动，并在当下写出可观察的后果",
     "causal_parent":None,"craft_focus":[]},
    {"id":"t02","kind":"decision","actor":"姜岚",
     "goal":"只依据上段已写出的后果作出带有现实代价的自主选择，不抢先预支秘密",
     "causal_parent":"t01","craft_focus":[]},
)
WRITER_SYSTEM=(
    "你是本篇《雨册》的唯一真正小说作者，不是测试人员。"
    "由你自己决定具体情节、句子、节奏、何时回头及修改范围。"
    "只返回此轮要求的 JSON 对象，禁止解释代码、测试或软件分数。"
)

def digest(value):
    return sha256(value.encode("utf8") if isinstance(value,str) else value).hexdigest()

def require(value,code):
    if not value:
        raise RuntimeError(code)

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2),
                    encoding="utf8")

def packet(content):
    return GroundedDraftPacket(
        project_id=PROJECT,scene_id=SCENE,snapshot_id=0,evidence=(),
        craft_ids=(),prompt=content,prompt_sha256=digest(content))

def normalized_model_turn(raw):
    obj=json.loads(raw)
    if set(obj)=={"type","prose","trace"} and obj["type"]=="json_object":
        obj={"prose":obj["prose"],"trace":obj["trace"]}
    require(set(obj)=={"prose","trace"} and type(obj["prose"]) is str and
            80<=len(obj["prose"].strip())<=1024,
            "WF0W_MODEL_PROSE_ENVELOPE_OR_LENGTH_INVALID")
    return json.dumps(obj,ensure_ascii=False,separators=(",",":"))

class OneNovelist:
    def __init__(self,key):
        self.budget=FlashBudget(
            max_calls=MAX_NEW_CALLS,
            max_reserved_output_tokens=MAX_OUTPUT_RESERVED,
            max_total_tokens=150000)
        self.events=[]
        self.active=None
        self.client=DeepSeekFlashModel(
            api_key=key,budget=self.budget,
            timeout_seconds=110,on_response_wire=self.keep_wire)

    def keep_wire(self,wire):
        require(type(wire) is bytes and self.active is not None,
                "WF0W_MODEL_WIRE_NOT_OWNED")
        place=OUT/"real-provider-wires"/(self.active+".json")
        place.parent.mkdir(parents=True,exist_ok=True)
        place.write_bytes(wire)
        self.events[-1]["raw_real_provider_wire_sha256"]=digest(wire)
        self.events[-1]["real_wire_stored_before_parse"]=True

    def ask(self,name,content,limit):
        require(name in (
            "first-original","second-original","independent-source-reader",
            "author-self-decision","author-source-V119-edit",
            "author-next-beat","new-downstream-from-repaired-source")
            and type(limit) is int and 100<=limit<=1800
            and len(self.events)<MAX_NEW_CALLS,
            "WF0W_UNBOUNDED_OR_UNKNOWN_MODEL_STAGE")
        self.active=f"{len(self.events)+1:02d}-{name}"
        self.events.append({
            "stage":name,"limit":limit,"prompt_sha256":digest(content),
            "same_literary_author":True})
        data=self.client.ask_json(
            role="self_scene_writing",system=WRITER_SYSTEM,
            user=content,max_tokens=limit)
        raw=json.dumps(data,ensure_ascii=False,separators=(",",":"))
        (OUT/"real-provider-wires"/(self.active+"-decoded.json")).write_text(
            raw,encoding="utf8")
        self.events[-1]["original_decoded_model_response_sha256"]=digest(raw)
        return raw

    def adapter(self,name):
        def ask_model(packet,*,model,api_base,max_tokens):
            require(model is None and api_base is None,
                    "WF0W_WRITER_MODEL_IDENTITY_CHANGED")
            return self.ask(name,packet.prompt,max_tokens)
        return ask_model

def ask_turn(model,beat,accepted=()):
    prompt=(
        "【原创目标，不是已写事实】"+SEED+
        "\n【只有这一步：写 250 至 600 字自然小说，不写整章，不写大纲】"+
        ("\n【此前已写候选正文，仅这些句子为已发生前史】"+
         "\n\n".join(x["prose"] for x in accepted) if accepted else "")+
        "\n【当前请你自主创作的实际事件要求】"+
        make_turn_instructions(beat,mode="causal_guard",
                               accepted=tuple(accepted)))
    require(len(prompt)<=18000,"WF0W_PROSE_PROMPT_TOO_LARGE")
    name=("first-original" if not accepted else
          "second-original" if beat["id"]=="t02" and
              accepted[0]["beat_id"]=="t01" and len(accepted)==1 and
              not getattr(model,"regenerating",False) else
          "new-downstream-from-repaired-source")
    answer=normalized_model_turn(model.ask(name,prompt,1400))
    result=check_turn(
        answer,beat,mode="causal_guard",
        accepted=tuple(accepted),max_prose_chars=1024)
    return answer,result

def check_source_gate(prose, prior=None):
    state=(prior["reducer_result"]["candidate_state"] if prior else {})
    report=preflight_next_prose(
        prose,previous_candidate_state=state,cast=CAST,
        previous_relation_receipt=(
            prior.get("v122_physical_relation_source_receipt")
            if prior is not None else None))
    hold=_physical_relation_source_hold(prose=prose,preflight=report)
    return report,hold

def third_beat(model,accepted):
    source="\n\n".join(x["prose"] for x in accepted)
    prompt=(
        "你还是原小说作者，现在只有一项任务：自行构思**一个**新的微型 t03 事件目标，"
        "不输出正文，不复述前两段，更不写下一章。"
        "\n【唯一已写事实】"+source+
        "\n【最后一段实际效果】"+
        json.dumps(accepted[-1]["effect_quote"],ensure_ascii=False)+
        "\n严格 JSON 对象只含 turn 键。turn 必须恰好包含 "
        "id、kind、actor、goal、causal_parent、craft_focus 六字段。"
        "id=t03，causal_parent=t02 或 null；kind 为"
        " action/decision/reversal/setup/dialogue/quiet/aftermath/transition；"
        "goal 8～220 字。人物和推进方式由你本人决定。"
    )
    raw=model.ask("author-next-beat",prompt,850)
    obj=json.loads(raw)
    if set(obj)=={"type","turn"} and obj["type"]=="json_object":
        obj={"turn":obj["turn"]}
    require(type(obj) is dict and set(obj)=={"turn"} and
            type(obj["turn"]) is dict and obj["turn"].get("id")=="t03",
            "WF0W_AUTHOR_THIRD_PLAN_SCHEMA_INVALID")
    parse_turn_outline(json.dumps(
        {"turns":[*BEATS,obj["turn"]]},ensure_ascii=False))
    return obj["turn"]

def signed_final(accepted):
    full="\n\n".join(x["prose"] for x in accepted)
    manuscript=OUT/"REAL_AUTHOR_UNACCEPTED_STAGED_STORY.md"
    manuscript.write_text(full,encoding="utf8")
    cp=external_temporal_step(full,cast=CAST)
    core=new_graph(project_id=PROJECT,scene_id=SCENE)
    core=advance_graph(core,project_id=PROJECT,scene_id=SCENE,
                       chapter_index=1,prose=full,events=[])
    core=record_chapter_memory(
        core,project_id=PROJECT,scene_id=SCENE,chapter_index=1,
        source_path=str(manuscript),prose=full)
    signed=make_resume(project_id=PROJECT,scene_id=SCENE,chapter_index=1,
                       checkpoint=cp,unified_narrative_core=core)
    read_resume(signed,project_id=PROJECT,scene_id=SCENE)
    return {"signed_unaccepted_candidate_sha256":signed["receipt_sha256"],
            "unreviewed_model_manuscript_sha256":digest(full),
            "source_stage_sha256":[digest(x["prose"]) for x in accepted],
            "human_literary_quality_verified":False}

def execute():
    require_external_runtime()
    require(not any(os.getenv(k) for k in (
        "WRITERFORGE_R2_ACCOUNT_ID","WRITERFORGE_R2_ACCESS_KEY_ID",
        "DISCOVERY_API_KEY","OPENAI_API_KEY")),
        "WF0W_NO_EXTERNAL_SOURCE_OR_SECOND_MODEL_ALLOWED")
    key=os.getenv("DEEPSEEK_API_KEY","")
    require(len(key)>=16,"WF0W_EXISTING_DEEPSEEK_NOT_CONFIGURED")
    writer=OneNovelist(key)
    report={
        "format":"wf.0w.new-original-same-author-source-revision.v1",
        "new_model_calls":0,"max_new_model_calls":MAX_NEW_CALLS,
        "max_output_token_reservation":MAX_OUTPUT_RESERVED,
        "fresh_no_book_source":True,
        "same_model_all_roles":True,"no_external_literary_critic":True,
        "actual_author_selected_revision":False,
        "actually_safe_revised_prose_and_new_downstream":False,
        "new_prose_literary_improvement_independently_verified":False,
        "no_hidden_model_retries":True,
        "R2_reads":0,"R2_writes":0,"Canon_writes":0,
        "Railway_deployments":0,"main_changed":False,
    }
    try:
        raw1,first=ask_turn(writer,BEATS[0])
        (OUT/"first-author-original.md").write_text(first["prose"],encoding="utf8")
        gate1,hold1=check_source_gate(first["prose"])
        save(OUT/"stage1-source-gate.json",gate1)
        require(not gate1["blocked"] and hold1 is None and
                not gate1["needs_review"],
                "WF0W_FIRST_REAL_SOURCE_NOT_CLEAN")
        cp1=external_temporal_step(first["prose"],cast=CAST)
        raw2,second=ask_turn(writer,BEATS[1],(first,))
        (OUT/"second-author-original.md").write_text(second["prose"],encoding="utf8")
        gate2,hold2=check_source_gate(second["prose"],cp1)
        save(OUT/"stage2-source-gate.json",gate2)
        report["original_story_sources"]=[
            digest(first["prose"]),digest(second["prose"])]
        if hold2 is not None:
            save(OUT/"second-source-physical-HOLD.json",hold2)
        # A source-based question is not a model command to edit. Same
        # novelist first reads exactly these two written prose texts.
        source_packet=packet("原作者两段正文来源审阅；不包含外部书籍或评价")
        reader=_reader_separates_written_and_inferred(
            raw=raw2,turn_packet=source_packet,
            ask_model=writer.adapter("independent-source-reader"),
            directory=OUT/"source-only-reader",
            earlier_source=first["prose"],
            earlier_source_sha256=digest(first["prose"]),
            compact_source_review=True)
        report["source_reader_status"]=reader["status"]
        require(reader["status"]=="SOURCE_ANCHORED_READER_HYPOTHESES",
                "WF0W_SOURCE_READER_NOT_ANCHORED")
        attention=_ai_decides_when_to_revisit(
            raw=raw2,beat=BEATS[1],accepted=(first,),
            turn_packet=packet(SEED),
            ask_model=writer.adapter("author-self-decision"),
            directory=OUT/"author-self-decision",
            reader_report=reader["report"],
            source_identity_contract="bind_null_current")
        save(OUT/"actual-author-choice.json",{
            "decision":attention["decision"],
            "target_turn":attention.get("target_turn"),
            "reason":attention.get("reason"),
            "risk":attention.get("risk"),
            "source_quote":attention.get("source_quote"),
            "receipt":attention["receipt"],
        })
        report["actual_author_choice"]=attention["decision"]
        if attention["decision"]=="MOVE_ON":
            report["status"]=(
                "SOURCE_HELD_AUTHOR_CHOSE_MOVE_ON" if hold2 or
                gate2["needs_review"] or gate2["blocked"] else
                "AUTHOR_MOVED_ON_NO_SELF_REWRITE")
            return report,writer
        require(attention["decision"]=="LOOK_BACK_NOW",
                "WF0W_AUTHOR_REVISIT_NOT_A_VALID_SELF_CHOICE")
        report["actual_author_selected_revision"]=True
        target_previous=attention["target_turn"]=="previous"
        require(attention["target_turn"] in ("previous","current"),
                "WF0W_AUTHOR_TARGET_SCOPE_INVALID")
        source_raw=(raw1 if target_previous else raw2)
        target_beat=(BEATS[0] if target_previous else BEATS[1])
        prior_for_edit=(() if target_previous else (first,))
        target_old_checkpoint=(None if target_previous else cp1)
        edit,new_receipt=_self_edit_one_turn(
            raw=source_raw,beat=target_beat,accepted=prior_for_edit,
            project_id=PROJECT,scene_id=SCENE,
            turn_packet=packet(SEED),
            ask_model=writer.adapter("author-source-V119-edit"),
            round_limit=2,call_allowance=2,
            directory=OUT/"author-V119-revision",
            previous_candidate_state=(
                {} if target_previous else cp1["reducer_result"]["candidate_state"]),
            cast=CAST,current_external_story_checkpoint=target_old_checkpoint,
            story_chapter_index=1,
            writer_attention={
                "reason":attention.get("reason"),
                "risk":attention.get("risk"),
                "desired_effect":attention.get("desired_effect"),
                "source_quote":attention.get("source_quote"),
                "focus":attention.get("focus"),
            })
        save(OUT/"author-V119-result.json",new_receipt)
        original=json.loads(source_raw)["prose"].strip()
        require(json.loads(edit)["prose"].strip()!=original,
                "WF0W_MODEL_SELF_EDIT_REJECTED_OR_KEPT")
        accepted_new=check_turn(
            edit,target_beat,mode="causal_guard",
            accepted=prior_for_edit,max_prose_chars=1024)
        gate_revised,hold_revised=check_source_gate(
            accepted_new["prose"],target_old_checkpoint)
        save(OUT/"revised-source-preflight.json",gate_revised)
        require(not gate_revised["blocked"] and
                not gate_revised["needs_review"] and
                hold_revised is None,
                "WF0W_REVISED_SOURCE_STILL_HAS_UNPROVEN_STATE")
        if target_previous:
            # The old second segment is revoked: no reuse of its story
            # bytes or derived V114/NarrativeCore state in this new branch.
            writer.regenerating=True
            cp_revised=external_temporal_step(accepted_new["prose"],cast=CAST)
            raw_after,down=ask_turn(writer,BEATS[1],(accepted_new,))
            adopted=(accepted_new,down)
            report["discarded_old_downstream_sha256"]=digest(second["prose"])
        else:
            cp_revised=external_temporal_step(
                accepted_new["prose"],cast=CAST,prior=cp1)
            third=third_beat(writer,(first,accepted_new))
            save(OUT/"author-own-third-beat.json",third)
            raw_after,down=ask_turn(writer,third,(first,accepted_new))
            adopted=(first,accepted_new,down)
            report["discarded_old_downstream_sha256"]=None
        gate_last,hold_last=check_source_gate(down["prose"],cp_revised)
        save(OUT/"new-downstream-source-gate.json",gate_last)
        v117=preflight_continuation(
            down["prose"],cp_revised,project_id=PROJECT,
            chapter_index=1,cast=CAST)
        save(OUT/"new-downstream-v117.json",v117)
        require(not gate_last["blocked"] and not gate_last["needs_review"]
                and hold_last is None and
                not v117["blocked"] and not v117["needs_review"],
                "WF0W_RECREATED_DOWNSTREAM_NOT_SOURCE_SAFE")
        report.update(signed_final(adopted))
        report["new_downstream_prose_sha256"]=digest(down["prose"])
        report["actually_safe_revised_prose_and_new_downstream"]=True
        report["status"]="GENUINE_SAME_AUTHOR_SOURCE_EDIT_AND_FRESH_DOWNSTREAM"
        return report,writer
    except Exception as exc:
        code=str(exc)
        if not (code.startswith("WF") and len(code)<=190):
            code=type(exc).__name__+":SOURCE_FAIL_CLOSED"
        report.update(status="REJECTED_OR_HELD_NO_RETRY",
                      failure_code=code,
                      actually_safe_revised_prose_and_new_downstream=False)
        return report,writer

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    novelist=None
    try:
        summary,novelist=execute()
    except Exception as exc:
        summary={
            "status":"PREFLIGHT_FAILED_NO_MODEL",
            "failure_code":str(exc)[:190] if str(exc).startswith("WF") else
                type(exc).__name__,
            "new_model_calls":0,"R2_reads":0,"R2_writes":0,
            "Canon_writes":0,"actually_safe_revised_prose_and_new_downstream":False,
            "new_prose_literary_improvement_independently_verified":False
        }
    if novelist is not None:
        summary["new_model_calls"]=novelist.budget.calls_reserved
        summary["provider_usage"]=novelist.budget.public_receipt()
        summary["model_original_wire_evidence"]=novelist.events
    summary.setdefault("new_prose_literary_improvement_independently_verified",False)
    save(OUT/"STATUS.json",summary)
    print("WF0W_REAL_NOVELIST "+json.dumps({
        "status":summary["status"],
        "model_calls":summary.get("new_model_calls",0),
        "author_choice":summary.get("actual_author_choice"),
        "source_edit_and_downstream_valid":summary.get(
            "actually_safe_revised_prose_and_new_downstream",False),
        "independent_literary_quality_proven":False
    },ensure_ascii=False),flush=True)


if __name__=="__main__":
    main()
