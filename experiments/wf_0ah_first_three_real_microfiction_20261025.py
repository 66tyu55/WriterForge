"""WF 0.AH: first three NEW genres, one 200-350-Hanzi micro-scene each.

Same frozen literary task, DeepSeek Flash, system, provider settings and max
completion tokens for bare and WF. WF only supplies existing source-boundary
instructions, not prose, literary grades or a mandated plot. Both original
provider response envelopes stay in an Actions artifact, SHA bound to scores.
This script intentionally does not replay or regenerate 0.AD/0.AE originals.
No R2, Canon, Railway, main, or literary memory writes; no retries.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import os
import re

from experiments.wf_0ad_multigenre_real_paired_writing_20261025 import (
    scene_prompt, judge_prompt, parse_judge, normalize, CRITERIA, JUDGEMENTS,
)
from writerforge.deepseek_flash_model import DeepSeekFlashModel, FlashBudget
from writerforge.v96_causal_turns import (
    check_turn, make_turn_instructions, normalize_model_source_citations,
    V96CausalDraftError,
)
from writerforge.v116_state_delta import preflight_next_prose
from writerforge.v114_external_story_state import (
    external_temporal_step, require_external_runtime,
)

OUT = Path("wf_0ah_first_three_original_microfiction_20261025")
AUTHOR_MAX_TOKENS = 1700  # IDENTICAL for both author arms.
JUDGE_MAX_TOKENS = 1750
MAX_CALLS = 12
MAX_RESERVED_OUTPUT = 22000
SCENES = (
    {
        "id": "wuxia_bridge", "genre": "原创武侠",
        "role": "伤后行动与桥面空间", "actor": "段衡", "kind": "action",
        "topic": (
            "峡谷夜雨，镖师段衡护送左腿受伤的顾青通过只能容一人侧身的悬桥。"
            "几块桥板松脱，两人均不能飞跃，也不能突然获得新武学、药物或武器。"
            "写一段真正发生的移动、阻力和即时代价；桥另一端是否安全尚未证实。"
        ),
        "literary_task": "用身体位置、可见阻力和细节表现不得不做的选择及代价。",
    },
    {
        "id": "xianxia_herb", "genre": "原创仙侠",
        "role": "灵植资源与有限认知", "actor": "洛荀", "kind": "setup",
        "topic": (
            "小药圃里一株灵植比预计提前一夜成熟，主人公洛荀天亮前尚未打开封住的园门。"
            "有人可能采摘过，但洛荀不知道是谁，也不知道植株是否仍在原位。"
            "用可观察之物与个人猜测制造悬念，不能直接把未知采摘者写成角色知道的事实。"
        ),
        "literary_task": "保留资源归属、观察范围与人物认知的边界，不强迫揭示答案。",
    },
    {
        "id": "history_dispatch", "genre": "原创历史",
        "role": "边关文书时间与决策", "actor": "谢让", "kind": "decision",
        "topic": (
            "边关前锋营夜里发现敌军调动，书记官谢让必须决定是否冒险送出文书。"
            "从前锋营传到主帅营至少需要穿越整整一夜，主帅不可能立即得知内容。"
            "描写封信、出发或延误的实际证据，以及当下选择的代价，不能突然跨越交通时间。"
        ),
        "literary_task": "用真实的消息传播时间、文书去向与军事代价构成叙事张力。",
    },
)
SYSTEM = (
    "你是中文原创小说写作者，或仅在匿名评分任务中作为文学评审。"
    "必须严格只输出有效 JSON，禁复制名著句子、人物和剧情。"
    "不得作为 WriterForge 软件作出结构事实裁定。"
)
ARM_ORDER = ("bare", "WF")
AUTHOR_TASK = {"bare": "bare-author", "WF": "WF-author"}
REVIEW_NOTE = "UNASSESSED_SOURCE_AND_SEMANTIC_AUDIT_REQUIRED"


def h(value):
    return sha256(value.encode("utf8") if isinstance(value, str) else value).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                               sort_keys=True), encoding="utf8")


def need(condition, code):
    if not condition:
        raise RuntimeError(code)


def safe_code(error):
    code = str(error)
    return code if re.fullmatch(r"WF[A-Z0-9_:\-]{3,160}", code) else (
        type(error).__name__ + ":NO_RETRY"
    )


def hanzi_count(value):
    return len(re.findall(r"[\u3400-\u9fff]", value))


def beat(item):
    return {
        "id": "t01", "kind": item["kind"], "actor": item["actor"],
        "goal": item["literary_task"] + "由写作AI自己选择叙事行为",
        "causal_parent": None, "craft_focus": [],
    }


def author_prompt(item, arm):
    common = scene_prompt(item)
    if arm == "bare":
        return common + '\n严格只输出JSON: {"prose":"你创作的完整小说正文"}。'
    return (common + "\n【WF现有来源核验契约，不决定文学内容】" +
            make_turn_instructions(beat(item), mode="causal_guard"))


def protocol_receipt():
    return {
        "format": "wf.0ah.frozen-three-genres-microfiction.v1",
        "frozen_scenes_sha256": h(canonical(SCENES)),
        "genres": [x["genre"] for x in SCENES],
        "author_max_tokens_each_arm": AUTHOR_MAX_TOKENS,
        "judge_max_tokens_each_order": JUDGE_MAX_TOKENS,
        "same_provider": "deepseek", "same_model": "deepseek-flash",
        "temperature": "provider_default_identical_both_arms",
        "thinking": "disabled", "response_format": "json_object",
        "same_system_both_arms": True,
        "same_literary_scene_prompt_both_arms": True,
        "equal_completion_ceiling_both_author_arms": True,
        "WF_extra_trace_JSON_uses_some_of_same_budget": True,
        "same_output_budget_does_not_equalize_prompt_length": True,
        "same_model_family_judge_not_independent_human": True,
        "original_0AD_0AE_authors_never_called": True,
        "no_paid_retry": True,
        "allowed_hanzi_count": [200, 350],
        "literary_score_does_not_decide_source_acceptance": True,
        "V117": "NOT_APPLICABLE_FIRST_MICROSEGMENT_NO_PREVIOUS_ACCEPTED_SCENE",
        "V119": "NOT_APPLICABLE_NO_AUTHOR_REVISION",
        "R2_reads": 0, "R2_writes": 0, "canon_writes": 0,
        "Railway_deployments": 0, "main_modified": False,
    }


class OriginalCaller:
    def __init__(self, api_key):
        self.active = None
        self.events = []
        self.budget = FlashBudget(max_calls=MAX_CALLS,
                                  max_reserved_output_tokens=MAX_RESERVED_OUTPUT)
        self.model = DeepSeekFlashModel(
            api_key=api_key, budget=self.budget, timeout_seconds=110,
            on_response_wire=self._preserve_wire,
        )

    def _preserve_wire(self, raw):
        need(type(raw) is bytes and self.active is not None,
             "WF0AH_UNCLAIMED_PROVIDER_WIRE")
        dest = OUT / "provider-originals" / (self.active + ".json")
        dest.parent.mkdir(parents=True, exist_ok=True)
        need(not dest.exists(), "WF0AH_NO_PROVIDER_WIRE_OVERWRITE")
        dest.write_bytes(raw)
        self.events[-1]["raw_provider_sha256"] = h(raw)
        self.events[-1]["original_provider_wire_preserved"] = True

    def ask(self, item_id, task, role, prompt, tokens):
        need(task in (
            "bare-author", "WF-author",
            "anonymous-rater-first", "anonymous-rater-reversed"
        ) and len(self.events) < MAX_CALLS, "WF0AH_NEW_CALL_OUTSIDE_SCOPE")
        self.active = item_id + "_" + task
        event = {
            "scene": item_id, "task": task, "prompt_sha256": h(prompt),
            "system_sha256": h(SYSTEM),
            "max_output_tokens_reserved": tokens,
            "model": "deepseek-flash", "original_provider_wire_preserved": False,
        }
        self.events.append(event)
        try:
            response = self.model.ask_json(
                role=role, system=SYSTEM, user=prompt, max_tokens=tokens)
            event["decoded_reply_sha256"] = h(canonical(response))
            event["response_valid_json"] = True
            return response
        except Exception as error:
            event["error_code"] = safe_code(error)
            event["response_valid_json"] = False
            raise
        finally:
            self.active = None


def source_check(prose, actor):
    pre = preflight_next_prose(
        prose, previous_candidate_state={}, cast=(actor,))
    checkpoint = external_temporal_step(prose, cast=(actor,))
    need(checkpoint["source_sha256"] == h(prose),
         "WF0AH_V114_CHECKPOINT_SOURCE_SHA_MISMATCH")
    return {
        "prose_sha256": h(prose),
        "V116_blocked": pre["blocked"],
        "V116_hard_findings": pre["findings"],
        "V116_review_findings": pre["review_findings"],
        "V116_needs_review": pre["needs_review"],
        "V122_source_relation_pairs": pre["physical_relation_review_pairs"],
        "V114_candidate_receipt_sha256": checkpoint["receipt_sha256"],
        "real_world_causality_judgment": REVIEW_NOTE,
        "human_confirmed_false_red": REVIEW_NOTE,
        "human_confirmed_false_green": REVIEW_NOTE,
    }


def make_authors(caller, item):
    data = {}
    b = beat(item)
    for arm in ARM_ORDER:
        prompt = author_prompt(item, arm)
        original = normalize(caller.ask(
            item["id"], AUTHOR_TASK[arm], "self_scene_writing",
            prompt, AUTHOR_MAX_TOKENS),
            ("prose",) if arm == "bare" else ("prose", "trace"))
        prose = original["prose"]
        need(type(prose) is str and prose == prose.strip() and
             80 <= len(prose) <= 1024,
             "WF0AH_AUTHOR_PROSE_EMPTY_OR_OUT_OF_V96_BOUND")
        # Never mutate a literary source. Even noncomparable lengths survive.
        (OUT / (item["id"] + "_" + arm + "-original.md")).write_text(
            prose, encoding="utf8")
        checks = source_check(prose, item["actor"])
        checks["hanzi_count"] = hanzi_count(prose)
        checks["within_200_350_hanzi"] = (200 <= hanzi_count(prose) <= 350)
        checks["writer_prompt_sha256"] = h(prompt)
        if arm == "WF":
            wire = json.dumps(original, ensure_ascii=False,
                              separators=(",", ":"))
            normalized, receipt = normalize_model_source_citations(
                wire, b, accepted=())
            need(json.loads(normalized)["prose"] == prose,
                 "WF0AH_TRACE_NORMALIZATION_CHANGED_ORIGINAL_PROSE")
            checks["V96_spelling_only_normalizer"] = receipt
            try:
                accepted = check_turn(
                    normalized, b, mode="causal_guard",
                    accepted=(), max_prose_chars=1024)
                checks["V96_status"] = "SOURCE_QUOTE_TRACE_VALID_CANDIDATE_ONLY"
                checks["V96_receipt"] = accepted["receipt"]
            except V96CausalDraftError as error:
                checks["V96_status"] = "HELD_TRACE_INVALID"
                checks["V96_failure_code"] = safe_code(error)
        data[arm] = {"prose": prose, "source_sha256": h(prose),
                     "source_checks": checks}
    return data


def assess(caller, item, pair):
    result = {"裸模型": [], "WF辅助": []}
    for idx, order in enumerate(JUDGEMENTS):
        prompt = judge_prompt(item, pair, order)
        parsed = parse_judge(caller.ask(
            item["id"], "anonymous-rater-first" if idx == 0
            else "anonymous-rater-reversed",
            "craft_analysis", prompt, JUDGE_MAX_TOKENS))
        for key, label in zip(order, ("甲", "乙")):
            entry = parsed[label]
            result[key].append({
                "total": sum(entry["scores"].values()),
                "dimensions": entry["scores"],
                "reason": entry["reason"], "weakness": entry["weakness"],
                "judge_prompt_sha256": h(prompt),
            })
    graded = {}
    for key, rows in result.items():
        graded[key] = {
            "score_100": sum(r["total"] for r in rows) / 2,
            "per_order_scores": [r["total"] for r in rows],
            "order_sensitivity": abs(rows[0]["total"] - rows[1]["total"]),
            "dimensions_average": {
                k: (rows[0]["dimensions"][k] + rows[1]["dimensions"][k]) / 2
                for k in CRITERIA
            },
            "rater_original_evaluations": rows,
        }
    graded["WF_minus_bare"] = graded["WF辅助"]["score_100"] - (
        graded["裸模型"]["score_100"])
    return graded


def main():
    need(not OUT.exists(), "WF0AH_ONE_SHOT_OUTPUT_ALREADY_EXISTS")
    OUT.mkdir(parents=True)
    status = {
        **protocol_receipt(),
        "status": "NOT_STARTED",
        "cases": {}, "events": [], "actual_paid_call_reservations": 0,
    }
    model = None
    try:
        require_external_runtime()
        need(not any(os.getenv(x) for x in (
            "WRITERFORGE_R2_ACCOUNT_ID", "WRITERFORGE_R2_ACCESS_KEY_ID",
            "DISCOVERY_API_KEY", "OPENAI_API_KEY")),
            "WF0AH_UNNEEDED_PROVIDER_OR_CANON_CONFIG")
        key = os.getenv("DEEPSEEK_API_KEY", "")
        need(len(key) >= 16, "WF0AH_EXISTING_DEEPSEEK_KEY_UNAVAILABLE")
        model = OriginalCaller(key)
        for item in SCENES:
            row = {
                "genre": item["genre"], "literary_role": item["role"],
                "scene_task_sha256": h(canonical(item)),
                "status": "NOT_YET_WRITTEN",
            }
            status["cases"][item["id"]] = row
            try:
                authors = make_authors(model, item)
                row["source_evidence"] = {
                    arm: {k: v for k, v in authors[arm].items() if k != "prose"}
                    for arm in ARM_ORDER
                }
                chars = [hanzi_count(authors[a]["prose"]) for a in ARM_ORDER]
                row["length_ratio"] = round(max(chars) / min(chars), 3)
                row["length_comparable"] = (
                    all(200 <= n <= 350 for n in chars)
                    and max(chars) <= 1.25 * min(chars))
                row["status"] = "ORIGINAL_PAIR_READY"
            except Exception as err:
                row["status"] = "ORIGINAL_AUTHOR_PAIR_INCOMPLETE"
                row["failure_code"] = safe_code(err)
                continue
            try:
                row["ratings"] = assess(model, item, authors)
                fluctuation = max(
                    row["ratings"][arm]["order_sensitivity"]
                    for arm in ("裸模型", "WF辅助"))
                row["score_interpretation"] = (
                    "NOT_COMPARABLE" if not row["length_comparable"]
                    else "LOW_CONFIDENCE_ORDER_SENSITIVITY" if fluctuation > 8
                    else "EXPLORATORY_SINGLE_SAMPLE_SAME_FAMILY_RATER"
                )
                row["status"] = "REAL_PAIR_AND_TWO_ORDER_SCORES"
            except Exception as err:
                row["status"] = "RATING_INCOMPLETE_NO_RETRY"
                row["failure_code"] = safe_code(err)
            finally:
                save(OUT / "PARTIAL.json", status)
        if all(x.get("status") == "REAL_PAIR_AND_TWO_ORDER_SCORES"
               for x in status["cases"].values()) and len(status["cases"]) == 3:
            status["status"] = "THREE_REAL_PAIRS_GRADED_WITH_LIMITATIONS"
        else:
            status["status"] = "PARTIAL_PRESERVE_REAL_ORIGINALS_NO_RETRY"
    except Exception as err:
        status["status"] = "INTERRUPTED_NO_PROVIDER_RETRY"
        status["failure_code"] = safe_code(err)
    finally:
        if model is not None:
            status["events"] = model.events
            status["budget_receipt"] = model.budget.public_receipt()
            status["actual_paid_call_reservations"] = (
                model.budget.calls_reserved)
        status["no_source_semantics_or_literary_superiority_inferred"] = True
        save(OUT / "STATUS.json", status)
        print("0AH_STATUS:", status["status"])
        print("0AH_PAID_REQUESTS_RESERVED:",
              status["actual_paid_call_reservations"])
        for key, row in status["cases"].items():
            print("0AH_SCENE:", key, row["status"],
                  row.get("score_interpretation"),
                  row.get("ratings", {}).get("WF_minus_bare"))
    if status["status"] != "THREE_REAL_PAIRS_GRADED_WITH_LIMITATIONS":
        raise RuntimeError("WF0AH_PARTIAL_MODEL_OR_GRADING_RESULT_SEE_ARTIFACT")


if __name__ == "__main__":
    main()
