"""V81 cross-work BLIND comparison: baseline vs restored WF experience.

This is NOT literary grading by GPT or the same model grading itself. Two
real DeepSeek Flash calls see identical two-unit, previously unread private
B00 historical source text. The experience arm also receives chapter10's
previously saved next_strategy; the baseline arm does not. Arm order is
SHA-precommitted BEFORE any paid API call, never selected after answers.

Original source content stays within private R2 -> Railway -> DeepSeek.
Private response objects are content-addressed and R2-readback-verified.
Public logs contain only SHA, brief objective schema metrics and token usage.

Experimental result can establish model output differences and that WF
uses a stored strategy on another work. It cannot independently prove the
strategy improved literary comprehension or human reader emotions.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import sys
import time
import types

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
pkg=types.ModuleType("writerforge")
pkg.__package__="writerforge"
pkg.__path__=[str(ROOT/"writerforge")]
sys.modules["writerforge"]=pkg

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
B00_SHA="c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4"
TRAINED_ORIGINAL="0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd"
PREV_EXPERIENCE_SHA="feee04808c6b14f84c16989d98b031937a897395f3d008c43e17b3449f9077e3"
TRAINED_V81_LAST_PROGRESS_SHA="e28490de3f0b17875ed23418726a8b8692b3029c1501b30da314080f4edb0901"


def emit(doc):
    print(json.dumps(doc,ensure_ascii=False,sort_keys=True),flush=True)


print("WF_V81_UNSEEN_CROSS_BOOK_BLIND_TRANSFER_STARTED",flush=True)


def main():
    for env in ("WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN","DEEPSEEK_API_KEY"):
        if not os.getenv(env):
            emit({"status":"WF_V81_BLIND_EXISTING_SECRET_MISSING",
                  "missing_secret_name":env,"calls":0})
            return 1
    model=None
    precommit_sha=None
    committed={}
    try:
        from writerforge.bulk_inbox import BulkCatalog
        from writerforge.private_reading_remote import WFPrivateReadingClient
        from writerforge.private_r2_sql_smoke import download_one_verified
        from writerforge.wf_batch_supervisor import frozen_preselection
        from writerforge.wf_charset_byte_review import byte_charset_audit
        from writerforge.v79_provisional_r2_cas_journal import (
            WFProvisionalR2CASJournal,
        )
        from writerforge.v81_transfer_probe import (
            prepare_heldout,validate_model_proposal,compare_arms,canonical,
        )
        from writerforge.deepseek_flash_model import FlashBudget
        from writerforge.wf_learn_model_registry import new_wf_learn_model

        journal=WFProvisionalR2CASJournal(endpoint=ENDPOINT)
        journal.require_writer_ready()
        experience=json.loads(journal._get_content(PREV_EXPERIENCE_SHA))
        previous=json.loads(journal._get_content(
            TRAINED_V81_LAST_PROGRESS_SHA))
        if (previous.get("format")!="wf.learn.150k-batch-progress.v80" or
            previous.get("last_completed_chapter")!=10 or
            previous.get("latest_experience_sha256")!=PREV_EXPERIENCE_SHA or
            experience.get("format")!="wf.learn.experience.v80" or
            experience.get("chapter")!=10 or
            experience.get("source_sha256")!=TRAINED_ORIGINAL or
            experience.get("literary_quality_independently_verified") is not False or
            not isinstance(experience.get("reflection"),dict)):
            raise ValueError("WF_V81_BLIND_PRIOR_EXPERIENCE_UNVERIFIED")
        strategy=experience["reflection"].get("next_strategy")
        if not isinstance(strategy,str) or not 8<=len(strategy)<=200:
            raise ValueError("WF_V81_BLIND_STRATEGY_NOT_BOUNDED")

        with TemporaryDirectory(prefix="wf-v81-heldout-") as td:
            folder=Path(td)
            cat=BulkCatalog(folder/"metadata.sqlite3")
            try:
                r2=WFPrivateReadingClient(endpoint=ENDPOINT)
                inv=r2.inventory_to_catalog(cat)
                if inv.get("all_folders_complete") is not True:
                    raise ValueError("WF_V81_BLIND_R2_INVENTORY_INCOMPLETE")
                selected,frozen=frozen_preselection(cat)
                if frozen["preselection_digest_sha256"]!=B00_SHA:
                    raise ValueError("WF_V81_BLIND_B00_COHORT_CHANGED")
                row=selected["历史"][0]
                key=row["object_key"]
                key_sha=sha256(key.encode("utf8")).hexdigest()
                path=folder/"heldout.txt"
                original=download_one_verified(r2,row,path)
                if original["source_sha256"]==TRAINED_ORIGINAL:
                    raise ValueError("WF_V81_BLIND_TRAINED_SOURCE_REUSED")
                charset=byte_charset_audit(
                    path,expected_source_sha256=original["source_sha256"],
                    expected_size=original["bytes"],expected_key_sha256=key_sha)
                if charset["plausible_distinct_decoded_texts"]!=1:
                    raise ValueError("WF_V81_BLIND_HELDOUT_DECODER_AMBIGUOUS")
                codec=next((c for c in
                    ("gb18030","utf-8-sig","utf-8")
                    if c in charset["unique_reading_codec_aliases"]),None)
                if codec is None:
                    raise ValueError("WF_V81_BLIND_HELDOUT_ENCODING_NOT_SUPPORTED")
                units,proof=prepare_heldout(
                    path,original_sha=original["source_sha256"],
                    source_key_sha=key_sha,encoding=codec,
                    trained_experience_sha=PREV_EXPERIENCE_SHA)
                self_source_sha=original["source_sha256"]
                precommit={
                    "format":"wf.exam.precommit.v81",
                    "holdout":proof,
                    "trained_original_sha256":TRAINED_ORIGINAL,
                    "trained_experience_sha256":PREV_EXPERIENCE_SHA,
                    "source_complete_book_not_trained":True,
                    "no_answer_key_preselected":True,
                    "future_model_response_unknown":True,
                    "literary_quality_not_prejudged":True,
                }
                precommit_sha,_=journal._put_content(canonical(precommit))
                emit({"status":"WF_V81_BLIND_HOLDOUT_FROZEN_BEFORE_MODEL",
                      "precommit_sha256":precommit_sha,
                      "holdout_source_sha256":self_source_sha,
                      "holdout_source_key_sha256":key_sha,
                      "unit_sha256":proof["source_first_two_unit_sha256"],
                      "condition_order":proof["arm_order"],
                      "model_calls_so_far":0,
                      "original_prose_or_book_title_logged":False})
                budget=FlashBudget(
                    max_calls=2,max_reserved_output_tokens=2400,
                    max_total_tokens=150000)
                model=new_wf_learn_model(budget=budget)
                system=(
                    "你是WriterForge正在执行不曾提前看到原文的文学迁移检测。"
                    "这不是作家等级考试，不得自行评分和宣称掌握。"
                    "在已经给出的两个连续原文单位之内，自己选择一个"
                    "值得追问的因果或叙事效果问题，并写出可证伪的假说。"
                    '只输出严格JSON对象，恰好包含'
                    '{"question":"8到240字","hypothesis":"8到240字",'
                    '"uncertainty":"8到240字","focus":"8到240字",'
                    '"evidence_units":[1,2]}。'
                    "证据只能引用单位序号1、2，不能引用未知章节，"
                    "不要复制任何连续长段原文。"
                )
                fixed=(
                    "以下是完全相同的陌生文学作品连续两个片段。"
                    "不要利用以前文学书名或外部知识猜测答案。"
                    "\n[单位1]\n"+units[0]+
                    "\n[单位2]\n"+units[1]+
                    "\n只选择当前文本能够支持的疑问，不装作已经读完整本。"
                )
                replies={}
                quality={}
                for arm in proof["arm_order"]:
                    extra=(
                        "这是基准组，不提供之前学习经验。"
                        if arm=="baseline" else
                        "这是经验组。你以前通过阅读得出的检查策略："+
                        strategy
                    )
                    # Neither arm is exposed to the previous arm's response.
                    response=model.ask_json(
                        role="craft_analysis",
                        system=system,
                        user=extra+"\n"+fixed,
                        max_tokens=1000)
                    schema=validate_model_proposal(
                        response,source_units=units)
                    record={
                       "format":"wf.exam.arm.v81",
                       "arm":arm,
                       "precommit_sha256":precommit_sha,
                       "source_sha256":self_source_sha,
                       "unit_sha256":proof["source_first_two_unit_sha256"],
                       "trained_experience_sha256":PREV_EXPERIENCE_SHA,
                       "raw_model_proposal":response,
                       "technical_schema_validation":schema,
                       "provider_model":"deepseek-flash",
                       "literary_quality_independently_verified":False,
                    }
                    sha,_=journal._put_content(canonical(record))
                    committed[arm]=sha
                    replies[arm]=response
                    quality[arm]=schema
                    emit({"status":"WF_V81_ONE_BLIND_ARM_IMMUTABLY_SAVED",
                          "arm":arm,"r2_record_sha256":sha,
                          "precommit_sha256":precommit_sha,
                          "provider_call_count":budget.calls_reserved,
                          "token_usage_total":(
                            budget.prompt_tokens_reported+
                            budget.completion_tokens_reported),
                          "no_source_text_or_model_answer_logged":True})
                contrast=compare_arms(
                    replies["baseline"],replies["experience"])
                pair={
                    "format":"wf.exam.paired-contrast.v81",
                    "precommit_sha256":precommit_sha,
                    "baseline_record_sha256":committed["baseline"],
                    "experience_record_sha256":committed["experience"],
                    "comparison":contrast,
                    "model_usage":model.public_usage_report(),
                    "transfer_improvement_independently_established":False,
                    "external_literary_quality_grade":None,
                    "v49_graduation_modified":False,
                }
                result_sha,_=journal._put_content(canonical(pair))
                emit({
                    "status":"WF_V81_HELDOUT_TWO_ARM_CONTRAST_R2_SAVED",
                    "precommit_sha256":precommit_sha,
                    "paired_result_sha256":result_sha,
                    "arms":committed,
                    "mechanical_comparison":contrast,
                    "DeepSeek_calls":budget.calls_reserved,
                    "provider_prompt_tokens":budget.prompt_tokens_reported,
                    "provider_completion_tokens":budget.completion_tokens_reported,
                    "literary_quality_not_self_graded":True,
                    "external_literary_transfer_success_not_claimed":True,
                    "original_source_writes":0,
                })
                return 0
            finally:
                cat.close()
    except Exception as e:
        error=str(e)
        if not error.startswith((
            "WF_V81_","WF_LEARN_","WF_INDEX_","WF_FLASH_","WF_USAGE_",
            "WF_PRIVATE_","WF_V71_","WF_CHARSET_","WF_PREFIX_","BULK_",
        )):
            error="WF_V81_BLIND_UNEXPECTED_FAILURE"
        emit({
            "status":"WF_V81_TRANSFER_PAUSED_WITH_R2_RECEIPT",
            "error_code":error,
            "precommit_sha256":precommit_sha,
            "completed_arm_record_sha256":committed,
            "model_usage":model.public_usage_report() if model else None,
            "source_prose_or_key_logged":False,
            "automatic_paid_retries":0,
            "literary_grade_unchanged":True,
        })
        return 1

out=main()
print("WF_V81_TRANSFER_PROBE_EXIT="+str(out),flush=True)
time.sleep(6)
raise SystemExit(out)
