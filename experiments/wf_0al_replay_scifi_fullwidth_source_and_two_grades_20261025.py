"""0.AL: replay four immutable ORIGINAL 0.AJ DeepSeek writer wires.

Romance bare manuscript was 195 chars (below 200), and SciFi WF had one
genuine U+FF0C between TOP-LEVEL JSON fields. Keep both original provider
responses forever. The precise old SciFi prose can be recovered without
altering a single character. Score those same FOUR existing manuscripts
in two anonymous orders (at most four judge-only calls, zero writer calls).
Grades of unequal/out-of-range lengths remain NOT_COMPARABLE even if high.
No training, external original, R2, Canon, Railway, or new literary memory.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from shutil import copytree
import json
import os
import re

from experiments.wf_0aj_diverse_micro_paired_20261025 import (
    BATCH, SCENE_BY_ID, CRITERIA, JUDGEMENTS,
    RATER_OUTPUT_TOKENS, prompt, judge_prompt_0ag, judge_one,
    check_source, normalize, h, save, need,
)
from experiments.wf_0ag_replay_three_real_micro_scores_only_20261025 import combine
from writerforge.deepseek_flash_model import (
    DeepSeekFlashModel,FlashBudget,
    recover_single_fullwidth_author_field_separator,
)
from writerforge.v114_external_story_state import require_external_runtime

PRIOR_RUN=40205342567
PRIOR=Path("wf0aj_two_original_author_artifact")
OUT=Path("wf_0al_0aj_four_original_author_score_only_replay_20261025")
ORIGINAL_SOURCE_SHA={
    "romance_photos":{
        "bare":"c963ad02fcd39a894b060938f73015d47e903f51ad029ddd0714fb76b8e4bcd8",
        "WF":"74e4217d4815a303dbab5cae980df736b987fef26281af3950e5d21909a9b352",
    },
    "scifi_airlock":{
        "bare":"0d06b93684f5103a182fb03fd2ec28ca1a6557fe109282fcb3346127b6bfbd53",
        "WF":"713534247a7071accb8852ee5e72133d3420ceeaabecf92cf1a542d5626edf35",
    },
}
REAL_SCIFI_ORIGINAL_RAW_WIRE_SHA="61b61ec1c651735e07a01df91b2836d859d98d6dcc397879ef3118afd8755548"
REAL_SCIFI_ORIGINAL_MESSAGE_SHA="bab2b02e7afe6084febf2ca51088ac873887683faa4c5b340152a7b4e9e705a6"
MAX_NEW_CALLS=4
MAX_NEW_RATER_TOKENS=RATER_OUTPUT_TOKENS*MAX_NEW_CALLS


def read_original_provider(event):
    wire=PRIOR/"provider-originals"/(event["task"]+".json")
    raw=wire.read_bytes()
    need(event["original_wire_preserved"] and
         h(raw)==event["raw_provider_sha256"],
         "WF0AL_OLD_PAID_MODEL_WIRE_SHA_NOT_VERIFIED")
    data=json.loads(raw)
    need(data.get("model")=="deepseek-flash"
         and type(data.get("choices")) is list
         and len(data["choices"])==1
         and data["choices"][0].get("finish_reason")=="stop",
         "WF0AL_PROVIDER_FINISH_MODEL_INVALID")
    content=data["choices"][0]["message"]["content"]
    receipt=None
    if event["task"]=="scifi_airlock_WF-author":
        need(h(raw)==REAL_SCIFI_ORIGINAL_RAW_WIRE_SHA
             and h(content)==REAL_SCIFI_ORIGINAL_MESSAGE_SHA
             and event.get("decoded_sha256") is None,
             "WF0AL_ONLY_ONE_REAL_UNDECODED_AUTHOR_WIRE_EXPECTED")
        result=recover_single_fullwidth_author_field_separator(content)
        need(result is not None,
             "WF0AL_ORIGINAL_FULLWIDTH_FIELD_SEPARATOR_NOT_VERIFIED")
        decoded,receipt=result
        need(receipt["original_prose_sha256"]==
             ORIGINAL_SOURCE_SHA["scifi_airlock"]["WF"] and
             receipt["single_external_separator_only"],
             "WF0AL_ORIGINAL_AUTHOR_PROSE_CHANGED_BY_RECOVERY")
    else:
        decoded=json.loads(content)
        need(event["decoded_sha256"]==h(json.dumps(
            decoded,ensure_ascii=False,separators=(",",":"))),
             "WF0AL_ORIGINAL_DECODED_MODEL_SHA_CHANGED")
    return decoded,receipt


def replay_four_original_authors():
    manifest=json.loads((PRIOR/"STATUS.json").read_text("utf8"))
    need(manifest["format"]=="wf.0aj.third-new-diverse-micro-two-paired.v1"
         and manifest["first_batch"]==list(BATCH)
         and manifest["actual_model_calls"]==4
         and manifest["same_model"]=="deepseek-flash"
         and manifest["same_author_max_tokens"]==1400
         and manifest["R2_reads"]==manifest["R2_writes"]==
            manifest["Canon_writes"]==0
         and manifest["Railway_deployments"]==0 and not manifest["main_modified"],
         "WF0AL_FROZEN_AUTHOR_EXPERIMENT_MANIFEST_INVALID")
    events={}
    for event in manifest["provider_calls"]:
        key=event["task"]
        need(key not in events and key.endswith(
            ("bare-author","WF-author"))
            and event["max_tokens"]==1400,
            "WF0AL_UNEXPECTED_PRIOR_JUDGE_OR_AUTHOR_RETRY")
        events[key]=event
    need(len(events)==4,
         "WF0AL_FOUR_ORIGINAL_AUTHORS_NOT_ACCOUNTED_FOR")
    cases={}
    for key in BATCH:
        item=SCENE_BY_ID[key]
        pair={}
        provenance={}
        for arm,task in (("bare","bare-author"),("WF","WF-author")):
            event=events[key+"_"+task]
            need(event["prompt_sha256"]==h(prompt(item,arm)),
                 "WF0AL_ORIGINAL_FROZEN_PROMPT_DRIFT")
            reply,format_receipt=read_original_provider(event)
            model=normalize(reply,("prose",) if arm=="bare" else ("prose","trace"))
            prose=model["prose"].strip()
            need(h(prose)==ORIGINAL_SOURCE_SHA[key][arm] and
                 80<=len(prose)<=1024,
                 "WF0AL_ORIGINAL_AUTHOR_PROSE_SHA_MISMATCH")
            # If initial 0.AJ stored an original .md, require identical.
            original_file=PRIOR/"author-originals"/(key+"-"+arm+".md")
            if original_file.exists():
                need(original_file.read_text("utf8")==prose,
                     "WF0AL_PUBLISHED_OLD_AUTHOR_PROSE_WAS_MODIFIED")
            pair[arm]={**model,"prose":prose}
            provenance[arm]={
                "source_sha256":h(prose),
                "chars":len(prose),
                "raw_provider_sha256":event["raw_provider_sha256"],
                "original_format_recovery":format_receipt,
            }
        check=check_source(item,pair)
        need(check["source_sha256"]==ORIGINAL_SOURCE_SHA[key]["WF"],
             "WF0AL_V96_WF_SOURCE_CHANGED")
        cases[key]={
            "item":item,"pair":pair,"source":provenance,"WF_source_checks":check,
            "length_ratio":round(max(len(pair[arm]["prose"])
                                        for arm in ("bare","WF"))/
                                 min(len(pair[arm]["prose"])
                                     for arm in ("bare","WF")),3),
        }
    return cases,manifest,events


class SourceOnlyTwoOrderRater:
    def __init__(self,api_key):
        self.task=None
        self.events=[]
        self.budget=FlashBudget(max_calls=MAX_NEW_CALLS,
                                max_reserved_output_tokens=MAX_NEW_RATER_TOKENS)
        self.client=DeepSeekFlashModel(
            api_key=api_key,budget=self.budget,timeout_seconds=110,
            on_response_wire=self.save_original_wire)

    def save_original_wire(self,raw):
        need(self.task is not None and type(raw) is bytes,
             "WF0AL_JUDGE_ORPHAN_ORIGINAL_WIRE")
        file=OUT/"new-rating-provider-wires"/(self.task+".json")
        file.parent.mkdir(parents=True,exist_ok=True)
        need(not file.exists(),"WF0AL_RATER_WIRE_OVERWRITE_FORBIDDEN")
        file.write_bytes(raw)
        event=self.events[-1]
        event["raw_provider_sha256"]=h(raw)
        event["original_wire_preserved"]=True

    def ask(self,item,task,role,question,max_tokens):
        need(self.task is None and task in ("blind-1","blind-2")
             and item["id"] in BATCH and role=="craft_analysis"
             and max_tokens==RATER_OUTPUT_TOKENS
             and len(self.events)<MAX_NEW_CALLS,
             "WF0AL_NO_WRITER_OR_UNREGISTERED_JUDGE_CALL_ALLOWED")
        name=item["id"]+"_"+task
        need(not any(x["task"]==name for x in self.events),
             "WF0AL_RATER_DUPLICATE_CALL_BLOCKED")
        self.task=name
        row={
            "task":name,"prompt_sha256":h(question),
            "max_tokens":max_tokens,"raw_provider_sha256":None,
            "original_wire_preserved":False,
        }
        self.events.append(row)
        try:
            result=self.client.ask_json(
                role=role,
                system=("你是中文原创文学作品的匿名评分读者。"
                        "禁止复制现成作品，只评价实际正文；分数不用于修改AI写作。"
                        "严格返回JSON对象。"),
                user=question,max_tokens=max_tokens,
            )
            row["decoded_sha256"]=h(json.dumps(
                result,ensure_ascii=False,separators=(",",":")))
            return result
        finally:
            self.task=None


def main():
    need(not OUT.exists(),"WF0AL_ONE_SHOT_SCORE_REPLAY_ALREADY_EXISTS")
    OUT.mkdir(parents=True)
    state={
        "format":"wf.0al.score-four-true-0aj-author-wires.v1",
        "status":"NOT_STARTED","original_paid_run":PRIOR_RUN,
        "original_author_provider_wires":4,
        "original_authors_replayed_without_model":4,
        "new_author_calls":0,"new_grade_call_cap":MAX_NEW_CALLS,
        "new_grade_calls":0,
        "R2_reads":0,"R2_writes":0,"Canon_writes":0,
        "Railway_deployments":0,"main_modified":False,
        "literary_improvement_not_proven":True,
        "rating_never_changes_or_reward_models":True,
        "independent_human_literary_review_done":False,
        "cases":{},"new_rating_provider_events":[],
    }
    rater=None
    try:
        cases,manifest,events=replay_four_original_authors()
        state["original_verified_wire_shas"]={
            name:e["raw_provider_sha256"] for name,e in events.items()}
        state["original_fullwidth_separation_preserved_unmodified"]=True
        # Archive all actual old provider envelopes (including the malformed
        # one) and verbatim authored prose, with no regenerated sentence.
        copytree(PRIOR/"provider-originals",
                 OUT/"original-four-provider-wires")
        for key,entry in cases.items():
            for arm in ("bare","WF"):
                p=OUT/"original-author-prose"/(key+"-"+arm+".md")
                p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(entry["pair"][arm]["prose"],encoding="utf8")
            status={
                "genre":entry["item"]["genre"],
                "source_evidence":entry["source"],
                "WF_source_checks":entry["WF_source_checks"],
                "length_ratio":entry["length_ratio"],
                "comparable_within_15pct":entry["length_ratio"]<=1.15,
                "both_in_200_to_350":all(
                    200<=entry["source"][arm]["chars"]<=350
                    for arm in ("bare","WF")),
                "scores_ready":False,
                "semantic_true_causality_independently_verified":False,
                "confirmed_false_green":None,
                "confirmed_false_red":None,
            }
            state["cases"][key]=status
        save(OUT/"PARTIAL.json",state)
        require_external_runtime()
        need(not any(os.getenv(x) for x in (
            "WRITERFORGE_R2_ACCOUNT_ID","WRITERFORGE_R2_ACCESS_KEY_ID",
            "DISCOVERY_API_KEY","OPENAI_API_KEY","OPENROUTER_API_KEY")),
            "WF0AL_BOOK_OR_EXTRA_MODEL_SOURCE_NOT_ALLOWED")
        key=os.getenv("DEEPSEEK_API_KEY","")
        need(len(key)>=16,"WF0AL_EXISTING_PROVIDER_KEY_UNAVAILABLE")
        rater=SourceOnlyTwoOrderRater(key)
        for k in BATCH:
            row=state["cases"][k]
            item=cases[k]["item"]
            pair=cases[k]["pair"]
            scores={}
            for order,task in zip(JUDGEMENTS,("blind-1","blind-2")):
                try:
                    scores[task]=judge_one(rater,item,pair,order,task)
                except Exception as error:
                    row["grade_failure_code"]=(
                        str(error) if re.fullmatch(r"WF[A-Z0-9_:\-]{3,170}",str(error))
                        else type(error).__name__+":NO_JUDGE_RETRY")
                    break
            if len(scores)==2:
                from experiments.wf_0ag_replay_three_real_micro_scores_only_20261025 import combine
                summary,delta=combine(scores["blind-1"],scores["blind-2"])
                row["ratings"]=summary
                row["WF_minus_bare"]=delta
                row["scores_ready"]=True
                max_swing=max(v["order_sensitivity"] for v in summary.values())
                row["comparison_confidence"]=(
                    "NOT_COMPARABLE_PROSE_LENGTH_OUT_OF_200_350"
                    if not row["both_in_200_to_350"] else
                    "NOT_COMPARABLE_LENGTH_MISMATCH"
                    if not row["comparable_within_15pct"] else
                    "LOW_CONFIDENCE_SCORE_ORDER"
                    if max_swing>8 else
                    "EXPLORATORY_SINGLE_MODEL_FAMILY_ONLY")
            save(OUT/"PARTIAL.json",state)
        state["status"]=(
            "FOUR_IMMUTABLE_AUTHORS_TWO_GENRES_BOTH_GRADES_RESTORED"
            if all(x["scores_ready"] for x in state["cases"].values())
            else "PARTIAL_ORIGINALS_AND_JUDGES_PRESERVED_NO_RETRY")
    except Exception as err:
        state["status"]="FROZEN_SOURCE_OR_SCORE_REVIEW_HOLD"
        message=str(err)
        state["failure_code"]=(
            message if re.fullmatch(r"WF[A-Z0-9_:\-]{3,170}",message)
            else type(err).__name__+":NO_MODEL_RETRY")
    finally:
        if rater is not None:
            state["new_grade_calls"]=rater.budget.calls_reserved
            state["new_rating_provider_events"]=rater.events
            state["new_rater_usage"]=rater.budget.public_receipt()
        save(OUT/"STATUS.json",state)
        print("WF0AL_SOURCE_SCORE_REPLAY "+json.dumps({
            "status":state["status"],"new_author_calls":0,
            "new_rating_calls":state["new_grade_calls"],
            "cases":{name:{
                "source":{arm:v["source_sha256"] for arm,v in
                          row["source_evidence"].items()},
                "delta":row.get("WF_minus_bare"),
                "grade_status":row.get("comparison_confidence"),
                "source_review":row["WF_source_checks"]["V96_causal_relation"],
            } for name,row in state["cases"].items()},
        },ensure_ascii=False),flush=True)
    if state["status"]!="FOUR_IMMUTABLE_AUTHORS_TWO_GENRES_BOTH_GRADES_RESTORED":
        raise RuntimeError("WF0AL_FROZEN_SOURCE_OR_JUDGE_PARTIAL")


if __name__=="__main__":
    main()
