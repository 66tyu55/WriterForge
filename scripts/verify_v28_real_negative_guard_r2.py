"""Zero-model real R2 negative evidence -> opt-in context quarantine smoke test."""
from __future__ import annotations
from hashlib import sha256
import json

from writerforge.r2_storage import R2Config,R2StudyVault
from writerforge.reverse_cross_window_review import quarantine_pairs_from_verified_candidate
from writerforge.reverse_mechanism_boundary import source_paragraphs,guarded_selections
from scripts.import_v28_chapter2_regression_evidence_r2 import V6_TRIAL,trial_root

CANDIDATE_SHA="563b5b28591fc38748f26f1dbc89d175c2b7d64802eda02b0247a91eac87ba6f"

def run():
    cfg=R2Config.from_environment()
    if cfg.bucket!="writerforge-private-library":
        raise RuntimeError("EXPECTED_PRIVATE_R2")
    store=R2StudyVault(cfg)
    root=trial_root(V6_TRIAL,"chapter-2-contiguous-window-1-diagnostic-only")
    key=f"{root}/cross-window-candidates/{CANDIDATE_SHA}.json"
    raw=store._get_small(key,8192)
    if sha256(raw).hexdigest()!=CANDIDATE_SHA:
        raise RuntimeError("REAL_R2_NEGATIVE_CANDIDATE_HASH_MISMATCH")
    candidate=json.loads(raw)
    blocked=quarantine_pairs_from_verified_candidate(
        candidate,candidate_sha256=CANDIDATE_SHA)
    if len(blocked)!=1 or blocked[0][0]!=candidate["new_unit_sha256"]:
        raise RuntimeError("INVALID_SOURCE_SCOPED_BLOCK")
    paragraphs=source_paragraphs(
        "合成但不涉及小说具体情节的第一段。"*20+"\n"+
        "合成但不涉及小说具体情节的第二段。"*20)
    reply={"selections":[
        {"id":name,"evidence_ids":["P"+str(i)]}
        for i,name in enumerate(candidate["selected_mechanisms_after"])
    ]}
    picked,reason=guarded_selections(reply,paragraphs,
                                     source_window_sha256=candidate["new_unit_sha256"],
                                     quarantined_pairs=blocked)
    if picked or reason!="QUARANTINED_PREVIOUS_NEGATIVE_CONTEXT":
        raise RuntimeError("NEGATIVE_EXPERIMENT_NOT_QUARANTINED")
    older,older_reason=guarded_selections(
        reply,paragraphs,source_window_sha256=candidate["old_unit_sha256"],
        quarantined_pairs=blocked)
    if len(older)!=len(reply["selections"]) or older_reason!="UNVERIFIED_EXPERIMENT_CANDIDATE":
        raise RuntimeError("NEW_NEGATIVE_DESTROYED_PRIOR_FUNCTIONALITY")
    out={"stage":"V28_REAL_R2_NEGATIVE_MECHANISM_QUARANTINE_VERIFIED",
         "private_candidate_sha256":CANDIDATE_SHA,
         "blocked_only_at_new_source_sha256":candidate["new_unit_sha256"],
         "selected_mechanisms":candidate["selected_mechanisms_after"],
         "prior_source_still_allows_experiment":True,
         "old_source_literary_promotion":False,
         "new_source_literary_promotion":False,
         "second_curriculum_window":"LOCKED",
         "model_calls":0,"raw_source_or_draft_downloaded":False}
    print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    return out

if __name__=="__main__":
    run()
