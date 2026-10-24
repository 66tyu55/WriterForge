"""Actual ONE bounded DeepSeek author self-review on its OWN prior real story.

The original prose is the byte-verified genuine provider artifact from
GitHub Actions run #40094106486. We DO NOT regenerate or seed a fake model
answer. First read: no host hints/diagnosis. Only when the author model does
not independently decide LOOK_BACK_NOW, the second (separate predeclared)
read contains ALL literal sentence source offsets and explicit names from
the same unmodified prose, NOT a selected contradiction or a prose fix.
Only a valid AI LOOK_BACK_NOW may enter its own V119 edit stage.

Three new model requests at most. No retries, no literary grader model,
no R2, no Canon, no main/Railway, and no repeated source study.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import os
import re
import sys

from writerforge.deepseek_flash_model import (
    DeepSeekFlashModel, FlashBudget, DeepSeekFlashError,
)
from writerforge.verified_flow import GroundedDraftPacket, WritingExecutionError
from writerforge.v96_causal_turns import check_turn,V96CausalDraftError
from writerforge.v114_external_story_state import (
    external_temporal_step,V114ExternalMemoryError,require_external_runtime,
)
from writerforge.narrative_core import (
    new_graph,advance_graph,NarrativeCoreError,
)
from writerforge.writing_assist import (
    _ai_decides_when_to_revisit,_self_edit_one_turn,
    _source_only_writer_replay_index,_decode_json,
)
from experiments.wf_three_existing_writer_models_real_20261024 import (
    SEED, BEAT, CAST, WRITER_SYSTEM, MOMENT_SYSTEM, EDIT_SYSTEM,
)

PRIOR_RUN=40094106486
PRIOR_ARTIFACT=12559689583
PRIOR_HEAD="42997c257568473049541d8d771eae3aae20a4ba"
REAL_PROSE_SHA="46334d4e783a32c1def8affeb6eea2b9a4bb6e429e846ef910fb4b44601cd6f7"
ORIGINAL_SOURCE=Path("wf_prior_deepseek_20261024/deepseek-flash")
OUTPUT=Path("wf_real_deepseek_source_replay_20261024")
PROJECT="wf-deepseek-original-blind-reread"
SCENE="han-ting-river-synthetic-source"
MAX_NEW_CALLS=3
TOKEN_BUDGET=600+600+1800
STAGES=("BLIND_SELF_READ","SOURCE_INDEX_SELF_READ","AUTHOR_V119_EDIT")

def digest(value):
    return sha256(value if type(value) is bytes else
                  value.encode("utf8")).hexdigest()

def safe_code(error):
    text=str(error)
    if len(text)<=160 and re.fullmatch(r"[A-Z][A-Z0-9_:\-]{3,159}",text):
        return text
    return type(error).__name__

def write_json(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,
                               sort_keys=True),encoding="utf8")

def verified_prior_source(directory=ORIGINAL_SOURCE,*,expected=REAL_PROSE_SHA):
    """Block tampered/incorrect archives *before any real model request*.

    This validates BOTH the previous provider wire hashes and the final
    manuscript bytes; the 0.N previous MOVE_ON must remain visible as a
    separate original decision, never overwritten by this new experiment.
    """
    required={
        "ORIGINAL_MODEL_PROSE.md","STATUS.json",
        "01-write-provider-wire.json","01-write-model-answer.json",
        "02-decide-provider-wire.json","02-decide-model-answer.json",
        "ai-moment/ai-when-and-why-original.json",
    }
    if (not isinstance(directory,Path) or
        any(not (directory/name).is_file() or
            (directory/name).is_symlink() for name in required)):
        raise RuntimeError("WF_ORIGINAL_PROVIDER_ARTIFACT_MISSING")
    src=(directory/"ORIGINAL_MODEL_PROSE.md").read_bytes()
    if (not 80<=len(src)<=6000 or
        digest(src)!=expected or
        src.decode("utf8","strict")!=src.decode("utf8","strict").strip()):
        raise RuntimeError("WF_ORIGINAL_PROVIDER_PROSE_SHA_INVALID")
    model_answers=[]
    records=json.loads((directory/"STATUS.json").read_text("utf8"))
    if (records.get("status")!="REAL_MODEL_EVALUATED" or
        records.get("model")!="deepseek-flash" or
        records.get("provider")!="deepseek" or
        records.get("calls_attempted")!=2 or
        records.get("ai_choice")!="MOVE_ON" or
        records.get("original_prose_sha256")!=expected or
        records.get("original_new_scenario_sha256")!=digest(SEED) or
        type(records.get("calls")) is not list or
        len(records["calls"])!=2):
        raise RuntimeError("WF_ORIGINAL_PROVIDER_HISTORY_INVALID")
    for ordinal,stage in enumerate(("write","decide")):
        wire=(directory/f"{ordinal+1:02d}-{stage}-provider-wire.json").read_bytes()
        decoded=(directory/f"{ordinal+1:02d}-{stage}-model-answer.json").read_bytes()
        event=records["calls"][ordinal]
        if (event.get("stage")!=stage or
            digest(wire)!=event.get("wire_sha256") or
            digest(decoded)!=event.get("response_sha256") or
            event.get("wire_preserved") is not True):
            raise RuntimeError("WF_ORIGINAL_PROVIDER_WIRE_TAMPERED")
        model_answers.append(decoded.decode("utf8","strict"))
    doc=_decode_json(model_answers[0])
    original=src.decode("utf8","strict")
    previous=json.loads(model_answers[1])
    earlier=(directory/"ai-moment/ai-when-and-why-original.json"
             ).read_text("utf8")
    if (type(doc) is not dict or
        set(doc)!={"prose","trace"} or
        doc["prose"].strip()!=original or
        previous.get("decision")!="MOVE_ON" or
        previous.get("source_sha256")!=expected or
        _decode_json(earlier)!=previous):
        raise RuntimeError("WF_ORIGINAL_PROVIDER_SOURCE_OR_DECISION_DIFFERENT")
    return {"source":original,"original_model_raw":model_answers[0],
            "previous_decision":previous,"status":records}

def packet_for_review(addition=""):
    # Intentionally NO target-person, plot-hole, river, boat, shore, or
    # editorial diagnosis in the initial blind packet.
    preamble=(
        "你是这篇作品的原写作模型。请独立重读你已经实际写出的"
        "完整候选段落，比较人物行动与呈现效果后由自己选择"
        "继续或回改。允许 MOVE_ON；工作台不给你任何错误清单"
        "或预设需要删除的情节。不能输出文学分数，不写新正文。"
    )
    prompt=preamble+addition
    return GroundedDraftPacket(
        scene_id=SCENE,project_id=PROJECT,snapshot_id=0,
        evidence=(),craft_ids=(),prompt=prompt,
        prompt_sha256=digest(prompt),
    )

class ModelCalls:
    def __init__(self,output):
        key=os.environ.get("DEEPSEEK_API_KEY")
        if type(key) is not str or len(key)<16:
            raise RuntimeError("WF_EXISTING_DEEPSEEK_WRITER_SECRET_NOT_AVAILABLE")
        self.output=output
        self.events=[]
        self.budget=FlashBudget(max_calls=MAX_NEW_CALLS,
                                max_reserved_output_tokens=TOKEN_BUDGET,
                                max_total_tokens=150000)
        self.client=DeepSeekFlashModel(
            api_key=key,budget=self.budget,timeout_seconds=100,
            on_response_wire=self._save_wire)
    def _save_wire(self,wire):
        if not self.events:
            raise RuntimeError("WF_SOURCE_REPLAY_WIRE_WITHOUT_STAGE")
        event=self.events[-1]
        path=self.output/f"{len(self.events):02d}-{event['stage']}-original-wire.json"
        path.write_bytes(wire)
        event["wire_sha256"]=digest(wire)
        event["wire_preserved_before_model_parse"]=True
    def ask(self,packet,*,model,api_base,max_tokens):
        if (len(self.events)>=MAX_NEW_CALLS or
            model is not None or api_base is not None or
            max_tokens not in (600,1800)):
            raise RuntimeError("WF_SOURCE_REPLAY_CALL_LIMIT_OR_ROLE_CHANGED")
        n=len(self.events)
        if max_tokens==600:
            if n==0:
                stage=STAGES[0]
            elif n==1 and self.events[0]["stage"]==STAGES[0]:
                stage=STAGES[1]
            else:
                raise RuntimeError("WF_SOURCE_REPLAY_MOMENT_ORDER_WRONG")
            system=MOMENT_SYSTEM
        else:
            if (n<1 or self.events[-1]["stage"] not in STAGES[:2]):
                raise RuntimeError("WF_SOURCE_REPLAY_EDIT_WITHOUT_AI_DECISION")
            stage=STAGES[2]
            system=EDIT_SYSTEM
        event={
            "stage":stage,"max_requested_output_tokens":max_tokens,
            "actual_prompt_sha256":digest(packet.prompt),
            "original_model_answer_saved":False,
            "wire_preserved_before_model_parse":False,
        }
        self.events.append(event)
        result=self.client.ask_json(
            role="self_scene_writing",system=system,
            user=packet.prompt,max_tokens=max_tokens)
        reply=json.dumps(result,ensure_ascii=False,separators=(",",":"))
        (self.output/f"{len(self.events):02d}-{stage}-decoded-model.json").write_text(
            reply,encoding="utf8")
        event["decoded_sha256"]=digest(reply)
        event["original_model_answer_saved"]=True
        return reply

def run():
    # Read-only provenance gate is first: no out-of-band assistant-edited
    # or source-identical-but-different-origin manuscript is accepted.
    proof=verified_prior_source()
    original=proof["source"]
    check_turn(proof["original_model_raw"],BEAT,
               mode="causal_guard",accepted=())
    index=_source_only_writer_replay_index(original,cast=CAST)
    if index["source_sha256"]!=REAL_PROSE_SHA:
        raise RuntimeError("WF_SOURCE_REPLAY_INDEX_NOT_ORIGINAL")
    require_external_runtime()
    # The prior seed is the only prior chapter/scene fact source for
    # existing NovelStudio; this is NOT a recreated author-approved Canon.
    prior=external_temporal_step(SEED,cast=CAST)
    graph=new_graph(project_id=PROJECT,scene_id=SCENE)
    graph=advance_graph(graph,project_id=PROJECT,scene_id=SCENE,
                        chapter_index=1,prose=SEED,events=())
    OUTPUT.mkdir(exist_ok=False)
    (OUTPUT/"ORIGINAL_PROVIDER_PROSE_READONLY.md").write_text(
        original,encoding="utf8")
    write_json(OUTPUT/"literal-index.json",index)
    write_json(OUTPUT/"prior-original-decision.json",proof["previous_decision"])
    status={
        "format":"wf.real.original-prose-blind-vs-source-index.v1",
        "status":"SOURCE_CONFIRMED_NO_MODEL_YET",
        "original_real_workflow_run":PRIOR_RUN,
        "original_real_artifact_id":PRIOR_ARTIFACT,
        "original_real_workflow_sha":PRIOR_HEAD,
        "source_sha256":REAL_PROSE_SHA,
        "old_original_model_decision":"MOVE_ON",
        "same_configured_writer_model":"deepseek-flash",
        "decision_prompts_do_not_prelabel_source_error":True,
        "source_index_derived_from_all_literal_units_not_cherry_picked":True,
        "max_additional_model_calls":MAX_NEW_CALLS,
        "new_model_retries":0,"canonical_story_writes":0,
        "R2_user_novel_or_private_cloud_writes":0,
        "literary_quality_verified":False,
        "valid_literary_judgment_by_host":False,
        "no_expert_or_external_critic_model_called":True,
    }
    client=None
    try:
        client=ModelCalls(OUTPUT)
        blind=_ai_decides_when_to_revisit(
            raw=proof["original_model_raw"],beat=BEAT,accepted=(),
            turn_packet=packet_for_review(),
            ask_model=client.ask,directory=OUTPUT/"blind")
        status.update({
            "blind_decision":blind["decision"],
            "blind_raw_model_calls":blind["model_calls"],
            "blind_reason":blind.get("reason"),
            "blind_actual_source_quote":blind.get("source_quote"),
            "blind_signal_receipt":blind.get("receipt"),
        })
        if blind["decision"]=="LOOK_BACK_NOW":
            selected=blind
            selected_phase="BLIND_SELF_READ"
            status["source_index_model_offered"]=False
        else:
            # No hint that any particular line is wrong: ALL exact
            # source positions/actor literal mentions are supplied in order.
            # The AI can still uphold MOVE_ON after reading the evidence.
            addition=(
                "\n【同一稿件逐句原文来源目录（仅字面序号与原文位置，"
                "无文学评分、无推断角色在哪）】"
                +json.dumps(index,ensure_ascii=False,separators=(",",":"))
                +"\n以上只是已写原文的可索引证据；这不是指出哪里错了。"
                "请你仍作为原作者自行决定要不要回头。"
            )
            source_read=_ai_decides_when_to_revisit(
                raw=proof["original_model_raw"],beat=BEAT,accepted=(),
                turn_packet=packet_for_review(addition),
                ask_model=client.ask,directory=OUTPUT/"source-index")
            status.update({
                "source_index_model_offered":True,
                "source_index_decision":source_read["decision"],
                "source_index_raw_model_calls":source_read["model_calls"],
                "source_index_reason":source_read.get("reason"),
                "source_index_actual_source_quote":source_read.get("source_quote"),
                "source_index_signal_receipt":source_read.get("receipt"),
            })
            selected=source_read
            selected_phase="SOURCE_INDEX_SELF_READ"
        status["ai_revision_trigger_source"]=selected_phase
        status["ai_revision_allowed"]=selected["decision"]=="LOOK_BACK_NOW"
        final=original
        if selected["decision"]=="LOOK_BACK_NOW":
            edit_packet=packet_for_review(
                "\n【AI 自己选择回改的原因与来源证据（并非宿主判决）】"
                +json.dumps({
                    "why_now":selected.get("reason"),
                    "source_quote":selected.get("source_quote"),
                    "risk_if_kept":selected.get("risk"),
                    "intended_effect":selected.get("desired_effect"),
                },ensure_ascii=False))
            raw,receipt=_self_edit_one_turn(
                raw=proof["original_model_raw"],beat=BEAT,accepted=(),
                project_id=PROJECT,scene_id=SCENE,
                turn_packet=edit_packet,ask_model=client.ask,
                round_limit=1,call_allowance=1,
                directory=OUTPUT/"actual-v119-edit",
                previous_candidate_state=prior["reducer_result"]["candidate_state"],
                cast=CAST,current_external_story_checkpoint=prior,
                active_narrative_core=graph,
                story_chapter_index=2,
                writer_attention={
                    "reason":selected.get("reason"),
                    "risk":selected.get("risk"),
                    "desired_effect":selected.get("desired_effect"),
                    "source_quote":selected.get("source_quote"),
                    "focus":selected.get("focus"),
                })
            status["v119_model_edit_receipt"]=receipt
            result=_decode_json(raw)
            revised=result["prose"].strip()
            if revised!=original:
                # Existing V96 + NovelStudio V114 source guards, no
                # separate novel-writing heuristic, no auto-rescue edits.
                check_turn(raw,BEAT,mode="causal_guard",accepted=())
                check=external_temporal_step(revised,cast=CAST,prior=prior)
                status["v114_revised_receipt_sha256"]=check["receipt_sha256"]
                final=revised
        status["revised_candidate_source_sha256"]=digest(final)
        status["source_actually_changed"]=final!=original
        (OUTPUT/"FINAL_PRIVATE_UNACCEPTED_CANDIDATE.md").write_text(
            final,encoding="utf8")
        status["status"]="REAL_REVIEW_STAGES_COMPLETED"
    except (DeepSeekFlashError,WritingExecutionError,V96CausalDraftError,
            V114ExternalMemoryError,NarrativeCoreError,ValueError,
            TypeError,KeyError,RuntimeError,OSError) as exc:
        status["status"]="REAL_REVIEW_PARTIAL_OR_REJECTED"
        status["failure_code"]=safe_code(exc)
    finally:
        status["actual_provider_calls"]=(client.budget.calls_reserved
                                           if client is not None else 0)
        status["requested_output_token_budget_used"]=(
            client.budget.tokens_reserved if client else 0)
        status["provider_usage_reported"]=(
            client.budget.public_receipt() if client else {})
        status["model_request_evidence"]=(client.events if client else [])
        write_json(OUTPUT/"STATUS.json",status)
        print(json.dumps({
            "status":status["status"],
            "old_real_decision":status["old_original_model_decision"],
            "blind":status.get("blind_decision"),
            "source_index":status.get("source_index_decision"),
            "edit_started_after_ai_lookback":status.get("ai_revision_allowed"),
            "prose_changed":status.get("source_actually_changed"),
            "new_calls":status["actual_provider_calls"],
            "max_calls":MAX_NEW_CALLS,
            "error":status.get("failure_code"),
            "source_sha256":REAL_PROSE_SHA,
        },ensure_ascii=False),flush=True)
    # The job itself succeeds even when the writer honestly chooses KEEP or
    # returns invalid schema; those are valuable real negative samples.
    return status

def main():
    run()
    return 0

if __name__=="__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({
            "stage":"REAL_REPLAY_PREFLIGHT_BLOCKED",
            "error_code":safe_code(exc),
            "no_retry_performed":True,
        },ensure_ascii=False),flush=True)
        sys.exit(2)
