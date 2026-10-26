"""WF 0.AV second real literary trial: original B vs prose-only V98 B+.

The previous completed A/B is immutable: Actions 40323596997, 16 paid
calls total. REAL B paragraphs t01/t02/t03 are source-locked and replayed
without network charge. Previous B t04/t05 frozen fallbacks are NEVER
rewritten, re-scored as a new original, or retconned into Canon.

B+ uses the SAME DeepSeek Flash and SAME chapter task, from the SAME t03
actual text. Only the existing opt-in G+V98 can now ask the author to
reconsider next steps from still-unverified source prose. Preserve raw
provider wires BEFORE decode and independent source/quality measures.
All new costs are explicitly reported (the arms are not equal-cost).
No user books, R2, Railway, main, 15-chapter training or second memory.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import sys
import re
from experiments import wf_0av_new_waterworks_g_v98_real_literary_ab_once_20261026 as wf

ORIGINAL_RUN=40323596997
ARCHIVE=Path("wf0av_completed_0av_source")
SOURCE=ARCHIVE/"wf_0av_new_waterworks_g_v98_real_literary_ab_20261026"
OUTPUT=Path("wf_0av_review_only_author_prose_uplift_trial_20261026")
OLD_G_SHA="3030cb436ac752d84dafe05cfeaa15767ef9b4ba02cab6ce290b21f3e8459bea"
OLD_B_SHA="b3a52d3ae0736e7003fa0651681e498888106ed3c1beba19101d4d6de53cd96d"
B_T03_SHA="3f22dd574a949a74bd5004f6fb54e33d1196ea3cb561e33dfe5dde1ebf334a0f"
ORIGINAL_B_SEVEN_WIRE_SHAS=(
 "9d6efe8e2375565cfbdc1a8ac6a30b5a6754fb6537c96835fd6fcd32f56d1a19",
 "f7b64df21080e7a196dc9e8babaebe94bb267a232ec1a9e2061c3d4598572ca4",
 "7b776a0277ae8721af6c689b87da7962d9012b24751de1b76454052dc8c62de3",
 "c5f74d6bd582f12ce55250a48c22cc457aeb3e31fe68107cc5acc054289ce719",
 "b719efa41a79372a7ec47eceef351d1ffe6ee3178cc89b7beaec189873be0dc3",
 "ddbb093fb6b1006d9d82169f6233378ecf68da667eea8eae6c6941a268335711",
 "6aaba5c012b43f01ff51a8c1fea312377f97b8f1ecbad4df102cec10e218718b",
)
WIRE_LOCATIONS=(
 "upstream-immutable-wire-copies/01-origin-run-40283464818.json",
 "upstream-immutable-wire-copies/02-origin-run-40283464818.json",
 "upstream-immutable-wire-copies/03-origin-run-40285930972.json",
 "upstream-immutable-wire-copies/08-origin-run-40294657373-B.json",
 "upstream-immutable-wire-copies/09-origin-run-40297313308-B.json",
 "upstream-immutable-wire-copies/11-origin-run-40321793262-B.json",
 "B/original-provider-wires/07-paid.json",
)
MAX_NEW_PAID_CALLS=6
MAX_NEW_RESERVED_OUTPUT_TOKENS=8000
OLD_TOTAL_PAID=16
OLD_TOTAL_RESERVED=20500
TASK={
 "format":"wf.0av.writer-source-only-real-prefix-literary-trial.v1",
 "old_b_writes":5,"new_b_plus_writes":5,
 "unchanged_original_B_first_three_paragraphs":True,
 "author_model":"deepseek-flash","source_G_mode":"continuity_guard",
 "writer_G_plus_V98_opt_in":True,
 "only_difference":"May replan t04/t05 from review-only signed PROSE (not verified effect)",
 "new_paid_calls_max":MAX_NEW_PAID_CALLS,
 "new_reserved_completion_max":MAX_NEW_RESERVED_OUTPUT_TOKENS,
 "previous_total_paid_calls":OLD_TOTAL_PAID,
 "total_calls_including_original_not_more_than":26,
 "old_total_completion_reservations":OLD_TOTAL_RESERVED,
 "total_completion_reservations_not_more_than":44000,
 "controls":"same initial DeepSeek, task, plan, seed, t01/t02/t03 bytes; t04/t05 author-owned",
 "pre_registered_dimensions":["new choice vs repetition","new consequence",
   "limited POV","actual communication mechanics","literary rhythm",
   "object/time continuity","quiet source allowed without KNOWN promotion"],
 "length_comparable_range":[0.75,1.33],
 "double_order_literary_grade_if_comparable":True,
 "single_model_family_grading_not_independent_human":True,
 "different_model_costs_explicit_confound":True,
 "no_canon_r2_railway_main_changes":True,
}

def h(v):
    return hashlib.sha256(v if isinstance(v,bytes) else v.encode("utf8")).hexdigest()

def need(ok,code):
    if not ok: raise RuntimeError(code)

def save(path,record):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(record,ensure_ascii=False,sort_keys=True,indent=2),
                    encoding="utf8")

def frozen_source():
    manifest=json.loads((SOURCE/"STATUS.json").read_text("utf8"))
    comparisons=json.loads((SOURCE/"SOURCE_AND_COST_COMPARISON.json").read_text("utf8"))
    need(manifest["status"]=="TWO_ARMS_TWO_BLIND_ORDER_REPORTS" and
         manifest["provider_calls"]==5 and
         manifest["total_paid_calls_including_original_red"]==OLD_TOTAL_PAID and
         manifest["total_reserved_tokens_including_original_red"]==OLD_TOTAL_RESERVED and
         manifest["A"]["sha256"]==OLD_G_SHA and
         manifest["B"]["sha256"]==OLD_B_SHA and
         comparisons["A_prose_sha256"]==OLD_G_SHA and
         comparisons["B_prose_sha256"]==OLD_B_SHA and
         comparisons["B_actual_source_anchored_replans"]==2 and
         [r["turn_id"] for r in comparisons["B_source_only_skips"]]==["t04","t05"] and
         all(r["reason"]=="PREVIOUS_TRACE_REVIEW_ONLY" for r in comparisons["B_source_only_skips"]),
         "WF0AV_PRIOR_REAL_B_LITERARY_EXPERIMENT_STATUS_DRIFT")
    prose=json.loads((SOURCE/"B"/"source-only-result.json").read_text("utf8"))
    need(prose["prose_sha256"]==OLD_B_SHA and len(prose["turns"])==5 and
         prose["turns"][2]["sha256"]==B_T03_SHA,
         "WF0AV_REAL_B_FIRST_THREE_PROSE_DRIFT")
    old_text="\n\n".join(t["prose"] for t in prose["turns"])
    need(h(old_text)==OLD_B_SHA,"WF0AV_PRIOR_B_AGGREGATE_PROSE_ASSEMBLY_CHANGED")
    requests=[]
    originals=[]
    for i,(sha,location) in enumerate(zip(
            ORIGINAL_B_SEVEN_WIRE_SHAS,WIRE_LOCATIONS),1):
        wire=(SOURCE/location).read_bytes()
        event=manifest["B_wire_events"][i-1]
        prior_request=json.loads((SOURCE/"B"/"exact-requests"/
                                 f"{i:02d}.json").read_text("utf8"))
        need(h(wire)==sha and event["wire_sha256"]==sha and
             event["model"]==wf.MODEL and
             event["reserved_output_tokens"]==prior_request["max_tokens"] and
             event["prompt_sha256"]==prior_request["prompt_sha256"]==
                h(prior_request["prompt"]) and
             event["saved_before_json_decode"] is True and
             event["paid_call"]==(i==7),
             "WF0AV_REAL_PREFIX_PROVIDER_WIRE_OR_REQUEST_CHANGED")
        provider=json.loads(wire)
        need(provider["model"]==wf.MODEL and
             len(provider["choices"])==1 and
             provider["choices"][0]["finish_reason"]=="stop",
             "WF0AV_REAL_PREFIX_PROVIDER_FINISH_CHANGED")
        response=json.loads(provider["choices"][0]["message"]["content"])
        raw=json.dumps(response,ensure_ascii=False,separators=(",",":"))
        originals.append(wire)
        requests.append(dict(event,raw_response=raw))
        if i in (3,5,7):
            expected={3:prose["turns"][0]["sha256"],
                      5:prose["turns"][1]["sha256"],
                      7:prose["turns"][2]["sha256"]}[i]
            need(type(response.get("prose")) is str and
                 h(response["prose"])==expected,
                 "WF0AV_REAL_T01_T02_T03_PROSE_TEXT_NOT_IMMUTABLE")
    return requests,originals,prose,manifest,comparisons

class TrialCap:
    def __init__(self,exhaust=False):
        self.calls=MAX_NEW_PAID_CALLS if exhaust else 0
        self.reserved=0
    def reserve(self,amount):
        need(self.calls<MAX_NEW_PAID_CALLS and
             self.reserved+amount<=MAX_NEW_RESERVED_OUTPUT_TOKENS,
             "WF0AV_NEW_SOURCE_ONLY_PAID_CAP_PRE_NETWORK")
        self.calls+=1
        self.reserved+=amount

def copy_provenance(originals):
    for i,raw in enumerate(originals,1):
        p=OUTPUT/"prior-immutable-real-provider-copies"/f"B-{i:02d}.json"
        need(not p.exists(),"WF0AV_PRIOR_WIRE_COPY_ALREADY_EXISTS")
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(raw)
    save(OUTPUT/"ORIGINAL_PREFIX_SHA_LOCK.json",{
        "source_run_id":ORIGINAL_RUN,
        "seven_original_model_response_wire_sha256s":list(ORIGINAL_B_SEVEN_WIRE_SHAS),
        "seven_genuine_author_requests_replayed_without_cost":True,
        "original_B_first_three_prose_sha256":[
            "ba054d739aade438044d4c0a51cb03e31474e0cfc5dc9bc76976376c5a4109b3",
            "a46f07ab64f0a6e9dc1d0d1b344ee5a06be8a74daca39725ed999c40499b9403",
            B_T03_SHA],
        "R2_reads":0,"R2_writes":0,"Canon_writes":0,
    })

def setup_author(model_key,cap,records):
    wf.ROOT=OUTPUT
    author=wf.WireWriter("B",model_key,cap,replay=records)
    return author

def no_model_preflight():
    need(not OUTPUT.exists(),"WF0AV_TRIAL_RESULT_MUST_NOT_BE_OVERWRITTEN")
    OUTPUT.mkdir(parents=True)
    save(OUTPUT/"PREREGISTERED_TRIAL.json",TASK)
    records,originals,prior,_,_=frozen_source()
    copy_provenance(originals)
    author=setup_author("offline-no-network-key-valid-0123456789",
                        TrialCap(exhaust=True),records)
    try:
        wf.run_arm("B",author)
    except Exception as ex:
        msg=str(ex)
        need("WF0AV_NEW_SOURCE_ONLY_PAID_CAP_PRE_NETWORK" in msg and
             len(author.events)==8 and
             all(not e["paid_call"] for e in author.events[:7]) and
             author.events[6]["wire_sha256"]==ORIGINAL_B_SEVEN_WIRE_SHAS[6],
             "WF0AV_AUTHENTIC_B_SOURCE_DID_NOT_REACH_NEW_REPLAN:"
             +type(ex).__name__+":"+msg[:180])
    else:
        raise RuntimeError("WF0AV_FAKE_B_SOURCE_COMPLETED_WITH_ZERO_PROVIDER")
    req=json.loads((OUTPUT/"B"/"exact-requests"/"08.json").read_text("utf8"))
    prompt=req["prompt"]
    need(req["max_tokens"]==650 and
         '"next_turn":{"id":"t04"' in prompt and
         '"causal_parent":"t03"' in prompt and
         "上一段正文已保存" in prompt and
         "仅供复核" in prompt and
         "不代表" in prompt and
         prior["turns"][2]["prose"][-160:] in prompt and
         req["prompt_sha256"]==h(prompt),
         "WF0AV_NEW_T04_PROSE_ONLY_AUTHOR_PROMPT_NOT_SOURCE_FIRST")
    save(OUTPUT/"OFFLINE_AUTHOR_NEXT_CHOICE_READY.json",{
        "status":"REAL_B_T01_TO_T03_BYTE_EXACT_REPLAY_T04_REPLAN_READY",
        "same_original_model":True,
        "saved_real_source_prose_sha256":B_T03_SHA,
        "original_t04_t05_prose_unchanged":True,
        "new_t04_author_prompt_sha256":req["prompt_sha256"],
        "new_paid_calls":0,
        "no_repaired_old_model_response_or_forced_rewrite":True,
        "literal_prose_source_only":True,
        "causality_not_promoted":True,
    })
    print("WF0AV_NEW_B_SOURCE_ONLY_TRUE_PROVIDER_PREFIX_ZERO_PAID_GREEN",flush=True)

def main():
    need(not OUTPUT.exists(),"WF0AV_TRIAL_RESULT_MUST_NOT_BE_OVERWRITTEN")
    OUTPUT.mkdir(parents=True)
    save(OUTPUT/"PREREGISTERED_TRIAL.json",TASK)
    cap=TrialCap()
    author=None
    status={
        "format":"wf.0av.source-only-review-prose-new-author-ab.v1",
        "status":"SOURCE_UNVERIFIED_NOT_BILLED",
        "prior_completed_real_run_id":ORIGINAL_RUN,
        "new_paid_model_calls":0,"prior_paid_calls":OLD_TOTAL_PAID,
        "new_completion_tokens_reserved":0,
        "literary_improvement_proven":False,
        "author_has_not_accepted":True,
        "R2_reads":0,"R2_writes":0,"Canon_writes":0,
        "main_modified":False,"Railway_deployments":0,
        "provider_events":[],
    }
    try:
        need(not any(os.getenv(k) for k in (
            "WRITERFORGE_R2_ACCOUNT_ID","WRITERFORGE_R2_ACCESS_KEY_ID",
            "DISCOVERY_API_KEY","OPENAI_API_KEY","OPENROUTER_API_KEY")),
            "WF0AV_OTHER_MODEL_OR_R2_SOURCE_FORBIDDEN")
        key=os.getenv("DEEPSEEK_API_KEY","")
        need(len(key)>=16,"WF0AV_PREVIOUS_DEEPSEEK_WRITER_KEY_UNAVAILABLE")
        records,originals,prior,_,old_comparisons=frozen_source()
        copy_provenance(originals)
        author=setup_author(key,cap,records)
        result=wf.run_arm("B",author)
        new_story=result["prose"]
        old_story="\n\n".join(t["prose"] for t in prior["turns"])
        new_turns=result["turns"]
        need(len(new_turns)==5 and
             [t["sha256"] for t in new_turns[:3]]==
                [t["sha256"] for t in prior["turns"][:3]] and
             len(author.events)>=11 and all(not e["paid_call"] for e in author.events[:7]),
             "WF0AV_ORIGINAL_WRITER_PREFIX_REVISED_OR_INCOMPLETE")
        receipt=result["evidence"]
        replans=receipt.get("g_writer_source_only_replans",[])
        source_based=[r for r in replans
            if r.get("review_only_or_quiet_prose_writer_plan") is True]
        need(any(r["beat_id"]=="t04" for r in source_based) and
             all(r["source_parent_causal_relation_verified"] is False and
                 r["canon_or_factjournal_writes"]==0 and
                 r["source_basis_is_observed_effect"] is False
                 for r in source_based),
             "WF0AV_REAL_WRITER_T04_PROSE_ONLY_PLAN_NOT_APPLIED_SAFELY")
        ratio=len(new_story)/len(old_story)
        comparison={
            "old_B_full_sha256":OLD_B_SHA,
            "new_source_only_B_plus_sha256":h(new_story),
            "same_first_three_paragraph_sha256s":[t["sha256"] for t in new_turns[:3]],
            "old_B_chars":len(old_story),"B_plus_chars":len(new_story),
            "B_plus_over_B_chars":ratio,
            "length_comparable":0.75<=ratio<=1.33,
            "old_G_frozen_prose_sha256":OLD_G_SHA,
            "B_plus_turn_chars":[t["chars"] for t in new_turns],
            "old_B_turn_chars":[t["chars"] for t in prior["turns"]],
            "B_plus_author_replan_receipts":replans,
            "B_plus_prose_only_replans":source_based,
            "B_plus_source_replan_skips":receipt.get("g_writer_review_only_replan_skips",[]),
            "previous_B_source_replans":2,
            "previous_B_source_only_skips":["t04","t05"],
            "B_plus_incremental_provider_calls":author.budget.calls_reserved,
            "B_plus_incremental_usage":author.budget.public_receipt(),
            "different_compute_budget_is_explicit_confound":True,
            "no_canon_or_training_progress_claimed":True,
        }
        save(OUTPUT/"SOURCE_ONLY_LITERARY_COMPARISON.json",comparison)
        prose_markdown="# WF 0.AV：同一 DeepSeek 前三段冻结，后两段新规划对照\n\n"
        for name,turns in (("旧 B｜t04/t05 冻结候选",prior["turns"]),
                           ("B+｜t04/t05 由签名正文自主重规划",new_turns)):
            prose_markdown+="## "+name+"\n\n"
            for i,t in enumerate(turns,1):
                prose_markdown+=f"### 第{i}段 SHA {t['sha256']}\n\n"+t["prose"]+"\n\n"
        (OUTPUT/"READABLE_B_vs_B_PLUS_REAL_AUTHOR.md").write_text(
            prose_markdown,encoding="utf8")
        status["status"]="TWO_REAL_WRITER_CONTINUATIONS_SAVED"
        status["comparison"]=comparison
        if comparison["length_comparable"]:
            try:
                # Old finished B is baseline X, new opt-in B+ is Y, then reverse.
                blind=wf.score_twice(old_story,new_story,key,cap)
                validation=[]
                for i,x in enumerate(blind["orders"]):
                    scores=x["scores"]
                    texts=(old_story,new_story) if i==0 else (new_story,old_story)
                    quotes_valid=all(type(scores[z].get("quote")) is str and
                        scores[z]["quote"] in txt for z,txt in zip(("X","Y"),texts))
                    validation.append(quotes_valid)
                status["judge"]=blind
                status["blind_quote_grounding_each_order"]=validation
                status["score_interpretation"]=(
                    "NOT_A_VALID_SOURCE_GROUNDED_GRADE" if not all(validation)
                    else "SAME_FAMILY_EXPLORATORY_NOT_HUMAN")
                status["status"]="BOTH_BRANCHES_REVERSE_BLIND_GRADED"
            except Exception as err:
                status["judge_error"]=type(err).__name__+":"+(str(err)[:130]
                    if re.fullmatch(r"WF[A-Z0-9_:.\-]{3,130}",str(err)) else
                    "NO_PAID_RETRY")
                status["status"]="BOTH_BRANCHES_SCORES_INCOMPLETE_NO_RETRY"
        else:
            status["judge_skipped"]="NOT_COMPARABLE_LENGTH"
        print("WF0AV_REVIEW_ONLY_AB "+json.dumps({
            "old_B_chars":len(old_story),"B_plus_chars":len(new_story),
            "old_B_sha256":OLD_B_SHA,"B_plus_sha256":h(new_story),
            "author_prose_only_replans":len(source_based),
            "old_B_skipped_replans":2,
            "B_plus_turns":[{"id":i+1,"sha256":v["sha256"],
                             "chars":v["chars"],"first_170":v["prose"][:170]}
                            for i,v in enumerate(new_turns)],
            "judge":status.get("judge"),"grade_validity":status.get("score_interpretation"),
        },ensure_ascii=False),flush=True)
    except Exception as ex:
        status["status"]="SOURCE_FIRST_SAFE_FAILURE_NO_RETRIES"
        err=str(ex)
        status["failure_code"]=err if re.fullmatch(
            r"WF[A-Z0-9_:.\-]{3,180}",err) else type(ex).__name__+":NO_RETRY"
    finally:
        status["new_paid_model_calls"]=cap.calls
        status["new_completion_tokens_reserved"]=cap.reserved
        status["combined_total_paid_calls"]=OLD_TOTAL_PAID+cap.calls
        status["combined_completion_reservations"]=OLD_TOTAL_RESERVED+cap.reserved
        status["provider_events"]=author.public_events() if author else []
        save(OUTPUT/"STATUS.json",status)
        print("WF0AV_REVIEW_ONLY_STATUS "+json.dumps({
            "status":status["status"],"new_calls":cap.calls,
            "new_reserved_completion":cap.reserved,
            "combined_calls":status["combined_total_paid_calls"],
            "B_plus_sha":status.get("comparison",{}).get("new_source_only_B_plus_sha256"),
            "failure_code":status.get("failure_code"),
            "literary_improvement_proven":False,
        },ensure_ascii=False),flush=True)
    if status["status"]=="SOURCE_FIRST_SAFE_FAILURE_NO_RETRIES":
        raise RuntimeError("WF0AV_REAL_SOURCE_FIRST_FAILED_IMMUTABLE_WIRES_SAVED")

if __name__=="__main__":
    if "--preflight" in sys.argv:
        no_model_preflight()
    else:
        main()
