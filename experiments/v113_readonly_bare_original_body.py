"""Read-only recovery of V113 bare-model ORIGINAL prose from red JSON.

Original bare DeepSeek responded to its one pre-registered model request with
a JSON object containing both "prose" (novel body) and an unauthorized extra
"type" field. It is a schema failure, NOT a model transport or body loss.

For literary observation only: extract original "prose" characters byte-for-
byte as decoded; never pretend original JSON passed the one-field contract.
No DeepSeek secret is needed, no regeneration, editing, or R2 writes.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json,os
from experiments.v113_github_r2_cas import GitHubS3CAS
from experiments.v113_recover_blind_read_only import (
    PRECOMMIT,MANIFEST,FAILED_BARE_DECODED,StrictReadOnlyCAS,load,need,
)

BARE_WIRE="259651bbdd61ca905c9d263cb4efab21f7b1045bbe561a098e00650b50a7406b"

def run():
    need(not os.environ.get("DEEPSEEK_API_KEY") and
         not os.environ.get("DEEPSEEK"),
         "WF113D_NO_MODEL_KEY_PERMITTED")
    cas=StrictReadOnlyCAS()
    manifest=load(cas,MANIFEST)
    receipt=manifest["raw_provider_request_receipts"][3]
    need(receipt["stage"]=="BARE_PROSE" and
         receipt["decoded_cas_sha256"]==FAILED_BARE_DECODED and
         receipt["wire_cas_sha256"]==BARE_WIRE and
         manifest["arms"][2]["status"]=="FAILED",
         "WF113D_NOT_HISTORICAL_BARE_ORIGINAL_FAILED_SLOT")
    wrapped=load(cas,FAILED_BARE_DECODED)
    need(wrapped["precommit_sha256"]==PRECOMMIT and
         wrapped["provider_wire_cas_sha256"]==BARE_WIRE and
         wrapped["not_manually_corrected"] is True,
         "WF113D_UNMODIFIED_MODEL_PROVENANCE_MISSING")
    orig=wrapped["original_answer"]
    need(type(orig) is dict and set(orig)=={"prose","type"}
         and type(orig["prose"]) is str and
         type(orig["type"]) is str,
         "WF113D_EXPECTED_EXTRA_TYPE_SCHEMA_REJECTION_NOT_GROUNDED")
    wire=load(cas,BARE_WIRE)
    content=wire["choices"][0]["message"]["content"]
    need(json.loads(content)==orig,
         "WF113D_WIRE_BODY_NOT_EQUAL_DECODED_ORIGINAL")
    body=orig["prose"]
    need(200<=len(body)<=10000 and
         "\ufffd" not in body and "\x00" not in body,
         "WF113D_ORIGINAL_BODY_INVALID")
    out=Path("wf113_original_schema_rejected_bare")
    out.mkdir(exist_ok=False)
    (out/"original_bare_prose_UNSCORED.txt").write_text(
        "V113 裸DeepSeek首次真实模型回答的原始正文（原JSON多出type字段，严格结构校验失败）\n"
        "题目：给我一个追逐打斗的玄幻1000字\n"
        "注意：此稿只供观察，不可假装原正式三组协议已通过，也不是补写或重抽。\n\n"
        +body+"\n",encoding="utf8")
    info={
        "format":"wf.eval.v113.schema-rejected-bare-original-text-only",
        "original_arm_status":"FAILED",
        "original_model_returned_extra_key":"type",
        "original_decoded_JSON_keys":sorted(orig),
        "body_extracted_without_editing":True,
        "literal_prose_characters":len(body),
        "literal_prose_sha256":sha256(body.encode("utf8")).hexdigest(),
        "original_decoded_answer_cas_sha256":FAILED_BARE_DECODED,
        "original_wire_cas_sha256":BARE_WIRE,
        "old_four_paid_requests_replayed":False,
        "new_model_calls":0,"R2_writes":0,
        "strict_three_arm_eligibility":False,
        "literary_grade":"UNDETERMINED",
    }
    (out/"original_bare_provenance_and_failure.json").write_text(
        json.dumps(info,ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps({"status":"WF113D_BARE_ORIGINAL_TEXT_RECOVERED_AS_UNSCORED_ONLY",
                      **info},ensure_ascii=False,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(run())
