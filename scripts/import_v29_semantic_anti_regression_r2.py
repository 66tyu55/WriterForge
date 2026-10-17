"""Zero-model immutable backfill from genuinely verified V29 recovered audit."""
from __future__ import annotations
from hashlib import sha256
import json
from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.v29_semantic_regression_candidates import candidate_from_audit
from scripts.run_v29_old_new_length_recovery import PREFIX

AGGREGATE_SHA="49ae267ebbc15be5f0350015ad610f994be277339471c4e72f27792d7f37683e"

def run(store):
    if store.config.bucket!="writerforge-private-library":
        raise ValueError("PRIVATE_R2_ONLY")
    raw=store._get_small(f"{PREFIX}/three-slot-holdout-audit/{AGGREGATE_SHA}.json",17000)
    if sha256(raw).hexdigest()!=AGGREGATE_SHA:
        raise ValueError("REAL_AGGREGATE_SHA_FAILED")
    source=json.loads(raw)
    result=candidate_from_audit(source,report_sha256=AGGREGATE_SHA)
    body=_canonical(result)
    h=sha256(body).hexdigest()
    key=f"{PREFIX}/unreviewed-semantic-change-candidates/{h}.json"
    store._put_small_immutable(key,body,h)
    if store._get_small(key,10000)!=body:
        raise ValueError("CANDIDATE_PRIVATE_R2_ROUNDTRIP_FAILED")
    output={
        "stage":"V29_ACTUAL_OLD_NEW_SEMANTIC_CONTEXT_CANDIDATES_VERIFIED",
        "audit_sha256":AGGREGATE_SHA,
        "candidate_sha256":h,
        "observations":[{
            "scenario":x["scenario"],"delta":x["model_effect_new_minus_old"],
            "status":x["candidate_status"],"mechanism_changed":
                x["semantic_changed_operations"],
        } for x in result["observations"]],
        "five_dimension_regression_present":result["any_five_dimension_regression"],
        "core_promoted":False,
        "legacy_mechanisms_deleted":False,
        "source_or_manuscript_downloaded":False,
        "model_calls":0,
        "second_window":"LOCKED",
    }
    print(json.dumps(output,ensure_ascii=False,sort_keys=True))
    return output

if __name__=="__main__":
    run(R2StudyVault(R2Config.from_environment()))
