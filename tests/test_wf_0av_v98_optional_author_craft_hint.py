"""0.AV RED from immutable DeepSeek provider plan #11 (run 40321793262).

Raw provider SHA ddbb093fb6b1006d9d82169f6233378ecf68da667eea8eae6c6941a268335711.
The genuinely authored t03 id, t02 source parent, goal, actor, basis,
pressure and unresolved question all survived. It used OPTIONAL craft_focus
['dialogue','interiority','decision']; the old V98->V96 plan parser rejected
the entire new story because craft tags must be <=2 and 'decision' is not
a registered craft label. Source wire is archived; these tests are offline
analogues only and do not replace any paid prose or model decision.
"""
import json
import unittest
from test_v98_rolling_causal_planner import (
    first, BASE_BEATS, proposed, raw,
)
from writerforge.v98_rolling_causal_planner import (
    validate_replan, V98RollingPlanError,
)

class V98OptionalCraftNotStoryTruth(unittest.TestCase):
    def test_extra_and_unknown_optional_tags_do_not_destroy_new_writer_story(self):
        original=first()
        p=proposed()
        p["next_turn"]["craft_focus"]=["dialogue","interiority","decision"]
        author_goal=p["next_turn"]["goal"]
        next_beat,receipt=validate_replan(
            raw(p),accepted=(original,),accepted_beats=(BASE_BEATS[0],),
            seed_next_beat=BASE_BEATS[1],
            allowed_actor_names=("少年","女子"))
        self.assertEqual(next_beat["id"],p["next_turn"]["id"])
        self.assertEqual(next_beat["actor"],p["next_turn"]["actor"])
        self.assertEqual(next_beat["goal"],author_goal)
        self.assertEqual(next_beat["causal_parent"],p["next_turn"]["causal_parent"])
        self.assertEqual(next_beat["craft_focus"],["dialogue","interiority"])
        self.assertTrue(receipt["only_optional_model_craft_adjusted"])
        self.assertEqual(receipt["removed_optional_craft_tags"],["decision"])
        self.assertTrue(receipt["original_model_answer_must_be_preserved"])
        self.assertFalse(receipt["source_parent_causal_relation_verified"])
        self.assertFalse(receipt["narrative_semantics_independently_verified"])
        self.assertEqual(receipt["canon_or_factjournal_writes"],0)

    def test_three_genuine_craft_modes_preserve_first_two_and_source_replay(self):
        p=proposed()
        p["next_turn"]["craft_focus"]=["dialogue","interiority","detail"]
        beat,receipt=validate_replan(raw(p),
            accepted=(first(),),accepted_beats=(BASE_BEATS[0],),
            seed_next_beat=BASE_BEATS[1],
            allowed_actor_names=("少年","女子"))
        self.assertEqual(beat["craft_focus"],["dialogue","interiority"])
        self.assertEqual(receipt["removed_optional_craft_tags"],["detail"])

    def test_existing_valid_plan_is_byte_neutral(self):
        p=proposed()
        beat,receipt=validate_replan(raw(p),
            accepted=(first(),),accepted_beats=(BASE_BEATS[0],),
            seed_next_beat=BASE_BEATS[1],
            allowed_actor_names=("少年","女子"))
        self.assertEqual(beat["craft_focus"],p["next_turn"]["craft_focus"])
        self.assertFalse(receipt["only_optional_model_craft_adjusted"])

    def test_non_optional_story_identity_or_forged_source_stays_red(self):
        p=proposed()
        p["next_turn"]["craft_focus"]=["dialogue","interiority","decision"]
        p["next_turn"]["id"]="t99"
        with self.assertRaises(V98RollingPlanError):
            validate_replan(raw(p),accepted=(first(),),
                accepted_beats=(BASE_BEATS[0],),
                seed_next_beat=BASE_BEATS[1],
                allowed_actor_names=("少年","女子"))
        p=proposed(basis="作者虚构了前文并不存在的医院水压报告")
        p["next_turn"]["craft_focus"]=["dialogue","interiority","decision"]
        with self.assertRaises(V98RollingPlanError):
            validate_replan(raw(p),accepted=(first(),),
                accepted_beats=(BASE_BEATS[0],),
                seed_next_beat=BASE_BEATS[1],
                allowed_actor_names=("少年","女子"))

    def test_unbounded_optional_tags_still_rejected(self):
        p=proposed()
        p["next_turn"]["craft_focus"]=["detail"]*60
        with self.assertRaises(V98RollingPlanError):
            validate_replan(raw(p),accepted=(first(),),
                accepted_beats=(BASE_BEATS[0],),
                seed_next_beat=BASE_BEATS[1],
                allowed_actor_names=("少年","女子"))

if __name__=="__main__":
    unittest.main()
