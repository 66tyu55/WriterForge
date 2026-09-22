import unittest

from writerforge import (
    EmbodiedSceneResolver, SceneEnvironment, SceneEntity, SceneAction,
    PerceptionContext, PerceptualChannel,
)


class V14EmbodiedSceneTests(unittest.TestCase):
    def setUp(self):
        self.r = EmbodiedSceneResolver()

    def test_walking_sound_is_derived_from_action_and_surface(self):
        result = self.r.resolve(
            environment=SceneEnvironment(surface="wood"),
            entities=(SceneEntity("a", "human"),),
            actions=(SceneAction("a", "walk"),),
        )
        semantics = {c.semantic for c in result.all_cues}
        self.assertIn("wooden_footfall", semantics)

    def test_boar_feeding_derives_snuffling_and_ground_disturbance(self):
        result = self.r.resolve(
            environment=SceneEnvironment(surface="forest_floor"),
            entities=(SceneEntity("boar1", "boar", traits=("snout_forager",)),),
            actions=(SceneAction("boar1", "forage", tags=("ground_feed",)),),
        )
        got = {(c.channel, c.semantic) for c in result.all_cues}
        self.assertIn((PerceptualChannel.SOUND, "boar_snuffling_while_feeding"), got)
        self.assertIn((PerceptualChannel.VISUAL, "ground_disturbance_from_rooting"), got)

    def test_cold_is_scene_state_not_a_decorative_sensory_request(self):
        result = self.r.resolve(environment=SceneEnvironment(temperature_c=-3))
        semantics = {c.semantic for c in result.all_cues}
        self.assertIn("cold_air_exposure", semantics)
        self.assertIn("exhalation_condensation_possible", semantics)

    def test_emotion_alone_does_not_emit_stock_body_reaction(self):
        result = self.r.resolve(
            environment=SceneEnvironment(),
            entities=(SceneEntity("x", "human", state_tags=("anger",)),),
        )
        self.assertEqual(result.all_cues, ())

    def test_emotion_can_manifest_through_established_character_tendency(self):
        result = self.r.resolve(
            environment=SceneEnvironment(),
            entities=(SceneEntity(
                "x", "human", state_tags=("anger",),
                embodiment_hints=("anger:clipped_speech", "fear:checks_exits"),
            ),),
        )
        semantics = {c.semantic for c in result.all_cues}
        self.assertIn("character_specific_expression:clipped_speech", semantics)
        self.assertNotIn("character_specific_expression:checks_exits", semantics)

    def test_environment_interaction_can_create_ambient_sound(self):
        result = self.r.resolve(environment=SceneEnvironment(tags=("rain", "tile_roof")))
        self.assertIn("rain_striking_tile", {c.semantic for c in result.all_cues})

    def test_pov_attention_selects_relevant_few_without_sense_quota(self):
        result = self.r.resolve(
            environment=SceneEnvironment(temperature_c=1, surface="gravel", tags=("wind", "dry_leaves")),
            entities=(SceneEntity("p", "human"),),
            actions=(SceneAction("p", "walk"),),
            perception=PerceptionContext("p", attention_tags=("footfall", "movement"), max_cues=1),
        )
        self.assertEqual(len(result.selected_cues), 1)
        self.assertEqual(result.selected_cues[0].semantic, "gravel_shift_under_foot")

    def test_same_scene_state_has_same_dependency_fingerprint(self):
        kwargs = dict(
            environment=SceneEnvironment(temperature_c=4, surface="stone"),
            entities=(SceneEntity("p", "human"),),
            actions=(SceneAction("p", "step"),),
            perception=PerceptionContext("p", max_cues=2),
        )
        self.assertEqual(self.r.resolve(**kwargs).dependency_fingerprint, self.r.resolve(**kwargs).dependency_fingerprint)


if __name__ == "__main__":
    unittest.main()
