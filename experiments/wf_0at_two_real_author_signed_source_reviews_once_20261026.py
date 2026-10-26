"""0.AT: source-aware SAME DeepSeek novelist self-review on frozen T05/T06.

The exact 0.AQ historical six-turn author prose and the 0.AS isolated-review
baseline are immutable. 0.AS made both T05 and T06 valid MOVE_ON decisions,
but had no authenticated old T03-T04 material-custody question. Ask the same
model on those SAME TWO texts again, only after an actual V114/V122 re-reduction
of the old source proves a signed unresolved booklet question exists.

No new novel generation, no literary grades, no forced revisions, no R2,
Canon, deployment, additional memory or automatic retry.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import json,os,re

from experiments import wf_0as_real_six_same_writer_self_review_once_20261026 as prior
from experiments import wf_0am_real_history_same_model_g_once_20261026 as historical
from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget
from writerforge.v114_external_story_state import external_temporal_step,require_external_runtime
from writerforge.writing_assist import (
    _signed_previous_author_source_question,
    _ai_decides_when_to_revisit,SELF_EDIT_MOMENT_TOKENS,
)
from writerforge.verified_flow import GroundedDraftPacket

OUT=Path("wf_0at_real_original_writer_source_aware_review_20261026")
OLDER=Path("wf0at_prior_0as_reviews")
TARGETS=(5,6)
MAX_NEW_CALLS=2
MAX_OUTPUT=1200
ORIGINAL_HISTORY_SHA=historical.EXPECTED_SOURCE_SHA


def h(s):
    return sha256(s if isinstance(s,bytes) else s.encode("utf8")).hexdigest()


def need(ok,code):
    if not ok:raise RuntimeError(code)


def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2),
                    encoding="utf8")


def signed_previous_source_review_context():
    prose,beats,receipts,prompts,old_schemas=prior.freeze_original_six()
    first,first_wire=historical.verify_old_real_source()
    need(h(first)==ORIGINAL_HISTORY_SHA,
         "WF0AT_REAL_AUTHOR_HISTORICAL_SOURCE_CHANGED")
    # No reauthor; reduce the SAME authentic G six turns through V114,
    # including original historical candidate root, using existing module.
    cast=("秦渊","周卒","传令兵","亲兵")
    state=external_temporal_step(first,cast=cast)
    earlier={}
    for i,doc in enumerate(prose,1):
        if i in TARGETS:
            # At review moment G has accepted only the earlier authored
            # turns; latest signed V114 checkpoint is exactly prior turn.
            previous={"prose":prose[i-2]["prose"]}
            quote,sha=_signed_previous_author_source_question(
                state,(previous,))
            need(quote and sha and
                 "周卒把册子揣进" in quote and
                 "地形册子一并纳入" in quote,
                 "WF0AT_REAL_SOURCE_CUSTODY_PROJECTION_NOT_AVAILABLE")
            earlier[i]={
                "previous_checkpoint":state,
                "source_note_sha256":sha,
                "signed_source_note":quote,
                "unresolved_question_semantics_not_proven":True,
            }
        state=external_temporal_step(doc["prose"],cast=cast,prior=state)
        need(state["source_sha256"]==h(doc["prose"]),
             "WF0AT_ACTUAL_G_V114_CHECKPOINT_SOURCE_CHANGED")
    need(len(earlier)==2,
         "WF0AT_MISSING_REAL_PREVIOUS_CUSTODY_CONTEXT")
    original_reviews=json.loads((OLDER/"STATUS.json").read_text("utf8"))
    need(original_reviews["format"]==
            "wf.0as.real-six-author-self-review-stage-separated.v1"
         and original_reviews["status"]==
            "SIX_REAL_SAME_AUTHOR_REVIEW_DECISIONS_RETAINED"
         and original_reviews["original_full_chapter_sha256"]==
            prior.ORIGINAL_CHAPTER_SHA
         and original_reviews["new_model_calls"]==6
         and original_reviews["new_valid_decision_count"]==6
         and all(original_reviews["statuses"][n-1][
             "new_review_decision"]=="MOVE_ON" for n in TARGETS),
         "WF0AT_OLDER_TWO_MOVE_ON_PROVIDER_BASELINE_CHANGED")
    return prose,beats,prompts,earlier,original_reviews


class TwoRealSourceReviewCalls:
    def __init__(self,api_key):
        self.rows=[]
        self.current=None
        self.budget=FlashBudget(
            max_calls=MAX_NEW_CALLS,
            max_reserved_output_tokens=MAX_OUTPUT)
        self.model=DeepSeekFlashModel(
            api_key=api_key,budget=self.budget,timeout_seconds=110,
            on_response_wire=self.wire_before_decode)

    def wire_before_decode(self,raw):
        need(self.current is not None and type(raw) is bytes and
             self.rows and self.rows[-1]["provider_raw_sha256"] is None,
             "WF0AT_ORIGINAL_SOURCE_RAW_RESPONSE_UNCLAIMED")
        p=OUT/"provider-originals"/f"source-aware-t{self.current:02d}.json"
        p.parent.mkdir(parents=True,exist_ok=True)
        need(not p.exists(),"WF0AT_WRITER_PROVIDER_EVIDENCE_CANNOT_OVERWRITE")
        p.write_bytes(raw)
        self.rows[-1]["provider_raw_sha256"]=h(raw)
        self.rows[-1]["raw_provider_saved_before_parse"]=True

    def ask(self,packet,*,model,api_base,max_tokens):
        need(model is None and api_base is None and
             max_tokens==SELF_EDIT_MOMENT_TOKENS and
             len(self.rows)<MAX_NEW_CALLS and
             packet.prompt.startswith(
                 "【WriterForge 独立写后审稿阶段 / ONLY_REVIEW_DECISION】") and
             "【已签名的前文来源疑问" in packet.prompt and
             "周卒把册子揣进" in packet.prompt and
             "地形册子一并纳入" in packet.prompt and
             "请创作原创简体中文小说正文" not in packet.prompt,
             "WF0AT_SOURCE_REVIEW_NOT_REALLY_DELIVERED")
        turn=TARGETS[len(self.rows)]
        row={
            "turn_id":f"t{turn:02d}",
            "review_prompt_sha256":h(packet.prompt),
            "reserved_max_tokens":max_tokens,
            "provider_raw_sha256":None,
            "raw_provider_saved_before_parse":False,
        }
        self.rows.append(row)
        save(OUT/"model-requests"/f"source-aware-t{turn:02d}.json",{
            "prompt":packet.prompt,"prompt_sha256":h(packet.prompt),
            "max_tokens":max_tokens,
            "model":"deepseek-flash",
            "original_author_changes_fiction_only_if_it_itself_decides_later":True,
        })
        self.current=turn
        try:
            obj=self.model.ask_json(
                role="self_scene_writing",system=prior.SYSTEM,
                user=packet.prompt,max_tokens=max_tokens)
            text=json.dumps(obj,ensure_ascii=False,separators=(",",":"))
            row["model_decision_json_sha256"]=h(text)
            return text
        finally:
            self.current=None


def main():
    need(not OUT.exists(),"WF0AT_PRIVATE_ORIGINAL_MODEL_EVIDENCE_ALREADY_EXISTS")
    OUT.mkdir(parents=True)
    receipt={
        "format":"wf.0at.real-two-source-signed-novelist-review.v1",
        "status":"NOT_STARTED",
        "source_run":prior.REAL_SOURCE_RUN,
        "original_history_source_sha256":ORIGINAL_HISTORY_SHA,
        "full_novel_candidate_sha256":prior.ORIGINAL_CHAPTER_SHA,
        "source_only_v114_v122_projection":True,
        "no_additional_narrative_memory_owner":True,
        "literary_problem_confirmed_by_WF":False,
        "old_isolated_move_on_count":2,
        "real_provider_calls":0,"new_novel_prose":0,
        "R2_reads":0,"R2_writes":0,"Canon_writes":0,
        "Railway_deployments":0,"main_modified":False,
        "original_writer_decides_change_or_keep":True,
        "author_edit_applied":False,"literary_improvement_proven":False,
        "old_provider_wires_preserved":True,
        "rows":[],"provider_events":[],
    }
    caller=None
    try:
        need(not any(os.getenv(k) for k in (
            "WRITERFORGE_R2_ACCOUNT_ID","WRITERFORGE_R2_ACCESS_KEY_ID",
            "DISCOVERY_API_KEY","OPENAI_API_KEY","OPENROUTER_API_KEY")),
            "WF0AT_OTHER_SOURCE_CREDENTIALS_NOT_ALLOWED")
        require_external_runtime()
        prose,beats,prompts,previous,old=signed_previous_source_review_context()
        secret=os.getenv("DEEPSEEK_API_KEY","")
        need(len(secret)>=16,"WF0AT_EXISTING_DEEPSEEK_SECRET_NOT_PRESENT")
        caller=TwoRealSourceReviewCalls(secret)
        for index in TARGETS:
            authored=prose[index-1]
            last_prose=prose[index-2]["prose"]
            saved_writer_prompt=prompts[index-1]
            writing_packet=GroundedDraftPacket(
                scene_id="0am-same-model-messenger-source.chapter-001",
                project_id="0am-unaccepted-original-history",
                snapshot_id=1,evidence=(),craft_ids=(),
                prompt=saved_writer_prompt["prompt"],
                prompt_sha256=saved_writer_prompt["prompt_sha256"])
            decision=_ai_decides_when_to_revisit(
                raw=json.dumps(authored,ensure_ascii=False,
                               separators=(",",":")),
                beat=beats[index-1],
                accepted=({"prose":last_prose},),
                turn_packet=writing_packet,ask_model=caller.ask,
                source_checkpoint=previous[index]["previous_checkpoint"],
                directory=OUT/"model-author-self-decisions"/
                          f"turn-{index:02d}")
            need(decision["receipt"].get(
                 "signed_prior_document_source_question_delivered") is True and
                 decision["receipt"].get(
                 "signed_prior_document_question_receipt_sha256")==
                    previous[index]["source_note_sha256"] and
                 decision["receipt"].get("no_host_mandated_revision_from_source_question")
                    is True,
                 "WF0AT_SOURCE_BOUND_REVIEW_REPLY_RECEIPT_NOT_DELIVERED")
            receipt["rows"].append({
                "turn_id":f"t{index:02d}",
                "original_author_prose_sha256":h(authored["prose"]),
                "old_isolated_decision":"MOVE_ON",
                "source_question_receipt_sha256":
                    previous[index]["source_note_sha256"],
                "new_same_author_decision":decision["decision"],
                "model_receipt":decision["receipt"],
                "no_new_prose_or_forced_v119_transaction":True,
                "literary_semantics_unverified":True,
            })
            save(OUT/"PARTIAL.json",receipt)
        receipt["status"]="TWO_NEW_ORIGINAL_AUTHOR_SOURCE_AWARE_REVIEWS_PRESERVED"
        receipt["valid_choice_count"]=sum(
            x["new_same_author_decision"] in ("MOVE_ON","LOOK_BACK_NOW")
            for x in receipt["rows"])
        receipt["look_back_choice_count"]=sum(
            x["new_same_author_decision"]=="LOOK_BACK_NOW"
            for x in receipt["rows"])
    except Exception as ex:
        code=str(ex)
        receipt["status"]="SOURCE_OR_MODEL_REVIEW_PARTIAL_NO_RETRY"
        receipt["failure_code"]=(code if re.fullmatch(
            r"WF[A-Z0-9_:\-]{3,180}",code)
            else type(ex).__name__+":NO_RETRY")
    finally:
        if caller is not None:
            receipt["real_provider_calls"]=caller.budget.calls_reserved
            receipt["provider_events"]=caller.rows
            receipt["budget"]=caller.budget.public_receipt()
        save(OUT/"STATUS.json",receipt)
        print("WF0AT_SOURCE_AWARE_NOVELIST "+json.dumps({
            "status":receipt["status"],
            "new_model_calls":receipt["real_provider_calls"],
            "old_move_on":2,
            "new_reviews":[(r["turn_id"],r["new_same_author_decision"])
                           for r in receipt["rows"]],
            "error":receipt.get("failure_code"),
            "new_novel_prose":0,"canon_writes":0,
        },ensure_ascii=False),flush=True)
    if receipt["status"]!="TWO_NEW_ORIGINAL_AUTHOR_SOURCE_AWARE_REVIEWS_PRESERVED":
        raise RuntimeError("WF0AT_TRUE_WRITER_SOURCE_AWARE_REVIEW_NOT_COMPLETE")


if __name__=="__main__":
    main()
