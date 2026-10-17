"""V34 one-shot full-chain validation after MiniMax nesting and two-pass length fixes.

WF learner's authentic R2 experiment memory frozen. Same task / GLM model
for control and memory arm; each must meet 950..1300 absolute and 15%
relative length or get exactly one symmetric own-draft revision.
Two distinct critics receive reversed anonymous A/B and a schema-fixed
prompt with at most one format-correction call each. No hidden grade picking.
Past V32 failures and history never mutated.
"""
from __future__ import annotations
from hashlib import sha256
import json,os,re,sys
from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.reverse_discovery_models import DiscoveryModel,DiscoveryCallBudget,DiscoveryError
from writerforge.v31_autonomous_core import digest,canonical
from writerforge.v33_balanced_writing import controlled_pair
from writerforge.v33_exam_contracts import grade_with_one_repair, ExamContractError,DIMENSIONS
from writerforge.v34_repair_topics import ids,question,manifest,manifest_sha
from scripts.run_v32_examiner_blind import frozen_memory,_review_model,EXAMINERS,STAGE2_SHA

PREFIX="writerforge/v1/examiner/v34-two-cycle-length-nested-minimax-json"
SESSION="20261017-v34-one-fresh-pinned-exam-two-length-cycles"
MAX_RECEIPT_BYTES=22000

class RepairExamError(ValueError):
    pass

def root_for_slot(slot):
    if type(slot) is not int or slot!=0:
        raise RepairExamError("V34_INVALID_EXAM_SLOT")
    data={"session":SESSION,"slot":slot,"topic":ids()[slot],
          "exam_manifest_sha":manifest_sha(),
          "task_sha":digest(question(slot)),"memory_sha":STAGE2_SHA,
          "writer":"glm-5.3","critics":list(EXAMINERS),
          "common_target_chars":1120,"range":[950,1300],
          "symmetric_revision_cycles":2,"json_schema_retry":1}
    return f"{PREFIX}/{SESSION}/slot-{slot}/"+digest(canonical(data))

def run(slot,*,store=None,model_factory=None):
    root=root_for_slot(slot)
    token=os.environ.get("DISCOVERY_API_KEY","")
    if model_factory is None and (not isinstance(token,str) or len(token)<12):
        raise RepairExamError("DISCOVERY_KEY_UNAVAILABLE")
    store=store or R2StudyVault(R2Config.from_environment())
    if store.config.bucket!="writerforge-private-library":
        raise RepairExamError("PRIVATE_R2_BUCKET_REQUIRED")
    pointer_key=root+"/complete.json"
    if store._head(pointer_key) is not None:
        pointer=json.loads(store._get_small(pointer_key,2048))
        h=pointer.get("sha256")
        if not isinstance(h,str) or re.fullmatch("[a-f0-9]{64}",h) is None:
            raise RepairExamError("EXAM_COMPLETION_POINTER_INVALID")
        raw=store._get_small(root+"/snapshot-"+h+".json",MAX_RECEIPT_BYTES)
        if sha256(raw).hexdigest()!=h:
            raise RepairExamError("EXAM_COMPLETION_SHA_MISMATCH")
        return {"stage":"V34_CACHED_NO_NEW_MODEL_CHARGES","slot":slot,"sha256":h,"calls_now":0}
    cards=frozen_memory(store)
    once=root+"/started.json"
    if store._head(once) is not None:
        raise RepairExamError("EXAM_STARTED_PREVIOUSLY_NO_PAID_RETRY")
    claim=_canonical({"session":SESSION,"slot":slot,"single_paid_attempt":True})
    store._put_small_immutable(once,claim,sha256(claim).hexdigest())
    budget=DiscoveryCallBudget(max_calls=10,max_reserved_output_tokens=50000)
    if model_factory is None:
        def model_factory(role,name):
            return DiscoveryModel(name=name,role=role,api_key=token,budget=budget,
                reasoning_effort="low" if role=="writer" else None)
    texts=None
    length_evidence=None
    grader_data=[]
    try:
        writer=model_factory("writer","glm-5.3")
        task=question(slot)
        texts,length_evidence=controlled_pair(writer,task,cards,
            max_revision_cycles=2,initial_tokens=7000,revision_tokens=4300)
        status=("IDENTICAL_DRAFTS_NO_MEASURABLE_EFFECT"
                if digest(texts["control"])==digest(texts["wf_memory"])
                else "READY_FOR_TWO_BLIND_CRITICS"
                if length_evidence["overall_eligible_for_blind_grading"]
                else "UNSCORABLE_ABSOLUTE_OR_RELATIVE_LENGTH")
        if status=="READY_FOR_TWO_BLIND_CRITICS":
            for rank,name in enumerate(EXAMINERS):
                sides=({"A":"control","B":"wf_memory"} if rank==0
                       else {"A":"wf_memory","B":"control"})
                anon={k:texts[arm] for k,arm in sides.items()}
                critic=model_factory("critic",name)
                grade,meta=grade_with_one_repair(
                    critic,task,anon,budget_first=4600,budget_retry=4600)
                outcome=_review_model(grade,anon,sides)
                grader_data.append({"model":name,
                    "format_validation":meta,
                    "blind_a_b_swapped_for_second_grader":rank==1,
                    "unadjusted_five_dimension_review":outcome})
            status="TWO_INDEPENDENT_MODELS_JSON_SCORED"
        result={
            "format":"writerforge.v34-repair-chain-result.v1",
            "exam_session":SESSION,"slot":slot,"topic":ids()[slot],
            "precommitted_manifest":manifest(),
            "precommitted_manifest_sha":manifest_sha(),
            "question_sha256":digest(task),
            "frozen_student_memory_sha256":STAGE2_SHA,
            "frozen_memory_card_sha256":[digest(canonical(c)) for c in cards],
            "student_wrote_same_task_in_both_conditions":True,
            "no_memory_and_with_memory_writer_same_model":True,
            "student_did_not_grade_or_modify_memory":True,
            "full_novel_drafts_saved":False,
            "draft_sha256":{k:digest(v) for k,v in texts.items()},
            "length_evidence":length_evidence,
            "grade_status":status,
            "two_critic_individual_results":grader_data,
            "model_calls_reserved":budget.calls,
            "tokens_input_reported":budget.total_prompt_tokens,
            "tokens_output_reported":budget.total_completion_tokens,
            "uncertainty_not_averaged_away":True,
            "literary_improvement_proven":False,
            "formal_skill_core_promoted":False,
            "second_window":"LOCKED",
        }
        raw=_canonical(result)
        if len(raw)>MAX_RECEIPT_BYTES:
            raise RepairExamError("V34_REPORT_TOO_LARGE")
        h=sha256(raw).hexdigest()
        store._put_small_immutable(root+"/snapshot-"+h+".json",raw,h)
        if store._get_small(root+"/snapshot-"+h+".json",MAX_RECEIPT_BYTES)!=raw:
            raise RepairExamError("V34_CONTENT_SHA_READBACK_FAILED")
        pointer=_canonical({"session":SESSION,"slot":slot,"sha256":h})
        if store._head(pointer_key) is not None:
            raise RepairExamError("V34_EXAM_CONCURRENT_FINALIZATION")
        store.client.put_object(Bucket=store.config.bucket,Key=pointer_key,
                                Body=pointer,ContentType="application/json")
        if store._get_small(pointer_key,2048)!=pointer:
            raise RepairExamError("V34_POINTER_READBACK_FAILED")
        return {"stage":"V34_REAL_LENGTH_AND_JSON_E2E_VERIFIED",
                "slot":slot,"topic":ids()[slot],
                "grade_status":status,
                "initial_length_compliant":length_evidence["initial"]["pass"],
                "final_length_compliant":length_evidence["final"]["pass"],
                "symmetric_revisions":length_evidence["symmetric_revision_calls"],
                "grader_models_with_full_json":len(grader_data),
                "grade_receipt_sha256":h,
                "model_calls":budget.calls,
                "literary_progress_automatically_promoted":False}
    except Exception as exc:
        code=str(exc)
        if not (isinstance(exc,(RepairExamError,ExamContractError,DiscoveryError))
                and re.fullmatch("[A-Z0-9_]{3,90}",code)):
            code=type(exc).__name__
        failure={
            "format":"writerforge.v34-repair-chain-failure.v1",
            "exam_session":SESSION,"slot":slot,"topic":ids()[slot],
            "question_sha256":digest(question(slot)),
            "failure_code":code,"model_calls":budget.calls,
            "safe_response_observations":list(budget.response_observations),
            "safe_length_observation":length_evidence,
            "grader_models_finished":len(grader_data),
            "no_grade_invented":True,"source_prose_or_draft_saved":False,
        }
        data=_canonical(failure);h=sha256(data).hexdigest()
        store._put_small_immutable(root+"/failure-"+h+".json",data,h)
        if store._get_small(root+"/failure-"+h+".json",MAX_RECEIPT_BYTES)!=data:
            raise RepairExamError("V34_FAILURE_RECEIPT_NOT_RECOVERABLE")
        print(json.dumps({"stage":"V34_REAL_INTEGRATION_FAILED",
                          "slot":slot,"reason":code,"sha256":h,
                          "calls":budget.calls},ensure_ascii=False),flush=True)
        raise

if __name__=="__main__":
    try:
        answer=run(int(os.environ.get("WF_V34_SLOT","-1")))
        print(json.dumps(answer,ensure_ascii=False,sort_keys=True),flush=True)
    except Exception as exc:
        print(json.dumps({"stage":"V34_NOT_PASSED","reason":type(exc).__name__,
                          "old_exam_remains_immutable":True}),file=sys.stderr)
        raise SystemExit(1)
