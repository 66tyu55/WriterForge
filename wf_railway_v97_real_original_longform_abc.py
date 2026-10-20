"""V97 bounded REAL DeepSeek Flash A/B/C writing through AutonomousWriting.

One-time, seven paid requests MAX, original author-created historical story
(no user R2 novels). A receives the common chapter objective and uses the old
whole-chapter route. B/C use identical frozen event plan and same model;
B only segments; C requires source-visible actual action/effect quotation
plus earlier parent-effect continuity. The real Xuehai and save_candidate
code are exercised using a strictly synthetic local DB fixture.

Each model response is saved unchanged in user's existing PRIVATE immutable
R2 CAS BEFORE checking its correctness or calling the model again. The old
V82/V92 experience and FactJournal are never modified. No model self-grading.
No retry of requests that might already have incurred provider charges.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from hashlib import sha256
import json
import os
import re
import sys

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"tests"))

from writerforge.v97_real_longform_abc_protocol import (
    ARM_ORDER,ARMS,FORMAT,RUN_NAME,MODEL,PROVIDER,
    MAX_PROVIDER_REQUESTS,MAX_RESERVED_OUTPUT_TOKENS,
    MAX_CONSERVATIVE_REQUEST_BUDGET,A_MAX_OUTPUT,TURN_MAX_OUTPUT,
    FROZEN_PLAN,OUTLINE,CHAPTER_GOAL,TARGET_CHARS,
    shared_story,make_precommit,request_bound,
    frozen_plan_json,frozen_turns_json,canonical,sha,
    mechanical_prose_fields,
)

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
SYSTEM=(
    "你是WriterForge的原创小说写作者。JSON结构严格由用户提示指定。"
    "不要打分、不要描述写作方法、不要将人物推测写成已知历史事实。"
    "以人物实际动作、压力、抉择和可观察后果推进原创故事。"
    "只输出合法JSON，不使用Markdown、代码块或多余文字。"
)


class WF97PilotError(ValueError):
    pass


def require(flag,code):
    if not flag:raise WF97PilotError(code)


def emit(doc):
    print(json.dumps(doc,sort_keys=True,ensure_ascii=False),flush=True)


def safe_error(err):
    word=str(err)
    if re.fullmatch(r"(?:WF97|WF96|WF_FLASH|WF_V79|WF_LEARN|WF_INDEX)_[A-Z0-9_]{1,150}",word):
        return word
    return "WF97_UNCLASSIFIED_PAUSE_NO_AUTOMATIC_RETRY"


def run():
    # This run uses the same existing R2 Reader and IndexWriter as V88/V92.
    # No novel is downloaded. Any missing credential blocks BEFORE a model.
    for name in ("DEEPSEEK_API_KEY","WF_API_TOKEN",
                 "WF_INDEX_UPLOAD_TOKEN"):
        if not os.environ.get(name):
            emit({"status":"WF97_EXISTING_CONFIG_NOT_READY",
                  "missing_variable_name":name,"paid_model_calls":0})
            return 1
    from test_v26_invisible_writer import make_db
    from writerforge import WriterForgeDB,RuntimeEngine
    from writerforge.writing_assist import (
        AutonomousWriting,InvisibleWritingAssist,WritingExecutionError,
    )
    from writerforge.v79_provisional_r2_cas_journal import (
        WFProvisionalR2CASJournal,
    )
    from writerforge.deepseek_flash_model import (
        DeepSeekFlashModel,FlashBudget,DeepSeekFlashError,
    )
    from writerforge.v96_causal_turns import canonical as causal_canonical

    writer=WFProvisionalR2CASJournal(endpoint=ENDPOINT)
    writer.require_writer_ready()
    frozen=make_precommit()
    precommit_raw=canonical(frozen)
    precommit_hash=sha(precommit_raw)
    saved_hash,created=writer._put_content(precommit_raw)
    require(saved_hash==precommit_hash and
            writer._get_content(saved_hash)==precommit_raw,
            "WF97_PRECOMMIT_IMMUTABLE_R2_MISMATCH")
    emit({"status":"WF97_REAL_PILOT_FROZEN_ON_R2",
          "precommit_sha256":saved_hash,
          "precommit_created":bool(created),
          "planned_max_provider_requests":MAX_PROVIDER_REQUESTS,
          "max_reserved_output_tokens":MAX_RESERVED_OUTPUT_TOKENS,
          "conservative_total_token_ceiling":
              MAX_CONSERVATIVE_REQUEST_BUDGET,
          "original_test_story_not_private_user_novel":True,
          "paid_calls_so_far":0})
    # Identical task already executed/partially executed; even if its
    # results were not published, don't risk billing duplicate attempts.
    require(created is True,
            "WF97_DUPLICATE_PRECOMMIT_REFUSE_TO_REBILL")

    budget=FlashBudget(
        max_calls=MAX_PROVIDER_REQUESTS,
        max_reserved_output_tokens=MAX_RESERVED_OUTPUT_TOKENS,
        max_total_tokens=None,
    )
    model=DeepSeekFlashModel(budget=budget,timeout_seconds=120)
    conservative_spent=0
    result_records=[]
    arms=[]
    in_progress=None
    with TemporaryDirectory(prefix="wf97-real-original-story-") as tmp:
        root=Path(tmp)
        dbpath=root/"synthetic-author-study.sqlite3"
        snapshot=make_db(dbpath)
        db=WriterForgeDB(dbpath)
        runtime=RuntimeEngine()
        runtime.enter_write(snapshot)
        try:
            assist=InvisibleWritingAssist(
                db,runtime,
                "wf97-original-one-shot-probe",
                "original-historical-ferry",
                CHAPTER_GOAL,model=MODEL,
                api_base="http://127.0.0.1:1234/v1",
                source_genre="古代白话")
            # Plan is pre-frozen and doesn't trigger a model request. This
            # removes one random planning variable from all three arms.
            def hooked_completion(packet,*,model: str,api_base: str,
                                  max_tokens:int,**_unused):
                nonlocal conservative_spent
                if max_tokens==650 and "请先规划本章" in packet.prompt:
                    return frozen_plan_json()
                require(in_progress in ARM_ORDER,
                        "WF97_MODEL_CALLED_OUTSIDE_FROZEN_ARM")
                is_turn=in_progress!="single"
                if is_turn:
                    require(max_tokens==TURN_MAX_OUTPUT,
                            "WF97_TURN_OUTPUT_TOKEN_LIMIT_CHANGED")
                    instruction=(
                        "这次请返回恰好两个JSON字段："
                        '{"prose":"这一段真实原创正文约350至550个中文字符",'
                        '"trace":{"action_quote":"从正文精确复制的动作短句或null",'
                        '"effect_quote":"动作后真正发生的后果短句或null",'
                        '"parent_effect_quote":"此前实际场景的后果原句或null"}}。'
                        "如果当前叙事节点是action/decision/reversal，"
                        "动作及后果短句务必在实际正文里各出现一次；"
                        "动作须先发生，再体现后果。不虚构未写下的引句。"
                    )
                else:
                    require(max_tokens==A_MAX_OUTPUT,
                            "WF97_SINGLE_OUTPUT_TOKEN_LIMIT_CHANGED")
                    instruction=(
                        "这次A组不做分段和额外因果校验，"
                        "仅按现有章节大纲一次写完整原创正文，"
                        "约1200到1600个中文字符（含标点）。"
                        '返回恰好{"prose":"章节全文"}的JSON对象。'
                        "自然写小说，不输出计划、分析或评语。"
                    )
                user=(shared_story()+
                      "\n【WF当前正式写作接口组装的提示上下文】\n"+
                      packet.prompt+"\n【本次输出合同】\n"+instruction)
                reserved=request_bound(SYSTEM,user,max_tokens)
                require(budget.calls_reserved<MAX_PROVIDER_REQUESTS and
                        conservative_spent+reserved<=
                          MAX_CONSERVATIVE_REQUEST_BUDGET,
                        "WF97_TOTAL_REAL_MODEL_CALL_OR_TOKEN_CEILING")
                conservative_spent+=reserved
                slot=len(result_records)+1
                req={
                    "model":MODEL,"role":"craft_analysis",
                    "system":SYSTEM,"user":user,
                    "max_tokens":max_tokens,
                }
                request_sha=sha(canonical(req))
                # The official adapter has no retries; if its reply fails
                # parsing the request MAY already have been billed.
                answer=model_client.ask_json(
                    role="craft_analysis",system=SYSTEM,
                    user=user,max_tokens=max_tokens)
                require(type(answer) is dict and
                        len(canonical(answer))<=25000,
                        "WF97_REAL_MODEL_OUTPUT_BOUNDED_JSON")
                record={
                    "format":"wf.writing.private-model-answer.v97",
                    "precommit_sha256":saved_hash,
                    "arm":in_progress,
                    "arm_letter":ARMS[in_progress],
                    "request_index":slot,
                    "request_sha256":request_sha,
                    "writer_packet_sha256":packet.prompt_sha256,
                    "model":MODEL,
                    "max_output_tokens":max_tokens,
                    "raw_model_answer":answer,
                    "student_answer_unmodified":True,
                    "literary_quality_independently_verified":False,
                    "author_accepted":False,
                    "previous_v92_training_unchanged":True,
                    "original_private_book_source_not_sent":True,
                }
                rr=canonical(record)
                pointer,was_created=writer._put_content(rr)
                require(pointer==sha(rr) and
                        writer._get_content(pointer)==rr,
                        "WF97_REAL_RESPONSE_CAS_READBACK_FAILED")
                meta={
                    "arm":in_progress,"request_index":slot,
                    "request_sha256":request_sha,
                    "response_cas_sha256":pointer,
                    "response_created":bool(was_created),
                    "reported_model_output_sha256":sha(canonical(answer)),
                    "response_bytes":len(canonical(answer)),
                    "model_calls_reserved_so_far":budget.calls_reserved,
                }
                result_records.append(meta)
                emit({"status":"WF97_REAL_ONE_MODEL_ANSWER_SAVED",
                      **meta,"private_story_prose_not_in_log":True,
                      "literary_grade_unavailable":True})
                text=mechanical_prose_fields(
                    answer,is_turn=is_turn)
                return (json.dumps(answer,ensure_ascii=False,
                         separators=(",",":")) if is_turn else text)

            # We instantiate AFTER defining completion to preserve an
            # explicit variable independent of optional synthetic callbacks.
            model_client=model
            for arm in ARM_ORDER:
                in_progress=arm
                arm_result={"arm":arm,"letter":ARMS[arm],
                            "attempted":True,"completed":False,
                            "raw_calls_saved_before_validation":0,
                            "literary_quality_independently_verified":False,
                            "new_factjournal_KNOWN_writes":0}
                before=len(result_records)
                try:
                    with patch(
                        "writerforge.writing_assist.local_chat_completion",
                        side_effect=hooked_completion):
                        generated=AutonomousWriting(assist).run(
                            outline=OUTLINE,
                            chapter_goals=[CHAPTER_GOAL],
                            output_dir=root/("arm-"+arm),
                            draft_mode=arm,
                            frozen_turn_outlines=(
                               (frozen_turns_json(),)
                               if arm!="single" else None),
                        )
                    require(generated["chapter_count"]==1 and
                            generated["chapters"][0]["accepted"] is False,
                            "WF97_AUTONOMOUS_AUTHOR_ACCEPTANCE_CHANGED")
                    # This experiment deliberately uses a frozen
                    # author-supplied plan, not an actual LLM-planned
                    # chapter. The old app always labels model_generated
                    # True; override it in this isolated trial's own
                    # candidate metadata before exporting any provenance.
                    planned_file=Path(generated["chapters"][0]["plan"])
                    plan_record=json.loads(planned_file.read_text("utf8"))
                    require(all(plan_record.get(k)==FROZEN_PLAN[k]
                                for k in FROZEN_PLAN),
                            "WF97_FROZEN_CHAPTER_PLAN_NOT_ACTUALLY_USED")
                    plan_record["model_generated_plan"]=False
                    plan_record["externally_frozen_ab_test_plan"]=True
                    planned_file.write_text(
                        json.dumps(plan_record,ensure_ascii=False,indent=2),
                        encoding="utf8")
                    source_file=Path(generated["chapters"][0]["candidate"])
                    real_prose=source_file.read_text("utf8")
                    require(100<=len(real_prose)<=16000,
                            "WF97_CANDIDATE_REAL_PROSE_LENGTH_INVALID")
                    draft_entry={
                        "format":"wf.writing.private-complete-candidate.v97",
                        "arm":arm,"precommit_sha256":saved_hash,
                        "body":real_prose,
                        "candidate_not_author_accepted":True,
                        "story_generated_with_original_fixture":True,
                        "model_weights_not_modified":True,
                    }
                    raw=canonical(draft_entry)
                    chapter_sha,_=writer._put_content(raw)
                    require(chapter_sha==sha(raw) and
                            writer._get_content(chapter_sha)==raw,
                            "WF97_COMPLETE_CHAPTER_CAS_READBACK_FAILED")
                    arm_result.update({
                        "completed":True,
                        "prose_chars":len(real_prose),
                        "reached_1000_chinese_characters":
                            len(real_prose)>=1000,
                        "candidate_r2_cas_sha256":chapter_sha,
                        "turns_attempted":generated.get(
                            "segmented_model_turns",1),
                        "exact_quotes_proved_only_text_presence":
                            arm=="causal_guard",
                        "first_real_logical_contradiction_position":
                            "NOT_INDEPENDENTLY_REVIEWED",
                        "independent_literary_review_status":
                            "NOT_PERFORMED",
                    })
                except WritingExecutionError as error:
                    code=str(error)
                    code=code if re.fullmatch(
                        r"(?:WF96|WF97)_[A-Z0-9_]+",code) else (
                           "WF97_AUTONOMOUS_CONTRACT_REJECTION")
                    arm_result.update({
                        "status":"MECHANICAL_CONTRACT_REJECTED_NO_RETRY",
                        "reason_code":code,
                        "prose_chars":None,
                        "first_real_logical_contradiction_position":
                            "UNDETERMINED",
                    })
                arm_result["raw_calls_saved_before_validation"]=(
                    len(result_records)-before)
                arms.append(arm_result)
                emit({"status":"WF97_REAL_ONE_ARM_FINISHED",
                      "arm":arm,
                      "completed":arm_result["completed"],
                      "raw_calls_saved":arm_result[
                           "raw_calls_saved_before_validation"],
                      "prose_chars":arm_result.get("prose_chars"),
                      "reason_code":arm_result.get("reason_code"),
                      "literary_quality_graduation":False})
            in_progress=None
        finally:
            db.close()
        manifest={
            "format":"wf.writing.original-longform-abc-run.v97",
            "precommit_sha256":saved_hash,
            "story_sha256":frozen["shared_story_sha256"],
            "provider":PROVIDER,"model":MODEL,
            "arm_order":list(ARM_ORDER),
            "arm_outcomes":arms,
            "raw_model_answers":result_records,
            "usage":{
                "reserved_provider_calls":budget.calls_reserved,
                "max_provider_calls":MAX_PROVIDER_REQUESTS,
                "reported_prompt_tokens":
                   budget.prompt_tokens_reported,
                "reported_completion_tokens":
                   budget.completion_tokens_reported,
                "reserved_output_tokens":budget.tokens_reserved,
                "conservative_input_output_reserved":
                   conservative_spent,
                "billing_dashboard_independently_reconciled":False,
            },
            "target_chinese_chars":TARGET_CHARS,
            "num_original_topics":1,
            "student_drafts_author_accepted":False,
            "v96_exact_quote_check_not_semantic_causality":True,
            "no_real_independent_human_literary_judge":True,
            "literary_improvement_verdict":"UNDETERMINED",
            "reported_first_logic_failure_position":"UNDETERMINED",
            "v49_third_strike_failed_preserved":True,
            "literary_window_two":"LOCKED",
            "new_trained_chapters":0,
            "original_v92_15_chapters_untouched":True,
            "real_model_called":True,
        }
        mr=canonical(manifest)
        manifest_sha,_=writer._put_content(mr)
        require(manifest_sha==sha(mr) and
                writer._get_content(manifest_sha)==mr,
                "WF97_FINAL_R2_MANIFEST_READBACK_FAILED")
        emit({
            "status":"WF97_REAL_ORIGINAL_LONGFORM_THREE_ARMS_R2_SAVED",
            "manifest_cas_sha256":manifest_sha,
            "precommit_sha256":saved_hash,
            "arms":arms,
            "usage":manifest["usage"],
            "real_model_provider":MODEL,
            "independent_literary_review_performed":False,
            "trained_chapters_added":0,
            "original_user_books_not_sent":True,
        })
        return 0


print("WF97_REAL_ORIGINAL_LONGFORM_ABC_STARTED",flush=True)
try:
    exit_code=run()
except Exception as err:
    emit({
        "status":"WF97_PAUSED_NO_PAID_RETRY",
        "error_code":safe_error(err),
        "provider_may_have_billed_incomplete_request":True,
        "model_and_r2_originals_never_logged":True,
        "factjournal_learning_unmodified":True,
        "literary_improvement_unproven":True,
    })
    exit_code=1
print("WF97_REAL_ORIGINAL_LONGFORM_ABC_EXIT="+str(exit_code),flush=True)
raise SystemExit(exit_code)
