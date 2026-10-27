"""WF 0.BH permanent evidence recheck, zero model, zero R2, zero Canon.

Checks six ORIGINAL locally-generated JSON completion bytes against the
independently recorded actions artifact SHA identities. No model API wire
exists and no reader signed any literary grade. Only exact source identity,
observable variation, and usage counters may be computed here.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json

from experiments.wf_0bh_stronger_local_writer_once import (
    prepare_stronger_inputs, MODEL_ID, MODEL_REVISION, MODEL_SHA256, MODEL_LICENSE,
    CASE_IDS, MAX_CALLS,
)
from experiments.wf_0be_v1_v2_preflight_only import canonical

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"experiments/wf_0bh_real_qwen25_3b_outputs_20261027"
OUTPUT=Path("wf0bh_verified_three_pair_source_summary")
ORIGINAL_RUN_ID=40499625320
ORIGINAL_ARTIFACT_ID=12732213344
ORIGINAL_LOCAL_RESPONSE_MODEL="/home/runner/work/_temp/wf0bh-qwen25-3b.gguf"
EXPECTED_SOURCE_PREPARED_SHA256="288f604cb79b03a4528933c2c27fd6bab4c9743c8be67af9e18e170a17be97cf"
KNOWN_ORIGINAL_BYTES={
    "output_00_purposeful-second-attempt_v1.json":
        "3fc9fe81e1bf4d22168817b8bf5c50487270f96154add86e69f0d22de87fb2b5",
    "output_01_purposeful-second-attempt_v2.json":
        "32947c4809549c0b1d7380abe9effdd135aa1d03a6270e839d23b1f53c5469ba",
    "output_02_bounded-eyewitness_v2.json":
        "47819ac67bff1493c745d1f3b190d89c2567edacd0704ebf0cb85d9f0ac60d39",
    "output_03_bounded-eyewitness_v1.json":
        "2dc99d56dc1cc5704e0b796539dffb02b12d4c01dccbe8405ccfd9f0b69478e7",
    "output_04_custody-without-fulfillment_v1.json":
        "10f920e2415e5f6235e655a346d1af2f2a96e3df3b8d56d7db416b74f0a3d1ef",
    "output_05_custody-without-fulfillment_v2.json":
        "b0ccf1f2d1ae5d08d6b52efeeb405e72afabcd6d1787ba7b461ee6544cf003e6",
}


def sha(raw:bytes)->str:
    return sha256(raw).hexdigest()


def fail(reason):
    raise ValueError(reason)


def parse_canonical_bytes(raw:bytes)->dict:
    def unique(pairs):
        o={}
        for k,v in pairs:
            if k in o:
                fail("WF0BH_DUPLICATE_ORIGINAL_JSON_FIELD")
            o[k]=v
        return o
    try:
        item=json.loads(raw.decode("utf8","strict"),object_pairs_hook=unique)
    except (UnicodeError,ValueError,TypeError) as e:
        raise ValueError("WF0BH_ORIGINAL_JSON_NOT_READABLE") from e
    if type(item) is not dict or canonical(item)!=raw:
        fail("WF0BH_ORIGINAL_JSON_NOT_CANONICAL")
    return item


def verify_stronger_local_originals(*,archive:Path=SOURCE)->dict:
    """Deterministic source identity & observed token usage, not a grade."""
    preflight=prepare_stronger_inputs()
    if sha(canonical(preflight))!=EXPECTED_SOURCE_PREPARED_SHA256:
        fail("WF0BH_ORIGINAL_MODEL_PREPARED_INPUT_SHA_MISMATCH")
    try:
        manifest=json.loads((archive/"SOURCE_MANIFEST.json").read_text("utf8"))
    except (ValueError,UnicodeError,OSError) as exc:
        raise ValueError("WF0BH_ORIGINAL_MANIFEST_NOT_PRESENT") from exc
    if (type(manifest) is not dict or
        manifest.get("format")!=
          "wf.0bh.stronger-local-originals-immutable-source-manifest.v1" or
        manifest.get("original_actions_run_id")!=ORIGINAL_RUN_ID or
        manifest.get("original_actions_artifact_id")!=ORIGINAL_ARTIFACT_ID or
        manifest.get("trial_id")!=preflight["trial_id"] or
        manifest.get("source_kind")!=
          "REAL_LOCAL_OPEN_WEIGHT_GENERATION_NOT_PROVIDER_HTTP_WIRE" or
        manifest.get("model_id")!=MODEL_ID or
        manifest.get("model_revision")!=MODEL_REVISION or
        manifest.get("model_weights_sha256")!=MODEL_SHA256 or
        manifest.get("engine")!="llama-cpp-python==0.3.16" or
        manifest.get("model_licence")!=MODEL_LICENSE or
        manifest.get("source_preflight_sha256")!=EXPECTED_SOURCE_PREPARED_SHA256 or
        manifest.get("source_original_status_sha256")!=
          "0df65c7a158e18b38b34ca6a90cd7488d51c8dd38fe790b41342686e09bb3d4c" or
        manifest.get("v1_capsule_sha256")!=preflight["v1_capsule_sha256"] or
        manifest.get("v2_capsule_sha256")!=preflight["v2_capsule_sha256"] or
        manifest.get("complete_cases")!=3 or
        manifest.get("total_model_calls")!=MAX_CALLS or
        manifest.get("paid_api_calls")!=0 or
        manifest.get("trusted_independent_reader_votes")!=0 or
        manifest.get("independently_proven_literary_gain") is not False or
        manifest.get("auto_promoted") is not False or
        manifest.get("original_glm_429_retried") is not False or
        manifest.get("no_source_canon_or_r2_changes") is not True or
        type(manifest.get("outputs")) is not list or
        len(manifest["outputs"])!=MAX_CALLS):
        fail("WF0BH_MANIFEST_SOURCE_INVALID")
    records={}
    for i,(expected,item) in enumerate(zip(preflight["items"],manifest["outputs"])):
        filename=f"output_{i:02d}_{expected['case_id']}_{expected['arm']}.json"
        key=(item.get("case_id"),item.get("arm"))
        # Fail with the exact *category* of changed trust data. Never
        # suppress a SHA mismatch or relax source matching to get GREEN.
        checks={
            "case_arm":key==(expected["case_id"],expected["arm"]),
            "unique":key not in records,
            "filename":item.get("file")==filename,
            "known_source_file":filename in KNOWN_ORIGINAL_BYTES,
            "original_wire_sha":item.get("original_local_completion_sha256")==
                KNOWN_ORIGINAL_BYTES.get(filename),
            "source_sha":item.get("source_sha256")==expected["source_sha256"],
            "prompt_sha":item.get("prompt_sha256")==expected["prompt_sha256"],
            "finish":item.get("finish_reason")=="stop",
        }
        mismatched=[name for name,passed in checks.items() if not passed]
        if mismatched:
            fail("WF0BH_ORIGINAL_PROMPT_SOURCE_OR_ORDER_CHANGED:"+str(i)+
                 ":"+",".join(mismatched))
        try:
            original=(archive/filename).read_bytes()
        except OSError as exc:
            raise ValueError("WF0BH_ORIGINAL_OUTPUT_FILE_MISSING") from exc
        if sha(original)!=KNOWN_ORIGINAL_BYTES[filename]:
            fail("WF0BH_ORIGINAL_MODEL_OUTPUT_SHA_MISMATCH")
        response=parse_canonical_bytes(original)
        try:
            choice=response["choices"][0]
            content=choice["text"]
            usage=response["usage"]
        except (IndexError,KeyError,TypeError) as exc:
            raise ValueError("WF0BH_INVALID_LOCAL_COMPLETION_SCHEMA") from exc
        if (response.get("model")!=ORIGINAL_LOCAL_RESPONSE_MODEL or
            response.get("object")!="text_completion" or
            type(content) is not str or not content.strip() or
            choice.get("finish_reason")!="stop" or
            sha(content.encode("utf8"))!=item.get("authored_text_sha256")):
            fail("WF0BH_ORIGINAL_TEXT_OR_MODEL_DRIFT")
        if (type(usage) is not dict or
            any(type(usage.get(key)) is not int or usage[key]<=0 or
                usage[key]!=item.get(key)
                for key in ("prompt_tokens","completion_tokens","total_tokens")) or
            usage["total_tokens"]!=
              usage["prompt_tokens"]+usage["completion_tokens"] or
            usage["completion_tokens"]>expected["max_completion_tokens"]):
            fail("WF0BH_ORIGINAL_LOCAL_USAGE_MISMATCH")
        records[key]={
            "filename":filename,
            "response_sha256":KNOWN_ORIGINAL_BYTES[filename],
            "text_sha256":item["authored_text_sha256"],
            "text":content,
            "source_sha256":expected["source_sha256"],
            "prompt_tokens":usage["prompt_tokens"],
            "completion_tokens":usage["completion_tokens"],
            "total_tokens":usage["total_tokens"],
        }
    if len(records)!=MAX_CALLS:
        fail("WF0BH_ORIGINAL_PAIR_INCOMPLETE")
    pairs=[]
    for case in CASE_IDS:
        a,b=records[(case,"v1")],records[(case,"v2")]
        pairs.append({
            "case_id":case,
            "v1_text_sha256":a["text_sha256"],
            "v2_text_sha256":b["text_sha256"],
            "literal_outputs_equal":a["text"]==b["text"],
            "v1_prompt_tokens":a["prompt_tokens"],
            "v2_prompt_tokens":b["prompt_tokens"],
            "v1_completion_tokens":a["completion_tokens"],
            "v2_completion_tokens":b["completion_tokens"],
            "v1_total_tokens":a["total_tokens"],
            "v2_total_tokens":b["total_tokens"],
            "v2_extra_total_tokens":b["total_tokens"]-a["total_tokens"],
            "human_literary_preference":None,
        })
    costs={}
    for arm in ("v1","v2"):
        subset=[v for (case,a),v in records.items() if a==arm]
        for unit in ("prompt_tokens","completion_tokens","total_tokens"):
            costs[f"{arm}_actual_{unit}"]=sum(x[unit] for x in subset)
    return {
        "format":"wf.0bh.verifiable-local-source-no-literary-score.v1",
        "status":"REAL_3B_LOCAL_OUTPUTS_VERIFIED_UNGRADED",
        "source_actions_run_id":ORIGINAL_RUN_ID,
        "trial_id":preflight["trial_id"],
        "model_id":MODEL_ID,
        "model_sha256":MODEL_SHA256,
        "author_host_kind":"SINGLE_LOCAL_CPU_RUNTIME_NOT_INDEPENDENT_AGENT",
        "actual_local_model_calls":MAX_CALLS,
        "completed_pairs":len(pairs),
        "exactly_equal_text_pairs":sum(p["literal_outputs_equal"] for p in pairs),
        "v2_extra_total_tokens":costs["v2_actual_total_tokens"]-
                                costs["v1_actual_total_tokens"],
        "new_paid_provider_calls":0,
        "new_model_calls_in_this_audit":0,
        "independent_reader_votes":0,
        "human_independent_blindness_proven":False,
        "literary_gain_proven":False,
        "safe_to_conclude_global_v2_falsification":False,
        "auto_activate_candidate":False,
        "candidate_stage":"SHADOW",
        "old_glm_429_retried":False,
        "no_private_r2_novel_or_canon_writes":True,
        "do_not_autoretry_for_preferred_scores":True,
        "case_pairs":pairs,
        **costs,
    }


def save_verified_observation(*,output:Path=OUTPUT)->dict:
    if output.exists():
        raise FileExistsError("WF0BH_REPORT_ALREADY_EXISTS_NO_REPEAT")
    result=verify_stronger_local_originals()
    output.mkdir(parents=True,exist_ok=False)
    (output/"STATUS.json").write_bytes(canonical(result))
    print("WF0BH_REAL_3B_SOURCE_AUDIT "+json.dumps({
        "completed_pairs":result["completed_pairs"],
        "v1_actual_total_tokens":result["v1_actual_total_tokens"],
        "v2_actual_total_tokens":result["v2_actual_total_tokens"],
        "v2_extra_total_tokens":result["v2_extra_total_tokens"],
        "literary_gain_proven":False,
        "new_paid_provider_calls":0,
    },ensure_ascii=False,sort_keys=True),flush=True)
    return result


if __name__=="__main__":
    save_verified_observation()
