"""V80 independent examiner must reject forged chapter receipts (synthetic).

Use real WF source parser over invented two-chapter text; model and R2 CAS
are mocks. This is NOT a literary test or a live Cloudflare read.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from writerforge.r2_learn_journal import identity,hexdigest
from writerforge.v79_provisional_r2_cas_journal import WFProvisionalR2CASJournal
from writerforge.wf_b01_prefix_prepare import _split_into_ordered_units
from writerforge.wf_self_learning_admission import _scan_document
from writerforge.v80_large_chapter_batch import WFLargeChapterBatch
from writerforge.v80_independent_exam import (
    audit_extended_batch,WFReadOnlyExamError,
)
from test_v80_150k_batch import MemoryCAS,ArtificialWFModel,reaction

READER="synthetic-reader-long-enough-credential"
WRITER="synthetic-writer-long-enough-credential"
KEY="writerforge/v1/private-reading/仙侠/合成原著/正文.txt"
SOURCE_SHA="2"*64

class IndependentV80ChapterEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.path=Path(self.temp.name)/"source.txt"
        c1=("少年走进院落，听见有人在背后说话，故事没有给出答案。\n"*125)
        c2=("另一个人在城门口望向远处，他想到前一个章节的问题。\n"*92)
        text="第1章 开端\n"+c1+"第2章 转折\n"+c2
        self.path.write_text(text,encoding="utf8")
        chapters,scan=_scan_document(self.path,"utf-8")
        self.chapters=chapters
        self.u1=_split_into_ordered_units(c1)
        self.u2=_split_into_ordered_units(c2)
        self.assertGreater(len(self.u1),3)
        self.store={}
        self.journal=WFProvisionalR2CASJournal(
            endpoint="https://wf-r2-api.synthetic.workers.dev",
            reader_token=READER,writer_token=WRITER)
        self.journal.vault=MemoryCAS(self.store)
        ident=identity(source_key=KEY,source_sha=SOURCE_SHA,
                       chapter=1,chapter_body_sha=chapters[0].body_sha256)
        prev=None
        for i,unit in enumerate(self.u1[:3],1):
            rec=self.journal.append_first_read(
                ident=ident,unit=i,
                source_unit_sha=hexdigest(unit.encode()),
                previous_record_sha=prev,reaction=reaction())
            prev=rec["event_sha256"]
        seal=self.journal.seal_first_read(
            ident=ident,units=3,last_record_sha=prev)
        self.journal.append_analysis(
            ident=ident,first_read_seal_sha=seal["event_sha256"],
            mechanisms=[{"unit":1,
             "evidence_unit_sha256":hexdigest(self.u1[0].encode()),
             "mechanism":"早期试验",
             "reader_effect":"尚未读全章",
             "uncertainty":"仅三单位"}])
        model=ArtificialWFModel()
        self.batch=WFLargeChapterBatch(
            journal=self.journal,model=model,
            original_key=KEY,source_sha=SOURCE_SHA)
        self.batch.complete(chapter=chapters[0],windows=self.u1)
        self.batch.complete(chapter=chapters[1],windows=self.u2)
        self.reader=WFProvisionalR2CASJournal(
            endpoint="https://wf-r2-api.synthetic.workers.dev",
            reader_token=READER,read_only=True)
        self.reader.vault=MemoryCAS(self.store)
        self.reader.restore_pointer(self.journal.checkpoint_sha)

    def tearDown(self):
        self.temp.cleanup()

    def run_audit(self):
        return audit_extended_batch(
            self.reader,source_path=self.path,
            original_key=KEY,source_sha256=SOURCE_SHA,
            chapters=self.chapters,
            last_batch_sha=self.batch.last_batch_pointer)

    def test_independent_examination_source_coverage_and_mixed_pilot(self):
        result=self.run_audit()
        self.assertEqual(result["source_complete_chapters"],2)
        self.assertEqual(result["clean_pass_a_before_pass_b_chapters"],1)
        self.assertEqual(result["verified_chapters"][0]["signed_source_units"],
                         len(self.u1))
        self.assertEqual(result["verified_chapters"][1]["signed_source_units"],
                         len(self.u2))
        self.assertFalse(result["literary_mastery_certified"])
        self.assertFalse(result["DeepSeek_dashboard_fee_reconciled"])

    def test_tampered_original_fails_by_sha_comparison(self):
        changed=self.path.read_text(encoding="utf8").replace(
            "少年走进院落","游客走进院落",1)
        self.path.write_text(changed,encoding="utf8")
        with self.assertRaisesRegex(WFReadOnlyExamError,
                                     "CHAPTER_BODY_SHA_FAILED"):
            self.run_audit()

    def test_exam_requires_reader_only_authority(self):
        self.reader.read_only=False
        with self.assertRaisesRegex(WFReadOnlyExamError,
                                    "READER_NOT_READ_ONLY"):
            self.run_audit()

if __name__=="__main__":
    unittest.main()
