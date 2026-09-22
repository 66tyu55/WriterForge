# Upstream Assimilation Map

WriterForge 不整仓复制任何外部项目。
采用“能力吸收 + 本地接口 + A/B Gate”。

## story-skills
吸收：
- Story/continuity contract 思想
- Deterministic continuity validator
- Promise/Payoff 与 series-level continuity 思路

不照搬：
- 所有文学状态都必须 schema 化
- outline-first 成为唯一写作方式

优先级：
- Continuity contracts: P0/P2
- Series continuity: P3

## novel-creator-skill
吸收：
- 两级检索：廉价候选 -> 精排/去同质
- Checkpoint / Resume
- Regression tests
- 项目级执行器思想

不照搬：
- 每次创作都走重型 RAG/图谱
- 大纲锚点压倒 Discovery/Emergence

优先级：
- Cheap candidate retrieval: P1
- Deep rerank / graph expansion: P2/P3

## better-writing
吸收：
- Voice > mechanical cleanliness
- Voice drift measurement
- False-positive-first editing
- Core skill 短小，references lazy-load

不照搬：
- AI-pattern detection 变成绝对禁词
- 命中模式就自动重写

优先级：
- Voice fingerprint: P1
- Deep prose audit: P2

## NovelWritingAgent
吸收：
- Memory budget
- Canon patch
- Reviewer board / meta-review 思路
- Long-horizon compression

不照搬：
- 多 Reviewer 每一步都常驻
- 所有判断都依赖多 Agent

优先级：
- Memory select: P1
- Reviewer board: P2
- Compression: P3

## AuthorAgent
吸收：
- 项目生命周期
- 不同 Reviewer 的输入隔离
- Experience / revision loop

不照搬：
- 过宽的出版/营销能力进入核心写作 Runtime

优先级：
- Reviewer isolation: P2
- Publishing workflow: 外置，不进 Kernel

## 统一原则

任何外部能力进入 WriterForge 主干前必须满足：

1. 明确解决一个现有短板；
2. 可放入 P0/P1/P2/P3；
3. 有缓存或触发条件；
4. A/B 测试不降低核心文学指标；
5. 延迟回归不超过预算；
6. 可撤销。
