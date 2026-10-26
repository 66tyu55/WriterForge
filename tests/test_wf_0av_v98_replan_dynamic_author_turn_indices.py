"""0.AV RED: DeepSeek's REAL second replan copied wrong structural event ids.

Real provider run 40297313308: original B second-beat prose is retained.
The next author decision chose sensible source-aware action but returned:
{"next_turn":{"id":"t02", ...,"causal_parent":"t03"}}
when the actual next beat was t03 and previous authored t02.
The original V98 prompt always illustrated t02/t01 in JSON, even at t03+.
This test isolates misleading software instructions, not literary grading.
"""
import unittest
from writerforge.v98_rolling_causal_planner import prepare_replan_instructions
from writerforge.v96_causal_turns import check_turn
from test_v96_causal_turns import (
    ACTION2,EFFECT2,EFFECT1,prose2,response,
)
from test_v98_rolling_causal_planner import first,BASE_BEATS

class DynamicWriterOwnedRealReplanIndices(unittest.TestCase):
    def test_next_beat_sample_uses_actual_source_beat_ids_and_kind(self):
        first_turn=first()
        second_beat=BASE_BEATS[1]
        second=check_turn(response(prose2(),ACTION2,EFFECT2,EFFECT1),
                          second_beat,mode="causal_guard",
                          accepted=(first_turn,))
        seed={"id":"t03","kind":"interiority","actor":"女子",
              "goal":"女子面对尚未确认的桥索责任先辨清自己已知与怀疑",
              "causal_parent":"t02","craft_focus":["interiority"]}
        prompt=prepare_replan_instructions(
            accepted=(first_turn,second),
            seed_next_beat=seed,
            allowed_actor_names=("少年","女子"))
        self.assertIn('"next_turn":{"id":"t03"',prompt)
        self.assertIn('"causal_parent":"t02"',prompt)
        self.assertNotIn('"next_turn":{"id":"t02"',prompt)
        self.assertIn('"kind":"interiority"',prompt)
        self.assertIn("下一事件编号必须为 t03",prompt)
        self.assertIn("仅用于来源顺序定位",prompt)

    def test_earlier_turn_example_was_initially_correct_but_must_stay_bound(self):
        initial=first()
        prompt=prepare_replan_instructions(
            accepted=(initial,),seed_next_beat=BASE_BEATS[1],
            allowed_actor_names=("少年","女子"))
        self.assertIn('"next_turn":{"id":"t02"',prompt)
        self.assertIn('"causal_parent":"t01"',prompt)

if __name__=="__main__":
    unittest.main()
