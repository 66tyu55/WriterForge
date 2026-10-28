"""0.BQ: put REAL COMPLETE original literary scenes into existing Xuehai.

This is CONTENT acquisition, not method cards, automated literary grading,
model training or human-quality certification. Two narrative packs contain
24 complete original 350-420 character scenes across many detail domains.
The staging database is isolated. No production DB/Canon/R2 is touched.

Source study uses OriginalStudy on each genuine complete source scene.
The added full-scene Xuehai entry retains every character (not an 80-char
tip). Normal Xuehai retrieval keeps its existing 80-char anti-copy summary,
but the complete SOURCE REMAINS available in the database and repo JSON.
"""
from __future__ import annotations

import argparse
from difflib import SequenceMatcher
from hashlib import sha256
import json
from pathlib import Path

from writerforge import WriterForgeDB, RuntimeEngine, OriginalStudy, XuehaiStore
from writerforge.xuehai import Query

ROOT=Path(__file__).resolve().parents[1]
CORPUS_FILES={
    "A":ROOT/"experiments/wf_0bq_full_literary_detail_corpus_A_20261028.json",
    "B":ROOT/"experiments/wf_0bq_full_literary_detail_corpus_B_20261028.json",
}
SOURCE_COMMITS={
    "A":"a8c1a25f7f70d97ad57acc31280541d1c9150424",
    "B":"67b1e3c4922d90bb05699acb457e16db2390adda",
}
EXPECTED_PACK_COUNTS={"A":10,"B":14}
ORIGINAL_ROLE="original_complete_scene_unreviewed"
WORK_PREFIX="wf0bq-original-20261028-"
MAX_TOTAL_PROSE_CHARS=30_000
MIN_PROSE_CHARS=340
MAX_PROSE_CHARS=850
MAX_CORPUS_ITEMS=32
RESULT_FORMAT="wf.0bq-original-detail-prose-actual-xuehai-staging.v1"


def _canonical(value:dict)->bytes:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode("utf8")


def validate_corpus()->tuple[list[dict],dict]:
    """Validate content scope, not *pretend* to validate literary quality."""
    found=[]
    source_hashes={}
    for pack_id,path in CORPUS_FILES.items():
        raw=path.read_bytes()
        if len(raw)>75_000:
            raise ValueError("WF0BQ_CORPUS_SOURCE_TOO_LARGE")
        obj=json.loads(raw.decode("utf8"))
        for key,val in {
            "format":"wf.0bq.original-prose-detail-corpus.v1",
            "pack":pack_id,
            "corpus_role":"FULL_ORIGINAL_PROSE_NOT_METHOD_TIPS",
            "status":"ORIGINAL_AUTHOR_DRAFTS_EDITORIAL_UNVERIFIED",
            "text_origin":"NEW_ORIGINAL_LITERARY_PROSE_GENERATED_FOR_WF_CORPUS_NOT_EXCERPTS_FROM_OTHER_NOVELS",
            "model_inference_used_for_writerforge":False,
            "model_acted_as_author_in_this_chat":True,
            "independent_literary_reader_rating":None,
            "production_canon_writes":0,
            "private_r2_reads":0,
        }.items():
            if obj.get(key)!=val:
                raise ValueError("WF0BQ_FALSE_CORPUS_CONTENT_OR_QUALITY_CLAIM")
        items=obj.get("items")
        if type(items) is not list or len(items)!=EXPECTED_PACK_COUNTS[pack_id]:
            raise ValueError("WF0BQ_CORPUS_PACK_SIZE_INVALID")
        source_hashes[pack_id]=sha256(raw).hexdigest()
        for item in items:
            if type(item) is not dict or set(item)!={
                "id","title","genre","subgenre","scene_type",
                "narrative_mode","detail_dimensions","prose",
                "source_kind","author_accepted",
            }:
                raise ValueError("WF0BQ_CORPUS_ITEM_SCHEMA_INVALID")
            prose=item["prose"]
            if (type(prose) is not str or not
                MIN_PROSE_CHARS<=len(prose)<=MAX_PROSE_CHARS or
                len(prose.split("\n"))<3 or
                type(item["detail_dimensions"]) is not list or
                not 4<=len(item["detail_dimensions"])<=7 or
                len(set(item["detail_dimensions"]))!=len(item["detail_dimensions"]) or
                item["source_kind"]!="WF_ORIGINAL_WRITING_DEMONSTRATION" or
                item["author_accepted"] is not False or
                any(type(item[k]) is not str or not item[k].strip() or
                    len(item[k])>70 for k in (
                        "id","title","genre","subgenre","scene_type","narrative_mode")) or
                len(item["id"])>48 or
                "\x00" in prose):
                raise ValueError("WF0BQ_CORPUS_LACKS_COMPLETE_DIVERSE_PROSE")
            if not item["id"].startswith(f"bq-{len(found)+1:02d}-"):
                raise ValueError("WF0BQ_CORPUS_ORDER_OR_IDS_CHANGED")
            found.append({**item,"pack":pack_id})
    if (len(found)!=24 or len(found)>MAX_CORPUS_ITEMS or
        sum(len(item["prose"]) for item in found)>MAX_TOTAL_PROSE_CHARS):
        raise ValueError("WF0BQ_CORPUS_TOTAL_UNBOUNDED")
    ids=[v["id"] for v in found]
    all_text=[v["prose"] for v in found]
    if len(set(ids))!=24 or len(set(all_text))!=24:
        raise ValueError("WF0BQ_CORPUS_DUPLICATE_IDS_OR_TEXT")
    if (len(set(v["scene_type"] for v in found))<20 or
        len(set(v["subgenre"] for v in found))<15 or
        len(set(v["narrative_mode"] for v in found))<20 or
        len(set(v["genre"] for v in found))<3 or
        len(set(d for v in found for d in v["detail_dimensions"]))<45):
        raise ValueError("WF0BQ_CORPUS_CRAFT_OR_GENRE_NOT_DIVERSE")
    # The same exact prose under different labels is not literary diversity.
    # Only check the small pre-registered batch; do not do quadratic work at scale.
    texts=["".join(v["prose"].split()) for v in found]
    for i in range(len(texts)):
        for j in range(i+1,len(texts)):
            if SequenceMatcher(None,texts[i],texts[j],autojunk=True).ratio()>0.73:
                raise ValueError("WF0BQ_CORPUS_NEAR_DUPLICATE_SCENES")
    return found,source_hashes


def stage_full_detail_prose(*,db_path:Path)->dict:
    """Actual OriginalStudy source READ and complete Xuehai prose STAGING.

    Create a fresh DB only. Source paragraphs are *not* made into P0
    method cards; they are *long prose texts* with diverse narration.
    """
    db_path=Path(db_path)
    if db_path.exists():
        raise FileExistsError("WF0BQ_REFUSE_EXISTING_OR_PRODUCTION_DB")
    entries,source_hashes=validate_corpus()
    db_path.parent.mkdir(parents=True,exist_ok=True)
    db=WriterForgeDB(db_path)
    rt=RuntimeEngine();rt.enter_learn()
    store=XuehaiStore(db,rt)
    try:
        source_spans=0
        chapter_sources=[]
        for item in entries:
            work_id=WORK_PREFIX+item["id"]
            body="第1回 "+item["title"]+"\n\n"+item["prose"]+"\n"
            uri=("https://github.com/66tyu55/WriterForge/blob/"
                 +SOURCE_COMMITS[item["pack"]]+"/experiments/"
                 +CORPUS_FILES[item["pack"]].name)
            receipt=OriginalStudy(db,rt).ingest(
                body,work_id=work_id,
                title="WF原创完整场景（未作独立文学审阅）·"+item["title"],
                source_uri=uri,require_hundred=False,
                expected_count=1,max_chapters=1,
            )
            if receipt["studied_chapters"]!=1 or not receipt["studied_units"]:
                raise RuntimeError("WF0BQ_FULL_PROSE_ORIGINAL_STUDY_FAILED")
            source_spans+=receipt["studied_units"]
            chapter_sources.append({
                "id":item["id"],"work_id":work_id,
                "source_sha256":receipt["source_sha256"],
                "chapter_count":receipt["studied_chapters"],
                "source_spans":receipt["studied_units"],
            })
        parent=store.latest_published()
        snapshot=store.create_staging_snapshot(
            parent_id=parent,
            note="WF0BQ_NEW_ORIGINAL_24_WHOLE_PROSE_SCENES_UNREVIEWED_STAGING")
        checks=[]
        for item in entries:
            eid=store.add_entry(
                snapshot,
                work_id=WORK_PREFIX+item["id"],
                text=item["prose"],chapter=1,
                paragraph=None,sentence=None,
                library_class="完整原创小说场景原文·待独立文学评审",
                culture="中国",genre=item["genre"],
                source_role=ORIGINAL_ROLE,
                function=item["scene_type"],
                effect=item["narrative_mode"],
                method_cluster=item["subgenre"],
                reuse_policy="study_original_structure_no_verbatim_copy",
            )
            check=db.conn.execute(
                "SELECT text,source_hash,snapshot_id FROM xuehai_entries WHERE id=?",
                (eid,),
            ).fetchone()
            expected=sha256((WORK_PREFIX+item["id"]+"|"+
                             " ".join(item["prose"].split()).strip()).encode("utf8")
                             ).hexdigest()
            if (check["text"]!=item["prose"] or
                check["source_hash"]!=expected or
                check["snapshot_id"]!=snapshot):
                raise RuntimeError("WF0BQ_SOURCE_PROSE_TRUNCATED_OR_CORRUPTED")
            checks.append({
                "id":item["id"],"entry_id":eid,"work_id":WORK_PREFIX+item["id"],
                "genre":item["genre"],"scene_type":item["scene_type"],
                "subgenre":item["subgenre"],"narrative_mode":item["narrative_mode"],
                "prose_chars":len(item["prose"]),
                "prose_sha256":sha256(item["prose"].encode("utf8")).hexdigest(),
                "full_text_saved_not_80_char_tip":True,
            })
        stored=db.conn.execute(
            "SELECT COUNT(*),SUM(LENGTH(text)) FROM xuehai_entries WHERE snapshot_id=?",
            (snapshot,),
        ).fetchone()
        if (stored[0]!=24 or stored[1]!=sum(len(item["prose"]) for item in entries)
            or db.conn.execute(
                "SELECT COUNT(*) FROM xuehai_method_cards").fetchone()[0]!=0
            or db.conn.execute("SELECT status FROM snapshots WHERE id=?",
                               (snapshot,)).fetchone()["status"]!="staging"):
            raise RuntimeError("WF0BQ_FULL_TEXT_STAGING_VERIFICATION_FAILED")
        result={
            "format":RESULT_FORMAT,
            "status":"24_FULL_ORIGINAL_PROSE_IN_REAL_XUEHAI_STAGING_ONLY",
            "source_pack_sha256":source_hashes,
            "complete_original_scene_texts":24,
            "actual_original_studied_chapters_in_isolated_db":24,
            "actual_original_structural_source_spans":source_spans,
            "full_prose_chars_saved":stored[1],
            "min_prose_chars":min(len(item["prose"]) for item in entries),
            "max_prose_chars":max(len(item["prose"]) for item in entries),
            "distinct_scene_types":len(set(item["scene_type"] for item in entries)),
            "distinct_subgenres":len(set(item["subgenre"] for item in entries)),
            "distinct_narrative_modes":len(set(item["narrative_mode"] for item in entries)),
            "distinct_genres":sorted(set(item["genre"] for item in entries)),
            "distinct_detail_dimensions":len(set(
                d for item in entries for d in item["detail_dimensions"])),
            "source_parent_published_snapshot_in_disposable_db":parent,
            "whole_prose_staging_snapshot":snapshot,
            "whole_prose_snapshot_status":"staging",
            "published_full_prose_in_production":0,
            "third_party_modern_novels_ingested":0,
            "new_method_cards":0,
            "new_model_provider_requests":0,
            "private_r2_reads_or_writes":0,
            "production_canon_writes":0,
            "author_accepted":False,
            "literary_quality_improvement_proven":False,
            "entries":checks,
        }
        return result
    finally:
        db.close()


def verify_isolated_retrieval(db_path:Path,*,publish_in_isolated_db:bool=False)->dict:
    """Demonstrate true content lookup, never publish a production database."""
    db=WriterForgeDB(db_path)
    rt=RuntimeEngine();rt.enter_learn()
    x=XuehaiStore(db,rt)
    try:
        row=db.conn.execute(
            "SELECT id,status FROM snapshots WHERE note=?",
            ("WF0BQ_NEW_ORIGINAL_24_WHOLE_PROSE_SCENES_UNREVIEWED_STAGING",),
        ).fetchone()
        if row is None:
            raise ValueError("WF0BQ_ISOLATED_STAGING_NOT_FOUND")
        sid=row["id"]
        if publish_in_isolated_db:
            x.publish(sid)
        elif row["status"]!="published":
            return {"status":"STAGING_BLOCKED_FROM_WRITE","snapshot_id":sid,
                    "published_for_real_user":False}
        rt.exit()
        rt.enter_write(sid)
        samples={}
        for genre,kind,term in (
            ("玄幻","炼丹","药泥"),
            ("武侠","近身斗法","枪"),
            ("志怪","志怪接触","祠堂"),
            ("玄幻","宗门政治","药签"),
            ("玄幻","制符失败","符纸"),
        ):
            items=x.query(Query(
                genre=genre,function=kind,
                source_role=ORIGINAL_ROLE,
                text_terms=(term,),limit=2,max_per_work=1))
            if not items:
                raise RuntimeError("WF0BQ_FULL_PROSE_RETRIEVAL_FAILED")
            entry_id=items[0]["entry_id"]
            row=db.conn.execute(
                "SELECT text FROM xuehai_entries WHERE id=?",
                (entry_id,)).fetchone()
            if len(row["text"])<MIN_PROSE_CHARS:
                raise RuntimeError("WF0BQ_STORED_ONLY_A_SHORT_TIP")
            samples[kind]={
                "entry_id":entry_id,
                "genre":genre,
                "stored_full_prose_chars":len(row["text"]),
                "returned_summary_chars":len(items[0]["evidence_excerpt"]),
                "full_prose_sha256":sha256(row["text"].encode("utf8")).hexdigest(),
                "still_not_an_independent_quality_rating":True,
            }
        return {"status":"ISOLATED_ONLY_5_SCENE_PROSE_QUERIES_GREEN",
                "verified":samples,
                "published_for_real_user":False,
                "model_generated_or_literary_evaluated":False}
    finally:
        db.close()


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--db",type=Path,required=True)
    parser.add_argument("--demonstrate-isolated-query",action="store_true")
    args=parser.parse_args()
    result=stage_full_detail_prose(db_path=args.db)
    if args.demonstrate_isolated_query:
        result["isolated_read_demo"]=verify_isolated_retrieval(
            args.db,publish_in_isolated_db=True)
    print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
