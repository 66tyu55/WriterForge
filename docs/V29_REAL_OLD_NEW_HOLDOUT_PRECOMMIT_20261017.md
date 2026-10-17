# WriterForge V29 · 新版究竟进步了吗？旧WF vs 语义WF全新题双稿盲测（预注册 2026-10-17）

## 固定前提出发

历史V28三道原创第一章，旧WF增强相对无技能 +17.6/-7.4/+13.8（三轮平均+8.0），完全不足证明文学稳定性；它们用于提出机制语义适配缺陷，**绝不可再次用于新机制升级验收**。

V29新增不与上述六题重合的题目池，固定 `writerforge/v29_fresh_holdout.py` 的种子和题目SHA，从五道场景按 SHA 抽三道。无成绩前即提交到 main，成功/失败不得事后换题。题材覆盖江湖人情、空间因果、有限认知等（见源文件）。

三个全新题目都使用同一私有R2已核验的《武动乾坤》第3章首个真实连续窗口，来源SHA `96b6363d40be7b99d5635af1346da0c04e44556fc06e32d1aab04e419e4942fa`；不解锁原著正式第二课程窗口。模型 Planner/Critic DeepSeek V4 Flash, Writer GLM-5.3，经验证的低推理网关配置。

每道题：旧Planner按原协议选最多2个HOST预设技巧，新Planner必须给出原段落12-48字的精确证据、人物认知、局部因果、新题目适配、误用风险，并且可以弃权。只将白名单技巧ID和HOST操作送到两份原创新稿；评审模型只见匿名 A/B 正文、同一任务，**不见来源、提示协议标签、实验预期**。

每题最多7次模型调用（两次Planner、两次Writer、最多两次对称修订Writer、一次Critic）；共享预留输出令牌上限50k，预定义预算 `4200/7700/6500`。两稿长度差大于15%时必须拒评，或两组各允许一次公平对称修订，绝不截断正文伪造成绩。正文不持久保存，只有HASH和有限摘要进入私有 R2。

## 预注册判定标准与严谨限制

旧vs新单题的真实模型分项均分差记为 **新版减旧版**，不是与不同题目历史成绩相减。

- 三个真实有效的双稿对照后，新版若至少两次胜出、第三次未大幅退化，可算**探索性正向信号**，但不可称文学能力已经被证明。审核报告中的更严格版本要求三题完整、至少2正0负才输出 `MODEL_SUGGESTS_IMPROVEMENT_NOT_PROVEN`；含负例将输出保守混合/不足。
- 若三个有效对照中至少两次新版下降，记 **回退信号**；不得将模型评审的单次波动视为严谨的统计因果实验。
- 新语义审查如弃权、源span杜撰、网关失败、稿长不合格，则该题 **UNSCORED**，不能补数或按0分算。
- 新旧如果选出同样技巧列表，稿件分数差主要受到随机生成影响，**不得称机制选择能力升级**。
- 目前评审模型与规划模型同为Flash，并非两名独立真人；没有保存可人审的全文，单次分数不构成真实文学提升证明。底层适配是否有效须用新的、可独立逐句复评的加密稿和盲审另测。

真实模型工作流（一次性，不随普通代码push重复扣费）：[#39006533808](https://github.com/66tyu55/WriterForge/actions/runs/39006533808)。R2结果写入 `writerforge/v1/reverse-craft/wudongqiankun/v29-old-vs-semantic-fresh-holdout/` 独立新前缀，旧V28历史、原稿候选及古杉负例一律不可变保存。最终审计 `scripts/audit_v29_old_new_holdout.py` 无需模型再次推理。

## 本轮待填真实结果

此文创建时工作流已提交且正在运行；不能预测新版得分。如果最后三题不足3个可评分样本，必须说明未满足真正的“3次对照”验收而保留部分结果；用户批准继续迭代，但不能以大量重试刷出正向结论。

正式文学门闩仍为 `NOT_PASSED`、第二窗口 `LOCKED`；不自动提升新核心或修改GLM模型权重。


## 第一次真实测试的核验结果（在补测之前保留）

[第一次 3 任务 Actions #39006533808](https://github.com/66tyu55/WriterForge/actions/runs/39006533808) 完成、后审计 success，但只获得**1个有效文学双稿模型评分**：

- `bridge_debt` 石桥旧债：旧WF **85.0**、新语义WF **92.8**、差 **+7.8**；五维新版减旧版分别 perception+7/causality+7/information+8/continuity+8/language+9。新旧机制**确实变化**：旧 `GOAL_FILTERS_ATTENTION+COST_VISIBLE_IN_ACTION`，新 `GOAL_FILTERS_ATTENTION+WITHHOLD_CAUSE_SHOW_CLUE`。稿长1238/1318字符，5次模型请求；私有R2完成SHA `8368176072491c04fb17dba6fa80d3590c9106a9fd3c43c7552e629da467d651`。这是一个鼓舞性的单例，但非统计性因果证明。
- `desert_well` 沙漠旧井：生成并做过双边各一次修订，但最终稿长仍>15%，不能进入Critic阶段，按规则记 **UNSCORABLE**，非文学负分；失败R2 SHA `fac3bb0a6c64d7a80ff00543eb916edd45f909550891e1e69c31abe582bd73fc`，6次模型调用。
- `lantern_town` 春汛灯牌：同样完成两次Writer修订，但稿长仍不合格，非文学负分；失败R2 SHA `6ec824bdbd3c368424ec8efa7baad5bbc1eb1427f0cc6d05da24df08f8b562c2`，6次模型调用。

原一次性R2审计返回 `valid_graded_scenarios=1`、`overall_status=INSUFFICIENT_OR_MIXED_MODEL_EVIDENCE`，摘要SHA `4747ac2ef06513f497d65dfdb0eb64b30acbc325a3a11bf4cbcf032eba9a0f13`，没把缺成绩的2题凑成0或90。**实际总17次模型调用**，仅首题有文学评分。严格不能说WF整体已提高。

### 技术原因与版本化有限补测

对双边等长策略进行了非文学分数导向的工程修复：若再出现稿长问题，内部`LengthUnscorable`只保存各自修订前后长度和最终相对差，绝不写文学稿全文或虚假评语。对称编辑器现在分别告知**自己那稿**的字符数、与共同1080字符目标的增减差和相同有效区间，不会看到另一稿长度和文本。默认 old-vs-new 对照源、语义证据门槛、两稿批评及之前真实R2记录均未修改。

一次性 [仅失败两slot的有限补测 #39007227522](https://github.com/66tyu55/WriterForge/actions/runs/39007227522) 新增独立R2协议 `v29-sourceblind-old-vs-semantic-two-arm-length-feedback-recovery`，只对原未评分的 slot1/2，绝不重复 slot0。两组之间仍公平，**但 slot0与slot1/2的篇幅修订协议可能不同**，后审计会明确标明不能当作三组完全同协议的严格因果实验。补测不得覆盖首轮任何结果，最终以真实R2 fresh GET为准。
