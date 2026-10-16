"""Mechanics-only tests for source-evidenced, two-pass literary scene learning.

Fake model replies verify orchestration, NOT quality of fiction or real readers.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from writerforge import WriterForgeDB, RuntimeEngine
from writerforge.scene_learning import (
    SceneLiteraryStudy, SceneStudyError, extract_scene_from_chapter,
    first_read_prompt, close_read_prompt,
)


PREFIX = (
    "這林黛玉常听得母親說過，陌生府邸的事情不比故鄉。"
    + ("她因此步步留心，時時在意，遇見正門卻不開，只留旁門待客。"
       "每一處規矩都提醒她在陌生人中不能失禮。") * 4
)
REVEAL = "一語未了，只听后院中有人笑聲。王熙鳳來了，和此前肅靜的眾人不同。"
REST = (
    "王熙鳳走近，笑道：天下真有這樣標致的人物，我今儿才算見了。"
    "旁人只聽得一時熱鬧，黛玉卻還不知如何稱呼。"
) * 4
SOURCE_TEXT = PREFIX + REVEAL + REST + "說話時，已擺了茶果上來。"
FIRST = json.dumps({
    "expectations":["來人應當也保持原有的禮節和安靜"],
    "questions":["這座府第是否容得下不守規矩的人"],
    "character_inferences":["黛玉第一次進府，擔心受到輕視所以格外克制"],
},ensure_ascii=False)
SECOND = json.dumps({"mechanisms":[{
    "source_quote":"天下真有這樣標致的人物",
    "hypothesis":"王熙鳳的言語不只是奉承，亦可能借長輩對外孫女的重視顯示自己會察言觀色。",
    "counterfactual":"若只寫她十分熱情，讀者便不易判斷她的分寸與地位，也看不到群體沉默的反差。",
    "transfer_question":"失敗稿中，人物行動是否改變群體關係，而非只順利完成外在任務？"
}]},ensure_ascii=False)


def scene():
    return extract_scene_from_chapter(
        SOURCE_TEXT,work_id="honglou-fixture",chapter=3,
        scene_id="ch3-arrival",source_sha256="raw-fixture-sha",
        start_anchor="這林黛玉常听得母親說過",
        reveal_anchor="一語未了，只听后院中有人笑聲",
        end_anchor="說話時，已擺了茶果上來",
        evidence_anchors=("步步留心，時時在意","正門卻不開",
                          "天下真有這樣標致的人物"),
        decoded_source_sha256="fixture-decoded-sha",
    )


class LiterarySceneTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.dbpath=Path(self.temp.name)/"study.sqlite3"
        self.db=WriterForgeDB(self.dbpath)
        self.db.conn.execute(
            "INSERT INTO studied_works(work_id,title,source_uri,source_sha256,chapter_count) "
            "VALUES(?,?,?,?,?)",
            ("honglou-fixture","红楼梦","fixture://original","fixture-decoded-sha",3),
        )
        cur=self.db.conn.execute(
            "INSERT INTO snapshots(parent_id,status,layout,note) "
            "VALUES(NULL,'published','full','real-structure-fixture')"
        )
        self.db.conn.execute(
            """INSERT INTO studied_chapters(
               work_id,chapter,chapter_sha256,heading,source_spans,retrieval_entries,snapshot_id)
               VALUES(?,?,?,?,?,?,?)""",
            ("honglou-fixture",3,"ch-hash","第三回",10,10,int(cur.lastrowid)),
        )
        self.db.conn.commit()
        self.rt=RuntimeEngine()
        self.rt.enter_learn()
        self.lab=SceneLiteraryStudy(self.db,self.rt,"project-a")

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_real_source_locator_requires_all_exact_bounded_anchors(self):
        current=scene()
        self.assertGreater(len(current.blind_text),180)
        self.assertNotIn("王熙鳳來了",first_read_prompt(current))
        self.assertIn("王熙鳳來了",close_read_prompt(current,{"expectations":[]}))
        self.assertEqual(current.public_receipt()["source_anchor_count"],3)
        with self.assertRaisesRegex(SceneStudyError,"source anchor missing"):
            extract_scene_from_chapter(
                SOURCE_TEXT,work_id="honglou-fixture",
                source_sha256="sha",scene_id="x",chapter=3,
                start_anchor="這林黛玉常听得母親說過",
                reveal_anchor="一語未了，只听后院中有人笑聲",
                end_anchor="天外飛來不存在的章回",
            )

    def test_prepared_is_not_model_training_or_first_read(self):
        current=scene()
        result=self.lab.prepare(current)
        self.assertEqual(result["stage"],"source_prepared")
        self.assertFalse(result["model_called"])
        self.assertFalse(result["real_reader_evaluation"])
        self.assertFalse(result["literary_mechanism_verified"])
        self.assertTrue(self.lab.prepare(current)["reused"])
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM literary_scene_trials"
        ).fetchone()[0],1)

    def test_first_read_sees_no_reveal_and_is_durable_before_close_read(self):
        current=scene()
        calls=[]
        def model(prompt):
            calls.append(prompt)
            if len(calls)==1:
                self.assertNotIn("王熙鳳來了",prompt)
                self.assertIsNone(self.db.conn.execute(
                    "SELECT first_read_json FROM literary_scene_trials"
                ).fetchone()["first_read_json"])
                return FIRST
            self.assertIn("王熙鳳來了",prompt)
            self.assertEqual(self.db.conn.execute(
                "SELECT stage FROM literary_scene_trials"
            ).fetchone()[0],"first_read_locked")
            return SECOND
        got=self.lab.run(current,model,"model-fixture")
        self.assertEqual(got["stage"],"interpretation_unreviewed")
        self.assertEqual(got["model_calls_this_invocation"],2)
        self.assertFalse(got["literary_mechanism_verified"])
        self.assertEqual(got["hypotheses"],1)
        self.db.close()
        self.db=WriterForgeDB(self.dbpath)
        self.lab=SceneLiteraryStudy(self.db,self.rt,"project-a")
        def forbidden(*args):
            raise AssertionError("must not re-run model or grow notes")
        after=self.lab.run(current,forbidden,"model-fixture")
        self.assertEqual(after["model_calls_this_invocation"],0)
        self.assertFalse(after["model_called"])
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM literary_scene_trials"
        ).fetchone()[0],1)

    def test_missing_quote_blocks_second_pass_and_can_resume(self):
        current=scene()
        self.lab.prepare(current)
        self.lab.lock_first_read(current,FIRST,"model-fixture")
        wrong=json.loads(SECOND)
        wrong["mechanisms"][0]["source_quote"]="原著不存在的假引文，卻被模型拿來解釋一切"
        with self.assertRaisesRegex(SceneStudyError,"nonexistent original"):
            self.lab.attach_analysis(current,json.dumps(wrong,ensure_ascii=False))
        self.assertEqual(self.db.conn.execute(
            "SELECT stage FROM literary_scene_trials"
        ).fetchone()[0],"first_read_locked")
        got=self.lab.run(current,lambda p:SECOND,"model-fixture")
        self.assertEqual(got["model_calls_this_invocation"],1)

    def test_first_read_cannot_be_rewritten_after_reveal(self):
        current=scene()
        self.lab.prepare(current)
        self.lab.lock_first_read(current,FIRST,"model-fixture")
        with self.assertRaisesRegex(SceneStudyError,"already locked"):
            self.lab.lock_first_read(current,FIRST,"model-fixture")
        self.assertEqual(self.lab.run(current,lambda p:SECOND,"model-fixture")["stage"],
                         "interpretation_unreviewed")

    def test_review_requires_explicit_confirmation_and_never_certifies_quality(self):
        current=scene()
        self.lab.run(current,lambda prompt:
                     FIRST if "截至此刻可見原文" in prompt else SECOND,
                     "model-fixture")
        with self.assertRaisesRegex(SceneStudyError,"explicit reasoned"):
            self.lab.review(current,approved=True,reason="同意",reviewer_confirmed=False)
        reviewed=self.lab.review(
            current,approved=True,reviewer_confirmed=True,
            reason="逐段核对来源，并确认这是待验证的写法假设而非文学质量成绩",
        )
        self.assertEqual(reviewed["review_status"],"approved")
        self.assertFalse(reviewed["transfer_and_literary_quality_verified"])

    def test_cross_source_and_cross_project_mix_rejected(self):
        current=scene()
        self.lab.prepare(current)
        from dataclasses import replace
        with self.assertRaisesRegex(SceneStudyError,"source edition changed"):
            self.lab.prepare(replace(current,raw_source_sha256="tampered-raw"))
        with self.assertRaisesRegex(SceneStudyError,"different original edition"):
            self.lab.prepare(replace(current,decoded_source_sha256="wrong-db"))
        elsewhere=SceneLiteraryStudy(self.db,self.rt,"project-b")
        self.assertFalse(elsewhere.prepare(current)["reused"])
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM literary_scene_trials"
        ).fetchone()[0],2)


if __name__=="__main__":
    unittest.main()
