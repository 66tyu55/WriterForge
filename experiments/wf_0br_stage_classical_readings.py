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
REMAINING_ORIGINAL=ROOT/"experiments/wf_0bu_remaining_sixteen_original_close_readings_20261028.json"
REMAINING_ORIGINAL_NOTE="WF0BU_REMAINING_SIXTEEN_ORIGINAL_COMPLETE_READINGS"
FANTASY_READINGS=ROOT/"experiments/wf_0bv_three_fantasy_classics_six_close_readings_20261028.json"
FANTASY_NOTE="WF0BV_THREE_PUBLIC_DOMAIN_FANTASY_BOOKS_SIX_FULL_READINGS"
FANTASY_LONG=ROOT/"experiments/wf_0bw_three_fantasy_classics_six_long_readings_20261029.json"
FANTASY_LONG_NOTE="WF0BW_THREE_FANTASY_BOOKS_TWELVE_COMPLETE_READINGS"
NEXT_FANTASY=ROOT/"experiments/wf_0bx_three_new_fantasy_books_six_close_readings_20261029.json"
NEXT_FANTASY_NOTE="WF0BX_SIX_BOOKS_EIGHTEEN_COMPLETE_FANTASY_READINGS"
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



def load_remaining_original_sixteen():
    """Remaining original readings must reproduce the OTHER 16 whole 0.BQ scenes."""
    sources,first_eight,originals=load_original_eight()
    obj=json.loads(REMAINING_ORIGINAL.read_text("utf8"))
    rows=obj.get("items")
    expected=set(originals)-{r["original_scene_id"] for r in first_eight}
    if (obj.get("format")!="wf.literary-reading.original-annotation-reflection.v1"
        or obj.get("literary_gain_proven") is not False
        or obj.get("independently_reviewed") is not False
        or obj.get("originals_are_unaccepted_writerforge_drafts") is not True
        or obj.get("sources")!=sources
        or type(rows) is not list or len(rows)!=16
        or {r.get("original_scene_id") for r in rows}!=expected
        or len({r.get("id") for r in rows})!=16):
        raise ValueError("WF0BU_EXPECTED_16_REMAINING_UNCHANGED_ORIGINALS")
    for r in rows:
        x=originals[r["original_scene_id"]]
        if (r.get("id")!="original-read-"+x["id"][:5]
            or r.get("source_key")!="original_"+x["pack"]
            or r.get("work")!="WF原创·"+x["title"]
            or r.get("chapter")!="完整场景"
            or r.get("original")!=x["prose"]
            or type(r.get("annotation")) is not list
            or len(r["annotation"])!=3
            or any(type(note) is not str or len(note)<45
                   or "\n" in note for note in r["annotation"])
            or type(r.get("reflection")) is not str
            or len(r["reflection"])<85):
            raise ValueError("WF0BU_ORIGINAL_PROSE_OR_REAL_READING_CHANGED")
    return sources,first_eight,rows,originals


def stage_with_all_original_24(db_path:Path,files:dict[str,Path])->dict:
    """Add last 16 deep readings into the SAME disposable Xuehai lineage."""
    stage_with_original_eight(db_path,files)
    sources,first_eight,remaining,originals=load_remaining_original_sixteen()
    db=WriterForgeDB(db_path)
    rt=RuntimeEngine();rt.enter_learn()
    store=XuehaiStore(db,rt)
    try:
        previous=db.conn.execute(
            "SELECT id FROM snapshots WHERE note=? AND status='published'",
            (ORIGINAL_NOTE,),
        ).fetchone()
        if previous is None:
            raise RuntimeError("WF0BU_OLD_EIGHT_ORIGINAL_READINGS_NOT_PUBLISHED")
        sid=store.create_staging_snapshot(
            parent_id=previous["id"],note=REMAINING_ORIGINAL_NOTE)
        for item in remaining:
            text=reading_text(item,sources[item["source_key"]])
            original=originals[item["original_scene_id"]]
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
        all_original=first_eight+remaining
        entries=db.conn.execute(
            "SELECT id,method_cluster FROM xuehai_entries WHERE source_role=?",
            (ORIGINAL_ROLE,),
        ).fetchall()
        by_cluster={row["method_cluster"]:row["id"] for row in entries}
        if (len(entries)!=24 or len(by_cluster)!=24 or
            set(by_cluster)!={item["id"] for item in all_original}):
            raise RuntimeError("WF0BU_24_DISTINCT_ORIGINAL_READINGS_NOT_FOUND")
        for item in all_original:
            full=store.read_literary_reading(by_cluster[item["id"]])
            if (full["original"]!=item["original"]
                or full["reflection"]!=item["reflection"]
                or full["source"]!=
                   f"{item['work']}·{item['chapter']}｜{sources[item['source_key']]['url']}"
                or len(full["annotations"])!=3
                or any(note not in full["annotations"][index]
                       for index,note in enumerate(item["annotation"]))):
                raise RuntimeError("WF0BU_FULL_ORIGINAL_ANNOTATION_REFLECTION_LOST")
        roles=("original_complete_scene_unreviewed",
               "public_domain_continuous_detail_prose_unreviewed",
               ROLE,ORIGINAL_ROLE)
        counts=dict(db.conn.execute(
            "SELECT source_role,COUNT(*) FROM xuehai_entries "
            "WHERE source_role IN (?,?,?,?) GROUP BY source_role",roles
        ).fetchall())
        expected=dict(zip(roles,(24,24,24,24)))
        methods=db.conn.execute(
            "SELECT COUNT(*) FROM xuehai_method_cards").fetchone()[0]
        if counts!=expected or methods!=0:
            raise RuntimeError(f"WF0BU_OLD_CONTENT_NOT_PRESERVED: {counts}")
        return {
            "status":"24_ORIGINAL_AND_24_CLASSIC_COMPLETE_THREE_PART_READINGS",
            "original_full_scenes_kept":24,"classic_full_excerpts_kept":24,
            "classic_three_part_readings_kept":24,
            "previous_original_readings_kept":8,
            "new_original_three_part_readings":16,
            "all_original_readings":24,
            "all_48_three_part_readings_complete":True,
            "total_literary_content_entries":sum(counts.values()),
            "method_cards":methods,"model_calls":0,
            "database":"DISPOSABLE_ONLY",
            "production_canon_changes":0,
            "literary_gain_proven":False,
        }
    finally:
        db.close()



def load_fantasy_six():
    """Three *classical* fantasy novels; preserve complete source and interpretations."""
    raw=json.loads(FANTASY_READINGS.read_text("utf8"))
    sources,items=raw.get("sources"),raw.get("items")
    if (raw.get("format")!="wf.literary-reading.original-annotation-reflection.v1"
        or raw.get("literary_gain_proven") is not False
        or raw.get("source_scope")!="USA_PUBLIC_DOMAIN_ONLY_NONUS_UNVERIFIED"
        or type(sources) is not dict or set(sources)!={"fs","jh","lz"}
        or type(items) is not list or len(items)!=6):
        raise ValueError("WF0BV_FANTASY_READINGS_FORMAT_INVALID")
    ids=set()
    for item in items:
        key=item["source_key"]
        source=sources[key]
        if (key not in sources or item["id"] in ids
            or item.get("work")!=source["work"]
            or type(item.get("original")) is not str
            or len(item["original"])<200
            or type(item.get("annotation")) is not list
            or len(item["annotation"])!=3
            or any(type(n) is not str or len(n)<35 for n in item["annotation"])
            or type(item.get("reflection")) is not str
            or len(item["reflection"])<80):
            raise ValueError("WF0BV_NO_COMPLETE_FANTASY_PROSE_READING")
        ids.add(item["id"])
    if {k:sum(i["source_key"]==k for i in items) for k in sources}!={k:2 for k in sources}:
        raise ValueError("WF0BV_FANTASY_BOOK_BALANCE_CHANGED")
    return sources,items


def verify_fantasy_books(files:dict[str,Path],sources:dict,items:list)->None:
    """Pinned source blob + continuous original text, whitespace-only line wrapping ignored."""
    if set(files)!=set(sources):
        raise ValueError("WF0BV_THREE_PINNED_PUBLIC_SOURCE_FILES_REQUIRED")
    for key,source in sources.items():
        raw=Path(files[key]).read_bytes()
        actual_sha=sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()
        if (len(raw)!=source["source_size_bytes"]
            or actual_sha!=source["source_blob_sha1"]):
            raise ValueError("WF0BV_PINNED_GIT_SOURCE_CHANGED_"+key)
        full=raw.decode("utf-8-sig").replace("\r\n","\n").replace("\r","\n")
        joined="".join(full.split())
        for item in items:
            if item["source_key"]!=key:
                continue
            target="".join(item["original"].split())
            if joined.count(target)!=1:
                raise ValueError(
                    "WF0BV_ORIGINAL_NOT_CONTIGUOUS_"+item["id"]+
                    "_head_present="+str(target[:30] in joined)+
                    "_full_length="+str(len(target)))
    return None


def load_fantasy_long(sources:dict,files:dict[str,Path])->list[dict]:
    """Content-only addition: six longer continuous excerpts from the SAME pinned books."""
    raw=json.loads(FANTASY_LONG.read_text("utf8"))
    extra=raw.get("items")
    if (raw.get("format")!="wf.literary-reading.original-annotation-reflection.v1"
        or raw.get("literary_gain_proven") is not False
        or raw.get("source_scope")!="USA_PUBLIC_DOMAIN_ONLY_NONUS_UNVERIFIED"
        or raw.get("existing_0bv_six_readings_kept") is not True
        or raw.get("sources")!=sources
        or type(extra) is not list or len(extra)!=6):
        raise ValueError("WF0BW_INVALID_LONG_READING_SOURCE")
    previous={row["id"] for row in load_fantasy_six()[1]}
    seen=set()
    texts={}
    for key in sources:
        text=Path(files[key]).read_bytes().decode("utf-8-sig")
        texts[key]=text.replace("\r\n","\n").replace("\r","\n")
    for item in extra:
        key=item.get("source_key")
        if (key not in sources or item.get("id") in previous|seen
            or item.get("work")!=sources[key]["work"]
            or type(item.get("original")) is not str
            or not 1000<=len(item["original"])<=4000
            or type(item.get("original_source_start")) is not int
            or type(item.get("original_source_end")) is not int
            or item["original_source_start"]<0
            or item["original_source_end"]!=(
                item["original_source_start"]+len(item["original"]))
            or texts[key][item["original_source_start"]:item["original_source_end"]]
               !=item["original"]
            or type(item.get("annotation")) is not list
            or len(item["annotation"])!=3
            or any(type(note) is not str or len(note)<80 for note in item["annotation"])
            or type(item.get("reflection")) is not str or len(item["reflection"])<150
            or not 200<=len(reading_text(item,sources[key]))<=5000):
            raise ValueError("WF0BW_SOURCE_EXCERPT_NOT_WHOLE_OR_NOT_CONTIGUOUS")
        seen.add(item["id"])
    if {key:sum(item["source_key"]==key for item in extra) for key in sources}!={k:2 for k in sources}:
        raise ValueError("WF0BW_BOOK_DIVERSITY_CHANGED")
    verify_fantasy_books(files,sources,extra)
    return extra


def load_next_fantasy(files:dict[str,Path])->tuple[dict,list[dict]]:
    """Six authentic new readings; reuse the existing source-aware Xuehai path."""
    data=json.loads(NEXT_FANTASY.read_text("utf8"))
    sources,items=data.get("sources"),data.get("items")
    if (data.get("format")!="wf.literary-reading.original-annotation-reflection.v1"
        or data.get("literary_gain_proven") is not False
        or data.get("independently_reviewed") is not False
        or data.get("source_scope")!="USA_PUBLIC_DOMAIN_ONLY_NONUS_UNVERIFIED"
        or type(sources) is not dict or set(sources)!={"hx","dd","zb"}
        or type(items) is not list or len(items)!=6
        or set(files)!=set(sources)):
        raise ValueError("WF0BX_INVALID_NEW_FANTASY_READINGS")
    previous={x["id"] for x in load_fantasy_six()[1]}
    previous.update(x["id"] for x in json.loads(FANTASY_LONG.read_text("utf8"))["items"])
    seen=set()
    texts={}
    for key,source in sources.items():
        original=Path(files[key]).read_bytes()
        actual=sha1(b"blob "+str(len(original)).encode("ascii")+b"\0"+original).hexdigest()
        if (len(original)!=source["source_size_bytes"]
            or actual!=source["source_blob_sha1"]):
            raise ValueError("WF0BX_PINNED_BOOK_CHANGED_"+key)
        texts[key]=original.decode("utf-8-sig").replace("\r\n","\n").replace("\r","\n")
    for row in items:
        key=row.get("source_key")
        if (key not in sources or row.get("id") in previous|seen
            or row.get("work")!=sources[key]["work"]
            or type(row.get("original")) is not str
            or not 750<=len(row["original"])<=2500
            or type(row.get("original_source_start")) is not int
            or type(row.get("original_source_end")) is not int
            or row["original_source_start"]<0
            or row["original_source_end"]!=row["original_source_start"]+len(row["original"])
            or texts[key][row["original_source_start"]:row["original_source_end"]]
               !=row["original"]
            or type(row.get("annotation")) is not list
            or len(row["annotation"])!=3
            or any(type(note) is not str or len(note)<75 for note in row["annotation"])
            or type(row.get("reflection")) is not str
            or len(row["reflection"])<150
            or not 200<=len(reading_text(row,sources[key]))<=5000):
            raise ValueError("WF0BX_COMPLETE_SOURCE_OR_READING_CHANGED")
        seen.add(row["id"])
    if {key:sum(item["source_key"]==key for item in items)
        for key in sources}!={key:2 for key in sources}:
        raise ValueError("WF0BX_TWO_READINGS_PER_BOOK_REQUIRED")
    return sources,items


def stage_with_fantasy_six(db_path:Path,files:dict[str,Path],
                           fantasy_files:dict[str,Path],long_readings:bool=False,
                           new_fantasy_files:dict[str,Path]|None=None)->dict:
    """One isolated Xuehai: retain old literary readings, then add new genuine prose."""
    stage_with_all_original_24(db_path,files)
    sources,items=load_fantasy_six()
    verify_fantasy_books(fantasy_files,sources,items)
    extra=load_fantasy_long(sources,fantasy_files) if long_readings else []
    fresh_sources,fresh=(load_next_fantasy(new_fantasy_files)
                         if new_fantasy_files is not None else ({},[]))
    sources={**sources,**fresh_sources}
    items=items+extra+fresh
    db=WriterForgeDB(db_path)
    rt=RuntimeEngine();rt.enter_learn()
    store=XuehaiStore(db,rt)
    try:
        parent=db.conn.execute(
            "SELECT id FROM snapshots WHERE note=? AND status='published'",
            (REMAINING_ORIGINAL_NOTE,),
        ).fetchone()
        if parent is None:
            raise RuntimeError("WF0BV_PREVIOUS_96_ENTRIES_NOT_PUBLISHED")
        sid=store.create_staging_snapshot(
            parent_id=parent["id"],note=(NEXT_FANTASY_NOTE if fresh
                                            else FANTASY_LONG_NOTE if long_readings
                                            else FANTASY_NOTE))
        for item in items:
            src=sources[item["source_key"]]
            store.add_entry(
                sid,work_id="gitenberg-fantasy-"+item["source_key"],
                text=reading_text(item,src),
                library_class="古典神魔奇幻原文＋批注＋心得",
                culture="中国",genre="神魔志怪古代小说",
                source_role=ROLE,function=item["topic"],
                effect=item["title"],method_cluster=item["id"],
                reuse_policy="read_reflect_not_copy",
            )
        store.publish(sid)
        rt.exit();rt.enter_write(sid)
        rows=db.conn.execute(
            "SELECT id,method_cluster FROM xuehai_entries "
            "WHERE snapshot_id=? AND source_role=?",
            (sid,ROLE),
        ).fetchall()
        cluster_to_id={r["method_cluster"]:r["id"] for r in rows}
        if len(rows)!=len(items) or set(cluster_to_id)!={i["id"] for i in items}:
            raise RuntimeError("WF0BV_SIX_FANTASY_READINGS_MISSING")
        for item in items:
            full=store.read_literary_reading(cluster_to_id[item["id"]])
            if (full["original"]!=item["original"]
                or full["reflection"]!=item["reflection"]
                or len(full["annotations"])!=3
                or any(n not in full["annotations"][i]
                       for i,n in enumerate(item["annotation"]))):
                raise RuntimeError("WF0BV_FANTASY_THREE_PART_READBACK_NOT_FULL")
        roles=("original_complete_scene_unreviewed",
               "public_domain_continuous_detail_prose_unreviewed",
               ROLE,ORIGINAL_ROLE)
        counts=dict(db.conn.execute(
            "SELECT source_role,COUNT(*) FROM xuehai_entries "
            "WHERE source_role IN (?,?,?,?) GROUP BY source_role",roles
        ).fetchall())
        expected=dict(zip(roles,(24,24,30+len(extra)+len(fresh),24)))
        method_count=db.conn.execute(
            "SELECT COUNT(*) FROM xuehai_method_cards").fetchone()[0]
        if counts!=expected or method_count!=0:
            raise RuntimeError("WF0BV_LOST_PREVIOUS_MATERIAL_"+str(counts))
        return {
            "status":("SIX_FANTASY_CLASSICS_EIGHTEEN_COMPLETE_READINGS" if fresh
                      else "THREE_FANTASY_CLASSICS_TWELVE_COMPLETE_READINGS" if long_readings
                      else "THREE_REAL_FANTASY_CLASSICS_SIX_COMPLETE_READINGS"),
            "new_books":len(sources),"new_complete_fantasy_readings":len(items),
            "previous_fantasy_readings_preserved":len(items)-len(fresh) if fresh else (6 if long_readings else 0),
            "added_books":len(fresh_sources),"added_readings":len(fresh),
            "additional_long_readings":len(extra),
            "old_readings_preserved":48,
            "all_literary_content_entries":sum(counts.values()),
            "all_three_part_readings":48+len(items),
            "new_long_original_characters":sum(len(i["original"]) for i in extra),
            "new_fantasy_original_characters":sum(len(i["original"]) for i in items),
            "full_fantasy_readback":True,
            "source_editions_pin_verified":True,
            "model_calls":0,"method_cards":0,
            "database":"DISPOSABLE_ONLY",
            "literary_improvement_proven":False,
            "production_canon_changes":0,
        }
    finally:
        db.close()



# 0.CC content-only continuation: eight NEW original fantasy literary readings.
# Same Xuehai tables, source roles and published snapshot lineage; no new store.
CC_ORIGINAL_PACKS=(
    ROOT/"experiments/wf_0cc_four_distinct_original_fantasy_readings_A_20261029.json",
    ROOT/"experiments/wf_0cc_four_distinct_original_fantasy_readings_B_20261029.json",
)


def append_cc_original_eight(db_path:Path)->dict:
    """Append eight 原文＋批注＋心得 to an EXISTING disposable 114-entry Xuehai.

    This is content insertion/readback, NOT a writer model run or an automatic
    literary verdict. Caller stages the full 0.BX 114 first; never overwrite
    the source snapshot or touch formal Canon.
    """
    items=[]
    for file in CC_ORIGINAL_PACKS:
        pack=json.loads(file.read_text("utf8"))
        if (pack.get("format")!="wf.literary-reading.original-annotation-reflection.v1"
            or pack.get("origin","").find("Original")<0 and
                 pack.get("origin","").find("original")<0
            or pack.get("literary_gain_proven") is not False
            or pack.get("independently_reviewed") is not False
            or len(pack.get("items",[]))!=4):
            raise ValueError("WF0CC_NEW_LITERARY_PACK_INVALID")
        for row in pack["items"]:
            if (not row["id"].startswith("cc-")
                or type(row.get("original")) is not str
                or not 650<=len(row["original"])<=2400
                or type(row.get("annotation")) is not list
                or len(row["annotation"])!=3
                or any(type(x) is not str or len(x)<70 or "\n" in x
                       for x in row["annotation"])
                or type(row.get("reflection")) is not str
                or len(row["reflection"])<130
                or type(row.get("form")) is not str
                or type(row.get("topic")) is not str):
                raise ValueError("WF0CC_LITERARY_TEXT_OR_NOTES_INCOMPLETE")
            source={"url":(
                "https://github.com/66tyu55/WriterForge/blob/"
                "refactor-unified-scene-delivery-audit/"+
                file.relative_to(ROOT).as_posix())}
            whole=reading_text({**row,"chapter":"完整原创场景"},source)
            if not 200<=len(whole)<=4900:
                raise ValueError("WF0CC_FULL_READING_MUST_FIT_AUTHOR_CONTEXT")
            items.append((row,whole))
    if (len(items)!=8 or len({r["id"] for r,_ in items})!=8
        or len({r["form"] for r,_ in items})<7):
        raise ValueError("WF0CC_ORIGINAL_DISTINCT_READING_SET_REQUIRED")

    db=WriterForgeDB(db_path)
    rt=RuntimeEngine()
    try:
        store=XuehaiStore(db,rt)
        parent=store.latest_published()
        roles=("original_complete_scene_unreviewed",
               "public_domain_continuous_detail_prose_unreviewed",
               ROLE,ORIGINAL_ROLE)
        counts=dict(db.conn.execute(
            "SELECT source_role,COUNT(*) FROM xuehai_entries "
            "WHERE source_role IN (?,?,?,?) GROUP BY source_role",roles))
        if (parent is None or counts!=dict(zip(roles,(24,24,42,24)))):
            raise ValueError("WF0CC_OLD_114_CONTENT_MUST_BE_PRESERVED")
        rt.enter_learn()
        sid=store.create_staging_snapshot(
            parent_id=parent,note="WF0CC_EIGHT_DISTINCT_ORIGINAL_FULL_READINGS")
        inserted={}
        for row,whole in items:
            eid=store.add_entry(
                sid,work_id="wf-original-"+row["id"],
                text=whole,library_class="原创玄幻：原文＋批注＋心得",
                culture="中国",genre="玄幻／仙侠",
                source_role=ORIGINAL_ROLE,function=row["topic"],
                effect=row["title"],method_cluster=row["id"],
                reuse_policy="read_reflect_not_copy")
            inserted[row["id"]]=eid
        store.publish(sid)
        rt.exit()
        rt.enter_write(sid)
        for row,whole in items:
            full=store.read_literary_reading(inserted[row["id"]])
            if (full["original"]!=row["original"]
                or full["reflection"]!=row["reflection"]
                or len(full["annotations"])!=3
                or any(note not in full["annotations"][i]
                       for i,note in enumerate(row["annotation"]))
                or "【原文】" not in whole
                or "【批注】" not in whole
                or "【心得】" not in whole):
                raise RuntimeError("WF0CC_WHOLE_ORIGINAL_READING_READBACK_FAILED")
        now=dict(db.conn.execute(
            "SELECT source_role,COUNT(*) FROM xuehai_entries "
            "WHERE source_role IN (?,?,?,?) GROUP BY source_role",roles))
        methods=db.conn.execute(
            "SELECT COUNT(*) FROM xuehai_method_cards").fetchone()[0]
        if (now!=dict(zip(roles,(24,24,42,32))) or
            methods!=0 or
            db.conn.execute("SELECT COUNT(*) FROM accepted_prose").fetchone()[0]!=0):
            raise RuntimeError("WF0CC_OLD_CORPUS_OR_NO_METHOD_BOUNDARY_CHANGED")
        return {
            "status":"EIGHT_NEW_COMPLETE_ORIGINAL_FANTASY_READINGS_IN_EXISTING_XUEHAI",
            "new_original_full_readings":len(items),
            "new_original_full_prose_characters":sum(len(r["original"]) for r,_ in items),
            "new_specific_annotations":sum(len(r["annotation"]) for r,_ in items),
            "new_open_reflections":len(items),
            "reading_forms":list(dict.fromkeys(row["form"] for row,_ in items)),
            "old_literary_content_preserved":114,
            "old_three_part_readings_preserved":66,
            "all_literary_content_entries":sum(now.values()),
            "all_three_part_readings":now[ROLE]+now[ORIGINAL_ROLE],
            "all_original_and_notes_exact_readback":True,
            "existing_method_cards":methods,
            "new_paid_author_model_requests":0,
            "writer_literary_gain_proven":False,
            "separate_database_created":False,
            "r2_reads_or_writes":0,
            "canonical_fact_writes":0,
        }
    finally:
        rt.exit()
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
    p.add_argument("--original24",action="store_true",
                   help="read all 24 original and all 24 classical three-part studies")
    p.add_argument("--fantasy6",action="store_true",
                   help="append six authentic fantasy passages from three pinned public books")
    p.add_argument("--fantasy12",action="store_true",
                   help="also read six longer pinned source passages and whole chapters")
    p.add_argument("--fantasy18",action="store_true",
                   help="include three more distinct fantasy books, source-verified in same Xuehai")
    p.add_argument("--cc-original8",action="store_true",
                   help="append eight new complete original fantasy readings after existing 114")
    for key in ("fs","jh","lz","hx","dd","zb"):
        p.add_argument("--"+key,type=Path)
    args=p.parse_args()
    old_files={key:getattr(args,key) for key in ("xy","hl","sh")}
    if args.fantasy6 or args.fantasy12 or args.fantasy18:
        if sum((args.fantasy6,args.fantasy12,args.fantasy18))!=1:
            p.error("choose exactly one fantasy reading option")
        fantasy_files={key:getattr(args,key) for key in ("fs","jh","lz")}
        if any(v is None for v in fantasy_files.values()):
            p.error("fantasy readings require --fs --jh --lz")
        next_files={key:getattr(args,key) for key in ("hx","dd","zb")} if args.fantasy18 else None
        if next_files is not None and any(v is None for v in next_files.values()):
            p.error("--fantasy18 requires --hx --dd --zb")
        output=stage_with_fantasy_six(
            args.db,old_files,fantasy_files,
            long_readings=args.fantasy12 or args.fantasy18,
            new_fantasy_files=next_files)
    else:
        runner=(stage_with_all_original_24 if args.original24
                else stage_with_original_eight if args.original8
                else stage_all_24 if args.all24 else stage)
        output=runner(args.db,old_files)
    if args.cc_original8:
        if not args.fantasy18:
            p.error("--cc-original8 requires --fantasy18 to preserve all 114")
        old_114_status=output["status"]
        new_content=append_cc_original_eight(args.db)
        output.update(new_content)
        output["previous_114_stage_status"]=old_114_status
    print(json.dumps(output,ensure_ascii=False,indent=2,sort_keys=True))
