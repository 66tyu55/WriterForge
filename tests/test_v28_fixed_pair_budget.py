import unittest
from writerforge.reverse_discovery_models import ROLE_MODELS, MAX_REQUESTED_OUTPUT_TOKENS

class TestFixedPair(unittest.TestCase):
    def test_roles(self):
        self.assertEqual(len(set(ROLE_MODELS.values())),2)
        self.assertNotEqual(ROLE_MODELS["writer"],ROLE_MODELS["critic"])
    def test_cap(self):
        self.assertEqual(MAX_REQUESTED_OUTPUT_TOKENS,50000)
