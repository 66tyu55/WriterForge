# WriterForge｜0.M Studio 内同一个创作 AI 自主跨章回头（2026-10-24）

**范围**：仅开发分支 refactor-unified-scene-delivery-audit 的本地 Studio，明确 opt-in。没有新的付费模型请求、重复文学训练、Railway 部署、main 修改、R2 原书增删或 Canon 写入。所有本轮新增回信均为人工模拟的模型输出，不能证明真实 AI 文学水平。

## 首要目标和责任界限

**同一个小说创作 AI** 决定此刻继续写还是回头、为什么不满意、哪句或哪场需要重写、希望带来什么阅读效果，并独立生成所有新正文。**WF** 只提供章边界、原稿、实际因果和人物状态、SHA、V119 精修、V117 版本分叉与恢复；绝不按软件关键词、文学打分或另一个代写模型强制小说修改。

保留 V26 两候选 Ctrl+1/Ctrl+2 采纳/忽略及自动保存、V98 正文驱动滚动构思、V114 Novel Studio 状态、V117 签名、V119 精确修订及原唯一 NarrativeCore FACT/UNKNOWN/THREAD 记忆，A–F 默认不受影响。

## 本轮实际实现

在 writerforge/writing_assist.py 的原 G 写作通路增加 _ai_decides_cross_chapter。仅当本地有**合法签名前一章**、本次已实际写完**两章未接受正文**，且作者明确开启功能时，把两章**完整**原文、章节意图和源 SHA 提交给本次同一写作模型，请它决定：

- MOVE_ON：说明当前为什么应保留，完全不启动双章重写。
- LOOK_BACK_NOW：说明第一章为什么要改、该章唯一原句（或缺失的场景效果）、如不改的具体后果和希望读者感受到的效果；只有这个合法决定才能触发已有双章 V117 分叉。
- 字段、引用、SHA 不合法则 INVALID_SIGNAL，绝不自动改稿或反复模型重试；完整两章放不下 10,000 字符上下文时 CONTEXT_TOO_FULL，**不收费、不假装已阅读全部**。

真实模型答复原样保存在私有 job 的 ai-chapter-review-original.json，另有解析 receipt，二者不相互覆盖。该步骤单次 job 最多一次额外模型决策调用，随后至多一个完整双章重写 job，仍受已有每轮模型额度上限约束。这一扩展可能增加真实使用时的模型费用，因此 UI 默认关闭、明示成本。

writerforge/studio_server.py 的 StudioService.start_auto 新增 ai_chapter_review 参数，严格要求 G、接续已签名未接受前章、恰好两章、self_edit_rounds 为 1 或 2、self_edit_timing 为 ai_decides、无人工每段等待。使用者**仅发送一次本次创作任务**；先真实写两章，再同一模型决定是否回改；若要改，让相同模型在另一私有 job 重新生成两章，而非 WF 直接代写、直接接受或偷用旧下游。新分支重建失败，保留原候选、明确保存错误，不把半成品标为成功。

## Studio 版本选择、重启和安全

在现有 writerforge/ui/studio.html 新增默认关闭的“AI 自主章节回看”选项，提供原始候选与 AI 回改候选的选择器。新的本地 /api/autodraft/branch/select HTTP 操作沿用 Studio 的 Host/Origin/令牌鉴权与严格 job-id 检验。选择只影响**下一章的 V117 来源**，不自动将任一候选晋级为正式作者确认事实。旧历史版本仍保存，选定新分支时旧下游 resume 被拒绝。

StudioStore 现有本机项目目录中保存 unaccepted_branch_selection.json：仅为分支选择与 SHA 指纹的元数据，**不是额外的故事记忆模块**。重启时核对目录指纹、原/新 job manifest、每章实际候选原文字节、其 V117 统一图最近热记忆来源路径与 SHA、新分支收据及项目/场景/模型；有修改或不一致则 fail-closed，不擅自删掉原稿。已确认作者原手写草稿、V26 两候选、停止本次工作及丢弃本次候选的能力保留。

## 首轮原始红灯和最终离线验收

- [Studio 首次反例红灯 #40089790688](https://github.com/66tyu55/WriterForge/actions/runs/40089790688)：构造候选分支时，已解析的内容视图被误当作签名目录本身，导致 WF_STUDIO_BRANCH_CATALOG_TAMPERED；修正返回值契约而非取消校验。
- [初步修复 #40089940484](https://github.com/66tyu55/WriterForge/actions/runs/40089940484)：**1,523 tests run，4 skipped，0 failures**；增加“候选正文原始字节被修改，重启拒绝”的负例。
- [最新最终回归 #40090238474](https://github.com/66tyu55/WriterForge/actions/runs/40090238474)：**1,525 tests run，4 skipped，0 failures**，并经 Node 实际检查 Studio 内联 JavaScript。新增覆盖：单次任务 AI 选 MOVE_ON 与 LOOK_BACK_NOW、坏 JSON 不强制重写、新旧候选签名选择、HTTP 无令牌 403 / 错误 job ID 400、冷重启恢复、从选定新头续写下一章、二次重写失败退回旧稿、损坏选择目录或正文源拒绝恢复。所有回答均为**模拟模型**，无付费请求。

原历史 DeepSeek [#40070821134](https://github.com/66tyu55/WriterForge/actions/runs/40070821134) 第一段 INVALID_SIGNAL、第二段原生 MOVE_ON，及 [#40071088617](https://github.com/66tyu55/WriterForge/actions/runs/40071088617) 零模型重播恢复 MOVE_ON，仍是唯一真实章内自主选择先验。**本轮没有任何真实写作模型自主完成跨章 LOOK_BACK_NOW、删稿和重写的文学证明**。

## 当前仍有限制

只能从已有合法签名前缀开始，于刚写完的两章边界选择一次，且只支持回看这两章的第一章，不支持任意往前十章、无前史新书首章、流式写半句就删、多次递归文学自审，也未实现全局 R2/StoryWorkTree 持久事务或跨设备同步。旧分支作为历史仍可独立查看，只有明确选定新分支后才拒绝旧下游。

**后续重点**：先验证真实同一创作模型是否会自然选择 MOVE_ON 或 LOOK_BACK_NOW，保留原始 wire、正文、错误回复、重写前后原文、模型费用和独立文学盲评；不得为拿到 LOOK_BACK_NOW 给模型规定剧情或让 WF 代作文学判断。未经另外授权，不自动启动新的付费实验、重复训练、部署 Railway 或修改 main。
