"""V88 independent cold examiner of REAL 4-answer V87 heldout WF test.

This starts in a fresh reader-only Railway process and strips ALL paid-model
and R2 writer secrets. It fetches real R2 answer objects by frozen SHA,
downloads original novels again, independently regenerates the frozen V87
visible and hidden unit hashes, and recomputes strict V88 validation failures.

No novels, model responses, title or private object keys are emitted.
Mechanical protocol failures ≠ independent literary semantic judgement.
"""
from __future__ import annotations
import json,os,sys,time
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
for key in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
            "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(key,None)

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
PRECOMMIT_SHA="5e6d27fe96fccfd1d545243e9d8e81d7a25d4dc563888095a6df9e461b558591"
MANIFEST_SHA="b4802c132bcdc4998ced3a5d34ee06224380b53645b3c15b6f9ba0cb3ca979eb"
PINNED_ARMS={
    ("历史","baseline"):"9676c6ef18904c38a38b3b7122fe47c5ebe990c1a7bc6bc9e2f447c3d47dacf5",
    ("历史","experience"):"ab3a4379d7abc819294fd9c42c922ee6ef470e2b6962cc854c5b1c94fa408b8c",
    ("科幻","experience"):"283d725bd2676c5003a21857bb23344cd39ef2f36dd9508fe49330e31050373a",
    ("科幻","baseline"):"a036c080541e2c1e5f9471bbceef2efec071319e5372e7359768d703bac62296",
}
PAIR_SHA={
    "历史":"07c70d513e2fb22a8674c95b16aa8ecdecdc62ee28166631bc008d7d64127613",
    "科幻":"13a7688bea9217e51d5c2cf416a4dc7830865e0281d95b7049937f48657e14bd",
}

def emit(doc):
    print(json.dumps(doc,sort_keys=True,ensure_ascii=False),flush=True)

def need(cond,code):
    if not cond:
        raise ValueError(code)

def digest(raw):
    return sha256(raw).hexdigest()

def error_code(exc):
    value=str(exc)
    if value.startswith(("WF88_","WF87_","WF_V79_","WF_PRIVATE_",
                         "WF_INDEX_","WF_CHARSET_","WF_V71_","BULK_")) and \
            len(value)<=100:
        return value
    return "WF88_INDEPENDENT_SOURCE_AUDIT_UNKNOWN_FAILURE"

print("WF88_INDEPENDENT_READER_ONLY_EXAM_START",flush=True)

def main():
    need(os.getenv("WF_API_TOKEN") and not os.getenv("DEEPSEEK_API_KEY") and
         not os.getenv("WF_INDEX_UPLOAD_TOKEN"),
         "WF88_INDEPENDENT_READER_ROLE_NOT_SAFE")
    from writerforge.bulk_inbox import BulkCatalog
    from writerforge.private_reading_remote import WFPrivateReadingClient
    from writerforge.private_r2_sql_smoke import download_one_verified
    from writerforge.wf_charset_byte_review import byte_charset_audit
    from writerforge.wf_b01_prefix_prepare import _split_into_ordered_units
    from writerforge.v87_random_holdout import (
        inventory_metadata_only,metadata_only_plan,recover_key_by_sha)
    from writerforge.v87_pinned_random_cases import FROZEN_CASES
    from writerforge.v87_contiguous_passage import choose_passage
    from writerforge.v79_provisional_r2_cas_journal import (
        WFProvisionalR2CASJournal)
    from writerforge.v88_frozen_blind_exam import (
        SYSTEM_PROMPT,ARM_ORDER,MAX_PAID_REQUESTS,
        MAX_OUTPUT_TOKENS_PER_REQUEST,MAX_CONSERVATIVE_INPUT_OUTPUT_TOKENS,
        V82_BATCH_SHA,V82_EXPERIENCE_SHA,V87_DRAW_SHA,
        validate_wf_answer,WF88BlindError,
        shared_prompt,arm_prompt,mechanical_pair,canonical)
    from writerforge.wf_api_usage_supervisor import canonical as usage_canonical

    reader=WFProvisionalR2CASJournal(endpoint=ENDPOINT,read_only=True)
    need(reader.writer is None and reader.read_only,
         "WF88_INDEPENDENT_READER_WRITER_LEAK")
    precommit=json.loads(reader._get_content(PRECOMMIT_SHA))
    manifest=json.loads(reader._get_content(MANIFEST_SHA))
    old_experience=json.loads(reader._get_content(V82_EXPERIENCE_SHA))
    old_batch=json.loads(reader._get_content(V82_BATCH_SHA))
    need(precommit.get("format")=="wf.exam.first-and-only-four-arm-precommit.v88"
         and precommit.get("paid_calls_so_far")==0
         and precommit.get("random_draw_sha256")==V87_DRAW_SHA
         and precommit.get("max_paid_requests")==MAX_PAID_REQUESTS
         and precommit.get("max_output_tokens_per_request")==
             MAX_OUTPUT_TOKENS_PER_REQUEST
         and precommit.get("hard_conservative_run_token_cap")==
             MAX_CONSERVATIVE_INPUT_OUTPUT_TOKENS
         and manifest.get("format")=="wf.exam.private-four-arm-manifest.v88"
         and manifest.get("precommit_sha256")==PRECOMMIT_SHA
         and manifest.get("independent_literary_review_completed") is False
         and old_batch.get("last_completed_chapter")==15
         and old_batch.get("latest_experience_sha256")==V82_EXPERIENCE_SHA
         and old_experience.get("chapter")==15,
         "WF88_INDEPENDENT_CAS_PRECOMMIT_OR_LEGACY_CHANGED")
    strategy=old_experience["reflection"]["next_strategy"]
    need(digest(strategy.encode("utf8"))==
         precommit["experience_strategy_sha256"],
         "WF88_INDEPENDENT_OLD_STRATEGY_CHANGED")
    precommit_requests=precommit["planned_requests"]
    usage=manifest["model_usage"]
    need(usage.get("reserved_requests")==4 and
         usage.get("event_count")==4 and
         usage.get("model")=="deepseek-flash" and
         len(usage.get("events",[]))==4 and
         manifest.get("second_literary_window")=="LOCKED" and
         len(manifest.get("individual_arms",[]))==4 and
         manifest.get("paired_case_sha256")==[
             PAIR_SHA["历史"],PAIR_SHA["科幻"]],
         "WF88_INDEPENDENT_MODEL_USAGE_OR_MANIFEST_INCONSISTENT")
    outcomes=[]
    total_source_bytes=0
    with TemporaryDirectory(prefix="wf88-cold-reader-only-") as tmp:
        folder=Path(tmp)
        catalog=BulkCatalog(folder/"private-metadata.sqlite3")
        try:
            source=WFPrivateReadingClient(endpoint=ENDPOINT,timeout=80)
            inventory_metadata_only(source,catalog)
            now=metadata_only_plan(catalog)
            need(now["plan_sha256"]==V87_DRAW_SHA,
                 "WF88_INDEPENDENT_V87_RANDOM_SELECTION_CHANGED")
            for case_index,reference in enumerate(FROZEN_CASES):
                genre=reference["genre_hint"]
                row=recover_key_by_sha(
                    catalog,reference["source_key_sha256"])
                need(row["category"]==genre,
                     "WF88_INDEPENDENT_ORIGINAL_SCOPE_CHANGED")
                file=folder/f"real-{case_index}.txt"
                downloaded=download_one_verified(source,row,file)
                total_source_bytes+=downloaded["bytes"]
                need(downloaded["bytes"]==reference["bytes"] and
                     downloaded["source_sha256"]==reference["source_sha256"],
                     "WF88_INDEPENDENT_ORIGINAL_SOURCE_CHANGED")
                codec_review=byte_charset_audit(
                    file,expected_source_sha256=downloaded["source_sha256"],
                    expected_size=downloaded["bytes"],
                    expected_key_sha256=reference["source_key_sha256"])
                need(codec_review["plausible_distinct_decoded_texts"]==1,
                     "WF88_INDEPENDENT_CHARSET_CHANGED")
                codec=next((x for x in ("gb18030","utf-8-sig","utf-8")
                            if x in codec_review["unique_reading_codec_aliases"]),None)
                need(codec is not None,"WF88_INDEPENDENT_CHARSET_UNKNOWN")
                raw=file.read_bytes()
                decoded=raw.decode(codec,"strict")
                need(decoded.encode(codec,"strict")==raw,
                     "WF88_INDEPENDENT_BYTE_ROUNDTRIP_INVALID")
                proof=choose_passage(
                    decoded,key_sha256=reference["source_key_sha256"],
                    source_sha256=downloaded["source_sha256"])
                for key in ("fragment_start_char","fragment_end_char",
                            "fragment_sha256","fragment_unit_count",
                            "first_read_visible_unit_sha256",
                            "sealed_unread_unit_sha256"):
                    need(proof[key]==reference[key],
                         "WF88_INDEPENDENT_SELECTED_PASSAGE_CHANGED")
                segment=decoded[proof["fragment_start_char"]:
                                proof["fragment_end_char"]]
                units=_split_into_ordered_units(segment)
                visible=tuple(units[:2])
                need(digest(units[2].encode("utf8"))==
                     reference["sealed_unread_unit_sha256"],
                     "WF88_INDEPENDENT_HIDDEN_UNIT_CHANGED")
                del segment,decoded,raw,units
                file.unlink(missing_ok=True)
                case_results={}
                for arm in ARM_ORDER[genre]:
                    expected=PINNED_ARMS[(genre,arm)]
                    entry=json.loads(reader._get_content(expected))
                    need(entry.get("format")=="wf.exam.private-one-arm.v88" and
                         entry.get("arm")==arm and
                         entry.get("case_genre_hint")==genre and
                         entry.get("case_source_sha256")==reference["source_sha256"]
                         and entry.get("precommit_sha256")==PRECOMMIT_SHA
                         and entry.get("future_text_in_prompt") is False
                         and entry.get("hidden_future_unit_sha256")==
                             reference["sealed_unread_unit_sha256"]
                         and entry.get("visible_unit_sha256")==
                             reference["first_read_visible_unit_sha256"],
                         "WF88_INDEPENDENT_ARM_SOURCE_OR_ROLE_CHANGED")
                    user=arm_prompt(
                        shared_prompt(visible),arm=arm,strategy=strategy)
                    req={"role":"craft_analysis","system":SYSTEM_PROMPT,
                         "user":user,
                         "max_tokens":MAX_OUTPUT_TOKENS_PER_REQUEST,
                         "model":"deepseek-flash"}
                    calc=digest(usage_canonical(req))
                    need(calc==entry.get("request_sha256") and
                         any(r.get("input_sha256")==calc and
                             r.get("arm")==arm and
                             r.get("genre_hint")==genre
                             for r in precommit_requests),
                         "WF88_INDEPENDENT_ACTUAL_PROMPT_NOT_PRECOMMITTED")
                    raw_answer=entry["raw_wf_answer"]
                    validation=entry["machine_source_validation"]
                    try:
                        machine=validate_wf_answer(
                            raw_answer,visible_units=visible)
                        assessment={"schema_valid":True,**machine}
                        category="TECHNICAL_SOURCE_SCHEMA_PASS"
                    except WF88BlindError as e:
                        assessment={"schema_valid":False,"reason_code":str(e),
                            "independent_literary_quality_verified":False}
                        category="SCHEMA_OR_EVIDENCE_FAILED_NO_RETRY"
                    need(validation==assessment,
                         "WF88_INDEPENDENT_SOURCE_ERROR_RECEIPT_NOT_REPRODUCIBLE")
                    case_results[arm]=(raw_answer,validation)
                    recorded=[x for x in manifest["individual_arms"]
                              if x["arm"]==arm and x["case_genre_hint"]==genre]
                    need(len(recorded)==1 and
                         recorded[0]["answer_cas_sha256"]==expected and
                         recorded[0]["schema_status"]==category and
                         recorded[0]["answer_raw_sha256"]==
                             digest(canonical(raw_answer)),
                         "WF88_INDEPENDENT_ARM_CAS_OR_VALIDATION_CHANGED")
                    outcomes.append({
                        "genre_hint":genre,"arm":arm,
                        "answer_cas_sha256":expected,
                        "mechanical_validation_status":category,
                        "mechanical_error_code":
                            assessment.get("reason_code"),
                        "answer_json_structurally_present":True,
                        "model_text_or_short_quotes_logged":False,
                        "semantic_causality_independently_verified":False,
                    })
                pair=json.loads(reader._get_content(PAIR_SHA[genre]))
                expected_comparison=mechanical_pair(
                    case_results["baseline"][0],case_results["experience"][0],
                    case_results["baseline"][1],case_results["experience"][1])
                need(pair.get("format")=="wf.exam.real-two-condition-pair.v88"
                     and pair.get("precommit_sha256")==PRECOMMIT_SHA
                     and pair.get("mechanical_comparison")==expected_comparison
                     and pair.get("baseline_arm_sha256")==
                         PINNED_ARMS[(genre,"baseline")]
                     and pair.get("experience_arm_sha256")==
                         PINNED_ARMS[(genre,"experience")],
                     "WF88_INDEPENDENT_PAIR_COMPARISON_CHANGED")
        finally:
            catalog.close()
    emit({
        "status":"WF88_INDEPENDENT_READER_R2_FOUR_ARMS_VERIFIED",
        "manifest_sha256":MANIFEST_SHA,"precommit_sha256":PRECOMMIT_SHA,
        "original_works_independently_revalidated":2,
        "sources_bytes_redownloaded":total_source_bytes,
        "reader_reconstructed_both_visible_units_and_hidden_unit":True,
        "individual_arm_results":outcomes,
        "answer_objects_independently_read_and_sha_verified":4,
        "provider_reported_prompt_tokens":usage["prompt_tokens_reported"],
        "provider_reported_completion_tokens":usage["completion_tokens_reported"],
        "provider_reported_calls":usage["reserved_requests"],
        "actual_billing_portal_reconciled":False,
        "repeated_paid_model_calls":0,
        "r2_writes":0,
        "new_trained_chapters":0,
        "literary_quality_winner":"UNDETERMINED",
        "independent_literary_semantic_judge_performed":False,
        "V49_failure_preserved":True,
        "second_literary_window":"LOCKED",
        "private_source_and_model_text_not_logged":True,
    })
    return 0

try:
    exitcode=main()
except Exception as error:
    emit({
      "status":"WF88_INDEPENDENT_READER_R2_AUDIT_FAILED",
      "reason_code":error_code(error),
      "model_calls":0,"r2_writes":0,
      "private_source_or_model_text_logged":False,
      "literary_grade_unchanged":True,
    })
    exitcode=1

print("WF88_INDEPENDENT_R2_EXAM_EXIT="+str(exitcode),flush=True)
time.sleep(4)
raise SystemExit(exitcode)
