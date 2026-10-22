"""Twenty real checkpoint transitions, not twenty imagined LLM chapters.

This tests the zero-model narrative-goal carrying/gating mechanism, NOT the
artistic quality of 20 independently generated and judged novel chapters.
"""
import copy
import hashlib
import inspect
import json
import unittest

from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v117_continuity_trace import make_resume,read_resume
from writerforge.v123_long_arc import (
    register_revenge,advance_open_revenge,relevant_revenge_hint,
    read_long_arc_from_resume,audit_revenge_prose,verify_long_arc,LongArcError,
)
from writerforge.writing_assist import AutonomousWriting,WritingExecutionError

P="novel-revenge"
S="writerforge-chapter-stream"
CAST=("沈砚","唐蜃","叶青梧")
OPENING="沈砚跪在父亲坟前，发誓向唐蜃追讨旧案血债。"
ORIGIN_QUOTE="沈砚跪在父亲坟前，发誓向唐蜃追讨旧案血债。"


def vow(scope="CHARACTER_BELIEF"):
    return register_revenge(
        project_id=P,scene_id=S,origin_chapter=0,
        source_prose=OPENING,source_quote=ORIGIN_QUOTE,
        arc_id="revenge-father",actor="沈砚",target="唐蜃",
        motive="父亲遇害，沈砚怀疑唐蜃涉案",
        truth_scope=scope,author_confirmed=True)


class TwentyChapterAuthorConfirmedRevenge(unittest.TestCase):
    def test_real_reducer_and_resume_retain_arc_for_twenty_chapters(self):
        """Actually invoke the pinned MIT reducer at every chapter boundary."""
        ledger=vow()
        old=external_temporal_step(OPENING,cast=CAST)
        bytesizes=[]
        initial=ledger["receipt_sha256"]
        for chapter in range(1,21):
            # 19 quiet unrelated chapters must not repeatedly turn on a
            # "revenge" writing template.
            if chapter<20:
                prose=f"第{chapter}章，叶青梧独自行过旧桥，雨落在竹篷上。"
                self.assertEqual(relevant_revenge_hint(
                    ledger,project_id=P,scene_id=S,
                    beat={"kind":"quiet","goal":"叶青梧观察山雨"}),
                    "")
                self.assertEqual(relevant_revenge_hint(
                    ledger,project_id=P,scene_id=S,
                    goal="叶青梧守着旧山门，不曾提起过往"),"")
            else:
                prose="沈砚踏入断桥边的庙门，终于再见唐蜃，却决定先追问旧案。"
                hint=relevant_revenge_hint(
                    ledger,project_id=P,scene_id=S,
                    goal="沈砚在旧庙再次遇到唐蜃，调查杀父疑案")
                self.assertIn("沈砚",hint)
                self.assertIn("唐蜃",hint)
                self.assertIn("父亲遇害",hint)
                self.assertIn("人物当前信念",hint)
                self.assertIn("尚未",hint)
            old=external_temporal_step(prose,cast=CAST,prior=old)
            ledger=advance_open_revenge(
                ledger,project_id=P,scene_id=S,
                chapter_index=chapter,prose=prose)
            resume=make_resume(
                project_id=P,scene_id=S,chapter_index=chapter,
                checkpoint=old,long_arc_checkpoint=ledger)
            # Simulate separate process/job: strict serialized roundtrip
            restored=json.loads(json.dumps(resume,ensure_ascii=False))
            self.assertEqual(
                read_resume(restored,project_id=P,scene_id=S),old)
            ledger=read_long_arc_from_resume(
                restored,project_id=P,scene_id=S)
            self.assertEqual(ledger["last_chapter"],chapter)
            self.assertEqual(ledger["chapter_advances"],chapter)
            self.assertEqual(ledger["target"],"唐蜃")
            self.assertEqual(ledger["status"],"OPEN_AUTHOR_CONFIRMED")
            self.assertEqual(ledger["automatic_resolution_count"],0)
            self.assertEqual(ledger["canon_writes"],0)
            self.assertEqual(ledger["model_calls"],0)
            bytesizes.append(len(json.dumps(ledger,ensure_ascii=False).encode()))
        self.assertNotEqual(ledger["receipt_sha256"],initial)
        self.assertLessEqual(max(bytesizes),3000)
        self.assertEqual(ledger["settlement_claim_count"],0)
        self.assertEqual(ledger["truth_scope"],"CHARACTER_BELIEF")
        # No 20 independent full character sheets stored to cause a leak.
        self.assertLess(max(bytesizes)-min(bytesizes),180)

    def test_claimed_revenge_by_killing_wrong_target_does_not_close_arc(self):
        ledger=vow()
        text="沈砚杀了叶青梧，转身说道：大仇得报。"
        report=audit_revenge_prose(
            ledger,project_id=P,scene_id=S,prose=text)
        self.assertTrue(report["needs_review"])
        self.assertIn("WF123_REVENGE_CLOSURE_CLAIM_NEEDS_AUTHOR_REVIEW",
                      report["review_findings"])
        self.assertFalse(report["automatic_settlement_allowed"])
        self.assertFalse(report["blocked"])
        after=advance_open_revenge(
            ledger,project_id=P,scene_id=S,chapter_index=1,
            prose=text)
        self.assertEqual(after["status"],"OPEN_AUTHOR_CONFIRMED")
        self.assertEqual(after["settlement_claim_count"],1)
        self.assertIsNotNone(after["last_settlement_claim_prose_sha256"])
        self.assertEqual(after["automatic_resolution_count"],0)

    def test_successful_textual_revenge_is_not_automatically_author_approved(self):
        text="沈砚终于杀死唐蜃，大仇得报。"
        report=audit_revenge_prose(
            vow(),project_id=P,scene_id=S,prose=text)
        self.assertTrue(report["needs_review"])
        self.assertFalse(report["automatic_settlement_allowed"])

    def test_ambiguous_no_actor_claim_is_review_not_false_proof(self):
        r=audit_revenge_prose(
            vow(),project_id=P,scene_id=S,
            prose="雨歇时，众人说大仇得报，却不知谁所为。")
        self.assertTrue(r["needs_review"])
        self.assertIn("WF123_REVENGE_CLAIM_ACTOR_UNRESOLVED",
                      r["review_findings"])

    def test_quoted_and_dreamt_claim_not_real_settlement(self):
        for text in (
            "唐蜃嘲弄道：“沈砚已经报了仇。”",
            "沈砚梦见自己报了仇，醒来仍站在桥头。",
            "如果沈砚报了仇，那又如何？",
        ):
            with self.subTest(prose=text):
                r=audit_revenge_prose(
                    vow(),project_id=P,scene_id=S,prose=text)
                self.assertFalse(r["needs_review"])
                self.assertFalse(r["automatic_settlement_allowed"])

    def test_author_asserted_vs_character_belief_not_confused(self):
        a=vow(scope="AUTHOR_ASSERTED")
        b=vow(scope="CHARACTER_BELIEF")
        goal="沈砚遇见唐蜃，心中涌起杀父旧案疑团"
        ha=relevant_revenge_hint(a,project_id=P,scene_id=S,goal=goal)
        hb=relevant_revenge_hint(b,project_id=P,scene_id=S,goal=goal)
        self.assertIn("作者确认的故事前提",ha)
        self.assertIn("真相尚未得到确证",hb)
        self.assertNotEqual(ha,hb)

    def test_no_author_confirm_no_long_arc(self):
        with self.assertRaisesRegex(
                LongArcError,"AUTHOR_REVIEW_REQUIRED"):
            register_revenge(
                project_id=P,scene_id=S,origin_chapter=0,
                source_prose=OPENING,source_quote=ORIGIN_QUOTE,
                arc_id="revenge-father",actor="沈砚",target="唐蜃",
                motive="父亲遇害",truth_scope="AUTHOR_ASSERTED",
                author_confirmed=False)

    def test_unanchored_vow_is_not_implicitly_registered(self):
        with self.assertRaisesRegex(
                LongArcError,"SOURCE_NOT_UNIQUE"):
            register_revenge(
                project_id=P,scene_id=S,origin_chapter=0,
                source_prose=OPENING,source_quote="沈砚想杀叶青梧",
                arc_id="revenge-father",actor="沈砚",target="唐蜃",
                motive="父亲遇害",truth_scope="AUTHOR_ASSERTED",
                author_confirmed=True)

    def test_arc_resume_tampering_or_cross_project_rejected(self):
        old=external_temporal_step(OPENING,cast=CAST)
        arc=vow()
        outer=make_resume(
            project_id=P,scene_id=S,chapter_index=0,
            checkpoint=old,long_arc_checkpoint=arc)
        good=read_long_arc_from_resume(
            outer,project_id=P,scene_id=S)
        self.assertEqual(good["target"],"唐蜃")
        forged=copy.deepcopy(outer)
        forged["v123_open_character_arc"]["target"]="叶青梧"
        with self.assertRaises((LongArcError,ValueError)):
            read_long_arc_from_resume(
                forged,project_id=P,scene_id=S)
        with self.assertRaises((LongArcError,ValueError)):
            read_long_arc_from_resume(
                outer,project_id="wrong-novel",scene_id=S)

    def test_cannot_replay_or_jump_from_chapter_one_to_twenty(self):
        arc=vow()
        with self.assertRaisesRegex(LongArcError,"GAP_REPLAY"):
            advance_open_revenge(
                arc,project_id=P,scene_id=S,
                chapter_index=20,prose="山雨依旧。")
        first=advance_open_revenge(
            arc,project_id=P,scene_id=S,
            chapter_index=1,prose="山雨依旧。")
        with self.assertRaisesRegex(LongArcError,"GAP_REPLAY"):
            advance_open_revenge(
                first,project_id=P,scene_id=S,
                chapter_index=1,prose="山雨依旧。")

    def test_resume_retains_author_vow_even_if_model_says_finished(self):
        prior=external_temporal_step(OPENING,cast=CAST)
        arc=vow()
        prose="沈砚口中说已经报了仇，却仍未找到唐蜃。"
        current=external_temporal_step(prose,cast=CAST,prior=prior)
        next_arc=advance_open_revenge(
            arc,project_id=P,scene_id=S,
            chapter_index=1,prose=prose)
        outer=make_resume(
            project_id=P,scene_id=S,chapter_index=1,
            checkpoint=current,long_arc_checkpoint=next_arc)
        resumed=read_long_arc_from_resume(
            outer,project_id=P,scene_id=S)
        self.assertEqual(resumed["status"],"OPEN_AUTHOR_CONFIRMED")
        self.assertFalse(
            audit_revenge_prose(resumed,project_id=P,
                               scene_id=S,prose="沈砚望着屋檐。")["blocked"])

    def test_writerforge_real_continuity_guard_invokes_arc_hooks(self):
        source=inspect.getsource(AutonomousWriting.run)
        self.assertIn("read_long_arc_from_resume(",source)
        self.assertIn("relevant_revenge_hint(",source)
        self.assertIn("audit_revenge_prose(",source)
        self.assertIn("advance_open_revenge(",source)
        self.assertIn("long_arc_checkpoint=active_long_arc",source)
        self.assertIn('"v123_long_arc_prose_reviews"',source)


if __name__=="__main__":
    unittest.main()
