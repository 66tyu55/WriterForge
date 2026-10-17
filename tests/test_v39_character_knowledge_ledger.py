"""Synthetic tests for future V39 precommit and causal evidence gates."""
import unittest
from writerforge.v39_character_knowledge_ledger import (
    validate_prewrite, verify_postwrite, KnowledgeLedgerError,
)

OBS = "女药童发现药包边缘多了一枚磨旧的青铜扣。"
ACT = "她因此暂缓交药并转身去找上游的采药人。"
REV = "采药人承认那枚青铜扣是旧封条的标记。"
FILL = "山镇上落叶满地，店主又翻了一遍旧账册。"


def ledger():
    return {"clues": [{
        "clue_id": "C1", "actor_id": "女药童",
        "clue_identity": "药包青铜扣对应旧封条",
        "knowledge_before": "此前只知道药包由店铺出售",
        "expected_observation": "注意到药包旧铜扣与新封条不同",
        "belief_update": "怀疑药包来路与商贩说法不符",
        "action_condition": "无法解释封条差异便暂缓交药",
        "planned_action": "带着药包去询问上游采药人",
        "planned_reveal": "采药人告知旧扣的真实用途",
        "alternative_explanation": "旧铜扣也可能只是装饰，不能直接断定为假药",
    }]}


def draft():
    return FILL * 12 + OBS + FILL * 3 + ACT + FILL * 3 + REV + FILL * 3


def evidence():
    return [{
        "clue_id": "C1", "application_status": "CLAIMED_APPLIED",
        "observation_quote": OBS, "action_quote": ACT,
        "reveal_quote": REV,
        "knowledge_as_written": "药童看到铜扣前并不知道封条来历，看到后才有新的怀疑。",
        "why_action_follows": "怀疑货源有问题，所以她决定暂缓交药并寻找采药人。",
        "unresolved_semantic_risk": "行为是否足够自然仍需读者独立判断，文字先后本身不说明原因。",
    }]


class CausalLedgerTests(unittest.TestCase):
    def test_verified_citations_remain_non_semantic(self):
        source = ledger()
        key = validate_prewrite(source)["prewrite_ledger_sha256"]
        actual = verify_postwrite(frozen_ledger=source, locked_sha256=key,
                                  draft=draft(), evidence=evidence())
        self.assertEqual(actual["textual_chain_claimed_count"], 1)
        self.assertFalse(actual["independent_literary_semantic_validation"])
        self.assertFalse(actual["checks"][0][
            "actual_action_motivated_by_clue_independently_verified"])
        self.assertNotIn(OBS, repr(actual))

    def test_prewrite_id_collision_rejected(self):
        d = ledger()
        d["clues"].append(dict(d["clues"][0]))
        with self.assertRaisesRegex(KnowledgeLedgerError,
                                    "ID_INVALID_OR_DUPLICATE"):
            validate_prewrite(d)

    def test_changed_prewrite_rejected(self):
        d = ledger()
        key = validate_prewrite(d)["prewrite_ledger_sha256"]
        d["clues"][0]["planned_action"] += "并观察封条"
        with self.assertRaisesRegex(KnowledgeLedgerError,
                                    "SHA_CHANGED"):
            verify_postwrite(frozen_ledger=d, locked_sha256=key,
                             draft=draft(), evidence=evidence())

    def test_causal_order_reversed_rejected(self):
        d = ledger()
        key = validate_prewrite(d)["prewrite_ledger_sha256"]
        reverse = FILL * 12 + ACT + FILL * 3 + OBS + FILL * 3 + REV
        with self.assertRaisesRegex(KnowledgeLedgerError,
                                    "KNOWLEDGE_ACTION_REVEAL_ORDER_INVALID"):
            verify_postwrite(frozen_ledger=d, locked_sha256=key,
                             draft=reverse, evidence=evidence())

    def test_uncertain_must_not_attach_as_fake_success(self):
        d = ledger()
        key = validate_prewrite(d)["prewrite_ledger_sha256"]
        items = evidence()
        items[0]["application_status"] = "UNCERTAIN"
        with self.assertRaisesRegex(KnowledgeLedgerError,
                                    "UNCERTAIN_MUST_NOT_FORGE_ANCHORS"):
            verify_postwrite(frozen_ledger=d, locked_sha256=key,
                             draft=draft(), evidence=items)
        for name in ("observation_quote", "action_quote", "reveal_quote"):
            items[0][name] = None
        ok = verify_postwrite(frozen_ledger=d, locked_sha256=key,
                              draft=draft(), evidence=items)
        self.assertEqual(ok["textual_chain_claimed_count"], 0)

    def test_fake_prose_quote_rejected(self):
        d = ledger()
        key = validate_prewrite(d)["prewrite_ledger_sha256"]
        items = evidence()
        items[0]["action_quote"] = "那天她立刻就把陌生药商抓到了大堂之上。"
        with self.assertRaisesRegex(KnowledgeLedgerError,
                                    "QUOTE_MISSING_OR_REPEATED"):
            verify_postwrite(frozen_ledger=d, locked_sha256=key,
                             draft=draft(), evidence=items)


if __name__ == "__main__":
    unittest.main()
