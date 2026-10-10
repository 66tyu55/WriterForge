"""WriterForge V23: executable original study, grounded drafting, review and audit."""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from .db import WriterForgeDB
from .runtime import RuntimeEngine
from .source_study import OriginalStudy, download_original, WORK_ID, SOURCE_PAGE, MAX_DOWNLOAD_BYTES
from .verified_flow import VerifiedWritingFlow, local_chat_completion, save_candidate, accept_candidate
from .litcritic_adapter import LitCriticAdapter
from .study_storage import restore_from_github, REPO_DEFAULT
from .r2_storage import R2Config, R2StudyVault


def _load_text(path: Path) -> str:
    if path.is_dir():
        files = sorted(path.glob("*.txt"))
        if not files or len(files)>100:
            raise ValueError("source directory must contain 1..100 numbered Chinese chapters")
        chunks=[]
        total=0
        for file in files:
            if not file.name[:3].isdigit():
                raise ValueError(f"expected ### chapter filenames, got {file.name}")
            raw=file.read_bytes()
            total+=len(raw)
            if total>MAX_DOWNLOAD_BYTES:
                raise ValueError("source directory exceeds 8 MiB")
            chunks.append(raw.decode("utf-8-sig"))
        return "\n\n".join(chunks)
    if not path.is_file() or path.stat().st_size>MAX_DOWNLOAD_BYTES:
        raise ValueError("local original source is missing or oversized")
    return path.read_text(encoding="utf-8-sig")


def _emit(data) -> None:
    print(json.dumps(data,ensure_ascii=False,indent=2))


def main(argv: list[str] | None = None):
    p=argparse.ArgumentParser(prog="writerforge")
    p.add_argument("--db",default="writerforge.sqlite3",
                   help="local SQLite store; not committed to Git")
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("init")
    f=sub.add_parser("fetch-xiyouji",help="download original Chinese Project Gutenberg #23962")
    f.add_argument("--output",default="corpus/xiyouji_23962_original.txt")
    learn=sub.add_parser("learn",help="transactional sequential original-text study")
    learn.add_argument("--source",required=True,help="100-chapter UTF-8 source file or numbered chapter directory")
    learn.add_argument("--work-id",default=WORK_ID)
    learn.add_argument("--source-uri",default=SOURCE_PAGE)
    learn.add_argument("--limit-chapters",type=int)
    learn.add_argument("--allow-partial",action="store_true",
                       help="for an authenticated sample, not a complete original book")
    learn.add_argument("--backup-r2",action="store_true",
                       help="back up after completed learning to your private R2 bucket")
    status=sub.add_parser("status")
    status.add_argument("--work-id",default=WORK_ID)
    context=sub.add_parser("draft-context")
    context.add_argument("--project",required=True)
    context.add_argument("--scene",required=True)
    context.add_argument("--goal",required=True)
    context.add_argument("--concerns",default="",help="comma-separated dialogue,description,action,...")
    context.add_argument("--output",default="draft_context.json")
    draft=sub.add_parser("draft")
    draft.add_argument("--project",required=True)
    draft.add_argument("--scene",required=True)
    draft.add_argument("--goal",required=True)
    draft.add_argument("--concerns",default="")
    draft.add_argument("--model",required=True,help="model currently loaded in LM Studio")
    draft.add_argument("--api-base",default="http://127.0.0.1:1234/v1")
    draft.add_argument("--output-dir",default="writing_runs")
    accept=sub.add_parser("accept")
    accept.add_argument("--project",required=True)
    accept.add_argument("--manifest",required=True)
    accept.add_argument("--commit-id",required=True)
    accept.add_argument("--confirm-accept",action="store_true",
                        help="explicit author approval is mandatory")
    review=sub.add_parser("review")
    review.add_argument("--project-path",required=True)
    review.add_argument("--scene",required=True)
    review.add_argument("--output-dir",default="reviews")
    review.add_argument("--mode",default="quick",choices=["quick","deep"])
    review.add_argument("--api-base",default="http://127.0.0.1:8000/api")
    restore=sub.add_parser("restore-xiyouji",help="automatically restore durable GitHub Release study into local SQLite")
    restore.add_argument("--repo",default=REPO_DEFAULT)
    restore.add_argument("--tag",help="optional versioned study Release tag; defaults to latest study")
    restore.add_argument("--storage-dir",default="corpus/library",help="verified, content-addressed local study directory")
    backup=sub.add_parser("backup-r2",help="back up live WriterForge SQLite with an online consistent R2 snapshot")
    backup.add_argument("--library",default="writerforge-personal")
    backup.add_argument("--source",help="optional owned/licensed original text to include privately")
    backup.add_argument("--edition",help="optional reproducible public-domain training edition ID (CI only)")
    backup.add_argument("--extra",action="append",default=[],metavar="NAME=PATH",
                        help="optional training report, source license or evidence file")
    restore_r2=sub.add_parser("restore-r2",help="restore a verified private R2 study snapshot")
    restore_r2.add_argument("--library",default="writerforge-personal")
    restore_r2.add_argument("--snapshot",help="specific 64-char SHA256 version; defaults to latest")
    restore_r2.add_argument("--storage-dir",default="corpus/r2-library")
    args=p.parse_args(argv)
    if args.cmd=="fetch-xiyouji":
        dest=download_original(args.output)
        _emit({"fetched":str(dest),"bytes":dest.stat().st_size,
               "source":SOURCE_PAGE,"language":"original Chinese (not translation)"})
        return
    if args.cmd=="restore-xiyouji":
        result=restore_from_github(
            repo=args.repo, storage_dir=args.storage_dir,tag=args.tag,
            token=os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"),
        )
        # Convenience: create the requested working DB ONLY when absent.
        # Never replace an author's existing accepted prose, preferences or
        # partially-trained local Xuehai with an imported snapshot.
        target=Path(args.db)
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            temp=target.with_name(target.name+".restore-partial")
            try:
                with Path(result["db"]).open("rb") as inp, temp.open("xb") as out:
                    shutil.copyfileobj(inp,out,length=1024*1024)
                os.replace(temp,target)
            finally:
                temp.unlink(missing_ok=True)
            result["working_db"]=str(target)
            result["working_db_created"]=True
        else:
            result["working_db"]=str(target)
            result["working_db_created"]=False
            result["note"]="existing project DB preserved; use --db with restored path if desired"
        _emit(result)
        return
    if args.cmd=="backup-r2":
        extras={}
        for value in args.extra:
            if "=" not in value:
                raise ValueError("--extra must be NAME=PATH")
            name,filename=value.split("=",1)
            if name in extras:
                raise ValueError("duplicate --extra name")
            extras[name]=filename
        vault=R2StudyVault(R2Config.from_environment())
        _emit(vault.backup(database=args.db,library=args.library,
                           source=args.source,extras=extras,edition=args.edition))
        return
    if args.cmd=="restore-r2":
        vault=R2StudyVault(R2Config.from_environment())
        result=vault.restore(library=args.library,destination=args.storage_dir,
                             snapshot=args.snapshot)
        # No clobber: only initialize the caller's working DB if it is absent.
        target=Path(args.db)
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            partial=target.with_name(target.name+".restore-partial")
            try:
                with Path(result["db"]).open("rb") as src,partial.open("xb") as dst:
                    shutil.copyfileobj(src,dst,length=1024*1024)
                os.replace(partial,target)
            finally:
                partial.unlink(missing_ok=True)
            result["working_db_created"]=True
        else:
            result["working_db_created"]=False
        result["working_db"]=str(target)
        _emit(result)
        return
    if args.cmd=="review":
        _emit(LitCriticAdapter(base_url=args.api_base).review(
            project_path=args.project_path,scene_path=args.scene,
            output_dir=args.output_dir,mode=args.mode,
        ))
        return
    db=WriterForgeDB(Path(args.db))
    try:
        if args.cmd=="init":
            _emit({"ok":True,"db":str(args.db)})
        elif args.cmd=="learn":
            rt=RuntimeEngine()
            rt.enter_learn()
            out=OriginalStudy(db,rt).ingest(
                _load_text(Path(args.source)),work_id=args.work_id,
                source_uri=args.source_uri,max_chapters=args.limit_chapters,
                require_hundred=not args.allow_partial,
            )
            if args.backup_r2 or (out.get("newly_studied",0)>0 and os.environ.get("WRITERFORGE_R2_AUTO_BACKUP")=="1"):
                library=os.environ.get("WRITERFORGE_R2_LIBRARY","writerforge-personal")
                source_file=args.source if Path(args.source).is_file() else None
                out["private_r2_backup"]=R2StudyVault(R2Config.from_environment()).backup(
                    database=args.db, library=library,source=source_file,
                )
            _emit(out)
        elif args.cmd=="status":
            snap=db.conn.execute(
                "SELECT id FROM snapshots WHERE status='published' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            _emit({"db":str(args.db),"latest_published_snapshot":snap["id"] if snap else None,
                   **OriginalStudy(db,RuntimeEngine()).status(args.work_id)})
        elif args.cmd in ("draft-context","draft"):
            row=db.conn.execute(
                "SELECT id FROM snapshots WHERE status='published' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row is None:
                raise ValueError("run learn and publish a real source snapshot first")
            rt=RuntimeEngine()
            rt.enter_write(int(row["id"]))
            flow=VerifiedWritingFlow(db,rt,args.project)
            concerns=tuple(x.strip() for x in args.concerns.split(",") if x.strip())
            packet=flow.prepare(args.scene,args.goal,concerns=concerns)
            if args.cmd=="draft-context":
                # Preview only: does NOT claim a model was called or produce prose.
                dest=Path(args.output)
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_text(json.dumps({
                    **packet.manifest(),"prompt":packet.prompt
                },ensure_ascii=False,indent=2),encoding="utf-8")
                _emit({"packet_path":str(dest),"verified_source_refs":len(packet.evidence),
                       "prose_generated":False})
            else:
                body=local_chat_completion(packet,model=args.model,api_base=args.api_base)
                _emit(save_candidate(packet,body,args.model,args.output_dir))
        elif args.cmd=="accept":
            meta=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
            rt=RuntimeEngine()
            sid=meta.get("snapshot_id")
            if not isinstance(sid,int) or sid<=0:
                raise ValueError("missing real source snapshot ID")
            rt.enter_write(sid)
            out=accept_candidate(
                db,rt,project_id=args.project,manifest_path=args.manifest,
                commit_id=args.commit_id,explicitly_approved=args.confirm_accept,
            )
            if out["accepted"] and not out.get("replayed") and os.environ.get("WRITERFORGE_R2_BACKUP_ON_ACCEPT")=="1":
                library=os.environ.get("WRITERFORGE_R2_LIBRARY","writerforge-personal")
                out["private_r2_backup"]=R2StudyVault(R2Config.from_environment()).backup(
                    database=args.db,library=library,
                )
            _emit(out)
    finally:
        db.close()


if __name__=="__main__":
    main()
