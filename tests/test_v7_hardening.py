import tempfile, unittest
from pathlib import Path
from writerforge import *
from writerforge.xuehai import Query
from writerforge.story import CanonPatchRequired

class V7HardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = WriterForgeDB(Path(self.tmp.name)/"v7.sqlite")
        self.runtime = RuntimeEngine()
        self.x = XuehaiStore(self.db, self.runtime)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def published(self):
        self.runtime.enter_learn()
        sid = self.x.create_staging_snapshot()
        # Three works, intentionally same method cluster for diversity testing.
        for i, work in enumerate(["A","A","B","C"]):
            self.x.add_entry(
                sid, work_id=work, text=f"环境证据{i} 愤怒 压抑",
                genre="玄幻", culture="中国", function="emotion_expression",
                effect="anger", method_cluster="restrained-anger" if i < 3 else "silence-after-anger",
                quality_weight=3-i*0.2, novelty_weight=1+i*0.1
            )
        self.x.publish(sid)
        self.runtime.exit()
        return sid

    def test_snapshot_inherits_parent(self):
        sid1 = self.published()
        self.runtime.enter_learn()
        sid2 = self.x.create_staging_snapshot(parent_id=sid1)
        count = self.db.conn.execute("SELECT COUNT(*) c FROM xuehai_entries WHERE snapshot_id=?", (sid2,)).fetchone()["c"]
        self.assertEqual(count, 4)
        self.runtime.exit()

    def test_retrieval_diversity_and_usage_penalty(self):
        sid = self.published()
        self.runtime.enter_write(sid)
        q = Query(function="emotion_expression", text_terms=("愤怒",), project_id="p", limit=3, max_per_work=1, max_per_cluster=2)
        rows1 = self.x.query(q)
        self.assertEqual(len({r["work_id"] for r in rows1}), len(rows1))
        first = rows1[0]["entry_id"]
        for _ in range(8):
            self.x.mark_used(first, "p")
        rows2 = self.x.query(q)
        self.assertGreaterEqual(rows2[0]["score"], rows2[-1]["score"])
        self.assertNotEqual(rows2[0]["entry_id"], first)

    def test_immutable_canon_requires_patch(self):
        sid = self.published()
        self.runtime.enter_write(sid)
        s = StoryStore(self.db, self.runtime, "p")
        s.add_canon("F1","fact","师父已死","immutable")
        with self.assertRaises(CanonPatchRequired):
            s.add_canon("F1","fact","师父活着","immutable")
        s.patch_canon("F1","师父活着","正式反转")
        row = self.db.conn.execute("SELECT statement FROM canon WHERE project_id='p' AND canon_id='F1'").fetchone()
        self.assertEqual(row["statement"], "师父活着")

    def test_dead_character_action(self):
        sid = self.published()
        self.runtime.enter_write(sid)
        s = StoryStore(self.db, self.runtime, "p")
        s.set_character("c", {"alive":False,"death_time_index":10,"knowledge":{"knows":[],"does_not_know":[]}})
        s.add_story_action("c", 11, "挥剑", "ch2")
        codes = {f.code for f in ValidatorSuite(self.db,"p").run_all()}
        self.assertIn("DEAD_CHARACTER_ACTION", codes)

    def test_pov_leak(self):
        sid = self.published()
        self.runtime.enter_write(sid)
        s = StoryStore(self.db, self.runtime, "p")
        s.add_narrative_claim("sc1","A","B","internal_thought","B心想……","sc1-s4")
        codes = {f.code for f in ValidatorSuite(self.db,"p").run_all()}
        self.assertIn("POV_LEAK", codes)

    def test_item_location_conflict(self):
        sid = self.published()
        self.runtime.enter_write(sid)
        s = StoryStore(self.db, self.runtime, "p")
        s.add_item_claim("sword", 5, holder="A", location="山门")
        s.add_item_claim("sword", 5, holder="B", location="城内")
        codes = {f.code for f in ValidatorSuite(self.db,"p").run_all()}
        self.assertIn("ITEM_LOCATION_CONFLICT", codes)

    def test_timeline_location_conflict(self):
        sid = self.published()
        self.runtime.enter_write(sid)
        s = StoryStore(self.db, self.runtime, "p")
        s.add_presence("A", 1, 5, "山门")
        s.add_presence("A", 4, 6, "城内")
        codes = {f.code for f in ValidatorSuite(self.db,"p").run_all()}
        self.assertIn("TIMELINE_LOCATION_CONFLICT", codes)

    def test_world_rule_conflict(self):
        sid = self.published()
        self.runtime.enter_write(sid)
        s = StoryStore(self.db, self.runtime, "p")
        s.set_world_rule("revive_dead","false","死人不可复生")
        s.assert_world_rule("revive_dead","true","ch9")
        codes = {f.code for f in ValidatorSuite(self.db,"p").run_all()}
        self.assertIn("WORLD_RULE_CONFLICT", codes)

    def test_promise_forgotten(self):
        sid = self.published()
        self.runtime.enter_write(sid)
        s = StoryStore(self.db, self.runtime, "p")
        s.set_project_position(20)
        s.set_promise("P1", {"importance":"high","expected_window_end":12}, "open")
        codes = {f.code for f in ValidatorSuite(self.db,"p").run_all()}
        self.assertIn("PROMISE_FORGOTTEN", codes)

if __name__ == "__main__":
    unittest.main()
