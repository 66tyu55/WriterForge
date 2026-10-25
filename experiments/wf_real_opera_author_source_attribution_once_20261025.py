"""One bounded REAL same-author provenance attestation on archived opera prose.

GitHub Actions original #40110957161 (7 true provider wires + signed V117)
and reader/author #40151857245 (2 true wires) are SHA-verified first.
The already-paid reader reply is replayed with 0 new calls. ONE NEW
official DeepSeek Flash request asks the SAME author how it justifies its
literary MOVE_ON/LOOK_BACK_NOW against actual earlier written source.
WRITTEN_WITH_QUOTE must quote the earlier novel. UNWRITTEN_OR_UNKNOWN and
INTENTIONAL_ELLIPSIS honestly permit literary silence. WF only proves the
quote bytes exist, NEVER that the quoted prose proves a legal transfer.
No automatic V119, R2, Canon, literary quality grade, retraining, retry,
main merge, Railway deployment or second literary/memory model.
"""
from __future__ import annotations
import os,json
from pathlib import Path
from hashlib import sha256
from writerforge.deepseek_flash_model import (
    DeepSeekFlashModel,FlashBudget,DeepSeekFlashError)
from writerforge.verified_flow import GroundedDraftPacket
from writerforge.writing_assist import (
    _reader_separates_written_and_inferred,
    _ai_decides_when_to_revisit,SELF_EDIT_ATTRIBUTION_TOKENS)
from experiments.wf_real_opera_cross_source_zero_model_receipt_20261025 import provenance

OUT=Path("wf_real_opera_author_evidence_20261025")
CALL_CAP=1
MODEL="deepseek-flash"

def digest(s):
    return sha256(s.encode("utf8") if isinstance(s,str) else s).hexdigest()

def save(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,
                               sort_keys=True,indent=2),encoding="utf8")

def packet():
    prompt="同一篇实际已写好的戏楼小说。只有你本人决定保留还是回头，不要给小说打分。"
    return GroundedDraftPacket(
        project_id="wf-original-night-opera-new-one-shot",
        scene_id="winter-opera-hall",snapshot_id=0,
        evidence=(),craft_ids=(),
        prompt=prompt,prompt_sha256=digest(prompt))

class Once:
    def __init__(self,key,out):
        self.calls=[]
        self.out=out
        self.budget=FlashBudget(
            max_calls=CALL_CAP,
            max_reserved_output_tokens=SELF_EDIT_ATTRIBUTION_TOKENS,
            max_total_tokens=150000)
        self.model=DeepSeekFlashModel(
            api_key=key,budget=self.budget,timeout_seconds=110,
            on_response_wire=self.wire)
    def wire(self,original):
        if not self.calls:
            raise RuntimeError("WF_AUTHOR_ATTESTATION_ORIGINAL_WIRE_STAGE_MISSING")
        (self.out/"01-REAL_AUTHOR_WIRE.json").write_bytes(original)
        self.calls[-1]["wire_sha256"]=digest(original)
        self.calls[-1]["original_wire_kept_before_parse"]=True
    def ask(self,pkt,*,model,api_base,max_tokens):
        if (model is not None or api_base is not None or
            max_tokens!=SELF_EDIT_ATTRIBUTION_TOKENS or self.calls):
            raise RuntimeError("WF_AUTHOR_ATTESTATION_CALL_BOUNDARY")
        self.calls.append({
            "stage":"SAME_NOVELIST_DECIDES_WITH_SOURCE",
            "max_tokens":max_tokens,"prompt_sha256":digest(pkt.prompt),
            "original_wire_kept_before_parse":False})
        result=self.model.ask_json(
            role="self_scene_writing",
            system=(
                "你是这篇原创小说真正的写作 AI。原小说原文、读者未证推测"
                "和早期源章节都在用户请求里。由你自己决定保留或修改，"
                "本次不直接生成新小说正文，也不保证要修改。"
                "当你称以前写过某处事件转换，请给此前原文章节的唯一真实引句；"
                "若此前没有实际明写，则用 UNWRITTEN_OR_UNKNOWN，"
                "或者若你有意省略则用 INTENTIONAL_ELLIPSIS。"
                "引句出现不等于它自动证明了物件转移。"
                "必须严格按用户文本的字段返回合法 JSON 对象。"
            ),
            user=pkt.prompt,max_tokens=max_tokens)
        raw=json.dumps(result,ensure_ascii=False,separators=(",",":"))
        (self.out/"01-REAL_AUTHOR_PARSED_REPLY.json").write_text(
            raw,encoding="utf8")
        self.calls[-1]["parsed_reply_sha256"]=digest(raw)
        return raw

def run():
    previous,old_status,reader_raw,old_writer_raw=provenance()
    if OUT.exists():
        raise RuntimeError("WF_AUTHOR_ATTESTATION_REPEAT_OUTPUT_FORBIDDEN")
    OUT.mkdir(parents=True)
    seed,prose=previous["seed"],previous["source"]
    (OUT/"SIGNED_EARLIER_UNCHANGED.md").write_text(seed,encoding="utf8")
    (OUT/"G_CURRENT_UNCHANGED.md").write_text(prose,encoding="utf8")
    (OUT/"HISTORIC_WRITER_MOVE_ON_RAW.json").write_text(
        old_writer_raw,encoding="utf8")
    p=packet()
    prior_reader=_reader_separates_written_and_inferred(
        raw=previous["first_raw"],turn_packet=p,
        ask_model=lambda *a,**k:reader_raw,
        directory=OUT/"OLD_READER_REPLAY_NO_NEW_CALL",
        earlier_source=seed,earlier_source_sha256=digest(seed))
    if (prior_reader["status"]!="SOURCE_ANCHORED_READER_HYPOTHESES"
        or len(prior_reader["report"]["cross_source_links"])!=3):
        raise RuntimeError("WF_AUTHOR_ATTESTATION_UNTRUSTED_OLD_READER")
    report={
        "format":"wf.real.same-writer-prior-citation-20261025.v1",
        "status":"VERIFIED_G_SOURCE_BEFORE_ONE_AUTHOR_CALL",
        "original_G_run":40110957161,
        "original_reader_run":40151857245,
        "earlier_prose_sha256":digest(seed),
        "current_prose_sha256":digest(prose),
        "original_author_selected":"MOVE_ON",
        "historical_reader_links":3,
        "original_raw_replies_not_changed":True,
        "only_original_writer_model_used":True,
        "maximum_real_provider_calls":CALL_CAP,
        "maximum_requested_output_tokens":SELF_EDIT_ATTRIBUTION_TOKENS,
        "no_network_retries":True,
        "new_fiction_generated":False,
        "V119_called":False,"literary_quality_verified":False,
        "human_blind_evaluation_completed":False,
        "R2_writes":0,"Canon_writes":0,"model_training_runs":0,
    }
    model=None
    try:
        key=os.getenv("DEEPSEEK_API_KEY")
        if not isinstance(key,str) or len(key)<16:
            raise RuntimeError("WF_AUTHOR_ATTESTATION_EXISTING_SECRET_MISSING")
        model=Once(key,OUT)
        verdict=_ai_decides_when_to_revisit(
            raw=previous["first_raw"],beat=previous["beat"],
            accepted=(),turn_packet=p,ask_model=model.ask,
            directory=OUT/"NEW_AUTHOR_WITH_PRIOR_QUOTES",
            reader_report=prior_reader["report"],
            source_identity_contract="bind_null_current",
            earlier_source_for_attribution=seed)
        evidence=verdict["receipt"].get("cross_source_author_attribution",{})
        report.update({
            "status":"ONE_REAL_AUTHOR_SOURCE_DECISION_SAVED",
            "new_author_literary_decision":verdict["decision"],
            "new_author_why_now":verdict.get("reason"),
            "author_source_attribution_status":evidence.get("status"),
            "claimed_earlier_written_quote_count":evidence.get("claimed_written_links"),
            "state_only_old_quote_not_transfer_count":evidence.get(
                "prior_state_only_citations_needing_review"),
            "author_unwritten_unknown_count":evidence.get(
                "author_declared_unwritten_or_unknown_links"),
            "author_intentional_ellipsis_count":evidence.get(
                "author_declared_intentional_ellipsis_links"),
            "source_attribution_receipt":evidence,
            "original_author_decision_receipt":verdict["receipt"],
            "author_evidence_not_canon_fact":True,
            "author_literary_choice_not_overridden":True,
        })
    except (DeepSeekFlashError,RuntimeError,ValueError,OSError) as exc:
        err=str(exc)
        report["status"]="ONE_REAL_AUTHOR_ATTRIBUTION_PARTIAL_OR_REJECTED"
        report["failure_code"]=(err if err.startswith("WF_") and len(err)<=160
                                else type(exc).__name__)
    finally:
        report["new_real_provider_calls"]=(model.budget.calls_reserved if model else 0)
        report["provider_usage"]=(model.budget.public_receipt() if model else {})
        report["provider_original_wires"]=(model.calls if model else [])
        save(OUT/"STATUS.json",report)
        print(json.dumps({
            "status":report["status"],
            "old_true_model_decision":"MOVE_ON",
            "new_true_model_decision":report.get("new_author_literary_decision"),
            "source_claim_status":report.get("author_source_attribution_status"),
            "old_state_only_claims":report.get(
                "state_only_old_quote_not_transfer_count"),
            "unwritten_or_unknown":report.get("author_unwritten_unknown_count"),
            "intentional_ellipsis":report.get("author_intentional_ellipsis_count"),
            "real_provider_calls":report["new_real_provider_calls"],
            "max_calls":CALL_CAP,"fiction_changed":False,
            "literary_quality_verified":False,
        },ensure_ascii=False),flush=True)
    return report

if __name__=="__main__":
    run()
