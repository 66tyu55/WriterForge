"""Pin three NEW Chinese fantasy originals before any private R2 archive.

This deliberately has a two-phase gate:
(1) validate-only fetches source in GitHub runner, emits hash + limited metadata;
(2) only after SHA is deliberately pinned can the upload + fresh R2 read proceed.
Do not log or publish full modern copyrighted source content.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import Request, urlopen
from urllib.parse import quote
from zipfile import ZipFile, BadZipFile
import argparse
import json
import os
import sys

from archive_three_xuanhuan_r2 import (
    NovelSource, OriginalSourceError, fetch_original, store_verified_source,
    verify_source, MAX_BYTES
)
from writerforge.r2_storage import R2Config
from writerforge.single_work_runner import SingleWorkVault

SOURCES = {
    "qiumo": NovelSource(
        "qiumo", "求魔", "耳根", "苏铭",
        "https://download.zxcs.zip/" + quote("《求魔》（校对版全本）作者：耳根.txt"),
        5_000_000, 18_000_000, None, None, 600),
    "zhetian": NovelSource(
        "zhetian", "遮天", "辰东", "叶凡",
        "https://download.zxcs.zip/" + quote("《遮天》（精校版全本）作者：辰东.txt"),
        8_000_000, 25_000_000, 13455412, "9cbf8da97daceb36fbd85edd84e2874a9ceac28252c18386fecf167d5a95660b", 800),
    "manghuangji": NovelSource(
        "manghuangji", "莽荒纪", "我吃西红柿", "纪宁",
        "https://download.zxcs.zip/" + quote("《莽荒纪》（校对版全本）作者：我吃西红柿.txt"),
        5_000_000, 25_000_000, 8961764, "f7aee869e201b4171e40a3ff9230e794f01fdc959d372017b8982635668be3d5", 500),
}

def fetch_zipped_txt(source: NovelSource, destination: Path) -> dict:
    if source.work_id != "manghuangji" or destination.exists():
        raise OriginalSourceError("ZIP_SOURCE_OR_DESTINATION_NOT_APPROVED")
    if source.source_url != "https://d.noveless.com/d/one/books/1965.txt.zip":
        raise OriginalSourceError("ZIP_SOURCE_URL_CHANGED")
    compressed = destination.with_suffix(".zip.part")
    partial = destination.with_suffix(".txt.part")
    try:
        req = Request(source.source_url, headers={"User-Agent": "WriterForge-private-R2/1"})
        with urlopen(req, timeout=90) as resp, compressed.open("xb") as out:
            if resp.status != 200:
                raise OriginalSourceError("ZIP_SOURCE_HTTP_NOT_200")
            count = 0
            while chunk := resp.read(1024 * 1024):
                count += len(chunk)
                if count > 16 * 1024 * 1024:
                    raise OriginalSourceError("ZIP_EXCEEDS_COMPRESSED_SIZE_CAP")
                out.write(chunk)
        with ZipFile(compressed, "r") as archive:
            entries = archive.infolist()
            candidates = [
                it for it in entries
                if not it.is_dir() and it.filename.lower().endswith(".txt")
            ]
            if len(candidates) != 1:
                raise OriginalSourceError("ZIP_MUST_CONTAIN_EXACTLY_ONE_TXT")
            info = candidates[0]
            if (info.file_size > MAX_BYTES or info.file_size < source.min_bytes
                    or info.compress_size == 0
                    or info.file_size > info.compress_size * 30):
                raise OriginalSourceError("ZIP_TXT_SIZE_OR_RATIO_INVALID")
            with archive.open(info) as src, partial.open("xb") as out:
                size = 0
                while chunk := src.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise OriginalSourceError("ZIP_EXTRACTION_OVER_BUDGET")
                    out.write(chunk)
        receipt = verify_source(source, partial)
        partial.replace(destination)
        return receipt
    except (BadZipFile, OSError, ValueError) as exc:
        raise OriginalSourceError("ZIP_DOWNLOAD_OR_DECODE_FAILED_"+type(exc).__name__) from None
    finally:
        compressed.unlink(missing_ok=True)
        partial.unlink(missing_ok=True)



def fetch_qiumo_probe(source: NovelSource, destination: Path) -> dict:
    """Keep runner-local bytes only for SAFE heading-format diagnosis if header validation fails."""
    if source.work_id != "qiumo" or destination.exists():
        raise OriginalSourceError("QIUMO_PROBE_SOURCE_OR_DESTINATION_INVALID")
    req = Request(source.source_url, headers={"User-Agent": "WriterForge-private-R2/1"})
    with urlopen(req, timeout=90) as response, destination.open("xb") as output:
        if response.status != 200:
            raise OriginalSourceError("SOURCE_SERVER_HTTP_NOT_200")
        total = 0
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_BYTES:
                raise OriginalSourceError("SOURCE_OVER_MAX_32_MIB")
            output.write(chunk)
    # Source remains in this private runner while its heading grammar is diagnosed.
    counts = {"lines": 0, "chapter_word_lines": 0, "line_start_chapter": 0,
              "volume_first": 0, "chapter_ordinal_anywhere": 0, "shape_samples": []}
    import re
    for codec in ("utf-8-sig", "gb18030"):
        try:
            with destination.open("r", encoding=codec) as stream:
                for line in stream:
                    counts["lines"] += 1
                    if len(line) > 400:
                        continue
                    t = line.strip()
                    if "第" in t and ("章" in t or "回" in t or "节" in t):
                        counts["chapter_word_lines"] += 1
                        if len(counts["shape_samples"]) < 12:
                            counts["shape_samples"].append({
                                "len": len(t), "di_index": t.find("第"),
                                "zhang_index": t.find("章"), "hui_index": t.find("回"),
                                "jie_index": t.find("节"), "juan_index": t.find("卷"),
                                "first_two_are_digits": t[:2].isdecimal()})
                    if re.match(r"^第[0-9零〇一二三四五六七八九十百千]{1,14}[章回节]", t):
                        counts["line_start_chapter"] += 1
                    if re.search(r"第[0-9零〇一二三四五六七八九十百千]{1,14}[章回节]", t):
                        counts["chapter_ordinal_anywhere"] += 1
                    if t.startswith("第") and "卷" in t[:25]:
                        counts["volume_first"] += 1
            counts["encoding"] = codec
            break
        except UnicodeError:
            counts["lines"] = 0
            continue
    print(json.dumps({"safe_qiumo_header_structure_probe": counts}, ensure_ascii=False), flush=True)
    # This edition prints a VOLUME first, then a chapter ordinal on the same
    # heading line. Do NOT turn a volume number into a chapter number.
    qualified = 0
    volume_head = re.compile(
        r"^第[0-9零〇一二三四五六七八九十百千萬万兩两]{1,10}卷"
        r"[^\\r\\n]{0,60}?第[0-9零〇一二三四五六七八九十百千萬万兩两]{1,14}章"
        r"(?:[^\\r\\n]{0,90})?$"
    )
    with destination.open("r", encoding=counts["encoding"]) as src:
        for line in src:
            if len(line) <= 180 and volume_head.fullmatch(line.strip()):
                qualified += 1
    print(json.dumps({"safe_qiumo_volume_qualified_heading_count": qualified}, ensure_ascii=False), flush=True)
    if qualified < source.min_heading_occurrences:
        raise OriginalSourceError(
            "SOURCE_VOLUME_QUALIFIED_HEADINGS_TOO_FEW: " + str(qualified))
    receipt = verify_source(replace(source, min_heading_occurrences=0), destination)
    receipt["chapter_heading_occurrences"] = qualified
    receipt["volume_qualified_heading_grammar"] = True
    return receipt

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", choices=sorted(SOURCES), required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    spec = SOURCES[args.work]
    if not args.validate_only and not spec.pinned_sha256:
        raise SystemExit("source: REFUSE_UPLOAD_UNPINNED_EDITION; run validate-only and commit vetted SHA256 first")
    try:
        with TemporaryDirectory(prefix="wf-next-xuanhuan-") as temp:
            path = Path(temp) / "original.txt"
            receipt = (fetch_qiumo_probe(spec, path) if args.work == "qiumo"
                       else fetch_original(spec, path))
            if args.validate_only:
                result = {"stage": "new_work_source_verified_only",
                          "work_id": spec.work_id, "title": spec.title,
                          "bytes": receipt["source_bytes"],
                          "sha256": receipt["source_sha256"],
                          "header_matches_not_order_proof": receipt["chapter_heading_occurrences"],
                          "new_private_archive": False}
            else:
                config = R2Config.from_environment()
                if config.bucket != "writerforge-private-library":
                    raise OriginalSourceError("WRONG_PRIVATE_R2_BUCKET")
                vault = SingleWorkVault(config, work_id=spec.work_id)
                saved = store_verified_source(vault, spec, path, receipt)
                result = {
                    "stage": "new_work_r2_archive_verified",
                    "work_id": spec.work_id, "title": spec.title,
                    "bytes": receipt["source_bytes"],
                    "sha256": receipt["source_sha256"],
                    "new_private_archive": saved["new_private_archive"],
                    "fresh_roundtrip": saved["fresh_roundtrip"],
                    "snapshot": saved["snapshot"],
                    "structural_learning_performed": False,
                    "independent_literary_review_performed": False,
                }
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        # Additional SAFE chapter-shape diagnostics: counts/positions only, never text.
        if args.work == "qiumo" and "path" in locals() and path.exists():
            import re
            for codec in ("utf-8-sig", "gb18030"):
                try:
                    lines = chapter_like = numbered = start_chapter = 0
                    examples = []
                    with path.open("r", encoding=codec) as src:
                        for line in src:
                            lines += 1
                            if len(line) > 400:
                                continue
                            text = line.strip()
                            pos = text.find("第")
                            if pos >= 0 and ("章" in text or "回" in text):
                                chapter_like += 1
                                if len(examples) < 8:
                                    examples.append({"line_length": len(text), "first_di_position": pos,
                                        "first_zhang_position": text.find("章"),
                                        "first_hui_position": text.find("回"),
                                        "starts_with_di": text.startswith("第"),
                                        "contains_juan": "卷" in text})
                            if re.search(r"第[0-9一二三四五六七八九十百千零〇]{1,12}章", text):
                                numbered += 1
                            if re.match(r"^第[0-9一二三四五六七八九十百千零〇]{1,12}章", text):
                                start_chapter += 1
                    print(json.dumps({"safe_qiumo_heading_probe": {
                        "encoding": codec, "lines": lines, "chapter_like": chapter_like,
                        "inline_numbered": numbered, "line_start_numbered": start_chapter,
                        "shape_samples_without_original_text": examples}}, ensure_ascii=False))
                    break
                except UnicodeError:
                    continue
        # redact URL/query and never include any original prose
        print(json.dumps({"work_id": args.work, "stage": "source_or_upload",
            "error_type": type(exc).__name__,
            "error": str(exc)[:350]}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
