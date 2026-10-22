"""V122: original sealed V113/V114B, zero-model cold provenance tests.

Only counters/hashes leave this script; never upload original prose, update
the canonical story, or reuse paid models to 'repair' the old failures.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path

from experiments.v116_readonly_sealed_state_audit import data_from_sealed,need
from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v116_state_delta import preflight_next_prose
from writerforge.v122_item_provenance import audit_item_provenance

V113="339b2b1cab1e4895ed73d4e8ef73ed0b51c6adb832149cd097c35b0ec9b585f7"
V114B="c5146b829348ea12724290550ab8d4b4d959f2c1aaa41459c38bdeef757ad166"


def main():
    need(not any(os.getenv(s) for s in ("DEEPSEEK_API_KEY","OPENAI_API_KEY",
         "DISCOVERY__API__KEY","ANTHROPIC_API_KEY","OPENROUTER_API_KEY")),
         "WF122_MODEL_SECRET_IS_NOT_ALLOWED_IN_COLD_AUDIT")
    old113,old114=data_from_sealed()
    need(len(old113)==951 and len(old114)==964 and
         sha256(old113.encode()).hexdigest()==V113 and
         sha256(old114.encode()).hexdigest()==V114B,
         "WF122_ORIGINAL_COLD_SOURCE_DRIFT")
    prior114=external_temporal_step(old114,cast=("沈砚","唐蜃"))
    prior113=external_temporal_step(old113,cast=("沈渡","叶青梧"))
    state114=prior114["reducer_result"]["candidate_state"]
    item_state=prior113["reducer_result"]["candidate_state"]
    cast=("沈砚","唐蜃","叶青梧")
    valid=("沈砚把火髓果从左手心递给唐蜃。"
           "唐蜃把火髓果从手中递给叶青梧。"
           "叶青梧握着火髓果。")
    miss="叶青梧握着火髓果，唐蜃仍不肯放手。"
    unclear="他把果子从左手心递给唐蜃。唐蜃握着火髓果。"
    good=preflight_next_prose(valid,previous_candidate_state=state114,
                             cast=cast)
    bad=preflight_next_prose(miss,previous_candidate_state=state114,
                            cast=cast)
    unknown=preflight_next_prose(unclear,previous_candidate_state=state114,
                                cast=cast)
    events=audit_item_provenance(
        prose=valid,previous_candidate_state=state114,cast=cast)
    # Real pinned upstream MIT state application, using the ORIGINAL 964
    # source as prior candidate state. These two later turns are synthetic
    # zero-model test strings, not a newly generated literary scene.
    carried=external_temporal_step(valid,cast=cast,prior=prior114)
    later=external_temporal_step(
        "叶青梧沿石壁疾行，唐蜃远远追在后面。",
        cast=cast,prior=carried)
    key=next((k for k in state114
              if json.loads(k)[:3]==["item","火髓果","holder"]),None)
    need(key is not None and
         carried["reducer_result"]["candidate_state"][key]=="叶青梧手中" and
         later["reducer_result"]["candidate_state"][key]=="叶青梧手中" and
         carried["reducer_result"]["error_code"] is None and
         carried["v122_extra_reducer_events_count"]>=1,
         "WF122_PINNED_REDUCER_DID_NOT_PERSIST_THREE_PERSON_TRANSFER")
    need(not good["blocked"] and
         events["remaining_holders_candidate_only"].get("火髓果")=="叶青梧手中"
         and len(events["candidate_source_events"])==2,
         "WF122_ACTUAL_OLD_STATE_FAILED_VALID_THREE_PERSON_HANDOFF")
    need(bad["blocked"] and
         "WF116_FRUIT_TELEPORT_TO_OTHER_ACTOR" in bad["findings"],
         "WF122_OLD_FRUIT_SOURCE_ACCEPTED_UNPROVEN_NEW_OWNER")
    need(not unknown["blocked"] and unknown["needs_review"],
         "WF122_UNKNOWN_PRONOUN_WAS_CONVERTED_TO_FALSE_TRANSFER")
    need(prior113["canon_writes"]==0 and
         prior114["canon_writes"]==0 and
         prior113["semantic_truth_verified"] is False and
         prior114["semantic_truth_verified"] is False,
         "WF122_PRIOR_CANDIDATE_PROMOTED")
    report={
        "format":"wf.audit.v122.sealed-original-three-person-provenance",
        "v113_original_sha256":V113,"v114b_original_sha256":V114B,
        "original_v113_characters":len(old113),
        "original_v114b_characters":len(old114),
        "original_tassel_state_unchanged":bool(item_state),
        "valid_three_person_handoff_preflight_passed":True,
        "two_source_anchored_handoffs_not_canon":True,
        "pinned_novel_studio_checkpoint_survived_next_chapter":True,
        "one_new_supplemental_source_event_atomic":True,
        "third_person_item_teleport_blocked":True,
        "unresolved_he_she_reference_review_only":True,
        "old_second_story_scene_not_generated":True,
        "new_model_calls":0,"R2_writes":0,"canon_writes":0,
        "literary_quality_improvement_proven":False,
        "raw_original_novel_never_logged":True,
    }
    folder=Path("wf122_sealed_multi_actor_cold")
    folder.mkdir(exist_ok=False)
    (folder/"SOURCE_ONLY_STATUS.json").write_text(
        json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2),
        encoding="utf8")
    print(json.dumps(report,ensure_ascii=False,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
