"""ONE new source-verified cross-chapter same-author literary probe.

The model really wrote this opera scene earlier in full WriterForge G
(#40110957161). It changed original synthetic seed "ticket hidden in sleeve"
to first paragraph "ticket under an old costume in backstage box". Ordinary
self-review chose MOVE_ON; fresh single-source reader also supplied 3
internal-prose guesses but missed the previous written item state.

Reader sees TWO source-verified complete pieces without prior verdict/plan:
original signed Chapter 1 seed, then exact DeepSeek generated Chapter 2 turn.
The original DeepSeek model must itself identify any cross-source gap in its
own words and decide whether to revise. WF only checks exact quotes and
the same old V119/V96/V114 guards. Model may choose MOVE_ON.

Bound: max 3 genuine DeepSeek calls, no retry. No user novels, R2, training,
Canon, Studio promotion, main change, Railway or fake quality scores.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from hashlib import sha256
from experiments.wf_real_opera_source_sha_replay_20261025 import (
    get_verified_prior,ORIGINAL_SOURCE_SHA,PREVIOUS_GH_RUN,
    PREVIOUS_ARTIFACT,
)
from experiments.wf_real_new_scene_reader_first_control_20261025 import (
    SEED,CAST,GOAL,
)
from writerforge.deepseek_flash_model import (
    DeepSeekFlashModel,FlashBudget,DeepSeekFlashError)
from writerforge.writing_assist import (
    _reader_separates_written_and_inferred,
    _ai_decides_when_to_revisit,
    _self_edit_one_turn,
    _decode_json,
)
from writerforge.verified_flow import GroundedDraftPacket,WritingExecutionError
from writerforge.v96_causal_turns import (
    check_turn,V96CausalDraftError)
from writerforge.v114_external_story_state import (
    external_temporal_step,require_external_runtime,V114ExternalMemoryError)
from writerforge.narrative_core import (
    new_graph,advance_graph,NarrativeCoreError)

OUTPUT=Path("wf_real_opera_true_prior_cross_source_review_20261025")
MODEL="deepseek-flash"
MAX_CALLS=3
TOKENS={"CROSS_SOURCE_READER":1000,
        "ORIGINAL_AUTHOR_DECIDES":600,
        "V119_AUTHOR_ONLY_IF_LOOK_BACK":1800}
TOTAL_BUDGET=sum(TOKENS.values())

def h(value):
    return sha256(value.encode("utf8") if isinstance(value,str)
                  else value).hexdigest()

def jsonwrite(path,obj):
    path.write_text(json.dumps(
        obj,ensure_ascii=False,sort_keys=True,indent=2),encoding="utf8")

class RealOriginalWriter:
    def __init__(self,root):
        key=os.getenv("DEEPSEEK_API_KEY")
        if not isinstance(key,str) or len(key)<16:
            raise RuntimeError("WF_OPERA_REAL_EXISTING_WRITER_KEY_UNAVAILABLE")
        self.root=root
        self.events=[]
        self.budget=FlashBudget(max_calls=MAX_CALLS,
                                max_reserved_output_tokens=TOTAL_BUDGET,
                                max_total_tokens=150000)
        self.model=DeepSeekFlashModel(api_key=key,budget=self.budget,
                                      timeout_seconds=110,
                                      on_response_wire=self._wire)
    def _wire(self,content):
        if not self.events:
            raise RuntimeError("WF_OPERA_WIRE_WITHOUT_RECORDED_STAGE")
        event=self.events[-1]
        name=f"{len(self.events):02d}-{event['stage']}-provider-wire.json"
        (self.root/name).write_bytes(content)
        event["wire_sha256"]=h(content)
        event["original_provider_wire_preserved_before_parse"]=True
    def ask(self,packet,*,model,api_base,max_tokens):
        if model is not None or api_base is not None:
            raise RuntimeError("WF_OPERA_CROSS_MODEL_SWITCH_FORBIDDEN")
        stage=list(TOKENS)[len(self.events)] if (
            len(self.events)<MAX_CALLS) else None
        if stage is None or max_tokens!=TOKENS[stage]:
            raise RuntimeError("WF_OPERA_CROSS_SOURCE_BUDGET_OR_ORDER")
        if stage=="CROSS_SOURCE_READER":
            # The first model sees ONLY real prior and current prose,
            # never the developer's ticket discrepancy diagnosis.
            if ("原始前提冲突" in packet.prompt or
                "票据位置错误" in packet.prompt or
                "你上一次选择" in packet.prompt):
                raise RuntimeError("WF_OPERA_CROSS_READER_PREDICTED_ANSWER")
            system=(
                "你作为第一次读这段小说的独立读者，"
                "只依据两份按顺序排列的真实原文区分已写行动与"
                "你需要自己补出的推测。"
                "不写新的小说，不打分，不决定是否修改。"
                "逐字引用相应来源句。只返回严格有效 JSON 对象。")
        elif stage=="ORIGINAL_AUTHOR_DECIDES":
            system=(
                "你是同一篇小说的原创作者。读者可能有猜测，"
                "但只有你可以决定 MOVE_ON 或 LOOK_BACK_NOW。"
                "文学含义及最后创作选择由你负责，不要为了改稿率"
                "强迫自己回头，必须准确回传原文唯一引句。"
                "只输出合法 JSON 对象。")
        else:
            system=(
                "你仍然是同一篇作品的写作模型。"
                "只有你自己此前选择 LOOK_BACK_NOW 时才能生成修订。"
                "按原 V119 结构提供精确引用的替换小说句子，"
                "不造历史前因；若 beat.causal_parent=null，"
                "trace.parent_effect_quote 必须为 null。"
                "只输出严格 JSON，不能要求 WF 代写。")
        self.events.append({
            "stage":stage,"requested_output_tokens":max_tokens,
            "prompt_sha256":h(packet.prompt),
            "original_provider_wire_preserved_before_parse":False,
        })
        parsed=self.model.ask_json(
            role="self_scene_writing",system=system,
            user=packet.prompt,max_tokens=max_tokens)
        response=json.dumps(parsed,ensure_ascii=False,separators=(",",":"))
        (self.root/f"{len(self.events):02d}-{stage}-original-answer.json").write_text(
            response,encoding="utf8")
        self.events[-1]["original_reply_sha256"]=h(response)
        return response

def real_packet():
    goal=("这是从真实 G 未接受前章继续写作的原创戏楼小说。"
          "小说人物按已写事实自己选择是否继续；"
          "所有实际修订文本只有原模型产生。"+GOAL)
    return GroundedDraftPacket(
        project_id="wf-original-night-opera-new-one-shot",
        scene_id="winter-opera-hall",
        snapshot_id=0,evidence=(),craft_ids=(),
        prompt=goal,prompt_sha256=h(goal))

def run():
    verified=get_verified_prior()
    source=verified["source"]
    earlier=verified["seed"]
    if source!=_decode_json(verified["first_raw"])["prose"].strip():
        raise RuntimeError("WF_OPERA_SOURCE_NOT_SAME_REAL_G_TURN")
    if earlier!=SEED or h(source)!=ORIGINAL_SOURCE_SHA:
        raise RuntimeError("WF_OPERA_SIGNED_PRIOR_NOT_IDENTICAL")
    # Signature/graph backed by original V117, not hand-written R2 training.
    memory=verified["graph"]["memory"]["hot"]
    if not any(row["chapter"]==1 and row["source_sha256"]==h(SEED)
               for row in memory):
        raise RuntimeError("WF_OPERA_PRIOR_NOT_SIGNED_IN_V117")
    check_turn(verified["first_raw"],verified["beat"],
               mode="causal_guard",accepted=())
    require_external_runtime()
    seed_checkpoint=external_temporal_step(SEED,cast=CAST)
    graph=new_graph(project_id=real_packet().project_id,
                    scene_id=real_packet().scene_id)
    graph=advance_graph(
        graph,project_id=real_packet().project_id,
        scene_id=real_packet().scene_id,
        chapter_index=1,prose=SEED,events=())
    if OUTPUT.exists():
        raise RuntimeError("WF_OPERA_CROSS_REVIEW_OLD_OUTPUT_NOT_OVERWRITTEN")
    OUTPUT.mkdir(parents=True)
    (OUTPUT/"ORIGINAL_G_PRIOR_CHAPTER_ONLY_SOURCE.md").write_text(
        earlier,encoding="utf8")
    (OUTPUT/"ORIGINAL_G_CURRENT_TURN_ONLY_SOURCE.md").write_text(
        source,encoding="utf8")
    writer=None
    record={
        "format":"wf.genuine.prior-chapter-opera-source-reader-followup.v1",
        "status":"VERIFIED_PUBLISHED_PROVIDER_AND_SIGNED_G_SOURCE",
        "earlier_source_sha256":h(earlier),
        "current_original_sha256":h(source),
        "genuine_parent_actions_run":PREVIOUS_GH_RUN,
        "genuine_parent_artifact":PREVIOUS_ARTIFACT,
        "previous_author_move_on_was_invalid_due_to_null_SHA":True,
        "prior_written_vs_current_written_both_shown_in_reader_stage":True,
        "preidentified_item_error_not_sent_to_model":True,
        "model_permitted_to_keep_source":True,
        "max_new_provider_calls":MAX_CALLS,"output_tokens_reserved_cap":TOTAL_BUDGET,
        "provider_retries":0,
        "canonical_writes":0,"user_R2_writes":0,
        "training_runs":0,"literary_quality_verified":False,
    }
    try:
        writer=RealOriginalWriter(OUTPUT)
        reader=_reader_separates_written_and_inferred(
            raw=verified["first_raw"],turn_packet=real_packet(),
            ask_model=writer.ask,directory=OUTPUT/"independent-signed-reader",
            earlier_source=earlier,earlier_source_sha256=h(earlier))
        record.update({
            "reader_status":reader["status"],
            "reader_original_source_check":reader["receipt"],
            "reader_uncertainty":(reader["report"]["reader_uncertainty"]
                                  if reader["report"] else None),
            "unverified_cross_source_hypotheses":(
                reader["report"]["cross_source_links"]
                if reader["report"] else []),
            "reader_output_is_not_confirmed_story_truth":True,
        })
        if reader["status"]!="SOURCE_ANCHORED_READER_HYPOTHESES":
            record["status"]="REAL_READER_SOURCE_SCHEMA_FAILED_NO_AUTHOR_FORCED"
            return record
        author=_ai_decides_when_to_revisit(
            raw=verified["first_raw"],beat=verified["beat"],accepted=(),
            turn_packet=real_packet(),ask_model=writer.ask,
            directory=OUTPUT/"original-author-own-decision",
            reader_report=reader["report"],
            source_identity_contract="bind_null_current")
        record.update({
            "author_original_decision":author["decision"],
            "author_original_reason":author.get("reason"),
            "author_original_quote":author.get("source_quote"),
            "author_decision_source_receipt":author["receipt"],
            "author_offered_explicit_same_real_prior_quote_report":(
                author["receipt"].get("unverified_reader_input_delivered")),
        })
        final=source
        if author["decision"]=="LOOK_BACK_NOW":
            patched,revision=_self_edit_one_turn(
                raw=verified["first_raw"],beat=verified["beat"],accepted=(),
                project_id=real_packet().project_id,scene_id=real_packet().scene_id,
                turn_packet=real_packet(),ask_model=writer.ask,
                round_limit=1,call_allowance=1,
                directory=OUTPUT/"V119-by-original-author-only",
                cast=CAST,
                previous_candidate_state=seed_checkpoint[
                    "reducer_result"]["candidate_state"],
                current_external_story_checkpoint=seed_checkpoint,
                active_narrative_core=graph,
                story_chapter_index=2,
                writer_attention={
                    "reason":author.get("reason"),
                    "risk":author.get("risk"),
                    "desired_effect":author.get("desired_effect"),
                    "source_quote":author.get("source_quote"),
                    "focus":author.get("focus")})
            record["writer_V119_source_transaction"]=revision
            candidate=_decode_json(patched)["prose"].strip()
            if candidate!=source:
                check_turn(patched,verified["beat"],mode="causal_guard",accepted=())
                checkpoint=external_temporal_step(candidate,cast=CAST,
                                                   prior=seed_checkpoint)
                record["V114_rebuilt_checkpoint_sha256"]=checkpoint[
                    "receipt_sha256"]
                final=candidate
        (OUTPUT/"FINAL_NOT_ACCEPTED_REAL_SOURCE.md").write_text(
            final,encoding="utf8")
        record["model_did_change_accepted_candidate"]=final!=source
        record["final_source_sha256"]=h(final)
        record["status"]="REAL_READER_AND_AUTHOR_FINISHED"
    except Exception as exc:
        record["status"]="REAL_MODEL_OR_WF_REJECTED_UNCHANGED_SOURCE"
        # Do not print provider error bodies, credentials, or full prompts.
        code=str(exc)
        record["error_code"]=(code if
            len(code)<=160 and code.startswith("WF_")
            else type(exc).__name__)
    finally:
        record["actual_new_provider_calls"]=(writer.budget.calls_reserved
                                                if writer else 0)
        record["actual_provider_usage"]=(writer.budget.public_receipt()
                                          if writer else {})
        record["real_provider_wire_provenance"]=(writer.events if writer else [])
        savepath=OUTPUT/"STATUS.json"
        jsonwrite(savepath,record)
        print(json.dumps({
            "status":record["status"],
            "source_earlier_sha256":h(earlier),
            "source_current_sha256":h(source),
            "reader_status":record.get("reader_status"),
            "cross_source_links":len(
                record.get("unverified_cross_source_hypotheses",[])),
            "real_author_choice":record.get("author_original_decision"),
            "candidate_rewritten":record.get("model_did_change_accepted_candidate"),
            "provider_calls":record["actual_new_provider_calls"],
            "cap":MAX_CALLS,
            "error":record.get("error_code"),
        },ensure_ascii=False),flush=True)
    return record

if __name__=="__main__":
    run()
