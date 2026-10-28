"""Six complete classical readings: 原文 + 批注 + 心得, in the EXISTING 学海.

No new schema, method-card bureaucracy or fabricated literary ratings.
Combine with the previous 24 original scenes in ONE disposable SQLite DB.
The three pinned GITenberg files are checked for exact excerpt membership;
source text is not changed or uploaded wholesale to WriterForge.
"""
from __future__ import annotations
from hashlib import sha1,sha256
from pathlib import Path
import argparse,json

from writerforge import WriterForgeDB,RuntimeEngine,XuehaiStore
from writerforge.xuehai import Query
from experiments.wf_0br_merge_three_classics_with_original_xuehai import (
    add_classics_to_actual_xuehai, STAGING_NOTE, load_curated_classical_texts,
)
from experiments.wf_0bq_stage_original_full_detail_prose import (
    validate_corpus, WORK_PREFIX, SOURCE_COMMITS, CORPUS_FILES,
)

ROOT=Path(__file__).resolve().parents[1]
CORPUS=ROOT/"experiments/wf_0br_classical_original_annotation_reflection_20261028.json"
ROLE="classical_original_annotation_reflection"
NOTE="WF0BR_SIX_CLASSICS_WITH_ORIGINAL_ANNOTATION_REFLECTION"
REMAINING=ROOT/"experiments/wf_0bs_classical_remaining_18_original_annotation_reflection_20261028.json"
REMAINING_NOTE="WF0BS_REMAINING_18_CLASSICS_ORIGINAL_ANNOTATION_REFLECTION"
ORIGINAL_READINGS=ROOT/"experiments/wf_0bt_original_eight_close_readings_20261028.json"
ORIGINAL_NOTE="WF0BT_ORIGINAL_EIGHT_COMPLETE_SCENE_READINGS"
ORIGINAL_ROLE="original_annotation_reflection"
# The first six deep readings overlap these six source excerpts. Keep them unchanged.
PREVIOUSLY_COVERED={"x02","x07","h03","h06","s03","s07"}


def load_readings():
    data=json.loads(CORPUS.read_text(encoding="utf8"))
    if data.get("format")!="wf.literary-reading.original-annotation-reflection.v1":
        raise ValueError("WF0BR_WRONG_CORPUS")
    sources=data["sources"]
    rows=data["items"]
    if len(rows)!=6 or set(sources)!={"xy","hl","sh"}:
        raise ValueError("WF0BR_EXPECTED_THREE_BOOKS_SIX_READINGS")
    if len({r["id"] for r in rows})!=6:
        raise ValueError("WF0BR_DUPLICATE_READING")
    for row in rows:
        if (row["source_key"] not in sources
            or not 250<=len(row["original"])<=1400
            or not isinstance(row["annotation"],list)
            or len(row["annotation"])!=3
            or any(not isinstance(x,str) or len(x)<30 for x in row["annotation"])
            or not isinstance(row["reflection"],str)
            or len(row["reflection"])<70):
            raise ValueError("WF0BR_MISSING_ORIGINAL_NOTES_OR_REFLECTION")
    return sources,rows


def read_source_bytes(files:dict[str,Path],sources:dict,rows:list)->None:
    """Only verify that excerpts occur verbatim in the PINNED source versions."""
    if set(files)!=set(sources):
        raise ValueError("WF0BR_SOURCE_FILES_REQUIRED")
    for key,source in sources.items():
        raw=Path(files[key]).read_bytes()
        git_sha=sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
        if git_sha!=source["git_blob_sha1"]:
            raise ValueError("WF0BR_SOURCE_GIT_BLOB_CHANGED")
        text=raw.decode("utf-8-sig").replace("\r\n","\n").replace("\r","\n")
        for item in rows:
            if item["source_key"]==key and text.count(item["original"])!=1:
                raise ValueError("WF0BR_ORIGINAL_PASSAGE_NOT_EXACTLY_IN_SOURCE")


def reading_text(row:dict,source:dict)->str:
    """A single human-readable corpus item, with no lost original or reflection."""
    return (
        f"【出处】{row['work']}·{row['chapter']}｜{source['url']}\n"
        f"【原文】\n{row['original']}\n"
        "【批注】\n"+ "\n".join(
            f"{i}. {note}" for i,note in enumerate(row["annotation"],1))
        +"\n【心得】\n"+row["reflection"]
    )


def stage(db_path:Path,files:dict[str,Path])->dict:
    """Add six annotated readings to the EXISTING 24+24 literary Xuehai."""
    db_path=Path(db_path)
    if db_path.exists():
        raise FileExistsError("WF0BR_REFUSE_OVERWRITE_DATABASE")
    sources,rows=load_readings()
    read_source_bytes(files,sources,rows)
    # Reuse the existing 0.BR importer, not a parallel source library.
    source_dir=Path(files["xy"]).parent
    expected={"xy":"23962-0.txt","hl":"24264-0.txt","sh":"23863-0.txt"}
    if any(Path(files[key])!=source_dir/name for key,name in expected.items()):
        raise ValueError("WF0BR_USE_EXISTING_PINNED_CLASSIC_FILENAMES")
    preexisting=add_classics_to_actual_xuehai(
        db_path=db_path,source_dir=source_dir)
    if (preexisting["existing_original_xuanhuan_scenes"]!=24
        or preexisting["new_actual_classical_prose_passages"]!=24):
        raise RuntimeError("WF0BR_PREVIOUS_48_TEXTS_NOT_FOUND")
    db=WriterForgeDB(db_path)
    rt=RuntimeEngine();rt.enter_learn()
    store=XuehaiStore(db,rt)
    try:
        root=db.conn.execute(
            "SELECT id FROM snapshots WHERE note=?",
            (STAGING_NOTE,),
        ).fetchone()
        if not root:
            raise RuntimeError("WF0BR_PREVIOUS_48_LITERARY_TEXTS_MISSING")
        # Publish ONLY the disposable, previously-staged original scene node
        # so both sources live in the SAME queryable Xuehai snapshot lineage.
        store.publish(root["id"])
        snapshot=store.create_staging_snapshot(
            parent_id=root["id"],note=NOTE)
        entries=[]
        for row in rows:
            text=reading_text(row,sources[row["source_key"]])
            eid=store.add_entry(
                snapshot,
                work_id="gitenberg-pinned-"+row["source_key"],
                text=text,library_class="古籍原文＋批注＋心得",
                culture="中国",genre="古代白话",
                source_role=ROLE,function=row["topic"],
                effect=row["title"],method_cluster=row["id"],
                reuse_policy="read_reflect_not_copy"
            )
            dbrow=db.conn.execute(
                "SELECT text FROM xuehai_entries WHERE id=?",(eid,)
            ).fetchone()
            if dbrow is None or dbrow["text"]!=text:
                raise RuntimeError("WF0BR_ORIGINAL_ANNOTATION_REFLECTION_NOT_PRESERVED")
            entries.append({
                "id":row["id"],"entry_id":eid,
                "work":row["work"],"chapter":row["chapter"],
                "original_chars":len(row["original"]),
                "annotation_count":3,
                "reflection_chars":len(row["reflection"]),
                "complete_entry_sha256":sha256(text.encode("utf8")).hexdigest()
            })
        count=db.conn.execute(
            "SELECT COUNT(*) FROM xuehai_entries WHERE snapshot_id=?",
            (snapshot,),
        ).fetchone()[0]
        if count!=6 or db.conn.execute(
            "SELECT COUNT(*) FROM xuehai_method_cards"
        ).fetchone()[0]!=0:
            raise RuntimeError("WF0BR_WRONG_XUEHAI_CONTENT")
        # Demo mode only. Not an author-model prompt, not production.
        store.publish(snapshot)
        rt.exit();rt.enter_write(snapshot)
        preview={}
        for term in ("黛玉","林沖","猴王"):
            result=store.query(Query(
                genre="古代白话",source_role=ROLE,
                text_terms=(term,),limit=3,max_per_work=3,max_per_cluster=3))
            if not result:
                raise RuntimeError("WF0BR_BOOK_NOT_RETRIEVABLE")
            entry_id=result[0]["entry_id"]
            full=store.read_literary_reading(entry_id)
            identity=db.conn.execute(
                "SELECT method_cluster FROM xuehai_entries WHERE id=?",
                (entry_id,)
            ).fetchone()["method_cluster"]
            matching=next(row for row in rows if row["id"]==identity)
            if (full["original"]!=matching["original"] or
                full["reflection"]!=matching["reflection"] or
                len(full["annotations"])!=len(matching["annotation"]) or
                not all(note in full["annotations"][i]
                        for i,note in enumerate(matching["annotation"]))):
                raise RuntimeError("WF0BR_READ_RETURNED_ONLY_SUMMARY")
            preview[term]={
                "entry_id":entry_id,
                "original_chars":len(full["original"]),
                "annotation_count":len(full["annotations"]),
                "reflection_chars":len(full["reflection"]),
                "read_complete_three_part_text":True,
                "legacy_short_query_excerpt_chars":len(result[0]["evidence_excerpt"]),
            }
        old=db.conn.execute(
            "SELECT COUNT(*) FROM xuehai_entries WHERE source_role=?",
            ("original_complete_scene_unreviewed",),
        ).fetchone()[0]
        if old!=24:
            raise RuntimeError("WF0BR_LOST_PREVIOUS_FULL_PROSE")
        classics=db.conn.execute(
            "SELECT COUNT(*) FROM xuehai_entries WHERE source_role=?",
            ("public_domain_continuous_detail_prose_unreviewed",),
        ).fetchone()[0]
        if classics!=24:
            raise RuntimeError("WF0BR_PREVIOUS_24_CLASSICS_WERE_LOST")
        return {
            "status":"SIX_REAL_CLASSICAL_ORIGINAL_ANNOTATIONS_REFLECTIONS_STORED",
            "books":3,"annotated_classic_entries":6,
            "original_prose_scenes_kept":old,
            "original_classical_passages_kept":classics,
            "total_content_entries":old+classics+len(entries),
            "original_classic_chars":sum(x["original_chars"] for x in entries),
            "distinct_reading_topics":len({x["topic"] for x in rows}),
            "database":"DISPOSABLE_ONLY",
            "model_calls":0,"actual_literary_gain_proven":False,
            "production_canon_changes":0,"external_review_claims":0,
            "read_examples":preview,"entries":entries,
        }
    finally:
        db.close()




def load_remaining_readings():
    """The 18 new readings retain the exact old 0.BR prose; no retranslation."""
    sources, six = load_readings()
    data=json.loads(REMAINING.read_text(encoding="utf8"))
    if (data.get("format")!="wf.literary-reading.original-annotation-reflection.v1"
        or data.get("sources")!=sources or data.get("literary_gain_proven") is not False):
        raise ValueError("WF0BS_WRONG_READING_SOURCE")
    rows=data.get("items")
    corpus=load_curated_classical_texts()
    by_id={x["id"]:x for x in corpus["excerpts"]}
    expected=set(by_id)-PREVIOUSLY_COVERED
    source_keys={"x":"xy","h":"hl","s":"sh"}
    work_names={"x":"西游记","h":"红楼梦","s":"水浒传"}
    if (type(rows) is not list or len(rows)!=18
        or {r.get("source_excerpt_id") for r in rows}!=expected
        or len({r.get("id") for r in rows})!=18):
        raise ValueError("WF0BS_EXPECTED_18_UNREAD_CLASSICAL_PASSAGES")
    for row in rows:
        excerpt=by_id[row["source_excerpt_id"]]
        prefix=row["source_excerpt_id"][0]
        if (row.get("id")!="classic-0bs-"+excerpt["id"]
            or row.get("source_key")!=source_keys[prefix]
            or row.get("work")!=work_names[prefix]
            or row.get("chapter")!=excerpt["chapter_title"]
            or row.get("original")!=excerpt["excerpt"]
            or not isinstance(row.get("annotation"),list)
            or len(row["annotation"])!=3
            or any(type(n) is not str or len(n)<38 or "\n" in n for n in row["annotation"])
            or type(row.get("reflection")) is not str
            or len(row["reflection"])<100):
            raise ValueError("WF0BS_READING_OR_ORIGINAL_NOT_PRESERVED")
    return sources, six, rows


def stage_all_24(db_path:Path,files:dict[str,Path])->dict:
    """Append the remaining 18 to the *same* isolated 24+24+6 Xuehai DB."""
    original_result=stage(db_path,files)
    sources,six,remaining=load_remaining_readings()
    read_source_bytes(files,sources,remaining)
    db=WriterForgeDB(db_path)
    rt=RuntimeEngine();rt.enter_learn()
    store=XuehaiStore(db,rt)
    try:
        previous=db.conn.execute(
            "SELECT id FROM snapshots WHERE note=? AND status='published'",
            (NOTE,),
        ).fetchone()
        if not previous:
            raise RuntimeError("WF0BS_SIX_PUBLISHED_READINGS_NOT_FOUND")
        sid=store.create_staging_snapshot(
            parent_id=previous["id"],note=REMAINING_NOTE)
        for row in remaining:
            text=reading_text(row,sources[row["source_key"]])
            store.add_entry(
                sid,work_id="gitenberg-pinned-"+row["source_key"],
                text=text,library_class="古籍原文＋批注＋心得",
                culture="中国",genre="古代白话",
                source_role=ROLE,function=row["topic"],
                effect=row["title"],method_cluster=row["id"],
                reuse_policy="read_reflect_not_copy",
            )
        store.publish(sid)
        rt.exit();rt.enter_write(sid)
        rows=db.conn.execute(
            "SELECT id,method_cluster FROM xuehai_entries WHERE source_role=?",
            (ROLE,),
        ).fetchall()
        by_cluster={row["method_cluster"]:row["id"] for row in rows}
        if (len(rows)!=24 or len(by_cluster)!=24
            or set(by_cluster)!={row["id"] for row in six+remaining}):
            raise RuntimeError("WF0BS_NOT_ALL_24_READINGS_IN_THE_EXISTING_XUEHAI")
        for row in six+remaining:
            full=store.read_literary_reading(by_cluster[row["id"]])
            if (full["original"]!=row["original"]
                or full["source"]!=f"{row['work']}·{row['chapter']}｜{sources[row['source_key']]['url']}"
                or full["reflection"]!=row["reflection"]
                or len(full["annotations"])!=3
                or any(note not in full["annotations"][i]
                       for i,note in enumerate(row["annotation"]))):
                raise RuntimeError("WF0BS_READING_LOST_ORIGINAL_OR_INTERPRETATION")
        roles=("original_complete_scene_unreviewed",
               "public_domain_continuous_detail_prose_unreviewed",ROLE)
        role_counts={
            row["source_role"]:row["n"] for row in db.conn.execute(
                "SELECT source_role,COUNT(*) AS n FROM xuehai_entries "
                "WHERE source_role IN (?,?,?) GROUP BY source_role",roles
            ).fetchall()
        }
        total=sum(role_counts.values())
        methods=db.conn.execute(
            "SELECT COUNT(*) FROM xuehai_method_cards"
        ).fetchone()[0]
        if (role_counts!={roles[0]:24,roles[1]:24,roles[2]:24}
            or total!=72 or methods!=0):
            raise RuntimeError(
                f"WF0BS_CONTENT_ROLES_CHANGED: {role_counts}, methods={methods}")
        return {
            "status":"24_COMPLETE_CLASSICAL_READINGS_IN_EXISTING_XUEHAI",
            "books":3,"original_prose_scenes_kept":24,
            "original_classical_passages_kept":24,
            "six_previous_readings_kept":6,
            "new_remaining_readings":18,
            "annotated_classic_entries":24,
            "total_content_entries":total,
            "original_classic_chars":sum(len(r["original"]) for r in six+remaining),
            "readback_all_24_complete":True,
            "published_method_cards":methods,
            "database":"DISPOSABLE_ONLY",
            "model_calls":0,"actual_literary_gain_proven":False,
            "production_canon_changes":0,
        }
    finally:
        db.close()



def load_original_eight():
    """Select eight existing original full scenes; never replace them with summaries."""
    raw=json.loads(ORIGINAL_READINGS.read_text("utf8"))
    sources=raw.get("sources")
    expected_sources={
        "original_"+pack:{
            "work":"WF原创场景 "+pack,
            "url":("https://github.com/66tyu55/WriterForge/blob/"
                   +SOURCE_COMMITS[pack]+"/experiments/"
                   +CORPUS_FILES[pack].name),
            "origin":"WriterForge original prose",
        } for pack in ("A","B")
    }
    if (raw.get("format")!="wf.literary-reading.original-annotation-reflection.v1"
        or raw.get("literary_gain_proven") is not False
        or raw.get("independently_reviewed") is not False
        or raw.get("originals_are_unaccepted_writerforge_drafts") is not True
        or sources!=expected_sources):
        raise ValueError("WF0BT_WRONG_ORIGINAL_NOTES_SOURCE")
    originals,_=validate_corpus()
    by_id={x["id"]:x for x in originals}
    selected={
        "bq-01-丹室潮火","bq-07-石桥短兵","bq-09-宗门药房",
        "bq-12-廊下异声","bq-14-筋伤余日","bq-21-外门入试",
        "bq-22-两封家书","bq-23-水下客",
    }
    rows=raw.get("items")
    if (type(rows) is not list or len(rows)!=8
        or {r.get("original_scene_id") for r in rows}!=selected
        or len({r.get("id") for r in rows})!=8):
        raise ValueError("WF0BT_EIGHT_DISTINCT_ORIGINALS_REQUIRED")
    for r in rows:
        source=by_id[r["original_scene_id"]]
        if (r.get("id")!="original-read-"+r["original_scene_id"][:5]
            or r.get("source_key")!="original_"+source["pack"]
            or r.get("work")!="WF原创·"+source["title"]
            or r.get("chapter")!="完整场景"
            or r.get("original")!=source["prose"]
            or type(r.get("annotation")) is not list
            or len(r["annotation"])!=3
            or any(type(n) is not str or len(n)<65 or "\n" in n
                   for n in r["annotation"])
            or type(r.get("reflection")) is not str
            or len(r["reflection"])<125):
            raise ValueError("WF0BT_ORIGINAL_NOTES_NOT_SOURCE_GROUNDED")
    return sources,rows,by_id


def stage_with_original_eight(db_path:Path,files:dict[str,Path])->dict:
    """Existing single disposable Xuehai: 24 originals + 24 classics + 24 classic readings + 8 original readings."""
    previous_result=stage_all_24(db_path,files)
    sources,rows,by_id=load_original_eight()
    db=WriterForgeDB(db_path)
    rt=RuntimeEngine();rt.enter_learn()
    store=XuehaiStore(db,rt)
    try:
        previous=db.conn.execute(
            "SELECT id FROM snapshots WHERE note=? AND status='published'",
            (REMAINING_NOTE,),
        ).fetchone()
        if previous is None:
            raise RuntimeError("WF0BT_24_CLASSICAL_READINGS_NOT_PUBLISHED")
        sid=store.create_staging_snapshot(parent_id=previous["id"],
                                          note=ORIGINAL_NOTE)
        for item in rows:
            text=reading_text(item,sources[item["source_key"]])
            original=by_id[item["original_scene_id"]]
            store.add_entry(
                sid,work_id=WORK_PREFIX+item["original_scene_id"],
                text=text,library_class="原创小说原文＋批注＋心得",
                culture="中国",genre=original["genre"],
                source_role=ORIGINAL_ROLE,function=item["topic"],
                effect=item["title"],method_cluster=item["id"],
                reuse_policy="read_reflect_not_copy",
            )
        store.publish(sid)
        rt.exit();rt.enter_write(sid)
        orig_entries=db.conn.execute(
            "SELECT id,method_cluster FROM xuehai_entries WHERE source_role=?",
            (ORIGINAL_ROLE,),
        ).fetchall()
        if len(orig_entries)!=8:
            raise RuntimeError("WF0BT_EIGHT_ORIGINAL_READING_ENTRIES_MISSING")
        cluster_to_id={e["method_cluster"]:e["id"] for e in orig_entries}
        if set(cluster_to_id)!={r["id"] for r in rows}:
            raise RuntimeError("WF0BT_DUPLICATE_ORIGINAL_READINGS")
        for item in rows:
            full=store.read_literary_reading(cluster_to_id[item["id"]])
            if (full["original"]!=item["original"]
                or full["reflection"]!=item["reflection"]
                or full["source"]!=
                   f"{item['work']}·{item['chapter']}｜{sources[item['source_key']]['url']}"
                or len(full["annotations"])!=3
                or any(note not in full["annotations"][i]
                       for i,note in enumerate(item["annotation"]))):
                raise RuntimeError("WF0BT_ORIGINAL_READING_TRUNCATED")
        roles=("original_complete_scene_unreviewed",
               "public_domain_continuous_detail_prose_unreviewed",
               ROLE,ORIGINAL_ROLE)
        counts=dict(db.conn.execute(
            "SELECT source_role,COUNT(*) FROM xuehai_entries "
            "WHERE source_role IN (?,?,?,?) GROUP BY source_role",roles
        ).fetchall())
        expected=dict(zip(roles,(24,24,24,8)))
        if (counts!=expected or
            db.conn.execute("SELECT COUNT(*) FROM xuehai_method_cards").fetchone()[0]!=0):
            raise RuntimeError(f"WF0BT_CHANGED_EXISTING_CORPUS: {counts}")
        return {
            "status":"8_ORIGINAL_AND_24_CLASSICAL_THREE_PART_READINGS_COMPLETE",
            "existing_24_original_scenes_kept":24,
            "existing_24_classic_prose_kept":24,
            "existing_24_classic_readings_kept":24,
            "new_original_readings":8,
            "original_readings_full_readback":True,
            "total_literary_entries":sum(counts.values()),
            "model_calls":0,
            "method_cards":0,
            "database":"DISPOSABLE_ONLY",
            "production_canon_changes":0,
            "literary_gain_proven":False,
        }
    finally:
        db.close()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--db",type=Path,required=True)
    for key in ("xy","hl","sh"):
        p.add_argument("--"+key,type=Path,required=True)
    p.add_argument("--all24",action="store_true",
                   help="include the 0.BS remaining eighteen complete readings")
    p.add_argument("--original8",action="store_true",
                   help="also store and read eight original prose critiques in the same Xuehai")
    args=p.parse_args()
    runner=(stage_with_original_eight if args.original8
            else stage_all_24 if args.all24 else stage)
    print(json.dumps(runner(args.db,{key:getattr(args,key) for key in ("xy","hl","sh")}),
                     ensure_ascii=False,indent=2,sort_keys=True))
