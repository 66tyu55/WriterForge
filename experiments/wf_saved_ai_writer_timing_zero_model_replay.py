"""Verify genuine DeepSeek AI-writer look-back timing without NEW model calls.

Historical paid run 40070821134: first AI moment echoed prose+trace (invalid
as a decision); second asked for MOVE_ON with concrete literary reasons
but included exact inert "type":"json_object" wrapper. Re-read unchanged
provider model originals, do NOT substitute prompts, model choices or prose.
No model API keys, no independent literary success claim.
"""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import json

from writerforge.verified_flow import GroundedDraftPacket
from writerforge.v96_causal_turns import parse_turn_outline
from writerforge.writing_assist import (
    _ai_decides_when_to_revisit,SELF_EDIT_MOMENT_TOKENS,
)

ROOT=Path("wf_real_timing_original_artifact")
OUT=Path("wf_real_timing_offline_recheck")
EXPECTED={
    "02-SELF_BEAT_PLAN-original-model.json":
        "c6f73fccc3aa5d3594fc5e76ccdc931dba2e0f1ddc84e6efa412db56decace44",
    "03-PROSE_1-original-model.json":
        "284fbe3b9cdf614e69841d91f3080f15c29f8a00380ee91b2ddf8ea33c909d73",
    "04-AI_MOMENT_1-original-model.json":
        "ed46bdbc96fe5a300f0f91e5d7f15caa0cdf39feb4d29ca2a0fa92d09e0333f4",
    "05-PROSE_2-original-model.json":
        "8a3991bf3f6a47ea6d58cd979319148475d95134c355e099b67272309d5da22f",
    "06-AI_MOMENT_2-original-model.json":
        "e9a635c677a224b3d5ecf1c998d4922d9dbee96aecb16c3243bb418b2727fede",
}


def sha(raw):
    return sha256(raw).hexdigest()


def read_exact(name):
    if name not in EXPECTED:
        raise RuntimeError("WF_REPLAY_UNKNOWN_PRIVATE_SOURCE_FILE")
    content=(ROOT/name).read_bytes()
    if sha(content)!=EXPECTED[name]:
        raise RuntimeError("WF_REPLAY_TRUE_DEEPSEEK_ORIGINAL_CHANGED")
    return content.decode("utf8")


def main():
    OUT.mkdir(parents=True,exist_ok=False)
    beats=parse_turn_outline(
        read_exact("02-SELF_BEAT_PLAN-original-model.json"))
    if len(beats)!=2:
        raise RuntimeError("WF_REPLAY_ORIGINAL_TWO_BEATS_NOT_PRESERVED")
    proven=[]
    calls=0
    for index in (1,2):
        original=read_exact({
            1:"03-PROSE_1-original-model.json",
            2:"05-PROSE_2-original-model.json"}[index])
        response=read_exact({
            1:"04-AI_MOMENT_1-original-model.json",
            2:"06-AI_MOMENT_2-original-model.json"}[index])
        old=json.loads(original)
        source=old["prose"].strip()
        prompt="这是原真实 WF 小说的下一段源范围、已发生情节和人物可知边界。"
        packet=GroundedDraftPacket(
            scene_id="historical-model-original",project_id="wf-source-only",
            snapshot_id=1,evidence=(),craft_ids=(),prompt=prompt,
            prompt_sha256=sha256(prompt.encode("utf8")).hexdigest())
        local_calls=[]
        def replay_exact_saved_response(item,*,model,api_base,max_tokens):
            if max_tokens!=SELF_EDIT_MOMENT_TOKENS:
                raise RuntimeError("WF_REPLAY_WRITER_MOMENT_BUDGET_DRIFT")
            local_calls.append(1)
            return response
        choice=_ai_decides_when_to_revisit(
            raw=original,beat=beats[index-1],accepted=(),
            turn_packet=packet,ask_model=replay_exact_saved_response,
            directory=OUT/f"turn-{index:02d}-source-only")
        if len(local_calls)!=1:
            raise RuntimeError("WF_REPLAY_DID_NOT_CONSUME_EXACT_MODEL_ORIGINAL")
        calls+=len(local_calls)
        proven.append({
            "turn":index,"original_prose_sha256":sha(source.encode("utf8")),
            "unmodified_real_response_sha256":sha(response.encode("utf8")),
            "model_original_action":choice["decision"],
            "exact_literal_wrapper_recovered":choice["receipt"].get(
                "format_wrapper_type_only_removed",False),
            "model_was_asked_in_historical_paid_run":True,
            "any_new_provider_calls":0,
            "literary_quality_independently_verified":False,
            "source_text_was_not_revised_in_replay":True,
        })
    if proven[0]["model_original_action"]!="INVALID_SIGNAL":
        raise RuntimeError("WF_REPLAY_FIRST_TRUE_MODEL_ECHO_MUST_STAY_INVALID")
    if (proven[1]["model_original_action"]!="MOVE_ON" or
        not proven[1]["exact_literal_wrapper_recovered"]):
        raise RuntimeError("WF_REPLAY_SECOND_TRUE_WRITER_MOVE_ON_NOT_RECOVERED")
    report={
        "format":"wf.writer.real-original-timing-source-only-recheck.v1",
        "historical_live_run_id":40070821134,
        "new_model_provider_calls":0,
        "original_writer_response_replayed_count":calls,
        "original_first_failure_kept":True,
        "real_second_model_chose_no_deletion":True,
        "code_did_not_choose_delete_or_keep":True,
        "literary_quality_not_proven":True,
        "model_weights_changed":False,
        "canon_writes":0,
        "results":proven,
    }
    (OUT/"RECHECK.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True),
        encoding="utf8")
    print("WF_REAL_AI_TIMING_ZERO_PROVIDER_RECHECK "+json.dumps({
        "results":proven,"new_model_calls":0,"original_preserved":True,
    },ensure_ascii=False,separators=(",",":")),flush=True)


if __name__=="__main__":
    main()
