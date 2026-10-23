"""Zero-model preflight for REAL three consecutive WF candidate chapters.

No literary judgments, mock writing, or new memory. Check the exact legacy
one-chapter-per-run interface and preserve original source/graph resumption.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import inspect
import unittest

from experiments import wf_three_chapter_real_continuity_pilot as pilot
from experiments.wf_real_self_scene_diagnostics import source_event
from writerforge.narrative_core import (
    new_graph,advance_graph,record_chapter_memory,read_core_from_resume,
    recall_original,
)
from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v117_continuity_trace import make_resume,read_resume
from writerforge.writing_assist import (
    AutonomousWriting,MAX_SEGMENTED_CHAPTERS_PER_JOB,
)


class RealMultiChapterSourceProtocol(unittest.TestCase):
    def test_distinct_source_cast_and_immutable_provider_maximum(self):
        self.assertTrue(pilot.structural_preflight())
        self.assertEqual(pilot.MAX_CALLS,12)
        self.assertEqual(pilot.MAX_RESERVED,15000)
        self.assertEqual(tuple(pilot.TOKENS),(650,1450,1450,1450))
        self.assertEqual(len(pilot.CHAPTER_GOALS),3)
        self.assertEqual(MAX_SEGMENTED_CHAPTERS_PER_JOB,2)
        self.assertNotIn("沈砚",pilot.SOURCE)
        self.assertTrue(pilot.MODEL=="deepseek-flash")

    def test_existing_unified_graph_source_and_resume_without_model(self):
        with TemporaryDirectory() as td:
            p=Path(td)/"real-source.md"
            p.write_text(pilot.SOURCE,encoding="utf8")
            g=new_graph(project_id=pilot.PROJECT,scene_id=pilot.STREAM)
            g=advance_graph(
                g,project_id=pilot.PROJECT,scene_id=pilot.STREAM,
                chapter_index=1,prose=pilot.SOURCE,
                events=[source_event(pilot.SOURCE,i,event)
                        for i,event in enumerate(pilot.EVENTS,1)])
            g=record_chapter_memory(
                g,project_id=pilot.PROJECT,scene_id=pilot.STREAM,
                chapter_index=1,source_path=str(p),prose=pilot.SOURCE)
            checkpoint=external_temporal_step(pilot.SOURCE,cast=pilot.CAST)
            packet=make_resume(
                project_id=pilot.PROJECT,scene_id=pilot.STREAM,
                chapter_index=1,checkpoint=checkpoint,
                unified_narrative_core=g)
            self.assertEqual(
                read_resume(packet,project_id=pilot.PROJECT,
                            scene_id=pilot.STREAM),
                checkpoint)
            r=read_core_from_resume(
                packet,project_id=pilot.PROJECT,scene_id=pilot.STREAM)
            self.assertEqual(r["chapter_index"],1)
            self.assertEqual(len([v for v in r["nodes"].values()
                                  if v["kind"]=="THREAD"]),1)
            self.assertEqual(recall_original(
                r,project_id=pilot.PROJECT,scene_id=pilot.STREAM,
                chapter_index=1),pilot.SOURCE)
            self.assertEqual(packet["canon_writes"],0)

    def test_resumed_writer_uses_actual_scene_chapter_not_local_001(self):
        from writerforge.writing_assist import (
            _writing_scene_scope,WritingExecutionError,
        )
        base="printshop"
        self.assertEqual(
            _writing_scene_scope(base,local_index=1),
            "printshop.chapter-001")
        self.assertEqual(
            _writing_scene_scope(base,local_index=1,resume_source_chapter=1),
            "printshop.chapter-002")
        self.assertEqual(
            _writing_scene_scope(base,local_index=1,resume_source_chapter=2),
            "printshop.chapter-003")
        self.assertEqual(
            _writing_scene_scope(base,local_index=1,resume_source_chapter=3),
            "printshop.chapter-004")
        self.assertEqual(
            _writing_scene_scope(base,local_index=2,resume_source_chapter=1),
            "printshop.chapter-003")
        with self.assertRaisesRegex(
                WritingExecutionError,"SCENE_CHAPTER_SCOPE_INVALID"):
            _writing_scene_scope(base,local_index=0)
        with self.assertRaisesRegex(
                WritingExecutionError,"SCENE_CHAPTER_OVERFLOW"):
            _writing_scene_scope(base,local_index=1,
                                 resume_source_chapter=1000000)

    def test_real_writer_runs_one_chapter_three_times_with_one_resume_chain(self):
        source=inspect.getsource(pilot.main)
        self.assertIn("for chapter_index,goal in enumerate(CHAPTER_GOALS,2)",source)
        self.assertIn("resume_story_checkpoint=resume",source)
        self.assertIn("resume=recovered",source)
        self.assertIn('literary_progression_mode="baseline"',source)
        self.assertIn('draft_mode="continuity_guard"',source)
        self.assertIn("source_reread_byte_equal",source)
        self.assertIn("ORIGINAL_WF_CANDIDATE.md",source)
        self.assertNotIn("retry_model(",source)
        self.assertNotIn("author_review=True",source)
        self.assertIn("provider_retries",source)
        self.assertIn("DeepSeekFlashModel(",source)


if __name__=="__main__":
    unittest.main()
