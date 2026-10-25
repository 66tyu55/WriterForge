"""One bounded post-B2 real-author repair of a genuine WF 0.T candidate.

Read bytes from the EXISTING completed provider-originals of the genuine
2026-10-25 A/B run. We do NOT invent a defective paragraph, pretend
a simulated manuscript is real, or replace the writer's literary choice.

The current source shows the same cord held, tied and untied ambiguously.
WF presents the exact writer-owned source, not an invented fix. The original
DeepSeek novelist is free to MOVE_ON. If it chooses LOOK_BACK_NOW, only it
writes a V119 source-locked replacement; WF re-runs V96/V114/V117, invalidates
the former signed candidate and asks that same model for a NEW third turn.
No R2, production Canon, main or Railway write; no second literary judge.
"""
from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path

from experiments import wf_fanren_staged_source_ab_0t as exp
from writerforge.v96_causal_turns import check_turn, make_turn_instructions
from writerforge.v114_external_story_state import external_temporal_step, require_external_runtime
from writerforge.v117_continuity_trace import preflight_continuation, make_resume, read_resume
from writerforge.narrative_core import new_graph, advance_graph, record_chapter_memory
from writerforge.writing_assist import _ai_decides_when_to_revisit, _self_edit_one_turn

OUT=Path("wf0t_replay_real_B2_source_repair")
INPUT=Path("wf0t_genuine_input")
MAX_NEW_PAID_CALLS=5
MAX_NEW_RESERVED_OUTPUT_TOKENS=7100
ORIGINAL_B1_SHA="e24ac2cd07a9a2e94b0923bbbdec9a0cffaca3db2da940610ffcf6a7c26716b2"
ORIGINAL_B2_SHA="eacda836547a0e3576c16be85e44ce7bbb4dbafb1a74096cbc5465b8b99af4b0"
EXPECTED_B_ORIGINAL_RESUME="1b51ed5871e5626832508d1d20ecb5029560ce37530429217c20fe79569fe48d"
NEXT_BEAT={
    "id":"t03","kind":"decision","actor":"林栖",
    "goal":"基于前两段实际已发生的潮簿与绳结证据，自主选择下一行动；保留悬念但不可跳过实物变化的前因。",
    "causal_parent":"t02","craft_focus":[]
}
READER_HYPOTHESIS=(
    "【来自实际已写第二段的可复核来源疑问：不是作家的文学裁决】"
    "同一段开头包含原作者写的连续字串："
    "“手里攥着那截麻绳，绳结还系在木桩上，只是绳子被人从桩头解下来”。"
    "此处同一截绳子的持有位置、绳结究竟还系着还是已经解开，"
    "可能令读者对实际发生的转移过程产生疑问。"
    "请你作为原作者自行判断：这是真正应该修改的源语句问题，"
    "还是有意留白、符合物理动作、应该保留的表达。"
    "选择 MOVE_ON 就不改；若你确实认为需要改，就选择 LOOK_BACK_NOW，"
    "指定唯一存在于原文中的 evidence_quote，指出读者认知风险。"
    "软件不得替你判断或生成新句。"
)

def truth(condition,reason):
    if not condition:
        raise RuntimeError(reason)

def read_json(path):
    return json.loads(path.read_text(encoding="utf8"))

def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf8")

def real_archived_turn(label,receipt_sha,beat,accepted):
    original=read_json(INPUT/"B"/"provider-originals"/(label+".json"))
    truth(original["choices"][0]["finish_reason"]=="stop",
          "WF0T_ARCHIVED_PROVIDER_COMPLETION_UNSAFE")
    raw=original["choices"][0]["message"]["content"]
    candidate=exp.canonical_response(raw)
    doc=json.loads(candidate)
    truth(exp.sha(doc["prose"])==receipt_sha,
          "WF0T_ARCHIVED_GENUINE_PROSE_SHA_MISMATCH")
    checked=check_turn(candidate,beat,mode="causal_guard",accepted=accepted,
                       max_prose_chars=1024)
    truth(checked["prose"]==doc["prose"],
          "WF0T_ARCHIVED_WF_ALTERED_PROSE")
    return candidate,checked

class CapWriter(exp.PaidSameAuthor):
    def __init__(self,key,root):
        super().__init__(key,root)
        self.reserved.max_calls=MAX_NEW_PAID_CALLS
        self.reserved.max_reserved_output_tokens=MAX_NEW_RESERVED_OUTPUT_TOKENS
    def call(self,arm,stage,name,packet,max_tokens,*,system):
        truth(self.reserved.calls_reserved<MAX_NEW_PAID_CALLS,
              "WF0T_REPAIR_EXACT_CALL_CAP_REACHED")
        return super().call(arm,stage,name,packet,max_tokens,system=system)

def run_real_B2_followthrough():
    result={
        "format":"wf.0t.one-genuine-B2-source-first-author-repair.v1",
        "source_pilot_run_id":40163959949,
        "source_B1_prose_sha256":ORIGINAL_B1_SHA,
        "source_B2_prose_sha256":ORIGINAL_B2_SHA,
        "old_B_two_turn_candidate_resume_sha256":EXPECTED_B_ORIGINAL_RESUME,
        "same_author_model":"deepseek-flash",
        "novelist_owns_literary_choice":True,
        "reader_hypothesis_not_literary_fact":True,
        "original_novel_source_not_in_artifact":True,
        "no_synthetic_source_or_original_text_refabrication":True,
        "max_new_paid_calls":MAX_NEW_PAID_CALLS,
        "max_new_reserved_output_tokens":MAX_NEW_RESERVED_OUTPUT_TOKENS,
        "actual_real_author_V119_repair_accepted":False,
        "third_new_author_turn_generated":False,
        "old_B_signed_resume_reused":False,
        "Canon_writes":0,"R2_writes":0,"Railway_deployments":0,
        "production_main_unchanged":True,
        "independent_literary_quality_proven":False}
    writer=None
    try:
        b1,original1=real_archived_turn(
            "B-T1-prose-04",ORIGINAL_B1_SHA,exp.BEATS[0],())
        b2,original2=real_archived_turn(
            "B-T2-prose-06",ORIGINAL_B2_SHA,exp.BEATS[1],(original1,))
        old_status=read_json(INPUT/"B"/"STATUS.json")
        truth(old_status["signed_candidate_resume_sha256"]==
              EXPECTED_B_ORIGINAL_RESUME and
              old_status["stages_completed"]==2,
              "WF0T_ARCHIVED_B_PRIOR_RESUME_IDENTITY_CHANGED")
        truth((INPUT/"B"/"stage-01-real-author-prose.md").read_text("utf8")==
              original1["prose"] and
              (INPUT/"B"/"stage-02-real-author-prose.md").read_text("utf8")==
              original2["prose"], "WF0T_GENUINE_SOURCE_FILES_DIFFER_FROM_PROVIDER")
        real_prose=original2["prose"]
        truth("手里攥着那截麻绳，绳结还系在木桩上，只是绳子被人从桩头解下来" in real_prose,
              "WF0T_EXACT_READER_SOURCE_NOT_IN_GENUINE_TEXT")
        previous=external_temporal_step(
            original1["prose"],cast=exp.CAST)
        old2=external_temporal_step(
            real_prose,prior=previous,cast=exp.CAST)
        previous_guard=preflight_continuation(
            real_prose,previous,project_id=exp.PROJECT,
            chapter_index=1,cast=exp.CAST)
        truth(not previous_guard["blocked"] and
              not previous_guard["needs_review"],
              "WF0T_REAL_B2_PREVIOUS_WF_STATE_CANNOT_BE_REPLAYED")
        require_external_runtime()
        key=os.getenv("DEEPSEEK_API_KEY","")
        truth(len(key)>=16,"WF0T_GENUINE_AUTHOR_MODEL_KEY_UNAVAILABLE")
        writer=CapWriter(key,OUT)
        def model_adapter(name):
            def ask(pkt,*,model,api_base,max_tokens):
                truth(model is None and api_base is None,
                      "WF0T_EDIT_SAME_AUTHOR_MODEL_NOT_USED")
                return writer.call("B",1,name,pkt,max_tokens,
                                   system=exp.AUTHOR_SYSTEM)
            return ask
        choice_packet=exp.make_packet(
            "【第二段写后自主复核；原著第一二章小窗已经先前读过，此次只检查原作者自己的源文本】"+
            READER_HYPOTHESIS, "staged-0t-b")
        choice=_ai_decides_when_to_revisit(
            raw=b2,beat=exp.BEATS[1],accepted=(original1,),
            turn_packet=choice_packet,
            ask_model=model_adapter("writer-choice-on-genuine-B2"),
            directory=OUT/"writer-choice-real-B2",
            source_identity_contract="bind_null_current")
        result.update({
            "real_author_choice":choice["decision"],
            "real_author_reason":choice.get("reason"),
            "real_author_risk":choice.get("risk"),
            "real_author_quote":choice.get("source_quote"),
            "choice_receipt":choice["receipt"],
        })
        if choice["decision"]!="LOOK_BACK_NOW":
            result["status"]="REAL_AUTHOR_KEPT_OR_CHOICE_UNUSABLE_NO_EDIT"
            return result
        if choice["target_turn"]!="current":
            result["status"]="AUTHOR_CHOSE_PREVIOUS_REQUIRE_REWIND_NOT_FAKED"
            result["previous_turn_downstream_reused"]=False
            return result
        # From here, WF really gives the source-first repair contract and
        # the SAME original author chooses whether/how to rewrite its sentence.
        editable_packet=exp.make_packet(
            "【带来源的真正作者自主修订，目标是同一模型亲写的 B 组第2段】"+
            READER_HYPOTHESIS+
            "\n【旧第2段正文原件 SHA】"+ORIGINAL_B2_SHA,
            "staged-0t-b")
        amended,receipt=_self_edit_one_turn(
            raw=b2,beat=exp.BEATS[1],accepted=(original1,),
            project_id=exp.PROJECT,scene_id="staged-0t-b",
            turn_packet=editable_packet,
            ask_model=model_adapter("real-V119-author-edit-or-source-trace"),
            round_limit=2,call_allowance=2,
            directory=OUT/"V119-source-first-real-edit",
            previous_candidate_state={},cast=exp.CAST,
            current_external_story_checkpoint=previous,
            story_chapter_index=1,
            writer_attention={
                "reason":choice.get("reason"),
                "risk":choice.get("risk"),
                "desired_effect":choice.get("desired_effect"),
                "source_quote":choice.get("source_quote"),
                "focus":choice.get("focus")})
        write_json(OUT/"real-source-guided-revision.json",receipt)
        statuses=[x["status"] for x in receipt.get("rounds",[])]
        result["WF_source_first_V119_round_statuses"]=statuses
        revised_doc=json.loads(amended)
        if (exp.sha(revised_doc["prose"])==ORIGINAL_B2_SHA or
            "PROVISIONALLY_REVISED" not in statuses):
            result["status"]="V119_NOT_EFFECTIVELY_REVISED_OR_ROLLED_BACK"
            return result
        fixed2=check_turn(amended,exp.BEATS[1],mode="causal_guard",
                          accepted=(original1,),max_prose_chars=1024)
        guard=preflight_continuation(
            fixed2["prose"],previous,project_id=exp.PROJECT,
            chapter_index=1,cast=exp.CAST)
        write_json(OUT/"V117-fixed-B2-preflight.json",guard)
        truth(not guard["blocked"] and not guard["needs_review"],
              "WF0T_NEW_V117_CONTINUITY_OR_SOURCE_REVIEW_BLOCKED")
        fixed_state=external_temporal_step(
            fixed2["prose"],prior=previous,cast=exp.CAST)
        result["revised_B2_sha256"]=exp.sha(fixed2["prose"])
        result["source_locked_V119_V96_V114_V117_pass"]=True
        # Every old downstream derived from the original signed B2 is now
        # invalid by construction. Reconstruct from B1 + selected final B2.
        joined2=original1["prose"]+"\n\n"+fixed2["prose"]
        (OUT/"real-B1-and-revised-B2-unaccepted.md").write_text(
            joined2,encoding="utf8")
        graph=new_graph(project_id=exp.PROJECT,scene_id="staged-0t-b")
        graph=advance_graph(graph,project_id=exp.PROJECT,
                            scene_id="staged-0t-b",chapter_index=1,
                            prose=joined2,events=())
        combined_state=external_temporal_step(
            joined2,cast=exp.CAST)
        graph=record_chapter_memory(
            graph,project_id=exp.PROJECT,scene_id="staged-0t-b",
            chapter_index=1,
            source_path=str(OUT/"real-B1-and-revised-B2-unaccepted.md"),
            prose=joined2)
        new_resume=make_resume(
            project_id=exp.PROJECT,scene_id="staged-0t-b",chapter_index=1,
            checkpoint=combined_state,unified_narrative_core=graph)
        read_resume(new_resume,project_id=exp.PROJECT,
                    scene_id="staged-0t-b")
        truth(new_resume["receipt_sha256"]!=EXPECTED_B_ORIGINAL_RESUME,
              "WF0T_OLD_CANDIDATE_RESUME_WRONGLY_REUSED")
        result["new_B_after_edit_resume_sha256"]=new_resume["receipt_sha256"]
        result["prior_V117_and_core_resigned_from_new_text"]=True
        result["original_B2_and_old_signed_resume_invalidated"]=True

        # A NEW real writer request, not replay of the old second paragraph.
        third_note=(
            "【同一原作家《潮簿》滚动续写第3片段】"
            "这里只写100到500汉字的下一小段，不写整章。"
            "旧未修改B2已作废，下面的源文本为真模型修订通过的版本。"
            "故事角色、时间、物品、债务与已写结果须连续。"
            "由你独立决定人物动机、动作、叙事和是否留白。"
            "\n【真实第一段】"+original1["prose"]+
            "\n【真实第二段的最终已核准候选】"+fixed2["prose"]+
            "\n【上一段刚写出的可引用真实后果】"+
            json.dumps(fixed2["effect_quote"],ensure_ascii=False)+
            "\n"+make_turn_instructions(
                NEXT_BEAT,mode="causal_guard",
                accepted=(original1,fixed2)))
        reply=model_adapter("third-prose-after-source-repair")(
            exp.make_packet(third_note,"staged-0t-b"),
            model=None,api_base=None,max_tokens=1450)
        next_raw=exp.canonical_response(reply)
        next_doc=json.loads(next_raw)
        truth(80<=len(next_doc["prose"].strip())<=exp.MAX_STAGE_PROSE,
              "WF0T_THIRD_WRITER_TURN_NOT_A_SHORT_SLICE")
        third=check_turn(next_raw,NEXT_BEAT,mode="causal_guard",
                         accepted=(original1,fixed2),max_prose_chars=1024)
        guard3=preflight_continuation(
            third["prose"],fixed_state,project_id=exp.PROJECT,
            chapter_index=1,cast=exp.CAST)
        write_json(OUT/"V117-real-new-third-turn-preflight.json",guard3)
        truth(not guard3["blocked"] and not guard3["needs_review"],
              "WF0T_NEW_NEXT_SOURCE_CONTINUITY_OR_REVIEW_BLOCKED")
        checkpoint3=external_temporal_step(
            third["prose"],prior=fixed_state,cast=exp.CAST)
        all_text=joined2+"\n\n"+third["prose"]
        (OUT/"real-B-final-three-small-stages-unaccepted.md").write_text(
            all_text,encoding="utf8")
        graph3=new_graph(project_id=exp.PROJECT,scene_id="staged-0t-b")
        graph3=advance_graph(
            graph3,project_id=exp.PROJECT,scene_id="staged-0t-b",
            chapter_index=1,prose=all_text,events=())
        combined3=external_temporal_step(all_text,cast=exp.CAST)
        graph3=record_chapter_memory(
            graph3,project_id=exp.PROJECT,scene_id="staged-0t-b",
            chapter_index=1,
            source_path=str(OUT/"real-B-final-three-small-stages-unaccepted.md"),
            prose=all_text)
        signed3=make_resume(
            project_id=exp.PROJECT,scene_id="staged-0t-b",chapter_index=1,
            checkpoint=combined3,unified_narrative_core=graph3)
        read_resume(signed3,project_id=exp.PROJECT,scene_id="staged-0t-b")
        result.update({
            "status":"REAL_AUTHOR_V119_REPAIR_AND_NEW_TURN_PASS_UNACCEPTED",
            "real_author_b2_edit_source_sha_changed":True,
            "actual_real_author_V119_repair_accepted":True,
            "third_new_author_turn_generated":True,
            "third_turn_source_sha256":exp.sha(third["prose"]),
            "new_complete_three_turn_resume_sha256":signed3["receipt_sha256"],
            "old_B_signed_resume_reused":False,
            "human_literary_improvement_proven":False
        })
        write_json(OUT/"new-third-source-check.json",{
            "action_quote":third["action_quote"],
            "effect_quote":third["effect_quote"],
            "parent_quote_sha256":exp.sha(fixed2["effect_quote"]),
            "third_real_V96":third["receipt"]["causal_check"],
            "third_V114_checkpoint_sha256":checkpoint3["receipt_sha256"],
            "new_recomputed_entire_narrative_sha256":exp.sha(all_text)})
        return result
    except Exception as exc:
        code=str(exc)
        if not code.startswith(("WF_","WF96_","WF119_","WFCORE_","WF0T_")):
            code=type(exc).__name__+":REAL_WRITER_REVIEW_NO_UNVERIFIED_RETRY"
        result["status"]="REAL_AUTHOR_SOURCE_REPAIR_FAILED_OR_HELD"
        result["failure_code"]=code[:150]
        # A partial source-legal writer edit does not count until the actual
        # model regenerated a new downstream turn from its accepted source.
        result["actual_real_author_V119_repair_accepted"]=False
        return result
    finally:
        if writer is not None:
            result["new_real_paid_calls"]=writer.reserved.calls_reserved
            result["model_token_usage"]=writer.reserved.public_receipt()
            result["original_provider_response_sha256s"]=[
                x.get("provider_wire_sha256") for x in writer.events]
            writer.release_wires("B",allow=True)

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    result=run_real_B2_followthrough()
    write_json(OUT/"STATUS.json",result)
    print("WF0T_B2_REAL_REPAIR "+json.dumps({
        "status":result["status"],
        "real_paid_calls":result.get("new_real_paid_calls",0),
        "author_chose":result.get("real_author_choice"),
        "V119_repair_and_new_real_turn_pass":result[
            "actual_real_author_V119_repair_accepted"],
        "independent_literary_criterion":False},
        ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
