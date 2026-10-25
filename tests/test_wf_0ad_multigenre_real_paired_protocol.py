"""0.AD offline fraud-and-scope tests for four different REAL writing jobs.

Never produce "successful literary progress" out of synthetic tests, and
never allow a paragraph with questionable state to become Canon.
"""
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch
import json

from experiments import wf_0ad_multigenre_real_paired_writing_20261025 as exp


class ModelFreeNovelist:
    def __init__(self):self.calls=[]
    def ask(self,scene,stage,role,prompt,tokens):
        self.calls.append((scene,stage,role,tokens))
        name=next(g["actor"] for g in exp.GENRES if g["id"]==scene)
        action=f"{name}把桌上的一页纸慢慢摊到窗边，反复看了上面的数字"
        effect=f"这次核对让{name}发现旧记录里确实多出一处无法解释的水痕"
        text=(
            f"天还没有亮，{name}站在潮湿的门口，听见外头的风从远处吹来。"
            f"他不知道自己的下一步会不会影响到别人，却仍决定先检查眼前确实存在的记录。"
            f"{action}。"
            f"{effect}。"
            f"他停了半晌，没有把猜测当作结论，也没有急着把责任推给未到场的人。"
            f"长桌上的旧纸发出轻微的响声，清晨的灯仍旧亮着。"
        )
        assert 130<len(text)<500
        if stage=="bare-author":
            return {"prose":text}
        if stage=="WF-author":
            return {"prose":text,"trace":{
                "action_quote":action,"effect_quote":effect,
                "parent_effect_quote":None}}
        if stage in ("anonymous-rater-first","anonymous-rater-reversed"):
            return {"ratings":[{
                "id":k,"scores":{c:(12 if k=="甲" else 13)
                                 for c in exp.CRITERIA},
                "reason":"叙述通过具体动作展示人物观察，语义基本连贯。",
                "weakness":"部分情绪变化较直白，细节尚可进一步增加。"}
                for k in ("甲","乙")]}
        raise AssertionError("Unknown model task "+stage)

class DiversePairingProtocol(unittest.TestCase):
    def test_four_different_genres_actors_roles_and_frozen_budget(self):
        self.assertEqual(len(exp.GENRES),4)
        self.assertEqual(len({x["genre"] for x in exp.GENRES}),4)
        self.assertEqual(len({x["topic"] for x in exp.GENRES}),4)
        self.assertEqual(len({x["actor"] for x in exp.GENRES}),4)
        self.assertEqual(len({x["literary_task"] for x in exp.GENRES}),4)
        self.assertEqual(exp.MAX_CALLS,16)
        self.assertEqual(len(exp.CRITERIA),5)
        self.assertEqual(exp.JUDGEMENTS[0],("裸模型","WF辅助"))
        self.assertEqual(exp.JUDGEMENTS[1],("WF辅助","裸模型"))

    def test_one_genre_two_actual_source_contracts_same_goal(self):
        fake=ModelFreeNovelist()
        for item in exp.GENRES:
            with self.subTest(item=item["genre"]):
                receipt=exp.author_pair(fake,item)
                self.assertTrue(receipt["stage_source_verified"])
                self.assertEqual(receipt["WF"]["V96"],
                                 "EXACT_OBSERVABLE_ANCHORS_ONLY")
                self.assertFalse(receipt["WF"]["V116_blocked"])
                self.assertEqual(receipt["WF"]["V116_hard_findings"],[])
                self.assertEqual(receipt["WF"]["V122_relation_pairs"],[])
                self.assertEqual(receipt["bare"]["source_sha256"],
                                 exp.h(receipt["bare"]["prose"]))
                self.assertEqual(receipt["WF"]["source_sha256"],
                                 exp.h(receipt["WF"]["prose"]))

    def test_each_genre_blind_judged_in_both_orders(self):
        fake=ModelFreeNovelist()
        item=exp.GENRES[0]
        writing=exp.author_pair(fake,item)
        scoring=exp.judge_pair(fake,item,writing)
        self.assertEqual(scoring["裸模型"]["score_100"],62.5)
        self.assertEqual(scoring["WF辅助"]["score_100"],62.5)
        self.assertEqual(scoring["WF_minus_bare"],0)
        self.assertEqual(scoring["WF辅助"]["per_order_scores"],[65,60])
        self.assertEqual(scoring["裸模型"]["per_order_scores"],[60,65])
        self.assertEqual(len(fake.calls),4)

    def test_realistic_partial_attribution_can_be_normalized_without_rewriting_prose(self):
        from writerforge.v96_causal_turns import (
            normalize_model_source_citations,check_turn)
        item=exp.GENRES[0]
        action="他从工具包侧袋摸出一支记号笔，是白天在五金店买的"
        effect="他把记号笔放进外套内袋，贴着胸口"
        prose=(
            "夜班站台上，许临停在钟下，等父亲把电话里的话说完。"
            "他把手机揣回衣兜，从工具包侧袋摸出一支记号笔，是白天在五金店买的。"
            "他没有马上写字，因为刚才那通电话里提到的药盒说明他仍不放心。"
            "父亲没有解释药瓶到底放在哪里，他也不打算替父亲臆测结论。"
            "末班车驶进站台时，许临站起来，把记号笔放进外套内袋，贴着胸口。")
        doc={"prose":prose,"trace":{
            "action_quote":action,"effect_quote":effect,
            "parent_effect_quote":None}}
        beat={"id":"t01","kind":item["kind"],"actor":item["actor"],
              "goal":item["literary_task"]+"人物在已有场景中自行决定语言与行动",
              "causal_parent":None,"craft_focus":[]}
        raw=json.dumps(doc,ensure_ascii=False)
        normalized,receipt=normalize_model_source_citations(
            raw,beat,accepted=())
        self.assertIsNotNone(receipt)
        after=json.loads(normalized)
        self.assertEqual(after["prose"],prose)
        self.assertNotEqual(after["trace"]["action_quote"],action)
        self.assertNotEqual(after["trace"]["effect_quote"],effect)
        actual=check_turn(normalized,beat,mode="causal_guard")
        self.assertEqual(actual["receipt"]["causal_check"],
                         "EXACT_OBSERVABLE_ANCHORS_ONLY")

    def test_anonymous_prefix_rating_is_not_a_literary_score_change(self):
        original={"ratings":[{
            "id":label,"scores":{key:value for key in exp.CRITERIA},
            "reason":"可见动作关联人物选择，但没有说明全部前史。",
            "weakness":"场面所展示的阻力可以更自然。"}
            for label,value in (("匿名甲",12),("匿名乙",15))]}
        parsed=exp.parse_judge(original)
        self.assertEqual(parsed["甲"]["scores"]["语言自然与节制"],12)
        self.assertEqual(parsed["乙"]["scores"]["语言自然与节制"],15)
        self.assertEqual(original["ratings"][0]["id"],"匿名甲")
        self.assertEqual(original["ratings"][1]["id"],"匿名乙")

    def test_invalid_model_grades_are_not_completed_scores(self):
        valid={"ratings":[{"id":"甲","scores":{x:12 for x in exp.CRITERIA},
                           "reason":"当前片段动作自然但缺少进一步后果。",
                           "weakness":"情绪节奏还可以适当优化。"},
                          {"id":"乙","scores":{x:11 for x in exp.CRITERIA},
                           "reason":"场景信息较清楚，但人物选择略仓促。",
                           "weakness":"部分因果还需要更明确地表现。"}]}
        self.assertEqual(len(exp.parse_judge(valid)),2)
        for bad in ({"ratings":[]},
                    {"ratings":[valid["ratings"][0],valid["ratings"][0]]},
                    {"ratings":[{**valid["ratings"][0],
                       "scores":{c:True for c in exp.CRITERIA}},
                        valid["ratings"][1]]}):
            with self.subTest(bad=bad),self.assertRaises(RuntimeError):
                exp.parse_judge(bad)

    def test_a_real_WF_physical_source_question_not_auto_granted_as_clean(self):
        from writerforge.v116_state_delta import preflight_next_prose
        text="芯片仍在隔离盒里。芯片已经被人从隔离盒里取出来。"
        result=preflight_next_prose(text,previous_candidate_state={},cast=())
        self.assertIn("NEEDS_SOURCE_RELATION_REVIEW",
                      result["review_findings"])
        self.assertTrue(result["needs_review"])
        self.assertFalse(result["blocked"])

    def test_no_literary_score_is_automatically_given_to_WF_memory(self):
        import inspect
        script=inspect.getsource(exp.main)
        self.assertNotIn("record_chapter_memory(",script)
        self.assertNotIn("writerforge.literary_grade(",script)
        self.assertIn("no_author_forced_revisions_or_retries",script)
        self.assertIn("statistical_literary_improvement_proven",script)

if __name__=="__main__":
    unittest.main()
