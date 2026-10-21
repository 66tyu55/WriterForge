"""V108: ONE real WF E/F causal-writing smoke experiment; no critic model.

Not a formal literary blind benchmark. Same frozen, WF-model-chosen TWO
event beats and V104's already-WF-selected deep-sea scene in both arms.
Production AutonomousWriting.run is executed verbatim, with its *local*
completion transport replaced ONLY at the call boundary by the already
registered single WF DeepSeekFlashModel. Everything the model returns is
private-R2 sealed before V105 or V102 parse/validation. No human model
rewrites, no external second critic, no retry on failures or timeouts.

A minimal synthetic published snapshot satisfies the preexisting local
VerifiedWritingFlow interface, not a user's 15 real trained chapters. Its
neutral placeholder is NOT literary training. Hence results evaluate WF's
code + DeepSeek base provider in two modes, not autonomous learned quality.
"""
from __future__ import annotations

from contextlib import ExitStack
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os
import re

from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.writing_assist import (
    AutonomousWriting,InvisibleWritingAssist,WritingExecutionError,
)
from writerforge.v96_causal_turns import parse_turn_outline,V96CausalDraftError
from writerforge.v79_provisional_r2_cas_journal import WFProvisionalR2CASJournal
from writerforge.deepseek_flash_model import (
    DeepSeekFlashModel,FlashBudget,DeepSeekFlashError,
)
from writerforge.v104_self_scene_protocol import encode,digest
from writerforge.v105_forward_horizon import V105FutureCausalityError
from writerforge.v107_outline_observation import observe_shared_two_turns

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
EXAM="WF-V108-E-VS-F-NEW-LOCKED-ONE-SHOT-20261021"
OLD_V104_SCENE="s01"
OLD_V104_MANIFEST="8de70e6d2276d617e9e84769c9f0c076963d4f71c7e23fbf1675490603313003"
MODEL="deepseek-flash"
MAX_CALLS=9
MAX_OUTPUT=11600
MAX_TOTAL=150000
ROLE="self_scene_writing"
FROZEN_ORDER=("emotion_rolling","foresight_rolling")
SCENE=(
    "WF在V104自己选过的深海采矿站：未知生物堵塞空气滤网，"
    "两名维修工被困B舱，站长面对全站其余人员的生命风险。"
    "工程师只能根据当时掌握的测量与设备实际能力行动。"
    "这次只创作独立全新文本，不续写V104原稿，"
    "也不复制任何原文中的句子。"
)
# Unlike a hidden solution, these are common world *constraints* to both
# writing arms. F additionally receives the same assumptions symbolically.
COMMON_HARD_FACTS=(
    "世界的硬限制：矿钻只由全站主电网供电，没有已经证实的独立电池；"
    "全站切电后，矿钻不可在没有新增能源的情况下自行空转。"
    "通风和生命维持也依赖供电，B舱门若封死会影响被困者。"
    "某些设备是否有备用储能目前未知，作者不可突然宣布已证实。"
)
CHAPTER_GOAL="这一小章：人物需要在氧气下降时实际选择路线，并让选择影响被困者与下一步行动"
HORIZON_PINS={
    "power:station":"on",
    "drill:supply":"mains_only",
    # No battery pin: "unknown" is not evidence that a battery exists.
}
TARGET_MIN=250
TARGET_MAX=3000

PLANNER_SYS=(
    "你是WriterForge唯一接入的创作执行模型。"
    "这次仅制定两个自然叙事事件，不输出小说正文；"
    "不要制造标准答案、审稿或逐项评分。"
    "只输出严格JSON对象。"
)
RUN_SYS=(
    "你是WriterForge自身的小说执行模型。"
    "只执行当前WF程序发来的一个请求，"
    "不额外引用别人的小说、不编辑另一组输出、不要自评。"
    "每次严格输出JSON对象，不带Markdown。"
)

def report(record):
    print(json.dumps(record,ensure_ascii=False,sort_keys=True,
                     separators=(",",":"),allow_nan=False),flush=True)

def require(ok,reason):
    if not ok:raise ValueError(reason)

def audit_sha(*,cas,pointer):
    require(type(pointer) is str and re.fullmatch("[0-9a-f]{64}",pointer),
            "WF106_INVALID_CAS_POINTER")
    raw=cas._get_content(pointer)
    require(digest(raw)==pointer,"WF106_REMOTE_CAS_CORRUPTED")
    return raw

def seal(cas,obj,why):
    raw=encode(obj)
    require(len(raw)<=250000,"WF106_REMOTE_BLOB_BOUND_EXCEEDED")
    ptr,_=cas._put_content(raw)
    require(audit_sha(cas=cas,pointer=ptr)==raw,why)
    return ptr

def freeze():
    return {
        "format":"wf.exam.v108.new-one-shot.ef-write.precommit",
        "new_experiment_not_replay_of_v106":True,
        "v106_failed_response_unmodified_and_unrecovered":True,
        "id":EXAM,
        "v104_source_scene_only":OLD_V104_SCENE,
        "v104_original_evidence_manifest_sha256":OLD_V104_MANIFEST,
        "old_v104_prose_not_transmitted":True,
        "source_outline_sha256":digest(SCENE.encode("utf8")),
        "known_constraints_sha256":digest(COMMON_HARD_FACTS.encode("utf8")),
        "locked_chapter_goal_sha256":digest(CHAPTER_GOAL.encode("utf8")),
        "pins_sha256":digest(encode(HORIZON_PINS)),
        "study_evidence":"SYNTHETIC_NEUTRAL_PUBLISHED_SNAPSHOT_NOT_15_REAL_CHAPTERS",
        "experiment_run_modes":list(FROZEN_ORDER),
        "same_self_selected_two_event_outline":True,
        "same_model":MODEL,
        "max_actual_provider_calls":MAX_CALLS,
        "max_reserved_completion_tokens":MAX_OUTPUT,
        "max_total_conservative_tokens":MAX_TOTAL,
        "no_retry_even_if_incomplete":True,
        "raw_answers_R2_before_source_validation":True,
        "external_literary_judge_model_calls":0,
        "quality_improvement_proven":False,
        "actual_E_F_token_cost_can_differ":True,
        "not_formal_blind_review":True,
        "original_15_chapters_are_not_part_of_synthetic_snapshot":True,
        "all_drafts_unaccepted":True,
        "old_15_chapters_untouched":True,
        "new_training_chapters":0,
        "no_r2_books_download":True,
    }

def fake_but_published_snapshot(path):
    """Tiny NEUTRAL fixture. Not actual book experience or historical R2."""
    db=WriterForgeDB(path)
    sample="这是一条用于核验软件连接的中性短句，不具有文学教学价值。"
    ss=digest(sample.encode("utf8"))
    cur=db.conn.execute(
        "INSERT INTO snapshots(parent_id,status,layout,note) "
        "VALUES(NULL,'published','full','synthetic bridge fixture only')")
    sid=int(cur.lastrowid)
    db.conn.execute(
        "INSERT INTO studied_works(work_id,title,source_uri,source_sha256,chapter_count) "
        "VALUES(?,?,?,?,?)",
        ("v108-fixture","中性软件连接测试","synthetic://v108-no-book",ss,1))
    db.conn.execute(
        "INSERT INTO source_spans(work_id,chapter,paragraph,sentence,excerpt,"
        "source_sha256,tracks_json,craft_json) VALUES(?,?,?,?,?,?,?,?)",
        ("v108-fixture",1,1,1,sample,ss,"{}","{}"))
    db.conn.execute(
        "INSERT INTO studied_chapters(work_id,chapter,chapter_sha256,heading,"
        "source_spans,retrieval_entries,snapshot_id) VALUES(?,?,?,?,?,?,?)",
        ("v108-fixture",1,ss,"synthetic",1,1,sid))
    db.conn.execute(
        "INSERT INTO xuehai_entries(snapshot_id,work_id,chapter,paragraph,"
        "sentence,text,library_class,culture,genre,source_role,function,"
        "effect,method_cluster,source_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (sid,"v108-fixture",1,1,1,sample,"synthetic_only","中国","科幻",
         "neutral","dialogue","none","no_training",ss))
    db.conn.commit()
    db.close()
    return sid

def make_outline_request():
    return (
       "【WF先自主提出两组共同使用的两个真实叙事事件；只给字段语法，不给剧情答案】\n"+
       SCENE+"\n"+COMMON_HARD_FACTS+
       "\n你必须自主选择人物、动作目标、冲突走向；"
       "此时不写正文、不写预定结局或文学评分。"
       "根JSON恰好一个键turns，恰好两个事件对象。"
       "每个事件恰好含id、kind、actor、goal、causal_parent、craft_focus这六个键。"
       "请严格遵守：t01为action或decision，causal_parent必须是null；"
       "t02为action或decision，causal_parent必须是字符串t01。"
       "goal必须至少八个字符；actor必须是出场人物的真实称谓。"
       "craft_focus必须是JSON数组，不是一个字符串；"
       "只可从action/detail/dialogue/interiority/pacing/restraint中选0至2项。"
       "\n以下仅示范字段数据类型，请自行替换人物、动作、目标和技法，"
       "示例中的人物/事件不代表本题答案："
       '{"turns":[{"id":"t01","kind":"action","actor":"角色一",'
       '"goal":"请自行构想具体可执行的行动目标",'
       '"causal_parent":null,"craft_focus":["action"]},'
       '{"id":"t02","kind":"decision","actor":"角色二",'
       '"goal":"请根据已写出的前一步后果决定下一步目标",'
       '"causal_parent":"t01","craft_focus":["dialogue"]}]}'
       "除此之外不可输出任何字段或Markdown。"
    )

def summarize(body):
    return {
        "actual_characters":len(body),
        "prose_sha256":digest(body.encode("utf8")),
        "within_requested_smoke_range":TARGET_MIN<=len(body)<=TARGET_MAX,
        "real_literary_causality_verified":False,
    }

def real():
    for key in ("DEEPSEEK_API_KEY","WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN"):
        require(bool(os.environ.get(key)),"WF106_EXISTING_API_CREDENTIAL_MISSING")
    cas=WFProvisionalR2CASJournal(endpoint=ENDPOINT)
    cas.require_writer_ready()
    frozen=encode(freeze())
    run_sha,first=cas._put_content(frozen)
    require(first is True and run_sha==digest(frozen) and
            audit_sha(cas=cas,pointer=run_sha)==frozen,
            "WF106_EXAM_ALREADY_RESERVED_NO_DOUBLE_BILLING")
    budget=FlashBudget(max_calls=MAX_CALLS,
                       max_reserved_output_tokens=MAX_OUTPUT,
                       max_total_tokens=MAX_TOTAL)
    wf_model=DeepSeekFlashModel(budget=budget,timeout_seconds=120)
    replies=[]
    call_index=0
    def provider(stage,mode,system,prompt,out_limit):
        nonlocal call_index
        require(type(prompt) is str and 0<len(prompt)<=11000
                and type(out_limit) is int and out_limit>=50 and
                call_index<MAX_CALLS,
                "WF106_CALL_LIMIT_OR_PROMPT_SHAPE")
        call_index+=1
        attempt={
            "format":"wf.exam.v108.before-model-request",
            "precommit_sha256":run_sha,
            "call_no":call_index,"stage":stage,"arm":mode,
            "prompt_sha256":digest(prompt.encode("utf8")),
            "system_sha256":digest(system.encode("utf8")),
            "max_output_tokens":out_limit,
            "role":ROLE,
            "no_auto_retry":True,
        }
        # One permanent attempt CAS before a potentially billed request.
        raw_attempt=encode(attempt)
        ptr,was_new=cas._put_content(raw_attempt)
        require(was_new is True and audit_sha(cas=cas,pointer=ptr)==raw_attempt,
                "WF106_ORIGINAL_REQUEST_SLOT_REUSED_REFUSE_REBILL")
        report({"status":"WF107_SINGLE_REQUEST_INTENT_R2_SEALED",
                "precommit_sha256":run_sha,"call_no":call_index,
                "mode":mode,"stage":stage,
                "immutable_attempt_cas_sha256":ptr,
                "model_response_not_yet_received":True,
                "no_retry":True})
        reply=wf_model.ask_json(role=ROLE,system=system,user=prompt,
                                max_tokens=out_limit)
        record={
            "format":"wf.exam.v108.single-unmodified-model-response",
            "original_precommit_sha256":run_sha,
            "attempt_sha256":ptr,
            "stage":stage,"arm":mode,
            "model":MODEL,
            "original_decoded_json":reply,
            "source_edit_or_automatic_fix":False,
        }
        sha=seal(cas,record,"WF106_ORIGINAL_MODEL_REPLY_NOT_READABLE")
        # An orphaned CAS pointer is not genuinely recoverable. Announce
        # its SHA BEFORE ANY V96 or V105 validation can raise.
        report({"status":"WF107_RAW_MODEL_REPLY_R2_SEALED_BEFORE_VALIDATION",
                "precommit_sha256":run_sha,
                "raw_original_model_reply_cas_sha256":sha,
                "request_attempt_cas_sha256":ptr,
                "stage":stage,"arm":mode,"call_no":call_index,
                "new_model_calls_after_this_record":0})
        replies.append({
            "no":call_index,"stage":stage,"arm":mode,
            "raw_reply_cas_sha256":sha,
            "request_intent_cas_sha256":ptr,
            "raw_response_sha256":digest(encode(reply)),
        })
        return reply

    raw_outline=provider("frozen_shared_turn_outline","both",
                         PLANNER_SYS,make_outline_request(),1450)
    # Diagnose student's ORIGINAL JSON without canonicalizing its creative
    # answer. Keep V96 strict; a red student response remains red forever.
    diagnostic=observe_shared_two_turns(raw_outline)
    if not diagnostic["exact_v96_valid"] or (
            type(raw_outline) is not dict or
            type(raw_outline.get("turns")) is not list or
            len(raw_outline["turns"])!=2):
        evidence={
            "format":"wf.exam.v107.original-outline-red-evidence",
            "precommit_sha256":run_sha,
            "raw_original_model_reply_cas_sha256":
                replies[-1]["raw_reply_cas_sha256"],
            "diagnostic":diagnostic,
            "V108_original_model_reply_never_edited":True,
            "no_retries_or_manual_corrections":True,
        }
        red_sha=seal(cas,evidence,
                     "WF107_INVALID_OUTLINE_EVIDENCE_R2_NOT_RECOVERABLE")
        report({"status":"WF107_STRICT_SHARED_OUTLINE_REJECTED_WITH_EVIDENCE",
                "red_evidence_cas_sha256":red_sha,
                "original_model_reply_cas_sha256":
                    replies[-1]["raw_reply_cas_sha256"],
                "field_level_violations":diagnostic["violations"],
                "no_model_retry":True})
        raise V96CausalDraftError("WF96_TURN_PLAN_FIELDS_ID_OR_CRAFT_INVALID")
    outline=parse_turn_outline(json.dumps(
        raw_outline,ensure_ascii=False,separators=(",",":")))
    require(len(outline)==2 and
            outline[0]["id"]=="t01" and
            outline[1]["id"]=="t02",
            "WF106_SHARED_2_EVENT_OUTLINE_NOT_VALID")
    shared_sha=seal(cas,{
        "format":"wf.exam.v108.shared-original-outline",
        "original_reply_cas_sha256":replies[-1]["raw_reply_cas_sha256"],
        "two_model_generated_beats":outline,
        "source_scene_sha256":digest(SCENE.encode("utf8")),
        "same_for_both_arms":True,
    },"WF106_SHARED_BEATS_NOT_RECOVERABLE")
    # Textually and symbolically BOTH arms receive identical world constraints.
    cast="、".join(dict.fromkeys(b["actor"] for b in outline))
    common_outline=(
        SCENE+"\n"+COMMON_HARD_FACTS+
        "\nWF本次提前自主选出将出场的人物："+cast+"。"
        "\n这些是给两个对照写法完全相同的客观限制，不是故事结局。"
    )
    report({"status":"WF106_COMMON_TWO_TURN_BEATS_LOCKED",
            "cas_sha256":shared_sha,
            "model_calls":call_index,
            "beat_count":2,
            "same_world_both_arms":True})
    outcomes=[]
    # Each arm starts from an empty local project with identical neutral
    # synthetic published source. No previous arm's prose is ever shown.
    for arm in FROZEN_ORDER:
        with TemporaryDirectory(prefix="wf106-ephemeral-") as root:
            root=Path(root)
            dbpath=root/"synthetic-source.sqlite"
            snapshot=fake_but_published_snapshot(dbpath)
            db=WriterForgeDB(dbpath)
            rt=RuntimeEngine()
            rt.enter_write(snapshot)
            assist=InvisibleWritingAssist(db,rt,
                "v108-experiment-only",f"v108-{arm}",CHAPTER_GOAL,
                model=MODEL,api_base="http://127.0.0.1:1234/v1",
                source_genre="科幻")
            start_count=call_index
            def wf_only_adapter(packet,*,model,api_base,max_tokens,
                                **kwargs):
                require(model==MODEL and
                        packet.project_id=="v108-experiment-only" and
                        kwargs.get("system_role_instruction") is None,
                        "WF106_HIDDEN_WRITING_TRANSPORT_OR_MODEL_CHANGED")
                return json.dumps(provider(
                    "actual_AutonomousWriting_call",arm,RUN_SYS,
                    packet.prompt,max_tokens),
                    ensure_ascii=False,separators=(",",":"))
            try:
                with patch("writerforge.writing_assist.local_chat_completion",
                           side_effect=wf_only_adapter):
                    result=AutonomousWriting(assist).run(
                        outline=common_outline,
                        chapter_goals=[CHAPTER_GOAL],
                        output_dir=root/"private-candidates",
                        draft_mode=arm,
                        frozen_turn_outlines=(
                            json.dumps({"turns":outline},
                                       ensure_ascii=False,separators=(",",":")),),
                        **({"forward_author_pinned_facts":HORIZON_PINS}
                           if arm=="foresight_rolling" else {}),
                    )
                chapter=result["chapters"][0]
                body=Path(chapter["candidate"]).read_text("utf8")
                details=summarize(body)
                requires_plan=(arm=="foresight_rolling")
                evidence={
                    "format":"wf.exam.v108.unaccepted-real-writing-arm",
                    "arm":arm,
                    "expected_same_two_turns":True,
                    "raw_shared_outline_cas_sha256":shared_sha,
                    "all_model_replies_sealed_separately":True,
                    "body":body,
                    "prose":details,
                    "v105_planner":(
                        json.loads(Path(chapter["v105_horizon_plan"]).read_text("utf8"))
                        if requires_plan else None),
                    "v105_open_debts":(
                        json.loads(Path(chapter["v105_candidate_checkpoint"]).read_text("utf8"))
                        if requires_plan else None),
                    "old_V102_emotional_candidate":(
                        json.loads(Path(chapter["v102_emotional_causality"]).read_text("utf8"))),
                    "actual_full_story_generated_by_WF_original_loop":True,
                    "story_not_author_accepted":True,
                    "human_literary_review":"NOT_PERFORMED",
                }
                response_sha=seal(
                    cas,evidence,"WF106_ORIGINAL_AUTONOMOUS_STORY_NOT_R2")
                outcome={
                    "arm":arm,"status":"CANDIDATE_SAVED",
                    "private_full_evidence_cas_sha256":response_sha,
                    "real_prose_characters":details["actual_characters"],
                    "original_prose_sha256":details["prose_sha256"],
                    "literary_truth":"UNDETERMINED",
                }
            except Exception as exc:
                message=str(exc)
                if not re.fullmatch(
                    r"(?:WF105|WF106|WF98|WF96|WF102|WF_FLASH|WF_)[A-Za-z0-9_]{1,160}",
                    message):
                    message="WF106_REAL_WRITING_MODE_FAILED_UNCLASSIFIED"
                outcome={
                    "arm":arm,"status":"ORIGINAL_MODE_REJECTED",
                    "original_error_code":message,
                    "no_auto_retry":True,
                    "writer_core_called":True,
                    "raw_successful_model_answers_still_private":True,
                    "literary_truth":"UNDETERMINED",
                }
            finally:
                accepted=db.conn.execute("SELECT COUNT(*) FROM accepted_prose").fetchone()[0]
                db.close()
                require(accepted==0,"WF106_ACCIDENTAL_CANON_AUTHOR_ACCEPTANCE")
            outcome["real_calls_in_mode"]=call_index-start_count
            outcomes.append(outcome)
            report({"status":"WF106_ONE_REAL_WF_ARM_FINISHED",
                    **outcome,"total_requests":call_index})
    manifest={
        "format":"wf.exam.v108.original-real-E-F-smoke",
        "precommit_sha256":run_sha,
        "frozen_shared_two_turns_cas_sha256":shared_sha,
        "arms":outcomes,
        "all_actual_model_call_receipts":replies,
        "provider_usage":budget.public_receipt(),
        "total_real_provider_requests":call_index,
        "upper_limit":MAX_CALLS,
        "old_v104_source_prose_used":False,
        "any_second_literary_model_used":False,
        "author_review":"NOT_PERFORMED",
        "prose_length_comparison_scored":False,
        "literary_quality_improvement":"UNDETERMINED",
        "unpaired_model_token_budgets":True,
        "production_code_full_E_F_entrypoint_used":True,
        "published_book_training_was_synthetic_only":True,
        "factual_and_literary_work_not_author_accepted":True,
        "new_trained_real_chapters":0,
        "historical_failure_records_unchanged":True,
    }
    msha=seal(cas,manifest,"WF106_REAL_SMOKE_MANIFEST_NOT_READABLE")
    report({"status":"WF106_REAL_E_F_CAUSAL_SMOKE_PRIVATE_R2_SAVED",
            "manifest_cas_sha256":msha,
            "precommit_cas_sha256":run_sha,
            "same_WF_two_turns_sha256":shared_sha,
            "real_provider_requests":call_index,
            "prompt_tokens":budget.prompt_tokens_reported,
            "completion_tokens":budget.completion_tokens_reported,
            "arm_results":outcomes,
            "other_models_called":0,
            "original_user_books_read":0,
            "author_accepted_chapters":0,
            "literary_effect_unproven":True})
    return 0

if __name__=="__main__":
    report({"status":"WF106_REAL_E_F_SCOPED_EXAM_START",
            "max_calls":MAX_CALLS,
            "no_auto_retry":True,
            "not_user_private_novel":True,
            "only_WF_registered_DeepSeek_provider":True})
    try:ret=real()
    except Exception as exc:
        status=str(exc)
        if not re.fullmatch(r"(?:WF105|WF106|WF_FLASH|WF98|WF96|WF102|WF_V79|WF_INDEX|WF_LEARN)_[A-Za-z0-9_]{1,170}",status):
            status="WF106_FAIL_CLOSED_DO_NOT_REDEPLOY_WITH_SAME_BUDGET"
        report({"status":"WF106_REAL_E_F_EXAM_STOPPED_NO_RETRY",
                "error_code":status,
                "paid_request_may_have_been_sent":True,
                "no_canon_writes":True})
        ret=1
    report({"status":"WF106_EXAM_EXIT","code":ret})
    raise SystemExit(ret)
