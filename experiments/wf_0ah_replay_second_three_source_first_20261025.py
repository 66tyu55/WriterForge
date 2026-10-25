"""0.AH source-first replay of 11 immutable provider wires; only 1 missing rater.

Original writer run 40201458798: 6 authors + 5 blind rater responses.
Two pairs are already fully graded; only comedy_breakfast/blind-2 is absent.
Never call any author again. Verify each original provider raw, decoded,
prompt SHA and immutable prose before allowing ONE new reversed rating.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from shutil import copytree
import json
import os
import re

from experiments.wf_0ah_diverse_micro_paired_20261025 import (
    BATCH, SCENE_BY_ID, CRITERIA, JUDGEMENTS,
    RATER_OUTPUT_TOKENS, normalize, parse_micro_judge, judge_one,
    judge_prompt_0ag, check_source, prompt, h, save, need,
)
from experiments.wf_0ag_replay_three_real_micro_scores_only_20261025 import (
    original_provider_response, combine,
)
from writerforge.deepseek_flash_model import DeepSeekFlashModel, FlashBudget
from writerforge.v114_external_story_state import require_external_runtime

ORIGINAL_PAID_RUN=40201458798
PRIOR=Path("wf0ah_second_three_original_artifact")
OUT=Path("wf_0ah_only_comedy_reverse_source_20261025")
LAST_MISSING="comedy_breakfast"
MAX_NEW_CALLS=1
MAX_RESERVED_OUTPUT=RATER_OUTPUT_TOKENS


def original_call(events, task):
    need(task in events,"WF0AH_REPLAY_MISSING_REAL_PROVIDER_CALL")
    event=events[task]
    wire=PRIOR/"provider-originals"/(task+".json")
    response=original_provider_response(wire,event)
    return response


def parse_once(item, pair, task, order, events):
    name=item["id"]+"_"+task
    need(events[name]["prompt_sha256"]==
         h(judge_prompt_0ag(item,pair,order)),
         "WF0AH_REPLAY_RATER_PROMPT_SHA_MISMATCH")
    result=original_call(events,name)
    parsed,receipt=parse_micro_judge(result)
    grades={}
    for arm,label in zip(order,("甲","乙")):
        row=parsed[label]
        grades[arm]={
            "score":sum(row["scores"].values()),
            "dimensions":row["scores"],
            "model_reason":row["reason"],
            "model_weakness":row["weakness"],
            "representation":receipt,
        }
    return grades


def replay_original_eleven():
    old=json.loads((PRIOR/"STATUS.json").read_text("utf8"))
    need(old["format"]=="wf.0ah.second-new-diverse-micro-three-paired.v1"
         and old["first_batch"]==list(BATCH)
         and old["actual_model_calls"]==11
         and old["same_model"]=="deepseek-flash"
         and old["same_author_max_tokens"]==1400
         and old["reserved_output_cap"]==18000
         and old["R2_reads"]==old["R2_writes"]==old["Canon_writes"]==0
         and old["Railway_deployments"]==0 and not old["main_modified"],
         "WF0AH_REPLAY_FROZEN_ORIGINAL_MANIFEST_INVALID")
    events={}
    for event in old["provider_calls"]:
        key=event["task"]
        need(key not in events and event["raw_provider_sha256"]
             and event["original_wire_preserved"],
             "WF0AH_REPLAY_DUPLICATE_OR_MISSING_PROVIDER_WIRE")
        need(event["max_tokens"] == (
            RATER_OUTPUT_TOKENS if "_blind-" in key else 1400),
            "WF0AH_REPLAY_PROVIDER_CALL_BUDGET_CHANGED")
        events[key]=event
    need(len(events)==11,"WF0AH_REPLAY_EXPECTED_EXACTLY_ELEVEN_WIRES")
    cases={}
    for key in BATCH:
        item=SCENE_BY_ID[key]
        before=old["cases"][key]
        need(before["original_writer_ready"],
             "WF0AH_REPLAY_AUTHOR_NOT_COMPLETED")
        originals={}
        for arm,task in (("bare","bare-author"),("WF","WF-author")):
            name=key+"_"+task
            need(events[name]["prompt_sha256"]==h(prompt(item,arm)),
                 "WF0AH_REPLAY_AUTHOR_PROMPT_SHA_MISMATCH")
            decoded=original_call(events,name)
            parsed=normalize(
                decoded,("prose",) if arm=="bare" else ("prose","trace"))
            prose=parsed["prose"].strip()
            stored=(PRIOR/"author-originals"/
                    (key+"-"+arm+".md")).read_text("utf8")
            need(prose==stored and
                 h(prose)==before[arm+"_source_sha256"] and
                 200<=len(prose)<=350,
                 "WF0AH_REPLAY_AUTHOR_ORIGINAL_PROSE_CHANGED")
            originals[arm]=dict(parsed)
            originals[arm]["prose"]=prose
        audit=check_source(item,originals)
        need(audit["source_sha256"]==before["WF_source_checks"]["source_sha256"]
             and audit["V96_status"]==
                 before["WF_source_checks"]["V96_status"],
             "WF0AH_REPLAY_V96_SOURCE_STATUS_DRIFT")
        lengths={arm:len(originals[arm]["prose"]) for arm in ("bare","WF")}
        ratio=max(lengths.values())/min(lengths.values())
        first=parse_once(item,originals,"blind-1",JUDGEMENTS[0],events)
        note_receipt=first["裸模型"]["representation"]
        if key==LAST_MISSING:
            need(before["status"]=="ORIGINAL_SOURCES_SAVED_JUDGE_MISSING"
                 and before["rater_failure_code"]==
                     "WF0AD_MODEL_SCHEMA_INVALID"
                 and note_receipt["supplementary_note_sha256"]==
                     "67a467a94a2c88e129775e90e1c03bdf3e7eb91147a30f01fb242849611d04a4",
                 "WF0AH_REPLAY_REAL_COMEDY_NOTE_NOT_LOSSLESS")
            reverse=None
        else:
            need(before["scores_ready"]
                 and before["status"]=="PAIRED_SOURCE_AND_BLIND_GRADE_SAVED",
                 "WF0AH_REPLAY_ORIGINAL_OTHER_GENRE_GRADES_NOT_VALID")
            reverse=parse_once(
                item,originals,"blind-2",JUDGEMENTS[1],events)
        cases[key]={
            "item":item, "pair":originals, "first":first,
            "reverse":reverse, "lengths":lengths,
            "ratio":round(ratio,3),
            "original_WF_source_audit":audit,
            "source_shas":{
                arm:h(originals[arm]["prose"]) for arm in ("bare","WF")},
            "first_provider_note_sha256":
                note_receipt["supplementary_note_sha256"],
        }
    return cases,old,events


class LastReverseRater:
    def __init__(self, key):
        self.active=None
        self.calls=[]
        self.budget=FlashBudget(max_calls=1,
                                 max_reserved_output_tokens=RATER_OUTPUT_TOKENS)
        self.model=DeepSeekFlashModel(
            api_key=key,budget=self.budget,
            timeout_seconds=110,on_response_wire=self.save_wire)

    def save_wire(self,raw):
        need(self.active=="comedy_breakfast_blind-2"
             and type(raw) is bytes,
             "WF0AH_UNEXPECTED_NEW_PROVIDER_WIRE")
        file=OUT/"reverse-provider-originals"/(self.active+".json")
        file.parent.mkdir(parents=True,exist_ok=True)
        need(not file.exists(),"WF0AH_IMMUTABLE_REVERSE_WIRE_OVERWRITE")
        file.write_bytes(raw)
        self.calls[-1]["raw_provider_sha256"]=h(raw)
        self.calls[-1]["original_wire_preserved"]=True

    def ask(self,item,task,role,question,max_tokens):
        need(self.active is None and len(self.calls)==0
             and item["id"]==LAST_MISSING and task=="blind-2"
             and role=="craft_analysis" and max_tokens==RATER_OUTPUT_TOKENS,
             "WF0AH_NO_AUTHOR_OR_REPEAT_RATER_ALLOWED")
        self.active=LAST_MISSING+"_blind-2"
        event={
            "task":self.active,"prompt_sha256":h(question),
            "max_tokens":max_tokens,
            "original_wire_preserved":False,"raw_provider_sha256":None,
        }
        self.calls.append(event)
        try:
            result=self.model.ask_json(
                role=role,
                system=("你是一名中文原创文学写作者或匿名评审，只回应当前角色要求。"
                        "不能读取外部原著，不使用固定评分当生成目标，必须输出JSON对象。"),
                user=question,max_tokens=max_tokens)
            event["decoded_sha256"]=h(json.dumps(
                result,ensure_ascii=False,separators=(",",":")))
            return result
        finally:
            self.active=None


def main():
    OUT.mkdir(parents=True,exist_ok=False)
    state={
        "format":"wf.0ah.original-eleven-replay-only-one-missing-grade.v1",
        "status":"NOT_STARTED",
        "prior_paid_run":ORIGINAL_PAID_RUN,
        "old_author_calls_replayed_without_billing":6,
        "old_grade_calls_replayed_without_billing":5,
        "old_original_provider_wires_expected":11,
        "new_writer_calls":0,"max_new_grade_calls":1,"new_grade_calls":0,
        "model_scores_not_promoted_to_literary_truth":True,
        "independent_human_literary_assessment":False,
        "R2_reads":0,"R2_writes":0,"Canon_writes":0,
        "Railway_deployments":0,"main_modified":False,
        "cases":{},"new_provider_events":[],
    }
    judge=None
    try:
        cases,prior,events=replay_original_eleven()
        state["old_actual_provider_wires_verified"]=len(events)
        copytree(PRIOR/"provider-originals",
                 OUT/"provider-originals"/"original-eleven-wires")
        for key,doc in cases.items():
            for arm in ("bare","WF"):
                dest=OUT/"author-originals"/(key+"-"+arm+".md")
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_text(doc["pair"][arm]["prose"],encoding="utf8")
            row={
                "genre":doc["item"]["genre"],"literary_role":doc["item"]["role"],
                "original_prose_sha256":doc["source_shas"],
                "original_prose_lengths":doc["lengths"],
                "length_ratio":doc["ratio"],
                "WF_original_source_audit":doc["original_WF_source_audit"],
                "first_blind_scores":{k:v["score"]
                                      for k,v in doc["first"].items()},
                "first_blind_additional_note_sha256":
                    doc["first_provider_note_sha256"],
                "author_prose_changed":False,
                "software_semantic_truth_verified":False,
                "confirmed_false_green":None,
                "confirmed_false_red":None,
            }
            if doc["reverse"] is not None:
                grade,diff=combine(doc["first"],doc["reverse"])
                row.update({
                    "score_status":"TWO_REAL_SAVED_ORDERS",
                    "ratings":grade,"WF_minus_bare":diff,
                    "comparison_confidence":(
                        "NOT_COMPARABLE_LENGTH_MISMATCH"
                        if doc["ratio"]>1.15 else
                        "LOW_CONFIDENCE_ORDER_SENSITIVITY"
                        if max(v["order_sensitivity"] for v in grade.values())>8
                        else "EXPLORATORY_SAME_FAMILY_MODEL_ONLY"),
                })
            else:
                row["score_status"]="REQUIRES_ONLY_COMEDY_REVERSE"
            state["cases"][key]=row
        save(OUT/"PARTIAL.json",state)
        require_external_runtime()
        need(not any(os.getenv(n) for n in (
             "WRITERFORGE_R2_ACCOUNT_ID","WRITERFORGE_R2_ACCESS_KEY_ID",
             "OPENAI_API_KEY","DISCOVERY_API_KEY","OPENROUTER_API_KEY")),
             "WF0AH_FORBIDDEN_SOURCE_OR_OTHER_MODEL_CREDENTIAL")
        key=os.getenv("DEEPSEEK_API_KEY","")
        need(len(key)>=16,"WF0AH_EXISTING_MODEL_KEY_MISSING")
        judge=LastReverseRater(key)
        original=cases[LAST_MISSING]
        reverse=judge_one(
            judge,original["item"],original["pair"],JUDGEMENTS[1],"blind-2")
        grade,diff=combine(original["first"],reverse)
        row=state["cases"][LAST_MISSING]
        row["ratings"]=grade
        row["WF_minus_bare"]=diff
        row["comparison_confidence"]=(
            "NOT_COMPARABLE_LENGTH_MISMATCH" if original["ratio"]>1.15 else
            "LOW_CONFIDENCE_ORDER_SENSITIVITY"
            if max(v["order_sensitivity"] for v in grade.values())>8 else
            "EXPLORATORY_SAME_FAMILY_MODEL_ONLY")
        row["score_status"]="REAL_ORIGINAL_FIRST_AND_ONE_NEW_REVERSE_RATED"
        state["status"]="THREE_GENRES_ALL_TWO_ORDERS_WITH_NOT_COMPARABLE_FLAGS"
    except Exception as err:
        code=str(err)
        state["status"]="SOURCE_OR_LAST_RATING_HELD_NO_MODEL_RETRY"
        state["failure_code"]=(
            code if re.fullmatch(r"WF[A-Z0-9_:\-]{3,170}",code)
            else type(err).__name__+":NO_RETRY")
    finally:
        if judge is not None:
            state["new_grade_calls"]=judge.budget.calls_reserved
            state["new_provider_events"]=judge.calls
            state["last_judge_usage"]=judge.budget.public_receipt()
        save(OUT/"STATUS.json",state)
        print("WF0AH_SOURCE_AND_SCORE "+json.dumps({
            "status":state["status"],
            "old_source_wire_count":state.get("old_actual_provider_wires_verified",0),
            "new_writer_calls":0,
            "new_grade_calls":state["new_grade_calls"],
            "cases":{k:{"first":v.get("first_blind_scores"),
                        "score":{a:z["score_100"] for a,z in v.get(
                            "ratings",{}).items()},
                        "difference":v.get("WF_minus_bare"),
                        "comparison":v.get("comparison_confidence"),
                        } for k,v in state["cases"].items()}
        },ensure_ascii=False),flush=True)
    if state["status"]!="THREE_GENRES_ALL_TWO_ORDERS_WITH_NOT_COMPARABLE_FLAGS":
        raise RuntimeError("WF0AH_SOURCE_OR_LAST_GRADE_PARTIAL_PROTECTED")


if __name__=="__main__":
    main()
