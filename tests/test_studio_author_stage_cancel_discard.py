"""Real Studio lifecycle tests: selectable staged writing and explicit discard.

No provider or model simulation is treated as LITERARY success. Stubbed worker
exercises genuine threads, locks, versioned local files and author controls;
the existing writer's full tests separately cover actual planning/segment
selection and saved prose. Must not touch another run or manual manuscript.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path
import sqlite3
import threading
import time
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

from test_v26_invisible_writer import make_db
from writerforge.studio_server import (
    StudioService,StudioError,_delete_only_job_folder,
)
from writerforge.writing_assist import (
    AutonomousWriting,WriterDraftCancelled,WritingExecutionError,
)

OUTLINE="南塘旧戏院停演前夕，女角与经纪人争执去留，真正的事实尚未被任何人完全掌握。"
GOALS=["第一章：人物要面对分歧，自己的决定应带来可见后果"]


def wait_status(service,targets,timeout=4):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        state=service.job()
        if state.get("status") in targets:
            return state
        time.sleep(.015)
    raise AssertionError(f"WriterForge Studio state timeout: {service.job()}")


class StudioAuthorControlledTurns(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.dbpath=self.root/"original-study.sqlite"
        make_db(self.dbpath)
        self.service=StudioService(
            db_path=self.dbpath,project="book-x",scene="scene-y",
            goal="演出结束前角色各自选择离开或留下",
            model="local-fixture",output_dir=self.root/"studio")

    def tearDown(self):
        self.temp.cleanup()

    def test_original_choice_options_and_manual_manuscript_are_still_there(self):
        import writerforge
        html=(Path(inspect.getfile(writerforge)).parent/"ui"/
              "studio.html").read_text(encoding="utf8")
        self.assertIn('id="tab-help"',html)
        self.assertIn('id="tab-auto"',html)
        self.assertIn('id="options"',html)
        self.assertIn("data.choices.forEach",html)
        self.assertIn('manuscript.addEventListener("input"',html)
        self.assertIn('id="pause-turns"',html)
        self.assertIn('id="continue-turn"',html)
        self.assertIn('id="stop-auto"',html)
        self.assertIn('id="discard-auto"',html)
        self.assertIn('value="single"',html)
        for mode in ("split_only","causal_guard","rolling_causal",
                     "emotion_rolling","foresight_rolling"):
            self.assertIn('value="'+mode+'"',html)
        self.assertIn("WF96_UNKNOWN_EXPERIMENTAL_DRAFT_MODE",
                      inspect.getsource(StudioService.start_auto))
        text="角色已经写出自己的最后一句台词，不能被 AI 删除。"
        saved=self.service.store.save(text,expected_revision=0)
        self.assertEqual(saved["revision"],1)
        self.assertEqual(self.service.store.load()["text"],text)

    def test_pause_then_continue_then_cancel_disposes_only_current_job(self):
        manuscript="作者已经写出的原手稿，取消候选时不可删除。"
        self.service.store.save(manuscript,expected_revision=0)
        step_two_model_calls=[]
        written=threading.Event()

        def partial_generator(_writer,**kwargs):
            target=Path(kwargs["output_dir"])/"auto-private"
            target.mkdir(parents=True)
            (target/"candidate.md").write_text(
                "旧候选未正式接受。",encoding="utf8")
            written.set()
            self.assertTrue(kwargs["pause_between_turns"] if
                            "pause_between_turns" in kwargs else True)
            review=kwargs["review_turn"]
            if not review(1,1,"第一段真实写作在结束之前必须等作者决定。"):
                raise WriterDraftCancelled("WF_STUDIO_DRAFT_CANCELLED")
            step_two_model_calls.append("second_turn_started")
            if not review(1,2,"第二段开始时，仍允许放弃或丢弃。"):
                raise WriterDraftCancelled("WF_STUDIO_DRAFT_CANCELLED")
            return {"chapter_count":1,"chapters":[],
                    "all_generated_prose_requires_author_review":True}

        with patch("writerforge.studio_server.AutonomousWriting.run",
                   autospec=True,side_effect=partial_generator):
            started=self.service.start_auto(
                OUTLINE,GOALS,draft_mode="causal_guard")
            self.assertTrue(started["pause_between_turns"])
            self.assertTrue(written.wait(2))
            first=wait_status(self.service,{"awaiting_review"})
            self.assertEqual(first["pending_turn"]["turn"],1)
            self.assertEqual(step_two_model_calls,[])
            with self.assertRaisesRegex(StudioError,"stale"):
                self.service.continue_auto(
                    started["job_id"],chapter=1,turn=2)
            self.service.continue_auto(started["job_id"],chapter=1,turn=1)
            second=wait_status(self.service,{"awaiting_review"})
            # Wait for second turn rather than reading stale first state.
            deadline=time.monotonic()+3
            while second["pending_turn"]["turn"]!=2 and time.monotonic()<deadline:
                time.sleep(.01)
                second=self.service.job()
            self.assertEqual(second["pending_turn"]["turn"],2)
            self.assertEqual(step_two_model_calls,["second_turn_started"])
            self.service.cancel_auto(started["job_id"])
            end=wait_status(self.service,{"cancelled"})
            self.assertTrue(end["discarded"])
            self.assertIsNone(end["result"])
            self.assertFalse(self.service._job_folder.exists())
            self.assertEqual(self.service.store.load()["text"],manuscript)
            self.assertFalse(list((self.root/"studio").rglob("candidate.md")))
            with sqlite3.connect(self.dbpath) as con:
                self.assertEqual(con.execute(
                    "SELECT COUNT(*) FROM accepted_prose").fetchone()[0],0)

    def test_cancel_during_model_call_is_cooperative_and_no_next_call(self):
        self.service.store.save("人工写下的正文仍保留。",expected_revision=0)
        entered=threading.Event()
        permit_return=threading.Event()
        stages=[]

        def slow_writer(_writer,**kwargs):
            private=Path(kwargs["output_dir"])/"auto-partial"
            private.mkdir(parents=True)
            (private/"partial.json").write_text("not accepted")
            entered.set()
            self.assertTrue(permit_return.wait(3))
            # A real model request cannot be killed mid-network wait; at
            # the first boundary, the writer should observe author cancel.
            if kwargs["cancel_requested"]():
                raise WriterDraftCancelled("WF_STUDIO_DRAFT_CANCELLED")
            stages.append("incorrect_continuation")
            return {"chapter_count":1,"chapters":[]}

        with patch("writerforge.studio_server.AutonomousWriting.run",
                   autospec=True,side_effect=slow_writer):
            job=self.service.start_auto(
                OUTLINE,GOALS,draft_mode="single")
            self.assertFalse(job["pause_between_turns"])
            self.assertTrue(entered.wait(2))
            stop=self.service.cancel_auto(job["job_id"])
            self.assertEqual(stop["status"],"cancelling")
            self.assertTrue(self.service._job_folder.exists())
            permit_return.set()
            finished=wait_status(self.service,{"cancelled"})
            self.assertTrue(finished["discarded"])
            self.assertEqual(stages,[])
            self.assertFalse(self.service._job_folder.exists())
            self.assertEqual(self.service.store.load()["text"],
                             "人工写下的正文仍保留。")

    def test_completed_candidate_can_be_discarded_not_the_old_project(self):
        old=self.root/"studio"/"autonomous"/"previous-owned-job"
        old.mkdir(parents=True)
        (old/"important-old-candidate.md").write_text("旧候选不应删")
        self.service.store.save("作者已有作品。",expected_revision=0)

        def complete(_writer,**kwargs):
            folder=Path(kwargs["output_dir"])/"auto-complete"
            folder.mkdir(parents=True)
            manuscript=folder/"candidate.md"
            manuscript.write_text("另一份尚未正式接受的候选。",encoding="utf8")
            return {"chapter_count":1,"chapters":[{
                "chapter":1,"candidate":str(manuscript)}],
                "all_generated_prose_requires_author_review":True}

        with patch("writerforge.studio_server.AutonomousWriting.run",
                   autospec=True,side_effect=complete):
            job=self.service.start_auto(OUTLINE,GOALS,draft_mode="single")
            self.assertEqual(wait_status(
                self.service,{"completed"})["status"],"completed")
            with self.assertRaisesRegex(StudioError,"cannot delete"):
                self.service.discard_auto("deadbeefdeadbeef")
            doc=self.service.discard_auto(job["job_id"])
            self.assertEqual(doc["status"],"discarded")
            self.assertFalse(self.service._job_folder.exists())
            self.assertTrue((old/"important-old-candidate.md").exists())
            self.assertEqual(self.service.store.load()["text"],"作者已有作品。")
            with self.assertRaises(StudioError):
                self.service.discard_auto(job["job_id"])

    def test_path_provenance_refuses_cross_job_or_autosave_deletion(self):
        root=self.root/"studio"
        base=root/"autonomous"
        base.mkdir(parents=True)
        wrong=base/"not-jobid"
        wrong.mkdir()
        with self.assertRaisesRegex(StudioError,"invalid author draft job id"):
            _delete_only_job_folder(wrong,base,"not-jobid")
        manuscript=self.service.store.path/"draft.md"
        self.service.store.save("独立作者原稿",expected_revision=0)
        with self.assertRaisesRegex(StudioError,"unsafe"):
            _delete_only_job_folder(
                manuscript,self.service.store.path,
                "1111111111111111")
        self.assertTrue(manuscript.exists())

    def test_callback_refuses_generation_before_any_provider(self):
        from writerforge import WriterForgeDB,RuntimeEngine
        from writerforge.writing_assist import InvisibleWritingAssist
        db=WriterForgeDB(self.dbpath)
        try:
            row=db.conn.execute(
                "SELECT id FROM snapshots WHERE status='published' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            rt=RuntimeEngine()
            rt.enter_write(row["id"])
            help=InvisibleWritingAssist(
                db,rt,"test-cancel","test-scene",
                "人物自己思考去留的问题",model="local-fixture")
            with patch("writerforge.writing_assist.local_chat_completion") as fake:
                with self.assertRaises(WriterDraftCancelled):
                    AutonomousWriting(help).run(
                        outline=OUTLINE,chapter_goals=GOALS,
                        output_dir=self.root/"never-write-source",
                        cancel_requested=lambda:True)
                fake.assert_not_called()
            self.assertFalse((self.root/"never-write-source").exists())
        finally:
            db.close()


if __name__=="__main__":
    unittest.main()
