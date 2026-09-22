# WriterForge V12 — Reactive Evolution + Literary Taste

V12 的目标：让 WriterForge 在不臃肿的前提下，开始具备“小说家级自我成长”能力。

## 新增主轴

1. **Reactive Skill Runtime**：Skill 不一直调用。场景开始选择技法，依赖未变就复用；只重算真正被改动影响的节点；相同并发请求 single-flight；长期状态只允许一次 Commit。
2. **Evolution Engine**：从真实失败簇发现能力缺口，自动设计 Train/Held-out/Transfer 小说训练场景，候选 Skill 只有通过迁移、回归、Judge 稳定性和运行成本门槛才晋级。
3. **Literary Taste Engine**：多个版本都正确时，用 pairwise 文学选择而不是绝对分数；A/B 顺序交换后翻票的 Judge 结果不得学习。
4. **Story Sense Router**：不同时运行所有 Reviewer，只抓当前 dominant literary problem。
5. **Craft Engine 增强但不扩组**：新增 Scene/Summary/Omission、Motif Return、Free Indirect Voice、Detail Utility、Strategic Reversal、Punctuation-as-Performance，全部作为原有五组内部 Technique Card。

## 仍然保持

- LEARN / WRITE 严格隔离。
- Reader-First 学原著。
- Actual Reader 评论按主类型隔离。
- Canon / Character / Knowledge / Promise / Memory / Causality。
- Craft Router 每次最多两组；Craft Auditor 不逐句常驻。
- AI 自己写的正文永远不能直接变成 Source Evidence。

## 核心运行句

`No Change -> No Recompute`

`One Change -> Only Dependents Recompute`

`Same Request -> One Execution`

`Rejected Candidate -> Zero Side Effects`

`Accepted Candidate -> One Commit`

## 成熟度

软件版本与作家成熟度分离：`V12 != L12`。

Writer Maturity 只有 L1-L10，而且只有出现可迁移的能力质变才允许晋级。

详见：
- `evolution/EVOLUTION_ENGINE.md`
- `evolution/WRITER_MATURITY_LEVELS.md`
- `taste/LITERARY_TASTE_ENGINE.md`
- `reactive/REACTIVE_SKILL_RUNTIME.md`
- `story_sense/STORY_SENSE.md`
