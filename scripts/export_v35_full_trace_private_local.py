"""Explicit local-only PRIVATE export of the exact V35 Xi You Ji evidence.

Requires the user's own Cloudflare R2 access configured in the environment.
Never runs in public GitHub Actions; never writes full study observations,
prose, prewriting rationales or the original excerpts to stdout/logs/repo.
Creates a new owner-only (0700) local folder atomically. Nothing is uploaded.
"""
from __future__ import annotations
import argparse,json,os,sys,tempfile
from pathlib import Path

from writerforge.r2_storage import R2Config,R2StudyVault
from writerforge.v35_observable_trace import sha,canonical
from scripts.run_v35_xiyouji_decision_trace import restore_stage
from scripts.debug_v36_xiyouji_learning_to_writing import (
    EXPECTED_ORIGINAL_SHA,AFTER_SHA,AFTER_EXAMINER_SHA,_after_key,
    _read_exact,analyze,
)

class PrivateExportError(ValueError):
    pass

def _json_text(obj)->str:
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+"\n"

def _write_secure(path:Path,text:str)->None:
    fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as f:f.write(text)

def export_private(vault,*,output:Path)->dict:
    if vault.config.bucket!="writerforge-private-library":
        raise PrivateExportError("PRIVATE_R2_ONLY")
    if os.environ.get("GITHUB_ACTIONS","").lower()=="true":
        raise PrivateExportError("NEVER_EXPORT_PRIVATE_PROSE_IN_PUBLIC_CI")
    output=Path(output).expanduser().resolve()
    if output.exists():
        raise PrivateExportError("EXPORT_DIRECTORY_ALREADY_EXISTS")
    if not output.parent.is_dir():
        raise PrivateExportError("PARENT_DIRECTORY_DOES_NOT_EXIST")
    oldmask=os.umask(0o077)
    try:
        # Verify all model-output and stage hashes BEFORE allocating files.
        original=[]
        parent=None
        for i,h in enumerate(EXPECTED_ORIGINAL_SHA):
            result=restore_stage(vault,i,parent)
            if result is None or result[1]!=h:
                raise PrivateExportError("HISTORICAL_EVIDENCE_SHA_MISMATCH")
            original.append(result[0])
            parent=h
        validated=_read_exact(vault,_after_key("valid-retrospective",AFTER_SHA),
                              AFTER_SHA,36000)
        examiner=_read_exact(vault,_after_key("append-only-examiner-audit",
                                              AFTER_EXAMINER_SHA),
                              AFTER_EXAMINER_SHA,36000)
        diagnostic=analyze(vault,persist=False)
        first=original[4]["payload"]["body"]
        corrected=original[5]["payload"]
        last=(corrected["edited_draft"]["body"] if corrected["edited"] else first)
        files={
            "00_原著阅读窗口.json":_json_text(original[0]["payload"]),
            "01_实际阅读观察.json":_json_text(original[1]["payload"]),
            "02_文学手法候选.json":_json_text(original[2]["payload"]),
            "03_写前决策_已锁定.json":_json_text(original[3]["payload"]),
            "04_原始第一稿.txt":first,
            "05_最终修订稿.txt":last,
            "05_修订溯源.json":_json_text({
                k:v for k,v in corrected.items() if k!="edited_draft"}),
            "06_写后复盘_追加独立版本.json":_json_text(validated),
            "07_考官机器核验.json":_json_text(examiner),
            "08_逐角度证据对照.json":_json_text(diagnostic),
            "README_私有资料.txt":(
                "WriterForge V35《西游记》真实局部原著学习与一篇原创小说记录。\n"
                "仅在本地、私有位置浏览，切勿放入公开GitHub仓库。\n"
                "00为实际阅读的第1/2回各2000字符，不是读完全部100回。\n"
                "01/02是WF明确输出的观察与技巧假说，03是写作前锁定的决策，"
                "04原始稿与05修订稿互不覆盖。\n"
                "06是第二次追加的写后复盘；首次写后复盘曾因虚假正文引用"
                "校验失败，不能称原始V35一次全成功。\n"
                "07/08验证来源引用、内容哈希和各角度覆盖度，"
                "不等于文学审稿或模型隐藏思考记录。\n"
            ),
        }
        with tempfile.TemporaryDirectory(prefix=".wf-private-export-",
                                         dir=str(output.parent)) as tmp:
            stage=Path(tmp)/"dossier"
            stage.mkdir(mode=0o700)
            for name,text in files.items():
                _write_secure(stage/name,text)
            stage.rename(output)
        return {
            "status":"LOCAL_PRIVATE_READING_DOSSIER_CREATED",
            "new_local_files":len(files),
            "target_folder":str(output),
            "zero_model_calls":True,
            "prose_printed_to_logs":False,
            "source_and_draft_not_uploaded":True,
        }
    finally:
        os.umask(oldmask)

if __name__=="__main__":
    cli=argparse.ArgumentParser(description="Export PRIVATE V35 proof to a local-only folder")
    cli.add_argument("--output",required=True,
        help="new non-existing LOCAL private output directory, NOT inside public repo")
    options=cli.parse_args()
    try:
        result=export_private(R2StudyVault(R2Config.from_environment()),
                              output=Path(options.output))
        print(json.dumps(result,ensure_ascii=False))
    except Exception as e:
        code=str(e) if isinstance(e,PrivateExportError) else type(e).__name__
        print(json.dumps({"status":"EXPORT_REFUSED",
                          "safe_failure":code},ensure_ascii=False),file=sys.stderr)
        raise SystemExit(1)
