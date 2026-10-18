"""Disk-first WF corpus foundation. No language models.

Remote sync is a separate, explicit action. Queries run entirely on a
verified local immutable cache and a separately derived disk SQLite index.
The original is never edited, and source prose never reaches creative prompts.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import tempfile
import unicodedata
from pathlib import Path
from urllib.parse import quote

from .r2_storage import R2StudyVault, _digest, _sqlite_audit

SHA = re.compile(r"[0-9a-f]{64}\Z")
LIBRARY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
SCAN_CAP = 256
CACHE_KIB = 1024


class CorpusIndexError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise CorpusIndexError(message)


def clean(value):
    """Normalize for an INDEX KEY only; do not rewrite literary text."""
    require(isinstance(value, str), "CLEAN_TEXT_INVALID")
    t=unicodedata.normalize("NFKC", value).casefold()
    return "".join(c for c in t if
                   unicodedata.category(c) not in ("Cc","Cf") and not c.isspace())


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def gram_pairs(t):
    return set(t[i:i+2] for i in range(len(t)-1))


def root_of(cache, library, snapshot):
    require(isinstance(library,str) and LIBRARY.fullmatch(library),
            "CORPUS_LIBRARY_INVALID")
    require(isinstance(snapshot,str) and SHA.fullmatch(snapshot),
            "CORPUS_SNAPSHOT_INVALID")
    return Path(cache).resolve()/library/snapshot[:16]


def ro_db(path):
    conn=sqlite3.connect("file:"+quote(str(Path(path).resolve()),safe="/")+"?mode=ro",
                         uri=True,cached_statements=24)
    conn.row_factory=sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    conn.execute(f"PRAGMA cache_size=-{CACHE_KIB}")
    conn.execute("PRAGMA temp_store=FILE")
    return conn


def verify_cache(cache,library,snapshot):
    root=root_of(cache,library,snapshot)
    manifest=root/"manifest.json"
    require(manifest.is_file() and digest(manifest.read_bytes())==snapshot,
            "CORPUS_R2_MANIFEST_MISSING_OR_TAMPERED")
    doc=json.loads(manifest.read_bytes())
    files=doc.get("files")
    require(doc.get("library")==library and
            doc.get("format")=="writerforge.r2.xuehai.v1" and
            isinstance(files,dict) and "study.sqlite3" in files and
            len(files)<=14,"CORPUS_R2_MANIFEST_INVALID")
    for name,record in files.items():
        require(name in ("source.txt","study.sqlite3") or
                ("/" not in name and "\\" not in name and
                 name.endswith((".txt",".md",".json"))),
                "CORPUS_R2_FILE_NAME_INVALID")
        path=root/name
        require(path.is_file() and _digest(path)==(
                    record["sha256"],record["size"]),
                "CORPUS_R2_SOURCE_CHANGED")
    require(_sqlite_audit(root/"study.sqlite3")==doc.get("stats"),
            "CORPUS_R2_SQLITE_CHANGED")
    return root


def build_index(cache,library,snapshot):
    root=verify_cache(cache,library,snapshot)
    src=root/"study.sqlite3"
    source_sha=_digest(src)[0]
    source_size=src.stat().st_size
    source_mtime_ns=src.stat().st_mtime_ns
    dest=root/"corpus-index.sqlite3"
    if dest.exists():
        db=ro_db(dest)
        try:
            m=dict(db.execute("SELECT key,value FROM meta"))
            require(m.get("snapshot")==snapshot and
                    m.get("source_sha")==source_sha,
                    "CORPUS_EXISTING_INDEX_WRONG_SOURCE")
            return {"snapshot_sha256":snapshot,
                    "source_sha256":source_sha,
                    "total_units":int(m["total_units"]),
                    "unique_units":int(m["unique_units"]),
                    "already_indexed":True}
        finally:
            db.close()
    handle=tempfile.NamedTemporaryFile(
        prefix=".wf-corpus-",suffix=".sqlite3",dir=root,delete=False)
    temp=Path(handle.name)
    handle.close()
    db=None
    try:
        db=sqlite3.connect(temp)
        db.execute(f"PRAGMA cache_size=-{CACHE_KIB}")
        db.execute("PRAGMA temp_store=FILE")
        db.executescript("""
        CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE units(
            id INTEGER PRIMARY KEY,
            work_id TEXT NOT NULL,
            chapter INT NOT NULL, paragraph INT NOT NULL, sentence INT NOT NULL,
            normalized_sha TEXT NOT NULL, source_sha TEXT NOT NULL,
            normalized TEXT NOT NULL, duplicates INT NOT NULL DEFAULT 1,
            UNIQUE(work_id,normalized_sha));
        CREATE TABLE grams(
            gram TEXT NOT NULL, unit_id INT NOT NULL,
            PRIMARY KEY(gram,unit_id));
        """)
        count=0
        source_db=ro_db(src)
        try:
            cursor=source_db.execute(
                "SELECT work_id,chapter,paragraph,sentence,excerpt,source_sha256 "
                "FROM source_spans ORDER BY work_id,chapter,paragraph,sentence")
            for row in cursor:
                count+=1
                t=clean(row["excerpt"][:160])
                if len(t)<2: continue
                norm_sha=digest(t.encode("utf-8"))
                old=db.execute(
                    "SELECT id FROM units WHERE work_id=? AND normalized_sha=?",
                    (row["work_id"],norm_sha)).fetchone()
                if old:
                    db.execute("UPDATE units SET duplicates=duplicates+1 WHERE id=?",
                               (old[0],))
                else:
                    cur=db.execute(
                        "INSERT INTO units(work_id,chapter,paragraph,sentence,"
                        "normalized_sha,source_sha,normalized) "
                        "VALUES(?,?,?,?,?,?,?)",
                        (row["work_id"],row["chapter"],row["paragraph"],
                         row["sentence"],norm_sha,row["source_sha256"],t))
                    db.executemany(
                        "INSERT INTO grams(gram,unit_id) VALUES(?,?)",
                        ((g,cur.lastrowid) for g in gram_pairs(t)))
                if count%200==0:
                    db.commit()  # periodic flush; no in-memory book cache
            db.commit()
        finally:
            source_db.close()
        db.execute("CREATE INDEX gram_lookup ON grams(gram,unit_id)")
        total_unique=db.execute("SELECT COUNT(*) FROM units").fetchone()[0]
        for k,v in {"snapshot":snapshot,"source_sha":source_sha,
                    "source_size":str(source_size),
                    "source_mtime_ns":str(source_mtime_ns),
                    "total_units":str(count),"unique_units":str(total_unique),
                    "method":"NFKC+Unicode-control-filter+dedup+2gram-v1",
                    "literary_quality_verified":"false"}.items():
            db.execute("INSERT INTO meta VALUES(?,?)",(k,v))
        db.commit()
        require(db.execute("PRAGMA quick_check").fetchone()[0]=="ok",
                "CORPUS_NEW_INDEX_BAD")
        db.close()
        db=None
        require(not dest.exists(),"CORPUS_INDEX_RACE_REFUSE_OVERWRITE")
        os.replace(temp,dest)
        return {"snapshot_sha256":snapshot,"source_sha256":source_sha,
                "total_units":count,"unique_units":total_unique,
                "already_indexed":False}
    finally:
        if db is not None: db.close()
        if temp.exists(): temp.unlink()


def sync_r2(vault,*,library,snapshot,cache):
    require(isinstance(vault,R2StudyVault) and
            vault.config.bucket=="writerforge-private-library",
            "CORPUS_ONLY_VERIFIED_PRIVATE_R2")
    info=vault.restore(library=library,snapshot=snapshot,destination=cache)
    require(info.get("verified"),"CORPUS_R2_RESTORE_NOT_VERIFIED")
    result=build_index(cache,library,info["snapshot"])
    return {"format":"WF.corpus-sync.v1",**result,
            "remote_download_performed":not info["from_local_cache"],
            "model_calls":0,"literary_skills_learned":False}


def search_disk(cache,*,library,snapshot,terms,limit=6):
    """No R2 access or original sentences in the query result."""
    require(type(limit) is int and 1<=limit<=8,"CORPUS_LIMIT_INVALID")
    require(isinstance(terms,tuple) and 1<=len(terms)<=4,
            "CORPUS_TERMS_INVALID")
    needles=[]
    for term in terms:
        require(isinstance(term,str) and term==term.strip()
                and 2<=len(term)<=32 and all(ord(c)>=32 for c in term),
                "CORPUS_TERM_INVALID")
        n=clean(term)
        require(len(n)>=2,"CORPUS_TERM_TOO_SHORT")
        if n not in needles:needles.append(n)
    root=root_of(cache,library,snapshot)
    manifest=root/"manifest.json"
    # O(1)-sized manifest check; full blob SHA happens ONLY in sync/verify.
    require(manifest.is_file() and digest(manifest.read_bytes())==snapshot,
            "CORPUS_MANIFEST_CHANGED")
    path=root/"corpus-index.sqlite3"
    require(path.is_file(),"CORPUS_NOT_INDEXED_RUN_R2_SYNC")
    db=ro_db(path)
    try:
        m=dict(db.execute("SELECT key,value FROM meta"))
        source=root/"study.sqlite3"
        require(source.is_file(),"CORPUS_R2_SOURCE_MISSING")
        st=source.stat()
        require(m.get("snapshot")==snapshot and
                m.get("source_size")==str(st.st_size) and
                m.get("source_mtime_ns")==str(st.st_mtime_ns),
                "CORPUS_INDEX_SOURCE_CHANGED")
        # Here we rely on the full SHA/SQLite audit done at sync time.
        # A forensic integrity recheck must explicitly run verify_cache().
        results={}
        for needle in needles:
            for row in db.execute(
                "SELECT u.id,u.work_id,u.chapter,u.paragraph,u.sentence,"
                "u.source_sha,u.normalized,u.duplicates "
                "FROM grams g JOIN units u ON u.id=g.unit_id "
                "WHERE g.gram=? ORDER BY u.id LIMIT ?",
                (needle[:2],SCAN_CAP)):
                if needle not in row["normalized"]: continue
                key=row["id"]
                if key not in results:
                    results[key]={
                        "work_id":row["work_id"],
                        "location":[row["chapter"],row["paragraph"],row["sentence"]],
                        "source_unit_sha256":row["source_sha"],
                        "duplicate_count":row["duplicates"],
                        "terms_matched":[],
                    }
                results[key]["terms_matched"].append(needle)
        ranked=sorted(results.values(),key=lambda x:(
            -len(x["terms_matched"]),x["work_id"],x["location"]))[:limit]
        return {"format":"WF.corpus-verify-comparison.v1",
                "snapshot_sha256":snapshot,"library":library,
                "query_terms":needles,"matches":ranked,"match_count":len(ranked),
                "network_calls":0,"model_calls":0,
                "source_prose_sent_to_writer":False,
                "unverified_lexical_comparison_only":True,
                "result_completeness_not_guaranteed":True,
                "per_term_shortlist_cap":SCAN_CAP,
                "full_sha_verified_at_sync_not_on_each_lookup":True,
                "per_lookup_cache_check":"manifest_sha_and_source_file_stat"}
    finally:
        db.close()
