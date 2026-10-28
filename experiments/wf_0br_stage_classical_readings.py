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
from experiments.wf_0bq_stage_original_full_detail_prose import stage_full_detail_prose

ROOT=Path(__file__).resolve().parents[1]
CORPUS=ROOT/"experiments/wf_0br_classical_original_annotation_reflection_20261028.json"
ROLE="classical_original_annotation_reflection"
NOTE="WF0BR_SIX_CLASSICS_WITH_ORIGINAL_ANNOTATION_REFLECTION"


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
    """Create ONE isolated 学海 containing 24 original + six classic readings."""
    db_path=Path(db_path)
    if db_path.exists():
        raise FileExistsError("WF0BR_REFUSE_OVERWRITE_DATABASE")
    sources,rows=load_readings()
    read_source_bytes(files,sources,rows)
    stage_full_detail_prose(db_path=db_path)
    db=WriterForgeDB(db_path)
    rt=RuntimeEngine();rt.enter_learn()
    store=XuehaiStore(db,rt)
    try:
        root=db.conn.execute(
            "SELECT id FROM snapshots WHERE note=?",
            ("WF0BQ_NEW_ORIGINAL_24_WHOLE_PROSE_SCENES_UNREVIEWED_STAGING",),
        ).fetchone()
        if not root:
            raise RuntimeError("WF0BR_PREVIOUS_24_ORIGINAL_SCENES_MISSING")
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
            full=db.conn.execute(
                "SELECT text FROM xuehai_entries WHERE id=?",
                (result[0]["entry_id"],)
            ).fetchone()["text"]
            if not all(label in full for label in ("【原文】","【批注】","【心得】")):
                raise RuntimeError("WF0BR_READ_RETURNED_ONLY_SUMMARY")
            preview[term]={
                "entry_id":result[0]["entry_id"],
                "whole_entry_chars":len(full),
                "read_complete_three_part_text":True,
                "legacy_short_query_excerpt_chars":len(result[0]["evidence_excerpt"]),
            }
        old=db.conn.execute(
            "SELECT COUNT(*) FROM xuehai_entries WHERE source_role=?",
            ("original_complete_scene_unreviewed",),
        ).fetchone()[0]
        if old!=24:
            raise RuntimeError("WF0BR_LOST_PREVIOUS_FULL_PROSE")
        return {
            "status":"SIX_REAL_CLASSICAL_ORIGINAL_ANNOTATIONS_REFLECTIONS_STORED",
            "books":3,"annotated_classic_entries":6,
            "original_prose_scenes_kept":old,
            "total_content_entries":old+len(entries),
            "original_classic_chars":sum(x["original_chars"] for x in entries),
            "distinct_reading_topics":len({x["topic"] for x in rows}),
            "database":"DISPOSABLE_ONLY",
            "model_calls":0,"actual_literary_gain_proven":False,
            "production_canon_changes":0,"external_review_claims":0,
            "read_examples":preview,"entries":entries,
        }
    finally:
        db.close()


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--db",type=Path,required=True)
    for key in ("xy","hl","sh"):
        p.add_argument("--"+key,type=Path,required=True)
    args=p.parse_args()
    print(json.dumps(stage(args.db,{key:getattr(args,key) for key in ("xy","hl","sh")}),
                     ensure_ascii=False,indent=2,sort_keys=True))
