"""V109 NEW F-only real WF experiment, using V108's original valid WF beats.

V106 failed schema and V108 E/F partial results are immutable. This does
not rerun either paid request or use external creative/judging models.

Uses unchanged AutonomousWriting(...).run(draft_mode='foresight_rolling')
and the ONE registered DeepSeekFlashModel. Unlike V108, captures ORIGINAL
HTTP response bytes to PRIVATE R2 CAS before attempting JSON parse. The
chapter, turn and rolling responses are also sealed BEFORE their validators.

Old V108 shared beats are imported only via their immutable private CAS,
and no old model-generated novel or user book text is transferred. The
synthetic published source satisfies existing local WF Studio prerequisites
without masquerading as 15 chapters of learned literary experience.
"""
from __future__ import annotations
import json,os,re
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.deepseek_flash_model import (
    DeepSeekFlashModel,FlashBudget,
)
from writerforge.v79_provisional_r2_cas_journal import WFProvisionalR2CASJournal
from writerforge.v96_causal_turns import parse_turn_outline
from writerforge.writing_assist import (
    InvisibleWritingAssist,AutonomousWriting,
)
from writerforge.v104_self_scene_protocol import encode,digest
from wf_railway_v108_real_e_f_once import (
    ENDPOINT,MODEL,ROLE,SCENE,COMMON_HARD_FACTS,
    CHAPTER_GOAL,HORIZON_PINS,fake_but_published_snapshot,
)

EXAM="WF-V109-F-ONLY-WIRE-FIRST-UNIQUE-20261021"
FROM_V108_PRECOMMIT="6a5b713768bdf6e8d78f1600b17d0745f40999cdad54d514f6d784e866a22631"
FROM_V108_SHARED="718a76ff2816ced4cf2f5780d56718ea928888be14d6c2c1bc185b321bec168f"
MAX_CALLS=4
MAX_RESERVED=5950
MAX_TOTAL=150000
MAX_WIRE_BYTES=150000
MAX_PROMPT_LENGTH=10000

def need(condition,code):
    if not condition:raise ValueError(code)
def note(obj):
    print(json.dumps(obj,sort_keys=True,ensure_ascii=False,
                     separators=(",",":"),allow_nan=False),flush=True)
def read_exact(cas,sha):
    need(type(sha) is str and re.fullmatch("[0-9a-f]{64}",sha),
         "WF109_UNKNOWN_R2_CAS_POINTER")
    blob=cas._get_content(sha)
    need(digest(blob)==sha,"WF109_R2_READBACK_HASH_MISMATCH")
    return blob
def store(cas,raw,code):
    need(type(raw) is bytes and 0<len(raw)<250000,
         "WF109_PRIVATE_R2_OBJECT_SIZE_INVALID")
    sha,_=cas._put_content(raw)
    need(read_exact(cas,sha)==raw,code)
    return sha

def precommit():
    return {
        "format":"wf.exam.v109.one-f-real-wire-precommit",
        "id":EXAM,
        "previous_v108_precommit_sha256":FROM_V108_PRECOMMIT,
        "wf_self_selected_beats_cas_sha256":FROM_V108_SHARED,
        "same_frozen_original_world_sha256":
            digest((SCENE+COMMON_HARD_FACTS).encode("utf8")),
        "original_F_mode":"foresight_rolling",
        "E_not_rerun":True,
        "new_unique_attempt":True,
        "other_models_called":0,
        "only_registered_provider":MODEL,
        "no_user_original_books":True,
        "neutral_synthetic_source_not_real_15_chapters":True,
        "max_calls":MAX_CALLS,
        "max_reserved_output_tokens":MAX_RESERVED,
        "max_total_conservative_tokens":MAX_TOTAL,
        "raw_provider_wire_sealed_before_decoding":True,
        "json_successful_replies_sealed_before_WF_validation":True,
        "no_auto_retry_even_on_format_errors":True,
        "no_factjournal_or_experience_promotion":True,
        "author_accepted":False,
        "independent_literary_review":"NOT_PERFORMED",
    }

SYS_PLAN=(
    "你是WriterForge自身唯一的创作执行模型，不是外部考官或润色者。"
    "本次只执行程序当前提供的一次独立写作请求。"
    "所有结构化字段以收到的用户提示为准，不添加外部字段。"
    "章计划只输出JSON，若要求horizon，必须是含choices数组的对象，"
    "choices里面的steps均为对象数组；不宣称猜想是已发生事实。"
    "本次不添加人物剧情答案，剧情完全由你自主创作。"
)
SYS_SCENE=(
    "你是WriterForge当前原创正文执行模型。只输出严格的JSON对象。"
    "必须包含prose、trace、affect三个键，prose是自然的小说正文。"
    "trace中action_quote和effect_quote必须是prose内实际连续原句，"
    "parent_effect_quote在没有前面真实已写事件时必须是JSON null。"
    "affect可以是null或明确列出来源触发/反应的对象，不能加未经写出的事实。"
    "实际动作、人物对白和写作节奏请自主处理，不向用户解释格式或技法。"
)
SYS_REPLAN=(
    "你是WriterForge自己的正文滚动规划模型。"
    "只输出严格JSON对象，完全遵守当前已提供的下一事件字段要求；"
    "此前未发生的假设不能当成现实。不得模仿前一个实验或外部考官。"
)
def select_system(*,stage,requested):
    if stage=="chapter_plan":return SYS_PLAN
    if stage=="replan":return SYS_REPLAN
    return SYS_SCENE

def run():
    need(all(os.environ.get(x) for x in
             ("DEEPSEEK_API_KEY","WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN")),
         "WF109_EXISTING_THREE_CREDENTIALS_UNAVAILABLE")
    cas=WFProvisionalR2CASJournal(endpoint=ENDPOINT)
    cas.require_writer_ready()
    p=encode(precommit())
    ident,created=cas._put_content(p)
    need(created is True and ident==digest(p) and
         read_exact(cas,ident)==p,
         "WF109_USED_PRECOMMIT_REFUSE_DUPLICATE_MODEL_CHARGE")
    shared=json.loads(read_exact(cas,FROM_V108_SHARED).decode("utf8","strict"))
    need(shared.get("format")=="wf.exam.v108.shared-original-outline" and
         shared.get("same_for_both_arms") is True,
         "WF109_PRIOR_WF_ORIGINAL_EVENT_LIST_NOT_FROZEN")
    locked=shared["two_model_generated_beats"]
    outline=parse_turn_outline(json.dumps(
        {"turns":locked},ensure_ascii=False,separators=(",",":"))
    )
    need(len(outline)==2 and outline[0]["id"]=="t01" and
         outline[1]["id"]=="t02",
         "WF109_PRIOR_WF_EVENT_TURNS_CORRUPT")
    frozen=store(cas,encode({
        "format":"wf.exam.v109.reused-real-WF-beats",
        "experiment":EXAM,"previous_beats_sha256":FROM_V108_SHARED,
        "student_beats":outline,"not_manual_fixed":True,
        "actual_story_from_previous_experiment_not_in_context":True,
    }),"WF109_FROZEN_EVENT_PROVENANCE_NOT_SAVED")

    budget=FlashBudget(max_calls=MAX_CALLS,
                       max_reserved_output_tokens=MAX_RESERVED,
                       max_total_tokens=MAX_TOTAL)
    phase={"call_index":0,"attempt":None,"stage":None,"wire":None}
    receipts=[]
    def preserve_wire(raw):
        need(type(raw) is bytes and 0<len(raw)<=MAX_WIRE_BYTES,
             "WF109_PROVIDER_WIRE_TOO_BIG_TO_SEAL")
        need(phase["attempt"] is not None and phase["wire"] is None,
             "WF109_PROVIDER_WIRE_OUTSIDE_SINGLE_REQUEST")
        wire_sha=store(cas,raw,"WF109_ACTUAL_PROVIDER_WIRE_R2_NOT_READABLE")
        phase["wire"]=wire_sha
        note({"status":"WF109_PROVIDER_WIRE_SEALED_BEFORE_JSON_DECODE",
              "call_no":phase["call_index"],
              "stage":phase["stage"],
              "private_exact_wire_cas_sha256":wire_sha,
              "response_bytes":len(raw),
              "provider_response_semantics_not_yet_checked":True,
              "no_wire_text_in_logs":True})

    wf=DeepSeekFlashModel(
        budget=budget,timeout_seconds=120,
        on_response_wire=preserve_wire)

    def bridge(packet,*,model,api_base,max_tokens,**kwargs):
        need(model==MODEL and
             packet.project_id=="v109-f-probe-only"
             and kwargs=={} and
             len(packet.prompt)<=MAX_PROMPT_LENGTH,
             "WF109_F_ONLY_WRITING_PACKET_CHANGED")
        i=phase["call_index"]+1
        need(1<=i<=MAX_CALLS,"WF109_F_CALL_COUNT_HARD_LIMIT")
        stage=("chapter_plan" if i==1 else
               "first_turn" if i==2 else
               "replan" if i==3 else "second_turn")
        need(max_tokens in (2400,1450,650) and
             (i,max_tokens) in ((1,2400),(2,1450),(3,650),(4,1450)),
             "WF109_EXPECTED_F_WRITER_CALL_ORDER_DIFFERENT")
        system=select_system(stage=stage,requested=max_tokens)
        original_req={
            "format":"wf.exam.v109.request-intent",
            "precommit_sha256":ident,
            "previous_real_WF_beats_cas_sha256":FROM_V108_SHARED,
            "call_no":i,"stage":stage,
            "original_WF_packet_sha256":packet.prompt_sha256,
            "actual_prompt_sha256":digest(packet.prompt.encode("utf8")),
            "system_sha256":digest(system.encode("utf8")),
            "max_tokens":max_tokens,"role":ROLE,
            "transport":"registered_WF_DeepSeekFlashModel",
            "no_retries":True,
        }
        attempt=encode(original_req)
        ptr,new=cas._put_content(attempt)
        need(new is True and ptr==digest(attempt) and
             read_exact(cas,ptr)==attempt,
             "WF109_PAID_REQUEST_INTENT_ALREADY_USED")
        phase.update({"call_index":i,"attempt":ptr,"stage":stage,"wire":None})
        note({"status":"WF109_PREPAID_CALL_INTENT_PRIVATE_CAS_LOCKED",
              "call_no":i,"stage":stage,"cas_sha256":ptr,
              "no_model_response_yet":True})
        # The callback saves the wire before JSON decode, including
        # answers that would have been lost to WF_FLASH_INVALID_JSON_RESPONSE.
        try:
            answer=wf.ask_json(
                role=ROLE,system=system,user=packet.prompt,
                max_tokens=max_tokens)
        except Exception as exc:
            message=str(exc)
            if not re.fullmatch(r"WF_FLASH_[A-Z0-9_]+",message):
                message="WF109_PROVIDER_OR_PRIVATE_EVIDENCE_FAILURE"
            receipts.append({
                "call_no":i,"stage":stage,
                "request_intent_cas_sha256":ptr,
                "provider_wire_cas_sha256":phase["wire"],
                "decoded_reply_cas_sha256":None,
                "status":"RESPONSE_INVALID_OR_UNAVAILABLE",
                "safe_error_code":message,
            })
            note({"status":"WF109_FIRST_FAILURE_NO_MODEL_RETRY",
                  "call_no":i,"stage":stage,"reason_code":message,
                  "wire_sha256":phase["wire"],
                  "no_auto_retry":True})
            raise
        need(phase["wire"] is not None,
             "WF109_VALID_JSON_WITHOUT_CAPTURED_PROVIDER_WIRE")
        doc=encode({
            "format":"wf.exam.v109.one-original-decoded-reply",
            "precommit_sha256":ident,"request_intent_cas_sha256":ptr,
            "provider_wire_cas_sha256":phase["wire"],
            "stage":stage,"original_answer":answer,
            "student_answer_unmodified":True,
        })
        decoded_sha=store(
            cas,doc,"WF109_UNMODIFIED_JSON_NOT_PRIVATE_READABLE")
        receipts.append({
            "call_no":i,"stage":stage,
            "request_intent_cas_sha256":ptr,
            "provider_wire_cas_sha256":phase["wire"],
            "decoded_reply_cas_sha256":decoded_sha,
            "status":"DECODED_UNVERIFIED",
        })
        note({"status":"WF109_PARSED_MODEL_JSON_SEALED_BEFORE_WF_CHECKS",
              "call_no":i,"stage":stage,
              "decoded_reply_cas_sha256":decoded_sha,
              "provider_wire_cas_sha256":phase["wire"]})
        return json.dumps(answer,ensure_ascii=False,separators=(",",":"))

    result=None
    with TemporaryDirectory(prefix="wf109-only-F-") as tmp:
        path=Path(tmp)
        pth=path/"neutral-snapshot.sqlite"
        snapshot=fake_but_published_snapshot(pth)
        db=WriterForgeDB(pth)
        rt=RuntimeEngine()
        rt.enter_write(snapshot)
        assist=InvisibleWritingAssist(
            db,rt,"v109-f-probe-only","v109-F-deep-sea",
            CHAPTER_GOAL,model=MODEL,api_base="http://127.0.0.1:1234/v1",
            source_genre="科幻",
        )
        common_outline=(
            SCENE+"\n"+COMMON_HARD_FACTS+
            "\n此前由WF自己生成的两段真实候选目标以独立CAS封存，"
            "本次只重新审视其前瞻机制，不重新随机选择人物/事件。"
        )
        try:
            with patch("writerforge.writing_assist.local_chat_completion",
                       side_effect=bridge):
                candidate=AutonomousWriting(assist).run(
                    outline=common_outline,
                    chapter_goals=[CHAPTER_GOAL],
                    output_dir=path/"private-candidates",
                    draft_mode="foresight_rolling",
                    frozen_turn_outlines=(json.dumps(
                        {"turns":outline},ensure_ascii=False,
                        separators=(",",":")),),
                    forward_author_pinned_facts=HORIZON_PINS,
                )
            ch=candidate["chapters"][0]
            prose=Path(ch["candidate"]).read_text("utf8")
            evidence={
                "format":"wf.exam.v109.one-real-forward-chapter",
                "precommit_sha256":ident,
                "original_WF_beats_cas_sha256":FROM_V108_SHARED,
                "whole_original_prose":prose,
                "prose_sha256":digest(prose.encode("utf8")),
                "prose_characters":len(prose),
                "horizon":json.loads(Path(ch["v105_horizon_plan"]).read_text("utf8")),
                "open_debts":json.loads(Path(ch["v105_candidate_checkpoint"]).read_text("utf8")),
                "model_responses_independently_saved":len(receipts),
                "author_accepted":False,
                "literary_quality_human_verified":False,
            }
            p=store(cas,encode(evidence),
                    "WF109_REAL_F_ORIGINAL_PROSE_NOT_PRIVATE_CAS")
            result={"status":"F_CHAPTER_ORIGINAL_SAVED",
                    "story_cas_sha256":p,
                    "prose_sha256":evidence["prose_sha256"],
                    "prose_characters":len(prose),
                    "V105_open_unreviewed_debts":
                        evidence["open_debts"]["open_debts_count"],
                    "literary_truth":"UNDETERMINED"}
        except Exception as exc:
            msg=str(exc)
            if not re.fullmatch(r"(?:WF109|WF105|WF98|WF96|WF102|WF_FLASH|WF_)[A-Z0-9_]{1,170}",msg):
                msg="WF109_ORIGINAL_WRITING_REJECTED_UNCLASSIFIED"
            result={"status":"F_CHAPTER_REJECTED_WITH_RAW_WIRE",
                    "safe_reason":msg,
                    "original_calls_attempted":phase["call_index"],
                    "wire_cas_pointer_count":sum(x["provider_wire_cas_sha256"] is not None
                                                  for x in receipts),
                    "student_own_prose_not_promoted":True}
        finally:
            accepted=db.conn.execute(
                "SELECT COUNT(*) FROM accepted_prose").fetchone()[0]
            db.close()
            need(accepted==0,"WF109_UNAUTHORIZED_STORY_ACCEPTANCE")

    manifest={
        "format":"wf.exam.v109.one-actual-F-wire-first-manifest",
        "precommit_sha256":ident,
        "source_shared_WF_original_beats":FROM_V108_SHARED,
        "new_model_call_receipts":receipts,
        "provider_usage":budget.public_receipt(),
        "model_requests_attempted":phase["call_index"],
        "max_requests":MAX_CALLS,
        "outcome":result,
        "one_model_only":True,
        "no_second_literary_model":True,
        "old_V106_or_V108_requests_replayed":False,
        "original_new_model_wire_saved_before_JSON_decode":True,
        "no_story_or_factjournal_accepted":True,
        "no_new_real_training_chapters":True,
        "independent_literary_review":"NOT_PERFORMED",
    }
    m=store(cas,encode(manifest),"WF109_FINISHED_EVIDENCE_NOT_R2")
    note({"status":"WF109_REAL_F_WIRE_FIRST_TRIAL_R2_SEALED",
          "manifest_cas_sha256":m,
          "precommit_cas_sha256":ident,
          "original_F_result":result,
          "actual_new_model_requests":phase["call_index"],
          "prompt_tokens_reported":budget.prompt_tokens_reported,
          "completion_tokens_reported":budget.completion_tokens_reported,
          "decoded_replies":sum(x["decoded_reply_cas_sha256"] is not None
                                for x in receipts),
          "original_provider_wires":sum(x["provider_wire_cas_sha256"] is not None
                                       for x in receipts),
          "author_accepted":False,
          "literary_mastery_proven":False,
          "production_not_touched":True})
    return 0

if __name__=="__main__":
    note({"status":"WF109_NEW_F_ONLY_EXPERIMENT_START",
          "max_new_calls":MAX_CALLS,
          "no_retry":True,"not_replay_of_V108":True})
    try:rc=run()
    except Exception as exc:
        message=str(exc)
        if not re.fullmatch(r"(?:WF109|WF105|WF98|WF96|WF102|WF_FLASH|WF_V79|WF_INDEX)_[A-Z0-9_]{1,160}",message):
            message="WF109_HALT_UNCLASSIFIED_KEEP_R2_AND_LOG_POINTERS"
        note({"status":"WF109_F_EXPERIMENT_ABORTED_NO_RETRY",
              "safe_error_code":message,
              "new_model_may_have_billed":True})
        rc=1
    note({"status":"WF109_F_ONLY_EXIT","code":rc})
    raise SystemExit(rc)
