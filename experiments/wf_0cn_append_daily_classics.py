"""0.CN: source-verified daily-life originals appended to EXISTING Xuehai.

Do not train author model, modify Canon, reuse the old 0.CM latest pointer,
create a new database schema, or claim that lexical retrieval is literary
understanding. The only remote mutation is a NEW immutable 136/88 R2 library.
"""
from __future__ import annotations
import argparse, json, hashlib, sqlite3
from contextlib import closing
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from urllib.parse import quote
from writerforge import WriterForgeDB, RuntimeEngine, XuehaiStore
from writerforge.xuehai import Query
from writerforge.r2_storage import R2StorageError
from experiments.wf_0cf_r2_durable_literary_snapshot import _vault, ROLES, _QueryOnlyDb
from experiments.wf_0cm_append_five_source_pinned_readings import (
    NEW_LIBRARY as PREVIOUS_LIBRARY,
    inspect_augmented as inspect_previous,
    complete_text as render_reading,
)
from experiments.wf_0cg_existing_r2_to_real_writer_offline import (
    PINNED_CONTENT as ORIGINAL_126,
)

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/"experiments/wf_0cn_five_daily_life_classics_20261029.json"
NEW_LIBRARY="wf-0cn-xuehai-literary-136-20261029-v1"
ROLE="classical_original_annotation_reflection"
CHILD_NOTE="WF0CN_FIVE_DAILY_LIFE_CLASSICS_NO_LITERARY_GRADE"


def load():
    p=json.loads(PACK.read_text("utf8"))
    if (p.get("format")!="wf.0cn.five-daily-life-classic-readings.v1"
        or len(p.get("items",[]))!=5
        or len({i["id"] for i in p["items"]})!=5
        or {i["source_key"] for i in p["items"]}!={"rl","zb"}
        or p.get("base_r2_library")!=PREVIOUS_LIBRARY
        or p.get("new_literary_entries_expected")!=136
        or p.get("new_full_readings_expected")!=88
        or p.get("preserve_originals") is not True
        or p.get("no_new_store_or_memory") is not True
        or p.get("author_use_skip_unchanged") is not True
        or p.get("model_calls")!=0):
        raise ValueError("WF0CN_PACK_OR_HISTORICAL_BOUNDARY_CHANGED")
    for item in p["items"]:
        if (not item["id"].startswith("classic-0cn-")
            or item["work"]!=p["sources"][item["source_key"]]["work"]
            or item["original_source_end"]-item["original_source_start"]!=len(item["original"])
            or len(item["original"])<130
            or len(item["annotation"])!=3
            or any(len(n)<65 for n in item["annotation"])
            or len(item["reflection"])<130
            or len(item["anchors"])!=3
            or any(a not in item["original"] for a in item["anchors"])
            or not 300<=len(render_reading(item,p["sources"][item["source_key"]]))<=5000):
            raise ValueError("WF0CN_INCOMPLETE_OR_UNGROUNDED_READING")
    return p


def verify_sources(data, *, rl:Path, zb:Path):
    for key,filename in (("rl",rl),("zb",zb)):
        src=data["sources"][key]
        raw=Path(filename).read_bytes()
        git=hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()
        if len(raw)!=src["source_size_bytes"] or git!=src["source_blob_sha1"]:
            raise ValueError("WF0CN_REAL_SOURCE_BLOB_CHANGED_"+key)
        # Only retrieval comparison is normalized; keep original item bytes
        # unchanged as they were selected from the pinned Gutenberg edition.
        text=raw.decode("utf-8").replace("\r\n","\n").replace("\r","\n")
        for row in data["items"]:
            if row["source_key"]!=key:
                continue
            a,b=row["original_source_start"],row["original_source_end"]
            if text[a:b]!=row["original"] or text.count(row["original"])!=1:
                raise ValueError("WF0CN_LITERAL_CONTIGUOUS_SOURCE_MISMATCH_"+row["id"])


def _fingerprint(rows):
    return hashlib.sha256(json.dumps(
        [[x["work_id"],x["source_role"],x["source_hash"],x["text"]] for x in rows],
        ensure_ascii=False,separators=(",",":")
    ).encode("utf8")).hexdigest()


def inspect(dbfile:Path):
    data=load()
    uri="file:"+quote(str(Path(dbfile).resolve()),safe="/:")+"?mode=ro"
    with closing(sqlite3.connect(uri,uri=True)) as conn:
        conn.row_factory=sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        if conn.execute("PRAGMA quick_check").fetchone()[0]!="ok":
            raise ValueError("WF0CN_SQLITE_CHECK_FAILED")
        if conn.execute("SELECT COUNT(*) FROM xuehai_method_cards").fetchone()[0] or (
            conn.execute("SELECT COUNT(*) FROM accepted_prose").fetchone()[0]):
            raise ValueError("WF0CN_NO_METHOD_OR_PROSE_CANON_CHANGES")
        rows=conn.execute(
            "SELECT id,work_id,source_role,source_hash,text,method_cluster "
            "FROM xuehai_entries WHERE source_role IN (?,?,?,?) "
            "ORDER BY work_id,source_role,source_hash,text",ROLES
        ).fetchall()
        previous=[r for r in rows if not r["method_cluster"].startswith("classic-0cn-")]
        newly=[r for r in rows if r["method_cluster"].startswith("classic-0cn-")]
        if (len(previous)!=131 or len(newly)!=5 or len(rows)!=136
            or _fingerprint(previous)!=data["base_literary_content_sha256"]
            or {r["method_cluster"] for r in newly}!={i["id"] for i in data["items"]}):
            raise ValueError("WF0CN_131_OLD_CONTENT_OR_NEW_FIVE_DID_NOT_MATCH")
        if len(newly)!=len({r["source_hash"] for r in newly}):
            raise ValueError("WF0CN_DUPLICATE_NEW_CONTENT")
        sid=conn.execute("SELECT id FROM snapshots WHERE status='published' "
                         "ORDER BY id DESC LIMIT 1").fetchone()
        if sid is None:
            raise ValueError("WF0CN_MISSING_PUBLISHED_CHILD")
        rt=RuntimeEngine()
        rt.enter_write(sid["id"])
        store=XuehaiStore(_QueryOnlyDb(conn),rt)
        try:
            count=0
            for r in rows:
                if r["source_role"] not in ("classical_original_annotation_reflection",
                                            "original_annotation_reflection"):
                    continue
                rd=store.read_literary_reading(r["id"])
                if len(rd["annotations"])!=3 or not rd["original"].strip():
                    raise ValueError("WF0CN_READING_NOT_COMPLETE")
                count+=1
            if count!=88:
                raise ValueError("WF0CN_88_THREE_PART_READBACK_COUNT_INVALID")
            for i in data["items"]:
                row=next(r for r in newly if r["method_cluster"]==i["id"])
                rd=store.read_literary_reading(row["id"])
                full=render_reading(i,data["sources"][i["source_key"]])
                if (row["text"]!=full or rd["original"]!=i["original"].rstrip("\n")
                    or rd["reflection"]!=i["reflection"]
                    or any(a not in note for a,note in zip(i["annotation"],rd["annotations"]))):
                    raise ValueError("WF0CN_NEW_COMPLETE_READING_CORRUPTED")
            # This exercises the SAME author-facing selector on the new
            # published snapshot, without asserting a literary grade.
            probes=(
                ("宗门灶边一位学徒给师兄留下一口热饭，又替他把衣襟掖好。",
                 "怎样写不多言的照顾？用饭菜、衣着、劳作和省下的零碎钱带出人物之间的感情。"),
                ("一位隐居的修士送别当年教自己读书的人，河上船渐渐离去。",
                 "如何写送别里的师友情谊和日常生计，既有留恋也想到以后衣食怎么安排？"),
                ("修真城新婚宴后，婆家逼新娘下厨做吉利菜。",
                 "如何借一尾鱼和礼俗称谓写出婚姻中不服气与暗中的尊卑冲突？")
            )
            selected=[]
            for goal,problem in probes:
                result=store.select_literary_reading_for_author(
                    goal=goal,writing_problem=problem,max_chars=4900)
                if result:
                    if not all(k in result["complete_reading"] for k in
                               ("【原文】","【批注】","【心得】")):
                        raise ValueError("WF0CN_AUTHOR_GOT_TRUNCATED_READING")
                    rr=conn.execute("SELECT method_cluster FROM xuehai_entries WHERE id=?",
                                    (result["entry_id"],)).fetchone()
                    selected.append(rr["method_cluster"])
                else:
                    selected.append(None)
        finally:
            rt.exit()
        return {"entries":136,"full_readings":88,"new_readings":5,
                "previous_content_sha256":_fingerprint(previous),
                "complete_content_sha256":_fingerprint(rows),
                "author_selection_observed":selected,
                "author_final_use_skip_not_overridden":True}


def stage(out:Path, *, rl:Path, zb:Path):
    data=load()
    verify_sources(data,rl=rl,zb=zb)
    if out.exists():
        raise FileExistsError("WF0CN_REFUSE_OVERWRITE_DB")
    with TemporaryDirectory(prefix="wf0cn-r2-readonly-") as tmp:
        restored=_vault(cold_only=True).restore(
            library=PREVIOUS_LIBRARY,snapshot=data["base_r2_snapshot"],
            destination=Path(tmp)/"previous")
        old=inspect_previous(Path(restored["db"]))
        if old["all_131_sha256"]!=data["base_literary_content_sha256"]:
            raise ValueError("WF0CN_BASE_131_PIN_CHANGED")
        if old["old_126_sha256"]!=ORIGINAL_126 or old["entries"]!=131:
            raise ValueError("WF0CN_BASE_DOES_NOT_PRESERVE_0CF")
        copyfile(restored["db"],out)
    db=WriterForgeDB(out)
    rt=RuntimeEngine()
    try:
        store=XuehaiStore(db,rt)
        oldcount=db.conn.execute(
            "SELECT COUNT(*) FROM xuehai_entries WHERE source_role IN (?,?,?,?)",
            ROLES
        ).fetchone()[0]
        if oldcount!=131:
            raise ValueError("WF0CN_NOT_EXISTING_131_LITERARY_ENTRIES")
        parent=store.latest_published()
        rt.enter_learn()
        new_sid=store.create_staging_snapshot(parent_id=parent,note=CHILD_NOTE)
        for i in data["items"]:
            store.add_entry(new_sid,work_id="gitenberg-pinned-"+i["source_key"],
                            text=render_reading(i,data["sources"][i["source_key"]]),
                            library_class="美国公版连续原文＋具体批注＋开放心得",
                            culture="中国",genre="古代白话／市井／人情",
                            source_role=ROLE,function=i["topic"],effect=i["title"],
                            method_cluster=i["id"],reuse_policy="read_reflect_not_copy")
        store.publish(new_sid)
    finally:
        rt.exit()
        db.close()
    return {"status":"WF0CN_DISPOSABLE_EXISTING_XUEHAI_136_88",
            **inspect(out),"old_r2_modified":False,"model_calls":0,"canon_writes":0}


def publish(dbfile:Path):
    expected=inspect(dbfile)
    v=_vault()
    if v._head(v._latest_key(NEW_LIBRARY)) is not None:
        with TemporaryDirectory(prefix="wf0cn-existing-") as tmp:
            restore=v.restore(library=NEW_LIBRARY,destination=tmp)
            if inspect(Path(restore["db"]))!=expected:
                raise R2StorageError("WF0CN_EXISTING_NEW_LIBRARY_DIFFERENT_NO_REPLACE")
            snapshot=restore["snapshot"]
            uploaded=False
    else:
        result=v.backup(database=dbfile,library=NEW_LIBRARY)
        snapshot=result["snapshot"]
        with TemporaryDirectory(prefix="wf0cn-verify-upload-") as tmp:
            restored=v.restore(library=NEW_LIBRARY,snapshot=snapshot,destination=tmp)
            if inspect(Path(restored["db"]))!=expected:
                raise R2StorageError("WF0CN_UPLOADED_SNAPSHOT_MISMATCH")
        uploaded=True
    return {"status":"WF0CN_IMMUTABLE_XUEHAI_SUCCESSOR_STORED",
            "library":NEW_LIBRARY,"snapshot":snapshot,**expected,
            "new_r2_successor_created":uploaded,"old_131_r2_unchanged":True,
            "model_calls":0,"canon_writes":0}


def cold_restore(*, snapshot:str, digest:str):
    with TemporaryDirectory(prefix="wf0cn-independent-read-") as tmp:
        restored=_vault(cold_only=True).restore(
            library=NEW_LIBRARY,snapshot=snapshot,destination=tmp)
        actual=inspect(Path(restored["db"]))
    if restored["snapshot"]!=snapshot or actual["complete_content_sha256"]!=digest:
        raise ValueError("WF0CN_INDEPENDENT_R2_CONTENT_MISMATCH")
    return {"status":"WF0CN_FIVE_REAL_READING_COLD_RESTORE_GREEN",
            "snapshot":snapshot,"library":NEW_LIBRARY,**actual,
            "r2_writes":0,"model_calls":0,"canon_writes":0}


def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="action",required=True)
    a=sub.add_parser("stage")
    a.add_argument("--db",type=Path,required=True)
    a.add_argument("--rl",type=Path,required=True)
    a.add_argument("--zb",type=Path,required=True)
    b=sub.add_parser("publish")
    b.add_argument("--db",type=Path,required=True)
    c=sub.add_parser("cold-restore")
    c.add_argument("--snapshot",required=True)
    c.add_argument("--digest",required=True)
    args=ap.parse_args()
    r=(stage(args.db,rl=args.rl,zb=args.zb) if args.action=="stage" else
       publish(args.db) if args.action=="publish" else
       cold_restore(snapshot=args.snapshot,digest=args.digest))
    print(json.dumps(r,ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
