"""V109A zero-paid read-only forensic: inspect actual F horizon duplicate IDs.

All pointers are NEW examiner-created test objects. No old user books.
Original decoded and HTTP wire responses stay immutable. Any temporary
ID renumbering below is used ONLY to test whether there are additional
syntactic errors; it is NEVER written back or used as prose plan.
"""
from __future__ import annotations
import os,json,re
from copy import deepcopy
from writerforge.v79_provisional_r2_cas_journal import WFProvisionalR2CASJournal
from writerforge.v104_self_scene_protocol import encode,digest
from writerforge.v105_forward_horizon import validate_horizon,V105FutureCausalityError
from wf_railway_v109_real_f_wire_first_once import ENDPOINT,HORIZON_PINS,EXAM,precommit

for k in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
          "DISCOVERY_API_KEY","WF_LEARN_UPLOAD_TOKEN"):
    os.environ.pop(k,None)
PRECOMMIT=digest(encode(precommit()))
MANIFEST="cf8e367ee7676cabe158a5e5516fe345b583015fbbf423b44c82f855a06c557b"
WIRE="757d2d66e28767f61785b13c2ec2d5de56b9b0272c725b23e5c39cff9c19069d"
DECODED="2cfe3842323e195a35f9b4decf0517d3cd98716dcaac7e8faa27e23f3efc9d9d"

def say(o):
    print(json.dumps(o,sort_keys=True,ensure_ascii=False,
                     separators=(",",":"),allow_nan=False),flush=True)

def req(ok,code):
    if not ok:raise ValueError(code)
def raw(cas,ptr):
    req(re.fullmatch("[0-9a-f]{64}",ptr) is not None,
        "WF109A_INVALID_CAS_POINTER")
    b=cas._get_content(ptr)
    req(digest(b)==ptr,"WF109A_R2_REMOTE_BYTES_CHANGED")
    return b

def run():
    req(os.environ.get("WF_API_TOKEN") and
        not os.environ.get("WF_INDEX_UPLOAD_TOKEN") and
        not os.environ.get("DEEPSEEK_API_KEY"),
        "WF109A_READER_NOT_ISOLATED")
    cas=WFProvisionalR2CASJournal(endpoint=ENDPOINT,read_only=True)
    req(cas.read_only and cas.writer is None,"WF109A_READER_NOT_READ_ONLY")
    fixed=json.loads(raw(cas,PRECOMMIT))
    req(fixed.get("id")==EXAM and fixed.get("max_calls")==4,
        "WF109A_WRONG_EXPERIMENT")
    manifest=json.loads(raw(cas,MANIFEST))
    req(manifest.get("format")=="wf.exam.v109.one-actual-F-wire-first-manifest"
        and manifest.get("precommit_sha256")==PRECOMMIT
        and manifest.get("model_requests_attempted")==1
        and manifest.get("outcome",{}).get("safe_reason")==
            "WF105_BRANCH_ID_NOT_UNIQUE",
        "WF109A_WRONG_PAID_RUN_STATUS")
    req(manifest["new_model_call_receipts"][0]["provider_wire_cas_sha256"]==WIRE
        and manifest["new_model_call_receipts"][0]["decoded_reply_cas_sha256"]==
            DECODED,"WF109A_LOG_POINTER_NOT_LINKED_TO_MANIFEST")
    w=json.loads(raw(cas,WIRE).decode("utf8","strict"))
    d=json.loads(raw(cas,DECODED).decode("utf8","strict"))
    user=d["original_answer"]
    req(d["stage"]=="chapter_plan"
        and d["provider_wire_cas_sha256"]==WIRE
        and json.loads(w["choices"][0]["message"]["content"])==user,
        "WF109A_DECODED_DOES_NOT_MATCH_RAW_PROVIDER_WIRE")
    horizon=user.get("horizon",{})
    choices=horizon.get("choices")
    req(type(choices) is list and len(choices) in (2,3),
        "WF109A_MODEL_HORIZON_MISSING")
    positions=[]
    for i,c in enumerate(choices,1):
        steps=c.get("steps") if type(c) is dict else None
        positions.append({
            "position":i,"original_model_branch_id":c.get("id"),
            "steps":len(steps) if type(steps) is list else None,
            "actor_actions":[
                {"actor":s.get("actor"),
                 "action_short":s.get("action","")[:120]}
                for s in (steps or []) if type(s) is dict
            ][:4],
            "original_content_sha256":digest(encode(c)),
        })
    original_sha=digest(encode(horizon))
    try:
        validate_horizon(horizon,author_pinned=HORIZON_PINS)
        actual_reject=None
    except V105FutureCausalityError as e:
        actual_reject=str(e)
    # IMPORTANT: This is a pure diagnostic and NEVER an alternative plan
    # supplied to WF. Only duplicate names are replaced in memory.
    hypothetical=deepcopy(horizon)
    for i,c in enumerate(hypothetical["choices"],1):
        c["id"]=f"diagnostic_branch_{i:02d}"
    try:
        audit=validate_horizon(hypothetical,author_pinned=HORIZON_PINS)
        hypothetical_error=None
        branch_states=[v["status"] for v in audit["branches"]]
    except V105FutureCausalityError as ex:
        hypothetical_error=str(ex)
        branch_states=None
    req(digest(encode(horizon))==original_sha,
        "WF109A_ATTEMPTED_MUTATION_OF_ORIGINAL_MODEL_RESPONSE")
    say({
        "status":"WF109A_ORIGINAL_WF_HORIZON_COLD_FORENSIC",
        "original_model_branch_structure":positions,
        "actual_original_validator_error":actual_reject,
        "simulated_unique_labels_only_other_error":hypothetical_error,
        "simulated_unique_labels_only_branch_states":branch_states,
        "diagnostic_touched_student_output":False,
        "hypothetical_fix_was_never_saved_or_used_in_prose":True,
        "provider_wire_cas_sha256":WIRE,
        "original_decoded_json_cas_sha256":DECODED,
        "provider_finish_reason":w.get("choices",[{}])[0].get("finish_reason"),
        "provider_usage":w.get("usage",{}),
        "actual_new_model_calls_for_forensic":0,
        "R2_writes":0,
        "model_output_literary_value_verified":False,
    })
    return 0

if __name__=="__main__":
    say({"status":"WF109A_READ_ONLY_STARTED","model_calls":0})
    try:rc=run()
    except Exception as ex:
        v=str(ex)
        if not re.fullmatch(r"(?:WF109A|WF105)_[A-Z0-9_]{1,150}",v):
            v="WF109A_FAIL_CLOSED_NO_RETRY"
        say({"status":"WF109A_READONLY_HALT","safe_reason":v,
             "model_calls":0,"r2_writes":0})
        rc=1
    say({"status":"WF109A_READONLY_EXIT","code":rc})
    raise SystemExit(rc)
