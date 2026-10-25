"""0.T: single real follow-up of previously sealed B arm, never re-generate old writing.

The SAME DeepSeek Flash novelist first reads its own authentic two stages
as an independent reader, then chooses KEEP or LOOK_BACK_NOW. If revising,
existing V119/V96/V114/V117 source rules apply, and the SAME novelist writes
the invalidated downstream stage anew (or its next small stage).
No book original is supplied to this job; exact prior model wire hashes,
prose hashes, prompt provenance and existing signed statuses are checked
before any new provider call. No other critic, literary judge, R2, Canon,
new memory owner or unbounded retry.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import os
import re

from writerforge.deepseek_flash_model import DeepSeekFlashModel, FlashBudget
from writerforge.verified_flow import GroundedDraftPacket
from writerforge.v96_causal_turns import (
    check_turn, make_turn_instructions, parse_turn_outline,
)
from writerforge.v114_external_story_state import (
    external_temporal_step, require_external_runtime,
)
from writerforge.v117_continuity_trace import (
    preflight_continuation, make_resume, read_resume,
)
from writerforge.narrative_core import (
    new_graph, advance_graph, record_chapter_memory,
)
from writerforge.writing_assist import (
    _reader_separates_written_and_inferred,
    _ai_decides_when_to_revisit, _self_edit_one_turn,
)
from experiments.wf_fanren_staged_source_ab_0t import (
    PROJECT, OUTLINE, BEATS, CAST, sha, sentence_lengths,
)

PRIOR = Path("wf0t_prior_paired_originals")
OUT = Path("wf0t_real_B_two_source_repair_20261025")
PRIOR_RUN = 40163959949
PRIOR_B_FIRST = "e24ac2cd07a9a2e94b0923bbbdec9a0cffaca3db2da940610ffcf6a7c26716b2"
PRIOR_B_SECOND = "eacda836547a0e3576c16be85e44ce7bbb4dbafb1a74096cbc5465b8b99af4b0"
PRIOR_WIRES = {
    "B-T1-prose-04": "650ea4d78a2fc87ca1f6bb3b208c4c90c4f18f1a605c9858e3ed87849ce257e8",
    "B-T2-prose-06": "e496ecb8a2a1cd125bfcecfb3af7efa917b395116ea2831bb482860063e8992c",
}
PRIOR_REFERENCE_SHA = (
    "bbe89973f914419f52bece2cb86a9d80e0e35ad037401f91a98f2321365a92be",
    "ad3f85a17cba44bc73dbb593689d808ed382633a6e9d0249b0134233410064bb",
)
SCENE = "staged-0t-b"    # matches unchanged original B candidate
MAX_CALLS = 6
MAX_OUTPUT = 8000
COMPETING_SPANS = (
    "绳结还系在木桩上",
    "绳子被人从桩头解下来",
)

def safe(value,reason):
    if not value:
        raise RuntimeError(reason)

def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf8")

def read_old_real_sources():
    """Never use synthetic text as purported real model evidence."""
    manifest=json.loads((PRIOR/"STATUS.json").read_text("utf8"))
    safe(manifest.get("format")=="wf.0t.fanren-private-readonly-staged-ab.v1" and
         manifest.get("complete_anonymous_pair") is True and
         manifest.get("same_model_actual_provider_calls")==6 and
         manifest.get("reference",{}).get("book_source_sha256")==
            "2fc1698410418bf136448807335c6359bf515b75e6f9c1e1d1f443a1c928e6cc" and
         manifest.get("reference",{}).get("reference_window_sha256")==
            list(PRIOR_REFERENCE_SHA),
         "WF0T_OLD_AUTHENTIC_PAIR_MANIFEST_INVALID")
    reported={
        event["label"]:event for event in manifest["provider_calls_with_private_wire_hash"]
    }
    documents=[]
    for idx,(label,source_sha) in enumerate(zip(PRIOR_WIRES,(
            PRIOR_B_FIRST,PRIOR_B_SECOND)),1):
        path=PRIOR/"B"/f"stage-{idx:02d}-real-author-prose.md"
        prose=path.read_text("utf8")
        safe(sha(prose)==source_sha and 80<=len(prose)<=1024,
             "WF0T_PINNED_WRITER_PROSE_CHANGED")
        wire=(PRIOR/"B"/"provider-originals"/(label+".json")).read_bytes()
        safe(sha(wire)==PRIOR_WIRES[label] and
             reported[label]["provider_wire_sha256"]==sha(wire),
             "WF0T_PINNED_ORIGINAL_PROVIDER_WIRE_CHANGED")
        packet=json.loads(wire)
        safe(packet.get("model")=="deepseek-flash" and
             len(packet.get("choices",()))==1 and
             packet["choices"][0].get("finish_reason")=="stop",
             "WF0T_PROVIDER_REAL_IDENTITY_INVALID")
        original=json.loads(packet["choices"][0]["message"]["content"])
        safe(set(original)=={"prose","trace"} and original["prose"].strip()==prose,
             "WF0T_MODEL_WIRE_DIFFERS_FROM_PROSE")
        raw=json.dumps(original,ensure_ascii=False,separators=(",",":"))
        safe(sha(raw)==reported[label]["decoded_model_reply_sha256"],
             "WF0T_AUTHORED_JSON_BYTE_HASH_CHANGED")
        documents.append(raw)
    prior_status=json.loads((PRIOR/"B"/"STATUS.json").read_text("utf8"))
    safe(prior_status["stages_completed"]==2 and
         prior_status["status"]=="COMPLETE_UNACCEPTED_TWO_STAGE_WF_CANDIDATE" and
         not prior_status["author_revision_observed"] and
         not prior_status["valid_author_revision_and_downstream"],
         "WF0T_FORK_NOT_GENUINE_INITIAL_B")
    step1=check_turn(documents[0],BEATS[0],mode="causal_guard",
                     accepted=(),max_prose_chars=1024)
    step2=check_turn(documents[1],BEATS[1],mode="causal_guard",
                     accepted=(step1,),max_prose_chars=1024)
    stages=json.loads((PRIOR/"B"/"source-stage-receipts.json").read_text("utf8"))
    safe([x["actual_writer_prose_sha256"] for x in stages]==[
             PRIOR_B_FIRST,PRIOR_B_SECOND] and
         [x["reference_window_sha256"] for x in stages]==list(PRIOR_REFERENCE_SHA),
         "WF0T_FROZEN_SOURCE_RECEIPTS_CHANGED")
    safe(all(earlier in step2["prose"] for earlier in COMPETING_SPANS),
         "WF0T_PREDECLARED_CASE_SOURCE_ANCHORS_MISSING")
    # Actual upstream reducers rather than trusting prior acceptance labels.
    checkpoint1=external_temporal_step(step1["prose"],cast=CAST)
    check2=preflight_continuation(step2["prose"],checkpoint1,
                                  project_id=PROJECT,chapter_index=1,cast=CAST)
    safe(not check2["blocked"] and not check2["needs_review"],
         "WF0T_ORIGINAL_B_SOURCE_NO_LONGER_VALID")
    checkpoint2=external_temporal_step(step2["prose"],cast=CAST,prior=checkpoint1)
    return (documents[0],documents[1],step1,step2,checkpoint1,checkpoint2)

class SameWriter:
    """Finite provider requests; every actual wire saved before JSON decoding."""
    def __init__(self,key):
        self.budget=FlashBudget(
            max_calls=MAX_CALLS,
            max_reserved_output_tokens=MAX_OUTPUT,
            max_total_tokens=150000)
        self.events=[]
        self.active=None
        self.client=DeepSeekFlashModel(
            api_key=key,budget=self.budget,timeout_seconds=110,
            on_response_wire=self.save_original_wire)
    def save_original_wire(self,raw):
        safe(type(raw) is bytes and self.active is not None,
             "WF0T_UNOWNED_PROVIDER_WIRE")
        path=OUT/"provider-wires"/(self.active+"-original.json")
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(raw)
        self.events[-1]["wire_sha256"]=sha(raw)
        self.events[-1]["source_saved_before_schema_validation"]=True
    def call(self,stage,packet,*,max_tokens):
        safe(stage in ("source-reader","author-choice","v119-edit",
                       "new-third-plan","new-downstream-prose") and
             len(self.events)<MAX_CALLS and
             max_tokens in (600,850,1000,1450,1800),
             "WF0T_SECOND_SESSION_STAGE_OR_BUDGET_INVALID")
        self.active=f"{len(self.events)+1:02d}-{stage}"
        self.events.append({
            "stage":stage,"max_tokens":max_tokens,
            "prompt_sha256":sha(packet.prompt),
            "same_original_novelist":True})
        system=(
            "你是本篇《潮簿》小说同一个创作 AI，"
            "独立负责小说全部文字和审美选择。"
            "只返回符合当前协议的 JSON 对象，不解释软件操作。"
        )
        result=self.client.ask_json(
            role="self_scene_writing",system=system,
            user=packet.prompt,max_tokens=max_tokens)
        raw=json.dumps(result,ensure_ascii=False,separators=(",",":"))
        (OUT/"provider-wires"/(self.active+"-decoded-original.json")).write_text(
            raw,encoding="utf8")
        self.events[-1]["decoded_sha256"]=sha(raw)
        return raw

def packet(prompt):
    return GroundedDraftPacket(
        project_id=PROJECT,scene_id=SCENE,snapshot_id=0,
        evidence=(),craft_ids=(),
        prompt=prompt,prompt_sha256=sha(prompt))

def write_new_prose(model,*,beat,accepted,checkpoint,stage):
    """Writer chooses sentences; WF only supplies actually written parents."""
    prior="\n\n".join(x["prose"] for x in accepted)
    prompt=(
        "【同一小说作者重新续写：仅依据目前仍有效的实际原稿】"
        +OUTLINE+
        "\n【前史原文字节，仅未被撤销的版本有效】"+prior+
        "\n【上一段可确证后果】"+
        json.dumps(accepted[-1]["effect_quote"],ensure_ascii=False)+
        "\n这一轮只写下一小片段，约250–600汉字；"
        "不要生成整个第一章或跨到其他章节，"
        "不得复制已经失效的下游原句，不要突然发明人物已知道的秘密。"+
        make_turn_instructions(beat,mode="causal_guard",accepted=tuple(accepted))
    )
    safe(len(prompt)<18000,"WF0T_NEW_DOWNSTREAM_CONTEXT_BUDGET")
    raw=model.call("new-downstream-prose",packet(prompt),max_tokens=1450)
    doc=json.loads(raw)
    if set(doc)=={"type","prose","trace"} and doc.get("type")=="json_object":
        doc={k:v for k,v in doc.items() if k!="type"}
        raw=json.dumps(doc,ensure_ascii=False,separators=(",",":"))
    safe(set(doc)=={"prose","trace"} and
         80<=len(doc["prose"].strip())<=1024,
         "WF0T_NEW_WRITER_TURN_NOT_SMALL_SOURCE")
    verified=check_turn(raw,beat,mode="causal_guard",
                        accepted=tuple(accepted),max_prose_chars=1024)
    continuity=preflight_continuation(
        verified["prose"],checkpoint,
        project_id=PROJECT,chapter_index=1,cast=CAST)
    write_json(OUT/"new-source-v117-preflight.json",continuity)
    safe(not continuity["blocked"] and not continuity["needs_review"],
         "WF0T_NEW_DOWNSTREAM_SOURCE_RISK_HELD")
    state=external_temporal_step(
        verified["prose"],cast=CAST,prior=checkpoint)
    return verified,state

def new_third_beat(model,accepted):
    """The novelist plans the next event, not the software."""
    source="\n\n".join(x["prose"] for x in accepted)
    prompt=(
        "【小说作者自行制定下一小段事件目标】"
        "此前已经完成 t01 和 t02 两个实际小段。"
        "你只能规划一个尚未写出的 t03 小段。"
        "不得重复旧情节，亦不得预写整个章节。"
        "\n【现存故事正文】"+source+
        "\n【紧邻 t02 已写的后果】"+
        json.dumps(accepted[-1]["effect_quote"],ensure_ascii=False)+
        "\n只返回严格 JSON 对象，恰好一个键 turn，"
        "turn 是对象，恰好字段 id='t03',"
        "kind(action/decision/reversal/setup/dialogue/quiet/aftermath/transition),"
        "actor,goal(8-220个字符),causal_parent(t02 或 null),craft_focus(0-2个 V96 有效技巧)。"
        "你自己选择文学目标、人物行动和节奏，WF 不替你写下一段。"
    )
    raw=model.call("new-third-plan",packet(prompt),max_tokens=850)
    value=json.loads(raw)
    if set(value)=={"type","turn"} and value["type"]=="json_object":
        value={"turn":value["turn"]}
    safe(set(value)=={"turn"} and type(value["turn"]) is dict,
         "WF0T_THIRD_AUTHOR_BEAT_SCHEMA_INVALID")
    b=value["turn"]
    safe(b.get("id")=="t03","WF0T_THIRD_AUTHOR_BEAT_ID_INVALID")
    joined=json.dumps({"turns":[*BEATS,b]},ensure_ascii=False)
    parse_turn_outline(joined)
    return b

def signed_new_candidate(accepted):
    manuscript="\n\n".join(x["prose"] for x in accepted)
    place=OUT/"NEW_UNACCEPTED_MODEL_MANUSCRIPT.md"
    place.write_text(manuscript,encoding="utf8")
    final_checkpoint=external_temporal_step(manuscript,cast=CAST)
    graph=new_graph(project_id=PROJECT,scene_id=SCENE)
    graph=advance_graph(graph,project_id=PROJECT,scene_id=SCENE,
                        chapter_index=1,prose=manuscript,events=[])
    graph=record_chapter_memory(graph,project_id=PROJECT,scene_id=SCENE,
                                chapter_index=1,source_path=str(place),prose=manuscript)
    signed=make_resume(project_id=PROJECT,scene_id=SCENE,
                       chapter_index=1,checkpoint=final_checkpoint,
                       unified_narrative_core=graph)
    read_resume(signed,project_id=PROJECT,scene_id=SCENE)
    return signed

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    status={
        "format":"wf.0t.real-previous-B-author-repair-and-downstream.v1",
        "old_paid_calls_replayed_not_regenerated":6,
        "prior_run_id":PRIOR_RUN,
        "max_new_paid_calls":MAX_CALLS,
        "max_output_reserved":MAX_OUTPUT,
        "original_book_source_never_loaded":True,
        "new_paid_calls":0,"original_six_calls_not_billed_again":True,
        "no_external_critic":True,"same_novelist_writes_every_word":True,
        "real_safe_repair_plus_new_downstream":False,
        "literary_quality_not_verified":True,
        "canon_writes":0,"R2_writes":0,"main_modified":False,
        "Railway_deployments":0,"historical_negative_examples_untouched":True,
    }
    novelist=None
    try:
        require_external_runtime()
        raw1,raw2,one,two,cp1,cp2=read_old_real_sources()
        status.update(
            verified_original_first_sha256=PRIOR_B_FIRST,
            verified_original_second_sha256=PRIOR_B_SECOND,
            sealed_pair_source_replayed_no_model_calls=True,
            historical_second_turn_reader_had_no_own_review=True,
        )
        key=os.getenv("DEEPSEEK_API_KEY","")
        safe(len(key)>=16,"WF0T_EXISTING_NOVELIST_KEY_MISSING")
        novelist=SameWriter(key)
        source_packet=packet("作者的真实两段已经通过 SHA 验证，当前只做来源审阅。")
        # Step 1: identical novelist, independent manuscript-only context.
        def ask(stage):
            def adapter(p,*,model,api_base,max_tokens):
                safe(model is None and api_base is None,
                     "WF0T_AUTHOR_PROVIDER_CHANGED")
                return novelist.call(stage,p,max_tokens=max_tokens)
            return adapter
        reader=_reader_separates_written_and_inferred(
            raw=raw2,turn_packet=source_packet,
            ask_model=ask("source-reader"),
            directory=OUT/"source-only-reader",
            earlier_source=one["prose"],
            earlier_source_sha256=sha(one["prose"]),
            compact_source_review=True)
        status["independent_same_author_reader_status"]=reader["status"]
        status["reader_inferred_current_links"]=len(
            (reader.get("report") or {}).get("inferred_links",[]))
        status["reader_inferred_cross_links"]=len(
            (reader.get("report") or {}).get("cross_source_links",[]))
        safe(reader["status"]=="SOURCE_ANCHORED_READER_HYPOTHESES",
             "WF0T_READER_SOURCE_QUOTE_FAILED_NO_FORCED_EDIT")

        # Step 2: original AI alone decides; reader hypotheses not facts.
        source_context=(
            "【原创大纲（不是已发生事实）】"+OUTLINE+
            "\n【WF 真正已有的上一段候选状态】"+
            json.dumps(cp1["reducer_result"]["candidate_state"],
                       ensure_ascii=False)[:3300]+
            "\n【原作者能否改写只由本人决定，WF 不硬推修改】"
        )
        choice=_ai_decides_when_to_revisit(
            raw=raw2,beat=BEATS[1],accepted=(one,),
            turn_packet=packet(source_context),
            ask_model=ask("author-choice"),
            reader_report=reader["report"],
            source_identity_contract="bind_null_current",
            directory=OUT/"author-own-decision")
        write_json(OUT/"author-choice-validated.json",{
            "decision":choice["decision"],
            "target_turn":choice.get("target_turn"),
            "reason":choice.get("reason"),
            "risk":choice.get("risk"),
            "desired_effect":choice.get("desired_effect"),
            "source_quote":choice.get("source_quote"),
            "receipt":choice["receipt"],
        })
        status["true_author_decision"]=choice["decision"]
        status["author_chose_which_turn"]=choice.get("target_turn")
        safe(choice["decision"] in ("MOVE_ON","LOOK_BACK_NOW"),
             "WF0T_AUTHOR_SIGNAL_INVALID")
        if choice["decision"]=="MOVE_ON":
            status["status"]="AUTHOR_KEPT_NO_REPAIR_DO_NOT_PRETEND_SUCCESS"
            return

        target=choice["target_turn"]
        safe(target in ("current","previous"),
             "WF0T_UNSUPPORTED_AUTHOR_REWIND")
        prior=target=="previous"
        target_raw=raw1 if prior else raw2
        target_beat=BEATS[0] if prior else BEATS[1]
        target_accepted=() if prior else (one,)
        checkpoint_state=(
            {} if prior else cp1["reducer_result"]["candidate_state"])
        target_checkpoint=cp1 if prior else cp2
        edit,receipt=_self_edit_one_turn(
            raw=target_raw,beat=target_beat,accepted=target_accepted,
            project_id=PROJECT,scene_id=SCENE,
            turn_packet=packet(source_context),
            ask_model=ask("v119-edit"),
            round_limit=2,call_allowance=2,
            directory=OUT/"source-first-edits",
            previous_candidate_state=checkpoint_state,
            current_external_story_checkpoint=target_checkpoint,
            cast=CAST,
            writer_attention={
                "reason":choice.get("reason"),
                "risk":choice.get("risk"),
                "desired_effect":choice.get("desired_effect"),
                "source_quote":choice.get("source_quote"),
                "focus":choice.get("focus"),
            },
            story_chapter_index=1,
        )
        write_json(OUT/"edit-receipt.json",receipt)
        status["v119_attempted_round_statuses"]=[
            row.get("status") for row in receipt.get("rounds",())]
        old_text=json.loads(target_raw)["prose"].strip()
        new_doc=json.loads(edit)
        safe(new_doc["prose"].strip()!=old_text,
             "WF0T_NO_SOURCE_CHANGED_KEEP_OR_INVALID_REVISION")
        changed=check_turn(edit,target_beat,mode="causal_guard",
                           accepted=target_accepted,max_prose_chars=1024)
        before,after=(
            (None,None) if prior else
            (preflight_continuation(
                changed["prose"],cp1,project_id=PROJECT,
                chapter_index=1,cast=CAST),None)
        )
        if before is not None:
            write_json(OUT/"repaired-current-preflight.json",before)
            safe(not before["blocked"] and not before["needs_review"],
                 "WF0T_REVISED_CURRENT_SOURCE_NOT_CONTINUITY_CLEAR")

        if prior:
            # Undo old T2 and its descendant state: NEVER reuse original T2.
            repaired_cp1=external_temporal_step(changed["prose"],cast=CAST)
            downstream,state=write_new_prose(
                novelist,beat=BEATS[1],accepted=(changed,),
                checkpoint=repaired_cp1,stage=2)
            adopted=(changed,downstream)
            status["invalidated_downstream"]=PRIOR_B_SECOND
            status["rewrote_original_second_turn"]=True
        else:
            repaired_cp2=external_temporal_step(
                changed["prose"],cast=CAST,prior=cp1)
            beat3=new_third_beat(novelist,(one,changed))
            write_json(OUT/"third-author-chosen-beat.json",beat3)
            next_,state=write_new_prose(
                novelist,beat=beat3,
                accepted=(one,changed),checkpoint=repaired_cp2,stage=3)
            adopted=(one,changed,next_)
            status["invalidated_downstream"]="new small following turn"
            status["rewrote_original_second_turn"]=False
        sign=signed_new_candidate(adopted)
        status.update({
                "status":"REAL_AUTHOR_REPAIR_AND_NEW_DOWNSTREAM_CANDIDATE",
                "changed_source_sha256":sha(changed["prose"]),
                "source_rewrite_model_only":True,
                "revised_turn_physical_claims_still_literal":[
                    phrase in changed["prose"] for phrase in COMPETING_SPANS],
                "new_writer_prose_sha256":sha(adopted[-1]["prose"]),
                "signed_new_unaccepted_resume_sha256":sign["receipt_sha256"],
                "real_safe_repair_plus_new_downstream":True,
                "author_accepted":False,
                "human_blind_review":"NOT_PERFORMED",
            }
        )
    except Exception as exc:
        err=str(exc)
        if not re.fullmatch(r"WF[A-Z0-9_:\-]{3,180}",err):
            err=type(exc).__name__+":FAILED_CLOSED"
        status.update(status="FAILED_OR_HELD_NO_RETRY",
                      reason_code=err,real_safe_repair_plus_new_downstream=False)
    finally:
        if novelist is not None:
            status["new_paid_calls"]=novelist.budget.calls_reserved
            status["reported_usage"]=novelist.budget.public_receipt()
            status["provider_source_sha_receipts"]=novelist.events
        write_json(OUT/"STATUS.json",status)
        print("WF0T_REPAIR_REAL_RESULT "+json.dumps({
            "status":status.get("status"),
            "old_authentic_calls_replayed":6,
            "new_model_calls":status["new_paid_calls"],
            "same_author_decision":status.get("true_author_decision"),
            "revision_and_regenerated_downstream_verified":
                status["real_safe_repair_plus_new_downstream"],
            "literary_quality_not_verified":True,
        },ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
