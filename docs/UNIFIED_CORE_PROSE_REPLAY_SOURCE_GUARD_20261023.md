# WriterForge 统一核心：真实心理类重复正文缺陷修复交接

日期：2026-10-23；分支：`fix-unified-core-long-prose-replay`；基于 `unified-core-r2-durable-memory`，未进入生产 main、未部署 Railway。

## 真实失败事实，不允许洗掉

七类实际书生/Discovery `Atria-Dawn-Preview` SSE 文学批测的心理类中，同一模型、同样题目：

- 裸模型原稿：855 汉字，没有全文重播。
- WF 引导版：1694 汉字，原始 `prose` 包含 2006 个 Unicode 字符，去除排版空白后共 1928 个字符，**恰好是同一段 964 字符的逐字连续重复两遍**。
- WF 版原始 `prose` SHA-256：`272557d79b55f4b6790591afcc0817d61feedf2deb11f25fcbacf3dee4dedbac`。
- 两半非空白文本各自 SHA-256：`9bb2ee8b1a70783f4c005f85decb315497a6972944665911a07681f8e982e84b`，完全一致。
- 此前 V114/V116/V117 原有状态检查报告 0 硬错误；只检查物件与知识不是文学正文重播检测，故出现漏检。

**只能确认已存储的可见输出发生了重复，尚不能依据当前 SSE 记录断言是模型本身循环生成，还是供应商网关重复发送文本片段。**不能用文学思考说明代替实际原文观察。

## 合并到已有统一核心的修复（不是新记忆模块）

- `writerforge/narrative_core.py` 直接增加 `detect_long_prose_replay(prose)`，使用 KMP 前缀函数计算非空白正文的最小周期；源 text/SHA 真实记录，整体复杂度 O(n)，不调用模型、不删除原文。
- 对整篇正文中的**长段精确重复**（最小周期 >= 280 字符、输出 >= 650 字符、至少 2 个完全相同周期）返回 `blocked=True` 和 `WFCORE_ENTIRE_LONG_PROSE_REPEATED`；对接近大段的非完整重复只提供 `WFCORE_LONG_TEXT_ECHO_NEEDS_REVIEW`，不硬拒绝文学回环；短句、意象或有限重复不能直接硬拦。
- `writerforge/writing_assist.py` 的 opt-in `continuity_guard` 路径在每一段实际 generated prose `check_turn` 通过后、`accepted_turns.append(evidence)` 之前核验；**整章所有段落组装后再次核验**，在 V96 证据完成签名之前、`save_candidate` 之前阻止整篇拷贝两遍。原有失败记录保存实际模型原始回合及 SHA，0 canon / 0 自动修复。只对该 opt-in 模式添加，老 `single` 模式不伪称覆盖。
- 通过时 `unified_prose_replay_checks`（逐段）与 `unified_completed_chapter_replay`（整章）在原有 V96 签名证据中记录，**不新建并行状态所有者**。
- 不自动把重复后半段删除。删掉后半段仍可能缺失真正结尾，故要拒绝原候选、保留全文并使修复成为可复核的单独动作。

## 验证

Github Actions 完整 WF 回归：[Run #39944633892](https://github.com/66tyu55/WriterForge/actions/runs/39944633892)。**1,394 tests run，4 skipped，0 failures**。包括新 `tests/test_unified_prose_replay.py`：完全重复、跨换行完整重播、正常非重复长篇、短台词回环、长首尾回声待审、空白拒绝、源 SHA、真实写作流程顺序及候选保存前门禁。

本地对 GitHub Actions 已封存的**七类14篇真实生成原稿**做同算法交叉核验：
- 共 14 篇、7 类全部配对齐；
- 硬拒绝 1 篇：心理 / WF；它恰好就是原来的已知真实失败稿。
- 其余 13 篇未出现该特定模式的硬拒绝，0 个仅待审的长首尾回声。
- 样本内没有误杀不等于对所有文学风格的低误判率有统计证明。
- 本次验证中的项目及原文只供本地只读；不将真实书生生成稿贴到 public GitHub 单元测试文件。

## 仍需承认的边界

1. 当前只检测足够长的**精确整篇/整段周期性重复**或明显首尾回声；语义改写式循环、短段落在中间的重复、低质量拖沓、人物心理空转等尚不能普遍检测。
2. 已证实的 SSE 完整输出不等于模型的隐藏思考可控，根因仍需通过另一个不泄露内容的 SSE chunk/hash 序列受限诊断区分“模型生成重复”和“网关推送重播”，不能瞎猜。
3. 这次是底层拦截能力测试，不是模型经训练而更会写。**真实文学盲评仍未完成**，七类别 A/B 的具体创作结论另在 `experiment-seven-literary-scenes-inkstone` 分支保留。
4. 如作者刻意要求整篇结构性重现，这个强门禁需要以后添加**明确的人工豁免**，不能依靠任意模型自述跳过。

无新增模型调用、无 R2 写入、无生产 main 或 Railway 部署。