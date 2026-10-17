# WriterForge V41｜同宿主真实分阶段阅读与写作审计（2026-10-17）

## 明确边界

用户要求由 GPT-6 作为 **宿主语言模型**，不得让任何其他模型替 WF 读书、分析或写作，且必须证明 WF 程序本身真正控制阶段。此实验按已冻结的 GitHub 原仓库源码执行，不自行改写 Reader/Craft/SQLite 类。*不能证明模型本身独立于宿主进行语义推理，也不能声称 WF 已经提升文学质量。*

源码与测试卷在隔离分支 v41-chatgpt-host-blind-reader，真实源文是GITenberg #25124《老殘遊記》**第十六回**，未用旧V40第七回。正文6147字符，源包SHA256 `07fdc71efb66cff8044c10edb22d7f4507b7eace1ea8cdcdeb0a65da171c60bf`。通过真实 `OriginalStudy.ingest(...source_sequence_start=16)` 得到246顺序 source_spans，SQLite持久保存。

## 实际 WF 原生阶段（不是提示词模拟冒充数据库执行）

1. `SceneLiteraryStudy.prepare` 锁定原文、真实章节、初读盲段（2484字符），由WF的 `first_read_prompt` 生成本次宿主唯一可见的先段请求。请求 SHA `b9b7f8416a76b30463da3a3c9a7b9ef59ccac934c49858d622bab5bd0d5b6213`。
2. GPT-6 宿主对盲段提交首次预测/疑问/人物信息推断，输出 SHA `3dbb1db639ed527bad98e83ebf83ae022bfb2b0682afcf0df6c5eeaea5423b70`；WF `lock_first_read` 真正在 SQLite 锁定首读。
3. **锁定以后**才执行 WF `close_read_prompt` 获取完整场景（5228字符）及已锁定推测；请求 SHA `9313f2a98201cb5cc3487c638c59dbe042c6c1d355430dc56f39c61764930e69`。
4. GPT-6 宿主按WF协议提交四条带真实原文短引文的文学机制假说，输出 SHA `6f48772fc976595a99df8ce0264d593757a825b3aae108ea5bf1ff65781a7965`，WF `attach_analysis` 返回状态 `interpretation_unreviewed`。**没有独立文学语义复评**。
5. WF原生 `VerifiedWritingFlow.prepare` 从本章已发布的词面结构学海选6条检索来源（不显示原著句子）与2个Craft标记，形成宿主创作prompt SHA `59909996bb501bc838230708d6aaede0f7d0343571ded71ab41b54156d56304d`。同一宿主生成504字符原创候选；WF原生 `save_candidate` 保存 `run.json` + `candidate.md`，正文SHA `456d6522bc07bcef0bb8f4ac7625cc403b32d5adc7b11a86847a0a070cef4689`；原稿无来自源文的连续24字符逐字重合。**accepted=false，尚未获得独立文学认可**。
6. 额外只读回放：在新SQLite使用**原生 `SceneLiteraryStudy.run` 正常调用链**，仅重播上述已冻结宿主回复并逐字比较两个WF真实提示词；2阶段请求相同，首读不可再次覆写，已完成重开不得再次请求模型。这是零新模型调用的技术重放，**不是重复付费训练或第二次文学考试**。

## 严格失败项：读到的经验尚未进入创作

真正的文学假设存在 `literary_scene_trials.analysis_json`，但 WF 实际 `VerifiedWritingFlow.prepare` 没有读取这些未经批准的假说，只读取 `study_level=deterministic_structural_unverified` 的源文索引。创作prompt里也没有刚才四条机制。所以这个阶段只能证明 **同一个宿主＋WF流程可以读、存、分析、写作**，不能证明文学经验已闭环迁移。若事后手写分析内容到写作prompt，会违反用户禁止代替WF及禁止作弊要求。

## 独立性和停止条件

- 有审计证据的：真实WF类被调用、盲段与后段由WF分别构造、SQLite首读锁定、复读原文引文可查、宿主阶段响应SHA、同一本真实来源检索、实际写稿归档。
- 可说明但不能密码学证明的：单一宿主声明为GPT-6、当前人工衔接对话的身份；该接口没有服务端签名的模型身份见证。
- 没有证明：WF脱离宿主的阅读推理；正式学习晋级；经独立评审的文学进步；WF已自动把新学的机制用在下一篇创作中。
- 不调用DeepSeek/GLM/MiniMax/OpenRouter，不启用额外 Critic，零第三方模型请求；既有V35~V40历史不回写。
- 原始全部提示词/宿主回答/小说/SQLite/候选manifest/审计代码保留在聊天交付的私有 ZIP，而不是公开仓库，不公开未发表原创全文或模型回复。
- 第一课程仍 `NOT_PASSED`，第二课程仍 `LOCKED`。PR仅为隔离实验，不合并正式Skill。

**下一步应修正的是 WF 内部从“首读假设→经过反证的文学候选→创作准备”的受控数据流，而不是再让宿主代替WF把四条经验手动粘进prompt。**
