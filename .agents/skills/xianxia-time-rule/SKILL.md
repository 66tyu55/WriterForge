---
name: xianxia-time-rule
description: A narrow independent time-rule skill for a fictional cultivation world. Uses explicit reference frame, units, per-actor subjective clock, observed training duration, era uncertainty, author-chosen breakthrough and unchanged offscreen world time; test with one random author character and a single time multiplier ablation.
compatibility: Python 3.10+, no extra dependencies; optional pinned local Qwen model experiment via GitHub Actions.
metadata:
  wf-skill-id: xianxia-time-rule
  wf-lifecycle: shadow
  wf-version: "0.3"
---

# 修仙时间：从 V1 的“数字表”改成 V2 可执行独立规则

**上一版 0.1 已经通过机械单元测试，但参数设计有明显缺陷，不能据此宣称它影响了真实小说。** 在 V2 中，`scripts/time_kernel.py` 仅用于历史回归；生产候选只考虑 `scripts/time_v2.py`，且仍处于 SHADOW，不接入 WF 的正式作者。

## 对参数的五个不可省略要求

1. **每项参数都必须具名且有单位。** `world_clock.hour` 是全世界统一的时刻（单位：世界小时），`actors.P001.age_subjective_hours` 是单一人物身体经历小时，`cultivation_subjective_hours` 是有记录的实修主观小时，绝不是宗门等级或“写作评分”。
2. **必须给出参考系和换算式。** `time_frames.cave={numerator:3,denominator:1}` 意味一个世界小时在洞府经历三个主观小时。运算使用精确有理数（Fraction），不能用小数浮点臆造“+0.145”。**参数只对时间起作用，不决定人物情绪、战力或政治制度。**
3. **每个人的时间都必须同时前进。** 世界推进一次，洞中 P001 和洞外守夜人 N001 都老去各自经历的时间；N001 不在主角视角内，不能因此停滞。若没有证据记录其活动，就把活动标记未知，不擅自断言对方在修炼。
4. **实修时间与突破结果分开。** 案例特设“需要至少 20 个主观实修小时才有资格成功尝试下一境”，它不是普适修仙法则。满足资格不会自动突破，仍可失败、放弃、推迟，也不能自动成功救洪水中的村庄。
5. **纪元史不是已知准确日期。** `era_history.past` 只表示“听说过一个过去纪元”；没有可靠纪元换算证据时，`past_exact_hours=null`，引用它不改变现在的时钟，更不能编造古人真实年龄。

每个时间字段的更新规则由 `time_v2.parameter_dictionary()` 显式给出。角色种族、时间流速、门槛和经历时间可以分别修改；**一次实验只能修改预注册的一项**，其他保持字节结构一致。数据出处是 `provenance.calibration=scenario_assumption`：表示本次原创世界的明示设定，并非从原著中已学到的真理。

## 真实写作试验：随机角色开启原创玄幻故事

随机种子 `20261113` 已在 V1 对角色身份做过一次抽签，选中“谨慎却倔强的灵田佃户”，不得为获得好看的结果重新抽签。河谷将在 8 世界小时后迎来洪水；主角在洞中闭关 6 世界小时；洞外守夜人继续修堤，不知主角是谁。主角起初已有 6 主观实修小时，至少 20 小时才具备下一境的突破尝试资格，而护堤术需要下一境，且到洪水抵达前才有施用资格。

冻结三组：
- 无参数规则的普通写作基线：相同随机角色、洪水、六小时闭关。
- V2 `rate1`：洞府 1:1；结束后实修累计 12 小时，**没有成功突破的时间资格**。
- V2 `rate3`：洞府 3:1；结束后实修累计 24 小时，**有资格尝试，可能仍失败**。

两种 V2 版本的唯一差异是 `time_frames.cave.numerator` 从 1 改到 3。世界小时、截止时刻、人数、目标、突破门槛、人物性格、守夜人都不变。请注意：这项实验只证明参数**有否实际约束可行行动、改变写作**，不是恢复《武动乾坤》或任何真实小说，也不是模型权重训练。

代码级参考：

```python
import json
from pathlib import Path
from time_v2 import replay, time_comparison
world = json.loads(Path("experiments/wf_xianxia_time_v2_frozen_world_20261113.json").read_text())
events = [
    {"kind":"advance","world_hours":6,
     "activities":{"P001":"cultivate","N001":"work"}},
    {"kind":"attempt","actor_id":"P001","outcome":"success"},
    {"kind":"use_technique","actor_id":"P001"}
]
out = time_comparison(world["rate1"],world["rate3"],events)
assert out["original"]["accepted"] is False
assert out["altered"]["accepted"] is True
```

这种计算证实参数对**资格**存在影响，但依然不能证明小说正文真正遵守了规则。因此真实作者实验还必须记录完整原始模型输出、时间事件表、错误和三组间真实叙述差别；若小说写“闭关十年”而事件表只写“六小时”，**时间核算通过也应判正文不合格**，不能偷偷修正文。

## 验收和停止

`tests/test_wf_xianxia_time_v2.py` 覆盖单参数差异、并发人物时钟、未来不停止、突破可失败、非修炼活动不加功、精确分数、未知纪元、无单位拒绝等；`tests/test_wf_xianxia_time_v2_writer_preflight.py` 冻结真实模型输入。实际生成只通过 `experiments/wf_xianxia_time_v2_real_writer_once.py` 一次性离线开源模型测试，没有重复提示词刷分、不调用付费 API、不碰现有小说原著、学海、R2 或 Canon。

**双闸门**：A. 独立时间引擎对改动参数作出不同的判决；B. 同模型同故事三组真实正文体现合理差别，且没有新增加的因果/时间矛盾。A 通过但 B 失败意味着**参数是可计算的，但尚未成为写作规则**。如果 B 失败，停止本轮，说明原因而不是继续堆模块。


## 2026-11-13 real writer checkpoint — STOP / NOT PROMOTED

The standalone numerical time V2 engine **PASS** (35/35 offline tests including old v1 regression); all five actual pinned local Qwen author replies were saved. The first three raw-JSON writer arms produced only a frozen opening action, not actual choices. The final two compact computed-window prose arms produced longer 878/744-character scenes, but did not demonstrate that changing one time-rate parameter caused a valid story action to change. The ×3 story also attributed unsupported knowledge of the hidden actor's cultivation status to an offscreen guard. **Rule-to-prose transfer FAIL.**

Do NOT represent this as learned novel-writing capability, release into WF Canon, or automatically retry. See `docs/WF_XIANXIA_TIME_V2_FINAL_RESULT_20261113.md`. World, subjective actor clocks, eligibility remain valid as independent time constraints; human/model choosing an action and respecting knowledge/causality requires a separate integration with existing WF narrative state. No integration is authorized by this experiment.


## Additional authorized test-first corrections — current time V2.1 (2026-11-13)

User explicitly resumed experiments after the historical river-story STOP. This is a NEW random-role case, not a replay of the frozen 20261113 model answers.

- **Physical reference-frame movement:** `time_v2.apply_event` now accepts `cross_frame` with `actor_id`, `to_frame`, `origin_world_hours`, `destination_world_hours`, and other actors' independent observed `activities`. Movement must spend positive world time; the moving actor ages according to both old and new time frame rates and earns **zero** cultivation credit while moving. All other actors advance with that **same** global world duration at their own time rates. No instant teleport or outside NPC clock freeze.
- **Independent current-frame parameter:** `actors.*.frame` has its own update semantics, changed only after a paid crossing. Future events use the new local rate; otherwise the old cave multiplier would incorrectly persist.
- **Portable author-facing time conditions:** `time_bridge.time_window` derives the *current* frame and ratio, necessary world hours of uninterrupted future cultivation and whether the deadline still permits satisfying a time threshold. `concise_context` no longer hardcodes prior river/guard story nouns; an optional event/person label comes from the current writer's task.
- **Commit-order clock consistency:** an accepted author action must be replayed BEFORE constructing the next author context. A rejected action does not advance the world. Earlier one-shot model results are historical evidence and **were not re-run** after this repair.

**Tests first, fixes second:** actual GitHub Actions failures were deliberately recorded for missing cross-frame support (8 bad cases), hardcoded story labels (1 case), and stale post-action clock (1 case). Final new targeted run: **56/56 PASS** including 11 legacy regression cases, [Actions #43397382727](https://github.com/66tyu55/WriterForge/actions/runs/43397382727).

**Actual new fictional writer run:** [Actions #43396159475](https://github.com/66tyu55/WriterForge/actions/runs/43396159475) used Qwen2.5-3B, seed 20261114, a new random mountain-bell keeper, 2 different cave time rates, one independent decision + one original prose reply per arm. Both chose a normal one-hour alarm and correctly passed time gating; neither demonstrated a differential personality/plot effect. The 1:1 novel became severely repetitive; the 3:1 novel introduced additional movements with no corresponding clock records. **Narrative temporal consistency FAIL/UNVERIFIED and no literary gain demonstrated.** Full report: `docs/WF_XIANXIA_TIME_V2_PARAMETER_REPAIR_AND_REAL_STORY_20261113.md`.

The time kernel remains **SHADOW**, does not generate or repair a story, and must not auto-promote to official WF writing. Source-original literary training and world-logic inverse remain separate unsolved goals. If a future trial occurs, it must make every author-originated action commit its time cost before subsequent prose, without hardcoding choices or borrowing omniscient NPC knowledge.


## V3: Original-source parameter learning — NOT COMPLETE / DO NOT PROMOTE

User correction: V1/V2 were only a narrow, hardcoded time-rule calculator plus some author tests. They were **not trained on complete time behavior in original xianxia novels**. Do not claim `V2 PASS` means a finished Skill. V2 remains a mechanical reference.

A private study of the user's 13 whole novel text files (150,798,245 raw bytes) produced 114,877 unreviewed candidate time expressions. A weak source-driven recognizer trained on 1,162 weakly labelled examples from 10 novels performed only **13/28** on 28 manually checked held-out probes from three other novels; the method FAILED and that result is preserved. Assistant-linked 33 original excerpts spanning 13 novels now provide at least one source-anchored comparison for each of 18 independent time semantics, but six semantics have only one example and no independent reviewer has checked them. **This is an early curriculum, not complete training.**

Use `scripts/time_parameters_v3.py` for source-local candidate evidence. Its open-world `DOMAINS` distinguish world elapsed time, reader reveal order, story event order, subjective/biological age, lifespan ceiling, cultivation exposure, cultivation efficiency, physical local time rate, temporal-zone admission quotas, realm time prerequisites, journey duration, waiting deadline, recurrence, epoch, offscreen overlap and epistemic uncertainty. The `frame_access_schedule` slot was learned as necessary after reading a complete novel passage that combines an unusual training-time space with limited visits per world day. An entry quota **is not** itself a number of awarded cultivation hours. An experienced dream year **is not** automatically a biological-aging year. Never interpret a cultivation effect comparison as time dilation.

Source evidence must preserve exact byte offsets, unit and numeric qualifier. Semantic review defaults to NOT_REVIEWED; a literal match is only evidence that wording exists, not that a causal time rule is true. No original novel text, private source mapping or model weights from weak labels may enter the public repository or production author. In the absence of independent confirmation, do not replace UNKNOWN with invented dates, ratios, lifespan or character experience.

Actual progress and strict training gaps: `docs/WF_TIME_V3_ORIGINAL_CORPUS_TRAINING_STATUS_20261113.md`. V3 tests run separately from legacy V1/V2 in GitHub Actions; CI validation of synthetic encoding and quotas is a precondition, **not** a substitute for chapter-by-chapter original-source learning and held-out fiction inference.

**Gate remains SHADOW / NOT READY**. Never mark this as a finished trained time Skill until all parameter meanings survive independent source-based reconstruction and action/state transitions on unseen passages.


## V4: Event-first original parameter localization (source-bound, not yet full training)

**Finding from user-owned original stories**: pre-assigning 18 abstract time slots and scanning for time words loses what a parameter *does* and whom it affects. The correct discovery unit is a **real story change / hard outcome question**, not a keyword count or fixed type name.

Use `scripts/event_first_time_locator.py`, not an LLM-generated number vector, when deciding whether a proposed temporal constraint belongs in the experiment:

1. Read a contiguous segment of real original text. Pin the complete original SHA, the exact two-chapter window and each cited byte slice. If a quote occurs only outside those chapters, it cannot be used.
2. Record each candidate as a **local, owner-specific, exact-source claim**. A reported cost, forecast, plan and physical observation are not interchangeable. Exact quantities need an original numeral token that matches the normalized rational value; even a byte-perfect source quote cannot justify inserting an arbitrary numeric value.
3. Freeze a question about the original **event or consequence** before testing parameters. Only then run representational deletion: remove each candidate source fact, answer again and flag where the result becomes UNKNOWN. This shows the fact is necessary **for that question**, not that it is a universal genre law or a verified cause.
4. Do not discard facts unused by a few questions; an actor's age, side character or alternate outcome may matter in later event questions. Missing input is UNKNOWN, conflicting reports stay separately attributed, and uncertainty never turns into an exact date or guaranteed death.
5. Change a single parameter and check that it affects an externally meaningful action/condition while preserving other actors' clocks, resource costs and downstream state. Never force an author choice or future plot simply to make a numeric test pass.

**Actual private two-original pilot** (not CI gold): first two consecutive chapters of two different xianxia works; 17 source-located anchors, 17 candidate facts, 7 preregistered event questions, 12 facts needed in those questions and 5 held for additional questions. The first version accepted a valid anchor with a forged numeric value; this negative test failed as intended and was repaired with `numeric_literal` source token checks. Private original-specific retest: 13/13 current local checks pass. Public source-free CI: **77/77 focused mechanics**. This is an event-first source-localization pilot, **NOT** an independently reviewed original novel decoder, full-book training or literary uplift. See `docs/WF_TIME_EVENT_FIRST_PARAMETER_LOCALIZATION_20261113.md`.

**Promotion gate remains closed.** Do not wire this to production WF as a mastered original-novel Skill. The 13 original novels and previous 13/28 weak-label failure record remain in the existing V3 study; no new model-weight training or private original upload is performed by V4.
