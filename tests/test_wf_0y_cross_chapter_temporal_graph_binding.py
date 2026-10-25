"""0.Y bug hunt: valid signatures from DIFFERENT story branches can be mixed.

All tests synthetic, zero providers, and no new memory owner. The RED
cases must fail on old WF, then pass only when actual source assembly and
temporal ancestry are bound in the signed V117/NarrativeCore candidate.
"""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from writerforge.narrative_core import (
    new_graph,advance_graph,record_chapter_memory,
)
from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v117_continuity_trace import make_resume,read_resume

PROJECT="wf-0y-signed-source"
SCENE="same-signature-wrong-story"
CAST=("姜岚","许槐")
CH1_OLD="姜岚走进灯塔，发现一页浸湿的潮汛簿。许槐依旧没说明上次涂改的缘由。"
CH1_NEW="姜岚走进堤坝值守室，发现一份写错的防汛账页。许槐没有说谁改了潮线。"
CH2="城里的人仍在等天亮，姜岚只记录自己亲眼见到的异常水位，没有公布传言。"
PART2A="雨落在后院，姜岚仔细查看旧灯下的纸张，仍然不愿贸然猜测来源。"
PART2B="许槐没有立即解释那道墨痕，只在纸旁做了记号，决定白日再核对。"


class SignedSourceTemporalMismatch(unittest.TestCase):
    def record(self,root,graph,chapter,prose,**opts):
        graph=advance_graph(graph,project_id=PROJECT,scene_id=SCENE,
                            chapter_index=chapter,prose=prose,events=())
        p=root/f"chapter-{chapter}-{len(list(root.iterdir()))}.md"
        p.write_text(prose,encoding="utf8")
        return record_chapter_memory(
            graph,project_id=PROJECT,scene_id=SCENE,
            chapter_index=chapter,source_path=str(p),prose=prose,**opts)

    def test_signed_v114_and_graph_of_different_chapter1_prose_cannot_pair(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            graph=self.record(root,new_graph(project_id=PROJECT,scene_id=SCENE),
                              1,CH1_OLD)
            other_cp=external_temporal_step(CH1_NEW,cast=CAST)
            with self.assertRaisesRegex(
                Exception,"WF117_.*SOURCE.*MISMATCH|WF117_.*SOURCE.*UNBOUND"):
                make_resume(project_id=PROJECT,scene_id=SCENE,
                            chapter_index=1,checkpoint=other_cp,
                            unified_narrative_core=graph)

    def test_two_real_turns_need_verified_whole_chapter_assembly(self):
        text=PART2A+"\n\n"+PART2B
        cp1=external_temporal_step(PART2A,cast=CAST)
        cp2=external_temporal_step(PART2B,prior=cp1,cast=CAST)
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            initial=new_graph(project_id=PROJECT,scene_id=SCENE)
            old=self.record(root,initial,1,text)
            with self.assertRaisesRegex(
                Exception,"WF117_.*SOURCE.*UNBOUND"):
                make_resume(project_id=PROJECT,scene_id=SCENE,
                            chapter_index=1,checkpoint=cp2,
                            unified_narrative_core=old)
            # Both true turn checkpoints, not two paragraphs invented by WF.
            graph=self.record(
                root,initial,1,text,
                chapter_source_parts=(PART2A,PART2B),
                chapter_temporal_checkpoints=(cp1,cp2))
            signed=make_resume(
                project_id=PROJECT,scene_id=SCENE,chapter_index=1,
                checkpoint=cp2,unified_narrative_core=graph)
            self.assertEqual(read_resume(
                signed,project_id=PROJECT,scene_id=SCENE),
                cp2)
            self.assertEqual(graph["source_temporal_link"]["turn_count"],2)

    def test_old_graph_descendant_cannot_use_new_revised_temporal_parent(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            g0=new_graph(project_id=PROJECT,scene_id=SCENE)
            old1=external_temporal_step(CH1_OLD,cast=CAST)
            g1=self.record(
                root,g0,1,CH1_OLD,
                chapter_source_parts=(CH1_OLD,),
                chapter_temporal_checkpoints=(old1,))
            old2=external_temporal_step(CH2,prior=old1,cast=CAST)
            old_g2=self.record(
                root,g1,2,CH2,
                chapter_source_parts=(CH2,),
                chapter_temporal_checkpoints=(old2,))
            valid_resume=make_resume(
                project_id=PROJECT,scene_id=SCENE,chapter_index=2,
                checkpoint=old2,unified_narrative_core=old_g2)
            self.assertEqual(
                read_resume(valid_resume,project_id=PROJECT,scene_id=SCENE),
                old2)
            # Two valid SHA-signed worlds, yet the new cp2 belongs to a
            # DIFFERENT chapter1 source. Must not combine with old graph2.
            revised1=external_temporal_step(CH1_NEW,cast=CAST)
            mixed2=external_temporal_step(CH2,prior=revised1,cast=CAST)
            with self.assertRaisesRegex(
                Exception,"WF117_.*SOURCE.*MISMATCH|WF117_.*TEMPORAL.*MISMATCH"):
                make_resume(project_id=PROJECT,scene_id=SCENE,
                            chapter_index=2,checkpoint=mixed2,
                            unified_narrative_core=old_g2)
            with self.assertRaisesRegex(
                Exception,"WFCORE_.*TEMPORAL.*PARENT"):
                self.record(
                    root,g1,2,CH2,
                    chapter_source_parts=(CH2,),
                    chapter_temporal_checkpoints=(mixed2,))

    def test_right_parent_can_build_fresh_descendant_not_reuse_old_ones(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            base=new_graph(project_id=PROJECT,scene_id=SCENE)
            old1=external_temporal_step(CH1_OLD,cast=CAST)
            oldg1=self.record(
                root,base,1,CH1_OLD,
                chapter_source_parts=(CH1_OLD,),
                chapter_temporal_checkpoints=(old1,))
            revised1=external_temporal_step(CH1_NEW,cast=CAST)
            newg1=self.record(
                root,base,1,CH1_NEW,
                chapter_source_parts=(CH1_NEW,),
                chapter_temporal_checkpoints=(revised1,))
            self.assertNotEqual(newg1["receipt_sha256"],
                                oldg1["receipt_sha256"])
            new2=external_temporal_step(CH2,prior=revised1,cast=CAST)
            newg2=self.record(
                root,newg1,2,CH2,
                chapter_source_parts=(CH2,),
                chapter_temporal_checkpoints=(new2,))
            resume=make_resume(project_id=PROJECT,scene_id=SCENE,
                               chapter_index=2,checkpoint=new2,
                               unified_narrative_core=newg2)
            self.assertEqual(
                newg2["source_temporal_link"]["previous_v114_checkpoint_sha256"],
                revised1["receipt_sha256"])
            self.assertEqual(read_resume(
                resume,project_id=PROJECT,scene_id=SCENE),new2)

if __name__=="__main__":
    unittest.main()
