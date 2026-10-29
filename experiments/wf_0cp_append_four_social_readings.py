"""0.CP four new pinned classics appended through EXISTING Xuehai/R2.

Everything before the 136-entry snapshot remains immutable. The only new
remote object is a separate successor R2 library; no model or Canon writes.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from shutil import copyfile
from contextlib import closing
from urllib.parse import quote
from hashlib import sha1
import json,sqlite3,argparse

from writerforge import WriterForgeDB,RuntimeEngine,XuehaiStore
from writerforge.r2_storage import R2StorageError
from experiments.wf_0cf_r2_durable_literary_snapshot import _vault,ROLES,_QueryOnlyDb
from experiments.wf_0cn_append_daily_classics import (
    NEW_LIBRARY as BASE_LIBRARY,inspect as inspect_base,_fingerprint,
)
from experiments.wf_0cm_append_five_source_pinned_readings import complete_text

PACK=Path(__file__).resolve().parents[1]/"experiments/wf_0cp_four_lao_can_sequel_social_close_readings_20261029.json"
NEW_LIBRARY="wf-0cp-xuehai-literary-140-20261029-v1"
ROLE="classical_original_annotation_reflection"
NOTE="WF0CP_FOUR_LAOCAN_SEQUEL_SOCIAL_FULL_READINGS"


def load_pack():
    p=json.loads(PACK.read_text("utf8"))
    if (p["format"]!="wf.0cp.four-social-dialogue-classic-readings.v1"
        or len(p["items"])!=4 or len({i["id"] for i in p["items"]})!=4
        or set(p["sources"])!={"lc"} or
        p["base_library"]!=BASE_LIBRARY or
        p["planned_entries"]!=140 or p["planned_full_readings"]!=92 or
        p["source_original_unchanged"] is not True or
        p["no_new_memory_or_review_system"] is not True or p["model_calls"]!=0):
        raise ValueError("WF0CP_EXPECTED_NEW_FOUR_OLD_136_CONTRACT")
    for row in p["items"]:
        if (row["source_key"]!="lc" or row["work"]!=p["sources"]["lc"]["work"]
            or not row["id"].startswith("classic-0cp-")
            or len(row["annotation"])!=3 or len(row["reflection"])<130
            or any(len(n)<70 for n in row["annotation"])
            or len(row["original"])<300
            or row["original_source_end"]-row["original_source_start"]!=len(row["original"])
            or any(a not in row["original"] for a in row["anchors"])
            or len(complete_text(row,p["sources"]["lc"]))>5000):
            raise ValueError("WF0CP_NEW_READING_NOT_COMPLETE")
    return p


def verify_source(p,filename:Path):
    src=p["sources"]["lc"]
    raw=Path(filename).read_bytes()
    if (len(raw)!=src["source_size_bytes"] or
        sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()!=src["source_blob_sha1"]):
        raise ValueError("WF0CP_GITENBERG_SOURCE_VERSION_CHANGED")
    text=raw.decode("utf8").replace("\r\n","\n").replace("\r","\n")
    for row in p["items"]:
        start,end=row["original_source_start"],row["original_source_end"]
        if text[start:end]!=row["original"] or text.count(row["original"])!=1:
            raise ValueError("WF0CP_ORIGINAL_CONTIGUOUS_SOURCE_DIFFERENT_"+row["id"])


def audit(path:Path):
    pack=load_pack()
    uri="file:"+quote(str(Path(path).resolve()),safe="/:")+"?mode=ro"
    with closing(sqlite3.connect(uri,uri=True)) as conn:
        conn.row_factory=sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        if conn.execute("PRAGMA quick_check").fetchone()[0]!="ok":
            raise ValueError("WF0CP_DB_DAMAGED")
        if (conn.execute("SELECT COUNT(*) FROM accepted_prose").fetchone()[0] or
            conn.execute("SELECT COUNT(*) FROM xuehai_method_cards").fetchone()[0]):
            raise ValueError("WF0CP_CANON_OR_METHOD_WRITE_FORBIDDEN")
        rows=conn.execute(
            "SELECT id,work_id,source_role,source_hash,text,method_cluster "
            "FROM xuehai_entries WHERE source_role IN (?,?,?,?) "
            "ORDER BY work_id,source_role,source_hash,text",ROLES
        ).fetchall()
        old=[x for x in rows if not x["method_cluster"].startswith("classic-0cp-")]
        new=[x for x in rows if x["method_cluster"].startswith("classic-0cp-")]
        if (len(rows)!=140 or len(old)!=136 or len(new)!=4 or
            _fingerprint(old)!=pack["base_content_sha256"] or
            {x["method_cluster"] for x in new}!={r["id"] for r in pack["items"]}):
            raise ValueError("WF0CP_PREVIOUS_136_CHANGED")
        latest=conn.execute("SELECT id FROM snapshots WHERE status='published' "
                            "ORDER BY id DESC LIMIT 1").fetchone()
        if latest is None:
            raise ValueError("WF0CP_MISSING_PUBLISHED_SOURCE")
        rt=RuntimeEngine();rt.enter_write(latest["id"])
        try:
            reader=XuehaiStore(_QueryOnlyDb(conn),rt)
            count=0
            for row in rows:
                if row["source_role"] not in (ROLE,"original_annotation_reflection"):
                    continue
                study=reader.read_literary_reading(row["id"])
                if len(study["annotations"])!=3 or not study["reflection"]:
                    raise ValueError("WF0CP_ONE_READING_MISSING")
                count+=1
            if count!=92:
                raise ValueError("WF0CP_EXPECT_92_COMPLETE_READINGS")
            for r in pack["items"]:
                row=next(x for x in new if x["method_cluster"]==r["id"])
                source=reader.read_literary_reading(row["id"])
                if (row["text"]!=complete_text(r,pack["sources"]["lc"]) or
                    source["original"]!=r["original"].rstrip("\n") or
                    source["reflection"]!=r["reflection"] or
                    any(note not in found for note,found in zip(r["annotation"],source["annotations"]))):
                    raise ValueError("WF0CP_NEW_READING_DIFFERS_FROM_SOURCE")
        finally:
            rt.exit()
        return {"entries":140,"full_readings":92,"new_readings":4,
                "old_136_sha256":_fingerprint(old),
                "all_140_sha256":_fingerprint(rows)}


def stage(dbpath:Path,source_path:Path):
    p=load_pack();verify_source(p,source_path)
    if dbpath.exists():
        raise FileExistsError("WF0CP_REFUSE_OVERWRITE_EXISTING_DB")
    with TemporaryDirectory(prefix="wf0cp-base-") as tmp:
        remote=_vault(cold_only=True).restore(
            library=BASE_LIBRARY,snapshot=p["base_snapshot"],
            destination=Path(tmp)/"source")
        previous=inspect_base(Path(remote["db"]))
        if previous["entries"]!=136 or previous["complete_content_sha256"]!=p["base_content_sha256"]:
            raise ValueError("WF0CP_PINNED_136_READBACK_CHANGED")
        copyfile(remote["db"],dbpath)
    db=WriterForgeDB(dbpath);rt=RuntimeEngine()
    try:
        store=XuehaiStore(db,rt)
        rt.enter_learn()
        sid=store.create_staging_snapshot(parent_id=store.latest_published(),note=NOTE)
        for row in p["items"]:
            store.add_entry(
                sid,work_id="gitenberg-pinned-lc-xupian",
                text=complete_text(row,p["sources"]["lc"]),
                library_class="美国公版原文＋贴句批注＋开放心得",
                culture="中国",genre="古代白话／世情／交谈",
                source_role=ROLE,function=row["topic"],effect=row["title"],
                method_cluster=row["id"],reuse_policy="read_reflect_not_copy")
        store.publish(sid)
    finally:
        rt.exit();db.close()
    return {"status":"WF0CP_EXISTING_XUEHAI_STAGED_140_92",
            **audit(dbpath),"old_r2_modified":False,
            "model_calls":0,"canon_writes":0}


def publish(dbpath:Path):
    wanted=audit(dbpath)
    vault=_vault()
    if vault._head(vault._latest_key(NEW_LIBRARY)) is not None:
        with TemporaryDirectory(prefix="wf0cp-existing-") as tmp:
            remote=vault.restore(library=NEW_LIBRARY,destination=tmp)
            if audit(Path(remote["db"]))!=wanted:
                raise R2StorageError("WF0CP_NEW_LIBRARY_EXISTS_WITH_DIFFERENT_CONTENT")
            snapshot=remote["snapshot"]
            created=False
    else:
        out=vault.backup(database=dbpath,library=NEW_LIBRARY)
        snapshot=out["snapshot"]
        with TemporaryDirectory(prefix="wf0cp-post-upload-") as tmp:
            check=vault.restore(library=NEW_LIBRARY,snapshot=snapshot,destination=tmp)
            if audit(Path(check["db"]))!=wanted:
                raise R2StorageError("WF0CP_NEW_SNAPSHOT_FAILED_VERIFICATION")
        created=True
    return {"status":"WF0CP_R2_NEW_LIBRARY_WRITTEN",
            "library":NEW_LIBRARY,"snapshot":snapshot,**wanted,
            "new_snapshot_created":created,"older_libraries_unchanged":True,
            "model_calls":0,"canon_writes":0}


def cold_restore(snapshot:str,digest:str):
    with TemporaryDirectory(prefix="wf0cp-readonly-cold-") as tmp:
        restored=_vault(cold_only=True).restore(
            library=NEW_LIBRARY,snapshot=snapshot,destination=tmp)
        result=audit(Path(restored["db"]))
    if result["all_140_sha256"]!=digest or restored["snapshot"]!=snapshot:
        raise ValueError("WF0CP_COLD_RESTORE_FAILED")
    return {"status":"WF0CP_INDEPENDENT_140_92_READBACK","snapshot":snapshot,
            **result,"model_calls":0,"r2_writes":0,"canon_writes":0}


def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="action",required=True)
    one=sub.add_parser("stage")
    one.add_argument("--db",type=Path,required=True)
    one.add_argument("--original",type=Path,required=True)
    two=sub.add_parser("publish")
    two.add_argument("--db",type=Path,required=True)
    three=sub.add_parser("cold-restore")
    three.add_argument("--snapshot",required=True)
    three.add_argument("--digest",required=True)
    args=ap.parse_args()
    result=(stage(args.db,args.original) if args.action=="stage" else
            publish(args.db) if args.action=="publish" else
            cold_restore(args.snapshot,args.digest))
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()
