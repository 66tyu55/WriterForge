"""V44 adversarial *execution* evaluation of the untouched V43 implementation.

Run six distinct goal contexts through the real published-source WF writing
entry point. No LLM, examiner-provided "good" novel, or historic evidence
rewrite. Report failed usefulness claims even when all engineering tests pass.
A/B holds goal/scene/concerns constant and changes ONLY experimental policy.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from writerforge import WriterForgeDB, RuntimeEngine, OriginalStudy
from writerforge import VerifiedWritingFlow, WritingExecutionError, save_candidate
from writerforge.experience_executor import ExperienceExecutor, RULE_ID


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/fixtures/xiyouji_chapter_001_original_zh.txt"
OUTPUT = ROOT / "v44_multicontext_adversarial_results.json"

# Previously unseen task-only prompts; no plots, prose, causal plans, or
# learning experiences are authored by this script for WF to impersonate.
TASKS = (
    ("mountain-market", "山镇药商面对真假货源与陌生顾客之间的冲突"),
    ("seaside-inn", "海滨驿站的邮差发现一次送信顺序异常"),
    ("border-pass", "边关守夜人必须选择是否放行带伤陌生人"),
    ("city-theater", "城市剧团演员发现道具遗失后准备登台"),
    ("forest-medic", "雨林救护员发现补给箱的封签出现破损"),
    ("river-ferry", "江边摆渡人接到互相矛盾的两份请求"),
)

def _digest(s):
    return sha256(s.encode("utf-8")).hexdigest()

def _real_db(path: Path):
    db=WriterForgeDB(path)
    rt=RuntimeEngine()
    rt.enter_learn()
    OriginalStudy(db,rt).ingest(
        SOURCE.read_text(encoding="utf-8"),work_id="v44-source-genuine-zh",
        require_hundred=False)
    sid=db.conn.execute(
        "SELECT MAX(id) id FROM snapshots WHERE status='published'"
    ).fetchone()["id"]
    rt.exit()
    rt.enter_write(int(sid))
    return db,rt,VerifiedWritingFlow(db,rt,"v44-audit")

def _provided_plan(scene: str) -> dict:
    """Explicitly red-team supplied: it is NOT generated/learned by WF."""
    return {
        "clue_id":"clue-"+scene,
        "actor_id":"虚构角色",
        "knowledge_before":"角色在观察前只掌握当前任务的基本事实",
        "unknown_before":"角色暂不清楚线索真正来源与完整含义",
        "observation":"角色在当前场景看见一个需要核对的物件细节",
        "decision":"角色决定暂缓原有行动并核对可疑细节",
        "decision_depends_on_clue":"物件细节与当前角色期待的正常状态不相符合",
        "later_reveal_target":"后文将明确这个物件细节如何出现以及真实缘由",
        "alternative_explanation":"也可能是普通搬运留下的痕迹而不是人为设置",
        "uncertainty":"尚未知道物件来源，任何人物归责都必须保持待定",
    }

def _call(flow,scene,goal,*,opt_in,plan):
    return flow.prepare(
        scene,goal,concerns=("setup_payoff",),
        experience_experiment=opt_in,causal_plan=plan)

def run() -> dict:
    with TemporaryDirectory(prefix="writerforge-v44-") as tmp:
        db,rt,flow=_real_db(Path(tmp)/"real-wf.sqlite3")
        executor=ExperienceExecutor(db.conn,"v44-audit")
        rule_sha=executor.install_v38_candidate(explicit_experiment_opt_in=True)
        six=[]
        for scene,goal in TASKS:
            base=_call(flow,scene,goal,opt_in=False,plan=None)
            missing=None
            try:
                _call(flow,scene,goal,opt_in=True,plan=None)
            except WritingExecutionError as e:
                missing=str(e)
            supplied=_provided_plan(scene)
            active=_call(flow,scene,goal,opt_in=True,plan=supplied)
            assert active.strategy_receipt["status"]=="CAUSAL_PREFLIGHT_VERIFIED_STRUCTURALLY"
            frozen_count=db.conn.execute(
                "SELECT COUNT(*) FROM wf_experience_prewrite WHERE project=? AND scene_id=?",
                ("v44-audit",scene)).fetchone()[0]
            six.append({
                "scene":scene,"task_sha256":_digest(goal),
                "baseline_prepare":"ALLOWED",
                "active_missing_prewrite_failure":missing,
                "active_with_examiner_supplied_plan":"ALLOWED",
                "prewrite_sha256":active.strategy_receipt["frozen_prewrite_sha256"],
                "frozen_plan_rows":frozen_count,
                "baseline_prompt_sha256":base.prompt_sha256,
                "experimental_prompt_sha256":active.prompt_sha256,
                "prompts_byte_for_byte_equal":base.prompt==active.prompt,
                "experience_plan_in_generation_prompt":any(
                    v in active.prompt for v in (
                        supplied["clue_id"],supplied["knowledge_before"],
                        supplied["decision_depends_on_clue"])),
                "prewrite_from_wf_self_learning":False,
                "real_prose_generated":False,
                "literary_quality_proven":False,
            })
        # If V43 accepts contradictory content, report it, never repair it.
        contradict=_provided_plan("contradiction")
        contradict["knowledge_before"]=(
            "角色已经知道所谓的悬念来自正常损坏并且完全知道物件真相")
        contradict["unknown_before"]=(
            "角色同时明确不知道此物如何损坏，只知道是自然损坏")
        logical_status="BLOCKED"
        try:
            _call(flow,"contradiction","一个角色遇到信息互相矛盾的现场",
                  opt_in=True,plan=contradict)
            logical_status="ACCEPTED_UNVERIFIED"
        except WritingExecutionError:
            pass

        # Same runtime storage, but no clue-identity story state -> role mismatch.
        with db.conn:
            db.conn.execute(
                "INSERT INTO causal_events(project_id,event_id,payload_json) VALUES(?,?,?)",
                ("v44-audit","already-paid",json.dumps({
                    "clue_id":"clue-already-paid",
                    "narrative_role":"payoff","review_status":"confirmed"
                },ensure_ascii=False)))
        resolved_status="ACCEPTED_UNSAFE"
        try:
            _call(flow,"already-paid","曾经回收的物件再次出现",
                  opt_in=True,plan=_provided_plan("already-paid"))
        except WritingExecutionError as err:
            resolved_status=str(err)
        with db.conn:
            db.conn.execute(
                "INSERT INTO causal_events(project_id,event_id,payload_json) VALUES(?,?,?)",
                ("v44-audit","disputed-paid",json.dumps({
                    "clue_id":"clue-disputed-paid",
                    "narrative_role":"payoff","review_status":"disputed"
                },ensure_ascii=False)))
        disputed=_call(flow,"disputed-paid","存在争议的线索的后续展开",
                       opt_in=True,plan=_provided_plan("disputed-paid"))

        unrelated=flow.prepare(
            "dialogue-only","两名旧友谈论离开小镇的原因",
            concerns=("dialogue",),experience_experiment=True)

        # RED TEAM: four real distinct ordered citations may have no
        # semantic dependency at all. This is NOT WF-authored prose.
        disconnected=(
            "村口晒着四个未收走的空竹篮。"
            "少女走到城中买了两斤盐和一尺麻绳。"
            "昨夜的雨冲掉了山坡上的几片旧瓦。"
            "第二天有人发现书架上的画册早已虫蛀。"
        )
        fake_anchors={
            "observation":"村口晒着四个未收走的空竹篮",
            "actor_decision":"少女走到城中买了两斤盐和一尺麻绳",
            "causal_consequence":"昨夜的雨冲掉了山坡上的几片旧瓦",
            "later_reveal":"第二天有人发现书架上的画册早已虫蛀",
        }
        unrelated_text_passed=False
        disconnected_status=None
        gate_packet=_call(flow,"semantic-adversary",
                 "四件完全不相关的事件被错误当作同一条因果链",
                 opt_in=True,plan=_provided_plan("semantic-adversary"))
        try:
            saved=save_candidate(
                gate_packet,disconnected,"V44_STATIC_TEST_FIXTURE",
                Path(tmp)/"adversarial-not-WF-written",
                postwrite_evidence=fake_anchors)
            unrelated_text_passed=True
            artifact=json.loads(Path(saved["manifest"]).read_text(encoding="utf-8"))
            disconnected_status=artifact.get("experience_semantic_correctness_verified")
        except WritingExecutionError as err:
            disconnected_status=str(err)

        # Attacker can claim reviewer_is_independent=True without a verified
        # reviewer receipt. The action proves technical rollback but not
        # authentic independent assessment.
        harm=[]
        for i in range(2):
            scene=f"harm-simulation-{i}"
            _call(flow,scene,"独立反馈资格攻击负例",opt_in=True,
                  plan=_provided_plan(scene))
            item=executor.record_outcome(
                scene_id=scene,outcome="HARMED",
                report_sha256=_digest("SYNTHETIC-NOT-INDEPENDENT-"+str(i)),
                reviewer_is_independent=True)
            harm.append(item["active_status"])
        post_rollback=_call(flow,"after-paused",
            "策略受害后恢复原始行为",opt_in=True,plan=None)
        db.close()
        # Additional fresh-open readback to avoid relying on process memory.
        reopened=WriterForgeDB(Path(tmp)/"real-wf.sqlite3")
        active=reopened.conn.execute(
            "SELECT status FROM wf_experience_policies "
            "WHERE project='v44-audit' AND rule_id=?", (RULE_ID,)
        ).fetchone()[0]
        rows=reopened.conn.execute(
            "SELECT COUNT(*) FROM wf_experience_prewrite WHERE project='v44-audit'"
        ).fetchone()[0]
        reopened.close()

    result={
        "format":"writerforge.v44-preregistered-multicontext-real-entry-ablation.v1",
        "parent_v43_original_production_code_changed":False,
        "scenario_count":len(TASKS),
        "source_material":"real_original_chinese_first_chapter_test_fixture",
        "experience_policy_source":"V38 historical conflict hard-coded as experimental candidate",
        "rule_sha256":rule_sha,
        "comparisons":six,
        "summary":{
            "missing_prewrite_blocked_count":sum(bool(x["active_missing_prewrite_failure"])
                                                  for x in six),
            "valid_examiner_supplied_plan_allowed_count":sum(
                x["active_with_examiner_supplied_plan"]=="ALLOWED" for x in six),
            "same_prompt_count":sum(x["prompts_byte_for_byte_equal"] for x in six),
            "semantic_contradiction_test_result":logical_status,
            "previously_confirmed_payoff_setup_result":resolved_status,
            "disputed_payoff_result":disputed.strategy_receipt["status"],
            "unrelated_dialogue_status":unrelated.strategy_receipt["status"],
            "unrelated_four_quotes_saved_as_candidate":unrelated_text_passed,
            "disconnected_semantics_verified_field":disconnected_status,
            "synthetic_unverified_reviewer_labels_caused_pause":harm[-1]=="PAUSED_DUE_TO_HARM",
            "policy_after_fresh_db_reopen":active,
            "prewrites_preserved_after_reopen":rows,
            "roll_back_allows_new_scene":post_rollback.strategy_receipt["status"],
            "new_model_calls":0,
            "completed_new_literary_AB":False,
            "learned_strategy_improved_novel":False,
        },
        "original_v35_v38_R2_untouched":True,
    }
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n",
                      encoding="utf-8")
    print(json.dumps({
        "format":result["format"],"scenario_count":len(TASKS),
        "summary":result["summary"],"report_sha256":_digest(
            OUTPUT.read_text(encoding="utf-8"))},
        ensure_ascii=False,sort_keys=True))
    return result


if __name__=="__main__":
    run()
