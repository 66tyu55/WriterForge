"""0.BR REAL continuous public-domain classical prose + existing 24 original scenes.

CONTENT-first, one disposable WriterForgeDB/XuehaiStore, no new memory, no
method cards, no reviewer signature creation, no author model and no Canon.
Keep entire selected passage in Xuehai's existing text column. Never claim
that 80-character legacy retrieval preview is the full learning context.
Source bytes are downloaded only from three explicitly pinned public files.
"""
from __future__ import annotations

import argparse
from hashlib import sha1, sha256
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

from writerforge import WriterForgeDB, RuntimeEngine, XuehaiStore
from writerforge.xuehai import Query

from experiments.wf_0bq_stage_original_full_detail_prose import (
    stage_full_detail_prose, ORIGINAL_ROLE, MIN_PROSE_CHARS,
)

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "experiments/wf_0br_three_classics_contiguous_prose_details_20261028.json"
PUBLIC_CLASSIC_ROLE = "public_domain_continuous_detail_prose_unreviewed"
STAGING_NOTE = "WF0BQ_NEW_ORIGINAL_24_WHOLE_PROSE_SCENES_UNREVIEWED_STAGING"
MIN_EXCERPT = 280
MAX_EXCERPT = 650
MAX_PUBLIC_SOURCE_BYTES = 3_000_000
EXPECTED_WORK_IDS = {23863, 23962, 24264}
EXPECTED_EXCERPTS_PER_WORK = 8
EXPECTED_TOTAL_EXCERPTS = 24
EXPECTED_TOTAL_CHARS = 10626


def _work_id(book: dict) -> str:
    return "gitenberg-original-%s-%s" % (
        book["gutenberg_id"], book["source_commit"][:12])


def load_curated_classical_texts(path:Path=CORPUS)->dict:
    """Literary texts are immutable selected *source passages*, not instructions."""
    raw=Path(path).read_bytes()
    if len(raw)>55_000:
        raise ValueError("WF0BR_UNBOUNDED_CLASSIC_PROSE_PACK")
    corpus=json.loads(raw)
    exact={
        "format":"wf.0br.classical-continuous-literary-details.v1",
        "status":"REAL_PUBLIC_DOMAIN_SOURCE_EXCERPTS_CURATED_NOT_LITERARY_SCORED",
        "excerpt_count":EXPECTED_TOTAL_EXCERPTS,
        "source_count":3,
        "excerpt_total_characters":EXPECTED_TOTAL_CHARS,
        "material_generated_by_chatgpt":False,
        "selection_and_analysis_done_by_chatgpt":True,
        "independent_human_literary_review_completed":False,
        "literary_improvement_proven":False,
        "no_pay_model_calls":True,
        "no_modern_copyrighted_novels":True,
        "no_r2_private_access":True,
        "canonical_production_imports":0,
        "published_method_cards":0,
        "full_books_copied_into_writerforge_repo":False,
        "source_repository_files_pinned_to_exact_git_commits":True,
    }
    if type(corpus) is not dict or any(corpus.get(k)!=v for k,v in exact.items()):
        raise ValueError("WF0BR_SOURCE_IS_NOT_REAL_CURATED_PENDING_TEXT")
    sources=corpus.get("sources")
    excerpts=corpus.get("excerpts")
    if (type(sources) is not list or len(sources)!=3 or
        type(excerpts) is not list or len(excerpts)!=EXPECTED_TOTAL_EXCERPTS):
        raise ValueError("WF0BR_SOURCE_OR_PASSAGE_COUNT_INVALID")
    expected_books={
        "xiyou":(23962,"6a0cca862cda18eefa8a3264372893308432e926",
                 "b43d48dae12142a6e8707dcb68938d86beeb51e8",2264071),
        "honglou":(24264,"f86ffb9dd67165e3e17c29ab3ea3d29fd5d00d34",
                   "4f75f649a922cb1d3576b40e5ccd15baf367b594",2663312),
        "shuihu":(23863,"c87e4e172a2223559b25ada53345b94b2d20aaab",
                  "b8811e4ea9340b572f943842e131f2ada6b2032e",1631948),
    }
    if {b.get("key") for b in sources}!=set(expected_books):
        raise ValueError("WF0BR_SOURCE_BOOK_INVENTORY_CHANGED")
    for book in sources:
        expected=expected_books[book["key"]]
        page=book["gutenberg_id"]
        if (tuple(book.get(k) for k in (
             "gutenberg_id","source_commit",
             "source_git_blob_sha1","source_size_bytes"))!=expected or
            book.get("source_filename")!=f"{page}-0.txt" or
            book.get("source_repo")!=f"GITenberg/---_{page}" or
            book.get("source_uri")!=(
                f"https://raw.githubusercontent.com/GITenberg/---_{page}/"
                f"{expected[1]}/{page}-0.txt") or
            book.get("publisher_uri")!=f"https://www.gutenberg.org/ebooks/{page}"):
            raise ValueError("WF0BR_SOURCE_VERSION_CHANGED")
    counts={k:0 for k in expected_books}
    seen=set()
    texts=set()
    domains=set()
    total=0
    for item in excerpts:
        if type(item) is not dict or set(item)!={
            "id","work_key","chapter_number","chapter_title","detail_domain",
            "title","anchor","observed_literary_facets","reading_question",
            "normalized_source_start","normalized_source_end","excerpt",
            "source_role","publication_state","author_accepted",
        }:
            raise ValueError("WF0BR_EXCERPT_SCHEMA_OR_MISSING_REAL_TEXT")
        k=item["work_key"]
        text=item["excerpt"]
        if (k not in counts or item["id"] in seen or
            type(item["chapter_number"]) is not int or
            not 0<=item["chapter_number"]<=100 or
            type(item["normalized_source_start"]) is not int or
            type(item["normalized_source_end"]) is not int or
            item["normalized_source_start"]<0 or
            item["normalized_source_end"]<=item["normalized_source_start"] or
            type(text) is not str or not MIN_EXCERPT<=len(text)<=MAX_EXCERPT or
            text in texts or type(item["anchor"]) is not str or
            len(item["anchor"])<3 or
            item["anchor"] not in text or
            type(item["title"]) is not str or not item["title"] or
            type(item["detail_domain"]) is not str or not item["detail_domain"] or
            type(item["reading_question"]) is not str or
            len(item["reading_question"])<8 or
            item["source_role"]!="ORIGINAL_PUBLIC_DOMAIN_CHINESE_PROSE" or
            item["publication_state"]!="UNREVIEWED_LITERARY_READING_EXCERPT" or
            item["author_accepted"] is not False):
            raise ValueError("WF0BR_MISSING_FULL_DISTINCT_OR_VALID_TEXT")
        counts[k]+=1
        seen.add(item["id"])
        texts.add(text)
        domains.add(item["detail_domain"])
        total+=len(text)
    if (counts!={k:EXPECTED_EXCERPTS_PER_WORK for k in counts}
        or total!=EXPECTED_TOTAL_CHARS or len(domains)!=24):
        raise ValueError("WF0BR_PROSE_NOT_DIVERSE_OR_VOLUME_CHANGED")
    return corpus


def verify_pinned_files(corpus:dict,source_dir:Path)->dict[str,str]:
    """Actual byte hash AND exact excerpt location for three public originals."""
    result={}
    for book in corpus["sources"]:
        path=Path(source_dir)/book["source_filename"]
        raw=path.read_bytes()
        if (len(raw)!=book["source_size_bytes"] or
            len(raw)>MAX_PUBLIC_SOURCE_BYTES):
            raise ValueError("WF0BR_SOURCE_LENGTH_NOT_PINNED")
        git_blob=sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()
        if git_blob!=book["source_git_blob_sha1"]:
            raise ValueError("WF0BR_SOURCE_GIT_BLOB_SHA_MISMATCH")
        normalized=raw.decode("utf-8-sig").replace("\r\n","\n").replace("\r","\n")
        result[book["key"]]=normalized
    for item in corpus["excerpts"]:
        raw=result[item["work_key"]]
        begin,end=item["normalized_source_start"],item["normalized_source_end"]
        if raw[begin:end]!=item["excerpt"]:
            raise ValueError("WF0BR_SOURCE_EXCERPT_NOT_CONTIGUOUS")
        anchor_count=raw[begin:end].count(item["anchor"])
        if anchor_count<1:
            raise ValueError("WF0BR_SOURCE_ANCHOR_MISSING")
    return result


def download_only_three_pinned_public_sources(*,source_dir:Path)->dict:
    """No arbitrary URL, no R2, no modern books; refuse any existing files."""
    corpus=load_curated_classical_texts()
    root=Path(source_dir)
    root.mkdir(parents=True,exist_ok=True)
    saved={}
    for book in corpus["sources"]:
        out=root/book["source_filename"]
        if out.exists():
            raise FileExistsError("WF0BR_REFUSE_OVERWRITE_EXISTING_SOURCE")
        req=Request(book["source_uri"],headers={
            "User-Agent":"WriterForge-original-classical-literature-corpus/1"})
        with urlopen(req,timeout=45) as response:
            if response.geturl()!=book["source_uri"]:
                raise ValueError("WF0BR_SOURCE_REDIRECT_REJECTED")
            b=response.read(MAX_PUBLIC_SOURCE_BYTES+1)
        if len(b)>MAX_PUBLIC_SOURCE_BYTES:
            raise ValueError("WF0BR_PUBLIC_SOURCE_TOO_LARGE")
        h=sha1(b"blob "+str(len(b)).encode("ascii")+b"\0"+b).hexdigest()
        if len(b)!=book["source_size_bytes"] or h!=book["source_git_blob_sha1"]:
            raise ValueError("WF0BR_SOURCE_BYTES_NOT_PINNED")
        out.write_bytes(b)
        saved[book["key"]]={"git_blob_sha1":h,"actual_bytes":len(b)}
    verify_pinned_files(corpus,root)
    return {"format":"wf.0br.public-books-pinned.v1",
            "sources_verified":saved,"third_party_modern_novels":0,
            "paid_author_model_requests":0}


def add_classics_to_actual_xuehai(*,db_path:Path,source_dir:Path)->dict:
    """24 original complete scenes + 24 REAL classics in ONE Xuehai snapshot."""
    corpus=load_curated_classical_texts()
    actual_sources=verify_pinned_files(corpus,source_dir)
    original=stage_full_detail_prose(db_path=db_path)
    if (original["complete_original_scene_texts"]!=24 or
        original["whole_prose_snapshot_status"]!="staging"):
        raise RuntimeError("WF0BR_ORIGINAL_SCENES_NOT_ACTUALLY_IN_XUEHAI")
    sid=original["whole_prose_staging_snapshot"]
    db=WriterForgeDB(db_path)
    rt=RuntimeEngine()
    rt.enter_learn()
    store=XuehaiStore(db,rt)
    book_by_key={b["key"]:b for b in corpus["sources"]}
    receipts=[]
    try:
        status=db.conn.execute(
            "SELECT status FROM snapshots WHERE id=?",(sid,)
        ).fetchone()
        if not status or status["status"]!="staging":
            raise RuntimeError("WF0BR_NOT_WRITING_IN_ISOLATED_STAGING")
        for item in corpus["excerpts"]:
            book=book_by_key[item["work_key"]]
            raw=actual_sources[book["key"]]
            if item["excerpt"]!=raw[
                    item["normalized_source_start"]:item["normalized_source_end"]]:
                raise RuntimeError("WF0BR_CLASSIC_RAW_TEXT_CHANGED")
            work_id=_work_id(book)
            eid=store.add_entry(
                sid,work_id=work_id,text=item["excerpt"],
                chapter=item["chapter_number"],paragraph=None,sentence=None,
                library_class="原典连续细节原文·%s·未评审"%book["variant"],
                culture="中国",genre="古代白话",
                source_role=PUBLIC_CLASSIC_ROLE,
                function=item["detail_domain"],
                effect=item["observed_literary_facets"],
                method_cluster=item["work_key"]+"-"+item["detail_domain"],
                reuse_policy="reading_study_only_no_verbatim_imitation",
            )
            row=db.conn.execute(
                "SELECT text,source_hash FROM xuehai_entries WHERE id=?",
                (eid,)
            ).fetchone()
            if not row or row["text"]!=item["excerpt"]:
                raise RuntimeError("WF0BR_CLASSIC_FULL_PROSE_NOT_STORED")
            receipts.append({
                "excerpt_id":item["id"],
                "entry_id":eid,
                "work":book["title"],
                "work_id":work_id,
                "chapter":item["chapter_number"],
                "source_uri":book["source_uri"],
                "source_git_blob_sha1":book["source_git_blob_sha1"],
                "excerpt_sha256":sha256(item["excerpt"].encode("utf8")).hexdigest(),
                "excerpt_chars":len(item["excerpt"]),
                "source_char_range":[item["normalized_source_start"],
                                     item["normalized_source_end"]],
                "literary_domain":item["detail_domain"],
                "entire_excerpt_preserved_in_xuehai":True,
            })
        stored=db.conn.execute(
            """SELECT source_role,COUNT(*) AS c,SUM(LENGTH(text)) AS n
                 FROM xuehai_entries WHERE snapshot_id=?
                 AND source_role IN (?,?)
                 GROUP BY source_role""",
            (sid,ORIGINAL_ROLE,PUBLIC_CLASSIC_ROLE),
        ).fetchall()
        counts={r["source_role"]:(r["c"],r["n"]) for r in stored}
        if (counts.get(ORIGINAL_ROLE)!=(24,9208)
            or counts.get(PUBLIC_CLASSIC_ROLE)!=(24,EXPECTED_TOTAL_CHARS)
            or db.conn.execute(
                "SELECT COUNT(*) FROM xuehai_method_cards"
            ).fetchone()[0]!=0):
            raise RuntimeError("WF0BR_FULL_48_TEXTS_NOT_STORED_IN_ONE_XUEHAI")
        return {
            "format":"wf.0br.48-real-literary-texts-in-one-xuehai.v1",
            "status":"48_FULL_CONTIGUOUS_LITERARY_TEXTS_IN_ONE_ISOLATED_XUEHAI_STAGING",
            "source_books":[b["title"] for b in corpus["sources"]],
            "distinct_original_source_books":3,
            "existing_original_xuanhuan_scenes":counts[ORIGINAL_ROLE][0],
            "new_actual_classical_prose_passages":counts[PUBLIC_CLASSIC_ROLE][0],
            "total_complete_prose_passages":48,
            "original_prose_chars":counts[ORIGINAL_ROLE][1],
            "real_classical_prose_chars":counts[PUBLIC_CLASSIC_ROLE][1],
            "total_prose_chars":sum(n for _,n in counts.values()),
            "xuehai_staging_snapshot":sid,
            "xuehai_snapshot_status":"staging",
            "new_classic_method_cards":0,
            "real_literary_improvement_proven":False,
            "source_whole_books_copied_into_writerforge_repo":False,
            "actual_full_classic_chapters_studied":0,
            "new_paid_author_model_requests":0,
            "private_r2_access":0,
            "production_canon_writes":0,
            "production_published_scenes":0,
            "entries":receipts,
        }
    finally:
        db.close()


def read_real_literary_mix_in_isolated_xuehai(*,db_path:Path)->dict:
    """One-time isolated proof full text is retrievable; not a WRITE launch."""
    db=WriterForgeDB(db_path)
    rt=RuntimeEngine();rt.enter_learn()
    store=XuehaiStore(db,rt)
    try:
        row=db.conn.execute(
            "SELECT id,status FROM snapshots WHERE note=?",
            (STAGING_NOTE,),
        ).fetchone()
        if not row or row["status"]!="staging":
            raise ValueError("WF0BR_XUEHAI_STAGING_EXPECTED")
        store.publish(row["id"])
        rt.exit()
        rt.enter_write(row["id"])
        samples=(
            ("古代白话",PUBLIC_CLASSIC_ROLE,"山林活气","猴"),
            ("古代白话",PUBLIC_CLASSIC_ROLE,"餐桌礼法","茶"),
            ("古代白话",PUBLIC_CLASSIC_ROLE,"风雪进程","雪"),
            ("玄幻",ORIGINAL_ROLE,"炼丹","药"),
            ("武侠",ORIGINAL_ROLE,"近身斗法","枪"),
            ("志怪",ORIGINAL_ROLE,"志怪接触","祠"),
        )
        receipts=[]
        for genre,role,domain,term in samples:
            result=store.query(Query(
                genre=genre,source_role=role,function=domain,
                text_terms=(term,),limit=1,max_per_work=1))
            if not result:
                raise RuntimeError("WF0BR_REAL_MIXED_XUEHAI_RETRIEVAL_EMPTY_"+domain)
            entry_id=result[0]["entry_id"]
            row=db.conn.execute(
                "SELECT text,source_role FROM xuehai_entries WHERE id=?",
                (entry_id,),
            ).fetchone()
            if (not row or len(row["text"])<MIN_EXCERPT
                or row["source_role"]!=role):
                raise RuntimeError("WF0BR_FULL_SOURCE_TEXT_UNRETRIEVABLE")
            receipts.append({
                "genre":genre,"source_role":role,"detail_domain":domain,
                "entry_id":entry_id,
                "full_prose_chars_stored":len(row["text"]),
                "retrieval_excerpt_preview_chars":len(result[0]["evidence_excerpt"]),
                "full_prose_sha256":sha256(row["text"].encode("utf8")).hexdigest(),
            })
        return {
            "status":"SIX_ACTUAL_FULL_PROSE_QUERIES_FROM_MIXED_XUEHAI_GREEN",
            "literary_source_types":["24 original","24 public-domain classical"],
            "returned_full_prose_from_existing_sqlite":True,
            "legacy_retriever_still_restricts_preview_to_80_chars":True,
            "no_live_author_model_calls":True,
            "published_in_real_user_xuehai":False,
            "queries":receipts,
        }
    finally:
        db.close()


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--db",type=Path,required=True)
    p.add_argument("--source-dir",type=Path,required=True)
    p.add_argument("--download-pinned-public-sources",action="store_true")
    p.add_argument("--preview-within-disposable-db",action="store_true")
    args=p.parse_args()
    if args.download_pinned_public_sources:
        download_only_three_pinned_public_sources(source_dir=args.source_dir)
    result=add_classics_to_actual_xuehai(
        db_path=args.db,source_dir=args.source_dir)
    if args.preview_within_disposable_db:
        result["isolated_read_test"]=read_real_literary_mix_in_isolated_xuehai(
            db_path=args.db)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2))
