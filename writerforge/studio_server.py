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
from threading import Lock, Semaphore, Thread
import json
import os
import secrets
import time
from urllib.parse import urlsplit

from .db import WriterForgeDB
from .runtime import RuntimeEngine
from .writing_assist import InvisibleWritingAssist, AutonomousWriting
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
        self._token=secrets.token_urlsafe(30)
        # Verify a REAL published snapshot on startup (not a fake mode flag).
        with self._writer() as assistant:
            _=assistant.flow.begin_draft(scene)

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

    def start_auto(self,outline:str,chapters:list[str]) -> dict:
        # Validate BEFORE queueing. No unlimited jobs or unbounded prompts.
        if (not isinstance(outline,str) or not 15<=len(outline.strip())<=6000
            or not isinstance(chapters,list) or not 1<=len(chapters)<=6
            or any(not isinstance(c,str) or not 8<=len(c.strip())<=450
                   for c in chapters)):
            raise StudioError("please supply an outline and 1..6 chapter goals")
        if not self._model_busy.acquire(blocking=False):
            raise StudioError("the local model is already processing a request")
        with self._job_lock:
            if self._job and self._job["status"] in ("queued","running"):
                self._model_busy.release()
                raise StudioError("an autonomous writing run is already active")
            jobid=secrets.token_hex(8)
            self._job={"id":jobid,"status":"queued","chapter":0,
                       "total":len(chapters),"stage":"queued","result":None,"error":None}
        def worker():
            try:
                with self._job_lock:
                    self._job["status"]="running"
                with self._writer() as assistant:
                    result=AutonomousWriting(assistant).run(
                        outline=outline,chapter_goals=chapters,
                        output_dir=self.output_dir/"autonomous",
                        progress=self._progress,
                    )
                with self._job_lock:
                    self._job["status"]="completed"
                    self._job["result"]=result
            except Exception as exc:
                with self._job_lock:
                    self._job["status"]="failed"
                    self._job["error"]=str(exc)[:500]
            finally:
                self._model_busy.release()
        Thread(target=worker,daemon=True).start()
        return {"job_id":jobid,"status":"queued","no_auto_accept":True}

    def job(self) -> dict:
        with self._job_lock:
            return dict(self._job) if self._job else {"status":"idle"}

    def bootstrap(self) -> dict:
        return {
            "token":self._token,"project":self.project,"scene":self.scene,
            "goal":self.goal,"model":self.model,
            "draft":self.store.load(),
            "auto_job":self.job(),
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
                    payload.get("outline"),payload.get("chapters")
                )
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
