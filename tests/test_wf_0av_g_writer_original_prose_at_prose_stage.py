"""0.AV true DeepSeek B++ RED: t04 planned ahead, but t05 prose recut old t01 signal.

The actual t05 prose request #40344654185 (prompt SHA fd7080de...) supplied
t04 prose and a frozen chapter decision that originally proposed signal cutting.
It did NOT supply the literal t01 '他扳了下去' and source SHA. The author
wrote a similar signal cut again; do not force an author rewrite, do not judge.
Fix the EXISTING opt-in G+V98 input delivery rather than adding literary gates.
"""
import unittest
from copy import deepcopy

from writerforge.v96_causal_turns import (
    check_turn,review_only_model_turn,digest,
)
from writerforge.v98_rolling_causal_planner import (
    author_signed_prior_prose_for_writer,V98RollingPlanError,
)
from writerforge.writing_assist import g_writer_active_plan_view
from test_v96_causal_turns import (
    ACTION1,ACTION2,EFFECT1,EFFECT2,plan,prose1,prose2,response,
)


def old_three():
    one,two=plan()
    a=check_turn(response(prose1(),ACTION1,EFFECT1),one,mode="causal_guard")
    b=check_turn(response(prose2(),ACTION2,EFFECT2,EFFECT1),
                 two,mode="causal_guard",accepted=(a,))
    three_beat={
        "id":"t03","kind":"dialogue","actor":"少年",
        "goal":"听完渡河争论后仍不能确定谁已走过木桥",
        "causal_parent":"t02","craft_focus":["dialogue"],
    }
    prose=(
        "两人站在驿站门边听着河风。"
        "女子用手遮住旧账本，少年也没有马上去找船工。"
        "一阵敲击声从下游传来，他们听见两下便再没有回音。"
        "既然眼前没有证实谁走过桥，两个人都不把声音当作确凿的信号，"
        "更不能说对方已经答应交还账册。")
    c=review_only_model_turn(response(prose,ACTION1,None,EFFECT2),
             three_beat,failure_code="WF96_PARTIAL_ACTION_EFFECT_NOT_ALLOWED",
             accepted=(a,b))
    return a,b,c


class OriginalPriorProseInWriterDelivery(unittest.TestCase):
    def test_first_actually_written_action_survives_source_limited_writer_stage(self):
        a,b,c=old_three()
        context=author_signed_prior_prose_for_writer((a,b,c))
        self.assertIn(ACTION1,context)
        self.assertIn(ACTION2,context)
        self.assertIn(digest(a["prose"].encode("utf8")),context)
        self.assertIn(digest(b["prose"].encode("utf8")),context)
        self.assertLess(len(context),2001)
        self.assertNotIn("已证实因果",context)
        self.assertNotIn("必然导致",context)

    def test_full_original_is_author_history_not_host_plan_reconstruction(self):
        a,b,c=old_three()
        four=deepcopy(c)
        four["prose"]+="外面有人正在问谁先往回走。"
        # Altered prose with unchanged SHA MUST fail even if text is plausible.
        with self.assertRaises(V98RollingPlanError):
            author_signed_prior_prose_for_writer((a,b,c,four))

    def test_full_static_chapter_decision_not_replayed_as_new_turn_after_v98_choice(self):
        original={
            "objective":"真正的争执尚未解决",
            "conflict":"两人的信息依旧不对称",
            "decision":"守桥人早已经扳下开关",
            "outcome":"门前第一处已被切断",
            "pov":"少年有限第三人称",
            "needs":["dialogue","decision"],
            "chapter_goal":"在真实已写的后文继续推进",
            "literary_quality_verified":False,
        }
        old=deepcopy(original)
        view=g_writer_active_plan_view(original)
        self.assertNotIn("decision",view)
        self.assertNotIn("outcome",view)
        for key in ("objective","conflict","pov","needs","chapter_goal",
                    "literary_quality_verified"):
            self.assertEqual(view[key],original[key])
        self.assertEqual(original,old)
        self.assertNotIn("守桥人早已经扳下开关",str(view))


if __name__=="__main__":
    unittest.main()
