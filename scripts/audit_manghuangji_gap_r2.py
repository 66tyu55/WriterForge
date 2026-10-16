"""Single-book diagnostic for Manghuangji's pinned private R2 original.

Writes no novel prose, original chapter headings, or auth details to public logs.
This is only an audit; it neither mutates R2 nor silently renumbers chapters.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from collections import Counter
import json
import re

from writerforge.r2_storage import R2Config, _digest
from writerforge.single_work_runner import SingleWorkVault
from writerforge.modern_source import _encoding
from writerforge.modern_volumes import VOLUME_LINE, LOCAL_CHAPTER
from writerforge.source_study import chapter_number, StudyError

WORK_ID="manghuangji"
SOURCE_SHA="f7aee869e201b4171e40a3ff9230e794f01fdc959d372017b8982635668be3d5"
SOURCE_BYTES=8961764
TARGET_VOLUMES={22,25}
# Allow spaced chapter markers to diagnose an omitted strict header. Not an ingest parser.
DIGITS=r"[0-9零〇○一二三四五六七八九十百千萬万兩两]{1,14}"
NEAR_HEADING=re.compile(r"^第[ \t\u3000]*(?P<num>"+DIGITS+r")[ \t\u3000]*章")
ANY_CHAPTER=re.compile(r"第[ \t\u3000]*(?P<num>"+DIGITS+r")[ \t\u3000]*章")

def read_audit(source:Path):
    volume=None
    counts=Counter()
    headings=[]
    candidate_lines=[]
    with source.open("r",encoding=_encoding(source)) as handle:
        for line_number,line in enumerate(handle,1):
            value=line.strip()
            if len(line)>500:
                continue
            marker=VOLUME_LINE.fullmatch(value)
            if marker:
                volume=chapter_number(marker.group("volume"))
                counts["volume_markers"]+=1
                continue
            if volume not in TARGET_VOLUMES:
                continue
            heading=LOCAL_CHAPTER.fullmatch(value)
            if heading:
                ordinal=chapter_number(heading.group("chapter"))
                headings.append({"volume":volume,"number":ordinal,"line":line_number,
                                 "raw_heading_sha256":sha256(line.encode("utf-8")).hexdigest()})
                counts["strict_headers"]+=1
                continue
            if len(value)>140:
                continue
            # Candidate-only evidence: line number, line length and hash, never prose.
            loose=NEAR_HEADING.match(value)
            any_number=ANY_CHAPTER.search(value)
            if loose or any_number:
                token=(loose or any_number).group("num")
                try:num=chapter_number(token)
                except (ValueError,StudyError):continue
                offset=(loose or any_number).start()
                prefix=value[:offset]
                candidate_lines.append({
                    "volume":volume,"ordinal":num,"line":line_number,
                    "length":len(value),"line_starts_with_numbered_chapter":bool(loose),
                    "prefix_length":len(prefix),
                    "prefix_is_zhengwen":bool(re.fullmatch(r"正文[ \\t\\u3000:：\\-]*",prefix)),
                    "prefix_is_volume_marker":bool(re.fullmatch(r"第[0-9零〇一二三四五六七八九十百千]+卷.*",prefix)),
                    "prefix_is_punctuation_only":bool(re.fullmatch(r"[\\W_]+",prefix)),
                    "prefix_starts_with_bracket":prefix.startswith(("[","【","(","（")),
                    "line_is_strict_chapter_header":False,
                    "line_sha256":sha256(line.encode("utf-8")).hexdigest(),
                })
    windows=[]
    for i,row in enumerate(headings):
        if i and row["volume"]==headings[i-1]["volume"] and row["number"]!=headings[i-1]["number"]+1:
            start=max(0,i-3)
            end=min(len(headings),i+4)
            samples=headings[start:end]
            near=[c for c in candidate_lines if c["volume"]==row["volume"]
                  and samples[0]["line"]-15 <= c["line"] <= samples[-1]["line"]+15]
            windows.append({
                "volume":row["volume"],"previous":headings[i-1]["number"],
                "current":row["number"],"line":row["line"],
                "surrounding_heading_number_and_line":samples,
                "relaxed_match_candidates":near[:45],
            })
    return {"source_sha256":SOURCE_SHA,"bytes":SOURCE_BYTES,
            "work_id":WORK_ID,"stage":"pinned_private_R2_chapter_gap_audit",
            "target_volumes":sorted(TARGET_VOLUMES),
            "counts":dict(counts),"strict_chapter_headers_in_target_volumes":len(headings),
            "strict_sequence_anomalies":windows,
            "alternate_format_candidate_count":len(candidate_lines),
            "full_original_text_exposed":False,
            "source_rewritten":False,"r2_modified":False,
            "structure_learning_performed":False}

def main():
    cfg=R2Config.from_environment()
    if cfg.bucket!="writerforge-private-library":
        raise RuntimeError("Wrong private bucket")
    vault=SingleWorkVault(cfg,work_id=WORK_ID)
    prior=vault.verify_existing_single_work()
    if prior is None or (prior["utf8_sha256"],prior["utf8_bytes"])!=(SOURCE_SHA,SOURCE_BYTES):
        raise RuntimeError("source: PINNED_R2_ORIGINAL_NOT_VERIFIED")
    with TemporaryDirectory(prefix="wf-manghuangji-single-audit-") as root:
        source=Path(root)/"private.txt"
        vault.client.download_file(cfg.bucket,vault._blob_key(WORK_ID,SOURCE_SHA),str(source))
        if _digest(source)!=(SOURCE_SHA,SOURCE_BYTES):
            raise RuntimeError("download: FRESH_SHA256_FAILED")
        print(json.dumps(read_audit(source),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
