"""V43 genuine production entry point experiments, not literary quality scores.

Use existing WF OriginalStudy, real published SQLite Xuehai and
VerifiedWritingFlow.prepare/save_candidate; model requests are NEVER sent.
No assertion that the synthetic plan is literary truth or independently
reviewed. The counterfactual measures execution behavior only.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
import json
import unittest

from writerforge import (
    WriterForgeDB, RuntimeEngine, OriginalStudy,
    VerifiedWritingFlow, WritingExecutionError, save_candidate,
)
from writerforge.experience_executor import ExperienceExecutor, ExperiencePolicyError, RULE_ID

FIXTURE = Path(__file__).parent / "fixtures" / "xiyouji_chapter_001_original_zh.txt"

STORY = (
    "青石桥边，女药童阿梨发现封蜡上的一个破口。"
    "她本来以为背药箱的人没有动过封口。"
    "旧封印不见了，箱子却比出门时轻了许多。"
    "她想起昨夜装箱时亲手留下过两道印记。"
    "因此她暂缓交付，转身去问守门的老伯。"
    "这一迟疑让她错过了当天唯一一趟山车。"
    "老伯查看后指出，破口是搬运途中被车架割开的。"
    "她仍不能断定药包是否完好，只得重新检查。"
)


def plan():
    return {
        "clue_id": "seal-01",
        "actor_id": "阿梨",
        "knowledge_before": "她亲手留下了两道封印但尚未核实封口现状",
        "unknown_before": "她不知道箱子重量为什么减轻也不清楚何时破损",
        "observation": "封蜡上有新出现的破口而且箱子重量减少",
        "decision": "先暂停交付并去询问当天负责守门的老伯",
        "decision_depends_on_clue": "破口和重量变化使她无法确认药箱未被动过",
        "later_reveal_target": "确认破口究竟来自运输刮碰还是有人打开",
        "alternative_explanation": "可能是车架割伤也可能是第三者碰了封口",
        "uncertainty": "只拥有不完整线索，目前无法断言具体的责任人",
    }


QUOTES = {
    "observation": "封蜡上的一个破口",
    "actor_decision": "她暂缓交付，转身去问守门的老伯",
    "causal_consequence": "这一迟疑让她错过了当天唯一一趟山车",
    "later_reveal": "破口是搬运途中被车架割开的",
}


class ExperienceActualWritingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.db = WriterForgeDB(Path(self.tmp.name) / "wf.sqlite")
        self.runtime = RuntimeEngine()
        self.runtime.enter_learn()
        OriginalStudy(self.db, self.runtime).ingest(
            FIXTURE.read_text(encoding="utf-8"),
            work_id="v43-xiyouji-real-fixture", require_hundred=False)
        sid = self.db.conn.execute(
            "SELECT MAX(id) AS id FROM snapshots WHERE status='published'"
        ).fetchone()["id"]
        self.runtime.exit()
        self.runtime.enter_write(int(sid))
        self.flow = VerifiedWritingFlow(self.db, self.runtime, "v43-study")

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def setup_rule(self):
        engine = ExperienceExecutor(self.db.conn, "v43-study")
        engine.install_v38_candidate(explicit_experiment_opt_in=True)
        return engine

    def prep(self, scene, *, enabled=False, intent=None, concerns=("setup_payoff",)):
        return self.flow.prepare(
            scene, "让角色依据有限信息选择，展示可回查线索与代价",
            concerns=concerns,
            experience_experiment=enabled, causal_plan=intent)

    def test_unmodified_baseline_runs_without_experimental_rule(self):
        packet = self.prep("control-01")
        self.assertIsNone(packet.strategy_receipt)
        self.assertIn("原著学习档案", packet.prompt)
        self.assertIsNone(packet.manifest()["experience_execution"])
        evidence = save_candidate(packet, STORY, "no-call-fixture",
                                  Path(self.tmp.name) / "output")
        self.assertFalse(json.loads(Path(evidence["manifest"]).read_text())["accepted"])

    def test_new_rule_changes_executable_gate_not_only_prompt_text(self):
        self.setup_rule()
        base = self.prep("control-02")  # opt-in flag off: still works
        self.assertIsNone(base.strategy_receipt)
        with self.assertRaisesRegex(
                WritingExecutionError, "EXPERIENCE_PREWRITE_KNOWLEDGE"):
            self.prep("experimental-02", enabled=True)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM wf_experience_prewrite").fetchone()[0], 0)
        experimental = self.prep("experimental-02", enabled=True, intent=plan())
        r = experimental.strategy_receipt
        self.assertEqual(r["status"], "CAUSAL_PREFLIGHT_VERIFIED_STRUCTURALLY")
        self.assertEqual(r["postwrite_evidence_required"],
                         ["observation","actor_decision",
                          "causal_consequence","later_reveal"])
        self.assertEqual(len(r["frozen_prewrite_sha256"]), 64)
        self.assertIsNotNone(r["policy_sha256"])
        # This is a *runtime control*, not added prose advice.
        self.assertNotIn("seal-01", experimental.prompt)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM wf_experience_prewrite").fetchone()[0], 1)

    def test_cannot_save_without_afterdraft_evidence(self):
        self.setup_rule()
        packet = self.prep("proof-required", enabled=True, intent=plan())
        with self.assertRaisesRegex(
                WritingExecutionError,"EXPERIENCE_POSTWRITE_FOUR_CAUSAL_ANCHORS"):
            save_candidate(packet,STORY,"synthetic-no-model",
                           Path(self.tmp.name)/"candidate")
        self.assertFalse((Path(self.tmp.name)/"candidate").exists())
        saved = save_candidate(packet, STORY, "synthetic-no-model",
                               Path(self.tmp.name) / "candidate",
                               postwrite_evidence=QUOTES)
        manifest = json.loads(Path(saved["manifest"]).read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["experience_postwrite_anchors"]),set(QUOTES))
        self.assertFalse(manifest["experience_semantic_correctness_verified"])
        self.assertFalse(manifest["accepted"])

    def test_fabricated_or_out_of_order_prose_cannot_pass(self):
        self.setup_rule()
        packet = self.prep("prove-false", enabled=True, intent=plan())
        fake = {**QUOTES,"later_reveal":"他突然得知一件正文根本没有写过的事情"}
        with self.assertRaisesRegex(
                WritingExecutionError,"EXPERIENCE_POSTWRITE_QUOTE_NOT_UNIQUE"):
            save_candidate(packet,STORY,"no-call",Path(self.tmp.name)/"out",
                           postwrite_evidence=fake)
        backwards = {**QUOTES,
                     "actor_decision":QUOTES["later_reveal"],
                     "later_reveal":QUOTES["actor_decision"]}
        with self.assertRaisesRegex(
                WritingExecutionError,"EXPERIENCE_POSTWRITE_CAUSAL_ORDER"):
            save_candidate(packet,STORY,"no-call",Path(self.tmp.name)/"out",
                           postwrite_evidence=backwards)

    def test_frozen_prewrite_rejects_retroactive_replacement(self):
        self.setup_rule()
        self.prep("locked",enabled=True,intent=plan())
        changed={**plan(),"decision":"不问守门人而直接奔回药铺寻找封条"}
        with self.assertRaisesRegex(
                WritingExecutionError,"EXPERIENCE_FROZEN_PREWRITE"):
            self.prep("locked",enabled=True,intent=changed)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM wf_experience_prewrite").fetchone()[0],1)

    def test_unrelated_scene_does_not_activate_l2(self):
        self.setup_rule()
        packet=self.prep("dialogue-only",enabled=True,concerns=("dialogue",))
        self.assertEqual(packet.strategy_receipt["status"],"NOT_APPLICABLE")
        self.assertEqual(packet.strategy_receipt["postwrite_evidence_required"],[])
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM wf_experience_prewrite").fetchone()[0],0)

    def test_policy_rollback_after_two_distinct_attested_harms(self):
        engine=self.setup_rule()
        for i in range(2):
            scene=f"fail-{i}"
            self.prep(scene,enabled=True,intent=plan())
            report=sha256(f"private-review-{i}".encode()).hexdigest()
            status=engine.record_outcome(
                scene_id=scene,outcome="HARMED",report_sha256=report,
                reviewer_is_independent=True)
            self.assertFalse(status["automatic_promotion"])
        self.assertEqual(status["observed_harmed_count"],2)
        self.assertEqual(status["active_status"],"PAUSED_DUE_TO_HARM")
        reset=self.prep("rollback",enabled=True)
        self.assertEqual(reset.strategy_receipt["status"],"POLICY_ROLLED_BACK")
        self.assertEqual(reset.strategy_receipt["postwrite_evidence_required"],[])
        self.assertNotIn("EXPERIENCE",reset.prompt)

    def test_self_report_cannot_pause_or_promote(self):
        engine=self.setup_rule()
        self.prep("self-report",enabled=True,intent=plan())
        with self.assertRaisesRegex(
                ExperiencePolicyError,"EXPERIENCE_SELF_REVIEW"):
            engine.record_outcome(
                scene_id="self-report",outcome="HELPED",
                report_sha256="a"*64,reviewer_is_independent=False)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM wf_experience_feedback").fetchone()[0],0)

    def test_project_isolation_and_no_auto_evolution(self):
        self.setup_rule()
        second=ExperienceExecutor(self.db.conn,"another-project")
        decision=second.before_write(
            scene_id="fresh",concerns=("setup_payoff",),causal_plan=None)
        self.assertEqual(decision.status,"NO_EXPERIMENTAL_POLICY")
        self.assertIsNone(decision.policy_sha256)
        active=self.db.conn.execute(
            "SELECT status FROM wf_experience_policies WHERE project='v43-study'"
        ).fetchone()[0]
        self.assertEqual(active,"EXPERIMENTAL_ACTIVE")


if __name__ == "__main__":
    unittest.main()
