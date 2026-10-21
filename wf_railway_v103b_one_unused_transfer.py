"""V103-B POSTHOC exploratory fifth (unused) request -- not a rerun.

First V103 run used exactly 4 of 5 reserved calls because its chapter-1
literal causal trace was partial (correctly recorded RED). Do NOT edit its
original answers or reinterpret it as a formal fully preregistered success.
Use ONLY chapters 2/3 independently re-validated reader *abstract lessons*
for one exploratory held-out original prose candidate. Parent 4 requests
are never repeated or auto-retried. Private R2 content addressed records.
"""
from __future__ import annotations
import os,json,re
from writerforge.v103_frozen_original_exam import (
    CHAPTERS,MODEL,TARGET_CHARS,WRITE_MAX_OUTPUT,
    MAX_CALLS,MAX_CONSERVATIVE_REQUEST_BUDGET,encode,h,
)
from writerforge.v99_longform_quality_evidence import (
    freeze_manuscript,compare_equal_length,
)
from wf_railway_v103_real_three_reveal_exam import (
    ENDPOINT,WRITER_SYSTEM,prompt_to_write,validate_read,need,printable,
)

PARENT_MANIFEST="7997d752a5d311caaa400fb855fae9bc6f465a7fd2fbacc6734892fc83539038"
PARENT_PRECOMMIT="052238edbbc9a9de5747df81bb8a416c1b819cdc073b3d03ef1bbc047338d996"

def try_run():
    from writerforge.deepseek_flash_model import (
        DeepSeekFlashModel,FlashBudget,
    )
    from writerforge.v79_provisional_r2_cas_journal import WFProvisionalR2CASJournal
    need(all(os.environ.get(k) for k in
             ("DEEPSEEK_API_KEY","WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN")),
         "WF103B_EXISTING_THREE_SECRETS_UNAVAILABLE")
    cas=WFProvisionalR2CASJournal(endpoint=ENDPOINT)
    cas.require_writer_ready()
    raw=cas._get_content(PARENT_MANIFEST)
    need(h(raw)==PARENT_MANIFEST,"WF103B_OLD_MANIFEST_CHANGED")
    parent=json.loads(raw.decode("utf8","strict"))
    need(parent.get("format")==
         "wf.exam.v103.actual-reading-transfer-manifest"
         and parent.get("precommit_sha256")==PARENT_PRECOMMIT
         and parent.get("real_premium_model_calls")==4
         and parent.get("reader_literal_anchored_count")==2
         and parent.get("reader_chapter_count")==3
         and len(parent.get("model_call_receipts",[]))==4
         and parent.get("literary_transfer_winner")=="UNDETERMINED"
         and len(parent.get("writing_drafts",[]))==1
         and parent.get("new_v82_training_chapters")==0,
         "WF103B_CANNOT_AUGMENT_NONMATCHING_HISTORICAL_FAILURE")
    refs=parent["model_call_receipts"]
    need([x["stage"] for x in refs]==[
        "sequential_reader","sequential_reader","sequential_reader",
        "baseline_no_reader"],"WF103B_HISTORICAL_SEQUENCE_MISMATCH")
    notes=[]
    originals=[]
    for i in range(1,4):
        ref=refs[i-1]["raw_response_cas_sha256"]
        prior=cas._get_content(ref)
        need(h(prior)==ref,"WF103B_ORIGINAL_READER_CAS_MISMATCH")
        item=json.loads(prior.decode("utf8","strict"))
        need(item["format"]=="wf.exam.original-student-response.v103"
             and item["precommit_sha256"]==PARENT_PRECOMMIT
             and item["stage"]=="sequential_reader"
             and item["ordinal"]==i,
             "WF103B_WRONG_ORIGINAL_READER_ANSWER")
        original=item["answer_unmodified"]
        originals.append(original)
        if i==1:
            # Preserve the original RED. Never retrofit PASS or change it.
            continue
        check=validate_read(original,CHAPTERS[i-1])
        need(check["evidence_existentially_checked"] is True,
             "WF103B_VALID_CHAPTER_EVIDENCE_MISSING")
        lesson=original["transfer_lesson"]
        need(type(lesson) is str and 8<=len(lesson)<=240 and
             all(name not in lesson for name in
                 ("葛梨","周迦","冯叔","南塘","旧戏园")),
             "WF103B_STUDENT_ABSTRACT_LESSON_LEAKED_OLD_SOURCE")
        notes.append(lesson)
    need(len(notes)==2,"WF103B_NOT_TWO_SOURCE_ANCHORED_LESSONS")
    original_baseline_ref=refs[3]["raw_response_cas_sha256"]
    baseline_raw=cas._get_content(original_baseline_ref)
    need(h(baseline_raw)==original_baseline_ref,
         "WF103B_OLD_BASELINE_CAS_MISMATCH")
    baseline_entry=json.loads(baseline_raw.decode("utf8","strict"))
    need(baseline_entry["stage"]=="baseline_no_reader" and
         baseline_entry["ordinal"]==1 and
         set(baseline_entry["answer_unmodified"])=={"prose"},
         "WF103B_BASELINE_MUST_BE_REAL_ORIGINAL_PROSE")
    baseline=baseline_entry["answer_unmodified"]["prose"]
    need(h(baseline.encode("utf8"))==
         parent["writing_drafts"][0]["prose_sha256"],
         "WF103B_REAL_BASELINE_SHA_CHANGED")
    common_prompt=prompt_to_write((),informed=False)
    prompt=(
        common_prompt+
        "\n【补充实验：仅给你刚刚独立读过、原文引句核验通过的后两段中"
        "WF自己提出的抽象写作经验。首段因动作后果证据格式错误不纳入经验。】\n"+
        "\n".join("- "+x[:190] for x in notes)+
        "\n这些判断不是权威真理；只在合适时自然使用，不准搬用旧人物/旧戏园情节。"
    )
    req={"model":MODEL,"system":WRITER_SYSTEM,"user":prompt,
         "max_output_tokens":WRITE_MAX_OUTPUT,
         "arm":"posthoc_reader_informed","one_real_provider_request_only":True}
    estimated=len(encode(req))+1024+WRITE_MAX_OUTPUT
    need(parent["conservative_input_output_committed"]+estimated
         <=MAX_CONSERVATIVE_REQUEST_BUDGET,
         "WF103B_COMBINED_V103_BUDGET_EXCEEDED")
    need(parent["real_premium_model_calls"]+1<=MAX_CALLS,
         "WF103B_ORIGINAL_FIVE_CALL_CAP_EXCEEDED")
    # CAS unique. No second execution can ever silently re-bill this slot.
    new_pre={
        "format":"wf.exam.v103.posthoc-one-remaining-slot.v1",
        "parent_manifest_cas_sha256":PARENT_MANIFEST,
        "parent_precommit_cas_sha256":PARENT_PRECOMMIT,
        "parent_red_stage":"sequential_reader_1",
        "red_reason":"WF103_CAUSAL_ACTION_EFFECT_PARTIAL",
        "which_old_abstract_lessons_used":[2,3],
        "reader_strict_quotes_revalidated":True,
        "prompt_sha256":h(prompt.encode("utf8")),
        "reserved_new_requests":1,
        "global_max_requests_including_parent":MAX_CALLS,
        "new_max_output_tokens":WRITE_MAX_OUTPUT,
        "reader_experience_conditions_changed_posthoc":True,
        "formal_precommitted_fairness_claim":False,
        "no_auto_retry":True,
        "no_skill_graduation":True,
    }
    b=encode(new_pre)
    pre_sha,new_created=cas._put_content(b)
    need(h(b)==pre_sha and new_created is True,
         "WF103B_DUPLICATE_POSTHOC_SLOT_REFUSE_TO_REBILL")
    budget=FlashBudget(
        max_calls=1,max_reserved_output_tokens=WRITE_MAX_OUTPUT,
        max_total_tokens=None)
    model=DeepSeekFlashModel(budget=budget,timeout_seconds=120)
    answer=model.ask_json(role="craft_analysis",system=WRITER_SYSTEM,
                          user=prompt,max_tokens=WRITE_MAX_OUTPUT)
    student_doc={
        "format":"wf.exam.one-posthoc-original-model-response.v103b",
        "parent_manifest_sha256":PARENT_MANIFEST,
        "posthoc_precommit_sha256":pre_sha,
        "request_sha256":h(encode(req)),
        "answer_unmodified":answer,
        "literary_semantics_independently_verified":False,
    }
    source=encode(student_doc)
    student_sha,_=cas._put_content(source)
    need(cas._get_content(student_sha)==source,
         "WF103B_ORIGINAL_STUDENT_ANSWER_READBACK_FAILED")
    need(type(answer) is dict and set(answer)=={"prose"}
         and type(answer["prose"]) is str and
         100<=len(answer["prose"])<=12000,
         "WF103B_REAL_MODEL_PROSE_INVALID_NO_RETRY")
    prose=answer["prose"]
    a=freeze_manuscript(prose=baseline,arm="single",
       case_id="v103_experiment_new_world_transfer",
       requested_chars=TARGET_CHARS)
    e=freeze_manuscript(prose=prose,arm="rolling_causal",
       case_id="v103_experiment_new_world_transfer",
       requested_chars=TARGET_CHARS)
    length=compare_equal_length(samples=(a,e))
    receipt={
        "format":"wf.exam.v103.posthoc-exploratory-transfer-pair",
        "parent_original_manifest_cas_sha256":PARENT_MANIFEST,
        "posthoc_precommit_cas_sha256":pre_sha,
        "real_model_original_reply_cas_sha256":student_sha,
        "parent_provider_requests":4,"new_provider_requests":1,
        "total_supplier_requests":5,
        "original_baseline_prose_sha256":a["prose_sha256"],
        "new_informed_prose_sha256":e["prose_sha256"],
        "length_fairness":length,
        "reader_lessons_source_from_chapters":[2,3],
        "old_red_remains_red":True,
        "posthoc_protocol_deviation_from_original":True,
        "causal_literary_improvement":"UNDETERMINED",
        "independent_literary_human_review":"NOT_PERFORMED",
        "actual_new_provider_usage":budget.public_receipt(),
        "no_factjournal_or_canon_writes":True,
        "new_learning_chapters":0,
    }
    frozen=encode(receipt)
    final_sha,_=cas._put_content(frozen)
    need(cas._get_content(final_sha)==frozen,
         "WF103B_PRIVATE_SUPPLEMENT_RECEIPT_READBACK_FAILED")
    printable({"status":"WF103B_ONE_NEW_REAL_LEARNED_WRITING_ARM_SAVED",
        "posthoc_manifest_cas_sha256":final_sha,
        "original_parent_v103_manifest_cas_sha256":PARENT_MANIFEST,
        "new_reply_private_cas_sha256":student_sha,
        "old_baseline_length":len(baseline),
        "new_reader_informed_length":len(prose),
        "relative_length_gap":length["relative_length_gap"],
        "lengths_comparable":length["lengths_comparable"],
        "first_150_generated_prose_chars":prose[:150],
        "old_reader_chapter_1_still_red":True,
        "total_actual_provider_requests":5,
        "actual_provider_prompt_tokens_new":budget.prompt_tokens_reported,
        "actual_provider_completion_tokens_new":
            budget.completion_tokens_reported,
        "human_literary_quality_verified":False,
        "exploratory_not_pre_registered_quality_winner":"UNDETERMINED",
        "author_private_books_transferred":False,
        "no_future_automatic_training":True})
    return 0

if __name__=="__main__":
    printable({"status":"WF103B_POSTHOC_ONLY_UNUSED_FIFTH_SLOT_START",
               "new_request_cap":1,"earlier_four_never_repeated":True})
    try:rc=try_run()
    except Exception as ex:
        raw=str(ex)
        if not re.fullmatch(
           r"(?:WF103B|WF103|WF101|WF102|WF_FLASH|WF_V79|WF_INDEX|WF_LEARN)_[A-Z0-9_]{1,160}",raw):
            raw="WF103B_PAUSED_UNKNOWN_DO_NOT_RETRY"
        printable({"status":"WF103B_SUPPLEMENT_PAUSED_NO_AUTORETRY",
                   "reason_code":raw,
                   "earlier_four_original_responses_unchanged":True,
                   "new_request_may_have_billed":True})
        rc=1
    printable({"status":"WF103B_POSTHOC_END","exit_code":rc})
    raise SystemExit(rc)
