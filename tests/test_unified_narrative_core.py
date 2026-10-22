"""One narrative middleware graph: keyed diff, scheduler, and scoped NPC facts.

These are deterministic source-anchored author annotations and graph state
regressions, NOT proof that a model understands long literature.
"""
from __future__ import annotations

import copy
import json
import unittest

from writerforge.narrative_core import (
    NarrativeCoreError,Patch,new_graph,advance_graph,keyed_diff,
    schedule,knows,audit_candidate,propose_source_interactions,
    validate,read_core_from_resume,
)
from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v117_continuity_trace import make_resume,read_resume
from writerforge.writing_assist import (
    _prepare_guarded_turn_packet,AutonomousWriting,WritingExecutionError,
)
from writerforge.verified_flow import GroundedDraftPacket
import hashlib


P="novel-graph"
S="story-stream"
ORIGIN=("沈砚把密令藏在井底。"
        "沈砚对唐蜃立誓，迟早要追查旧案血债。")
FACT="沈砚把密令藏在井底。"
THREAD="沈砚对唐蜃立誓，迟早要追查旧案血债。"


def annotation(prose,quote,kind,**fields):
    return {
        "id":fields.pop("id","ev-"+str(prose.index(quote))),
        "kind":kind,
        "quote":quote,"start":prose.index(quote),
        "author_confirmed":True,**fields,
    }


def intro():
    state=new_graph(project_id=P,scene_id=S,chapter_index=0)
    events=[
        annotation(ORIGIN,FACT,"FACT",id="fact",
                   fact_id="secret-letter",
                   name="密令藏在井底",visibility="SECRET"),
        annotation(ORIGIN,THREAD,"THREAD_OPEN",id="thread",
                   thread_id="old-debt",thread_kind="FORESHADOW",
                   owner="沈砚",target="唐蜃",
                   premise="旧案血债的幕后人尚未查明",
                   truth_scope="CHARACTER_BELIEF"),
    ]
    return advance_graph(state,project_id=P,scene_id=S,
                         chapter_index=1,prose=ORIGIN,events=events)


def update(old,text,events=()):
    return advance_graph(old,project_id=P,scene_id=S,
                         chapter_index=old["chapter_index"]+1,
                         prose=text,events=events)


def beat(goal,actor,kind="action"):
    return {"id":"t01","kind":kind,"actor":actor,"goal":goal,
            "craft_focus":[],"causal_parent":None}


class GraphWithPriorityAndKnowledge(unittest.TestCase):
    def test_scoped_npc_unknown_not_contaminated_by_protagonist_contact(self):
        graph=intro()
        q="叶青梧尚不知道密令藏在井底。"
        graph=update(graph,q,[annotation(
            q,q,"UNKNOWN",id="bound",
            actor="叶青梧",fact_id="secret-letter")])
        q2="叶青梧在石桥遇见沈砚，两人短暂交谈。"
        next_graph=update(graph,q2,[annotation(
            q2,q2,"CONTACT",id="meeting",
            actor="叶青梧",other="沈砚")])
        self.assertEqual(knows(next_graph,character="叶青梧",
                               fact_id="secret-letter"),
                         "AUTHOR_ASSERTED_UNKNOWN")
        self.assertEqual(knows(next_graph,character="沈砚",
                               fact_id="secret-letter"),
                         "NOT_ESTABLISHED")
        self.assertTrue(any(e["kind"]=="CONTACT" for e in next_graph["edges"].values()))
        self.assertFalse(any(e["kind"]=="KNOWS" for e in next_graph["edges"].values()))
        d=keyed_diff(graph,next_graph)
        self.assertTrue(d["dirty_nodes"])
        self.assertTrue(any(v & int(Patch.RELATION)
                            for v in d["patch_flags"].values()))
        preview=schedule(next_graph,project_id=P,scene_id=S,
                         chapter_index=4,
                         beat=beat("叶青梧已经知道密令藏在井底",actor="叶青梧"))
        self.assertIn("人物认知边界",preview["required_context"])
        self.assertNotIn("旧案血债的幕后人尚未查明",
                         preview["required_context"])
        self.assertEqual(preview["tasks"][0]["lane"],"NPC_KNOWLEDGE")
        issue=audit_candidate(
            next_graph,project_id=P,scene_id=S,
            prose="叶青梧早已知道密令藏在井底。")
        self.assertTrue(issue["blocked"])
        self.assertIn("WFCORE_AUTHOR_UNKNOWN_RETCON_CONFLICT",
                      issue["hard_findings"])

    def test_source_encounter_proposed_not_knowledge_automatically(self):
        graph=intro()
        text="叶青梧尚不知道密令藏在井底。"
        graph=update(graph,text,[annotation(
            text,text,"UNKNOWN",actor="叶青梧",
            fact_id="secret-letter")])
        story="叶青梧在石桥遇见沈砚，两人只是擦肩。"
        proposals=propose_source_interactions(
            graph,project_id=P,scene_id=S,prose=story)
        self.assertEqual(len(proposals["source_contact_proposals"]),1)
        self.assertEqual(
            proposals["source_contact_proposals"][0]["actors"],
            ["叶青梧","沈砚"] if "叶青梧"<"沈砚" else
            ["沈砚","叶青梧"])
        self.assertEqual(proposals["automatic_contact_commits"],0)
        self.assertEqual(proposals["automatic_knowledge_commits"],0)
        self.assertFalse(proposals["source_contact_proposals"][0]["author_confirmed"])
        self.assertEqual(knows(graph,character="叶青梧",
                               fact_id="secret-letter"),
                         "AUTHOR_ASSERTED_UNKNOWN")
        receipt=audit_candidate(graph,project_id=P,scene_id=S,prose=story)
        self.assertEqual(receipt["blocked"],False)
        self.assertEqual(
            len(receipt["source_interaction_proposals"][
                "source_contact_proposals"]),1)

    def test_explicit_message_only_proposed_after_knowable_speaker(self):
        graph=intro()
        msg="沈砚告诉叶青梧密令藏在井底。"
        self.assertEqual(propose_source_interactions(
            graph,project_id=P,scene_id=S,prose=msg)[
                "source_disclosure_proposals"],[])
        source="沈砚亲眼看见密令藏在井底。"
        graph=update(graph,source,[annotation(
            source,source,"WITNESS",
            actor="沈砚",fact_id="secret-letter")])
        proposals=propose_source_interactions(
            graph,project_id=P,scene_id=S,prose=msg)
        self.assertEqual(len(proposals["source_disclosure_proposals"]),1)
        self.assertEqual(
            proposals["source_disclosure_proposals"][0]["speaker"],
            "沈砚")
        self.assertFalse(
            proposals["source_disclosure_proposals"][0]["author_confirmed"])
        self.assertEqual(
            knows(graph,character="叶青梧",fact_id="secret-letter"),
            "NOT_ESTABLISHED")
        approved=update(graph,msg,[annotation(
            msg,msg,"SHARE",actor="沈砚",receiver="叶青梧",
            fact_id="secret-letter")])
        self.assertEqual(
            knows(approved,character="叶青梧",fact_id="secret-letter"),
            "KNOWN")

    def test_rumors_and_dreams_do_not_propose_actual_meeting(self):
        graph=intro()
        for text in (
            "据说沈砚遇见唐蜃，两人便散去。",
            "沈砚梦见他遇见唐蜃，惊醒后冷汗直流。",
            "如果沈砚遇见唐蜃，旧仇便会复燃。"):
            with self.subTest(text=text):
                probe=propose_source_interactions(
                    graph,project_id=P,scene_id=S,prose=text)
                self.assertEqual(probe["source_contact_proposals"],[])
                self.assertEqual(probe["source_disclosure_proposals"],[])

    def test_fact_can_be_learned_only_through_named_witness(self):
        graph=intro()
        src="叶青梧尚不知道密令藏在井底。"
        graph=update(graph,src,[annotation(
            src,src,"UNKNOWN",actor="叶青梧",fact_id="secret-letter")])
        scene="叶青梧亲眼看见密令藏在井底。"
        after=update(graph,scene,[annotation(
            scene,scene,"WITNESS",actor="叶青梧",
            fact_id="secret-letter")])
        self.assertEqual(knows(after,character="叶青梧",
                               fact_id="secret-letter"),"KNOWN")
        self.assertFalse(any(e["kind"]=="UNKNOWN" for e in after["edges"].values()))
        d=keyed_diff(graph,after)
        self.assertTrue(any(f & int(Patch.KNOWLEDGE)
                            for f in d["patch_flags"].values()))
        p=schedule(after,project_id=P,scene_id=S,chapter_index=4,
                   beat=beat("叶青梧看见密令藏在井底",actor="叶青梧"))
        self.assertNotIn("人物认知边界",p["required_context"])

    def test_share_requires_that_speaker_already_knows_actual_fact(self):
        graph=intro()
        msg="叶青梧告诉唐蜃密令藏在井底。"
        event=annotation(msg,msg,"SHARE",actor="叶青梧",
                         receiver="唐蜃",fact_id="secret-letter")
        with self.assertRaisesRegex(
                NarrativeCoreError,"SPEAKER_HAS_NO_PROVEN_SOURCE_KNOWLEDGE"):
            update(graph,msg,[event])
        witness="叶青梧亲眼看见密令藏在井底。"
        graph=update(graph,witness,[annotation(
            witness,witness,"WITNESS",actor="叶青梧",
            fact_id="secret-letter")])
        shared=update(graph,msg,[event])
        self.assertEqual(knows(shared,character="唐蜃",
                               fact_id="secret-letter"),"KNOWN")
        self.assertEqual(knows(shared,character="沈砚",
                               fact_id="secret-letter"),"NOT_ESTABLISHED")
        self.assertEqual(knows(shared,character="叶青梧",
                               fact_id="secret-letter"),"KNOWN")

    def test_contact_only_even_when_npc_and_hero_are_relatives(self):
        graph=intro()
        src="沈砚和叶青梧认出彼此，两人是多年未见的旧友。"
        later=update(graph,src,[annotation(
            src,src,"CONTACT",actor="沈砚",other="叶青梧")])
        self.assertEqual(knows(later,character="叶青梧",
                               fact_id="secret-letter"),"NOT_ESTABLISHED")
        self.assertFalse(any(e["kind"]=="KNOWS" for e in later["edges"].values()))
        p=schedule(later,project_id=P,scene_id=S,
                   chapter_index=3,
                   beat=beat("叶青梧打听密令藏在井底",actor="叶青梧"))
        self.assertIn("缺少已获知的来源证据",p["required_context"])

    def test_300_dormant_chapters_keep_thread_without_prompt_pollution(self):
        graph=intro()
        base_size=len(json.dumps(graph,ensure_ascii=False))
        for chapter in range(2,302):
            old=graph
            graph=update(graph,f"第{chapter}章山雨纷纷，路人远去。")
            diff=keyed_diff(old,graph)
            self.assertEqual(diff["dirty_nodes"],[])
            self.assertEqual(diff["patch_flags"],{})
            self.assertGreaterEqual(diff["reused_nodes"],0)
            self.assertEqual(schedule(
                graph,project_id=P,scene_id=S,
                chapter_index=chapter+1,
                beat=beat("山雨纷纷，没人提起旧事",actor="沈砚",
                          kind="quiet"))["required_context"],"")
        self.assertLess(
            len(json.dumps(graph,ensure_ascii=False))-base_size,550)
        final=schedule(graph,project_id=P,scene_id=S,chapter_index=302,
                       beat=beat("沈砚与唐蜃在天牢重逢",actor="沈砚"))
        self.assertIn("LONG_THREAD",[t["lane"] for t in final["tasks"]])
        self.assertIn("旧案血债",final["required_context"])
        self.assertIn("人物看法尚未确证",final["required_context"])
        self.assertTrue(graph["nodes"]["thread:old-debt"]["props"]["status"]=="OPEN")

    def test_revenges_secrets_prophecies_share_same_thread_mechanism(self):
        graph=intro()
        scene=("叶青梧给唐蜃留下预言，唐蜃听得心惊。"
               "沈砚与叶青梧约定在重阳夜重逢。")
        graph=update(graph,scene,[
            annotation(scene,scene.split("。")[0]+"。","THREAD_OPEN",
                       id="prophecy",thread_id="prophecy-200",
                       thread_kind="MYSTERY",owner="叶青梧",target="唐蜃",
                       premise="预言真假尚未证实",truth_scope="CHARACTER_BELIEF"),
            annotation(scene,scene.split("。")[1]+"。","THREAD_OPEN",
                       id="promise",thread_id="promise-020",
                       thread_kind="PROMISE",owner="沈砚",target="叶青梧",
                       premise="重阳再会约定尚未兑现",truth_scope="AUTHOR_ASSERTED"),
        ])
        self.assertEqual(
            sum(x["kind"]=="THREAD" for x in graph["nodes"].values()),3)
        revived=schedule(graph,project_id=P,scene_id=S,chapter_index=3,
                         beat=beat("叶青梧在重阳夜想起沈砚的约定",
                                   actor="沈砚"))
        self.assertIn("LONG_THREAD",[t["lane"] for t in revived["tasks"]])
        self.assertIn("重阳",revived["required_context"])

    def test_author_approved_resolution_is_generic_not_revenge_specific(self):
        graph=intro()
        source="沈砚与唐蜃在山门前对质，旧案终于由作者确认结案。"
        settled=update(graph,source,[annotation(
            source,source,"THREAD_RESOLVE",id="approved-close",
            thread_id="old-debt")])
        self.assertEqual(
            settled["nodes"]["thread:old-debt"]["props"]["status"],
            "RESOLVED_AUTHOR_CONFIRMED")
        self.assertTrue(any(x & int(Patch.STATUS) for x in
                            keyed_diff(graph,settled)["patch_flags"].values()))
        self.assertEqual(schedule(
            settled,project_id=P,scene_id=S,chapter_index=3,
            beat=beat("沈砚再次遇到唐蜃",actor="沈砚"))["required_context"],"")

    def test_model_claim_without_author_event_cannot_close_registered_thread(self):
        graph=intro()
        scene="沈砚说他已复仇成功，唐蜃却仍在逃。"
        after=update(graph,scene)
        self.assertEqual(
            after["nodes"]["thread:old-debt"]["props"]["status"],"OPEN")
        self.assertEqual(after["last_event_count"],0)
        self.assertEqual(keyed_diff(graph,after)["dirty_nodes"],[])

    def test_fake_author_annotation_and_wrong_span_rejected(self):
        graph=intro()
        src="叶青梧看见密令藏在井底。"
        ev=annotation(src,src,"WITNESS",actor="叶青梧",
                      fact_id="secret-letter")
        ev["author_confirmed"]=False
        with self.assertRaisesRegex(NarrativeCoreError,"AUTHOR_REVIEW"):
            update(graph,src,[ev])
        ev["author_confirmed"]=True
        ev["start"]=1
        with self.assertRaisesRegex(NarrativeCoreError,"AUTHOR_REVIEW"):
            update(graph,src,[ev])
        self.assertEqual(
            graph["nodes"]["thread:old-debt"]["props"]["status"],"OPEN")

    def test_unrelated_quoted_dream_is_never_registered_knowledge(self):
        graph=intro()
        for text in (
            "沈砚梦见叶青梧亲眼看见密令藏在井底。",
            "沈砚说：“叶青梧亲眼看见密令藏在井底。”",
            "如果叶青梧亲眼看见密令藏在井底，她会作何打算？"):
            with self.subTest(text=text),self.assertRaises(
                    NarrativeCoreError):
                update(graph,text,[annotation(
                    text,text if len(text)<=150 else text[:150],
                    "WITNESS",actor="叶青梧",fact_id="secret-letter")])

    def test_graph_does_not_leak_across_projects_or_tamper(self):
        graph=intro()
        bad=copy.deepcopy(graph)
        bad["nodes"]["thread:old-debt"]["props"]["status"]="RESOLVED"
        with self.assertRaises(NarrativeCoreError):
            validate(bad,project_id=P,scene_id=S)
        with self.assertRaises(NarrativeCoreError):
            validate(graph,project_id="other-book",scene_id=S)

    def test_legacy_v117_resume_embeds_unified_graph_without_parallel_revenge(self):
        prior=external_temporal_step(ORIGIN,cast=("沈砚","唐蜃"))
        graph=intro()
        checkpoint=make_resume(
            project_id=P,scene_id=S,chapter_index=1,
            checkpoint=prior,unified_narrative_core=graph)
        restored=json.loads(json.dumps(checkpoint,ensure_ascii=False))
        self.assertEqual(
            read_resume(restored,project_id=P,scene_id=S),prior)
        core=read_core_from_resume(restored,project_id=P,scene_id=S)
        self.assertEqual(core["receipt_sha256"],graph["receipt_sha256"])
        self.assertEqual(core["nodes"]["thread:old-debt"]["props"]["status"],"OPEN")

    def test_hard_cognition_guard_honors_prompt_budget_not_silent_skip(self):
        graph=intro()
        state="叶青梧尚不知道密令藏在井底。"
        graph=update(graph,state,[annotation(
            state,state,"UNKNOWN",actor="叶青梧",
            fact_id="secret-letter")])
        with self.assertRaisesRegex(
                NarrativeCoreError,"REQUIRED_SCENE_GUARD_EXCEEDS_BUDGET"):
            schedule(graph,project_id=P,scene_id=S,
                     chapter_index=3,max_prompt_chars=5,
                     beat=beat("叶青梧知道密令藏在井底",actor="叶青梧"))

    def test_actual_turn_dispatch_prioritizes_unknown_npc_over_craft(self):
        graph=intro()
        source="叶青梧尚不知道密令藏在井底。"
        graph=update(graph,source,[annotation(
            source,source,"UNKNOWN",actor="叶青梧",
            fact_id="secret-letter")])
        target_beat=beat("叶青梧早已知道密令藏在井底",
                         actor="叶青梧",kind="decision")
        target_beat["craft_focus"]=["interiority"]
        source_prompt="字"*9200
        packet=GroundedDraftPacket(
            scene_id=S+".chapter-003",project_id=P,snapshot_id=1,
            evidence=(),craft_ids=(),prompt=source_prompt,
            prompt_sha256=hashlib.sha256(
                source_prompt.encode("utf8")).hexdigest())
        out,lamps,receipt=_prepare_guarded_turn_packet(
            packet,plan={"objective":"她试探旧案"},facets=(),
            hard_turn_addition="角色以明确已发生的物理状态行事。",
            dependency_hint="",
            project_id=P,chapter_index=3,turn_index=0,
            beat=target_beat,frame=None,previous_lamp_receipt=None,
            narrative_graph=graph,narrative_scene_id=S)
        self.assertIn("人物认知边界",out.prompt)
        self.assertLessEqual(len(out.prompt),10000)
        self.assertTrue(receipt["hard_context_preserved"])
        self.assertEqual(
            receipt["unified_narrative_priority_dispatch"]["tasks"][0]["lane"],
            "NPC_KNOWLEDGE")
        self.assertEqual(receipt["delivered_prompt_sha256"],out.prompt_sha256)
        self.assertEqual(receipt["priority_lanes_ordered"],
                         ["HARD_STATE","NPC_KNOWLEDGE","LONG_THREAD","CRAFT"])

    def test_no_unified_graph_can_be_loaded_over_v123_legacy_arc(self):
        from writerforge.v123_long_arc import register_revenge
        source="沈砚说他要找唐蜃讨回旧债。"
        arc=register_revenge(
            project_id=P,scene_id=S,origin_chapter=1,
            source_prose=source,source_quote=source,
            arc_id="legacy-arc",actor="沈砚",target="唐蜃",
            motive="旧案仍有疑点",truth_scope="CHARACTER_BELIEF",
            author_confirmed=True)
        checkpoint=external_temporal_step(source,cast=("沈砚","唐蜃"))
        with self.assertRaisesRegex(Exception,"DUPLICATE_NARRATIVE_MEMORY"):
            make_resume(project_id=P,scene_id=S,chapter_index=1,
                        checkpoint=checkpoint,
                        long_arc_checkpoint=arc,
                        unified_narrative_core=intro())

    def test_host_refuses_unmatched_graph_before_any_model_request(self):
        class FakeAssist:
            project_id=P
            scene_id=S
        with self.assertRaisesRegex(
                WritingExecutionError,
                "WFCORE_EXPLICIT_STATE_REQUIRES_MATCHED_STORY_RESUME"):
            AutonomousWriting(FakeAssist()).run(
                outline="这是小说大纲：沈砚调查密令与旧案，寻找线索。",
                chapter_goals=["沈砚在山寺重新寻找密令的真正主人"],
                output_dir="/tmp/wf_unified_core_must_not_touch",
                draft_mode="continuity_guard",
                narrative_core_checkpoint=intro())

    def test_many_relevant_hooks_are_deduped_and_deferred_not_deleted(self):
        graph=intro()
        for i in range(12):
            text=f"沈砚对唐蜃发誓保留第{i}道未解之谜。"
            graph=update(graph,text,[annotation(
                text,text,"THREAD_OPEN",
                thread_id=f"mystery-{i:02}",
                owner="沈砚",target="唐蜃",
                thread_kind="MYSTERY",premise=f"第{i}道谜尚待解释",
                truth_scope="CHARACTER_BELIEF")])
        result=schedule(
            graph,project_id=P,scene_id=S,
            chapter_index=graph["chapter_index"]+1,
            beat=beat("沈砚询问唐蜃十二道旧谜",actor="沈砚"))
        self.assertLessEqual(len(result["required_context"]),1300)
        self.assertLessEqual(
            len([x for x in result["tasks"]
                 if x["lane"]=="LONG_THREAD"]),13)
        self.assertGreater(result["deferred_unresolved_thread_count"],0)
        self.assertEqual(
            sum(x["kind"]=="THREAD" for x in graph["nodes"].values()),13)
        self.assertTrue(all(n["props"]["status"]=="OPEN"
            for n in graph["nodes"].values() if n["kind"]=="THREAD"))

    def test_chapter_and_event_replay_never_mutate_live_state(self):
        graph=intro()
        with self.assertRaisesRegex(NarrativeCoreError,"GAP_OR_REPLAY"):
            advance_graph(graph,project_id=P,scene_id=S,
                          chapter_index=20,prose="山雨连绵")
        self.assertEqual(graph["chapter_index"],1)
        self.assertEqual(graph["nodes"]["thread:old-debt"]["props"]["status"],"OPEN")


if __name__=="__main__":
    unittest.main()
