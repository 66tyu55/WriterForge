"""0.AE: replay unchanged REAL 0.AD writer/judge provider wires, finish missing blind grades.

This is NOT rerunning prose or asking the author to repair a quote.
Old novel text is *never* modified. All 10 previous provider wires are
checked against their already saved SHA receipts. WF exact cite normalizer
may ONLY amend source trace metadata, never a prose byte. Reverse literary
judgments are limited to SIX calls (no retries) using the existing provider.
Failure preserves original wire, source bug, and missing scores as UNKNOWN.
No reference novel, R2, Canon, Railway or extra memory owner.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json
import os
import re

from experiments.wf_0ad_multigenre_real_paired_writing_20261025 import (
    GENRES,CRITERIA,JUDGEMENTS,OUT as UNUSED,
    normalize,parse_judge,judge_prompt,scene_prompt,
)
from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget
from writerforge.v96_causal_turns import (
    check_turn,normalize_model_source_citations,make_turn_instructions,
    V96CausalDraftError)
from writerforge.v116_state_delta import preflight_next_prose
from writerforge.v114_external_story_state import external_temporal_step,require_external_runtime

FROZEN_RUN=40190602528
PRIOR=Path("wf0ad_real_first_pilot_artifact")
OUT=Path("wf_0ae_paired_genre_repair_and_completion")
MAX_NEW_CALLS=6
MAX_NEW_RESERVED_TOKENS=10300

def guard(value,code):
    if not value:raise RuntimeError(code)
def h(value):
    return sha256(value.encode("utf8") if type(value) is str else value).hexdigest()
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2),
                    encoding="utf8")
def sanitize_code(e):
    v=str(e)
    return v if re.fullmatch(r"WF[A-Z0-9_:\-]{3,170}",v) else type(e).__name__+":NO_MODEL_RETRY"

def author_prompt(item,mode):
    same=scene_prompt(item)
    if mode=="bare-author":
        return same+'仅输出 JSON: {"prose":"你真正创作的小说原文"}。'
    beat={
        "id":"t01","kind":item["kind"],"actor":item["actor"],
        "goal":item["literary_task"]+"人物在已有场景中自行决定语言与行动",
        "causal_parent":None,"craft_focus":[]}
    return (same+"\n【WF原有V96候选来源契约，仅供校验，不规定小说答案】"+
            make_turn_instructions(beat,mode="causal_guard"))

def open_verified_real_wire(name,events):
    raw=(PRIOR/"provider-originals"/(name.replace(":","_")+".json")).read_bytes()
    event=events[name]
    guard(h(raw)==event["raw_provider_sha256"] and
          event["original_wire_preserved"] is True,
          "WF0AE_ORIGINAL_PROVIDER_SHA_NOT_VERIFIED")
    obj=json.loads(raw)
    guard(obj.get("model")=="deepseek-flash" and
          len(obj.get("choices",()))==1 and
          obj["choices"][0]["finish_reason"]=="stop",
          "WF0AE_PROVIDER_MODEL_OR_FINISH_CHANGED")
    decoded=json.loads(obj["choices"][0]["message"]["content"])
    text=json.dumps(decoded,ensure_ascii=False,separators=(",",":"))
    guard(h(text)==event["decoded_original_sha256"],
          "WF0AE_DECODED_WRITER_OR_JUDGE_DRIFT")
    return decoded

def replay_first_real_run():
    status=json.loads((PRIOR/"STATUS.json").read_text("utf8"))
    guard(status["format"]=="wf.0ad.multigenre-real-original-writing-v1" and
          status["status"]=="PARTIAL_REAL_SOURCE_OR_RATING_FAILURE_NOT_A_FULL_SCORE" and
          status["actual_model_calls"]==10 and
          status["R2_reads"]==status["R2_writes"]==status["canon_writes"]==0,
          "WF0AE_PRIOR_REAL_RUN_METADATA_INVALID")
    events={}
    for e in status["provider_sha_receipts"]:
        name=e["scene"]+":"+e["task"]
        guard(name not in events and
              re.fullmatch(r"[0-9a-f]{64}",e["prompt_sha256"]) and
              re.fullmatch(r"[0-9a-f]{64}",e["raw_provider_sha256"]),
              "WF0AE_DUPLICATE_OR_INVALID_PROVIDER_RECEIPT")
        events[name]=e
    guard(len(events)==10,"WF0AE_EXPECTED_TEN_REAL_WIRES")
    sources={}
    old_ratings={}
    for item in GENRES:
        scene=item["id"]
        pair={}
        for mode,key in (("bare-author","bare"),("WF-author","WF")):
            name=scene+":"+mode
            guard(name in events and
                  h(author_prompt(item,mode))==events[name]["prompt_sha256"],
                  "WF0AE_ORIGINAL_FROZEN_PROMPT_DRIFT")
            original=open_verified_real_wire(name,events)
            parsed=normalize(original,("prose",) if key=="bare" else
                             ("prose","trace"))
            prose=parsed["prose"].strip()
            guard(type(prose) is str and 130<=len(prose)<=1024,
                  "WF0AE_ORIGINAL_AUTHOR_PROSE_INVALID")
            pair[key]={"prose":prose,"source_sha256":h(prose)}
        source=pair["WF"]["prose"]
        beat={"id":"t01","kind":item["kind"],"actor":item["actor"],
              "goal":item["literary_task"]+"人物在已有场景中自行决定语言与行动",
              "causal_parent":None,"craft_focus":[]}
        original=open_verified_real_wire(scene+":WF-author",events)
        raw=json.dumps(normalize(original,("prose","trace")),
                       ensure_ascii=False,separators=(",",":"))
        corrected,change=normalize_model_source_citations(
            raw,beat,accepted=())
        guard(json.loads(corrected)["prose"]==source,
              "WF0AE_NORMALIZER_MODIFIED_AUTHORED_FICTION")
        try:
            checked=check_turn(corrected,beat,mode="causal_guard",
                               accepted=(),max_prose_chars=1024)
            valid="SOURCE_TRACE_VERIFIED"
            trace_err=None
        except V96CausalDraftError as e:
            checked=None
            valid="HELD_TRACE_UNVERIFIED"
            trace_err=sanitize_code(e)
        preflight=preflight_next_prose(
            source,previous_candidate_state={},cast=(item["actor"],))
        cp=external_temporal_step(source,cast=(item["actor"],))
        guard(cp["source_sha256"]==h(source),
              "WF0AE_V114_SOURCE_CHANGED")
        pair["WF_provenance"]={
            "V96_status":valid,"V96_failure_code":trace_err,
            "V96_normalization_receipt":change,
            "V96_first_effect_anchor_verified":bool(checked),
            "V116_blocked":preflight["blocked"],
            "V116_hard_findings":preflight["findings"],
            "V116_needs_review":preflight["needs_review"],
            "V116_review_findings":preflight["review_findings"],
            "V122_relation_pairs":preflight["physical_relation_review_pairs"],
            "V114_candidate_checkpoint_sha256":cp["receipt_sha256"],
            "literary_preference_cannot_override_source_state":True,
        }
        sources[scene]=pair
        rater_name=scene+":anonymous-rater-first"
        if rater_name in events:
            p=judge_prompt(item,pair,JUDGEMENTS[0])
            guard(h(p)==events[rater_name]["prompt_sha256"],
                  "WF0AE_FROZEN_RATING_PROMPT_DRIFT")
            observed=parse_judge(open_verified_real_wire(rater_name,events))
            old_ratings[scene]={
                arm:observed[label]
                for arm,label in zip(JUDGEMENTS[0],("甲","乙"))}
    return sources,old_ratings,events

class MissingOnlyRater:
    def __init__(self,secret):
        self.budget=FlashBudget(max_calls=MAX_NEW_CALLS,
                                max_reserved_output_tokens=MAX_NEW_RESERVED_TOKENS)
        self.calls=[]
        self.current=None
        self.client=DeepSeekFlashModel(
            api_key=secret,budget=self.budget,timeout_seconds=110,
            on_response_wire=self.on_response_wire)
    def on_response_wire(self,raw):
        guard(type(raw) is bytes and self.current is not None,
              "WF0AE_UNEXPECTED_PROVIDER_WIRE")
        path=OUT/"new-rater-original-wires"/(self.current+".json")
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(raw)
        self.calls[-1]["original_provider_wire_sha256"]=h(raw)
        self.calls[-1]["original_provider_wire_saved"]=True
    def grade(self,item,pair,order,part):
        self.current=item["id"]+"_"+part
        p=judge_prompt(item,pair,order)
        self.calls.append({"stage":self.current,
                           "prompt_sha256":h(p),
                           "original_provider_wire_sha256":None})
        output=self.client.ask_json(
            role="craft_analysis",
            system=("你是同题小说短篇匿名文学审阅者。"
                    "按照统一的五维百分制逐项打分，只输出合法JSON。"
                    "不能改变任何实际小说原稿或原有WF状态。"),
            user=p,max_tokens=1650)
        self.calls[-1]["decoded_original_sha256"]=h(json.dumps(
            output,ensure_ascii=False,separators=(",",":")))
        normalized=parse_judge(output)
        return {arm:normalized[label]
                for arm,label in zip(order,("甲","乙"))}

def merge_scores(first,second):
    merged={}
    for arm in ("裸模型","WF辅助"):
        v=[first[arm],second[arm]]
        scores=[sum(item["scores"].values()) for item in v]
        merged[arm]={
            "score_out_of_100":sum(scores)/2,
            "two_order_scores":scores,
            "order_variation_points":abs(scores[0]-scores[1]),
            "dimension_means":{
                axis:sum(x["scores"][axis] for x in v)/2
                for axis in ("语言自然与节制","具体细节的叙事作用",
                             "动作与因果可信度","人物心理与动机","类型目标完成程度")},
            "blind_reasons":[{"reason":x["reason"],"weakness":x["weakness"]}
                             for x in v]}
    merged["WF_minus_bare_points"]=(
        merged["WF辅助"]["score_out_of_100"]-
        merged["裸模型"]["score_out_of_100"])
    return merged

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    status={
        "format":"wf.0ae.forensic-replay-0ad-scores.v1",
        "old_real_provider_run_id":FROZEN_RUN,
        "old_author_model_calls_replayed_without_billing":8,
        "old_judge_wires_replayed_without_billing":2,
        "max_new_judge_calls":MAX_NEW_CALLS,
        "new_model_calls":0,
        "R2_reads":0,"R2_writes":0,"Canon_writes":0,
        "Railway_deployments":0,"main_modified":False,
        "author_prose_changed":False,
        "no_new_fiction_or_author_retries":True,
        "no_independent_human_grades":True,
        "same_model_family_rater":True,
        "scores_not_proof_of_literary_improvement":True,
        "no_matched_reference_book_claim":True,
        "cases":{},"status":"UNSTARTED",
    }
    model=None
    try:
        require_external_runtime()
        original,existing,events=replay_first_real_run()
        # Write ALL true original author prose, even when previous WF trace
        # contract was malformed: missing trace != missing manuscript.
        for item in GENRES:
            key=item["id"]
            pair=original[key]
            for k in ("bare","WF"):
                (OUT/(key+"_"+k+"-original.md")).write_text(
                    pair[k]["prose"],encoding="utf8")
            status["cases"][key]={
                "genre":item["genre"],"task":item["role"],
                "bare_source_sha256":pair["bare"]["source_sha256"],
                "WF_source_sha256":pair["WF"]["source_sha256"],
                "WF_provenance":pair["WF_provenance"],
                "source_pair_preserved":True,
                "scores_ready":False,
            }
        key=os.getenv("DEEPSEEK_API_KEY","")
        guard(len(key)>=16,"WF0AE_EXISTING_JUDGE_KEY_NOT_CONFIGURED")
        model=MissingOnlyRater(key)
        for item in GENRES:
            name=item["id"]
            pair=original[name]
            rows=status["cases"][name]
            try:
                first=existing.get(name)
                if first is None:
                    first=model.grade(item,pair,JUDGEMENTS[0],"first")
                second=model.grade(item,pair,JUDGEMENTS[1],"reversed")
                rows["scores"]=merge_scores(first,second)
                lengths=[len(pair[x]["prose"]) for x in ("bare","WF")]
                rows["length_ratio"]=round(max(lengths)/min(lengths),3)
                rows["comparability_length_within_25pct"]=(
                    max(lengths)/min(lengths)<=1.25)
                rows["scores_ready"]=True
            except Exception as exc:
                rows["status"]="RATING_FAILED_NO_RETRY"
                rows["failure_code"]=sanitize_code(exc)
            save(OUT/"PARTIAL.json",status)
        good=[x for x in status["cases"].values() if x["scores_ready"]]
        status["score_pair_count"]=len(good)
        status["local_mean_WF_minus_bare_points"]=(
            round(sum(x["scores"]["WF_minus_bare_points"] for x in good)/
                  len(good),1) if good else None)
        status["status"]=(
            "FOUR_REAL_GENRE_PAIRS_WITH_TWO_ORDER_SCORES"
            if len(good)==len(GENRES) else "PARTIAL_SCORES_NO_FALSE_COMPLETE")
    except Exception as exc:
        status["status"]="OLD_SOURCE_OR_SCHEMA_UNVERIFIED_NO_RETRY"
        status["failure_code"]=sanitize_code(exc)
    finally:
        if model is not None:
            status["new_model_calls"]=model.budget.calls_reserved
            status["provider_usage"]=model.budget.public_receipt()
            status["new_judge_original_sha"]=model.calls
        save(OUT/"STATUS.json",status)
        print("WF0AE_REAL_SCORES "+json.dumps({
            "status":status["status"],
            "old_author_calls_replayed_without_billing":8,
            "new_judge_calls":status["new_model_calls"],
            "rated_scenes":status.get("score_pair_count",0),
            "WF_minus_bare":{
                k:v.get("scores",{}).get("WF_minus_bare_points")
                for k,v in status["cases"].items()},
            "WF_literary_improvement_proven":False,
        },ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
