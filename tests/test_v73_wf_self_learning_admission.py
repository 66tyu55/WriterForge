"""V73 WF-owned admission tests: synthetic novels only, NO study cheating."""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from writerforge.runtime import RuntimeEngine,Mode,RuntimeErrorState
from writerforge.wf_self_learning_admission import (
    admit_source,WFLearnAdmissionError,
)
ROOT="writerforge/v1/private-reading/"

class V73WFAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.path=Path(self.temp.name)/"source.txt"
        self.key=ROOT+"科幻/自带分类提示/原始内容.txt"
    def tearDown(self):
        self.temp.cleanup()
    def admit(self,text,*,encoding="utf-8",key=None,runtime=None):
        self.path.write_bytes(text.encode(encoding))
        raw=self.path.read_bytes()
        result=admit_source(
            self.path,original_key=key or self.key,
            verified_original_sha256=sha256(raw).hexdigest(),
            downloaded_size=len(raw),runtime=runtime)
        return result,raw

    def test_only_wf_owns_category_and_ordinals_not_external_tutor(self):
        text=("第1章 在雨中\n" + "夜风经过城市，一群人看向塔楼。\n"*48+
              "第2章 在城外\n" + "有人沿着石路前进，没有任何答案。\n"*43)
        status,original=self.admit(text)
        self.assertEqual(status["document_scan"]["chapters_detected"],2)
        self.assertEqual(status["first_chapter"]["ordinal"],1)
        self.assertEqual(status["first_chapter"]["printed_number"],1)
        self.assertEqual(status["hint_from_r2_folder_only"],"科幻")
        self.assertEqual(status["WF_genre_classification"],"UNDECIDED")
        self.assertEqual(status["learned_chapters"],0)
        self.assertFalse(status["WF_first_read_executed"])
        self.assertFalse(status["WF_literary_classification_executed"])
        self.assertFalse(status["WF_learning_checkpoint_persisted_to_r2"])
        self.assertFalse(status["assistant_selected_work"])
        self.assertEqual(status["model_calls"],0)
        self.assertEqual(status["remote_writes"],0)
        self.assertNotIn("夜风经过",str(status))
        self.assertNotIn("在雨中",str(status))
        self.assertEqual(original,self.path.read_bytes())

    def test_hint_from_folder_is_not_literary_genre_proof(self):
        text=("第1章 大雨\n"+"世界突然暗了下来。\n"*48+
              "第2章 风声\n"+"少年回头望了望四周。\n"*50)
        r,_=self.admit(text,key=ROOT+"历史/作者未知/正文.txt")
        self.assertEqual(r["hint_from_r2_folder_only"],"历史")
        self.assertFalse(r["WF_genre_classification_evidence"])
        self.assertEqual(r["WF_genre_classification"],"UNDECIDED")

    def test_printed_number_gap_stops_instead_of_faking_chapter_two(self):
        text="第1章 甲\n"+"短句重复，原文不改。\n"*45
        text+="第3章 乙\n"+"另一段内容继续。\n"*55
        with self.assertRaisesRegex(WFLearnAdmissionError,
                                     "NONCONSECUTIVE"):
            self.admit(text)

    def test_duplicate_chapter_numbers_stop(self):
        text="第1章 甲\n"+"第一章内容。\n"*65
        text+="第1章 乙\n"+"第二段内容。\n"*55
        with self.assertRaisesRegex(WFLearnAdmissionError,
                                     "DUPLICATE"):
            self.admit(text)

    def test_no_chapter_boundaries_does_not_fabricate_learning(self):
        text=("一个很长的故事开始了。\n"*150)
        with self.assertRaisesRegex(WFLearnAdmissionError,
                                     "NO_UNAMBIGUOUS"):
            self.admit(text)

    def test_text_hash_changed_since_worker_transfer_rejected(self):
        text="第1章 甲\n"+"内容丰富了一点。\n"*50
        text+="第2章 乙\n"+"中间发生了很多事情。\n"*50
        self.path.write_bytes(text.encode("utf-8"))
        with self.assertRaisesRegex(WFLearnAdmissionError,
                                    "SOURCE_CHANGED"):
            admit_source(self.path,original_key=self.key,
                         verified_original_sha256="0"*64,
                         downloaded_size=self.path.stat().st_size)

    def test_learn_write_mode_mutual_exclusion(self):
        text="第1章 起\n"+"人群四处奔跑。\n"*50
        text+="第2章 合\n"+"新的悬念出现了。\n"*50
        rt=RuntimeEngine()
        rt.enter_write(1)
        with self.assertRaises(RuntimeErrorState):
            self.admit(text,runtime=rt)
        self.assertEqual(rt.mode,Mode.WRITE)

    def test_lost_source_or_incorrect_length_fails_without_progress(self):
        self.path.write_bytes(b"x"*2000)
        with self.assertRaisesRegex(WFLearnAdmissionError,"SIZE_OR_FILE_INVALID"):
            admit_source(self.path,original_key=self.key,
                         verified_original_sha256=sha256(
                             self.path.read_bytes()).hexdigest(),
                         downloaded_size=3000)

    def test_five_hundred_long_chapters_do_not_become_skill_proof(self):
        chapter=("旅人停在山峰，观察着云层的变化。\n"*6)
        text="".join("第"+str(i)+"章 测试\n"+chapter
                     for i in range(1,501))
        status,raw=self.admit(text)
        self.assertEqual(status["document_scan"]["chapters_detected"],500)
        self.assertFalse(status["WF_skill_upgrade_certified"])
        self.assertEqual(status["learned_chapters"],0)

    def test_provisional_legacy_encoding_blocks_training(self):
        text=("第1章 出发\n"+"东方山脉吹来风声，远处传来了钟声。\n"*85+
              "第2章 决心\n"+"青石山路漫长，山林遍布大雾。\n"*85)
        status,_=self.admit(text,encoding="gb18030")
        self.assertEqual(status["decoding"],"gb18030")
        self.assertTrue(status["decoding_provisional"])
        self.assertEqual(
            status["training_gate"],
            "PROVISIONAL_ENCODING_REQUIRES_VERIFICATION")
        self.assertFalse(status["WF_first_read_executed"])

    def test_two_independent_heading_rules_disagree_requires_review(self):
        text=("第1章 初遇\n"+"旅人走过山道，耳边传来回声。\n"*60+
              "第2卷 不等于章节\n"+"这是一处可能为卷名的独立标记。\n"*60+
              "第2章 告别\n"+"这个章节暂时没有更多答案。\n"*60)
        doc,_=self.admit(text)
        self.assertEqual(doc["document_scan"]["legacy_sql_heading_candidates"],3)
        self.assertEqual(doc["document_scan"]["chapters_detected"],2)
        self.assertEqual(doc["document_scan"]["boundary_rule_disagreements"],1)
        self.assertEqual(len(doc["document_scan"]["disagreement_heading_hashes"]),1)
        self.assertEqual(doc["training_gate"],
                         "WF_CHAPTER_BOUNDARY_PARSERS_DISAGREE")
        self.assertEqual(doc["status"],
                         "WF_DOCUMENT_ADMISSION_REVIEW_REQUIRED")
        self.assertEqual(doc["learned_chapters"],0)

    def test_chinese_printed_numbers_are_read_but_not_guessed(self):
        text=("第一章 问路\n"+"陌生人徘徊在森林的边缘。\n"*65+
              "第二章 返回\n"+"另一名旅人从远处走来。\n"*65)
        doc,_=self.admit(text)
        self.assertEqual(doc["document_scan"]["numbered_chapters"],2)
        self.assertEqual(doc["first_chapter"]["printed_number"],1)
        self.assertEqual(doc["document_scan"]["boundary_rule_disagreements"],0)
        self.assertEqual(doc["learned_chapters"],0)

    def test_foreign_private_source_rejected(self):
        text=("第1章 起\n"+"听到远处的叫声。\n"*55+
              "第2章 止\n"+"道路变得更加狭窄。\n"*55)
        with self.assertRaises(Exception):
            self.admit(text,key="writerforge/v1/indexes/v1/unknown.txt")

if __name__=="__main__":
    unittest.main()
