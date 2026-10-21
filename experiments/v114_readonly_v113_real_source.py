"""V114 real-source read-only cold calibration against V113 WF 951-char story.

The source is the ORIGINAL WF-generated xuanhuan manuscript already sealed
on V113 R2. NO new writing, model, R2 write or other people's novel books.
Validates real sword-tassel anchors and both candidate state engines.
"""
from __future__ import annotations
import json,os
from hashlib import sha256

from experiments.v113_github_r2_cas import GitHubS3CAS
from writerforge.v114_continuity_memory import literal_item_continuity
from writerforge.v114_external_story_state import (
    external_temporal_step,temporal_prompt,
)

V113_MANIFEST="4dd25ee40a90eec7ff9e67b184720903a145df9f54918f4eb68ea52f3a3af67f"
EXPECTED_PROSE_SHA="339b2b1cab1e4895ed73d4e8ef73ed0b51c6adb832149cd097c35b0ec9b585f7"

def need(v,code):
    if not v:raise RuntimeError(code)

def run():
    need(not os.getenv("DEEPSEEK_API_KEY") and not os.getenv("DEEPSEEK"),
         "WF114_READ_ONLY_NEVER_USE_MODEL")
    cas=GitHubS3CAS()
    manifest=json.loads(cas._get_content(V113_MANIFEST))
    need(manifest["format"]=="wf.eval.v113.three-arm-original-model-experiment"
         and manifest["arms"][0]["arm"]=="WF_SINGLE"
         and manifest["arms"][0]["status"]=="WRITTEN"
         and manifest["arms"][0]["real_codepoints"]==951,
         "WF114_V113_OLD_WF_MANIFEST_NOT_GENUINE")
    original=cas._get_content(
        manifest["arms"][0]["prose_private_cas_sha256"])
    need(sha256(original).hexdigest()==EXPECTED_PROSE_SHA,
         "WF114_HISTORICAL_PROSE_SHA_CHANGED")
    source=original.decode("utf8","strict")
    need(len(source)==951 and source.count("剑穗")>=2,
         "WF114_OLD_WF_STORY_NOT_RESTORED")
    cast=("叶青梧","沈渡")
    native=literal_item_continuity(source,cast=cast)
    external=external_temporal_step(source,cast=cast)
    native_risks=[e for e in native["risks"]
                  if e["kind"]=="ITEM_OWNER_CHANGE_WITHOUT_TRANSFER"
                  and e["item"]=="剑穗"]
    oss_risks=[e for e in external["reducer_result"].get("risks",[])
               if e["kind"]=="UNPROVEN_ITEM_TRANSFER"]
    need(native_risks and oss_risks,
         "WF114_REAL_V113_SWORD_TASSEL_CHANGE_NOT_CAUGHT")
    need("沈渡" in str(external["reducer_result"]["candidate_state"]) and
         "索钩" in temporal_prompt(external) and
         external["reducer_result"]["verified_events"]>=1 and
         external["semantic_truth_verified"] is False and
         external["canon_writes"]==0,
         "WF114_EXTERNAL_ORIGINAL_ITEM_MEMORY_NOT_CONSERVATIVE")
    print(json.dumps({
        "status":"WF114_V113_REAL_WF_951_CHAR_SOURCE_STATE_AUDIT_PASS",
        "previous_WF_prose_sha256":EXPECTED_PROSE_SHA,
        "full_original_prose_read_from_R2_not_logged":True,
        "original_WF_prose_characters":len(source),
        "native_sword_tassel_candidate_risks":len(native_risks),
        "external_unproven_transfer_rejections":len(oss_risks),
        "last_confirmed_candidate_carrier":"沈渡",
        "magic_or_other_items_semantically_proven":False,
        "AI_model_calls":0,"R2_writes":0,
        "novel_studio_original_temporal_reducer_used":True,
        "formal_literary_improvement_verified":False,
        "V113_original_and_failures_unchanged":True,
    },ensure_ascii=False,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(run())
