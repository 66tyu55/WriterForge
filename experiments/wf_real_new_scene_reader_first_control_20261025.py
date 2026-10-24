"""One new real WF G chapter, two SAME-SOURCE author self-review arms.

Control: same DeepSeek author directly decides MOVE_ON / LOOK_BACK_NOW.
Treatment: same DeepSeek first reconstructs exactly SOURCE-written events as a
fresh reader, then returns to AUTHOR role to decide. Neither arm is instructed
to find a bug or change prose. Only the model itself may create a V119 patch.
Every original provider wire and rejected candidate stays in private Actions.

One new seed, no literary training, no user source/R2, no second reviewer,
no formal Canon, no model retries. 9 API calls / 10800 reserved tokens hard cap.
The WHOLE real WriterForge G writing path first creates plan/beat/two turns.
No mock fiction or synthetic success for real results.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os
import re
import shutil
import sys

from experiments.v111_peer.neutral_bridge import fresh_neutral_published_snapshot
from experiments.wf_real_self_scene_diagnostics import SYSTEMS
from writerforge import WriterForgeDB, RuntimeEngine
from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget
from writerforge.writing_assist import (
    InvisibleWritingAssist,AutonomousWriting,
    _reader_separates_written_and_inferred,_ai_decides_when_to_revisit,
    _self_edit_one_turn,_decode_json,
)
from writerforge.v96_causal_turns import (
    check_turn,V96CausalDraftError,parse_turn_outline,
)
from writerforge.v114_external_story_state import (
    external_temporal_step,require_external_runtime,
)
from writerforge.v117_continuity_trace import make_resume
from writerforge.narrative_core import (
    new_graph,advance_graph,record_chapter_memory,
)
from writerforge.verified_flow import GroundedDraftPacket,WritingExecutionError

OUT=Path("wf_real_new_scene_reader_first_control_20261025")
PROJECT="wf-original-night-opera-new-one-shot"
SCENE="winter-opera-hall"
MODEL="deepseek-flash"
API="https://api.deepseek.com"
GENRE="江湖悬疑"
SEED=(
    "寒夜庙会散场，临水戏楼的二层南廊第三块木板已经开裂，"
    "楼里的人都没有把木板修好。"
    "戏班女伶江遥左脚扭伤，无法快跑，衣袖里藏着一张尚未交出去的赎身票据。"
    "年迈的打更人宋易握着后门钥匙，他知道木板有裂缝，"
    "却不知道江遥藏着票据，也不知道她想离开戏班。"
    "北侧楼梯从楼下上了锁，通往正门须穿过没有点灯的看台。"
    "楼上传来三声轻轻的鼓响，两人都看不见打鼓的人，也不知道是谁。"
)
OUTLINE=(
    "江湖悬疑的一个原创深夜戏楼场景。让江遥与宋易按各自真实所知"
    "作出小而有后果的决定；声音来源可以保持未知，"
    "留白与沉默是允许的，但不能把尚未见到的人当作已知真相。"
    "人物可以犯错，可以选择放弃，不必为了结尾反转而行动。"
    "\n先前确切已写的初始事实（不是后续故事命令）："+SEED
)
GOAL=(
    "江遥与宋易对楼上传来的鼓声作出各自真实可见的选择，"
    "受伤、封锁路线、相互未知的动机要真实影响选择和代价。"
)
CAST=("江遥","宋易")
MAX_CALLS=9
G_STAGES=("CHAPTER_PLAN","SELF_BEAT_PLAN","PROSE_1","PROSE_2")
TOKENS_BY_STAGE={
    "CHAPTER_PLAN":650,
    "SELF_BEAT_PLAN":1450,
    "PROSE_1":1450,
    "PROSE_2":1450,
    "CONTROL_AUTHOR":600,
    "CONTROL_V119":1800,
    "TREATMENT_READER":1000,
    "TREATMENT_AUTHOR":600,
    "TREATMENT_V119":1800,
}
FULL_MAX_RESERVED=650+1450*3+600+1800+1000+600+1800
assert FULL_MAX_RESERVED==10800
READER_SYSTEM=(
    "你是一位从未看过这段作品的读者。只看真正写下的完整小说，"
    "严格区分原文字面事实与需要读者自行补足的推测。"
    "只输出来源引句可复核的 JSON，不评分、不代写、不替作者决定修改。"
)
AUTHOR_SYSTEM=(
    "你就是正在写作该小说的同一个作者。"
    "自己决定保留还是回头修改。"
    "小说的审美与人物选择不能由 WriterForge 代码决定。"
    "只返回实际接口规定的 JSON，不写新正文或自评分。"
)
EDIT_SYSTEM=(
    "你仍然是同一个小说作者。根据自己先前的自主决定，"
    "只输出严格 V119 逐字 source-locked 替换 JSON。"
    "从正文唯一原句确定选区，没有前一事件时 parent_effect_quote 必须为 null。"
    "仅你负责创作实际新小说句子，不能要求软件代写。"
)
SYSTEM_BY_STAGE={
    "CHAPTER_PLAN":SYSTEMS["CHAPTER_PLAN"],
    "SELF_BEAT_PLAN":SYSTEMS["SELF_BEAT_PLAN"],
    "PROSE_1":SYSTEMS["PROSE"],
    "PROSE_2":SYSTEMS["PROSE"],
    "CONTROL_AUTHOR":AUTHOR_SYSTEM,
    "CONTROL_V119":EDIT_SYSTEM,
    "TREATMENT_READER":READER_SYSTEM,
    "TREATMENT_AUTHOR":AUTHOR_SYSTEM,
    "TREATMENT_V119":EDIT_SYSTEM,
}

def h(v):
    return sha256(v.encode("utf8") if isinstance(v,str) else v).hexdigest()

def save(path,doc):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,
                               indent=2),encoding="utf8")

def code(exc):
    s=str(exc)
    if isinstance(s,str) and re.fullmatch(r"[A-Z][A-Z0-9_:\-]{2,150}",s):
        return s
    return type(exc).__name__

class SameActualWriter:
    """Only stage-bound actual DeepSeek calls; never silent repetition."""
    def __init__(self,secret):
        self.events=[]
        self.active=None
        self.budget=FlashBudget(
            max_calls=MAX_CALLS,
            max_reserved_output_tokens=FULL_MAX_RESERVED,
            max_total_tokens=150000,
        )
        self.client=DeepSeekFlashModel(
            api_key=secret,budget=self.budget,timeout_seconds=110,
            on_response_wire=self._save_wire)
    def _save_wire(self,raw):
        if self.active is None or not self.events:
            raise RuntimeError("WF_NEW_REAL_WIRE_WITHOUT_MODEL_CALL")
        name=f"{len(self.events):02d}-{self.active}-provider-wire.json"
        (OUT/"provider-wires"/name).write_bytes(raw)
        self.events[-1]["provider_wire_sha256"]=h(raw)
        self.events[-1]["original_provider_wire_saved"]=True

    def call(self,stage,packet,*,max_tokens):
        if (stage not in TOKENS_BY_STAGE or
            TOKENS_BY_STAGE[stage]!=max_tokens or
            len(self.events)>=MAX_CALLS):
            raise RuntimeError("WF_NEW_REAL_STAGE_OR_BUDGET_REJECTED")
        if stage in ("CONTROL_V119","TREATMENT_V119") and not (
            self.events and
            self.events[-1]["stage"] in (
                "CONTROL_AUTHOR","TREATMENT_AUTHOR")):
            raise RuntimeError("WF_NEW_REAL_EDIT_NOT_AUTHORIZED_BY_AUTHOR")
        if stage in ("TREATMENT_READER","TREATMENT_AUTHOR"):
            # Underlying creative seed must not be snuck into the
            # READER phase through an assistant's author-plan prompt.
            if (stage=="TREATMENT_READER" and
                (SEED in packet.prompt or OUTLINE in packet.prompt or
                 "WF 上一次认为" in packet.prompt)):
                raise RuntimeError("WF_NEW_READER_PROMPT_LEAKED_WRITER_PLAN")
        self.active=stage
        row={
            "stage":stage,"request_max_tokens":max_tokens,
            "prompt_sha256":h(packet.prompt),
            "provider_wire_before_validation":False,
            "same_writer_model":MODEL,
        }
        self.events.append(row)
        result=self.client.ask_json(
            role="self_scene_writing",system=SYSTEM_BY_STAGE[stage],
            user=packet.prompt,max_tokens=max_tokens)
        raw=json.dumps(result,ensure_ascii=False,separators=(",",":"))
        name=f"{len(self.events):02d}-{stage}-original-model.json"
        (OUT/"provider-wires"/name).write_text(raw,encoding="utf8")
        row["original_model_reply_sha256"]=h(raw)
        row["provider_wire_before_validation"]=bool(
            row.get("original_provider_wire_saved"))
        return raw

def fixed_packet(prompt):
    return GroundedDraftPacket(
        project_id=PROJECT,scene_id=SCENE,snapshot_id=0,
        evidence=(),craft_ids=(),
        prompt=prompt,prompt_sha256=h(prompt))

def try_review_arm(*,name,writer,source_raw,beat,
                   checkpoint,graph,reader_first):
    """Arms differ ONLY by source-reader preliminary call."""
    arm=OUT/name
    arm.mkdir(exist_ok=False)
    original=_decode_json(source_raw)["prose"].strip()
    checkpoint_state=checkpoint["reducer_result"]["candidate_state"]
    information={
        "arm":name,"same_original_prose_sha256":h(original),
        "reader_first":reader_first,"author_writes_all_revision_prose":True,
        "reader_cannot_decide_author_action":True,
        "source_truth_not_literary_judgment":True,
        "real_model_calls_in_this_arm":0,
        "novel_quality_not_verified":True,
        "author_accepted":False,"canon_writes":0,
    }
    def ask_by_stage(stage):
        def ask(packet,*,model,api_base,max_tokens):
            if model is not None or api_base is not None:
                raise RuntimeError("WF_NEW_SAME_MODEL_ONLY")
            return writer.call(stage,packet,max_tokens=max_tokens)
        return ask
    try:
        # Author receives same actual source, beat and scene brief in both
        # arms. Reader only sees source, not this previous context.
        p=fixed_packet(
            "【此单一作者任务背景，不是已发生的全文】"+OUTLINE+
            "\n【实际先前事件状态仅作来源约束】"+SEED)
        reader=None
        if reader_first:
            reader=_reader_separates_written_and_inferred(
                raw=source_raw,turn_packet=p,
                ask_model=ask_by_stage("TREATMENT_READER"),
                directory=arm/"reader-source-only")
            information["reader_status"]=reader["status"]
            information["reader_report"]=reader["report"]
            information["reader_receipt"]=reader["receipt"]
            information["reader_model_calls"]=reader["model_calls"]
        choice=_ai_decides_when_to_revisit(
            raw=source_raw,beat=beat,accepted=(),
            turn_packet=p,
            ask_model=ask_by_stage(
                "TREATMENT_AUTHOR" if reader_first else "CONTROL_AUTHOR"),
            directory=arm/"writer-own-decision",
            reader_report=reader["report"] if reader else None)
        information.update({
            "author_decision":choice["decision"],
            "author_reason":choice.get("reason"),
            "author_wants_changed_scene":choice["decision"]=="LOOK_BACK_NOW",
            "author_decision_receipt":choice["receipt"],
            "unverified_reader_delivered":choice["receipt"].get(
                "unverified_reader_input_delivered",False),
        })
        final_raw=source_raw
        if choice["decision"]=="LOOK_BACK_NOW":
            final_raw,edit=_self_edit_one_turn(
                raw=source_raw,beat=beat,accepted=(),
                project_id=PROJECT,scene_id=SCENE,
                turn_packet=p,
                ask_model=ask_by_stage(
                    "TREATMENT_V119" if reader_first else "CONTROL_V119"),
                round_limit=1,call_allowance=1,
                directory=arm/"author-proposed-V119",
                previous_candidate_state=checkpoint_state,
                current_external_story_checkpoint=checkpoint,
                active_narrative_core=graph,story_chapter_index=2,
                cast=CAST,writer_attention={
                    "reason":choice.get("reason"),
                    "risk":choice.get("risk"),
                    "desired_effect":choice.get("desired_effect"),
                    "source_quote":choice.get("source_quote"),
                    "focus":choice.get("focus")})
            information["strict_v119_receipt"]=edit
        revised=_decode_json(final_raw)["prose"].strip()
        if revised!=original:
            check_turn(final_raw,beat,mode="causal_guard",accepted=())
            replay=external_temporal_step(
                revised,cast=CAST,prior=checkpoint)
            information["v114_recomputed_receipt"]=replay["receipt_sha256"]
        information["approved_as_provisional_source"]=(revised!=original)
        information["final_prose_sha256"]=h(revised)
        information["status"]="ARM_COMPLETED"
        (arm/"FINAL_UNACCEPTED_ARM_MANUSCRIPT.md").write_text(
            revised,encoding="utf8")
    except Exception as exc:
        information["status"]="ARM_REJECTED_OR_PARTIAL"
        information["reason_code"]=code(exc)
        information["approved_as_provisional_source"]=False
        information["final_prose_sha256"]=h(original)
        (arm/"FINAL_UNACCEPTED_ARM_MANUSCRIPT.md").write_text(
            original,encoding="utf8")
    information["real_model_calls_in_this_arm"]=sum(
        row["stage"].startswith(("CONTROL_","TREATMENT_"))
        and (row["stage"].startswith("TREATMENT_")==reader_first)
        for row in writer.events)
    save(arm/"STATUS.json",information)
    print(json.dumps({
        "arm":name,"status":information["status"],
        "model_choice":information.get("author_decision"),
        "reader_hypotheses":len(
            information.get("reader_report",{}).get("inferred_links",[])
            if isinstance(information.get("reader_report"),dict) else []),
        "actual_text_changed":information["approved_as_provisional_source"],
        "new_model_calls":information["real_model_calls_in_this_arm"],
        "error":information.get("reason_code"),
    },ensure_ascii=False),flush=True)
    return information

def run():
    if OUT.exists():
        raise RuntimeError("WF_NEW_REAL_OUT_ALREADY_EXISTS_NO_REPEAT")
    OUT.mkdir(parents=True)
    (OUT/"provider-wires").mkdir()
    (OUT/"SYNTHETIC_SEED_NOT_REAL_NOVEL.md").write_text(
        SEED,encoding="utf8")
    status={
        "format":"wf.real-new-scene-writer-reader-first-comparison.v1",
        "status":"SOURCE_AND_MODEL_NOT_YET_CALLED",
        "project":PROJECT,"seed_sha256":h(SEED),
        "new_scenario_not_r2_or_previous_father_bridge":True,
        "original_same_story_for_both_arms":True,
        "model":MODEL,
        "no_other_model_or_trainer":True,
        "max_real_model_requests":MAX_CALLS,
        "max_output_tokens_reserved":FULL_MAX_RESERVED,
        "network_retries":0,"canon_writes":0,"R2_writes":0,
        "main_or_railway_deployed":False,
        "literary_quality_verified":False,
        "independent_human_blind_review_performed":False,
    }
    writer=None
    db=None
    try:
        require_external_runtime()
        secret=os.environ.get("DEEPSEEK_API_KEY")
        if not isinstance(secret,str) or len(secret)<16:
            raise RuntimeError("WF_NEW_REAL_EXISTING_DEEPSEEK_KEY_MISSING")
        writer=SameActualWriter(secret)
        with TemporaryDirectory(prefix="wf-new-one-real-G-") as tmp:
            root=Path(tmp)
            snapshot=fresh_neutral_published_snapshot(root/"neutral.sqlite")
            db=WriterForgeDB(root/"neutral.sqlite")
            db.conn.execute(
                "UPDATE xuehai_entries SET genre=? WHERE work_id=?",
                (GENRE,"v111-neutral-fixture"))
            db.conn.commit()
            rt=RuntimeEngine();rt.enter_write(snapshot)
            graph=new_graph(project_id=PROJECT,scene_id=SCENE)
            graph=advance_graph(graph,project_id=PROJECT,
                                scene_id=SCENE,chapter_index=1,
                                prose=SEED,events=())
            graph=record_chapter_memory(
                graph,project_id=PROJECT,scene_id=SCENE,
                chapter_index=1,
                source_path=str(OUT/"SYNTHETIC_SEED_NOT_REAL_NOVEL.md"),
                prose=SEED)
            previous=external_temporal_step(SEED,cast=CAST)
            resume=make_resume(
                project_id=PROJECT,scene_id=SCENE,
                chapter_index=1,checkpoint=previous,
                unified_narrative_core=graph)
            helper=InvisibleWritingAssist(
                db,rt,PROJECT,SCENE,GOAL,model=MODEL,api_base=API,
                source_genre=GENRE)
            next_call=0
            def real_g_adapter(packet,*,model,api_base,max_tokens,**kwargs):
                nonlocal next_call
                if (model!=MODEL or api_base!=API or kwargs or
                    next_call>=len(G_STAGES)):
                    raise RuntimeError("WF_NEW_REAL_ORIGINAL_G_STAGE_UNEXPECTED")
                stage=G_STAGES[next_call]
                if max_tokens!=TOKENS_BY_STAGE[stage]:
                    raise RuntimeError("WF_NEW_REAL_ORIGINAL_G_TOKEN_CAP_CHANGED")
                next_call+=1
                return writer.call(stage,packet,max_tokens=max_tokens)

            baseline_root=root/"G-original"
            try:
                with patch("writerforge.writing_assist.local_chat_completion",
                           side_effect=real_g_adapter):
                    baseline=AutonomousWriting(helper).run(
                        outline=OUTLINE,chapter_goals=[GOAL],
                        output_dir=baseline_root,
                        draft_mode="continuity_guard",
                        resume_story_checkpoint=resume,
                        literary_progression_mode="baseline")
            finally:
                # Even if the real novel fails a strict source check, copy
                # all available raw responses and bad G evidence before
                # the temporary context is destroyed. No success fabrication.
                if baseline_root.exists():
                    shutil.copytree(baseline_root,OUT/"G-private-raw-record",
                                    dirs_exist_ok=True)
            status["actual_G_original_provider_calls"]=next_call
            if not isinstance(baseline,dict):
                raise RuntimeError("WF_NEW_REAL_ORIGINAL_G_NOT_VALID")
            item=baseline["chapters"][0]
            manuscript=Path(item["candidate"]).read_text("utf8")
            (OUT/"G_ACTUAL_ORIGINAL_CHAPTER.md").write_text(
                manuscript,encoding="utf8")
            status.update({
                "actual_wf_G_original_generated":True,
                "actual_wf_G_chapter_index":item["story_chapter_index"],
                "actual_wf_G_original_chapter_sha256":h(manuscript),
                "actual_wf_G_source_trace_passed":True,
                "actual_wf_G_canon_writes":baseline.get(
                    "canonical_fact_writes"),
                "actual_wf_G_literary_quality_verified":False,
            })
            turns_obj=json.loads(Path(item["turn_outline"]).read_text("utf8"))
            beats=turns_obj["candidate_turns"]
            if not isinstance(beats,list) or len(beats)!=2:
                raise RuntimeError("WF_NEW_REAL_BEAT_SOURCE_NOT_TWO")
            chosen=beats[0]
            raw_source=(Path(baseline["job_dir"])/
                        "chapter-001-turn-01-raw.json").read_text("utf8")
            check_turn(raw_source,chosen,mode="causal_guard",accepted=())
            pristine=_decode_json(raw_source)["prose"].strip()
            (OUT/"TRUE_IDENTICAL_FIRST_TURN_SOURCE.md").write_text(
                pristine,encoding="utf8")
            (OUT/"TRUE_ORIGINAL_TURN_ENVELOPE.json").write_text(
                raw_source,encoding="utf8")
            save(OUT/"ACTUAL_WF_BEAT_SOURCE.json",chosen)
            status["single_source_for_control_and_treatment"]=h(pristine)
            # SAME pristine source; different reviewer method. The AI can
            # say MOVE_ON in EITHER arm, no mandatory story edits.
            control=try_review_arm(
                name="control_author_without_reader",writer=writer,
                source_raw=raw_source,beat=chosen,
                checkpoint=previous,graph=graph,reader_first=False)
            treatment=try_review_arm(
                name="treatment_reader_first_then_author",writer=writer,
                source_raw=raw_source,beat=chosen,
                checkpoint=previous,graph=graph,reader_first=True)
            status["control"]=control
            status["reader_first_treatment"]=treatment
            # Anonymized for human evaluation; these are exact source
            # bytes from real actual writer results, NOT host rewritten.
            entries=[("X1",pristine),
                     ("X2",(OUT/"control_author_without_reader"/
                            "FINAL_UNACCEPTED_ARM_MANUSCRIPT.md").read_text("utf8")),
                     ("X3",(OUT/"treatment_reader_first_then_author"/
                            "FINAL_UNACCEPTED_ARM_MANUSCRIPT.md").read_text("utf8"))]
            for alias,text in entries:
                (OUT/f"BLIND_{alias}.md").write_text(text,encoding="utf8")
            save(OUT/"BLIND_REVEAL_AFTER_READING.json",{
                "X1":"G original selected turn",
                "X2":"same-model direct author-review candidate",
                "X3":"same-model reader-first author-review candidate",
                "identical_texts_are_possible":True,
                "literary_superiority_not_verified":True})
            status["blind_candidates_created"]=3
            status["true_different_candidate_count"]=len(set(v for _,v in entries))
            status["status"]="G_REAL_SOURCE_AND_TWO_AUTHENTIC_REVIEW_ARMS_SAVED"
    except Exception as exc:
        status["status"]="REAL_G_OR_REVIEW_BLOCKED_SOURCE_PRESERVED"
        status["error_code"]=code(exc)
    finally:
        status["actual_provider_calls"]=(
            writer.budget.calls_reserved if writer is not None else 0)
        status["provider_usage_reported"]=(
            writer.budget.public_receipt() if writer is not None else {})
        status["real_model_evidence"]=writer.events if writer is not None else []
        status["no_model_retries_or_literary_scoring"]=True
        status["accepted_prose_rows_at_end"]=(
            db.conn.execute("SELECT count(*) FROM accepted_prose").fetchone()[0]
            if db is not None else None)
        if db is not None:
            db.close()
        save(OUT/"STATUS.json",status)
        print(json.dumps({
            "status":status["status"],
            "actual_calls":status["actual_provider_calls"],
            "max_calls":MAX_CALLS,
            "source":status.get("single_source_for_control_and_treatment"),
            "original_real_G":status.get("actual_wf_G_original_generated"),
            "control_decision":status.get("control",{}).get("author_decision"),
            "treatment_decision":status.get(
                "reader_first_treatment",{}).get("author_decision"),
            "control_changed":status.get("control",{}).get(
                "approved_as_provisional_source"),
            "treatment_changed":status.get(
                "reader_first_treatment",{}).get("approved_as_provisional_source"),
            "new_unique_drafts":status.get("true_different_candidate_count"),
            "error":status.get("error_code"),
        },ensure_ascii=False),flush=True)
    return status

if __name__=="__main__":
    try:
        run()
    except Exception as exc:
        print(json.dumps({
            "stage":"REAL_NEW_G_COMPARISON_PREFLIGHT_BLOCKED",
            "error_code":code(exc),
            "no_unapproved_training":True,
        },ensure_ascii=False),flush=True)
        sys.exit(2)
