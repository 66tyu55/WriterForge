"""V102: exact generated scene evidence + emotion/pressure feedback.
All inputs are synthetic. ZERO models, no R2, no user originals.
"""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest

from test_v26_invisible_writer import PLAN,make_db
from test_v96_causal_turns import (
    ACTION1,EFFECT1,ACTION2,EFFECT2,
    plan,prose1,prose2,turns,
)
from test_v98_rolling_causal_planner import OUTLINE,GOALS,proposed,raw
from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.writing_assist import AutonomousWriting,InvisibleWritingAssist,WritingExecutionError
from writerforge.v96_causal_turns import canonical,digest
from writerforge.v102_emotional_causality import (
    V102EmotionalCausalityError,check_emotional_turn,
    pressure_context,emotion_turn_instructions,export_candidate_emotions
)

def emotional(prose,action,effect,parent,who,affect=None):
    return json.dumps({
        "prose":prose,
        "trace":{"action_quote":action,"effect_quote":effect,
                 "parent_effect_quote":parent},
        "affect":affect,
    },ensure_ascii=False,separators=(",",":"))

def note1():
    return {
        "actor":"少年","before":"焦灼担忧","after":"警觉但仍犹豫",
        "trigger_quote":ACTION1,"response_quote":EFFECT1,
        "cost_quote":"他本来答应朋友当夜入城",
        "consequence_quote":EFFECT1,
        "open_pressure":"朋友仍在城中等药，绕路将挤掉救援时间",
        "choice_shift":"少年先绕过石桥，改为核实船工的消息",
    }

def note2():
    return {
        "actor":"女子","before":"对桥索的动机存疑","after":"对证据更加审慎",
        "trigger_quote":ACTION2,"response_quote":EFFECT2,
        "cost_quote":None,"consequence_quote":EFFECT2,
        "open_pressure":"旧账没有证明桥索是谁动过的",
        "choice_shift":"她要求先查证，放弃立即强行渡桥",
    }

def accepted():
    bs=plan()
    first=check_emotional_turn(emotional(prose1(),ACTION1,EFFECT1,None,
                                      "少年",note1()),bs[0])
    second=check_emotional_turn(emotional(prose2(),ACTION2,EFFECT2,EFFECT1,
                                       "女子",note2()),bs[1],accepted=(first,))
    return first,second

class V102CoreTests(unittest.TestCase):
    def test_actual_quote_to_emotion_to_outstanding_cost_and_next_choice(self):
        one,two=accepted()
        self.assertEqual(two["receipt"]["parent_turn_id"],"t01")
        self.assertEqual(one["effect_quote"],EFFECT1)
        self.assertFalse(one["affect_receipt"]["emotion_semantics_verified"])
        self.assertFalse(one["affect_receipt"]["cost_semantics_verified"])
        self.assertIsNotNone(one["affect_receipt"]["cost_anchor"])
        self.assertIsNotNone(two["affect_receipt"]["consequence_anchor"])
        self.assertLess(one["affect_receipt"]["trigger_anchor"]["start"],
                        one["affect_receipt"]["response_anchor"]["start"])
        context=pressure_context((one,two))
        self.assertIn("朋友仍在城中等药",context)
        self.assertIn("旧账没有证明桥索",context)
        self.assertIn("警觉但仍犹豫",context)
        self.assertIn("代价尚未核实",context)
        self.assertIn("不是已确认",context)
        self.assertIn("affect",emotion_turn_instructions((one,)))
        record=export_candidate_emotions((one,two))
        self.assertEqual(record["canon_or_factjournal_writes"],0)
        self.assertFalse(record["actual_cost_semantics_independently_verified"])
        self.assertNotIn(ACTION1,str(record))
        self.assertEqual(record["manifest_sha256"],digest(canonical({
            k:v for k,v in record.items() if k!="manifest_sha256"})))

    def test_no_fake_cost_or_unwritten_consequence(self):
        p=note1();p["cost_quote"]="少年为了救人真的失去全部修为"
        with self.assertRaisesRegex(V102EmotionalCausalityError,"COST_NOT_UNIQUE"):
            check_emotional_turn(emotional(prose1(),ACTION1,EFFECT1,None,
                                         "少年",p),plan()[0])
        p=note1();p["consequence_quote"]="仍然没有发生的后果"
        with self.assertRaisesRegex(V102EmotionalCausalityError,"CONSEQUENCE_NOT_UNIQUE"):
            check_emotional_turn(emotional(prose1(),ACTION1,EFFECT1,None,
                                         "少年",p),plan()[0])

    def test_disordered_trigger_reaction_not_interpreted_as_emotion(self):
        p=note1();p["trigger_quote"]=EFFECT1;p["response_quote"]=ACTION1
        with self.assertRaisesRegex(V102EmotionalCausalityError,"RESPONSE_PRECEDES"):
            check_emotional_turn(emotional(prose1(),ACTION1,EFFECT1,None,
                                          "少年",p),plan()[0])

    def test_no_fake_causal_parent_or_emotion_ghost_actor(self):
        one,_=accepted()
        p=note2();p["actor"]="未登场的神君"
        with self.assertRaisesRegex(V102EmotionalCausalityError,"AFFECT_ACTOR"):
            check_emotional_turn(emotional(prose2(),ACTION2,EFFECT2,EFFECT1,
                                          "女子",p),plan()[1],accepted=(one,))
        p=note2()
        with self.assertRaisesRegex(Exception,"WF96_PARENT_CAUSE"):
            check_emotional_turn(emotional(prose2(),ACTION2,EFFECT2,
                              "未写下的前因","女子",p),
                              plan()[1],accepted=(one,))

    def test_quiet_scene_may_abstain_from_forced_emotion(self):
        quiet={"id":"t01","kind":"quiet","actor":"少年",
               "goal":"少年暂时停下来安静地审视眼前经过",
               "causal_parent":None,"craft_focus":["restraint"]}
        text="雨声落在旧窗沿上。灯火微微摇晃，少年想起刚才没说出口的那句话。"*3
        one=check_emotional_turn(emotional(text,None,None,None,"少年",None),quiet)
        self.assertEqual(one["affect_receipt"]["affect_state"],"NOT_OBSERVED")
        self.assertIn("留白",pressure_context((one,)))
        self.assertFalse(one["receipt"]["literary_causality_independently_verified"])

    def test_tampered_earlier_emotion_is_rejected_and_not_auto_cleared(self):
        one,_=accepted()
        forged=deepcopy(one)
        forged["prose"]+="新写了一段未验证的戏"
        with self.assertRaisesRegex(V102EmotionalCausalityError,"RECEIPT_CORRUPT"):
            pressure_context((forged,))
        forged=deepcopy(one)
        forged["affect_receipt"]["open_pressure"]=None
        with self.assertRaisesRegex(V102EmotionalCausalityError,"RECEIPT_CORRUPT"):
            pressure_context((forged,))
        self.assertIn("朋友仍在城中等药",pressure_context((one,)))


class V102WriterIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.root=Path(self.tmp.name)
        dbpath=self.root/"test.sqlite3"
        snapshot=make_db(dbpath)
        self.db=WriterForgeDB(dbpath)
        self.rt=RuntimeEngine()
        self.rt.enter_write(snapshot)
        self.assist=InvisibleWritingAssist(self.db,self.rt,
            "v102-synthetic-project","synthetic-scene",
            "雨夜少年和女子须付出代价完成送药",model="mock-local-no-billing",
            api_base="http://127.0.0.1:1234/v1")

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_E_mode_replans_with_actual_emotional_change_and_no_extra_calls(self):
        responses=[
            PLAN,
            emotional(prose1(),ACTION1,EFFECT1,None,"少年",note1()),
            raw(proposed()),
            emotional(prose2(),ACTION2,EFFECT2,EFFECT1,"女子",note2()),
        ]
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=responses) as model:
            doc=AutonomousWriting(self.assist).run(
                outline=OUTLINE,chapter_goals=GOALS,
                output_dir=self.root/"emotional-mode",
                draft_mode="emotion_rolling",
                frozen_turn_outlines=(json.dumps(turns(),ensure_ascii=False),))
        self.assertEqual(model.call_count,4)
        self.assertEqual(doc["rolling_replan_model_calls"],1)
        self.assertEqual(doc["canonical_fact_writes"],0)
        self.assertIn("朋友仍在城中等药",model.call_args_list[2].args[0].prompt)
        self.assertIn("affect",model.call_args_list[3].args[0].prompt)
        ch=doc["chapters"][0]
        self.assertFalse(ch["accepted"])
        self.assertEqual(ch["draft_mode"],"emotion_rolling")
        assert Path(ch["candidate"]).read_text("utf8")==prose1()+"\n\n"+prose2()
        receipt=json.loads(Path(ch["v102_emotional_causality"]).read_text("utf8"))
        self.assertEqual(receipt["format"],"wf.writing.emotion-causality-candidate.v102")
        self.assertEqual(len(receipt["turns"]),2)
        self.assertFalse(receipt["actual_cost_semantics_independently_verified"])
        self.assertIsNone(self.db.conn.execute(
            "SELECT 1 FROM accepted_prose").fetchone())
        html=(Path(__file__).parents[1]/"writerforge"/"ui"/"studio.html").read_text("utf8")
        self.assertIn('value="emotion_rolling"',html)
        self.assertIn('value="single"',html)

    def test_fake_affect_stops_no_retry_and_keeps_rejection_evidence(self):
        bogus=note1();bogus["cost_quote"]="突然献出一件并不存在的法器"
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=[
                        PLAN,emotional(prose1(),ACTION1,EFFECT1,None,"少年",bogus)
                   ]) as model:
            with self.assertRaisesRegex(WritingExecutionError,
                                        "WF96_SCENE_TURN_REJECTED_WF102"):
                AutonomousWriting(self.assist).run(
                    outline=OUTLINE,chapter_goals=GOALS,
                    output_dir=self.root/"bad-emotion",
                    draft_mode="emotion_rolling",
                    frozen_turn_outlines=(json.dumps(turns(),ensure_ascii=False),))
        self.assertEqual(model.call_count,2)
        rejected=list((self.root/"bad-emotion").rglob("chapter-001-rejected.json"))
        self.assertEqual(len(rejected),1)
        info=json.loads(rejected[0].read_text("utf8"))
        self.assertEqual(info["previous_valid_turn_count"],0)
        self.assertEqual(info["automatic_repair_attempts"],0)
        self.assertFalse(list((self.root/"bad-emotion").rglob("candidate.txt")))


if __name__=="__main__":
    unittest.main()
