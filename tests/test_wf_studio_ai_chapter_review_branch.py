"""Studio same-writer chapter self-review, branch choice, and cold restart.

Deterministic synthetic provider responses ONLY: not proof of literary taste.
No real model, R2, Railway, or Canon writes. The creator sends one request;
the same opted-in model chooses MOVE_ON or LOOK_BACK_NOW afterward.
"""
import json
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from writerforge.studio_server import StudioService,StudioError
from writerforge.writing_assist import WritingExecutionError
from test_v26_invisible_writer import make_db,PLAN
from test_studio_author_stage_cancel_discard import wait_status
from test_wf_cross_chapter_candidate_fork import (
    PLAN_TURNS,prose_response,visible_prose,sha,
)
from test_wf_ai_writer_previous_turn_rewind import moment


OUTLINE=("沈砚和唐蜃在旧书铺讨论一份缺页账册。双方必须从真实行为"
         "判断对方知道什么，避免幻想已经发生的物件交换和密令披露。")
GOALS=[
    "主角从旧书铺开始调查但不提前宣布对方知道自己的秘密。",
    "两人考虑是否继续调查时必须尊重前面真实发生的事实。",
]
TURNS=json.dumps(PLAN_TURNS,ensure_ascii=False)


def one_chapter(chapter):
    return [
        PLAN,TURNS,prose_response(chapter,1),prose_response(chapter,2),
    ]


def two_chapters(chapter,*,alternate=False,edit=True):
    answers=[]
    for n in range(chapter,chapter+2):
        answers += [
            PLAN,TURNS,
            prose_response(n,1,alternate=alternate),
            *([moment("MOVE_ON",visible_prose(n,1,alternate=alternate))]
              if edit else []),
            prose_response(n,2,alternate=alternate),
            *([moment("MOVE_ON",visible_prose(n,2,alternate=alternate))]
              if edit else []),
        ]
    return answers


def assembled(n,*,alternate=False):
    return (visible_prose(n,1,alternate=alternate)+"\n\n"+
            visible_prose(n,2,alternate=alternate))


def decision(n,action):
    if action=="MOVE_ON":
        return json.dumps({
            "decision":"MOVE_ON","target_chapter_index":n,
            "source_sha256":sha(assembled(n)),
            "evidence_quote":None,
            "why_now":"我认为尚未揭开的身份秘密此时应该继续留白，人物仍须沿原有冲突作出选择。",
            "what_goes_wrong_if_unchanged":None,
            "intended_reader_effect":None,
        },ensure_ascii=False)
    return json.dumps({
        "decision":"LOOK_BACK_NOW","target_chapter_index":n,
        "source_sha256":sha(assembled(n)),
        "evidence_quote":f"第{n}章第1段，细雨不停。",
        "why_now":"我觉得前一章的天气描写不能承担我想让人物暴露的真实抉择代价。",
        "what_goes_wrong_if_unchanged":"如果保持原样，后面的空间变化会显得没有前因，读者难以辨认人物的选择。",
        "intended_reader_effect":"我希望让现场景象从实际事件变化展开，而不是凭空加入一个新的揭示。",
    },ensure_ascii=False)


class StudioSameWriterChapterFork(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.db=self.root/"learned.sqlite"
        make_db(self.db)
        self.params={
            "db_path":self.db,
            "project":"studio-branch-synthetic",
            "scene":"studio-autodraft-test",
            "goal":"从真实来源判断人物有限视角。",
            "model":"synthetic-writer",
            "output_dir":self.root/"studio",
        }
        self.studio=StudioService(**self.params)

    def create_parent(self):
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=one_chapter(1)) as model:
            response=self.studio.start_auto(
                OUTLINE,[GOALS[0]],draft_mode="continuity_guard",
                pause_between_turns=False)
            completed=wait_status(self.studio,{"completed","failed"},timeout=12)
        self.assertEqual(completed["status"],"completed",completed.get("error"))
        self.assertEqual(model.call_count,4)
        self.assertTrue(completed["unreviewed_resume_available"])
        saved=self.studio.store.path/"unaccepted_branch_selection.json"
        self.assertTrue(saved.is_file())
        self.assertEqual(completed["candidate_branches"]["available"],["original"])
        return response

    def full_writer(self,action):
        previous=self.create_parent()
        answers=two_chapters(2)+[decision(2,action)]
        if action=="LOOK_BACK_NOW":
            answers+=two_chapters(2,alternate=True)
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=answers) as model:
            started=self.studio.start_auto(
                OUTLINE,GOALS,draft_mode="continuity_guard",
                continue_unreviewed=True,
                self_edit_rounds=1,self_edit_timing="ai_decides",
                ai_chapter_review=True,pause_between_turns=False)
            completed=wait_status(self.studio,{"completed","failed"},timeout=20)
        self.assertEqual(completed["status"],"completed",completed.get("error"))
        self.assertEqual(model.call_count,len(answers))
        self.assertEqual(completed["result"]["wf_chapter_ai_moment_calls"],1)
        return started,completed,model

    def test_same_writer_revisits_rebuilds_selects_old_or_new_and_cold_restart(self):
        started,completed,model=self.full_writer("LOOK_BACK_NOW")
        found=completed["candidate_branches"]
        self.assertEqual(found["selected"],"revised")
        self.assertEqual(set(found["available"]),{"original","revised"})
        self.assertEqual(completed["result"]["wf_chapter_ai_review_decision"],
                         "LOOK_BACK_REBUILT_PROVISIONAL")
        jobroot=self.studio.output_dir/"autonomous"/started["job_id"]
        old_original=(jobroot/"ai-chapter-review-original.json").read_text("utf8")
        self.assertEqual(old_original,decision(2,"LOOK_BACK_NOW"))
        self.assertEqual(json.loads((jobroot/
            "ai-chapter-review-receipt.json").read_text("utf8"))["decision"],
            "LOOK_BACK_NOW")
        first=Path(completed["result"]["chapters"][0]["candidate"]).read_text(
            "utf8")
        self.assertIn("山雨渐停",first)
        self.assertNotIn("细雨不停",first)
        old_head=found["selected_resume_sha256"]
        old_choice=self.studio.select_branch(started["job_id"],"original")
        self.assertEqual(old_choice["selected_branch"],"original")
        self.assertNotEqual(old_choice["resume_sha256"],old_head)
        self.assertEqual(self.studio.branch_summary()["selected"],"original")
        self.assertIn("细雨不停",Path(
            self.studio.job()["result"]["chapters"][0]["candidate"]
        ).read_text("utf8"))
        new_choice=self.studio.select_branch(started["job_id"],"revised")
        self.assertEqual(new_choice["resume_sha256"],old_head)
        reopened=StudioService(**self.params)
        self.assertTrue(reopened.job()["restored_from_signed_local_candidate"])
        self.assertTrue(reopened.job()["unreviewed_resume_available"])
        self.assertEqual(reopened.branch_summary()["selected"],"revised")
        self.assertIn("山雨渐停",Path(
            reopened.job()["result"]["chapters"][0]["candidate"]
        ).read_text("utf8"))
        # A subsequent third chapter must inherit ONLY the newly chosen head.
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=one_chapter(4)) as further:
            reopened.start_auto(
                OUTLINE,[GOALS[1]],draft_mode="continuity_guard",
                continue_unreviewed=True,pause_between_turns=False)
            later=wait_status(reopened,{"completed","failed"},timeout=12)
        self.assertEqual(later["status"],"completed",later.get("error"))
        self.assertEqual(further.call_count,4)
        self.assertEqual(later["result"]["chapters"][0][
            "story_chapter_index"],4)
        self.assertEqual(later["candidate_branches"]["selected"],"original")
        self.assertEqual(later["result"]["canonical_fact_writes"],0)

    def test_ai_can_choose_move_on_no_second_writing_run(self):
        started,completed,model=self.full_writer("MOVE_ON")
        self.assertEqual(completed["candidate_branches"]["available"],["original"])
        self.assertEqual(completed["result"]["wf_chapter_ai_review_decision"],
                         "MOVE_ON")
        self.assertNotIn("cross_chapter_fork_receipt",completed["result"])
        self.assertFalse((self.studio.output_dir/"autonomous"/started["job_id"]/
                          "revised").exists())
        self.assertEqual(completed["result"]["wf_chapter_ai_moment_calls"],1)

    def test_invalid_ai_signal_never_forces_chapter_rewrite_or_retry(self):
        self.create_parent()
        answers=two_chapters(2)+["model mistakenly wrote prose instead of decision"]
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=answers) as model:
            started=self.studio.start_auto(
                OUTLINE,GOALS,draft_mode="continuity_guard",
                continue_unreviewed=True,self_edit_rounds=1,
                self_edit_timing="ai_decides",ai_chapter_review=True,
                pause_between_turns=False)
            done=wait_status(self.studio,{"completed","failed"},timeout=15)
        self.assertEqual(done["status"],"completed",done.get("error"))
        self.assertEqual(model.call_count,len(answers))
        self.assertEqual(done["result"]["wf_chapter_ai_review_decision"],
                         "INVALID_SIGNAL")
        self.assertEqual(done["candidate_branches"]["available"],["original"])
        self.assertFalse((self.studio.output_dir/"autonomous"/started["job_id"]/
                          "revised").exists())

    def test_wrong_scope_and_no_signed_parent_rejected_before_model(self):
        for extra in (
            {"ai_chapter_review":True},
            {"ai_chapter_review":True,"continue_unreviewed":True},
            {"ai_chapter_review":True,"self_edit_rounds":1,
             "self_edit_timing":"ai_decides","continue_unreviewed":True},
        ):
            with patch("writerforge.writing_assist.local_chat_completion") as m:
                with self.assertRaises(StudioError):
                    self.studio.start_auto(
                        OUTLINE,GOALS,draft_mode="continuity_guard",
                        pause_between_turns=False,**extra)
                m.assert_not_called()
        self.assertFalse((self.studio.output_dir/"autonomous").exists())

    def test_modified_branch_catalog_fails_closed_after_restart(self):
        self.create_parent()
        branch_path=self.studio.store.path/"unaccepted_branch_selection.json"
        before=branch_path.read_text("utf8")
        forged=json.loads(before)
        forged["branches"]["original"]["resume_sha256"]="0"*64
        branch_path.write_text(json.dumps(forged,ensure_ascii=False),encoding="utf8")
        loaded=StudioService(**self.params)
        self.assertFalse(loaded.job()["unreviewed_resume_available"])
        self.assertIn("TAMPERED",loaded.branch_summary()["restore_warning"])
        self.assertEqual(loaded.job()["status"],"idle")
        self.assertTrue((self.studio.store.path/"draft.md").exists() is False)
        branch_path.write_text(before,encoding="utf8")
        reread=StudioService(**self.params)
        self.assertTrue(reread.job()["unreviewed_resume_available"])
        self.assertEqual(reread.branch_summary()["selected"],"original")

    def test_browser_exposes_real_choice_controls_without_default_activation(self):
        html=(Path(__file__).resolve().parents[1]/"writerforge"/"ui"/
              "studio.html").read_text("utf8")
        self.assertIn('id="ai-chapter-review"',html)
        self.assertIn('id="candidate-branch"',html)
        self.assertIn('"/api/autodraft/branch/select"',html)
        self.assertIn("ai_chapter_review",html)
        self.assertIn("showBranchChoices(bootstrap.candidate_branches)",html)
        self.assertTrue(self.studio.bootstrap()["candidate_branches"]["available"]==[])


if __name__=="__main__":
    import unittest
    unittest.main()
