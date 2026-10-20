"""V88: FIRST real WF blind answers on V87's two independently verified R2 samples.

Exactly four official DeepSeek Flash calls MAX (A/B on each of two works).
Each raw answer saved immutably to existing R2 CAS before another is sent.
No preexisting V82 literary training repeats, no hidden unit enters prompts.
A deterministic one-time CAS precommit refuses any automatic paid redeploy;
uncertain requests are NEVER retried. No novel titles, prose or keys in logs.

This is NOT semantic literary quality grading. Every result is a hypothesis
until an independently trusted and blind literary examiner adjudicates it.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json,os,sys,time

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0,str(ROOT))

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
RUN_NAME="WF-V88-V87-TWO-WORKS-2026-10-20-FIRST-AND-ONLY-PAID-RUN"
def emit(obj):
    print(json.dumps(obj,sort_keys=True,ensure_ascii=False),flush=True)

def need(flag, code):
    if not flag: raise ValueError(code)

def sha(value:bytes):
    return sha256(value).hexdigest()

def only_safe_error(exc):
    code=str(exc)
    prefixes=("WF88_","WF87_","WF_V79_","WF_V82_","WF_FLASH_",
              "WF_USAGE_","WF_PRIVATE_","WF_V71_","WF_INDEX_",
              "WF_CHARSET_","WF_LEARN_","BULK_")
    return code if code.startswith(prefixes) and len(code)<=100 else \
        "WF88_UNEXPECTED_PAUSED_CHECK_PRECOMMIT_AND_PAID_USAGE"

def run():
    for env in ("DEEPSEEK_API_KEY","WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN"):
        if not os.getenv(env):
            emit({"status":"WF88_EXISTING_CREDENTIAL_MISSING",
                  "secret_name":env,"model_calls":0})
            return 1
    from writerforge.bulk_inbox import BulkCatalog
    from writerforge.private_reading_remote import WFPrivateReadingClient
    from writerforge.private_r2_sql_smoke import download_one_verified
    from writerforge.wf_charset_byte_review import byte_charset_audit
    from writerforge.wf_b01_prefix_prepare import _split_into_ordered_units
    from writerforge.v87_random_holdout import (
        metadata_only_plan,inventory_metadata_only,recover_key_by_sha)
    from writerforge.v87_frozen_random_draw import PLAN_SHA256
    from writerforge.v87_pinned_random_cases import FROZEN_CASES
    from writerforge.v87_contiguous_passage import choose_passage
    from writerforge.v79_provisional_r2_cas_journal import WFProvisionalR2CASJournal
    from writerforge.deepseek_flash_model import FlashBudget
    from writerforge.wf_learn_model_registry import new_wf_learn_model
    from writerforge.v88_frozen_blind_exam import (
        SYSTEM_PROMPT,ARM_ORDER,MAX_PAID_REQUESTS,
        MAX_OUTPUT_TOKENS_PER_REQUEST,MAX_CONSERVATIVE_INPUT_OUTPUT_TOKENS,
        V82_BATCH_SHA,V82_EXPERIENCE_SHA,V82_TRAINED_SOURCE_SHA,
        V87_DRAW_SHA,V87_COLD_SOURCE_RECEIPT_SHA,validate_wf_answer,
        WF88BlindError,canonical,shared_prompt,arm_prompt,mechanical_pair)
    from writerforge.wf_api_usage_supervisor import canonical as metered_canonical
    journal=None
    model=None
    precommit_sha=None
    immutable_arms=[]
    paired_shas=[]
    reserved_conservative=0
    try:
        journal=WFProvisionalR2CASJournal(endpoint=ENDPOINT)
        journal.require_writer_ready()
        old_batch=json.loads(journal._get_content(V82_BATCH_SHA))
        old_experience=json.loads(journal._get_content(V82_EXPERIENCE_SHA))
        need(old_batch.get("last_completed_chapter")==15 and
             old_batch.get("source_sha256")==V82_TRAINED_SOURCE_SHA and
             old_batch.get("latest_experience_sha256")==V82_EXPERIENCE_SHA,
             "WF88_V82_PREVIOUS_BATCH_NOT_VERIFIED")
        need(old_experience.get("format")=="wf.learn.experience.v80" and
             old_experience.get("chapter")==15 and
             old_experience.get("source_sha256")==V82_TRAINED_SOURCE_SHA and
             old_experience.get("literary_quality_independently_verified") is False and
             isinstance(old_experience.get("reflection"),dict),
             "WF88_V82_EXPERIENCE_NOT_VERIFIED")
        strategy=old_experience["reflection"].get("next_strategy")
        need(isinstance(strategy,str) and 8<=len(strategy)<=200,
             "WF88_V82_STRATEGY_NOT_BOUNDED")
        strategy_sha=sha(strategy.encode("utf8"))
        with TemporaryDirectory(prefix="wf-v88-real-blind-") as directory:
            root=Path(directory)
            cat=BulkCatalog(root/"metadata.sqlite3")
            try:
                source=WFPrivateReadingClient(endpoint=ENDPOINT,timeout=80)
                inventory_metadata_only(source,cat)
                plan=metadata_only_plan(cat)
                need(plan["plan_sha256"]==PLAN_SHA256 and
                     PLAN_SHA256==V87_DRAW_SHA and
                     len(FROZEN_CASES)==2 and
                     [x["genre_hint"] for x in FROZEN_CASES]==
                     ["历史","科幻"],
                     "WF88_V87_RANDOM_DRAW_CHANGED")
                work_items=[]
                for index,reference in enumerate(FROZEN_CASES):
                    row=recover_key_by_sha(cat,reference["source_key_sha256"])
                    need(row["category"]==reference["genre_hint"],
                         "WF88_V87_SOURCE_SCOPE_CHANGED")
                    file=root/f"private-source-{index}.txt"
                    result=download_one_verified(source,row,file)
                    need(result["source_sha256"]==reference["source_sha256"] and
                         result["bytes"]==reference["bytes"] and
                         result["source_sha256"]!=V82_TRAINED_SOURCE_SHA,
                         "WF88_V87_SOURCE_BYTES_CHANGED")
                    codec_info=byte_charset_audit(
                        file,expected_source_sha256=reference["source_sha256"],
                        expected_size=reference["bytes"],
                        expected_key_sha256=reference["source_key_sha256"])
                    need(codec_info["plausible_distinct_decoded_texts"]==1,
                         "WF88_V87_SOURCE_ENCODING_UNVERIFIED")
                    aliases=codec_info["unique_reading_codec_aliases"]
                    codec=next((c for c in ("gb18030","utf-8-sig","utf-8")
                                if c in aliases),None)
                    need(codec is not None,"WF88_NO_REVERSIBLE_CODEC")
                    full=file.read_bytes()
                    decoded=full.decode(codec,"strict")
                    need(decoded.encode(codec,"strict")==full,
                         "WF88_V87_TEXT_ROUNDTRIP_CHANGED")
                    proof=choose_passage(
                        decoded,key_sha256=reference["source_key_sha256"],
                        source_sha256=reference["source_sha256"])
                    for field in ("fragment_start_char","fragment_end_char",
                                  "fragment_sha256","fragment_unit_count",
                                  "first_read_visible_unit_sha256",
                                  "sealed_unread_unit_sha256"):
                        need(proof[field]==reference[field],
                             "WF88_V87_FROZEN_PRIVATE_PASSAGE_CHANGED")
                    private_fragment=decoded[
                        proof["fragment_start_char"]:proof["fragment_end_char"]]
                    pieces=_split_into_ordered_units(private_fragment)
                    need(len(pieces)==proof["fragment_unit_count"] and
                         len(pieces)>=4 and
                         sha(pieces[2].encode("utf8"))==
                            reference["sealed_unread_unit_sha256"],
                         "WF88_V87_FUTURE_UNIT_SEAL_CHANGED")
                    visible=tuple(pieces[:2])
                    need([sha(x.encode("utf8")) for x in visible]==
                         reference["first_read_visible_unit_sha256"],
                         "WF88_VISIBLE_TWO_UNITS_CHANGED")
                    # Hidden pieces are never included in any prompt.
                    del pieces,private_fragment,decoded,full
                    file.unlink(missing_ok=True)
                    shared=shared_prompt(visible)
                    prompts={}
                    for arm in ARM_ORDER[reference["genre_hint"]]:
                        user=arm_prompt(shared,arm=arm,strategy=strategy)
                        req={
                            "role":"craft_analysis","system":SYSTEM_PROMPT,
                            "user":user,"max_tokens":MAX_OUTPUT_TOKENS_PER_REQUEST,
                            "model":"deepseek-flash"}
                        prompts[arm]={
                            "user":user,"input_sha256":sha(metered_canonical(req)),
                            "conservative_token_reserve":(
                                len(metered_canonical(req))+1024+
                                MAX_OUTPUT_TOKENS_PER_REQUEST)}
                    work_items.append({
                        "reference":reference,"visible":visible,"prompts":prompts,
                        "order":ARM_ORDER[reference["genre_hint"]],
                        "shared_prompt_sha256":sha(shared.encode("utf8")),
                    })
            finally:
                cat.close()
            planned=[]
            for item in work_items:
                ref=item["reference"]
                for arm in item["order"]:
                    p=item["prompts"][arm]
                    planned.append({
                        "genre_hint":ref["genre_hint"],"arm":arm,
                        "input_sha256":p["input_sha256"],
                        "conservative_token_reserve":p[
                            "conservative_token_reserve"]})
                    reserved_conservative+=p["conservative_token_reserve"]
            need(len(planned)==MAX_PAID_REQUESTS and
                 reserved_conservative<=MAX_CONSERVATIVE_INPUT_OUTPUT_TOKENS,
                 "WF88_FOUR_CALL_HARD_TOKEN_CEILING_EXCEEDED")
            precommit={
                "format":"wf.exam.first-and-only-four-arm-precommit.v88",
                "run_name":RUN_NAME,
                "random_draw_sha256":V87_DRAW_SHA,
                "cold_verified_v87_source_receipt_sha256":
                    V87_COLD_SOURCE_RECEIPT_SHA,
                "prior_v82_batch_sha256":V82_BATCH_SHA,
                "prior_v82_experience_sha256":V82_EXPERIENCE_SHA,
                "experience_strategy_sha256":strategy_sha,
                "system_prompt_sha256":sha(SYSTEM_PROMPT.encode("utf8")),
                "provider":"deepseek","model":"deepseek-flash",
                "max_paid_requests":MAX_PAID_REQUESTS,
                "max_output_tokens_per_request":MAX_OUTPUT_TOKENS_PER_REQUEST,
                "hard_conservative_run_token_cap":
                    MAX_CONSERVATIVE_INPUT_OUTPUT_TOKENS,
                "planned_upper_reserve":reserved_conservative,
                "planned_requests":planned,
                "works":[{
                    "genre_hint":i["reference"]["genre_hint"],
                    "source_sha256":i["reference"]["source_sha256"],
                    "visible_unit_hashes":
                       i["reference"]["first_read_visible_unit_sha256"],
                    "sealed_future_unit_hash":
                       i["reference"]["sealed_unread_unit_sha256"],
                    "shared_visible_prompt_sha256":i["shared_prompt_sha256"],
                    "arm_order":list(i["order"]),
                    "whole_chapter_claimed":False,
                } for i in work_items],
                "hidden_source_text_not_sent_to_wf":True,
                "future_answers_not_known_at_precommit":True,
                "author_independent_quality_review_not_yet_run":True,
                "paid_calls_so_far":0,
                "source_prose_and_titles_not_published":True,
                "reruns_prohibited_without_manual_checkpoint_audit":True,
                "literary_promotion_prohibited":True,
            }
            # One-time CAS object prevents automatic re-deploy from billing
            # the same precommitted task a second time. If a previous attempt
            # produced this precommit, fail closed rather than charging again.
            precommit_sha,created=journal._put_content(canonical(precommit))
            emit({"status":"WF88_FIRST_ONLY_PAID_PRECOMMIT_R2_SIGNED",
                  "precommit_sha256":precommit_sha,
                  "new_precommit_created":created,
                  "planned_model_calls":MAX_PAID_REQUESTS,
                  "conservative_reserved_max":reserved_conservative,
                  "max_tokens_allowed":MAX_CONSERVATIVE_INPUT_OUTPUT_TOKENS,
                  "model_calls_so_far":0,"private_source_logged":False})
            need(created is True,
                 "WF88_DUPLICATE_PAID_PRECOMMIT_REFUSE_ALL_RETRY")
            budget=FlashBudget(
                max_calls=MAX_PAID_REQUESTS,
                max_reserved_output_tokens=MAX_PAID_REQUESTS*
                                           MAX_OUTPUT_TOKENS_PER_REQUEST,
                max_total_tokens=150000)
            model=new_wf_learn_model(budget=budget)
            for case in work_items:
                ref=case["reference"]
                answers={}
                validations={}
                for arm in case["order"]:
                    user=case["prompts"][arm]["user"]
                    req={
                        "role":"craft_analysis","system":SYSTEM_PROMPT,
                        "user":user,"max_tokens":MAX_OUTPUT_TOKENS_PER_REQUEST,
                        "model":"deepseek-flash"}
                    need(sha(metered_canonical(req))==
                         case["prompts"][arm]["input_sha256"],
                         "WF88_PRECOMMITTED_EXACT_INPUT_CHANGED")
                    # No automatic retry after unknown billing result.
                    answer=model.ask_json(
                        role="craft_analysis",system=SYSTEM_PROMPT,
                        user=user,max_tokens=MAX_OUTPUT_TOKENS_PER_REQUEST)
                    try:
                        evidence=validate_wf_answer(
                            answer,visible_units=case["visible"])
                        status="TECHNICAL_SOURCE_SCHEMA_PASS"
                        schema={"schema_valid":True,**evidence}
                    except WF88BlindError as error:
                        status="SCHEMA_OR_EVIDENCE_FAILED_NO_RETRY"
                        schema={"schema_valid":False,
                                "reason_code":str(error),
                                "independent_literary_quality_verified":False}
                    record={
                        "format":"wf.exam.private-one-arm.v88",
                        "precommit_sha256":precommit_sha,
                        "case_source_sha256":ref["source_sha256"],
                        "case_genre_hint":ref["genre_hint"],
                        "arm":arm,
                        "request_sha256":case["prompts"][arm]["input_sha256"],
                        "visible_unit_sha256":
                            ref["first_read_visible_unit_sha256"],
                        "hidden_future_unit_sha256":
                            ref["sealed_unread_unit_sha256"],
                        "provider_model":"deepseek-flash",
                        "raw_wf_answer":answer,
                        "machine_source_validation":schema,
                        "literary_quality_independently_verified":False,
                        "model_weights_updated":False,
                        "future_text_in_prompt":False,
                    }
                    arm_sha,_=journal._put_content(canonical(record))
                    immutable_arms.append({
                        "case_genre_hint":ref["genre_hint"],
                        "arm":arm,"answer_cas_sha256":arm_sha,
                        "schema_status":status,
                        "usage_reserved_calls":budget.calls_reserved,
                        "answer_raw_sha256":sha(canonical(answer)),
                    })
                    emit({"status":"WF88_ONE_REAL_WF_BLIND_ARM_SAVED",
                          "precommit_sha256":precommit_sha,
                          "genre_hint":ref["genre_hint"],
                          "arm":arm,"answer_cas_sha256":arm_sha,
                          "source_schema_status":status,
                          "provider_reserved_calls":budget.calls_reserved,
                          "reported_tokens_so_far":
                             budget.prompt_tokens_reported+
                             budget.completion_tokens_reported,
                          "private_model_answer_not_logged":True})
                    answers[arm]=answer
                    validations[arm]=schema
                pair={
                    "format":"wf.exam.real-two-condition-pair.v88",
                    "precommit_sha256":precommit_sha,
                    "case_genre_hint":ref["genre_hint"],
                    "case_source_sha256":ref["source_sha256"],
                    "baseline_arm_sha256":next(a["answer_cas_sha256"]
                          for a in immutable_arms
                          if a["case_genre_hint"]==ref["genre_hint"]
                          and a["arm"]=="baseline"),
                    "experience_arm_sha256":next(a["answer_cas_sha256"]
                          for a in immutable_arms
                          if a["case_genre_hint"]==ref["genre_hint"]
                          and a["arm"]=="experience"),
                    "mechanical_comparison":mechanical_pair(
                        answers["baseline"],answers["experience"],
                        validations["baseline"],validations["experience"]),
                    "literary_quality_winner":"UNDETERMINED",
                    "independent_literary_review_performed":False,
                }
                pair_sha,_=journal._put_content(canonical(pair))
                paired_shas.append(pair_sha)
                emit({"status":"WF88_ONE_PRIVATE_PAIR_SAVED",
                      "genre_hint":ref["genre_hint"],
                      "pair_cas_sha256":pair_sha,
                      "paid_requests_used_so_far":budget.calls_reserved,
                      "semantic_improvement_unproven":True})
            need(budget.calls_reserved==MAX_PAID_REQUESTS and
                 len(immutable_arms)==MAX_PAID_REQUESTS and
                 len(paired_shas)==2,
                 "WF88_NOT_ALL_FOUR_PAID_REQUESTS_SIGNED")
            manifest={
                "format":"wf.exam.private-four-arm-manifest.v88",
                "precommit_sha256":precommit_sha,
                "individual_arms":immutable_arms,
                "paired_case_sha256":paired_shas,
                "model_usage":model.public_usage_report(),
                "existing_chapter15_training_unchanged":True,
                "new_trained_chapters":0,
                "independent_literary_review_completed":False,
                "literary_improvement_proven":False,
                "v49_third_strike_status":"FAILED",
                "second_literary_window":"LOCKED",
                "no_auto_retry":True,
            }
            batch_sha,_=journal._put_content(canonical(manifest))
            emit({"status":"WF88_FOUR_REAL_BLIND_ANSWERS_R2_SIGNED",
                  "manifest_cas_sha256":batch_sha,
                  "precommit_sha256":precommit_sha,
                  "pairs":paired_shas,"answers":immutable_arms,
                  "usage":model.public_usage_report(),
                  "independent_semantic_review_completed":False,
                  "new_training_chapters":0,
                  "original_books_not_modified":True})
            return 0
    except Exception as error:
        emit({
            "status":"WF88_PAUSED_NO_AUTOMATIC_PAID_RETRY",
            "reason_code":only_safe_error(error),
            "precommit_sha256":precommit_sha,
            "arms_saved_so_far":immutable_arms,
            "pairs_saved_so_far":paired_shas,
            "model_usage":model.public_usage_report() if model else None,
            "provider_billing_may_need_independent_reconciliation":True,
            "no_unlogged_source_prose_or_credentials":True,
            "literary_graduation_unchanged":True,
        })
        return 1

print("WF88_REAL_TWO_WORK_BLIND_EXAM_STARTED",flush=True)
code=run()
print("WF88_REAL_TWO_WORK_BLIND_EXAM_EXIT="+str(code),flush=True)
time.sleep(5)
raise SystemExit(code)
