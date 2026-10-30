"""Append a small, source-pinned 原文＋批注＋心得 pack to EXISTING Xuehai.

A reusable experiment runner, NOT a new runtime datastore or literature
grader. Verify original bytes and immutable old content; publish only a NEW
R2 successor prefix. Work is limited to an ephemeral copy of the old SQLite.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from hashlib import sha1
import json
from pathlib import Path
from shutil import copyfile
import sqlite3
from tempfile import TemporaryDirectory
from urllib.parse import quote

from writerforge import WriterForgeDB, RuntimeEngine, XuehaiStore
from writerforge.r2_storage import R2StorageError
from experiments.wf_0cf_r2_durable_literary_snapshot import (
    ROLES, _vault, _QueryOnlyDb,
)
from experiments.wf_0cn_append_daily_classics import _fingerprint
from experiments.wf_0cm_append_five_source_pinned_readings import complete_text

ROLE="classical_original_annotation_reflection"

def pack_from(path:Path):
    p=json.loads(Path(path).read_text("utf8"))
    rows=p.get("items")
    old=p.get("old_entries")
    # Only explicitly source-frozen additive editions are accepted. No generic
    # catalogue importer, mutable pointer, or second learning database.
    specifications={
        "wf.0cq.five-public-classics-close-readings.v1":
            (140,97,5,"wf-0cq-xuehai-literary-145-","classic-0cq-"),
        "wf.0cr.three-anchored-classical-close-readings.v1":
            (145,100,3,"wf-0cr-xuehai-literary-148-","classic-0cr-"),
        "wf.0cs.five-social-dialogue-close-readings.v1":
            (148,105,5,"wf-0cs-xuehai-literary-153-","classic-0cs-"),
        "wf.0ct.four-voices-and-negotiation-classics.v1":
            (153,109,4,"wf-0ct-xuehai-literary-157-","classic-0ct-"),
        "wf.0cu.four-genre-real-world-close-readings.v1":
            (157,113,4,"wf-0cu-xuehai-literary-161-","classic-0cu-"),
        "wf.0cv.five-supernatural-and-human-cost-close-readings.v1":
            (161,118,5,"wf-0cv-xuehai-literary-166-","classic-0cv-"),
        "wf.0cw.four-original-xuanhuan-scenes.v1":
            (166,122,4,"wf-0cw-xuehai-literary-170-","classic-0cw-original-"),
        "wf.0cx.five-original-xuanhuan-continuations.v1":
            (170,127,5,"wf-0cx-xuehai-literary-175-","classic-0cx-original-"),
        "wf.0cy.five-diverse-original-xuanhuan-scenes.v1":
            (175,132,5,"wf-0cy-xuehai-literary-180-","classic-0cy-original-"),
        "wf.0cz.five-distinct-public-domain-classic-close-readings.v1":
            (180,137,5,"wf-0cz-xuehai-literary-185-","classic-0cz-"),
        "wf.0da.three-cross-genre-genuine-classics.v1":
            (185,140,3,"wf-0da-xuehai-literary-188-","classic-0da-"),
        "wf.0db.four-genuine-human-relations-close-readings.v1":
            (188,144,4,"wf-0db-xuehai-literary-192-","classic-0db-"),
        "wf.0dc.four-genuine-causality-and-responsibility-readings.v1":
            (192,148,4,"wf-0dc-xuehai-literary-196-","classic-0dc-"),
        "wf.0dd.four-immersive-concrete-classics.v1":
            (196,152,4,"wf-0dd-xuehai-literary-200-","classic-0dd-"),
        "wf.0de.four-lived-material-and-supernatural-readings.v1":
            (200,156,4,"wf-0de-xuehai-literary-204-","classic-0de-"),
        "wf.0df.five-labor-travel-object-power-readings.v1":
            (204,161,5,"wf-0df-xuehai-literary-209-","classic-0df-"),
    }
    expected_source_sets={
        "wf.0cq.five-public-classics-close-readings.v1": {"fs","ss"},
        "wf.0cr.three-anchored-classical-close-readings.v1": {"fs","ss"},
        "wf.0cs.five-social-dialogue-close-readings.v1": {"dp","jm"},
        "wf.0ct.four-voices-and-negotiation-classics.v1": {"hh","nh"},
        "wf.0cu.four-genre-real-world-close-readings.v1": {"fu","ru","er","gc"},
        "wf.0cv.five-supernatural-and-human-cost-close-readings.v1": {"fg","jh","lz","sj"},
        "wf.0cw.four-original-xuanhuan-scenes.v1": {"own"},
        "wf.0cx.five-original-xuanhuan-continuations.v1": {"own"},
        "wf.0cy.five-diverse-original-xuanhuan-scenes.v1": {"own"},
        "wf.0cz.five-distinct-public-domain-classic-close-readings.v1": {"hl","sh","md","th","jt"},
        "wf.0da.three-cross-genre-genuine-classics.v1": {"xx","xh","xk"},
        "wf.0db.four-genuine-human-relations-close-readings.v1": {"ym","ek","fs","rl"},
        "wf.0dc.four-genuine-causality-and-responsibility-readings.v1": {"sg","xy","lc","lz"},
        "wf.0dd.four-immersive-concrete-classics.v1": {"hl","sh","lc","rl"},
        "wf.0de.four-lived-material-and-supernatural-readings.v1": {"fs","ek","sj","rl"},
        "wf.0df.five-labor-travel-object-power-readings.v1": {"ek","lc","rl","th"},
    }
    spec=specifications.get(p.get("format"))
    if (spec is None
        or not isinstance(rows,list) or len(rows)!=spec[2]
        or old!=spec[0] or p.get("expected_entries")!=old+len(rows)
        or p.get("expected_full_readings")!=spec[1]
        or p.get("new_entries")!=len(rows)
        or p.get("preserve_originals") is not True
        or p.get("new_rules_or_memory") is not False
        or p.get("author_model_use_skip_unchanged") is not True
        or p.get("model_calls")!=0
        or len({v["id"] for v in rows})!=len(rows)
        or not str(p.get("new_library","")).startswith(spec[3])
        or set(p.get("sources",{}))!=expected_source_sets.get(p.get("format"),set())):
        raise ValueError("WF_SOURCE_PACK_NOT_FROZEN_SUCCESSOR")
    for r in rows:
        if (not r["id"].startswith(spec[4])
            or r["source_key"] not in p["sources"]
            or r["work"]!=p["sources"][r["source_key"]]["work"]
            or r["original_source_end"]-r["original_source_start"]!=len(r["original"])
            or len(r["original"])<95
            or len(r["annotation"])!=3 or any(len(x)<70 for x in r["annotation"])
            or len(r["reflection"])<140
            or len(r["anchors"])!=3 or any(a not in r["original"] for a in r["anchors"])
            or len(complete_text(r,p["sources"][r["source_key"]]))>5000):
            raise ValueError("WF_SOURCE_PACK_THREE_PART_READING_INVALID")
    return p

def verify_sources(p,source_dir:Path):
    for key,src in p["sources"].items():
        expected_url=("https://raw.githubusercontent.com/"+src["source_repo"]+"/"
                      +src["source_commit"]+"/"+src["filename"])
        if src["url"]!=expected_url:
            raise ValueError("WF_SOURCE_PINNED_URL_INVALID")
        original_editions={
            "wf.0cw.four-original-xuanhuan-scenes.v1":
                "experiments/wf_0cw_original_xuanhuan_scenes_20261030.txt",
            "wf.0cx.five-original-xuanhuan-continuations.v1":
                "experiments/wf_0cx_original_xuanhuan_continuations_20261030.txt",
            "wf.0cy.five-diverse-original-xuanhuan-scenes.v1":
                "experiments/wf_0cy_five_diverse_xuanhuan_scenes_20261030.txt",
        }
        if p.get("format") in original_editions:
            if (src["source_repo"]!="66tyu55/WriterForge"
                or src["filename"]!=original_editions[p["format"]]
                or src.get("provenance")!="CHATGPT_WRITTEN_IN_THIS_USER_REQUEST_UNREVIEWED"
                or len(src["source_commit"])!=40):
                raise ValueError("WF_SOURCE_PINNED_ORIGINAL_INVALID")
        elif not src["source_repo"].startswith("GITenberg/"):
            raise ValueError("WF_SOURCE_PINNED_URL_INVALID")
        raw=(Path(source_dir)/src["filename"]).read_bytes()
        git=sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()
        if len(raw)!=src["source_size_bytes"] or git!=src["source_blob_sha1"]:
            raise ValueError("WF_SOURCE_GIT_BLOB_CHANGED_"+key)
        source=raw.decode("utf8").replace("\r\n","\n").replace("\r","\n")
        for r in p["items"]:
            if r["source_key"]!=key:
                continue
            a,b=r["original_source_start"],r["original_source_end"]
            if source[a:b]!=r["original"] or source.count(r["original"])!=1:
                raise ValueError("WF_SOURCE_ORIGINAL_NOT_LITERAL_CONTIGUOUS_"+r["id"])

def inspect(dbpath:Path,p):
    uri="file:"+quote(str(Path(dbpath).resolve()),safe="/:")+"?mode=ro"
    with closing(sqlite3.connect(uri,uri=True)) as conn:
        conn.row_factory=sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        if conn.execute("PRAGMA quick_check").fetchone()[0]!="ok":
            raise ValueError("WF_SOURCE_DB_CORRUPT")
        if (conn.execute("SELECT COUNT(*) FROM accepted_prose").fetchone()[0]!=0 or
            conn.execute("SELECT COUNT(*) FROM xuehai_method_cards").fetchone()[0]!=0):
            raise ValueError("WF_SOURCE_FORBID_CANON_AND_METHOD_CARD_WRITE")
        rows=conn.execute(
            "SELECT id,work_id,source_role,source_hash,text,method_cluster "
            "FROM xuehai_entries WHERE source_role IN (?,?,?,?) "
            "ORDER BY work_id,source_role,source_hash,text",ROLES
        ).fetchall()
        # Compare the explicit, frozen IDs in this edition only; "classic-0cq"
        # is a valid part of the OLD 145-entry snapshot during 0.CR.
        new_ids={r["id"] for r in p["items"]}
        old=[v for v in rows if v["method_cluster"] not in new_ids]
        new=[v for v in rows if v["method_cluster"] in new_ids]
        if (len(rows)!=p["expected_entries"] or len(old)!=p["old_entries"]
            or len(new)!=p["new_entries"]
            or _fingerprint(old)!=p["base_content_sha256"]
            or {v["method_cluster"] for v in new}!={r["id"] for r in p["items"]}):
            raise ValueError("WF_SOURCE_OLD_EDITION_OR_NEW_ENTRIES_NOT_EXACT")
        latest=conn.execute("SELECT id FROM snapshots WHERE status='published' "
                            "ORDER BY id DESC LIMIT 1").fetchone()
        if not latest:
            raise ValueError("WF_SOURCE_NO_PUBLISHED_CHILD")
        rt=RuntimeEngine()
        rt.enter_write(latest["id"])
        try:
            store=XuehaiStore(_QueryOnlyDb(conn),rt)
            n=0
            for v in rows:
                if v["source_role"] not in ("classical_original_annotation_reflection",
                                            "original_annotation_reflection"):
                    continue
                read=store.read_literary_reading(v["id"])
                if not read["original"] or len(read["annotations"])!=3 or not read["reflection"]:
                    raise ValueError("WF_SOURCE_THREE_PARTS_MISSING")
                n+=1
            if n!=p["expected_full_readings"]:
                raise ValueError("WF_SOURCE_WRONG_NUMBER_OF_FULL_READINGS")
            for r in p["items"]:
                v=next(x for x in new if x["method_cluster"]==r["id"])
                rd=store.read_literary_reading(v["id"])
                if (v["text"]!=complete_text(r,p["sources"][r["source_key"]])
                    or rd["original"]!=r["original"].rstrip("\n")
                    or rd["reflection"]!=r["reflection"]
                    or any(a not in b for a,b in zip(r["annotation"],rd["annotations"]))):
                    raise ValueError("WF_SOURCE_NEW_READING_BYTES_CHANGED_"+r["id"])
        finally:
            rt.exit()
        return {"entries":len(rows),"full_readings":n,
                "added":len(new),"old_content_sha256":_fingerprint(old),
                "all_content_sha256":_fingerprint(rows)}

def stage(dbpath:Path,p,source_dir:Path):
    verify_sources(p,source_dir)
    if dbpath.exists():
        raise FileExistsError("WF_SOURCE_REFUSE_OVERWRITE_DB")
    with TemporaryDirectory(prefix="wf-source-prev-") as tmp:
        old=_vault(cold_only=True).restore(
            library=p["base_library"],snapshot=p["base_snapshot"],
            destination=Path(tmp)/"r2-old")
        # Prior content checksum is independently checked below after append.
        copyfile(old["db"],dbpath)
    db=WriterForgeDB(dbpath)
    rt=RuntimeEngine()
    try:
        store=XuehaiStore(db,rt)
        if (db.conn.execute(
            "SELECT COUNT(*) FROM xuehai_entries WHERE source_role IN (?,?,?,?)",ROLES
        ).fetchone()[0]!=p["old_entries"] or not store.latest_published()):
            raise ValueError("WF_SOURCE_OLD_PUBLISHED_LIBRARY_NOT_FOUND")
        rt.enter_learn()
        sid=store.create_staging_snapshot(parent_id=store.latest_published(),
                                          note="WF_SOURCE_FIVE_PINNED_CLASSIC_CLOSE_READINGS")
        for r in p["items"]:
            is_original=p.get("format") in (
                "wf.0cw.four-original-xuanhuan-scenes.v1",
                "wf.0cx.five-original-xuanhuan-continuations.v1",
                "wf.0cy.five-diverse-original-xuanhuan-scenes.v1")
            store.add_entry(sid,work_id=("wf-original-pinned-"+r["source_key"]
                                         if is_original else "gitenberg-pinned-"+r["source_key"]),
                            text=complete_text(r,p["sources"][r["source_key"]]),
                            library_class=("本轮新写原创玄幻完整场景，非古籍且未经人工文学评审"
                                           if is_original else "美国公版完整原文＋贴句批注＋开放心得"),
                            culture="中国",genre=r.get("genre","古典世情／笔记／家常"),
                            source_role=ROLE,function=r["topic"],effect=r["title"],
                            method_cluster=r["id"],reuse_policy="read_reflect_not_copy")
        store.publish(sid)
    finally:
        rt.exit()
        db.close()
    return {"status":"WF_SOURCE_EXISTING_XUEHAI_APPEND_FIVE",
            **inspect(dbpath,p),"old_r2_modified":False,
            "model_calls":0,"canon_writes":0}

def publish(dbpath:Path,p):
    want=inspect(dbpath,p)
    v=_vault()
    if v._head(v._latest_key(p["new_library"])) is not None:
        with TemporaryDirectory(prefix="wf-source-old-successor-") as tmp:
            prior=v.restore(library=p["new_library"],destination=tmp)
            if inspect(Path(prior["db"]),p)!=want:
                raise R2StorageError("WF_SOURCE_NEW_PREFIX_HAS_DIFFERENT_CONTENT")
            snapshot=prior["snapshot"]
            wrote=False
    else:
        snapshot=v.backup(database=dbpath,library=p["new_library"])["snapshot"]
        with TemporaryDirectory(prefix="wf-source-r2-verify-") as tmp:
            restored=v.restore(library=p["new_library"],snapshot=snapshot,
                               destination=tmp)
            if inspect(Path(restored["db"]),p)!=want:
                raise R2StorageError("WF_SOURCE_UPLOAD_NOT_VERIFIED")
        wrote=True
    return {"status":"WF_SOURCE_NEW_IMMUTABLE_R2_SUCCESSOR",
            "library":p["new_library"],"snapshot":snapshot,**want,
            "created_new_prefix":wrote,"old_prefix_modified":False,
            "model_calls":0,"canon_writes":0}

def cold_restore(p,*,snapshot:str,digest:str):
    with TemporaryDirectory(prefix="wf-source-cold-") as tmp:
        restored=_vault(cold_only=True).restore(
            library=p["new_library"],snapshot=snapshot,destination=tmp)
        audit=inspect(Path(restored["db"]),p)
    if restored["snapshot"]!=snapshot or audit["all_content_sha256"]!=digest:
        raise ValueError("WF_SOURCE_COLD_R2_DIFFERENT")
    status=f"WF_SOURCE_NEW_R2_COLD_READBACK_{p['expected_entries']}_{p['expected_full_readings']}"
    return {"status":status,
            **audit,"r2_writes":0,"model_calls":0,"canon_writes":0}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("action",choices=("stage","publish","cold-restore"))
    ap.add_argument("--pack",type=Path,required=True)
    ap.add_argument("--db",type=Path)
    ap.add_argument("--source-dir",type=Path)
    ap.add_argument("--snapshot")
    ap.add_argument("--digest")
    args=ap.parse_args()
    p=pack_from(args.pack)
    if args.action=="stage":
        r=stage(args.db,p,args.source_dir)
    elif args.action=="publish":
        r=publish(args.db,p)
    else:
        r=cold_restore(p,snapshot=args.snapshot,digest=args.digest)
    print(json.dumps(r,ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
