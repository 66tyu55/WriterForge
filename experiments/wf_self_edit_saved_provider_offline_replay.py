"""Replay the EXACT previously paid DeepSeek writer's original edit proposals.

No new model calls and no rewriting model outputs. Observed faulty offsets
(11/82 Unicode codepoints) are recomputed only when the model supplied a
UNIQUE verbatim original quote. V119 and V96 still guard each edit. Original
Actions evidence at #40068690550 is immutable and remains RED for those
initial offset failures. This rerun tests the host fix, not literary quality.
"""
from __future__ import annotations
from pathlib import Path
import hashlib,json
from writerforge.verified_flow import GroundedDraftPacket
from writerforge.writing_assist import _self_edit_one_turn
from writerforge.v96_causal_turns import (
    parse_turn_outline,check_turn,review_only_model_turn,
    V96CausalDraftError,
)

ROOT=Path("wf_old_self_edit_originals")
OUT=Path("wf_exact_quote_offline_selfedit_replay")
SHA={
    "02-SELF_BEAT_PLAN-original-model.json":
        "53b3eef77bc8289ebdd7a6066d7260537be615db9e3e3c3cfee517ce4bf159d3",
    "03-PROSE_1-original-model.json":
        "49a73becd8b36cc7b593f068b2f474d6d82d2853d613f33fa46333e0f7a2bb6d",
    "04-SELF_EDIT_1-original-model.json":
        "445110058ef65c99b5c1453286a3043bdbcd2f01994ea23385d9f8e07d692e70",
    "05-PROSE_2-original-model.json":
        "3e7c7505b3a2a1fb55745b502399da9adcacc7b497afe1bda0795c7c9a203776",
    "06-SELF_EDIT_2-original-model.json":
        "1728db7327959b5aadfa40743b75ae4fe2064ccf4ee2e234bab60ea93c31b3e0",
    "PRIVATE_WRITER_DRAFTS_01/first-original.md":
        "ef55398422056a0ce209fe537c599216f1b6c2b757f70e0d7537203e173f1060",
    "PRIVATE_WRITER_DRAFTS_02/first-original.md":
        "a5b5992a51ff90320fe8b2196757db8c256cd6a908f4ab76392e58d7e86ecca3",
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def original(name):
    raw=(ROOT/name).read_bytes()
    if name not in SHA or sha(raw)!=SHA[name]:
        raise RuntimeError("WF_SELF_EDIT_OLD_ORIGINAL_SHA_MISMATCH")
    return raw.decode("utf8")


def main():
    OUT.mkdir(parents=True,exist_ok=False)
    beats=parse_turn_outline(original(
        "02-SELF_BEAT_PLAN-original-model.json"))
    if len(beats)!=2:
        raise RuntimeError("WF_SELF_EDIT_FROZEN_PLAN_CHANGED")
    accepted=[]
    results=[]
    revisions=[
        ("03-PROSE_1-original-model.json",
         "04-SELF_EDIT_1-original-model.json",
         "PRIVATE_WRITER_DRAFTS_01/first-original.md"),
        ("05-PROSE_2-original-model.json",
         "06-SELF_EDIT_2-original-model.json",
         "PRIVATE_WRITER_DRAFTS_02/first-original.md"),
    ]
    for i,(name,proposal,source) in enumerate(revisions,1):
        old=original(name)
        actual=json.loads(old)
        old_source=original(source)
        if actual["prose"].strip()!=old_source:
            raise RuntimeError("WF_SELF_EDIT_ORIGINAL_SOURCE_TEXT_CHANGED")
        prompt="现有 WF 原模型作品与作者真实前史均须保留，按其真实已写原文自主复读。"
        packet=GroundedDraftPacket(
            scene_id="historical-source-replay",project_id="wf-test-self-editor",
            snapshot_id=1,evidence=(),craft_ids=(),prompt=prompt,
            prompt_sha256=hashlib.sha256(prompt.encode("utf8")).hexdigest())
        reply=original(proposal)
        asked=[]
        def old_saved_proposal_only(pkt,*,model,api_base,max_tokens):
            asked.append((model,api_base,max_tokens))
            return reply
        effective,receipt=_self_edit_one_turn(
            raw=old,beat=beats[i-1],accepted=tuple(accepted),
            project_id=packet.project_id,scene_id=packet.scene_id,
            turn_packet=packet,ask_model=old_saved_proposal_only,
            round_limit=1,call_allowance=1,
            directory=OUT/f"original-writer-turn-{i:02d}")
        if len(asked)!=1:
            raise RuntimeError("WF_SELF_EDIT_OFFLINE_REPLAY_MISSING_ONE_PROPOSAL")
        updated=json.loads(effective)["prose"].strip()
        (OUT/f"turn-{i:02d}-provisional-prose.md").write_text(
            updated,encoding="utf8")
        # Just like the real writing kernel, the next turn receives an
        # actually validated previous turn, not the author's presumed plan.
        try:
            evidence=check_turn(effective,beats[i-1],
                                mode="causal_guard",accepted=tuple(accepted),
                                max_prose_chars=1024)
        except V96CausalDraftError as error:
            evidence=review_only_model_turn(
                effective,beats[i-1],failure_code=str(error),
                accepted=tuple(accepted),max_prose_chars=1024)
        accepted.append(evidence)
        results.append({
            "turn":i,
            "original_sha256":sha(old_source.encode("utf8")),
            "final_sha256":sha(updated.encode("utf8")),
            "round_status":receipt["rounds"][0]["status"],
            "exact_old_proposal_replayed":True,
            "model_provider_calls_for_this_replay":0,
            "only_exact_unique_quote_recovered":bool(
                receipt["rounds"][0].get(
                    "source_offset_recovered_exactly")),
            "real_novel_source_rewritten_by_any_model_now":False,
            "new_literary_quality_proven":False,
            "causal_check":evidence["receipt"]["causal_check"],
        })
    output={
        "format":"wf.writer.real-old-proposal-source-only-replay.v1",
        "original_paid_source_run_id":40068690550,
        "original_paid_run_literary_edit_failures_preserved":True,
        "new_model_calls":0,
        "true_existing_provider_answers_used":True,
        "model_weight_training_claim":False,
        "canon_writes":0,"results":results,
    }
    (OUT/"RESULTS.json").write_text(
        json.dumps(output,ensure_ascii=False,indent=2,sort_keys=True),
        encoding="utf8")
    print("WF_SELF_EDIT_SOURCE_ONLY_REPLAY "+json.dumps({
        "results":results,"provider_calls":0,
        "original_red_artifact_untouched":True,
    },ensure_ascii=False,separators=(",",":")),flush=True)


if __name__=="__main__":
    main()
