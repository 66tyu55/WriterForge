"""0.AV B++: equal original t01..t03 DeepSeek prose, V98 sees signed older prose.

Historical observations:
- original frozen G and B: Actions 40323596997 (16 total paid).
- B+ source-only replan t04/t05: Actions 40328385610 (+6 paid).
- real B+ t04 writer plan ignored t01's already-written cut of branch signal;
  t04 literally cut the signal again. B+ average judge advantage over old B
  only +1.5 points, highly order-sensitive, no established quality growth.

One variable: existing V98's *author-visible* bounded earlier PROSE window.
No host plot summaries, no host author voice, no inference of actual cause.
Same frozen seven original DeepSeek wire replies / same task and model.
HARD global experiment cap: 16 + 6 + at most 4 = 26 calls, no judge calls.
This is a new UNACCEPTED candidate branch, not a replacement for B+.
"""
from __future__ import annotations
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
from experiments import wf_0av_review_only_prose_uplift_ab_once_20261026 as first
from experiments import wf_0av_new_waterworks_g_v98_real_literary_ab_once_20261026 as wf

ROOT=Path("wf_0av_recent_source_prose_window_Bplusplus_20261026")
FIRST_PLUS=Path("wf0av_first_Bplus_source")
FIRST_PLUS_SHA="8357516a97e2ced231c3a44a8c961a708ecbc3db44e82d7eba24bd9fce61a706"
T04_PRIOR_SHA="750d54a61268786eb0381040dbc833da880de3515546772f20683bef515b74fe"
T05_PRIOR_SHA="ee3fd3054c99b312d429e0c27551bb78e2fca59adbd473c64eb5647165df7449"
MAX_NEW_PAID=4
MAX_RESERVED=4400
PAID_ALREADY=22
RESERVED_ALREADY=28100
REGISTER={
 "format":"wf.0av.same-real-author-recent-prose-source-window.v1",
 "task":"Night Valve -- t04/t05 source-first writer continuation",
 "model":"deepseek-flash","same_original_literary_task":True,
 "same_frozen_actual_t01_t02_t03_sha":True,
 "Bplus_old_source_only_2_author_replans_not_reauthored":True,
 "Bplusplus_only_new_variable":"V98 reveals earlier signed prose t01/t02 to model in addition to t03",
 "V98_infers_no_additional_story_fact_or_goal":True,
 "new_author_plan_and_prose_calls_limit":4,
 "new_reservation_ceiling":MAX_RESERVED,
 "combined_hard_paid_ceiling":26,
 "combined_total_reservation_ceiling":44000,
 "no_extra_model_judge_to_stay_inside_original_budget":True,
 "literary_observation_priorities":[
    "previously cut branch signal re-cut as new action",
    "actor choices and actual irreversible consequences",
    "new uncertainty vs re-issued command",
    "physical signal, timing, and actor knowledge",
    "unforced dialogue tension and prose rhythm"],
 "no_canon_r2_main_railway_second_memory":True,
 "human_independent_grades_available":False,
}

def h(b):
    return sha256(b if type(b) is bytes else b.encode("utf8")).hexdigest()

def need(test,code):
    if not test:raise RuntimeError(code)

def save(filename,obj):
    filename.parent.mkdir(parents=True,exist_ok=True)
    filename.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,
                                  indent=2),encoding="utf8")

class FourOnly:
    def __init__(self,dry=False):
        self.calls=MAX_NEW_PAID if dry else 0
        self.reserved=0
    def reserve(self,count):
        need(self.calls<MAX_NEW_PAID and
             self.reserved+count<=MAX_RESERVED,
             "WF0AV_BPLUSPLUS_TOTAL_PRE_NETWORK_LITERARY_CAP")
        self.calls+=1
        self.reserved+=count

def old_bplus_source():
    old=json.loads((FIRST_PLUS/"STATUS.json").read_text("utf8"))
    prior=json.loads((FIRST_PLUS/"SOURCE_ONLY_LITERARY_COMPARISON.json").read_text("utf8"))
    prose=json.loads((FIRST_PLUS/"B"/"source-only-result.json").read_text("utf8"))
    need(old["status"]=="BOTH_BRANCHES_REVERSE_BLIND_GRADED"
         and old["new_paid_model_calls"]==6
         and old["combined_total_paid_calls"]==PAID_ALREADY
         and old["combined_completion_reservations"]==RESERVED_ALREADY
         and old["blind_quote_grounding_each_order"]==[True,True]
         and old["score_interpretation"]=="SAME_FAMILY_EXPLORATORY_NOT_HUMAN"
         and prior["old_B_full_sha256"]==first.OLD_B_SHA
         and prior["new_source_only_B_plus_sha256"]==FIRST_PLUS_SHA
         and len(prior["B_plus_prose_only_replans"])==2
         and prose["prose_sha256"]==FIRST_PLUS_SHA
         and len(prose["turns"])==5
         and prose["turns"][3]["sha256"]==T04_PRIOR_SHA
         and prose["turns"][4]["sha256"]==T05_PRIOR_SHA
         and h("\n\n".join(t["prose"] for t in prose["turns"]))==FIRST_PLUS_SHA,
         "WF0AV_ORIGINAL_BPLUS_REAL_WRITER_STATUS_OR_SHA_NOT_LOCKED")
    return prior,prose

def frozen_environment():
    # The original A/B artifact includes all 7 immutable same-model wires
    # and requests. Reuse its strict source checker, never ask to regenerate.
    first.OUTPUT=ROOT
    records,originals,old_B,source_manifest,old_comparison=first.frozen_source()
    older,old_Bplus=old_bplus_source()
    need([t["sha256"] for t in old_B["turns"][:3]]==
         [t["sha256"] for t in old_Bplus["turns"][:3]] and
         old_B["turns"][2]["sha256"]==first.B_T03_SHA,
         "WF0AV_BPLUSPLUS_OLDER_REAL_FIRST_THREE_TEXT_CHANGED")
    first.copy_provenance(originals)
    save(ROOT/"PREVIOUS_BPLUS_IMMUTABLE_CONTROL.json",{
        "source_run_id":40328385610,
        "old_B_sha256":first.OLD_B_SHA,
        "old_Bplus_sha256":FIRST_PLUS_SHA,
        "old_t04_sha256":T04_PRIOR_SHA,
        "old_t05_sha256":T05_PRIOR_SHA,
        "old_Bplus_original_model_wires_not_regenerated":True,
        "same_frozen_real_author_first_three":True,
        "new_source_window_only_variable_not_quality_claim":True,
    })
    return records,old_B,old_Bplus,source_manifest

def author(key,cap,records):
    wf.ROOT=ROOT
    return wf.WireWriter("B",key,cap,replay=records)

def dry():
    need(not ROOT.exists(),"WF0AV_BPLUSPLUS_NEVER_OVERWRITE_OLD_WRITER")
    ROOT.mkdir(parents=True)
    save(ROOT/"PREREGISTERED_0AV_NEXT_WINDOW.json",REGISTER)
    records,old_B,Bplus,manifest=frozen_environment()
    a=author("offline-no-network-key-valid-0123456789",FourOnly(dry=True),records)
    try:
        wf.run_arm("B",a)
    except Exception as e:
        reason=str(e)
        need("WF0AV_BPLUSPLUS_TOTAL_PRE_NETWORK_LITERARY_CAP" in reason
             and len(a.events)==8
             and all(not row["paid_call"] for row in a.events[:7])
             and a.events[6]["wire_sha256"]==
                 first.ORIGINAL_B_SEVEN_WIRE_SHAS[6],
             "WF0AV_BPLUSPLUS_SIGNED_PREFIX_FAILED_BEFORE_NEW_T04_PLAN:"
             +type(e).__name__+":"+reason[:180])
    else:
        raise RuntimeError("WF0AV_BPLUSPLUS_DRY_AUTHORED_NEW_PROSE_WITHOUT_MODEL")
    req=json.loads((ROOT/"B"/"exact-requests"/"08.json").read_text("utf8"))
    prompt=req["prompt"]
    # Previously the source-backed t01 signal cut was not visible at all.
    earlier=old_B["turns"][0]["prose"]
    exact="他扳了下去。面板上一排绿灯暗掉一格"
    need(exact in earlier and exact in prompt
         and '"next_turn":{"id":"t04"' in prompt
         and '"causal_parent":"t03"' in prompt
         and "SHA256" in prompt
         and "之前真实正文" not in prompt
         and "更早两段的真实正文来源" in prompt
         and old_B["turns"][2]["prose"][-160:] in prompt
         and req["prompt_sha256"]==h(prompt)
         and req["max_tokens"]==650,
         "WF0AV_BPLUSPLUS_NEW_T04_PROMPT_DID_NOT_SHOW_PRIOR_SIGNED_ACTION")
    save(ROOT/"SOURCE_WINDOW_PREFLIGHT.json",{
        "status":"ORIGINAL_SEVEN_DEEPSEEK_WIRES_ZERO_CALLS_T04_INCLUDES_T01_SOURCE",
        "t01_prior_literal_cut_is_visible_to_author":True,
        "original_t03_prose_sha256":first.B_T03_SHA,
        "t04_new_prompt_sha256":req["prompt_sha256"],
        "old_Bplus_unmodified":True,
        "model_calls":0,"Canon_writes":0,"R2_writes":0,
        "literary_growth_unproven":True})
    print("WF0AV_SOURCE_WINDOW_SIGNED_T01_T03_TO_REAL_T04_ZERO_PROVIDER_PASS",flush=True)

def main():
    need(not ROOT.exists(),"WF0AV_BPLUSPLUS_NEVER_OVERWRITE_OLD_WRITER")
    ROOT.mkdir(parents=True)
    save(ROOT/"PREREGISTERED_0AV_NEXT_WINDOW.json",REGISTER)
    cap=FourOnly()
    writer=None
    status={
        "format":"wf.0av.real-bplusplus-signed-prior-source-window.v1",
        "status":"NOT_STARTED","old_paid_calls":PAID_ALREADY,
        "new_paid_calls":0,"new_reserved_completion":0,
        "new_prose_sha256":None,
        "literary_improvement_proven":False,
        "provider_events":[],
        "R2_reads":0,"R2_writes":0,"Canon_writes":0,
        "main_modified":False,"Railway_deployments":0,
    }
    try:
        need(not any(os.getenv(k) for k in (
            "WRITERFORGE_R2_ACCOUNT_ID","WRITERFORGE_R2_ACCESS_KEY_ID",
            "OPENAI_API_KEY","DISCOVERY_API_KEY","OPENROUTER_API_KEY")),
            "WF0AV_BPLUSPLUS_FORBIDDEN_OTHER_VENDOR_OR_R2")
        key=os.getenv("DEEPSEEK_API_KEY","")
        need(len(key)>=16,"WF0AV_BPLUSPLUS_EXISTING_DEEPSEEK_KEY_ABSENT")
        records,old_B,Bplus,manifest=frozen_environment()
        writer=author(key,cap,records)
        new=wf.run_arm("B",writer)
        story=new["prose"]
        orig_Bplus="\n\n".join(t["prose"] for t in Bplus["turns"])
        need(len(new["turns"])==5 and
             [t["sha256"] for t in new["turns"][:3]]==
             [t["sha256"] for t in old_B["turns"][:3]] and
             len(writer.events)==11 and
             all(not e["paid_call"] for e in writer.events[:7]),
             "WF0AV_BPLUSPLUS_REAL_SOURCE_PREFIX_MUTATED")
        receipts=new["evidence"].get("g_writer_source_only_replans",[])
        review=[r for r in receipts
            if r.get("review_only_or_quiet_prose_writer_plan")]
        need(len(review)==2 and [r["beat_id"] for r in review]==["t04","t05"] and
             all(not r["source_parent_causal_relation_verified"] and
                 r["canon_or_factjournal_writes"]==0
                 for r in review),
             "WF0AV_BPLUSPLUS_REAL_WRITER_DID_NOT_REPLAN_REVIEW_SOURCE")
        # Fair provenance and length only. No new grading budget remains.
        ratio=len(story)/len(orig_Bplus)
        compare={
           "original_Bplus_source_run":40328385610,
           "original_Bplus_prose_sha256":FIRST_PLUS_SHA,
           "new_Bplusplus_prose_sha256":h(story),
           "old_Bplus_chars":len(orig_Bplus),
           "new_Bplusplus_chars":len(story),
           "length_ratio":ratio,"length_comparable":0.75<=ratio<=1.33,
           "same_original_t01_t02_t03_bytes":True,
           "new_source_window_literal_t01_cut_exposed":True,
           "new_replan_decisions_from_actual_model":new["evidence"].get(
               "g_writer_provisional_beat_choices",[]),
           "old_Bplus_final_original_prose_sha256s":[
               t["sha256"] for t in Bplus["turns"][3:]],
           "new_Bplusplus_final_original_prose_sha256s":[
               t["sha256"] for t in new["turns"][3:]],
           "prose_only_source_receipts":review,
           "new_true_model_calls":writer.budget.calls_reserved,
           "actual_model_usage":writer.budget.public_receipt(),
           "independent_literary_grade":None,
           "grade_not_paid_to_respect_cumulative_cost_ceiling":True,
           "no_literary_win_asserted":True,
        }
        save(ROOT/"SOURCE_WINDOW_ORIGINAL_LITERARY_COMPARISON.json",compare)
        txt="# WF 0.AV 原稿逐段来源窗口：同原作者 B+ vs B++\n\n"
        for title,turns in (("B+ 只看最近一段",Bplus["turns"]),
                           ("B++ t04/t05 同时看见签名的更早正文",new["turns"])):
            txt+="## "+title+"\n\n"
            for i,t in enumerate(turns,1):
                txt+=f"### t{i:02d} SHA256 {t['sha256']}\n\n"+t["prose"]+"\n\n"
        (ROOT/"READABLE_REAL_BPLUS_BPLUSPLUS.md").write_text(txt,encoding="utf8")
        status["status"]="REAL_BPLUS_BPLUSPLUS_SOURCE_WINDOW_WRITER_PROSE_COMPLETED"
        status["comparison"]=compare
        status["new_prose_sha256"]=h(story)
        print("WF0AV_REAL_SOURCE_WINDOW_LITERARY "+json.dumps({
            "old_Bplus_chars":len(orig_Bplus),"Bplusplus_chars":len(story),
            "old_Bplus_SHA":FIRST_PLUS_SHA,"Bplusplus_SHA":h(story),
            "original_Bplus_t04_t05":
                [t["prose"][:210] for t in Bplus["turns"][3:]],
            "new_Bplusplus_t04_t05":[t["prose"][:400] for t in new["turns"][3:]],
            "writer_beat_choices":compare["new_replan_decisions_from_actual_model"],
            "grade":None,"literary_improvement_proven":False,
        },ensure_ascii=False),flush=True)
    except Exception as e:
        msg=str(e)
        status["status"]="SOURCE_WINDOW_SAFE_PARTIAL_FAILURE_NO_RETRY"
        status["failure_code"]=msg if re.fullmatch(
            r"WF[A-Z0-9_:.\-]{3,180}",msg) else type(e).__name__+":NO_RETRY"
    finally:
        status["new_paid_calls"]=cap.calls
        status["new_reserved_completion"]=cap.reserved
        status["total_paid_calls"]=PAID_ALREADY+cap.calls
        status["combined_reserved_completion"]=RESERVED_ALREADY+cap.reserved
        status["provider_events"]=writer.public_events() if writer else []
        save(ROOT/"STATUS.json",status)
        print("WF0AV_SOURCE_WINDOW_STATUS "+json.dumps({
            "status":status["status"],
            "new_paid_calls":cap.calls,
            "combined_paid_calls":PAID_ALREADY+cap.calls,
            "new_SHA":status["new_prose_sha256"],
            "failure":status.get("failure_code"),
        },ensure_ascii=False),flush=True)
    if status["status"]=="SOURCE_WINDOW_SAFE_PARTIAL_FAILURE_NO_RETRY":
        raise RuntimeError("WF0AV_SOURCE_WINDOW_REAL_PARTIAL_WIRES_PRESERVED_NO_RETRY")

if __name__=="__main__":
    if "--preflight" in sys.argv:
        dry()
    else:
        main()
