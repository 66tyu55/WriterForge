"""V38 one-shot WF SELF commentary on its immutable Xi You Ji L2 foreshadowing.

NOT a new novel, not a rewriting of the frozen 7 prewriting choices, and NOT
an independent literary reviewer. The learner can say NOT_APPLIED/UNCERTAIN.

Only its source-derived L2 *abstract technique*, frozen prewriting decision
and the 1136-character original creative story are shown. The model does NOT
see copyrighted novels or an external literary exam score. All raw output
(even invalid JSON) is privately archived before validation. Historical
record from V35 remains unchanged and marked as originally incomplete.
"""
from __future__ import annotations
from hashlib import sha256
import json,os,re,sys
from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.reverse_discovery_models import (
    DiscoveryModel,DiscoveryCallBudget,DiscoveryError
)
from writerforge.v35_observable_trace import sha,canonical
from writerforge.v38_lesson_transfer_bridge import (
    append_frozen_lesson_check,LearnedTransferGateError
)
from scripts.recover_v35_afterdraft_only import _stages as frozen_source
from scripts.forensic_v37_xiyouji_L2 import frozen_evidence,sentence_menu
from scripts.run_v35_xiyouji_decision_trace import restore_stage
from scripts.debug_v36_xiyouji_learning_to_writing import (
    AFTER_SHA,EXPECTED_ORIGINAL_SHA,_after_key,_read_exact
)

ROOT="writerforge/v1/examiner/v38-append-only-original-L2-selfreport"
SESSION="20261017-frozen-WF-L2-one-extra-selfreport-v1"
MAX_RAW_BYTES=26000
STATUS_FIELDS={"foreshadowing_check","transfer_claim"}
EXCERPT_LIMIT=80

class L2SelfReportError(ValueError):pass

def _record(vault,label,content:dict)->str:
    data=canonical(content)
    if len(data)>MAX_RAW_BYTES:
        raise L2SelfReportError("V38_SELF_RECORD_TOO_LARGE")
    h=sha(data);path=f"{ROOT}/{SESSION}/{label}-{h}.json"
    vault._put_small_immutable(path,data,h)
    if vault._get_small(path,MAX_RAW_BYTES)!=data:
        raise L2SelfReportError("V38_SELF_RECORD_NOT_RECOVERABLE")
    return h

def quote_catalog(story:str)->list[dict]:
    """True exact unique text from beginning AND ending of real chapter."""
    entries=sentence_menu(story,"Q")
    selected=[*entries[:12],*entries[-16:]]
    rows=[];used=set()
    for entry in selected:
        excerpt=entry["text"][:EXCERPT_LIMIT]
        if not 10<=len(excerpt)<=EXCERPT_LIMIT or excerpt in used:
            continue
        if story.count(excerpt)!=1:
            continue
        used.add(excerpt)
        rows.append({
            "number":len(rows)+1,
            "text":excerpt,
            "start":story.find(excerpt),
            "sha256":sha(excerpt),
        })
    if len(rows)<2:
        raise L2SelfReportError("V38_SELF_NO_UNAMBIGUOUS_EXACT_QUOTES")
    return rows

def _load(vault):
    checked=frozen_evidence(vault)   # verifies actual V35/V36 SHA chain
    original=frozen_source(vault)
    stage2=restore_stage(vault,2,EXPECTED_ORIGINAL_SHA[1])
    if stage2 is None or stage2[1]!=EXPECTED_ORIGINAL_SHA[2]:
        raise L2SelfReportError("V38_FROZEN_LEARNED_LESSON_STAGE_CHANGED")
    prior=_read_exact(vault,_after_key("valid-retrospective",AFTER_SHA),
                      AFTER_SHA,36000)
    original_review={"checks":prior["checks"],
                     "biggest_mistake":prior["biggest_mistake"]}
    plan=original["plan"]
    lesson_stage=stage2[0]["payload"]
    # Pure learned candidate—not original chapter text—is shown to learner.
    l2=next((v for v in lesson_stage["lessons"]
             if v["id"]=="L2"),None)
    if l2 is None or checked["original_lesson"]!=l2:
        raise L2SelfReportError("V38_L2_HISTORICAL_LESSON_MISMATCH")
    if (checked["revised_draft"]!=original["final_text"] or
        checked["frozen_foreshadowing_decision"]!=next(
            (r for r in plan["decisions"] if r["angle"]=="foreshadowing"),None)):
        raise L2SelfReportError("V38_FROZEN_PREWRITE_OR_STORY_CHANGED")
    if any(r["angle"]=="foreshadowing" for r in original_review["checks"]):
        raise L2SelfReportError("V38_HISTORICAL_MISSING_FORESHADOWING_NO_LONGER_TRUE")
    return {
        "prior":original_review,"plan":plan,"learned":lesson_stage,
        "lesson":l2,"story":original["final_text"],
        "stage5_sha256":original["original_stage5_sha256"],
    }

def _unwrap(reply):
    if isinstance(reply,dict) and set(reply)==STATUS_FIELDS:
        return reply
    if (isinstance(reply,dict) and len(reply)==1
        and next(iter(reply)) in ("result","review","data")
        and isinstance(next(iter(reply.values())),dict)
        and set(next(iter(reply.values())))==STATUS_FIELDS):
        return next(iter(reply.values()))
    raise L2SelfReportError("V38_SELF_MODEL_JSON_INCOMPLETE")

def make_request(data:dict)->str:
    story=data["story"]
    menu=quote_catalog(story)
    selected=data["plan"]["decisions"]
    frozen=next(x for x in selected if x["angle"]=="foreshadowing")
    return json.dumps({
        "role":"WF 自己的课后核对，不是更改作文或补编考前思考",
        "lesson":{"id":"L2",**{k:data["lesson"][k] for k in (
            "technique","why","use_when","avoid_when","verification_question")}},
        "actual_precommitted_foreshadowing_decision":frozen,
        "already_frozen_story_exact_text":story,
        "host_extracted_exact_quote_catalog":menu,
        "required_reply_fields":{
            "foreshadowing_check":[
                "angle=foreshadowing",
                "actual_draft_quote=one exact quote catalog text",
                "followed_prewrite_plan=boolean",
                "observed_gap=concrete 12..250 chars",
                "possible_next_revision=concrete 12..250 chars"],
            "transfer_claim":[
                "lesson_id=L2","angle=foreshadowing",
                "application_status=CLAIMED_APPLIED/NOT_APPLIED/UNCERTAIN",
                "setup_quote and payoff_quote=two unique catalog text values IF CLAIMED_APPLIED ELSE null",
                "character_knowledge_at_setup=14..260 chars",
                "setup_to_payoff_connection=14..260 chars",
                "uncertainty_or_abstention=14..260 chars"],
        },
        "honesty_first":"找不到真实的铺垫与后续回收就报告 NOT_APPLIED 或 UNCERTAIN，不得杜撰引用，不得为学分强行自称成功。",
        "important":"这只是写后的显式自检，不是写前思考，更不是隐藏神经推理，不得修改原始故事。",
    },ensure_ascii=False,separators=(",",":"))

def run(*,vault=None,model_factory=None):
    vault=vault or R2StudyVault(R2Config.from_environment())
    if vault.config.bucket!="writerforge-private-library":
        raise L2SelfReportError("V38_PRIVATE_R2_ONLY")
    done=f"{ROOT}/{SESSION}/complete.json"
    if vault._head(done) is not None:
        p=json.loads(vault._get_small(done,2048))
        h=p.get("sha256")
        if not isinstance(h,str) or re.fullmatch(r"[0-9a-f]{64}",h) is None:
            raise L2SelfReportError("V38_SELF_COMPLETED_POINTER_INVALID")
        raw=vault._get_small(f"{ROOT}/{SESSION}/result-{h}.json",MAX_RAW_BYTES)
        if sha(raw)!=h:raise L2SelfReportError("V38_SELF_COMPLETED_REPORT_TAMPERED")
        return {"status":"V38_SELF_REPORT_CACHED","sha256":h,"calls_now":0}
    data=_load(vault)
    # Preflight the complete, real frozen quote catalog and model credential
    # BEFORE writing a paid-attempt lock. Do not lock a literary experiment
    # for a missing secret or an incomplete host-created sentence list.
    requested=make_request(data)
    key=os.environ.get("DISCOVERY_API_KEY","")
    if model_factory is None and (not isinstance(key,str) or len(key)<12):
        raise L2SelfReportError("V38_SELF_DISCOVERY_KEY_MISSING")
    started=f"{ROOT}/{SESSION}/started.json"
    if vault._head(started) is not None:
        raise L2SelfReportError("V38_SELF_REPORT_ALREADY_ATTEMPTED_NO_PAID_REPEAT")
    start=canonical({"session":SESSION,"real_V35_frozen_stage5_sha256":
                     data["stage5_sha256"],"one_shot_two_calls_max":True})
    vault._put_small_immutable(started,start,sha(start))
    budget=DiscoveryCallBudget(max_calls=2,max_reserved_output_tokens=10800)
    if model_factory is None:
        model=DiscoveryModel(name="deepseek-v4-flash-0731",
            role="planner",api_key=key,budget=budget)
    else:
        model=model_factory(budget)
    attempts=[];accepted=None;result_code=None
    try:
        for n in (1,2):
            reply=model.ask(
                "你是WriterForge自己，不是独立文学考官。对已冻结的写前L2"
                "决定和同一份已写完的小说进行严格写后对账。只选程序提供的"
                "真实引文，不能伪造引用，允许承认没有应用。"
                "只输出一个JSON对象，顶层严格包含foreshadowing_check和"
                "transfer_claim；不得修改已提交的历史作文与其他四项复盘。",
                requested+("\n你上一版结构或证据无效。只重新核对原先冻结"
                            "的数据和引用菜单，不能为了通过而编写不存在的线索。"
                           if n==2 else ""),num_predict=5100)
            raw_h=_record(vault,f"raw-before-validate-{n}",{
                "format":"writerforge.v38-learner-unreviewed-afterthought.v1",
                "attempt":n,"model_response_unmodified":reply,
                "frozen_stage5_sha256":data["stage5_sha256"],
                "not_hidden_model_reasoning":True})
            try:
                x=_unwrap(reply)
                allowed={row["text"] for row in quote_catalog(data["story"])}
                check=x.get("foreshadowing_check")
                claim=x.get("transfer_claim")
                if (not isinstance(check,dict)
                    or check.get("actual_draft_quote") not in allowed):
                    raise L2SelfReportError("V38_SELF_AFTERCHECK_QUOTE_NOT_FROM_FROZEN_MENU")
                if (not isinstance(claim,dict)
                    or (claim.get("application_status")=="CLAIMED_APPLIED"
                        and (claim.get("setup_quote") not in allowed
                             or claim.get("payoff_quote") not in allowed))):
                    raise L2SelfReportError("V38_SELF_L2_QUOTES_NOT_FROM_FROZEN_MENU")
                accepted=append_frozen_lesson_check(
                    prior_validated_response=data["prior"],
                    additional_check=x["foreshadowing_check"],
                    transfer_claim=x["transfer_claim"],story=data["story"],
                    plan=data["plan"],lessons=data["learned"])
                result_code="APPENDED_STRICT_TEXTUAL_EVIDENCE_ONLY"
                attempts.append({"n":n,"raw_sha256":raw_h,
                                 "schema_and_quote_valid":True})
                break
            except (L2SelfReportError,LearnedTransferGateError,
                    ValueError) as err:
                code=str(err)
                if not re.fullmatch("[A-Z0-9_]{3,99}",code or ""):
                    code=type(err).__name__
                attempts.append({"n":n,"raw_sha256":raw_h,
                                 "validation_error_code":code})
        if accepted is None:
            result_code="LEARNER_COULD_NOT_PROVIDE_GROUNDED_L2_APPLICATION"
        summary={
            "format":"writerforge.v38-l2-extra-afterthought-append-only.v1",
            "status":result_code,
            "original_v35_stage5_sha256":data["stage5_sha256"],
            "original_v35_after_review_sha256":AFTER_SHA,
            "history_never_rewritten":True,
            "source_lesson_was_precommitted":"L2",
            "original_report_had_missing_L2_coverage":True,
            "attempts":attempts,
            "strict_validated_aftercheck":accepted,
            "no_independent_literary_validation":True,
            "not_original_prewrite_or_hidden_reasoning":True,
            "model_calls":budget.calls,
            "formal_skill_core_promoted":False,
        }
        blob=canonical(summary)
        if len(blob)>MAX_RAW_BYTES:
            raise L2SelfReportError("V38_SELF_FINAL_REPORT_TOO_LARGE")
        h=_record(vault,"result",summary)
        pointer=canonical({"session":SESSION,"sha256":h})
        if vault._head(done) is not None:
            raise L2SelfReportError("V38_SELF_CONCURRENT_COMPLETION")
        vault.client.put_object(
            Bucket=vault.config.bucket,Key=done,
            Body=pointer,ContentType="application/json")
        if vault._get_small(done,2048)!=pointer:
            raise L2SelfReportError("V38_SELF_RESULT_POINTER_NOT_READABLE")
        transfer=(accepted["full_validated_aftercheck"][
            "learned_transfer_evidence"] if accepted else None)
        return {
            "status":result_code,"sha256":h,
            "raw_attempts":len(attempts),"calls":budget.calls,
            "application_claim":(
                transfer["evidence_claims"][0]["application_claim"]
                if transfer else None),
            "host_verified_quoted_setup_and_payoff":(
                transfer["evidence_claims"][0]["exact_characters_grounded_by_host"]
                if transfer else False),
            "semantics_proven":False,"history_unchanged":True,
            "official_promotion":False,
        }
    except Exception as err:
        message=str(err)
        if not re.fullmatch("[A-Z0-9_]{3,99}",message or ""):
            message=type(err).__name__
        h=_record(vault,"failed",{
            "format":"writerforge.v38-self-L2-aftercheck-error.v1",
            "reason_code":message,"calls":budget.calls,
            "previous_unmodified_raw_attempts":attempts,
            "frozen_stage5_sha256":data["stage5_sha256"],
            "no_study_or_draft_overwrite":True,
        })
        print(json.dumps({"status":"V38_SELF_L2_APPEND_FAILED",
                          "failure_sha256":h,"reason_code":message,
                          "calls":budget.calls},ensure_ascii=False))
        raise

if __name__=="__main__":
    try:
        print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
    except Exception as error:
        code=str(error)
        if not re.fullmatch("[A-Z0-9_]{3,99}",code or ""):
            code=type(error).__name__
        print(json.dumps({"status":"V38_L2_AFTERCHECK_UNVERIFIED",
                          "reason":code,"no_previous_history_modified":True}),
              file=sys.stderr)
        raise SystemExit(1)
