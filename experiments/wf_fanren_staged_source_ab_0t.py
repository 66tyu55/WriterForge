"""0.T controlled real-writer staged source exposure. Never a literary grade.

Two isolated author jobs use the same original outline, beats, model and WF
V96/V114/V117/V119 machinery. ONLY the B author may see one authentic,
hash-pinned, privately-read reference excerpt per visible writing turn.
Writer prose is produced in two small calls, never one whole chapter prompt.
No new memory owner, model critic, source publication, training, R2 writes,
canon changes, automatic retries, or production deployment.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from writerforge.deepseek_flash_model import DeepSeekFlashModel, FlashBudget
from writerforge.verified_flow import GroundedDraftPacket
from writerforge.v96_causal_turns import check_turn, make_turn_instructions
from writerforge.v114_external_story_state import external_temporal_step, require_external_runtime
from writerforge.v117_continuity_trace import preflight_continuation, make_resume, read_resume
from writerforge.narrative_core import new_graph, advance_graph, record_chapter_memory
from writerforge.writing_assist import (
    _ai_decides_when_to_revisit, _self_edit_one_turn,
)

OUT = Path("wf_fanren_staged_ab_0T")
MODEL = "deepseek-flash"
PROJECT = "wf-0t-staged-originality-source-ab"
CAST = ("林栖", "程满")
MAX_SOURCE_BYTES = 32 * 1024 * 1024
MAX_CALLS = 10
MAX_OUTPUT_RESERVATION = 14200
FIRST_CHAPTERS = 2
EXCERPT_CHARS = 230
MAX_STAGE_PROSE = 660
TITLE = "潮簿"
OUTLINE = (
    "《潮簿》为原创架空低魔成长故事，发生在以海堤和潮汐观测谋生的城镇，"
    "不出现宗门、炼丹、神秘小瓶、灵根选拔或任何现成小说人物与专有设定。"
    "少年林栖是欠着修堤债的抄簿工，谨慎、沉默、善于观察微小异常；"
    "年长的测潮人程满曾在一次堤坝事故中失去同伴，知道一部分原因但不肯随便说。"
    "平静的日常成本、偶然机会、逐步变化的信任与不可轻易消除的代价推动故事。"
    "你本人决定人物具体动作、心理、语言、留白与结尾，不照搬任何文学原文。"
    "本实验只先创作两个连续片段，不写完整第一章，不预告未来几章。"
)
BEATS = (
    {"id":"t01", "kind":"action", "actor":"林栖",
     "goal":"在一次寻常记潮工作中作出有来源的细小行动，让结果真正影响眼下处境",
     "causal_parent":None, "craft_focus":[]},
    {"id":"t02", "kind":"decision", "actor":"林栖",
     "goal":"根据上一步已经发生的实际后果，自行作出带有代价而非套路反转的选择",
     "causal_parent":"t01", "craft_focus":[]},
)
WRITER_SYSTEM = (
    "你是创作《潮簿》的同一名小说作者。"
    "写作语言由你自己选择。不能抄袭任何参考段落或复述参考剧情。"
    "只输出符合当前提示格式的严格 JSON 对象，不附说明。"
)
AUTHOR_SYSTEM = (
    "你仍是《潮簿》的同一名小说作者。"
    "由你自己决定保留、删除或回写，软件不判断文学优劣。"
    "严格只输出当前协议规定的 JSON 对象。"
)
CHAPTER_RE = re.compile(
    r"(?m)^[ \t]*第[0-9零一二三四五六七八九十百千]{1,8}章[^\n\r]{0,45}$"
)

def sha(value):
    raw = value.encode("utf8") if isinstance(value,str) else value
    return hashlib.sha256(raw).hexdigest()

def require(condition,code):
    if not condition:
        raise RuntimeError(code)

def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2),encoding="utf8")

def source_windows(text):
    """Choose only the opening of chapter 1 and chapter 2; no fake source."""
    require(type(text) is str and len(text)>1000, "WF0T_REAL_BOOK_SOURCE_NOT_PRESENT")
    matches=list(CHAPTER_RE.finditer(text))
    require(len(matches)>=FIRST_CHAPTERS+1, "WF0T_CANNOT_VERIFY_TWO_CHAPTER_BOUNDS")
    result=[]
    for i in range(FIRST_CHAPTERS):
        span=text[matches[i].end():matches[i+1].start()]
        span=re.sub(r"\s+","",span)[:EXCERPT_CHARS]
        require(len(span)>=EXCERPT_CHARS and
                "\ufffd" not in span, "WF0T_BOOK_CHAPTER_TOO_SHORT_OR_CORRUPT")
        result.append(span)
    require(len(set(result))==FIRST_CHAPTERS, "WF0T_REFERENCE_EXCERPTS_NOT_DISTINCT")
    return tuple(result)

def download_pinned_private_reference():
    """Private HTTPS read only. No book text enters logs or GitHub artifacts."""
    uri=os.getenv("WRITERFORGE_FANREN_SOURCE_URL","")
    expected=os.getenv("WRITERFORGE_FANREN_SOURCE_SHA256","").lower()
    parsed=urlparse(uri)
    require(parsed.scheme=="https" and bool(parsed.netloc) and
            not parsed.username and not parsed.password and
            not parsed.fragment and
            re.fullmatch(r"[0-9a-f]{64}",expected) is not None,
            "WF0T_PRIVATE_SOURCE_OR_PIN_NOT_CONFIGURED")
    request=Request(uri,headers={"User-Agent":"WriterForge-staged-source-readonly/0.T"})
    digest=hashlib.sha256()
    chunks=[]
    total=0
    with urlopen(request,timeout=70) as response:
        final=urlparse(response.geturl())
        require(final.scheme=="https" and final.hostname==parsed.hostname,
                "WF0T_PRIVATE_SOURCE_REDIRECT_NOT_PINNED")
        while True:
            block=response.read(1024*1024)
            if not block:
                break
            total+=len(block)
            require(total<=MAX_SOURCE_BYTES,"WF0T_PRIVATE_SOURCE_BYTES_EXCEEDED")
            digest.update(block)
            chunks.append(block)
    require(digest.hexdigest()==expected and total>=10000,
            "WF0T_PRIVATE_SOURCE_SHA_MISMATCH")
    raw=b"".join(chunks)
    try:
        text=raw.decode("utf-8-sig","strict")
    except UnicodeError:
        raise RuntimeError("WF0T_PRIVATE_SOURCE_NOT_UTF8") from None
    return source_windows(text), {"book_source_sha256":expected,
                                   "whole_book_bytes_read_privately":total,
                                   "reference_window_sha256":[sha(x) for x in source_windows(text)],
                                   "reference_window_chars":[EXCERPT_CHARS]*FIRST_CHAPTERS,
                                   "full_book_passed_to_any_model":False,
                                   "source_uploaded_or_rewritten":False}

def build_prompt(arm,stage,*,previous_prose="",previous_effect=None,reference=None):
    """One evolving turn. A never sees any provided source or its metadata."""
    require(arm in ("A","B") and stage in (0,1),"WF0T_ARM_STAGE_INVALID")
    require((arm=="A" and reference is None) or
            (arm=="B" and type(reference) is str and
             len(reference)==EXCERPT_CHARS),"WF0T_REFERENCE_ISOLATION_FAILED")
    note=(
        "【原创故事共同大纲；不是已发生正文】"+OUTLINE+
        "\n【本次仅写一个自然片段】100至500汉字。"
        "不许预写后续片段或整个第一章，不许在小说里解释写作任务。"
        "请让动作有可观察的结果，若延续上段则据实继承。"
    )
    if stage:
        require(type(previous_prose) is str and 80<=len(previous_prose)<=MAX_STAGE_PROSE,
                "WF0T_PREVIOUS_REAL_PROSE_REQUIRED")
        note+=("\n【同一作者上一步真正写出的正文】"+previous_prose+
               "\n【上一步来源 SHA】"+sha(previous_prose)+
               "\n【上一步确实可定位的后果，可能为 null】"+
               json.dumps(previous_effect,ensure_ascii=False))
    else:
        require(not previous_prose and previous_effect is None,
                "WF0T_STAGE1_NO_PREGENERATED_SOURCE")
    if arm=="B":
        note+=("\n【当前阶段唯一解锁的原著阅读参考】"+reference+
               "\n这不是续写目标，不是小说角色/情节来源。"
               "只体会观察细节、句子节奏与铺垫，并写完全不同的原创故事。"
               "禁止连续照抄、改人名复刻事件或直接介绍原著。")
    note+="\n"+make_turn_instructions(BEATS[stage],mode="causal_guard",
                                         accepted=())
    return note

def make_packet(prompt,scene):
    return GroundedDraftPacket(
        project_id=PROJECT,scene_id=scene,snapshot_id=0,
        evidence=(),craft_ids=(),prompt=prompt,prompt_sha256=sha(prompt))

def original_enough(prose,windows):
    """Protect public artifacts: refuse long literal matches with the source."""
    require(type(prose) is str,"WF0T_PROSE_NOT_STRING")
    for text in windows:
        for start in range(0,len(text)-29):
            if text[start:start+30] in prose:
                raise RuntimeError("WF0T_REFERENCE_VERBATIM_COPY_HELD")
    return True

def sentence_lengths(prose):
    items=[x.strip() for x in re.split(r"[。！？]+",prose) if x.strip()]
    sizes=[len(x) for x in items]
    return {"sentences":len(sizes),"short_under_18":sum(x<18 for x in sizes),
            "long_over_50":sum(x>50 for x in sizes),
            "mean_sentence_chars":round(sum(sizes)/len(sizes),2) if sizes else 0,
            "han_chars":sum("\u3400"<=c<="\u9fff" for c in prose),
            "paragraph_chars":len(prose),
            "dialogue_quote_marks":prose.count("“"),
            "no_automatic_literary_grade":True}

class PaidSameAuthor:
    def __init__(self,key,root):
        self.root=root
        self.max=MAX_CALLS
        self.reserved=FlashBudget(
            max_calls=MAX_CALLS,max_reserved_output_tokens=MAX_OUTPUT_RESERVATION,
            max_total_tokens=150000)
        self.client=DeepSeekFlashModel(
            api_key=key,budget=self.reserved,timeout_seconds=110,
            on_response_wire=self._observe_wire)
        self.current=None
        self.events=[]
        self.pending_wires={}
    def _observe_wire(self,raw):
        require(type(raw) is bytes and self.current is not None,
                "WF0T_ORPHAN_PROVIDER_WIRE")
        self.pending_wires[self.current]=raw
        self.events[-1]["provider_wire_sha256"]=sha(raw)
        self.events[-1]["provider_response_observed_before_decoding"]=True
    def call(self,arm,stage,name,packet,max_tokens,*,system):
        require(arm in ("A","B") and stage in (0,1) and
                max_tokens in (600,1150,1450,1800),
                "WF0T_MODEL_CALL_OUTSIDE_CONTRACT")
        require(len(self.events)<MAX_CALLS,"WF0T_MODEL_CALL_CAP_EXCEEDED")
        label=f"{arm}-T{stage+1}-{name}-{len(self.events)+1:02d}"
        self.current=label
        self.events.append({"label":label,"arm":arm,"stage":stage+1,
                            "operation":name,"prompt_sha256":sha(packet.prompt),
                            "max_tokens_reserved":max_tokens,
                            "provider_wire_sha256":None})
        # The actual paid novelist response, not WF-written fiction.
        response=self.client.ask_json(role="self_scene_writing",system=system,
                                      user=packet.prompt,max_tokens=max_tokens)
        original=json.dumps(response,ensure_ascii=False,separators=(",",":"))
        self.events[-1]["decoded_model_reply_sha256"]=sha(original)
        self.events[-1]["decoded_original_not_rewritten"]=True
        return original
    def release_wires(self,arm,*,allow):
        # If the novelist copied a long reference passage, never publish that wire.
        for label,raw in list(self.pending_wires.items()):
            if not label.startswith(arm+"-"):
                continue
            if allow:
                path=self.root/arm/"provider-originals"/(label+".json")
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(raw)
            del self.pending_wires[label]

def canonical_response(raw):
    data=json.loads(raw)
    if set(data)=={"type","prose","trace"} and data["type"]=="json_object":
        data={k:v for k,v in data.items() if k!="type"}
    require(set(data)=={"prose","trace"} and type(data["prose"]) is str,
            "WF0T_PROSE_SCHEMA_NOT_VALID")
    return json.dumps(data,ensure_ascii=False,separators=(",",":"))

def perform_arm(arm,author,windows):
    """Writes step1; self-review + actual V119 closure; only then writes step2."""
    scene=f"staged-0t-{arm.lower()}"
    directory=OUT/arm
    directory.mkdir(parents=True,exist_ok=False)
    receipts=[]
    accepted=[]
    previous=None
    changed=False
    held=False
    output={"arm":arm,"stages_completed":0,"novelist_wrote_every_sentence":True,
            "author_revision_observed":False,"valid_author_revision_and_downstream":False,
            "no_canon_or_R2_writes":True,"literary_quality_proven":False,
            "source_reference_sent_to_author":arm=="B"}
    def model_adapter(stage,name,system=AUTHOR_SYSTEM):
        def ask(packet,*,model,api_base,max_tokens):
            require(model is None and api_base is None,
                    "WF0T_WRITER_MODEL_IDENTITY_CHANGED")
            return author.call(arm,stage,name,packet,max_tokens,system=system)
        return ask
    try:
        for i,beat in enumerate(BEATS):
            prompt=build_prompt(
                arm,i,
                previous_prose=accepted[-1]["prose"] if accepted else "",
                previous_effect=accepted[-1]["effect_quote"] if accepted else None,
                reference=windows[i] if arm=="B" else None)
            packet=make_packet(prompt,scene)
            result=model_adapter(i,"prose",WRITER_SYSTEM)(
                packet,model=None,api_base=None,max_tokens=1450)
            result=canonical_response(result)
            doc=json.loads(result)
            require(80<=len(doc["prose"].strip())<=MAX_STAGE_PROSE,
                    "WF0T_TURN_MUST_REMAIN_A_SMALL_SLICE")
            original_enough(doc["prose"],windows)
            checked=check_turn(result,beat,mode="causal_guard",
                               accepted=tuple(accepted),max_prose_chars=1024)
            if i==0:
                decision=_ai_decides_when_to_revisit(
                    raw=result,beat=beat,accepted=(),
                    turn_packet=make_packet(build_prompt(
                        arm,0,reference=windows[0] if arm=="B" else None),scene),
                    ask_model=model_adapter(i,"author-choice"),
                    directory=directory/"writer-own-decision",
                    source_identity_contract="bind_null_current")
                write_json(directory/"author-choice-receipt.json",{
                    "decision":decision["decision"],
                    "reason":decision.get("reason"),
                    "risk":decision.get("risk"),
                    "intended_reader_effect":decision.get("desired_effect"),
                    "source_quote":decision.get("source_quote"),
                    "receipt":decision["receipt"]})
                require(decision["decision"] in ("LOOK_BACK_NOW","MOVE_ON"),
                        "WF0T_INVALID_AUTHOR_DECISION_NO_AUTOMATIC_RETRY")
                if decision["decision"]=="LOOK_BACK_NOW":
                    output["author_revision_observed"]=True
                    patched,edit=_self_edit_one_turn(
                        raw=result,beat=beat,accepted=(),
                        project_id=PROJECT,scene_id=scene,
                        turn_packet=packet,
                        ask_model=model_adapter(i,"edit-or-trace"),
                        round_limit=2,call_allowance=2,
                        directory=directory/"source-guided-author-edit",
                        previous_candidate_state={},cast=CAST,
                        writer_attention={
                            "reason":decision.get("reason"),
                            "risk":decision.get("risk"),
                            "desired_effect":decision.get("desired_effect"),
                            "source_quote":decision.get("source_quote"),
                            "focus":decision.get("focus")})
                    write_json(directory/"edit-receipt.json",edit)
                    if patched!=result:
                        revised=json.loads(patched)
                        original_enough(revised["prose"],windows)
                        checked=check_turn(patched,beat,mode="causal_guard",
                                           accepted=(),max_prose_chars=1024)
                        result=patched
                        changed=True
                        output["revision_receipt_statuses"]=[
                            x["status"] for x in edit["rounds"]]
                    else:
                        statuses=[x.get("status") for x in edit.get("rounds",())]
                        if any(x in ("REJECTED_AND_ROLLED_BACK",
                                     "HELD_NEW_UNVERIFIED_SOURCE_RISK")
                               for x in statuses):
                            held=True
                            raise RuntimeError("WF0T_AUTHOR_REVISION_REJECTED_STOP_DOWNSTREAM")
            if i==1:
                guard=preflight_continuation(
                    checked["prose"],previous,
                    project_id=PROJECT,chapter_index=1,cast=CAST)
                write_json(directory/"second-turn-v117-preflight.json",guard)
                require(not guard["blocked"] and not guard["needs_review"],
                        "WF0T_NEXT_TURN_HAS_UNRESOLVED_SOURCE_RISK")
            previous=external_temporal_step(checked["prose"],cast=CAST,
                                            prior=previous)
            accepted.append(checked)
            path=directory/f"stage-{i+1:02d}-real-author-prose.md"
            path.write_text(checked["prose"],encoding="utf8")
            receipts.append({
                "stage":i+1,"actual_writer_prose_sha256":sha(checked["prose"]),
                "reference_window_sha256":sha(windows[i]) if arm=="B" else None,
                "actual_V96_check":checked["receipt"]["causal_check"],
                "actual_V114_checkpoint_sha256":previous["receipt_sha256"],
                "sentence_diagnostics_only":sentence_lengths(checked["prose"]),
            })
            output["stages_completed"]=len(accepted)
        joined="\n\n".join(x["prose"] for x in accepted)
        original_enough(joined,windows)
        whole=external_temporal_step(joined,cast=CAST)
        core=new_graph(project_id=PROJECT,scene_id=scene)
        core=advance_graph(core,project_id=PROJECT,scene_id=scene,
                           chapter_index=1,prose=joined,events=[])
        # Unified memory must verify the original saved manuscript bytes.
        # Archive the genuine model-authored candidate before memory indexing.
        (directory/"composed-unaccepted.md").write_text(joined,encoding="utf8")
        core=record_chapter_memory(core,project_id=PROJECT,scene_id=scene,
                                   chapter_index=1,
                                   source_path=str(directory/"composed-unaccepted.md"),
                                   prose=joined)
        signed=make_resume(project_id=PROJECT,scene_id=scene,chapter_index=1,
                           checkpoint=whole,unified_narrative_core=core)
        read_resume(signed,project_id=PROJECT,scene_id=scene)
        (directory/"composed-unaccepted.md").write_text(joined,encoding="utf8")
        write_json(directory/"source-stage-receipts.json",receipts)
        output.update(status="COMPLETE_UNACCEPTED_TWO_STAGE_WF_CANDIDATE",
                      signed_candidate_resume_sha256=signed["receipt_sha256"],
                      author_accepted=False,
                      valid_author_revision_and_downstream=changed and
                      len(accepted)==2,
                      prior_turn_prose_replaced_by_model=changed,
                      following_turn_freshly_generated_from_final_source=True,
                      older_downstream_reused=False)
        author.release_wires(arm,allow=True)
    except Exception as exc:
        # No provider retry, no acceptance, no publishing of possible copied
        # private book passages from any incomplete arm's raw wire.
        code=str(exc)
        if not re.fullmatch(r"WF[A-Z0-9_:\-]{3,150}",code):
            code=type(exc).__name__+":SINGLE_RUN_FAILED"
        output.update(status="FAILED_OR_HELD_NO_RETRY",
                      failure_code=code,
                      author_accepted=False,
                      source_repair_may_remain_unverified=held or changed,
                      valid_author_revision_and_downstream=False)
        author.release_wires(arm,allow=False)
    write_json(directory/"STATUS.json",output)
    return output

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    report={"format":"wf.0t.fanren-private-readonly-staged-ab.v1",
            "max_total_paid_calls":MAX_CALLS,
            "max_reserved_output_tokens":MAX_OUTPUT_RESERVATION,
            "no_automatic_retries":True,"reference_never_in_public_artifacts":True,
            "no_original_book_prose_in_reports":True,"model":MODEL,
            "same_freeze_outline_and_beats":True,"candidate_not_canon":True,
            "human_literary_blind_review":"NOT_PERFORMED",
            "real_full_repair_accepted":False}
    author=None
    try:
        # Both source identity and Node checks finish BEFORE any paid request.
        windows,source=download_pinned_private_reference()
        report["reference"]=source
        require_external_runtime()
        key=os.getenv("DEEPSEEK_API_KEY","")
        require(len(key)>=16,"WF0T_AUTHOR_MODEL_KEY_NOT_CONFIGURED")
        # Does not reveal book excerpts even in metadata or exception logs.
        author=PaidSameAuthor(key,OUT)
        arms={}
        for arm in ("A","B"):
            arms[arm]=perform_arm(arm,author,windows)
        report["arms"]=arms
        report["same_model_actual_provider_calls"]=author.reserved.calls_reserved
        report["same_model_usage"]=author.reserved.public_receipt()
        report["complete_anonymous_pair"]=all(
            row["status"]=="COMPLETE_UNACCEPTED_TWO_STAGE_WF_CANDIDATE"
            for row in arms.values())
        report["real_full_repair_accepted"]=any(
            x.get("valid_author_revision_and_downstream",False)
            for x in arms.values())
        report["literary_quality_improvement_proven"]=False
        report["status"]=("PAIRED_REAL_CANDIDATES" if report["complete_anonymous_pair"]
                          else "INCOMPLETE_REAL_PAIR_NO_FALSE_SUCCESS")
        if report["complete_anonymous_pair"]:
            x=(OUT/"A"/"composed-unaccepted.md").read_text("utf8")
            y=(OUT/"B"/"composed-unaccepted.md").read_text("utf8")
            (OUT/"BLIND_PAIR.md").write_text(
                "# 匿名渐进双轨候选，不是原著复制\n\n"+
                "## X\n"+x+"\n\n## Y\n"+y+"\n",
                encoding="utf8")
            write_json(OUT/"UNBLIND_MAPPING.json",{"X":"A","Y":"B"})
    except Exception as exc:
        why=str(exc)
        if not re.fullmatch(r"WF[A-Z0-9_:\-]{3,150}",why):
            why=type(exc).__name__+":NO_PROVIDER_RETRY"
        report.update(status="SOURCE_PREFLIGHT_OR_RUNTIME_FAILED",
                      preflight_code=why,
                      actual_paid_calls=author.reserved.calls_reserved if author else 0,
                      real_full_repair_accepted=False)
    finally:
        if author:
            report["provider_calls_with_private_wire_hash"]=[
                {k:v for k,v in x.items() if k!="raw"}
                for x in author.events]
        report["R2_writes"]=0
        report["canon_writes"]=0
        report["production_main_changed"]=False
        report["railway_deployments"]=0
        write_json(OUT/"STATUS.json",report)
    print("WF0T_STAGED_SOURCE_RESULT "+json.dumps({
        "status":report["status"],
        "actual_provider_calls":(author.reserved.calls_reserved if author else 0),
        "stage_counts":{k:v["stages_completed"] for k,v in
                        report.get("arms",{}).items()},
        "real_complete_author_repair_observed":report["real_full_repair_accepted"],
        "independent_literary_quality_proven":False},
        ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
