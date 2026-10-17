# WriterForge V29 · 语义适配与原创稿可复评留证底层修复（2026-10-17）

**范围声明**：用户批准 V28 随机原创首章复盘后提出的六阶段计划。本轮实际落地的是**P0 语义证据隔离与弃权协议、P1 新原创稿私有加密留证/错误位置数据协议、正负任务证据云端归档、兼容性回归**。本轮没有新增任何付费文学训练，没有验证模型文学能力真的提升，更没有将候选规则自动晋级。其余“真实独立读者逐字评审、因果学习策略升级、跨题材3→6→9迁移”仍属于下一验收阶段。

## 一、为什么要改

V28 三个原创小说第一章题目（先设计六题后随机固定3题）获得：封矿峡谷 69.0→86.6 (+17.6)、古杉林 86.2→78.8 (-7.4)、黑沙盐湾72.4→86.2 (+13.8)。三轮**同一来源窗口、同一模型角色、同一宿主预置技巧组合** `GOAL_FILTERS_ATTENTION + WITHHOLD_CAUSE_SHOW_CLUE`，古杉林五维都负向。无法用三次模型单评证明机制适用条件或某种文学失误的单因果；旧临时草稿已销毁，不能冒称可恢复给人类逐句评价。

## 二、P0 完成：带语义假说的可核查源证据

`writerforge/reverse_semantic_evidence.py` 新增**显式选择才启用**的结构化Planner合同，八字段：`id`、`evidence_id`、`source_span`、`character_knowledge`、`local_cause_effect`、`new_task_fit`、`misuse_risk`、`decision`。必须给出原文指定段落内实际存在的连续12–48字符证据，不得把不存在的段落、杜撰原著事实或任意模型定义的新机制送给Writer。可选 `SUPPORTED_FOR_TRIAL/INSUFFICIENT_EVIDENCE/RISK_IN_THIS_TASK`，全部不适用则提前弃权，不消耗Writer/Critic调用。

`CloudABTrial(...,evidence_first=True,semantic_evidence_first=True)` 用以上协议；Writer只收到宿主原有合法ID和**预置操作**，不得收到source_span、模型解释、角色人名或原著剧情。输出只记来源证据指纹和解释hash、弃权和“`semantic_truth_independently_verified=false`”状态。模型解释本身并不是独立事实；**此阶段实现的是证据合约/核验通路，并未解决文学语义判断的真实性**。仍需独立人审或另一不共谋的评估者逐句确认，届时才可批准。

旧 `CloudABTrial(planner,writer,critic)`、旧解析和原始R2提交路径默认行为均未更改，旧 A/B API 的学习/写作机制隔离也仍有效。

## 三、P1 完成：下一批匿名原创正文的加密可复评留证

`writerforge/reverse_private_draft_evidence.py` 与 `pyproject.toml` 的可选 `[evidence]` 依赖建立 AES-256-GCM、独立随机密钥的私有R2保留接口，专门留未来**两份原创练习稿**，不下载或存原著书文本；数据和只含SHA/到期时间的回执分开。强制私有桶 `writerforge-private-library`、两份220–4500字符限定、R2内容SHA与全量readback、来源/写作任务的AEAD绑定、错误密钥拒绝解密、最多14天保留（默认7天）。

**重要限制**：TTL 是读取时强制到期限制，**不是自动执行 R2 删除**！只有明确授权/显式运行 `delete_expired(...,explicitly_authorized=True)` 才真正清理存储对象。GitHub需要另行配置 `WF_PRIVATE_DRAFT_KEY_B64`（32随机字节以标准base64编码），不得使用/复用R2 Secret，不能写进repo或公开日志；这条密钥当前尚未配置，不存在已保存的真人可复评新稿。本轮未触发私有新稿保存。丢失此独立密钥后无法恢复已加密的稿件。

`CloudABTrial(...,manuscript_sink=vault)` **仅在真实匿名 Critic、15%相对篇幅检查、引用保护成功之后**才触发加密保留；默认`manuscript_sink=None`不保存。摘要只包含加密回执SHA、两稿SHA与到期信息，不含正文。旧 `reverse_ab_candidates.py` 现仅允许具完整加密回执绑定的未来留存记录参与有界未验证候选账本，仍然不会自动晋级/声称已有人评。

`writerforge/reverse_draft_review_marks.py` 提供供未来审稿者使用的逐句定位结构：`baseline/skill`、五维、错误分类、起止字符位置、评论及修订思路，至多32条。只以SHA导出标注的原文片段及意见；未经独立身份核实的人/模型审评始终标 `independence_verified=false`，不能冒充真正90%文学验收。**当前模块不是已进行审稿**。

## 四、已真实执行的零收费 R2 负例归档

在V28真回执三轮 R2聚合 `2b2aea9c6563b402d0795fc1812e09d5d066e56a4ab51be045ddeabaae00b55d` 上，实际由 [零模型 one-shot #39005416238](https://github.com/66tyu55/WriterForge/actions/runs/39005416238) fresh GET核验后新增**不覆盖旧资料**的内容寻址候选SHA：

`63cde6bacd51f7c655ec4eb6e6ccdab7e96c54c9f507512dfbfeaba73cf7d60f`。

保存的上下文事实：封矿峡谷+17.6、古杉林-7.4（五维均负）、黑沙盐湾+13.8；三项为同一预置机制组合。**`new_rules_promoted=false`，不能因为单个负例全局删除整个机制，也不能因两正就删除负例；并未修改现有正式 Writer 写作规则**。R2对象不含原著正文或已经销毁的A/B原始稿，额外模型调用0次。

## 五、回归验收

- `tests/test_v29_semantic_evidence.py`：假原文段落精确证据、杜撰拒绝、风险弃权时Writer零调用、源文不泄漏和旧模式保持。
- `tests/test_v29_private_draft_evidence.py`：真实可选依赖 cryptography 的 AES-GCM 本地加解密回读、错误密钥拒绝、伪造回执拒绝、显式到期删除、未来加密凭据同旧有候选账本兼容、旧模式无留存。
- `tests/test_v29_draft_review_marks.py`：错误句子字符位置必须存在，导出不泄漏具体小说。
- `tests/test_v29_original_context_r2_import.py`：合成R2不覆盖、篡改拒绝与真实文献同形态回执；另有真实R2只读与候选回填验证。
- [专门加密证据可选依赖的离线工作流](https://github.com/66tyu55/WriterForge/actions/workflows/v29-semantic-evidence-offline-once.yml)：无云端模型调用，真实AES-256-GCM加解密回归；全仓库 `WriterForge Tests` 也持续检查旧 API。当前最终测试数量/通过状态，应以最新commit的 Actions 为准，不能沿用过时数。

## 六、接下来的验证，不是已经完成

1. 为未来新原创练习安全配置独立密钥和经明确授权的私有稿回读/清理程序；确认能保留匿名双稿供独立读者审查，但本轮历史六篇文本永远不可逆恢复。
2. 在完全**新随机题目**中显式开启新的语义源证据机制，分别比较旧WF/新语义隔离WF/无技能基线，记录审稿者的**同一份稿件**逐句缺陷；不能只在古杉林旧提纲不断优化刷分。
3. 只有多题、独立全文核查、旧成功题材与旧失败题材无回归后，才考虑上下文条件化技巧应用；任何文学机制永久化都需3→6→9客观迁移证据及用户原定50完整作品门槛。
4. 绝不能将`SOURCE_SPAN_EXACT_MATCH`等同“语义证据已由人证明”、把基础四个预置ID称作WF的新学习成果，或把显示锚点30当作原始文学质量分数。

**门闩不变**：第一课程窗口 `NOT_PASSED`，第二课程窗口 `LOCKED`，人类独立文学质量90%未通过、模型权重未更新、没有新增付费训练。
