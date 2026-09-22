# Craft Assimilation Policy — V13

WriterForge 只吸收可解释、可回归、可按需触发的小说技法机制；不复制外部 Skill 文本，也不把作者表面风格当成能力。

## 已吸收机制族

- `novel-writing` 类：transcript 对白风险、共享知识讲义、隐藏动机过早解释、有效沉默。
- `better-writing` 类：Trust the reader、stating-the-moral / fractal-recap 风险、false-positive caution。
- `Calliope` 类：dialogue collision/turn、psychic distance、prose rhythm、单一 lever 训练。
- `Worldsmith/prose-craft` 类：scene turn、leave after turn、具体细节优先、情绪标签只作审查信号。
- Scene/Sequel：Reaction -> Dilemma -> Decision，防心理原地循环。
- Novel-studio / narrative-craft：Scene/Summary/Omission、Free Indirect Voice、Motif Return。
- Novel-writer skill families：Strategic Reversal、punctuation as performance，只作为低频 technique card。
- Literary skill design：机制重复时合并，不用作者模仿包装成新 Skill。

## V12 新增但不扩 Craft Group

- `narrative_magnification`
- `motif_return`
- `free_indirect_voice`
- `detail_utility`
- `strategic_reversal`
- `punctuation_as_performance`

它们全部进入现有五组；没有新增常驻 Craft Agent。

## 拒绝进入核心

- 纯 AI 词表 / 人类化改写器。
- 每句启动 Reviewer。
- 固定句长、对白率、感官数量。
- “show don't tell”绝对化。
- 剧本媒介规则直接覆盖小说。
- 训练一次成功就宣布 Skill 升级。

## Skill Birth Gate

新机制进入主干前必须说明：
1. 独立诊断对象；
2. 独立干预方式；
3. 独立失败模式；
4. 不与已有 Technique Card 高度重合；
5. 能进入 held-out / transfer / regression 测试。


## V13 吸收

- `jwynia/agent-skills` Endings：吸收“结尾必须可向前追溯、意外与必然同时成立、结尾问题可能需要上游修订”的机制；不复制它的完整 checklist。
- `jwynia/agent-skills` Cliche Transcendence：吸收 Form / Knowledge / Goal / Role 的正交性判断与“先保留 function”原则；拒绝把八步流程变成每次创作固定打卡。
- `jwynia/agent-skills` Reverse Outliner：吸收“从成稿反推实际结构/功能”的思想，并改造成 WriterForge 自己的 Observed Story Auditor。
- `jwynia/agent-skills` Key Moments：只吸收“先定义目标 Reader Experience，再让情节服务它”；拒绝固定类型节拍表。
- `pilcrow` fiction guidance：进一步确认 load-bearing concrete detail / free indirect / reader inference；这些已由 telling_detail + free_indirect_voice + trust_the_reader 覆盖，因此不新建 Skill。

新增唯一 Technique Card：`temporal_reordering`，仍属于 Scene Turn & Rhythm。
