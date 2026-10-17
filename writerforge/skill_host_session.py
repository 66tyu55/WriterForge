"""V47 opt-in host-facing WF Skill session, using EXISTING WF production APIs.

A Skill normally uses the host's language cognition; this adapter is a
strict controller, not an alternate model. Host output must be returned via
the controlled CLI and is logged AS HOST-GENERATED. It never claims the host
response was made by Python or that quality improved.

Steps: blind first read -> lock -> full close read -> source-linked
unreviewed literary hypothesis -> baseline and memory-enabled drafts by
the SAME declared host -> a non-independent self-review -> frozen evidence.

No cloud provider is invoked by this code. No historical trials change.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import json
import re

from .db import WriterForgeDB
from .runtime import RuntimeEngine
from .source_study import OriginalStudy, parse_original
from .scene_learning import (
    VerifiedScene, SceneLiteraryStudy, first_read_prompt, close_read_prompt,
)
from .verified_flow import VerifiedWritingFlow, save_candidate

STAGES = ("first", "close", "baseline", "learned", "self_review", "complete")
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{2,63}\Z")
SCENE_CHARS = 6800
MAX_SOURCE = 18000
MAX_DRAFT = 4000


class HostSkillError(ValueError):
    pass


def _sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _json(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False)


def _check(expr, code):
    if not expr:
        raise HostSkillError(code)


def _schema(db):
    db.conn.execute("""CREATE TABLE IF NOT EXISTS wf_host_skill_runs(
        run_id TEXT PRIMARY KEY, project_id TEXT NOT NULL,
        model_id TEXT NOT NULL, source_file TEXT NOT NULL,
        source_sha TEXT NOT NULL, work_id TEXT NOT NULL,
        scene_id TEXT NOT NULL, chapter INTEGER NOT NULL,
        goal TEXT NOT NULL, snapshot_id INTEGER NOT NULL,
        stage TEXT NOT NULL, baseline_sha TEXT, learned_sha TEXT,
        candidate_lesson_json TEXT, baseline_manifest TEXT,
        learned_manifest TEXT, self_review_json TEXT,
        total_failed_submissions INTEGER NOT NULL DEFAULT 0)""")
    db.conn.execute("""CREATE TABLE IF NOT EXISTS wf_host_skill_events(
        run_id TEXT NOT NULL, ordinal INTEGER NOT NULL,
        stage TEXT NOT NULL, prompt_sha TEXT NOT NULL,
        response_sha TEXT NOT NULL, response_kind TEXT NOT NULL,
        PRIMARY KEY(run_id,ordinal))""")
    db.conn.execute("""CREATE TABLE IF NOT EXISTS wf_host_skill_admissions(
        run_id TEXT PRIMARY KEY, state TEXT NOT NULL,
        cause TEXT NOT NULL, candidate_sha TEXT,
        applicability_sha TEXT)""")
    db.conn.commit()


def _load(row, source_file=None):
    path=Path(row["source_file"])
    _check(path.is_file() and path.stat().st_size < MAX_SOURCE*4,
           "HOST_SOURCE_FILE_MISSING_OR_OVERSIZED")
    data=path.read_text(encoding="utf-8-sig")
    _check(_sha(data)==row["source_sha"],"HOST_SOURCE_EDITION_CHANGED")
    chapters=parse_original(data,require_hundred=False,expected_count=1,
                            sequence_start=int(row["chapter"]))
    ch=chapters[0]
    body=ch.text[:SCENE_CHARS]
    cut=max(180,min(2400,len(body)//3))
    _check(len(body)>cut+90,"HOST_SCENE_NOT_LONG_ENOUGH")
    return data,VerifiedScene(
        row["work_id"],ch.number,row["scene_id"],
        row["source_sha"],row["source_sha"],_sha(body),_sha(body[:cut]),
        body,body[:cut],(),
    )


def _trial(db, run_id):
    _schema(db)
    row=db.conn.execute(
        "SELECT * FROM wf_host_skill_runs WHERE run_id=?",(run_id,)
    ).fetchone()
    _check(row is not None,"HOST_RUN_NOT_STARTED")
    return row


def start(db:WriterForgeDB, *, run_id:str, source:str, goal:str,
          model_id:str, chapter:int=1) -> dict:
    _check(isinstance(run_id,str) and SAFE_ID.fullmatch(run_id),
           "HOST_RUN_ID_INVALID")
    _check(isinstance(model_id,str) and 1<=len(model_id)<=120,
           "HOST_MODEL_ID_MISSING")
    _check(isinstance(goal,str) and 35<=len(goal)<=900,
           "HOST_GOAL_NOT_BOUNDED")
    _check(type(chapter) is int and 1<=chapter<=200,
           "HOST_CHAPTER_INVALID")
    path=Path(source).resolve()
    _check(path.is_file() and path.stat().st_size<=MAX_SOURCE*4,
           "HOST_SOURCE_MISSING")
    text=path.read_text(encoding="utf-8-sig")
    _check(400<=len(text)<=MAX_SOURCE,"HOST_ONE_CHAPTER_NOT_BOUNDED")
    parsed=parse_original(text,require_hundred=False,expected_count=1,
                          sequence_start=chapter)
    _check(parsed[0].number==chapter,"HOST_CHAPTER_ID_MISMATCH")
    _schema(db)
    _check(db.conn.execute(
        "SELECT 1 FROM wf_host_skill_runs WHERE run_id=?",(run_id,)
    ).fetchone() is None,"HOST_RUN_ALREADY_EXISTS")
    project="v47-"+run_id
    work="v47-source-"+run_id
    scene="v47-scene-"+run_id
    rt=RuntimeEngine();rt.enter_learn()
    learned=OriginalStudy(db,rt).ingest(
        text,work_id=work,title="unreviewed host original",
        source_uri="host-file:"+_sha(text),require_hundred=False,
        expected_count=1,source_sequence_start=chapter,
        wrapped_lines=True)
    snap=db.conn.execute(
        "SELECT snapshot_id FROM studied_chapters WHERE work_id=? AND chapter=?",
        (work,chapter)).fetchone()["snapshot_id"]
    _check(learned["newly_studied"]==1,"HOST_SOURCE_STUDY_NOT_REAL")
    row={
        "source_file":str(path),"source_sha":_sha(text),
        "work_id":work,"chapter":chapter,"scene_id":scene,
    }
    _,vscene=_load(row)
    SceneLiteraryStudy(db,rt,project).prepare(vscene)
    with db.conn:
        db.conn.execute("""INSERT INTO wf_host_skill_runs(
            run_id,project_id,model_id,source_file,source_sha,
            work_id,scene_id,chapter,goal,snapshot_id,stage)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (run_id,project,model_id,str(path),_sha(text),
             work,scene,chapter,goal,int(snap),"first"))
    return {"run_id":run_id,"stage":"first","source_sha256":_sha(text),
            "source_ingested_into_existing_WF_Xuehai":True,
            "host_identity_attested":False,
            "literary_capability_proven":False}


def _packet(db,row,learned:bool):
    rt=RuntimeEngine();rt.enter_write(int(row["snapshot_id"]))
    base=VerifiedWritingFlow(db,rt,row["project_id"]).prepare(
        row["scene_id"],  # same scene and same goal in both arms
        row["goal"],concerns=("setup_payoff","decision"),
        evaluation_neutral=True,
    )
    fixed="\n请写350至1200字的自然原创小说正文，不要编写写作说明或教学答案。"
    guidance=""
    receipt={"format":"WF.v47-host-continuity.v1",
             "mode":"MEMORY_UNVERIFIED" if learned else "BASELINE",
             "real_experience_applied_to_prompt":False,
             "literary_quality_verified":False}
    if learned:
        from .experience_applicability import choose_experience
        decision=choose_experience(db,row)
        _check(decision.state=="ELIGIBLE_EXPERIMENT_ONLY",
               "HOST_EXPERIENCE_NOT_APPLICABLE_"+decision.cause)
        guidance=decision.guidance
        receipt.update(decision.receipt())
        receipt["real_experience_applied_to_prompt"]=True
    prompt=base.prompt+fixed+guidance
    _check(len(prompt)<=10000,"HOST_DRAFT_PROMPT_BUDGET")
    return replace(base,prompt=prompt,prompt_sha256=_sha(prompt),
                   strategy_receipt=receipt)


def pending(db:WriterForgeDB, run_id:str)->dict:
    row=_trial(db,run_id)
    if row["stage"] in ("complete","abstained"):
        audit=db.conn.execute(
            "SELECT state,cause FROM wf_host_skill_admissions WHERE run_id=?",
            (run_id,)).fetchone()
        return {"run_id":run_id,"stage":row["stage"],"host_prompt":None,
                "experience_admission":dict(audit) if audit else None,
                "independent_literary_approval":False}
    _,scene=_load(row)
    step=row["stage"]
    if step=="first":
        prompt=first_read_prompt(scene)
    elif step=="close":
        st=db.conn.execute(
            "SELECT stage,first_read_json FROM literary_scene_trials "
            "WHERE project_id=? AND scene_id=?",
            (row["project_id"],row["scene_id"])).fetchone()
        _check(st is not None and st["stage"]=="first_read_locked",
               "HOST_FIRST_READ_NOT_FROZEN")
        prompt=close_read_prompt(scene,json.loads(st["first_read_json"]))
    elif step in ("baseline","learned"):
        prompt=_packet(db,row,step=="learned").prompt
    elif step=="self_review":
        _check(row["baseline_sha"] and row["learned_sha"],
               "HOST_DRAFTS_NOT_BOTH_FROZEN")
        # Review is explicitly NOT an independent literary judge.
        prompt=(
            "对以下两篇来自同一宿主的候选稿逐项揭示缺点，不要宣称"
            "文学水平提升。仅输出JSON：baseline_problem、learned_problem、"
            "evidence_baseline、evidence_learned，每个字段为短文字。"
            "证据引用必须在对应稿件真实存在；此评审只是同一宿主自评，"
            "不得用于正式能力晋级。\n"
            "【基线稿】"+_draft_text(db,row,"baseline")+
            "\n【经验稿】"+_draft_text(db,row,"learned")
        )
    else:
        raise HostSkillError("HOST_UNKNOWN_STAGE")
    return {
        "run_id":run_id,"stage":step,"model_id_declared":row["model_id"],
        "host_prompt":prompt,"prompt_sha256":_sha(prompt),
        "prompt_characters":len(prompt),
        "reply_contract":"plain_prose_350_to_4000" if step in
          ("baseline","learned") else "json_object",
        "host_authorship_not_skill_weight_learning":True,
    }


def _draft_text(db,row,which):
    manifest_path=row[which+"_manifest"]
    _check(isinstance(manifest_path,str),"HOST_CANDIDATE_NOT_SAVED")
    meta=json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    text=(Path(manifest_path).parent/meta["candidate_file"]).read_text(encoding="utf-8")
    _check(_sha(text)==meta["candidate_sha256"]==row[which+"_sha"],
           "HOST_CANDIDATE_FILE_CHANGED")
    return text


def _error(db,row):
    with db.conn:
        db.conn.execute(
            "UPDATE wf_host_skill_runs SET total_failed_submissions=total_failed_submissions+1 "
            "WHERE run_id=?",(row["run_id"],)
        )


def submit(db:WriterForgeDB, *, run_id:str, model_id:str,
           reply:str, prompt_sha256:str, output_dir:str)->dict:
    row=_trial(db,run_id)
    _check(model_id==row["model_id"],
           "HOST_MODEL_CHANGED_BETWEEN_STAGES")
    _check(isinstance(reply,str) and len(reply)<=14000 and len(reply)>0,
           "HOST_EMPTY_OR_UNBOUNDED_REPLY")
    request=pending(db,run_id)
    _check(request["stage"] not in ("complete","abstained"),"HOST_TRIAL_ALREADY_COMPLETE")
    _check(request["prompt_sha256"]==prompt_sha256,
           "HOST_REPLY_FOR_DIFFERENT_PROMPT")
    _,scene=_load(row)
    step=row["stage"]
    rt=RuntimeEngine()
    try:
        if step in ("first","close"):
            rt.enter_learn()
            study=SceneLiteraryStudy(db,rt,row["project_id"])
            if step=="first":
                study.lock_first_read(scene,reply,model_id)
                stage="close"
                lesson=None
            else:
                accepted=study.attach_analysis(scene,reply)
                # SOURCE-BASED and MODEL-CANDIDATE, not hand-authored by
                # programmer or promoted. Choose the FIRST bounded hypothesis.
                lesson=accepted["mechanisms"][0]
                lesson={
                    k:lesson[k] for k in (
                        "hypothesis","counterfactual","transfer_question")
                }|{"source_quote_sha256":_sha(accepted["mechanisms"][0]["source_quote"])}
                stage="baseline"
            with db.conn:
                db.conn.execute(
                    "UPDATE wf_host_skill_runs SET stage=?,candidate_lesson_json=COALESCE(?,candidate_lesson_json) "
                    "WHERE run_id=?",(stage,_json(lesson) if lesson else None,run_id))
        elif step in ("baseline","learned"):
            _check(350<=len(reply.strip())<=MAX_DRAFT,
                   "HOST_PROSE_LENGTH_INVALID")
            packet=_packet(db,row,step=="learned")
            saved=save_candidate(
                packet,reply,row["model_id"],Path(output_dir)/run_id)
            next_stage=("learned" if step=="baseline" else "self_review")
            admission=None
            if step=="baseline":
                from .experience_applicability import choose_experience
                admission=choose_experience(db,row)
                if admission.state!="ELIGIBLE_EXPERIMENT_ONLY":
                    next_stage="abstained"
            with db.conn:
                db.conn.execute(
                    "UPDATE wf_host_skill_runs SET stage=?, "+step+"_sha=?, "+step+"_manifest=? "
                    "WHERE run_id=?",
                    (next_stage,_sha(reply),saved["manifest"],run_id))
                if admission is not None:
                    db.conn.execute(
                        "INSERT INTO wf_host_skill_admissions VALUES(?,?,?,?,?)",
                        (run_id,admission.state,admission.cause,
                         admission.candidate_sha,admission.applicability_sha))
        else:
            data=json.loads(reply)
            required={"baseline_problem","learned_problem",
                      "evidence_baseline","evidence_learned"}
            _check(isinstance(data,dict) and set(data)==required,
                   "HOST_SELF_REVIEW_SCHEMA_INVALID")
            for field in required:
                _check(isinstance(data[field],str) and 8<=len(data[field])<=450,
                       "HOST_SELF_REVIEW_FIELD_OUT_OF_BOUNDS")
            _check(data["evidence_baseline"] in _draft_text(db,row,"baseline"),
                   "HOST_BASELINE_REVIEW_QUOTE_NOT_IN_STORY")
            _check(data["evidence_learned"] in _draft_text(db,row,"learned"),
                   "HOST_LEARNED_REVIEW_QUOTE_NOT_IN_STORY")
            with db.conn:
                db.conn.execute(
                    "UPDATE wf_host_skill_runs SET stage='complete',self_review_json=? "
                    "WHERE run_id=?",(_json(data),run_id))
        with db.conn:
            count=db.conn.execute(
                "SELECT COUNT(*) n FROM wf_host_skill_events WHERE run_id=?",
                (run_id,)).fetchone()["n"]
            db.conn.execute(
                "INSERT INTO wf_host_skill_events VALUES(?,?,?,?,?,?)",
                (run_id,count,step,prompt_sha256,_sha(reply),
                 "HOST_MODEL_REPLY_NOT_SKILL_WEIGHT_LEARNING"))
    except (ValueError,KeyError,TypeError) as e:
        _error(db,row)
        raise HostSkillError("HOST_STAGE_REJECTED: "+str(e)) from e
    return {"run_id":run_id,"completed_stage":step,
            "next_stage":_trial(db,run_id)["stage"],
            "response_sha256":_sha(reply),
            "original_text_and_history_untouched":True,
            "literary_success_proven":False}


def summary(db:WriterForgeDB,run_id:str)->dict:
    row=_trial(db,run_id)
    events=db.conn.execute(
        "SELECT ordinal,stage,prompt_sha,response_sha FROM wf_host_skill_events "
        "WHERE run_id=? ORDER BY ordinal",(run_id,)
    ).fetchall()
    evidence=db.conn.execute(
        "SELECT state,cause,candidate_sha,applicability_sha "
        "FROM wf_host_skill_admissions WHERE run_id=?",(run_id,)
    ).fetchone()
    return {"run_id":run_id,"stage":row["stage"],
            "experience_admission":dict(evidence) if evidence else None,
            "host_id_claimed_not_attested":row["model_id"],
            "source_sha256":row["source_sha"],
            "learned_experience_recorded":bool(row["candidate_lesson_json"]),
            "baseline_draft_sha256":row["baseline_sha"],
            "learned_draft_sha256":row["learned_sha"],
            "candidate_prose_author_approved":False,
            "self_review_is_not_independent":bool(row["self_review_json"]),
            "failed_submissions":row["total_failed_submissions"],
            "events":[dict(e) for e in events],
            "skill_autonomous_literary_gain_proven":False,
            "host_installation_proven":False}



def run_with_local_host(db:WriterForgeDB, *, run_id:str, source:str,
                        goal:str, model_id:str, output_dir:str,
                        chapter:int=1, api_base:str="http://127.0.0.1:1234/v1")->dict:
    """One WF-controlled execution, ONE explicitly configured loopback LLM.

    NOT an assistant answering its own test. WF builds each exact prompt, the
    same local host computes each response, then WF validates/persists it.
    Fail without retry or fallback when the real model is not running.
    In GitHub CI there is no model so this path is deliberately NOT a
    completed literary-generation proof.
    """
    from .verified_flow import GroundedDraftPacket, local_chat_completion
    _check(isinstance(output_dir,str) and bool(output_dir.strip()),
           "HOST_OUTPUT_DIR_INVALID")
    _schema(db)
    old=db.conn.execute(
        "SELECT run_id,model_id,source_file FROM wf_host_skill_runs WHERE run_id=?",
        (run_id,)).fetchone()
    if old is None:
        start(db,run_id=run_id,source=source,goal=goal,
              model_id=model_id,chapter=chapter)
    else:
        _check(old["model_id"]==model_id,
               "HOST_MODEL_CHANGED_BETWEEN_STAGES")
        _check(Path(old["source_file"]).resolve()==Path(source).resolve(),
               "HOST_RESTART_SOURCE_DIFFERENT")
    performed=[]
    for i in range(5):
        request=pending(db,run_id)
        if request["stage"] in ("complete","abstained"):
            break
        prompt=request["host_prompt"]
        packet=GroundedDraftPacket(
            scene_id=run_id+"-"+request["stage"],project_id=run_id,
            snapshot_id=0,evidence=(),craft_ids=(),prompt=prompt,
            prompt_sha256=request["prompt_sha256"],
        )
        # The *real* local completion is the only author; no host-chat
        # assistant, second model, examiner answer or mocked fallback.
        reply=local_chat_completion(
            packet,model=model_id,api_base=api_base,
            max_tokens=3000 if request["stage"] in ("baseline","learned") else 1700,
        )
        receipt=submit(db,run_id=run_id,model_id=model_id,
                       reply=reply,prompt_sha256=request["prompt_sha256"],
                       output_dir=output_dir)
        performed.append({"stage":request["stage"],
                          "response_sha256":receipt["response_sha256"]})
    result=summary(db,run_id)
    result["loopback_completion_adapter_invocations"]=len(performed)
    result["host_model_identity_cryptographically_attested"]=False
    result["response_provider_expected"]="configured_localhost_only"
    result["independent_literary_judgement_done"]=False
    result["same_seed_blind_literary_quality_AB_proven"]=False
    return result
