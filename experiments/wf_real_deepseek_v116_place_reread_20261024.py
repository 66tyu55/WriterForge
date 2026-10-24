"""One short SAME-DeepSeek follow-up on two observed failures to self-detect.

Previous true original #40094106486: MOVE_ON despite unclear boat -> shore.
Blind and neutral full-sentence source replay #40104976936: MOVE_ON again.
This explicitly different third condition supplies ONLY all *literal* V116
actor + movement + place phrases, chronologically, without a contradiction
label, preferred outcome or replacement sentence. Creative AI may keep prose.

At most 1 new review and, only on its own valid LOOK_BACK_NOW, 1 V119 edit
from the original prior provider response. No repeated writing/critic calls,
no cross-R2/Canon/main, no retries, no independent fictional text generator.
"""
from __future__ import annotations

from pathlib import Path
from hashlib import sha256
import json
import os
import re
import sys

from experiments import wf_real_deepseek_blind_source_replay_20261024 as prior
from experiments.wf_three_existing_writer_models_real_20261024 import (
    BEAT,CAST,SEED,MOMENT_SYSTEM,EDIT_SYSTEM,
)
from writerforge.deepseek_flash_model import (
    DeepSeekFlashModel,FlashBudget,DeepSeekFlashError,
)
from writerforge.writing_assist import (
    _ai_decides_when_to_revisit,_self_edit_one_turn,_decode_json,
)
from writerforge.v116_state_delta import source_only_character_place_mentions
from writerforge.v114_external_story_state import (
    external_temporal_step,V114ExternalMemoryError,require_external_runtime,
)
from writerforge.narrative_core import (
    new_graph,advance_graph,NarrativeCoreError,
)
from writerforge.v96_causal_turns import check_turn,V96CausalDraftError
from writerforge.verified_flow import WritingExecutionError

INPUT_PREVIOUS=Path("wf_prior_reread_20261024")
OUTPUT=Path("wf_real_deepseek_v116_place_reread_20261024")
OLDER_RUN=40104976936
OLDER_ARTIFACT=12564063524
MODEL_CALL_CAP=2
TOTAL_OUTPUT_RESERVE=600+1800

def sha(v):
    if type(v) is str:
        v=v.encode("utf8")
    return sha256(v).hexdigest()

def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,
                               sort_keys=True,indent=2),encoding="utf8")

def previous_two_real_reviews(path=INPUT_PREVIOUS,*,expected=prior.REAL_PROSE_SHA):
    """Prove one already billed blind + one already billed all-sentence read.

    Only a run with genuine older replies permits an additional diagnostic.
    """
    docs=("STATUS.json","ORIGINAL_PROVIDER_PROSE_READONLY.md",
          "01-BLIND_SELF_READ-decoded-model.json",
          "01-BLIND_SELF_READ-original-wire.json",
          "02-SOURCE_INDEX_SELF_READ-decoded-model.json",
          "02-SOURCE_INDEX_SELF_READ-original-wire.json",
          "blind/ai-when-and-why-original.json",
          "source-index/ai-when-and-why-original.json")
    if any(not (path/f).is_file() or (path/f).is_symlink()
           for f in docs):
        raise RuntimeError("WF_V116_PRIOR_REAL_REVIEW_NOT_AVAILABLE")
    source=(path/"ORIGINAL_PROVIDER_PROSE_READONLY.md").read_text("utf8")
    old=json.loads((path/"STATUS.json").read_text("utf8"))
    if (sha(source)!=expected or
        old.get("source_sha256")!=expected or
        old.get("status")!="REAL_REVIEW_STAGES_COMPLETED" or
        old.get("old_original_model_decision")!="MOVE_ON" or
        old.get("blind_decision")!="MOVE_ON" or
        old.get("source_index_decision")!="MOVE_ON" or
        old.get("actual_provider_calls")!=2 or
        old.get("source_actually_changed") is not False or
        old.get("source_index_model_offered") is not True or
        type(old.get("model_request_evidence")) is not list or
        len(old["model_request_evidence"])!=2):
        raise RuntimeError("WF_V116_PRIOR_REAL_DECISION_CHANGED")
    for ordinal,stage,root in (
        (1,"BLIND_SELF_READ","blind"),
        (2,"SOURCE_INDEX_SELF_READ","source-index"),
    ):
        answer=(path/f"{ordinal:02d}-{stage}-decoded-model.json").read_bytes()
        wire=(path/f"{ordinal:02d}-{stage}-original-wire.json").read_bytes()
        literal=(path/root/"ai-when-and-why-original.json").read_bytes()
        item=old["model_request_evidence"][ordinal-1]
        if (answer!=literal or
            sha(answer)!=item.get("decoded_sha256") or
            sha(wire)!=item.get("wire_sha256") or
            item.get("wire_preserved_before_model_parse") is not True or
            _decode_json(literal.decode("utf8")).get("decision")!="MOVE_ON"):
            raise RuntimeError("WF_V116_PRIOR_REAL_REPLY_OR_WIRE_INVALID")
    return {"source":source,"status":old}

class SameActualWriter:
    def __init__(self,folder):
        token=os.environ.get("DEEPSEEK_API_KEY")
        if not isinstance(token,str) or len(token)<16:
            raise RuntimeError("WF_V116_EXISTING_WRITER_SECRET_NOT_CONFIGURED")
        self.folder=folder
        self.calls=[]
        self.budget=FlashBudget(
            max_calls=MODEL_CALL_CAP,
            max_reserved_output_tokens=TOTAL_OUTPUT_RESERVE,
            max_total_tokens=150000)
        self.provider=DeepSeekFlashModel(
            api_key=token,budget=self.budget,timeout_seconds=100,
            on_response_wire=self._on_wire)
    def _on_wire(self,wire):
        if not self.calls:
            raise RuntimeError("WF_V116_REAL_WIRE_WITHOUT_REQUEST")
        row=self.calls[-1]
        name=f"{len(self.calls):02d}-{row['stage']}-provider-wire.json"
        (self.folder/name).write_bytes(wire)
        row["provider_wire_sha256"]=sha(wire)
        row["wire_kept_before_decoding"]=True
    def ask(self,packet,*,model,api_base,max_tokens):
        if (len(self.calls)>=MODEL_CALL_CAP or
            model is not None or api_base is not None or
            max_tokens not in (600,1800)):
            raise RuntimeError("WF_V116_REAL_MODEL_BUDGET_EXCEEDED")
        if max_tokens==600:
            if self.calls:
                raise RuntimeError("WF_V116_SOURCE_STAGE_ALREADY_USED")
            stage="SOURCE_PLACES_REREAD"
            system=MOMENT_SYSTEM
        else:
            if not self.calls or self.calls[-1]["stage"]!="SOURCE_PLACES_REREAD":
                raise RuntimeError("WF_V116_V119_WITHOUT_AUTHOR_LOOKBACK")
            stage="SAME_WRITER_V119"
            system=EDIT_SYSTEM
        row={
            "stage":stage,"prompt_sha256":sha(packet.prompt),
            "requested_output_tokens":max_tokens,
            "wire_kept_before_decoding":False,
        }
        self.calls.append(row)
        answer=self.provider.ask_json(
            role="self_scene_writing",system=system,user=packet.prompt,
            max_tokens=max_tokens)
        reply=json.dumps(answer,ensure_ascii=False,separators=(",",":"))
        (self.folder/f"{len(self.calls):02d}-{stage}-model-answer.json"
         ).write_text(reply,encoding="utf8")
        row["response_sha256"]=sha(reply)
        return reply

def run():
    genuine=prior.verified_prior_source()
    if sha(genuine["source"])!=prior.REAL_PROSE_SHA:
        raise RuntimeError("WF_V116_GENUINE_MODEL_SOURCE_NOT_AVAILABLE")
    earlier=previous_two_real_reviews()
    if earlier["source"]!=genuine["source"]:
        raise RuntimeError("WF_V116_MULTIPLE_REAL_RUNS_SOURCE_DIFFERENT")
    original=genuine["source"]
    check_turn(genuine["original_model_raw"],BEAT,
               mode="causal_guard",accepted=())
    place=source_only_character_place_mentions(original,cast=CAST)
    if (place["source_sha256"]!=prior.REAL_PROSE_SHA or
        not place["entries"]):
        raise RuntimeError("WF_V116_SOURCE_PLACES_MISSING")
    require_external_runtime()
    oldstate=external_temporal_step(SEED,cast=CAST)
    graph=new_graph(project_id=prior.PROJECT,scene_id=prior.SCENE)
    graph=advance_graph(
        graph,project_id=prior.PROJECT,scene_id=prior.SCENE,
        chapter_index=1,prose=SEED,events=())
    OUTPUT.mkdir(exist_ok=False)
    (OUTPUT/"GenuineOld451Unchanged.md").write_text(original,encoding="utf8")
    save(OUTPUT/"V116_Literal_Place_Sources.json",place)
    status={
        "format":"wf.real.v116-source-literal-place-review-20261024.v1",
        "status":"PREFLIGHT_ACCEPTED",
        "parent_original_workflow":prior.PRIOR_RUN,
        "parent_original_artifact":prior.PRIOR_ARTIFACT,
        "previous_blind_plus_index_workflow":OLDER_RUN,
        "previous_two_review_artifact":OLDER_ARTIFACT,
        "old_original_model_decision":"MOVE_ON",
        "old_blind_decision":"MOVE_ON",
        "old_literal_index_decision":"MOVE_ON",
        "source_sha256":prior.REAL_PROSE_SHA,
        "literal_place_source_receipt_sha256":place["receipt_sha256"],
        "literal_place_sources_count":len(place["entries"]),
        "literal_place_extraction_does_not_prove_world_state":True,
        "host_has_not_declared_any_place_change_a_contradiction":True,
        "host_did_not_specify_a_revision_or_literary_outcome":True,
        "max_new_provider_calls":MODEL_CALL_CAP,
        "provider_retries":0,
        "canonical_prose_writes":0,"R2_library_writes":0,
        "model_training":False,"literary_quality_verified":False,
    }
    model=None
    try:
        model=SameActualWriter(OUTPUT)
        addition=(
            "\n【仅提取本篇原文所有明确姓名＋位置动作的 V116 来源短句】"
            +json.dumps(place,ensure_ascii=False,separators=(",",":"))
            +"\n它们是从原文逐字截取的叙述候选，只按出现先后记录；"
            "软件没有推断中间发生了什么、谁移动错了，也没有给你删改建议。"
            "这些片段不一定构成问题；你仍可以自主选择 MOVE_ON。"
            "请作为原来的小说作者重新阅读整段正文，再独立判断。"
        )
        review=_ai_decides_when_to_revisit(
            raw=genuine["original_model_raw"],beat=BEAT,accepted=(),
            turn_packet=prior.packet_for_review(addition),
            ask_model=model.ask,directory=OUTPUT/"v116-source-review")
        status.update({
            "source_place_review_decision":review["decision"],
            "source_place_review_model_calls":review["model_calls"],
            "source_place_review_why_now":review.get("reason"),
            "source_place_review_quote":review.get("source_quote"),
            "source_place_review_receipt":review.get("receipt"),
            "writer_called_v119":review["decision"]=="LOOK_BACK_NOW",
        })
        final=original
        if review["decision"]=="LOOK_BACK_NOW":
            edit_packet=prior.packet_for_review(
                "\n【原写作 AI 自己选择的修订意图】"+
                json.dumps({
                    "why_now":review.get("reason"),
                    "risk_if_unchanged":review.get("risk"),
                    "source_quote":review.get("source_quote"),
                    "desired_effect":review.get("desired_effect"),
                },ensure_ascii=False))
            draft,receipt=_self_edit_one_turn(
                raw=genuine["original_model_raw"],beat=BEAT,accepted=(),
                project_id=prior.PROJECT,scene_id=prior.SCENE,
                turn_packet=edit_packet,ask_model=model.ask,
                round_limit=1,call_allowance=1,
                directory=OUTPUT/"writer-V119-own-revision",
                previous_candidate_state=oldstate[
                    "reducer_result"]["candidate_state"],
                cast=CAST,current_external_story_checkpoint=oldstate,
                active_narrative_core=graph,
                story_chapter_index=2,
                writer_attention={
                    "reason":review.get("reason"),
                    "risk":review.get("risk"),
                    "desired_effect":review.get("desired_effect"),
                    "source_quote":review.get("source_quote"),
                    "focus":review.get("focus"),
                })
            status["writer_v119_proposal_receipt"]=receipt
            proposed=_decode_json(draft)["prose"].strip()
            if proposed!=original:
                check_turn(draft,BEAT,mode="causal_guard",accepted=())
                finalstate=external_temporal_step(
                    proposed,cast=CAST,prior=oldstate)
                status["new_v114_temporal_receipt_sha256"]=(
                    finalstate["receipt_sha256"])
                final=proposed
        status["actual_revised_source_sha256"]=sha(final)
        status["did_writer_actually_rewrite"]=final!=original
        (OUTPUT/"FinalUnacceptedCandidate.md").write_text(
            final,encoding="utf8")
        status["status"]="GENUINE_AUTHOR_SOURCE_REVIEW_FINISHED"
    except (DeepSeekFlashError,WritingExecutionError,V96CausalDraftError,
            V114ExternalMemoryError,NarrativeCoreError,ValueError,
            RuntimeError,TypeError,KeyError,OSError) as err:
        status["status"]="GENUINE_AUTHOR_REVIEW_PARTIAL_OR_REJECTED"
        status["error_code"]=prior.safe_code(err)
    finally:
        status["new_actual_provider_calls"]=(
            model.budget.calls_reserved if model else 0)
        status["provider_usage_reported"]=(
            model.budget.public_receipt() if model else {})
        status["raw_provider_evidence"]=model.calls if model else []
        save(OUTPUT/"STATUS.json",status)
        print(json.dumps({
            "status":status["status"],
            "source_place_mentions":status["literal_place_sources_count"],
            "older_real_3_choices":["MOVE_ON","MOVE_ON","MOVE_ON"],
            "new_writer_choice":status.get("source_place_review_decision"),
            "author_proposed_revision":status.get("writer_called_v119"),
            "actual_source_changed":status.get("did_writer_actually_rewrite"),
            "actual_new_provider_calls":status["new_actual_provider_calls"],
            "max_new_provider_calls":MODEL_CALL_CAP,
            "failure":status.get("error_code"),
        },ensure_ascii=False),flush=True)
    return status

if __name__=="__main__":
    try:
        run()
    except Exception as error:
        print(json.dumps({
            "stage":"V116_REAL_SOURCE_PROVENANCE_PREFLIGHT_BLOCKED",
            "error":prior.safe_code(error),
            "no_new_model_retries":True,
        },ensure_ascii=False),flush=True)
        sys.exit(2)
