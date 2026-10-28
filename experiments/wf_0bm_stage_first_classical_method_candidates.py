"""0.BM: read one REAL existing ancient chapter fixture into an ISOLATED LEARN DB.

No new web downloads, private R2, copied copyrighted modern books, LLM calls,
Canonical database writes or production method publication. The complete local
fixture is NOT the same edition as Wikisource oldid 2562136. A genuine
OriginalStudy structural source snapshot is distinguishable from a *method*
approval; only the candidate delta remains STAGING and PENDING.
"""
from __future__ import annotations

from hashlib import sha1, sha256
from pathlib import Path
import argparse
import json
import re

from writerforge import WriterForgeDB, RuntimeEngine, OriginalStudy, XuehaiStore

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "experiments/wf_0bm_classical_source_anchored_method_candidates_20261028.json"
OUTPUT = Path("wf0bm_classical_isolated_pending_only.sqlite3")
OWNED_FIXTURE = ROOT / "tests/fixtures/xiyouji_chapter_001_original_zh.txt"
WORK_ID = "wf0bm-xiyouji-chapter001-local-fixture-only"
PINNED_FIXTURE_SOURCE_URI = (
    "https://github.com/66tyu55/WriterForge/blob/"
    "d4222f9bba35dbd36f96ad2a6dcd082d22fba984/"
    "tests/fixtures/xiyouji_chapter_001_original_zh.txt"
)
CARD_FIELDS = {
    "id", "work_id", "scene_type", "source_anchor",
    "source_anchor_sha256", "local_fixture_anchor",
    "source_kind", "rights_status", "review_status", "value_status",
    "review_receipt_sha256", "scene_facets", "target_genres",
    "style_scope", "signal", "mechanism", "writer_option",
    "applies_when", "not_when", "pov_limit", "counterexample",
    "literary_hypothesis", "transfer_examples", "source_unit_locator",
}
ADMISSION_FIELDS = (
    "scene_type", "scene_facets", "target_genres", "style_scope",
    "signal", "mechanism", "writer_option", "applies_when",
    "not_when", "pov_limit", "counterexample", "source_kind",
    "rights_status", "review_status", "value_status", "review_receipt_sha256",
)
SOURCE_IDS = ("xiyou-001", "shiji-007")


def _git_blob_sha1(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode() + b"\\0" + raw).hexdigest()


def validate_catalog(path: Path = CANDIDATES,
                     fixture: Path = OWNED_FIXTURE) -> tuple[dict, str, str]:
    raw = Path(path).read_bytes()
    if len(raw) > 30_000:
        raise ValueError("WF0BM_CANDIDATE_CATALOG_TOO_LARGE")
    data = json.loads(raw.decode("utf8"))
    if (type(data) is not dict or
        data.get("format") != "wf.0bm.classical-first-source-anchored-candidate-methods.v1" or
        data.get("status") != "PENDING_EDITORIAL_RIGHTS_AND_LITERARY_REVIEW_NOT_PRODUCTION" or
        data.get("method_count") != 4 or
        data.get("allowed_production_method_imports") != 0 or
        data.get("source_raw_page_bytes_in_repo") != 0 or
        data.get("wiksource_editorial_license_review_complete") is not False or
        data.get("printing_basetext_verified") is not False or
        data.get("literary_quality_proven") is not False or
        data.get("author_model_calls") != 0 or
        data.get("actual_modern_novel_ingestions") != 0 or
        data.get("production_canon_writes") != 0 or
        type(data.get("sources")) is not list or len(data["sources"]) != 2 or
        type(data.get("cards")) is not list or len(data["cards"]) != 4):
        raise ValueError("WF0BM_FALSE_PRODUCTION_OR_RIGHTS_OR_LITERARY_CLAIM")

    sources = {x.get("id"): x for x in data["sources"]}
    if set(sources) != set(SOURCE_IDS):
        raise ValueError("WF0BM_SOURCE_INVENTORY_INVALID")
    for source in sources.values():
        oldid = source.get("oldid")
        if (type(oldid) is not int or
            source.get("source_layer") != "HISTORICAL_ORIGINAL_TEXT_PUBLIC_DOMAIN" or
            source.get("digital_layer") != "CC_BY_SA_4_0_AND_EDITION_NOT_YET_APPROVED" or
            source.get("full_page_sha256") is not None or
            type(source.get("url")) is not str or
            "zh.wikisource.org/w/index.php?" not in source["url"] or
            f"oldid={oldid}" not in source["url"]):
            raise ValueError("WF0BM_UNPINNED_EDITION_OR_DIGITAL_RIGHTS")
    local = sources["xiyou-001"]
    remote = sources["shiji-007"]
    if (local["identity"] != "WIKISOURCE_REVISION_NOT_EQUAL_TO_LOCAL_FIXTURE" or
        local["local_fixture"] != "tests/fixtures/xiyouji_chapter_001_original_zh.txt" or
        remote["identity"] != "WEB_PAGE_REVIEW_ONLY_NO_LOCAL_SOURCE_BYTES" or
        remote["local_fixture"] is not None or
        remote["local_git_blob_sha1"] is not None):
        raise ValueError("WF0BM_MIXED_EDITION_OR_FAKE_LOCAL_SHIJI")
    local_raw = Path(fixture).read_bytes()
    actual_git_sha = _git_blob_sha1(local_raw)
    if actual_git_sha != local["local_git_blob_sha1"]:
        raise ValueError("WF0BM_LOCAL_FIXTURE_GIT_BLOB_SHA_CHANGED")
    local_text = local_raw.decode("utf8")
    identifiers = set()
    counts = {key: 0 for key in SOURCE_IDS}
    for item in data["cards"]:
        if type(item) is not dict or set(item) != CARD_FIELDS:
            raise ValueError("WF0BM_METHOD_CANDIDATE_SCHEMA_INVALID")
        key = item["id"]
        if key in identifiers or item["work_id"] not in sources:
            raise ValueError("WF0BM_CARD_DUPLICATE_OR_UNKNOWN_SOURCE")
        identifiers.add(key)
        counts[item["work_id"]] += 1
        anchor = item["source_anchor"]
        if (type(anchor) is not str or not 4 <= len(anchor) <= 30 or
            sha256(anchor.encode("utf8")).hexdigest() != item["source_anchor_sha256"]):
            raise ValueError("WF0BM_SOURCE_ANCHOR_SHA_MISMATCH")
        if (item["source_kind"] != "PUBLIC_DOMAIN_CLASSIC" or
            item["rights_status"] != "RIGHTS_UNVERIFIED" or
            item["review_status"] != "PENDING" or
            item["value_status"] != "UNVERIFIED" or
            item["review_receipt_sha256"] != "" or
            item["style_scope"] != "ERA_NEUTRAL" or
            type(item["literary_hypothesis"]) is not str or
            len(item["literary_hypothesis"]) < 15 or
            type(item["transfer_examples"]) is not list or
            not 1 <= len(item["transfer_examples"]) <= 3):
            raise ValueError("WF0BM_PROHIBITED_AUTO_APPROVAL_OR_EMPTY_TECHNIQUE")
        if (type(item["scene_facets"]) is not list or
            not 2 <= len(item["scene_facets"]) <= 5 or
            item["target_genres"] != ["玄幻"] or
            any(type(item[k]) is not str or not 8 <= len(item[k]) <= 180
                for k in ("signal","mechanism","writer_option","applies_when",
                          "not_when","pov_limit","counterexample"))):
            raise ValueError("WF0BM_UNBOUNDED_OR_UNCONDITIONAL_METHOD")
        if item["work_id"] == "xiyou-001":
            marker = item["local_fixture_anchor"]
            if type(marker) is not str or marker not in local_text:
                raise ValueError("WF0BM_LOCAL_ANCHOR_NOT_PRESENT_IN_ACTUAL_SOURCE")
        elif item["local_fixture_anchor"] is not None:
            raise ValueError("WF0BM_SHIJI_WAS_NOT_LOCALLY_STUDIED")
    if counts != {"xiyou-001":2,"shiji-007":2}:
        raise ValueError("WF0BM_UNBALANCED_PILOT_SOURCE_IDS")
    return data, sha256(raw).hexdigest(), sha256(local_raw).hexdigest()


def stage_isolated_classical_methods(*, output: Path = OUTPUT,
                                  catalog: Path = CANDIDATES) -> dict:
    output = Path(output)
    if output.exists():
        raise FileExistsError("WF0BM_ISOLATED_DB_NO_OVERWRITE")
    pack, pack_sha, fixture_sha = validate_catalog(catalog)
    output.parent.mkdir(parents=True,exist_ok=True)
    db = WriterForgeDB(output)
    rt = RuntimeEngine()
    rt.enter_learn()
    try:
        # This is REAL local source bytes and OriginalStudy, not a fabricated
        # chapter status. It remains a separate disposable test database.
        study = OriginalStudy(db,rt).ingest(
            OWNED_FIXTURE.read_text(encoding="utf8"),
            work_id=WORK_ID,title="西游记第001回·既有本地测试版本",
            source_uri=PINNED_FIXTURE_SOURCE_URI,
            require_hundred=False,max_chapters=1,
        )
        if (study["studied_chapters"] != 1 or
            study["source_sha256"] != fixture_sha or
            study["literary_reader_first_complete"] is not False):
            raise RuntimeError("WF0BM_REAL_LOCAL_CHAPTER_STUDY_INVALID")
        parent = db.conn.execute(
            "SELECT snapshot_id FROM studied_chapters WHERE work_id=?",
            (WORK_ID,),
        ).fetchone()["snapshot_id"]
        store = XuehaiStore(db,rt)
        sid = store.create_staging_snapshot(parent_id=parent,
            note="WF0BM_CLASSICAL_CANDIDATE_PENDING_EDITORIAL_RIGHTS")
        entries = []
        for card in pack["cards"]:
            if card["work_id"] != "xiyou-001":
                # Do not invent a studied_shiji chapter/entry without the
                # actual pinned digital text and edition permissions.
                continue
            matches = db.conn.execute(
                """SELECT * FROM source_spans
                     WHERE work_id=? AND instr(excerpt,?) > 0
                  ORDER BY chapter,paragraph,sentence LIMIT 2""",
                (WORK_ID,card["local_fixture_anchor"]),
            ).fetchall()
            if len(matches) != 1:
                raise RuntimeError("WF0BM_ANCHOR_NOT_UNIQUELY_LOCATABLE")
            span = matches[0]
            eid = store.add_entry(
                sid,work_id=WORK_ID,text=span["excerpt"],
                chapter=span["chapter"],
                paragraph=span["paragraph"],
                sentence=span["sentence"],
                library_class="原典文本结构来源·方法尚未获许可与审阅",
                culture="中国",genre="玄幻",
                source_role="classical_method_candidate",
                function=card["scene_type"],
                effect=card["mechanism"],
                method_cluster=card["id"],
                reuse_policy="technique_only",
            )
            payload = {name:card[name] for name in ADMISSION_FIELDS if name != "source_edition"}
            payload["source_edition"] = (
                "仅WF独立测试文本，尚未核定与维基文库固定修订的底本同一性"
            )
            receipt = store.add_method_card(eid,payload)
            entries.append((card["id"],eid,receipt["card_sha256"]))
        status = db.conn.execute(
            "SELECT status FROM snapshots WHERE id=?", (sid,)
        ).fetchone()["status"]
        cards = db.conn.execute(
            "SELECT COUNT(*) FROM xuehai_method_cards"
        ).fetchone()[0]
        eligible = db.conn.execute(
            """SELECT COUNT(*) FROM xuehai_method_cards
                WHERE rights_status='RIGHTS_VERIFIED'
                  AND review_status='PILOT_APPROVED'""",
        ).fetchone()[0]
        if status != "staging" or cards != 2 or eligible:
            raise RuntimeError("WF0BM_PENDING_CLASSIC_QUARANTINE_FAILED")
        db.conn.commit()
        return {
            "format":"wf.0bm.classical-source-anchored-STAGING-only.v1",
            "status":"REAL_LOCAL_FIXTURE_STUDIED_METHOD_CANDIDATES_NOT_ADMITTED",
            "source_catalog_sha256":pack_sha,
            "actual_local_fixture_sha256":fixture_sha,
            "local_fixture_git_blob_sha1":pack["sources"][0]["local_git_blob_sha1"],
            "local_structurally_studied_chapters_in_isolated_db":1,
            "actual_wikisource_revision_text_bytes_downloaded":0,
            "local_fixture_is_not_claimed_equivalent_to_wikisource":True,
            "original_scene_method_cards_staging":cards,
            "original_classics_reference_only_not_ingested":2,
            "pending_method_cards":cards,
            "production_eligible_classical_method_cards":eligible,
            "pending_staging_snapshot":sid,
            "published_source_study_snapshot":parent,
            "reviewer_authenticated_admissions":0,
            "new_author_model_calls":0,
            "new_modern_novel_reads":0,
            "private_r2_reads_or_writes":0,
            "production_canon_writes":0,
            "literary_gain_proven":False,
            "sources":[{"candidate_id":name,"entry_id":eid,
                        "card_sha256":sha} for name,eid,sha in entries],
        }
    finally:
        db.close()


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=OUTPUT)
    parser.add_argument("--catalog",type=Path,default=CANDIDATES)
    args=parser.parse_args()
    print(json.dumps(stage_isolated_classical_methods(
        output=args.output,catalog=args.catalog),
        ensure_ascii=False,indent=2,sort_keys=True))
