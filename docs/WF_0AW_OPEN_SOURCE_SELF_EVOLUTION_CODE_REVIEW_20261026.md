# WriterForge 0.AW｜StoryDaemon、SI2CA、GEPA 源码核验（2026-10-26）

只研究并评估可迁移机制；不是新文学实写验收。开发分支仅 refactor-unified-scene-delivery-audit。**禁止自动用评分决定小说情节、删除正文、把假设写入 Canon。**

## 1. 固定的第三方源码和许可

**StoryDaemon**：EdwardAThomson/StoryDaemon @ 4b57f496f01f25923062a6b93700f94169463ab9（2026-10-17）。
- [rolling horizon](https://github.com/EdwardAThomson/StoryDaemon/blob/4b57f496f01f25923062a6b93700f94169463ab9/novel_agent/plot/manager.py)：PlotOutlineManager.revise_horizon 先生成下一组候选，再标旧 pending 为 abandoned；completed/in-progress 保留。但是先保存 outline 再 add_beats，是两次写入，不是跨文件强原子事务。
- [writer_context](https://github.com/EdwardAThomson/StoryDaemon/blob/4b57f496f01f25923062a6b93700f94169463ab9/novel_agent/agent/writer_context.py)：最近两场实际全篇 + 更早三场摘要。若源文件不存在就回退摘要，这一点不能让 WF 冒充真实原文。
- [agent](https://github.com/EdwardAThomson/StoryDaemon/blob/4b57f496f01f25923062a6b93700f94169463ab9/novel_agent/agent/agent.py)：_maybe_rewrite_for_tension 自动依据 LLM 张力目标决定改写/采用；_verify_beat_execution 发生异常时默认 True。对 WF 文学作者主权、来源真伪不适合照搬。
- 许可注意：README 和 setup.py 声称 MIT，但该 SHA 仓库根目录找不到 LICENSE，直接 /LICENSE 读取亦为 404。补齐权利核查前**不复制第三方代码**。

**SI2CA**：Self-Improving-Coding-Agents/SI2CA @ e750e3512e4368e4e6a3d3a7392a73dc50bad12a（2026-10-16）；已核实根目录 Apache-2.0 LICENSE。
- [discovered](https://github.com/Self-Improving-Coding-Agents/SI2CA/blob/e750e3512e4368e4e6a3d3a7392a73dc50bad12a/si2ca/strategies/discovered.py)：前几个修改类动作窗口使用 K=2，随后走单候选；不是小说文学分支的证明。
- [runtime strategy](https://github.com/Self-Improving-Coding-Agents/SI2CA/blob/e750e3512e4368e4e6a3d3a7392a73dc50bad12a/si2ca/runtime/strategy.py)：Strategy.plan(ctx) 在抽样前决定候选数；select(ctx,cands,judge) 决定继续保留哪个。此接口不能“看过第一稿才追加第二稿”，不得想当然说支持。
- [search](https://github.com/Self-Improving-Coding-Agents/SI2CA/blob/e750e3512e4368e4e6a3d3a7392a73dc50bad12a/si2ca/search.py)：要求完整可比的 192 项编程任务、相同 harness、context audit 后才给出 promotion 建议；本身不启动 agent，不部署结果。
- [Proposal](https://github.com/Self-Improving-Coding-Agents/SI2CA/blob/e750e3512e4368e4e6a3d3a7392a73dc50bad12a/skills/Proposal.md) / [Recorder](https://github.com/Self-Improving-Coding-Agents/SI2CA/blob/e750e3512e4368e4e6a3d3a7392a73dc50bad12a/skills/Recorder.md)：提议、执行评估和记录各司其职；按真实运行日志/调用量区分无触发、无改动、失败、有效。不能自动训练 WF 小说模型。

**GEPA**：gepa-ai/gepa @ d7918ba2f382d5d0652c10814bb278c1c7ffa7c3（2026-10-26）；已核实根目录 MIT LICENSE。
- [API](https://github.com/gepa-ai/gepa/blob/d7918ba2f382d5d0652c10814bb278c1c7ffa7c3/src/gepa/api.py)：文本组件、完整轨迹、反思变异、合并以及 Pareto 前沿。
- [engine](https://github.com/gepa-ai/gepa/blob/d7918ba2f382d5d0652c10814bb278c1c7ffa7c3/src/gepa/core/engine.py)：_add_evaluated_program 维护验证集表现；_run_reflective_batch 分离条件通过、候选选择、完整验证与拒绝原因；持久化 run_dir 可以恢复。**这些只是优化文字参数的工程机制；绝不能证明某个文学评价函数正确。**

## 2. WF 已有模块的对应点及实际优劣

| 外部概念 | WF 原生实现 | 适合吸收的部分 | 必须拒绝 |
| --- | --- | --- | --- |
| StoryDaemon 滚动未来 | writerforge/v98_rolling_causal_planner.py + writing_assist.py 的 G 开关 | 同作者根据已写原文重新选 next beat，计划先成为未接受候选 | 用张力评分自动决定人物情节、以摘要冒充精确来源、删除 V119 回滚 |
| SI2CA 分叉策略 | V26 两种候选、V98 下一步、V119 AI 决定何时回头 | 可计费的候选数、真实作者选择、是否真正改变决定的原始证据 | 系统用一个文学百分制选择“最优”剧情或主机自动删稿 |
| GEPA Pareto | 历史 A/B provider wire SHA + 不同题材审阅 | 多维保留候选机制，固定留出题，完整失败原因，评委引句真实核对 | 根据同家族评委+1.5 就自动升级 WF、修改 Canon 或模型权重 |

**保护作者主权的界线**：第三方库只能启发 WF 如何提供上下文、安排构思选择、保留候选与回滚。小说正文、人物命运、删改内容及是否认可由实际写作 AI 决定；正式采纳仍需用户/作者确认。叙事记忆只有 NarrativeCore，事实要源可追溯。

## 3. 真实《夜阀》证据决定下一轮方向

- [旧 G 对 G+V98（run #40323596997）](https://github.com/66tyu55/WriterForge/actions/runs/40323596997)：同题同模型同源五段；A 79.0、B 75.5（同模型家族两序评委均值，不能确证）；B 逐段重规划两次，后两次因为 trace review-only 跳过。
- [旧 B 对 B+（run #40328385610）](https://github.com/66tyu55/WriterForge/actions/runs/40328385610)：冻结真正作者前 3 段，B+ 将两次原本跳过的滚动构思放回作者手中。原 B 均分 74.5，B+ 76.0，逆序不稳定，额外模型成本明确；不能宣称普适文学提升。
- 后续现有源码已实现签名先前正文窗口（V98 prepare_replan_instructions），为更早已发生动作提供字节来源；**它是否真的减少重复、提高文学表现还要新的独立类型验证**。不能重复 0.AQ 六段、旧十类原稿或 15 章训练。

## 4. 真正值得投入的最小改进，而不是接入重型自我进化框架

1. **P0（小说写作）**：沿用现有 V98，保证近段真实正文的来源 SHA 可核对；模型从已经写出的角色行动出发重新构思，允许安静、留白、有限认知。不要新增“禁止重复动作”的检查词表。
2. **P1（选择式创作）**：参考 SI2CA 的“何时、几个候选、如何选择”的职责分离，但内容选择来自**原写作模型本身**。原 V26/V119 先保持无损。额外模型成本与真实触发率必须记录；无新选择不制造成功证据。
3. **P2（工程自优化）**：参考 GEPA 的多目标对照，只为 WF 的辅助上下文供应、预算路由、回滚事务生成候选改进；先在离线不同文本/题材 A/B 验收，再决定是否合并。不能把同族评委评分自动当文学奖惩。

实验应先冻结模型、文学任务、已有前文和可比预算；保存每一份原始 provider wire、正文 SHA、实际重规划触发与选择、文本长度、失败原因、盲评原句及评委引句是否真的出现在对应稿件中。任何 source/因果问题均不能用高文学评分冲抵。未做人类或跨类型独立质量评审，一律标记文学提升 **UNPROVEN**。

## 5. 本次处置清单

- 只做源码阅读与本份来源冻结说明；**尚未导入外部依赖，也没有做新付费模型训练/小说生成**。
- StoryDaemon 缺 LICENSE 独立文件，不复制实现；SI2CA/GEPA 虽有 Apache/MIT 许可也没有嵌入其库。
- 不更改 main、Railway、用户 R2 原著、正式 Canon、V26/V98/V119 的所有权，不新增第二叙事记忆。
- 本份材料不构成文学质量已提升的声称；唯一可信下一步是验证当前较完整的真实正文窗口能否让作者选出更有因果推进力、少重复的新段落。
