"""0.BO pinned Gutenberg #23962 chapter-1 source -> same XuehaiStore -> PENDING review.

Only one *public, immutable* Git-hosted source is supported. Do not use this
to scrape other books, access R2, publish production methods, or call a model.
Full source bytes remain ephemeral and are NOT committed to WriterForge.
The attached review packet is for real external reviewers, NOT an approval.
"""
from __future__ import annotations

import argparse
from hashlib import sha1, sha256
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

from writerforge import WriterForgeDB, RuntimeEngine, OriginalStudy, XuehaiStore
from writerforge.source_study import parse_original
from experiments.wf_0bm_stage_first_classical_method_candidates import (
    CANDIDATES as CARDS_SOURCE,
    validate_catalog,
)

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"experiments/wf_0bo_pinned_gutenberg_23962_source_manifest_20261028.json"
MAX_PUBLIC_SOURCE_BYTES=3_000_000
WORK_ID="wf0bo-pinned-gutenberg-23962-ch1-isolated"
METHOD_CARD_FIELDS=(
    "scene_type","scene_facets","target_genres","style_scope",
    "signal","mechanism","writer_option","applies_when","not_when",
    "pov_limit","counterexample","source_kind","rights_status",
    "review_status","value_status","review_receipt_sha256",
)
RAW_SHA256="fc9a3956fd22b9a4356af8dd0dca27596fd0c9da87c35eae45c4f331c1b8f597"
BLOB_SHA1="b43d48dae12142a6e8707dcb68938d86beeb51e8"
NORMALIZED_SHA256="a6826b4a110e45bc47e5b94098611140fd58e7a07b7823ea4388e385898fa2f8"
FIRST_CHAPTER_SHA256="d70a073cb4482f4e1edcbdff924f371b8e3e68c0eaf24d05d0c2c32ae6b3a86f"
PINNED_COMMIT="6a0cca862cda18eefa8a3264372893308432e926"
PINNED_URL=("https://raw.githubusercontent.com/GITenberg/---_23962/"
            +PINNED_COMMIT+"/23962-0.txt")
SOURCE_BYTES=2264071


def load_source_manifest(path:Path=MANIFEST)->tuple[dict,str]:
    raw=Path(path).read_bytes()
    if len(raw)>12000:
        raise ValueError("WF0BO_PROVENANCE_MANIFEST_TOO_BIG")
    data=json.loads(raw)
    expected={
        "format":"wf.0bo.pinned-project-gutenberg-digital-source.v1",
        "status":"PUBLIC_DIGITAL_FILE_HASH_VERIFIED_REVIEW_PENDING",
        "gutenberg_ebook_number":23962,
        "pinned_git_commit":PINNED_COMMIT,
        "pinned_raw_source_uri":PINNED_URL,
        "pinned_git_blob_sha1":BLOB_SHA1,
        "raw_source_size_bytes":SOURCE_BYTES,
        "raw_source_sha256":RAW_SHA256,
        "normalized_source_sha256":NORMALIZED_SHA256,
        "first_chapter_sha256":FIRST_CHAPTER_SHA256,
        "chapter_count_in_pinned_version":100,
        "staged_chapters_per_pilot":1,
        "public_source_text_committed_to_writerforge":False,
        "full_source_republished":False,
        "actual_external_human_reviewers":0,
        "actual_literary_model_calls":0,
        "production_xuehai_changes":0,
        "actual_unverified_methods_published_to_writer":False,
        "rights_and_craft_status":"PENDING_EXTERNAL_REVIEW",
        "reviewer_keys_or_signatures_in_repo":False,
        "literary_benefit_proven":False,
        "same_bytes_as_existing_local_fixture":False,
        "scope":"DISPOSABLE_DB_STAGING_ONLY",
    }
    if type(data) is not dict or any(data.get(k)!=v for k,v in expected.items()):
        raise ValueError("WF0BO_SOURCE_IDENTITY_OR_PERMISSION_CLAIM_CHANGED")
    refs=data.get("method_source_pairing")
    if (type(refs) is not list or len(refs)!=2 or
        {r.get("method_id") for r in refs}!={"classic-xiyou-001-cave-pledge",
                                         "classic-xiyou-001-woodcutter"} or
        any(type(r.get("source_anchor")) is not str or
            not 5<=len(r["source_anchor"])<=25 for r in refs)):
        raise ValueError("WF0BO_UNTRUSTED_METHOD_SOURCE_PAIRING")
    return data,sha256(raw).hexdigest()


def pin_source_bytes(raw:bytes)->tuple[str,dict]:
    """Verify actual byte identity BEFORE parsing or creating any database."""
    if type(raw) is not bytes or len(raw)!=SOURCE_BYTES:
        raise ValueError("WF0BO_SOURCE_BYTE_LENGTH_DRIFT")
    digest=sha256(raw).hexdigest()
    blob=sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()
    if digest!=RAW_SHA256 or blob!=BLOB_SHA1:
        raise ValueError("WF0BO_SOURCE_RAW_SHA256_OR_BLOB_DRIFT")
    text=raw.decode("utf-8-sig").replace("\r\n","\n").replace("\r","\n")
    if sha256(text.encode("utf8")).hexdigest()!=NORMALIZED_SHA256:
        raise ValueError("WF0BO_SOURCE_NORMALIZATION_CHANGED")
    chapters=parse_original(text,require_hundred=True,expected_count=100)
    if chapters[0].fingerprint!=FIRST_CHAPTER_SHA256 or chapters[0].number!=1:
        raise ValueError("WF0BO_FIRST_CHAPTER_SHA_CHANGED")
    return text, {
        "git_commit":PINNED_COMMIT,
        "raw_sha256":digest,
        "git_blob_sha1":blob,
        "normalized_sha256":NORMALIZED_SHA256,
        "chapter_1_sha256":chapters[0].fingerprint,
        "actual_chapter_count":len(chapters),
        "source_bytes":len(raw),
        "source_entire_text_republished":False,
    }


# A source can have a valid SHA and still contain an editorial defect.
# This looks like a repeated opening cosmology paragraph in the pinned
# Gutenberg transcription; another existing local edition has it once.
# NEVER silently repair or pretend to have authenticated a print edition.
SUSPECT_DUPLICATE_TRAD=(
    "至此，地始凝結。再五千四百歲，正當丑會，"
    "重濁下凝，有水，有火，有山，有石，有土。"
)
SUSPECT_DUPLICATE_SIMPLIFIED=(
    "至此，地始凝结。再五千四百岁，正当丑会，"
    "重浊下凝，有水，有火，有山，有石，有土。"
)
OTHER_EDITION_LOCAL_FIXTURE=ROOT/"tests/fixtures/xiyouji_chapter_001_original_zh.txt"
OTHER_EDITION_SHA256="e3d137b317f2996805bbd6aa84abf47395a94dfbd2397324c1b9e9db157f2628"


def audit_source_quality(text:str,method_anchors:tuple[str,...])->dict:
    """Known source inconsistency evidence, not a transcription correction."""
    chapter=parse_original(text,require_hundred=True,expected_count=100)[0].text
    compact=re.sub(r"\\s+","",chapter)
    repeated=[m.start() for m in re.finditer(re.escape(SUSPECT_DUPLICATE_TRAD),compact)]
    other=OTHER_EDITION_LOCAL_FIXTURE.read_bytes()
    if sha256(other).hexdigest()!=OTHER_EDITION_SHA256:
        raise ValueError("WF0BO_INDEPENDENT_REFERENCE_VERSION_CHANGED")
    local=other.decode("utf8")
    local_count=len(list(re.finditer(
        re.escape(SUSPECT_DUPLICATE_SIMPLIFIED),
        re.sub(r"\\s+","",local))))
    if len(repeated)!=2 or local_count!=1:
        raise ValueError("WF0BO_SOURCE_DUPLICATION_FINDING_CHANGED_REVIEW_REQUIRED")
    # Quarantine *a bounded context around the repeated paragraph*, without
    # modifying or deleting any original bytes. Do not admit a method anchored
    # to the questionable area. An unaffected later scene can still be reviewed.
    affected=[]
    for anchor in method_anchors:
        at=compact.find(re.sub(r"\\s+","",anchor))
        if at<0:
            raise ValueError("WF0BO_METHOD_ANCHOR_NOT_IN_SOURCE_QUALITY_AUDIT")
        if any(p-40<=at<=p+260 for p in repeated):
            affected.append(anchor)
    return {
        "status":"SOURCE_DUPLICATION_SUSPECT_REQUIRES_REVIEW",
        "duplicate_phrase_occurrences":len(repeated),
        "duplicate_pattern_sha256":sha256(
            SUSPECT_DUPLICATE_TRAD.encode("utf8")).hexdigest(),
        "repeated_compact_character_positions":repeated,
        "other_local_edition_occurrences":local_count,
        "other_local_edition_sha256":OTHER_EDITION_SHA256,
        "method_card_anchors_affected":affected,
        "human_source_quality_review_complete":False,
        "source_bytes_edited":False,
        "source_not_certified_identical_to_print_base":True,
        "production_method_activation":False,
    }


def download_exact_source(output:Path)->Path:
    """Only allow the pinned public GitHub raw URL; no arbitrary download."""
    output=Path(output)
    if output.exists():
        raise FileExistsError("WF0BO_EXISTING_SOURCE_REFUSED")
    output.parent.mkdir(parents=True,exist_ok=True)
    part=output.with_name(output.name+".partial")
    try:
        req=Request(PINNED_URL,headers={"User-Agent":"WriterForge-0BO-pinned-public-provenance/1"})
        with urlopen(req,timeout=45) as response:
            if response.geturl()!=PINNED_URL:
                raise ValueError("WF0BO_SOURCE_REDIRECT_REJECTED")
            raw=response.read(MAX_PUBLIC_SOURCE_BYTES+1)
        if len(raw)>MAX_PUBLIC_SOURCE_BYTES:
            raise ValueError("WF0BO_SOURCE_TOO_LARGE")
        pin_source_bytes(raw)
        part.write_bytes(raw)
        part.replace(output)
        return output
    finally:
        part.unlink(missing_ok=True)


def stage_pinned_first_chapter(source:Path,db_path:Path,
                               review_dir:Path)->dict:
    """Creates a disposable DB and an unsigned reviewer-only packet."""
    db_path=Path(db_path);review_dir=Path(review_dir)
    if db_path.exists() or review_dir.exists():
        raise FileExistsError("WF0BO_OUTPUT_EXISTS_NO_REPLAY")
    manifest,manifest_sha=load_source_manifest()
    candidates,_cat_sha,_fixture_sha=validate_catalog(CARDS_SOURCE)
    text,source_identity=pin_source_bytes(Path(source).read_bytes())
    quality=audit_source_quality(
        text,tuple(ref["source_anchor"]
                   for ref in manifest["method_source_pairing"]))
    if quality["method_card_anchors_affected"]:
        raise ValueError("WF0BO_METHOD_OVERLAPS_SUSPECT_SOURCE_DUPLICATION")
    db_path.parent.mkdir(parents=True,exist_ok=True)
    db=WriterForgeDB(db_path)
    rt=RuntimeEngine();rt.enter_learn()
    try:
        study=OriginalStudy(db,rt).ingest(
            text,work_id=WORK_ID,
            title="西游记·GITenberg固定原件·第001回隔离研究",
            source_uri=PINNED_URL,
            max_chapters=1,require_hundred=True,expected_count=100,
            wrapped_lines=True,
        )
        if (study["source_sha256"]!=NORMALIZED_SHA256 or
            study["studied_chapters"]!=1 or
            study["literary_reader_first_complete"] is not False):
            raise ValueError("WF0BO_ORIGINAL_STUDY_DID_NOT_COMPLETE")
        parent=db.conn.execute(
            "SELECT snapshot_id FROM studied_chapters WHERE work_id=?",
            (WORK_ID,),
        ).fetchone()["snapshot_id"]
        source_cards={v["id"]:v for v in candidates["cards"]}
        source_store=XuehaiStore(db,rt)
        child=source_store.create_staging_snapshot(
            parent_id=parent,note="WF0BO_SOURCE_VERIFIED_CLASSIC_METHODS_PENDING")
        reviewer_rows=[]
        for ref in manifest["method_source_pairing"]:
            method=source_cards[ref["method_id"]]
            anchor=ref["source_anchor"]
            spans=db.conn.execute(
                """SELECT * FROM source_spans
                    WHERE work_id=? AND chapter=1 AND instr(excerpt,?)>0
                    ORDER BY paragraph,sentence LIMIT 3""",
                (WORK_ID,anchor),
            ).fetchall()
            if len(spans)!=1:
                raise ValueError("WF0BO_CANDIDATE_ANCHOR_NOT_UNIQUE_IN_STUDIED_SOURCE")
            span=spans[0]
            entry=source_store.add_entry(
                child,work_id=WORK_ID,
                text=span["excerpt"],
                chapter=span["chapter"],paragraph=span["paragraph"],
                sentence=span["sentence"],
                culture="中国",genre="玄幻",source_role="classical_method_candidate",
                library_class="公有领域原文·方法尚未人工审阅",
                function=method["scene_type"],effect=method["mechanism"],
                method_cluster=method["id"],reuse_policy="technique_only",
            )
            data={key:method[key] for key in METHOD_CARD_FIELDS}
            data["source_edition"]=(
                "GITenberg #23962 commit 6a0cca8 - 具体印刷底本未证实"
            )
            result=source_store.add_method_card(entry,data)
            reviewer_rows.append({
                "format":"wf.0bo.external-review-unsigned.v1",
                "method_id":method["id"],
                "entry_id":entry,"snapshot_id":child,
                "parent_published_study_snapshot":parent,
                "card_sha256":result["card_sha256"],
                "source_uri":PINNED_URL,
                "source_raw_sha256":RAW_SHA256,
                "source_normalized_sha256":NORMALIZED_SHA256,
                "source_chapter_sha256":FIRST_CHAPTER_SHA256,
                "source_unit_sha256":span["source_sha256"],
                "source_locator":{
                    "chapter":span["chapter"],
                    "paragraph":span["paragraph"],
                    "sentence":span["sentence"],
                },
                # Public-domain historical excerpt ONLY for reviewer. Never
                # enter real author prompt or serialize private R2 contents.
                "short_review_excerpt_only":span["excerpt"][:100],
                "source_anchor":anchor,
                "scene_type":method["scene_type"],
                "scene_facets":method["scene_facets"],
                "mechanism":method["mechanism"],
                "writer_option":method["writer_option"],
                "applies_when":method["applies_when"],
                "not_when":method["not_when"],
                "pov_limit":method["pov_limit"],
                "counterexample":method["counterexample"],
                "rights_status":"RIGHTS_UNVERIFIED",
                "review_status":"PENDING",
                "value_status":"UNVERIFIED",
                "rights_reviewer_completed":False,
                "literary_reviewer_completed":False,
                "signed_rights_authorization":None,
                "signed_craft_approval":None,
                "production_admission":False,
            })
        if db.conn.execute("SELECT COUNT(*) FROM xuehai_method_cards").fetchone()[0]!=2:
            raise ValueError("WF0BO_CARD_COUNT_WRONG")
        if db.conn.execute(
            "SELECT COUNT(*) FROM xuehai_method_attestations"
        ).fetchone()[0]!=0:
            raise ValueError("WF0BO_UNAUTHORIZED_REVIEW_SIGNATURE_PRESENT")
        if db.conn.execute(
            "SELECT status FROM snapshots WHERE id=?",(child,)
        ).fetchone()["status"]!="staging":
            raise ValueError("WF0BO_STAGING_NOT_PRESERVED")
        evidence={
            "format":"wf.0bo.first-chapter-real-source-structural-study.v1",
            "status":"ONE_TRUE_PINNED_CLASSICAL_EDITION_STUDIED_METHODS_PENDING",
            "source_identity":source_identity,
            "source_quality_audit":quality,
            "source_manifest_sha256":manifest_sha,
            "source_work_id":WORK_ID,
            "actual_original_chapters_structurally_studied":1,
            "source_spans":study["studied_units"],
            "published_source_snapshot":parent,
            "unpublished_candidate_snapshot":child,
            "pending_method_cards":len(reviewer_rows),
            "real_externally_signed_reviewers":0,
            "write_admissible_method_cards":0,
            "model_calls":0,
            "model_weight_training":False,
            "production_canon_writes":0,
            "r2_private_reads_or_writes":0,
            "literary_benefit_proven":False,
            "digital_source_is_not_identical_to_old_local_fixture":True,
            "review_packet_has_truncated_public_domain_excerpts_only":True,
        }
        review_dir.mkdir(parents=True,exist_ok=False)
        (review_dir/"REVIEW_PACKET.json").write_text(
            json.dumps({
                "status":"PENDING_TWO_REAL_EXTERNAL_REVIEWERS",
                "source_identity":source_identity,
                "source_quality_audit":quality,
                "cases":reviewer_rows,
                "has_authenticated_human_review":False,
                "does_not_confer_permissions":True,
                "no_production_use":True,
            },ensure_ascii=False,sort_keys=True,indent=2)+"\n",
            encoding="utf8",
        )
        guide=(
            "# 0.BO 来源和方法外部审阅材料（不可自动审批）\n\n"
            "固定数字原件："+PINNED_URL+"\n\n"
            "Project Gutenberg 美国公有领域声明：https://www.gutenberg.org/ebooks/23962\n\n"
            "许可和商标说明：https://www.gutenberg.org/policy/permission.html\n\n"
            "**此包尚无真人签名，不表示可直接用于生产 WRITE。**\n\n"            "已发现固定电子原件第一回开篇存在一段疑似转录重复；另一份既有测试"
            "文本中对应段落仅出现一次。请审阅源内容差异；不得直接修改原文，也不得"
            "因 SHA 正确就宣称文本已校勘。当前两条方法锚点不在疑似重复区域。\n\n"
            "权利审核者必须独立检查：真实数字版本、使用地域和商标/许可、源指纹、"
            "当前用途是否属于隔离方法研究；不能用未确认的现代排版/整理版权假设代替检查。\n\n"
            "文学方法审核者必须逐条检查：来源句段确实发生了何种选择、"
            "源中并未发生的事是否被错写、转移机制的具体触发和禁用条件、"
            "反例是否真的能使结论失败，是否会压制作者的自由。\n\n"
            "两名具备独立信任根的审核者需在自己的受控环境中分别签署限定范围"
            " ISOLATED_WRITE_PILOT_ONLY 的 XuehaiMethodAdmission 原始 challenge。"
            "本文不是签名工具，不生成密钥，不产生合成审批。\n"
        )
        (review_dir/"REVIEW_GUIDE.md").write_text(guide,encoding="utf8")
        (review_dir/"SOURCE_RECEIPT.json").write_text(
            json.dumps(evidence,ensure_ascii=False,sort_keys=True,indent=2)+"\n",
            encoding="utf8")
        return evidence
    finally:
        db.close()


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--db",type=Path,required=True)
    p.add_argument("--review-dir",type=Path,required=True)
    p.add_argument("--download",action="store_true")
    args=p.parse_args()
    if args.download:
        download_exact_source(args.source)
    result=stage_pinned_first_chapter(args.source,args.db,args.review_dir)
    print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
