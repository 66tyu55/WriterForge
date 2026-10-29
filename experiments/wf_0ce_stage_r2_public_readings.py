"""0.CE: reuse the existing XuehaiStore and 122-entry disposable SQLite.

Four real, source-exact public-domain readings originated from the user's R2
and are already pinned into the dev branch. This only appends and READS those
four full 原文＋批注＋心得 in that same isolated DB. Zero R2 writes/models.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json
import sys

from writerforge import WriterForgeDB, RuntimeEngine
from writerforge.classics_catalog import CATALOG
from writerforge.xuehai import XuehaiStore
from experiments.wf_0br_stage_classical_readings import reading_text

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"experiments/wf_0ce_r2_public_classics_four_full_readings_20261029.json"
ROLE="classical_original_annotation_reflection"
ORIGINAL_ROLE="original_annotation_reflection"


def append_four(dbfile:Path):
    pack=json.loads(SOURCE.read_text("utf8"))
    rows=pack.get("items",[])
    if (pack.get("format")!="wf.0ce.r2-public-original-annotation-reflection.v1"
        or pack.get("original_r2_modified") is not False
        or pack.get("paid_model_api_calls")!=0
        or len(rows)!=4):
        raise ValueError("WF0CE_R2_PUBLIC_READING_PACK_INVALID")
    readings=[]
    for row in rows:
        book=CATALOG.get(row["work_key"])
        source=pack["sources"].get(row["work_key"])
        if (book is None or book.key not in ("laocanyouji","sanguo")
            or row["work"]!=book.title
            or source["source_git_blob_sha1"]!=book.git_blob_sha1
            or row["source_raw_sha256"]!=source["source_sha256"]
            or row["source_is_existing_r2_study_snapshot"] is not True
            or sha256(row["original"].encode("utf8")).hexdigest()!=row["original_sha256"]
            or len(row["annotation"])!=3
            or not all(isinstance(n,str) and len(n)>=70
                       for n in row["annotation"])
            or len(row["reflection"])<130):
            raise ValueError("WF0CE_PUBLIC_R2_SOURCE_OR_THREE_PARTS_CHANGED")
        original=reading_text(row,{"url":book.source_page})
        if not 200<len(original)<=5000:
            raise ValueError("WF0CE_ORIGINAL_COMPLETE_READING_BUDGET")
        readings.append((row,original))
    db=WriterForgeDB(dbfile)
    rt=RuntimeEngine()
    try:
        store=XuehaiStore(db,rt)
        old_count=db.conn.execute(
            "SELECT COUNT(*) FROM xuehai_entries "
            "WHERE source_role IN (?,?,?,?)",
            ("original_complete_scene_unreviewed",
             "public_domain_continuous_detail_prose_unreviewed",
             ROLE,ORIGINAL_ROLE)).fetchone()[0]
        parent=store.latest_published()
        if parent is None or old_count!=122:
            raise ValueError("WF0CE_MUST_PRESERVE_EXISTING_122_XUEHAI_ENTRIES")
        rt.enter_learn()
        sid=store.create_staging_snapshot(
            parent_id=parent,note="WF0CE_VERIFIED_REAL_R2_PUBLIC_CLASSICS_FOUR")
        ids={}
        for row,original in readings:
            ids[row["id"]]=store.add_entry(
                sid,work_id="gitenberg-r2-public-"+row["work_key"],
                text=original,library_class="公版原文＋贴句批注＋心得",
                culture="中国",genre="古典历史／晚清社会小说",
                source_role=ROLE,function=row["topic"],
                effect=row["title"],method_cluster=row["id"],
                reuse_policy="read_reflect_not_copy")
        store.publish(sid)
        rt.exit()
        rt.enter_write(sid)
        for row,_ in readings:
            got=store.read_literary_reading(ids[row["id"]])
            if (got["original"]!=row["original"]
                or got["reflection"]!=row["reflection"]
                or len(got["annotations"])!=3
                or any(note not in got["annotations"][i]
                       for i,note in enumerate(row["annotation"]))):
                raise RuntimeError("WF0CE_REAL_R2_SOURCE_EXACT_READBACK_FAILED")
        all_count=db.conn.execute(
            "SELECT COUNT(*) FROM xuehai_entries WHERE "
            "source_role IN (?,?,?,?)",
            ("original_complete_scene_unreviewed",
             "public_domain_continuous_detail_prose_unreviewed",
             ROLE,ORIGINAL_ROLE)).fetchone()[0]
        three_part=db.conn.execute(
            "SELECT COUNT(*) FROM xuehai_entries WHERE source_role IN (?,?)",
            (ROLE,ORIGINAL_ROLE)).fetchone()[0]
        if all_count!=126 or three_part!=78:
            raise RuntimeError("WF0CE_OLD_OR_NEW_LITERATURE_MISSING")
        return {
            "status":"FOUR_REAL_R2_PUBLIC_CLASSIC_LITERATURE_READINGS_STORED_IN_EXISTING_XUEHAI",
            "prior_contents":122,
            "prior_full_three_part_readings":74,
            "new_real_historical_contiguous_originals":4,
            "new_original_characters":sum(len(r["original"]) for r,_ in readings),
            "new_specific_annotations":12,
            "new_open_reflections":4,
            "contents_total":all_count,
            "full_three_part_readings_total":three_part,
            "four_exact_source_readbacks":True,
            "new_paid_model_calls":0,
            "private_r2_writes":0,
            "new_database_schema_or_store":False,
            "literary_gain_proven":False,
            "canon_writes":0,
        }
    finally:
        rt.exit()
        db.close()


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("USAGE: python -m experiments.wf_0ce_stage_r2_public_readings existing.sqlite")
    print(json.dumps(append_four(Path(sys.argv[1])),ensure_ascii=False,sort_keys=True))
