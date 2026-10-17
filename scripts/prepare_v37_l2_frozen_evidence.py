"""V37 strict L2 foreshadowing investigation of immutable V35 evidence.

No paid calls; this script is the *examiner*, not a literary judge.
It verifies actual original source quote, candidate L2, prewrite binding,
first draft and revision, then persists a PRE-REVIEW evidence packet.
Actual source/prose/prewrite are PRIVATE R2 only. Public logs show IDs,
locations, digests and fault-classification readiness, never actual text.
"""
from __future__ import annotations
import json
import re
from hashlib import sha256

from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.v35_observable_trace import (
    sha,canonical,validate_read,validate_lessons,validate_plan,
    validate_draft,validate_after
)
from scripts.run_v35_xiyouji_decision_trace import restore_stage
from scripts.debug_v36_xiyouji_learning_to_writing import (
    EXPECTED_ORIGINAL_SHA, AFTER_SHA, AFTER_EXAMINER_SHA,
    _after_key,_read_exact,analyze as audit_v36,
)

ROOT="writerforge/v1/examiner/v37-l2-foreshadowing-frozen"
CAP=26000
SEGMENT_MAX=70
MAX_ANCHORS=48

class L2BreakpointError(ValueError):
    pass

def ensure(ok:bool,code:str)->None:
    if not ok:raise L2BreakpointError(code)

def _clip_sentences(story:str,prefix:str)->list[dict]:
    """Host-made, exact substrings; covers entire text incl last segment."""
    out=[]
    # Split at sentence punctuation, but retain original text offsets.
    boundaries=[m.end() for m in re.finditer(r"[。！？!?；;]",story)]
    if not boundaries or boundaries[-1]!=len(story):
        boundaries.append(len(story))
    start=0
    for end in boundaries:
        raw=story[start:end]
        # Long sentences are cut into fixed short exact substrings.
        for pos in range(start,end,SEGMENT_MAX):
            local=story[pos:min(pos+SEGMENT_MAX,end)]
            if not local.strip():continue
            out.append({
                "id":f"{prefix}{len(out)+1:02d}",
                "offset":pos,"end":min(pos+SEGMENT_MAX,end),
                "text":local,
                "sha256":sha(local),
            })
        start=end
    ensure(1<=len(out)<=MAX_ANCHORS,"TOO_MANY_UNBOUNDED_DRAFT_ANCHORS")
    ensure(all(story[x["offset"]:x["end"]]==x["text"] for x in out),
           "ANCHOR_NOT_IN_GENUINE_DRAFT")
    # Every non-whitespace character must be covered, including last sentence.
    positions=set()
    for a in out:positions.update(range(a["offset"],a["end"]))
    ensure(all(not c.strip() or i in positions for i,c in enumerate(story)),
           "DRAFT_ANCHOR_COVERAGE_GAP")
    return out

def _history(vault):
    parent=None
    steps=[]
    for i,expected in enumerate(EXPECTED_ORIGINAL_SHA):
        saved=restore_stage(vault,i,parent)
        ensure(saved is not None and saved[1]==expected,
               "V35_ORIGINAL_STAGE_SHA_MISMATCH")
        steps.append(saved[0])
        parent=expected
    return steps

def verified_material(vault)->dict:
    ensure(vault.config.bucket=="writerforge-private-library","PRIVATE_R2_REQUIRED")
    # Require V36's previous all-source and postwrite verification first.
    baseline=audit_v36(vault,persist=False)
    ensure(baseline["transfer_trace"]["source_linked_prewrite_angles"]==
           ["foreshadowing"] and
           baseline["transfer_trace"]["source_linked_angles_missing_postwrite_evidence"]==
           ["foreshadowing"],"L2_MISSING_POSTWRITE_COVERAGE_NOT_GROUNDED")
    steps=_history(vault)
    original,reading,learned,prewrite,first,revision=[x["payload"] for x in steps]
    windows={int(i):v for i,v in original["actual_model_read_windows"].items()}
    read=validate_read({"observations":reading["observations"]},windows)
    candidate=validate_lessons({
        "lessons":[{k:v for k,v in row.items() if k!="id"}
                   for row in learned["lessons"]]
    },len(read["observations"]))
    ensure(candidate["lessons"]==learned["lessons"],"LESSON_SOURCE_LINK_CHANGED")
    l2=next((x for x in candidate["lessons"] if x["id"]=="L2"),None)
    ensure(l2 is not None,"L2_LESSON_MISSING")
    index=l2["source_observation_index"]
    obs=reading["observations"][index]
    # V35 validated the authentic source quote after removing whitespace
    # induced by source line wrapping. Enforce that SAME historic contract,
    # never reject a verified original only because of typography.
    compact_quote="".join(obs["source_quote"].split())
    compact_source="".join(windows[obs["chapter"]].split())
    ensure(compact_quote in compact_source,
           "L2_SOURCE_QUOTE_NOT_IN_ORIGINAL")
    plan=validate_plan({"decisions":prewrite["plan"]["decisions"]},{"L1","L2"})
    selected=[x for x in plan["decisions"] if x["learned_lesson_id"]=="L2"]
    ensure(len(selected)==1 and selected[0]["angle"]=="foreshadowing",
           "L2_NOT_UNIQUELY_BOUND_TO_FORESHADOWING")
    first_story=first["body"]
    final_story=(revision["edited_draft"]["body"] if revision["edited"]
                 else first_story)
    ensure(validate_draft(first_story,windows)==first,
           "FIRST_DRAFT_WAS_REWRITTEN")
    final_proof=validate_draft(final_story,windows)
    ensure(final_proof["body_sha256"]==revision["final_body_sha256"],
           "FINAL_DRAFT_WAS_REWRITTEN")
    reviewed=_read_exact(vault,_after_key("valid-retrospective",AFTER_SHA),
                         AFTER_SHA,36000)
    audit=_read_exact(vault,_after_key("append-only-examiner-audit",
                                      AFTER_EXAMINER_SHA),
                      AFTER_EXAMINER_SHA,36000)
    after=validate_after({"checks":reviewed["checks"],
                          "biggest_mistake":reviewed["biggest_mistake"]},
                         final_story,plan)
    ensure(not any(x["angle"]=="foreshadowing" for x in after["checks"]),
           "L2_ALREADY_REVIEWED_UNEXPECTEDLY")
    ensure(reviewed["original_frozen_final_draft_sha256"]==sha(final_story)
           and audit["new_visible_retrospective_record_sha256"]==AFTER_SHA,
           "REVIEW_REFERENCE_IDENTITY_FAILED")
    return {
        "reference_source_sha":EXPECTED_ORIGINAL_SHA[0],
        "reference_read_sha":EXPECTED_ORIGINAL_SHA[1],
        "reference_lesson_sha":EXPECTED_ORIGINAL_SHA[2],
        "reference_prewrite_sha":EXPECTED_ORIGINAL_SHA[3],
        "reference_draft_sha":EXPECTED_ORIGINAL_SHA[4],
        "reference_revision_sha":EXPECTED_ORIGINAL_SHA[5],
        "candidate_l2":l2,
        "origin_observation":obs,
        "actual_chapter_source":windows[obs["chapter"]],
        "source_quote_offset":compact_source.find(compact_quote),
        "foreshadowing_plan":selected[0],
        "first_draft":first_story,
        "final_draft":final_story,
        "previous_checked_angles":[x["angle"] for x in after["checks"]],
        "first_anchors":_clip_sentences(first_story,"F"),
        "final_anchors":_clip_sentences(final_story,"R"),
        "no_semantic_authority_from_host":True,
    }

def _private_packet(material:dict)->dict:
    return {
        "format":"writerforge.v37-l2-source-to-draft-evidence.v1",
        "references":{
            k:v for k,v in material.items()
            if k.startswith("reference_")},
        "source_observation_index":material["candidate_l2"]["source_observation_index"],
        "original_source_quote_sha256":sha(material["origin_observation"]["source_quote"]),
        "source_quote_offset":material["source_quote_offset"],
        "candidate_l2":material["candidate_l2"],
        "source_observation":material["origin_observation"],
        "prewrite_foreshadowing_decision":material["foreshadowing_plan"],
        "first_draft_anchors":material["first_anchors"],
        "revision_anchors":material["final_anchors"],
        "first_draft_sha256":sha(material["first_draft"]),
        "final_draft_sha256":sha(material["final_draft"]),
        "previously_reviewed_angles":material["previous_checked_angles"],
        "missing_review_angle":"foreshadowing",
        "lesson_transfer_not_proven":True,
        "original_history_not_modified":True,
        "model_calls":0,
        "official_skill_promoted":False,
    }

def prepare(vault,*,persist=True)->dict:
    material=verified_material(vault)
    packet=_private_packet(material)
    blob=canonical(packet)
    ensure(len(blob)<=CAP,"PRIVATE_L2_PACKET_TOO_LARGE")
    digest=sha(blob)
    if persist:
        path=f"{ROOT}/private-snapshots/{digest}.json"
        vault._put_small_immutable(path,blob,digest)
        ensure(vault._get_small(path,CAP)==blob,
               "PRIVATE_L2_PACKET_R2_FRESH_READBACK_FAILED")
    result={
        "stage":"V37_L2_FROZEN_EVIDENCE_READY_ZERO_MODEL",
        "packet_sha256":digest,
        "private_snapshot_saved":bool(persist),
        "actual_source_observation_index":packet["source_observation_index"],
        "source_chapter":material["origin_observation"]["chapter"],
        "source_quote_offset":material["source_quote_offset"],
        "prewrite_angle":"foreshadowing",
        "first_draft_characters":len(material["first_draft"]),
        "final_draft_characters":len(material["final_draft"]),
        "first_draft_evidence_anchor_count":len(material["first_anchors"]),
        "final_draft_evidence_anchor_count":len(material["final_anchors"]),
        "same_candidate_l2_in_prewrite":True,
        "after_draft_l2_evidence_missing":True,
        "candidate_l2_semantics_verified":False,
        "writing_skill_promoted":False,
        "model_calls":0,
    }
    return result

if __name__=="__main__":
    print(json.dumps(prepare(R2StudyVault(R2Config.from_environment())),
                     ensure_ascii=False,sort_keys=True))
