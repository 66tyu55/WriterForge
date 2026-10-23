"""Replay EXACT past DeepSeek model replies through corrected WriterForge.

Zero model requests, no new writing/rewriting: only re-evaluate the two
original plot-turn outputs for the horror genre where W2's second turn
measured 975 codepoints against legacy V96=950. Live original remains RED.
Both frozen arms are validated by the identical current host code for
source/POV/physical state. Never overwrite the original Actions artifact.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from experiments import wf_source_progression_ab as ab
from experiments import wf_real_self_scene_diagnostics as diag
from experiments import wf_holdout_three_fresh_literary_genres as holdout
from writerforge.v96_causal_turns import parse_turn_outline
from writerforge.writing_assist import _normalize_optional_model_craft_labels
from writerforge.v114_external_story_state import require_external_runtime

ORIGINAL=Path("wf_horror_originals")
RESULTS=Path("wf_horror_offline_replay_results")
SHA={
    "original-CHAPTER_PLAN-model.json":
        "08cc15cbc55c68746fe6a38ea7b5b58f8a209dfecb97839bbd152bff3c9244f3",
    "original-SELF_BEAT_PLAN-model.json":
        "7494db54d3e236f4e1cdcce9587fc97f294f5793495605700850815589d2e7ff",
    "W1/original-decoded-PROSE_1.json":
        "9ffd93e5b323e7fd176ac9db4e385aee3d4a426dd7b4b4da0e1cbf92f63d1897",
    "W1/original-decoded-PROSE_2.json":
        "f04ad85c06e30813eb2139989de08a6c8a866ab45387d765d95b1d69f1e18525",
    "W2/original-decoded-PROSE_1.json":
        "9c2d120f99b46d308358a6cb2391e3c46e668bc4973d9b0742e8313f797364d6",
    "W2/original-decoded-PROSE_2.json":
        "d6ee18c7797437fad7f6fc0875835447db886c7fed957e82924b8cd4313287ac",
}
EXPECTED={
    "W1":"9446c0ebc761a3199309ae68d2c77bf72555ef0184d94f5de8a4d2c5e9a9bc93",
    "W2":"40b88b798ad9b0f2d6ff98a10a5397aa747d27329e5b5f7d285c613498b25968",
}


def h(raw):
    return hashlib.sha256(
        raw.encode("utf8") if type(raw) is str else raw).hexdigest()


def exact_text(relative):
    if relative not in SHA:
        raise RuntimeError("WF_HORROR_REPLAY_UNKNOWN_ORIGINAL_FILE")
    value=(ORIGINAL/relative).read_bytes()
    if h(value)!=SHA[relative]:
        raise RuntimeError("WF_HORROR_REPLAY_ORIGINAL_BYTES_CHANGED")
    return value.decode("utf8")


class OriginalOnlyClient:
    def __init__(self,arm):
        self.arm=arm
        self.next=0
        self.received=[
            json.loads(exact_text(f"{arm}/original-decoded-PROSE_1.json")),
            json.loads(exact_text(f"{arm}/original-decoded-PROSE_2.json"))]
        self.last_response_format_recovery=None
        self._on_response_wire=None

    def ask_json(self,*,role,system,user,max_tokens):
        if self.next>=2 or role!="self_scene_writing" or max_tokens!=1450:
            raise RuntimeError("WF_HORROR_REPLAY_NOT_EXACTLY_TWO_SOURCE_RESPONSES")
        record=self.received[self.next]
        self.next+=1
        return record


def main():
    require_external_runtime()
    genre="horror"
    diag.CASES[genre]=holdout.CASES[genre]
    assert ab.CASES is diag.CASES
    ab.TARGET=RESULTS
    original_plan=exact_text("original-CHAPTER_PLAN-model.json")
    original_beats=exact_text("original-SELF_BEAT_PLAN-model.json")
    model_beats,normalization=_normalize_optional_model_craft_labels(
        original_beats)
    assert len(parse_turn_outline(model_beats))==2
    # Original holdout arms were blinded W1/W2. Mapping was disclosed only
    # after the pre-unblinding editorial notes were durably saved.
    old_mapping=json.loads((ORIGINAL/"UNBLIND_MAPPING.json").read_text("utf8"))
    assert old_mapping["W1"]=="baseline"
    assert old_mapping["W2"]=="source_progression"
    plans={
        "model_plan":original_plan,"model_beats":model_beats,
        "model_optional_craft_recovery":normalization,
    }
    results={}
    for arm in ("W1","W2"):
        client=OriginalOnlyClient(arm)
        receipts=[]
        actual=ab._runner(
            genre,mode=old_mapping[arm],blind_id=arm,plans=plans,
            root=RESULTS/genre,client=client,calls=receipts)
        assert client.next==2 and len(receipts)==2
        path=RESULTS/genre/arm/"original-complete-candidate.md"
        if actual["status"]!="COMPLETE_UNACCEPTED_REAL_WF_CANDIDATE":
            raise RuntimeError("WF_HORROR_REPLAY_ORIGINAL_STILL_UNAVAILABLE")
        actual_body=path.read_text("utf8")
        if h(actual_body)!=EXPECTED[arm]:
            raise RuntimeError("WF_HORROR_REPLAY_TEXT_WAS_REWRITTEN")
        results[arm]={
            "status":actual["status"],
            "prose_sha256":h(actual_body),
            "han_chars":actual["han_chars"],
            "trace_reviews":len(actual["model_trace_review_failures"]),
            "all_original_model_response_bytes_verified":True,
        }
    output={
        "format":"wf.horror.source-original-offline-host-replay.v1",
        "original_live_run":39968891775,
        "original_live_w2_failure_preserved":True,
        "model_calls":0,"new_prose_generated":0,"provider_retries":0,
        "same_original_model_answer_hashes":SHA,
        "results":results,
        "independent_literary_quality_verified":False,
        "no_user_novels_or_canon_writes":True,
    }
    path=RESULTS/genre/"REPLAY_STATUS.json"
    path.write_text(json.dumps(
        output,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf8")
    print(json.dumps({
        "status":"WF_HORROR_REAL_SAVED_PROSE_REVALIDATED",
        "arms":results,"model_calls":0,
        "live_original_failure_not_overwritten":True,
    },ensure_ascii=False,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
