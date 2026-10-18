"""WriterForge V68: zero-model, bulk R2 inbox metadata and deferred SQL.

This code NEVER uploads/downloads R2 objects. Feed it R2 LIST metadata, then
feed a separately verified local/Railway temporary text file to index. The
original key and bytes remain unchanged; display numbers are catalog-only.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from urllib.parse import quote
import codecs
import os
import re
import sqlite3
import tempfile
import unicodedata

INBOX = "writerforge/v1/inbox/"
PRIVATE_READING = "writerforge/v1/private-reading/"
PRIVATE_FOLDERS = frozenset(("single-works", "仙侠", "历史", "科幻"))
MAX_RAW_BYTES = 256 * 1024 * 1024
CHUNK = 1024 * 1024
ALLOWED_TEXT = frozenset((".txt", ".md"))
ARCHIVE = frozenset((".zip", ".rar", ".7z"))
CAT = {
 "古典":"古典","古典小说":"古典","古典文学":"古典","名著":"古典",
 "玄幻":"玄幻","仙侠":"仙侠","修仙":"仙侠","科幻":"科幻",
 "科学幻想":"科幻","历史":"历史","历史小说":"历史",
 "奇幻":"奇幻","武侠":"武侠","都市":"都市","悬疑":"悬疑",
 "灵异":"灵异","言情":"言情","游戏":"游戏","军事":"军事",
 "竞技":"竞技","体育":"体育","轻小说":"轻小说",
}
CHAPTER = re.compile(r"^\s*(?:第[0-9零〇一二三四五六七八九十百千万两]{1,15}[章回卷节].*|序章|楔子|尾声|终章|番外(?:第.{1,12}[章回])?).{0,130}$")
SENTENCE = re.compile(r"(?<=[。！？!?；;])")

class BulkCorpusError(ValueError):
    pass

def require(value, code):
    if not value:
        raise BulkCorpusError(code)

def category_from_folder(folder):
    require(isinstance(folder,str) and bool(folder.strip()),"BULK_CATEGORY_INVALID")
    normalized = re.sub(r"^\s*\d{1,3}\s*[,，.．、_\-\s]*","",folder).strip()
    return CAT.get(normalized,"待分类")

def parse_key(key):
    """Both historic V68 inbox and actual R2 private-reading source prefixes.

    single-works is a storage folder, NOT a literary genre. Any nested
    chapter-file sets remain uncounted as independent novels until grouped.
    """
    require(isinstance(key,str) and len(key.encode("utf8"))<=1536,
            "BULK_KEY_INVALID")
    if key.startswith(PRIVATE_READING):
        parts=key[len(PRIVATE_READING):].split("/")
        require(len(parts)>=2 and parts[0] in PRIVATE_FOLDERS,
                "BULK_PRIVATE_FOLDER_OUT_OF_SCOPE")
        batch="private-reading"
        folder=parts[0]
        nested_genre=(category_from_folder(parts[1]) if
                      folder=="single-works" and len(parts)==3 else "待分类")
        category=(nested_genre if folder=="single-works" else folder)
        nested_source=(len(parts)>2 and not (
            folder=="single-works" and len(parts)==3 and
            nested_genre!="待分类"))
    elif key.startswith(INBOX):
        parts=key[len(INBOX):].split("/")
        require(len(parts)>=3, "BULK_INBOX_PATH_TOO_SHORT")
        batch,folder=parts[:2]
        require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}",batch),
                "BULK_BATCH_UNSAFE")
        category=category_from_folder(folder)
        nested_source=len(parts)>3
    else:
        raise BulkCorpusError("BULK_KEY_OUTSIDE_APPROVED_PREFIXES")
    require(all(p and p not in (".","..") and "\\\\" not in p and
                not any(ord(ch)<32 for ch in p) for p in parts),
            "BULK_KEY_UNSAFE_SEGMENTS")
    filename=parts[-1]
    ext=Path(filename).suffix.casefold()
    status=("RAW_ONLY_PENDING_SQL" if ext in ALLOWED_TEXT else
            "EPUB_PENDING_PARSER" if ext==".epub" else
            "ARCHIVE_NEEDS_LOCAL_EXTRACTION" if ext in ARCHIVE else
            "UNSUPPORTED_REVIEW")
    if nested_source and ext in ALLOWED_TEXT:
        status="GROUPED_FILES_NEED_ASSEMBLY"
    return dict(batch=batch,folder=folder,category=category,
                filename=filename,raw_title=Path(filename).stem,
                ext=ext,status=status)

def normalize_term(text):
    require(isinstance(text,str),"BULK_QUERY_TERM_INVALID")
    return "".join(ch for ch in unicodedata.normalize("NFKC",text).casefold()
                   if not ch.isspace() and unicodedata.category(ch)
                   not in ("Cc","Cf"))

class BulkCatalog:
    """Own stable virtual ordering, immutable object references, SHA book IDs."""
    def __init__(self,db_path):
        self.conn=sqlite3.connect(str(db_path))
        self.conn.row_factory=sqlite3.Row
        self.conn.execute("PRAGMA busy_timeout=3000")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript("""
          CREATE TABLE IF NOT EXISTS assets(
            object_key TEXT PRIMARY KEY,batch TEXT NOT NULL,
            category TEXT NOT NULL,folder TEXT NOT NULL,
            display_no INTEGER NOT NULL,filename TEXT NOT NULL,
            raw_title TEXT NOT NULL,ext TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,etag TEXT,status TEXT NOT NULL,
            sha256 TEXT,book_id TEXT,UNIQUE(category,display_no));
          CREATE INDEX IF NOT EXISTS assets_status ON assets(status,category);
          CREATE INDEX IF NOT EXISTS assets_book ON assets(book_id);
          CREATE TABLE IF NOT EXISTS books(
            book_id TEXT PRIMARY KEY,sha256 TEXT NOT NULL UNIQUE,
            size_bytes INTEGER NOT NULL,shard_name TEXT NOT NULL,
            parser_version TEXT NOT NULL,units INTEGER NOT NULL,
            chapters INTEGER NOT NULL,confidence TEXT NOT NULL);
        """)

    def close(self):
        self.conn.close()

    def ready_count(self):
        return self.conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]

    def register(self,records):
        """R2 LIST metadata only. NEVER writes/modifies original R2 names."""
        added=unchanged=0
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            for row in sorted(records,key=lambda r:r["key"]):
                key=row["key"]
                info=parse_key(key)
                size=row.get("size")
                require(type(size) is int and 0<=size<=10*1024**3,
                        "BULK_LIST_SIZE_INVALID")
                etag=row.get("etag")
                require(etag is None or
                        (isinstance(etag,str) and len(etag)<=256),
                        "BULK_ETAG_INVALID")
                old=self.conn.execute(
                    "SELECT size_bytes,etag FROM assets WHERE object_key=?",
                    (key,)).fetchone()
                if old:
                    require(old["size_bytes"]==size and
                            (old["etag"] is None or etag is None
                             or old["etag"]==etag),
                            "BULK_EXISTING_OBJECT_MUTATED_USE_NEW_KEY")
                    unchanged+=1
                    continue
                number=self.conn.execute(
                    "SELECT COALESCE(MAX(display_no),0)+1 FROM assets WHERE category=?",
                    (info["category"],)).fetchone()[0]
                self.conn.execute("""INSERT INTO assets
                 (object_key,batch,category,folder,display_no,filename,
                  raw_title,ext,size_bytes,etag,status)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                 (key,info["batch"],info["category"],info["folder"],
                  number,info["filename"],info["raw_title"],info["ext"],
                  size,etag,info["status"]))
                added+=1
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise
        return {"added":added,"unchanged":unchanged,
                "verified_book_count":self.ready_count(),
                "original_text_read":False,"r2_writes":0,"llm_calls":0}

    def summary(self):
        counts=self.conn.execute("""SELECT category,COUNT(*) AS objects,
          SUM(CASE WHEN status='INDEXED_LEXICAL_ONLY'
               THEN 1 ELSE 0 END) AS indexed
          FROM assets GROUP BY category ORDER BY category""").fetchall()
        return {"objects":self.conn.execute(
                    "SELECT COUNT(*) FROM assets").fetchone()[0],
                "distinct_indexed_books":self.ready_count(),
                "by_category":[dict(r) for r in counts],
                "literary_understanding_verified":False}

    def rows(self,category=None):
        sql=("SELECT category,display_no,filename,raw_title,object_key,"
             "status,size_bytes,book_id,sha256 FROM assets")
        args=()
        if category is not None:
            sql+=" WHERE category=?"
            args=(category,)
        return [dict(r) for r in self.conn.execute(
            sql+" ORDER BY category,display_no",args)]

    def _mark_duplicate(self,key,book_id,source_sha):
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            self.conn.execute("""UPDATE assets SET sha256=?,book_id=?,
              status='DUPLICATE_ALIAS' WHERE object_key=?""",
              (source_sha,book_id,key))
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise

    def index_text_file(self,key,source_path,shard_dir,*,encoding=None):
        """One source -> one immutable SHA-named SQLite, streaming by line.

        The caller, not this function, verifies/downloads a private R2 blob
        into an ephemeral path. EPUB/archives require separate safe parsers.
        """
        obj=self.conn.execute("SELECT * FROM assets WHERE object_key=?",
                              (key,)).fetchone()
        require(obj is not None and obj["ext"] in ALLOWED_TEXT,
                "BULK_TEXT_SOURCE_NOT_REGISTERED")
        source=Path(source_path)
        require(source.is_file() and source.stat().st_size==obj["size_bytes"]
                and 0<obj["size_bytes"]<=MAX_RAW_BYTES,
                "BULK_TEXT_SOURCE_SIZE_MISMATCH")
        hash_=sha256()
        with source.open("rb") as handle:
            while True:
                data=handle.read(CHUNK)
                if not data:break
                hash_.update(data)
        source_sha=hash_.hexdigest()
        require(obj["sha256"] is None or obj["sha256"]==source_sha,
                "BULK_REINDEX_SOURCE_CHANGED")
        book_id="b_"+source_sha[:32]
        shard_dir=Path(shard_dir)
        shard_dir.mkdir(parents=True,exist_ok=True)
        name=book_id+".sqlite3"
        target=shard_dir/name
        existing=self.conn.execute(
            "SELECT sha256,shard_name FROM books WHERE book_id=?",
            (book_id,)).fetchone()
        if existing:
            require(existing["sha256"]==source_sha and target.is_file(),
                    "BULK_EXISTING_SHARD_UNVERIFIED")
            with sqlite3.connect("file:"+quote(str(target.resolve()),safe="/")
                                 +"?mode=ro",uri=True) as con:
                identity=dict(con.execute("SELECT key,value FROM meta"))
                require(identity.get("source_sha256")==source_sha,
                        "BULK_EXISTING_SHARD_SHA_CHANGED")
            self._mark_duplicate(key,book_id,source_sha)
            return {"book_id":book_id,"duplicate_alias":True,
                    "source_sha256":source_sha,"index_exists":True}
        require(not target.exists(),"BULK_SHARD_COLLISION_REFUSE_OVERWRITE")
        if encoding is None:
            with source.open("rb") as handle: sample=handle.read(128*1024)
            if sample.startswith(codecs.BOM_UTF8):
                encoding="utf-8-sig"
            elif sample.startswith((codecs.BOM_UTF16_LE,codecs.BOM_UTF16_BE)):
                encoding="utf-16"
            else:
                try: sample.decode("utf-8",errors="strict")
                except UnicodeError:
                    raise BulkCorpusError(
                        "BULK_ENCODING_UNCERTAIN_EXPLICIT_ENCODING_REQUIRED") from None
                encoding="utf-8"
        require(encoding in ("utf-8","utf-8-sig","utf-16","gb18030"),
                "BULK_ENCODING_NOT_ALLOWED")
        descriptor,temp_name=tempfile.mkstemp(prefix=".wf-index-",
                     suffix=".sqlite3",dir=str(shard_dir))
        os.close(descriptor)
        tmp=Path(temp_name)
        db=None
        units=paragraphs=chapter=0
        fts_enabled=True
        try:
            db=sqlite3.connect(tmp)
            db.executescript("""
                PRAGMA journal_mode=DELETE;
                PRAGMA temp_store=FILE;
                PRAGMA cache_size=-2048;
                CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE units(id INTEGER PRIMARY KEY,
                 chapter INTEGER NOT NULL,paragraph INTEGER NOT NULL,
                 sentence INTEGER NOT NULL,line_no INTEGER NOT NULL,
                 chunk_no INTEGER NOT NULL,excerpt TEXT NOT NULL,
                 normalized TEXT NOT NULL,unit_sha256 TEXT NOT NULL);
                CREATE INDEX unit_location ON units(chapter,paragraph,sentence);
            """)
            try:
                db.execute("CREATE VIRTUAL TABLE units_fts USING fts5("
                           "normalized,tokenize='trigram')")
            except sqlite3.OperationalError:
                fts_enabled=False
            p=line_no=0
            with source.open("r",encoding=encoding,errors="strict",
                             newline=None) as handle:
                for line in handle:
                    line_no+=1
                    stripped=line.rstrip("\r\n").strip()
                    if not stripped:continue
                    if CHAPTER.fullmatch(stripped):
                        chapter+=1;p=0
                        continue
                    p+=1;paragraphs+=1
                    sentence_no=0
                    for segment in SENTENCE.split(stripped):
                        if not segment.strip():continue
                        for offset in range(0,len(segment),160):
                            fragment=segment[offset:offset+160]
                            if not fragment.strip():continue
                            norm=normalize_term(fragment)
                            if not norm:continue
                            sentence_no+=1;units+=1
                            cur=db.execute("""INSERT INTO units(
                              chapter,paragraph,sentence,line_no,chunk_no,
                              excerpt,normalized,unit_sha256)
                              VALUES(?,?,?,?,?,?,?,?)""",
                              (chapter,p,sentence_no,line_no,offset//160,
                               fragment,norm,sha256(fragment.encode("utf8")).hexdigest()))
                            if fts_enabled:
                                db.execute("INSERT INTO units_fts(rowid,normalized)"
                                           "VALUES(?,?)",(cur.lastrowid,norm))
                            if units%200==0:db.commit()
            require(units>0,"BULK_NO_INDEXABLE_TEXT")
            metadata={
                "book_id":book_id,"source_sha256":source_sha,
                "source_bytes":str(obj["size_bytes"]),
                "parser_version":"v68.lexical.v1",
                "chapters_with_headers":str(chapter),
                "units":str(units),"encoding":encoding,
                "fts_trigram":str(fts_enabled).lower(),
                "literary_semantics_verified":"false",
            }
            db.executemany("INSERT INTO meta VALUES(?,?)",metadata.items())
            db.commit()
            require(db.execute("PRAGMA quick_check").fetchone()[0]=="ok",
                    "BULK_SHARD_CORRUPT")
            db.close();db=None
            os.replace(tmp,target)
            try:
                self.conn.execute("BEGIN IMMEDIATE")
                self.conn.execute("""INSERT INTO books(
                  book_id,sha256,size_bytes,shard_name,parser_version,
                  units,chapters,confidence) VALUES(?,?,?,?,?,?,?,?)""",
                  (book_id,source_sha,obj["size_bytes"],name,
                   "v68.lexical.v1",units,chapter,"LEXICAL_ONLY"))
                self.conn.execute("""UPDATE assets SET sha256=?,book_id=?,
                  status='INDEXED_LEXICAL_ONLY' WHERE object_key=?""",
                  (source_sha,book_id,key))
                self.conn.commit()
            except BaseException:
                self.conn.rollback()
                target.unlink(missing_ok=True)
                raise
            return {"book_id":book_id,"source_sha256":source_sha,
                    "chapters_detected":chapter,"paragraphs_detected":paragraphs,
                    "units_indexed":units,"encoding":encoding,
                    "search_engine":"sqlite_fts5_trigram" if fts_enabled
                                    else "bounded_literal_scan",
                    "literary_semantics_verified":False,"r2_writes":0,
                    "llm_calls":0}
        except BaseException:
            if db is not None:db.close()
            tmp.unlink(missing_ok=True)
            raise

    def search(self,*,category,book_id,text,shard_dir,chapter=None,
               limit=6,vm_budget=3_000_000):
        """Scoped search: never silently glob/load all 400 books."""
        require(isinstance(category,str) and
                category in set(CAT.values())|{"待分类"},
                "BULK_QUERY_CATEGORY_REQUIRED")
        require(isinstance(book_id,str) and
                re.fullmatch(r"b_[a-f0-9]{32}",book_id),
                "BULK_QUERY_BOOK_ID_REQUIRED")
        require(type(limit) is int and 1<=limit<=12 and
                (chapter is None or type(chapter) is int and chapter>=0),
                "BULK_QUERY_SCOPE_OR_LIMIT_INVALID")
        needle=normalize_term(text)
        require(2<=len(needle)<=80 and
                not any(c in needle for c in ("%","_","\\")),
                "BULK_QUERY_TEXT_INVALID")
        own=self.conn.execute("""SELECT 1 FROM assets
                WHERE category=? AND book_id=? LIMIT 1""",
                (category,book_id)).fetchone()
        require(own is not None,"BULK_QUERY_CROSS_CATEGORY_BOOK_FORBIDDEN")
        book=self.conn.execute("SELECT * FROM books WHERE book_id=?",
                              (book_id,)).fetchone()
        require(book is not None,"BULK_QUERY_UNINDEXED_BOOK")
        path=Path(shard_dir)/book["shard_name"]
        require(path.is_file(),"BULK_QUERY_SHARD_MISSING")
        db=sqlite3.connect("file:"+quote(str(path.resolve()),safe="/")+
                           "?mode=ro",uri=True,cached_statements=16)
        db.row_factory=sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        remaining=[vm_budget]
        def deadline():
            remaining[0]-=1000
            return 1 if remaining[0]<=0 else 0
        db.set_progress_handler(deadline,1000)
        try:
            m=dict(db.execute("SELECT key,value FROM meta"))
            require(m.get("book_id")==book_id and
                    m.get("source_sha256")==book["sha256"],
                    "BULK_QUERY_SHARD_IDENTITY_MISMATCH")
            scope="u.chapter=? AND " if chapter is not None else ""
            args=[chapter] if chapter is not None else []
            accelerated=len(needle)>=3 and m.get("fts_trigram")=="true"
            if accelerated:
                sql=("SELECT u.chapter,u.paragraph,u.sentence,u.line_no,"
                     "u.excerpt,u.unit_sha256 FROM units_fts f JOIN units u "
                     "ON u.id=f.rowid WHERE "+scope+
                     "f.normalized LIKE ? ORDER BY u.chapter,u.paragraph,"
                     "u.sentence LIMIT ?")
            else:
                sql=("SELECT u.chapter,u.paragraph,u.sentence,u.line_no,"
                     "u.excerpt,u.unit_sha256 FROM units u WHERE "+scope+
                     "instr(u.normalized,?)>0 ORDER BY u.chapter,u.paragraph,"
                     "u.sentence LIMIT ?")
            args += ["%"+needle+"%" if accelerated else needle,limit+1]
            try: hits=[dict(x) for x in db.execute(sql,args)]
            except sqlite3.OperationalError as exc:
                if "interrupted" in str(exc).lower():
                    return {"status":"SCAN_BUDGET_EXCEEDED","matches":[],
                            "complete":False,
                            "literary_understanding_verified":False}
                raise
            return {"status":"LEXICAL_RESULTS_ONLY","matches":hits[:limit],
                    "complete":len(hits)<=limit,"has_more":len(hits)>limit,
                    "source_sha256":book["sha256"],
                    "literary_understanding_verified":False}
        finally:
            db.close()

def local_inventory(root,batch):
    """Safe local metadata preview for rclone folder upload, zero prose."""
    base=Path(root).resolve()
    require(base.is_dir() and re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}",batch),
            "BULK_LOCAL_ROOT_OR_BATCH_INVALID")
    entries=[]
    for path in base.rglob("*"):
        if path.is_symlink() or not path.is_file():continue
        if not path.resolve().is_relative_to(base):continue
        relative=path.relative_to(base).as_posix()
        if "/" not in relative:continue
        key=INBOX+batch+"/"+relative
        info=parse_key(key)
        entries.append({"key":key,"size":path.stat().st_size,
                        "category":info["category"],
                        "status":info["status"]})
    return sorted(entries,key=lambda r:r["key"])
