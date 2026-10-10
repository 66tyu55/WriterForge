"""Real, resumable Chinese ORIGINAL-text structural study (NOT model fine-tuning).

Project Gutenberg #23962 / GITenberg provides the full Traditional-Chinese
西遊記. Reader-first literary judgments are not fabricated: this stage records
sequential, provenance-stamped structural evidence in eight separate tracks.
A later human/model reader may enrich it, but no 'real reader liked this'
score is inferred from keywords.

Memory bounds: downloads <= 8 MiB, per chapter <= 180K chars, <= 8000 source
units, transaction per chapter; no full-text re-copy per published snapshot.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
import os
import re
import urllib.request

from .db import WriterForgeDB
from .runtime import Mode, RuntimeEngine


WORK_ID = "xiyouji-gutenberg-23962"
SOURCE_URL = "https://raw.githubusercontent.com/GITenberg/---_23962/master/23962-0.txt"
SOURCE_PAGE = "https://www.gutenberg.org/ebooks/23962"
MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024
MAX_CHAPTER_CHARS = 180_000
MAX_CHAPTER_UNITS = 8_000
MAX_EXCERPT = 160
TRACKS = ("plot", "object", "character", "environment", "time", "location", "sense", "emotion")
HEAD = re.compile(
    r"(?m)^[ \t\u3000]*第([0-9零〇○一二三四五六七八九十百千兩两"
    r"壹貳參肆伍陸柒捌玖拾佰]+)回[ \t\u3000]*([^\r\n]{0,90})[ \t\u3000]*\r?$"
)
FIGURES = {"零":0, "〇":0, "○":0, "一":1,"二":2,"兩":2,"两":2,"三":3,"四":4,"五":5,
           "六":6,"七":7,"八":8,"九":9,
           "壹":1,"貳":2,"參":3,"肆":4,"伍":5,"陸":6,"柒":7,"捌":8,"玖":9}
SCALE = {"十":10,"拾":10,"百":100,"佰":100,"千":1000}
SOURCE_SIGNALS = {
    "plot": ("卻","却","便","遂","乃","忽","只見","只见"),
    "object": ("棍","杖","石","刀","劍","剑","袈裟","鉢","钵","果","丹"),
    "character": ("猴","王","祖師","祖师","悟空","唐僧","行者","師父","师父"),
    "environment": ("風","风","雨","雪","雲","云","山","水","樹","树","海","天"),
    "time": ("日","夜","時","时","年","朝","晚","須臾","须臾"),
    "location": ("山","洞","海","國","国","府","州","殿","城"),
    "sense": ("聽","听","聞","闻","看","見","见","嗅","冷","熱","热"),
    "emotion": ("喜","怒","懼","惧","憂","忧","愁","悲","笑","恨"),
}


class StudyError(ValueError):
    pass


def chapter_number(raw: str) -> int:
    if raw.isdecimal():
        return int(raw)
    # Gutenberg #23962 uses old Chinese chapter counters such as 第六一回
    # for chapter 61, not necessarily the modern 第六十一回 spelling.
    if len(raw) > 1 and all(ch in FIGURES for ch in raw):
        return int("".join(str(FIGURES[ch]) for ch in raw))
    result = current = 0
    for char in raw:
        if char in FIGURES:
            current = FIGURES[char]
        elif char in SCALE:
            amount = current if current else 1
            result += amount * SCALE[char]
            current = 0
        else:
            raise StudyError(f"unrecognized Chinese numeral: {raw!r}")
    return result + current


@dataclass(frozen=True)
class Chapter:
    number: int
    heading: str
    text: str

    @property
    def fingerprint(self) -> str:
        return sha256(self.text.encode("utf-8")).hexdigest()


def parse_original(text: str, *, require_hundred: bool = True,
                   expected_count: int | None = None,
                   include_prologue: bool = False) -> tuple[Chapter, ...]:
    if not isinstance(text, str) or len(text) > MAX_DOWNLOAD_BYTES:
        raise StudyError("source too large or not UTF-8 text")
    # Strip Gutenberg licence/postface; its English prose must not be learned.
    marker = re.search(r"(?mi)^\*{3}\s*END OF (?:THE )?PROJECT GUTENBERG", text)
    if marker:
        text = text[:marker.start()]
    matches = [m for m in HEAD.finditer(text) if 1 <= chapter_number(m.group(1)) <= 200]
    if not matches:
        raise StudyError("no original Chinese chapter headings; refused to ingest")
    # Reject duplicate or nonsequential headings; no silent skipped chapters.
    nums = [chapter_number(m.group(1)) for m in matches]
    if nums != list(range(1, len(nums) + 1)):
        raise StudyError(f"chapter order malformed: {nums[:12]}")
    if require_hundred and len(matches) != 100:
        raise StudyError(f"expected all 100 original chapters, found {len(matches)}")
    if expected_count is not None and len(matches) != expected_count:
        raise StudyError(f"expected {expected_count} chapter headings, found {len(matches)}")
    chapters = []
    if include_prologue:
        # Water Margin has a real 楔子 before chapter 1; do NOT silently drop it.
        intro = re.search(r"(?m)^[ \t\u3000]*楔子[ \t\u3000]+([^\r\n]{1,90})\r?$", text[:matches[0].start()])
        if not intro:
            raise StudyError("original source requires a 楔子 prologue, but none was found")
        body = text[intro.end():matches[0].start()].strip()
        if not 100 <= len(body) <= MAX_CHAPTER_CHARS:
            raise StudyError("source prologue is missing or truncated")
        chapters.append(Chapter(0, "楔子 " + intro.group(1).strip(), body))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end].strip()
        if not body or len(body) > MAX_CHAPTER_CHARS:
            raise StudyError(f"chapter {i+1} missing or oversized")
        chapters.append(Chapter(nums[i], m.group(2).strip(), body))
    return tuple(chapters)


def download_original(path: str | Path, *, url: str = SOURCE_URL) -> Path:
    """Bounded and atomic download. Never download an arbitrary URL via the CLI."""
    if url != SOURCE_URL:
        raise StudyError("unsupported source URL; use --source to import another local edition")
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".partial")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WriterForge-original-text-study/1"})
        with urllib.request.urlopen(req, timeout=40) as response, part.open("wb") as handle:
            total = 0
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    raise StudyError("source exceeds 8 MiB safety limit")
                handle.write(chunk)
        text = part.read_text(encoding="utf-8-sig")
        parse_original(text)
        os.replace(part, dest)
        return dest
    finally:
        part.unlink(missing_ok=True)


def _unitize(chapter: Chapter, *, wrapped_lines: bool = False):
    """Sequential chapter->paragraph->sentence. No global keyword shortcuts.

    Gutenberg texts differ: 西遊記 stores naturally separated lines, while
    紅樓夢 / 水滸傳 hard-wrap each paragraph into narrow printed lines.
    For those editions, reconstruct wrapped paragraphs before punctuation
    segmentation; keep the source content and ordered offsets intact.
    """
    if not wrapped_lines:
        paragraphs = [line.strip() for line in chapter.text.splitlines() if line.strip()]
        stops = r"[^。！？!?；;\r\n]+[。！？!?；;]?"
    else:
        paragraphs = []
        current: list[str] = []
        def flush():
            if current:
                paragraphs.append("".join(current))
                current.clear()
        for raw in chapter.text.splitlines():
            line = raw.rstrip()
            if not line.strip() or re.fullmatch(r"[-—─]{8,}", line.strip()):
                flush()
                continue
            # The Gutenberg editions use leading indentation to signal a
            # genuine paragraph. A hard-wrapped continuation has no indent.
            if current and (line.startswith("\u3000") or len(line)-len(line.lstrip(" "))>=2):
                flush()
            current.append(line.strip())
            if len(current)>500:
                raise StudyError("malformed wrapped paragraph exceeds 500 physical lines")
        flush()
        stops = r"[^。！？!?；;．\r\n]+[。！？!?；;．]?"
    if len(paragraphs)>4_000:
        raise StudyError("chapter exceeds 4000 paragraphs")
    counter = 0
    for p, paragraph in enumerate(paragraphs, 1):
        chunks = re.findall(stops, paragraph)
        s_index = 0
        for chunk in chunks:
            chunk = chunk.strip()
            for start in range(0, len(chunk), 240):
                piece = chunk[start:start + 240].strip()
                if not piece:
                    continue
                s_index += 1
                counter += 1
                if counter>MAX_CHAPTER_UNITS:
                    raise StudyError("chapter exceeds 8000 source units")
                yield p, s_index, piece


def _structural_analysis(sentence: str) -> tuple[dict, dict]:
    """Cheap factual signals, not invented reader feelings or LLM literary analysis."""
    tracks = {
        k: [tag for tag in tags if tag in sentence][:3]
        for k, tags in SOURCE_SIGNALS.items()
    }
    if ("“" in sentence or "「" in sentence or "：" in sentence) and (
        "道" in sentence or "說" in sentence or "说" in sentence
    ):
        function = "dialogue"
    elif sentence.startswith(("詩曰", "诗曰", "有詩", "有诗", "詞曰", "词曰")):
        function = "verse"
    elif len(tracks["environment"]) >= 2:
        function = "environment"
    elif tracks["emotion"]:
        function = "emotion_expression"
    elif tracks["plot"]:
        function = "action_sequence"
    else:
        function = "narration"
    craft = {
        "sentence_function": function,
        "sentence_chars": len(sentence),
        "is_dialogue": function == "dialogue",
        "has_transition_marker": any(x in sentence for x in ("卻說", "却说", "且聽", "且听", "不題", "不题")),
        "analysis_level": "deterministic_structural_unverified",
        "reader_effect": None,  # no fake reader-first measurements
    }
    return tracks, craft


class OriginalStudy:
    def __init__(self, db: WriterForgeDB, runtime: RuntimeEngine):
        self.db, self.runtime = db, runtime

    def ingest(
        self, text: str, *, work_id: str = WORK_ID, title: str = "西遊記",
        source_uri: str = SOURCE_PAGE, max_chapters: int | None = None,
        require_hundred: bool = True,
        expected_count: int | None = None,
        include_prologue: bool = False,
        wrapped_lines: bool = False,
    ) -> dict:
        self.runtime.require(Mode.LEARN)
        if not work_id or len(work_id) > 128:
            raise StudyError("invalid work ID")
        chapters = parse_original(text, require_hundred=require_hundred,
                                  expected_count=expected_count,
                                  include_prologue=include_prologue)
        if max_chapters is not None and not 1 <= max_chapters <= len(chapters):
            raise StudyError("max_chapters outside the source")
        content_hash = sha256(text.encode("utf-8")).hexdigest()
        conn = self.db.conn
        prev = conn.execute(
            "SELECT source_sha256,chapter_count FROM studied_works WHERE work_id=?",
            (work_id,),
        ).fetchone()
        if prev and (prev["source_sha256"] != content_hash or prev["chapter_count"] != len(chapters)):
            raise StudyError("source edition changed: start a new work_id; do not silently mix revisions")
        if not prev:
            conn.execute(
                """INSERT INTO studied_works(
                   work_id,title,source_uri,source_sha256,chapter_count)
                   VALUES(?,?,?,?,?)""",
                (work_id,title,source_uri,content_hash,len(chapters)),
            )
            conn.commit()
        completed, studied_spans, retrievable = 0, 0, 0
        for chapter in chapters[:max_chapters]:
            old = conn.execute(
                "SELECT chapter_sha256 FROM studied_chapters WHERE work_id=? AND chapter=?",
                (work_id, chapter.number),
            ).fetchone()
            if old:
                if old["chapter_sha256"] != chapter.fingerprint:
                    raise StudyError("chapter changed after ingestion")
                continue
            if conn.in_transaction:
                raise StudyError("cannot ingest inside another transaction")
            try:
                conn.execute("BEGIN IMMEDIATE")
                latest = conn.execute(
                    """SELECT id FROM snapshots WHERE status='published'
                       ORDER BY id DESC LIMIT 1"""
                ).fetchone()
                parent_id = latest["id"] if latest else None
                cur = conn.execute(
                    """INSERT INTO snapshots(parent_id,status,layout,note)
                       VALUES(?, 'staging', ?, ?)""",
                    (parent_id, "delta" if parent_id is not None else "full",
                     f"{work_id}/chapter-{chapter.number:03}"),
                )
                sid = int(cur.lastrowid)
                count, inserted = 0, 0
                hashes: set[str] = set()
                for paragraph, sentence, piece in _unitize(chapter, wrapped_lines=wrapped_lines):
                    count += 1
                    tracks, craft = _structural_analysis(piece)
                    excerpt = piece[:MAX_EXCERPT]
                    unit_hash = sha256(piece.encode("utf-8")).hexdigest()
                    conn.execute(
                        """INSERT INTO source_spans(
                           work_id,chapter,paragraph,sentence,excerpt,source_sha256,
                           tracks_json,craft_json) VALUES(?,?,?,?,?,?,?,?)""",
                        (work_id, chapter.number, paragraph, sentence, excerpt,
                         unit_hash, json.dumps(tracks, ensure_ascii=False),
                         json.dumps(craft, ensure_ascii=False)),
                    )
                    # A repeated sentence is still a distinct source_span, but
                    # need not occupy duplicate retrieval slots in this chapter.
                    key = sha256((work_id + "|" + piece).encode("utf-8")).hexdigest()
                    if key in hashes:
                        continue
                    hashes.add(key)
                    cur = conn.execute(
                        """INSERT INTO xuehai_entries(
                           snapshot_id,work_id,chapter,paragraph,sentence,text,
                           library_class,culture,genre,source_role,function,effect,
                           method_cluster,quality_weight,novelty_weight,reuse_policy,
                           source_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (sid,work_id,chapter.number,paragraph,sentence,excerpt,
                         "中国古代小说","中国","古代白话","core",
                         craft["sentence_function"],"unverified",
                         "classical_"+craft["sentence_function"],1.0,1.0,
                         "technique_only",key),
                    )
                    if self.db.fts_enabled:
                        conn.execute(
                            """INSERT INTO xuehai_fts(
                               entry_id,text,function,effect,method_cluster
                               ) VALUES(?,?,?,?,?)""",
                            (int(cur.lastrowid), excerpt,
                             craft["sentence_function"],"unverified",
                             "classical_"+craft["sentence_function"]),
                        )
                    inserted += 1
                if count == 0:
                    raise StudyError("chapter has no source sentences")
                conn.execute("UPDATE snapshots SET status='published' WHERE id=?", (sid,))
                conn.execute(
                    """INSERT INTO studied_chapters(
                       work_id,chapter,chapter_sha256,heading,source_spans,
                       retrieval_entries,snapshot_id) VALUES(?,?,?,?,?,?,?)""",
                    (work_id,chapter.number,chapter.fingerprint,chapter.heading,
                     count,inserted,sid),
                )
                conn.commit()
                completed += 1
                studied_spans += count
                retrievable += inserted
            except Exception:
                if conn.in_transaction:
                    conn.rollback()
                raise
            finally:
                hashes = set()
        state = self.status(work_id)
        return {
            "work_id":work_id,"source_sha256":content_hash,
            "source_chapters":len(chapters),"newly_studied":completed,
            "new_source_spans":studied_spans,"new_retrieval_entries":retrievable,
            **state,
        }

    def status(self, work_id: str = WORK_ID) -> dict:
        row = self.db.conn.execute(
            """SELECT w.chapter_count,
                      COUNT(c.chapter) AS studied_chapters,
                      COALESCE(SUM(c.source_spans),0) AS studied_units,
                      COALESCE(SUM(c.retrieval_entries),0) AS retrieval_entries
               FROM studied_works w
               LEFT JOIN studied_chapters c ON c.work_id=w.work_id
               WHERE w.work_id=? GROUP BY w.work_id""",
            (work_id,),
        ).fetchone()
        if row is None:
            return {"studied_chapters":0,"studied_units":0,
                    "retrieval_entries":0,"structure_complete":False,
                    "literary_reader_first_complete":False}
        return {
            "studied_chapters":int(row["studied_chapters"]),
            "studied_units":int(row["studied_units"]),
            "retrieval_entries":int(row["retrieval_entries"]),
            "structure_complete":row["studied_chapters"]==row["chapter_count"],
            # This level requires sequential reader reactions and confirmed
            # craft links, not merely deterministic keyword/cue extraction.
            "literary_reader_first_complete":False,
        }
