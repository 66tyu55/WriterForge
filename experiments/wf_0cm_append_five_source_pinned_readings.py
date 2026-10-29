"""0.CM content-first: 5 genuine new pinned classics in EXISTING Xuehai.

Read-only restore of the original 126/78 R2 edition; append 5 readings to a
new published Xuehai child snapshot in a DISPOSABLE copied SQLite. A separate,
immutable R2 library receives the 131/83 successor edition, never overwriting
0.CF or an old literary passage. No model calls, Canon, Railway, rules,
semantic grades or new persistence system.
"""
from __future__ import annotations

from contextlib import closing
from hashlib import sha1, sha256
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from urllib.parse import quote
import argparse
import json
import sqlite3

from writerforge import WriterForgeDB, RuntimeEngine, XuehaiStore
from writerforge.r2_storage import R2StorageError
from experiments.wf_0cf_r2_durable_literary_snapshot import (
    LIBRARY as OLD_LIBRARY, ROLES, _vault, inspect_literary_db, _QueryOnlyDb,
)
from experiments.wf_0cg_existing_r2_to_real_writer_offline import (
    PINNED_SNAPSHOT, PINNED_CONTENT,
)

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/"experiments/wf_0cm_five_genuine_classics_original_annotation_reflection_20261029.json"
NEW_LIBRARY="wf-0cm-xuehai-literary-131-20261029-v1"
NEW_ROLE="classical_original_annotation_reflection"
STAGE_NOTE="WF0CM_FIVE_GENUINE_PUBLIC_CLASSICS_THREE_PART_READINGS"


def load_pack():
    data=json.loads(PACK.read_text("utf8"))
    if (data.get("format")!="wf.0cm.existing-xuehai-five-public-classic-readings.v1"
        or len(data.get("items",[]))!=5
        or len({r["id"] for r in data["items"]})!=5
        or set(data["sources"])!={"hx","zb"}
        or data.get("modify_existing_r2") is not False
        or data.get("modify_originals") is not False
        or data.get("new_schema_or_memory") is not False
        or data.get("model_calls")!=0):
        raise ValueError("WF0CM_CONTENT_CONTRACT_CHANGED")
    for row in data["items"]:
        src=data["sources"].get(row["source_key"])
        if (not src or row["work"]!=src["work"] or
            not row["id"].startswith("classic-0cm-") or
            len(row["original"])<330 or len(row["original"])>3000 or
            row["original_source_end"]-row["original_source_start"]!=len(row["original"]) or
            len(row["annotation"])!=3 or
            any(len(note)<72 for note in row["annotation"]) or
            len(row["reflection"])<145 or
            len(row["anchors"])!=3 or
            any(a not in row["original"] for a in row["anchors"])):
            raise ValueError("WF0CM_SOURCE_OR_NOTES_INVALID")
        if not 200 <= len(complete_text(row,src)) <= 5000:
            raise ValueError("WF0CM_READING_TOO_LARGE_OR_INCOMPLETE")
    return data


def complete_text(row, source):
    # Preserve every word and internal line break. The boundary newline
    # belongs to the separator, so no duplicate blank paragraph is fabricated.
    original=row["original"].rstrip("\n")
    return (f"【出处】{row['work']}·{row['chapter']}｜{source['url']}\n"
            "【原文】\n"+original+"\n【批注】\n"+
            "\n".join(f"{i}. {a}" for i,a in enumerate(row["annotation"],1))+
            "\n【心得】\n"+row["reflection"])


def verify_public_sources(data, *, hx:Path, zb:Path):
    for key,filename in (("hx",hx),("zb",zb)):
        src=data["sources"][key]
        raw=Path(filename).read_bytes()
        if (len(raw)!=src["source_size_bytes"] or
            sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()!=src["source_blob_sha1"]):
            raise ValueError("WF0CM_PINNED_GITENBERG_SOURCE_CHANGED_"+key)
        normalized=raw.decode("utf-8").replace("\r\n","\n").replace("\r","\n")
        for row in data["items"]:
            if row["source_key"]!=key:
                continue
            a,b=row["original_source_start"],row["original_source_end"]
            if normalized[a:b]!=row["original"] or normalized.count(row["original"])!=1:
                raise ValueError("WF0CM_CONTIGUOUS_LITERAL_ORIGINAL_CHANGED_"+row["id"])


def inspect_augmented(path:Path):
    # Both prior and new contents are audited against exact bytes. Compare
    # preexisting 126-entry fingerprint against 0.CF, independent of SQLite
    # row IDs, time, VACUUM or the new Xuehai child snapshot.
    uri="file:"+quote(str(Path(path).resolve()),safe="/:")+"?mode=ro"
    data=load_pack()
    with closing(sqlite3.connect(uri,uri=True)) as conn:
        conn.row_factory=sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        if conn.execute("PRAGMA quick_check").fetchone()[0]!="ok":
            raise ValueError("WF0CM_SQLITE_CORRUPT")
        rows=conn.execute(
            "SELECT id,work_id,source_role,source_hash,text,method_cluster "
            "FROM xuehai_entries WHERE source_role IN (?,?,?,?) "
            "ORDER BY work_id,source_role,source_hash,text",ROLES
        ).fetchall()
        old=[x for x in rows if not str(x["method_cluster"]).startswith("classic-0cm-")]
        new=[x for x in rows if str(x["method_cluster"]).startswith("classic-0cm-")]
        fingerprint=sha256(json.dumps(
            [[x["work_id"],x["source_role"],x["source_hash"],x["text"]] for x in old],
            ensure_ascii=False,separators=(",",":")).encode("utf8")).hexdigest()
        if (len(old)!=126 or len(new)!=5 or len(rows)!=131 or
            fingerprint!=PINNED_CONTENT or
            {x["method_cluster"] for x in new}!={x["id"] for x in data["items"]}):
            raise ValueError("WF0CM_PRIOR_126_CHANGED_OR_NEW_FIVE_MISSING")
        latest=conn.execute("SELECT id FROM snapshots WHERE status='published' "
                            "ORDER BY id DESC LIMIT 1").fetchone()
        if not latest:
            raise ValueError("WF0CM_NO_PUBLISHED_SUCCESSOR_SNAPSHOT")
        rt=RuntimeEngine()
        rt.enter_write(int(latest["id"]))
        store=XuehaiStore(_QueryOnlyDb(conn),rt)
        try:
            old_reads=0
            for x in rows:
                if x["source_role"] not in ("original_annotation_reflection",NEW_ROLE):
                    continue
                read=store.read_literary_reading(int(x["id"]))
                if not read["original"].strip() or len(read["annotations"])!=3:
                    raise ValueError("WF0CM_THREE_PART_MISSING")
                old_reads+=1
            if old_reads!=83:
                raise ValueError("WF0CM_83_THREE_PART_READINGS_NOT_PRESENT")
            for row in data["items"]:
                x=next(v for v in new if v["method_cluster"]==row["id"])
                exp=complete_text(row,data["sources"][row["source_key"]])
                got=store.read_literary_reading(x["id"])
                if (x["text"]!=exp or x["source_role"]!=NEW_ROLE or
                    got["original"]!=row["original"].rstrip("\n") or
                    got["reflection"]!=row["reflection"] or
                    any(a not in n for a,n in zip(row["annotation"],got["annotations"]))):
                    raise ValueError("WF0CM_NEW_READING_EXACT_BYTES_CHANGED")
        finally:
            rt.exit()
        all_sha=sha256(json.dumps(
            [[x["work_id"],x["source_role"],x["source_hash"],x["text"]] for x in rows],
            ensure_ascii=False,separators=(",",":")).encode("utf8")).hexdigest()
        return {"entries":131,"full_readings":83,"added":5,
                "old_126_sha256":fingerprint,"all_131_sha256":all_sha}


def stage(dbfile:Path, *, hx:Path, zb:Path):
    data=load_pack()
    verify_public_sources(data,hx=hx,zb=zb)
    if Path(dbfile).exists():
        raise FileExistsError("WF0CM_REFUSE_OVERWRITE_STAGED_DATABASE")
    with TemporaryDirectory(prefix="wf0cm-source-only-r2-") as folder:
        restore=_vault(cold_only=True).restore(
            library=OLD_LIBRARY,snapshot=PINNED_SNAPSHOT,
            destination=Path(folder)/"pinned")
        old=inspect_literary_db(Path(restore["db"]))
        if old["content_sha256"]!=PINNED_CONTENT or old["contents"]!=126:
            raise ValueError("WF0CM_PINNED_BASE_NOT_126_78")
        copyfile(restore["db"],dbfile)
    db=WriterForgeDB(dbfile)
    rt=RuntimeEngine()
    try:
        store=XuehaiStore(db,rt)
        parent=store.latest_published()
        if parent is None or db.conn.execute("SELECT COUNT(*) FROM xuehai_entries WHERE source_role IN (?,?,?,?)",ROLES).fetchone()[0]!=126:
            raise ValueError("WF0CM_NO_BASE_PUBLISHED_126")
        rt.enter_learn()
        sid=store.create_staging_snapshot(parent_id=parent,note=STAGE_NOTE)
        for row in data["items"]:
            src=data["sources"][row["source_key"]]
            store.add_entry(
                sid,work_id="gitenberg-pinned-"+row["source_key"],
                text=complete_text(row,src),
                library_class="公版完整连续原文＋具体批注＋开放心得",
                culture="中国",genre="志怪／游仙／古代白话",
                source_role=NEW_ROLE,function=row["topic"],
                effect=row["title"],method_cluster=row["id"],
                reuse_policy="read_reflect_not_copy",
            )
        store.publish(sid)
    finally:
        rt.exit()
        db.close()
    result=inspect_augmented(dbfile)
    return {"status":"WF0CM_FIVE_PUBLIC_CLASSICS_APPENDED_DISPOSABLE",
            **result,"old_r2_modified":False,"new_library_not_yet_published":True,
            "model_calls":0,"canon_writes":0}


def publish(dbfile:Path):
    expected=inspect_augmented(dbfile)
    vault=_vault()
    if vault._head(vault._latest_key(NEW_LIBRARY)) is not None:
        # Never overwrite a different existing successor; on rerun require
        # exact same logical literature and otherwise refuse outright.
        with TemporaryDirectory(prefix="wf0cm-existing-r2-") as folder:
            saved=vault.restore(library=NEW_LIBRARY,destination=folder)
            actual=inspect_augmented(Path(saved["db"]))
            if actual!=expected:
                raise R2StorageError("WF0CM_EXISTING_NEW_LIBRARY_CONTENT_DIFFERS")
            snapshot=saved["snapshot"]
            wrote=False
    else:
        saved=vault.backup(database=dbfile,library=NEW_LIBRARY)
        snapshot=saved["snapshot"]
        with TemporaryDirectory(prefix="wf0cm-published-verify-") as folder:
            actual=inspect_augmented(Path(
                vault.restore(library=NEW_LIBRARY,snapshot=snapshot,
                              destination=folder)["db"]))
            if actual!=expected:
                raise R2StorageError("WF0CM_NEW_R2_COLD_READBACK_FAILED")
        wrote=True
    return {"status":"WF0CM_NEW_IMMUTABLE_R2_SUCCESSOR",
            "library":NEW_LIBRARY,"snapshot":snapshot,
            **expected,"uploaded_new_successor":wrote,
            "old_library_unchanged":True,"model_calls":0,"canon_writes":0}


def cold_restore(*, snapshot:str,expected_sha:str):
    with TemporaryDirectory(prefix="wf0cm-independent-") as folder:
        restored=_vault(cold_only=True).restore(
            library=NEW_LIBRARY,snapshot=snapshot,destination=folder)
        actual=inspect_augmented(Path(restored["db"]))
    if actual["all_131_sha256"]!=expected_sha or restored["snapshot"]!=snapshot:
        raise ValueError("WF0CM_INDEPENDENT_RESTORE_DIFFERENT")
    return {"status":"WF0CM_INDEPENDENT_COLD_RESTORE_131_83",
            "library":NEW_LIBRARY,"snapshot":snapshot,**actual,
            "model_calls":0,"r2_writes":0,"canon_writes":0}


def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="action",required=True)
    st=sub.add_parser("stage")
    st.add_argument("--db",type=Path,required=True)
    st.add_argument("--hx",type=Path,required=True)
    st.add_argument("--zb",type=Path,required=True)
    pb=sub.add_parser("publish")
    pb.add_argument("--db",type=Path,required=True)
    cr=sub.add_parser("cold-restore")
    cr.add_argument("--snapshot",required=True)
    cr.add_argument("--sha",required=True)
    a=parser.parse_args()
    if a.action=="stage":
        r=stage(a.db,hx=a.hx,zb=a.zb)
    elif a.action=="publish":
        r=publish(a.db)
    else:
        r=cold_restore(snapshot=a.snapshot,expected_sha=a.sha)
    print(json.dumps(r,ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()
