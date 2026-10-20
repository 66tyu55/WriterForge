"""V100 read old V97 ORIGINAL A/B/C and seal anonymous literary review CAS.

Run only as a manually selected private cloud job with existing Reader and
IndexWriter capabilities. Never import or call DeepSeek; no original novel,
original raw model JSON, private prose or secrets are written to public logs.
NO automatic training, no new writer generation, no canonical facts.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json, os, secrets, sys

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0,str(ROOT))
# Fail closed against accidental paid calls even when live service has a key.
for name in ("DEEPSEEK_API_KEY","DISCOVERY_API_KEY","WF_LEARN_UPLOAD_TOKEN"):
    os.environ.pop(name,None)

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"


def need(value,code):
    if not value:
        raise ValueError(code)


def emit(value):
    print(json.dumps(value,ensure_ascii=False,sort_keys=True),flush=True)


def run():
    need(bool(os.environ.get("WF_API_TOKEN")) and
         bool(os.environ.get("WF_INDEX_UPLOAD_TOKEN")) and
         not os.environ.get("DEEPSEEK_API_KEY"),
         "WF100_COLD_READER_EXISTING_CREDENTIALS_UNAVAILABLE")
    from writerforge.v79_provisional_r2_cas_journal import (
        WFProvisionalR2CASJournal,
    )
    from writerforge.v97_real_longform_abc_protocol import (
        ARM_ORDER,MODEL,MAX_PROVIDER_REQUESTS,make_precommit,
        canonical as v97_canonical,sha as v97_sha,
        frozen_turns_json,mechanical_prose_fields,
    )
    from writerforge.v96_causal_turns import (
        parse_turn_outline,check_turn,assemble_prose,
    )
    from writerforge.v100_blind_fair_protocol import (
        HISTORICAL_PRECOMMIT,HISTORICAL_MANIFEST,
        HISTORICAL_ACTUAL,BLIND_IDS,historical_blind_packets,
        canonical,digest,
    )

    # Existing append-only private CAS namespace, never LEARN/CANON.
    cas=WFProvisionalR2CASJournal(endpoint=ENDPOINT)
    cas.require_writer_ready()
    pre=cas._get_content(HISTORICAL_PRECOMMIT)
    need(v97_sha(pre)==HISTORICAL_PRECOMMIT and
         pre==v97_canonical(make_precommit()),
         "WF100_V97_PRECOMMIT_OR_FROZEN_TASK_MISMATCH")
    payload=cas._get_content(HISTORICAL_MANIFEST)
    need(v97_sha(payload)==HISTORICAL_MANIFEST,
         "WF100_V97_MANIFEST_CAS_MISMATCH")
    manifest=json.loads(payload.decode("utf8","strict"))
    usage=manifest.get("usage",{})
    need(manifest.get("format")=="wf.writing.original-longform-abc-run.v97"
         and manifest.get("precommit_sha256")==HISTORICAL_PRECOMMIT
         and manifest.get("arm_order")==list(ARM_ORDER)
         and manifest.get("model")==MODEL
         and manifest.get("new_trained_chapters")==0
         and manifest.get("student_drafts_author_accepted") is False
         and manifest.get("literary_improvement_verdict")=="UNDETERMINED"
         and manifest.get("v49_third_strike_failed_preserved") is True
         and manifest.get("literary_window_two")=="LOCKED"
         and len(manifest.get("raw_model_answers",[]))==
             MAX_PROVIDER_REQUESTS==7
         and len(manifest.get("arm_outcomes",[]))==3
         and usage.get("reserved_provider_calls")==7,
         "WF100_V97_MANIFEST_HISTORY_OR_POLICY_CHANGED")

    originals={}
    answer_shas=set()
    for index,item in enumerate(manifest["raw_model_answers"],1):
        addr=item["response_cas_sha256"]
        need(item["request_index"]==index and
             item["arm"] in ARM_ORDER and addr not in answer_shas,
             "WF100_V97_ORIGINAL_ANSWER_ORDER_OR_REPETITION")
        answer_shas.add(addr)
        raw=cas._get_content(addr)
        need(v97_sha(raw)==addr,"WF100_V97_ORIGINAL_ANSWER_HASH")
        doc=json.loads(raw.decode("utf8","strict"))
        need(doc.get("format")=="wf.writing.private-model-answer.v97"
             and doc.get("arm")==item["arm"]
             and doc.get("precommit_sha256")==HISTORICAL_PRECOMMIT
             and doc.get("request_index")==index
             and doc.get("request_sha256")==item["request_sha256"]
             and doc.get("student_answer_unmodified") is True
             and doc.get("literary_quality_independently_verified") is False
             and doc.get("model")==MODEL
             and v97_sha(v97_canonical(doc["raw_model_answer"]))==
                 item["reported_model_output_sha256"],
             "WF100_V97_ORIGINAL_ANSWER_CONTENT_MISMATCH")
        originals.setdefault(item["arm"],[]).append(doc["raw_model_answer"])
    need([len(originals[x]) for x in ARM_ORDER]==[1,3,3],
         "WF100_V97_EXACT_SEVEN_ANSWER_SEQUENCE_INVALID")

    turns=parse_turn_outline(frozen_turns_json())
    body_by_arm={}
    origin_by_arm={}
    for arm,meta in zip(ARM_ORDER,manifest["arm_outcomes"]):
        need(meta["arm"]==arm and meta["completed"] is True and
             meta["new_factjournal_KNOWN_writes"]==0 and
             meta["literary_quality_independently_verified"] is False,
             "WF100_V97_ARM_WAS_NOT_PURE_UNACCEPTED_CANDIDATE")
        if arm=="single":
            body=mechanical_prose_fields(originals[arm][0],is_turn=False)
        else:
            accepted=[]
            for turn,answer in zip(turns,originals[arm]):
                mechanical_prose_fields(answer,is_turn=True)
                parsed=check_turn(
                    json.dumps(answer,ensure_ascii=False,separators=(",",":")),
                    turn,mode=arm,accepted=tuple(accepted),
                    author_confirmed_forbidden_phrases=())
                accepted.append(parsed)
            body=assemble_prose(accepted)
        addr=meta["candidate_r2_cas_sha256"]
        raw=cas._get_content(addr)
        need(v97_sha(raw)==addr,"WF100_V97_ORIGINAL_CANDIDATE_CAS_CHANGED")
        doc=json.loads(raw.decode("utf8","strict"))
        need(doc.get("format")=="wf.writing.private-complete-candidate.v97"
             and doc.get("arm")==arm
             and doc.get("precommit_sha256")==HISTORICAL_PRECOMMIT
             and doc.get("candidate_not_author_accepted") is True
             and doc.get("body")==body
             and len(body)==meta["prose_chars"]==HISTORICAL_ACTUAL[arm],
             "WF100_V97_REASSEMBLED_BODY_NOT_IDENTICAL")
        body_by_arm[arm]=body
        origin_by_arm[arm]=addr

    blind_order=list(ARM_ORDER)
    secrets.SystemRandom().shuffle(blind_order)
    packets,mapping,fairness=historical_blind_packets(
        body_by_arm,tuple(blind_order))
    need(fairness["lengths_comparable"] is False,
         "WF100_HISTORICAL_LENGTH_BIAS_NOT_DISCLOSED")

    # No original prose in the public manifest or Railway logs; full text
    # exists only in private, independently hashed packet CAS objects.
    listing=[]
    for packet,link in zip(packets,mapping):
        content=canonical(packet)
        addr,_=cas._put_content(content)
        need(cas._get_content(addr)==content,
             "WF100_ANONYMOUS_PACKET_READBACK_FAILED")
        listing.append({"blind_id":packet["blind_id"],"packet_cas_sha256":addr})
        link["packet_cas_sha256"]=addr
        link["original_candidate_cas_sha256"]=origin_by_arm[link["arm"]]
    need([row["blind_id"] for row in listing]==list(BLIND_IDS),
         "WF100_PRIVATE_BLIND_ID_ORDER_CHANGED")

    # Reviewer gets only the public-looking index CAS (still stored PRIVATE).
    # Owner keeps the separate mapping receipt, never shared with judges.
    judge_index={
        "format":"wf.writing.anonymous-review-index.v100",
        "case_id":"v97_historical_ferry",
        "anonymous_packets":listing,
        "review_stage":"UNREVIEWED",
        "review_method":"INDEPENDENT_HUMAN_IF_AUTHORIZED",
        "length_bias_warning":"ACTUAL_PROSE_LENGTHS_NOT_COMPARABLE",
        "blind_method_identity_masked":True,
        "first_verified_error_position":None,
        "literary_winner":"UNDETERMINED",
    }
    index_content=canonical(judge_index)
    index_sha,_=cas._put_content(index_content)
    need(cas._get_content(index_sha)==index_content,
         "WF100_PRIVATE_INDEX_READBACK_FAILED")
    owner_key={
        "format":"wf.writing.owner-only-unblinding-key.v100",
        "v97_original_manifest":HISTORICAL_MANIFEST,
        "v97_original_precommit":HISTORICAL_PRECOMMIT,
        "judge_index_cas_sha256":index_sha,
        "private_arm_mapping":mapping,
        "length_fairness":fairness,
        "judge_not_assigned_and_reviews_not_completed":True,
        "unblind_only_after_all_reviews_frozen":True,
        "old_original_candidates_unchanged":True,
        "v92_learning_untouched":True,
        "new_model_calls":0,
        "canonical_writes":0,
    }
    key_content=canonical(owner_key)
    key_sha,_=cas._put_content(key_content)
    need(cas._get_content(key_sha)==key_content,
         "WF100_OWNER_KEY_READBACK_FAILED")
    emit({
        "status":"WF100_V97_PRIVATE_ANONYMOUS_PACKETS_SEALED",
        "v97_manifest_cas_sha256":HISTORICAL_MANIFEST,
        "blind_review_index_cas_sha256":index_sha,
        "owner_only_unblinding_key_cas_sha256":key_sha,
        "anonymous_packet_count":len(listing),
        "exact_7_model_replies_verified":True,
        "exact_3_original_manuscripts_verified":True,
        "char_lengths_known_to_owner_but_not_in_blind_index":True,
        "v97_lengths_comparable":False,
        "new_model_calls":0,
        "historical_original_r2_objects_changed":False,
        "private_story_text_or_keys_in_logs":False,
        "human_reviews":0,
        "first_logic_failure_character":None,
        "literary_winner":"UNDETERMINED",
        "newly_trained_chapters":0,
    })
    return 0


print("WF100_V97_PRIVATE_BLIND_PREPARATION_STARTED",flush=True)
try:
    code=run()
except Exception as exc:
    message=str(exc)
    if not (message.startswith(("WF100_","WF99_","WF97_","WF96_",
                                "WF_V79_","WF_INDEX_"))
            and len(message)<=150):
        message="WF100_PRIVATE_BLIND_FAIL_CLOSED_UNCLASSIFIED"
    emit({"status":"WF100_V97_PRIVATE_BLIND_PREPARATION_PAUSED",
          "error_code":message,"paid_model_calls":0,
          "literary_quality_winner":"UNDETERMINED",
          "private_prose_not_printed":True})
    code=1
print("WF100_V97_PRIVATE_BLIND_PREPARATION_EXIT="+str(code),flush=True)
raise SystemExit(code)
