"""One real same-model reader-first -> author-choice test on old real fiction.

This is NOT a repeat of old 'please look again' prompt. It uses the existing
G writing_assist._reader_separates_written_and_inferred implementation:
in a fresh context the SAME DeepSeek model reads only its own original
manuscript, separates literal quoted events from unproven reader-added links,
then assumes its author role with those UNVERIFIED hypotheses.

Old genuine manuscript and old provider wire must pass hashes first.
Only the author's VALID LOOK_BACK_NOW authorizes one same-model V119 patch.
No outcome is forced, no retries, no extra model, no R2 or Canon promotion.
"""
from __future__ import annotations

from pathlib import Path
from hashlib import sha256
import json
import os
import re
import sys

from writerforge.deepseek_flash_model import (
    DeepSeekFlashModel,FlashBudget,DeepSeekFlashError,
)
from writerforge.verified_flow import WritingExecutionError
from writerforge.writing_assist import (
    _reader_separates_written_and_inferred,
    _ai_decides_when_to_revisit,
    _self_edit_one_turn,
    _decode_json,
)
from writerforge.v96_causal_turns import check_turn,V96CausalDraftError
from writerforge.v114_external_story_state import (
    external_temporal_step,require_external_runtime,
    V114ExternalMemoryError,
)
from writerforge.narrative_core import (
    new_graph,advance_graph,NarrativeCoreError,
)
from experiments.wf_real_deepseek_blind_source_replay_20261024 import (
    verified_prior_source,packet_for_review,REAL_PROSE_SHA,
    PRIOR_RUN,PRIOR_ARTIFACT,safe_code,
)
from experiments.wf_three_existing_writer_models_real_20261024 import (
    SEED,BEAT,CAST,MOMENT_SYSTEM,EDIT_SYSTEM,
)

OUTPUT=Path("wf_deepseek_reader_first_author_20261024")
MODEL="deepseek-flash"
MAX_CALLS=3
READER_TOKENS=1000
AUTHOR_TOKENS=600
EDIT_TOKENS=1800
EXPECTED_TOKENS=READER_TOKENS+AUTHOR_TOKENS+EDIT_TOKENS
READER_SYSTEM=(
    "你是第一次看到这篇陌生小说的真实读者。"
    "只读用户提示内实际已写的完整正文，不调用原先作者大纲和评语。"
    "请严格区分原文逐字出现的事实与阅读过程中需要自行想象的过渡。"
    "任何推测必须带前后逐字原文引句，不写代替作者的小说新句，"
    "不对稿件评分，不负责决定是否要删稿。只输出完整 JSON 对象。"
)


def h(value):
    return sha256(value if type(value) is bytes else
                  value.encode("utf8")).hexdigest()


def save(path,value):
    path.write_text(json.dumps(
        value,ensure_ascii=False,sort_keys=True,indent=2),encoding="utf8")


class OriginalModelInTwoRoles:
    def __init__(self,path):
        token=os.environ.get("DEEPSEEK_API_KEY")
        if not isinstance(token,str) or len(token)<16:
            raise RuntimeError("WF_READER_FIRST_NO_EXISTING_DEEPSEEK_SECRET")
        self.path=path
        self.events=[]
        self.budget=FlashBudget(
            max_calls=MAX_CALLS,
            max_reserved_output_tokens=EXPECTED_TOKENS,
            max_total_tokens=150000)
        self.provider=DeepSeekFlashModel(
            api_key=token,budget=self.budget,
            timeout_seconds=100,on_response_wire=self._save_wire)
    def _save_wire(self,wire):
        if not self.events:
            raise RuntimeError("WF_READER_FIRST_WIRE_UNEXPECTED")
        current=self.events[-1]
        name=f"{len(self.events):02d}-{current['stage']}-provider-wire.json"
        (self.path/name).write_bytes(wire)
        current["wire_sha256"]=h(wire)
        current["provider_wire_preserved_before_decode"]=True
    def ask(self,packet,*,model,api_base,max_tokens):
        if (model is not None or api_base is not None or
            len(self.events)>=MAX_CALLS):
            raise RuntimeError("WF_READER_FIRST_INCORRECT_MODEL_OR_BUDGET")
        sequence=((READER_TOKENS,"INDEPENDENT_READER",READER_SYSTEM),
                  (AUTHOR_TOKENS,"ORIGINAL_AUTHOR",MOMENT_SYSTEM),
                  (EDIT_TOKENS,"AUTHOR_V119_REVISION",EDIT_SYSTEM))
        need=sequence[len(self.events)]
        # The final stage only exists if author chose to revise.
        if max_tokens!=need[0]:
            raise RuntimeError("WF_READER_FIRST_STAGE_NOT_AUTHORIZED")
        stage,system=need[1:]
        if stage=="INDEPENDENT_READER":
            # First reader only sees raw candidate fiction, NOT the author's
            # earlier MOVE_ONs, sealed historical risk, or chapter plan.
            if (SEED in packet.prompt or
                "上一次" in packet.prompt or
                "程九坐进船里后" in packet.prompt or
                "下船" in packet.prompt):
                raise RuntimeError("WF_READER_FIRST_PREJUDGED_SOURCE")
        self.events.append({
            "stage":stage,"prompt_sha256":h(packet.prompt),
            "max_requested_output_tokens":max_tokens,
            "provider_wire_preserved_before_decode":False,
        })
        reply=self.provider.ask_json(
            role="self_scene_writing",system=system,
            user=packet.prompt,max_tokens=max_tokens)
        raw=json.dumps(reply,ensure_ascii=False,separators=(",",":"))
        (self.path/f"{len(self.events):02d}-{stage}-decoded.json").write_text(
            raw,encoding="utf8")
        self.events[-1]["decoded_reply_sha256"]=h(raw)
        return raw


def run():
    original=verified_prior_source()
    prose=original["source"]
    if h(prose)!=REAL_PROSE_SHA:
        raise RuntimeError("WF_READER_FIRST_WRONG_ORIGINAL_SOURCE")
    check_turn(original["original_model_raw"],BEAT,
               mode="causal_guard",accepted=())
    require_external_runtime()
    oldstate=external_temporal_step(SEED,cast=CAST)
    graph=new_graph(project_id="wf-original-reader-first",
                    scene_id="river-original")
    graph=advance_graph(
        graph,project_id="wf-original-reader-first",scene_id="river-original",
        chapter_index=1,prose=SEED,events=())
    OUTPUT.mkdir(parents=True,exist_ok=False)
    (OUTPUT/"OLD_PROVIDER_ORIGINAL_UNTOUCHED.md").write_text(
        prose,encoding="utf8")
    status={
        "format":"wf.real.reader-first-author-after-three-move-ons.v1",
        "status":"GENUINE_OLD_SOURCE_VERIFIED",
        "source_sha256":REAL_PROSE_SHA,
        "source_original_run":PRIOR_RUN,
        "source_original_artifact":PRIOR_ARTIFACT,
        "prior_deepseek_self_reviews_already_existed":4,
        "no_old_move_on_replies_added_to_reader_prompt":True,
        "same_writer_is_only_model_called":True,
        "max_additional_provider_calls":MAX_CALLS,
        "max_reserved_output_tokens":EXPECTED_TOKENS,
        "new_model_retries":0,
        "no_host_literary_judgment":True,
        "reader_hypotheses_unproven":True,
        "canon_writes":0,"R2_writes":0,"model_training":False,
        "literary_quality_verified":False,
    }
    model=None
    try:
        model=OriginalModelInTwoRoles(OUTPUT)
        reader=_reader_separates_written_and_inferred(
            raw=original["original_model_raw"],
            turn_packet=packet_for_review(),
            ask_model=model.ask,directory=OUTPUT/"same-AI-reader")
        status.update({
            "reader_result_status":reader["status"],
            "reader_called_model":reader["model_calls"],
            "reader_source_receipt":reader["receipt"],
            "reader_proposed_unwritten_links":(
                reader["report"]["inferred_links"]
                if reader["report"] is not None else []),
            "reader_literal_observations":(
                reader["report"]["observed"]
                if reader["report"] is not None else []),
            "reader_reply_not_fictional_canon":True,
        })
        # Same provider, fresh author's role. Literary choice remains its own:
        # even with a valid guessed gap, it may select MOVE_ON.
        author=_ai_decides_when_to_revisit(
            raw=original["original_model_raw"],beat=BEAT,
            accepted=(),turn_packet=packet_for_review(),
            ask_model=model.ask,directory=OUTPUT/"same-AI-author",
            reader_report=reader["report"])
        status.update({
            "same_AI_author_decision":author["decision"],
            "same_AI_author_decision_receipt":author["receipt"],
            "same_AI_author_why_now":author.get("reason"),
            "same_AI_author_risk":author.get("risk"),
            "same_AI_author_requested_quote":author.get("source_quote"),
            "reader_report_delivered_to_author":author["receipt"].get(
                "unverified_reader_input_delivered",False),
            "v119_allowed_only_on_AI_LOOK_BACK_NOW":True,
        })
        final=prose
        if author["decision"]=="LOOK_BACK_NOW":
            # Original author must produce each new piece itself; WF cannot
            # write a 'bridge sentence' even for a real missing scene link.
            changed,receipt=_self_edit_one_turn(
                raw=original["original_model_raw"],beat=BEAT,
                accepted=(),project_id="wf-original-reader-first",
                scene_id="river-original",
                turn_packet=packet_for_review(),
                ask_model=model.ask,round_limit=1,call_allowance=1,
                directory=OUTPUT/"original-AI-V119-change",
                previous_candidate_state=oldstate[
                    "reducer_result"]["candidate_state"],
                current_external_story_checkpoint=oldstate,
                active_narrative_core=graph,
                cast=CAST,story_chapter_index=2,
                writer_attention={
                    "reason":author.get("reason"),
                    "risk":author.get("risk"),
                    "desired_effect":author.get("desired_effect"),
                    "source_quote":author.get("source_quote"),
                    "focus":author.get("focus"),
                })
            status["writer_V119_revision_receipt"]=receipt
            revised=_decode_json(changed)["prose"].strip()
            if revised!=prose:
                check_turn(changed,BEAT,mode="causal_guard",accepted=())
                newstate=external_temporal_step(
                    revised,cast=CAST,prior=oldstate)
                final=revised
                status["rewritten_V114_receipt_sha256"]=newstate[
                    "receipt_sha256"]
        status["written_candidate_changed"]=final!=prose
        status["final_candidate_sha256"]=h(final)
        (OUTPUT/"FINAL_PRIVATE_UNACCEPTED_DRAFT.md").write_text(
            final,encoding="utf8")
        status["status"]="GENUINE_AI_READER_AND_AUTHOR_REVIEW_COMPLETED"
    except (DeepSeekFlashError,WritingExecutionError,V96CausalDraftError,
            V114ExternalMemoryError,NarrativeCoreError,
            ValueError,KeyError,TypeError,RuntimeError,OSError) as error:
        status["status"]="GENUINE_READER_OR_AUTHOR_FAILED_UNACCEPTED"
        status["failure_code"]=safe_code(error)
    finally:
        status["new_actual_provider_calls"]=(
            model.budget.calls_reserved if model else 0)
        status["reported_provider_usage"]=(
            model.budget.public_receipt() if model else {})
        status["provider_original_wire_evidence"]=model.events if model else []
        save(OUTPUT/"STATUS.json",status)
        print(json.dumps({
            "status":status["status"],
            "reader":status.get("reader_result_status"),
            "literal_observations":len(
                status.get("reader_literal_observations",[])),
            "source_anchored_unwritten_links":len(
                status.get("reader_proposed_unwritten_links",[])),
            "author":status.get("same_AI_author_decision"),
            "model_reader_report_delivered":status.get(
                "reader_report_delivered_to_author"),
            "changed":status.get("written_candidate_changed"),
            "requests":status["new_actual_provider_calls"],
            "max_requests":MAX_CALLS,
            "failure":status.get("failure_code"),
        },ensure_ascii=False),flush=True)
    return status

if __name__=="__main__":
    try:
        run()
    except Exception as error:
        print(json.dumps({
            "status":"PROVENANCE_OR_SETUP_BLOCKED_BEFORE_MODEL",
            "reason":safe_code(error),
            "no_model_retries":True,
        },ensure_ascii=False),flush=True)
        sys.exit(2)
