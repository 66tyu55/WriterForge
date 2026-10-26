# WriterForge 0.AU｜让 G 自己根据已写正文滚动构思（2026-10-26）

唯一分支：`refactor-unified-scene-delivery-audit`；不改 main、Railway、R2 用户作品、Canon 或第二叙事记忆主人。不让 WF 写文学正文或给作者艺术评分。

## 真实基线与缺陷

已保存真实 [0.AQ 六段 DeepSeek 写作 #40264287305](https://github.com/66tyu55/WriterForge/actions/runs/40264287305) 共2269字符，SHA256 `d1b86f2b6430b80bdb70df70199b9644e0a0b041ab842a81abc0a625c29cb0e3`。现有 G 一次性制定整章多个 beat，即使前面模型真正写了变动，也继续机械使用旧 beat。这是规划时机和真实来源不同步的架构缺口，可能造成重复封套、安排换马、再派信使；但这些文学问题的唯一致因仍未通过控制实验确证。

[0.AS真实六次同作者复审 #40272430331](https://github.com/66tyu55/WriterForge/actions/runs/40272430331)：修复写作/审稿双 JSON 合同后，有效自审输出从2/6到6/6；6次都选择MOVE_ON。 [0.AT真实两次有来源的自审 #40273633246](https://github.com/66tyu55/WriterForge/actions/runs/40273633246) 作者看到册子去向签名疑点后，仍2/2选择MOVE_ON。故**只优化审稿提示和报错不会自动提高小说质量**。

## 0.AU 工程变更

在原 `writerforge/writing_assist.py::AutonomousWriting.run` 新增**默认关闭**的 `g_rolling_author_planning: bool=False`。仅在 `draft_mode="continuity_guard"` 允许显式启用；保留默认六段原写作合同。G 中上一段已经真实生成且它的**字面后果来源或待观察决策**通过既有 V96 SHA、V98 来源校验时，才复用现有 `prepare_replan_instructions`、`validate_replan` 让**同一个写作模型**重新提出下一 beat。宿主只能验证原句、角色范围、未接受父节点等结构，**不能编写新目标、人物欲望、小说正文、替作者选故事走向**。

如果刚刚写完的实际段落为`TRACE_REJECTED_SOURCE_PROSE_REVIEW_ONLY`或者无观察结果的安静叙述，不能跳过它去偷用更早前一个“真实后果”当作当前事实；`g_source_replan_eligibility` 默认跳过这次构思，继续冻结的原 beat，并在回执记录`PREVIOUS_TRACE_REVIEW_ONLY`或`NO_VERIFIED_SOURCE_BASIS`。签名被篡改则直接 RED，而不是降低审计强度。所有此类模型构思与跳过状态仍属候选，`causal_truth_verified=false`、不能晋级 KNOWN、无 Canon 写入。

新增 source-only 回归 `tests/test_wf_0au_g_rolling_author_planning.py`。G 的老路线仍工作；受影响后文一旦因 V119 回改，新增 rolling_goals、rolling_receipts、滚动 prompt SHAs 和 skip lists 一起纳入原来的同一 rewind snapshot（不得留下旧计划假父节点）。章节证据附 `g_writer_v98_opt_in`、`g_writer_source_only_replans`、`g_writer_review_only_replan_skips`，明确文学效果未证实。

## 验收与尚欠缺口

[0.AU 初次全量回归 #40278971202](https://github.com/66tyu55/WriterForge/actions/runs/40278971202) 成功；最终加入来源回执输出后的新运行详见分支 Actions。测试必须保留原 RED 日志；不要将原先 Python 源码中误注入的字面 `\n` 语法错误称为文学模型故障（仅是实验编辑过程出错，已修复）。

**尚未通过真实文学增益**：没有在此开关下完成真实 DeepSeek 全章，也没有“同小说同预算、同段落数量、可比文字长度”的传统 G 与 G+V98 新后文对照，更没有独立、逆序文学盲评。下一阶段必须用实际非 0.AQ 老稿的原创场景做两臂作者生成（预算封顶、原回包 SHA、不重写历史文学原稿），检查重复事件率、人物认知、来源连续性、节奏，以及同模型家族评分的局限。作者依然要有不修改、等待、停顿、选择推进的权利。

只要不能证实质量改善，就不能把 `g_rolling_author_planning` 改成默认 True，也不能把它当学习奖励或“正式 WF 写作提升已实现”。
