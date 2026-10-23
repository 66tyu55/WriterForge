"""Causally tighter WF literary A/B: SAME real first-turn model prose.

The optional source-progression cue is only used on turn two, so the old
two-independent-first-turn A/B cannot attribute whole-scene differences to
that cue. This test reuses a real prior DeepSeek model first-turn answer
byte-for-byte in BOTH arms, freezes the same previous source and two plans,
and asks DeepSeek Flash for the NEXT turn once per arm.

Not a new original first turn, no fictional first-turn mocks. Source text and
original plan bytes are SHA-pinned from live run 39968891775. Maximum two
new provider prose calls per genre, six calls total, no retries, no canon/R2
writes. Old failed horror original remains failed in historical evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

from experiments import wf_real_self_scene_diagnostics as diag
from experiments import wf_source_progression_ab as ab
from experiments import wf_holdout_three_fresh_literary_genres as hold
from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget
from writerforge.v96_causal_turns import parse_turn_outline
from writerforge.writing_assist import _normalize_optional_model_craft_labels
from writerforge.v114_external_story_state import require_external_runtime

ORIGINAL_ROOT=Path("wf_prior_holdout_sources")
TARGET=Path("wf_same_first_turn_blind_results")
SOURCE_RUN=39968891775
EXACT_SHA={
    "plot":{
        "original-CHAPTER_PLAN-model.json":"e65dcd8d665a6c46a17a970a388c4f4b692d9208cd5aefbd45e1dcc7012d2d6c",
        "original-SELF_BEAT_PLAN-model.json":"4f3e81c0bd799fcaec0b39740eba1d125b90b087218ff760efa88a85af42e616",
        "W1/original-decoded-PROSE_1.json":"6898373890237eaf1ce297e71115d7544ac65d2247feaf91e1b4048c094c5aae",
    },
    "climax":{
        "original-CHAPTER_PLAN-model.json":"8c688e74e798a194246ab560f3e692f751513ebc80056fbdb7b8a371c9c5da40",
        "original-SELF_BEAT_PLAN-model.json":"4b0a883a3b2143724d8b0d3bec06bdf57936b64a23fd856a8a1c5d66219c6d8d",
        "W1/original-decoded-PROSE_1.json":"204fb8f96bfb8d91e45533f996037fe7774ff3b42c8736bbdfef6dade2f75e39",
    },
    "horror":{
        "original-CHAPTER_PLAN-model.json":"08cc15cbc55c68746fe6a38ea7b5b58f8a209dfecb97839bbd152bff3c9244f3",
        "original-SELF_BEAT_PLAN-model.json":"7494db54d3e236f4e1cdcce9587fc97f294f5793495605700850815589d2e7ff",
        "W1/original-decoded-PROSE_1.json":"9ffd93e5b323e7fd176ac9db4e385aee3d4a426dd7b4b4da0e1cbf92f63d1897",
    },
}
MODES=("baseline","source_progression")
MAX_REAL_PROVIDER_CALLS=2
PER_CALL_TOKENS=1450
OUTPUT_LIMIT=2900


def sha(data):
    return hashlib.sha256(
        data.encode("utf8") if type(data) is str else data).hexdigest()


def exact_file(genre,relative):
    if genre not in EXACT_SHA or relative not in EXACT_SHA[genre]:
        raise RuntimeError("WF_SHARED_TURN_PROVENANCE_UNKNOWN_FILE")
    raw=(ORIGINAL_ROOT/genre/relative).read_bytes()
    if sha(raw)!=EXACT_SHA[genre][relative]:
        raise RuntimeError("WF_SHARED_TURN_PROVENANCE_BYTES_CHANGED")
    return raw.decode("utf8")


class SharedRealFirstTurn:
    """Replay FIRST genuine provider answer; call provider only for SECOND."""
    def __init__(self,original,model):
        self.original=original
        self.model=model
        self.called=0
        self.replay_count=0
        self.live_count=0

    @property
    def last_response_format_recovery(self):
        return self.model.last_response_format_recovery

    @property
    def _on_response_wire(self):
        return self.model._on_response_wire

    @_on_response_wire.setter
    def _on_response_wire(self,callback):
        self.model._on_response_wire=callback

    def ask_json(self,*,role,system,user,max_tokens):
        if role!="self_scene_writing" or max_tokens!=PER_CALL_TOKENS:
            raise RuntimeError("WF_SHARED_TURN_UNEXPECTED_PROVIDER_REQUEST")
        self.called+=1
        if self.called==1:
            self.replay_count+=1
            # Do not mutate the shared original.
            return json.loads(json.dumps(self.original,ensure_ascii=False))
        if self.called!=2:
            raise RuntimeError("WF_SHARED_TURN_CALLS_OUT_OF_BOUNDS")
        self.live_count+=1
        return self.model.ask_json(
            role=role,system=system,user=user,max_tokens=max_tokens)


def main(genre):
    if genre not in hold.CASES:
        raise RuntimeError("WF_SHARED_TURN_GENRE_NOT_PREDECLARED")
    if not os.getenv("DEEPSEEK_API_KEY"):
        raise RuntimeError("WF_SHARED_TURN_EXISTING_PROVIDER_KEY_MISSING")
    require_external_runtime()
    diag.CASES[genre]=hold.CASES[genre]
    assert diag.CASES is ab.CASES
    ab.TARGET=TARGET
    root=TARGET/genre
    root.mkdir(parents=True,exist_ok=False)
    plan=exact_file(genre,"original-CHAPTER_PLAN-model.json")
    beat_raw=exact_file(genre,"original-SELF_BEAT_PLAN-model.json")
    beat,craft_note=_normalize_optional_model_craft_labels(beat_raw)
    if len(parse_turn_outline(beat))!=2:
        raise RuntimeError("WF_SHARED_TURN_FROZEN_BEATS_INVALID")
    original=json.loads(exact_file(
        genre,"W1/original-decoded-PROSE_1.json"))
    if set(original)!={"prose","trace"} or not original["prose"]:
        raise RuntimeError("WF_SHARED_TURN_NOT_REAL_SOURCE_PROSE")
    shared_original_prose_sha=sha(original["prose"].strip())
    first_order=(MODES if int(sha(
        genre+"|same-first-pair-order")[0],16)%2==0 else MODES[::-1])
    budget=FlashBudget(
        max_calls=MAX_REAL_PROVIDER_CALLS,
        max_reserved_output_tokens=OUTPUT_LIMIT,
        max_total_tokens=150000)
    model=DeepSeekFlashModel(budget=budget,timeout_seconds=120)
    plans={"model_plan":plan,"model_beats":beat,
           "model_optional_craft_recovery":craft_note}
    results={}
    start=time.monotonic()
    try:
        for arm,mode in zip(("W1","W2"),first_order):
            calls=[]
            shared=SharedRealFirstTurn(original,model)
            row=ab._runner(
                genre,mode=mode,blind_id=arm,
                plans=plans,root=root,client=shared,calls=calls)
            # Each arm replays a genuine old DeepSeek original once and
            # sends exactly ONE new request only for turn 2.
            if shared.called!=2 or shared.replay_count!=1 or shared.live_count!=1:
                raise RuntimeError("WF_SHARED_TURN_REAL_CALL_COUNT_UNTRUSTED")
            generated_path=root/arm/"original-decoded-PROSE_1.json"
            if sha(generated_path.read_text("utf8"))!=sha(
                json.dumps(original,ensure_ascii=False,separators=(",",":"))):
                raise RuntimeError("WF_SHARED_TURN_FIRST_PROSE_HAS_DRIFTED")
            row["new_provider_requests"]=1
            row["replayed_real_prior_provider_response"]=1
            results[arm]=row
            prior_evidence=root/arm/"scene_evidence.json"
            if prior_evidence.exists():
                report=json.loads(prior_evidence.read_text("utf8"))
                report.update({
                    "new_provider_requests":1,
                    "replayed_original_first_turn":True,
                    "shared_prior_prose_sha256":shared_original_prose_sha,
                    "only_second_turn_changed":True,
                })
                prior_evidence.write_text(json.dumps(
                    report,ensure_ascii=False,indent=2,sort_keys=True),
                    encoding="utf8")
        if budget.calls_reserved!=2:
            raise RuntimeError("WF_SHARED_TURN_EXCESS_NEW_PROVIDER_CALLS")
        # The old A/B had DIFFERENT first-turn samples across arms; this
        # experiment fixes that confound, but model sampling still varies.
        texts=[]
        for arm in ("W1","W2"):
            file=root/arm/"original-complete-candidate.md"
            content=(file.read_text("utf8") if file.exists()
                     else "[NO COMPLETE CANDIDATE]")
            texts.append((arm,content))
        (root/"BLIND_PAIR.md").write_text(
            "# Shared first-turn source-only A/B ("+genre+")\n\n"+
            "W1/W2 have identical original DeepSeek first-turn prose. "
            "Only the second-turn cue differs; labels remain hidden.\n\n"+
            "## First-turn source (same both arms)\n"+
            original["prose"].strip()+
            "".join("\n\n## "+arm+"\n"+body
                    for arm,body in texts),
            encoding="utf8")
        fair=(all(x["status"]=="COMPLETE_UNACCEPTED_REAL_WF_CANDIDATE"
                  for x in results.values()) and budget.calls_reserved==2)
        summary={
            "format":"wf.experiment.shared-real-first-turn-literary-ab.v1",
            "genre":genre,"source_run":SOURCE_RUN,
            "original_first_turn_prose_sha256":shared_original_prose_sha,
            "same_first_turn_json_and_both_wf_prompts":True,
            "old_plans_are_from_actual_model_not_author_prewrites":True,
            "source_genre_has_new_cast":True,
            "actual_new_provider_calls":budget.calls_reserved,
            "maximum_new_provider_calls":2,"no_retries":True,
            "pair_generated":fair,
            "blind_results":{
                arm:{"status":row["status"],"han_chars":row.get("han_chars"),
                     "trace_review_count":len(row.get(
                         "model_trace_review_failures",[])),
                     "source_length_review_count":row.get(
                         "unified_source_length_review_count")}
                for arm,row in results.items()},
            "literary_quality_proven":False,
            "old_horror_run_was_not_overwritten":True,
            "no_canon_or_railway":True,
            "model_usage":budget.public_receipt(),
        }
        (root/"PAIR_STATUS.json").write_text(
            json.dumps(summary,ensure_ascii=False,indent=2,
                       sort_keys=True),encoding="utf8")
        (root/"UNBLIND_MAPPING.json").write_text(
            json.dumps({"W1":first_order[0],"W2":first_order[1]},
                       sort_keys=True,indent=2),encoding="utf8")
        print("WF_SHARED_TURN_AB_RESULT "+json.dumps({
            "genre":genre,"status":"PAIRED" if fair else "INCOMPLETE",
            "new_provider_calls":budget.calls_reserved,
            "anonymous_results":summary["blind_results"],
            "model_quality_not_independently_verified":True,
        },ensure_ascii=False),flush=True)
        return fair
    except Exception as exc:
        message=str(exc)
        if not re.fullmatch(r"WF_[A-Z0-9_:]{5,160}",message):
            message=type(exc).__name__+":SHARED_TURN_NO_RETRY"
        error={
            "status":"SOURCE_AB_FAILED_NO_AUTO_RETRY",
            "code":message,
            "genre":genre,
            "actual_new_provider_calls":budget.calls_reserved,
            "original_replayed_not_model_generated":True,
        }
        (root/"FAILURE.json").write_text(
            json.dumps(error,ensure_ascii=False,indent=2),
            encoding="utf8")
        print(json.dumps(error,ensure_ascii=False),flush=True)
        return False


if __name__=="__main__":
    main(os.getenv("WF_SHARED_GENRE",""))
