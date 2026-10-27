# WriterForge 0.BE｜v2 认知习惯的第一次反向攻击、宿主主动不进化与完整价值证伪预检

日期：2026-10-27。**请先读本文再继续。**本轮不是 v2 文学提升实证，没有调用收费的模型、没有自动升格、没有向 main 合并。仍只允许开发分支 `refactor-unified-scene-delivery-audit`。

## 1. 最重要的源代码发现

将 immutable v1 (`42cad98118dea662cea472f708ef1de22f4bb139da3210b1f5c3c1f9ac12664d`) 与 0.BD ChatGPT 提议的 SHADOW v2 (`0d43a023bc278ac12e3165e319d2acb73dcf40c0d9af453e623c786f3b476a10`) 按**同一字段**真实对照发现：

- v1 procedure[1] 138 字符，已经会区分来源上真正写到的行动、人物信念、未知事实与仅有计划。v2 procedure[1] 417 字符，**多 279 字符**。
- v1 falsifiers[0] 149 字符；v2 332 字符，**多 183 字符**；完整胶囊比较多出 **462 字符**。这是精确字符差，不是实际 token 使用，更不是供应商账单。
- **真实能力风险**：0.BD v2 是用面向无线电/回执的局部三阶段方案**替换**了 v1 的广域过程，而不是增量融合。因此它在安静描写、人物信念和“计划不等于发生”的场景可能发生负迁移。v1 很可能已经覆盖了本次提出的内容，v2 当前无任何独立文学益处的证据，绝不该冒称成功演化。

这些是关于*字节/协议差异*的真实发现；实际写作输出会不会变差或变好**仍未实验**。冻结 v2 SHA 不覆盖、不擅自改造成第三版。

## 2. 找到的真正底层问题和 RED→GREEN

原 `FirstHostNutrientLoop.acquire_once` 允许宿主返回完整的新 procedure/falsifier 字符串覆盖其 parent 的通用步骤。新的合成 RED 实际证实：使用面向个别案例的窄规则或覆盖原证伪条件，都可能被当成“学到新认知”并进入 SHADOW。

已在原 `writerforge/evolution.py` **仅对第一宿主的自动提炼入口**修复：

- 模型获取 meta-proposal 时同时拿到其当前 parent 的 4 条认知程序与 4 个 falsifier（没有把真正 heldout 例题交给它）。
- 模型只能保留选中父步骤/证伪条件的**完整原文前缀**，再在同一字段 450 字符上限内添加足够明确、限定适用范围的新内容；完整抹除或换掉原始认知、覆盖原证伪、只换同义词以及超过上限都被拒绝。仍保留作者模型对文学写作的自由，仍需要独立试验发现新尾句与旧前缀是否在语义上自相矛盾。
- 模型可以主动输出一个经过任务、来源和父 SHA 核查的 `decision=NO_CHANGE`，表示本次没有值得保留的新方法。WF **记录一次已经消耗的宿主授权尝试**，在 SQLite 原有尝试表用兼容的终态 `REJECTED_HOST_HABIT_PROPOSAL` + `failure_code=WF0BE_VOLUNTARY_NO_CHANGE` 保存；上层与下一次读取得到 `DORMANT_NO_NEW_TRANSFERABLE_HABIT`，不会无穷生成失败补丁或退款重试。不会因为一次 NO_CHANGE 自动销毁其他 Skill、主线程任务或历史旧版本。
- 新进程/另一个 host_id 读取同一个实验状态也必须继续 DORMANT，不得因切换宿主偷偷多调用一次。
- **范围限制**：此自动保留 parent 的强约束只在 `FirstHostNutrientLoop`，不是对原 `PortableHabitCandidatePool.propose` 所有人工签名提案的追溯性禁止。0.BD 历史 v2 仍原样可读、仍 SHADOW；独立可信策展者后续可走另有人工许可的修改路线。

**真实初始 RED** [#40460812111](https://github.com/66tyu55/WriterForge/actions/runs/40460812111)：父步骤/证伪条件可以被覆盖。自主停止的 RED [#40460994296](https://github.com/66tyu55/WriterForge/actions/runs/40460994296)：NO_CHANGE 未识别。P0/P1/P2 与既有 0.BD 原文源保存并未因此被提升或改动。[完整底层 GREEN #40461652510](https://github.com/66tyu55/WriterForge/actions/runs/40461652510)：**1,962 tests、6 skipped、0 failures**。

期间曾发现 0.BA 的整仓工作流没有下载 0.BD 历史 source artifact，导致 8 项真实 source 依赖测试“缺原件”失败；已把原 0.AY 固定工件下载加入 CI，而不是伪造 provider wire 或把测试跳过。这个环境修复与认知能力无关。

## 3. v1-v2 新场景对照预登记，尚未付费运行

新 `experiments/wf_0be_v1_v2_falsification_cases_20261027.json` 含 **8 个从未作为旧付费原稿运行的新合成情境**：

1. 交付与实际目标都已经证实成功——不能制造虚假的未确认。
2. 行为失败后条件发生变化，第二次尝试合法——不能见到重复就扣分。
3. 无接收方的安静家庭场景——不强迫行动/回执账本毁掉文学节奏。
4. 人物有限所见、将听到的动静误当接收确认的危险。
5. 武侠物品确已交给人，但目的是否达成未知。
6. 家庭承诺已说出口、行动未发生——v1 本来就应该能识别。
7. 软件工具返回 HTTP 202/排队，但真实备份未完成——跨文学宿主领域的正向可能价值。
8. 幻想情境黑板计划写了步骤，但角色并未执行——v1 的一般性负对照。

`experiments/wf_0be_v1_v2_preflight_only.py` 是**纯离线的宿主输入预检**：从真实固定 v1/v2 字节组成 16 个 prospectively matched 输入，两臂相同任务/相同已写合成源/相同系统角色/相同预定输出上限（每请求最多 1800 completion token 的计划，而非实际使用）。对每例的 v1/v2 顺序依据 case_id SHA 固定交替，不含真正答案或 case risk 的提示词，作者自行决定文学内容，评审需独立盲审、报告真实用量。

预览会精确输出文档字符差与源、任务 SHA，但**不执行任何模型，不保存伪造的正文，不构造质量分数**。此份公开代码中的 case risk 字段只是预注册分析提示，**不是对有仓库读取权的宿主真正保密的 heldout**；正式独立检验应由审阅者可信封存或使用新的未暴露例题，不得把“模型没在 prompt 中看到 risk”声称成完全盲法。

拟真实完成 8 组 v1/v2 对照将涉及 **最多 16 次新授权模型请求**、每次计划的 completion 上限 1800，即最多 28,800 的总输出 token 配额**预留上限**；还没有选定宿主、真实输入 token 计数、费用上限、读者或模型调用授权。这不是实际消耗，不能自动触发。明确新的预算前状态必须是 `DORMANT_NEEDS_AUTHORIZED_MODEL_AND_READER_EVIDENCE`。

**预检真实 RED** [#40462265023](https://github.com/66tyu55/WriterForge/actions/runs/40462265023)：接口尚不存在；[预检 GREEN #40462585987](https://github.com/66tyu55/WriterForge/actions/runs/40462585987)：**1,970 tests、6 skipped、0 failures**，8 项新预检测试通过，输出8组/16未执行的 paired envelopes、0 模型调用、无文学胜者。最新跨新进程 NO_CHANGE 停止测试加入后需以随后 CI 的实际结论为准。

## 4. 下一阶段只做真正有收益的测试

现在首先应该**阻止 v2 自动获权**；保留它为有来源但价值未证的 SHADOW。只有新的真实、同模型、同成本、已签原始 model wire 和独立读者负对照才能决定它是否比 v1 值得长存或该主动 DORMANT。不得为“进化”而对 v2 先行微调，也不能再把静态规则、偏爱冗长说明或代替作者选择当作增益。

不接触 main / Railway / 用户 R2 原著 / Canon；不新增第二叙事记忆。不重试 0.AY GLM HTTP 429，不修改封存 provider wire，不使用已有 Github Secrets 发新付费调用。保留原 V26/V98/V119 和唯一 NarrativeCore。
