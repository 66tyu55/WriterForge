"""0.AV B++ LAST writer prose from exact ten original DeepSeek wires.

Actual historic paid status: 16 original A/B + 6 B+ + 3 B++ = 25 calls.
The newest B++ t05 plan (wire10) was wrongly rejected by V98 for citing
the earlier *signed* t03 prose. It is now valid SOURCE-only, never a
t04 effect/cause. No model may re-plan t05 or rewrite B++ t04: ask ONLY
for the previously never-generated original author's t05 prose (wire11).

No retry, no re-grade, no R2, main, Railway, Canon, memory duplication.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys

from experiments import wf_0av_prior_prose_window_last_four_calls_once_20261026 as bp
from experiments import wf_0av_review_only_prose_uplift_ab_once_20261026 as first
from experiments import wf_0av_new_waterworks_g_v98_real_literary_ab_once_20261026 as wf

SOURCE=Path("wf0av_failed_Bplusplus_original_wire_source")
ROOT=Path("wf_0av_Bplusplus_original_t05_only_resume_20261026")
ORIGINAL_BPLUSPLUS_FAILED_RUN=40339756228
PRIOR_PAID_CALLS=25
PRIOR_RESERVED_COMPLETION=30850
MAX_NEW_PAID=1
MAX_NEW_RESERVED=1450
T04_PROSE_SHA="7f636d503ab6b6c9d47dcc980b3305329282b3e7d62375d582cfe9618058eda2"
ORIGINAL_WIRES={
 8:("852bbb3e70b7a7bf8126dd0eeecec1f1ee4d99474c79678b55cb88cdb52ffeb3",
    "c27c8a286baab65e804e12b576d6fdc4b1958516cfd45f47f31bc3cdd39ff7ae",650),
 9:("b2577db25adf76ce54487af2973e1babb5d40c062a0723f3aa716cd1931896e8",
    "0460962850a3da20acdb26e427dbf1840c9631ad74a42f831ac984f7882725d0",1450),
 10:("7de3f1bb829b90ab8bd67aacbdbd00b2f1faa073305f88ce201f1b15bce51362",
     "c1fa71b9902555879008ef3b862eb14b9890389a3bc46b5ed6c9e69107da6671",650),
}
REGISTRATION={
 "format":"wf.0av.Bplusplus-recover-original-ten-wires-final-t05-only.v1",
 "failed_real_Bplusplus_provider_run_id":ORIGINAL_BPLUSPLUS_FAILED_RUN,
 "original_A_B_run_id":40323596997,
 "original_Bplus_run_id":40328385610,
 "one_change":"V98 source-locates old writer's t03 quote, allowing its original t05 plan",
 "no_new_t05_planning_allowed":True,
 "frozen_actual_first_four_turn_prose":True,
 "same_writer_model":wf.MODEL,
 "new_paid_calls_ceiling":MAX_NEW_PAID,
 "new_reserved_completion_ceiling":MAX_NEW_RESERVED,
 "combined_paid_calls_ceiling":26,
 "combined_completion_reservation_ceiling":44000,
 "all_original_provider_wires_kept":True,
 "no_blind_grade_cost_remaining":True,
 "never_automatically_claim_literary_improvement":True,
 "require_unchanged_original_first_three_B_and_Bplus":True,
 "require_unchanged_original_t04_Bplusplus":True,
 "R2_or_Canon_or_Railway_or_main_writes":False,
}

def h(x):
    return hashlib.sha256(x if type(x) is bytes else x.encode("utf8")).hexdigest()

def need(test,code):
    if not test: raise RuntimeError(code)

def save(p,doc):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2),encoding="utf8")

class LastOne:
    """One more previously ungenerated original DeepSeek prose, nothing else."""
    def __init__(self,exhausted=False):
        self.calls=MAX_NEW_PAID if exhausted else 0
        self.reserved=0
    def reserve(self,amount):
        need(self.calls<MAX_NEW_PAID and amount==MAX_NEW_RESERVED
             and self.reserved+amount<=MAX_NEW_RESERVED,
             "WF0AV_BPLUSPLUS_FINAL_ONE_ONLY_BEFORE_PROVIDER")
        self.calls+=1
        self.reserved+=amount

def locked_previous_three():
    """Source verify original B++ live-failure wire bytes BEFORE JSON decoding."""
    failed=json.loads((SOURCE/"STATUS.json").read_text("utf8"))
    need(failed.get("format")=="wf.0av.real-bplusplus-signed-prior-source-window.v1"
         and failed.get("status")=="SOURCE_WINDOW_SAFE_PARTIAL_FAILURE_NO_RETRY"
         and failed.get("old_paid_calls")==22
         and failed.get("new_paid_calls")==3
         and failed.get("total_paid_calls")==PRIOR_PAID_CALLS
         and failed.get("new_reserved_completion")==2750
         and failed.get("combined_reserved_completion")==PRIOR_RESERVED_COMPLETION
         and failed.get("failure_code")==
             "WF96_SCENE_TURN_REJECTED_WF98_REPLAN_NOT_ANCHORED_TO_ACTUAL_EFFECT"
         and failed.get("literary_improvement_proven") is False
         and failed.get("R2_reads")==failed.get("R2_writes")==failed.get("Canon_writes")==0
         and len(failed.get("provider_events",[]))==10,
         "WF0AV_BPLUSPLUS_PRIOR_ACTUAL_FAILED_RUN_IDENTITY_DRIFT")
    events=failed["provider_events"]
    records=[]
    for i,(wire_sha,prompt_sha,max_out) in ORIGINAL_WIRES.items():
        wire=(SOURCE/"B"/"original-provider-wires"/f"{i:02d}-paid.json").read_bytes()
        request=json.loads((SOURCE/"B"/"exact-requests"/f"{i:02d}.json").read_text("utf8"))
        row=events[i-1]
        need(h(wire)==wire_sha==row.get("wire_sha256")
             and prompt_sha==row.get("prompt_sha256")==request["prompt_sha256"]
             and h(request["prompt"])==prompt_sha
             and request["max_tokens"]==row.get("reserved_output_tokens")==max_out
             and request["system"]==wf.WRITER_SYSTEM
             and row.get("model")==request.get("model")==wf.MODEL
             and row.get("paid_call") is True
             and row.get("saved_before_json_decode") is True,
             "WF0AV_BPLUSPLUS_OLD_PROVIDER_WIRE_PROMPT_OR_COST_DRIFT")
        provider=json.loads(wire)
        need(provider.get("model")==wf.MODEL and
             len(provider.get("choices",[]))==1 and
             provider["choices"][0]["finish_reason"]=="stop",
             "WF0AV_BPLUSPLUS_OLD_MODEL_WIRE_PROVIDER_FINISH_INVALID")
        doc=json.loads(provider["choices"][0]["message"]["content"])
        decoded=json.dumps(doc,ensure_ascii=False,separators=(",",":"))
        need(h(decoded)==row["returned_json_sha256"] and
             (type(doc.get("prose")) is str and type(doc.get("trace")) is dict
              if i==9 else type(doc.get("next_turn")) is dict),
             "WF0AV_BPLUSPLUS_OLD_MODEL_CONTENT_CHANGED")
        target=ROOT/"immutable-prior-bplusplus-paid-wires"/f"{i:02d}-paid.json"
        need(not target.exists(),"WF0AV_BPLUSPLUS_PREVIOUS_WIRE_OVERWRITE")
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(wire)
        save(ROOT/"immutable-prior-bplusplus-requests"/f"{i:02d}.json",request)
        records.append(dict(row,raw_response=decoded,source_arm="B",
                            raw_bytes_owned_by=str(target.relative_to(ROOT))))
    need(h(json.loads(json.loads(
         (SOURCE/"B"/"original-provider-wires"/"09-paid.json").read_text("utf8")
         )["choices"][0]["message"]["content"])["prose"])==T04_PROSE_SHA,
         "WF0AV_BPLUSPLUS_T04_LITERAL_AUTHOR_PROSE_CHANGED")
    result10=json.loads(json.loads(
        (SOURCE/"B"/"original-provider-wires"/"10-paid.json").read_text("utf8")
        )["choices"][0]["message"]["content"])
    need(result10["next_turn"]["id"]=="t05"
         and result10["next_turn"]["causal_parent"]=="t04"
         and result10["next_turn"]["actor"]=="许照"
         and result10["basis_effect_quote"]=="那两下短磕之后，再没有声音了。"
         and result10["pressure_quote"]=="倒计时跳到二十四周分。",
         "WF0AV_BPLUSPLUS_ORIGINAL_WRITER_T05_PLAN_NOT_EXACT")
    save(ROOT/"IMMMUTABLE_ORIGINAL_3_NEW_DEEPSEEK_WIRES.json",{
        "historical_run_id":ORIGINAL_BPLUSPLUS_FAILED_RUN,
        "previously_paid_calls":3,
        "new_model_calls_to_replay_these":0,
        "previous_exact_wire_sha256s":{str(i):v[0] for i,v in ORIGINAL_WIRES.items()},
        "t04_original_prose_sha256":T04_PROSE_SHA,
        "t05_original_model_choice_sha256":h(records[-1]["raw_response"]),
        "failed_only_after_t05_model_response_already_saved":True,
        "V98_fix_preserves_original_writer_t05_plan":True,
    })
    return records,result10

def restored_environment():
    bp.ROOT=ROOT
    first.OUTPUT=ROOT
    wf.ROOT=ROOT
    records7,old_B,old_Bplus,_=bp.frozen_environment()
    old3,original_t05_plan=locked_previous_three()
    need(len(records7)==7 and
         [r["wire_sha256"] for r in records7]==list(first.ORIGINAL_B_SEVEN_WIRE_SHAS)
         and len(old3)==3,
         "WF0AV_BPLUSPLUS_ORIGINAL_TEN_PROVENANCE_INCOMPLETE")
    return tuple(records7)+tuple(old3),old_B,old_Bplus,original_t05_plan

def verify_writer_prefix(writer):
    need(len(writer.events)==11
         and all(e["paid_call"] is False for e in writer.events[:10])
         and [e["wire_sha256"] for e in writer.events[7:10]]==
            [v[0] for v in ORIGINAL_WIRES.values()]
         and writer.events[10]["paid_call"] is True,
         "WF0AV_BPLUSPLUS_UNCHANGED_TEN_WRITER_RESPONSES_NOT_REPLAYED")
    prompt=json.loads((ROOT/"B"/"exact-requests"/"11.json").read_text("utf8"))
    original_t05=json.loads((ROOT/"immutable-prior-bplusplus-requests"/"10.json").read_text("utf8"))
    need(prompt["max_tokens"]==MAX_NEW_RESERVED
         and prompt["model"]==wf.MODEL
         and prompt["prompt_sha256"]==h(prompt["prompt"])
         and original_t05["prompt_sha256"]==ORIGINAL_WIRES[10][1]
         and "许照在阀前辨认手轮的实际转向与阀位" in prompt["prompt"]
         and "他把频道旋钮拧到备用位" in prompt["prompt"],
         "WF0AV_BPLUSPLUS_T05_WRITER_NOT_GIVEN_ORIGINAL_PLAN_AND_T04")
    return prompt

def dry():
    need(not ROOT.exists(),"WF0AV_BPLUSPLUS_FINAL_NOT_OVERWRITE")
    ROOT.mkdir(parents=True)
    save(ROOT/"PREREGISTERED_FINAL_ONE.json",REGISTRATION)
    records,old_B,Bplus,plan=restored_environment()
    cap=LastOne(exhausted=True)
    writer=bp.author("offline-no-network-key-valid-0123456789",cap,records)
    try:
        wf.run_arm("B",writer)
    except Exception as err:
        need("WF0AV_BPLUSPLUS_FINAL_ONE_ONLY_BEFORE_PROVIDER" in str(err),
             "WF0AV_BPLUSPLUS_FINAL_TEN_SOURCE_REPLAY_FAILED_OTHER_REASON:"
             +type(err).__name__+":"+str(err)[:150])
    else:
        raise RuntimeError("WF0AV_BPLUSPLUS_NO_REAL_MODEL_T05_SHOULD_NOT_COMPLETE")
    req=verify_writer_prefix(writer)
    save(ROOT/"SOURCE_LOCKED_T05_ONLY_ZERO_PAID_PREFLIGHT.json",{
        "format":"wf.0av.bplusplus-original-t05-ready.v1",
        "status":"TEN_AUTHENTIC_WIRES_REPLAYED_ONE_NEW_T05_PROSE_PROMPT_READY",
        "new_paid_calls":0,
        "original_25_historical_model_calls_not_recharged":True,
        "new_t05_prompt_sha256":req["prompt_sha256"],
        "original_t05_plan_sha256":h(json.dumps(plan,ensure_ascii=False,separators=(",",":"))),
        "original_Bplusplus_t04_sha256":T04_PROSE_SHA,
        "source_only_not_literary_quality_approval":True,
        "Canon_writes":0,"R2_writes":0,
    })
    print("WF0AV_BPLUSPLUS_T05_TEN_ORIGINAL_WIRES_ZERO_PAID_GREEN",flush=True)

def main():
    need(not ROOT.exists(),"WF0AV_BPLUSPLUS_FINAL_NOT_OVERWRITE")
    ROOT.mkdir(parents=True)
    save(ROOT/"PREREGISTERED_FINAL_ONE.json",REGISTRATION)
    cap=LastOne()
    writer=None
    status={
        "format":"wf.0av.bplusplus-author-original-final-t05-once.v1",
        "status":"NOT_STARTED","original_paid_calls":PRIOR_PAID_CALLS,
        "last_new_paid_calls":0,"last_new_reserved_completion":0,
        "all_four_new_Bplusplus_calls_total":None,
        "literary_improvement_proven":False,
        "R2_reads":0,"R2_writes":0,"Canon_writes":0,
        "main_modified":False,"Railway_deployments":0,
    }
    try:
        need(not any(os.getenv(x) for x in (
            "WRITERFORGE_R2_ACCOUNT_ID","WRITERFORGE_R2_ACCESS_KEY_ID",
            "OPENAI_API_KEY","DISCOVERY_API_KEY","OPENROUTER_API_KEY")),
            "WF0AV_BPLUSPLUS_FINAL_FORBIDDEN_NONDEEPSEEK_OR_R2")
        key=os.getenv("DEEPSEEK_API_KEY","")
        need(len(key)>=16,"WF0AV_BPLUSPLUS_FINAL_DEEPSEEK_SECRET_ABSENT")
        records,old_B,Bplus,original_plan=restored_environment()
        writer=bp.author(key,cap,records)
        new=wf.run_arm("B",writer)
        verify_writer_prefix(writer)
        need(len(new["turns"])==5
             and [t["sha256"] for t in new["turns"][:3]]==
                 [t["sha256"] for t in old_B["turns"][:3]]
             and new["turns"][3]["sha256"]==T04_PROSE_SHA
             and writer.events[-1]["paid_call"] is True
             and writer.events[-1]["saved_before_json_decode"] is True
             and cap.calls==MAX_NEW_PAID and cap.reserved==MAX_NEW_RESERVED,
             "WF0AV_BPLUSPLUS_REAL_WRITER_FIVE_PROSE_OR_SOURCE_DRIFT")
        choices=new["evidence"].get("g_writer_provisional_beat_choices",[])
        need(len(choices)>=2 and choices[-1]["id"]=="t05"
             and choices[-1]["goal"]==original_plan["next_turn"]["goal"]
             and choices[-1]["actor"]==original_plan["next_turn"]["actor"],
             "WF0AV_BPLUSPLUS_TRUE_AUTHOR_T05_PLAN_REPLACED")
        receipts=new["evidence"].get("g_writer_source_only_replans",[])
        last_two,review=bp.later_author_replan_receipts(receipts)
        need(last_two[1]["grounded_prior_beat_id"]=="t03" and
             last_two[1]["source_parent_beat_id"]=="t04" and
             last_two[1]["source_basis_from_older_signed_prose"] is True
             and last_two[1]["source_basis_kind"]=="EARLIER_SIGNED_PROSE_AUTHOR_ONLY",
             "WF0AV_BPLUSPLUS_T05_EARLIER_SIGNED_SOURCE_NOT_RECOVERED")
        previous="\n\n".join(t["prose"] for t in Bplus["turns"])
        txt=new["prose"]
        compare={
            "old_Bplus_source_run":40328385610,
            "failed_first_Bplusplus_run":ORIGINAL_BPLUSPLUS_FAILED_RUN,
            "last_successful_resume_run_this_workflow":True,
            "old_Bplus_sha256":bp.FIRST_PLUS_SHA,
            "new_Bplusplus_sha256":h(txt),
            "same_t01_t02_t03_author_originals":True,
            "unchanged_t04_live_DeepSeek_prose_sha256":T04_PROSE_SHA,
            "new_t05_actual_original_writer_prose_sha256":new["turns"][4]["sha256"],
            "old_Bplus_chars":len(previous),"new_Bplusplus_chars":len(txt),
            "length_ratio":len(txt)/len(previous),
            "length_comparable":.75<=len(txt)/len(previous)<=1.33,
            "writer_replans_t04_t05_original":last_two,
            "unverified_earlier_t03_basis_not_t04_effect":True,
            "writer_model_total_last_new_calls":writer.budget.calls_reserved,
            "no_extra_literary_judge":True,
            "literary_quality_from_readers_NOT_MEASURED":True,
            "human_literary_grade":None,
            "not_canon_or_accepted":True,
            "no_literary_win_asserted":True,
        }
        save(ROOT/"REAL_BPLUS_BPLUSPLUS_SOURCE_ONLY_COMPARISON.json",compare)
        manuscript="# WriterForge 0.AV｜B+ / B++ 不同原作者续写，同一原始前三段\n\n"
        for label,turns in (("B+ 只看最近一段",Bplus["turns"]),
                            ("B++ 让真正作者看到签名的前面几段",new["turns"])):
            manuscript+="## "+label+"\n\n"
            for i,t in enumerate(turns,1):
                manuscript+=f"### t{i:02d} SHA256 {t['sha256']}\n\n"+t["prose"]+"\n\n"
        (ROOT/"ORIGINAL_READABLE_LITERARY_BPLUS_VS_BPLUSPLUS.md").write_text(
            manuscript,encoding="utf8")
        status["status"]="SOURCE_LOCKED_BPLUSPLUS_AUTHOR_ORIGINAL_T05_COMPLETED"
        status["comparison"]=compare
        print("WF0AV_REAL_ORIGINAL_BPLUSPLUS_FULL_PROSE "+json.dumps({
            "old_Bplus_sha":bp.FIRST_PLUS_SHA,"Bplusplus_sha":h(txt),
            "new_t05_sha":new["turns"][4]["sha256"],
            "old_Bplus_t04_t05":[x["prose"][:200] for x in Bplus["turns"][3:]],
            "new_Bplusplus_t04_t05":[x["prose"][:450] for x in new["turns"][3:]],
            "one_new_writer_call":cap.calls,"model_judge":None,
            "literary_improvement_proven":False,
        },ensure_ascii=False),flush=True)
    except Exception as e:
        msg=str(e)
        status["status"]="SOURCE_FIRST_FINAL_T05_FAILURE_NO_RETRY"
        status["failure_code"]=msg if re.fullmatch(
            r"WF[A-Z0-9_:.\-]{3,180}",msg) else type(e).__name__+":NO_RETRY"
    finally:
        status["last_new_paid_calls"]=cap.calls
        status["last_new_reserved_completion"]=cap.reserved
        status["all_four_new_Bplusplus_calls_total"]=3+cap.calls
        status["total_paid_calls"]=PRIOR_PAID_CALLS+cap.calls
        status["total_reserved_completion"]=PRIOR_RESERVED_COMPLETION+cap.reserved
        status["provider_events"]=writer.public_events() if writer else []
        save(ROOT/"STATUS.json",status)
        print("WF0AV_LAST_T05_SOURCE_STATUS "+json.dumps({
            "status":status["status"],"new_calls":cap.calls,
            "cumulative_paid_calls":status["total_paid_calls"],
            "failure":status.get("failure_code"),
            "literary_improvement_proven":False,
        },ensure_ascii=False),flush=True)
    if status["status"]=="SOURCE_FIRST_FINAL_T05_FAILURE_NO_RETRY":
        raise RuntimeError("WF0AV_BPLUSPLUS_FINAL_T05_ORIGINAL_WIRES_SAVED_NO_RETRY")

if __name__=="__main__":
    if "--preflight" in sys.argv:
        dry()
    else:
        main()
