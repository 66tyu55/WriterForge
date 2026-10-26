# WriterForge 0.AP—0.AQ｜真实模型四段续写、来源引用债务与安全恢复（2026-10-26）

> 仓库：\`66tyu55/WriterForge\`；唯一开发分支 \`refactor-unified-scene-delivery-audit\`。不修改 main，不部署 Railway，不触及用户 R2 原著与正式 Canon，不重复既有15章训练，不新增文学记忆主人。原始 DeepSeek 小说正文只来源于 DeepSeek 真正的 provider wire；宿主及 WriterForge 没有代写。

## 1. 真实失败原件，不根据旧交接猜测

[0.AM 真实六事件规划失败 #40257489862](https://github.com/66tyu55/WriterForge/actions/runs/40257489862) 的原始 DeepSeek 计划在 t03 的 \`causal_parent=t02\`（对话）、t06 的 \`causal_parent=t05\`（安静观察），旧 V96 按事件类别一律拒绝。这是实际能复现的计划结构缺陷，不是AI文学质量评分。0.AN 已在原 V96/V119 与 G 提示内分开**真正有来源的对话效果**和**尚未证实因果的时间承接**；伪造父事件、来源 SHA 篡改仍拒绝。[0.AN 全量回归 #40258573154](https://github.com/66tyu55/WriterForge/actions/runs/40258573154)：1771 tests，10 skipped，0 failed。

[0.AO 新正文真实实验 #40259961845](https://github.com/66tyu55/WriterForge/actions/runs/40259961845) 成功严格复用旧两次计划结果，8次新的 DeepSeek Flash 真调用，生成4段真正原创正文与4次同模型写作时机回复。新章未完成，第一次真实 HOLD 错误 \`WF96_NONCAUSAL_PARENT_SOURCE_INVALID\`。原回包 artifact \`12624461773\` 已保留，没有因软件拒绝删除任何一段。

- t01 由原模型写出一段真正决定，后果尚未观察，可标 \`DECISION_EFFECT_UNOBSERVED\`。
- t02 对话的动作及后果引句在实际文字中有来源。
- t03 的 \`parent_effect_quote\` 不是 t02 已被 V96 锚定的后果；原 \`WF96_PARENT_CAUSE_NOT_ANCHORED_IN_PREVIOUS_PROSE\` 应当保留为错误，G 正确采用 \`TRACE_REJECTED_SOURCE_PROSE_REVIEW_ONLY\` 保留该段作者正文；本段文学效果不因此判失败，也不证明后果。
- t04 以 t03 的真实原稿作为前文继续写，旧 V96 却把这种已签名、引用未证的候选误送入“非因果安静段父来源”入口后硬拒，导致整个 G 章节提前停止。**这才是 0.AP RED 攻击到的 WF 下游事务断点**。

## 2. 0.AP 源证明 RED → 原模块 FIX → GREEN

[实际 RED #40261666807](https://github.com/66tyu55/WriterForge/actions/runs/40261666807)：1778条测试中2条新增测试失败，覆盖 V96 继续承接待复核父段以及 V119 同样来源修订契约。

在原 \`writerforge/v96_causal_turns.py\` 增加 \`_verified_review_only_temporal_parent\`，验证**旧作者正文 SHA、原候选 V96 回执 SHA、明确 \`TRACE_REJECTED\` 及不能写入KNOWN**；对下游的错误 \`parent_effect_quote\` 仍执行 REVIEW，不假称为可证因果。原 \`review_only_model_turn\` 现在以 source SHA 将这种 REVIEW 负债传递给后代，拒绝非法篡改。原 \`writerforge/v119_revision_transaction.py\` 复用这一同源核验，用于原作者请求修订时保留未证父节点；不新增独立状态库。

[完整 GREEN #40261947634](https://github.com/66tyu55/WriterForge/actions/runs/40261947634)：1778 tests，10 skipped，0 failed。后续在 [0.AP 原始8份付费回包零模型回放 #40262280590](https://github.com/66tyu55/WriterForge/actions/runs/40262280590) 再验真正供应商字节 SHA，新增模型调用0。逐段结果是：

| 真实段 | 原始正文SHA256 | 源验证状态 | 新模型调用 |
|---|---|---|---|
| t01 | \`a5d8814fac32e22b07817b9b233b0b81862d091c0295095d91da302ba12b737c\` | 有源引用，文学因果未证 | 0 |
| t02 | \`e5ed869a300904e63a43e063a5d9e71e6d79d21a6ecf939d991e9612dd4fb473\` | 有源引用，文学因果未证 | 0 |
| t03 | \`9009cce68d3fed4905f83e33732fca8cbb1e21478aa6df298e91f30f21156acc\` | 源字面引句错误，正文保留，因果 REVIEW | 0 |
| t04 | \`b867d7903bd94e4cbaaba8d59889a1ffabbb8e725b317affe1f271d7873b5c33\` | 保留作者原文，继承 t03 REVIEW 负债 | 0 |

**严格限制：**“回放能保留四段”不等于“文学因果正确”，更不意味着 V114、V117、G 全章已成功完成，也不能说已实现作者自主删改。

## 3. 0.AQ 恢复真实 G 至第五事件：不用重复之前八次付费

[0.AQ 八份旧答案复用到第五事件、零新模型 #40262899598](https://github.com/66tyu55/WriterForge/actions/runs/40262899598) 真正调用现有 G \`AutonomousWriting.run\`：来源锁定0.AH旧小说、0.AM原两条计划、0.AO原8条作者回应。重复付费0次；旧 G 路线已跨越 t04 的来源债务，并且确实**到达 t05 尚未写作的新提示词边界**。

八条旧回答中：
- 第1—6次新旧 prompt SHA、输出预算均逐字一致。
- 第7—8次原文字稿已存在，源代码修复后提示新增“父段错误引用不等于已证因果”的提醒，导致其 prompt SHA 不再与旧的相同。离线逐字比对确认**仅这一条 WF 来源提示有变化**，并将这两次严格标为“旧作者在旧提示下的已创作候选，复用而非新模型回应”。不能对它们宣称新提示改善文学创作。
- 新增 \`tests/test_wf_0aq_only_old_source_warning_prompt_replay.py\`：仅允许这两个且只有单条警示替换的模型回答在改后 G 上复用；其他提示变更、角色信息变更、输出限额改变都先 RED 拒绝。
- [完整回归 #40263239747](https://github.com/66tyu55/WriterForge/actions/runs/40263239747)：1781 tests，10 skipped，0 failed。

[0.AQ 第五、六事件真实写作运行 #40263390051](https://github.com/66tyu55/WriterForge/actions/runs/40263390051) 已发起：先完成全量零模型回归和严格旧8件来源复用，只有到 t05 后才会请求 DeepSeek Flash 创作后文。它的**最终状态必须以本次真实运行的 STATUS.json 与 provider wire 及回执为准**，不能根据计划宣称全章成功、作者已自行回改、已有文学百分制或文学生态升级。

## 4. 下一个验收的硬边界

若 0.AQ 的新 t05/t06 失败：优先从原始供应商 wire/实际 trace/V114或V117已存在账本定位真实错误，执行 RED → 修原模块 → 真实来源 GREEN，**不重问已生成的旧四段，不通过隐式修稿或改分数取得假绿色**。若整章通过：保存全章 SHA、V114逐turn链、V117签名resume、NarrativeCore父SHA、真实 DeepSeek 自审的 \`MOVE_ON/LOOK_BACK_NOW\` 决定以及任何被作废下游真实原稿；最后才按文学维度做独立、尽量等长的盲评。旧历史传令正文与0.AO作者回应、原始失败及各自分支都必须继续可查。
