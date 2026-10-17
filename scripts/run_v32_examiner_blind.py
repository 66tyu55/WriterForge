"""Examiner-set fair blind V32 exam of WF's ACTUAL retained V31 rule.

One-shot, three SHA-precommitted unseen prompts, no WF-generated prompts,
no new learning, no on-the-fly coaching. Same GLM-5.3 writer with and without
the frozen experiment memory from private V31 R2. Two DISTINCT critic models
are external graders, not teachers; graders receive only anonymous task + A/B
prose with opposite label order. All reports immutable private R2; zero
persistent full manuscripts, no original books or model response in logs.

Scores are uncalibrated model judgments. One bad dimension may not be
cancelled by average. No score can promote official literary skill.
"""
from __future__ import annotations
from hashlib import sha256
import json,os,re,sys

from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.reverse_discovery_models import (
    DiscoveryModel,DiscoveryCallBudget,DiscoveryError,ROLE_MODELS,
)
from writerforge.v31_stage_evidence import get_stage
from writerforge.v31_autonomous_core import CARD_FIELDS,digest,canonical,writer_instruction
from writerforge.v32_exam_bank import selected,question,manifest,manifest_sha256
from writerforge.reverse_cloud_ab import (
    DIMENSIONS,_choice_score,_brief,_has_long_exact_overlap,
)

SESSION="20261017-v32-heldout-no-coaching-3-exam-questions"
PREFIX="writerforge/v1/examiner/v32-frozen-memory-holdout"
STAGE1_SHA="cd9cfa1d6413ed84bb4d3bb18c9a77d873666df95cbcd5898d4745cfeb2e3c7c"
STAGE2_SHA="fbb06fc6a53d0708b99b813eeb4cd9c96d1152413b4880d69ddf0ad294e6b555"
EXAMINERS=("deepseek-v4-pro-0813","minimax-m3")
TARGET_MIN=850
TARGET_MAX=1400
RELATIVE_LENGTH_CAP=.15
MAX_REPORT_BYTES=21000

class ExamError(ValueError):
    pass

def _sha_bytes(blob:bytes)->str:return sha256(blob).hexdigest()
def _is_sha(value)->bool:return isinstance(value,str) and re.fullmatch("[a-f0-9]{64}",value) is not None

def exam_root(slot:int)->str:
    if type(slot) is not int or slot not in (0,1,2):
        raise ExamError("EXAM_QUESTION_SLOT_INVALID")
    config={
        "exam_session":SESSION,"slot":slot,
        "exam_manifest_sha256":manifest_sha256(),
        "question_sha256":_sha_bytes(question(slot).encode("utf-8")),
        "frozen_v31_memory_sha256":STAGE2_SHA,
        "writer":"glm-5.3-low","critics":list(EXAMINERS),
        "no_independent_training":True,
    }
    return f"{PREFIX}/{SESSION}/{slot}-{selected()[slot]}/"+_sha_bytes(_canonical(config))

def frozen_memory(vault)->tuple[dict,...]:
    one=get_stage(vault,1)
    two=get_stage(vault,2)
    if one is None or two is None or one[1]!=STAGE1_SHA or two[1]!=STAGE2_SHA:
        raise ExamError("FROZEN_SELF_TRAINING_R2_HISTORY_NOT_VERIFIED")
    a=one[0];b=two[0]
    if (a.get("parent_sha256") is not None or
        b.get("parent_sha256")!=one[1] or
        a.get("phase")!="LEARN_WRITE_SELF_REVIEW" or
        b.get("phase")!="LEARN_WRITE_SELF_REVIEW" or
        b.get("reviewer_external") is not False or
        a.get("reviewer_external") is not False or
        b.get("formal_skill_promoted") is not False):
        raise ExamError("FROZEN_LEARNER_PROVENANCE_UNVERIFIED")
    cards=b.get("memory")
    if (not isinstance(cards,list) or len(cards)!=1 or
        cards!=a.get("memory") or
        b.get("prior_memory_hashes")!=[digest(canonical(cards[0]))]):
        raise ExamError("V31_SELF_RULE_WAS_NOT_REUSED")
    for card in cards:
        if (not isinstance(card,dict) or set(card)!=CARD_FIELDS or
            any(not isinstance(card[k],str) or not 16<=len(card[k].strip())<=140
                for k in CARD_FIELDS)):
            raise ExamError("SELF_MEMORY_CARD_CORRUPTED")
    return tuple(cards)

def _grade_prompt(task:str,a:str,b:str)->str:
    return json.dumps({
        "question":task,
        "anonymous_answer_A":a,"anonymous_answer_B":b,
        "fixed_rubric":{
            "perception":"感官与人物知识约束是否自然，避免无关物件清单",
            "causality":"人物目标-选择-实际代价的因果链，不能借巧合硬翻转",
            "information":"关键伏笔是否提前建立，结尾悬念可回查",
            "continuity":"时空行动、人物立场和情节连续性",
            "language":"语言、对话与节奏是否自然，不用解释代替情节",
        },
        "negative_evidence_priority":True,
        "no_draft_labels_or_writer_identity":True,
        "scores_are_not_human_quality_proof":True,
    },ensure_ascii=False)

def _review_model(rating:dict,prose:dict,side_to_arm:dict)->dict:
    if not isinstance(rating,dict) or set(rating)!={"A","B","uncertainty"}:
        raise ExamError("EXAM_GRADER_REQUIRED_JSON_SCHEMA")
    validated={}
    for label in ("A","B"):
        validated[label]=_choice_score(rating[label],prose[label],prose["A"]+prose["B"])
    uncertainty=_brief(rating["uncertainty"],"grader_uncertainty")
    if _has_long_exact_overlap(uncertainty,prose["A"],prose["B"]):
        uncertainty="NOTE_REDACTED_"+digest(uncertainty)[:18]
    old_label=next(x for x,arm in side_to_arm.items() if arm=="control")
    new_label=next(x for x,arm in side_to_arm.items() if arm=="wf_memory")
    differences={d:validated[new_label][d]["score"]-validated[old_label][d]["score"]
                 for d in DIMENSIONS}
    return {
        "dimension_deltas_wf_memory_minus_control":differences,
        "all_five_memory_regressed":all(v<0 for v in differences.values()),
        "negative_dimensions":{k:v for k,v in differences.items() if v<0},
        "control":validated[old_label],
        "wf_memory":validated[new_label],
        "uncertainty":uncertainty,
        "grader_did_not_see_memory_card":True,
        "independent_human_review":False,
    }

def run(slot:int,*,vault=None,models_factory=None)->dict:
    root=exam_root(slot)
    token=os.environ.get("DISCOVERY_API_KEY","")
    if models_factory is None and (not isinstance(token,str) or len(token)<12):
        raise ExamError("DISCOVERY_KEY_NOT_PRESENT")
    vault=vault or R2StudyVault(R2Config.from_environment())
    if vault.config.bucket!="writerforge-private-library":
        raise ExamError("PRIVATE_EXAMINATION_BUCKET_REQUIRED")
    done=root+"/complete.json"
    if vault._head(done) is not None:
        pointer=json.loads(vault._get_small(done,2048))
        h=pointer.get("sha256")
        if not _is_sha(h):raise ExamError("INVALID_PREVIOUS_EXAM_POINTER")
        body=vault._get_small(root+"/snapshots/"+h+".json",MAX_REPORT_BYTES)
        if _sha_bytes(body)!=h:raise ExamError("PRIOR_EXAM_REPORT_SHA_FAILED")
        return {"stage":"VERIFIED_CACHED_EXAM_NO_RECHARGE",
                "slot":slot,"receipt_sha256":h,"paid_calls_now":0}
    cards=frozen_memory(vault)
    start=root+"/started.json"
    if vault._head(start) is not None:
        raise ExamError("EXAM_ATTEMPT_ALREADY_STARTED_NO_SECRET_RERUN")
    claim=_canonical({"slot":slot,"question_sha256":_sha_bytes(question(slot).encode()),
                      "exam_session":SESSION,"only_one_attempt":True})
    vault._put_small_immutable(start,claim,_sha_bytes(claim))
    budget=DiscoveryCallBudget(max_calls=7,max_reserved_output_tokens=48000)
    if models_factory is None:
        def models_factory(role,name):
            return DiscoveryModel(name=name,role=role,api_key=token,budget=budget,
                                  reasoning_effort="low" if role=="writer" else None)
    writer=models_factory("writer","glm-5.3")
    task=question(slot)
    texts={}
    graders=[]
    try:
        for arm,mem in (("control",()),("wf_memory",cards)):
            packet=writer_instruction(task,mem)
            response=writer.ask(
                "你是参加匿名考试的中文小说作者。只写这道题的原创第一章正文。"
                "不可看答案、不可回顾考试成绩、不得自行学习或修改实验规则；"
                "不输出标题、提纲、点评、代码块或学习过程。",
                packet,num_predict=8500)
            story=response.get("scene") if isinstance(response,dict) else None
            if not isinstance(story,str) or not 350<=len(story)<=4500:
                raise ExamError("WRITER_ANSWER_NOT_BOUNDED")
            texts[arm]=story
        if digest(texts["control"])==digest(texts["wf_memory"]):
            result={"grade_status":"IDENTICAL_EXAM_ANSWERS_NO_MEASURABLE_EFFECT",
                    "per_grader":[]}
        else:
            sizes={arm:len(t) for arm,t in texts.items()}
            rel=abs(sizes["control"]-sizes["wf_memory"])/max(sizes.values())
            if rel>RELATIVE_LENGTH_CAP:
                result={"grade_status":"DIFFERENT_LENGTHS_COMPARISON_NOT_FAIR",
                        "per_grader":[]}
            else:
                for index,name in enumerate(EXAMINERS):
                    # Second grader sees A/B swapped. Both never learn arms.
                    sides=({"A":"control","B":"wf_memory"} if index==0
                           else {"A":"wf_memory","B":"control"})
                    anon={k:texts[arm] for k,arm in sides.items()}
                    grader=models_factory("critic",name)
                    response=grader.ask(
                        "你是考试评阅者，不是作家助手。两份匿名文章来自同一个题目，"
                        "不要推断谁有WF实验规则。严格只看实际正文，不要夸大成绩。"
                        "保持单篇独立判断，任何五维缺点都需指出，不能用平均分遮盖。"
                        "JSON顶层严格只有A/B/uncertainty；A、B各有perception、"
                        "causality、information、continuity、language，"
                        "每项为score整数0-100和reason简短中文具体缺点或优点（4-180字），"
                        "uncertainty为4-180字的评分不确定性。不得输出Markdown。",
                        _grade_prompt(task,anon["A"],anon["B"]),num_predict=6800)
                    r=_review_model(response,anon,sides)
                    graders.append({"model":name,**r})
                result={"grade_status":"TWO_DIFFERENT_GRADERS_ANONYMOUSLY_SCORED",
                        "per_grader":graders}
        report={
            "format":"writerforge.v32-examiner-blind-evidence.v1",
            "slot":slot,"scene":selected()[slot],
            "question_sha256":_sha_bytes(task.encode()),
            "exam_manifest":manifest(),"exam_manifest_sha256":manifest_sha256(),
            "frozen_memory_stage2_sha256":STAGE2_SHA,
            "frozen_card_hashes":[digest(canonical(c)) for c in cards],
            "actual_memory_cards_used":len(cards),
            "same_glm_writer_both_arms":True,
            "model_planner_not_called":True,
            "student_was_not_allowed_to_mutate_rules_during_exam":True,
            "full_answers_saved":False,
            "answer_sha256":{k:digest(v) for k,v in texts.items()},
            "answer_characters":{k:len(v) for k,v in texts.items()},
            "absolute_length_valid":{k:TARGET_MIN<=len(v)<=TARGET_MAX
                                      for k,v in texts.items()},
            "relative_length_ratio":round(
                abs(len(texts["control"])-len(texts["wf_memory"]))/
                max(map(len,texts.values())),5),
            "question_only_sent_to_student":True,
            "exam_protocol":result,
            "provider_reported_input_tokens":budget.total_prompt_tokens,
            "provider_reported_output_tokens":budget.total_completion_tokens,
            "total_model_requests_reserved":budget.calls,
            "literary_progress_proven":False,
            "official_core_promoted":False,
            "second_window":"LOCKED",
        }
        data=_canonical(report)
        if len(data)>MAX_REPORT_BYTES:raise ExamError("EXAM_REPORT_TOO_LARGE")
        h=_sha_bytes(data)
        vault._put_small_immutable(root+"/snapshots/"+h+".json",data,h)
        if vault._get_small(root+"/snapshots/"+h+".json",MAX_REPORT_BYTES)!=data:
            raise ExamError("EXAM_R2_ROUNDTRIP_FAIL")
        pointer=_canonical({"sha256":h,"slot":slot,"session":SESSION})
        if vault._head(done) is not None:raise ExamError("EXAM_CONCURRENT_FINISH")
        vault.client.put_object(Bucket=vault.config.bucket,Key=done,
                                Body=pointer,ContentType="application/json")
        if vault._get_small(done,2048)!=pointer:
            raise ExamError("EXAM_R2_POINTER_FAIL")
        return {"stage":"REAL_V32_EXAM_VERIFIED","slot":slot,
                "scene":selected()[slot],"grade_status":result["grade_status"],
                "receipt_sha256":h,
                "model_calls":budget.calls,
                "answers_only_sha_saved":True,
                "official_literary_progress_proven":False}
    except Exception as error:
        msg=str(error)
        if not (isinstance(error,(ExamError,DiscoveryError)) and
            len(msg)<=90 and re.fullmatch("[A-Z0-9_]+",msg)):
            msg=type(error).__name__
        failure=_canonical({
            "format":"writerforge.v32-exam-failure.v1",
            "slot":slot,"scene":selected()[slot],
            "question_sha256":_sha_bytes(task.encode()),
            "code":msg,"calls":budget.calls,
            "response_observations":list(budget.response_observations),
            "no_scores_invented":True,"answer_prose_saved":False,
        })
        h=_sha_bytes(failure)
        vault._put_small_immutable(root+"/failure/"+h+".json",failure,h)
        if vault._get_small(root+"/failure/"+h+".json",8000)!=failure:
            raise ExamError("EXAM_FAILURE_RECEIPT_UNVERIFIED")
        print(json.dumps({"stage":"EXAM_FAILED_HONESTLY","slot":slot,
                          "error":msg,"failure_sha256":h,
                          "calls":budget.calls},ensure_ascii=False),flush=True)
        raise

if __name__=="__main__":
    try:
        outcome=run(int(os.environ.get("WF_EXAM_SLOT","-1")))
        print(json.dumps(outcome,ensure_ascii=False,sort_keys=True),flush=True)
    except Exception as exc:
        msg=str(exc) if isinstance(exc,(ExamError,DiscoveryError)) else type(exc).__name__
        if not re.fullmatch(r"[A-Z0-9_]{3,90}",msg):msg=type(exc).__name__
        print(json.dumps({"stage":"V32_EXAM_JOB_DID_NOT_SCORE","code":msg,
                          "no_regrade_or_secret_repetition":True}),file=sys.stderr)
        raise SystemExit(1)
