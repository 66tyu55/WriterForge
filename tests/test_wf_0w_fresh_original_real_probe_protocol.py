"""Only code-level rehearsal of the fresh 0.W literary pilot, no paid AI."""
import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from experiments import wf_0w_new_original_autonomous_repair_once_20261025 as exp

PROSE1=(
    "夜雨打在水尺房的木檐上，姜岚守了半夜才听见台阶下的急促脚步。"
    "她没有立刻转身，而是将潮汛表放到干燥的台面上，"
    "用手背擦掉最末行沾湿的墨迹。"
    "纸面露出一道被水冲淡的红线，比昨夜记录的高度高出两寸。"
    "许槐在门边站了片刻，望见她的手迟疑地停在那道红线旁。"
)
PROSE2=(
    "姜岚记得纸面那道突然升高的红线，知道若直接呈报可能让沿河摊贩连夜搬离。"
    "她把潮汛表递到许槐面前，要求他在交接簿上写下自己的姓名。"
    "许槐皱着眉在交接簿上签了字，却不肯解释昨夜谁曾进入水尺房。"
    "姜岚没有替他编造借口，只把这次署名和模糊的红线一并抄在自己的册子上。"
)
EFFECT1="纸面露出一道被水冲淡的红线"


def raw(prose,action,effect,parent=None):
    return json.dumps({
        "prose":prose,
        "trace":{"action_quote":action,
                 "effect_quote":effect,
                 "parent_effect_quote":parent}},ensure_ascii=False)


class OfflineNovelist:
    calls=[]
    def __init__(self,key):
        self.calls=[]
        self.events=[]
        self.budget=type("Budget",(),{
            "calls_reserved":0,
            "public_receipt":lambda obj:{"calls_reserved":obj.calls_reserved}
        })()

    def ask(self,name,content,limit):
        self.calls.append((name,content,limit))
        self.budget.calls_reserved+=1
        self.events.append({"stage":name,"mock_only":True})
        if name=="first-original":
            return raw(PROSE1,"她没有立刻转身，而是将潮汛表放到干燥的台面上",
                       EFFECT1)
        if name=="second-original":
            return raw(PROSE2,"她把潮汛表递到许槐面前",
                       "许槐皱着眉在交接簿上签了字",EFFECT1)
        if name=="independent-source-reader":
            self.assert_source_only(content)
            return json.dumps({
                "observed":[],"inferred_links":[],"cross_source_links":[],
                "reader_uncertainty":"没有发现需要读者补写的实际移动动作。"
            },ensure_ascii=False)
        if name=="author-self-decision":
            return json.dumps({
                "decision":"MOVE_ON","target_turn":"current",
                "source_sha256":None,"evidence_quote":None,
                "focus":None,
                "why_now":"已经写出代价和未解的传闻，此刻可以保留人物沉默。",
                "what_goes_wrong_if_unchanged":None,
                "intended_reader_effect":None
            },ensure_ascii=False)
        raise AssertionError("Unapproved model stage: "+name)

    @staticmethod
    def assert_source_only(prompt):
        assert exp.SEED not in prompt
        assert PROSE2 in prompt

    def adapter(self,name):
        def fake(packet,*,model,api_base,max_tokens):
            assert model is None and api_base is None
            return self.ask(name,packet.prompt,max_tokens)
        return fake


EDIT_OLD="姜岚没有替他编造借口"
EDIT_NEW="姜岚依旧没有替他编造借口"
EDITED_PROSE2=PROSE2.replace(EDIT_OLD,EDIT_NEW,1)
PROSE3=(
    "凌晨的石桥上，姜岚仍记得许槐在交接簿上签下的名字。"
    "她决定先把旧表抄成两份，自己留下一份，再把另一份交给真正负责查水位的人。"
    "薄纸被河风吹得直响，城门尚未打开，她只能靠站在檐下等待天明。"
    "她还不知道旧账是谁改过，也不打算把传闻当成已经核对过的结果。"
)


class OfflineNovelistSelfReviser(OfflineNovelist):
    def ask(self,name,content,limit):
        if name=="author-self-decision":
            self.calls.append((name,content,limit))
            self.budget.calls_reserved+=1
            return json.dumps({
                "decision":"LOOK_BACK_NOW","target_turn":"current",
                "source_sha256":None,
                "evidence_quote":EDIT_OLD,"focus":"sentence",
                "why_now":"人物在签字后应表现更稳定的疑虑，当前语气突然下定论。",
                "what_goes_wrong_if_unchanged":"后续人物可能把没有证据的签字当作已知真相。",
                "intended_reader_effect":"让读者感受到谨慎但不失去继续追索的动力。"
            },ensure_ascii=False)
        if name=="author-source-V119-edit":
            self.calls.append((name,content,limit))
            self.budget.calls_reserved+=1
            if sum(row[0]=="author-source-V119-edit" for row in self.calls)==1:
                return json.dumps({
                    "decision":"REVISE","scope":"sentence",
                    "source_sha256":exp.digest(PROSE2),
                    "start":PROSE2.index(EDIT_OLD),
                    "end":PROSE2.index(EDIT_OLD)+len(EDIT_OLD),
                    "expected_original":EDIT_OLD,
                    "replacement":EDIT_NEW,
                    "trace":{
                        "action_quote":"她把潮汛表递到许槐面前",
                        "effect_quote":"许槐皱着眉在交接簿上签了字",
                        "parent_effect_quote":EFFECT1,
                    },
                    "reason":"保留已有代价，局部处理人物的判断态度。"
                },ensure_ascii=False)
            return json.dumps({
                "decision":"KEEP","scope":None,
                "source_sha256":exp.digest(EDITED_PROSE2),
                "start":None,"end":None,"expected_original":None,
                "replacement":None,"trace":None,
                "reason":"修订后的前因后果已经足够清晰，无须反复修改。"
            },ensure_ascii=False)
        if name=="author-next-beat":
            self.calls.append((name,content,limit))
            self.budget.calls_reserved+=1
            return json.dumps({"turn":{
                "id":"t03","kind":"quiet","actor":"姜岚",
                "goal":"谨慎保存已经交接的真实记录，继续调查来源而不预支未证秘密",
                "causal_parent":"t02","craft_focus":[]}},
                ensure_ascii=False)
        if name=="new-downstream-from-repaired-source":
            self.calls.append((name,content,limit))
            self.budget.calls_reserved+=1
            assert EDIT_NEW in content
            return raw(PROSE3,None,None,
                       "许槐皱着眉在交接簿上签了字")
        return super().ask(name,content,limit)



class NewOriginalPilotBoundary(unittest.TestCase):
    def test_budget_and_independent_story_identity(self):
        self.assertEqual(exp.MAX_NEW_CALLS,8)
        self.assertEqual(exp.MAX_OUTPUT_RESERVED,11400)
        self.assertEqual(len(exp.BEATS),2)
        self.assertIn("雨册",exp.SEED)
        for inherited in ("潮簿","火髓果","韩立"):
            self.assertNotIn(inherited,exp.CAST)
        self.assertNotIn("WRITERFORGE_R2_SECRET_ACCESS_KEY",exp.SEED)

    def test_two_real_v96_fragments_mock_Author_move_on_never_counts_as_repair(self):
        with TemporaryDirectory() as d:
            root=Path(d)/"new-original"
            root.mkdir()
            with patch.object(exp,"OUT",root),patch.object(
                exp,"OneNovelist",OfflineNovelist),patch.dict(
                os.environ,{"DEEPSEEK_API_KEY":"test-only-long-fake-api-key"}):
                report,model=exp.execute()
            self.assertEqual(len(model.calls),4,report)
            self.assertEqual([n for n,_,_ in model.calls],[
                "first-original","second-original",
                "independent-source-reader","author-self-decision"])
            self.assertEqual(report["actual_author_choice"],"MOVE_ON")
            self.assertEqual(report["status"],"AUTHOR_MOVED_ON_NO_SELF_REWRITE",
                             report)
            self.assertFalse(report["actually_safe_revised_prose_and_new_downstream"])
            self.assertFalse(report["new_prose_literary_improvement_independently_verified"])
            self.assertEqual(len(report["original_story_sources"]),2)
            self.assertEqual(report["R2_reads"],report["Canon_writes"])
            self.assertTrue((root/"first-author-original.md").is_file())
            self.assertTrue((root/"second-author-original.md").is_file())
            self.assertFalse((root/"REAL_AUTHOR_UNACCEPTED_STAGED_STORY.md").exists())

    def test_synthetic_v119_author_revises_and_new_downstream_is_actually_regenerated(self):
        # No model is called; this ONLY proves the exact transaction wiring.
        with TemporaryDirectory() as d:
            root=Path(d)/"one-synthetic-revision"
            root.mkdir()
            with patch.object(exp,"OUT",root),patch.object(
                exp,"OneNovelist",OfflineNovelistSelfReviser),patch.dict(
                os.environ,{"DEEPSEEK_API_KEY":"test-only-long-fake-api-key"}):
                result,writer=exp.execute()
            self.assertEqual(result["status"],
                             "GENUINE_SAME_AUTHOR_SOURCE_EDIT_AND_FRESH_DOWNSTREAM",
                             result)
            self.assertEqual(result["actual_author_choice"],"LOOK_BACK_NOW")
            self.assertTrue(result["actually_safe_revised_prose_and_new_downstream"])
            self.assertFalse(
                result["new_prose_literary_improvement_independently_verified"])
            self.assertEqual(len(writer.calls),8,writer.calls)
            self.assertTrue((root/"REAL_AUTHOR_UNACCEPTED_STAGED_STORY.md").exists())
            manuscript=(root/"REAL_AUTHOR_UNACCEPTED_STAGED_STORY.md").read_text("utf8")
            self.assertIn(EDIT_NEW,manuscript)
            self.assertNotIn(EDIT_OLD,manuscript)
            self.assertIn(PROSE3,manuscript)
            self.assertEqual(result["new_downstream_prose_sha256"],exp.digest(PROSE3))
            edit=json.loads((root/"author-V119-result.json").read_text("utf8"))
            self.assertEqual(edit["rounds"][0]["status"],"PROVISIONALLY_REVISED")
            self.assertEqual(edit["rounds"][1]["status"],"KEEP_BY_WRITER")

    def test_source_only_relation_hold_does_not_write_fiction(self):
        scene=("铜牌还在木匣里，只是铜牌已经被人从木匣里取出来。"
               "姜岚仍站在门前，没有见到谁走进档房。")
        preflight,hold=exp.check_source_gate(scene,None)
        self.assertTrue(preflight["needs_review"])
        self.assertEqual(hold["status"],"HELD_NEEDS_SOURCE_RELATION_REVIEW")
        self.assertEqual(hold["prose_sha256"],exp.digest(scene))
        self.assertEqual(hold["new_model_calls"],0)
        self.assertEqual(hold["canon_writes"],0)

    def test_new_author_must_supply_both_action_and_effect(self):
        wrong=raw(PROSE1,"她没有立刻转身，而是将潮汛表放到干燥的台面上",
                  "她没有立刻转身，而是将潮汛表放到干燥的台面上")
        with self.assertRaises(Exception):
            from writerforge.v96_causal_turns import check_turn
            check_turn(wrong,exp.BEATS[0],mode="causal_guard")


if __name__=="__main__":
    unittest.main()
