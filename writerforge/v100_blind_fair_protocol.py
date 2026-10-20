"""V100: private historical blind packet builder and NEW xianxia preregistration.

Pure local functions: NO model calls, remote reads/writes, skill graduation or
canonical state changes. V97 1500-target is historical and never relabeled 1600.
Full prose appears ONLY in caller-saved private blind packets, not in logs.
"""
from __future__ import annotations
from hashlib import sha256
import json

from .v99_longform_quality_evidence import (
    freeze_manuscript, compare_equal_length, digest,
)

HISTORICAL_MANIFEST = "d304d2432e2c3290b6bbd8ccb6bc209e38b7e12bc0aabb968b489b31c22b02a1"
HISTORICAL_PRECOMMIT = "5c7fac8ef9ab0f588698711ba1b63672a2eab18ff4f65d53bf8616489d36cae1"
HISTORICAL_TARGET = 1500
HISTORICAL_ACTUAL = {"single":1902, "split_only":1601, "causal_guard":1554}
MODES = ("single", "split_only", "causal_guard", "rolling_causal")
BLIND_IDS = ("稿件01", "稿件02", "稿件03")
NEW_CASE = "v100_xianxia_critical_watergate"
NEW_TARGET = 1600
# Each arm reserves the SAME output-token capacity, including D replans.
# This is not equality of ACTUAL tokens consumed; record them separately.
MODEL = "deepseek-flash"
OUTPUT_RESERVATION = {
    "single": (4800,),
    "split_only": (1600, 1600, 1600),
    "causal_guard": (1600, 1600, 1600),
    "rolling_causal": (1300, 450, 1300, 450, 1300),
}
MAX_CALLS = 12
MAX_OUTPUT_RESERVED = 19200
MAX_CONSERVATIVE_INPUT_OUTPUT = 145000
WORLD = (
    "原创仙侠。暮雨时，栖梧山下灵渠水位猛涨，山脚九户人家将被淹。"
    "守渠外门弟子林霁炼气三层，既怕山门责罚，也不愿眼看村民丧命。"
    "他只能使用一枚传讯符，不能瞬移、凭空修复闸轮或无限施法。"
    "医谷学徒顾晚禾知道旧渠账本有一页被调换，却不知是谁换的，"
    "更不知道今晚闸轴毁坏是否人为。掌管禁令的师叔真实动机未知。"
    "旧泄洪渠可导水至盐田，若启用会损失当季药盐、切断下山药路。"
    "归潮闸必须有人到现场手动转动铜轮，灵符不能隔空开闸。"
    "师门禁令未经许可不得开旧渠；人物可违反，却应承担现实后果。"
    "不允许突然出现万能法宝、全知旁白确认嫌疑，或零代价化解全部困境。"
)
GOAL = (
    "写一章约1600中文含标点字符的仙侠原创小说。林霁和顾晚禾"
    "面对真实水势、有限证据与相互冲突的责任，必须凭可观察事实决定"
    "先救人、核查旧闸或违令分洪。至少一次选择导致不可轻易抹去的代价，"
    "留下一个未解但有铺垫的疑问。情节用动作和人物声音推进，"
    "避免机械解释因果/技法，视角限定林霁。"
)
FROZEN_PLAN = {
    "objective": "在暮雨淹村之前护住山下九户性命",
    "conflict": "旧闸需要现场操作，开闸将淹盐田且违背师门禁令",
    "decision": "林霁权衡证据后选择实际可执行的救援方式，不能靠未知万能法宝",
    "outcome": "选择改变水势和人物关系；若开旧渠须承担盐田及师门后果",
    "pov": "林霁有限视角；师叔与改账者的意图都尚未知",
    "needs": ["action", "dialogue", "decision"],
}
FROZEN_TURNS = {"turns": [
    {"id":"t01","kind":"action","actor":"林霁",
     "goal":"实地查验闸前水势并作首次救援行动，付出资源或时间代价",
     "causal_parent":None,"craft_focus":["detail","action"]},
    {"id":"t02","kind":"decision","actor":"顾晚禾",
     "goal":"拿出旧渠账页可证实的异常，促使两人区别传闻与事实",
     "causal_parent":"t01","craft_focus":["dialogue","restraint"]},
    {"id":"t03","kind":"decision","actor":"林霁",
     "goal":"在水涨时作出能执行的选择，承担真实损失且改变后续局面",
     "causal_parent":"t02","craft_focus":["interiority","action"]},
]}
REVIEW_AXES = (
    "人物欲望/可信动机", "信息边界/人物知情", "行动导致的可见因果",
    "选择的不可抹除代价", "时间物品能力硬连续", "对白与人物声音",
    "节奏张力与伏笔兑现", "自然度/避免说明书语言",
)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",",":"), allow_nan=False).encode("utf8")


def xianxia_precommit():
    reservations = {a: sum(v) for a,v in OUTPUT_RESERVATION.items()}
    assert set(reservations) == set(MODES)
    assert set(reservations.values()) == {4800}
    assert sum(len(v) for v in OUTPUT_RESERVATION.values()) == MAX_CALLS
    assert sum(reservations.values()) == MAX_OUTPUT_RESERVED
    return {
        "format": "wf.writing.xianxia-four-arm-preregistered.v100",
        "case_id": NEW_CASE, "genre": "原创仙侠", "model": MODEL,
        "model_version_must_be_recorded_if_provider_exposes": True,
        "story_sha256": digest(WORLD.encode("utf8")),
        "chapter_goal_sha256": digest(GOAL.encode("utf8")),
        "frozen_plan_sha256": digest(canonical(FROZEN_PLAN)),
        "frozen_turns_sha256": digest(canonical(FROZEN_TURNS)),
        "world": WORLD, "goal": GOAL,
        "frozen_plan": FROZEN_PLAN, "frozen_turns": FROZEN_TURNS,
        "arm_order_fixed_before_first_request": list(MODES),
        "target_codepoints_including_punctuation": NEW_TARGET,
        "arm_request_output_token_reservations": {
            k: list(v) for k,v in OUTPUT_RESERVATION.items()
        },
        "max_calls": MAX_CALLS,
        "max_reserved_completion_tokens": MAX_OUTPUT_RESERVED,
        "max_conservative_input_output": MAX_CONSERVATIVE_INPUT_OUTPUT,
        "no_auto_retry_on_timeout_or_schema_failure": True,
        "lengths_compared_only_with_max_relative_gap": 0.10,
        "also_require_each_length_within_10pct_of_target": True,
        "cost_study_records_actual_prompt_completion_tokens": True,
        "D_replan_extra_requests_are_part_of_its_5_call_budget": True,
        "equal_output_reservation_not_equal_actual_inference_cost": True,
        "original_15_chapters_and_v97_7_requests_untouched": True,
        "no_acceptance_no_auto_graduation_no_known_fact_writes": True,
        "literary_outcome": "UNDETERMINED",
        "blind_independent_human_review": "NOT_PERFORMED",
    }


def historical_blind_packets(prose_by_arm, blind_order):
    """blind_order is an independently shuffled tuple of ORIGINAL modes."""
    if set(prose_by_arm) != set(HISTORICAL_ACTUAL) or (
            len(blind_order) != 3 or set(blind_order) != set(HISTORICAL_ACTUAL)):
        raise ValueError("WF100_V97_ARMS_OR_BLIND_PERMUTATION_INVALID")
    packets, mapping, cards = [], [], []
    for label,arm in zip(BLIND_IDS, blind_order):
        body = prose_by_arm[arm]
        if len(body) != HISTORICAL_ACTUAL[arm]:
            raise ValueError("WF100_V97_ACTUAL_PROSE_NOT_AS_COLD_MANIFEST")
        frozen = freeze_manuscript(prose=body,arm=arm,
                case_id="v97_historical_ferry",requested_chars=HISTORICAL_TARGET)
        # This document alone is given to the evaluator, never its mapping.
        packet = {"format":"wf.writing.blind-original-prose.v100",
                  "blind_id":label,"case":"渡桥送药（原创历史悬念）",
                  "body":body,
                  "review_axes":list(REVIEW_AXES),
                  "independent_review_status":"UNREVIEWED",
                  "method_hidden":True}
        packets.append(packet)
        mapping.append({"blind_id":label,"arm":arm,
                        "body_sha256":frozen["prose_sha256"],
                        "actual_characters":len(body)})
        cards.append(frozen)
    result = compare_equal_length(samples=cards)
    if result["lengths_comparable"]:
        raise ValueError("WF100_V97_IMPROPERLY_LABELED_EQUAL_LENGTH")
    return packets,mapping,result


def xianxia_fairness(cards):
    """Structural length audit only; no literary or cost claims."""
    if len(cards)!=4 or set(x.get("arm") for x in cards)!=set(MODES):
        raise ValueError("WF100_NEW_FOUR_ARMS_REQUIRED")
    result=compare_equal_length(samples=cards)
    result["within_target_10pct"]=all(
       abs(c["actual_characters_including_punctuation"]-NEW_TARGET)
       <=NEW_TARGET*0.10 for c in cards)
    result["eligible_for_equal_length_blind_comparison"]=(
       result["lengths_comparable"] and result["within_target_10pct"])
    result["model_cost_equivalence_verified"]=False
    result["narrative_or_literary_advantage_verified"]=False
    return result
