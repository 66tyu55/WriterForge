"""One genuinely author-CHOSEN DeepSeek V119 edit of old source-verified G turn.

Requires THREE actual historical provenance chains:
  #40110957161 original full G story (7 true wires, V117 signed state);
  #40151857245 same writer's source-anchored reader (2 true wires);
  #40153456601 same writer's source-attribution and unique LOOK_BACK_NOW
                  (1 true wire, verified current prose SHA).

This is NOT a retry asking the model to change its mind; it ALREADY did.
Use exactly one fresh paid DeepSeek response for the model's own V119 edit,
and only AFTER all originals, causal beat, and signed source check pass.
Every provider wire is preserved before parsing, including bad responses.
No reusing the OLD second turn as a new-branch sequel; until it is rewritten,
a good first-turn patch stays an unaccepted private branch and V117 is a
preflight only, NOT a new whole-chapter signed resume.
No hidden literary-critic model, repeated training, R2, Canon, main or
Railway deployment, automatic retry, or host-authored fiction.
"""
from __future__ import annotations
import json,os
from hashlib import sha256
from pathlib import Path

from experiments.wf_real_opera_cross_source_zero_model_receipt_20261025 import (
    provenance,source_file)
from experiments.wf_real_opera_author_source_attribution_once_20261025 import (
    digest as author_h)
from experiments.wf_real_new_scene_reader_first_control_20261025 import CAST
from writerforge.deepseek_flash_model import (
    DeepSeekFlashModel,FlashBudget,DeepSeekFlashError)
from writerforge.verified_flow import GroundedDraftPacket
from writerforge.writing_assist import (
    _reader_separates_written_and_inferred,_ai_decides_when_to_revisit,
    _self_edit_one_turn,_decode_json,SELF_EDIT_MODEL_MAX_TOKENS)
from writerforge.v96_causal_turns import check_turn
from writerforge.v114_external_story_state import (
    require_external_runtime,external_temporal_step)
from writerforge.v117_continuity_trace import preflight_continuation
from writerforge.narrative_core import new_graph,advance_graph

ATTESTATION=Path("wf_real_opera_prior_attestation_20261025")
OUTPUT=Path("wf_real_opera_author_selected_v119_20261025")
PROJECT="wf-original-night-opera-new-one-shot"
SCENE="winter-opera-hall"
REAL_OLD_ATTEST_RUN=40153456601
OLD_ATTEST_ARTIFACT=12583830221
CALL_LIMIT=1
TARGET_SOURCE_SHA="2a0d2827d51dc1197065cd21126e091a3fd44c4db3bb7d92048c3167d24f4dbd"
WRITER_SYSTEM=(
    "你仍然是写出这一段小说的原 DeepSeek 作家。"
    "你的先前决定已经由原供应商记录证明是 LOOK_BACK_NOW，"
    "但是否最终 KEEP、以及改哪句话和怎样写新句，仍由你自己决定。"
    "只提供原 WriterForge V119 所需的来源锁定 JSON 方案；"
    "source_sha256、expected_original 需逐字对应实际原稿。"
    "若原 beat 无前一事件，trace.parent_effect_quote 必须为 JSON null；"
    "trace.action_quote / effect_quote 必须逐字出现在你自己修改后的全文中。"
    "禁止制造新的源未支持的物品转移或角色已知秘密，"
    "也不能请宿主替你写一句小说。"
    "小说效果由你作为原作者判断，本流程不强制改稿、不打美学分数。"
)

def h(data):
    return sha256(data if type(data) is bytes else data.encode("utf8")).hexdigest()

def write(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,
                               sort_keys=True,indent=2),encoding="utf8")

def prior_real_writer_decision():
    original,older,reader_reply,_=provenance()
    manifest=json.loads(source_file(ATTESTATION,"STATUS.json"))
    if (manifest.get("status")!="ONE_REAL_AUTHOR_SOURCE_DECISION_SAVED" or
        manifest.get("new_real_provider_calls")!=1 or
        manifest.get("new_author_literary_decision")!="LOOK_BACK_NOW" or
        manifest.get("author_source_attribution_status")!=
            "SOURCE_ATTRIBUTIONS_RECORDED_LITERAL_ONLY" or
        manifest.get("current_prose_sha256")!=TARGET_SOURCE_SHA or
        manifest.get("earlier_prose_sha256")!=h(original["seed"]) or
        manifest.get("V119_called") is not False or
        type(manifest.get("provider_original_wires")) is not list or
        len(manifest["provider_original_wires"])!=1):
        raise RuntimeError("WF_AUTHENTIC_AUTHOR_LOOK_BACK_SOURCE_CHANGED")
    provenance_entry=manifest["provider_original_wires"][0]
    original_wire=source_file(ATTESTATION,"01-REAL_AUTHOR_WIRE.json")
    raw=source_file(ATTESTATION,"01-REAL_AUTHOR_PARSED_REPLY.json")
    private=source_file(
        ATTESTATION,"NEW_AUTHOR_WITH_PRIOR_QUOTES/ai-when-and-why-original.json")
    if (provenance_entry.get("original_wire_kept_before_parse") is not True or
        provenance_entry.get("stage")!="SAME_NOVELIST_DECIDES_WITH_SOURCE" or
        h(original_wire)!=provenance_entry.get("wire_sha256") or
        h(raw)!=provenance_entry.get("parsed_reply_sha256") or
        raw!=private or
        source_file(ATTESTATION,"G_CURRENT_UNCHANGED.md").decode("utf8")!=
            original["source"] or
        source_file(ATTESTATION,"SIGNED_EARLIER_UNCHANGED.md").decode("utf8")!=
            original["seed"]):
        raise RuntimeError("WF_AUTHENTIC_AUTHOR_LOOK_BACK_WIRE_CHANGED")
    if h(original["source"])!=TARGET_SOURCE_SHA:
        raise RuntimeError("WF_AUTHENTIC_AUTHOR_LOOK_BACK_TARGET_CHANGED")
    # Read previous REAL reader's original model answer by replaying it
    # through the exact same source-identity rules, without another model.
    prompt="只有原写作模型决定是否重写真实小说，所有源引用必须对应正文。"
    pkt=GroundedDraftPacket(
        project_id=PROJECT,scene_id=SCENE,snapshot_id=0,
        evidence=(),craft_ids=(),prompt=prompt,
        prompt_sha256=h(prompt))
    precheck_dir=OUTPUT/"REPLAY_ORIGINAL_READER_NO_PROVIDER"
    reader=_reader_separates_written_and_inferred(
        raw=original["first_raw"],turn_packet=pkt,
        ask_model=lambda *args,**kwargs:reader_reply,
        directory=precheck_dir,
        earlier_source=original["seed"],
        earlier_source_sha256=h(original["seed"]))
    if (reader["status"]!="SOURCE_ANCHORED_READER_HYPOTHESES" or
        len(reader["report"]["cross_source_links"])!=3):
        raise RuntimeError("WF_AUTHENTIC_AUTHOR_READER_EVIDENCE_CHANGED")
    source_decision=_ai_decides_when_to_revisit(
        raw=original["first_raw"],beat=original["beat"],accepted=(),
        turn_packet=pkt,ask_model=lambda *args,**kwargs:raw.decode("utf8"),
        directory=OUTPUT/"REPLAY_ORIGINAL_AUTHOR_DECISION_NO_PROVIDER",
        reader_report=reader["report"],
        earlier_source_for_attribution=original["seed"],
        source_identity_contract="bind_null_current")
    if (source_decision["decision"]!="LOOK_BACK_NOW" or
        source_decision["target_turn"]!="current" or
        source_decision["target_prose_sha256"]!=TARGET_SOURCE_SHA or
        original["source"].count(source_decision["source_quote"])!=1 or
        source_decision["focus"]!="sentence" or
        source_decision["receipt"].get(
            "cross_source_author_attribution_status")!=
            "SOURCE_ATTRIBUTIONS_RECORDED_LITERAL_ONLY"):
        raise RuntimeError("WF_AUTHENTIC_AUTHOR_REVISE_NOT_CONFIRMED")
    # Earlier archived Chapter 2 signed V117 remains an old historical
    # source, not the parent graph for the new revision branch.
    return original,source_decision,manifest,raw.decode("utf8"),pkt

class OneOriginalWriterV119:
    def __init__(self,secret,path):
        self.path=path
        self.events=[]
        self.budget=FlashBudget(
            max_calls=CALL_LIMIT,
            max_reserved_output_tokens=SELF_EDIT_MODEL_MAX_TOKENS,
            max_total_tokens=150000)
        self.client=DeepSeekFlashModel(
            api_key=secret,budget=self.budget,timeout_seconds=110,
            on_response_wire=self._wire)
    def _wire(self,data):
        if len(self.events)!=1:
            raise RuntimeError("WF_REAL_V119_WIRE_UNEXPECTED")
        (self.path/"01-AUTHOR_V119_PROVIDER_WIRE.json").write_bytes(data)
        self.events[-1]["original_wire_sha256"]=h(data)
        self.events[-1]["wire_saved_before_parsing"]=True
    def ask(self,packet,*,model,api_base,max_tokens):
        if (model is not None or api_base is not None or self.events or
            max_tokens!=SELF_EDIT_MODEL_MAX_TOKENS):
            raise RuntimeError("WF_REAL_V119_ONCE_ONLY")
        self.events.append({
            "stage":"ORIGINAL_AUTHOR_V119_ON_SELECTED_SOURCE",
            "requested_output_tokens":max_tokens,
            "prompt_sha256":h(packet.prompt),
            "wire_saved_before_parsing":False})
        outcome=self.client.ask_json(
            role="self_scene_writing",
            system=WRITER_SYSTEM,user=packet.prompt,max_tokens=max_tokens)
        raw=json.dumps(outcome,ensure_ascii=False,separators=(",",":"))
        (self.path/"01-AUTHOR_V119_DECODED_RESPONSE.json").write_text(
            raw,encoding="utf8")
        self.events[-1]["decoded_sha256"]=h(raw)
        return raw

def main():
    # Archive both real-source predecessor chains prior to inference.
    if OUTPUT.exists():
        raise RuntimeError("WF_REAL_V119_NEVER_OVERWRITE_PRIVATE_RESULT")
    OUTPUT.mkdir(parents=True)
    old,decision,history,old_writer_reply,pkt=prior_real_writer_decision()
    prose=old["source"]
    (OUTPUT/"ORIGINAL_G_FIRST_TURN_UNCHANGED.md").write_text(
        prose,encoding="utf8")
    (OUTPUT/"OLDER_AUTHOR_LOOK_BACK_ORIGINAL.json").write_text(
        old_writer_reply,encoding="utf8")
    (OUTPUT/"OLDER_G_SIGNED_PREVIOUS_CHAPTER_UNCHANGED.md").write_text(
        old["seed"],encoding="utf8")
    require_external_runtime()
    checkpoint=external_temporal_step(old["seed"],cast=CAST)
    # Separate provisional graph rooted BEFORE the originally written
    # second chapter, never derive from the old complete chapter's graph.
    draft_graph=new_graph(project_id=PROJECT,scene_id=SCENE)
    draft_graph=advance_graph(
        draft_graph,project_id=PROJECT,scene_id=SCENE,
        chapter_index=1,prose=old["seed"],events=())
    record={
        "format":"wf.real.provisional-one-turn-author-chosen-v119.v1",
        "status":"PREFLIGHT_SOURCE_ONLY_AND_REAL_AUTHOR_LOOKBACK_CONFIRMED",
        "original_G_run":40110957161,
        "original_double_source_reader_run":40151857245,
        "original_author_LOOK_BACK_run":REAL_OLD_ATTEST_RUN,
        "original_author_reply_sha256":h(old_writer_reply),
        "old_source_sha256":TARGET_SOURCE_SHA,
        "original_author_target_quote":decision["source_quote"],
        "original_author_reason":decision["reason"],
        "real_author_intended_reader_effect":decision["desired_effect"],
        "original_author_decision":"LOOK_BACK_NOW",
        "source_parent_tracked_by_V114":True,
        "signed_prior_source_and_old_full_chapter_unchanged":True,
        "old_complete_chapter_second_turn_not_reused_as_new_branch":True,
        "new_provider_max_calls":CALL_LIMIT,
        "new_completion_max_tokens":SELF_EDIT_MODEL_MAX_TOKENS,
        "model_retry_count":0,"user_canon_writes":0,"R2_writes":0,
        "new_literary_memory_owner":False,
        "literary_quality_independently_verified":False,
        "V117_full_new_chapter_signed":False,
        "all_real_prose_generated_only_by_original_model":True,
    }
    model=None
    try:
        secret=os.getenv("DEEPSEEK_API_KEY")
        if not isinstance(secret,str) or len(secret)<16:
            raise RuntimeError("WF_REAL_V119_ORIGINAL_AUTHOR_SECRET_NOT_AVAILABLE")
        model=OneOriginalWriterV119(secret,OUTPUT)
        old_state=checkpoint["reducer_result"]["candidate_state"]
        result,receipt=_self_edit_one_turn(
            raw=old["first_raw"],beat=old["beat"],accepted=(),
            project_id=PROJECT,scene_id=SCENE,
            turn_packet=pkt,ask_model=model.ask,
            round_limit=1,call_allowance=1,
            directory=OUTPUT/"V119_SAME_AUTHOR_PRIVATE_TRANSACTION",
            cast=CAST,previous_candidate_state=old_state,
            current_external_story_checkpoint=checkpoint,
            active_narrative_core=draft_graph,
            story_chapter_index=2,
            writer_attention={
                "reason":decision["reason"],
                "risk":decision["risk"],
                "desired_effect":decision["desired_effect"],
                "source_quote":decision["source_quote"],
                "focus":decision["focus"]})
        record["v119_source_transaction"]=receipt
        statuses=[entry.get("status") for entry in receipt.get("rounds",[])]
        record["V119_round_statuses"]=statuses
        changed=_decode_json(result)["prose"].strip()
        success=(changed!=prose and "PROVISIONALLY_REVISED" in statuses)
        record["new_provisional_first_turn_source_sha256"]=h(changed)
        record["new_candidate_first_turn_source_changed"]=success
        if success:
            check_turn(result,old["beat"],mode="causal_guard",accepted=())
            newcheckpoint=external_temporal_step(
                changed,cast=CAST,prior=checkpoint)
            v117=preflight_continuation(
                changed,checkpoint,project_id=PROJECT,
                chapter_index=2,cast=CAST)
            record.update({
                "V96_revised_first_turn_passed":True,
                "V114_recomputed_temporal_source_sha256":
                    newcheckpoint["source_sha256"],
                "V114_recomputed_checkpoint_sha256":
                    newcheckpoint["receipt_sha256"],
                "V117_source_preflight_ran":True,
                "V117_source_preflight_blocked":v117["blocked"],
                "V117_source_preflight_needs_review":v117["needs_review"],
                "V117_source_preflight_receipt":v117,
            })
            if v117["blocked"]:
                success=False
                record["new_candidate_first_turn_source_changed"]=False
                record["source_preflight_cannot_be_ignored"]=True
            else:
                (OUTPUT/"NEW_PRIVATE_FIRST_TURN_AFTER_V119.md").write_text(
                    changed,encoding="utf8")
                # Original turn2 has become potentially stale. No fake
                # branch selection or V117 full chapter resume.
                (OUTPUT/"ANONYMOUS_ORIGINAL_A.md").write_text(
                    prose,encoding="utf8")
                (OUTPUT/"ANONYMOUS_MODEL_REVISED_B.md").write_text(
                    changed,encoding="utf8")
                write(OUTPUT/"ANONYMOUS_UNBLIND_ONLY_AFTER_READING.json",{
                    "A":"previously valid real G first turn",
                    "B":"new same-writer V119 first-turn provisional rewrite",
                    "blind_human_review_completed":False,
                    "downstream_original_G_turn2_is_stale":True,
                    "full_revised_chapter_not_yet_validated":True,
                })
        if success:
            record["status"]="REAL_V119_FIRST_TURN_REVISED_PROVISIONAL_ONLY"
        else:
            record["status"]="REAL_V119_UNCHANGED_OR_STRICTLY_REJECTED"
        record["user_accepted_source_changed"]=False
    except Exception as exc:
        record["status"]="REAL_V119_UNCHANGED_OR_STRICTLY_REJECTED"
        err=str(exc)
        record["failure_code"]=(
            err[:155] if err.startswith("WF_") else type(exc).__name__)
    finally:
        record["new_real_provider_requests"]=(
            model.budget.calls_reserved if model else 0)
        record["actual_provider_usage"]=(
            model.budget.public_receipt() if model else {})
        record["real_original_model_wire_receipts"]=(
            model.events if model else [])
        record["V119_requested_only_after_old_model_LOOK_BACK"]=True
        record["new_full_chapter_and_all_downstream_state_rebuilt"]=False
        write(OUTPUT/"STATUS.json",record)
        print(json.dumps({
            "status":record["status"],
            "real_call_count":record["new_real_provider_requests"],
            "max_real_calls":CALL_LIMIT,
            "old_author_selected":"LOOK_BACK_NOW",
            "V119_round_statuses":record.get("V119_round_statuses"),
            "V117_preflight_blocked":record.get("V117_source_preflight_blocked"),
            "actual_first_turn_candidate_changed":record.get(
                "new_candidate_first_turn_source_changed",False),
            "full_new_chapter_signed":False,
            "human_literary_superiority_verified":False,
            "error":record.get("failure_code"),
        },ensure_ascii=False),flush=True)
    return record

if __name__=="__main__":
    main()
