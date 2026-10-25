"""WF cross-chapter candidates: source-locked V117 fork, never literary scoring.

All model replies are deterministic fixtures.  No API credentials, no R2, no
Canon writes, no overwrite of historical branches and no hidden retraining.
"""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from writerforge import WriterForgeDB, RuntimeEngine
from writerforge.writing_assist import (
    AutonomousWriting,InvisibleWritingAssist,
    _prepare_unaccepted_chapter_fork,_validate_unaccepted_fork_resume,
    _save_unified_cold_capsule,
)
from writerforge.verified_flow import WritingExecutionError
from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v117_continuity_trace import make_resume,read_resume
from writerforge.narrative_core import (
    new_graph,advance_graph,record_chapter_memory,read_core_from_resume,
)
from test_v26_invisible_writer import make_db,PLAN

ACTORS=("沈砚","唐蜃")
PLAN_TURNS={"turns":[
    {"id":"t01","kind":"quiet","actor":"沈砚",
     "goal":"沈砚在旧书铺旁思索怎样回应现实的误会",
     "causal_parent":None,"craft_focus":[]},
    {"id":"t02","kind":"quiet","actor":"唐蜃",
     "goal":"唐蜃不能提前知道对方没有说出的想法",
     "causal_parent":None,"craft_focus":[]},
]}


def sha(src):
    if isinstance(src,str):
        src=src.encode("utf8")
    return hashlib.sha256(src).hexdigest()


def visible_prose(chapter,turn,*,alternate=False):
    # No model proxies or host-authored creative text in production: this
    # test fixture merely stands in for FOUR actual provider prose answers.
    line=(f"第{chapter}章第{turn}段，"
          +("山雨渐停" if alternate else "细雨不停")
          +"。")
    lines=(
        "沈砚看见门外有一盏旧灯，却没有立即认为它是别人留下的暗号。"
        "唐蜃听见脚步声走近，想起两人昨夜并没有说清楚账目为何有出入。"
        "旧书铺的掌柜在屋内整理纸页，外面的人仍不知道他心里究竟作何打算。"
        "他们先互相观察，没有在这一刻把没有来源的猜测当成亲眼见到的事实。"
    )
    return line+lines


def prose_response(n,t,*,alternate=False):
    return json.dumps({
        "prose":visible_prose(n,t,alternate=alternate),
        "trace":{"action_quote":None,"effect_quote":None,
                 "parent_effect_quote":None},
    },ensure_ascii=False)


def replies(chapter_start,*,alternate=False):
    output=[]
    for chapter in range(chapter_start,chapter_start+2):
        output.extend([
            PLAN,
            json.dumps(PLAN_TURNS,ensure_ascii=False),
            prose_response(chapter,1,alternate=alternate),
            prose_response(chapter,2,alternate=alternate),
        ])
    return output


class CrossChapterUnacceptedSourceFork(TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.dbpath=self.root/"verified.db"
        sid=make_db(self.dbpath)
        self.db=WriterForgeDB(self.dbpath)
        self.addCleanup(self.db.close)
        rt=RuntimeEngine()
        rt.enter_write(sid)
        self.project="fork-synthetic"
        self.scene="fork-scene"
        self.assist=InvisibleWritingAssist(
            self.db,rt,self.project,self.scene,
            "人物在未知的局面中必须保持有限视角和现实行动后果。",
            model="same-synthetic-author",
            api_base="http://127.0.0.1:1234/v1")
        self.outline=("沈砚与唐蜃在一间旧书铺相遇，逐渐发现彼此对于"
                      "旧案和人物选择的理解并不一致，需要实际行动而非幻想。")
        self.goals=[
            "旧书铺里出现影响人物彼此信任的隐晦证据，先让真实行动发生。",
            "尚未知晓完整事实的两人继续作出各自决定，不能省略实际代价。",
        ]
        self.initial=external_temporal_step(
            "沈砚在旧院里听见风吹过墙头，转身询问唐蜃为何还没有回去。",
            cast=ACTORS)
        self.initial_graph=new_graph(
            project_id=self.project,scene_id=self.scene,chapter_index=0)
        self.parent=make_resume(
            project_id=self.project,scene_id=self.scene,chapter_index=0,
            checkpoint=self.initial,
            unified_narrative_core=self.initial_graph)

    def run_writer(self,*,out,answer_list,resume=None,fork=None,
                   selected_fork_receipt=None):
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=answer_list) as model:
            output=AutonomousWriting(self.assist).run(
                outline=self.outline,chapter_goals=self.goals,
                draft_mode="continuity_guard",
                resume_story_checkpoint=resume or self.parent,
                cross_chapter_fork=fork,
                selected_fork_receipt=selected_fork_receipt,
                output_dir=self.root/out)
        self.assertEqual(model.call_count,len(answer_list))
        return output

    def old_branch(self):
        first=self.run_writer(out="old",answer_list=replies(1))
        head=json.loads(Path(first["chapters"][-1][
            "v117_unreviewed_text_trace_resume"]).read_text("utf8"))
        original=Path(first["chapters"][0]["candidate"]).read_text("utf8")
        return first,head,original

    def request(self,old,head,original):
        start=original.find("细雨不停")
        self.assertGreaterEqual(start,0)
        return {
            "source_job_dir":old["job_dir"],
            "expected_old_head_sha256":head["receipt_sha256"],
            "writer_decision_reply":json.dumps({
                "decision":"LOOK_BACK_NOW","target_chapter_index":1,
                "source_sha256":sha(original),
                "evidence_quote":"第1章第1段，细雨不停。",
                "why_now":"我读回这一章，觉得连场景最初的天气铺垫都在妨碍人物选择的节奏。",
                "what_goes_wrong_if_unchanged":"继续写可能使读者误以为两人已经在雨势中被迫离开，后续空间不连贯。",
                "intended_reader_effect":"希望读者在实际行动和犹豫之间体会危险，而非接收预定的背景解释。",
            },ensure_ascii=False),
        }

    def test_ai_proposed_fork_rebuilds_two_chapters_from_signed_parent(self):
        old,old_head,old_original=self.old_branch()
        old_files={row["candidate"]:Path(row["candidate"]).read_bytes()
                   for row in old["chapters"]}
        decision=self.request(old,old_head,old_original)
        new=self.run_writer(
            out="new",answer_list=replies(1,alternate=True),fork=decision)
        self.assertEqual(new["cross_chapter_rebuilt_old_descendants_count"],2)
        fork=json.loads(Path(new["cross_chapter_fork_receipt"]).read_text("utf8"))
        self.assertEqual(fork["target_chapter_index"],1)
        self.assertEqual(fork["parent_resume_sha256"],
                         self.parent["receipt_sha256"])
        self.assertEqual(fork["old_head_resume_sha256"],
                         old_head["receipt_sha256"])
        self.assertNotEqual(fork["new_branch_head_resume_sha256"],
                            old_head["receipt_sha256"])
        self.assertEqual(len(fork["obsolete_only_in_this_fork"]),2)
        self.assertFalse(fork["author_accepted"])
        self.assertEqual(fork["canon_writes"],0)
        self.assertTrue(fork["old_artifacts_are_immutable"])
        self.assertFalse(fork["literary_quality_verified"])
        self.assertTrue(all(Path(path).read_bytes()==blob
                            for path,blob in old_files.items()))
        new_head=json.loads(Path(new["chapters"][-1][
            "v117_unreviewed_text_trace_resume"]).read_text("utf8"))
        _validate_unaccepted_fork_resume(
            fork_receipt=fork,candidate_resume=new_head,
            project_id=self.project,scene_id=self.scene)
        with self.assertRaisesRegex(
            WritingExecutionError,"WF_CHAPTER_FORK_OLD_DESCENDANT_BLOCKED"):
            _validate_unaccepted_fork_resume(
                fork_receipt=fork,candidate_resume=old_head,
                project_id=self.project,scene_id=self.scene)
        parent_graph=read_core_from_resume(
            self.parent,project_id=self.project,scene_id=self.scene)
        first_new=json.loads(Path(new["chapters"][0][
            "v117_unreviewed_text_trace_resume"]).read_text("utf8"))
        new_first_graph=read_core_from_resume(
            first_new,project_id=self.project,scene_id=self.scene)
        new_graph=read_core_from_resume(
            new_head,project_id=self.project,scene_id=self.scene)
        self.assertEqual(new_first_graph["parent_sha256"],
                         parent_graph["receipt_sha256"])
        self.assertEqual(new_graph["parent_sha256"],
                         new_first_graph["receipt_sha256"])
        # A graph parent SHA alone is not sufficient: each G chapter
        # also binds its archived FULL prose to every V114 short-turn SHA.
        self.assertTrue(new_first_graph["source_temporal_link"][
            "source_assembly_verified"])
        self.assertEqual(new_first_graph["source_temporal_link"][
            "turn_count"],2)
        self.assertEqual(new_graph["source_temporal_link"][
            "turn_count"],2)
        self.assertEqual(new_graph["source_temporal_link"][
            "previous_v114_checkpoint_sha256"],
            first_new["source_checkpoint_sha256"])
        self.assertTrue(new_graph["source_temporal_link"][
            "prior_link_verified"])
        for row,snapshot in ((new["chapters"][0],first_new),
                             (new["chapters"][1],new_head)):
            body=Path(row["candidate"]).read_text("utf8")
            bound=read_core_from_resume(
                snapshot,project_id=self.project,scene_id=self.scene)
            self.assertEqual(bound["source_temporal_link"][
                "whole_chapter_sha256"],sha(body))
            self.assertEqual(bound["source_temporal_link"][
                "last_v114_checkpoint_sha256"],
                snapshot["source_checkpoint_sha256"])
        old_sources={x["source_sha256"] for x in
                     fork["obsolete_only_in_this_fork"]}
        for entry in new_graph["memory"]["hot"]+new_graph["memory"]["warm"]:
            self.assertNotIn(entry["source_sha256"],old_sources)
        self.assertEqual(new_graph["memory"]["last_recorded_chapter"],2)
        self.assertEqual(read_resume(new_head,project_id=self.project,
                         scene_id=self.scene)["receipt_sha256"],
                         new_head["source_checkpoint_sha256"])
        self.assertFalse(new_head["author_accepted"])

    def test_failed_new_branch_does_not_replace_old_immutable_history(self):
        old,old_head,original=self.old_branch()
        original_paths={
            row["candidate"]:Path(row["candidate"]).read_bytes()
            for row in old["chapters"]}
        originals={
            row["v117_unreviewed_text_trace_resume"]:
                Path(row["v117_unreviewed_text_trace_resume"]).read_bytes()
            for row in old["chapters"]}
        bad_answers=replies(1,alternate=True)
        bad_answers[6]="invalid second chapter model prose response"
        dest=self.root/"aborted-fork"
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=bad_answers) as provider:
            with self.assertRaises(WritingExecutionError):
                AutonomousWriting(self.assist).run(
                    outline=self.outline,chapter_goals=self.goals,
                    draft_mode="continuity_guard",
                    resume_story_checkpoint=self.parent,
                    cross_chapter_fork=self.request(old,old_head,original),
                    output_dir=dest)
        self.assertEqual(provider.call_count,7)
        self.assertTrue(all(Path(p).read_bytes()==raw for p,raw in
                            {**original_paths,**originals}.items()))
        self.assertEqual(
            read_resume(old_head,project_id=self.project,
                        scene_id=self.scene)["receipt_sha256"],
            old_head["source_checkpoint_sha256"])
        aborted=list(dest.glob("auto-*"))
        self.assertEqual(len(aborted),1)
        self.assertTrue((aborted[0]/"cross-chapter-fork-intent.json").is_file())
        self.assertFalse((aborted[0]/"cross-chapter-fork-rebuilt.json").exists())
        self.assertFalse((aborted[0]/"job_manifest.json").exists())

    def test_fork_requires_exact_old_head_source_and_original_snapshot(self):
        old,head,prose=self.old_branch()
        request=self.request(old,head,prose)
        cases=[
            {"expected_old_head_sha256":"0"*64},
            {"writer_decision_reply":json.dumps({
                **json.loads(request["writer_decision_reply"]),
                "source_sha256":"0"*64},ensure_ascii=False)},
            {"writer_decision_reply":json.dumps({
                **json.loads(request["writer_decision_reply"]),
                "evidence_quote":"这个章节不存在的唯一原句"},ensure_ascii=False)},
            {"writer_decision_reply":json.dumps({
                **json.loads(request["writer_decision_reply"]),
                "decision":"MOVE_ON"},ensure_ascii=False)},
        ]
        for index,broken in enumerate(cases):
            bad={**request,**broken}
            dest=self.root/f"bad-{index}"
            with patch("writerforge.writing_assist.local_chat_completion") as model:
                with self.assertRaises(WritingExecutionError):
                    AutonomousWriting(self.assist).run(
                        outline=self.outline,chapter_goals=self.goals,
                        draft_mode="continuity_guard",
                        resume_story_checkpoint=self.parent,
                        cross_chapter_fork=bad,output_dir=dest)
                model.assert_not_called()
            self.assertFalse(dest.exists())

    def test_completed_author_acceptance_and_modified_old_source_block_rewrite(self):
        old,head,prose=self.old_branch()
        request=self.request(old,head,prose)
        old_path=Path(old["chapters"][0]["candidate"])
        old_bytes=old_path.read_bytes()
        old_path.write_bytes(old_bytes+b"x")
        try:
            with self.assertRaisesRegex(
                WritingExecutionError,"WF_CHAPTER_FORK_MANUSCRIPT_CHANGED"):
                _prepare_unaccepted_chapter_fork(
                    **self._prepare_args(request))
        finally:
            old_path.write_bytes(old_bytes)
        manifest=Path(old["job_dir"])/"job_manifest.json"
        original=manifest.read_text("utf8")
        doc=json.loads(original)
        doc["chapters"][1]["accepted"]=True
        manifest.write_text(json.dumps(doc,ensure_ascii=False),encoding="utf8")
        try:
            with self.assertRaisesRegex(
                WritingExecutionError,"WF_CHAPTER_FORK_ACCEPTED_OR_GAPPED"):
                _prepare_unaccepted_chapter_fork(
                    **self._prepare_args(request))
        finally:
            manifest.write_text(original,encoding="utf8")

    def _prepare_args(self,request):
        return {
            **request,"retained_resume":self.parent,
            "project_id":self.project,"scene_id":self.scene,
            "outline_sha256":sha(self.outline),
            "source_snapshot_id":self.assist.rt.pinned_snapshot_id,
            "model_used":self.assist.model,
            "chapter_count":2,
        }

    def test_selected_new_branch_rejects_old_v117_at_run_entry(self):
        old,head,prose=self.old_branch()
        fresh=self.run_writer(
            out="redone",answer_list=replies(1,alternate=True),
            fork=self.request(old,head,prose))
        receipt=json.loads(Path(fresh["cross_chapter_fork_receipt"]).read_text(
            "utf8"))
        untouched=self.root/"should-not-exist"
        with patch("writerforge.writing_assist.local_chat_completion") as model:
            with self.assertRaisesRegex(
                WritingExecutionError,"WF_CHAPTER_FORK_OLD_DESCENDANT_BLOCKED"):
                AutonomousWriting(self.assist).run(
                    outline=self.outline,
                    chapter_goals=["沈砚又发现另外一个需要回答的问题，必须保留前章来源。"],
                    draft_mode="continuity_guard",
                    resume_story_checkpoint=head,
                    selected_fork_receipt=receipt,
                    output_dir=untouched)
            model.assert_not_called()
        self.assertFalse(untouched.exists())

    def test_only_new_v117_head_can_continue_writer_to_next_chapter(self):
        old,old_head,original=self.old_branch()
        fresh=self.run_writer(
            out="regenerated",answer_list=replies(1,alternate=True),
            fork=self.request(old,old_head,original))
        selected=json.loads(Path(fresh["cross_chapter_fork_receipt"]).read_text(
            "utf8"))
        new_head=json.loads(Path(fresh["chapters"][-1][
            "v117_unreviewed_text_trace_resume"]).read_text("utf8"))
        answers=replies(3,alternate=True)[:4]
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=answers) as provider:
            following=AutonomousWriting(self.assist).run(
                outline=self.outline,
                chapter_goals=["新的故事选择只继承真正生效的前章人物视角与物件状态。"],
                draft_mode="continuity_guard",
                resume_story_checkpoint=new_head,
                selected_fork_receipt=selected,
                output_dir=self.root/"following")
        self.assertEqual(provider.call_count,4)
        self.assertEqual(following["chapter_count"],1)
        self.assertEqual(following["chapters"][0]["story_chapter_index"],3)
        last=json.loads(Path(following["chapters"][0][
            "v117_unreviewed_text_trace_resume"]).read_text("utf8"))
        parent_core=read_core_from_resume(
            new_head,project_id=self.project,scene_id=self.scene)
        child_core=read_core_from_resume(
            last,project_id=self.project,scene_id=self.scene)
        self.assertEqual(child_core["parent_sha256"],
                         parent_core["receipt_sha256"])
        old_graph=read_core_from_resume(
            old_head,project_id=self.project,scene_id=self.scene)
        self.assertNotEqual(child_core["parent_sha256"],
                            old_graph["receipt_sha256"])
        old_descendant={x["source_sha256"] for x in
                        selected["obsolete_only_in_this_fork"]}
        self.assertFalse(any(
            item["source_sha256"] in old_descendant
            for item in child_core["memory"]["hot"]+
                        child_core["memory"]["warm"]))
        self.assertEqual(following["canonical_fact_writes"],0)

    def test_legacy_valid_but_unbound_resume_cannot_start_new_G_writing(self):
        # Authentic old V117 files may contain separately signed V114 and
        # graph snapshots whose true chapter-assembly relationship was
        # never recorded. They remain readable, but cannot be source of
        # *new* chapters until that provenance is independently checked.
        from writerforge.v117_continuity_trace import RESUME,packed,hashb
        graph=new_graph(project_id=self.project,scene_id=self.scene)
        a=visible_prose(1,1)
        b=visible_prose(1,2)
        whole=a+"\\n\\n"+b
        first=external_temporal_step(a,cast=ACTORS)
        last=external_temporal_step(b,cast=ACTORS,prior=first)
        path=self.root/"legacy-chapter.md"
        path.write_text(whole,encoding="utf8")
        graph=advance_graph(
            graph,project_id=self.project,scene_id=self.scene,
            chapter_index=1,prose=whole,events=())
        graph=record_chapter_memory(
            graph,project_id=self.project,scene_id=self.scene,
            chapter_index=1,source_path=str(path),prose=whole)
        legacy={
            "format":RESUME,"project_id":self.project,"scene_id":self.scene,
            "chapter_index":1,
            "source_checkpoint_sha256":last["receipt_sha256"],
            "source_prose_sha256":last["source_sha256"],
            "unreviewed_story_state_checkpoint":last,
            "author_accepted":False,"literary_truth_verified":False,
            "canon_writes":0,"model_calls":0,
            "unified_narrative_core":graph,
        }
        legacy["receipt_sha256"]=hashb(packed(legacy))
        self.assertEqual(
            read_resume(legacy,project_id=self.project,
                        scene_id=self.scene),last)
        dest=self.root/"old-unbound-rejected"
        with patch("writerforge.writing_assist.local_chat_completion") as model:
            with self.assertRaisesRegex(
                WritingExecutionError,"WF117_GRAPH_TEMPORAL_SOURCE_UNBOUND"):
                AutonomousWriting(self.assist).run(
                    outline=self.outline,
                    chapter_goals=["新一章必须继承真实、可证的前章物件和人物状态。"],
                    draft_mode="continuity_guard",
                    resume_story_checkpoint=legacy,output_dir=dest)
            model.assert_not_called()
        self.assertFalse(dest.exists())

    def test_tampered_branch_selection_receipt_rejected(self):
        old,head,prose=self.old_branch()
        rebuilt=self.run_writer(out="new",answer_list=replies(1,alternate=True),
                               fork=self.request(old,head,prose))
        receipt=json.loads(Path(rebuilt["cross_chapter_fork_receipt"]).read_text(
            "utf8"))
        receipt["new_branch_final_chapter_index"]=900
        target=self.root/"should-not-be-created"
        new_head=json.loads(Path(rebuilt["chapters"][-1][
            "v117_unreviewed_text_trace_resume"]).read_text("utf8"))
        with patch("writerforge.writing_assist.local_chat_completion") as model:
            with self.assertRaisesRegex(
                WritingExecutionError,"WF_CHAPTER_FORK_RECEIPT_TAMPERED"):
                AutonomousWriting(self.assist).run(
                    outline=self.outline,
                    chapter_goals=["谨慎处理下一个章节人物互不知情的事件。"],
                    draft_mode="continuity_guard",
                    resume_story_checkpoint=new_head,
                    selected_fork_receipt=receipt,output_dir=target)
            model.assert_not_called()
        self.assertFalse(target.exists())


class HotWarmColdRetentionAcrossFork(TestCase):
    def test_only_signed_prefix_owns_previous_hot_warm_and_cold(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            project="old-long-story"
            scene="long-scene"
            graph=new_graph(project_id=project,scene_id=scene,chapter_index=0)
            checkpoint=None
            for n in range(1,14):
                prose=(f"第{n}章，沈砚仍在山门前看着更早的雨痕。"
                       "他记得每件事情应当从真正写出的原文里寻找证据。"
                       "远处路人离开，旧事未曾得到新的答案。")
                path=root/f"chapter-{n:03d}.md"
                path.write_text(prose,encoding="utf8")
                checkpoint=external_temporal_step(prose,
                                                   cast=("沈砚",),prior=checkpoint)
                graph=advance_graph(
                    graph,project_id=project,scene_id=scene,
                    chapter_index=n,prose=prose,events=())
                graph=record_chapter_memory(
                    graph,project_id=project,scene_id=scene,
                    chapter_index=n,source_path=str(path),prose=prose,
                    archive_writer=lambda packet:
                        _save_unified_cold_capsule(root,packet))
            parent=make_resume(project_id=project,scene_id=scene,
                               chapter_index=13,checkpoint=checkpoint,
                               unified_narrative_core=graph)
            memory=graph["memory"]
            self.assertEqual(len(memory["hot"]),3)
            self.assertEqual(len(memory["warm"]),8)
            self.assertGreater(memory["cold_count"],0)
            self.assertIsNotNone(memory["cold_head"])
            # The saved parent is signed and references only <= chapter13.
            restored=read_core_from_resume(parent,project_id=project,
                                           scene_id=scene)
            self.assertEqual(restored["receipt_sha256"],graph["receipt_sha256"])
            before=json.dumps(memory,ensure_ascii=False,sort_keys=True)
            new_prose="沈砚望见云层散开，唐蜃也看着无人的山谷。"
            regenerated_graph=advance_graph(graph,project_id=project,scene_id=scene,
                                    chapter_index=14,prose=new_prose,events=())
            new_path=root/"chapter-14-rewritten.md"
            new_path.write_text(new_prose,encoding="utf8")
            regenerated_graph=record_chapter_memory(
                regenerated_graph,project_id=project,scene_id=scene,chapter_index=14,
                source_path=str(new_path),prose=new_prose,
                archive_writer=lambda packet:
                    _save_unified_cold_capsule(root,packet))
            self.assertEqual(json.dumps(memory,ensure_ascii=False,
                                        sort_keys=True),before)
            self.assertEqual(regenerated_graph["memory"]["hot"][-1]["source_sha256"],
                             sha(new_prose))
            self.assertEqual(regenerated_graph["parent_sha256"],
                             graph["receipt_sha256"])
            self.assertFalse(any(x["chapter"]>=14 for x in
                                 graph["memory"]["hot"]+graph["memory"]["warm"]))
            self.assertEqual(regenerated_graph["memory"]["cold_count"],
                             memory["cold_count"]+1)


if __name__=="__main__":
    import unittest
    unittest.main()
