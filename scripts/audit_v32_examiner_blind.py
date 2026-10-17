"""Zero-model R2 exam auditor: no mean-based pass, grader disagreements visible."""
from __future__ import annotations
from hashlib import sha256
import json,re

from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.reverse_cloud_ab import DIMENSIONS
from writerforge.v32_exam_bank import selected,manifest,manifest_sha256,question
from scripts.run_v32_examiner_blind import (
    exam_root,SESSION,EXAMINERS,STAGE2_SHA,
    TARGET_MIN,TARGET_MAX,RELATIVE_LENGTH_CAP,MAX_REPORT_BYTES,
)

def read_grades(vault):
    if vault.config.bucket!="writerforge-private-library":
        raise ValueError("PRIVATE_EXAM_AUDIT_ONLY")
    rows=[]
    for slot,scene in enumerate(selected()):
        root=exam_root(slot)
        pointer=root+"/complete.json"
        if vault._head(pointer) is None:
            rows.append({"slot":slot,"scene":scene,"status":"NOT_SCORED",
                         "grades":None,"failures_not_given_zero_score":True})
            continue
        p=json.loads(vault._get_small(pointer,2048))
        h=p.get("sha256")
        if (p.get("slot")!=slot or p.get("session")!=SESSION or
            not isinstance(h,str) or re.fullmatch(r"[a-f0-9]{64}",h) is None):
            raise ValueError("EXAM_POINTER_MISMATCH")
        raw=vault._get_small(root+"/snapshots/"+h+".json",MAX_REPORT_BYTES)
        if sha256(raw).hexdigest()!=h:raise ValueError("EXAM_RECEIPT_HASH_FAILED")
        doc=json.loads(raw)
        if (doc.get("format")!="writerforge.v32-examiner-blind-evidence.v1"
            or doc.get("slot")!=slot or doc.get("scene")!=scene
            or doc.get("question_sha256")!=sha256(question(slot).encode()).hexdigest()
            or doc.get("exam_manifest")!=manifest()
            or doc.get("exam_manifest_sha256")!=manifest_sha256()
            or doc.get("frozen_memory_stage2_sha256")!=STAGE2_SHA
            or doc.get("actual_memory_cards_used")!=1
            or doc.get("same_glm_writer_both_arms") is not True
            or doc.get("model_planner_not_called") is not True
            or doc.get("student_was_not_allowed_to_mutate_rules_during_exam") is not True
            or doc.get("full_answers_saved") is not False
            or doc.get("literary_progress_proven") is not False
            or doc.get("official_core_promoted") is not False
            or doc.get("second_window")!="LOCKED"):
            raise ValueError("EXAM_OR_MEMORY_PROVENANCE_UNVERIFIED")
        grade=doc.get("exam_protocol")
        texts=doc.get("answer_characters",{})
        hashes=doc.get("answer_sha256",{})
        if (not isinstance(grade,dict) or
            set(texts)!={"control","wf_memory"} or
            set(hashes)!={"control","wf_memory"} or
            any(type(v) is not int or not 350<=v<=4500 for v in texts.values()) or
            any(not isinstance(v,str) or re.fullmatch("[a-f0-9]{64}",v) is None
                for v in hashes.values())):
            raise ValueError("EXAM_ANSWERS_METADATA_INVALID")
        if doc.get("absolute_length_valid")!={k:TARGET_MIN<=v<=TARGET_MAX
                                            for k,v in texts.items()}:
            raise ValueError("EXAM_ABSOLUTE_LENGTH_FALSE_CLAIM")
        relative=abs(texts["control"]-texts["wf_memory"])/max(texts.values())
        if abs(doc.get("relative_length_ratio",-1)-round(relative,5))>1e-7:
            raise ValueError("EXAM_LENGTH_RATIO_FALSE_CLAIM")
        status=grade.get("grade_status")
        if (status=="TWO_DIFFERENT_GRADERS_ANONYMOUSLY_SCORED"
            and hashes["control"]!=hashes["wf_memory"]
            and relative<=RELATIVE_LENGTH_CAP):
            reviewers=grade.get("per_grader")
            if (not isinstance(reviewers,list) or len(reviewers)!=2 or
                [g.get("model") for g in reviewers]!=list(EXAMINERS)):
                raise ValueError("EXAM_CRITIC_MODEL_IDENTITY_INVALID")
            notices=[];grader_deltas=[]
            for g in reviewers:
                dim=g.get("dimension_deltas_wf_memory_minus_control")
                neg=g.get("negative_dimensions")
                control=g.get("control");memory=g.get("wf_memory")
                if (not isinstance(dim,dict) or set(dim)!=set(DIMENSIONS)
                    or not isinstance(control,dict) or not isinstance(memory,dict)
                    or set(control)!=set(DIMENSIONS) or set(memory)!=set(DIMENSIONS)):
                    raise ValueError("EXAM_CRITIC_FIVE_DIMENSIONS_MISSING")
                calculated={d:memory[d]["score"]-control[d]["score"] for d in DIMENSIONS}
                if dim!=calculated or neg!={d:v for d,v in dim.items() if v<0}:
                    raise ValueError("EXAM_CRITIC_SCORE_DIFFERENCE_FORGED")
                notices.append({d:v for d,v in dim.items() if v<0})
                grader_deltas.append(dim)
            rows.append({
                "slot":slot,"scene":scene,
                "status":"TWO_INDEPENDENT_MODELS_GRADED_NOT_HUMAN",
                "receipt_sha256":h,"question_sha256":doc["question_sha256"],
                "lengths":texts,"absolute_length_valid":doc["absolute_length_valid"],
                "individual_critic_deltas":dict(zip(EXAMINERS,grader_deltas)),
                "individual_negative_dimensions":dict(zip(EXAMINERS,notices)),
                "unanimous_memory_better_all_dimensions":all(
                    all(x[d]>0 for d in DIMENSIONS) for x in grader_deltas),
                "any_grader_found_regression":any(notice for notice in notices),
                "no_cross_critic_averaging_to_hide_loss":True,
            })
        elif status in ("DIFFERENT_LENGTHS_COMPARISON_NOT_FAIR",
                        "IDENTICAL_EXAM_ANSWERS_NO_MEASURABLE_EFFECT"):
            if grade.get("per_grader")!=[]:
                raise ValueError("EXAM_UNSCORABLE_TRIAL_FAKED_GRADES")
            rows.append({"slot":slot,"scene":scene,"status":status,
                         "receipt_sha256":h,"lengths":texts,
                         "grades":None,"insufficient_evidence":True})
        else:
            raise ValueError("EXAM_GRADER_SCHEMA_OR_FAIRNESS_UNSUPPORTED")
    scores=[r for r in rows if r["status"]=="TWO_INDEPENDENT_MODELS_GRADED_NOT_HUMAN"]
    return {
        "format":"writerforge.v32-examiner-audit.v1",
        "exam_manifest_sha256":manifest_sha256(),
        "frozen_rule_snapshot_sha256":STAGE2_SHA,
        "preselected_scenes":list(selected()),
        "results":rows,
        "attempts":3,"two_grader_valid_trials":len(scores),
        "any_critic_criticizes_memory":any(x["any_grader_found_regression"] for x in scores),
        "all_exams_consensus_positive":len(scores)==3 and all(
            x["unanimous_memory_better_all_dimensions"] for x in scores),
        "independent_human_validation":False,
        "student_did_not_set_exam_questions":True,
        "student_did_not_grade_own_answers":True,
        "experimental_memory_is_not_formal_literary_skill":True,
        "literary_skill_promotion":False,
        "stage_two_window":"LOCKED",
        "model_calls_for_this_audit":0,
    }

if __name__=="__main__":
    result=read_grades(R2StudyVault(R2Config.from_environment()))
    print(json.dumps({"stage":"V32_ACTUAL_EXAMINER_R2_RESULTS",**result},
                     ensure_ascii=False,sort_keys=True))
