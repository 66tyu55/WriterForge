"""WF 0.BL: stage 16 newly authored Xuehai diagnostic scene details.

This is NOT ingestion of commercial xuanhuan novels or human-verified literary
learning. Only an isolated SQLite DB in a fresh output path, using the EXISTING
WriterForgeDB and XuehaiStore with LEARN status. The snapshot is left STAGING
and is deliberately not eligible to feed WRITE. Real public-domain original
texts require their own edition/rights/paragraph-source audit.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from writerforge import WriterForgeDB,RuntimeEngine,XuehaiStore

ROOT=Path(__file__).resolve().parents[1]
SEED=ROOT/"experiments/wf_0bl_xuanhuan_original_micro_scenes_20261028.json"
OUTPUT=Path("wf0bl_xuehai_staging_diagnostic_only.sqlite3")
WORK_ID="wf0bl-original-diagnostic-scene-atlas-v1"


def digest(raw:bytes)->str:
    return sha256(raw).hexdigest()


def validate_seed(path:Path=SEED)->tuple[dict,str]:
    raw=Path(path).read_bytes()
    if len(raw)>45_000:
        raise ValueError("WF0BL_ORIGINAL_SOURCE_PACK_TOO_LARGE")
    pack=json.loads(raw.decode("utf8"))
    if (type(pack) is not dict or pack.get("format")!=
            "wf.0bl.original-scene-atlas.v1" or
        pack.get("status")!="STAGING_ORIGINAL_TEST_SEEDS_ONLY" or
        pack.get("copyright_scope")!=
            "NEW_ORIGINAL_SCENES_NOT_EXCERPTS_FROM_EXISTING_XUANHUAN_NOVELS" or
        pack.get("max_production_imports")!=0 or
        pack.get("no_user_r2_access") is not True or
        pack.get("no_model_calls") is not True or
        pack.get("not_independently_literary_graded") is not True or
        type(pack.get("cards")) is not list or len(pack["cards"])!=16):
        raise ValueError("WF0BL_NOT_AN_UNREVIEWED_ORIGINAL_SOURCE_PACK")
    fields={
        "id","scene_type","subgenre","genre","condition",
        "method_hypothesis","anti_pattern","original_micro_scene",
        "source_kind","rights","evidence_state","scene_is_author_accepted"
    }
    ids=set()
    types=set()
    for item in pack["cards"]:
        if type(item) is not dict or set(item)!=fields:
            raise ValueError("WF0BL_ORIGINAL_CARD_SCHEMA_INVALID")
        if (type(item["id"]) is not str or
            not item["id"].startswith("wf0bl-") or
            item["id"] in ids or
            item["scene_type"] in types or
            item["genre"]!="玄幻" or
            item["source_kind"]!="AUTHOR_CREATED_ORIGINAL_FOR_WF_DIAGNOSTIC" or
            item["rights"]!="NEW_ORIGINAL_NO_THIRD_PARTY_QUOTE" or
            item["evidence_state"]!="UNVERIFIED_CANDIDATE_NOT_LEARNED" or
            item["scene_is_author_accepted"] is not False or
            any(type(item[k]) is not str or
                not 12<=len(item[k])<=240
                for k in ("condition","method_hypothesis","anti_pattern")) or
            type(item["original_micro_scene"]) is not str or
            not 45<=len(item["original_micro_scene"])<=250):
            raise ValueError("WF0BL_UNTRUSTED_OR_FALSELY_QUALIFIED_CARD")
        ids.add(item["id"])
        types.add(item["scene_type"])
    return pack,digest(raw)


def stage_original_diagnostic(*,output:Path=OUTPUT,seed:Path=SEED)->dict:
    output=Path(output)
    if output.exists():
        raise FileExistsError("WF0BL_DIAGNOSTIC_DB_ALREADY_EXISTS_NO_OVERWRITE")
    doc,source_sha=validate_seed(seed)
    output.parent.mkdir(parents=True,exist_ok=True)
    db=WriterForgeDB(output)
    rt=RuntimeEngine()
    rt.enter_learn()
    try:
        # An original, authored diagnostic source. Not marked as structurally
        # studied classic/modern text; no studied_chapters rows are invented.
        db.conn.execute(
            "INSERT INTO studied_works("
            "work_id,title,source_uri,source_sha256,chapter_count,"
            "language,script,study_level) VALUES(?,?,?,?,?,?,?,?)",
            (WORK_ID,"WF原创玄幻微场景诊断集（非名著原作）",
             "wf-original-diagnostic://0bl/scene-atlas-v1",source_sha,16,
             "zh","original_chinese",
             "diagnostic_unverified_original_examples_not_literary_study")
        )
        db.conn.commit()
        xuehai=XuehaiStore(db,rt)
        sid=xuehai.create_staging_snapshot(
            parent_id=None,
            note="WF0BL_ORIGINAL_DIAGNOSTIC_NOT_FOR_PRODUCTION")
        identifiers=[]
        for ix,card in enumerate(doc["cards"],1):
            entry=xuehai.add_entry(
                sid,work_id=WORK_ID,
                text=card["original_micro_scene"],
                chapter=ix,paragraph=1,sentence=1,
                library_class="WF原创诊断样本（未评级）",
                culture="中国",genre="玄幻",
                source_role="diagnostic_only",
                function=card["scene_type"],
                effect=card["condition"],
                method_cluster=card["id"],
                quality_weight=1.0,novelty_weight=1.0,
                reuse_policy="technique_only")
            identifiers.append(entry)
        count=db.conn.execute(
            "SELECT COUNT(*) FROM xuehai_entries WHERE snapshot_id=?",
            (sid,)).fetchone()[0]
        snapshot=db.conn.execute(
            "SELECT status,layout FROM snapshots WHERE id=?",
            (sid,)).fetchone()
        studied=db.conn.execute(
            "SELECT COUNT(*) FROM studied_chapters").fetchone()[0]
        if (count!=16 or snapshot["status"]!="staging" or
            snapshot["layout"]!="full" or studied!=0 or
            len(set(identifiers))!=16):
            raise RuntimeError("WF0BL_STAGING_NOT_EXACT_OR_PROVENANCE_CORRUPT")
        result={
            "format":"wf.0bl.xuehai-original-test-staging.v1",
            "status":"DIAGNOSTIC_ONLY_STAGING_NOT_USABLE_BY_WRITE",
            "source_sha256":source_sha,
            "staging_snapshot_id":sid,
            "new_original_diagnostic_entries":count,
            "actual_classics_text_ingested":0,
            "actual_modern_copyright_novels_ingested":0,
            "published_snapshots":0,
            "studied_novel_chapters_claimed":studied,
            "new_model_calls":0,
            "r2_private_reads_or_writes":0,
            "production_canon_writes":0,
            "literary_quality_proven":False,
        }
        db.conn.commit()
        return result
    finally:
        db.close()


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=OUTPUT)
    parser.add_argument("--seed",type=Path,default=SEED)
    args=parser.parse_args()
    status=stage_original_diagnostic(output=args.output,seed=args.seed)
    print(json.dumps(status,ensure_ascii=False,sort_keys=True,indent=2))
