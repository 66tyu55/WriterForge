"""V116 sealed R2 cold re-audit: genuine V113 WF 951 and V114B 964.

Zero model credential, zero new provider calls, strictly no R2 writes.
Print SHA/offsets/candidate counts only; NEVER publicize original manuscripts.
Software PASS != story-quality validation or approval of V114B rejected prose.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import os

from experiments.v114c_readonly_rejected_first_scene import (
    StrictReadOnlyCAS,SCENE_ORIGINAL,SCENE_WIRE,MANIFEST as V114B_MANIFEST,
    load,need,
)
from experiments.v114_readonly_v113_real_source import (
    V113_MANIFEST,EXPECTED_PROSE_SHA,
)
from experiments.v113_github_r2_cas import GitHubS3CAS as V113CAS

class StrictV113ReadOnlyCAS(V113CAS):
    def _put_content(self,*args,**kwargs):
        raise RuntimeError("WF116_V113_ORIGINAL_CAS_NEVER_WRITABLE")
from writerforge.v114_external_story_state import external_temporal_step,temporal_prompt
from writerforge.v116_state_delta import extract_state_events,preflight_next_prose
from writerforge.v96_causal_turns import MAX_PROSE_CHARS

EXPECTED_V114B_PROSE_SHA=(
    "c5146b829348ea12724290550ab8d4b4d959f2c1aaa41459c38bdeef757ad166"
)

def digest(text):
    return sha256(text.encode("utf8")).hexdigest()

def state_cells(value):
    seen={}
    for key,content in value.items():
        domain,entity,predicate,scope,_=json.loads(key)
        seen[(domain,entity,predicate,scope)]=content
    return seen

def data_from_sealed():
    need(not os.getenv("DEEPSEEK") and not os.getenv("DEEPSEEK_API_KEY"),
         "WF116_MODEL_CREDENTIAL_IN_READONLY_RUNNER")
    cas_v113=StrictV113ReadOnlyCAS()
    cas_v114=StrictReadOnlyCAS()
    old=load(cas_v113,V113_MANIFEST)
    need(old.get("format")=="wf.eval.v113.three-arm-original-model-experiment" and
         old["arms"][0]["arm"]=="WF_SINGLE" and
         old["arms"][0]["real_codepoints"]==951 and
         old["arms"][0]["status"]=="WRITTEN","WF116_V113_OLD_MANIFEST_INVALID")
    wf_old=old["arms"][0]["prose_private_cas_sha256"]
    raw=cas_v113._get_content(wf_old)
    need(sha256(raw).hexdigest()==EXPECTED_PROSE_SHA,
         "WF116_V113_PROSE_CAS_MISMATCH")
    v113=raw.decode("utf8","strict")
    need(len(v113)==951 and v113.count("剑穗")>=2,
         "WF116_V113_PROSE_IDENTITY_FAILED")
    v114b=load(cas_v114,V114B_MANIFEST)
    need(v114b.get("result",{}).get("status")=="WF_WRITING_REJECTED_NO_RETRY" and
         v114b.get("actual_calls")==3 and
         "WF96_TURN_PROSE_OR_TRACE_SCHEMA_INVALID"
             in v114b["result"].get("reason",""),
         "WF116_V114B_OLD_FAILURE_NOT_PRESERVED")
    original=load(cas_v114,SCENE_ORIGINAL)
    need(original.get("wire_sha256")==SCENE_WIRE and
         type(original.get("student_unmodified_answer")) is dict,
         "WF116_V114B_WIRE_IDENTITY_FAILED")
    answer=original["student_unmodified_answer"]
    v114=answer["prose"]
    need(type(v114) is str and
         len(v114)==964 and digest(v114)==EXPECTED_V114B_PROSE_SHA and
         {"火髓果","右臂"}.issubset(set(
             ("火髓果" if "火髓果" in v114 else "", 
              "右臂" if "右臂" in v114 else ""))) and
         964>MAX_PROSE_CHARS and MAX_PROSE_CHARS==950,
         "WF116_V114B_SEALED_LENGTH_OR_TEXT_MISMATCH")
    return v113,v114

def run():
    v113,v114=data_from_sealed()
    first=external_temporal_step(v113,cast=("叶青梧","沈渡"))
    risks=[r["kind"] for r in first["reducer_result"].get("risks",[])]
    need("UNPROVEN_ITEM_TRANSFER" in risks,
         "WF116_GENUINE_V113_SWORD_TASSEL_TELEPORT_NOT_CAUGHT")
    old_items=state_cells(first["reducer_result"]["candidate_state"])
    need(old_items.get(("item","剑穗","holder","author_plan"))=="沈渡",
         "WF116_V113_SWORD_TASSEL_OLD_CARRIER_NOT_PRESERVED")
    old_index=v113.find("剑穗")
    need(old_index>=0,"WF116_V113_MISSING_OLD_TASSEL_ANCHOR")
    second=extract_state_events(v114,cast=("沈砚","唐蜃"))
    actual=external_temporal_step(v114,cast=("沈砚","唐蜃"))
    state=state_cells(actual["reducer_result"]["candidate_state"])
    needed={
        ("item","火髓果","holder","author_plan"):"沈砚左手心",
        ("character","沈砚","右臂可用性","author_plan"):"受限",
        ("character","沈砚","右臂伤情","author_plan"):"丹火灼及右前臂",
    }
    for key,want in needed.items():
        need(state.get(key)==want,
             "WF116_REAL_964_STATE_DELTA_UNRESOLVED_"+key[2].replace("右臂","ARM"))
    need(("item","火髓果","consumption","author_plan") not in state,
         "WF116_FRUIT_CONSUMPTION_FABRICATED")
    events=second["source_anchored_events"]
    fruit=[e for e in events if
           e["ops"][0]["cell"]["entityId"]=="火髓果"]
    need(len(fruit)==2 and
         fruit[0]["ops"][0]["value"]=="沈砚齿间" and
         fruit[1]["ops"][0]["value"]=="沈砚左手心" and
         fruit[1]["ops"][0]["expected"]=={"kind":"value","value":"沈砚齿间"},
         "WF116_REAL_FRUIT_TRANSFER_SEQUENCE_MISSING")
    need(actual["reducer_result"]["verified_events"]>=4,
         "WF116_MIT_REDUCER_DID_NOT_APPLY_STATE_CHANGES")
    prompt=temporal_prompt(actual)
    need("火髓果" in prompt and "左手心" in prompt and
         "右臂" in prompt and "受限" in prompt and
         actual["canon_writes"]==0 and actual["model_calls"]==0,
         "WF116_NEXT_TURN_STATE_NOT_TRANSMITTED")
    next_bad=("沈砚右臂挥剑，火髓果还在齿间。"
              "他未曾服下灵丹，法力却瞬间回涨，原来的痛苦一扫而空。")
    check=preflight_next_prose(
        next_bad,previous_candidate_state=actual["reducer_result"]["candidate_state"],
        previous_risks=actual["reducer_result"]["risks"])
    need(check["blocked"] and
         "WF116_ARM_USED_WITHOUT_RECOVERY" in check["findings"],
         "WF116_NEXT_TURN_UNSUPPORTED_ARM_ACTION_NOT_REJECTED")
    next_ok=("沈砚右臂仍垂在身后，左手攥住火髓果，"
             "用肩撞开岔口的木栅，带着尚未痊愈的伤势继续逃。")
    ok=preflight_next_prose(
        next_ok,previous_candidate_state=actual["reducer_result"]["candidate_state"],
        previous_risks=actual["reducer_result"]["risks"])
    need(not ok["blocked"],"WF116_NEXT_TURN_VALID_BUT_REJECTED")
    report={
        "format":"wf.audit.v116.sealed-original-state-delta.zero-provider",
        "V113":{
            "source_sha256":digest(v113),
            "original_characters":len(v113),
            "first_sword_tassel_character_offset":old_index,
            "sword_tassel_teleport_rejected":True,
            "last_held_candidate_actor":"沈渡",
            "reducer_unresolved_codes":risks,
        },
        "V114B":{
            "source_sha256":digest(v114),
            "original_characters":len(v114),
            "strict_schema_original_rejected_for_length":True,
            "original_v96_max_chars":MAX_PROSE_CHARS,
            "old_original_model_calls":3,
            "second_prose_never_generated":True,
            "fruit_anchored_events":[{
                 "at":e["evidence"]["start"],
                 "end":e["evidence"]["end"],
                 "value":e["ops"][0]["value"],
                 "expected":e["ops"][0]["expected"]
             } for e in fruit],
            "arm_disability_candidate":"受限",
            "right_forearm_injury_candidate":"丹火灼及右前臂",
            "fruit_consumed":False,
            "event_proposal_count":len(events),
            "mit_temporal_reducer_applied_events":
                 actual["reducer_result"]["verified_events"],
            "novel_studio_next_turn_state_prompt_contains_fruit_arm":True,
            "synthetic_next_turn_wrong_arm_blocked":check["blocked"],
            "synthetic_next_turn_safe_path_passed":not ok["blocked"],
        },
        "new_model_calls":0,"R2_writes":0,
        "historical_prose_rewritten":False,
        "factjournal_canon_writes":0,
        "literary_semantic_truth_independently_verified":False,
        "new_actual_WF_second_scene_generated":False,
        "paid_literary_test_authorized":False,
    }
    # Only SHA, line offsets and derived state; no original source text.
    directory=Path("wf116_sealed_state_audit_summary")
    directory.mkdir(exist_ok=False)
    (directory/"STATE_DELTA_READONLY_AUDIT.json").write_text(
         json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps(report,ensure_ascii=False,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(run())
