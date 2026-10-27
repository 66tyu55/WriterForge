"""WF 0.BK fail-first: bare vs REAL WF G author vs G plus SHADOW.

Zero model calls: fixture only. The original AutonomousWriting.run is invoked,
not replaced by a static prompt that merely names WF. V98 G rolling and the
sole NarrativeCore are opt-in. V119 remains preserved but not forced here.
"""
from __future__ import annotations
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from writerforge import WriterForgeDB, RuntimeEngine
from writerforge.writing_assist import InvisibleWritingAssist
from writerforge.scheduler import OptionalHostResourceLease, OptionalHostResourceUnavailable
from experiments.wf_0bk_actual_writer_three_arm_host_gate import (
    three_arm_preflight, execute_three_arm_trial, HostStudyCompletion, FROZEN_ARMS
)
from test_v26_invisible_writer import make_db, PLAN
from test_v96_causal_turns import (
    ACTION1, ACTION2, EFFECT1, EFFECT2, prose1, prose2, response, turns
)

OUTLINE="两位同行者因石桥状况改变渡河决定，逐步发现对方不曾掌握同样事实。"
TASK="先处理真实桥边动作，再处理旧账册所记录的未知往事，保留不同立场。"
SOURCE=("守桥人留下告示，少年仍有疑虑。","女子准备查阅账册，但并不知道谁改动过桥索。")

def sha(s):
    return sha256(s.encode("utf8")).hexdigest()


class SyntheticHost:
    def __init__(self, stop_arm=None):
        self.by_arm={}
        self.events=[]
        self.stop_arm=stop_arm

    def __call__(self,packet,*,arm,model,max_tokens,api_base):
        if arm==self.stop_arm:
            self.events.append((arm,"HOST_429"))
            raise OptionalHostResourceUnavailable("HTTP_429")
        step=len(self.by_arm.setdefault(arm,[]))
        if arm=="bare":
            answer=prose1()+"\n"+prose2()
        else:
            sequence=[
                PLAN, json.dumps(turns(),ensure_ascii=False),
                response(prose1(),ACTION1,EFFECT1),
                json.dumps({
                    "next_turn":{**turns()["turns"][1],
                        "goal":"女子核对石桥行动实际后果，才确定旧账册应如何使用"},
                    "basis_effect_quote":EFFECT1,
                    "pressure_quote":None,"cost_quote":None,
                    "unresolved_question":"谁改动桥索仍没有已写来源证明。",
                    "reason_for_shift":"少年上一段确实绕开石桥，旧账册应承接后果而非重写行动。",
                },ensure_ascii=False),
                response(prose2(),ACTION2,EFFECT2,EFFECT1),
            ]
            answer=sequence[step]
        self.by_arm[arm].append((packet.prompt_sha256,max_tokens))
        self.events.append((arm,step))
        return HostStudyCompletion(
            content=answer,model_id=model,
            request_prompt_sha256=packet.prompt_sha256,
            source_kind="SYNTHETIC_TEST_ONLY",provider_wire_sha256=None,
            actual_prompt_tokens=None,actual_completion_tokens=None
        )


class WF0BKRealCoreThreeArm(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.db_open=[]

    def tearDown(self):
        for db in self.db_open:
            db.close()
        self.temp.cleanup()

    @contextmanager
    def factory(self,arm):
        path=self.root/(arm+".sqlite")
        sid=make_db(path)
        db=WriterForgeDB(path)
        self.db_open.append(db)
        rt=RuntimeEngine();rt.enter_write(sid)
        assist=InvisibleWritingAssist(
            db,rt,"novel","s1","两位同行者为了石桥与旧账册发生意见分歧",
            model="fixture-author",api_base="http://127.0.0.1:1234/v1")
        yield assist

    def invoke(self,*,host=None,lease=None,directory="triad"):
        host=host or SyntheticHost()
        lease=lease or OptionalHostResourceLease(
            authorization_id="synthetic-three-arm-host-lease",
            allowances={"bare":8,"wf_core":8,"wf_habit":8})
        result=execute_three_arm_trial(
            outline=OUTLINE,task=TASK,source_prose=SOURCE,
            model_id="fixture-author",call_model=host,
            fresh_assist_factory=self.factory,
            output_dir=self.root/directory,host_lease=lease,
            fixture_mode=True,optional_habit_revision="v2")
        return result,host,lease

    def test_preflight_has_real_WF_not_fake_static_v1_v2_prompt(self):
        p=three_arm_preflight(
            outline=OUTLINE,task=TASK,source_prose=SOURCE,
            optional_habit_revision="v2")
        self.assertEqual(tuple(p["arms"]),FROZEN_ARMS)
        self.assertEqual(p["new_paid_provider_calls_authorized"],0)
        self.assertEqual(p["wf_core_execution_mode"],"continuity_guard")
        self.assertTrue(p["wf_core_uses_real_autonomous_writing"])
        self.assertTrue(p["wf_rolling_v98_opt_in"])
        self.assertTrue(p["wf_unified_narrative_core"])
        self.assertFalse(p["wf_v119_self_edit_used_in_this_protocol"])
        self.assertTrue(p["candidate_is_shadow_context_not_active_skill"])
        self.assertFalse(p["quality_improvement_proven"])

    def test_actual_core_WF_and_G_rolling_run_twice_with_local_fixture(self):
        receipt,host,lease=self.invoke()
        self.assertEqual(receipt["status"],"SYNTHETIC_PLUMBING_ONLY_NOT_LITERARY_RESULT")
        self.assertEqual(receipt["actual_model_callback_count"],11)
        self.assertEqual([len(host.by_arm[a]) for a in FROZEN_ARMS],[1,5,5])
        self.assertEqual(receipt["provider_authenticated_original_wires"],0)
        self.assertFalse(receipt["auto_promote"])
        self.assertFalse(receipt["literary_gain_proven"])
        self.assertIsNone(receipt["literary_winner"])
        self.assertEqual(receipt["canonical_fact_writes"],0)
        self.assertTrue(receipt["arm_results"]["bare"]["no_wf_core_invoked"])
        for arm in ("wf_core","wf_habit"):
            info=receipt["arm_results"][arm]
            self.assertEqual(info["origin"],"REAL_AUTONOMOUS_WRITING_CORE")
            self.assertEqual(info["writing_mode"],"continuity_guard")
            self.assertGreater(info["g_rolling_replan_calls"],0)
            self.assertEqual(info["narrative_core_owner_count"],1)
            self.assertEqual(info["chapter_count"],1)
            self.assertFalse(info["author_accepted"])
            self.assertTrue(info["source_checked_candidate_on_disk"])
        with self.assertRaises(FileExistsError):
            self.invoke()

    def test_paired_WF_arms_must_use_same_published_source_snapshot(self):
        receipt,_,_=self.invoke(directory="source-matched")
        self.assertEqual(
            receipt["arm_results"]["wf_core"]["published_source_snapshot_sha256"],
            receipt["arm_results"]["wf_habit"]["published_source_snapshot_sha256"])
        self.assertEqual(
            receipt["wf_paired_published_source_sha256"],
            receipt["arm_results"]["wf_core"]["published_source_snapshot_sha256"])

    def test_changed_WF_source_scope_is_rejected_before_candidate_model(self):
        @contextmanager
        def divergent(arm):
            with self.factory(arm) as assist:
                if arm=="wf_habit":
                    assist.goal="另外一套主角与旧书店的情节，不能冒充相同的原著范围。"
                yield assist
        host=SyntheticHost()
        lease=OptionalHostResourceLease(
            authorization_id="synthetic-paired-source-mismatch",
            allowances={"bare":8,"wf_core":8,"wf_habit":8})
        with self.assertRaisesRegex(ValueError,"SOURCE_SCOPE_DIVERGED"):
            execute_three_arm_trial(
                outline=OUTLINE,task=TASK,source_prose=SOURCE,
                model_id="fixture-author",call_model=host,
                fresh_assist_factory=divergent,
                output_dir=self.root/"different-source",
                host_lease=lease,fixture_mode=True)
        self.assertEqual(len(host.by_arm.get("bare",[])),1)
        self.assertEqual(len(host.by_arm.get("wf_core",[])),5)
        self.assertEqual(len(host.by_arm.get("wf_habit",[])),0)
        state=json.loads((self.root/"different-source"/"STATUS.json").read_text("utf8"))
        self.assertEqual(state["status"],"DORMANT_CORE_OR_HOST_FAILURE_NO_RETRY")
        self.assertEqual(state["arm_results"]["wf_habit"]["status"],"FAILED_NO_RETRY")
        self.assertFalse(state["auto_promote"])

    def test_bare_never_receives_WF_internals_or_habit_instruction(self):
        outer=self
        class Checking(SyntheticHost):
            def __call__(self,packet,**kwargs):
                outer.assertEqual(sha(packet.prompt),packet.prompt_sha256)
                if kwargs["arm"]=="bare":
                    outer.assertNotIn("WriterForge",packet.prompt)
                    outer.assertNotIn("observe-before-next-choice",packet.prompt)
                    outer.assertNotIn("【认知候选（仅实验数据）】",packet.prompt)
                if kwargs["arm"]=="wf_core":
                    outer.assertNotIn("【认知候选（仅实验数据）】",packet.prompt)
                if kwargs["arm"]=="wf_habit":
                    outer.assertIn("【认知候选（仅实验数据）】",packet.prompt)
                    outer.assertIn("source-verified facts separate",packet.prompt)
                return super().__call__(packet,**kwargs)
        self.invoke(host=Checking())

    def test_missing_host_budget_no_any_model_or_WF_run(self):
        cb=SyntheticHost()
        with self.assertRaises(PermissionError):
            execute_three_arm_trial(
                outline=OUTLINE,task=TASK,source_prose=SOURCE,
                model_id="fixture-author",call_model=cb,
                fresh_assist_factory=self.factory,
                output_dir=self.root/"blocked",host_lease=None,
                fixture_mode=True)
        self.assertFalse((self.root/"blocked").exists())
        self.assertEqual(cb.events,[])

    def test_structured_429_burns_attempt_and_no_hidden_retry(self):
        host=SyntheticHost(stop_arm="wf_core")
        with self.assertRaises(OptionalHostResourceUnavailable):
            self.invoke(host=host,directory="partial")
        state=json.loads((self.root/"partial"/"STATUS.json").read_text("utf8"))
        self.assertEqual(state["status"],"DORMANT_HOST_RESOURCE_NO_RETRY")
        self.assertEqual(state["arm_results"]["bare"]["status"],"CALLBACK_COMPLETED")
        self.assertEqual(state["arm_results"]["wf_core"]["status"],"FAILED_NO_RETRY")
        self.assertEqual(host.events.count(("wf_core","HOST_429")),1)
        self.assertEqual(state["new_paid_model_api_requests"],0)
        self.assertFalse(state["auto_promote"])

    def test_fixture_can_never_claim_verified_paid_provider(self):
        cb=SyntheticHost()
        lease=OptionalHostResourceLease(
            authorization_id="synthetic-only-no-production",
            allowances={"bare":8,"wf_core":8,"wf_habit":8})
        with self.assertRaisesRegex(PermissionError,"REAL_PROVIDER_WIRE_REQUIRED"):
            execute_three_arm_trial(
                outline=OUTLINE,task=TASK,source_prose=SOURCE,
                model_id="fixture-author",call_model=cb,
                fresh_assist_factory=self.factory,
                output_dir=self.root/"not-real",host_lease=lease,
                fixture_mode=False)
        self.assertFalse((self.root/"not-real").exists())
        self.assertEqual(cb.events,[])


if __name__=="__main__":
    unittest.main()
