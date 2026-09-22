# Evolution Engine｜小说家能力自我迭代

Evolution Engine 不参与普通正文生成。它是 P3/offline 元系统，负责判断 WriterForge 是否真的学会了新的小说创作能力。

## 不是数值升级

L4 -> L5 不是“经验 +1”，而必须附带新的 Capability Statement：以前做不到什么，现在在陌生小说场景中能稳定做到什么。

软件版本 V12/V13 与作家成熟度 L1-L10 独立。连续多个软件版本可以仍然停留在同一成熟度。

## 闭环

```text
真实创作 / 真实读者 / 回归测试
        ↓
Failure Events
        ↓
Failure Clustering   # 一次偶发失败不创建 Skill
        ↓
Capability Diagnosis
        ↓
Learning Gap
        ↓
Curriculum Designer
        ↓
Scenario Verifier
        ↓
Train / Held-out / Transfer
        ↓
候选 Skill 修改（bounded edit）
        ↓
Fresh evaluation
        ↓
Regression + Transfer + Judge Stability + Runtime
        ↓
Promotion Gate
        ↓
PASS: promote one level
FAIL: archive candidate, keep stable version
```

## Failure Cluster

只有反复出现、具有共同机制的失败才进入升级流程。例如：

- 同一类 `COGNITIVE_LOOP` 连续跨多个场景出现；
- `DialogueCraft` 在不同关系类型中都无法维持 private/public goal gap；
- `NarrativeRestraint` 反复把本应留白的高潮解释掉。

偶发失误记录 Experience Ledger，但不立即修改 Skill。

## Curriculum

训练场景不复用原失败文本。训练集、Held-out、Transfer 必须改变关系、压力、信息结构等表面变量，同时保持底层能力不变。

例如训练的是“潜台词”：
- train：师徒、兄弟、伴侣；
- held-out：敌友、君臣；
- transfer：陌生人错误身份/共同目标但价值冲突。

训练答案不能进入验证输入。

## Promotion Gate

默认至少要求：
- held-out success >= 0.80
- transfer success >= 0.75
- regression preservation >= 0.95
- pairwise judge stability >= 0.90
- 目标失败簇下降 >= 30%
- runtime regression <= 20%

Taste / Story Sense 等主观文学升级还必须有至少一个外部锚点：Beta Reader、真实同类型 Reader Corpus 或人工盲评。

## 小 Skill 联动

Skill 升级改变 capability contract 后，只有直接依赖者标记 `NEEDS_REVALIDATION`。

例：

`CharacterEngine L4 -> L5 (增加 false belief / asymmetric relationship view)`

可能标脏：DialogueCraft、CognitiveMotion、ScenePlanner。
不会自动标脏：ProseRhythm、XuehaiDedup 等无关能力。

如果下游需要上游最低等级而尚未达到，记录 `CAPABILITY_LAG / SKILL_DEBT`，整体成熟度不得晋级。

## Skill Birth / Retirement

新增能力不等于新增 Skill。

候选机制若与现有 Skill 在“诊断对象 + 干预机制 + 失败模式”高度重合，必须升级/合并已有 Skill。

真正不同才允许 Skill Birth。

无效或被替代的 Skill 进入 retired/shadow，可回滚但不进入正常调度。
