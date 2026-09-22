import unittest
from writerforge import ActualReaderCorpus, ActualReaderCritic, SkillScheduler

class V10ActualReaderTests(unittest.TestCase):
    def test_genre_isolation(self):
        c = ActualReaderCorpus()
        rows = c.query(
            primary_genre="悬疑_无限流_规则生存",
            signals=("promise_payoff_failure",),
            limit=20
        )
        self.assertTrue(rows)
        self.assertTrue(all(r.primary_genre == "悬疑_无限流_规则生存" for r in rows))

    def test_no_cross_genre_fallback(self):
        c = ActualReaderCorpus()
        rows = c.query(primary_genre="不存在的类型", limit=10)
        self.assertEqual(rows, [])

    def test_critic_returns_review_questions_not_rewrite(self):
        critic = ActualReaderCritic()
        plan = critic.review_plan(
            primary_genre="都市异能_神话_怪物",
            concern_signals=("repetition_fatigue","promise_payoff_failure"),
            limit=3
        )
        self.assertIn("review_questions", plan)
        self.assertIn("reader_evidence", plan)
        self.assertNotIn("rewrite", plan)

    def test_current_work_can_be_excluded(self):
        c = ActualReaderCorpus()
        rows = c.query(
            primary_genre="都市异能_神话_怪物",
            limit=20,
            exclude_works=("异兽迷城",)
        )
        self.assertTrue(all(r.work != "异兽迷城" for r in rows))

    def test_actual_reader_not_in_sentence_drafting(self):
        d = SkillScheduler().drafting_decision("sentence_accepted", budget=8)
        self.assertNotIn("actual_reader_critic", d.selected)

if __name__ == "__main__":
    unittest.main()
