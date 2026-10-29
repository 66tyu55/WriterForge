"""0.CE: materialize four ACTUAL public-domain R2 source spans + written close readings.

R2 is immutable READ ONLY; only verified public-domain passages are retained
in the dev repository. Never copy any private modern source to GitHub.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys

from writerforge.classics_catalog import CATALOG, verify_edition
from writerforge.r2_storage import R2Config, R2StudyVault, R2StorageError
from experiments.wf_0br_stage_classical_readings import reading_text

ROOT=Path(__file__).resolve().parents[1]
NOTES=ROOT/"experiments/wf_0ce_r2_two_pinned_classics_four_reading_notes_20261029.json"
FINAL=ROOT/"experiments/wf_0ce_r2_public_classics_four_full_readings_20261029.json"
ALLOWED=frozenset(("laocanyouji","sanguo"))
PINNED_R2_SOURCE_SHA={
    "laocanyouji":"273f4cbaecb4c4d396ecec7103b4761e62bde0c0f368185a1697c1880cfe9cf7",
    "sanguo":"c8ca016d417dbd9540ed854ed02c97cf3d7aca13dd88b7e08555ffd2c0e5e2c3",
}


def materialize(vault:R2StudyVault,*,path:Path=FINAL):
    if vault.config.bucket!="writerforge-private-library":
        raise R2StorageError("WF0CE_PUBLIC_CLASSICS_R2_BUCKET_CHANGED")
    proposals=json.loads(NOTES.read_text("utf8"))
    rows=proposals["items"]
    if len(rows)!=4 or {x["work_key"] for x in rows}!=ALLOWED:
        raise ValueError("WF0CE_UNEXPECTED_R2_PUBLIC_READINGS")
    sources={}
    full_rows=[]
    with TemporaryDirectory(prefix="wf0ce-actual-r2-classic-") as cache:
        for key in sorted(ALLOWED):
            book=CATALOG[key]
            result=vault.restore(library=book.library,snapshot=None,
                                 destination=cache)
            if not result["verified"] or not result.get("source"):
                raise ValueError("WF0CE_REAL_PUBLIC_R2_RESTORE_FAILED")
            raw=Path(result["source"]).read_bytes()
            if sha256(raw).hexdigest()!=PINNED_R2_SOURCE_SHA[key]:
                raise ValueError("WF0CE_STORED_R2_PUBLIC_SOURCE_SHA_CHANGED")
            original=verify_edition(book,raw)
            sources[key]=original
        for x in rows:
            key=x["work_key"]
            original=sources[key]
            a,b=x["start_char"],x["end_char"]
            if not (type(a) is int and type(b) is int
                    and 0<=a<b<=len(original) and 400<=b-a<=2200):
                raise ValueError("WF0CE_ORIGINAL_SOURCE_SPAN_INVALID")
            prose=original[a:b]
            if sha256(prose.encode("utf8")).hexdigest()!=x["original_sha256"]:
                raise ValueError("WF0CE_PUBLIC_ORIGINAL_SPAN_NOT_EXACT")
            if (len(x["annotation"])!=3 or
                not all(type(n) is str and len(n)>=70 for n in x["annotation"])
                or len(x["reflection"])<130):
                raise ValueError("WF0CE_ORIGINAL_CLOSE_READING_NOT_COMPLETE")
            book=CATALOG[key]
            row={
                **x,
                "work":book.title,
                "source_key":key,
                "original":prose,
                "source_title":book.title,
                "source_edition":book.source_page,
                "source_blob_sha1":book.git_blob_sha1,
                "source_raw_sha256":PINNED_R2_SOURCE_SHA[key],
                "source_is_existing_r2_study_snapshot":True,
            }
            whole=reading_text(row,{"url":book.source_page})
            if not 250<len(whole)<=5000:
                raise ValueError("WF0CE_XUEHAI_FULL_READING_BOUND")
            full_rows.append(row)
    pack={
        "format":"wf.0ce.r2-public-original-annotation-reflection.v1",
        "title":"真实R2公版古籍原文＋批注＋心得（非AI仿写）",
        "source_access":"read-only R2StudyVault.restore + edition/blob/byte/span SHA cross-check",
        "rights":"public-domain classical Chinese source, edition-specific digital uncertain glyphs retained exactly",
        "original_prose_is_verbatim_contiguous":True,
        "original_modern_novels_copied_to_git":0,
        "original_r2_modified":False,
        "paid_model_api_calls":0,
        "writer_literary_improvement_verified":False,
        "sources":{key:{"url":CATALOG[key].source_page,
                       "source_git_blob_sha1":CATALOG[key].git_blob_sha1,
                       "source_sha256":PINNED_R2_SOURCE_SHA[key]}
                   for key in sorted(ALLOWED)},
        "items":full_rows,
    }
    encoded=json.dumps(pack,ensure_ascii=False,indent=2)+"\n"
    if path.exists():
        if path.read_text("utf8")!=encoded:
            raise FileExistsError("WF0CE_IMMUTABLE_R2_PUBLIC_READING_PACK_CHANGED")
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("x",encoding="utf8") as f:f.write(encoded)
    print(json.dumps({
        "status":"WF0CE_FOUR_EXACT_R2_PUBLIC_ORIGINALS_WITH_REAL_LITERARY_NOTES",
        "r2_public_classics_restored":len(ALLOWED),
        "full_original_three_part_readings":len(full_rows),
        "continuous_source_chars":sum(len(x["original"]) for x in full_rows),
        "specific_annotations":12,
        "open_reflections":4,
        "source_spans_SHA256_checked":True,
        "r2_writes":0,
        "private_modern_novel_sources_copied":0,
        "paid_author_model_calls":0,
        "literary_gain_proven":False,
    },ensure_ascii=False))


if __name__=="__main__":
    if len(sys.argv)!=1:
        raise SystemExit("WF0CE_NO_COMMAND_LINE_ARGUMENTS")
    materialize(R2StudyVault(R2Config.from_environment()))
