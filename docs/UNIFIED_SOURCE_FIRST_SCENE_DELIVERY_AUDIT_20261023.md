# WriterForge 统一场景功能审计：不以模型自评冒充剧情兑现

日期：2026-10-23。分支 `refactor-unified-scene-delivery-audit`，从 `fix-unified-core-long-prose-replay` 继承已有 1394 项绿色基线。原生产 `main` 未动，Railway 未部署，本轮没有任何新模型调用、R2 或 Canon 写入。

## 用户原始问题

书生 / Atria 七类文学 A/B 已实际出现：
- **心理**：WF 原始正文先写出约一千字符，再整段逐字重复一次；旧物件与状态归约没有发现；
- **搞笑**：裸版有明确的雨伞误拿与新反转，WF 版延长尴尬与被注视感，却没有明显有效的包袱兑现；
- **打斗/计谋**：有新增物性或推论缺口及字数越界；
- 所有来源规则未报错，不能因此声称文学功能完成。

**逻辑真相层和文学完成层必须分开。**大纲要求某个选择、转折、兑现或悬念，未必意味着模型正文已经实现。即使模型的 `trace.effect_quote` 在正文逐字存在，也只是来源锚点，不足以证明文学上的“笑点兑现”“心理选择有效”。

## 已合并底层代码（一个状态所有者，不开平行技能）

1. `writerforge/narrative_core.py` 新增 `audit_scene_delivery()`：
   - 同时调用原有 `detect_long_prose_replay()`：完整长段周期重复仍是 **blocked** 硬失败；
   - 按 5 字符 shingles 对相隔至少一个窗口的长片段做保守相似度检查，只形成 `WFCORE_LONG_PROSE_ECHO_REVIEW`；**字面相似不等于语义重复**，不自动拒绝文学回环；
   - 允许引用以前 V96 的效果句，但验证只有真实文本中唯一来源位置才收下；同句多次出现只提示歧义，不以引用重复作为硬错；
   - 一条作者明确登记、附稳定 ID 的通用 `author_delivery_contract` 可选说明“本场要产生变化/揭示/反转/选择/复杂化”或者明确 `DEFERRED`。没有强行按“搞笑/心理/悬疑”等文类创建平行模块；
   - 若合同明确 `THIS_SCENE`，**无论模型或第三方评论如何自信、即便所引句子真实存在，也不能自动给出完成认证**：它始终提示 `WFCORE_DUE_SCENE_PAYOFF_NOT_YET_VERIFIED`，需要作者另行认可；此函数无直接结案权；
   - optional `reviewer_proposal` 可存 `CHANGED/TRANSFORMED/STILL_OPEN/UNCERTAIN` 语义建议，但必须有正文原句中唯一行动与后果锚点，保留 `semantic_interpretation_still_unverified`，不修改事实、道具、人物认知或任何长期线程；
   - 使用原文 SHA 与哈希化的片段证据，返回统一签名 receipt。没有将用户私人原文写入返回数据。
2. `writerforge/writing_assist.py` 的真正 `AutonomousWriting.run(..., draft_mode="continuity_guard")`：
   - 各段 `check_turn` 得到实际正文后、加入 `accepted_turns` 前，统一调用场景与重复核验；
   - 组装整章后再做一次，**在已有 V96 manifest 签名生成、候选保存和 R2 memory 之前**拒绝整篇重播；
   - 两类源证据及 `needs_review` 都放到既有 `v96_turn_evidence.json`，不写单独数据库；
   - 新增可选 `scene_delivery_contracts=(...,)`，数量须与章节目标相同，严格要求作者明确确认，非法结构**在调用模型或创建输出目录之前失败**。非 continuity_guard 模式不能悄悄忽略这个字段；
   - 承诺未证实的返回状态直接反映在 `chapter_data.unified_scene_function_review_needed` 和 `unified_scene_function_review_findings`，不让作者翻十层 JSON 查；
   - 不是生成或自动重写工具，也没有把“段落更长”当“文学更好”。

## 真实输出只读核验

来源：GitHub Actions 封存的七类 `Atria-Dawn-Preview` 原创合成题目，**14 篇文本，7 个裸/WF 配对**；只做本地离线检测，不把原稿加进公开 GitHub fixture。

对代码中的 exact replay + long lexical echo 边界进行同算法只读交叉检查：14 篇里只有心理类 WF 原稿触发完整长段硬拒，另外 13 篇不触发；长字面回声也只出现在同一篇失败原稿。该结果只能说明当前这一小批素材的**字面重复识别**，不能当作任意作品语义判断的误报率。

针对搞笑类，源文阅读发现裸版“拿错唐蜃的伞”转折比 WF 版结尾的尴尬铺垫更清楚；这是**原文观察性质的编辑意见**，而非这套无模型检查器自动可靠检验了幽默效果。明确作者合同允许将该问题标成“兑现未得到独立验证”，不能凭模型自评把它登记为完成；仍须文学评审认可。

## 测试、能力范围和反例

`tests/test_unified_scene_delivery.py` 覆盖：
- 需要当场兑现的作者确认 scene contract 和“有意延期”的长期问号；
- 模型自己引用真实句子仍不能独立宣告兑付；
- 评审建议必须绑定两条有顺序的唯一原句，来源不存在拒绝；
- 长篇完整重播硬拦截，略有改写的远距相似只待审，短诗意复沓/心理沉默不可硬拒；
- 作者确认权限、章节数量和写作模式在付费模型运行前校验；
- 书稿候选生成路径验证：每回合与整章检查均在接受和保存之前，结果写进已有 V96 signed receipt；
- 审计结果源文本 SHA 完整，未包含小说原文，模型调用数 0，canon 写入 0。

## 最终自动验证

最新已完成 GitHub Actions 运行：[#39947647329](https://github.com/66tyu55/WriterForge/actions/runs/39947647329)；**1,407 tests run、4 skipped、0 failures**。此运行覆盖最终功能性代码提交 `c216a83426431a9261f4d211773ab1f4fe605802`，后续仅补充本技术交接文字，未改动代码。无新模型调用、无生产代码部署。

本地对 14 篇真实原稿执行同阈值 source text replay/long lexical echo 只读检查：整段硬拒 1 篇（心理 WF），字面近重复提示 1 篇（同一原稿），其余 13 篇无这两类命中。数据只作为小样本回归，不宣称测出了文学语义误报率。

已注意两项必须继续做的工作：
1. *通用语义重复* 与“人物不断考虑但毫无新变化”无法由 5-gram 相似度或简单关键词证明。真正的心理与喜剧专项文学判断仍需要独立、可追溯且可反驳的读者/模型审阅，而非在底层增加硬编码“笑字”“决定字”规则。
2. `author_delivery_contracts` 只是当前章节作者意图，长期未偿承诺仍应由**同一 unified THREAD 图**持久化。不要另造“喜剧记忆库”或把短期未证实合同自动升级为跨章正典。

## 原始仓库与生产边界

开发分支：[refactor-unified-scene-delivery-audit](https://github.com/66tyu55/WriterForge/tree/refactor-unified-scene-delivery-audit)；验证工作流 `.github/workflows/unified-scene-delivery-audit.yml`。未修改稳定生产 main，未部署 Railway，未消费新的书生赠送额度。本次没有假装训练了模型权重。
