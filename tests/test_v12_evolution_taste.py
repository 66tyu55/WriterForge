import tempfile
import threading
import time
import unittest

from writerforge import (
    WriterForgeDB,
    ReactiveSkillRuntime, CommitLedger,
    LiteraryTasteEngine, PairwiseJudgment, TasteMemory, TasteObservation, TasteSource,
    SkillRegistry, CapabilityContract, SkillStatus,
    FailureEvent, FailureClusterer, CurriculumPlanner,
    SkillBirthGate, SkillSignature,
    PromotionEvidence, PromotionGate,
    CraftEngine, CraftRequest,
    SkillScheduler,
)


class V12EvolutionTasteTests(unittest.TestCase):
    def test_reactive_cache_reuses_unchanged_dependencies(self):
        rt = ReactiveSkillRuntime()
        calls = []
        def fn():
            calls.append(1)
            return {"cards": ["dialogue_as_action"]}
        deps = {"scene_plan": "v3", "character_state": "v9"}
        a = rt.compute(skill_name="craft_router", scope="scene-12", dependencies=deps, fn=fn)
        b = rt.compute(skill_name="craft_router", scope="scene-12", dependencies=deps, fn=fn)
        self.assertFalse(a.cache_hit)
        self.assertTrue(b.cache_hit)
        self.assertEqual(len(calls), 1)

    def test_reactive_invalidation_is_selective(self):
        rt = ReactiveSkillRuntime()
        rt.compute(skill_name="dialogue", scope="s1", dependencies={"character": "v1"}, fn=lambda: 1)
        rt.compute(skill_name="motif", scope="s1", dependencies={"motif_state": "v1"}, fn=lambda: 2)
        result = rt.invalidate({"character"})
        self.assertEqual(len(result.invalidated_keys), 1)
        self.assertEqual(rt.cache_size(), 1)

    def test_singleflight_shares_concurrent_identical_work(self):
        rt = ReactiveSkillRuntime()
        calls = []
        results = []
        def fn():
            calls.append(1)
            time.sleep(0.04)
            return "same"
        def worker():
            results.append(rt.compute(skill_name="taste", scope="x", dependencies={"draft":"v1"}, fn=fn))
        ts = [threading.Thread(target=worker) for _ in range(3)]
        for t in ts: t.start()
        for t in ts: t.join()
        self.assertEqual(len(calls), 1)
        self.assertEqual([r.value for r in results], ["same"] * 3)
        self.assertTrue(any(r.shared_inflight for r in results))

    def test_commit_ledger_is_idempotent(self):
        ledger = CommitLedger()
        effects = []
        a = ledger.commit_once("chapter-1", "body", lambda: effects.append("write"))
        b = ledger.commit_once("chapter-1", "body", lambda: effects.append("write"))
        self.assertTrue(a.committed)
        self.assertFalse(b.committed)
        self.assertEqual(effects, ["write"])

    def test_commit_id_cannot_be_reused_for_different_body(self):
        ledger = CommitLedger()
        ledger.commit_once("x", "a", lambda: None)
        with self.assertRaises(ValueError):
            ledger.commit_once("x", "b", lambda: None)

    def test_taste_judge_swap_stability(self):
        engine = LiteraryTasteEngine()
        def judge(a, b, context):
            # Candidate text contains its id; prefer restrained regardless of position.
            return PairwiseJudgment("A" if "restrained" in a else "B", ("preserves ambiguity",), 0.8)
        d = engine.compare(
            candidate_a_id="restrained", candidate_a="restrained version",
            candidate_b_id="explicit", candidate_b="explicit version",
            context="betrayal scene", judge=judge,
        )
        self.assertTrue(d.stable)
        self.assertEqual(d.preferred_id, "restrained")
        self.assertTrue(engine.can_learn(d))

    def test_taste_flip_is_not_learnable(self):
        engine = LiteraryTasteEngine()
        def biased(a, b, context):
            return PairwiseJudgment("A", ("first-position bias",), 0.9)
        d = engine.compare(
            candidate_a_id="a", candidate_a="A text",
            candidate_b_id="b", candidate_b="B text",
            context="scene", judge=biased,
        )
        self.assertFalse(d.stable)
        self.assertFalse(engine.can_learn(d))
        self.assertIn("JUDGE_UNSTABLE", d.warning)

    def test_taste_memory_persists_conditioned_preference(self):
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            db = WriterForgeDB(f.name)
            memory = TasteMemory(db, project_id="p1")
            memory.add(TasteObservation(
                context="betrayal aftermath",
                preferred_id="B",
                alternative_id="A",
                reasons=("keeps self-deception alive",),
                conditions=("close third person",),
                source=TasteSource.BETA_READER,
                confidence=0.9,
                tags=("restraint", "betrayal"),
            ))
            n = db.conn.execute("SELECT COUNT(*) c FROM taste_observations").fetchone()["c"]
            self.assertEqual(n, 1)
            db.close()

    def test_skill_promotion_marks_only_dependents_for_revalidation(self):
        r = SkillRegistry()
        r.register(CapabilityContract("character_engine", 4, "bounded character decisions"))
        r.register(CapabilityContract("dialogue_craft", 4, "goal-driven dialogue", {"character_engine": 4}))
        r.register(CapabilityContract("prose_rhythm", 4, "functional sentence rhythm"))
        affected = r.promote("character_engine", new_level=5, statement="supports false belief and asymmetric relation view", evidence_id="eval-1")
        self.assertEqual(affected, ["dialogue_craft"])
        self.assertEqual(r.get("dialogue_craft").status, SkillStatus.NEEDS_REVALIDATION)
        self.assertEqual(r.get("prose_rhythm").status, SkillStatus.ACTIVE)

    def test_capability_lag_is_detected(self):
        r = SkillRegistry()
        r.register(CapabilityContract("character_engine", 4, "bounded character decisions"))
        r.register(CapabilityContract("dialogue_craft", 5, "advanced subtext", {"character_engine": 5}))
        lags = r.lagging()
        self.assertEqual(len(lags), 1)
        self.assertEqual(lags[0].dependency, "character_engine")

    def test_failure_cluster_requires_recurrence(self):
        events = [
            FailureEvent("cognitive_motion", "COGNITIVE_LOOP", f"scene-{i}") for i in range(3)
        ] + [FailureEvent("dialogue", "EMPTY_DIALOGUE", "one-off")]
        clusters = FailureClusterer().cluster(events, min_count=3)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].code, "COGNITIVE_LOOP")

    def test_curriculum_contains_heldout_and_transfer(self):
        cluster = FailureClusterer().cluster([
            FailureEvent("dialogue_craft", "SUBTEXT_FAIL", f"x{i}") for i in range(3)
        ])[0]
        scenarios = CurriculumPlanner().design(cluster, count=8)
        splits = {s.split for s in scenarios}
        self.assertEqual(splits, {"train", "heldout", "transfer"})
        self.assertGreater(len({s.relationship for s in scenarios}), 3)

    def test_skill_birth_gate_merges_near_duplicates(self):
        gate = SkillBirthGate()
        existing = {
            "dialogue_action": SkillSignature(
                frozenset({"empty_dialogue", "transcript"}),
                frozenset({"line_as_action", "subtext"}),
                frozenset({"exposition", "no_turn"}),
            )
        }
        candidate = SkillSignature(
            frozenset({"empty_dialogue", "transcript"}),
            frozenset({"line_as_action", "subtext"}),
            frozenset({"exposition", "no_turn"}),
        )
        d = gate.decide(candidate, existing)
        self.assertFalse(d.create_new_skill)
        self.assertEqual(d.merge_target, "dialogue_action")

    def test_promotion_gate_requires_transfer_regression_and_stability(self):
        gate = PromotionGate()
        good = PromotionEvidence(
            capability_statement="Can transfer subtext control across unfamiliar relationships.",
            heldout_success=.88, transfer_success=.81, regression_success=.98,
            judge_stability=.95, repeated_failure_reduction=.40,
            runtime_regression=.08, human_anchor_count=2,
        )
        self.assertTrue(gate.evaluate(good, requires_human_anchor=True).accepted)
        bad = PromotionEvidence(
            capability_statement="Seems better",
            heldout_success=.95, transfer_success=.50, regression_success=.99,
            judge_stability=.95, repeated_failure_reduction=.50,
            runtime_regression=.02, human_anchor_count=2,
        )
        self.assertFalse(gate.evaluate(bad, requires_human_anchor=True).accepted)

    def test_scene_craft_contract_is_stable_until_dependency_changes(self):
        engine = CraftEngine()
        req = CraftRequest(needs=("dialogue",), risks=("empty_dialogue",))
        a = engine.compile_scene_contract(scene_id="s1", request=req, dependencies={"character":"v1", "scene_plan":"v2"})
        b = engine.compile_scene_contract(scene_id="s1", request=req, dependencies={"character":"v1", "scene_plan":"v2"})
        c = engine.compile_scene_contract(scene_id="s1", request=req, dependencies={"character":"v2", "scene_plan":"v2"})
        self.assertEqual(a.contract_id, b.contract_id)
        self.assertNotEqual(a.contract_id, c.contract_id)

    def test_taste_and_evolution_are_never_normal_sentence_drafting(self):
        scheduler = SkillScheduler()
        d = scheduler.drafting_decision("sentence_accepted", budget=20)
        self.assertNotIn("literary_taste_compare", d.selected)
        self.assertNotIn("evolution_curriculum", d.selected)
        d2 = scheduler.boundary_decision("hard_literary_choice", budget=30)
        self.assertIn("literary_taste_compare", d2.selected)
        d3 = scheduler.offline_decision("skill_training", budget=60)
        self.assertIn("evolution_curriculum", d3.selected)


if __name__ == "__main__":
    unittest.main()

class V12StorySenseTests(unittest.TestCase):
    def test_story_sense_selects_one_dominant_problem(self):
        from writerforge import StorySenseRouter, LiterarySignal
        d = StorySenseRouter().diagnose([
            LiterarySignal("FLAT_RHYTHM", "craft", 2, "paragraph", "same cadence"),
            LiterarySignal("NO_CHARACTER_CHOICE", "character", 4, "scene", "protagonist only reacts"),
            LiterarySignal("MINOR_REPEAT", "craft", 1, "line", "word echo"),
        ])
        self.assertEqual(d.primary.code, "NO_CHARACTER_CHOICE")
        self.assertLessEqual(len(d.supporting), 2)

    def test_story_sense_is_not_normal_drafting(self):
        from writerforge import SkillScheduler
        d = SkillScheduler().drafting_decision("sentence_accepted", budget=20)
        self.assertNotIn("story_sense_router", d.selected)
        d2 = SkillScheduler().boundary_decision("literary_diagnosis", budget=20)
        self.assertIn("story_sense_router", d2.selected)

class V12EvolutionEngineControlTests(unittest.TestCase):
    def test_subjective_upgrade_can_self_apply_only_after_gate_and_external_anchor(self):
        from writerforge import EvolutionEngine, SkillRegistry, CapabilityContract, UpgradeCandidate, PromotionEvidence
        reg = SkillRegistry()
        reg.register(CapabilityContract("dialogue_craft", 4, "basic goal-driven dialogue"))
        engine = EvolutionEngine(registry=reg)
        candidate = UpgradeCandidate(
            skill="dialogue_craft",
            new_level=5,
            capability_statement="Transfers subtext across unfamiliar relationships.",
            evidence_id="heldout-2026-09-22",
            evidence=PromotionEvidence(
                capability_statement="Transfers subtext across unfamiliar relationships.",
                heldout_success=.9, transfer_success=.8, regression_success=.99,
                judge_stability=.95, repeated_failure_reduction=.4,
                runtime_regression=.05, human_anchor_count=1,
            ),
            requires_human_anchor=True,
        )
        engine.apply_upgrade(candidate, policy="shadow_only")
        self.assertEqual(reg.get("dialogue_craft").level, 4)
        engine.apply_upgrade(candidate, policy="gated_auto")
        self.assertEqual(reg.get("dialogue_craft").level, 5)
