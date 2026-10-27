"""WF 0.BG source-first analysis of REAL saved local model outputs.

Zero inference, zero network. Rechecks each output's exact SHA, literal text,
model identity, prompt SHA, frozen task and observed local engine token usage.
Only counts *observable* identical/different outputs and resource deltas.
Never manufactures human independent literary preference or Skill promotion.
"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import json
import re

from experiments.wf_0bg_first_local_open_weight_v1_v2_once import (
    prepare_inputs, MODEL_SHA256, MODEL_REVISION, MODEL_ID,
    EXPECTED_CALLS, CASE_IDS,
)
from experiments.wf_0be_v1_v2_preflight_only import build_preflight, canonical

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "experiments/wf_0bg_local_cpu_actual_outputs_20261027"
SUMMARY = Path("wf0bg_verified_real_local_two_pair_contrast")


def _sha(raw):
    return sha256(raw).hexdigest()


def _read_checked(path: Path, expected: str) -> dict:
    raw=path.read_bytes()
    if _sha(raw)!=expected:
        raise ValueError("WF0BG_LOCAL_ORIGINAL_OUTPUT_SHA_MISMATCH")
    def unique(pairs):
        obj={}
        for key,value in pairs:
            if key in obj:
                raise ValueError("WF0BG_DUPLICATE_SOURCE_FIELD")
            obj[key]=value
        return obj
    try:
        result=json.loads(raw.decode("utf8"),object_pairs_hook=unique)
    except (UnicodeError,ValueError) as e:
        raise ValueError("WF0BG_ORIGINAL_OUTPUT_INVALID") from e
    if raw!=canonical(result):
        raise ValueError("WF0BG_ORIGINAL_OUTPUT_NOT_CANONICAL")
    return result


def review_observed_local_pairs(*, archive: Path = SOURCE) -> dict:
    """No provider, no judge, no model: observed byte equality and token costs."""
    plan=prepare_inputs()
    full=build_preflight()
    rows=json.loads((archive/"SOURCE_MANIFEST.json").read_text("utf8"))
    if (rows.get("format")!="wf.0bg.preserved-local-open-weight-source-evidence.v1" or
            rows.get("trial_id")!=plan["trial_id"] or
            rows.get("real_actions_run_id")!=40496101857 or
            rows.get("real_actions_artifact_id")!=12730279357 or
            rows.get("model_weights_sha256")!=MODEL_SHA256 or
            rows.get("model_revision")!=MODEL_REVISION or
            rows.get("source_model")!=MODEL_ID or
            rows.get("preflight_sha256")!=_sha(canonical(plan)) or
            rows.get("source_kind")!="LOCAL_OPEN_WEIGHT_REAL_MODEL" or
            rows.get("actual_new_local_model_generations")!=EXPECTED_CALLS or
            rows.get("original_paid_provider_calls")!=0 or
            rows.get("literary_gain_proven") is not False or
            rows.get("no_independent_reader_votes") is not True or
            rows.get("no_skill_activation") is not True or
            rows.get("historical_trial_0ay_429_unchanged") is not True or
            rows.get("original_v1_capsule_sha256")!=plan["v1_capsule_sha256"] or
            rows.get("original_v2_shadow_capsule_sha256")!=plan["v2_capsule_sha256"] or
            type(rows.get("outputs")) is not list or
            len(rows["outputs"])!=EXPECTED_CALLS):
        raise ValueError("WF0BG_ARCHIVED_MODEL_OR_TRIAL_PROVENANCE_INVALID")
    original={(r["case_id"],r["arm"]):r for r in plan["items"]}
    fixed={(r["case_id"],r["arm"]):r for r in full["envelopes"]}
    observed={}
    for item in rows["outputs"]:
        key=(item.get("case_id"),item.get("arm"))
        if key not in original or key in observed:
            raise ValueError("WF0BG_LOCAL_CASE_DUPLICATE_OR_MISSING")
        ex=original[key]
        if (item.get("prompt_sha256")!=ex["prompt_sha256"] or
                item.get("source_sha256")!=ex["source_sha256"] or
                not isinstance(item.get("file"),str) or
                item["file"]!=f"output_{ex['index']:02d}_{ex['case_id']}_{ex['arm']}.json"):
            raise ValueError("WF0BG_ARCHIVED_LOCAL_PROMPT_OR_SOURCE_DRIFT")
        raw=_read_checked(archive/item["file"],item.get("raw_sha256"))
        try:
            response=raw["choices"][0]
            text=response["text"]
            finish=response["finish_reason"]
            usage=raw["usage"]
        except (IndexError,TypeError,KeyError) as exc:
            raise ValueError("WF0BG_ORIGINAL_LOCAL_MODEL_RESPONSE_INVALID") from exc
        if (raw.get("object")!="text_completion" or
                raw.get("model")!="/home/runner/work/_temp/wf0bg-qwen3.gguf" or
                type(text) is not str or not text.strip() or
                _sha(text.encode("utf8"))!=item.get("text_sha256") or
                finish not in ("stop","length") or
                item.get("finish_reason")!=finish or
                any(type(usage.get(k)) is not int or
                    usage[k]!=item.get(k) or usage[k]<=0
                    for k in ("prompt_tokens","completion_tokens","total_tokens")) or
                usage["total_tokens"]!=
                usage["prompt_tokens"]+usage["completion_tokens"]):
            raise ValueError("WF0BG_LOCAL_OUTPUT_TEXT_OR_ACTUAL_USAGE_DRIFT")
        normalized=re.sub(r"^\s*<think>.*?</think>\s*","",text,flags=re.DOTALL).strip()
        source_segments=fixed[key]["source_segments"]
        # String equality is evidence of exact source copying, NOT a
        # semantic literary score. A model can legitimately repeat source
        # for some tasks; only an external reviewer can judge appropriateness.
        pure_source_echo = normalized=="".join(source_segments)
        observed[key]=dict(raw_sha256=item["raw_sha256"],
                           authored_text_sha256=item["text_sha256"],
                           text=text,pure_source_echo=pure_source_echo,
                           prompt_tokens=usage["prompt_tokens"],
                           completion_tokens=usage["completion_tokens"],
                           total_tokens=usage["total_tokens"])

    if set(observed)!=set(original):
        raise ValueError("WF0BG_LOCAL_MODEL_PAIR_INCOMPLETE")
    result=[]
    for case in CASE_IDS:
        a,b=observed[(case,"v1")],observed[(case,"v2")]
        result.append({
            "case_id":case,
            "v1_text_sha256":a["authored_text_sha256"],
            "v2_text_sha256":b["authored_text_sha256"],
            "literal_generated_texts_equal":a["text"]==b["text"],
            "v1_is_literal_source_echo":a["pure_source_echo"],
            "v2_is_literal_source_echo":b["pure_source_echo"],
            "v1_prompt_tokens":a["prompt_tokens"],
            "v2_prompt_tokens":b["prompt_tokens"],
            "additional_v2_prompt_tokens":b["prompt_tokens"]-a["prompt_tokens"],
            "v1_actual_total_tokens":a["total_tokens"],
            "v2_actual_total_tokens":b["total_tokens"],
            "additional_v2_total_tokens":b["total_tokens"]-a["total_tokens"],
            "independent_literary_preference":None,
        })
    return {
        "format":"wf.0bg.verified-local-cpu-observation-no-judge.v1",
        "status":"ACTUAL_LOCAL_MODEL_OUTPUTS_VERIFIED_QUALITY_UNGRADED",
        "source_run_id":rows["real_actions_run_id"],
        "first_host_kind":"SINGLE_CPU_LOCAL_MODEL_NOT_INDEPENDENT_AGENT",
        "trial_id":plan["trial_id"],
        "model_sha256":MODEL_SHA256,
        "actual_local_model_calls":EXPECTED_CALLS,
        "real_external_paid_provider_calls":0,
        "completed_pairs":len(result),
        "literal_identical_pairs":sum(x["literal_generated_texts_equal"] for x in result),
        "both_arms_literal_prior_source_echo_pairs":sum(
            x["v1_is_literal_source_echo"] and x["v2_is_literal_source_echo"]
            for x in result),
        "v1_total_actual_tokens":sum(x["v1_actual_total_tokens"] for x in result),
        "v2_total_actual_tokens":sum(x["v2_actual_total_tokens"] for x in result),
        "new_model_calls_in_this_review":0,
        "actual_independent_reader_votes":0,
        "literary_quality_proven":False,
        "cross_host_literary_improvement_proven":False,
        "candidate_auto_promoted":False,
        "candidate_status":"SHADOW",
        "no_paid_old_trial_retry":True,
        "should_next_autonomous_revision_run":False,
        "suggested_evidence_state":"SHADOW_PARTIAL_LOCAL_NEGATIVE_SIGNAL_AWAIT_INDEPENDENT_PROOF",
        "pairs":result,
    }


def main(*, output: Path=SUMMARY):
    summary=review_observed_local_pairs()
    if output.exists():
        raise FileExistsError("WF0BG_VERIFIED_LOCAL_REVIEW_ALREADY_EXISTS")
    output.mkdir(parents=True,exist_ok=False)
    (output/"STATUS.json").write_bytes(canonical(summary))
    print("WF0BG_REAL_LOCAL_EVIDENCE_REVIEW "+
          json.dumps({
              "pairs":summary["completed_pairs"],
              "literal_identical_pairs":summary["literal_identical_pairs"],
              "v1_total_tokens":summary["v1_total_actual_tokens"],
              "v2_total_tokens":summary["v2_total_actual_tokens"],
              "new_provider_calls":0,
              "literary_quality_proven":False,
          },sort_keys=True),flush=True)
    return summary


if __name__=="__main__":
    main()
