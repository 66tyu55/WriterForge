"""A genuinely observed three-chapter WF failure: omniscient seed -> POV leak.

These are invented counterexamples, NOT pasted model manuscript or
user-private fiction. The same existing unified graph tracks author-confirmed
UNKNOWN facts; it must prompt the writer even when a beat does not contain
the secret's exact name. A new real disclosure is reviewable, not forbidden.
"""
import unittest

from writerforge.narrative_core import (
    new_graph,advance_graph,schedule,audit_candidate,knows,
)


P="writerforge-synthetic-pov-probe"
S="chapter-knowledge-scope"
SEED=("简洛在柜台捡到蓝印运单，纸面只写灰袋三十，"
      "没有收货地点；他还没有告诉陶筠。")
NAME="灰袋三十"


def graph():
    g=new_graph(project_id=P,scene_id=S)
    events=[
        {"id":"source-fact","kind":"FACT","quote":SEED,"start":0,
         "author_confirmed":True,"fact_id":"blue-slip",
         "name":NAME,"visibility":"SECRET"},
        {"id":"source-unknown","kind":"UNKNOWN","quote":SEED,"start":0,
         "author_confirmed":True,"actor":"陶筠","fact_id":"blue-slip"},
    ]
    return advance_graph(
        g,project_id=P,scene_id=S,chapter_index=1,
        prose=SEED,events=events)


def beat(actor,goal,kind="decision"):
    return {"id":"t01","kind":kind,"actor":actor,"goal":goal,
            "causal_parent":None,"craft_focus":[]}


class PovWithoutReaderOmniscience(unittest.TestCase):
    def test_actual_registered_unknown_must_reach_writer_without_keyword_goal(self):
        state=graph()
        self.assertEqual(knows(state,character="陶筠",fact_id="blue-slip"),
                         "AUTHOR_ASSERTED_UNKNOWN")
        goal="陶筠决定是否在封院前把工资账公开给简洛"
        self.assertNotIn(NAME,goal)
        planned=schedule(
            state,project_id=P,scene_id=S,chapter_index=2,
            beat=beat("陶筠",goal))
        self.assertIn("人物尚未知情的来源底线",planned["required_context"])
        self.assertIn("灰袋三十",planned["required_context"])
        self.assertIn("不等于人物知道",planned["required_context"])
        self.assertIn("先写出亲见、查阅或被告知的经过",
                      planned["required_context"])
        self.assertEqual(planned["author_unknown_proactive_eligible"],1)
        self.assertEqual(planned["author_unknown_proactive_chosen"],1)
        self.assertIn("NPC_KNOWLEDGE",
                      [row["lane"] for row in planned["tasks"]])

    def test_unrelated_pov_and_quiet_scene_do_not_expose_seed_secrets(self):
        state=graph()
        outsider=schedule(
            state,project_id=P,scene_id=S,chapter_index=2,
            beat=beat("闻遥","闻遥到院外独自等工人下班"))
        self.assertNotIn(NAME,outsider["required_context"])
        self.assertEqual(outsider["author_unknown_proactive_eligible"],0)
        quiet=schedule(
            state,project_id=P,scene_id=S,chapter_index=2,
            beat=beat("陶筠","陶筠默默看雨",kind="quiet"))
        self.assertNotIn(NAME,quiet["required_context"])
        self.assertEqual(quiet["author_unknown_proactive_chosen"],0)
        # Explicit mention of the same source fact remains a relevant
        # guard even in a quiet scene, no automatic knowledge transfer.
        explicit=schedule(
            state,project_id=P,scene_id=S,chapter_index=2,
            beat=beat("陶筠","陶筠不曾看过灰袋三十的单据",kind="quiet"))
        self.assertIn("NPC_KNOWLEDGE",
                      [row["lane"] for row in explicit["tasks"]])

    def test_fact_in_character_dialogue_is_reviewed_not_auto_hard_rejected(self):
        state=graph()
        draft="陶筠放下账本：“灰袋三十是什么？我似乎从没看到过这个数字。”"
        result=audit_candidate(
            state,project_id=P,scene_id=S,
            prose=draft,cast=("陶筠","简洛"))
        self.assertTrue(result["needs_review"])
        self.assertFalse(result["blocked"])
        self.assertIn("WFCORE_UNREVIEWED_UNKNOWN_FACT_MENTION",
                      result["review_findings"])
        self.assertEqual(result["source_interaction_proposals"][
            "automatic_knowledge_commits"],0)
        # Even a plausible legitimate disclosure must not be auto-accepted.
        evidence="简洛把写着灰袋三十的单据递给陶筠，并当面讲了来历。"
        possible=audit_candidate(
            state,project_id=P,scene_id=S,prose=evidence,
            cast=("简洛","陶筠"))
        self.assertIn("WFCORE_UNREVIEWED_UNKNOWN_FACT_MENTION",
                      possible["review_findings"])
        self.assertFalse(possible["blocked"])
        self.assertEqual(possible["canon_writes"],0)

    def test_author_clarified_real_pilot_seed_is_source_anchorable(self):
        # The previous real source has Chinese quotation marks around the
        # inscription; strict source events cannot span those quoted zones.
        # A clearly disclosed synthetic author clarification preserves the
        # old source byte sequence as a prefix and creates real FACT+UNKNOWN.
        from experiments import wf_pov_unknown_real_prose_probe as probe
        from experiments.wf_real_self_scene_diagnostics import source_event
        from writerforge.narrative_core import knows
        case=probe.case_with_author_known_unknown()
        self.assertTrue(case["seed"].startswith(probe.pilot.SOURCE))
        self.assertNotEqual(case["seed"],probe.pilot.SOURCE)
        core=new_graph(project_id=P,scene_id=S)
        core=advance_graph(
            core,project_id=P,scene_id=S,chapter_index=1,
            prose=case["seed"],
            events=[source_event(case["seed"],n,event)
                    for n,event in enumerate(case["event_quotes"],1)])
        self.assertEqual(
            knows(core,character="陶筠",fact_id="blue-shipping-note"),
            "AUTHOR_ASSERTED_UNKNOWN")
        scene=schedule(core,project_id=P,scene_id=S,chapter_index=2,
                       beat=beat("陶筠",
                                 "陶筠清点活字并询问简洛当夜值班情况"))
        self.assertIn("灰袋三十",scene["required_context"])
        self.assertEqual(scene["author_unknown_proactive_chosen"],1)

    def test_no_author_unknown_does_not_invent_an_invisible_prohibition(self):
        source=new_graph(project_id=P,scene_id=S)
        result=schedule(
            source,project_id=P,scene_id=S,chapter_index=1,
            beat=beat("陶筠","陶筠询问工人账单是否丢失"))
        self.assertEqual(result["author_unknown_proactive_chosen"],0)
        self.assertNotIn("灰袋三十",result["required_context"])


if __name__=="__main__":
    unittest.main()
