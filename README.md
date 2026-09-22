# WriterForge V13 — Novelist Growth Without Skill Bloat

WriterForge 是面向**长篇小说创作**的作家系统，不是通用润色器。V13 继续沿用 LEARN / WRITE 隔离、Reader-First、Canon/Character/Promise/Memory、Reactive Skill Runtime、Literary Taste 与 Evolution Engine，并补上三个成熟小说家经常依赖、但普通 AI 写作系统缺失的能力。

## V13 三个强化

### 1. Ending Backtrace

结尾不在最后几页单独修。系统从结尾向前追溯：

`payoff -> setup -> character choice -> central question -> irreversible change`

检查“结局从哪里长出来”。突然出现的解法、角色成长与高潮无关、末尾继续扩大新谜题、主题演讲式解释都会形成明确诊断，但系统不会替作者机械选择结局。

### 2. Orthogonal Originality

反俗套不是简单把 trope 反过来，也不是换皮。一个故事元素从 `form / knowledge / goal / role` 四个轴观察；只换名字或职业、但仍然知道主线、服务主角、承担同一套路角色，属于 `COSMETIC_SWAP`。

原创性必须同时保护已有 story function，避免“为了新奇把故事功能拆掉”。

### 3. Observed Story / Reverse Outline

WriterForge 不再只相信计划写了什么。章节/卷完成后，可以从**已接受正文**反向抽取每个场景实际完成的功能、人物选择、状态变化与读者效果，再和 planned story 比较。

持续偏离可以成为 Emergence Proposal；没有功能、选择、状态变化或读者效果的场景才进入强审查。安静场景不会因为“没发生大事”被误杀。

## Craft 仍只有五组

1. Dialogue Action
2. Perception & Description
3. Cognitive Motion
4. Narrative Restraint
5. Scene Turn & Rhythm

V13 只在第 5 组增加 `temporal_reordering`：非线性时间顺序必须提升理解、预期或情绪压力，并保持因果可重建。没有新增常驻 Craft Agent。

## Reactive 规则

`No Change -> No Recompute`

`One Change -> Only Dependents Recompute`

`Same Request -> One Execution`

`Rejected Candidate -> Zero Side Effects`

`Accepted Candidate -> One Commit`

## Evolution

自我升级仍然遵守：

`Failure Cluster -> Diagnosis -> Curriculum -> Held-out -> Transfer -> Regression -> Promotion Gate`

V13 增加一条重要证据来源：**Observed Story**。系统必须研究自己实际写出来的小说，而不是只研究计划和 Reviewer 的意见。

软件版本与作家成熟度继续分离：`V13 != L13`。Writer Maturity 仍然只有 L1-L10。

## Test

`python -m unittest discover -s tests -q`

当前：**72 / 72 passed**。
