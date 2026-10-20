"""V97 entirely independent cold R2 Reader checks FIRST real longform A/B/C.

No DeepSeek or R2 writer secrets, no model calls and no raw original prose
in any public log. Re-download seven immutable raw model answer CAS objects,
three full generated candidate CAS and precommitted design. Recompute B/C
V96 source-literal action/effect/parent links from original model responses,
not the original writer's self-reported PASS. This is still NOT a human
literary semantic review.
"""
from __future__ import annotations

from pathlib import Path
import json,os,sys
ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0,str(ROOT))
for name in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
             "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(name,None)

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
PRECOMMIT="5c7fac8ef9ab0f588698711ba1b63672a2eab18ff4f65d53bf8616489d36cae1"
MANIFEST="d304d2432e2c3290b6bbd8ccb6bc209e38b7e12bc0aabb968b489b31c22b02a1"

def emit(doc):
    print(json.dumps(doc,sort_keys=True,ensure_ascii=False),flush=True)

def need(flag,reason):
    if not flag: raise ValueError(reason)


def main():
    if not os.getenv("WF_API_TOKEN") or os.getenv("WF_INDEX_UPLOAD_TOKEN") or (
          os.getenv("DEEPSEEK_API_KEY")):
        raise ValueError("WF97_COLD_READER_CREDENTIAL_ISOLATION_INVALID")
    from writerforge.v79_provisional_r2_cas_journal import (
        WFProvisionalR2CASJournal)
    from writerforge.v97_real_longform_abc_protocol import (
        ARM_ORDER,ARMS,FORMAT,MODEL,RUN_NAME,
        canonical,sha,make_precommit,
        frozen_turns_json,mechanical_prose_fields,
        MAX_PROVIDER_REQUESTS,
    )
    from writerforge.v96_causal_turns import (
        parse_turn_outline,check_turn,assemble_prose,
    )
    reader=WFProvisionalR2CASJournal(
        endpoint=ENDPOINT,read_only=True)
    need(reader.read_only and reader.writer is None,
         "WF97_COLD_READER_OBJECT_NOT_READ_ONLY")
    precommit_raw=reader._get_content(PRECOMMIT)
    need(sha(precommit_raw)==PRECOMMIT and
         precommit_raw==canonical(make_precommit()),
         "WF97_COLD_PRECOMMIT_OR_STORY_CHANGED")
    manifest_raw=reader._get_content(MANIFEST)
    need(sha(manifest_raw)==MANIFEST,
         "WF97_COLD_MANIFEST_CONTENT_SHA_CHANGED")
    result=json.loads(manifest_raw.decode("utf8","strict"))
    usage=result.get("usage",{})
    need(result.get("format")==
         "wf.writing.original-longform-abc-run.v97" and
         result.get("precommit_sha256")==PRECOMMIT and
         result.get("arm_order")==list(ARM_ORDER) and
         result.get("model")==MODEL and
         result.get("literary_improvement_verdict")=="UNDETERMINED" and
         result.get("student_drafts_author_accepted") is False and
         result.get("new_trained_chapters")==0 and
         result.get("v49_third_strike_failed_preserved") is True and
         result.get("literary_window_two")=="LOCKED" and
         len(result.get("raw_model_answers",[]))==
             MAX_PROVIDER_REQUESTS and
         len(result.get("arm_outcomes",[]))==3 and
         usage.get("reserved_provider_calls")==7,
         "WF97_COLD_MANIFEST_HISTORICAL_POLICY_OR_CALLS_CHANGED")
    original_answers={}
    seen=set()
    for ordinal,item in enumerate(result["raw_model_answers"],1):
        need(item["request_index"]==ordinal and
             item["arm"] in ARM_ORDER and
             item["response_cas_sha256"] not in seen,
             "WF97_COLD_RAW_ANSWER_ORDINAL_OR_DUPLICATE")
        seen.add(item["response_cas_sha256"])
        payload=reader._get_content(item["response_cas_sha256"])
        need(sha(payload)==item["response_cas_sha256"],
             "WF97_COLD_RAW_MODEL_ANSWER_CAS_HASH_CHANGED")
        row=json.loads(payload.decode("utf8","strict"))
        need(row.get("format")=="wf.writing.private-model-answer.v97" and
             row.get("precommit_sha256")==PRECOMMIT and
             row.get("arm")==item["arm"] and
             row.get("request_index")==ordinal and
             row.get("request_sha256")==item["request_sha256"] and
             row.get("student_answer_unmodified") is True and
             row.get("literary_quality_independently_verified") is False and
             row.get("author_accepted") is False and
             row.get("model")==MODEL and
             sha(canonical(row["raw_model_answer"]))==
                item["reported_model_output_sha256"],
             "WF97_COLD_ORIGINAL_ANSWER_METADATA_NOT_VERIFIED")
        original_answers.setdefault(item["arm"],[]).append(
            row["raw_model_answer"])
    need([len(original_answers[k]) for k in ARM_ORDER]==[1,3,3],
         "WF97_COLD_ARMS_OR_MODEL_CALL_SEQUENCE_CHANGED")
    beats=parse_turn_outline(frozen_turns_json())
    results=[]
    for arm,arm_manifest in zip(ARM_ORDER,result["arm_outcomes"]):
        answers=original_answers[arm]
        need(arm_manifest["arm"]==arm and
             arm_manifest["completed"] is True and
             arm_manifest.get("literary_quality_independently_verified")
                is False and
             arm_manifest["new_factjournal_KNOWN_writes"]==0,
             "WF97_COLD_ARM_QUALITY_OR_WRITER_AUTHORITY_CHANGED")
        if arm=="single":
            text=mechanical_prose_fields(answers[0],is_turn=False)
            proof={"source_exact_quote_gate":"NOT_APPLIED",
                   "validated_turn_count":0}
        else:
            turns=[]
            for beat,answer in zip(beats,answers):
                mechanical_prose_fields(answer,is_turn=True)
                original_raw=json.dumps(answer,ensure_ascii=False,
                                        separators=(",",":"))
                one=check_turn(
                    original_raw,beat,mode=arm,
                    accepted=tuple(turns),
                    author_confirmed_forbidden_phrases=())
                turns.append(one)
            text=assemble_prose(turns)
            proof={
                "source_exact_quote_gate":
                     "PASSED_LITERAL_ANCHORS_ONLY" if
                     arm=="causal_guard" else
                     "NOT_APPLIED_SPLIT_ONLY",
                "validated_turn_count":len(turns),
                "actor_motivation_and_causal_semantics_verified":False,
                "exact_source_actions_in_actual_model_prose":(
                     sum(int(x["receipt"]["action_anchor"] is not None)
                         for x in turns) if arm=="causal_guard" else None),
                "exact_source_effects_in_actual_model_prose":(
                     sum(int(x["receipt"]["effect_anchor"] is not None)
                         for x in turns) if arm=="causal_guard" else None),
                "parent_effect_refs_matching_actual_earlier_prose":(
                     sum(int(x["receipt"]["parent_effect_sha256"] is not None)
                         for x in turns) if arm=="causal_guard" else None),
            }
        expected=arm_manifest["candidate_r2_cas_sha256"]
        doc_raw=reader._get_content(expected)
        need(sha(doc_raw)==expected,
             "WF97_COLD_COMPLETE_CHAPTER_CAS_CHANGED")
        final=json.loads(doc_raw.decode("utf8","strict"))
        need(final.get("format")==
               "wf.writing.private-complete-candidate.v97" and
             final.get("arm")==arm and
             final.get("precommit_sha256")==PRECOMMIT and
             final.get("candidate_not_author_accepted") is True and
             final.get("model_weights_not_modified") is True and
             final.get("body")==text and
             len(text)==arm_manifest["prose_chars"],
             "WF97_COLD_FULL_CHAPTER_DIFFERS_FROM_MODEL_TURNS")
        results.append({
            "arm":arm,"letter":ARMS[arm],
            "prose_chars":len(text),
            "reached_1000_characters":len(text)>=1000,
            "raw_model_json_answers_recovered":len(answers),
            "candidate_cas_sha256":expected,
            "model_response_to_chapter_byte_reassembly_verified":True,
            "mechanical_source_gate":proof,
            "independent_semantic_literature_grade":"UNDETERMINED",
            "literary_style_or_plot_quality_proven":False,
        })
    emit({
        "status":"WF97_INDEPENDENT_R2_REAL_LONGFORM_ABC_RECONSTRUCTED",
        "manifest_cas_sha256":MANIFEST,
        "precommit_cas_sha256":PRECOMMIT,
        "all_seven_original_model_responses_cold_verified":True,
        "all_three_real_chapter_candidates_recovered":True,
        "results":results,
        "provider_reported_prompt_tokens":usage["reported_prompt_tokens"],
        "provider_reported_completion_tokens":
            usage["reported_completion_tokens"],
        "real_model_calls_original_trial":usage["reserved_provider_calls"],
        "new_paid_model_calls":0,
        "r2_writes":0,
        "author_original_books_not_transferred":True,
        "original_V92_training_experiences_unchanged":True,
        "independent_human_literary_grade_not_performed":True,
        "first_actual_narrative_logic_failure_position":
            "UNDETERMINED",
        "private_fiction_text_not_logged":True,
    })
    return 0

print("WF97_COLD_R2_REAL_LONGFORM_READER_STARTED",flush=True)
try:
    exit_code=main()
except Exception as exc:
    code=str(exc)
    if not code.startswith(("WF97_","WF96_","WF_V79_","WF_INDEX_")) or len(code)>150:
        code="WF97_COLD_READER_UNCLASSIFIED_FAIL_CLOSED"
    emit({"status":"WF97_COLD_R2_LONGFORM_VERIFICATION_FAILED",
          "reason_code":code,"paid_model_calls":0,
          "r2_writes":0,"literary_graduation":False,
          "private_generated_fiction_not_logged":True})
    exit_code=1
print("WF97_COLD_R2_REAL_LONGFORM_READER_EXIT="+str(exit_code),flush=True)
raise SystemExit(exit_code)
