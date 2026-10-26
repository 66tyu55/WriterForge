"""0.AM: one REAL bounded WriterForge G chapter from frozen 0.AH history.

1. Verify archived historical DeepSeek author text and original provider bytes
   from 40201458798 against the independently recovered 40202483990 artifact.
2. Make a LOCAL, unaccepted candidate V114 + unified NarrativeCore source root.
3. Invoke WriterForge's real AutonomousWriting(continuity_guard, ai_decides),
   never substitute model-authored prose, reasons, or edit operations.
4. If the author chooses previous-turn revision, G must invalidate/recreate
   downstream and source-link the rebuilt V114/V117/core. KEEP/MOVE_ON is valid;
   it is NOT proof of literary quality. Every provider wire is saved FIRST.

No R2, originals training, Canon, Railway, main or second memory owner.
No retry after provider/schema/trace failures and no grading-driven rewrites.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import json
import os
import re

from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.writing_assist import AutonomousWriting,InvisibleWritingAssist
from writerforge.deepseek_flash_model import DeepSeekFlashModel,FlashBudget
from writerforge.v114_external_story_state import external_temporal_step,require_external_runtime
from writerforge.v117_continuity_trace import make_resume,read_resume
from writerforge.narrative_core import new_graph,read_core_from_resume

FIRST=Path("wf0am_frozen_0ah_first")
OUTPUT=Path("wf_0am_real_history_closed_loop_20261026")
EXPECTED_SOURCE_SHA="4069722777f98ef5b9bc3b3eaea5429def9ab9b61be0a224114fae9d7ff97991"
ORIGINAL_SOURCE_RUN=40201458798
ORIGINAL_RECOVERY_RUN=40202483990
PROJECT="0am-unaccepted-original-history"
SCENE="0am-same-model-messenger-source"
CAST=("秦渊","驿卒","亲兵")
MAX_MODEL_CALLS=12
MAX_COMPLETION_RESERVATION=26000
WRITER_SYSTEM=(
    "你是续写自己既有历史原创小说的 DeepSeek Flash 写作模型。"
    "只输出当前任务要求的严格 JSON，绝不输出解释或Markdown。"
    "由你自己确定人物所知、动作与后果，决定要不要回头删改。"
    "没有收到的文书不可被角色假装知道内容，未见的马蹄来源不能变成确知。"
    "WriterForge 仅检查真实字面引用和未接受候选事务，不能代替你创作。"
    "不得模仿或复制其他作品的人物、情节、原句。"
)
GOALS=[
    "边关书记官秦渊继续核对传令路径、到达时间和消息不确定性，"
    "夜色里听见的马蹄尚不能确定是谁，主帅何时收到书信也未知。"
    "只写两小段，每段尽量200至350个中文字符，不写整章。"
]


def h(s):
    return sha256(s if isinstance(s,bytes) else s.encode("utf8")).hexdigest()


def require(ok,code):
    if not ok: raise RuntimeError(code)


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,
                  sort_keys=True,indent=2),encoding="utf8")


def verify_old_real_source():
    original=FIRST/"provider-originals"/"history_message_WF-author.json"
    # The FIRST official DeepSeek paid artifact alone contains both
    # exact provider bytes and authored prose with the same source receipt.
    # A second cross-run download is not required and may fail on GitHub
    # credentials; never weaken the original signed provider SHA check.
    source_file=FIRST/"author-originals"/"history_message-WF.md"
    manifest=json.loads((FIRST/"STATUS.json").read_text("utf8"))
    events={r["task"]:r for r in manifest["provider_calls"]}
    entry=events["history_message_WF-author"]
    raw=original.read_bytes()
    require(h(raw)==entry["raw_provider_sha256"] and
            entry["original_wire_preserved"] is True,
            "WF0AM_REAL_ORIGINAL_PROVIDER_WIRE_SHA_MISMATCH")
    response=json.loads(raw)
    require(response["model"]=="deepseek-flash" and
            len(response["choices"])==1 and
            response["choices"][0]["finish_reason"]=="stop",
            "WF0AM_REAL_ORIGINAL_MODEL_OR_FINISH_CHANGED")
    author=json.loads(response["choices"][0]["message"]["content"])
    old=author["prose"].strip()
    require(old==source_file.read_text("utf8") and
            h(old)==EXPECTED_SOURCE_SHA and
            h(old)==manifest["cases"]["history_message"]["WF_source_sha256"],
            "WF0AM_REAL_HISTORICAL_AUTHORED_SOURCE_DRIFT")
    require(len(old)>=200 and len(old)<=350 and
            "明日卯时" in old and "秦渊" in old,
            "WF0AM_SOURCE_REQUIREMENT_DRIFT")
    return old,h(raw)


def local_source_only_snapshot(db,real_original):
    """One proven author-origin source excerpt, not a training dataset.

    WF VerifiedWritingFlow requires local evidence. The ONLY local evidence
    is a literal span of this same earlier writer microfiction, grounded in
    the officially preserved wire, never a third-party book or 15-chapter set.
    The temporary DB is not a permanent memory owner or a Canon database.
    """
    c=db.conn
    id=int(c.execute(
        "INSERT INTO snapshots(parent_id,status,layout,note) "
        "VALUES(NULL,'published','full','0am frozen original provider only')"
    ).lastrowid)
    quote=real_original[:88]
    c.execute(
        "INSERT INTO studied_works(work_id,title,source_uri,source_sha256,chapter_count) "
        "VALUES(?,?,?,?,?)",
        ("wf-0ah-original","0.AH同模型原作家冻结历史微段",
         "wf-provider-original://40201458798/history_message-WF",
         h(real_original),1))
    c.execute(
        "INSERT INTO source_spans(work_id,chapter,paragraph,sentence,excerpt,"
        "source_sha256,tracks_json,craft_json) VALUES(?,?,?,?,?,?,?,?)",
        ("wf-0ah-original",1,1,1,quote,h(quote),"{}","{}"))
    c.execute(
        "INSERT INTO studied_chapters(work_id,chapter,chapter_sha256,heading,"
        "source_spans,retrieval_entries,snapshot_id) VALUES(?,?,?,?,?,?,?)",
        ("wf-0ah-original",1,h(real_original),"上次未接受候选来源",1,1,id))
    c.execute(
        "INSERT INTO xuehai_entries(snapshot_id,work_id,chapter,paragraph,"
        "sentence,text,library_class,culture,genre,source_role,function,effect,"
        "method_cluster,source_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (id,"wf-0ah-original",1,1,1,quote,"原创作者此前已写文本","中国",
         "古代白话","core","decision","unverified",
         "prior_source_not_literary_style_reward",h(quote)))
    c.commit()
    return id


class OneRealAuthor:
    def __init__(self,secret):
        self.records=[]
        self.active=None
        self.budget=FlashBudget(
            max_calls=MAX_MODEL_CALLS,
            max_reserved_output_tokens=MAX_COMPLETION_RESERVATION,
            max_total_tokens=150000)
        self.model=DeepSeekFlashModel(
            api_key=secret,budget=self.budget,timeout_seconds=110,
            on_response_wire=self.preserve_before_parse)

    def preserve_before_parse(self,wire):
        require(self.active is not None and type(wire) is bytes,
                "WF0AM_REAL_ORPHAN_PROVIDER_RESPONSE")
        path=OUTPUT/"provider-originals"/(
            f"{len(self.records):02d}-real-model-wire.json")
        path.parent.mkdir(parents=True,exist_ok=True)
        require(not path.exists() and self.records[-1]["wire_sha256"] is None,
                "WF0AM_NO_WIRE_OVERWRITE_OR_RETRY")
        path.write_bytes(wire)
        self.records[-1]["wire_sha256"]=h(wire)
        self.records[-1]["original_wire_saved_before_parsing"]=True

    def ask(self,packet,*,model,api_base,max_tokens):
        require(model=="deepseek-flash" and type(packet.prompt) is str
                and len(packet.prompt)>60 and
                len(self.records)<MAX_MODEL_CALLS,
                "WF0AM_UNEXPECTED_WRITER_MODEL_OR_CALL_LIMIT")
        index=len(self.records)+1
        name=f"{index:02d}-request.json"
        (OUTPUT/"model-requests").mkdir(parents=True,exist_ok=True)
        event={
            "index":index,"model":"deepseek-flash",
            "prompt_sha256":h(packet.prompt),
            "max_completion_tokens_reserved":max_tokens,
            "wire_sha256":None,
            "original_wire_saved_before_parsing":False}
        self.records.append(event)
        save(OUTPUT/"model-requests"/name,{
            "format":"wf.0am.verbatim-model-request.v1",
            "prompt":packet.prompt,
            "prompt_sha256":h(packet.prompt),
            "max_tokens":max_tokens,
            "canonical_literary_truth":False})
        self.active=index
        try:
            obj=self.model.ask_json(
                role="self_scene_writing",system=WRITER_SYSTEM,
                user=packet.prompt,max_tokens=max_tokens)
            raw=json.dumps(obj,ensure_ascii=False,separators=(",",":"))
            event["decoded_json_sha256"]=h(raw)
            event["source_only_format_recovery"]=(self.model.
                                                  last_response_format_recovery)
            return raw
        finally:
            self.active=None


def main():
    require(not OUTPUT.exists(),"WF0AM_PRIVATE_RESULT_MUST_NEVER_BE_OVERWRITTEN")
    OUTPUT.mkdir(parents=True)
    status={
        "format":"wf.0am.single-model-original-history-full-g-once.v1",
        "status":"NOT_STARTED","original_author_run":ORIGINAL_SOURCE_RUN,
        "original_recovery_run":ORIGINAL_RECOVERY_RUN,
        "source_sha256":EXPECTED_SOURCE_SHA,
        "source_is_unaccepted_candidate":True,
        "new_story_authored_only_by_deepseek":True,
        "new_revision_chosen_only_by_writer":True,
        "model_calls":0,"max_model_calls":MAX_MODEL_CALLS,
        "main_modified":False,"R2_reads":0,"R2_writes":0,
        "canon_writes":0,"Railway_deployments":0,
        "literary_improvement_proven":False,
        "independent_human_blind_grades":False,
        "existing_narrative_core_only":True,"model_events":[],
    }
    writer=None
    db=None
    try:
        require(not any(os.getenv(k) for k in (
            "WRITERFORGE_R2_ACCOUNT_ID","WRITERFORGE_R2_ACCESS_KEY_ID",
            "OPENAI_API_KEY","DISCOVERY_API_KEY","OPENROUTER_API_KEY")),
            "WF0AM_FORBIDDEN_SOURCE_VENDOR_OR_R2_SECRET_PRESENT")
        old,old_wire_sha=verify_old_real_source()
        status["original_wire_sha256"]=old_wire_sha
        (OUTPUT/"frozen-original-history.md").write_text(old,encoding="utf8")
        save(OUTPUT/"frozen-original-provenance.json",{
            "source_sha256":h(old),"original_wire_sha256":old_wire_sha,
            "source_prose_preserved":True,"prior_source_semantics_unverified":True,
            "prior_author_accepted":False,
            "new_model_calls":0})
        secret=os.getenv("DEEPSEEK_API_KEY","")
        require(len(secret)>=16,"WF0AM_EXISTING_DEEPSEEK_MODEL_KEY_ABSENT")
        require_external_runtime()
        checkpoint=external_temporal_step(old,cast=CAST)
        graph=new_graph(project_id=PROJECT,scene_id=SCENE,chapter_index=0)
        root=make_resume(project_id=PROJECT,scene_id=SCENE,chapter_index=0,
                         checkpoint=checkpoint,unified_narrative_core=graph)
        require(root["author_accepted"] is False and
                root["source_checkpoint_sha256"]==checkpoint["receipt_sha256"],
                "WF0AM_BASELINE_SOURCE_ROOT_NOT_SIGNED")
        save(OUTPUT/"root-unaccepted-resume.json",root)
        db=WriterForgeDB(OUTPUT/"local-one-run-source-only.db")
        snapshot=local_source_only_snapshot(db,old)
        rt=RuntimeEngine()
        rt.enter_write(snapshot)
        assist=InvisibleWritingAssist(
            db,rt,PROJECT,SCENE,
            "以真实人物的有限认知继续边关文书送达，短片段由DeepSeek自己写。",
            model="deepseek-flash",api_base="https://api.deepseek.com/v1",
            source_genre="古代白话")
        writer=OneRealAuthor(secret)
        outline=(
            "【已存在的同一原创写作模型旧文，仍未作者接受】\n"+old+
            "\n【源边界】这是真实旧正文，不是新小说计划："
            "申时末旧信最快明日卯时抵达；听见马蹄不证明信使已经起程，"
            "更不能证明主帅收到。旧人物心理与来源以旧文字为准。"
            "\n【后续原创任务】只写接下来发生的短时段，每个小片段200到350字。"
            "作者自行决定留白、人物动作、选择、是否回头修句；"
            "你可以不修改，无文学分数目标。"
        )
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=writer.ask):
            result=AutonomousWriting(assist).run(
                outline=outline,chapter_goals=GOALS,
                draft_mode="continuity_guard",
                resume_story_checkpoint=root,
                narrative_memory_backend="local",
                self_edit_rounds=1,
                self_edit_timing="ai_decides",
                reader_first_self_review=False,
                output_dir=OUTPUT/"g-unaccepted-job")
        require(len(result["chapters"])==1,
                "WF0AM_WRITER_DID_NOT_FINISH_ONE_CANDIDATE_CHAPTER")
        chapter=result["chapters"][0]
        source=Path(chapter["candidate"]).read_text("utf8")
        unaccepted=json.loads(Path(chapter[
            "v117_unreviewed_text_trace_resume"]).read_text("utf8"))
        verified=read_resume(unaccepted,project_id=PROJECT,scene_id=SCENE)
        revised_graph=read_core_from_resume(
            unaccepted,project_id=PROJECT,scene_id=SCENE)
        link=revised_graph["source_temporal_link"]
        require(verified["receipt_sha256"]==unaccepted["source_checkpoint_sha256"]
                and link["whole_chapter_sha256"]==h(source)
                and link["source_assembly_verified"] is True
                and link["ancestry_fully_verified"] is True
                and revised_graph["parent_sha256"]==graph["receipt_sha256"],
                "WF0AM_NEW_CONTINUATION_NOT_SOURCE_GRAPH_VERIFIED")
        require(old== (OUTPUT/"frozen-original-history.md").read_text("utf8"),
                "WF0AM_ORIGINAL_WRITER_TEXT_OVERWRITTEN")
        edits=result.get("wf_self_edit_previous_turn_rewinds",0)
        status.update({
            "status":"SIGNED_UNACCEPTED_CONTINUATION_COMPLETED",
            "one_visible_new_chapter_sha256":h(source),
            "new_chapter_chars":len(source),
            "revised_previous_turn_count":edits,
            "previous_turn_rewind_and_downstream_rebuilt":edits>0,
            "final_core_receipt_sha256":revised_graph["receipt_sha256"],
            "final_resume_receipt_sha256":unaccepted["receipt_sha256"],
            "new_chapter_author_accepted":unaccepted["author_accepted"],
            "wf_edit_receipts_source":"g-unaccepted-job only",
            "writer_chose_to_revamp":edits>0,
            "unaccepted_fiction_not_relabelled_canon":True,
        })
    except Exception as error:
        code=str(error)
        status["status"]="SOURCE_OR_WRITER_FAILED_SAFELY_NO_RETRY"
        status["error_code"]=(code if re.fullmatch(r"WF[A-Z0-9_:\-]{3,170}",code)
                              else type(error).__name__+":NO_MODEL_RETRY")
    finally:
        if db is not None: db.close()
        if writer is not None:
            status["model_calls"]=writer.budget.calls_reserved
            status["model_usage"]=writer.budget.public_receipt()
            status["model_events"]=writer.records
        save(OUTPUT/"STATUS.json",status)
        print("WF0AM_G_REAL "+json.dumps({
            "status":status["status"],"calls":status["model_calls"],
            "source_sha256":status["source_sha256"],
            "new_prose_sha256":status.get("one_visible_new_chapter_sha256"),
            "previous_turn_rewinds":status.get(
                "revised_previous_turn_count"),
            "canonical_writes":0,"new_literary_grade":False,
            "error":status.get("error_code"),
        },ensure_ascii=False),flush=True)
    if status["status"]!="SIGNED_UNACCEPTED_CONTINUATION_COMPLETED":
        raise RuntimeError("WF0AM_REAL_G_PARTIAL_EVIDENCE_PRESERVED_NO_RETRY")


if __name__=="__main__":
    main()
