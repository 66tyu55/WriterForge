"""Local WriterForge Studio: REAL keystroke-event entrypoint for V26.

Python Skill code cannot see what somebody types into an unrelated editor.
This intentionally supplies its own loopback-only browser editor, with
debounced two-choice assistance, automatic local draft saving, and a single
bounded chapter-writing job. No browser cloud calls or manual corpus browsing.
"""
from __future__ import annotations

from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from threading import Event, Lock, Semaphore, Thread
import json
import os
import re
import shutil
import secrets
import time
from urllib.parse import urlsplit

from .db import WriterForgeDB
from .runtime import RuntimeEngine
from .writing_assist import (
    InvisibleWritingAssist, AutonomousWriting, WriterDraftCancelled,
    _ai_decides_cross_chapter, _validate_unaccepted_fork_resume,
)
from .v117_continuity_trace import read_resume, ContinuityTraceError
from .narrative_core import read_core_from_resume, NarrativeCoreError
from .verified_flow import WritingExecutionError

MAX_REQUEST_BYTES = 30_000
MAX_DRAFT_CHARS = 12_000
MAX_HISTORY = 128


class StudioError(ValueError):
    pass


class RevisionConflict(StudioError):
    pass


class StudioStore:
    """Single-scene bounded autosave; NOT a formal accepted StoryCommit."""

    def __init__(self,root:str|Path,project:str,scene:str):
        if not project or not scene or len(project)>128 or len(scene)>128:
            raise StudioError("project and scene are required and limited to 128 characters")
        folder=sha256((project+"\0"+scene).encode("utf-8")).hexdigest()[:22]
        self.path=Path(root).expanduser().resolve()/folder
        self.path.mkdir(parents=True,exist_ok=True)
        self._lock=Lock()

    def _load_unlocked(self) -> dict:
        draft=self.path/"draft.md"
        meta=self.path/"meta.json"
        body=draft.read_text(encoding="utf-8") if draft.exists() else ""
        if len(body)>MAX_DRAFT_CHARS:
            raise StudioError("autosaved manuscript exceeds maximum size")
        info=json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else {}
        return {"text":body,"revision":int(info.get("revision",0)),
                "sha256":sha256(body.encode("utf-8")).hexdigest()}

    def load(self) -> dict:
        with self._lock:
            return self._load_unlocked()

    @staticmethod
    def _atomic(path:Path,content:str):
        temp=path.with_name(path.name+".partial")
        try:
            temp.write_text(content,encoding="utf-8")
            os.replace(temp,path)
        finally:
            temp.unlink(missing_ok=True)

    def save(self,text:str,expected_revision:int) -> dict:
        if not isinstance(text,str) or len(text)>MAX_DRAFT_CHARS:
            raise StudioError("manuscript must be at most 12000 characters")
        if not isinstance(expected_revision,int) or isinstance(expected_revision,bool) or expected_revision<0:
            raise StudioError("invalid manuscript revision")
        with self._lock:
            current=self._load_unlocked()
            if current["revision"]!=expected_revision:
                raise RevisionConflict("manuscript changed since last autosave")
            if current["text"]==text:
                return {**current,"saved":True}
            nextrev=expected_revision+1
            self._atomic(self.path/"draft.md",text)
            self._atomic(self.path/"meta.json",json.dumps({
                "revision":nextrev,
                "sha256":sha256(text.encode("utf-8")).hexdigest(),
            }))
            return {"revision":nextrev,"saved":True,
                    "sha256":sha256(text.encode("utf-8")).hexdigest()}

    def choice(self,*,choice_index:int,prompt_sha256:str) -> dict:
        if choice_index not in (0,1) or isinstance(choice_index,bool):
            raise StudioError("only one of the two generated choices may be selected")
        if (not isinstance(prompt_sha256,str) or len(prompt_sha256)!=64
            or any(ch not in "0123456789abcdef" for ch in prompt_sha256)):
            raise StudioError("invalid suggestion provenance")
        with self._lock:
            path=self.path/"choice_events.json"
            old=json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
            if not isinstance(old,list):
                raise StudioError("choice history corrupted")
            old=old[-(MAX_HISTORY-1):]
            old.append({
                "choice_index":choice_index,"prompt_sha256":prompt_sha256,
                "recorded_at":int(time.time()),
                "status":"weak_author_selection_not_a_verified_style_rule",
            })
            self._atomic(path,json.dumps(old,ensure_ascii=False))
            return {"recorded":True,"count":len(old),
                    "learning_rule_automatically_promoted":False}


def _delete_only_job_folder(root:Path,base:Path,job_id:str):
    """Erase only THIS job's unaccepted outputs, never author autosave.

    No absolute arbitrary path arrives from an HTTP request. Check the
    exact parent and session name BEFORE recursive removal; do not follow
    symlinks or delete previous jobs, shared snapshots, manuscript drafts,
    Canon, or any R2 file.
    """
    if not isinstance(job_id,str) or not re.fullmatch(r"[a-f0-9]{16}",job_id):
        raise StudioError("invalid author draft job id")
    parent=base.resolve()
    if (root.is_symlink() or root.name!=job_id or
        root.resolve().parent!=parent or
        base.is_symlink()):
        raise StudioError("refused unsafe draft directory deletion")
    if root.exists():
        shutil.rmtree(root)


class StudioService:
    def __init__(self,*,db_path:str|Path,project:str,scene:str,goal:str,
                 model:str,api_base:str="http://127.0.0.1:1234/v1",
                 output_dir:str|Path="writing_runs/studio",source_genre:str="古代白话"):
        if not goal.strip() or len(goal)>2000 or not model:
            raise StudioError("valid scene goal and locally configured model are required")
        self.db_path=Path(db_path)
        if not self.db_path.is_file():
            raise StudioError("a downloaded and studied SQLite DB is required")
        self.project,self.scene,self.goal=project,scene,goal
        self.model,self.api_base,self.source_genre=model,api_base,source_genre
        self.output_dir=Path(output_dir).expanduser().resolve()
        self.store=StudioStore(self.output_dir,project,scene)
        self._model_busy=Semaphore(1)
        self._job_lock=Lock()
        self._job=None
        self._job_folder=None
        self._cancel_event=None
        self._continue_event=None
        self._last_unreviewed_resume=None
        self._last_unreviewed_job_id=None
        self._selected_fork_receipt=None
        self._branch_catalog=None
        self._selection_restore_warning=None
        self._token=secrets.token_urlsafe(30)
        # Verify a REAL published snapshot on startup (not a fake mode flag).
        with self._writer() as assistant:
            _=assistant.flow.begin_draft(scene)
        # Unaccepted branch selection is existing Studio metadata, never a
        # second story memory. All V117 and graph receipts are revalidated.
        try:
            self._restore_branch_catalog()
        except (StudioError,WritingExecutionError,OSError,ValueError) as error:
            self._selection_restore_warning=str(error)[:180]
            self._last_unreviewed_resume=None
            self._last_unreviewed_job_id=None
            self._selected_fork_receipt=None
            self._branch_catalog=None

    class _Context:
        def __init__(self,parent):self.parent=parent
        def __enter__(self):
            self.db=WriterForgeDB(self.parent.db_path)
            try:
                row=self.db.conn.execute(
                    "SELECT id FROM snapshots WHERE status='published' ORDER BY id DESC LIMIT 1"
                ).fetchone()
                if row is None:
                    raise StudioError("the selected SQLite has no published source study")
                rt=RuntimeEngine()
                rt.enter_write(int(row["id"]))
                self.assistant=InvisibleWritingAssist(
                    self.db,rt,self.parent.project,self.parent.scene,self.parent.goal,
                    model=self.parent.model,api_base=self.parent.api_base,
                    source_genre=self.parent.source_genre,
                )
                return self.assistant
            except Exception:
                self.db.close()
                raise
        def __exit__(self,*args):
            self.db.close()
            return False

    def _writer(self):
        return StudioService._Context(self)

    def _branch_file(self,job_id:str,path:str,*,max_bytes=4_000_000):
        if (type(job_id) is not str or
            re.fullmatch(r"[a-f0-9]{16}",job_id) is None or
            type(path) is not str or not path or
            Path(path).is_absolute() or ".." in Path(path).parts):
            raise StudioError("WF_STUDIO_BRANCH_PATH_INVALID")
        root=self.output_dir/"autonomous"/job_id
        relative=Path(path)
        if relative.parts[:2]!=("autonomous",job_id):
            raise StudioError("WF_STUDIO_BRANCH_NOT_CURRENT_PROJECT")
        target=self.output_dir/relative
        if (not target.resolve().is_relative_to(root.resolve()) or
            not target.is_file() or
            not 0<target.stat().st_size<=max_bytes or
            root.is_symlink() or self.output_dir.is_symlink()):
            raise StudioError("WF_STUDIO_BRANCH_FILE_INVALID")
        # Prevent a symlink within the path from escaping/redirecting source.
        node=self.output_dir
        for part in relative.parts:
            node=node/part
            if node.is_symlink():
                raise StudioError("WF_STUDIO_BRANCH_SYMLINK_BLOCKED")
        return target

    def _branch_relative(self,job_id,path):
        if type(path) is not str:
            raise StudioError("WF_STUDIO_BRANCH_RELATIVE_NOT_STRING")
        full=Path(path)
        root=self.output_dir/"autonomous"/job_id
        if (not full.resolve().is_relative_to(root.resolve()) or
            not full.is_file()):
            raise StudioError("WF_STUDIO_BRANCH_FOREIGN_FILE")
        relative=str(full.resolve().relative_to(self.output_dir))
        self._branch_file(job_id,relative)
        return relative

    @staticmethod
    def _selection_hash(doc):
        return sha256(json.dumps(doc,ensure_ascii=False,sort_keys=True,
                                  separators=(",",":")).encode("utf8")).hexdigest()

    def _build_branch_catalog(self,*,job_id,branch_results,selected):
        if (type(branch_results) is not dict or
            set(branch_results) not in ({"original"},
                                        {"original","revised"}) or
            selected not in branch_results):
            raise StudioError("WF_STUDIO_BRANCH_OPTIONS_INVALID")
        branches={}
        for name,result in branch_results.items():
            if type(result) is not dict or type(result.get("job_dir")) is not str:
                raise StudioError("WF_STUDIO_BRANCH_JOB_RESULT_INVALID")
            job_dir=Path(result["job_dir"])
            manifest=self._branch_relative(job_id,str(job_dir/"job_manifest.json"))
            manifest_path=self._branch_file(job_id,manifest)
            info=json.loads(manifest_path.read_text("utf8"))
            if (type(info) is not dict or
                info.get("project_id")!=self.project or
                info.get("model_used")!=self.model or
                info.get("status")!="candidates_saved" or
                type(info.get("chapters")) is not list or
                not info["chapters"]):
                raise StudioError("WF_STUDIO_BRANCH_MANIFEST_INVALID")
            final_resume=self._branch_relative(
                job_id,info["chapters"][-1]["v117_unreviewed_text_trace_resume"])
            resume_path=self._branch_file(job_id,final_resume)
            resume=json.loads(resume_path.read_text("utf8"))
            try:
                read_resume(resume,project_id=self.project,scene_id=self.scene)
                core=read_core_from_resume(
                    resume,project_id=self.project,scene_id=self.scene)
                if core is None:
                    raise StudioError("WF_STUDIO_BRANCH_UNIFIED_CORE_MISSING")
            except (ContinuityTraceError,NarrativeCoreError) as error:
                raise StudioError(
                    "WF_STUDIO_BRANCH_RESUME_INVALID:"+str(error)) from None
            row={
                "manifest":manifest,
                "manifest_sha256":sha256(manifest_path.read_bytes()).hexdigest(),
                "resume":final_resume,
                "resume_sha256":resume["receipt_sha256"],
            }
            if name=="revised":
                fork_path=self._branch_relative(
                    job_id,result["cross_chapter_fork_receipt"])
                row["fork_receipt"]=fork_path
                row["fork_receipt_file_sha256"]=sha256(
                    self._branch_file(job_id,fork_path).read_bytes()).hexdigest()
            branches[name]=row
        doc={
            "format":"wf.studio.unaccepted-branch-selection.v1",
            "project_id":self.project,"scene_id":self.scene,
            "model":self.model,"job_id":job_id,
            "branches":branches,"selected":selected,
            "author_accepted":False,"canon_writes":0,
        }
        doc["receipt_sha256"]=self._selection_hash(doc)
        self._validate_branch_catalog(doc)
        return doc

    def _validate_branch_catalog(self,doc):
        if (type(doc) is not dict or
            set(doc)!={"format","project_id","scene_id","model","job_id",
                       "branches","selected","author_accepted","canon_writes",
                       "receipt_sha256"} or
            doc["format"]!="wf.studio.unaccepted-branch-selection.v1" or
            doc["project_id"]!=self.project or doc["scene_id"]!=self.scene or
            doc["model"]!=self.model or
            doc["author_accepted"] is not False or
            doc["canon_writes"]!=0 or
            doc["receipt_sha256"]!=self._selection_hash({
                k:v for k,v in doc.items() if k!="receipt_sha256"})):
            raise StudioError("WF_STUDIO_BRANCH_CATALOG_TAMPERED")
        job_id=doc["job_id"]
        branches=doc["branches"]
        if (type(branches) is not dict or
            set(branches) not in ({"original"},{"original","revised"}) or
            doc["selected"] not in branches):
            raise StudioError("WF_STUDIO_BRANCH_CATALOG_OPTIONS")
        loaded={}
        for name,row in branches.items():
            allowed={"manifest","manifest_sha256",
                     "resume","resume_sha256"}
            if name=="revised":
                allowed|={"fork_receipt","fork_receipt_file_sha256"}
            if type(row) is not dict or set(row)!=allowed:
                raise StudioError("WF_STUDIO_BRANCH_ROW_SCHEMA")
            mf=self._branch_file(job_id,row["manifest"])
            if sha256(mf.read_bytes()).hexdigest()!=row["manifest_sha256"]:
                raise StudioError("WF_STUDIO_BRANCH_MANIFEST_STALE")
            item=json.loads(mf.read_text("utf8"))
            if (item.get("status")!="candidates_saved" or
                item.get("project_id")!=self.project or
                item.get("model_used")!=self.model or
                type(item.get("chapters")) is not list or
                len(item["chapters"])<1 or
                type(item.get("chapter_count")) is not int or
                len(item["chapters"])!=item["chapter_count"]):
                raise StudioError("WF_STUDIO_BRANCH_MANIFEST_SCHEMA")
            # The signed resume alone cannot prove on-disk prose hasn't
            # changed. Recheck EACH saved chapter's actual bytes against its
            # hot-buffer source pointer and its own V117 graph receipt.
            for chapter in item["chapters"]:
                if (type(chapter) is not dict or
                    chapter.get("accepted") is not False):
                    raise StudioError("WF_STUDIO_BRANCH_CHAPTER_ACCEPTANCE")
                cp=self._branch_relative(job_id,chapter.get("candidate"))
                actual_prose=self._branch_file(
                    job_id,cp,max_bytes=70_000).read_bytes()
                c_resume=self._branch_relative(
                    job_id,chapter.get("v117_unreviewed_text_trace_resume"))
                c_raw=json.loads(self._branch_file(
                    job_id,c_resume).read_text("utf8"))
                try:
                    read_resume(c_raw,project_id=self.project,
                                scene_id=self.scene)
                    c_graph=read_core_from_resume(
                        c_raw,project_id=self.project,scene_id=self.scene)
                except (ContinuityTraceError,NarrativeCoreError):
                    raise StudioError(
                        "WF_STUDIO_BRANCH_CHAPTER_SOURCE_TAMPERED") from None
                hot=(c_graph["memory"]["hot"] if c_graph is not None else [])
                if (not hot or hot[-1]["source_sha256"]!=sha256(
                        actual_prose).hexdigest() or
                    hot[-1]["chapter"]!=chapter.get("story_chapter_index") or
                    self._branch_relative(job_id,hot[-1]["source_path"])!=cp):
                    raise StudioError("WF_STUDIO_BRANCH_MANUSCRIPT_CHANGED")
            actual=self._branch_relative(
                job_id,item["chapters"][-1]["v117_unreviewed_text_trace_resume"])
            if actual!=row["resume"]:
                raise StudioError("WF_STUDIO_BRANCH_RESUME_NOT_IN_MANIFEST")
            rp=self._branch_file(job_id,row["resume"])
            resume=json.loads(rp.read_text("utf8"))
            try:
                read_resume(resume,project_id=self.project,scene_id=self.scene)
                core=read_core_from_resume(
                    resume,project_id=self.project,scene_id=self.scene)
                if core is None:
                    raise StudioError("WF_STUDIO_BRANCH_CORE_MISSING")
            except (ContinuityTraceError,NarrativeCoreError):
                raise StudioError("WF_STUDIO_BRANCH_V117_TAMPERED") from None
            if resume["receipt_sha256"]!=row["resume_sha256"]:
                raise StudioError("WF_STUDIO_BRANCH_HEAD_CHANGED")
            loaded[name]={"manifest":item,"resume":resume,
                          "resume_path":rp}
            if name=="revised":
                fpath=self._branch_file(job_id,row["fork_receipt"])
                if (sha256(fpath.read_bytes()).hexdigest()!=
                    row["fork_receipt_file_sha256"]):
                    raise StudioError("WF_STUDIO_FORK_SOURCE_CHANGED")
                receipt=json.loads(fpath.read_text("utf8"))
                _validate_unaccepted_fork_resume(
                    fork_receipt=receipt,candidate_resume=resume,
                    project_id=self.project,scene_id=self.scene)
                loaded[name]["fork_receipt"]=receipt
        if "revised" in loaded:
            receipt=loaded["revised"]["fork_receipt"]
            if receipt["old_head_resume_sha256"]!=loaded["original"][
                    "resume"]["receipt_sha256"]:
                raise StudioError("WF_STUDIO_FORK_WRONG_OLD_BRANCH")
        return loaded

    def _set_branch_catalog(self,catalog,*,persist=True):
        validated=self._validate_branch_catalog(catalog)
        name=catalog["selected"]
        source=validated[name]
        if persist:
            self.store._atomic(
                self.store.path/"unaccepted_branch_selection.json",
                json.dumps(catalog,ensure_ascii=False,indent=2))
        self._branch_catalog=catalog
        self._selected_fork_receipt=source.get("fork_receipt")
        self._last_unreviewed_resume=source["resume_path"]
        self._last_unreviewed_job_id=catalog["job_id"]
        self._selection_restore_warning=None
        return source["manifest"]

    def _restore_branch_catalog(self):
        path=self.store.path/"unaccepted_branch_selection.json"
        if not path.exists():
            return
        data=json.loads(path.read_text("utf8"))
        manifest=self._set_branch_catalog(data,persist=False)
        jobid=data["job_id"]
        result={**manifest,
                "job_dir":str(self._branch_file(
                    jobid,data["branches"][data["selected"]]["manifest"]).parent)}
        self._job_folder=self.output_dir/"autonomous"/jobid
        self._job={"id":jobid,"status":"completed","stage":"restored_candidate",
                   "result":result,"error":None,
                   "draft_mode":"continuity_guard",
                   "pending_turn":None,"cancel_requested":False,
                   "restored_from_signed_local_candidate":True}

    def select_branch(self,job_id:str,branch:str) -> dict:
        """Select historical or revised private candidate, never story Canon."""
        if not self._model_busy.acquire(blocking=False):
            raise StudioError("WF_STUDIO_WRITER_BUSY_CANNOT_SELECT_BRANCH")
        try:
            with self._job_lock:
                catalog=self._branch_catalog
                if (catalog is None or
                    catalog["job_id"]!=job_id or
                    branch not in catalog["branches"] or
                    (self._job and self._job.get("status") in (
                        "queued","running","awaiting_review","cancelling"))):
                    raise StudioError("WF_STUDIO_BRANCH_SELECTION_UNAVAILABLE")
                updated={**catalog,"selected":branch}
                updated["receipt_sha256"]=self._selection_hash({
                    k:v for k,v in updated.items() if k!="receipt_sha256"})
                manifest=self._set_branch_catalog(updated)
                if self._job and self._job.get("id")==job_id:
                    current=self._job.get("result")
                    # Branch selection restores exactly the original saved
                    # run manifest, not a fabricated new model response.
                    new_result={**manifest,
                        "job_dir":str(self._branch_file(
                            job_id,updated["branches"][branch][
                                "manifest"]).parent)}
                    if type(current) is dict:
                        new_result["wf_chapter_ai_review_decision"]=current.get(
                            "wf_chapter_ai_review_decision")
                    self._job["result"]=new_result
                return {"job_id":job_id,"selected_branch":branch,
                        "available_branches":list(updated["branches"]),
                        "author_accepted":False,"canon_writes":0,
                        "resume_sha256":updated["branches"][branch]["resume_sha256"]}
        finally:
            self._model_busy.release()

    def branch_summary(self):
        catalog=self._branch_catalog
        if catalog is None:
            return {"available":[],"selected":None,
                    "restore_warning":self._selection_restore_warning}
        return {"job_id":catalog["job_id"],
                "available":list(catalog["branches"]),
                "selected":catalog["selected"],
                "restore_warning":self._selection_restore_warning,
                "author_accepted":False,
                "selected_resume_sha256":catalog["branches"][
                    catalog["selected"]]["resume_sha256"]}

    def suggest(self,text:str) -> dict:
        if not self._model_busy.acquire(blocking=False):
            raise StudioError("本地模型正在生成，请稍候")
        try:
            with self._writer() as assistant:
                return assistant.suggest(text)
        finally:
            self._model_busy.release()

    def _progress(self,index,total,stage):
        with self._job_lock:
            if self._job is not None:
                self._job["chapter"]=index
                self._job["total"]=total
                self._job["stage"]=stage

    def start_auto(self,outline:str,chapters:list[str], *,
                   draft_mode:str="single",
                   pause_between_turns:bool|None=None,
                   continue_unreviewed:bool=False,
                   self_edit_rounds:int=0,
                   self_edit_timing:str="always_offer",
                   ai_chapter_review:bool=False) -> dict:
        # Author chooses A (single) or segmented B-F. For segmented Studio
        # work, default to SHOW EACH TURN and wait for explicit continuation.
        if draft_mode not in ("single","split_only","causal_guard",
                              "rolling_causal","emotion_rolling",
                              "foresight_rolling","continuity_guard"):
            raise StudioError("WF96_UNKNOWN_EXPERIMENTAL_DRAFT_MODE")
        if type(continue_unreviewed) is not bool or (
                continue_unreviewed and draft_mode!="continuity_guard"):
            raise StudioError("WFCORE_CONTINUATION_REQUIRES_G_MODE")
        if (type(self_edit_rounds) is not int or
            not 0<=self_edit_rounds<=2 or
            self_edit_rounds and draft_mode!="continuity_guard"):
            raise StudioError("WF_SELF_EDIT_REQUIRES_G_MODE_0_TO_2_ROUNDS")
        if (self_edit_timing not in ("always_offer","ai_decides") or
            self_edit_timing=="ai_decides" and (
                self_edit_rounds==0 or draft_mode!="continuity_guard")):
            raise StudioError(
                "WF_AI_WRITER_TIMING_REQUIRES_ACTIVE_G_SELF_EDIT")
        if type(ai_chapter_review) is not bool:
            raise StudioError("WF_STUDIO_CHAPTER_REVIEW_FLAG_INVALID")
        if (ai_chapter_review and
            (draft_mode!="continuity_guard" or
             not continue_unreviewed or
             self_edit_rounds==0 or
             self_edit_timing!="ai_decides" or
             type(chapters) is not list or len(chapters)!=2)):
            raise StudioError(
                "WF_STUDIO_AI_CHAPTER_REVIEW_NEEDS_G_TWO_CHAPTERS_SIGNED_PARENT")
        if pause_between_turns is not None and type(pause_between_turns) is not bool:
            raise StudioError("invalid staged-review option")
        # The self-editing writer works without repeated author sends.
        # Human reviews remain separately opt-in when self-edit is on.
        pause=(draft_mode!="single" and self_edit_rounds==0
               if pause_between_turns is None
               else pause_between_turns)
        if draft_mode=="single" and pause:
            raise StudioError("single-shot writing cannot pause between turns")
        if ai_chapter_review and pause:
            raise StudioError(
                "WF_STUDIO_AI_CHAPTER_REVIEW_CANNOT_REQUIRE_MANUAL_TURN_SEND")
        if draft_mode!="single" and (
            not isinstance(chapters,list) or len(chapters)>2):
            raise StudioError("WF96_SCENE_MODE_MAX_TWO_CHAPTERS_FOR_MODEL_BUDGET")
        if (not isinstance(outline,str) or not 15<=len(outline.strip())<=6000
            or not isinstance(chapters,list) or not 1<=len(chapters)<=6
            or any(not isinstance(c,str) or not 8<=len(c.strip())<=450
                   for c in chapters)):
            raise StudioError("please supply an outline and 1..6 chapter goals")
        if not self._model_busy.acquire(blocking=False):
            raise StudioError("the local model is already processing a request")

        jobid=secrets.token_hex(8)
        jobbase=self.output_dir/"autonomous"
        jobroot=jobbase/jobid
        cancel_event=Event()
        continue_event=Event()
        try:
            with self._job_lock:
                if self._job and self._job["status"] in (
                    "queued","running","awaiting_review","cancelling"):
                    raise StudioError("an autonomous writing run is already active")
                resume_candidate=None
                selected_fork_receipt=None
                if continue_unreviewed:
                    resume_path=self._last_unreviewed_resume
                    if (resume_path is None or
                        not resume_path.is_file() or
                        not self._last_unreviewed_job_id or
                        resume_path.is_symlink() or
                        self._last_unreviewed_job_id not in resume_path.parts):
                        raise StudioError(
                            "WFCORE_NO_VERIFIED_PREVIOUS_CANDIDATE_TO_CONTINUE")
                    # Stable byte snapshot; the downstream V117 reader will
                    # verify project/scene, source SHA and the unified graph
                    # BEFORE any model is charged.
                    resume_candidate=json.loads(resume_path.read_text("utf8"))
                    selected_fork_receipt=self._selected_fork_receipt
                    if selected_fork_receipt is not None:
                        _validate_unaccepted_fork_resume(
                            fork_receipt=selected_fork_receipt,
                            candidate_resume=resume_candidate,
                            project_id=self.project,scene_id=self.scene)
                jobroot.mkdir(parents=True,exist_ok=False)
                self._job_folder=jobroot
                self._cancel_event=cancel_event
                self._continue_event=continue_event
                self._job={
                    "id":jobid,"status":"queued","chapter":0,
                    "total":len(chapters),"stage":"queued",
                    "result":None,"error":None,"draft_mode":draft_mode,
                    "pause_between_turns":pause,
                    "continue_unreviewed":continue_unreviewed,
                    "self_edit_rounds":self_edit_rounds,
                    "self_edit_timing":self_edit_timing,
                    "ai_chapter_review":ai_chapter_review,
                    "pending_turn":None,
                    "cancel_requested":False,
                    "discarded":False,
                }
        except Exception:
            self._model_busy.release()
            raise

        def turn_review(chapter,turn,prose):
            with self._job_lock:
                if cancel_event.is_set():
                    return False
                continue_event.clear()
                self._job.update(
                    status="awaiting_review",stage="awaiting_review",
                    chapter=chapter,
                    pending_turn={
                        "chapter":chapter,"turn":turn,
                        "text":prose,"length":len(prose),
                        "provisional_not_accepted":True,
                    })
            # This is a human pause, not auto acceptance. No more provider
            # requests are made until the author clicks CONTINUE.
            while not cancel_event.is_set():
                if continue_event.wait(0.2):
                    with self._job_lock:
                        if cancel_event.is_set():
                            return False
                        continue_event.clear()
                        self._job.update(
                            status="running",stage="drafting",
                            pending_turn=None)
                    return True
            return False

        def worker():
            try:
                with self._job_lock:
                    if cancel_event.is_set():
                        raise WriterDraftCancelled("WF_STUDIO_DRAFT_CANCELLED")
                    self._job["status"]="running"
                with self._writer() as assistant:
                    result=AutonomousWriting(assistant).run(
                        outline=outline,chapter_goals=chapters,
                        output_dir=jobroot,
                        progress=self._progress,
                        draft_mode=draft_mode,
                        cancel_requested=cancel_event.is_set,
                        review_turn=(turn_review if pause else None),
                        bootstrap_unified_core=(
                            draft_mode=="continuity_guard" and
                            not continue_unreviewed),
                        resume_story_checkpoint=resume_candidate,
                        selected_fork_receipt=selected_fork_receipt,
                        self_edit_rounds=self_edit_rounds,
                        self_edit_timing=self_edit_timing,
                    )
                    candidate_branches={"original":result}
                    selected_candidate="original"
                    if ai_chapter_review:
                        with self._job_lock:
                            self._job["stage"]="ai_decides_cross_chapter"
                        def check_author_stop():
                            if cancel_event.is_set():
                                raise WriterDraftCancelled(
                                    "WF_STUDIO_DRAFT_CANCELLED")
                        try:
                            moment=_ai_decides_cross_chapter(
                                assist=assistant,outline=outline,
                                chapter_goals=chapters,
                                original_result=result,
                                parent_resume=resume_candidate,
                                directory=jobroot,
                                cancel_check=check_author_stop)
                        except WriterDraftCancelled:
                            raise
                        except Exception as exc:
                            # The real initial story is already a valid
                            # private candidate. Failure to ask for a chapter
                            # decision must not discard it or invent a rewrite.
                            moment={
                                "decision":"CHAPTER_REVIEW_FAILED",
                                "model_calls":0,
                                "receipt":{
                                    "status":"CHAPTER_REVIEW_FAILED",
                                    "failure_code":str(exc)[:160],
                                    "literary_quality_verified":False,
                                    "canon_writes":0}}
                        result["wf_chapter_ai_review_decision"]=moment["decision"]
                        result["wf_chapter_ai_moment_calls"]=moment["model_calls"]
                        result["wf_chapter_ai_review_receipt"]=moment["receipt"]
                        result["wf_chapter_ai_literary_quality_verified"]=False
                        if moment["decision"]=="LOOK_BACK_NOW":
                            old_end=json.loads(Path(
                                result["chapters"][-1][
                                    "v117_unreviewed_text_trace_resume"]
                            ).read_text("utf8"))
                            proposal={
                                "source_job_dir":result["job_dir"],
                                "writer_decision_reply":moment["raw_reply"],
                                "expected_old_head_sha256":
                                    old_end["receipt_sha256"],
                            }
                            with self._job_lock:
                                self._job["stage"]="rewriting_ai_chosen_chapters"
                            try:
                                alternate=AutonomousWriting(assistant).run(
                                    outline=outline,chapter_goals=chapters,
                                    output_dir=jobroot/"revised",
                                    progress=self._progress,
                                    draft_mode=draft_mode,
                                    cancel_requested=cancel_event.is_set,
                                    review_turn=None,
                                    bootstrap_unified_core=False,
                                    resume_story_checkpoint=resume_candidate,
                                    selected_fork_receipt=selected_fork_receipt,
                                    cross_chapter_fork=proposal,
                                    self_edit_rounds=self_edit_rounds,
                                    self_edit_timing=self_edit_timing)
                                check_author_stop()
                            except WriterDraftCancelled:
                                raise
                            except Exception as error:
                                result["wf_chapter_ai_review_decision"]=(
                                    "LOOK_BACK_REBUILD_FAILED_ORIGINAL_RETAINED")
                                result["wf_chapter_ai_rebuild_failure"]=(
                                    str(error)[:160])
                                (jobroot/"ai-chapter-rebuild-rejected.json").write_text(
                                    json.dumps({
                                        "format":"wf.studio.chapter-rebuild-failed.v1",
                                        "original_job_dir":result["job_dir"],
                                        "failure_code":str(error)[:160],
                                        "old_candidate_unchanged":True,
                                        "literary_quality_verified":False,
                                        "canon_writes":0,
                                    },ensure_ascii=False,indent=2),
                                    encoding="utf8")
                            else:
                                candidate_branches["revised"]=alternate
                                selected_candidate="revised"
                                alternate["wf_chapter_ai_review_decision"]=(
                                    "LOOK_BACK_REBUILT_PROVISIONAL")
                                alternate["wf_chapter_ai_moment_calls"]=(
                                    moment["model_calls"])
                                alternate["wf_chapter_ai_review_receipt"]=(
                                    moment["receipt"])
                                alternate["wf_chapter_ai_literary_quality_verified"]=False
                                result=alternate
                if cancel_event.is_set():
                    raise WriterDraftCancelled("WF_STUDIO_DRAFT_CANCELLED")
                with self._job_lock:
                    if draft_mode=="continuity_guard":
                        chapters_out=result.get("chapters") or []
                        candidate_path=(chapters_out[-1].get(
                            "v117_unreviewed_text_trace_resume")
                            if chapters_out else None)
                        if not candidate_path or not Path(candidate_path).is_file():
                            raise StudioError(
                                "WFCORE_STAGED_WRITER_MISSING_UNIFIED_RESUME")
                        # A real G result has its signed local job manifest.
                        # Save this as existing Studio selection metadata;
                        # historical fake tests lacking a job manifest keep
                        # the prior in-session resume behavior only.
                        if (type(result.get("job_dir")) is str and
                            Path(result["job_dir"],"job_manifest.json").is_file()):
                            catalog=self._build_branch_catalog(
                                job_id=jobid,
                                branch_results=candidate_branches,
                                selected=selected_candidate)
                            self._set_branch_catalog(catalog)
                        else:
                            self._last_unreviewed_resume=Path(candidate_path)
                            self._last_unreviewed_job_id=jobid
                            self._selected_fork_receipt=None
                    self._job.update(status="completed",result=result,
                                     pending_turn=None,stage="saved")
            except WriterDraftCancelled:
                try:
                    _delete_only_job_folder(jobroot,jobbase,jobid)
                except (OSError,StudioError):
                    with self._job_lock:
                        self._job.update(
                            status="cancel_cleanup_failed",
                            error="本次生成已停止，但私有候选目录清理失败，请手动检查",
                            pending_turn=None)
                else:
                    with self._job_lock:
                        self._job.update(
                            status="cancelled",result=None,
                            error=None,discarded=True,
                            stage="cancelled",pending_turn=None)
            except Exception as exc:
                if cancel_event.is_set():
                    try:
                        _delete_only_job_folder(jobroot,jobbase,jobid)
                    except (OSError,StudioError):
                        with self._job_lock:
                            self._job.update(
                                status="cancel_cleanup_failed",
                                error="停止后清理失败，原手稿未变更",
                                pending_turn=None)
                    else:
                        with self._job_lock:
                            self._job.update(
                                status="cancelled",result=None,
                                error=None,discarded=True,
                                stage="cancelled",pending_turn=None)
                else:
                    with self._job_lock:
                        self._job.update(
                            status="failed",error=str(exc)[:500],
                            pending_turn=None)
            finally:
                self._model_busy.release()
        Thread(target=worker,daemon=True).start()
        return {"job_id":jobid,"status":"queued",
                "draft_mode":draft_mode,
                "pause_between_turns":pause,
                "self_edit_rounds":self_edit_rounds,
                "self_edit_timing":self_edit_timing,
                "self_edit_provider_call_cap":(
                    8 if self_edit_rounds else 0),
                "ai_chapter_review":ai_chapter_review,
                "chapter_review_model_call_cap":(1 if ai_chapter_review else 0),
                "chapter_fork_redraft_cap":(1 if ai_chapter_review else 0),
                "no_auto_accept":True,"can_request_discard":True}

    def cancel_auto(self,job_id:str) -> dict:
        """Author explicitly stops and discards the CURRENT draft job."""
        with self._job_lock:
            if (not self._job or self._job["id"]!=job_id or
                self._job["status"] not in (
                    "queued","running","awaiting_review","cancelling")):
                raise StudioError("draft job is not active")
            if self._job["status"]!="cancelling":
                self._cancel_event.set()
                self._continue_event.set()
                self._job.update(
                    status="cancelling",stage="cancelling",
                    cancel_requested=True,pending_turn=None)
            return {"job_id":job_id,"status":"cancelling",
                    "discard_after_current_model_call":True,
                    "already_saved_manuscript_unchanged":True}

    def continue_auto(self,job_id:str,chapter:int,turn:int) -> dict:
        """Approve ONLY continuing draft generation, never story Canon."""
        with self._job_lock:
            current=self._job
            if (not current or current.get("id")!=job_id or
                current.get("status")!="awaiting_review" or
                current.get("cancel_requested") or
                type(chapter) is not int or type(turn) is not int or
                not current.get("pending_turn") or
                current["pending_turn"]["chapter"]!=chapter or
                current["pending_turn"]["turn"]!=turn):
                raise StudioError("stale or unavailable staged writing choice")
            self._continue_event.set()
            return {"job_id":job_id,"status":"continuing",
                    "author_accepted_prose":False,
                    "canon_writes":0}

    def discard_auto(self,job_id:str) -> dict:
        """Explicitly discard a finished/failed run's own candidates only."""
        with self._job_lock:
            if (not self._job or self._job["id"]!=job_id or
                self._job["status"] not in (
                    "completed","failed","cancelled","cancel_cleanup_failed")):
                raise StudioError("cannot delete an active or unrelated job")
            _delete_only_job_folder(
                self._job_folder,
                self.output_dir/"autonomous",
                job_id)
            if self._last_unreviewed_job_id==job_id:
                self._last_unreviewed_resume=None
                self._last_unreviewed_job_id=None
                self._selected_fork_receipt=None
                if (self._branch_catalog is not None and
                    self._branch_catalog["job_id"]==job_id):
                    self._branch_catalog=None
                    (self.store.path/"unaccepted_branch_selection.json"
                     ).unlink(missing_ok=True)
            self._job.update(
                status="discarded",result=None,error=None,
                pending_turn=None,discarded=True,stage="discarded")
            return {"job_id":job_id,"status":"discarded",
                    "author_manuscript_unchanged":True,
                    "canonical_story_not_deleted":True}

    def job(self) -> dict:
        with self._job_lock:
            state=dict(self._job) if self._job else {"status":"idle"}
            state["unreviewed_resume_available"]=bool(
                self._last_unreviewed_resume is not None and
                self._last_unreviewed_resume.is_file())
            state["candidate_branches"]=self.branch_summary()
            return state

    def bootstrap(self) -> dict:
        return {
            "token":self._token,"project":self.project,"scene":self.scene,
            "goal":self.goal,"model":self.model,
            "draft":self.store.load(),
            "auto_job":self.job(),
            "unreviewed_resume_available":self.job()[
                "unreviewed_resume_available"],
            "candidate_branches":self.branch_summary(),
            "status":"studio_connected_to_published_xuehai",
            "external_litcritic_not_automatically_run":True,
            "unverified_facets_not_treated_as_verified":True,
        }


class StudioHTTPServer(ThreadingHTTPServer):
    daemon_threads=True
    request_queue_size=16

    def __init__(self,host:str,port:int,service:StudioService):
        if host not in ("127.0.0.1","localhost"):
            raise StudioError("Studio must bind only to local loopback")
        self.service=service
        super().__init__((host,port),StudioHandler)


class StudioHandler(BaseHTTPRequestHandler):
    server:StudioHTTPServer

    def log_message(self,format,*args):
        # Do not accidentally log author draft content or project prompts.
        pass

    def _json(self,status:int,data:dict):
        raw=json.dumps(data,ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(raw)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.end_headers()
        self.wfile.write(raw)

    def _localhost(self) -> bool:
        host=self.headers.get("Host","")
        port=self.server.server_address[1]
        return host in (f"127.0.0.1:{port}",f"localhost:{port}")

    def _authorized(self) -> bool:
        if not self._localhost():
            return False
        origin=self.headers.get("Origin")
        if origin and origin not in (
            f"http://127.0.0.1:{self.server.server_address[1]}",
            f"http://localhost:{self.server.server_address[1]}",
        ):
            return False
        return secrets.compare_digest(
            self.headers.get("X-WriterForge-Token",""),
            self.server.service._token,
        )

    def do_GET(self):
        if not self._localhost():
            self._json(403,{"error":"invalid host"})
            return
        if self.path=="/api/bootstrap":
            self._json(200,self.server.service.bootstrap())
            return
        if self.path=="/api/job":
            if not self._authorized():
                self._json(403,{"error":"invalid local request token"})
                return
            self._json(200,self.server.service.job())
            return
        if self.path.startswith("/api/chapter/"):
            if not self._authorized():
                self._json(403,{"error":"invalid local request token"})
                return
            number=self.path[len("/api/chapter/"):]
            if not number.isdecimal() or not 1<=int(number)<=6:
                self._json(400,{"error":"invalid chapter index"})
                return
            job=self.server.service.job()
            if job.get("status")!="completed" or not job.get("result"):
                self._json(409,{"error":"autonomous writing has not completed"})
                return
            index=int(number)-1
            chapters=job["result"].get("chapters",[])
            if index>=len(chapters):
                self._json(404,{"error":"requested chapter does not exist"})
                return
            try:
                draft=Path(chapters[index]["candidate"]).read_text(encoding="utf-8")
                if len(draft)>16000:
                    raise StudioError("chapter exceeds safe preview size")
                self._json(200,{"chapter":index+1,"text":draft,
                                "accepted":False,"source":"actual_local_model_candidate"})
            except (OSError,StudioError):
                self._json(503,{"error":"saved candidate cannot be read"})
            return
        if self.path=="/":
            html=resources.files("writerforge").joinpath("ui/studio.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length",str(len(html)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
                "connect-src 'self'; base-uri 'none'; form-action 'none'",
            )
            self.end_headers()
            self.wfile.write(html)
            return
        self._json(404,{"error":"not found"})

    def do_POST(self):
        if not self._authorized():
            self._json(403,{"error":"invalid local request"})
            return
        try:
            n=int(self.headers.get("Content-Length","-1"))
        except ValueError:
            n=-1
        if not 0<=n<=MAX_REQUEST_BYTES:
            self._json(413,{"error":"request exceeds size limit"})
            return
        if self.headers.get("Content-Type","").split(";")[0]!="application/json":
            self._json(415,{"error":"JSON required"})
            return
        try:
            payload=json.loads(self.rfile.read(n).decode("utf-8"))
            if not isinstance(payload,dict):
                raise StudioError("JSON must be an object")
            svc=self.server.service
            if self.path=="/api/autosave":
                result=svc.store.save(payload.get("text"),
                                      payload.get("expected_revision"))
            elif self.path=="/api/suggest":
                result=svc.suggest(payload.get("text"))
            elif self.path=="/api/choice":
                result=svc.store.choice(
                    choice_index=payload.get("choice_index"),
                    prompt_sha256=payload.get("prompt_sha256"),
                )
            elif self.path=="/api/autodraft":
                result=svc.start_auto(
                    payload.get("outline"),payload.get("chapters"),
                    draft_mode=payload.get("draft_mode","single"),
                    pause_between_turns=payload.get("pause_between_turns"),
                    continue_unreviewed=payload.get(
                        "continue_unreviewed",False),
                    self_edit_rounds=payload.get(
                        "self_edit_rounds",0),
                    self_edit_timing=payload.get(
                        "self_edit_timing","always_offer"),
                    ai_chapter_review=payload.get(
                        "ai_chapter_review",False),
                )
            elif self.path=="/api/autodraft/cancel":
                result=svc.cancel_auto(payload.get("job_id"))
            elif self.path=="/api/autodraft/continue":
                result=svc.continue_auto(
                    payload.get("job_id"),payload.get("chapter"),
                    payload.get("turn"))
            elif self.path=="/api/autodraft/discard":
                result=svc.discard_auto(payload.get("job_id"))
            elif self.path=="/api/autodraft/branch/select":
                result=svc.select_branch(
                    payload.get("job_id"),payload.get("branch"))
            else:
                self._json(404,{"error":"unknown command"})
                return
            self._json(200,result)
        except RevisionConflict as exc:
            self._json(409,{"error":str(exc)})
        except (StudioError,WritingExecutionError,ValueError,KeyError,TypeError) as exc:
            self._json(400,{"error":str(exc)[:500]})
        except Exception:
            # Model / network errors should never expose credentials or traces
            # to the browser. Full error is not logged alongside author prose.
            self._json(503,{"error":"本地模型或学习数据库暂时不可用，请检查本地服务"})


def serve(*,db_path:str|Path,project:str,scene:str,goal:str,
          model:str,api_base:str="http://127.0.0.1:1234/v1",
          port:int=8765,output_dir:str|Path="writing_runs/studio"):
    if not isinstance(port,int) or not 1024<=port<=65535:
        raise StudioError("port must be 1024..65535")
    svc=StudioService(
        db_path=db_path,project=project,scene=scene,goal=goal,
        model=model,api_base=api_base,output_dir=output_dir,
    )
    server=StudioHTTPServer("127.0.0.1",port,svc)
    print(f"WriterForge Studio: http://127.0.0.1:{port}/")
    print("Local only; auto-save on; private draft is not automatically accepted.")
    try:
        server.serve_forever(poll_interval=0.35)
    finally:
        server.server_close()
