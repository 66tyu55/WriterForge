"""V115 dynamic source entity discovery, candidate only; no model."""
import unittest
from writerforge.v115_dynamic_entity_candidates import discover_candidates,compact_entity_context
from writerforge.v114_external_story_state import external_temporal_step,temporal_prompt
class DynamicEntities(unittest.TestCase):
    def test_specific_fruit_and_arm_mentioned_without_claiming_owner(self):
        text="沈砚的右臂被击伤，血流不止。唐蜃拿出一枚火髓果，神色犹疑。"
        r=discover_candidates(text)
        terms={v["term"] for v in r["mentions"]}
        self.assertIn("火髓果",terms)
        self.assertIn("右臂",terms)
        self.assertEqual(r["authoritative_entity_states_created"],0)
        self.assertFalse(r["literary_semantics_verified"])
        self.assertTrue(all(x["holder"]=="UNKNOWN" for x in r["mentions"]))
        self.assertIn("火髓果",compact_entity_context(r))
    def test_real_external_reducer_preserves_unknown_holder_but_passes_names(self):
        text="沈砚右臂疼得发麻，眼前的火髓果散出赤红灵光。"
        r=external_temporal_step(text,cast=("沈砚",))
        self.assertIn("火髓果",temporal_prompt(r))
        self.assertIn("右臂",temporal_prompt(r))
        self.assertNotIn("火髓果",str(r["reducer_result"]["candidate_state"]))
        self.assertEqual(r["canon_writes"],0)
    def test_dream_mention_not_promoted(self):
        r=discover_candidates("梦中他看见一枚火髓果，右臂仍然疼。")
        self.assertFalse(r["literary_semantics_verified"])
        self.assertEqual(r["canon_writes"],0)
if __name__=="__main__":unittest.main()
