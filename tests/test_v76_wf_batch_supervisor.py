"""V76 examiner batch admission/anti-cheating invariants (synthetic only)."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from writerforge.bulk_inbox import BulkCatalog
from writerforge.wf_batch_supervisor import (
   GENRES,BATCH_ID,SOURCE_BYTES_MAX,MAX_SOURCES_DOWNLOADED,
   BatchPlan,WFBatchAuditError,frozen_preselection,
   classify_admission,independent_claim_gate,
   independently_recheck_r2_events,ReaderOnlyR2Evidence,
)

PREFIX="writerforge/v1/private-reading/"


class IndependentBatchAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.catalog=BulkCatalog(Path(self.temp.name)/"metadata.sqlite3")
    def tearDown(self):
        self.catalog.close()
        self.temp.cleanup()
    def add(self,category,title,size=20000,ext=".txt"):
        key=PREFIX+category+"/"+title+"/正文"+ext
        self.catalog.register([{"key":key,"size":size,"etag":'"test-etag"'}])
        return key
    def test_batch_policy_fixed_three_books_but_only_after_admission(self):
        p=BatchPlan().public_config()
        self.assertEqual(p["batch_id"],BATCH_ID)
        self.assertEqual(GENRES,("仙侠","历史","科幻"))
        self.assertEqual(p["max_downloads"],6)
        self.assertEqual(p["max_total_source_bytes"],
                         MAX_SOURCES_DOWNLOADED*SOURCE_BYTES_MAX)
        self.assertEqual(p["real_model_calls"],0)
        self.assertEqual(p["full_chapters_claimed_learned"],0)
        self.assertEqual(p["next_phase"]["max_books"],1)
        self.assertFalse(p["next_phase"]["full_chapter_claimed"])
        self.assertEqual(
            p["after_B01_if_independent_supervision_passes"]["max_books"],3)
        self.assertTrue(
            p["after_B01_if_independent_supervision_passes"]["not_auto_enabled"])

    def test_deterministic_shortlist_no_key_or_private_text_in_summary(self):
        a=self.add("仙侠","第三本",size=19000)
        b=self.add("仙侠","第一本",size=11000)
        self.add("仙侠","第二本",size=15000)
        c=self.add("历史","古代史",size=12000)
        d=self.add("科幻","银河实验",size=17000)
        first,proof=frozen_preselection(self.catalog)
        second,again=frozen_preselection(self.catalog)
        self.assertEqual(first,second)
        self.assertEqual(proof,again)
        self.assertEqual([r["object_key"] for r in first["仙侠"]],
                         [b,PREFIX+"仙侠/第二本/正文.txt"])
        self.assertEqual(len(first["历史"]),1)
        self.assertEqual(len(first["科幻"]),1)
        self.assertEqual(proof["total_preselected_candidates"],4)
        self.assertNotIn("第一本",str(proof))
        self.assertNotIn("银河实验",str(proof))
        self.assertNotIn("古代史",str(proof))
        self.assertEqual(len(proof["preselection_digest_sha256"]),64)

    def test_archive_sibling_and_oversized_file_excluded(self):
        self.add("仙侠","坏的备份",size=12000)
        self.add("仙侠","坏的备份",size=12000,ext=".rar")
        self.add("仙侠","过大",size=SOURCE_BYTES_MAX+1)
        good=self.add("仙侠","独立原始书",size=22000)
        selected,proof=frozen_preselection(self.catalog)
        self.assertEqual([x["object_key"] for x in selected["仙侠"]],[good])
        self.assertEqual(proof["candidate_counts_by_hint"]["仙侠"],1)

    def _good_admission(self):
        return {
          "WF_genre_classification":"UNDECIDED",
          "WF_first_read_executed":False,
          "learned_chapters":0,"model_calls":0,"remote_writes":0,
          "source_sha256":"a"*64,
          "decoding_provisional":False,
          "training_gate_reasons":["WAITING_FOR_WF_MODEL_AND_IMMUTABLE_LEARN_JOURNAL"],
          "document_scan":{
             "chapter_boundaries_are_structural_candidates":True,
             "chapters_detected":10,
             "legacy_sql_heading_candidates":10,
             "boundary_rule_agreement":True,
             "boundary_rule_disagreements":0,
             "duplicate_printed_numbers":0,
             "printed_order_backward_or_equal_steps":0,
             "printed_order_forward_gaps":0,
             "prelude_requires_review":False,
             "chapters_with_unverified_numerals":0,
          },
        }
    def test_valid_structure_is_only_an_entry_gate(self):
        record=classify_admission(self._good_admission())
        self.assertTrue(record["structural_ready_for_later_WF_model"])
        self.assertFalse(record["r2_learning_checkpoint_created"])
        self.assertTrue(record["no_literary_ability_claimed"])

    def test_legacy_and_provisional_blocks_falsely_complete_text(self):
        broken=self._good_admission()
        broken["decoding_provisional"]=True
        broken["document_scan"]["boundary_rule_disagreements"]=4
        broken["document_scan"]["duplicate_printed_numbers"]=295
        broken["document_scan"]["printed_order_backward_or_equal_steps"]=3
        result=classify_admission(broken)
        self.assertFalse(result["structural_ready_for_later_WF_model"])
        self.assertIn("CHARSET_NOT_INDEPENDENTLY_VERIFIED",
                      result["review_reasons"])
        self.assertIn("CHAPTER_PARSERS_DISAGREE",
                      result["review_reasons"])
        self.assertIn("PRINTED_CHAPTER_COLLISION_OR_RESET",
                      result["review_reasons"])

    def test_wf_claiming_study_from_index_is_rejected(self):
        cheated=self._good_admission()
        cheated["learned_chapters"]=10
        with self.assertRaisesRegex(WFBatchAuditError,"FALSE_LEARNING"):
            classify_admission(cheated)

    def test_self_report_claimed_mastery_never_autopromotes(self):
        h="a"*64
        result=independent_claim_gate(
            registered_source_sha=h,self_report={
                "source_sha256":h,"claims_complete_chapter":True,
                "claims_mastery":True},reader_receipts={
                  "pass_a_immutable":True,"pass_a_units_complete":True,
                  "no_future_unit_exposure":True,"pass_b_after_seal":True,
                  "all_craft_refs_match_source":True,
                  "usage_within_pre_registered_budget":True,
                })
        self.assertEqual(result["verdict"],"REJECTED")
        self.assertEqual(result["code"],"UNAUTHORIZED_SELF_PROMOTION")

    def test_claim_without_r2_receipt_never_counts_complete_chapter(self):
        h="a"*64
        self_report={"source_sha256":h,"claims_complete_chapter":True}
        result=independent_claim_gate(
            registered_source_sha=h,self_report=self_report,
            reader_receipts=None)
        self.assertEqual(result["code"],"NO_INDEPENDENT_R2_READ_RECEIPT")

    def test_source_switch_detected_even_with_supposed_quality(self):
        result=independent_claim_gate(
            registered_source_sha="a"*64,
            self_report={"source_sha256":"b"*64,
                         "claims_complete_chapter":True},
            reader_receipts={})
        self.assertEqual(result["code"],"SOURCE_SWITCHED")



class ReaderOnlyExaminerNotSelfScoreTests(unittest.TestCase):
    def setUp(self):
        from writerforge.r2_learn_journal import (
           WFLearnJournal,identity,event_doc,canonical,hexdigest,
        )
        self.base_key=PREFIX+"仙侠/完全合成作品/正文.txt"
        self.src_hash="a"*64
        self.body_sha="b"*64
        self.unit_hashes=("c"*64,"d"*64)
        self.ident=identity(
            source_key=self.base_key,source_sha=self.src_hash,
            chapter=1,chapter_body_sha=self.body_sha,
        )
        self.records={}
        previous=None
        for i,h in enumerate(self.unit_hashes,1):
            event=event_doc(
                stage="first_read",ident=self.ident,unit=i,
                source_unit_sha256=h,
                previous_event_sha256=previous,
                future_source_seen=False,
                reaction={
                    "attention":3,"curiosity":4,"confusion":1,"tension":2,
                    "urge_to_continue":4,"question":"为什么？",
                    "prediction":"后面还有情节","what_changed":"多了一个问题",
                })
            previous=hexdigest(canonical(event))
            self.records[("first_read",i)]={
              "event_sha256":previous,"doc":event,
            }
        seal=event_doc(stage="seal",ident=self.ident,units_read=2,
                  last_first_read_sha256=previous,future_source_seen=False)
        seal_sha=hexdigest(canonical(seal))
        self.records[("seal",None)]={
            "event_sha256":seal_sha,"doc":seal,
        }
        analyst=event_doc(
            stage="analysis",ident=self.ident,
            first_read_seal_sha256=seal_sha,
            mechanisms=[{
                "unit":1,"evidence_unit_sha256":self.unit_hashes[0],
                "mechanism":"合成阅读机制",
                "reader_effect":"自述的阅读效果",
                "uncertainty":"不是人类的证明",
            }],
            independent_reviewed=False,
        )
        self.records[("analysis",None)]={
           "event_sha256":hexdigest(canonical(analyst)),"doc":analyst,
        }
        class Reader(WFLearnJournal):
            def __init__(self,records):
                super().__init__(
                    endpoint="https://synthetic.workers.dev",
                    reader_token="synthetic-reader-token-for-test-long-enough",
                    writer_token=None,
                    index_writer_token=None,
                )
                self.writer=None
                self.records=records
            def fetch_event(self,*,ident,stage,unit=None):
                return self.records.get((stage,unit))
        self.reader=Reader(self.records)

    def audit(self):
        return independently_recheck_r2_events(
            reader=self.reader,original_key=self.base_key,
            original_sha256=self.src_hash,
            chapter=1,chapter_body_sha256=self.body_sha,
            source_unit_hashes=self.unit_hashes,
        )

    def test_independent_r2_chain_rechecked_but_still_not_literary_mastery(self):
        result=self.audit()
        self.assertIsInstance(result,ReaderOnlyR2Evidence)
        self.assertTrue(result.protocol_verified_from_r2)
        self.assertEqual(result.unit_count,2)
        self.assertEqual(len(result.first_read_seal_sha256),64)
        self.assertFalse(result.independent_complete_chapter_coverage_verified)
        self.assertFalse(result.future_prompt_content_audited)
        self.assertFalse(result.provider_billing_reconciled)
        claim=independent_claim_gate(
            registered_source_sha=self.src_hash,
            self_report={"source_sha256":self.src_hash,
                         "claims_complete_chapter":True},
            reader_receipts=result)
        self.assertEqual(claim["code"],
                         "COMPLETE_CHAPTER_COVERAGE_NOT_PROVEN")

    def test_forged_all_green_flags_are_rejected(self):
        proof={k:True for k in (
            "pass_a_immutable","pass_a_units_complete",
            "no_future_unit_exposure","pass_b_after_seal",
            "all_craft_refs_match_source",
            "usage_within_pre_registered_budget",
        )}
        claim=independent_claim_gate(
            registered_source_sha=self.src_hash,
            self_report={"source_sha256":self.src_hash,
                         "claims_complete_chapter":True},
            reader_receipts=proof)
        self.assertEqual(claim["code"],
                         "UNTRUSTED_SELF_REPORTED_R2_CHECKS")

    def test_reader_only_role_cannot_be_replaced_by_writer(self):
        self.reader.writer="synthetic-writer-present"
        with self.assertRaisesRegex(WFBatchAuditError,
                                    "MUST_USE_R2_READER_ONLY"):
            self.audit()

    def test_modified_first_read_hash_must_fail_independent_check(self):
        self.records[("first_read",2)]["doc"][
            "source_unit_sha256"]="e"*64
        with self.assertRaisesRegex(WFBatchAuditError,
                                    "FIRST_READ_SOURCE_OR_ORDER_CHANGED"):
            self.audit()

    def test_changed_pass_a_seal_blocks_audit(self):
        self.records[("seal",None)]["doc"][
           "last_first_read_sha256"]="f"*64
        with self.assertRaisesRegex(WFBatchAuditError,
                                    "PASS_A_SEAL_NOT_CONSISTENT"):
            self.audit()

    def test_fake_pass_b_source_ref_blocks_audit(self):
        self.records[("analysis",None)]["doc"][
            "mechanisms"][0]["evidence_unit_sha256"]="f"*64
        with self.assertRaisesRegex(WFBatchAuditError,
                                    "FAKE_SOURCE_EVIDENCE"):
            self.audit()

if __name__=="__main__":
    unittest.main()
