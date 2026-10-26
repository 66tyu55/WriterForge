"""0.AU: G opt-in V98 uses signed source, never review-only as plot truth."""
import unittest
from writerforge.v98_rolling_causal_planner import g_source_replan_eligibility
from writerforge.v96_causal_turns import check_turn,review_only_model_turn,canonical,digest,V96CausalDraftError
from writerforge.verified_flow import WritingExecutionError
from test_v96_causal_turns import prose1,ACTION1,EFFECT1,response,plan

class GWriterRollingGate(unittest.TestCase):
    def test_real_action_effect_is_a_provisional_replan_basis(self):
        turn=check_turn(response(prose1(),ACTION1,EFFECT1),plan()[0],mode="causal_guard")
        doc=g_source_replan_eligibility((turn,))
        self.assertTrue(doc["eligible"])
        self.assertFalse(doc["causal_truth_verified"])
    def test_review_only_cannot_be_relabelled_as_real_cause(self):
        turn=review_only_model_turn(response(prose1(),ACTION1,ACTION1),plan()[0],
             failure_code="WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED")
        doc=g_source_replan_eligibility((turn,))
        self.assertFalse(doc["eligible"])
        self.assertEqual(doc["reason"],"PREVIOUS_TRACE_REVIEW_ONLY")
        tampered={**turn,"prose":turn["prose"]+"伪造"}
        with self.assertRaises(Exception):
            g_source_replan_eligibility((tampered,))

    def test_0av_real_author_interiority_is_a_valid_unforced_narrative_turn(self):
        """RED from real new paid author plan: interiority is legitimate prose, not an action."""
        import json
        from writerforge.v96_causal_turns import parse_turn_outline,CAUSAL_KINDS
        author_plan={"turns":[
            {"id":"t01","kind":"dialogue","actor":"林槐/许照",
             "goal":"通过不完整的对讲机话音表现双方认知差异和冲突",
             "causal_parent":None,"craft_focus":["dialogue","restraint"]},
            {"id":"t02","kind":"interiority","actor":"林槐",
             "goal":"在真正动手前林槐反复权衡停电时间与医院未知的水压",
             "causal_parent":"t01","craft_focus":["interiority","pacing"]}]}
        parsed=parse_turn_outline(json.dumps(author_plan,ensure_ascii=False))
        self.assertEqual(parsed[0]["actor"],"林槐/许照")
        self.assertEqual(parsed[1]["kind"],"interiority")
        self.assertNotIn("interiority",CAUSAL_KINDS)
        self.assertEqual(parsed[1]["goal"],author_plan["turns"][1]["goal"])
    def test_0av_interiority_keeps_parent_temporal_not_fake_effect(self):
        from writerforge.v96_causal_turns import parse_turn_outline,check_turn
        import json
        beats=parse_turn_outline(json.dumps({"turns":[
            {"id":"t01","kind":"interiority","actor":"林槐",
             "goal":"林槐承认自己尚未知道医院的实际水压",
             "causal_parent":None,"craft_focus":["interiority"]},
            {"id":"t02","kind":"quiet","actor":"林槐",
             "goal":"暂时不决定开阀，在对讲机静默中留白",
             "causal_parent":"t01","craft_focus":["restraint"]}]},
             ensure_ascii=False))
        prose=("她看着屏幕上的刻度，却不敢说数字究竟代表什么。"
               "城西医院是否已经断水没有回报，井下的人只听见半截对讲机话音。"
               "林槐想起白天那场争执，但并未因此认定有人改动封签。"
               "她知道自己的恐惧不等于证据，手指停在控制板边缘。")
        a=check_turn(json.dumps({"prose":prose,"trace":{
            "action_quote":None,"effect_quote":None,
            "parent_effect_quote":None}},ensure_ascii=False),
            beats[0],mode="causal_guard")
        b=check_turn(json.dumps({"prose":prose+"她停住了手。",
            "trace":{"action_quote":None,"effect_quote":None,
                     "parent_effect_quote":None}},ensure_ascii=False),
            beats[1],mode="causal_guard",accepted=(a,))
        self.assertIsNone(a["effect_quote"])
        self.assertTrue(b["receipt"]["parent_temporal_link_unverified"])
        self.assertFalse(b["receipt"]["causal_relation_verified"])


    def test_0av_g_schedules_two_real_dialogue_participants_not_one_fake_person(self):
        """RED on saved DeepSeek t01: A/B should keep duet, not invent a third person."""
        from writerforge.narrative_core import new_graph,schedule
        graph=new_graph(project_id="0av-actors",scene_id="nightvalve",chapter_index=0)
        planned={"id":"t01","kind":"dialogue","actor":"林槐/许照",
                 "goal":"林槐隔着对讲机与井下的许照发生第一次严重分歧",
                 "causal_parent":None,"craft_focus":["dialogue","restraint"]}
        preview=schedule(graph,project_id="0av-actors",scene_id="nightvalve",
                         chapter_index=1,beat=planned)
        self.assertEqual(preview["model_calls"],0)
        self.assertEqual(preview["canon_writes"],0)
        self.assertTrue(preview["knowledge_is_character_scoped"])
        self.assertEqual(preview["ensemble_source_actor_labels"],["林槐","许照"])
        self.assertTrue(preview["ensemble_composite_actor_not_personified"])
        self.assertNotIn("character:林槐/许照",graph["nodes"])

    def test_0av_interiority_receives_non_forced_character_lens(self):
        """A writer's introspective beat should not be coerced into a decision/action."""
        from writerforge.narrative_core import new_graph,schedule
        graph=new_graph(project_id="0av-lens",scene_id="nightvalve",chapter_index=0)
        beat={"id":"t01","kind":"interiority","actor":"林槐",
              "goal":"面对不确定的医院水压林槐想清楚自己真正害怕的事",
              "causal_parent":None,"craft_focus":["interiority"]}
        guide=schedule(graph,project_id="0av-lens",scene_id="nightvalve",
                       chapter_index=1,beat=beat)
        self.assertEqual(guide["model_calls"],0)
        self.assertTrue(guide["knowledge_is_character_scoped"])


    def test_0av_v120_keeps_original_duet_dialogue_without_fake_single_actor(self):
        """RED: original DeepSeek joint dialogue must be a valid UNPROVEN plan."""
        from writerforge.v120_plan_prose_gate import compare_plan_to_prose
        from hashlib import sha256
        beat={"id":"t01","kind":"dialogue","actor":"林槐/许照",
              "goal":"林槐通过对讲机向许照核对两份签名不同的检修记录",
              "causal_parent":None}
        prose=("林槐握着对讲机解释两份记录互相矛盾。"
               "许照听见一阵电流声，要求她核对封签，却仍没有亲眼看见控制室。"
               "医院的真实水压没有新的报告，林槐也不敢说自己知道答案。")
        r=compare_plan_to_prose(
            project_id="0av-duet",scene_id="nightvalve",
            beat=beat,prose=prose,cast=("林槐","许照"))
        self.assertEqual(r["status"],"UNPROVEN")
        self.assertEqual(r["coverage"],"NON_STATEFUL_BEAT")
        self.assertIsNone(r["expected_narrow_state"])
        self.assertEqual(r["prose_sha256"],sha256(prose.encode("utf8")).hexdigest())
        self.assertEqual(r["canon_writes"],0)
        self.assertFalse(r["whole_beat_goal_verified"])

    def test_0av_v120_interiority_is_not_automatically_action(self):
        from writerforge.v120_plan_prose_gate import compare_plan_to_prose
        beat={"id":"t04","kind":"interiority","actor":"林槐",
              "goal":"林槐犹豫是否可以再催促井下工人",
              "causal_parent":None}
        prose=("仪表绿线停在那里，她不知城西医院是否已经断了水。"
               "林槐想起许照昨夜的一句话，又怀疑自己此前听错了编号，"
               "但这些念头都不能当成封签已经被人动过的证据。")
        r=compare_plan_to_prose(
            project_id="0av-duet",scene_id="nightvalve",
            beat=beat,prose=prose,cast=("林槐","许照"))
        self.assertEqual(r["status"],"UNPROVEN")
        self.assertEqual(r["coverage"],"NON_STATEFUL_BEAT")
        self.assertIsNone(r["expected_narrow_state"])


    def test_0av_v118_real_t04_interiority_is_never_contract_rejected(self):
        """Real paid A wrote three turns; t04's interiority is author choice."""
        from writerforge.v118_lamp_scheduler import plan_scene_lamps
        beat={"id":"t04","kind":"interiority","actor":"林槐",
              "goal":"在未证实的水压与停电之间反复怀疑自己的开阀命令",
              "causal_parent":"t03",
              "craft_focus":["interiority","pacing"]}
        receipt=plan_scene_lamps(project_id="0av-nightvalve",
            chapter_index=1,turn_index=4,beat=beat)
        self.assertEqual(receipt["beat_kind"],"interiority")
        self.assertEqual(receipt["new_model_calls"],0)
        self.assertEqual(receipt["factjournal_canon_writes"],0)
        self.assertFalse(receipt["literary_quality_improvement_proven"])

    def test_G_requires_explicit_opt_in_parameter(self):
        from writerforge.writing_assist import AutonomousWriting
        import inspect
        self.assertIn("g_rolling_author_planning",inspect.signature(AutonomousWriting.run).parameters)
