# WriterForge V8 Priority Model

## P0 — 常驻，必须极轻
每个写作步骤都可以执行，但必须是确定性/缓存级成本。

- Runtime Guard
- Snapshot Guard
- Delta Detector
- Quick Continuity

**禁止调用 LLM Reviewer。**

## P1 — 响应式
只有依赖字段真实变化才执行。

- Xuehai Retrieval
- Voice Guard
- Memory Recall
- Promise Watch

普通句子没有相关状态变化时，P1 不执行。

## P2 — 边界
只在 Scene / Chapter 边界执行。

- Deep Continuity
- Causality Audit
- Character Audit
- Reader Experience
- Reviewer Board

绝不每句调用。

## P3 — 离线/重型
只在 LEARN、Checkpoint、大修或用户明确要求时执行。

- Full Book Audit
- Cross-work Compare
- Memory Compression
- Structural Rewrite Impact

## 目标

吸收外部成熟项目时，能力必须先被放入一个 Priority。
没有 Priority 的能力不得接入主干。
