"""0.AG: complete only three missing reverse blind ratings on frozen real originals.

The first run already spent 9 calls (six author plus three first-order rater)
and saved NINE provider envelopes, but the original score decoder rejected
valid five-number positional arrays. Do not generate fiction ever again:
verify each old wire hash and original source hash, losslessly recover the
three first-order ratings, then request only reversed anonymous order.

Score recovery is NOT model learning, training, Canon or semantic verdict.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import os
import re

from experiments.wf_0ag_diverse_micro_paired_20261025 import (
    BATCH,SCENE_BY_ID,CRITERIA,JUDGEMENTS,RATER_OUTPUT_TOKENS,
    parse_micro_judge,judge_one,judge_prompt_0ag,beat,
    check_source,normalize,scene_prompt,prompt,h,save,need,
)
from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget
from writerforge.v114_external_story_state import require_external_runtime

FROZEN_RUN=40198761026
PRIOR=Path("wf0ag_first_three_provider_artifact")
OUT=Path("wf_0ag_three_real_score_only_recovery_20261025")
MAX_NEW_CALLS=3
RESERVED_NEW_OUTPUT_TOKENS=RATER_OUTPUT_TOKENS*MAX_NEW_CALLS
SOURCE_MODELS=("bare-author","WF-author")
RATER_MODELS=("blind-1",)

def original_provider_response(path,call):
    raw=path.read_bytes()
    need(h(raw)==call["raw_provider_sha256"] and
         call.get("original_wire_preserved") is True,
         "WF0AG_RECOVERY_ORIGINAL_PROVIDER_WIRE_SHA_MISMATCH")
    envelope=json.loads(raw)
    need(envelope.get("model")=="deepseek-flash" and
         type(envelope.get("choices")) is list and
         len(envelope["choices"])==1 and
         envelope["choices"][0]["finish_reason"]=="stop",
         "WF0AG_RECOVERY_PROVIDER_MODEL_OR_FINISH_CHANGED")
    content=json.loads(envelope["choices"][0]["message"]["content"])
    need(h(json.dumps(content,ensure_ascii=False,separators=(",",":")))==
         call["decoded_sha256"],
         "WF0AG_RECOVERY_DECODED_PROVIDER_DRIFT")
    return content

def replay_old_first_once():
    summary=json.loads((PRIOR/"STATUS.json").read_text("utf8"))
    need(summary.get("format")==
         "wf.0ag.first-new-diverse-micro-three-paired.v1" and
         summary["first_batch"]==list(BATCH) and
         summary["actual_model_calls"]==9 and
         summary["same_model"]=="deepseek-flash" and
         summary["reserved_output_cap"]==18000 and
         summary["R2_reads"]==summary["R2_writes"]==
         summary["Canon_writes"]==0,
         "WF0AG_RECOVERY_FROZEN_FIRST_BATCH_MANIFEST_INVALID")
    calls={}
    for event in summary["provider_calls"]:
        key=event["task"]
        need(key not in calls and
             event["max_tokens"]==(RATER_OUTPUT_TOKENS if
             key.endswith("blind-1") else 1400) and
             bool(re.fullmatch(r"[0-9a-f]{64}",
                 event["raw_provider_sha256"] or "")),
             "WF0AG_RECOVERY_ORIGINAL_CALL_NOT_FROZEN")
        calls[key]=event
    need(len(calls)==9,
         "WF0AG_RECOVERY_EXPECTED_NINE_UNCHANGED_PROVIDER_WIRES")
    result={}
    for key in BATCH:
        item=SCENE_BY_ID[key]
        prior_case=summary["cases"][key]
        need(prior_case["original_writer_ready"] and
             not prior_case["scores_ready"] and
             prior_case["rater_failure_code"]==
                 "WF0AD_JUDGE_SCORE_OR_EXPLANATION_INVALID",
             "WF0AG_RECOVERY_NOT_ONLY_THE_LOSSLESS_SCORE_FORMAT_FAILURE")
        pair={}
        for arm,task in (("bare","bare-author"),("WF","WF-author")):
            event=calls[key+"_"+task]
            need(h(prompt(item,arm))==event["prompt_sha256"],
                 "WF0AG_RECOVERY_FROZEN_AUTHOR_PROMPT_DRIFT")
            doc=original_provider_response(
                PRIOR/"provider-originals"/(key+"_"+task+".json"),event)
            normalized=normalize(doc,("prose",) if arm=="bare"
                                  else ("prose","trace"))
            prose=normalized["prose"].strip()
            ground=(PRIOR/"author-originals"/
                    (key+"-"+arm+".md")).read_text("utf8")
            need(prose==ground and
                 h(prose)==prior_case[arm+"_source_sha256"] and
                 200<=len(prose)<=350,
                 "WF0AG_RECOVERY_ORIGINAL_AUTHOR_PROSE_SHA_OR_LENGTH_CHANGED")
            pair[arm]={"prose":prose}
            if arm=="WF":
                pair[arm]["trace"]=normalized["trace"]
        name=key+"_blind-1"
        event=calls[name]
        need(h(judge_prompt_0ag(item,pair,JUDGEMENTS[0]))==
             event["prompt_sha256"],
             "WF0AG_RECOVERY_BLIND_FIRST_PROMPT_CHANGED")
        response=original_provider_response(
            PRIOR/"provider-originals"/(name+".json"),event)
        first,receipt=parse_micro_judge(response)
        # The *exact originally published* five-dimension order must be
        # the only mapping. Never weight the scores or reinterpret content.
        need(receipt["score_arrangement_recovered"]==2 and
             receipt["numeric_scores_unchanged"],
             "WF0AG_RECOVERY_FIRST_RATER_UNSUPPORTED_ARRAY")
        first_map={
            group:{
                "score":sum(first[label]["scores"].values()),
                "dimensions":first[label]["scores"],
                "model_reason":first[label]["reason"],
                "model_weakness":first[label]["weakness"],
                "score_representation_receipt":receipt,
            } for group,label in zip(JUDGEMENTS[0],("甲","乙"))}
        need(all(0<=v["score"]<=100 for v in first_map.values()),
             "WF0AG_RECOVERY_RATING_100_BOUND")
        result[key]={
            "item":item,"pair":pair,"first_ratings":first_map,
            "old_source_receipts":prior_case["WF_source_checks"],
            "source_verified_again_without_model":check_source(item,{
                "WF":pair["WF"]}),
            "original_author_wires":[
                calls[key+"_bare-author"]["raw_provider_sha256"],
                calls[key+"_WF-author"]["raw_provider_sha256"]],
            "original_first_rater_wire_sha256":event["raw_provider_sha256"],
            "original_blind_first_prompt_sha256":event["prompt_sha256"],
            "score_schema_issue_confirmed_from_provider_wire":True,
        }
    return result,summary,calls


class OnlyReverseJudge:
    def __init__(self,key):
        self.calls=[]
        self.active=None
        self.budget=FlashBudget(max_calls=MAX_NEW_CALLS,
                                max_reserved_output_tokens=
                                RESERVED_NEW_OUTPUT_TOKENS)
        self.client=DeepSeekFlashModel(
            api_key=key,budget=self.budget,timeout_seconds=110,
            on_response_wire=self.on_original)
    def on_original(self,raw):
        need(type(raw) is bytes and self.active is not None,
             "WF0AG_RECOVERY_ORPHAN_NEW_JUDGE_WIRE")
        target=OUT/"reverse-provider-originals"/(self.active+".json")
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(raw)
        self.calls[-1]["raw_provider_sha256"]=h(raw)
        self.calls[-1]["original_provider_wire_preserved"]=True

    def ask(self,item,task,role,question,max_tokens):
        need(self.active is None and task=="blind-2" and
             role=="craft_analysis" and
             max_tokens==RATER_OUTPUT_TOKENS and
             item["id"] in BATCH,
             "WF0AG_RECOVERY_AUTHOR_CALL_OR_OUT_OF_SCOPE")
        self.active=item["id"]+"_"+task
        row={"scene":item["id"],"task":task,
             "prompt_sha256":h(question),"max_tokens":max_tokens,
             "raw_provider_sha256":None,
             "original_provider_wire_preserved":False}
        self.calls.append(row)
        try:
            out=self.client.ask_json(
                role=role,system=(
                  "你是一名中文原创文学写作者或匿名评审，只回应当前角色要求。"
                  "不能读取外部原著，不使用固定评分当生成目标，必须输出JSON对象。"),
                user=question,max_tokens=max_tokens)
            row["decoded_original_sha256"]=h(
                json.dumps(out,ensure_ascii=False,separators=(",",":")))
            return out
        finally:
            self.active=None


def combine(first,reverse):
    rows={k:[first[k],reverse[k]] for k in ("裸模型","WF辅助")}
    scores={
        k:{
            "score_100":sum(x["score"] for x in values)/2,
            "two_blind_order_scores":[x["score"] for x in values],
            "order_sensitivity":abs(values[0]["score"]-values[1]["score"]),
            "five_dimensions_means":{
                axis:sum(v["dimensions"][axis] for v in values)/2
                for axis in CRITERIA},
            "two_actual_judge_reasons":values,
        } for k,values in rows.items()}
    return scores,round(
        scores["WF辅助"]["score_100"]-
        scores["裸模型"]["score_100"],2)


def main():
    OUT.mkdir(parents=True,exist_ok=False)
    status={
        "format":"wf.0ag.real-three-micro-first-ratings-lossless-recovery.v1",
        "status":"NOT_STARTED",
        "replayed_old_first_paid_run":FROZEN_RUN,
        "old_author_requests_replayed_without_new_call":6,
        "old_rater_requests_replayed_without_new_call":3,
        "new_writer_requests":0,
        "new_reverse_rater_request_cap":3,
        "new_model_calls":0,
        "no_original_prose_changed":True,
        "literary_judgment_not_author_feedback":True,
        "score_not_proof_of_WF_superiority":True,
        "independent_human_grades":False,
        "R2_reads":0,"R2_writes":0,"Canon_writes":0,
        "Railway_deployments":0,"main_modified":False,
        "cases":{},
    }
    judge=None
    try:
        recovered,prior,calls=replay_old_first_once()
        status["real_originals_and_first_blind_wires_verified"]=9
        for key in BATCH:
            record=recovered[key]
            case={
                "genre":record["item"]["genre"],
                "first_blind_scores_recovered":True,
                "first_blind_score_source_wire_sha256":
                    record["original_first_rater_wire_sha256"],
                "original_author_wires":record["original_author_wires"],
                "original_author_sha256":{
                    x:h(record["pair"][x]["prose"])
                    for x in ("bare","WF")},
                "source_verification":record[
                    "source_verified_again_without_model"],
                "original_first_order_scores":{
                    k:v["score"] for k,v in
                    record["first_ratings"].items()},
                "scores_ready":False,
                "original_prose_preserved":True,
                "literary_errors_independently_verified":False,
                "WF_false_negative_confirmed":None,
                "WF_false_positive_confirmed":None,
            }
            status["cases"][key]=case
            target=OUT/"author-originals"
            target.mkdir(parents=True,exist_ok=True)
            for arm in ("bare","WF"):
                (target/(key+"-"+arm+".md")).write_text(
                    record["pair"][arm]["prose"],encoding="utf8")
        save(OUT/"PARTIAL.json",status)
        require_external_runtime()
        need(not any(os.getenv(x) for x in (
            "WRITERFORGE_R2_ACCOUNT_ID","WRITERFORGE_R2_ACCESS_KEY_ID",
            "DISCOVERY_API_KEY","OPENAI_API_KEY","OPENROUTER_API_KEY")),
            "WF0AG_RECOVERY_NO_BOOK_OR_SECOND_PROVIDER")
        secret=os.getenv("DEEPSEEK_API_KEY","")
        need(len(secret)>=16,"WF0AG_RECOVERY_PROVIDER_KEY_NOT_CONFIGURED")
        judge=OnlyReverseJudge(secret)
        for key in BATCH:
            original=recovered[key]
            case=status["cases"][key]
            item=original["item"]
            try:
                reversed_scores=judge_one(
                    judge,item,original["pair"],JUDGEMENTS[1],"blind-2")
                scoring,diff=combine(
                    original["first_ratings"],reversed_scores)
                case["ratings"]=scoring
                case["WF_minus_bare_points"]=diff
                case["scores_ready"]=True
                lengths=[len(original["pair"][x]["prose"])
                         for x in ("bare","WF")]
                ratio=max(lengths)/min(lengths)
                case["author_codepoints"]={
                    x:len(original["pair"][x]["prose"])
                    for x in ("bare","WF")}
                case["length_ratio"]=round(ratio,3)
                case["lengths_comparable_within_15pct"]=ratio<=1.15
                worst=max(v["order_sensitivity"] for v in scoring.values())
                case["comparison_confidence"]=(
                    "NOT_COMPARABLE_LENGTH_MISMATCH" if ratio>1.15
                    else "LOW_CONFIDENCE_ORDER_SENSITIVITY" if worst>8
                    else "EXPLORATORY_SAME_FAMILY_NOT_HUMAN")
                case["status"]="BOTH_ORDERS_RATED_FROM_SOURCE_ORIGINALS"
            except Exception as error:
                code=str(error)
                case["status"]="REVERSE_SCORE_INVALID_NO_RETRY"
                case["failure_code"]=(code if re.fullmatch(
                    r"WF[A-Z0-9_:\-]{3,170}",code)
                    else type(error).__name__+":REVERSE_RATER")
            save(OUT/"PARTIAL.json",status)
        status["status"]=(
            "THREE_PAIRS_RESTORED_FROM_REAL_ORIGINAL_TWO_ORDER_SCORES"
            if all(r["scores_ready"] for r in status["cases"].values())
            else "SOURCE_ONLY_PARTIAL_GRADES_NOT_A_WIN")
    except Exception as error:
        code=str(error)
        status["status"]="FORENSIC_SOURCE_OR_PROVIDER_HOLD"
        status["failure_code"]=(code if re.fullmatch(
            r"WF[A-Z0-9_:\-]{3,170}",code)
            else type(error).__name__+":SOURCE_UNVERIFIED")
    finally:
        if judge is not None:
            status["new_model_calls"]=judge.budget.calls_reserved
            status["provider_usage"]=judge.budget.public_receipt()
            status["new_provider_calls"]=judge.calls
        save(OUT/"STATUS.json",status)
        print("WF0AG_REPLAY_THREE "+json.dumps({
            "status":status["status"],
            "prior_author_calls_repeated":status["new_writer_requests"],
            "new_rater_calls":status["new_model_calls"],
            "scored_cases":{
                k:(v.get("ratings",{}).get("裸模型",{}).get("score_100"),
                   v.get("ratings",{}).get("WF辅助",{}).get("score_100"),
                   v.get("WF_minus_bare_points"),
                   v.get("comparison_confidence"))
                for k,v in status["cases"].items()},
            "canon_writes":0,
        },ensure_ascii=False),flush=True)


if __name__=="__main__":
    main()
