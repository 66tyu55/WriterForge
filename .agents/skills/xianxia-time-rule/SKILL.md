---
name: xianxia-time-rule
description: A narrow independent time-rule skill for a fictional cultivation world. Uses explicit reference frame, units, per-actor subjective clock, observed training duration, era uncertainty, author-chosen breakthrough and unchanged offscreen world time; test with one random author character and a single time multiplier ablation.
compatibility: Python 3.10+, no extra dependencies; optional pinned local Qwen model experiment via GitHub Actions.
metadata:
  wf-skill-id: xianxia-time-rule
  wf-lifecycle: shadow
  wf-version: "0.2"
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
