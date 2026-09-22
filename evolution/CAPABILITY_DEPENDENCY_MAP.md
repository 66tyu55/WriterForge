# Capability Dependency Map｜小 Skill 联动升级

这张图描述“谁依赖谁”，不伪造当前等级。第一次真实基准测试后才给各 Skill 写入 L1-L10。

## 主要依赖

```text
Character Engine
 ├─> Dialogue Craft
 ├─> Cognitive Motion
 ├─> Scene Planner
 └─> Character Consistency Auditor

Knowledge / Belief Ledger
 ├─> Character Engine
 ├─> Dialogue Craft
 ├─> Suspense / Dramatic Irony
 └─> Cold Reader payload boundary

Reader Engine
 ├─> Literary Taste
 ├─> Page Turn / Ending Craft
 └─> Actual Reader Critic

Craft Engine
 ├─> Craft Auditor
 └─> Story Sense signals

Promise / Motif / Long Memory
 ├─> Motif Return
 ├─> Payoff / Ending Craft
 └─> Long-range Taste / Aftertaste

Literary Taste
 ├─> Rewrite choice
 └─> Major revision candidate selection
```

## 升级传播

上游 Skill 的 `capability contract` 一旦变化：
- direct dependents -> `NEEDS_REVALIDATION`
- 未依赖者 -> 保持 `ACTIVE`
- 若 dependent 声明 `minimum upstream level` 且不满足 -> `CAPABILITY_LAG`

`NEEDS_REVALIDATION` 不等于必须重写 Skill；先用旧实现跑新的兼容测试，仍通过则直接恢复 ACTIVE。

## 示例

Character Engine 新增：
- false belief
- confidence/source-aware knowledge
- asymmetric relationship view

Dialogue Craft 必须重新验证：它是否仍然把角色“真实动机”错误地直接写进对白。

Prose Rhythm 与这个升级无直接依赖，因此不需要重跑。
