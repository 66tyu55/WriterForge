# WriterForge 0.Z｜红灯驱动：修复跨章祖先来源“签名洗白”，验证 14 章冷热记忆分支（2026-10-25）

**本轮目标不是劝 AI 认错，更不是为 WF 凑绿灯。** 真实问题在 WF：两个各自合法的签名未必证明所有前史来自同一版原文。只有修复系统对版本、原件、父状态的解释，才允许后文把它们当成可信来源。

**工程范围：** `refactor-unified-scene-delivery-audit` 开发分支，原 NarrativeCore / V114 / V117 / G；不改 main，不部署 Railway，不读取或修改用户 R2 原小说，不修改正式 Canon，不重跑 15 章训练，不增加任何模型、第二记忆系统或审稿器。本轮新增付费模型调用 **0**。

## 1. 先造红灯：单章签名不等于完整祖先可信

- [RED #40180369416](https://github.com/66tyu55/WriterForge/actions/runs/40180369416)：1 条新增失败。第 1 章未绑定真实 V114 章节来源，第 2 章即使自己有整章原文字节和真实 V114 回执，旧 `make_resume` 仍把二章组成有效的新故事头。这是 WF 的来源链误放行。
- [RED #40180485943](https://github.com/66tyu55/WriterForge/actions/runs/40180485943)：3 条新增失败；第一章未核验 → 第二章签名 → 第三章再签名，即使即时父签名相符，也能继续洗白更早的来源缺口；第 1 章从不存在于本项目的外部 V114 快照继承时间状态也被错误接受。
- 这些测试在 `tests/test_wf_0y_cross_chapter_temporal_graph_binding.py`，只用确定性的短篇合成原文、现有 Novel Studio Node reducer、真实工程校验接口。模型调用0、文学评价0、R2真实读写0。

## 2. 原底层的最小可信修复

**`writerforge/narrative_core.py`**

- 在**原有已签名的** `source_temporal_link` 增加 `ancestry_fully_verified`，区分“只有上一段时态的 SHA”与“从可信来源根到当前章节，整条先后链都经过签名校验”。`advance_graph` 以本图上一章的真实证据传递 `source_temporal_parent_ancestry_verified`；`record_chapter_memory` 再核对本章原稿完整字节、全部分段和对应 V114 CP 链并签名。**父章不可证明，不允许由一个后来写对的章节将它变成已经证明的事实。**
- 第 1 章可以是真正无前史的新书根；除此以外，若要在真实 G 写作前使用一段有来源的第 0 章初始状态，必须提供**完整签名 V117 resume** 作为 `root_resume_anchor`，并验证同项目/同场景、原根图 SHA、该 root 的第 1 个真实 V114 CP 与新章第 1 段的父 CP 准确一致。裸露的外来 V114 CP 没有此资格。
- 历史旧图/旧 resume 的合法签名仍可用于只读核对，旧记录不会自动丢失或被伪造“补证”；旧图没有 `ancestry_fully_verified`，不能直接认作新写作分支所需的完整凭证。没有把这条状态存到另一个数据库。

**`writerforge/v117_continuity_trace.py`**

- `make_resume` 和新写作分支入口强制验证 `ancestry_fully_verified is True`；否则 `WF117_GRAPH_TEMPORAL_ANCESTRY_UNVERIFIED`。既有 `read_resume` 对无完整新字段的历史归档仍允许只读检查自身签名，不自动把旧状态认证成新的安全续写来源。

**`writerforge/writing_assist.py`**

- 原 G `record_chapter_memory` 同时收到实际写作段落、对应 V114 签名段、以及用户已明确提供的签名第 0 章初始化 resume（如有），让真正 G 的默认流程使用新证明，而非只让测试函数能使用。
- 保留原 V26 选择续写、V98 规划、V119 局部删改、单一统一叙事记忆、候选废稿回滚；不让 WF 决定删哪句、补哪句，也不要求小说作者再次回答 `MOVE_ON`。

## 3. 正反例：防漏检，也防止误拦

- 真正从无前史开始的第 1 章：可以完成首次 V114/NarrativeCore 签名；之后第 2 章只有正确父源和完整来源链才能放行。
- 完整签名第 0 章初始化：允许第 1 章接着创作；若用另一份初始化 resume、另一条 CP、另一项目或没登记的外部原文混接，必须拒绝。
- 旧第 1 章没有来源证明：第 2 章的新签名不能洗白它；即使再出现第 3 章，也不能因为上一章的局部签名存在而自动升级整段前史为可信。
- 14 章本地候选：第 1～12 章发生热→暖→冷归档；从合法第 12 章分叉改写第 13 章，再重建第 14 章。第 14 章字节可和旧版本完全相同，但时态 CP、图父 SHA 必须指向新第 13 章；旧第 13～14 章候选不允许当作新源继续使用。第 1～12 章旧原文及冷档读取路径必须保持不变。
- 无关故事片段、人物有意留白不自动判文学错误；这条修复只检测**软件自身的来源归属和版本身份**，不做文学审美裁判。

## 4. 工程结果（历史红灯不得改写）

- [最终 GREEN #40181186594](https://github.com/66tyu55/WriterForge/actions/runs/40181186594)：**1,678 tests run，7 skipped，0 failed**；包含以上三个红灯反例、合法 signed 第 0 章原根、十四章 hot/warm/cold 分叉、旧源码签名/版式兼容、现有跨章 G fork、模拟 R2 CAS 和 Studio JS 校验。
- 中间 [#40180815423](https://github.com/66tyu55/WriterForge/actions/runs/40180815423) 曾出现 7 个旧跨章 fork 失败，暴露出“明确签名的第 0 章初始化状态”是合法功能，而当时的过严根规则误拦。**修复办法是验证完整 V117 根，而非放宽对孤立 V114 种子和未证祖先的要求**。
- 任何一项 `make_resume` 正常签名或测试绿灯都**不是**真实小说质量提高的证明。本轮没有新的真实作家模型结果、没有将旧《潮簿》《雨册》原作者 `MOVE_ON` 改为回改、没有正式 Canon/Railway/R2 修改。

## 5. 尚存问题和下一轮故障测试方向

1. **源版本选择后的冷热档分支索引**：当前测试证明 14 章本地完整原稿回查与分支 SHA 继承；仍需检查极长篇冷档中的索引跳转、旧摘要缓存是否在特定组合下泄漏旧 fork 的来源，并继续使用同一 NarrativeCore，而非新建记忆系统。
2. **语义状态**：来源签名再严，也不能保证 AI 句子本身文学或因果准确；应继续用真实坏正文找 WF 漏检，不用 AI 的 `MOVE_ON` 作为安全证明。
3. **历史迁移**：旧 V117/NarrativeCore 无完整祖先来源时，必须独立核对真实原件重建证据后才能用于新章；不要让系统靠自称 `signed` 就放行，也不能默默自动篡改历史或把旧模型输出重训练一遍。

**下一次读取顺序**：本文件 → `CURRENT_HANDOFF.md` 最新 0.Z → `WF_0Y_CROSS_CHAPTER_SOURCE_LINEAGE_BUG_HUNT_20261025.md` → `WF_0X_FAILURE_FIRST_WF_DEFECT_REPAIR_20261025.md`。
