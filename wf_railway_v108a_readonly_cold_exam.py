"""V108 read-only investigation of *already paid* E/F ORIGINAL CAS objects.

Zero model calls and ZERO writes. This reads ONLY five explicit experiment
object addresses, never private source books. Distinguish a decoded JSON
candidate rejected by WF's V96 parser from a provider WIRE JSON error which
the legacy DeepSeek client did NOT save (no fabricated candidate prose).
"""
from __future__ import annotations
import os, json, re
from writerforge.v79_provisional_r2_cas_journal import WFProvisionalR2CASJournal
from writerforge.v104_self_scene_protocol import digest,encode
from writerforge.v107_outline_observation import observe_shared_two_turns

for key in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
            "DISCOVERY_API_KEY","WF_LEARN_UPLOAD_TOKEN"):
    os.environ.pop(key,None)

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
PRECOMMIT="6a5b713768bdf6e8d78f1600b17d0745f40999cdad54d514f6d784e866a22631"
MANIFEST="dc5b6095174acb350426192c44159783026cb647e0dce21bc528eba8111f2f6e"
SHARED_OUTLINE="718a76ff2816ced4cf2f5780d56718ea928888be14d6c2c1bc185b321bec168f"
RAW=(
("both",1,"de4bbceecdda8eb9ca382220dad1f899d252874088d0c1dbc9b8c238cb5b99c9"),
("emotion_rolling",2,"51f43637794319af4cd4ae6cf336494170b98fdd4ced83d33b8124efbbb4bec7"),
("emotion_rolling",3,"cbd9af5fdb29c193af093a51dba2972a06a3b08da0e20642ad4d3d5ff5ad8f9e"),
("foresight_rolling",4,"ca54a9e95b262d487ef211127a7dd91a90e1971da2e48d9e033e4e3d5ff0abb1"),
)
def need(x,code):
    if not x:raise ValueError(code)
def say(x):
    print(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")),flush=True)
def load(cas,sha):
    need(re.fullmatch("[0-9a-f]{64}",sha) is not None,"WF108A_PTR_INVALID")
    raw=cas._get_content(sha)
    need(digest(raw)==sha,"WF108A_PRIVATE_CAS_CHANGED")
    return json.loads(raw.decode("utf8","strict"))

def run():
    need(os.environ.get("WF_API_TOKEN") and
         not os.environ.get("DEEPSEEK_API_KEY") and
         not os.environ.get("WF_INDEX_UPLOAD_TOKEN"),
         "WF108A_READ_ONLY_IDENTITY_REQUIRED")
    cas=WFProvisionalR2CASJournal(endpoint=ENDPOINT,read_only=True)
    need(cas.read_only and cas.writer is None,
         "WF108A_READER_WRITER_PRIVILEGE_LEAK")
    pre=load(cas,PRECOMMIT)
    need(pre["id"]=="WF-V108-E-VS-F-NEW-LOCKED-ONE-SHOT-20261021"
         and pre["new_experiment_not_replay_of_v106"] is True,
         "WF108A_NOT_NEW_EXPERIMENT_PRECOMMIT")
    manifest=load(cas,MANIFEST)
    need(manifest["format"]=="wf.exam.v108.original-real-E-F-smoke"
         and manifest["precommit_sha256"]==PRECOMMIT
         and manifest["total_real_provider_requests"]==5
         and manifest["author_review"]=="NOT_PERFORMED"
         and len(manifest["arms"])==2,
         "WF108A_ORIGINAL_RUN_MANIFEST_WRONG")
    shared=load(cas,SHARED_OUTLINE)
    need(shared["format"]=="wf.exam.v108.shared-original-outline"
         and shared["same_for_both_arms"] is True,
         "WF108A_COMMON_BEAT_NOT_LOCKED")
    seen=[]
    for arm,index,ptr in RAW:
        original=load(cas,ptr)
        need(original["format"]==
             "wf.exam.v108.single-unmodified-model-response"
             and original["original_precommit_sha256"]==PRECOMMIT
             and original["arm"]==arm
             and original["source_edit_or_automatic_fix"] is False,
             "WF108A_ORIGINAL_REPLY_NOT_SAME_TRIAL")
        body=original["original_decoded_json"]
        record={"ordinal":index,"arm":arm,
                "raw_model_reply_cas_sha256":ptr,
                "full_decoded_reply_sha256":digest(encode(body)),
                "returned_JSON_keys":sorted(body.keys()),
                "raw_model_answer_not_edited":True}
        if index==1:
            record["two_turns"]=observe_shared_two_turns(body)
        elif index==2:
            record["plan_contains_horizon"]="horizon" in body
            record["chapter_plan_keys"]=sorted(body)
        elif index==3:
            trace=body.get("trace")
            affect=body.get("affect")
            txt=body.get("prose")
            record.update({
                "prose_length":len(txt) if type(txt) is str else None,
                "prose_first_150_chars":txt[:150] if type(txt) is str else None,
                "trace":trace,
                "affect_shape":sorted(affect) if type(affect) is dict else None,
                "original_WF_rejection":"WF96_UNDECLARED_PREVIOUS_CAUSE",
                "first_turn_should_have_null_parent_effect":True,
            })
        elif index==4:
            horizon=body.get("horizon")
            record.update({
                "plan_has_two_future_choices":
                    type(horizon) is dict and len(horizon.get("choices",[]))==2,
                "plan_has_event_types":sorted(body.keys()),
                "first_future_choice_step_count":
                    len(horizon["choices"][0]["steps"])
                    if type(horizon) is dict and type(horizon.get("choices")) is list
                    and len(horizon["choices"])>=1 else None,
            })
        say({"status":"WF108A_ORIGINAL_MODEL_COLD_RECORD",**record})
        seen.append(record)
    need(shared["original_reply_cas_sha256"]==RAW[0][2],
         "WF108A_SHARED_BEAT_NOT_FROM_RAW_MODEL")
    say({
        "status":"WF108A_FIVE_PAID_ATTEMPTS_FOUR_JSON_REPLIES_COLD_VERIFIED",
        "precommit_sha256":PRECOMMIT,
        "manifest_sha256":MANIFEST,
        "raw_decoded_model_replies_verified":len(seen),
        "last_call_index":5,
        "last_call_decoded_reply_cas_sha256":None,
        "reason":"WF_FLASH_INVALID_JSON_RESPONSE_BEFORE_DECODED_CAS",
        "model_calls_during_cold_read":0,
        "r2_writes_during_cold_read":0,
        "old_books_loaded":False,
        "original_E_F_story_winner":"UNDETERMINED",
    })
    return 0

if __name__=="__main__":
    say({"status":"WF108A_ZERO_MODEL_COLD_FORENSIC_START","read_only":True})
    try:rc=run()
    except Exception as e:
        v=str(e)
        if not re.fullmatch(r"WF108A_[A-Z0-9_]{1,160}",v):
            v="WF108A_FORENSIC_HALTED_UNCLASSIFIED"
        say({"status":"WF108A_FOR_FAILED_NO_RETRY","reason_code":v,
             "r2_writes":0,"model_calls":0})
        rc=1
    say({"status":"WF108A_ZERO_MODEL_COLD_FORENSIC_EXIT","code":rc})
    raise SystemExit(rc)
