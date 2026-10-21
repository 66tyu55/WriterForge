"""V114 ONE NEW real WF source-memory writing smoke; GitHub only.

User-approved request: original Chinese 1000-character Xuanhuan chase and
fight; exactly the same base question as V113. The SINGLE registered official
DeepSeek Flash executes WF's actual continuity_guard segmented writing.
V113 old four paid calls remain frozen, never repeated.

The WF student itself chooses two beats in one (capped) API request, then
AutonomousWriting invokes its original chapter plan and two actual writing
turns with the pinned MIT Novel Studio temporal reducer between turns.

No second critic/model, no human example sentences, no post-hoc rewrite.
Every received provider HTTP wire and decoded JSON is CAS saved before V96
or story-state validation; a failure never auto-retries or becomes CANON.
This is exploratory: non-symmetric against old V113, no literary winner.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json,os,re
from hashlib import sha256

from experiments.v114_github_r2_cas import GitHubS3CAS
from experiments.v111_peer.neutral_bridge import fresh_neutral_published_snapshot
from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget
from writerforge.v96_causal_turns import parse_turn_outline
from writerforge.writing_assist import AutonomousWriting,InvisibleWritingAssist
from writerforge.v114_external_story_state import require_external_runtime
from writerforge.v114_continuity_memory import packed,hashb

TASK="给我一个追逐打斗的玄幻1000字"
EXAM="WF-V114-REAL-CONTINUITY-AND-NOVEL-STUDIO-20261021"
MODEL="deepseek-flash"
MAX_CALLS=4
BEAT_TOKENS=1450
PLAN_TOKENS=650
TURN_TOKENS=1450
MAX_OUTPUT=BEAT_TOKENS+PLAN_TOKENS+2*TURN_TOKENS
MAX_TOTAL=135000
ROLE="self_scene_writing"
MAX_WIRE=220000

def require(cond,code):
    if not cond:raise ValueError(code)
def print_receipt(doc):
    print(json.dumps(doc,ensure_ascii=False,sort_keys=True,
                     separators=(",",":"),allow_nan=False),flush=True)

def precommit():
    return {
        "format":"wf.exam.v114.real-source-memory-one-shot",
        "exam":EXAM,"user_exact_task":TASK,"model":MODEL,
        "source_branch":"v114-chase-live-state-and-oss-fallback",
        "writer_actual_WF_route":"AutonomousWriting.continuity_guard",
        "external_memory_core":"bbaz123/novel-studio temporal reducer",
        "external_memory_pinned_upstream_commit":"b585a9ca4ce474fe2471bf3bb7f8c284c6e4104a",
        "old_V113_original_951_char_body_never_sent_to_model":True,
        "student_autonomously_selects_own_two_events":True,
        "only_one_registered_model":True,
        "max_model_requests":MAX_CALLS,
        "max_reserved_model_output":MAX_OUTPUT,
        "max_conservative_budget":MAX_TOTAL,
        "same_base_question_not_equal_compute_budget":True,
        "original_wire_R2_before_JSON_parse":True,
        "original_decoded_R2_before_WF_validation":True,
        "no_auto_retry_or_author_prose_rewrite":True,
        "old_fifteen_chapters_not_finetuning_evidence":True,
        "synthetic_neutral_snapshot_used":True,
        "no_external_rating_model":True,"no_factjournal_writes":True,
        "human_independent_literary_review":"NOT_PERFORMED",
        "acceptance_and_skill_graduation":"LOCKED",
    }

def read(cas,sha):
    require(type(sha) is str and re.fullmatch("[0-9a-f]{64}",sha) is not None,
            "WF114_WIRE_CAS_POINTER_NOT_SHA")
    raw=cas._get_content(sha)
    require(hashb(raw)==sha,"WF114_CAS_FRESH_READBACK_MISMATCH")
    return raw

def write(cas,item,reason):
    b=packed(item)
    sha,_=cas._put_content(b)
    require(read(cas,sha)==b,reason)
    return sha

PLAN_SYSTEM=(
    "你是WriterForge自己的小说事件规划环节；这次仅构思2段相继发生的"
    "玄幻追逐打斗事件，不撰写正文、不能引用任何现成小说或其他模型答案。"
    "两个事件的具体人物、争夺原因、地点、招式和结局全部由你自主思考。"
    "严格仅输出JSON对象，恰好根字段turns。"
)
PLAN_PROMPT=(
    TASK+
    "\n只给出两个相连事件的自主构想，目标是最后写成约1000字自然小说。"
    "turns恰好2项，每项必须有id,kind,actor,goal,causal_parent,craft_focus六个字段。"
    "第一个id=t01, kind=action或decision, causal_parent=null；"
    "第二个id=t02, kind=action或decision, causal_parent=t01。"
    "actor必须是真实出场的人物名字，goal必须是具体可实行的行动，至少8字。"
    "craft_focus必须为数组0-2个，不允许字符串，只可用"
    "action/detail/dialogue/interiority/pacing/restraint。"
    "不输出文学建议、自评、小说原文、额外说明或Markdown。"
)
CHAPTER_SYSTEM=(
    "你是WriterForge自己的文学创作程序。章计划请严格遵循收到的"
    "objective/conflict/decision/outcome/pov/needs字段结构，不添加无关内容。"
    "仅依照当前输入故事任务自行组织人物动机、矛盾与冲突。"
)
TURN_SYSTEM=(
    "你是WriterForge独立撰写小说正文的执行模型。仅输出一个JSON对象，"
    "根字段严格为prose和trace。"
    "prose为本段约450-550个中文含标点字符的原创追逐打斗正文，"
    "两段拼接目标1000字；不输出技能说明、分数或写作指导。"
    "trace严格包含action_quote、effect_quote、parent_effect_quote三个键。"
    "前两者必须是本段prose中唯一出现的实际动作和随后真实后果短句；"
    "第1段parent_effect_quote必须为JSON null，"
    "第2段必须引用之前真的写出的后果原句。"
    "有无人物情感、物件交接和法术消耗由故事自身推动。"
    "任何人物、物件、法力改变必须通过实际文字交代，否则保持未知。"
)

def run():
    require(all(os.environ.get(x) for x in (
        "DEEPSEEK_API_KEY","WRITERFORGE_R2_ACCOUNT_ID","WRITERFORGE_R2_BUCKET",
        "WRITERFORGE_R2_ACCESS_KEY_ID","WRITERFORGE_R2_SECRET_ACCESS_KEY")),
        "WF114_ONE_SHOT_GITHUB_SECRET_MISSING")
    require_external_runtime()
    cas=GitHubS3CAS()
    pre=packed(precommit())
    sha,new=cas._put_content(pre)
    require(new is True and sha==hashb(pre) and read(cas,sha)==pre,
            "WF114_EXAM_ALREADY_RESERVED_REFUSE_DOUBLE_BILL")
    budget=FlashBudget(max_calls=MAX_CALLS,
                       max_reserved_output_tokens=MAX_OUTPUT,
                       max_total_tokens=MAX_TOTAL)
    phase={"idx":0,"stage":None,"attempt":None,"wire":None}
    calls=[]

    def wire(raw):
        require(phase["attempt"] and phase["wire"] is None and
                type(raw) is bytes and 0<len(raw)<MAX_WIRE,
                "WF114_PROVIDER_WIRE_NOT_SINGLE_BOUNDED")
        w,_=cas._put_content(raw)
        require(read(cas,w)==raw,"WF114_REAL_PROVIDER_WIRE_NOT_READABLE")
        phase["wire"]=w
        print_receipt({"status":"WF114_WIRE_CAS_BEFORE_DECODE",
                       "slot":phase["idx"],"stage":phase["stage"],
                       "private_wire_sha256":w,"raw_wire_not_logged":True})
    model=DeepSeekFlashModel(budget=budget,timeout_seconds=120,
                            on_response_wire=wire)

    def call(stage,system,body,max_output):
        n=phase["idx"]+1
        require(n<=MAX_CALLS,"WF114_PAID_CALL_LIMIT")
        req={
            "format":"wf.exam.v114.one-before-model-immutable-intent",
            "experiment_sha256":sha,
            "slot":n,"stage":stage,"model":MODEL,
            "system_sha256":hashb(system.encode("utf8")),
            "prompt_sha256":hashb(body.encode("utf8")),
            "max_output":max_output,"no_repeat":True}
        ident=packed(req)
        ptr,created=cas._put_content(ident)
        require(created and read(cas,ptr)==ident,
                "WF114_PAID_CALL_ALREADY_RESERVED")
        phase.update({"idx":n,"stage":stage,"wire":None,"attempt":ptr})
        print_receipt({"status":"WF114_REQUEST_INTENT_R2_LOCKED",
                       "slot":n,"stage":stage,"private_request_sha256":ptr})
        try:
            doc=model.ask_json(
                role=ROLE,system=system,user=body,max_tokens=max_output)
        except Exception as ex:
            safe=str(ex)
            if not safe.startswith("WF_FLASH_"):
                safe="WF114_MODEL_OR_R2_TRANSPORT_FAILED_STOP"
            calls.append({
                "slot":n,"stage":stage,"request_sha256":ptr,
                "wire_sha256":phase["wire"],"decoded_sha256":None,
                "status":"FAILED_OR_UNDECODABLE","reason":safe})
            raise
        require(phase["wire"] is not None,
                "WF114_MODEL_PARSED_BUT_WIRE_MISSING")
        rec={
            "format":"wf.exam.v114.one-model-decoded-original",
            "source_precommit_sha256":sha,
            "wire_sha256":phase["wire"],"intent_sha256":ptr,
            "stage":stage,"student_unmodified_answer":doc,
        }
        d=write(cas,rec,"WF114_PARSED_ORIGINAL_R2_NOT_READABLE")
        calls.append({"slot":n,"stage":stage,
                      "request_sha256":ptr,"wire_sha256":phase["wire"],
                      "decoded_sha256":d,"status":"DECODED_UNJUDGED"})
        print_receipt({"status":"WF114_DECODED_ORIGINAL_BEFORE_ANY_WF_GUARD",
                       "slot":n,"stage":stage,"decoded_cas_sha256":d})
        return doc

    result=None
    try:
        beats_doc=call("WF_SELF_2_BEAT_PLAN",PLAN_SYSTEM,PLAN_PROMPT,BEAT_TOKENS)
        beats=parse_turn_outline(json.dumps(beats_doc,
                         ensure_ascii=False,separators=(",",":")))
        require(len(beats)==2,"WF114_SELF_SCENE_BEATS_NOT_TWO")
        shared=write(cas,{
           "format":"wf.exam.v114.frozen-WF-self-beats",
           "precommit_sha256":sha,
           "original_model_reply_sha256":calls[0]["decoded_sha256"],
           "beats":beats,"author_supplied_story_answer":False,
        },"WF114_FROZEN_BEATS_NOT_R2")
        with TemporaryDirectory(prefix="wf114-source-memory-") as root:
            root=Path(root)
            sqlite=root/"neutral-published.sqlite"
            snap=fresh_neutral_published_snapshot(sqlite)
            db=WriterForgeDB(sqlite)
            rt=RuntimeEngine()
            rt.enter_write(snap)
            helper=InvisibleWritingAssist(
                db,rt,"v114-experiment-only","v114-fantasy-battle",
                TASK,model=MODEL,api_base="http://127.0.0.1:1234/v1",
                source_genre="玄幻")
            def adapter(packet,*,model,api_base,max_tokens,**kwargs):
                require(model==MODEL and not kwargs and
                        packet.project_id=="v114-experiment-only",
                        "WF114_SINGLE_PROVIDER_TRANSPORT_GUARD")
                stage="WF_CHAPTER_PLAN" if phase["idx"]==1 else (
                    "WF_FIRST_SCENE" if phase["idx"]==2 else "WF_SECOND_SCENE")
                required=(PLAN_TOKENS if stage=="WF_CHAPTER_PLAN"
                          else TURN_TOKENS)
                require(max_tokens==required,
                        "WF114_WF_MODEL_CALL_SCHEDULE_CHANGED")
                sys=CHAPTER_SYSTEM if stage=="WF_CHAPTER_PLAN" else TURN_SYSTEM
                reply=call(stage,sys,packet.prompt,max_tokens)
                return json.dumps(reply,ensure_ascii=False,
                                  separators=(",",":"))
            try:
                with patch("writerforge.writing_assist.local_chat_completion",
                           side_effect=adapter):
                    output=AutonomousWriting(helper).run(
                        outline=TASK+"。场景中每件物品与法力都有真实后果。",
                        chapter_goals=[TASK],
                        output_dir=root/"candidates",
                        draft_mode="continuity_guard",
                        frozen_turn_outlines=(
                          json.dumps({"turns":beats},
                                     ensure_ascii=False,
                                     separators=(",",":")),),
                    )
                ch=output["chapters"][0]
                prose=Path(ch["candidate"]).read_text("utf8")
                candidate={
                   "format":"wf.exam.v114.one-full-WF-continuity-prose",
                   "prose":prose,
                   "prose_sha256":hashb(prose.encode("utf8")),
                   "actual_codepoints":len(prose),
                   "body_in_original_model_receipts":True,
                   "wf_continuity_state":json.loads(Path(
                        ch["v114_novel_studio_temporal_state"]).read_text("utf8")),
                   "native_report":json.loads(Path(
                        ch["v114_candidate_item_memory"]).read_text("utf8")),
                   "author_accepted":False,
                   "human_literary_review":"NOT_PERFORMED",
                }
                novel_sha=write(cas,candidate,"WF114_REAL_WF_NOVEL_NOT_R2")
                result={
                    "status":"FULL_CHAPTER_UNACCEPTED",
                    "novel_original_cas_sha256":novel_sha,
                    "prose_sha256":candidate["prose_sha256"],
                    "actual_characters":len(prose),
                    "original_LLM_calls_for_continuity_guard":phase["idx"],
                    "novel_studio_temporal_state_passed_between_turns":True,
                    "literary_semantics_verified":False,
                }
            except Exception as ex:
                reason=str(ex)
                if not re.fullmatch(r"(?:WF114|WF96|WF105|WF98|WF102|WF_FLASH|WF110)_[A-Z0-9_]{1,150}",reason):
                    reason="WF114_ORIGINAL_WF_WRITING_REJECTED"
                result={"status":"WF_WRITING_REJECTED_NO_RETRY",
                        "reason":reason,
                        "original_decoded_model_receipts_still_saved":True,
                        "no_model_rewrite":True}
            finally:
                accepted=db.conn.execute(
                    "SELECT COUNT(*) FROM accepted_prose").fetchone()[0]
                db.close()
                require(accepted==0,"WF114_ACCIDENTAL_CANON_PROMOTION")
    except Exception as ex:
        reason=str(ex)
        if not re.fullmatch(r"(?:WF114|WF96|WF105|WF_FLASH)_[A-Z0-9_]{1,150}",reason):
            reason="WF114_READER_PLAN_OR_PROVIDER_REJECTED"
        result={"status":"SOURCE_OR_MODEL_REJECTED_NO_RETRY","reason":reason}
    manifest={
        "format":"wf.exam.v114.one-real-WF-continuity-result",
        "precommit_sha256":sha,"model":MODEL,
        "source_two_beat_provenance":calls[0]["decoded_sha256"] if calls else None,
        "all_original_model_requests":calls,
        "provider_usage":budget.public_receipt(),
        "actual_calls":phase["idx"],
        "max_calls":MAX_CALLS,"result":result,
        "external_memory_original_MIT_node_reducer_installed":True,
        "literary_improvement_vs_V113_UNDETERMINED":True,
        "original_V113_unchanged":True,
        "author_acceptance":False,
        "model_judge_calls":0,
    }
    m=write(cas,manifest,"WF114_EVIDENCE_MANIFEST_MISSING")
    print_receipt({
        "status":"WF114_NEW_REAL_CONTINUITY_STUDENT_RESULT_SAVED",
        "precommit_cas_sha256":sha,"manifest_cas_sha256":m,
        "outcome":result,"actual_provider_calls":phase["idx"],
        "reported_prompt_tokens":budget.prompt_tokens_reported,
        "reported_completion_tokens":budget.completion_tokens_reported,
        "original_model_replies":len(calls),"no_auto_retry":True,
        "no_user_novel_corpus_read":True,"legacy_trials_unchanged":True,
    })
    return 0

if __name__=="__main__":
    print_receipt({"status":"WF114_REAL_CONTINUITY_GITHUB_ONLY_START",
                   "new_model_call_upper_bound":MAX_CALLS,
                   "no_repeating_old_V113_requests":True})
    try:exit_code=run()
    except Exception as exc:
        msg=str(exc)
        if not re.fullmatch(r"(?:WF114|WF96|WF_FLASH|WF_V79)_[A-Z0-9_]{1,150}",msg):
            msg="WF114_STOPPED_UNCLASSIFIED_NO_RETRY"
        print_receipt({"status":"WF114_ONE_SHOT_ABORTED",
                       "reason":msg,"no_auto_retry":True,
                       "provider_request_could_have_billed":True})
        exit_code=1
    raise SystemExit(exit_code)
