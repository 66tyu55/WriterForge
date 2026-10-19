"""V81 independent 7-10 source/experience-chain examiner regressions.

Only fabricated chapters and an in-memory SHA content store. This DOES NOT
trigger GitHub Actions, real R2, DeepSeek billing, or any literary promotion.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from writerforge.wf_self_learning_admission import _scan_document
from writerforge.wf_b01_prefix_prepare import _split_into_ordered_units
from writerforge.v79_provisional_r2_cas_journal import WFProvisionalR2CASJournal
from writerforge.v80_large_chapter_batch import (
    WFLargeChapterBatch,pack,
)
from writerforge.v81_independent_exam import (
    examine_v81,WFV81ExamError,
)
from writerforge.r2_learn_journal import hexdigest
from test_v80_150k_batch import MemoryCAS,ArtificialWFModel

READER="synthetic-v81-reader-token-with-length"
WRITER="synthetic-v81-indexwriter-token-with-length"
KEY="writerforge/v1/private-reading/仙侠/合成八章材料/正文.txt"
SOURCE_SHA="5"*64
KEY_HASH=hexdigest(KEY.encode("utf8"))


class V81ExamEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary=TemporaryDirectory()
        self.source=Path(self.temporary.name)/"synthetic.txt"
        prose=[]
        for chapter in range(1,9):
            prose.append(
                f"第{chapter}章 合成测试\n"+
                (f"第{chapter}段合成小说中，人物走进院子，远处钟声改变了场景的感受。\n"*50)
            )
        self.source.write_text("".join(prose),encoding="utf-8")
        self.chapters,_=_scan_document(self.source,"utf-8")
        self.storage={}
        self.writer=WFProvisionalR2CASJournal(
            endpoint="https://wf-r2-api.synthetic.workers.dev",
            reader_token=READER,writer_token=WRITER)
        self.writer.vault=MemoryCAS(self.storage)
        # Simulate an immutable V80 chapter6 anchor and experienced strategy.
        self.prior_journal="b"*64
        self.prior_experience_doc={
           "format":"wf.learn.experience.v80",
           "source_sha256":SOURCE_SHA,
           "source_key_sha256":KEY_HASH,
           "chapter":6,
           "reflection":{"next_strategy":"观察声音出现之后人物是否改变动作"},
           "literary_quality_independently_verified":False,
        }
        self.prior_exp,_=self.writer._put_content(
            pack(self.prior_experience_doc))
        self.prior_batch_doc={
           "format":"wf.learn.150k-batch-progress.v80",
           "source_sha256":SOURCE_SHA,
           "source_key_sha256":KEY_HASH,
           "last_completed_chapter":6,
           "journal_checkpoint_sha256":self.prior_journal,
           "latest_experience_sha256":self.prior_exp,
           "mastery_graduation_approved":False,
        }
        self.prior_batch,_=self.writer._put_content(
            pack(self.prior_batch_doc))
        model=ArtificialWFModel()
        wf=WFLargeChapterBatch(
            journal=self.writer,model=model,
            original_key=KEY,source_sha=SOURCE_SHA,
            batch_id="WF-V81-CH7-10-150K")
        wf.last_batch_pointer=self.prior_batch
        wf.previous_experience_sha=self.prior_exp
        wf.earlier_strategy=self.prior_experience_doc[
            "reflection"]["next_strategy"]
        with self.source.open("r",encoding="utf8") as fh:
            for ch in self.chapters[6:8]:
                fh.seek(ch.start_cookie)
                parts=[]
                while fh.tell()<ch.end_cookie:
                    parts.append(fh.readline())
                windows=_split_into_ordered_units("".join(parts))
                wf.complete(chapter=ch,windows=windows)
        self.final_batch=wf.last_batch_pointer
        self.final_journal=self.writer.checkpoint_sha
        self.reader=WFProvisionalR2CASJournal(
            endpoint="https://wf-r2-api.synthetic.workers.dev",
            reader_token=READER,read_only=True)
        self.reader.vault=MemoryCAS(self.storage)
        self.reader.restore_pointer(self.final_journal)

    def tearDown(self):
        self.temporary.cleanup()

    def examine(self,**overrides):
        params={
           "reader":self.reader,
           "original_key":KEY,
           "source_sha":SOURCE_SHA,
           "source_path":self.source,
           "source_chapters":self.chapters,
           "final_batch_pointer":self.final_batch,
           "prior_v80_batch_pointer":self.prior_batch,
           "prior_v80_journal_pointer":self.prior_journal,
           "prior_chapter6_experience":self.prior_exp,
           "expected_start":7,
           "expected_end":8,
           "source_encoding":"utf-8",
        }
        params.update(overrides)
        return examine_v81(**params)

    def test_ch7_8_all_source_units_and_previous_experience_verified(self):
        evidence=self.examine()
        self.assertEqual(
            evidence["status"],
            "WF_V81_INDEPENDENT_R2_CH7_TO_10_PROVENANCE_PASSED")
        self.assertEqual(evidence["full_chapters_source_covered"],2)
        self.assertEqual(evidence["strict_pass_a_before_pass_b_chapters"],2)
        self.assertTrue(evidence["chapter6_experience_link_verified"])
        self.assertEqual([x["chapter"] for x in evidence["examined_chapters"]],
                         [7,8])
        self.assertFalse(
            evidence["actual_experience_improved_literary_quality_proven"])
        self.assertFalse(evidence["independent_literary_transfer_exam_passed"])
        self.assertEqual(evidence["model_calls_by_examiner"],0)

    def test_read_only_role_never_inherits_index_writer(self):
        self.reader.writer=WRITER
        with self.assertRaisesRegex(WFV81ExamError,"NOT_READER_ONLY"):
            self.examine()

    def test_original_chapter_tampering_fails_closed(self):
        original=self.source.read_text(encoding="utf8")
        self.source.write_text(
            original.replace("第7段合成", "第7段冒充",1),encoding="utf8")
        with self.assertRaisesRegex(
            WFV81ExamError,"ORIGINAL_CONTENT_CHANGED"):
            self.examine()

    def test_missing_first_read_unit_fails_closed(self):
        key=next(k for k in self.reader.event_addresses
                 if "/000007/first/000002.json" in k)
        del self.reader.event_addresses[key]
        with self.assertRaisesRegex(
            WFV81ExamError,"FIRST_READ_SKIPPED"):
            self.examine()

    def test_previous_experience_chain_does_not_allow_switch(self):
        with self.assertRaisesRegex(
            WFV81ExamError,"V80_CHAPTER6_ANCHOR_INVALID"):
            self.examine(prior_chapter6_experience="f"*64)

    def test_forged_extra_tokens_rejected_without_real_model_call(self):
        doc=json.loads(self.writer._get_content(self.final_batch))
        doc["reported_total_input_tokens"]=150001
        malicious,_=self.writer._put_content(pack(doc))
        with self.assertRaisesRegex(WFV81ExamError,"150K_BUDGET_INVALID"):
            self.examine(final_batch_pointer=malicious)

if __name__=="__main__":
    unittest.main()
