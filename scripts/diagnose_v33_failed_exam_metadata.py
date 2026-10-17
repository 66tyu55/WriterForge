"""Read-only metadata diagnostics for V33 genuine failure; never model call."""
from __future__ import annotations
from writerforge.r2_storage import R2Config,R2StudyVault
from scripts.run_v33_repair_e2e import root_for_slot
import json
from hashlib import sha256

FAILURE_SHA="d6c7063023799cbea26159b28276c0a6eb9ff1e72b2f610b7c6279b1918ff7fb"

def run():
    store=R2StudyVault(R2Config.from_environment())
    if store.config.bucket!="writerforge-private-library":
        raise ValueError("PRIVATE_BUCKET_REQUIRED")
    root=root_for_slot(0)
    raw=store._get_small(root+"/failure-"+FAILURE_SHA+".json",22000)
    if sha256(raw).hexdigest()!=FAILURE_SHA:
        raise ValueError("PRIVATE_FAILURE_DIGEST_INVALID")
    doc=json.loads(raw)
    length=doc.get("safe_length_observation") or {}
    result={
        "stage":"V33_METADATA_ONLY_FAILURE_DIAGNOSTIC",
        "sha256":FAILURE_SHA,
        "failure_code":doc.get("failure_code"),
        "calls":doc.get("model_calls"),
        "finished_graders":doc.get("grader_models_finished"),
        "initial_length_state":length.get("initial"),
        "final_length_state":length.get("final"),
        "symmetric_revision_calls":length.get("symmetric_revision_calls"),
        "response_observation_roles":[x.get("role") for x in
                                      doc.get("safe_response_observations",[])],
        "prose_or_prompts_exposed":False,
        "new_model_calls":0,
    }
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return result
if __name__=="__main__":run()
