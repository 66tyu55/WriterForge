"""WriterForge V76: independent, zero-model B00 admission batch and audit.

Examiner policy is frozen BEFORE the WF process sees actual R2 titles/body:
- exactly three genre-folder *hints*: 仙侠, 历史, 科幻;
- WF, not GPT, chooses at most two single-TXT candidates per hint by
  (size_bytes, SHA256(object_key)) from existing R2 metadata;
- no literary classification from folder hints;
- reject ambiguous chapter boundaries, volume restarts, provisional charset;
- no actual DeepSeek request and no LEARN record fabricated during B00;
- evidence consists of source fingerprints and failure codes, not prose.
B00 is a gate, NOT the learning batch or a certified book count.

Supervisor neither writes novel answers nor edits R2. Later batch phases
require a distinct, immutable R2 LEARN journal verified with reader-only
authority, usage receipts, external blind assessment and independent tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import re

from .bulk_inbox import BulkCatalog
from .private_reading_remote import WFPrivateReadingClient
from .private_r2_sql_smoke import candidate_sources,download_one_verified
from .wf_self_learning_admission import (
    admit_source,WFLearnAdmissionError,
)

WORKER="https://wf-r2-api.3227482831.workers.dev"
BATCH_ID="B00-20261019-WF-SELF-ADMISSION"
GENRES=("仙侠","历史","科幻")
SOURCE_BYTES_MIN=10*1024
SOURCE_BYTES_MAX=8*1024*1024
MAX_ATTEMPTS_PER_GENRE=2
MAX_SOURCES_DOWNLOADED=6
MAX_ORIGINAL_BYTES_READ=MAX_SOURCES_DOWNLOADED*SOURCE_BYTES_MAX
B01_FIRST_READ_MAX_BOOKS=1
B01_FIRST_READ_MAX_UNITS=3
B01_MAX_MODEL_CALLS=4
B01_MAX_RESERVED_OUTPUT_TOKENS=2000
NEXT_BATCH_MAX_BOOKS=3
NEXT_BATCH_CHAPTERS_PER_BOOK=1
SHA=re.compile(r"^[0-9a-f]{64}$")


class WFBatchAuditError(ValueError):
    pass


def check(ok,reason):
    if not ok:raise WFBatchAuditError(reason)


def stable_hash(text):
    return sha256(text.encode("utf-8")).hexdigest()


def canonical(doc):
    return json.dumps(doc,ensure_ascii=False,sort_keys=True,
                      separators=(",",":")).encode("utf-8")


@dataclass(frozen=True)
class BatchPlan:
    batch_id:str=BATCH_ID
    genres:tuple[str,...]=GENRES
    max_attempts_per_genre:int=MAX_ATTEMPTS_PER_GENRE
    max_source_bytes:int=SOURCE_BYTES_MAX
    max_downloads:int=MAX_SOURCES_DOWNLOADED

    def public_config(self):
        return {
           "batch_id":self.batch_id,
           "phase":"B00_DOCUMENT_ADMISSION_NO_PAID_LEARNING",
           "genre_hints":list(self.genres),
           "genre_hint_is_not_a_WF_genre_decision":True,
           "selection":"ONE_PER_HINT; SIZE_ASCENDING; KEY_SHA256_TIEBREAK",
           "candidate_fallbacks_only_if_prior_document_gate_failed":True,
           "max_attempts_per_genre":self.max_attempts_per_genre,
           "source_size_range_bytes":[SOURCE_BYTES_MIN,self.max_source_bytes],
           "max_downloads":self.max_downloads,
           "max_total_source_bytes":self.max_source_bytes*self.max_downloads,
           "real_model_calls":0,
           "r2_writes":0,
           "full_chapters_claimed_learned":0,
           "literary_categories_assigned_by_examiner":0,
           "next_phase":{
               "batch":"B01_ONE_BOOK_TWO_TO_THREE_UNITS_ONLY",
               "max_books":B01_FIRST_READ_MAX_BOOKS,
               "max_units":B01_FIRST_READ_MAX_UNITS,
               "max_model_calls":B01_MAX_MODEL_CALLS,
               "max_reserved_output_tokens":B01_MAX_RESERVED_OUTPUT_TOKENS,
               "requires_live_immutable_r2_learn_journal":True,
               "full_chapter_claimed":False,
           },
           "after_B01_if_independent_supervision_passes":{
               "batch":"B02_THREE_BOOKS_ONE_COMPLETE_CHAPTER_EACH",
               "max_books":NEXT_BATCH_MAX_BOOKS,
               "max_complete_chapters_per_book":NEXT_BATCH_CHAPTERS_PER_BOOK,
               "requires_full_source_coverage":True,
               "requires_breakpoint_resume":True,
               "requires_independent_blind_transfer":True,
               "not_auto_enabled":True,
           },
        }


def frozen_preselection(catalog:BulkCatalog,plan:BatchPlan=BatchPlan()):
    """Only R2 metadata, no original text. Deterministic under inventory."""
    check(isinstance(catalog,BulkCatalog),
          "WF_BATCH_METADATA_CATALOG_REQUIRED")
    rows=candidate_sources(catalog)
    selected={}
    count=0
    for genre in plan.genres:
        matching=[r for r in rows
                  if r["category"]==genre and
                  SOURCE_BYTES_MIN<=r["size_bytes"]<=plan.max_source_bytes]
        matching.sort(key=lambda r:(
            r["size_bytes"],stable_hash(r["object_key"])))
        selected[genre]=matching[:plan.max_attempts_per_genre]
        count+=len(selected[genre])
    check(count<=plan.max_downloads,
          "WF_BATCH_PRESELECTION_OVER_BUDGET")
    # Freeze the eligible Key hashes BEFORE actually decoding or reading any
    # source. GPT can verify the list SHA, but never selects individual books.
    anonymous=[
        {"hint":genre,
         "candidate_hashes":[stable_hash(row["object_key"])
                             for row in selected[genre]],
         "source_sizes":[row["size_bytes"]
                         for row in selected[genre]]}
        for genre in plan.genres
    ]
    return selected,{
        "preselection_digest_sha256":sha256(canonical(anonymous)).hexdigest(),
        "candidate_counts_by_hint":{
            x:len(selected[x]) for x in plan.genres},
        "candidates_anonymous":anonymous,
        "total_preselected_candidates":count,
        "preselection_before_content_read":True,
    }


def classify_admission(result):
    """Only procedural gate; never claim model-literary genre/mastery."""
    check(isinstance(result,dict),
          "WF_BATCH_ADMISSION_RESULT_MALFORMED")
    scan=result.get("document_scan")
    check(isinstance(scan,dict),
          "WF_BATCH_CHAPTER_SCAN_MISSING")
    blocked=list(result.get("training_gate_reasons") or [])
    reasons=[]
    if scan.get("boundary_rule_agreement") is not True or (
        scan.get("boundary_rule_disagreements",0) != 0
    ):
        reasons.append("CHAPTER_PARSERS_DISAGREE")
    if scan.get("duplicate_printed_numbers",0)>0 or (
        scan.get("printed_order_backward_or_equal_steps",0)>0
    ):
        reasons.append("PRINTED_CHAPTER_COLLISION_OR_RESET")
    if scan.get("printed_order_forward_gaps",0)>0:
        reasons.append("PRINTED_CHAPTER_GAPS")
    if result.get("decoding_provisional") is True:
        reasons.append("CHARSET_NOT_INDEPENDENTLY_VERIFIED")
    if scan.get("prelude_requires_review") is True:
        reasons.append("PRELUDE_NEEDS_REVIEW")
    if scan.get("chapters_detected",0)<2:
        reasons.append("INSUFFICIENT_CHAPTER_BOUNDARIES")
    if scan.get("chapters_with_unverified_numerals",0)>0:
        reasons.append("UNKNOWN_PRINTED_CHAPTER_NUMBERS")
    # Note: "WAITING_FOR_WF_MODEL..." is not a structural failure; it
    # remains the next explicit gate after source becomes suitable.
    check(result.get("WF_genre_classification")=="UNDECIDED" and
          result.get("learned_chapters")==0 and
          result.get("model_calls")==0 and
          result.get("remote_writes")==0 and
          result.get("WF_first_read_executed") is False,
          "WF_BATCH_FALSE_LEARNING_CLAIM")
    return {
        "structural_ready_for_later_WF_model":len(reasons)==0,
        "review_required":bool(reasons),
        "review_reasons":reasons,
        "source_hash_verified":bool(SHA.fullmatch(
            str(result.get("source_sha256","")))),
        "detected_chapter_candidates":scan["chapters_detected"],
        "legacy_candidate_headings":scan.get("legacy_sql_heading_candidates"),
        "no_literary_ability_claimed":True,
        "r2_learning_checkpoint_created":False,
    }


def preflight_one_batch(*,endpoint=WORKER,progress=None,
                        plan:BatchPlan=BatchPlan()):
    """Bounded real WF/Railway -> Worker -> private R2 metadata+source.

    Runs entirely inside WF's Python cloud process, never copies original
    source/keys to ChatGPT or GitHub. Every attempt uses a fresh tempfile.
    """
    def publish(stage):
        if progress:progress(stage)
    client=WFPrivateReadingClient(endpoint=endpoint,timeout=60)
    with TemporaryDirectory(prefix="wf-b00-batch-") as temporary:
        root=Path(temporary)
        catalog=BulkCatalog(root/"inventory.sqlite3")
        try:
            publish("WF_B00_METADATA_SCAN_STARTED")
            inventory=client.inventory_to_catalog(catalog)
            check(inventory.get("all_folders_complete") is True,
                  "WF_BATCH_INVENTORY_INCOMPLETE")
            selected,preselect=frozen_preselection(catalog,plan)
            publish("WF_B00_SELECTION_FROZEN_BEFORE_SOURCE_READ")
            total_bytes=0
            count=0
            out=[]
            for genre in plan.genres:
                attempts=[]
                winner=None
                for entry in selected[genre]:
                    check(count<plan.max_downloads,
                          "WF_BATCH_TOTAL_DOWNLOAD_COUNT_LIMIT")
                    sourcekey=entry["object_key"]
                    filename=root/("candidate-"+str(count+1)+".txt")
                    check(not filename.exists(),
                          "WF_BATCH_PRIVATE_TEMP_PATH_REUSED")
                    count+=1
                    public={
                       "hint":genre,
                       "key_sha256":stable_hash(sourcekey),
                       "size_bytes":entry["size_bytes"],
                       "source_edition_verified":False,
                       "literary_genre_WF_judged":False,
                       "fully_read_chapters":0,
                       "model_calls":0,
                       "r2_learning_writes":0,
                    }
                    try:
                        check(entry["size_bytes"] <= plan.max_source_bytes,
                              "WF_BATCH_SOURCE_TOO_LARGE")
                        transferred=download_one_verified(
                            client,entry,filename)
                        total_bytes+=transferred["bytes"]
                        check(total_bytes<=
                              plan.max_downloads*plan.max_source_bytes,
                              "WF_BATCH_CONTENT_BYTE_BUDGET")
                        study=admit_source(
                            filename,original_key=sourcekey,
                            verified_original_sha256=transferred["source_sha256"],
                            downloaded_size=transferred["bytes"],
                            source_etag=entry.get("etag"))
                        audit=classify_admission(study)
                        public.update({
                           "status":"STRUCTURE_READY" if
                                    audit["structural_ready_for_later_WF_model"]
                                    else "WAITING_FOR_WF_SELF_REVIEW",
                           "source_sha256":transferred["source_sha256"],
                           "source_bytes_verified":transferred["bytes"],
                           "audit":audit,
                        })
                        if audit["structural_ready_for_later_WF_model"]:
                            winner=public["key_sha256"]
                    except Exception as exc:
                        code=str(exc)
                        if not code.startswith(("WF_ADMISSION_",
                            "WF_BATCH_","WF_V71_","WF_PRIVATE_","BULK_")):
                            code="WF_BATCH_SOURCE_PREFLIGHT_UNVERIFIED"
                        public.update({"status":"SOURCE_REJECTED",
                                       "reason_code":code})
                    finally:
                        filename.unlink(missing_ok=True)
                    attempts.append(public)
                    publish("WF_B00_ONE_SOURCE_AUDITED_NO_MODEL")
                    if winner is not None:break
                out.append({
                  "genre_folder_hint":genre,
                  "tested_candidates":len(attempts),
                  "accepted_document_key_sha256":winner,
                  "works_literarily_classified":0,
                  "first_read_pass_a_started":False,
                  "admissions":attempts,
                })
            report={
               "status":"WF_B00_READ_ONLY_ADMISSION_AUDIT_COMPLETED",
               "format":"writerforge.batch-admission.v1",
               "batch_policy":plan.public_config(),
               "preselection":preselect,
               "r2_inventory_objects":inventory["total_objects"],
               "r2_inventory_source_sha_recorded":False,
               "number_of_source_files_tested":count,
               "total_source_bytes_read":total_bytes,
               "accepted_structure_candidates":sum(
                   x["accepted_document_key_sha256"] is not None
                   for x in out),
               "unverified_literary_genres":len(plan.genres),
               "audits":out,
               "paid_deepseek_calls":0,
               "r2_write_requests":0,
               "full_original_books_literarily_studied":0,
               "human_reader_reactions_claimed":False,
               "original_private_titles_or_prose_logged":False,
               "source_tempfiles_destroyed_after_return":True,
               "graduation_or_v49_status_changed":False,
            }
            report["batch_receipt_sha256"]=sha256(canonical(report)).hexdigest()
            return report
        finally:
            catalog.close()



@dataclass(frozen=True)
class ReaderOnlyR2Evidence:
    """Reader-only evidence reconstructed from real, immutable R2 events.

    NOT a dictionary copied from WF's self-report. Only proves protocol and
    source binding, not literary understanding or human emotional response.
    """
    source_sha256: str
    source_key_sha256: str
    chapter_body_sha256: str
    unit_count: int
    first_read_chain_sha256: str
    first_read_seal_sha256: str
    analysis_sha256: str
    protocol_verified_from_r2: bool
    independent_complete_chapter_coverage_verified: bool
    future_prompt_content_audited: bool
    provider_billing_reconciled: bool

    def public_receipt(self):
        return {
           "source_sha256":self.source_sha256,
           "source_key_sha256":self.source_key_sha256,
           "chapter_body_sha256":self.chapter_body_sha256,
           "unit_count":self.unit_count,
           "first_read_chain_sha256":self.first_read_chain_sha256,
           "first_read_seal_sha256":self.first_read_seal_sha256,
           "analysis_sha256":self.analysis_sha256,
           "reader_only_r2_evidence_verified":
              self.protocol_verified_from_r2,
           "full_chapter_coverage_verified":
              self.independent_complete_chapter_coverage_verified,
           "future_prompt_content_audited":
              self.future_prompt_content_audited,
           "provider_billing_reconciled":
              self.provider_billing_reconciled,
           "literary_quality_verified":False,
        }


def independently_recheck_r2_events(*,reader,original_key,
                                    original_sha256,chapter,
                                    chapter_body_sha256,
                                    source_unit_hashes:Sequence[str]):
    """Re-fetch ALL expected first-read/seal/analysis R2 events in order.

    The source-unit SHA list must come from a separate, reader-only parsing
    of the original text. Current V76 does NOT certify complete-chapter
    coverage or audit DeepSeek request prompts/billing yet.
    """
    from .r2_learn_journal import WFLearnJournal,identity
    check(isinstance(reader,WFLearnJournal) and
          reader.writer is None,
          "WF_SUPERVISOR_MUST_USE_R2_READER_ONLY_PROCESS")
    check(1<=len(source_unit_hashes)<=2000 and
          all(bool(SHA.fullmatch(str(x))) for x in source_unit_hashes),
          "WF_SUPERVISOR_EXPECTED_SOURCE_UNITS_MISSING")
    ident=identity(source_key=original_key,source_sha=original_sha256,
                   chapter=chapter,chapter_body_sha=chapter_body_sha256)
    expected_prev=None
    hashes=[]
    for i,known_unit_sha in enumerate(source_unit_hashes,1):
        saved=reader.fetch_event(ident=ident,stage="first_read",unit=i)
        check(saved is not None,"WF_SUPERVISOR_MISSING_R2_FIRST_READ_UNIT")
        record=saved["doc"]
        check(record["source_unit_sha256"]==known_unit_sha and
              record["previous_event_sha256"]==expected_prev and
              record["future_source_seen"] is False,
              "WF_SUPERVISOR_R2_FIRST_READ_SOURCE_OR_ORDER_CHANGED")
        expected_prev=saved["event_sha256"]
        hashes.append(expected_prev)
    seal=reader.fetch_event(ident=ident,stage="seal")
    check(seal is not None,"WF_SUPERVISOR_R2_PASS_A_SEAL_MISSING")
    check(seal["doc"]["units_read"]==len(source_unit_hashes) and
          seal["doc"]["last_first_read_sha256"]==hashes[-1] and
          seal["doc"]["future_source_seen"] is False,
          "WF_SUPERVISOR_R2_PASS_A_SEAL_NOT_CONSISTENT")
    analysis=reader.fetch_event(ident=ident,stage="analysis")
    check(analysis is not None,
          "WF_SUPERVISOR_R2_PASS_B_ANALYSIS_MISSING")
    check(analysis["doc"]["first_read_seal_sha256"]==
          seal["event_sha256"],
          "WF_SUPERVISOR_ANALYSIS_WITHOUT_LOCKED_FIRST_READ")
    for mechanism in analysis["doc"]["mechanisms"]:
        index=mechanism["unit"]-1
        check(0<=index<len(source_unit_hashes) and
              mechanism["evidence_unit_sha256"]==
              source_unit_hashes[index],
              "WF_SUPERVISOR_FAKE_SOURCE_EVIDENCE")
    return ReaderOnlyR2Evidence(
        source_sha256=original_sha256,
        source_key_sha256=ident["source_key_sha256"],
        chapter_body_sha256=chapter_body_sha256,
        unit_count=len(source_unit_hashes),
        first_read_chain_sha256=sha256(canonical(hashes)).hexdigest(),
        first_read_seal_sha256=seal["event_sha256"],
        analysis_sha256=analysis["event_sha256"],
        protocol_verified_from_r2=True,
        independent_complete_chapter_coverage_verified=False,
        future_prompt_content_audited=False,
        provider_billing_reconciled=False,
    )

def independent_claim_gate(*,registered_source_sha:str,
                           self_report:dict,reader_receipts:dict|None):
    """Independent examiner checks machine evidence, NEVER grades its prose.

    Fail closed when WF claims a completed chapter or mastery without exact
    source binding, an immutable signed PASS A, sequenced PASS B and usage.
    This is a protocol audit, NOT actual literary quality measurement.
    """
    check(bool(SHA.fullmatch(str(registered_source_sha))),
          "WF_SUPERVISOR_REGISTERED_ORIGINAL_HASH_INVALID")
    check(isinstance(self_report,dict),
          "WF_SUPERVISOR_INVALID_SELF_REPORT")
    if self_report.get("source_sha256")!=registered_source_sha:
        return {"verdict":"REJECTED","code":"SOURCE_SWITCHED"}
    if self_report.get("claims_mastery") is True or (
        self_report.get("literary_grade_raised") is True):
        return {"verdict":"REJECTED","code":"UNAUTHORIZED_SELF_PROMOTION"}
    if self_report.get("claims_complete_chapter") is not True:
        return {"verdict":"NO_COMPLETION_CLAIM",
                "code":"PARTIAL_EXPERIMENT_ONLY"}
    if reader_receipts is None:
        return {"verdict":"REJECTED","code":"NO_INDEPENDENT_R2_READ_RECEIPT"}
    if not isinstance(reader_receipts,ReaderOnlyR2Evidence):
        return {"verdict":"REJECTED","code":"UNTRUSTED_SELF_REPORTED_R2_CHECKS"}
    if (reader_receipts.source_sha256 != registered_source_sha or
        not reader_receipts.protocol_verified_from_r2):
        return {"verdict":"REJECTED","code":"R2_EVIDENCE_NOT_BOUND_TO_SOURCE"}
    if not reader_receipts.independent_complete_chapter_coverage_verified:
        return {"verdict":"REJECTED","code":"COMPLETE_CHAPTER_COVERAGE_NOT_PROVEN"}
    if not reader_receipts.future_prompt_content_audited:
        return {"verdict":"REJECTED","code":"FUTURE_SOURCE_EXPOSURE_NOT_AUDITED"}
    if not reader_receipts.provider_billing_reconciled:
        return {"verdict":"REJECTED","code":"PROVIDER_USAGE_NOT_RECONCILED"}
    return {
        "verdict":"PROCEDURE_PASSED_NOT_LITERARY_MASTERY",
        "independent_literary_transfer_test_still_required":True,
        "WF_promoted_to_next_literary_level":False,
    }
