"""Read-only V34 actual graded evidence audit: no averages, no fake scores."""
from __future__ import annotations
from hashlib import sha256
import json,re

from writerforge.r2_storage import R2Config,R2StudyVault
from writerforge.v34_repair_topics import ids,question,manifest,manifest_sha
from writerforge.v33_exam_contracts import DIMENSIONS,RELATIVE_CAP,MIN_CHARS,MAX_CHARS
from scripts.run_v34_repair_e2e import (
    PREFIX,SESSION,root_for_slot,STAGE2_SHA,EXAMINERS,MAX_RECEIPT_BYTES,
)

def audit(store):
    if store.config.bucket!="writerforge-private-library":
        raise ValueError("V34_PRIVATE_BUCKET_REQUIRED")
    rows=[]
    for slot,topic in enumerate(ids()):
        root=root_for_slot(slot)
        if store._head(root+"/complete.json") is None:
            rows.append({"slot":slot,"topic":topic,"status":"NOT_SCORED",
                         "score":None,"no_score_was_invented":True})
            continue
        pointer=json.loads(store._get_small(root+"/complete.json",2048))
        h=pointer.get("sha256")
        if (pointer.get("slot")!=slot or pointer.get("session")!=SESSION or
            not isinstance(h,str) or re.fullmatch("[a-f0-9]{64}",h) is None):
            raise ValueError("V34_FINAL_POINTER_UNVERIFIED")
        raw=store._get_small(root+"/snapshot-"+h+".json",MAX_RECEIPT_BYTES)
        if sha256(raw).hexdigest()!=h:
            raise ValueError("V34_IMMUTABLE_HASH_MISMATCH")
        doc=json.loads(raw)
        if (doc.get("format")!="writerforge.v34-repair-chain-result.v1" or
            doc.get("exam_session")!=SESSION or
            doc.get("slot")!=slot or doc.get("topic")!=topic or
            doc.get("precommitted_manifest")!=manifest() or
            doc.get("precommitted_manifest_sha")!=manifest_sha() or
            doc.get("question_sha256")!=sha256(question(slot).encode()).hexdigest() or
            doc.get("frozen_student_memory_sha256")!=STAGE2_SHA):
            raise ValueError("V34_EXAM_SOURCE_IDENTITY_INVALID")
        if (not isinstance(doc.get("frozen_memory_card_sha256"),list) or
            len(doc["frozen_memory_card_sha256"])!=1 or
            doc.get("student_wrote_same_task_in_both_conditions") is not True or
            doc.get("no_memory_and_with_memory_writer_same_model") is not True or
            doc.get("student_did_not_grade_or_modify_memory") is not True or
            doc.get("full_novel_drafts_saved") is not False or
            doc.get("literary_improvement_proven") is not False or
            doc.get("formal_skill_core_promoted") is not False or
            doc.get("second_window")!="LOCKED"):
            raise ValueError("V34_FAIRNESS_OR_NO_PROMOTION_FLAG_MISSING")
        lengths=doc.get("length_evidence")
        if not isinstance(lengths,dict) or not lengths.get("no_one_sided_revision",False):
            raise ValueError("V34_LENGTH_SYMMETRY_UNVERIFIED")
        final=lengths.get("final",{})
        if not isinstance(final,dict) or "arms" not in final:
            raise ValueError("V34_LENGTH_RECORD_MISSING")
        observed=final["arms"]
        if set(observed)!={"control","wf_memory"}:
            raise ValueError("V34_MISSING_CONTROL_OR_MEMORY")
        raw_chars={}
        for label in ("control","wf_memory"):
            n=observed[label].get("chars")
            if type(n) is not int or n<220 or n>4500:
                raise ValueError("V34_DRAFT_LENGTH_INVALID")
            raw_chars[label]=n
            if observed[label].get("within_hard_range")!=(MIN_CHARS<=n<=MAX_CHARS):
                raise ValueError("V34_FALSE_ABSOLUTE_LENGTH_VALID")
        ratio=round(abs(raw_chars["control"]-raw_chars["wf_memory"])/
                    max(raw_chars.values()),6)
        if abs(final.get("relative_difference",-1)-ratio)>1e-7:
            raise ValueError("V34_FALSE_RELATIVE_LENGTH_VALID")
        correct=all(MIN_CHARS<=n<=MAX_CHARS for n in raw_chars.values()) and ratio<=RELATIVE_CAP
        if final.get("pass") is not correct:
            raise ValueError("V34_FAKE_LENGTH_PASS")
        grading=doc.get("two_critic_individual_results")
        status=doc.get("grade_status")
        if not isinstance(grading,list):
            raise ValueError("V34_GRADES_NOT_A_LIST")
        if status=="TWO_INDEPENDENT_MODELS_JSON_SCORED":
            if not correct or len(grading)!=2 or [g.get("model") for g in grading]!=list(EXAMINERS):
                raise ValueError("V34_CRITIC_OR_LENGTH_CONTRACT_FALSE")
            each={}
            for rank,grader in enumerate(grading):
                d=grader.get("unadjusted_five_dimension_review",{})
                vals=d.get("dimension_deltas_wf_memory_minus_control")
                base=d.get("control")
                wf=d.get("wf_memory")
                if (not isinstance(vals,dict) or set(vals)!=set(DIMENSIONS) or
                    not isinstance(base,dict) or set(base)!=set(DIMENSIONS) or
                    not isinstance(wf,dict) or set(wf)!=set(DIMENSIONS) or
                    grader.get("blind_a_b_swapped_for_second_grader")!=(rank==1)):
                    raise ValueError("V34_CRITIC_DIMENSIONS_OR_LABEL_SWAP_INVALID")
                for name in DIMENSIONS:
                    if vals[name]!=wf[name]["score"]-base[name]["score"]:
                        raise ValueError("V34_CRITIC_DELTA_FORGED")
                each[grader["model"]]={
                    "differences":vals,
                    "negative_dimensions":{k:v for k,v in vals.items() if v<0},
                    "format_retry_used":grader["format_validation"]["attempted_calls"]==2,
                }
            rows.append({"slot":slot,"topic":topic,"status":status,
                         "receipt_sha256":h,
                         "draft_chars":raw_chars,
                         "symmetric_revision_calls":lengths["symmetric_revision_calls"],
                         "critic_results_separate_no_average":each,
                         "human_literary_pass_verified":False})
        elif status in ("UNSCORABLE_ABSOLUTE_OR_RELATIVE_LENGTH",
                        "IDENTICAL_DRAFTS_NO_MEASURABLE_EFFECT"):
            if grading:
                raise ValueError("V34_UNSCORABLE_BUT_HAS_GRADES")
            rows.append({"slot":slot,"topic":topic,"status":status,
                         "receipt_sha256":h,"draft_chars":raw_chars,
                         "grading":None})
        else:
            raise ValueError("V34_GRADE_STATUS_UNKNOWN")
    ready=sum(r["status"]=="TWO_INDEPENDENT_MODELS_JSON_SCORED" for r in rows)
    return {"stage":"V34_ACTUAL_BOUNDED_WRITER_AND_JSON_GRADER_AUDIT",
            "new_exam_manifest_sha256":manifest_sha(),
            "actual_exam_slots":len(rows),"two_valid_grader_trials":ready,
            "results":rows,"user_goal_length_json_chain_fixed_in_real_runs":ready==len(rows),
            "independent_human_review":False,"official_skill_promoted":False,
            "any_score_averaging_used":False,"model_calls_in_audit":0,
            "old_v32_results_unchanged":True,"second_window":"LOCKED"}

if __name__=="__main__":
    print(json.dumps(audit(R2StudyVault(R2Config.from_environment())),
                     ensure_ascii=False,sort_keys=True),flush=True)
