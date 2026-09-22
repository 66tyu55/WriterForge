# Performance Budget

WriterForge 的目标不是“调用越多越聪明”。V12 增加 Reactive Runtime 后，能力库增长不应线性增加每次写作成本。

## Draft Step
普通逐句创作：
- 只允许 P0 + 被真实 Delta 触发的 P1
- Cost Budget 默认 <= 8
- P2/P3 = 0
- Taste / Story Sense / Evolution = 0
- Scene Craft Contract 已生成时直接复用，不重新跑 Router

## Paragraph Boundary
- P0/P1
- Voice Guard 可触发
- Cost Budget <= 12

## Scene Boundary
- 允许 P2
- Cost Budget <= 24
- Craft Auditor 仍需显式 `craft_review`

## Hard Literary Choice
- 只有确实存在两个以上合法候选，才允许 `literary_taste_compare`
- P2
- 不与整套 Reviewer Board 同时默认启动

## Chapter Boundary
- 允许 Reviewer Board / Reader Review
- Cost Budget <= 32
- Story Sense 只在 `literary_diagnosis / review_conflict` 时启动

## Offline / LEARN / Rewrite / Evolution
- 才允许 P3
- Cost Budget <= 60
- Failure Cluster / Curriculum / Promotion Gate 全部离线

## Reactive 复用

- dependency fingerprint 未变 -> cache hit
- 一处变化 -> 只失效直接依赖节点
- 同 fingerprint 并发 -> single-flight
- candidate 被拒绝 -> zero side effects
- commit idempotent -> one accepted commit

## 自动退化优先级

Runtime/Canon correctness
> Causality
> Memory relevance
> Voice
> Reader simulation
> Targeted Craft
> Taste compare
> Deep stylistic review
> Evolution training

绝不为了“多审一次文笔”牺牲核心连续性，也不允许 Evolution 占用普通创作路径。
