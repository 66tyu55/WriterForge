# WriterForge 0.S｜同一真实 DeepSeek 原作者自主选中动作漏洞并亲自 V119 改写：新句确实生成，但 V96 因果引句重叠而严格回滚（2026-10-25）

**范围**：仅开发分支 `refactor-unified-scene-delivery-audit`，不改主分支 `main`、Railway、用户 R2 原作和已接受 Canon；没有重复旧15章文学训练、增加第二记忆主人或让 WF 代作家写正文。这次只有 **1 次全新真实 DeepSeek V119 提案调用**，完全独立于此前一次原作者文学选择的真实费用。本轮没有自动再调用模型，也没有私自把错误因果字段改成正确值。

## 1. 源历史必须保留，不能因修订失败被覆盖

按以下四条真正的供应商历史来核验（用户此前“继续”已授权执行一次真正 V119）：

| 历史阶段 | 原始 Actions | 这次是否新增付费 |
|---|---|---|
| 原生 G 章计划、beat、两段真正原创小说，以及原 G 双条件自审 | [#40110957161](https://github.com/66tyu55/WriterForge/actions/runs/40110957161) | 否，7 次旧账 |
| 同一 DeepSeek 的跨章双文本读者，作者当时 `MOVE_ON` | [#40151857245](https://github.com/66tyu55/WriterForge/actions/runs/40151857245) | 否，2 次旧账 |
| 同一个原作家，针对有实际早期原句的 3 条疑问区别 `WRITTEN/UNWRITTEN/ELLIPSIS`，真正选择 `LOOK_BACK_NOW` | [#40153456601](https://github.com/66tyu55/WriterForge/actions/runs/40153456601) | 否，1 次旧账 |
| 本次仅让其依据**自己此前真正选择的唯一原句**提出一轮 V119 `REVISE` | [#40155863914](https://github.com/66tyu55/WriterForge/actions/runs/40155863914) | **1 次本轮新请求** |

新模型调用前下载并逐字核实上述原始模型 provider wires、正文 SHA `2a0d2827d51dc1197065cd21126e091a3fd44c4db3bb7d92048c3167d24f4dbd`、真正合法 `LOOK_BACK_NOW` 及与原文唯一对应的被选片段，后续只通过旧 V119/V96/V114/V117 的已有代码门槛。没有再向模型问“愿不愿删稿”，没有改写作者原意。

## 2. 本次真正作者所写的文学替换（原样，不由 WF 生成）

**真实旧稿中被选的原文**：

> 她刚要把重心全压上去，板缘猛地往上一翻——她整个人朝栏杆撞过去，膝头磕在硬木上，疼得眼前一白，手却本能地揪住了后台帘边那截布。

**真正的同一 DeepSeek V119 `replacement`**：

> 她把重心一点点挪上去，心里早备好了往回撤的那口气；板缘还是猛地往上一翻——她整个人朝栏杆撞过去，膝头磕在硬木上，疼得眼前一白，手却本能地揪住了后台帘边那截布。

这一句确实改掉了此前“已经看见裂板，却不设预判突然全压”的动作；增添了自己权衡危险的谨慎心理，却保留了真正撞伤和原本的身体代价。**文学方向可讨论，不能说已通过文学盲评**，也没有处理“票据从袖中出现在旧戏箱”及“钥匙从手里变腰间”的前后源风险。

## 3. 真正失败根因，是模型自己的 V96 引句，不是模型没有写新小说

DeepSeek 回复 `type=json_object` 的冗余包装、错误的 Unicode `start/end=418/497` 都被原软件限定在源 SHA 唯一原句内机械兼容，完全保留模型原始 provider wire、原错误坐标和 raw JSON。第一轮唯一的新供应商请求产生了真实 `REVISE` 和**非空** `replacement`。

但真正旧 V96 引句：

- `trace.action_quote` = **整个 replacement**
- `trace.effect_quote` = **同一个整个 replacement**
- `trace.parent_effect_quote` = `null`（该 beat 确无父事件，本项正确）

V96 必须区分已发生动作与后果的两处**不同、先动作后后果、互不重叠的原文字面引句**。其拒绝码准确为：

`WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED`

**正确做法是保留模型写下的 replacement、原始 V96 错误和已签名旧 G 章节，不是由 WF 自动给两种引句拆段、默默填入“合法 trace”或将私有修订当已接受 Canon。**

原始 [真实 V119 的 provider wire、失败稿和回滚回执附件](https://github.com/66tyu55/WriterForge/actions/runs/40155863914/artifacts/12584493249)。

## 4. 零成本深一层取证：可源锁预览 ≠ 可正式采用

[四条真实源历史完整零模型核验 #40156185580](https://github.com/66tyu55/WriterForge/actions/runs/40156185580)，对原 DeepSeek 回答不作任何主观改写：
- 唯一原句逐字定位、V119 `preview_revision`：**`PROVISIONAL_REVIEW`**，可以构成一份与原源锁定的**纯私人候选预览**；
- V96 对模型原 `trace`：仍然 **`WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED`**；**正式 V119/96 有效修订次数为 0**；
- 只针对其纯文本的 V117 `preflight_continuation`：`blocked=false`、`needs_review=false`。这不是已经证明文学连续性，更不是一份由 V117 签名的**新完整章节**；
- 旧 G 第二段基于旧第一段写成，**没有重新生成，必须保持为旧分支历史**；不能悄悄沿用旧第二段冒充新作品；
- 机械预览的新原稿 SHA `653865dfc002e24493178773d4c90ec4c5b6dea1d57a05d3ba47eb714c696beb` 与真实旧原文 SHA 不同，**不代表其文艺效果更佳**。该预览完全来自原模型自己写出的 replacement；用户、WF 和本聊天均没有代替它写新句。文件独立存为 [私人真实旧/新文本及未通过因果证据](https://github.com/66tyu55/WriterForge/actions/runs/40156185580/artifacts/12584084616)。

## 5. 代码的实际改善与安全边界

为了未来模型**自己**提交正确的 JSON 因果引句，在原 `writing_assist.py` 的同一 V119 提示中补充约束：如果 `beat.kind=action`，其 `trace.action_quote` 和 `trace.effect_quote` 必须是**两个分别6—96字、来源唯一、先后有序、互不重叠**的真实文本片段；可位于同一句的不同子串，但不能把整段或同一个完整 replacement 复制两遍以假装动作和结果都已证实。如果新句没有结果，作家本人需重新构思句子，不能要求 WF 自动生成结果或篡改数据。

原 V119 的**源锁定不唯一拒绝**、V96 的**因果先后和防假 trace**、V114 时态与 V117 复读源、原一套 NarrativeCore 热/暖/冷和旧历史分支、V26、V98 与 Studio 用户取消/删除候选职责保持不变。

- [真实 V119 前原子保护及第一次回归 #40155768365](https://github.com/66tyu55/WriterForge/actions/runs/40155768365)：**1,589 tests executed、4 skipped、0 failed**。第一次测试红灯 #40155679207 为一条错误的源码字符串断言，后来只修测试校验到真实仓库的 old run 及 wire 源。
- [针对真失败新增源引句先后提示的最新全量回归 #40156031520](https://github.com/66tyu55/WriterForge/actions/runs/40156031520)：**1,590 tests executed、4 skipped、0 failed**，并经 Node 校验 Studio 浏览器脚本。
- [完全零模型 V119 原回复取证 #40156185580](https://github.com/66tyu55/WriterForge/actions/runs/40156185580)：完整旧 wire 验证、新 source-only preview、**原 V96 红灯不变**。这一工作流没有任何模型密钥或新模型成本。

## 6. 下一步：从“知道要改”走向“真正写成可验收的作品”

不要继续对同一篇旧稿无上限付费求合法 JSON，也不能靠人为改 trace 凑成功数。下一阶段宜：

1. 用一个**新创作场景**与不同叙事类型独立验证“源锁定的原模型 V119 改稿能否一次通过动作/结果引句、V114、V117 与真正下一段的重新创作”；
2. 对真实成功的新章节，保留匿名 A/B 源件，由**独立阅读者**判断人物动机、空间位置、自然度、物件/信息连续与节奏是否改善，而不是让 WF 或创作模型给自己打分；
3. 如发现模型容易写新句却老填错 trace，优先改进**写作者对自己文本的来源引用**，不能另建一个偷偷自动帮模型生成小说的“纠错 AI”。

**本轮结束时状态**：**1 次新真实 V119 模型调用、0 次自动重试、0 次合法的新完整章、0 次 Canon/R2/main/Railway 写入**。相关证据保留、旧已接受作品完全未动。下一次真实付费模型试验仍需用户明确指示。
