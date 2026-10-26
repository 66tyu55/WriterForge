"""WF 0.AS: six REAL same-author writer self-review calls, one per old source.

RESEARCH QUESTION (preregistered): 0.AQ original G author produced four
{prose,trace} schema echoes in six calls; will a separated source-locked
self-review task now yield valid, author-owned MOVE_ON/LOOK_BACK_NOW JSON
more often on THE EXACT SAME SIX PREVIOUSLY WRITTEN PARAGRAPHS?

NOT an A/B literary quality claim: later stochastic calls, different task
prompt, same DeepSeek Flash family. Never reauthor any paragraph, never ask
a judge to score fiction, never force a revision or mark old prose accepted.

Original: Actions 40264287305, 40259961845. Old full manuscript SHA
d1b86f2b6430b80bdb70df70199b9644e0a0b041ab842a81abc0a625c29cb0e3.
Old six self-review response SHAs frozen below. No R2/Canon/main/Railway.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json,os,re

from writerforge.writing_assist import (
    _ai_decides_when_to_revisit,SELF_EDIT_MOMENT_TOKENS,
)
from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget
from writerforge.verified_flow import GroundedDraftPacket

SOURCE=Path("wf0as_original_0aq_full_g")
OLD=Path("wf0as_original_0ao_eight")
OUTPUT=Path("wf_0as_real_six_same_author_isolated_self_review_20261026")
REAL_SOURCE_RUN=40264287305
REAL_EARLY_AUTHOR_RUN=40259961845
ORIGINAL_CHAPTER_SHA="d1b86f2b6430b80bdb70df70199b9644e0a0b041ab842a81abc0a625c29cb0e3"
ORIGINAL_PROSE_SHAS=(
    "a5d8814fac32e22b07817b9b233b0b81862d091c0295095d91da302ba12b737c",
    "e5ed869a300904e63a43e063a5d9e71e6d79d21a6ecf939d991e9612dd4fb473",
    "9009cce68d3fed4905f83e33732fca8cbb1e21478aa6df298e91f30f21156acc",
    "b867d7903bd94e4cbaaba8d59889a1ffabbb8e725b317affe1f271d7873b5c33",
    "9e96f86a4a232fa3b31dc1c94b445d91365c7214d008c15868eefd3e2e0dc475",
    "4a17c114e40afc8b4866d61de73577bab8525e1d05e03c973b4bb68d42e57b5b",
)
ORIGINAL_REVIEW_SHAS=(
    "c6bab8b37c16a4fe33789b2db5f70e24f0126d604e0eee22a812fe4fd9dda663",
    "c2ce29bd95563b32a820f63944bbbfdf6916a7952178da1c27501acfcf0f57c8",
    "a06429ca2998cda6f9bfed0d12d647346cd83cc7a3b64104f0e9c066bc06a165",
    "d017f9e793f372638eede5ea5cbc2c6d03a1f54179334d770af987f6d5a5a97c",
    "b54a5878573b839713499e9600c15b11a13a3ba54b326f5acd1a030ec899d116",
    "babc87004ca1aea82acc29bb95c88394f6b95de075e56d209b5899d5619c9df7",
)
MAX_NEW_CALLS=6
OUTPUT_CAP=3600
SYSTEM=(
    "你是刚创作了以下中国原创历史小说的同一名写作模型。"
    "你的文学判断属于你自己，既可以决定继续，也可以决定回改。"
    "WriterForge不会替你写故事、给艺术评分、强迫修改或虚构前文证据。"
    "所有回应严格为当前提示要求的JSON对象，无Markdown。"
)


def h(s):
    return sha256(s if isinstance(s,bytes) else s.encode("utf8")).hexdigest()


def need(c,why):
    if not c:
        raise RuntimeError(why)


def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True),
                    encoding="utf8")


def freeze_original_six():
    artifact=SOURCE/"wf_0aq_older_eight_real_prose_restore_20261026"
    old=json.loads((artifact/"STATUS.json").read_text("utf8"))
    need(old["status"]=="UNACCEPTED_REAL_G_CHAPTER_COMPLETED_SOURCE_REVIEW_SEPARATE"
         and old["complete_candidate_prose_sha256"]==ORIGINAL_CHAPTER_SHA
         and old["new_model_calls"]==4
         and old["R2_reads"]==old["R2_writes"]==old["Canon_writes"]==0
         and not old["main_modified"],
         "WF0AS_ORIGINAL_REAL_G_MANIFEST_CHANGED")
    artifacts=list((artifact/"g-source-authored-continuation").glob(
        "auto-*/**/v96_turn_evidence.json"))
    need(len(artifacts)==1,"WF0AS_ORIGINAL_G_EVIDENCE_NOT_UNIQUE")
    child=artifacts[0].parent
    job=child.parent
    chapter=(child/"candidate.md").read_text("utf8")
    need(h(chapter)==ORIGINAL_CHAPTER_SHA,
         "WF0AS_ORIGINAL_FULL_MANUSCRIPT_BYTE_DRIFT")
    evidence=json.loads(artifacts[0].read_text("utf8"))
    receipts=evidence["turn_receipts"]
    beats=json.loads((child/"v96_turn_outline.json").read_text("utf8"))[
        "candidate_turns"]
    need(len(receipts)==len(beats)==6 and
         evidence["all_drafts_pending_author_acceptance"] is True,
         "WF0AS_ORIGINAL_BEAT_OR_SOURCE_CANDIDATE_INVALID")
    # Early originals must also appear in their real provider wires. The
    # latter two were generated in the later successful 0.AQ continuation.
    before=json.loads((OLD/"STATUS.json").read_text("utf8"))
    need(before["new_model_calls"]==8 and
         before["old_real_six_event_plan_preserved"] is True,
         "WF0AS_FIRST_FOUR_SOURCE_WIRES_MANIFEST_CHANGED")
    now=old["new_provider_events"]
    raws=[]
    source_prompts=[]
    old_review_schema=[]
    for ix,(b,r) in enumerate(zip(beats,receipts)):
        n=ix+1
        need(b["id"]==r["turn_id"]==f"t{n:02d}",
             "WF0AS_ORIGINAL_BEAT_ID_CHANGED")
        fn=job/f"chapter-001-turn-{n:02d}-raw.json"
        doc=json.loads(fn.read_text("utf8"))
        prose=doc["prose"]
        need(h(prose)==r["prose_sha256"]==ORIGINAL_PROSE_SHAS[ix] and
             type(doc["trace"]) is dict,
             "WF0AS_PREVIOUS_WRITER_PROSE_SHA_CHANGED")
        rawreview=(job/f"chapter-001-turn-{n:02d}-ai-moment"/
                   "ai-when-and-why-original.json").read_bytes()
        need(h(rawreview)==ORIGINAL_REVIEW_SHAS[ix],
             "WF0AS_REAL_OLD_AUTHOR_REVIEW_REPLY_CHANGED")
        parsed=json.loads(rawreview)
        old_review_schema.append("decision" if
                                 type(parsed) is dict and
                                 "decision" in parsed else
                                 "prose_echo" if
                                 type(parsed) is dict and
                                 set(parsed)=={"prose","trace"} else
                                 "other_invalid")
        # Ground each new self-review in that turn's ACTUAL earlier
        # prose-write prompt and source. Never smuggle the original
        # review response into the next author's decision.
        if ix<4:
            row=before["new_provider_events"][2*ix]
            wire=(OLD/"provider-originals"/
                  f"new-{2*ix+1:02d}.json").read_bytes()
            request=(OLD/"new-model-requests"/
                     f"{2*ix+1:02d}-request.json")
        else:
            row=now[2*(ix-4)]
            wire=(artifact/"new-provider-originals"/
                  f"new-{2*(ix-4)+1:02d}.json").read_bytes()
            request=(artifact/"new-model-requests"/
                     f"{2*(ix-4)+1:02d}.json")
        need(h(wire)==row.get("raw_provider_sha256",row.get("wire_sha256")),
             "WF0AS_OLD_PROVIDER_ORIGINAL_SHA_MISMATCH")
        envelope=json.loads(wire)
        need(envelope["model"]=="deepseek-flash" and
             envelope["choices"][0]["finish_reason"]=="stop" and
             json.loads(envelope["choices"][0]["message"]["content"])==doc,
             "WF0AS_OLD_MODEL_BODY_NOT_PROVIDER_SOURCE")
        instruction=json.loads(request.read_text("utf8"))
        need(h(instruction["prompt"])==instruction["prompt_sha256"] and
             instruction["prompt_sha256"]==row["prompt_sha256"],
             "WF0AS_OLD_AUTHOR_WRITING_PROMPT_CHANGED")
        raws.append(doc)
        source_prompts.append(instruction)
    need(old_review_schema==[
         "prose_echo","prose_echo","decision","decision",
         "prose_echo","prose_echo"],
         "WF0AS_ORIGINAL_SIX_AUTHOR_REVIEW_SCHEMA_BASELINE_DRIFT")
    return raws,beats,receipts,source_prompts,old_review_schema


class SixOriginalReviews:
    def __init__(self,api_key):
        self.calls=[]
        self.active=None
        self.budget=FlashBudget(max_calls=MAX_NEW_CALLS,
                                max_reserved_output_tokens=OUTPUT_CAP)
        self.api=DeepSeekFlashModel(
            api_key=api_key,budget=self.budget,
            timeout_seconds=110,on_response_wire=self._save_original)

    def _save_original(self,raw):
        need(type(raw) is bytes and self.active is not None and
             self.calls and
             self.calls[-1]["raw_provider_sha256"] is None,
             "WF0AS_PROVIDER_RAW_CALLBACK_UNEXPECTED")
        target=OUTPUT/"new-provider-originals"/(
            f"self-review-{self.active:02d}.json")
        target.parent.mkdir(parents=True,exist_ok=True)
        need(not target.exists(),"WF0AS_PROVIDER_ORIGINAL_IMMUTABLE")
        target.write_bytes(raw)
        self.calls[-1]["raw_provider_sha256"]=h(raw)
        self.calls[-1]["saved_before_decode"]=True

    def ask(self,pkt,*,model,api_base,max_tokens):
        need(model is None and api_base is None and
             max_tokens==SELF_EDIT_MOMENT_TOKENS and
             len(self.calls)<MAX_NEW_CALLS and
             pkt.prompt.startswith(
               "【WriterForge 独立写后审稿阶段 / ONLY_REVIEW_DECISION】") and
             "请创作原创简体中文小说正文" not in pkt.prompt and
             "仅输出严格JSON：{\"prose\"" not in pkt.prompt,
             "WF0AS_WRITER_REVIEW_PROMPT_STILL_IN_PROSE_MODE")
        number=len(self.calls)+1
        event={
            "scene_turn":f"t{number:02d}",
            "prompt_sha256":h(pkt.prompt),
            "reserved_output_tokens":max_tokens,
            "raw_provider_sha256":None,"saved_before_decode":False,
        }
        self.calls.append(event)
        save(OUTPUT/"new-model-requests"/f"self-review-{number:02d}.json",{
            "format":"wf.0as.one-genuine-writer-review-question.v1",
            "prompt":pkt.prompt,"prompt_sha256":h(pkt.prompt),
            "max_tokens":max_tokens,
            "only_original_author_self_review":True,
        })
        self.active=number
        try:
            doc=self.api.ask_json(
                role="self_scene_writing",
                system=SYSTEM,user=pkt.prompt,max_tokens=max_tokens)
            raw=json.dumps(doc,ensure_ascii=False,separators=(",",":"))
            event["decoded_sha256"]=h(raw)
            return raw
        finally:
            self.active=None


def main():
    need(not OUTPUT.exists(),"WF0AS_ORIGINAL_REVIEW_RESULT_ALREADY_EXISTS")
    OUTPUT.mkdir(parents=True)
    status={
        "format":"wf.0as.real-six-author-self-review-stage-separated.v1",
        "source_run":REAL_SOURCE_RUN,
        "original_full_chapter_sha256":ORIGINAL_CHAPTER_SHA,
        "previous_real_model_review_valid_count":2,
        "previous_real_model_review_prose_echo_count":4,
        "old_prose_did_not_change":True,
        "new_model_calls":0,
        "maximum_new_calls":MAX_NEW_CALLS,
        "same_provider":"deepseek-flash",
        "new_writer_prose_calls":0,
        "actual_canon_writes":0,"R2_reads":0,"R2_writes":0,
        "Railway_deployments":0,"main_modified":False,
        "literary_quality_improvement_proven":False,
        "revision_is_never_forced":True,
        "statuses":[],"provider_events":[],"status":"NOT_STARTED",
    }
    model=None
    try:
        need(not any(os.getenv(k) for k in (
            "WRITERFORGE_R2_ACCOUNT_ID","WRITERFORGE_R2_ACCESS_KEY_ID",
            "DISCOVERY_API_KEY","OPENAI_API_KEY","OPENROUTER_API_KEY")),
            "WF0AS_UNNEEDED_EXTERNAL_CREDENTIALS_PRESENT")
        prose,beats,receipts,prompts,old_schemas=freeze_original_six()
        key=os.getenv("DEEPSEEK_API_KEY","")
        need(len(key)>=16,"WF0AS_ORIGINAL_DEEPSEEK_KEY_NOT_PRESENT")
        model=SixOriginalReviews(key)
        for i,(doc,beat,request) in enumerate(zip(prose,beats,prompts),1):
            # Previous original paragraph from the exact source, not
            # reconstructed by a second model or invented from state.
            accepted=({"prose":prose[i-2]["prose"],
                       "effect_quote":None},) if i>1 else ()
            writer_packet=GroundedDraftPacket(
                scene_id="0am-same-model-messenger-source.chapter-001",
                project_id="0am-unaccepted-original-history",
                snapshot_id=1,evidence=(),craft_ids=(),
                prompt=request["prompt"],
                prompt_sha256=request["prompt_sha256"])
            review=_ai_decides_when_to_revisit(
                raw=json.dumps(doc,ensure_ascii=False,separators=(",",":")),
                beat=beat,accepted=accepted,
                turn_packet=writer_packet,ask_model=model.ask,
                directory=OUTPUT/"raw-self-review-decisions"/
                          f"turn-{i:02d}")
            need(review["receipt"].get(
                "review_prompt_stage_isolated_from_prose_generation") is True
                and review["receipt"].get(
                    "review_writer_source_prose_unchanged") is True,
                 "WF0AS_SELF_REVIEW_STAGE_NOT_ISOLATED")
            row={
                "turn_id":f"t{i:02d}",
                "source_prose_sha256":h(doc["prose"]),
                "old_review_schema":old_schemas[i-1],
                "new_review_decision":review["decision"],
                "new_review_receipt":review["receipt"],
                "response_source_not_a_literary_truth_verdict":True,
                "new_model_calls_for_one_review":1,
                "new_author_prose_generated":False,
                "new_canon_writes":0,
            }
            status["statuses"].append(row)
            save(OUTPUT/"PARTIAL.json",status)
        status["status"]="SIX_REAL_SAME_AUTHOR_REVIEW_DECISIONS_RETAINED"
        status["new_valid_decision_count"]=sum(
            x["new_review_decision"] in ("MOVE_ON","LOOK_BACK_NOW")
            for x in status["statuses"])
        status["new_move_on_count"]=sum(
            x["new_review_decision"]=="MOVE_ON" for x in status["statuses"])
        status["new_look_back_count"]=sum(
            x["new_review_decision"]=="LOOK_BACK_NOW"
            for x in status["statuses"])
        status["new_invalid_count"]=6-status["new_valid_decision_count"]
        status["task_contract_quality_only_not_literary"]=True
    except Exception as exc:
        err=str(exc)
        status["status"]="SOURCE_OR_SELF_REVIEW_PARTIAL_NO_RETRY"
        status["failure_code"]=(
            err if re.fullmatch(r"WF[A-Z0-9_:\-]{3,170}",err)
            else type(exc).__name__+":NO_RETRY")
    finally:
        if model is not None:
            status["new_model_calls"]=model.budget.calls_reserved
            status["provider_events"]=model.calls
            status["model_budget"]=model.budget.public_receipt()
        save(OUTPUT/"STATUS.json",status)
        print("WF0AS_SAME_WRITER_REVIEW "+json.dumps({
            "status":status["status"],
            "old_valid":status["previous_real_model_review_valid_count"],
            "old_prose_echoes":status["previous_real_model_review_prose_echo_count"],
            "new_calls":status["new_model_calls"],
            "new_valid":status.get("new_valid_decision_count"),
            "new_move_on":status.get("new_move_on_count"),
            "new_look_back":status.get("new_look_back_count"),
            "error":status.get("failure_code"),
        },ensure_ascii=False),flush=True)
    if status["status"]!="SIX_REAL_SAME_AUTHOR_REVIEW_DECISIONS_RETAINED":
        raise RuntimeError("WF0AS_REAL_WRITER_SELF_REVIEW_PARTIAL_HELD")


if __name__=="__main__":
    main()
