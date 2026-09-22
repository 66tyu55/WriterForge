import tempfile, unittest
from pathlib import Path
from writerforge import *
from writerforge.reader_learning import ReaderLearningSession, ReaderReaction, ReaderLearningError
from writerforge.cold_reader import build_cold_reader_payload
from writerforge.reader_effects import ReaderEffectLibrary

class V9ReaderLearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = WriterForgeDB(Path(self.tmp.name)/"v9.sqlite")
        self.rt = RuntimeEngine()
        self.rt.enter_learn()
        self.x = XuehaiStore(self.db,self.rt)
        self.sid = self.x.create_staging_snapshot()

    def tearDown(self):
        if self.rt.mode != Mode.IDLE:
            self.rt.exit()
        self.db.close()
        self.tmp.cleanup()

    def test_reader_learning_must_be_sequential(self):
        s = ReaderLearningSession(self.db,self.rt,"s1","work",self.sid,3)
        s.start()
        with self.assertRaises(ReaderLearningError):
            s.record_first_read(1,"p2",ReaderReaction(3,3,3))

    def test_craft_analysis_requires_first_read_trace(self):
        s = ReaderLearningSession(self.db,self.rt,"s2","work",self.sid,1)
        s.start()
        with self.assertRaises(ReaderLearningError):
            s.attach_craft_analysis(0,"fear","delay reveal")

    def test_first_read_then_analysis(self):
        s = ReaderLearningSession(self.db,self.rt,"s3","work",self.sid,1)
        s.start()
        s.record_first_read(0,"ch1-p1",ReaderReaction(
            attention=5,curiosity=5,urge_to_continue=5,
            fear=4,awe=3,tension=4,
            predictions=["门外不是人"],questions=["是什么东西？"],
            first_impression="危险但看不清",
            continue_reason="想知道门外是什么"
        ))
        s.attach_craft_analysis(0,"fear+curiosity","先声音、后轮廓、延迟命名","ch1-p1")
        s.finish()
        traj = s.trajectory()
        self.assertEqual(traj[0]["urge_to_continue"],5)

    def test_finish_requires_complete_read(self):
        s = ReaderLearningSession(self.db,self.rt,"s4","work",self.sid,2)
        s.start()
        s.record_first_read(0,"u0",ReaderReaction(3,3,3))
        with self.assertRaises(ReaderLearningError):
            s.finish()

    def test_page_turn_risk(self):
        s = ReaderLearningSession(self.db,self.rt,"s5","work",self.sid,1)
        s.start()
        s.record_first_read(0,"u0",ReaderReaction(
            attention=2,curiosity=1,urge_to_continue=1,
            confusion=4,cognitive_load=4
        ))
        self.assertEqual(len(s.page_turn_risks()),1)

    def test_cold_reader_payload_excludes_hidden_truth(self):
        p = build_cold_reader_payload(
            text_so_far="正文到这里",
            chapter_ref="ch3",
            prior_reader_questions=["师父真的死了吗？"]
        )
        self.assertIn("visible_text",p)
        self.assertNotIn("canon",p)
        self.assertNotIn("future_plan",p)
        self.assertNotIn("author_intent",p)

    def test_reader_effect_query_links_reaction_to_method(self):
        s = ReaderLearningSession(self.db,self.rt,"s6","work",self.sid,1)
        s.start()
        s.record_first_read(0,"u0",ReaderReaction(
            attention=5,curiosity=5,urge_to_continue=5,fear=4
        ))
        s.attach_craft_analysis(0,"fear","先给异常声音，再给不完整轮廓","u0",0.9)
        rows = ReaderEffectLibrary(self.db).query(effect="fear",min_continue=4)
        self.assertEqual(len(rows),1)
        self.assertIn("craft_mechanism",rows[0])

if __name__ == "__main__":
    unittest.main()
