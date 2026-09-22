import tempfile
from pathlib import Path
import unittest
from writerforge import *
from writerforge.runtime import RuntimeErrorState
from writerforge.xuehai import Query

class WriterForgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = WriterForgeDB(Path(self.tmp.name)/"test.sqlite")
        self.runtime = RuntimeEngine()
        self.x = XuehaiStore(self.db, self.runtime)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def _published(self):
        self.runtime.enter_learn()
        sid = self.x.create_staging_snapshot()
        self.x.add_entry(
            sid, work_id="w", text="风吹动窗纸。",
            genre="玄幻", culture="中国", function="environment",
            effect="unease", method_cluster="environment-change", quality_weight=2
        )
        self.x.publish(sid)
        self.runtime.exit()
        return sid

    def test_runtime_mutual_exclusion(self):
        self.runtime.enter_learn()
        with self.assertRaises(RuntimeErrorState):
            self.runtime.enter_write(1)

    def test_write_cannot_mutate_xuehai(self):
        sid = self._published()
        self.runtime.enter_write(sid)
        with self.assertRaises(RuntimeErrorState):
            self.x.add_entry(sid, work_id="w", text="非法写入")

    def test_learn_cannot_write_story(self):
        self.runtime.enter_learn()
        story = StoryStore(self.db, self.runtime, "p")
        with self.assertRaises(RuntimeErrorState):
            story.add_canon("F1","fact","x")

    def test_snapshot_must_be_published(self):
        self.runtime.enter_learn()
        sid = self.x.create_staging_snapshot()
        self.runtime.exit()
        self.runtime.enter_write(sid)
        with self.assertRaises(ValueError):
            self.x.query(Query())

    def test_query_returns_adapted_evidence(self):
        sid = self._published()
        self.runtime.enter_write(sid)
        rows = self.x.query(Query(function="environment"))
        self.assertEqual(len(rows), 1)
        self.assertIn("evidence_excerpt", rows[0])
        self.assertNotIn("text", rows[0])

    def test_knowledge_conflict_validator(self):
        sid = self._published()
        self.runtime.enter_write(sid)
        story = StoryStore(self.db, self.runtime, "p")
        story.set_character("c", {
            "knowledge":{"knows":["secret"],"does_not_know":["secret"]}
        })
        findings = ValidatorSuite(self.db, "p").run_all()
        self.assertTrue(any(f.code == "KNOWLEDGE_CONFLICT" for f in findings))

    def test_causality_validator(self):
        sid = self._published()
        self.runtime.enter_write(sid)
        story = StoryStore(self.db, self.runtime, "p")
        story.add_causal_event("E", {"cause":"x"})
        findings = ValidatorSuite(self.db, "p").run_all()
        self.assertTrue(any(f.code == "MISSING_TRIGGER" for f in findings))

    def test_middleware_delta(self):
        sid = self._published()
        self.runtime.enter_write(sid)
        m = ReactiveMiddleware(self.x)
        first = m.react({"scene.location":"山门外"})
        second = m.react({"scene.location":"山门外"})
        self.assertTrue(first["deltas"])
        self.assertEqual(second["deltas"], [])

if __name__ == "__main__":
    unittest.main()
