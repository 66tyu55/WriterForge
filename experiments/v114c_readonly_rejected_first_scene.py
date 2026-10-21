"""V114B failed first scene: zero-inference S3 R2 cold forensic and original text.

Never repeat the previously metered three model requests. Precisely match
provider HTTP raw wire, decoded JSON, frozen 2-beat original and manifest.
The result is structural diagnosis, NOT a new "repaired" student story.
No R2 mutations, no reading user's private novel corpus, no external model.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json,os,re
from writerforge.v96_causal_turns import (
    MIN_PROSE_CHARS,MAX_PROSE_CHARS,TURN_FIELDS,TRACE_FIELDS,
)
from experiments.v114_github_r2_cas import GitHubS3CAS
from experiments.v114b_real_wf_continuity_once import (
    precommit,packed,EXAM,
)

PRECOMMIT="c48ec7b4d20c346567f4639c51c987c0ab00cd131b75ddcbe9b82a631441a539"
MANIFEST="c9d1ffea1319f27bbd530f2bb44da2ccf68feda2d49280ffdf548e81eb430ffc"
SCENE_ORIGINAL="c49198a29fed64d8883393b3a2168e37011a09de32a9899986edfc148a499e88"
SCENE_WIRE="4ac42046aa4a45fc85c8572ca2828b938710041e15aa35b595deb37839f96bd8"

class StrictReadOnlyCAS(GitHubS3CAS):
    def _put_content(self,*args,**kwargs):
        raise RuntimeError("WF114C_PRIVATE_R2_WRITE_FORBIDDEN")

def need(ok,code):
    if not ok:raise ValueError(code)

def load(cas,ptr):
    need(type(ptr) is str and re.fullmatch("[0-9a-f]{64}",ptr) is not None,
         "WF114C_BAD_CAS_POINTER")
    b=cas._get_content(ptr)
    need(sha256(b).hexdigest()==ptr,"WF114C_REMOTE_CAS_MISMATCH")
    return json.loads(b.decode("utf8","strict"))

def report():
    need(not os.environ.get("DEEPSEEK_API_KEY") and
         not os.environ.get("DEEPSEEK"),
         "WF114C_NO_MODEL_CREDENTIALS_ALLOWED")
    cas=StrictReadOnlyCAS()
    frozen=load(cas,PRECOMMIT)
    need(frozen==precommit() and frozen["exam"]==EXAM,
         "WF114C_EXPERIMENT_PRECOMMIT_NOT_ORIGINAL")
    manifest=load(cas,MANIFEST)
    need(manifest.get("format")=="wf.exam.v114.one-real-WF-continuity-result"
         and manifest.get("precommit_sha256")==PRECOMMIT
         and manifest.get("actual_calls")==3
         and manifest.get("result",{}).get("status")==
             "WF_WRITING_REJECTED_NO_RETRY"
         and "WF96_TURN_PROSE_OR_TRACE_SCHEMA_INVALID"
             in manifest.get("result",{}).get("reason",""),
         "WF114C_ORIGINAL_MANIFEST_NOT_REJECTED_AS_EXPECTED")
    receipts=manifest.get("all_original_model_requests",[])
    need(type(receipts) is list and len(receipts)==3 and
         [r["status"] for r in receipts]==["DECODED_UNJUDGED"]*3 and
         receipts[2]["decoded_sha256"]==SCENE_ORIGINAL and
         receipts[2]["wire_sha256"]==SCENE_WIRE and
         receipts[2]["stage"]=="WF_FIRST_SCENE",
         "WF114C_THREE_REAL_REPLIES_NOT_SOURCE_LINKED")
    decoded=load(cas,SCENE_ORIGINAL)
    wire=load(cas,SCENE_WIRE)
    actual=decoded["student_unmodified_answer"]
    need(decoded.get("format")=="wf.exam.v114.one-model-decoded-original"
         and decoded["source_precommit_sha256"]==PRECOMMIT
         and decoded["wire_sha256"]==SCENE_WIRE
         and wire["choices"][0]["finish_reason"] in ("stop","length"),
         "WF114C_ORIGINAL_DECODED_NOT_WIRE_LINKED")
    raw_text=wire["choices"][0]["message"]["content"]
    need(json.loads(raw_text)==actual,
         "WF114C_PROVIDER_HTTP_NOT_EQUAL_TO_DECODED_STUDENT")
    if type(actual) is dict:
        prose=actual.get("prose")
        trace=actual.get("trace")
        root_keys=sorted(actual.keys())
        trace_keys=sorted(trace.keys()) if type(trace) is dict else None
        prose_chars=len(prose) if type(prose) is str else None
        enough=(type(prose) is str and
                MIN_PROSE_CHARS<=len(prose.strip())<=MAX_PROSE_CHARS)
        flags={
            "root_keys_exact":set(actual)==TURN_FIELDS,
            "prose_unicode_length_bounded":enough,
            "trace_object":type(trace) is dict,
            "trace_fields_exact":type(trace) is dict and
                set(trace)==TRACE_FIELDS,
        }
    else:
        prose,root_keys,trace_keys,prose_chars=None,None,None,None
        flags={"root_keys_exact":False,"prose_unicode_length_bounded":False,
               "trace_object":False,"trace_fields_exact":False}
    need(not all(flags.values()),
         "WF114C_MODEL_STORY_STRICT_SCHEMA_MYSTERIOUSLY_VALID")
    out=Path("wf114b_original_first_turn_readonly")
    out.mkdir(exist_ok=False)
    (out/"original_decoded_WF_FIRST_SCENE.json").write_text(
        json.dumps(actual,ensure_ascii=False,indent=2),
        encoding="utf8")
    if type(prose) is str:
        (out/"first_scene_UNACCEPTED_original_prose.txt").write_text(
            "V114B 真正 WF 首段候选原文：模型已返回但软件结构校验失败，"
            "不得当成合格章节。没有自动修改或重新生成。\n\n"+
            prose+"\n",encoding="utf8")
    analysis={
        "format":"wf.exam.v114b.zero-model.original-first-scene-diagnostics",
        "old_V114_135K_preHTTP_failure_preserved":True,
        "V114B_real_provider_requests":3,
        "V114B_paid_request_count_in_this_reader":0,
        "R2_new_writes":0,
        "first_scene_original_decoded_cas_sha256":SCENE_ORIGINAL,
        "first_scene_original_wire_cas_sha256":SCENE_WIRE,
        "original_reply_keys":root_keys,
        "original_trace_keys":trace_keys,
        "original_prose_characters":prose_chars,
        "actual_v96_required_fields":sorted(TURN_FIELDS),
        "actual_v96_required_trace_fields":sorted(TRACE_FIELDS),
        "original_schema_subchecks":flags,
        "original_failure":"WF96_TURN_PROSE_OR_TRACE_SCHEMA_INVALID",
        "model_generated_original_unmodified":True,
        "not_literary_accepted":True,
        "second_scene_generated":False,
        "novel_studio_run_on_actual_first_scene":False,
        "literary_quality_verified":False,
    }
    (out/"SCHEMA_DIAGNOSIS_AND_CAS.json").write_text(
        json.dumps(analysis,ensure_ascii=False,indent=2),
        encoding="utf8")
    print(json.dumps({
        "status":"WF114C_V114B_ORIGINAL_FIRST_SCENE_COLD_VERIFIED",
        "actual_v96_schema_subchecks":flags,
        "original_reply_keys":root_keys,
        "original_trace_keys":trace_keys,
        "first_scene_chars":prose_chars,
        "original_first_scene_sha256":SCENE_ORIGINAL,
        "new_model_calls":0,
        "R2_writes":0,
        "old_first_scene_still_schema_REJECTED":True,
        "next_turn_literary_improvement":"NOT_EVALUATED",
    },ensure_ascii=False,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(report())
