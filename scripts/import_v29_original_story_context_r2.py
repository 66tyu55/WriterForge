"""Zero-model import of three true random ORIGINAL story context observations.

Requires the immutable real private R2 aggregate saved on 2026-10-17.
No calls to Discovery; no original book or generated drafts downloaded.
All three observations are unverified *candidates*, never active rules.
"""
from __future__ import annotations
from hashlib import sha256
import json
from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.reverse_story_context_evidence import derive_story_context_candidates
from scripts.run_wf_three_random_openings_v10 import PREFIX

AGGREGATE_SHA="2b2aea9c6563b402d0795fc1812e09d5d066e56a4ab51be045ddeabaae00b55d"

def import_candidates(store):
    if store.config.bucket!="writerforge-private-library":
        raise ValueError("ONLY_PRIVATE_R2_ALLOWED")
    source_key=f"{PREFIX}/three-original-openings-audit/{AGGREGATE_SHA}.json"
    raw=store._get_small(source_key,24000)
    if sha256(raw).hexdigest()!=AGGREGATE_SHA:
        raise ValueError("ORIGINAL_R2_AGGREGATE_SHA_MISMATCH")
    doc=json.loads(raw)
    candidates=derive_story_context_candidates(doc,report_sha256=AGGREGATE_SHA)
    payload=_canonical(candidates)
    h=sha256(payload).hexdigest()
    dest=f"{PREFIX}/unreviewed-story-context-candidates/{h}.json"
    store._put_small_immutable(dest,payload,h)
    fresh=store._get_small(dest,8192)
    if fresh!=payload or sha256(fresh).hexdigest()!=h:
        raise ValueError("PRIVATE_STORY_CANDIDATE_FRESH_READBACK_FAILURE")
    safe={
        "stage":"WRITERFORGE_V29_REAL_STORY_CONTEXT_CANDIDATES_R2_VERIFIED",
        "source_aggregate_sha256":AGGREGATE_SHA,
        "candidate_sha256":h,
        "model_effects_by_scenario":[
            {"story_id":x["story_id"],"raw_delta":x["model_effect"],
             "status":x["candidate_status"]}
            for x in candidates["model_only_contextual_observations"]
        ],
        "same_pair_three":candidates["same_mechanism_pair_all_three"],
        "positive_and_negative":candidates["positive_and_negative_same_pair"],
        "new_rules_promoted":False,
        "original_source_or_drafts_downloaded":False,
        "paid_model_calls":0,
        "first_window":"NOT_PASSED",
        "second_window":"LOCKED",
    }
    print(json.dumps(safe,ensure_ascii=False,sort_keys=True))
    return safe

if __name__=="__main__":
    import_candidates(R2StudyVault(R2Config.from_environment()))
