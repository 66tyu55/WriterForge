"""V103 independent cold R2 witness reconstruction; ZERO provider/R2 writes.

Only prints outputs of the newly examiner-authored original fiction exercise.
Never opens user-private novel blobs, V82/V92 training or other LLM lessons.
No DeepSeek key, no index writer, no authoritative/accepted manuscript writes.
"""
from __future__ import annotations
import os,sys,json
from hashlib import sha256

for secret in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
               "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(secret,None)

from writerforge.v79_provisional_r2_cas_journal import (
    WFProvisionalR2CASJournal,
)
from writerforge.v103_frozen_original_exam import (
    CHAPTERS,TRANSFER_STORY,RUN_NAME,SOURCE_KIND,encode,h,
)
from wf_railway_v103_real_three_reveal_exam import (
    ENDPOINT,validate_read,printable,
)
from wf_railway_v103b_one_unused_transfer import (
    PARENT_MANIFEST,PARENT_PRECOMMIT,
)
from writerforge.v101_narrative_reader import V101ReadingError

SUPPLEMENT="ac1438cd1414198c88049bef4b8fbbf8fb832aca5d5cbdb3e03dc5d1c19e8c00"

def need(cond,code):
    if not cond:raise ValueError(code)

def get(journal,address):
    need(type(address) is str and len(address)==64,
         "WF103C_CAS_POINTER_BOUNDS")
    raw=journal._get_content(address)
    need(h(raw)==address,"WF103C_ACTUAL_REMOTE_SOURCE_CHANGED")
    return json.loads(raw.decode("utf8","strict"))

def main():
    need(bool(os.environ.get("WF_API_TOKEN")) and
         not os.environ.get("DEEPSEEK_API_KEY") and
         not os.environ.get("WF_INDEX_UPLOAD_TOKEN"),
         "WF103C_READER_ONLY_CREDENTIAL_BOUNDARY_INVALID")
    cas=WFProvisionalR2CASJournal(endpoint=ENDPOINT,read_only=True)
    need(cas.read_only is True and cas.writer is None,
         "WF103C_READER_HAS_WRITER_PRIVILEGES")
    m=get(cas,PARENT_MANIFEST)
    post=get(cas,SUPPLEMENT)
    old=get(cas,PARENT_PRECOMMIT)
    need(old.get("run_name")==RUN_NAME and
         old.get("source_kind")==SOURCE_KIND and
         old.get("source_sha256")==h(encode(CHAPTERS)) and
         old.get("originals_transmitted_to_model_in_status_check") is not True,
         "WF103C_EXAMINER_ORIGINAL_SOURCE_NOT_PINNED")
    need(m.get("format")=="wf.exam.v103.actual-reading-transfer-manifest"
         and m.get("precommit_sha256")==PARENT_PRECOMMIT
         and m.get("real_premium_model_calls")==4
         and m.get("reader_literal_anchored_count")==2
         and len(m.get("model_call_receipts",[]))==4
         and m.get("no_factjournal_or_canon_writes") is True,
         "WF103C_PARENT_REAL_RESULTS_MISSING")
    need(post.get("format")=="wf.exam.v103.posthoc-exploratory-transfer-pair"
         and post.get("parent_original_manifest_cas_sha256")==PARENT_MANIFEST
         and post.get("total_supplier_requests")==5
         and post.get("posthoc_protocol_deviation_from_original") is True
         and post.get("old_red_remains_red") is True
         and post.get("independent_literary_human_review")=="NOT_PERFORMED",
         "WF103C_SUPPLEMENT_NOT_GENUINE_EXPLORATORY")
    students=[]
    for n,ref in enumerate(m["model_call_receipts"][:3],1):
        doc=get(cas,ref["raw_response_cas_sha256"])
        need(doc["format"]=="wf.exam.original-student-response.v103"
             and doc["ordinal"]==n
             and doc["stage"]=="sequential_reader"
             and doc["precommit_sha256"]==PARENT_PRECOMMIT,
             "WF103C_READ_SOURCE_IDENTITY_CHANGED")
        answer=doc["answer_unmodified"]
        students.append(answer)
        if n in (2,3):
            check=validate_read(answer,CHAPTERS[n-1])
            need(check["evidence_existentially_checked"] is True,
                 "WF103C_OLD_SIGNED_READER_LITERAL_EVIDENCE_CHANGED")
        printable({
            "status":"WF103C_COLD_READER_FULL_INDEPENDENT_LITERARY_CONTENT",
            "chapter":n,
            "student_motives":answer.get("motives"),
            "student_knowledge_boundary":answer.get("knowledge_boundary"),
            "student_relationship":answer.get("relationship"),
            "student_emotion":answer.get("emotion"),
            "student_causality":answer.get("causality"),
            "student_prediction":answer.get("forecast"),
            "student_correction":answer.get("correction"),
            "student_taste":answer.get("literary_sentence"),
            "student_self_extracted_lesson":answer.get("transfer_lesson"),
            "original_v103_stage_one_literal_status":(
                "RED_CAUSAL_ACTION_EFFECT_PARTIAL" if n==1
                else "EXACT_SOURCE_WITNESSES_VERIFIED_NOT_SEMANTIC"),
            "independent_human_judge":"NOT_PERFORMED",
            "source_is_examiner_original_only":True,
        })
    b=get(cas,m["model_call_receipts"][3]["raw_response_cas_sha256"])
    n=get(cas,post["real_model_original_reply_cas_sha256"])
    base=b.get("answer_unmodified",{}).get("prose")
    enhanced=n.get("answer_unmodified",{}).get("prose")
    need(type(base) is str and type(enhanced) is str and
         h(base.encode("utf8"))==post["original_baseline_prose_sha256"]
         and h(enhanced.encode("utf8"))==post["new_informed_prose_sha256"]
         and base!=enhanced,
         "WF103C_REAL_PROSE_AND_CANDIDATE_SHA_MISMATCH")
    # The text is made up entirely for the new original experiment, not a
    # private imported novel. Two blind labels only, without arm mapping.
    pair=sorted((base,enhanced),key=lambda x:h(x.encode("utf8")))
    for label,body in zip(("匿名稿件甲","匿名稿件乙"),pair):
        printable({
            "status":"WF103C_VERIFIED_FULL_ORIGINAL_EXPERIMENTAL_MANUSCRIPT",
            "blind_label":label,
            "actual_characters":len(body),
            "prose_sha256":h(body.encode("utf8")),
            "prose":body,
            "private_user_novel_source_embedded":False,
            "human_literary_grade":"UNDETERMINED",
        })
    printable({
        "status":"WF103C_INDEPENDENT_R2_ORIGINAL_RESPONSES_AND_FULL_PROSE_VERIFIED",
        "parent_manifest":PARENT_MANIFEST,
        "exploratory_supplement_manifest":SUPPLEMENT,
        "three_reader_responses_rehydrated":len(students),
        "real_original_prose_candidates":len(pair),
        "model_calls_this_readback":0,
        "r2_writes_this_readback":0,
        "first_chapter_source_gate_red_still_preserved":True,
        "literary_quality_grade":"UNDETERMINED",
        "user_private_original_books_downloaded":False,
    })
    return 0

if __name__=="__main__":
    printable({"status":"WF103C_COLD_R2_READER_ONLY_START",
               "no_billing":True,"private_user_corpus_not_accessed":True})
    try:rc=main()
    except Exception as ex:
        val=str(ex)
        if not val.startswith(("WF103C_","WF103_","WF101_","WF102_","WF_V79_","WF_INDEX_")):
            val="WF103C_UNKNOWN_FAIL_CLOSED"
        printable({"status":"WF103C_COLD_R2_AUDIT_STOPPED",
                   "reason_code":val,
                   "model_calls":0,"r2_writes":0})
        rc=1
    printable({"status":"WF103C_COLD_R2_AUDIT_EXIT","exit_code":rc})
    raise SystemExit(rc)
