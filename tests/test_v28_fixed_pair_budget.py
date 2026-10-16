import unittest
from writerforge.reverse_discovery_models import ROLE_MODELS, MAX_REQUESTED_OUTPUT_TOKENS, FIXED_MODEL_CONTEXT_TOKENS, DISCOVERY_GATEWAY_1M_LOAD_VERIFIED, DiscoveryCallBudget, DiscoveryError

class TestFixedPair(unittest.TestCase):
    def test_roles(self):
        self.assertEqual(len(set(ROLE_MODELS.values())),2)
        self.assertEqual(ROLE_MODELS["planner"],"deepseek-v4-flash-0731")
        self.assertEqual(ROLE_MODELS["critic"],"deepseek-v4-flash-0731")
        self.assertEqual(ROLE_MODELS["writer"],"glm-5.3")
        self.assertNotEqual(ROLE_MODELS["writer"],ROLE_MODELS["critic"])
    def test_cap(self):
        self.assertEqual(MAX_REQUESTED_OUTPUT_TOKENS,50000)

    def test_model_documentation_not_gateway_stress_proof(self):
        self.assertFalse(DISCOVERY_GATEWAY_1M_LOAD_VERIFIED)
        for model in set(ROLE_MODELS.values()):
            self.assertGreaterEqual(FIXED_MODEL_CONTEXT_TOKENS[model],1_000_000)

    def test_aggregate_limit_is_50000(self):
        budget=DiscoveryCallBudget(max_calls=7,max_reserved_output_tokens=50000)
        budget.reserve(1000,49000,role="writer")
        with self.assertRaises(DiscoveryError):
            budget.reserve(1000,1001,role="critic")
        self.assertEqual(budget.calls,1)
