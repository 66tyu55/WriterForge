"""V74 WF LEARN provider choice remains DeepSeek Flash even with old code."""
from __future__ import annotations
import unittest

from writerforge.deepseek_flash_model import DeepSeekFlashError, FlashBudget
from writerforge.wf_learn_model_registry import (
    WF_LEARN_MODEL_ID, WF_LEARN_PROVIDER, WF_LEGACY_DISCOVERY_USED,
    FIRST_READ_R2_JOURNAL_IMPLEMENTED,
    model_status, new_wf_learn_model, require_sequential_training_ready,
)

class WFModelChoiceTests(unittest.TestCase):
    def test_wf_learn_registry_only_official_deepseek_flash(self):
        result=model_status({})
        self.assertEqual(WF_LEARN_MODEL_ID,"deepseek-flash")
        self.assertEqual(WF_LEARN_PROVIDER,"deepseek")
        self.assertFalse(WF_LEGACY_DISCOVERY_USED)
        self.assertFalse(FIRST_READ_R2_JOURNAL_IMPLEMENTED)
        self.assertFalse(result["WF_PassA_PassB_execution_unlocked"])
        self.assertFalse(result["first_read_immutable_r2_journal_deployed"])
        self.assertEqual(result["key_variable_name"],"DEEPSEEK_API_KEY")

    def test_key_presence_does_not_unlock_full_original_training(self):
        status=model_status({"DEEPSEEK_API_KEY":"synthetic-secret-key"})
        self.assertTrue(status["key_present"])
        self.assertFalse(status["auto_paid_training_enabled"])
        self.assertFalse(status["WF_PassA_PassB_execution_unlocked"])
        with self.assertRaisesRegex(DeepSeekFlashError,"JOURNAL_MISSING"):
            require_sequential_training_ready()

    def test_legacy_discovery_not_used_as_fallback(self):
        status=model_status({"DISCOVERY_API_KEY":"old-key"})
        self.assertFalse(status["key_present"])
        with self.assertRaisesRegex(DeepSeekFlashError,
                                    "API_KEY_NOT_CONFIGURED"):
            new_wf_learn_model(api_key="")

    def test_factory_returns_one_bounded_shared_flash_client(self):
        fake=lambda r: b'{"choices":[{"finish_reason":"stop","message":{"content":"{\\"ok\\":true}"}}]}'
        m=new_wf_learn_model(
            api_key="fake-official-ds-key-test-value-123",
            budget=FlashBudget(max_calls=1,max_reserved_output_tokens=200),
            transport=fake)
        self.assertEqual(m.provider,"deepseek")
        self.assertEqual(m.name,"deepseek-flash")
        result=m.ask_json(
            role="first_read",system='仅返回JSON对象 {"ok":true}。',
            user="仅为合成内容",max_tokens=100)
        self.assertEqual(result,{"ok":True})
        self.assertEqual(m.budget.calls_reserved,1)

if __name__=="__main__":
    unittest.main()
