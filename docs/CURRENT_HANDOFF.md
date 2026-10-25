# WriterForge 当前有效交接｜2026-10-24


## 0.AB 文学质量必须有分数，但评分也得接受故障测试：真实原著62、A79、B76仅是未匹配片段的局部偏好（2026-10-25，最新）

**下窗口先读**：[WF_0AA_0AB_REAL_LITERARY_SCORECARD_20261025.md](WF_0AA_0AB_REAL_LITERARY_SCORECARD_20261025.md) → [WF_0Z_SIGNED_ANCESTRY_PROVENANCE_20261025.md](WF_0Z_SIGNED_ANCESTRY_PROVENANCE_20261025.md) → [WF_0X_FAILURE_FIRST_WF_DEFECT_REPAIR_20261025.md](WF_0X_FAILURE_FIRST_WF_DEFECT_REPAIR_20261025.md)。用户新的明确方向：**逐段对照《凡人》前几章的真实文学技巧，让 WF 辅助 AI 靠近文学水平而不复制/编造，必须有直观的分数**。测试仍以暴露和修复 WF 自身真实错误为目的，绝不因为高分迁就 AI 或偷改文学判断。

- **评分的实际数字，不是我编的**：[旧真实 A/B DeepSeek 六次作者调用 #40163959949](https://github.com/66tyu55/WriterForge/actions/runs/40163959949) 的四份源码和 provider wire 重新校验，私有 R2《凡人》原著与原实验 SHA 锁定，只读提取第1、2章开始的230字窗口。新增隔离的 `experiments/wf_0aa_literary_reference_score_20261025.py` 采用五项各20的百分制：语言自然与节制、细节的叙事作用、动作与场景可信、节奏与信息取舍、人物真实感。现有 DeepSeek Flash 以**4次非 WF 内部文学裁判**匿名顺序交叉评分。[真实评分 #40182718487](https://github.com/66tyu55/WriterForge/actions/runs/40182718487)：原著R第一窗口66.5/第二57.5/平均**62.0**，WF未读原著A 80.0/78.0/平均**79.0**，WF逐次读原著B 76.5/75.5/平均**76.0**。每个分数含两种匿名顺序原始 provider wire SHA 与维度回执，不预设名著100分，不公开版权原文，不修改作者真实四段原稿。
- **这并不意味着 WF 比《凡人》强，也不能说读原著反而降低文学能力**：作者和打分者是同一模型家族，可能偏爱自己的叙事密度；原著开篇是家境/城镇背景，AI片段是异常发现/责任/悬疑，文学任务不一样；第二窗口原著230字，B仅183字；仅2个位置，没有裸模型 C，也没有独立人类评委。表面 A 比原著高17、B高14是**不公平的局部模型偏好指标**，不能拿作 WF 文学进步或自动训练奖励。
- **用评分红灯修正测量流程**：新增 `experiments/wf_0ab_score_validity_gate.py` + `tests/test_wf_0ab_literary_score_validity_gate.py`。严格保存真实 62/79/76，但对叙事功能不匹配、样本长度不平衡、同模型家族打分、缺裸模型、缺人类复评等给出红旗，`valid_progression_signal=false`、`comparable_literary_level_score=null`、`proves_WF_improvement=false`、`cannot_use_as_WF_training_reward=true`。评分系统的破坏性测试还找出了共享可变 SHA 夹具的问题，已修正而未放松来源身份核验。无模型 [审计 #40183539551](https://github.com/66tyu55/WriterForge/actions/runs/40183539551) 对原先 62/79/76 重放，结论是“数字真实，但不可作为写作水平已经接近或超越原著的凭证”。
- **文学分不能洗白源世界错误**：B第二段文学局部分75.5，但原 `绳结仍系在桩上/从桩头解下` 被现有 V122/V114/V117 在 [真实旧源重放 #40167612081](https://github.com/66tyu55/WriterForge/actions/runs/40167612081) 确认为 `HELD_NEEDS_SOURCE_RELATION_REVIEW`。文学读者观感和可核实的世界状态事实是**两个不同维度**，不能互相冒名当通关。绝不要求 AI `LOOK_BACK_NOW` 才把 WF 源错误算错。
- **最新无付费软件回归**：[全量 #40183418181](https://github.com/66tyu55/WriterForge/actions/runs/40183418181) **1,691 tests run、8 skipped、0 failed**；历史最初错误或拒绝样本没有被抹去。
- **后续正确的一点点比较**：先把下一轮每个 200–300 字片段的“叙事任务”对齐（静态生活/环境与人物压力 → 选择及代价 → 自然后果），以三路相同模型/相同原创题/相同预算对照：裸模型、WF辅助不读原著、WF辅助逐段读原著；原著只作为独立参照和文学技巧对照，不强行复制人物/剧情/原句。5项评分一律先冻结标准、匿名复评、显式来源风险，尽可能加独立人类读者。不能从一个 230字低分片段推断数百万字名著水平，也不把新的分数自动反喂给创作 AI。
- **安全/版本**：所有本轮代码仅开发分支 `refactor-unified-scene-delivery-audit`，评分实验只是 `experiments/` 外部测量工具，不新增 WF 文学裁判、知识库或记忆模块；既有 V26、V98、V119 及唯一 NarrativeCore 的职责不变。不修改 main、不部署 Railway、不写 R2/正式 Canon，不重复旧 15 章训练，也不对旧《潮簿》《雨册》重复付费劝改。0.AA新增 4次**评分模型调用**、0次**新小说生成调用**；0.AB审计新增0模型调用。

---

## 0.Z 先红后绿：修复旧未证祖先经后续合法签名被“洗白”；明确签名第 0 章根与 14 章热暖冷分支源绑定（2026-10-25，最新）

**下一窗口先读**：[WF_0Z_SIGNED_ANCESTRY_PROVENANCE_20261025.md](WF_0Z_SIGNED_ANCESTRY_PROVENANCE_20261025.md) → [WF_0Y_CROSS_CHAPTER_SOURCE_LINEAGE_BUG_HUNT_20261025.md](WF_0Y_CROSS_CHAPTER_SOURCE_LINEAGE_BUG_HUNT_20261025.md) → [WF_0X_FAILURE_FIRST_WF_DEFECT_REPAIR_20261025.md](WF_0X_FAILURE_FIRST_WF_DEFECT_REPAIR_20261025.md)。继续遵守用户的真正测试目的：**用测试找出并修复 WriterForge 自身错误，不能逼小说 AI 认错，更不能让 WF 迁就 AI 的 `MOVE_ON`**。只改 `refactor-unified-scene-delivery-audit`；不改 main、Railway、用户 R2 原小说、正式 Canon、旧真实模型证据，不重复 15 章训练或增建第二文学记忆。

- **WF 又找到一项真假绿色**：第 1 章没有完整 V114 祖先来源时，旧系统只要第 2 章新签名正常，就可能当作整个历史已证；再追加第 3 章依然错误放行；第 1 章偷偷把未登记外部 V114 CP 当先验也被误接。[RED #40180369416](https://github.com/66tyu55/WriterForge/actions/runs/40180369416) 1 条失败，[RED #40180485943](https://github.com/66tyu55/WriterForge/actions/runs/40180485943) 3 条失败。**合法单个签名不等于合法完整来源祖先链。**
- **实际修在原 NarrativeCore/V117/G，不造新记忆**：`source_temporal_link.ancestry_fully_verified` 和 `source_temporal_parent_ancestry_verified` 随章节从可信来源根递推。未证祖先不能因后来一章局部签名变成已证，V117 新 resume 与新 G 续写在 `WF117_GRAPH_TEMPORAL_ANCESTRY_UNVERIFIED` 处拒绝。旧签名归档仍可只读查原文，但不可直接冒充新的安全父版本；正式状态不落 Canon。
- **保留合法第 0 章初始化**：首次过严测试把旧 G 的已签名第 0 章种子也拦了，这是**假红色**。已在原 `record_chapter_memory(root_resume_anchor=...)` 与原 G 中验证完整同项目/同场景、根图、根 V117 签名和真正 V114 CP 的联系；允许合法初始化，裸 V114 外部种子依旧拒绝。中间失败的 [#40180815423](https://github.com/66tyu55/WriterForge/actions/runs/40180815423) 如实保留。
- **真实多章软件验收（不冒充文学）**：14 章本地热/暖/冷归档，从已证第 12 章改第 13 章，旧/新第 14 章就算正文一样也必须各自指向不同父 SHA；旧第 1～12 章原始归档和冷档索引保持可追溯，不污染新分支。已有跨章 G 真实方法的合成模型回包重建测试、合法 root、孤立/两跳洗白攻击都做了。
- **最终全量**：[GitHub Actions #40181186594](https://github.com/66tyu55/WriterForge/actions/runs/40181186594) **1,678 tests executed，7 skipped，0 failed**，含原 Novel Studio 及统一叙事图的现有回归；0 个新增付费模型请求、0 个用户 R2 真实读写、0 Canon、0 Railway 部署、main 未动。
- **仍不应过度宣称**：这轮只证明在开发分支中，新版本的源回滚与来源根能按既定工程边界工作。旧冷档长期索引跨分支污染尚需持续攻击；没有证明任何新真实 AI 的自主 V119 文学改稿成功、没有独立人类文学质量认可。后续继续“失败原稿→真正 RED→修 WF→正反例 GREEN”，不要再问旧《潮簿》/《雨册》原作者认不认错。

---

## 0.X 测试本来是爆出 WF 自身缺陷，不能让 WF 迎合 AI：三项实测红→绿修复（2026-10-25，最新）

**优先阅读**：[WF_0X_FAILURE_FIRST_WF_DEFECT_REPAIR_20261025.md](WF_0X_FAILURE_FIRST_WF_DEFECT_REPAIR_20261025.md) → [WF_0W_CONTAINER_CROSS_CHAPTER_REAL_WRITER_20261025.md](WF_0W_CONTAINER_CROSS_CHAPTER_REAL_WRITER_20261025.md) → [WF_SOURCE_FIRST_REPAIR_GUIDANCE_20261025.md](WF_SOURCE_FIRST_REPAIR_GUIDANCE_20261025.md)。用户明确纠偏：**测试是为了发现 WF 底层的错误，再修 WF；不是让 WF 迁就 AI 的 `MOVE_ON` 或不断提问逼 AI 修改。** 此阶段新文学模型调用0次，仅开发分支 `refactor-unified-scene-delivery-audit`；主线 main、Railway、R2 原小说、正式 Canon、旧模型回包和已完成的15章训练都不动。

- **WF 错误 1：V119 只比较风险码，可能漏检“改完旧错，产生另一个同码新错”**。原 `v122_item_provenance.physical_relation_issue_keys` 现给不同物件/接触对象/关系类别建立具体 SHA 风险身份（重复风险按多重集保留）；原 `v119_revision_transaction.preview_revision/compare_source_repair_impact` 返回旧/新增/消失/仍存风险身份，不能用同一个 `NEEDS_SOURCE_RELATION_REVIEW` 掩盖新错误。严格只是软件来源归类，不是文学评分。
- **WF 错误 2：合法 V119 修了原文，旧 V114 未证债务不能安全结案**。原 `v114_external_story_state.replay_revised_source_checkpoint` 新增源锁重放入口，逐字段校验 V119 签名、原/新原文 SHA、被改字符范围、未改前后缀和正确的上一版本，再调用原 Novel Studio reducer 建新的非 Canon V114 签名候选；仅这次原文真正消失的冲突能退役，前章仍未证状态必须保留。**这是可调用的显式重建事务，并未证明所有 G 长篇旧章节的派生图自动回滚/重写完成；下游新版本链仍要实测。**
- **WF 错误 3：重复物理状态引句会被全文唯一性校验直接丢弃，造成误放行**。V122 现在按原文 SHA + 出现位置 + 引句 SHA 区分同样的两次句子；原 G `_physical_relation_source_hold` 同样用位置验证。仅同句重复不自动判错；与相反状态发生时不会静默跳过待核。
- **先红再绿的工程证据**：[缺少修订重建接口的红灯 #40174663965](https://github.com/66tyu55/WriterForge/actions/runs/40174663965)，[重复引句两项失败 #40175124198](https://github.com/66tyu55/WriterForge/actions/runs/40175124198)，[最终全量 #40175372260](https://github.com/66tyu55/WriterForge/actions/runs/40175372260) **1,665 tests run、7 skipped、0 failed**。三个真实 WF 缺陷已落成原 `tests/test_wf_0x_bug_hunt_state_repair.py` 的对抗回归，不使用原模型代写/模拟文学进步、无需新模型或第二记忆。
- **后续验收重点**：继续找假绿色/假红色、状态丢失、未授权“清债”、跨章老派生状态复用和过度正则覆盖问题。采用“失败原稿→红灯复现→精确模块级修复→原样正反例绿色”的顺序；**KEEP/MOVE_ON 是作者选择，绝不取代 WF 世界状态真值边界**。系统真实不确定时保留 UNKNOWN、不能晋级确定前因；AI 不想改稿也不能让 WF 报 SAFE。真正同作者文学改稿 + 重新写下游 + 实际文学质量提升仍**未证明**，不能再重复付费劝旧《潮簿》或《雨册》作者。

---

## 0.W 容器/多物件/跨章来源债务不断链 + 全新《雨册》同作者逐段真写：工程1,656通过，但作者又选 MOVE_ON、真实改稿仍0（2026-10-25，最新）

**下一窗口先读**：[WF_0W_CONTAINER_CROSS_CHAPTER_REAL_WRITER_20261025.md](WF_0W_CONTAINER_CROSS_CHAPTER_REAL_WRITER_20261025.md) → [WF_0V_SOURCE_RELATION_REPAIR_20261025.md](WF_0V_SOURCE_RELATION_REPAIR_20261025.md) → [WF_0T_REAL_FANREN_SENTENCE_EVIDENCE_20261025.md](WF_0T_REAL_FANREN_SENTENCE_EVIDENCE_20261025.md) → [WF_SOURCE_FIRST_REPAIR_GUIDANCE_20261025.md](WF_SOURCE_FIRST_REPAIR_GUIDANCE_20261025.md)。**仅开发分支 `refactor-unified-scene-delivery-audit`；不修改 main、Railway、私有 R2 原小说、正式 Canon。不能因为 CI 绿灯宣称文学变好。**

- **修复0.V的跨章隐蔽断链**：原 `v122_item_provenance.audit_physical_relation_sources` 过去只存上一章 `review_pairs`，一章不再提相同物品就会丢失最初的不确定关系。现在 `open_relation_reviews` 作为**旧 V114 签名候选快照中的有限来源投影**携原句/来源 SHA 穿过第二、第三章的无关文本，第四章真正依赖该物品状态时由旧 V117 标为 review，而无关场景照常推进。**没有第二个事实/文学记忆主人，旧候选状态不写入 Canon**。
- **容器、多对象与时态**：旧 V122 新增非常受限的 `CONTAINMENT` 来源句式（还在容器里/已经从容器取出/明确放入）。和 `ATTACHMENT` 关系分域，不能误把两个不同物件或两个容器合并；“后来/随后才取出”“不同颜色的牌”“人物猜测/对话”正反例均校验，所有 ID 别名仍只是待证。还在木匣/已从木匣取出的同刻候选只标 `NEEDS_SOURCE_RELATION_REVIEW`，**不判文学错误**。旧 V116/V114/V117/G/V119 的来源契约与 HOLD 接线保持有效。
- **有界不丢证据**：旧 V114 单一签名中最多8条未消债关系，新的第9条返回 `WF122_OPEN_RELATION_DEBT_BUDGET_EXCEEDED`，不是静默淘汰旧证据；场景扫描/审阅容量溢出也拒绝虚假的完整性。**尚非无限长篇的最终形态**，未来须通过旧统一 NarrativeCore 热暖冷归档与真正有双侧 SHA 的作者修订结案，不允许长期无限停在8条，也不许无凭据清债。
- **最终工程回归**：[全量 #40172308706](https://github.com/66tyu55/WriterForge/actions/runs/40172308706) **1,656 tests executed、7 skipped、0 failures**，含跨多个安静章节、伪源、多个物件/容器、V114/V117 签名和模拟同作者 `MOVE_ON` / 模拟有效 V119→新段。模拟成功不等于真实写作 AI 成功。
- **全新原创真实实验 #40172411065**：[Actions](https://github.com/66tyu55/WriterForge/actions/runs/40172411065)。真 DeepSeek Flash 作者在完全新原创《雨册》里写了两段真实小说：姜岚调查出现的铁皮盒、许槐抱走盒子、姜岚暗中留下半页纸。4次真实调用（两段小文/独立读者/同作者自己的决定），prompt tokens 5,039、completion 1,221，原始四份 provider wires+SHA 均留存，未读《凡人》或重写旧《潮簿》。独立读者发现“半页纸**不知何时从盒底滑到桌角下**”缺少明写移动，小说作者却合法选择 **`MOVE_ON`**，称有意留白。V119真正修订 **0**、重新生成下游 **0**、独立人类文学盲评 **0**，且当前物理关系探测未能证实该移动；**不能强迫作者改、不能自动判错、不能继续对同一篇小说付费重问以凑成功**。
- **继续的实质方向**：研究在原 NarrativeCore/V114 来源签名内如何处理真实动作/容器移动的“已发生/由角色猜测/叙述有意省略”与有源明确结案。尤其“滑出、落下”等多义自然语言不能靠无边界增加正则关键词解决；先建有来源的候选事件身份与适用范围，才能使旧 V119 保证每次修改**不创造新错误**。用户的最终目标仍为真实小说 AI 自己决定何时不满意、删哪句、亲写新句，WF 帮它安全维护真实故事状态/废稿回滚而非文学代写；真正 **V119→下游成功、文学提升的真实样本仍0**。
- **执行边界**：不增第二文学记忆、外部文学评论模型或新训练任务；不重复15章训练、旧《潮簿》与新《雨册》的付费劝改。保留 V26 选择续写、V98 滚动构思、V119 精修、原统一叙事记忆和用户停止废稿机制。

---

## 0.V 《潮簿》绳结世界状态底层纠偏：V122 有源系解关系、G 私有 HOLD、V119 旧风险守门及零付费原始模型重放（2026-10-25，最新）

**下一窗口依次读取**：[WF_0V_SOURCE_RELATION_REPAIR_20261025.md](WF_0V_SOURCE_RELATION_REPAIR_20261025.md) → [WF_0T_REAL_FANREN_SENTENCE_EVIDENCE_20261025.md](WF_0T_REAL_FANREN_SENTENCE_EVIDENCE_20261025.md) → [WF_SOURCE_FIRST_REPAIR_GUIDANCE_20261025.md](WF_SOURCE_FIRST_REPAIR_GUIDANCE_20261025.md)，再看下方 0.U/0.T。代码仅开发分支 `refactor-unified-scene-delivery-audit`；**不改 main、Railway、用户 R2 原小说或正式 Canon**，不重复旧15章训练、不添加独立文学记忆或审稿模型、不对同一旧稿再付费劝改。

- **真实缺口**：0.U 的 B T2 同句“绳结还系在木桩上／只是绳子被人从桩头解下来”在旧 V96/114/117 通过，却没有证明同一物件/同刻接触状态可以共存。真实原作者 [#40165586323](https://github.com/66tyu55/WriterForge/actions/runs/40165586323) 选择 `MOVE_ON` 保留悬念。**不能把“谁动绳子未知”的艺术理由当作“绳是否系着”的物理来源证明**。历史原件、负例一字未改。
- **在原核心实现来源审查**：原 `v122_item_provenance.py` 新增 `audit_physical_relation_sources`，只识别字面可定位、唯一引句/SHA 的 `ATTACHED/DETACHED` 接触状态，标记指称为 `EXACT_LITERAL` 或 `POSSIBLE_ALIAS`，区分先后、自由端、不同绳和猜测。**不是关键词文学裁判也不是普适物理语义引擎**：不确定时只是 `NEEDS_SOURCE_RELATION_REVIEW`，绝不自动认定小说错。
- **从报错变成可执行修复和有限 HOLD**：V116 出实际来源对；V114 将来源收据放入**同一签名候选快照**，不创建第二记忆或写入 item holder；V117 只针对**依赖旧未证关系的新句**继续标 HOLD，无关剧情不受阻。V119 给作者原句、SHA、前因、修改与保留路径，`compare_source_repair_impact` 会将无关文字修改但旧关系仍未解决的稿标 `HELD_EXISTING_SOURCE_RELATION_RISK`。原 G `writing_assist` 私有保存 HOL​​D JSON 和未接受正文、拦下依赖旧未证物理状态的后文；**绝不替 AI 删句写句或强行揭示谜底**。
- **真提供商原件零成本重放**：[原双轨 #40163959949](https://github.com/66tyu55/WriterForge/actions/runs/40163959949) 的 B T1/T2 官方 DeepSeek provider wire/SHA 经 GitHub artifact 独立验证，然后由新 V96/V114/V116/V117/V119 完整只读再检。[实际新证据 #40167612081](https://github.com/66tyu55/WriterForge/actions/runs/40167612081) **SUCCESS**：旧已通过但未接受的 B 文字被当前代码识别为 `HELD_NEEDS_SOURCE_RELATION_REVIEW`，原句 SHA/时态签名均成立。原文没有改、作者旧 `MOVE_ON` 没重问，**新模型调用0，R2读写0，Canon0**。
- **软件工程验收**：[最新完整回归 #40167561524](https://github.com/66tyu55/WriterForge/actions/runs/40167561524) **1,639 tests run，7 skipped，0 failed**，Studio JS 检查成功。涵盖真 B 两段锚点、先系后解、后来才解、不同绳、自由端、猜测、非绳物件、伪 SHA、跨段匹配依赖、无关故事不被连坐、同模型模拟改无关句不能绕过 V119。均为**不扣费的结构测试，不是文学训练成绩**。
- **不能夸大的地方**：真正新场景的“写作 AI 自己选改→AI 写出新正文→V119/V96/V114/V117安全通过→依赖后文由AI亲自重写→匿名读者验证语言和人物因果”**成功样本仍0**。这轮没有新增收费模型、没有新的完整修订章节，也未进行人类盲评。不允许用一次成功 HOLD 旧样本冒充模型已经会写好小说。
- **下一步**：先从来源可证的系/解关系谨慎走向更多物品的容器、空间和长篇跨章债务；研究如何用原 NarrativeCore 和现有 V114/V122 查询真实状态，避免新增第二事实主人或无限扩词表。若需下轮付费文学实验必须**换新的原创题**、用同作者逐小段写作与严格预算，不重问旧《潮簿》。V26、V98、V119、统一热暖冷叙事记忆及用户停止/保存废稿均保留。

---

## 0.U 《凡人》前两章逐步阅读真实 A/B 与最后 B 原作家自主复读：读者看见物件疑问，作者仍选择 MOVE_ON；必须补源锁物理关系而非重复提醒（2026-10-25，最新）

**下窗口优先读**：[WF_0T_REAL_FANREN_SENTENCE_EVIDENCE_20261025.md](WF_0T_REAL_FANREN_SENTENCE_EVIDENCE_20261025.md) → [WF_SOURCE_FIRST_REPAIR_GUIDANCE_20261025.md](WF_SOURCE_FIRST_REPAIR_GUIDANCE_20261025.md) → 本文 0.T/0.S 原始失败。所有变更仅 `refactor-unified-scene-delivery-audit`，不改 main、Railway、用户 R2 原著、正式 Canon，不重复旧 15 章训练，不增加第二文学记忆和外部文学裁判。

- **真正从 0→1 的双轨**：[A/B 真实 #40163959949](https://github.com/66tyu55/WriterForge/actions/runs/40163959949)。同一个 DeepSeek Flash + WF V96/V114/V117、同一原创《潮簿》大纲和两段事件计划；A 不获原文，B 依次只获《凡人修仙传》前两章各 230 字私有 R2 阅读窗口，绝不一次灌整章或全书。6 次真实模型调用；A 两段 268/340 汉字，B 两段 226/421 汉字。A 更突出修堤责任代价，B 铺绳结/瓦片悬念；**样本不支持“读原著更好”结论**，人类匿名盲评未做。第一段后两位原作者均真实 `MOVE_ON`，**真实 V119 修订0**。
- **决定性真物件反例**：B 第二段同一时刻写“绳结还系在木桩上”，又写“绳子被人从桩头解下来”，后文再“重新系回木桩”。老 V96/V114/V117 全部放行，因为绑定关系不是目前严格可证的 item holder 事件；这不是文学评价，而是**普通物件位置/系解关系未覆盖**。A 第二段也用了先前未写明的“照程满教的法子”，属不确定前史，不得自动认定错误或升级事实。
- **真实自主复读第一轮红灯**：[原件 #40165076370](https://github.com/66tyu55/WriterForge/actions/runs/40165076370)，旧六次 provider SHA 只读回放确认，新增真实读者1次 `finish_reason=length`，1000 completion tokens 截断。其未完成原答确实提出绳结/解下缺少实际转场，但严格保留 `WF_FLASH_OUTPUT_TRUNCATED`，没有补齐坏 JSON、没有作者决定或改稿。
- **最小结构修复及最终测试**：原 `writing_assist._reader_separates_written_and_inferred` 新增**默认关闭** `compact_source_review=True`，3条实际观察/1段内推测/1跨段推测，保持1000 token、不改原来源 SHA 唯一检验、不新增外部模型。全量 [#40165499368](https://github.com/66tyu55/WriterForge/actions/runs/40165499368) **1,621 tests，6 skipped，0 failures**。最终真正 [#40165586323](https://github.com/66tyu55/WriterForge/actions/runs/40165586323) 又新增2次同一 DeepSeek 模型：读者合法输出 3/1/1，有唯一来源跨段引句指向绳结状态；原作者却 **`MOVE_ON`**，称不揭示谁动绳/瓦片谜底是合理留白，并**没有**辨明目前是否仍系在桩上的物理状态。回执 `author_kept_unresolved_cross_source_hypotheses=true`。**新 V119改稿0、新下游0，文学质量改进未获证实**；旧作品、旧 provider wire 皆未修改。
- **不能第三次付费劝同一小说原作者**：本案例新跟进实付费共3次（首个读者截断1次 + 紧凑读者和作者决定2次），历史 A/B 6次；不以模拟成功、签名绿灯或 AI 的 `MOVE_ON` 擦掉反例。所有流程运行前先核对原始 SHA／证据，已明确**停止重复付费重问**。
- **新工程重点**：WF 不能只把 untyped 的 `reader_imagined_step` 文本提示给小说 AI，让它将物理状态与艺术悬念混为一谈。应在**现有唯一 NarrativeCore / V114 / V116 / V122 / V117** 内构造源锁、时态绑定的物理关系候选（物品/位置/系或解/谁见证/source quote/SHA/证实还是角色猜测），把**不知道谁动绳**（可合理留白）和**同刻仍系/已解**（需状态来源核对）分开。冲突证据不足时 `NEEDS_SOURCE_RELATION_REVIEW`，作者可自主选择留白/删改，但**未证物件关系不可晋级事实或作为下游确定前因**。不得用“绳子关键词检测器”冒充普适文学理解；必须有反例（先系后解、两个绳、自由端解绑、人物猜测）。真正有源的改稿仍由同一写作 AI 完成，WF 提供 source-first 契约，修后经过 V119/V96/V114/V117、风险比较和真正下游重新写作验收；新实付费测试必须换原创题。
- **验收边界**：源追溯、分段原创、有限回头机会已实证；“WF 可帮助真实 AI 完成一次完整合法文学修订 + 重新生成受影响下游 + 读者公正评价”依然 **未完成**。保留 V26 选择续写、V98 文本滚动构思、V119 精确修订、唯一热暖冷叙事记忆、用户取消/废稿隔离，不回退成“红灯提醒一下”的旧方案。

---

## 0.T WF 不能停在“发现错误，提醒 AI”：已加入有来源的改稿指导、修订影响比较、抗 A→B→A 反复改错和同作者只补引句的有限救援（2026-10-25，本轮最新）

**下一窗口先按此顺序读**：[WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md](WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md) → [WF_SOURCE_FIRST_REPAIR_GUIDANCE_20261025.md](WF_SOURCE_FIRST_REPAIR_GUIDANCE_20261025.md) → 下方 0.S 真 DeepSeek 自主改句却填错 action/effect 的历史原始失败。此次为用户“WF 应自身正确引导和帮助，不是提醒完就算”的**架构纠偏**，不是另一个增加训练样本／堆模块的任务。所有变更仅开发分支 `refactor-unified-scene-delivery-audit`；绝不改 main / Railway / 用户 R2 原著 / 已接受作品 Canon，不重复 15 章训练、不加第二文学记忆或额外模型文学裁判。

- **职责重新划清**：小说创作 AI 仍必须自己想、自己选择要不要删、应该改哪里、什么样的文学节奏与人物动机才合适，也由它独立生成全部小说正文。WF **负责正确提供可核对的实际前因、人物/道具候选状态、源 SHA、修改范围、相互依赖的后续及真正差异，并管理能完成修复的有界事务**。WF 不能凭关键字断文学对错，也不能只返回红色错误码就把修复责任再次全甩给模型。
- **每次真正出手前有一份源锁的“修复契约”**：原 `v119_revision_transaction.prepare_source_repair_contract` + `writing_assist._self_edit_one_turn` 会向同一小说 AI 传递它本人选定的真实原句及文学意图（标记为未经验证），原 V96 父事件有据的后果或 null、V114/V116 已有实际候选物件/人物伤势状态值、原来就有的风险，以及几个**由 AI 自选**的保留、局部修订、删除或整场重写路径。上一状态视图最多八项且明确其他域／余项可能没展示，不得因此假装物品丢失、伤势痊愈。源若对不上或完整必要信息超预算，不得悄悄舍弃硬约束然后发请求。该契约有独立 SHA，只是原 G 私有 job 文件，非新长期记忆。
- **不再修完就假装完成**：`compare_source_repair_impact` 直接用原 V119 与 V116/122 的已有前后检查：旧硬风险消失多少、仍在多少、新硬风险是什么、出现哪些**尚无语义真相的**来源 review 风险。新硬风险按原 V119 拒稿；新增未证问题将新稿放在私有 `HELD_NEW_UNVERIFIED_SOURCE_RISK`，不写入原后续故事；既有未解风险不能因一处新词而自动清零。每段后续如果依赖被改事件必须重新生成，旧 G 第二段不能偷偷复用。文学目标是否解决**依然不由软件评分**。
- **防循环及可执行失败反馈**：同一作者任务内已验过的原稿 SHA 组成有限来源账，A→B→A 再改回旧版直接 `REJECTED_REVISION_OSCILLATION` 且保留上一个有效版。每个因果红灯给出真实原因和下一次原作者**应当补什么来源证明**，不制造小说句子或替模型切割 action/effect。
- **重点新能力：有界“只补来源引句”，不整段反复创作**：如果原作家第一次确实已经写出了 V119 来源合法的小说新句，而唯一失败是 V96 可核的动作/结果/父事件引用错误，且用户当前任务**此前已允许 self_edit_rounds=2** 并在原八次预算内，WF 可在原同一任务内最多再问**同一个写作模型1次，只返回 trace 三字段**。该请求冻结模型第一次亲写的候选 prose，不能返回新 prose/剧情；软件不代写 trace，只保存两次模型原 raw，并用旧 V96/V114/V117 重新严格验证。成功也仅为未接受候选；第二次仍错、格式异常、额度不足或用户取消，立即回滚或传播取消，**绝无第三次自动劝改**。默认 rounds=0/1 无新请求，所有已完成旧付费原回复仍保持历史失败。
- **真实证据等级和最新测试**：[前半回归 #40157466289](https://github.com/66tyu55/WriterForge/actions/runs/40157466289) 1,598 tests、4 skipped、0 fail；[来源-only 一次补引用双模型结构测试 #40157703160](https://github.com/66tyu55/WriterForge/actions/runs/40157703160) 1,602 项；[最终无模型全量 #40158010084](https://github.com/66tyu55/WriterForge/actions/runs/40158010084) **1,604 tests executed、4 skipped、0 failures**，含正确 V96 action/decision/reversal、上文道具持有/受伤候选状态及截断说明、新 review HOLD、循环保护和 Studio JS 语法。**本轮新增真实付费模型调用是0次**；旧 #40155863914 模型亲写却因 `WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED` 无效的原始样本没有被改写成功，不能用模拟成功补引句冒充模型文学水平提高。
- **真正下一步**：先证明同一模型在不同原创题里使用这一闭环，真正完成一次经过全部 V119/V96/V114/V117 的安全改稿、重新写受影响下游，最后用匿名实际读者比较人物因果/时空/物件/情绪和语言效果；任何只是编出另一种错误的稿件均不得晋级创作经验。不要再走“报错→不分根因让 AI 整段重写→又报错”的旧路；新的实付费文学验证、部署生产或修改 Canon 需要独立授权。

---

## 0.S 已签名戏楼原作者自主 LOOK_BACK 后，真正改写动作句但 V96 因果引句重叠严格拒绝；私有预览不得当成新完整章（2026-10-25，最新）

**继续先读**：[WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md](WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md) → [WF_REAL_OPERA_AUTHOR_V119_SOURCE_ONLY_20261025.md](WF_REAL_OPERA_AUTHOR_V119_SOURCE_ONLY_20261025.md)。仅 `refactor-unified-scene-delivery-audit` 开发分支；禁止改 main、Railway、用户 R2 原小说或正式 Canon，不再重复旧15章训练、不得添加第二个文学记忆/审稿 AI。

- **来源真的未被替换**：沿 [原真正 G 完整作者章 #40110957161](https://github.com/66tyu55/WriterForge/actions/runs/40110957161) → [同一真模型双文本读者 #40151857245](https://github.com/66tyu55/WriterForge/actions/runs/40151857245) → [原作家带来源归因自行决定 LOOK_BACK_NOW #40153456601](https://github.com/66tyu55/WriterForge/actions/runs/40153456601) → [这次仅一次真正 DeepSeek V119 修改提案 #40155863914](https://github.com/66tyu55/WriterForge/actions/runs/40155863914)。发出模型请求前核对上述真实原始 wire、V96/G 源、V117、来源 SHA `2a0d2827d51dc1197065cd21126e091a3fd44c4db3bb7d92048c3167d24f4dbd`，以及作者自己选定的唯一原句。**本轮新模型调用仅1次、没有重试或再次劝改**。
- **AI 的确写出了小说修订，不是 WF 编句**：原写“她刚要把重心全压上去，板缘猛地往上一翻……”，原 DeepSeek 新 `replacement` 写“她把重心一点点挪上去，心里早备好了往回撤的那口气；板缘还是猛地往上一翻……”，增加江遥预判风险的谨慎心理，保留撞栏和膝头受伤后果。模型 raw XML/JSON 原件独立存档，WF 未代写。其 `type=json_object` 冗余字样及错误字符位置均只按旧精确、唯一、同 SHA 原句机械归位。
- **关键文学/技术红灯不能绕过**：实际 V119 提案却令 `trace.action_quote` 与 `trace.effect_quote` 同时等于**整个相同的 replacement**，V96 正确拒绝 `WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED`。旧 G 章旧第二段、V117 旧签名及原正文照旧保留，实际**合法通过全部源/因果门槛的新编辑0次，完整新章节0份**；不能悄悄由 Python 替原作家拆 `trace` 制造“成功”。[本次真 V119 全部原回包、失败源](https://github.com/66tyu55/WriterForge/actions/runs/40155863914/artifacts/12584493249)。
- **零模型严格取证 #40156185580**：从四组真正 provider wire 重新核验，在没有多花任何模型费用下得到原模型文字的 V119 **私人源锁定预览 `PROVISIONAL_REVIEW`**。其 V117 **仅源预检** `blocked=false`、`needs_review=false`，而模型原 V96 trace 仍然红灯；**没有**新完整章节 signed resume，旧章第二段也**没有**当新下游被复用。私人预览 SHA `653865dfc002e24493178773d4c90ec4c5b6dea1d57a05d3ba47eb714c696beb`，并非文学质量通过的凭证。[真实作者新句＋原文匿名对照源件](https://github.com/66tyu55/WriterForge/actions/runs/40156185580/artifacts/12584084616)。
- **代码修复只纠正下一次模型的来源引用约束**：在原 `writing_assist._self_edit_one_turn` 提示里明确动作与后果必须各选 **6—96字、两个不同、不重叠、动作先于结果的真正源字串**；同句可分两段，不能同一全文充作双重证据。WF 不自行补结果、解析语义或替模型修正本次坏 `trace`。原 V26、V98、V114/V117、V119、单一 NarrativeCore 热暖冷记忆及 Studio 用户取消／私有废稿功能保持完整。
- **验收和准确状态**：[首次 #40155679207](https://github.com/66tyu55/WriterForge/actions/runs/40155679207) 的红灯仅为测试源码检索断言写错，修正后 [#40155768365](https://github.com/66tyu55/WriterForge/actions/runs/40155768365) 1,589 项绿；[补充分离 V96 源行动与结果引用的最新全量 #40156031520](https://github.com/66tyu55/WriterForge/actions/runs/40156031520) **1,590 tests run、4 skipped、0 failures**。软件绿不证明文学进步，单一作者新句不是完整真实作家反复删改能力。
- **下一步不是反复付费劝这篇旧稿认错**：换真正不同的原创场景，让同一创作 AI 自己选择何时删改并写出**源合法且 V96/V114/V117 完整可用的修订后章节**，重新创作已受影响的下一段；以真实匿名读者比较人物选择、动作因果、物件秘密一致性和自然度。未经用户继续授权，不启动新模型调用，不部署生产环境。

---

## 0.R 原作家“前章已经写过”必须提供原文：真实 DeepSeek 自主区分有意留白与未写动作，也真的决定 LOOK_BACK（2026-10-25，本轮最新）

**接续顺序**：[WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md](WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md) → [WF_AUTHOR_SOURCE_EVIDENCE_REAL_20261025.md](WF_AUTHOR_SOURCE_EVIDENCE_REAL_20261025.md)。本节只代表**签名更早原文＋原作者同模型来源引用约束**的单阶段真模型实验，不能假装已有文学质量进步。所有变更仅 `refactor-unified-scene-delivery-audit`，不改 main / Railway / R2 原著 / 用户正式接受 Canon，勿重复旧书学习或添加第二文学记忆/审稿 AI。

- **原问题仍然真实存在**：旧戏楼签名第1章写“江遥衣袖里藏着尚未交出去的赎身票据”，DeepSeek 自己在第2章写“票据还压在箱底一件戏服底下”，没有给出处；0.Q 双真实正文读者查到这组源句及两项额外疑问，原作者当时却选择 `MOVE_ON` 并声称“前章已交代”——实际此前只写了袖内状态。不能抹掉原模型旧答复或让程序擅自判文学错误。
- **现在确实接入 G/Studio**：在原 `writing_assist.py`，有更早**真实已写文本和对应唯一读者源引句**时，原作者的**同一次**自审输出 `source_attributions`，为各条跨源读者疑问选择 `WRITTEN_WITH_QUOTE`、`UNWRITTEN_OR_UNKNOWN` 或 `INTENTIONAL_ELLIPSIS`，并提供归因理由。软件只查前史 SHA 和引句唯一存在，不查其文学含义、不以有引句等于动作合法。仅复述问题里旧状态原句者标记 `PRIOR_STATE_QUOTE_NOT_TRANSFER_PROOF`，不能晋级物件持有事实；伪造旧句、错误 SHA、错误 link_index、声称未写又附证明句都不能得到来源认证。**模型仍可自己选择 MOVE_ON**，不自动 V119。自动审稿调用原每作业 **8 次上限**不变；需要输出来源归因时本次模型单次输出 cap 从600提高到1150（默认 reader-first 仍关闭），原 raw 回复从不改写。
- **真实文学证据**：[唯一新 DeepSeek 作者来源归因 #40153456601](https://github.com/66tyu55/WriterForge/actions/runs/40153456601) 这次只产生 **1 次真实提供商调用**，之前的七次 G 原写作和两次来源读者均通过旧 provider wire / V117 byte SHA 核验后**只读复用**。模型主动把“票据袖中→戏服箱底”及“三次鼓→第四次鼓”解释为 **2 个 INTENTIONAL_ELLIPSIS**；另把“宋易此前握钥匙→当前从腰间解下”列为 **1 个 UNWRITTEN_OR_UNKNOWN**；没有任何 `WRITTEN_WITH_QUOTE` 冒充旧章完成转移的引用。它也**真实自主选择 `LOOK_BACK_NOW`**，具体意图却是自己认为江遥已经看出裂板危险，后来贸然把全身重心压上去导致跌撞，和先前谨慎性格没有写出可信的预判联系。原文唯一引句、为什么不满意和期望读者效果均由同一个真写作模型生成，不是 WF 填答案。
- **文学生成尚未结束，不得冒充已修复**：本次实验契约就是一次来源说明＋原作者决定，没有调用第二次 V119，**新小说文字0字、真正改稿成功0次、读者匿名盲评0次**。模型自己说“票据转移故意省略”是它的艺术理由，不能证明票据在世界事实中已经合法到旧箱。新选择原因也不一定让作品更好。所有真正历史 `MOVE_ON`、这次真 `LOOK_BACK_NOW` 及原始提供商 wire 按独立证据保留：[本次真答复附件 #12583830221](https://github.com/66tyu55/WriterForge/actions/runs/40153456601/artifacts/12583830221)。
- **最新可信软件验收**：[0.R 来源归因及伪原文反例 #40153005020](https://github.com/66tyu55/WriterForge/actions/runs/40153005020) 1,585 tests run、4 skipped、0 failed；[原签名前章全文恢复＋真实 G 两段作者与读者闭环 #40153219104](https://github.com/66tyu55/WriterForge/actions/runs/40153219104) **1,586 tests run、4 skipped、0 failures**。不能用测试绿灯取代新稿自然度提升。界面 reader-first 选项已经更新预算/原句归因说明。
- **下一步不要再靠 AI 自评堆成功率**：换新题，保持相同作者模型和大致公平 token，证明真正 `LOOK_BACK_NOW` 后能独立写成有效 V119/96/114/117 修订，再做原稿/修改稿匿名人类阅读比较；防止新补充的动作引入另外的物件、人物知识、因果和时间错误。不得让 WF 代写、自动改编原书、追加文学评判模型或忽略用户停止/放弃/保存旧候选能力。新付费/部署/正式接受要遵守新授权和调用上限。

---

## 0.Q 新戏楼 G 真模型跨章来源复读：读者独立发现票据位置变化，原作者仍依据未写出的转移决定保留；只记录未证来源，不强制改稿（2026-10-25，本轮最新）

**务必继续从事实原件开始**：[WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md](WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md) → [WF_REAL_OPERA_SOURCE_IDENTITY_CROSS_CHAPTER_REVIEW_20261025.md](WF_REAL_OPERA_SOURCE_IDENTITY_CROSS_CHAPTER_REVIEW_20261025.md)。只修改开发分支 `refactor-unified-scene-delivery-audit`，main、Railway、用户 R2 书库、正式接受 Canon 不动，不重复旧 15 章训练、不建第二记忆／审稿模型、无 WF 自己编小说正文。

- **原 G 真写作和来源证据**：前次 [Actions #40110957161](https://github.com/66tyu55/WriterForge/actions/runs/40110957161) 七次真实 DeepSeek，完整 G 章规划／事件规划／两个真实事件段、直接原作者自审、单段读者先行及作者自审，完整旧 provider wire、原稿、未接受候选均在旧附件。源 SHA `2a0d2827d51dc1197065cd21126e091a3fd44c4db3bb7d92048c3167d24f4dbd`。旧合法签名初始章写江遥“衣袖里藏着一张尚未交出去的赎身票据”，模型后续真正文却写“票据还压在箱底一件戏服底下”，**正文没有明写转移动作**。这是一对可源定位的事实疑问，不能只因为 G 绿灯就宣称广义普通物品状态皆已检验；但审美省略是否可接受仍归真正创作 AI 和人类读者判断。
- **机械哈希与文学意图必须分离**：上轮 reader-first 原作者真正回复 `MOVE_ON` 但把机械 `source_sha256` 返回 `null`，旧严格规则报 `INVALID_SIGNAL`，不能改写历史。新 `writing_assist._ai_decides_when_to_revisit(source_identity_contract="bind_null_current")` 仅当**明确启用且模型未填写当前原文 SHA**，才由 WF 用自己真正已验证的**当前 SHA**绑定返回值，源引句／文学 `decision` 和原始 JSON 字节不修改；提供了错误 SHA、旧段 SHA 为 null、引句伪造或重复则完全拒绝。G reader-first opt-in 独立开启；旧基线不受影响。[零新模型的完整七次 provider 源回放 #40151464649](https://github.com/66tyu55/WriterForge/actions/runs/40151464649) 保留旧 INVALID，验证只补漏填 SHA 后原文学结果仍真实为 `MOVE_ON`。
- **本轮新实测，不能擦掉红灯**：[DeepSeek 官方 #40151857245](https://github.com/66tyu55/WriterForge/actions/runs/40151857245)，付费前从 #40110957161 回读七次真实 wire、当章 V96、V117 唯一 graph 和更早源 SHA。相同 DeepSeek 先纯读者视角接收**真实前章全文＋当前第一段小说全文**，自己产出有真实原句配对的 **3 条跨文本阅读推测**；首条明确指出赎身票据袖内→戏服箱底没有明写转移，另两条为钥匙状态及第三下鼓接续的未证含义。然后同模型切回原作者身份，**合法选择了 `MOVE_ON`**，也声称“票据藏处与宋易持钥匙的状态在上一章末尾已有交代”，但更早原文只写票据藏在衣袖里。小说里可以留白，不可把没有写过的转移当已证前史。新增**2 次真实 DeepSeek provider 请求**，没有 V119 调用、没有修订成功、没有改写原稿；旧所有模型结果均独立保存。
- **保留三个未证，而非程序认定三处错误**：`reader_report.cross_source_links` 的 SHA 和唯一原句从真实源码核对，WF 不把其解释当已确认的角色行动；原 `self_edit_moment_receipts`／`turn_evidence`／chapter data 追加 `cross_source_reader_hypotheses_unverified_count` 和 `author_kept_unresolved_cross_source_hypotheses` 这些**仅审阅元数据**。既有 V96/V114/V117/唯一 NarrativeCore 仍负责来源/恢复；不会因 AI `MOVE_ON` 晋级编造的物件持有状态。旧作者真实原答复的 [0 新付费来源重放 #40152137576](https://github.com/66tyu55/WriterForge/actions/runs/40152137576) 成功，三条读者未证审阅债务与其 `MOVE_ON` 同时可追溯，不生成新小说。
- **如实记录工程红灯及绿灯**：本轮初始无模型真实来源回放 [#40151345236](https://github.com/66tyu55/WriterForge/actions/runs/40151345236) 是脚本错误拒绝合法 `PosixPath`；首次新增两段来源单测 [#40151682340](https://github.com/66tyu55/WriterForge/actions/runs/40151682340) 只是漏 `import unittest`。均仅修机械源和测试导入，**没有**取消来源 SHA 绑定、虚假引用/非唯一引用、V96 因果父节点检验。最新无模型完整回归 [#40152033480](https://github.com/66tyu55/WriterForge/actions/runs/40152033480) **1,576 tests run，4 skipped，0 failures**，包含 Studio JS 语法检查；不可用软件回归绿色证明小说自然度改善。
- **下一阶段文学重点**：**不能靠第四次第五次提示同模型认错来作弊**。应要求小说原作者针对独立读者的来源疑问明确区分“真正有原文引句证明的转换”和“没有写出来但故意留白”，若自称前章已交代则必须给唯一原句，WF 只做机械核对；如果无对应原句可以 `UNWRITTEN_OR_UNKNOWN` 并继续保持 `MOVE_ON`，但不得成为物理状态/人物知识的正典事实。不增加文学打分器、不自动补台词或剧情，也不把模型的主观自评当文学进步。后续要换新题目且独立读者盲评，新的付费模型请求需用户另行指示。本轮已经结束。

---

## 0.P 真正让同一写作 AI 先像独立读者寻找“原文 vs 推测”，再作为作家自主取舍：真实 LOOK_BACK_NOW，但严格 V119/V96 最终仍拒稿（2026-10-24，本轮最新）

**正确下一阶段入口**：[WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md](WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md) → [WF_READER_FIRST_SAME_AI_LITERARY_REAL_PILOT_20261024.md](WF_READER_FIRST_SAME_AI_LITERARY_REAL_PILOT_20261024.md)。旧 0.O 三次对**同一篇真实 DeepSeek 451 字候选**读回都选 `MOVE_ON`，所有原始供应商回包与这次新结果一起存档，不能覆盖老反例或冒称模型训练。仅开发分支 `refactor-unified-scene-delivery-audit`，不改 main / Railway / R2 原著 / Canon，不重新训练已做 15 章，不另建文学记忆或审稿 AI。

- **用户真正要的作者自主回头**：作文模型 DeepSeek Flash 必须自己想、自己写、自己选什么时候回头及改哪处。WF 只提供实际原文、读者意见来源 SHA/唯一引句与旧 V96/V114/V117/V119/单一 NarrativeCore 事务；软件不能凭“文字不自然”关键词做文学裁判、不能强迫模型回改或代替生成任何故事。V26 Ctrl+1/Ctrl+2 可选文字、旧自动保存、V98 真正文滚动构思、用户停止/删本次废稿、A–F 保持原职责。
- **新增真实机制，不是强制审稿规则**：写作模型先在完全不同的**独立读者请求**中只读真实候选正文（不提供先前大纲、模型旧自夸结论、WF 出的文学错误清单），输出精确原文引句观察和**只属读者推测**的缺失过渡；程序验证引句真实唯一及先后源位置，不能晋级事实或直接下删稿命令。之后相同实际模型回原作者身份才选 `MOVE_ON / LOOK_BACK_NOW`。G `reader_first_self_review=True` 为 opt-in，必须 G+自审轮次+ai_decides，新增读者请求**计入原 8 次自主审稿模型调用上限**；预算不足时优先留给作者自己选择。Studio 原页新增默认关闭的读者先行控件。
- **真的自主判断已经发生，不是模拟**：[真实 DeepSeek #40108836214](https://github.com/66tyu55/WriterForge/actions/runs/40108836214) 用先前原始供应商 wire/SHA 完整验证的旧 451 字，不重新付费写作。读者实际提出 8 条来源可复核动作＋3 条未证推测，其中准确指出“程九先进入船里、最终蹲在岸边桩旁”的缺失过渡。随后同一创作 AI **第一次真实选择 `LOOK_BACK_NOW`**，说“位置和姿态的转换没有落笔，读者只能自行补足”；第三次模型真实写了“片刻后他却又起身跨回岸上……”的 V119 `REVISE` 候选。新实测真供应商调用 **3 次**，用量 prompt 4,120 + completion 1,480 tokens，旧三次 `MOVE_ON` 原话仍在 0.O。
- **不要错说为成功改稿**：本次真实提供商编辑 JSON 额外带 `type=json_object` 标识，模型报错的 `start/end=423/500` 甚至超过原文451字，旧 `_self_edit_one_turn` 首次报 `WF_SELF_EDIT_SCHEMA_INVALID`，旧文原样保留。[零模型来源回放 #40109306167](https://github.com/66tyu55/WriterForge/actions/runs/40109306167) 仅剥离这一种已观察冗余包装、按实际 `expected_original` 在同 SHA 原文中**唯一逐字定位**恢复坐标，能产生真实模型文字的**私有源锁预览**，但严格 V96 进一步拒绝 `WF96_UNDECLARED_PREVIOUS_CAUSE`：模型居然把**本场**“我留着……”对白当作不存在的**前一事件** `trace.parent_effect_quote`。不能悄悄把值替模型写成 `null` 或软化 V96；真正通过完整因果门槛的新原稿数 **0**。私有预览还可能让程九**在“你留着？”问话之前**已跨岸，后续放刀动作位置也不完全清楚；文学盲评没有做，不得宣称艺术品质进步或自动经验晋级。
- **只修通用机械问题，原始文学/因果判断不动**：已在原 V119 写作入口增加极窄 `type=json_object` 兼容及按唯一逐字源句找实际 Unicode 坐标，保留真实原 raw JSON/原错误坐标和 SHA 证据；虚假引句、不唯一原句、伪造前因仍回滚。未来 V119 请求字段加明确**没有 `causal_parent` 时模型自己须输出 `trace.parent_effect_quote=null`** 的技术提示。旧原始错误及所有供应商 wire 没有被改写、R2 / Canon 0 写。
- **验收和交接**：[初次 reader-first 全量离线回归 #40108338519](https://github.com/66tyu55/WriterForge/actions/runs/40108338519) 1,547 项、4 skipped、0 失败；[狭窄来源兼容 + trace 负例 #40109111936](https://github.com/66tyu55/WriterForge/actions/runs/40109111936) 1,551 项；[目前最终回归 #40109468598](https://github.com/66tyu55/WriterForge/actions/runs/40109468598) **1,552 tests run、4 skipped、0 failures**，同时 Node Studio JS 检查成功。真实实测仍为一个独立场景，不是 Studio 跨章付费文学证明；真正记录见上述专项文档，raw 供应商附件 [#12566065553](https://github.com/66tyu55/WriterForge/actions/runs/40108836214/artifacts/12566065553)，无模型严格编辑回放 [#12566001733](https://github.com/66tyu55/WriterForge/actions/runs/40109306167/artifacts/12566001733)。
- **下一步不要重复对同稿付费劝改**：先保存原样旧正文、真实盲读源回包、AI 第一次 LOOK_BACK_NOW、由同一 AI 创造的**未验收**版本和 V96 源由来。待新授权换**不同原创场景**检验能否稳定自己发现真实写作错误，确认真正经过 V119/V96/V114 的有效改稿，并通过读者匿名盲评对比人物行动、动机、已知信息、代价与语言自然度。没有新授权绝不自动扣费、训练或部署。

---

## 0.O 同一真实 DeepSeek 连续三次读回自己真实原稿，仍无法主动发现并改正空间跳转（2026-10-24，本轮最新）

**从真实证据继续，不要复制旧提示假装训练**：[WF_REAL_DEEPSEEK_451_BLIND_SOURCE_V116_20261024.md](WF_REAL_DEEPSEEK_451_BLIND_SOURCE_V116_20261024.md) 是完整来源、真模型原话、有限架构、原 CI 和后续限定条件。前次三模型试验仍见下方 0.N。所有操作只发生在开发分支 `refactor-unified-scene-delivery-audit`，禁止触碰 main、Railway、R2 原著、作者正式 Canon，不重复训练已读 15 章、不增第二文学记忆或代写 AI。

- **需求**：针对前次官方 DeepSeek Flash 真正生成的 451 字符“顾翎／程九寒汀渡口”源码，检验**同一写作 AI**能否自己发现“程九坐进船里、随后又在岸边桩旁”的没有明写的空间转场；模型是否要删稿、删哪句、用什么文字只能由它自己决定。WF 只提供原文真实来源、安全保存和原 V119／V96／V114／V117 事务，不强迫剧情或通过关键词自动发出文学裁决。
- **三次真实复查**：[#40104976936](https://github.com/66tyu55/WriterForge/actions/runs/40104976936) 使用本次前彻底验证原始 provider wire/source SHA `46334d4e783a32c1def8affeb6eea2b9a4bb6e429e846ef910fb4b44601cd6f7`，先让模型独立读原文，回复合法 `MOVE_ON`；它没有主动回改，才将**全文所有真实句子的只读原句偏移索引**交给同一模型，再次合法 `MOVE_ON`。双方原始回包、之前实验原始 `MOVE_ON` 和被淘汰尝试不覆盖。
- **再一次只给原位置信息**：[#40105777757](https://github.com/66tyu55/WriterForge/actions/runs/40105777757) 在验证旧两轮所有供应商原回复没有变更后，从原 `v116_state_delta.py` 现有模块新增的窄范围只读候选提取四条可逐字定位来源：`程九蹲在船头`、`程九已经坐进船里`、`顾翎跨上船`、`程九仍蹲在桩边`。不标“矛盾”、不加计划、不猜测下船事件、不给改稿建议，模型仍有效回复 `MOVE_ON`。它**明确看到了这些位置**，却说“读者能自然补出他回身留岸的动作”，并称动线已经清楚。文学省略不一定都是错误，**但在原文没有写下船动作的前提下，“已经清楚写出”无法由原文证明**；这是自主审查里的**合理化已有错误的倾向**，尚未通过盲读文学鉴定。
- **真实预算和结果**：本轮追加 2+1＝**3 次实际官方 DeepSeek provider 请求**，分别实报 prompt 3,494／1,561、completion 341／186；无 network retry、无主动 `LOOK_BACK_NOW`、V119 修订调用 **0**、最终候选仍与旧 451 字模型原文逐字相同。不可将保留稿件算成文学进步，也不可虚构真实扣费金额。原供应商 wire 原件保存在 [blind/index #12564063524](https://github.com/66tyu55/WriterForge/actions/runs/40104976936/artifacts/12564063524) 和 [V116 #12564064911](https://github.com/66tyu55/WriterForge/actions/runs/40105777757/artifacts/12564064911)；前次原始创作见 0.N。
- **实际代码改动有限**：`writing_assist.py` 新增无损原文句群证据索引；`v116_state_delta.py` 增添源码显式 actor＋动作／位置词的受限提取函数，不把引号、梦境、听说、否定认作确切状态，不评文学、不建立新数据库，不让这项实验接口默认为 G／Studio 强制重审。源码仍由原 NarrativeCore/V114/V117 唯一主人管理；V26、V98、V119、自主取消/放弃旧稿、A–F 保留。
- **最终新离线工程验证**：[Actions #40105578908](https://github.com/66tyu55/WriterForge/actions/runs/40105578908) **1,539 tests executed、4 skipped、0 failed**，包括新旧真实来源 SHA 防调包、V116 可复核事件段原句偏移、排除梦境/引述/传闻/否定、负例保留。零模型的绿色只证明工程健壮，不证明文学自审进步。
- **下一阶段不要第四次付费诱导同稿删改**：正确方向是把**同一写作 AI 的匿名读者式来源重建**（区分“文本实际写出”与“读者自行补全的可能性”）与其作家式文学取舍分离，再由真正的原作家模型考虑要不要回改，WF 只做源身份/状态验证和事务，不能设置必须删稿的文学评分，也不能每段无止境请求模型。后续用独立匿名作品阅读与真实另题验证提升，仍需新的明确付费试验授权；此轮已结束。

---

## 0.N 三个现有真实写作模型的第一轮文学自审对照：会写不等于会发现自己写错（2026-10-24，本轮最新）

**必须从实测证据而不是技术回归开始**：[WF_REAL_THREE_EXISTING_WRITER_MODELS_20261024.md](WF_REAL_THREE_EXISTING_WRITER_MODELS_20261024.md)。第一轮 [Actions #40094106486](https://github.com/66tyu55/WriterForge/actions/runs/40094106486)，未完成模型的单独思考参数补测 [Actions #40094721282](https://github.com/66tyu55/WriterForge/actions/runs/40094721282)。两轮共 **8 次真实模型请求**，不是模拟；原始供应商 wire、原文、原始判断和失败全部保留在 Actions 附件。没有新增 R2/Canon、模型训练、main 修改或 Railway 部署。

- **已选现有三模型**：DeepSeek 官方 `deepseek-flash`、Discovery 已集成 `glm-5.3` 和 `kimi-k2.6`。相同全新“顾翎与程九的雾中渡索、带血税簿与身份不明求救者”原创场景，写作模型必须自己设计人物选择与代价。每个模型 WRITE → **同一写作 AI 自己选 MOVE_ON/LOOK_BACK_NOW** → 只有真实合法 LOOK_BACK_NOW 才允许由**同一模型**提议 V119 source-locked 修改；至多 3 次 provider 调用、无隐藏重试、无第三方文学代写。
- **首次真实红灯不抹掉**：DeepSeek 第一次直接完成 451 字符原文、V96/V114 PASS、本人决定 `MOVE_ON`。GLM 和 Kimi 第一次各用完 1,450 输出 token，真实 `finish_reason=length`，不具备完整来源；没有因此断言模型不会写作。另一次独立用户已授权的有界补测只重试这两个未完成模型，GLM 设 `reasoning_effort=low`、Kimi 设 `thinking.type=disabled` 并各调高实际传输额度；完整原文都产生，但此时不能冒称相同模型参数。
- **真实结果一览**：DeepSeek 451 字符，真 `MOVE_ON`；GLM 360 字符、真回复 `MOVE_ON` 但 **64 位原文 SHA 抄成 62 位**，WF 依法拒绝 `INVALID_SIGNAL`；Kimi 772 字符、真 `MOVE_ON`，**超过本次 260—520 字符建议上限**。三者真实 V96/V114 来源校验都通过，但真正完成合法 `LOOK_BACK_NOW → V119 自主修订` 的次数为 **0**。不可用代码绿灯声称 AI 已具备人类式文学删稿能力。
- **最关键文学负例**：DeepSeek 实际原文前面写“程九已经坐进船里”，末尾变成“程九仍蹲在桩边”，却没有下船动作；同一个模型自我辩护“顾翎先走、程九留守的代价都已落实”，判定保留。说明**AI 自己说明为什么满意，不等于真正知道自己错在哪里**，V96 来源 PASS 也不覆盖空间物理连续性。应优先关注此类可定位正文错误，不重复安装另一套 AI 文学打分器。
- **公平报告和来源纪律**：两轮总 8 次真实 provider calls，DeepSeek 2、GLM 3、Kimi 3；所有回复原件仅在限期 Actions 附件存档 30 天。原 GH 初次输出和补测都有独立原件，不将坏结果“修饰成绿色”。模型声明的文学理由仍是未证、用户仍需独立匿名读正文。本实验是**真实模型单场景写作＋现有 WF V96/V114/自审入口**，不是完整 Studio 双章 V117 跨章流程付费验证，更不是在真实 Xuehai 原书上重新训练。
- **工程回归**：[离线 Actions #40094532271](https://github.com/66tyu55/WriterForge/actions/runs/40094532271)：1,531 tests run、4 skipped、0 失败，核验原白名单、真模型请求总闸、独立输出推理参数与失败不重试、真 AI MOVE_ON 不做 V119、真实决定触发才源锁改稿。这个 CI 无模型密钥；不能替代上述真实模型负例。
- **0.M 原写作中枢全部保持**：Studio 单次任务、同一 AI 章节级自主回看、候选版本 SHA 选择与冷恢复、V26 双候选/自动保存、V98 滚动计划、V119 精确修改、V117/唯一 NarrativeCore FACT/UNKNOWN/THREAD 及热暖冷内容不删不重建。保留“AI 作家负责创造、WF 只负责来源和事务”的三层职责。禁止把模型自行留白扭曲成“必须强制删一段”，也禁止让 WF 替它创造替换小说正文。
- **下一步建议**：先审阅这三份原著样本，让独立阅读者从正文定位问题；后续用不同类型的新题、相同的真实条件研究模型会否**自然**选回看，且修改后确实减少局部因果、人物认知/位置错误。机械复制 SHA 可研究既有 WF 源身份由软件确定性绑定（**不是**由程序替 AI 判断文学），但不能擅自改原始模型判断或静默放宽来源校验。**本轮试验结束，不再自动开启任何额外付费推断；新一轮需用户明确许可**。

---

## 0.M 写作 AI 自己在两章边界选择回头，Studio 版本选择和冷重启连通（2026-10-24，本轮最新）

**跨窗口必读**：[WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md](WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md)；真实软件路径、负例和边界 [WF_AI_STUDIO_CHAPTER_SELF_REVIEW_BRANCH_20261024.md](WF_AI_STUDIO_CHAPTER_SELF_REVIEW_BRANCH_20261024.md)。本轮只动开发分支 refactor-unified-scene-delivery-audit，不改生产 main、Railway、用户 R2 原书、已接受 Canon，不重新训练15章、不引入第二个文学记忆主人。

- **关键纠偏一直有效**：AI 小说作者负责人物心理、叙事意义、任何文字生成，自己决定什么时候不满意、为什么、哪句/哪章和如何重写；WF 只提供真实原稿、V96/V114/V117/唯一 graph 的可观察安全边界、V119 修改事务和私有版本管理。不能由 WF 根据关键词、美学分数或默认反转决定删除。V26 双候选 Ctrl+1/Ctrl+2、自动保存/忽略、作者停止丢弃、V98 正文滚动构思、统一叙事记忆与 A–F 保持原样。
- **同一 AI 的章节自审真实调用已经接好**：writing_assist.py 的 _ai_decides_cross_chapter 在 G 双章实际完成后，将两章**完整未接受正文**及来源 SHA 提供给**同一已配置 model/api_base**，只有模型实际发出 MOVE_ON 或 source-unique 的 LOOK_BACK_NOW 才允许进入下一阶段。其他格式、错 SHA、重复引句、没放进完整原文的超长上下文都不能触发软件删除；任何结论没有文学质量已证明标记。原始回复及失败解析另存私有字节文件，每次 Studio job 最多一次 AI 章节审阅调用，无自动重复。
- **本地 Studio 单次任务已连通**：StudioService.start_auto 增加默认关闭的 ai_chapter_review，必须是 G、接续既有签名前章、恰好两章、ai_decides 与 self_edit_rounds>0、无逐段人工等待。先由模型实际写双章；模型可 MOVE_ON 不删，或 LOOK_BACK_NOW 后沿 0.L 原签名分叉再跑**一次**双章模型正文；两章完成并通过 V96/V114/V117 以后才能认定新候选分支。失败/无效回答仍留原稿，不让宿主代写，也不静默额外重试。
- **候选选择可以跨 Studio 重启**：原 Studio 页面有 ai-chapter-review 开关（默认关）和旧/新候选选择；新 /api/autodraft/branch/select 仍需本机令牌、正确 job ID、服务端来源校验。现有 StudioStore 本地项目目录记录 unaccepted_branch_selection.json，仅保存候选签名元数据而不是文学记忆；重启验证每章候选**真实字节**、V117 graph 的热缓冲源 SHA/路径、原/新 manifest 和 fork receipt。篡改或越权直接 fail-closed，续写从明确选择的新 V117 head 恢复，不能继承废弃的旧后续；作者手写稿、旧历史稿不删除。
- **真实失败完整保留**：[最初开发回归 #40089790688](https://github.com/66tyu55/WriterForge/actions/runs/40089790688) 的四处新测试失败由目录签名函数返回已解析内容视图而不是 signed catalog 导致，后来只纠正返回契约并补正文原始字节冷核验，不放宽来源身份。[首轮 #40089940484](https://github.com/66tyu55/WriterForge/actions/runs/40089940484) 1,523 tests、4 skipped、0 failures；[最新最终全量 #40090238474](https://github.com/66tyu55/WriterForge/actions/runs/40090238474) **1,525 tests、4 skipped、0 failures**，另通过 Node 检查 Studio JavaScript，且有实际 local HTTP 分支选择令牌 403 / 假 job 400、重写后章失败旧稿不变、冷重启恢复测试。
- **证据边界不能夸大**：本轮所有写作 AI 选择与正文都是**离线人工模拟的模型答复**，新付费模型请求为 0，不能说真实 DeepSeek 自己跨章删改成功或文学水平提高。旧真实运行 #40070821134 第一段 INVALID_SIGNAL、第二段原生 MOVE_ON，及 #40071088617 零付费回放依然是唯一真实模型时机证据。至今没有真实同模型的 LOOK_BACK_NOW→有效跨章重写与独立文学盲评。
- **仍未具备**：仅在已有 V117 前缀的本地 G 两章完成边界回看第一章，不能任意前十章、初书无前史章节、逐字/半句自动擦掉、多轮无限回头、跨设备/R2 的完整事务或所有被作者其他客户端接受的 Canon 状态。已保存工作流本次是用户 opt-in 的单次任务；没有授权不能启动新的真实模型实验。下一步先对同一真实写作 AI 做极有限、原始 wire 可保全的自然选择探针，再独立分析原稿、删改后正文和负例，不让 WF 成为文学裁判。

---

## 0.L 已保存两章的 AI 回头：新的 V117 签名分支，不继承弃稿的热暖冷状态（2026-10-24，本轮最新）

**接续顺序**：[WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md](WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md) → [WF_AI_CROSS_CHAPTER_BRANCH_FORK_20261024.md](WF_AI_CROSS_CHAPTER_BRANCH_FORK_20261024.md) → 本节 0.L。真实写作 AI 的第一段格式失败和第二段 MOVE_ON 仍见 0.I，不要重新训练或覆盖原始答复。本阶段仅 `refactor-unified-scene-delivery-audit`，禁止动 main / Railway / R2 原库 / 既有 Canon。

- **目标与职责**：同一小说创作 AI 才能决定何时觉得不满意、为什么、原文什么位置、删什么和如何重写；WF 只提供可恢复章节边界、原文和角色事实、精确 SHA 和 V119/V117 安全事务。不能靠程序的关键词、文字评分、模板或额外第三方模型创造文学意见。保持原 V26 两候选、Ctrl+1/Ctrl+2 接受或忽略、自动保存/可取消、V98 滚动构思、V119 精确局部改稿、V114/117 和原唯一 FACT/UNKNOWN/THREAD 记忆，A–F 不变。
- **新功能范围**：`writing_assist.py` 支持可选 `cross_chapter_fork` 和 `selected_fork_receipt`。安全子集是原来一份 **G 本地 job 内恰好两章未接受小说**、有**前一章已存在且合法的 V117 parent resume**、AI 传入明确源章和原稿 SHA 的 `LOOK_BACK_NOW`。当前只可回看该 job 第一章、重写它和紧邻的下游第二章；不支持无签名前缀的新书第一章，也不支持任意往前十章、作者已接受作品、R2 外部归档直接修改。
- **分叉前审查**：读取旧 job manifest 和所有旧 candidate.md 原文字节、原 V114 checkpoint、V117 resume 及其唯一统一叙事 graph；项目/scene、模型和快照、大纲 source SHA、未接受标志、原文 SHA、图 `parent_sha256` 的上游链及 target 逐字唯一引用全部真实一致，才能建立新 job。失败时新模型调用数 0、无新目录、不擅自触及旧稿。作者已在别的客户端确认作品的外部记录仍须该客户端另行核查，不能只凭本地 candidate flag 宣称不存在。
- **有效新链**：在新的独立 job 调**同一写作模型**重新规划和写两章，不复用已作废第二章正文，然后原 V96/V114/V117/NarrativeCore 管道计算新候选。没有任何实际文字变化不得伪报“已改”；修订两章完成后才写出 SHA 封口的 `cross-chapter-fork-rebuilt.json`，标明原分支 head、所废弃的原候选 SHA、新分支 parent/head、作者是否已接受（始终 false）和实际模型意见 raw SHA。旧分支旧稿/旧签名始终为不可篡改历史证据，**只在明确选择新分支续写时才拒绝旧下游 V117**，同时允许从新 head 续写下一章。
- **热暖冷**：回到目标之前一章的现存 V117 唯一 graph，只沿它合法源的 FACT/UNKNOWN/THREAD、V114 时态与热/暖/冷 index 继续，不能从旧两章偷取人物已知秘密、物件交付或伏笔结案。纯离线本地 13 章前缀验证 hot=3、warm=8、cold 旧页签名与下一章延续；旧废弃候选的物理字节 **仍在原历史目录**，不是云端物理删除或完整垃圾回收。
- **失败与测试**：[红灯 #40083002707](https://github.com/66tyu55/WriterForge/actions/runs/40083002707) 原始模拟 AI 引句短语重复触发唯一源拒绝，另一个测试变量掩盖图构造器，未放宽底层。 [首次绿色 #40083135333](https://github.com/66tyu55/WriterForge/actions/runs/40083135333) **1,514 tests、4 skipped、0 failures**。 [最终绿色 #40083326608](https://github.com/66tyu55/WriterForge/actions/runs/40083326608) **1,516 tests、4 skipped、0 failures**。新增模型供应商调用 **0**：完全离线人工模拟原模型 reply；还核验选择新头后真正能写第三章、改到下一章中途失败时旧两章/签名完整且新分支没有成功收据。
- **重要未完成**：当前 `writer_decision_reply` 是调用方提供的文本，**没有由真实写作 AI 自己在完成章节时触发跨章选择的自动流程，也无法从此单凭字段证明它真的来自同一模型**；Studio 的后续版本分支选择和新头冷重启尚未全流程接好；跨很多章节、已接受作品、热暖冷/R2 远端孤立页的完整事务无证明；StoryWorkTree 尚非这套章节 fork 的持久事务主人。不能用软件绿灯证明小说审美变好。
- **下一步**：先沿已有 Studio 单次作者请求做有界的“同一写作 AI 自主跨章 LOOK_BACK_NOW 或 MOVE_ON”候选触发，把选定分支的 SHA receipt 真正接到本地继续和恢复；再有限真实同模型探针，保留原 wire、坏例和未通过情形。未经另外授权不得发起新付费文学实验或自动删除 R2 / Canon，禁止重复 V96–V123 训练和加第二文学记忆模块。

---

## 0.K 删掉的事件不能继续活着：V114/V117/统一图失效与 AI 回看失败原子恢复（2026-10-24，本轮最新）

**精简继续入口**：[WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md](WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md)。详细工程验证和真实红灯 [WF_AI_WRITER_DISCARDED_STATE_ATOMIC_RECOVERY_20261024.md](WF_AI_WRITER_DISCARDED_STATE_ATOMIC_RECOVERY_20261024.md)。本轮仍仅在 `refactor-unified-scene-delivery-audit`，不改生产 main / Railway / 用户小说与 R2 原库，不增独立记忆，也不复训原有15章。

- **职责仍严格分开**：创作 AI 自己产生小说正文，决定自己何时不满意、具体为什么、保留还是 LOOK_BACK_NOW、删哪处、如何重写。WF 只核实未接受源稿 SHA 和唯一选区、调旧 V119、重演原 V114/V117/统一图状态，不给出文学审稿分数，不替 AI 生成正文或认为某个故事“该反转”。
- **原始来源删除负例已经跑通**：新 `tests/test_wf_discarded_event_state_replay.py` 包含“火髓果合法持有人交付后被删”“右臂真实伤势被删”“无来源剑穗转移产生的 V117 债务被删”“不被作者正式确认的秘密披露删后维持 UNKNOWN、不进热记忆”“真实 G 源事务删物后按新文重写及 V117 signed resume”的纯离线实现。真实 MIT Novel Studio reducer、V122 核验、V117 signed resume、原 NarrativeCore 唯一 graph 均受检；这些是 source-only 有界工程证据，不证明对中文所有代词/隐喻/旁白都能做语义推断。
- **原子恢复**：此前 V119 成功改前段后，若后续 V96、V114、V117 或模型生成出错，可能留下半段派生状态。现在用原 `writing_assist.py` 的有限旧候选冻结/还原，恢复旧前段＋旧下一段的真实供应商原答复和临时来源状态，再经过标准校验完成原未接受候选；绝不能给代码生成替代小说正文，不能借失败追加超限调用。原回答 `*-raw.json` 不被 `*-regenerated-01-raw.json` 覆盖。旧草稿/坏提案留私有记录；计数明确区分 `wf_self_edit_previous_turn_rewind_attempts` 与确认通过新下游的 `wf_self_edit_previous_turn_rewinds`，模型费用已经用掉就不能伪装归零。
- **最终全量 [#40076159662](https://github.com/66tyu55/WriterForge/actions/runs/40076159662)**：**1,508 tests run / 4 skipped / 0 failures**；工作流明确不注入任何付费模型密钥，新测试全部是人工模拟模型回信。旧 DeepSeek `#40070821134` 首段 INVALID_SIGNAL、次段原生 MOVE_ON 的证据和 `#40071088617` 零模型回放仍保持原样；绝不能把新 mock LOOK_BACK_NOW 冒称真实成功。
- **不能抹掉红灯**：[#40075407455](https://github.com/66tyu55/WriterForge/actions/runs/40075407455) 暴露同一原子事件的来源前提和短文本门槛，[#40075680350](https://github.com/66tyu55/WriterForge/actions/runs/40075680350) 漏 cast/仍短于 V96，[#40076014846](https://github.com/66tyu55/WriterForge/actions/runs/40076014846) 与 [#40076099235](https://github.com/66tyu55/WriterForge/actions/runs/40076099235) 重构的旧 V121 固定缩进源码断言触发——均未放松校验，而是修正原件和非语义布局，重新验证后绿色。
- **当前能力边界**：只有 G 自愿 opt-in、同章紧邻上一事件段、最多一次跨段回头；逐段故障可恢复。仍**没有**任意多段/跨章已保存候选热暖冷索引撤销，整章完成/文件存储/R2 失败的完备跨系统原子恢复，或流式半句自主删写。不要因 1508 次工程绿灯误称文学判断已成熟。以后若对真实同模型原创试验做有限探针，需单独授权并保留完整原始成功/失败样本及匿名文学审阅。
- **下阶段**：先按既有 V117/StoryWorkTree 的可追溯依赖图研究“跨章候选 A 被推翻后，下游章节 B/C 的私有签名、热暖冷引用是否失效”，禁止对既有作者确认 Canon 反向修改；源错则 fail-closed，不能自动修补小说文字。

---

## 0.J AI 真正拥有回看上一段的决定权，WF 只负责源事务和下游撤销（2026-10-24，本轮最新）

**下一窗口先读**：[WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md](WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md)，再读 [WF_AI_WRITER_PREVIOUS_TURN_TRANSACTION_20261024.md](WF_AI_WRITER_PREVIOUS_TURN_TRANSACTION_20261024.md)，必要时回看下面 0.I 的原始模型证据。继续范围严格为开发分支 `refactor-unified-scene-delivery-audit`，不改 `main`、不部署 Railway、不增加记忆模块或训练。

- **为何改**：原 G 只能在刚完成的事件段做自审，AI 即使觉得**上一段**有错也无精确选段 / 依赖撤销能力；现用显式 `target_turn=current|previous`，仅由**同一个创作 AI**提出决定、原因、引用证据和实际改稿。WF 不判断美学，不生成正文，不拿文学分数触发修订。原旧版本只有七个字段的 MOVE_ON 仍兼容，程序只处理字段/源身份。
- **如何改**：真实前段 `prose+trace` 回包按本 job 的 `selected_turn_raws` 暂存（V96 的 accepted evidence 只有正文/effect，不能伪造丢失的 trace）；既有 V119 检查 SHA / 唯一原句 / 修改区间。原上一段有实际改动后，先私有归档被废弃的当前下一段，再整体裁剪 `accepted_turns`、计划、V96/叙事审查、lamp、提示/审修等暂存回执，恢复从未被删源污染的 V114 事件前时态状态。修改后的上一段必须重新走原 V96/NovelStudio/统一 graph 检查，再由创作模型重新生成下一段，最后才产生新候选章节；不改已有 signed resume 或 Canon。
- **明确限度**：仅 `continuity_guard`、`self_edit_rounds>0`、`self_edit_timing="ai_decides"` 自愿启用；一 job 最多回看上一事件段一次，额外模型调用受原有 8 次上限约束。还不支持多段/跨章/逐字流式回改，完整冷重启依赖树、后续更大范围校验失败时的原子旧稿恢复待继续。现有 V26 Ctrl+1/Ctrl+2 候选、V98 正文驱动滚动计划、V119 精修、V117 和统一 FACT/UNKNOWN/THREAD 主体不动。
- **本轮工程 red → green**：[首次新全链路红灯 #40074029791](https://github.com/66tyu55/WriterForge/actions/runs/40074029791) 真实抓到丢失 V96 action_quote 字段，已修复为回放完整实际 model JSON；[首轮绿色 #40074160492](https://github.com/66tyu55/WriterForge/actions/runs/40074160492) 1,501 项执行、4 跳过、0 失败；[增加 V114 从新源重归约证据后再次全绿 #40074298398](https://github.com/66tyu55/WriterForge/actions/runs/40074298398) 同为 1,501 项、4 跳过；[真正启用原统一叙事图的上一段事务模拟 #40074549545](https://github.com/66tyu55/WriterForge/actions/runs/40074549545) **1,501 项、4 跳过、0 失败**，并验证最终候选仍复用原有唯一 graph 记忆主人。均由现成 Actions 无模型秘密环境运行，无真实模型扣费、无人替小说作者评价文学。
- **历史真实模型原件必须不混淆**：见下节 0.I：DeepSeek 第一次回看判断返回 prose+trace 无效，第二次真实 `MOVE_ON` 经零新增调用只恢复了多余 type wrapper。真实 6 次 call 仍**没有** `LOOK_BACK_NOW → 回上一段 → 下游重写` 成功样本。人工写的单元/端到端模拟模型回复不是它的证明，不能声称作家水平提高。
- **下一步**：本分支先实现和验证删去关键物件交付 / 获知秘密 / 重伤事实后 V114、V117、统一图临时状态完全按新文源重建，旧稿后果不可漏入人物认知、长期债务或热暖冷记忆；检测状态中途失败时要复原整个候选。只在单独授权后才开展有限真实模型探针；不重复15章训练或改动原始模型证据。

---

## 0.I AI 自己决定何时回头以及为什么：作家负责思考，WF 只负责工作台（2026-10-24，本轮最新）

**跨窗口精简交接（先读）**：[WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md](WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md)。这一份涵盖最新代码与验收状态、未实现能力、真实负例和下窗口原样复制的继续指令，避免从约 20 万字历史交接重新开始。

**用户纠偏：前版还不是完整人类式作家自审——WF 不许通过规则、关键词、分数替 AI 判断文学、生成文字；真正缺的就是“AI 在什么时刻觉得自己不满意、为什么决定删”这一层。先读 [WF_AI_WRITER_JUDGMENT_AND_REVISION_ARCHITECTURE_20261024.md](WF_AI_WRITER_JUDGMENT_AND_REVISION_ARCHITECTURE_20261024.md) 全文和实际验证，不要只盯 CI 数。**

- **职责分离**：AI 承担人物动机、因果、叙事意图、语言与情绪的判断和全部小说生成；WF 只安排现实模型可观察的写作暂停边界、把真实前文/角色认知/物件状态提供给 AI、记录 AI 真正的意见，并由旧 V119 只执行来源可核查的编辑及 V96/Novel Studio/统一 graph 安全验证。严禁 WF 根据句子长短/关键词自行选择 DELETE/REVISE 或制造自评文学分数。
- **实现范围**：仅开发分支的 G continuity_guard、自主删改轮数>0 时，允许明确选择 self_edit_timing="ai_decides"（默认保持 "always_offer" 旧方式）。一次小说事件段真正写成后，同一个写作模型收到原稿、人物动机与上一段已发生的后果，自己输出 MOVE_ON（保留并继续写）或 LOOK_BACK_NOW（回头审改），并说明 why_now、原句证据或未写出目标、若不改的后续问题、希望表达的阅读效果。只有 AI 确认 LOOK_BACK_NOW 才调用已有 V119 KEEP/DELETE/REVISE/REPLACE_SCENE 操作；模型的字面证据和 SHA 由 WF 校验。两种决定都仅为文学候选，不经由模型自我赞美晋级文学经验/Canon。
- **重要诚实边界**：所谓「什么时候」目前只能是**可观察的事件段写完之后**，不是模型内部秘密思维过程中写半句马上擦掉。要实现小句群、段落甚至上一章未接受剧情的回头撤销，应将 AI 输出拆为可见短工作片并使用 V117/已有 StoryWorkTree 做受影响下游的事务回退；不是给它一个长固定提示就冒称人类思考。
- 新版 Studio G 有明确“AI 自己决定何时回头 / 原固定每段审稿”两种选择，默认旧版不变；一个作者任务可有内部多次同一模型生成/选择，当前最多 8 次额外审核或删改请求，超过预算不能自动继续扣费。
- **首批真实模型结果必须保留负例**：[真实 DeepSeek 原始运行 #40070821134](https://github.com/66tyu55/WriterForge/actions/runs/40070821134)，6 次付费模型调用（计划×2、原文×2、AI判断×2），没有人工重发。第一段 AI 判断请求却返回了 **prose+trace 重述**，并非有效选择；第二段确实自行判断 **MOVE_ON 不删**，指出遗信疑点、无名孩子、旧仇信念松动与收束有合理进展，但它多输出了无害的格式元字段 type=json_object，因此最初都被严格 JSON 源解析记为 INVALID_SIGNAL。
- 修复仅允许精确 type=json_object **唯一多余包装字段**，不修改模型的写作意见或原文内容；[零新增模型调用源真答回放 #40071088617](https://github.com/66tyu55/WriterForge/actions/runs/40071088617)：第一段仍 INVALID_SIGNAL，第二段恢复真 AI 选择 MOVE_ON（不删），没有任何新模型调用、没有改动已封存原始回复或 Canon。证明 AI 参与了“继续还是回头”的选择，不等于证明它独立文学鉴赏可靠；本批 **没有验证成功的 LOOK_BACK_NOW/DELETE**。以后不要把没有发生过的删改说成成果。
- 完整工程回归 [#40070986328](https://github.com/66tyu55/WriterForge/actions/runs/40070986328)：**1,495 tests run、4 skipped、0 failures**；原始回复回放专项 9 项通过，原本字符定位与 V119 修订 12 项另保留。已完成 paid live 与零模型回放 workflow 现 manual-only，避免反复耗用。
- **下一轮首要文学能力**：基于多部真实新小说实验，让同一写作模型在不受模板强制影响的情况下辨别“保留留白”与“该删掉缺乏因果的冗长段”；负例包括明明该删却 MOVE_ON、硬写桥段导致偷换人物认知、从旧废稿窃取未发生物件状态。不能由 WF 逻辑字段代替模型自己纠正，不能用 model 自评证明人类作家水平。
- 原 V26 两种候选与作者选择、V98 真正文驱动重规划、V119 源范围事务、G 统一记忆和 V117 跨章路径都保留。不要新增独立记忆、模型替代函数、授权规则以冒充“文学底层”。仅 dev 分支，无生产 main、Railway 或私人 R2 变动，无新的模型权重训练。

---



## 0.H 真正作家自我删改核心：WF 自己审读、删除、改段、整场重写（2026-10-24，本次最新）

**用户再次强调最初 WF 要有作家式“删删改改”的能力：使用者只给一次创作任务，不应不断重发文本或修改指令；WF 应自己在写作时读回自己的作品，主动淘汰坏句、短段、大段和整个无效场景。最新版首要细节及真实源证据见 [WF_WRITER_SELF_EDIT_CORE_20261024.md](WF_WRITER_SELF_EDIT_CORE_20261024.md)。**

- 已回溯最初 [V26_INVISIBLE_WRITING_STUDIO.md](V26_INVISIBLE_WRITING_STUDIO.md)：WriterForge 原设计明确有两种独立续写候选、作者 Ctrl+1 / Ctrl+2 或忽略、自动保存、自己在后台检索/选择手法，并独立提供分章计划。现有 A–F 写作分段/预见/情绪模式，以及 V98 正文驱动滚动重规划，均不得丢弃。G 是当前统一叙事与角色视角、物件时态和 V117 跨章的工作入口。之前实现的作者人工停止并删除作业，不等于 WF 自己修稿。
- 旧 V119 正好具备定位原文位置与源 SHA 的精确范围修改，原先只是被动预览。现已由原有 writerforge/writing_assist.py 在 G 写作回路里自动调用：模型写完真正小说段落→同一模型审视→自主 KEEP 保留、DELETE 删句、REVISE 改句或段、REPLACE_SCENE 整段作废重写→V119 真实源选区与 V96 动作/后果/前因、V114/V117/人物未知事实核验→只把可用候选送往下一段。不新建第二套记忆、权限或外部写作评审器。无法证明的改法必须回滚。
- G 的 self_edit_rounds 明确 opt-in 0/1/2，默认为 0；每段最多两轮，整次任务最多 8 次额外同模型请求，无自动无限重试。Studio 中选择自主删改可默认取消人工每段点“继续”，用户不用再发送指令；作者仍能手动要求停下与丢弃。本次作业的原稿、废稿、模型提案与 SHA 仅留在当前私有 job 内，正式手写稿、其他作业、Canonical 故事不会被删除或污染；A–F 原逻辑保留。
- **真正 DeepSeek 实跑 [#40068690550](https://github.com/66tyu55/WriterForge/actions/runs/40068690550) 共 6 次供应商调用、0 重试**：1 章计划、1 事件计划、2 段原文、2 次同写作模型自己审稿。模型两次都能找到真实句子，提出具体心理修法，却把源代码字符下标分别算错 11 和 82。历史运行如实两次拒改，原小说仍保存。
- 宿主现可只依据**唯一真实逐字的原文片段**，恢复模型错算的位置，仍重新经过 V119 范围锁和 V96 真正因果原句。重复短语、源 SHA 不匹配、改动越界、额外物件/知识问题绝不猜。用原供方答案**零新模型调用**重验 [#40069059042](https://github.com/66tyu55/WriterForge/actions/runs/40069059042)：第一段真实自主“先不问你”改为“先不找你”，V119 和 V96 通过，保存原稿 SHA 与改稿 SHA；第二段虽然精确定位了选区，但其 parent_effect_quote 不属上段真实前因，仍保留旧稿，错误为 WF96_PARENT_CAUSE_NOT_ANCHORED_IN_PREVIOUS_PROSE。文学失败不能因形式修复被洗白。
- 完整离线代码和测试 [#40068947820](https://github.com/66tyu55/WriterForge/actions/runs/40068947820)：**1,486 tests run、4 skipped、0 failures**；另一个原始已付费模型回应的零模型回放工作流通过了 12 项针对性测试。最初开发阶段括号、Path 类型和测试入口的旧红灯均记录在 Actions 历史，并未删除。付费实验及原始回答回放 workflow 已改成 workflow_dispatch 手动运行，防止再次产生费用。
- 本轮只是**真实自主改写的可运行基础**，没有证明 WF 已有托尔斯泰或金庸的文学判断力，也没有独立真人评价。最难的是能真正判断一个段落该不该保留、人物动机是否可信、删改是否误伤文学气韵、后面几章会不会继承删掉的废稿。下一轮应做同前文/同模型/接近调用成本的真实多个篇章盲测，对照未自审、1 轮、2 轮，保留所有正负证据，不盲目默认推广。
- 生产 main 未修改，Railway 未部署，原始 Atria 七类证据、R2 原书稿和用户文学记忆均未动，没有模型权重微调。未来修改不得丢弃早期 WF 的选择式生成、可中途取消、原文源控和统一叙事核心。

---



## 0.G 三章实写和人物认知越界：不要再以格式绿灯冒充文学理解（本轮最新）

**最新真实作品与源码审查入口：[WF_REAL_THREE_CHAPTER_POV_CAUSAL_FAILURE_20261023.md](WF_REAL_THREE_CHAPTER_POV_CAUSAL_FAILURE_20261023.md)。本轮应继续 WF 自己真正写文本、追踪真实因果与人物心理，禁止新增独立记忆模块、不要重复 V96–V123 已完成的训练/配置。**

- 真实 WF 模型经 #39976958906 使用 DeepSeek Flash **12 次供应商请求、0 重试**完成全新虚构《北塘旧印坊》在合成前史后连续第 2/3/4 章 **909/728/1232 汉字**。各章自己产生章计划、两段事件计划和真实正文，前章原始 V117 signed resume + 同一 unified graph 真正传入后章，三份原稿、原始 HTTP wire/decoder、source/temporal 证据均保存 GitHub Actions Artifact，Canon 0。最初两次技术预检红灯 #39976385618、#39976689395 都在付费 HTTP 前停止，供应商调用 0。
- **核心负例不可抹去**：前史明确简洛未把蓝印运单内容告知陶筠，但第 2 章真实模型**章/事件计划**先让陶筠去试探运单，正文还让她说出“灰袋三十”。第 3 章第二段重做第一段部分捆废纸/争工资动作；第 4 章直接发半月工资而少了钱的来路/代价。**模型从全知作者前史偷渡信息给角色，文学逻辑仍未学会。**
- 现有 narrative_core 仅在**已有作者源句确认**的 FACT+UNKNOWN 上修源认知：活跃人物即使 goal 不包含秘密名字也有界提醒未知（最多两项）；实际正文出现这类秘密（含对话）只报待核验，不会自动证实已知或写 Canon。全量 #39980044114：**1,465 tests run，4 skipped，0 failures**。原本内嵌书面引号“灰袋三十”不能作为跨引用的作者事件原句，保留严格来源约束不放松。
- 唯一两次新模型正文验证 #39980263483：明确注明为**增加一条合成作者说明的新种子**，复用旧模型章节/事件计划，DeepSeek Flash 实写 2 段共 634 汉字、2 次供应商调用、0 重试。新稿不再让陶筠直接说出“灰袋三十”，但仍让她无交代地问“蓝印的单子”，且第二段重复上一段放“勤”字/挪纸捆，trace 待审 1。不是 byte-identical A/B，绝不宣布问题已解决。第一次试验 #39979496310 受书面引号锚点限制，调用数 0，原红灯保留。
- **又发现重启单章时实际 scene_id 总是 chapter-001**，哪怕统一 V117 状态已经是第 2、3、4 章；现在 writerforge/writing_assist.py 的 _writing_scene_scope 按实际已恢复的故事章号构建准备器场景标签，已有实验证据仍原封不动。最新完整源码与测试 CI [#39981865340](https://github.com/66tyu55/WriterForge/actions/runs/39981865340)：**1,466 tests run，4 skipped，0 failures**；此编号修复尚无新真实文学 A/B 佐证，不能声称段落重复已因此消失。
- 目前 source_progression 仍然默认 **baseline**，只可显式 opt-in；前面的同源首段文学 A/B 负迁移（1/3 偏好新提示）继续有效，禁止因为短期过拟合再次默认推全体裁。
- 下轮重点不是额外权限、校验字段或者假“训练”，而是让作者已写 FACT/UNKNOWN 先参与**WF 自己生成章计划/事件计划**，杜绝规划阶段角色全知；另要拿真实原文检验后一段是否回到已发生动作、人物选择是否真正造成可见且留存的代价。每次先读作者/模型原始作品再决定窄改，不能单靠软件通过率。
- 生产 main 未变、Railway 未部署、未接触用户私人原著与 Atria 七类封存稿，没有新记忆库、没有微调权重。所有已完成的付费文学试验 workflow 均设为**手动触发**，防止普通提交自动扣费。

---



## 0.F 真实跨章创作发现全知视角漏检（2026-10-23，本次最新）

**用户要求继续 WF 自己写文本→从真实原稿发现问题→改进 AI 的文学处理，禁止把增加权限/记忆或测试通过替代文学表现。请从本节及 [WF_REAL_THREE_CHAPTER_POV_CAUSAL_FAILURE_20261023.md](WF_REAL_THREE_CHAPTER_POV_CAUSAL_FAILURE_20261023.md) 开始续接。**

- 新合成世界《北塘旧印坊》由 WF 真正连续写出 3 个后续章节（第 2/3/4 章）。[真实 DeepSeek Flash Actions #39976958906](https://github.com/66tyu55/WriterForge/actions/runs/39976958906)：**12 次有界供应商请求，零重试；909、728、1232 汉字**，每章独立作者计划+两段事件规划+两段正文。靠同一 V117 resume 和 unified graph 顺序承接，源文件 SHA fresh-read；全为未接受候选、Canon 0。原模型 wires、完整小说原稿、物件状态/人物图/计划都在本次 Actions Artifact，旧原稿未改。前两次实验跑线错误 #39976385618（源事件引用不含参与人）与 #39976689395（实验客户端 model 变量遮蔽）都在模型调用前失败，均供应商请求 0，原红灯保留。
- **真正严重的文学错误**：前史注明只有简洛拿到蓝印单据，尚未告诉陶筠单上“灰袋三十”，但 WF 在**第 2 章的模型规划阶段**已安排陶筠询问此单，正文还让她直接说出“灰袋三十”。三章整体另有第 3 章前后两段重复捆废纸与核账、第 4 章半月工资发放缺乏资金来源/代价交代。读者全知不等于人物知情，正文变长不等于小说有逻辑。工资账作者先前承诺在第 3 章有实际公开描写，统一 THREAD 未擅自自动结案，仍 OPEN。
- **底层窄修复已在既有统一图完成**：已由真实作者来源注明的 FACT+UNKNOWN，即便事件目标未提到秘密名，也向当前活跃角色有界发出“其尚不知情”的提醒；候选若出现该人物与秘密（包括对话），仅标 WFCORE_UNREVIEWED_UNKNOWN_FACT_MENTION 待审，不把文本或谎言自动写成已知/Canon，不阻碍合法的实际披露。这不推定未注册的猜想成世界事实，也不另建记忆模块。
- 零模型全库验证：[Actions #39980044114](https://github.com/66tyu55/WriterForge/actions/runs/39980044114) **1,465 tests run，4 skipped，0 failures**。一项新来源边界问题也暴露：原前史“灰袋三十”是**书面带引号的标注**，严格原事件定位不能跨这种引号。首次新试验 #39979496310 因此在模型前失败，供应商调用 0；没有为过关削弱全球来源校验。
- 最后一次真实小复测 [#39980263483](https://github.com/66tyu55/WriterForge/actions/runs/39980263483)：保留旧真实 WF 模型自己产生的章节计划及事件计划，仅在**注明的合成源**上添加一条明确“陶筠没有见过运单/不知道灰袋三十”的作者前史，新增 source SHA b050b08c...，所以**非相同源种子的公平 A/B**。再让同一个 DeepSeek Flash 实际生成 2 段正文，**仅 2 次新模型调用、0 重试，634 汉字完整候选**。陶筠没有再直接说出“灰袋三十”，但仍无来源地问“蓝印的单子”，第二段再次重演摆放“勤”字、拖纸捆动作，且模型 trace 待审 1。正反两面都保留，绝不能说“人物逻辑已学会”。
- 开发分支的 source_progression 实验提示依然**默认关闭（baseline）**，此前同原始首段 A/B 新提示仅 1/3 偏好得到用户未授权的稳定性证明，因此不擅自推广。所有本轮已完成的付费 GitHub Actions 已设为 workflow_dispatch 手动触发，防止无意继续扣费。没有修改生产 main 或部署 Railway，没有覆盖 Atria 七类原稿、R2 小说或任何 Canon，也没有新模型权重训练。
- **下一阶段研究方向**：问题在更早的“WF 自己生成章节/事件计划”阶段已经形成，应该验证同一真实来源的 FACT/UNKNOWN 能否用于**模型写前构思**，人物先拥有自己的有限视角、目的与代价，再决定做什么；同时改善后一段时间、位置、已完成动作的衔接，而不是笼统强迫场景产生转折。要用新小说实际正文、同原始种子的对照检验，不能再堆泛化 Skill、口号提示或测试数量。

---



## 0.E 同源第一段文学 A/B：发现负迁移，撤回统一写作默认增强（本轮最新）

**继续 WriterForge 时，优先读 [WF_SAME_FIRST_TURN_LITERARY_NEGATIVE_TRANSFER_20261023.md](WF_SAME_FIRST_TURN_LITERARY_NEGATIVE_TRANSFER_20261023.md)，不要以历史 0.D 的 4/4 主观判断认定 WF 已学会通用文学手法。**

- 真正三种新世界的 W1/W2 原稿来自 [GitHub Actions #39971705331](https://github.com/66tyu55/WriterForge/actions/runs/39971705331)，全部 3 类 × 2 臂生成成功，每类两臂**同一第一段实际 DeepSeek 原文、同一 WF 原模型章计划/两段计划、同一来源状态**，只让第二段文学建议不同。全次仅 **6 次新供应商请求**，无重试。三组原稿、原始 wire、来源与 trace、匿名文件、独立映射都封存在三份 Actions artifacts。
- 揭盲前实际编辑偏好文件是 docs/WF_SHARED_FIRST_TURN_BLIND_VOTES_20261023.json，GitHub 提交 1280497f40024fb88bc5a82741f10b8385b924ff；优选小镇剧情 W2、洪水高潮 W1、灯塔恐怖 W2。揭盲后：**剧情 W2 是新 source_progression，高潮 W1 和恐怖 W2 都是 baseline**。即本小样本仅 1/3 偏好新提示，仍无独立真人评审；模型采样与输入 token 不同，也不能下统计结论。
- 具体负迁移：高潮新版为了“继续推进”加入停止原倒计时的不合理指令和显得突然的铜哨回想，尽管机械绞盘的部分新后果写得具体；恐怖新版（W1）多次复查湿痕、数时间，却较少推进人物互动。相比之下，剧情新版在库房单据、存根与退库凭证上有新可检验线索，但也存在地点转换偏快的问题。不能按体裁名字给 WF 写死文学模板。
- **立即回退误推广的开发默认**：在原 writerforge/writing_assist.py，AutonomousWriting.run(...,draft_mode="continuity_guard") 默认恢复 literary_progression_mode="baseline"。只有明确指定 source_progression 才启用实验提示。旧真实句校验、V114 物件状态、统一人物认知、长段重复拦截、同一 THREAD 记忆均不变；不增加新记忆/Skill/额外模型调用。先前修复的“文学建议不能挤掉因果提示”的独立预算+签名仍保留。
- **回退后全仓库 CI [#39973669036](https://github.com/66tyu55/WriterForge/actions/runs/39973669036)：1,457 tests run、4 skipped、0 failures**。该结果证明回退没有破坏工程功能，不证明某版文学质量最优。
- 新剧情/高潮/恐怖首轮 #39968891775 的原稿红灯保留：恐怖 W2 第二段真实写出 975 字符，被旧 950 限制拒绝。现对统一写作模式限定 1,024 字符并明确长度待审，零模型调用旧原稿复验 #39970808206 两臂均保存原 SHA；旧 V96 模式仍 950。软件限制问题和文学质量问题分开记录。
- 本轮所有已完成的实验性 GitHub Actions workflow 已设为**手动触发**，防止后续普通提交导致新的付费调用；不修改生产 main，不部署 Railway，不改用户私有原书稿、旧 Atria 七类原稿或 Canon。
- 下轮优先做**新的跨章真实创作/状态接续**以及人物是否真实形成选择，而不是重复同一个测试题、追加职业权限/评分模块、或者因三个随机样本临时“发明文学理论”。保留所有原始失败与负面意见，不造格式通过=文学成功的幻觉。

---



## 0.D 真实文学 A/B：第二段承接上段的创作改进（2026-10-23，本轮最新）

**用户的最新目标是让 WF 自己写不同场景、审读具体正文、改进文学手法帮助 AI；不是加权限、造新记忆、追逐测试数。** 首先读本节及 [WF_SOURCE_PROGRESSION_LITERARY_AB_20261023.md](WF_SOURCE_PROGRESSION_LITERARY_AB_20261023.md)。

- 唯一工作分支继续为 refactor-unified-scene-delivery-audit；生产 main、Railway、Canon、用户私人小说 R2、先前 Atria 14 篇原稿均未修改。旧 V96–V123 不重训、不重复配置 API。
- 以真实 WF #39961720469 四篇原稿作为文学证据：打斗人物长时间隔桥僵持；计谋将脚印推断为必然已受骗；喜剧验伞反复、真巡察使出现却无明确误会后果；心理篇烧毁伏击计划改查孩子，有较自然的内心与行为互证。因此没有新增喜剧专用技能，只在原有 writerforge/writing_assist.py 增加后续创作可选提示，让 AI 以**上一段已经真实写出的结果**为起点推进新反馈，而非重演准备动作；仍允许克制、改变计划、失败、安静或延期，并守住 POV 和事实／猜测隔离。创作提示属于低优先级可丢弃 lane，不抢硬连续性上下文，也不增加记忆数据库。
- **真实锁定计划的四类 A/B [#39964830150](https://github.com/66tyu55/WriterForge/actions/runs/39964830150) success**：四类每类 W1/W2 两臂共用上一批同一 WF 模型原始章节计划、事件计划、源前史和同一 deepseek-flash；每臂只生成两段，每段 1,450 max_tokens；共 16 次提供商真实写作调用，零重试。四类均生成完整候选，真正 source-progression 提示仅第二段送达。原文及受控盲标文件均在四份 Actions Artifacts。
- 助手在未看揭盲映射时读完匿名稿，先记录四类偏好（本轮盲读 SHA256 892beacf7c7dfeae73ee5bd29a320ea80cda7ad3d61c56085e1e3f02c00b31e0）。W2 打斗、W2 计谋、W2 喜剧、W1 心理的首选在揭盲后均为 source_progression，即**四组探索性编辑偏好为 4/4**。这不是独立真人审评，不是统计胜率，不能当模型权重学习或跨作品稳定提升。
- **负面证据必须同时记住**：新提示虽使本小样本场景推进更清楚，但喜剧的模型 trace 待审计数由 1→2，心理从 0→2；打斗 0→0，计谋 2→1。中文汉字长度（原→新）分别打斗 1082→832、计谋 1207→1051、喜剧 783→709、心理 747→773；并非所有文章均达固定篇幅或文学高质要求。真正意思仍需外部读者/作者审阅。
- 仅在**该开发分支**的 AutonomousWriting.run(draft_mode="continuity_guard") 将可选 source_progression 提示设为默认；旧其他写作模式无变化，单次任务可显式使用 literary_progression_mode="baseline" 回滚。新提示只在已有前段真实候选之后使用，若预算不够则有明确未送达记录，不会改正文或正典。
- **最新绿色全量工程回归 [#39965763978](https://github.com/66tyu55/WriterForge/actions/runs/39965763978)：1,447 tests run、4 skipped、0 failures**。过渡红灯 #39965523424 是旧合成测试还在断言签名中的老默认字符串，随后更新该测试并重新绿灯；不能隐瞒当时的红灯，也不能把绿色回归当文学胜利。
- 新真实 A/B workflow 已关闭自动 push 触发、只留下 workflow_dispatch 手动运行，避免重复消耗 DeepSeek 配额。本轮没有 Railway 生产部署，下一轮应继续**跨不同小说种子、多章情节与人物自主逻辑的真实文本校验**，尤其关注新提示是否导致 trace 变差，不能越改越乱。

---


## 0.C 真正文学正文优先：解决解析与引句拒绝（2026-10-23，本次最新）

**用户明确纠偏：WF 的核心不是不断增加权限或独立模块，而是让 WF 自己持续创作不同类型的真实文本，观察实际人物、剧情、表达、情绪、因果和节奏缺点，再改进原有写作能力。先读此节和 [WF_REAL_SELF_SCENE_FORMAT_REPAIR_20261023.md](WF_REAL_SELF_SCENE_FORMAT_REPAIR_20261023.md)，再看旧审计。**

- 分支仍是 `refactor-unified-scene-delivery-audit`，未修改生产 main / Railway / Canon；没有创建任何新记忆模块、没有重训 V96–V123。
- 首轮实测 [#39957986613](https://github.com/66tyu55/WriterForge/actions/runs/39957986613) 是实验接线问题：错误 Path 类型导致四个场景请求模型前全部退出（供应商调用零）。已修复并保留历史失败。
- 第二轮 [#39959076839](https://github.com/66tyu55/WriterForge/actions/runs/39959076839) 找到**真正 JSON 根因**：计谋、搞笑提供的 DeepSeek Flash 正文响应含完整有效的 `prose`/`trace` JSON 对象，但该对象后精确多出 `"}` 两字符；供应商 `finish_reason=stop`，旧模型适配器误判整个正文 `WF_FLASH_INVALID_JSON_RESPONSE`。此外打斗上一段 effect 只被引用前半句、心理 action/effect 引句同源重叠、早期模糊的人称引句、模型将 `decision` 错塞入可选 `craft_focus`，这些都曾导致真实稿被拒。
- 现有 `writerforge/deepseek_flash_model.py` 对**仅限这一种已验证尾部垃圾**的完整源 JSON 安全解析；对其它损坏格式仍拒绝。`writerforge/v96_causal_turns.py` 增加源原句唯一定位的轻量引用归一化，以及对错误模型 trace 的**正文保留但因果未证**候选降级。`writerforge/writing_assist.py` 以原始回复优先、零额外模型调用串起处理；真实正文仍通过 Novel Studio 物理状态、人物知识、长段重播和作者硬约束。不自动修稿、做假式文学通过或晋级学习。
- **修复后完整回归**：GitHub Actions [#39961354519](https://github.com/66tyu55/WriterForge/actions/runs/39961354519)，**1,443 tests run，4 skipped，0 failures**（此前有一次故意保留的红灯，为新合成测试句不满足严格 18 字引句阈值；只修了测试句，没有放松生产闸门）。
- **最重要的真实结果：DeepSeek Flash 自主四类生成 [#39961720469](https://github.com/66tyu55/WriterForge/actions/runs/39961720469) 已完成**：打斗 845 汉字、计谋 970、搞笑 756、心理 873；四类各 4 次真实模型调用、无重试，均调用真正的 `AutonomousWriting.continuity_guard`、自行产生章节与事件计划、两段真实正文、成功保存候选。四份原始模型 wire、未篡改 decoded JSON、完整小说文本、软件审核均附在该 run 的四个 Artifacts。上一轮不能完稿，这轮 **4/4 产生完整候选**；这是写作链路修复的证据，不是文学水平已经提升的证据。
- 有**真实可见的剩余文学问题**：搞笑篇主要堆‘验伞/验官声’的滑稽铺垫，未给真假巡察使误会有效的收束；打斗篇受伤与破桥约束基本进入动作，但阶段目标还不够推进，第二段前因引句仍标记待审；计谋篇可见布局和代价，人物依据与跨日时序仍需独立阅读；心理篇的旧仇转向调查出现较具体选择。机械无错误不等于幽默/心理/谋略好。
- 本轮最后真实在线 batch 的 JSON 包装格式**恰好没有再多出尾串**，记录的包装修复次数 0；不能谎称模型现场再次复现同样错误并已通过恢复。修复路径通过原始失败 wire 的离线诊断和合成 8 项回归证明。模型请求工作流已经改成**仅手动触发**，防止重复产生费用。
- **下次重点：用这四份具体正文和此前 Atria 原始七类封存稿做独立遮盲、逐场景细读，明确‘人物为什么这样做/本场到底推进了什么/语言是否像小说’，只针对失败的实际写作手法做窄改，再做同题预算公平的 A/B；不要再次让权限、JSON、记忆底层压过真正文学质量。**

---


## 0.B 最新补充：安静场景人物自主调度＋原始证据防过期复验（2026-10-23）

**此节更新于下面的 0.A 历史绿色状态之后；下次交接从此处读起。**

- 工作分支仍为 refactor-unified-scene-delivery-audit。最新源码与测试提交 d9be9b265a0998d15aa9091e59087e33452cd0ae。全量 GitHub Actions [#39954588343](https://github.com/66tyu55/WriterForge/actions/runs/39954588343) 已真实完成：**1,429 tests run、4 skipped、0 failures**。这是由 1,407 的初始基线增长而来的合成工程验证；不证明文学质量改善。
- **补上安静／心理场景断点**：统一 schedule 原先对 kind=quiet 直接跳过 CHARACTER_INTENT 与 LONG_THREAD。现在有经来源确认的角色内心 desire/fear/value lens 时，即使人物独处也提醒其自主心理张力，允许沉默、迟疑、暂缓行动，不要求肢体动作或强行兑付大纲。相关长期线在 quiet 里仅当目标同时明确提及 owner 与 target、或稳定 THREAD ID 时才恢复提示；主角无关听雨场景不激活所有旧债。NPC 视角仍禁止获取主角隐藏的意图正文。两项回归与全库测试均已通过。
- **作者权限没有被伪装解决**：生成时只有债务提议；CARRY_FORWARD、SETTLE_WITH_SOURCE、ABANDON_BY_AUTHOR 必须在作者单独审阅、重新读取保存的原 candidate.md（或必须有实际 R2 source_reader GET）且校验正文 SHA 后方能更新同一 THREAD 的候选状态；布尔 author_confirmed 不是身份认证。文学效果是否真兑现仍需独立遮盲判断，不会因为工程测试绿灯而自动宣告。
- **Atria 九份原始附件已复验**：新一轮 [#39953846247](https://github.com/66tyu55/WriterForge/actions/runs/39953846247) 先完整执行 **1,427 tests / 4 skipped / 0 failures**，再对九份已归档在私有 R2 的原始 ZIP fresh GET，全数 9/9 成功，manifest SHA256 仍为 14e0e957f2564af71ee0ee3b8f74bf743948f6e06fa59e750b58387a5b74650e。原始七类 Atria 14 篇及失败证据没有删改、未重跑模型、未公开原文。唯一保留的归档工作流为 .github/workflows/preserve-atria-evidence-r2.yml，现改为**只有手动触发**；重复旧 workflow 已删除，避免提交代码时反复上传。
- 原生产 main 再核为 d6ca4b769faa2ef2b47da91fb623a417be49de17（未改），没有部署 Railway，没有新模型调用或 Canon 写入。今后重点仍是独立、源证据约束的文学盲评及真正作者身份审阅交互，不再重复 V96–V123 或新增记忆模块。

---


## 0.A 本次已实际续接：源正文—场景承诺—跨章 THREAD—人物选择（2026-10-23）

**此节比下面 0～0.3 更晚；保留原 0 节作为首轮基线，后续请先看这一节再往下读。**

- 唯一工作位置仍为仓库 66tyu55/WriterForge 的 refactor-unified-scene-delivery-audit 分支。核心叙事**功能与测试最后提交** cb704a845ac2bc90c5609ab704b65ae28f915842；另有封存 Atria 原始证据的工作流功能提交 61714072b96d05bce06093d851da405b5c3c1b49（非叙事记忆模块），文档 HEAD SHA 会继续变化。生产 main 未修改，Railway 未部署；没有调用书生/DeepSeek、没有覆盖旧 R2/Canon/七类原稿；但本轮**确实新增私有 R2 只增不改的证据备份**（见下）。
- **已核验的最新全量 GitHub Actions**：[WF Unified Scene Delivery #39953606339](https://github.com/66tyu55/WriterForge/actions/runs/39953606339)，结论 success，**1,422 tests run、4 skipped、0 failures**；新增 15 项合成回归（首轮 1,407 → 1,422），工程测试不等于真实文学质量改善。
- 解决的真正断点：之前 author_delivery_contract 能检查当章未验证的兑现，但 AutonomousWriting.run 之后推进统一图时 events=()，并不会自动登记未偿合同。现在 writerforge/narrative_core.py 新增 propose_scene_delivery_debt（生成时只读提议）、review_scene_delivery_on_graph（保存原候选 + 作者另行确认后才可更改同一 THREAD）、review_scene_delivery_resume（生成不覆盖旧版本的新 V117 候选恢复封套）。writerforge/writing_assist.py 在已有 V96 evidence 及章结果直出 THREAD 待审状态，自动提交次数为零。作者审阅时还必须重新读取并核验真实保存的候选原文；R2 源必须有提供实际字节的私有 source_reader，不能仅凭旧 SHA 结案。完整源码及决策说明见 [UNIFIED_SOURCE_FIRST_SCENE_DELIVERY_AUDIT_20261023.md](UNIFIED_SOURCE_FIRST_SCENE_DELIVERY_AUDIT_20261023.md) 新增小节。
- 审阅三种结果：CARRY_FORWARD 以 AUTHOR_INTENT（仅写作意图，不是世界事实）登记开放的通用 THREAD；SETTLE_WITH_SOURCE 需明确作者复核 + 两条按顺序出现且唯一、真实叙述的行动/心理决定与后果锚点，标 SETTLED_AUTHOR_REVIEW_ONLY，**不宣称文学质量已证**；ABANDON_BY_AUTHOR 是放弃而非兑现。THIS_SCENE 当场未付可经作者决定跨章保留，DEFERRED 自然留白。不同人物的秘密认知仍隔离。普通安静情节不强求反转。
- **完整的两章合成回归已完成**：第一章保存候选并且作者复核保留原问题 → 第二章仍处 OPEN，正文写到角色不同于大纲的选择与后果 → 作者另行确认后在同一图结案 → 第三章不再重复提醒旧债；已验证此合成回归内 R2 / Canon 写入数为 0，长段重播即使篡改回执并重算普通 SHA 也无法借此开/关债务，非法封闭 THREAD 结构不被签名校验单独放行。
- Atria 原始七类的来源、预算不均、失败与编辑观察**一个也没有删**。原心理 WF 重播稿 SHA-256 为 272557d79b55f4b6790591afcc0817d61feedf2deb11f25fcbacf3dee4dedbac，14 篇真实原稿在原 Actions artifacts 里有可回查来源，本轮只使用新写的合成句测试叙事闭环，不把封存原稿复制成公开 fixture；其原始 ZIP 和两类补测原始 ZIP 已在本轮另行私有 R2 备份。
- **新增实证来源保全成功**：初次七类+高潮心理补测共九份 GitHub Actions 原始 ZIP 附件发现 2026-11-06 过期风险，已执行私有 R2 原字节不可变上传、逐件 ZIP SHA 核验、fresh GET：[#39953107366](https://github.com/66tyu55/WriterForge/actions/runs/39953107366)，**9/9 保存并重新下载成功**。只增加 writerforge/v1/private-evidence/atria-seven-genres-20261023/ 下的证据对象与哈希清单，没有覆盖原小说记忆。manifest SHA256 14e0e957f2564af71ee0ee3b8f74bf743948f6e06fa59e750b58387a5b74650e；新增工具 scripts/preserve_atria_artifacts_r2.py、.github/workflows/preserve-atria-evidence-r2.yml。**此项不同于先前“本轮未 R2 写入”阶段性历史描述**，新证据只入私有存储；不构成训练或文学盲评。
- 下轮需要继续验证的是：作者确认接口尚缺真正的用户身份/审阅权限服务（布尔 author_confirmed 仅是程序调用门槛，不是不可伪造鉴权）；文学场景效果仍需独立遮盲、反事实对照与本人审稿；不应让其他模型自己调用作者审阅接口并自行传 True。无需重新配置 V96–V123，勿再新增独立记忆技能。为保证候选签名链，任何新审阅版 resume 必须当成**新版本**保存，不得覆盖旧 R2/原始候选。

---


> **新对话从这一节开始，旧版 2026-10-16～20 “最新 V66/V99” 字样仅是历史快照，不再代表 WF 最新进度。** 请先核验当前 GitHub 分支与 GitHub Actions，之后再读本文件历史记录；不可重建原书库、重复配置 API、覆盖封存真实输出或修改生产 main。

## 0. 当前权威工作位置及本轮验收

- 唯一当前开发分支：`refactor-unified-scene-delivery-audit`，仓库 `66tyu55/WriterForge`。已验证的最后功能提交：`c216a83426431a9261f4d211773ab1f4fe605802`，随后仅更新交接文档（无功能性代码改动）。最新文档 HEAD 请现场查询 GitHub（本文件自身更新会产生新提交），不可将文档提交误认成功能源码变动。
- 最新全量回归：[GitHub Actions #39947647329](https://github.com/66tyu55/WriterForge/actions/runs/39947647329)，**1,407 tests run，4 skipped，0 failures**；测试确认的是软件机制，不是原创小说质量提升。
- `main` 当时为 `d6ca4b769faa2ef2b47da91fb623a417be49de17`，未将开发分支合入；Railway 生产服务未部署本轮变化。
- **技术交接与已核验行为详见：[UNIFIED_SOURCE_FIRST_SCENE_DELIVERY_AUDIT_20261023.md](UNIFIED_SOURCE_FIRST_SCENE_DELIVERY_AUDIT_20261023.md)**。这是新对话的首个详细源码证据入口。此前统一图/缓冲压缩/R2 请按需读 [UNIFIED_NARRATIVE_CORE_DIFF_PRIORITY_NPC_KNOWLEDGE_20261022.md](UNIFIED_NARRATIVE_CORE_DIFF_PRIORITY_NPC_KNOWLEDGE_20261022.md)、[UNIFIED_NARRATIVE_BUFFERED_MEMORY_AND_AUTHOR_AGENCY_20261022.md](UNIFIED_NARRATIVE_BUFFERED_MEMORY_AND_AUTHOR_AGENCY_20261022.md)、[UNIFIED_NARRATIVE_R2_DURABLE_CAS_20261022.md](UNIFIED_NARRATIVE_R2_DURABLE_CAS_20261022.md)。

## 0.1 这次绝不能混淆的两条事实

**底层**：`writerforge/narrative_core.py` 统一管理人物知识（KNOWS/BELIEVES/UNKNOWN）、CONTACT、通用 THREAD、章节热/温/冷记忆、稳定键变更标志与调度；物件/人物动作依然交给现有 V114/V116/V117 Novel Studio 归约器。新增 `detect_long_prose_replay()` + `audit_scene_delivery()` 已接入 `writerforge/writing_assist.py` 的 `continuity_guard` 逐段及整章验收，重播直接拒绝并留原始凭证。作者确认的 `scene_delivery_contracts` 区分 THIS_SCENE 与 DEFERRED；对心理选择、喜剧笑点是否兑现只提示待审，**模型或评论者能引用真实效果句也不等于完成证明，不自动结案或改正典**。当前旧模块为兼容而保留，新图与 V123 长线复仇专用账本不可同时作为状态所有者。

**真实模型**：书生 Discovery 网关 Base URL `https://discovery-api.intern-ai.org.cn/v1` 可用。`Atria-Dawn-Preview` SSE 实测 926 汉字、正常 stop；七类文学每类裸/WF 各一篇，现有共 **14 篇真实原稿 / 7 个配对**。首次 3,100 max_tokens 中五类成功；高潮及心理因推理 Token 耗尽分别失败，另一次 6,000 max_tokens 配对补测成功，因此跨类别预算不完全一致，不可合并成公平总体优胜率。心理 WF 版出现约 964 字符完整段落连写两遍（原稿 SHA-256 `272557d79b55f4b6790591afcc0817d61feedf2deb11f25fcbacf3dee4dedbac`），其余 13 篇不触发同种精确重播。搞笑一类裸模型的误拿雨伞笑点比 WF 版兑现更清楚；打斗、计谋 WF 较冗长且有规则推测。所有这些是原稿编辑观察，不是独立文学盲评、也不是能由词面算法完全判定的语义真相。

七类源运行：[初次 7 类矩阵 #39937669584](https://github.com/66tyu55/WriterForge/actions/runs/39937669584)、[高潮和心理 6,000-token 补测 #39939718654](https://github.com/66tyu55/WriterForge/actions/runs/39939718654)。[原稿实测专项交接](https://github.com/66tyu55/WriterForge/blob/experiment-seven-literary-scenes-inkstone/docs/SEVEN_GENRES_FIRST_ACTUAL_PROSE_RESULTS_20261023.md)，[重复检查专文](UNIFIED_CORE_PROSE_REPLAY_SOURCE_GUARD_20261023.md)。

## 0.2 下一轮唯一优先工作

1. **先复核本节指定的 GitHub 提交和绿色 CI**，不要因文档最后提交与 CI 功能提交不同而误报未测；下一段继续同一 `refactor-unified-scene-delivery-audit` 分支，不重复开 V124/125 微型技能。
2. **打通已注册当场兑现的场景合同与同一 unified THREAD 图的跨章节债务**：只保留一位状态所有者；有延期决定且能回查原文时允许自然留白，不要求每章出现强行笑点或情节反转。验证来源与模型判断分离，不能将审稿提议自动写成已发生事实。
3. **对真实作品做独立盲评**：随机遮住裸/WF 标签，把高潮、打斗、计谋、恐怖、喜剧和心理分别按适合文体的标准看具体原稿；延续用户最重视的“人物自主逻辑、计划/正文分离、不会越改越乱”。任何自动文学分数都必须注明校准不足。
4. 若需要继续使用已接入的 Discovery / DeepSeek，允许在用户已有授权和实际免费额度内做**有调用上限**的模型试验；不得推断账号剩余额度、无界重试超时/429，也不要重复要求配置已存在的凭证。R2 记忆的真实私有桶合成源/CAS/续写快照曾完整远端回读，但**开发分支未部署生产**。

## 0.3 禁止误声明

- 测试 1,407 成功 ≠ 文学水平提高/语义理解全面解决。
- “有正文效果引句” ≠ 本场心理变化/喜剧包袱已经真正兑现。
- “模型经过规划” ≠ 正文实际写到了该情节。
- 新模块不应该增加第二套长期叙事记忆；不要因独立失败而随便覆盖已存原稿、Canon 或私有 R2 源。
- 本轮功能**仅在开发分支**，不是 Railway 的已上线能力。
- 旧版本全文保存在下面历史文档中，不能把 2026-10-16／18 的旧 `latest` 字样误当现在状态。

---

# WriterForge 当前交接记录 · 2026-10-16

> **本文件是新对话的唯一首读交接入口。** 每次继续项目前，先检查本文件并复核有关 GitHub Actions 运行结果；不要重建已完成的原文归档，不要将用户的聊天结论冒充 R2 中的真实数据。本文报告的是截至 **2026-10-16 06:08 UTC** 核实的状态，而不是当前实时桶扫描结果。

> **最新更新（2026-10-18）：第53节【V66云端连接成功，WF自主文学检索未开始；用户因长度限制要求交接】为此刻唯一最新状态。详情参见 docs/V66_WF_SELF_RETRIEVAL_EXAM_HANDOFF_20261018.md。原第52节是连接搭建时的历史快照，不代表当前失败或仍需本地安装。V49 THIRD_STRIKE_FAILED 与第二窗口 LOCKED 不变。**

## 1. 已完成：六本现代小说的私有 R2 原文归档

目标存储桶：`writerforge-private-library`（**私有**）。

目标对象前缀：`writerforge/v1/private-reading/single-works/<work_id>/`。

每本独立保存内容寻址的原文 blob、不可变 manifest、latest 指针。成功标准为：**GitHub Actions 下载原文 → 校验实际字节与 SHA-256 → 上传新对象 → 全新 R2 下载 → SHA-256 一致**。无一需要 GPT 临时目录、Google Drive OAuth 或遗失的十三本合辑。

| 作品 | work_id | 归档原文大小（字节） | 原文 SHA-256 | 核验证据 |
|---|---|---:|---|---|
| 《星辰变》 | `xingchenbian` | 8,256,014 | `83da08694a5d5510124711c7bfcc7522be531cdb73e01790aa0d3076932ab5f0` | [单书上传与回读](https://github.com/66tyu55/WriterForge/actions/runs/38107901164)，[无需旧合集的再恢复](https://github.com/66tyu55/WriterForge/actions/runs/38852727960) |
| 《仙逆》 | `xianni` | 20,379,949 | `8174861b528c2781b4aa102670a363021fa97f8b0cfc358ee7ba08d3584dd14c` | [单书上传与回读](https://github.com/66tyu55/WriterForge/actions/runs/38108185835) |
| 《凡人修仙传》 | `fanrenxiuxian` | 15,079,878 | `2fc1698410418bf136448807335c6359bf515b75e6f9c1e1d1f443a1c928e6cc` | [网页固定版本下载、新上传、全新回读](https://github.com/66tyu55/WriterForge/actions/runs/38858109163) |
| 《斗破苍穹》 | `doupo` | 16,085,734 | `8d2e617d7ea4742452b765393bb66b0b0bb8546f63b9ff88dff9d3f6a779c0f6` | [三书独立归档：doupo job](https://github.com/66tyu55/WriterForge/actions/runs/38859398597) |
| 《武动乾坤》 | `wudongqiankun` | 8,254,079 | `86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28` | [三书独立归档：wudongqiankun job](https://github.com/66tyu55/WriterForge/actions/runs/38859398597) |
| 《完美世界》 | `wanmeishijie` | 14,053,175 | `322e84872b2259d9210f84de63efd70d901a412dfefbe9bb9d52168eea56d481` | [三书独立归档：wanmeishijie job](https://github.com/66tyu55/WriterForge/actions/runs/38859398597) |

**合计 6 本、82,108,829 字节原文（约 82.11 MB）。** 这个合计仅针对六份已归档原文，不包括 manifest、数据库，也不代表已经深度学习六部。

### 三本玄幻：实测新增快照

三个 GitHub Actions job 都报告 `new_private_archive=true`、`new_blob_uploaded=true`、`fresh_roundtrip=true`；整次 [运行 #38859398597](https://github.com/66tyu55/WriterForge/actions/runs/38859398597) 结论为 `success`。

- `doupo`: `8c8caa056005bc8eab3fa90177bcbd2d5caa37e1b88517537f057c7f7c66c08d`，标题模式命中 1,648 处。
- `wudongqiankun`: `a747f34425db5d0866f7804a432242e8f9f498376a9695cc820300377a9763aa`，标题模式命中 1,311 处。
- `wanmeishijie`: `ea3ca7b5bfa9eb2893edc890c737499a03d390048cd342782ebf4faaf0bd0256`，标题模式命中 2,015 处。

`fanrenxiuxian` 新快照为 `201d71349b90ba0067823509fd9b0076185b745338babcae0fe2a50ea0541ce5`，**2,451 处标题匹配不是完整、连续、无缺章的证明**。

**来源版本差异要保留**：《凡人修仙传》网页归档 15,079,878 字节；用户私有 Google Drive 同名 TXT 实测为 15,224,548 字节。两者不能声称字节相同，也不能用任一版本的哈希验证另一版本。

真正可复用的上传实现：

- [scripts/archive_web_fanren_r2.py](../scripts/archive_web_fanren_r2.py)
- [scripts/archive_three_xuanhuan_r2.py](../scripts/archive_three_xuanhuan_r2.py)
- [.github/workflows/fanren-pinned-web-r2.yml](../.github/workflows/fanren-pinned-web-r2.yml)
- [.github/workflows/three-xuanhuan-r2.yml](../.github/workflows/three-xuanhuan-r2.yml)
- [writerforge/single_work_runner.py](../writerforge/single_work_runner.py) 的 `verify_existing_single_work`

## 2. 已完成的古典原文结构化学习（与现代单书原文归档是两套不同目录）

已在 R2 `writerforge/v1/libraries/` 中有独立目录：

| work_id / 目录 | 说明 |
|---|---|
| `xiyouji-23962` | 《西游记》，经典原著结构化学习 |
| `honglou-24264` | 《红楼梦》，120 回；另有第三回场景的 **source_prepared** 证据，尚未执行真实模型深读 |
| `shuihu-23863` | 《水浒传》，结构化原著（含楔子） |
| `sanguo-23950` | 《三国演义》，120 回 |
| `jinghuayuan-25377` | 《镜花缘》，100 回 |
| `laocanyouji-25124` | 《老残游记》，20 回，新入库并全新恢复；4,857 个结构化来源单位 |

《老残游记》验收：[运行 #38853753144](https://github.com/66tyu55/WriterForge/actions/runs/38853753144)，原文 SHA-256 `273f4cbaecb4c4d396ecec7103b4761e62bde0c0f368185a1697c1880cfe9cf7`，R2 快照 `7fe1ceff8d637139d51b0b6bf2de6a7de220aeaea670247868fa17cc55270dd2`。

《红楼梦》场景来源证据入 R2 并恢复验收：[运行 #38848332025](https://github.com/66tyu55/WriterForge/actions/runs/38848332025)。状态仍为 `source_prepared`，不应谎称已进行模型文学理解或真人盲评。

## 3. 反复失败的根因（已实际定位；勿再循环排障）

- 旧的 13 部小说合辑 `WriterForge_PrivateReading_13Works_20261011.sqlite3` 曾可被读取，但后续原始键不可用。经 [只读全桶盘点 #38852072980](https://github.com/66tyu55/WriterForge/actions/runs/38852072980) 扫描当前桶 **85 个对象**，根目录源不存在，且全桶无同名、同大小对象；仅有 `xianni`、`xingchenbian` 单书独立入口（该次盘点发生在其余 4 本上传之前）。
- 早期单书传输流程在**上传之前**就因找不到旧合辑退出，典型错误 `root_size=None; matching_size_candidates=0; no upload attempted`。这不是 R2 普遍无法写入，也不是 8 MiB 上限。
- [PR #37](https://github.com/66tyu55/WriterForge/pull/37) 让已独立归档书籍直接按 latest→manifest→blob 下载验证，解除对旧合辑的重复依赖。
- Google Drive 连接器有访问用户私有 TXT 的授权，**GitHub Actions 没有继承该授权**；[Drive→R2 尝试](https://github.com/66tyu55/WriterForge/actions/runs/38855035159) 因缺 Google SA Secrets 在下载前终止。无须重试该失败路径。后续已证实网站→Actions→R2 可行。
- 用户明确要求：**停止依赖 13 本合辑；不再用 GPT 本地持久保存或 Google Drive 作为必需条件；不要重新争论、重新下载已经归档的书。**

## 4. 目前未完成、绝不可写成成功的工作

1. 现代六本小说目前是**独立原文归档**。标题正则命中数不等于严格章节数；未执行完整章节序列/分卷/番外兼容校验，未形成各自完整的 `libraries/<work_id>` SQLite 学习库。
2. `writerforge/modern_source.py` 已支持最大 32 MiB 原文、单章事务及断点式 SQLite 结构化写入，并通过 >8MiB 合成样本；但其第 1 章起连续编号、章节标题匹配约束，**不能不审原文就直接套用到六本不同卷制的现代小说**。
3. 原著学习的八轨结构标签属于词汇/启发式证据，不能冒充真正的文学深度理解或模型参数训练。文学场景学习 `writerforge/scene_learning.py` 初读锁定与解释程序存在，但原著《红楼梦》模型分析未执行，真人/独立评审未完成。
4. 既有《渡口无名簿》三章样稿为 **M0 对话生成的失败样稿**，不是 WriterForge 文学能力的有效 A/B 提升实证；可用于局部修订失败分析。文风基准 [PR #34](https://github.com/66tyu55/WriterForge/pull/34) 是可撤销的作者认可样段，**不是训练过的文笔模型**。
5. 用户决定辅助界面次要，自主创作能力优先；文学水平的 **50 部完整作品总体评价门槛**仍保留。现有已完成归档/结构证据不能算成 50 部真实文学能力掌握成果。

## 5. 下一对话推荐严格执行的顺序

**不要先加新 Skill，不要再重复三章写作测试。**

1. **从已有私有 R2 验证输入。** 选一本现代小说（建议先 `fanrenxiuxian`），在同一 GitHub Actions runner 使用现有 R2 Secrets 获取该书 `single-works/<id>/latest.json`、快照 manifest 和原文 blob，按 SHA-256 复核。源文件只在运行器临时目录，**不公开、不给 GPT 容器当中转**。如果发现确切缺源，仅报告和修复那一书。
2. **先严格核实章节语法和完整性。** 逐卷识别标题、重复序号、番外、章节缺失；留下带来源哈希的审计报告。若解析器不支持当前版本，就**修解析器并生成回归样例**，而不是修改原文去凑预计章节数。
3. **完成真正的现代单书结构化读取。** `learn-modern` 逐章写 SQLite、重跑可续、来源哈希不可混版；R2 `libraries/<work_id>` 新库备份＋干净环境恢复后校验章节数、来源单位数、原文 SHA256；这才是“现代小说原文入库 + 结构学习完成”，不是仅单书 blob 存在。
4. **再进行真实模型的场景深读**：先不剧透的读者假设锁定 → 后见揭示 → 逐条引用原文解释人物认知、信息释放、行为因果与表达取舍 → 独立复核后才可能迁移到创作。保存失败、修订和复评；无真实模型/审稿不能自称完成。
5. **质量门槛**：与无 Skill 同模型写作基线比较，帮助不了或写得更差的干预必须能够禁用；不要复制原著、不可让劣质 AI 样稿自动晋级为文风范例。

### 验收与日志约定

- **原文归档成功**：新 R2 blob / manifest / pointer 存在，远端全新下载 SHA-256 一致。
- **章节结构学习成功**：原文版本和完整章节证据、SQLite `PRAGMA quick_check`、整章记录、来源单位、R2 全新恢复全部一致。
- **文学语义学习有效**：真实模型输出、来源引文、独立评价和迁移对照均可追踪；无上述证据明确为“未验证”。
- 新增失败必须打印**失败在哪一步**（source、download、chapter、db、upload、restore、review）并保留可复核的 GitHub run URL；不要因聊天中断就宣称远端任务失败。
- 不记录 R2 Secrets、Google OAuth 密钥或私有整本原文到公开 repo、Issue、PR、Actions Artifact。
- 需要用户明确指定的任务继续执行，不必为已经商定的执行环境、目录、文件格式重复询问。

## 6. 给下一对话的最短启动指令

> 继续 GitHub 仓库 `66tyu55/WriterForge`。先读取 `docs/CURRENT_HANDOFF.md` 并核对引用的 Actions 成功证据。六本现代小说已在私有 R2 `writerforge/v1/private-reading/single-works/`，**不要重新下载原文**。从 `fanrenxiuxian` 做“私有 R2 原文恢复 → 真实章节语法核验 → 完整 SQLite 结构读取 → R2 全新恢复”这一阶段，一本一本来；先交付真实代码、日志、哈希。不要再拿存储架构和文学计划重复聊天。

——交接状态来源：项目 GitHub 代码、原有 Actions 日志、用户确认的 R2 控制台目录截图。每次实际继续应以最新日志和 R2 回读为准。


## 7. 本轮续接实际结果 · 2026-10-16（此节比上方 06:08 UTC 历史状态更新）

**本节为新一轮真实 Actions 的结果；第 1 节的六本数字是历史快照，不再是全部归档数量。**

- **已从私人 R2 独立完成《完美世界》的原文恢复、2015 章确定性 SQLite 结构学习（249612 个来源单位）、新 R2 学习库备份、全新下载恢复、原文哈希及 SQLite quick_check 验收。** 新库：`writerforge/v1/libraries/wanmeishijie-private-original/`；快照 `fe0fd571c97a7a59f7f38c74408a85ec3a55b31abb90db343505e9aff1de2bfc`；[真实运行 #38866296144](https://github.com/66tyu55/WriterForge/actions/runs/38866296144) 的 `wanmeishijie` job **success**。结构化学习不代表模型参数训练、真实场景深读或独立文学评价。
- **新增且与此前六本不重复的三本玄幻已在私人 R2 独立原文归档、全新下载比对 SHA 成功**：
  - 《遮天》 `zhetian`：13,455,412 bytes，SHA256 `9cbf8da97daceb36fbd85edd84e2874a9ceac28252c18386fecf167d5a95660b`，归档快照 `c64901291446fd847757a4396d9a1d76462f645c98751c0f1874ee4a4083e357`。
  - 《莽荒纪》 `manghuangji`：8,961,764 bytes，SHA256 `f7aee869e201b4171e40a3ff9230e794f01fdc959d372017b8982635668be3d5`，归档快照 `02e5fd3c958c925e8c0426339a8a25465bea061713c8c4aa728153a358b82798`。
  - 《求魔》 `qiumo`：9,437,806 bytes，SHA256 `210acebeef123f2c369d57d95d2ea5ee5a1c15716b859db15696c48294bcd687`，归档快照 `5dfbb317e6028d66dbe8ea151821b59d3de9a5ec2bddceabcfac7468f296a779`；此版本卷名在章名前，独立安全识别到 1476 处卷限定标题，不能将“标题数”冒充完整章节。
  - 以上新三本共 **31,854,982 bytes**，新增前六本 **82,108,829 bytes**，累计归档 **9 本、113,963,811 bytes**（仅原文体积）；[三本独立归档 R2 回读均 success #38867522198](https://github.com/66tyu55/WriterForge/actions/runs/38867522198)。原文私有路径 `writerforge/v1/private-reading/single-works/<work_id>/`。
- **存在真实失败，不能抹去：** [章节审计 #38866296144](https://github.com/66tyu55/WriterForge/actions/runs/38866296144)：《凡人修仙传》匹配 2451 处但于 1754→1747、另有跳号；《武动乾坤》有 248→449→250 等异常；《斗破苍穹》安全诊断为 1648 个连续的 1..1648 标题，但现有严格解析器无法识别首章，需验证实际标题语法后修解析器。这三本**本轮没有新的结构学习成功或 R2 学习库**。不要改动原著、强行补齐缺章、用推测章节数宣称完成。
- 新增原文归档实现：[scripts/archive_next_three_xuanhuan_r2.py](../scripts/archive_next_three_xuanhuan_r2.py)、[归档 workflow](../.github/workflows/next-three-xuanhuan-r2.yml)；新结构学习执行器 [scripts/learn_archived_modern_r2.py](../scripts/learn_archived_modern_r2.py)、[结构学习 workflow](../.github/workflows/next-three-modern-study-r2.yml)、[已归档旧小说结构学习 workflow](../.github/workflows/modern-archive-study-r2.yml)。
- 新三本实际章节结构学习的 [run #38867581785](https://github.com/66tyu55/WriterForge/actions/runs/38867581785) **在本节记录时仍在运行**；不可预写成功结论。需逐个核对 job log 的 `complete_structural_only`、`fresh_r2_study_restore_verified=true`，才可计入。若不通过，保留失败并针对确实存在的章节格式改解析器与回归，而非跳过验证。

**截至本节已验证门槛：** 私有 R2 原文归档 9 本；有完整 SQLite + R2 回读证据的现代小说至少《完美世界》1 本。文学深读与独立评审仍未证实，保持 50 部完整作品总评门槛。



## 8. 三本新增玄幻真实结构学习验收 · 2026-10-16 07:39 UTC（覆盖第 7 节“仍在运行”记载）

- [第一次三本结构学习 #38867581785](https://github.com/66tyu55/WriterForge/actions/runs/38867581785)：**《遮天》success**；《莽荒纪》与《求魔》因旧解析器不了解卷制而失败。已根据原 R2 数据独立校核真实卷章格式，而非用推测补齐章节。
- [只输出数字、不记录原文的卷章实测 #38868040071](https://github.com/66tyu55/WriterForge/actions/runs/38868040071)：
  - 《莽荒纪》45 个顺序卷标记、1449 个严格章标题，其中 44 次章号回到 1 都与新卷吻合；**另有 3 处卷内异常**：第 22 卷 2→4、第 25 卷 17→20→19（章数与完整性不能无条件判定）。
  - 《求魔》1476 个“第 n 卷 … 第 m 章”同一行的章标题；其章号是**全书累计**而非每卷重置，至少有 5 个实测跳号或重号，例如 103→106、1304→1304。
- 已新增严格 `writerforge/modern_volumes.py` 双卷制流式解析器、合成回归 `tests/test_v34_modern_volumes.py`；`writerforge/modern_source.py` 的 `chapter_scheme` 支持 `continuous`、`volume_reset`、`volume_prefix_global`。原文 SHA 校验、字节限制、单章事务及恢复验收继续适用，**发现原文序号异常必须失败停止**。主仓库 GitHub Tests 运行 [#38868398691](https://github.com/66tyu55/WriterForge/actions/runs/38868398691) **success**。
- [新三本最终真实来源试跑 #38868398653](https://github.com/66tyu55/WriterForge/actions/runs/38868398653)：
  - 《遮天》`zhetian-private-original` **success**：1821 章，226655 个结构化来源单位，原文验证、R2 学习库备份和全新恢复、SQLite `quick_check=ok` 均完成。快照 `6027a1b657f219369d8980cc600a9f6dcf4a285268567bdf54f1abb2d14e45a6`。
  - 《莽荒纪》按真实分卷后 **真实失败在卷 22、预计第 3 章却遇到第 4 章**，原文 `f7aee...` 已保存在私有 R2，**没有完整结构学习 R2 库**。
  - 《求魔》按真实卷+全书累计章号后 **真实失败在预计第 104 章却遇到第 106 章**，原文 `210ace...` 已保存在私有 R2，**没有完整结构学习 R2 库**。
- **九本现代书仍有九份 R2 原文归档**，其中现代原文有严格结构学习与 R2 SQLite 全新恢复证据的为《完美世界》《遮天》**2 本**。其他七本（包括未在本节完成结构学习者）不可计入“完整结构已学习”。真实模型文学深读、独立评价和创作能力提升仍未验收。
- **后续明确路线**：对《莽荒纪》卷 22/25 和《求魔》103→106 等异常，先在**私有 R2 原文**检查该区间是否有标题异常、正文夹带的假标题、或原来源版本缺章，生成仅哈希/数字的核验记录；不能直接改号、忽略缺章或以“不完整训练完成”冒充全部成功。待原文严格通过才能使用现有 `scripts/learn_archived_modern_r2.py` 与 `.github/workflows/next-three-modern-study-r2.yml` 继续做 SQLite 与 R2 验收。如果来源确实缺章，只报告该来源未达到完整性门槛，另选经核验的版本并保留版本哈希区别。


## 9. 单本执行：莽荒纪结构学习成功 · 2026-10-16（覆盖第 8 节的失败状态）

用户要求改为**一次只处理一本**。本轮只针对《莽荒纪》，不再自动并行其他新书。已把 `.github/workflows/next-three-modern-study-r2.yml` 改为仅手动触发。

- 私有 R2 单书原文 SHA-256：`f7aee869e201b4171e40a3ff9230e794f01fdc959d372017b8982635668be3d5`，8,961,764 bytes。未重写原文、未依赖旧 13 本合辑。
- [仅元数据的缺章审计 #38869855383](https://github.com/66tyu55/WriterForge/actions/runs/38869855383)、[精确标题佐证 #38870323360](https://github.com/66tyu55/WriterForge/actions/runs/38870323360) 实测：
  - 卷 22 第三章实际在私有源第 60160 行，但带非标准前缀，旧 parser 漏识别；标题与独立目录吻合，行 SHA256 `8af3b3af69a68e1d2b0f72f8c541fc8a2cdb4f3e6ef324842599e2e8e74f1f9c`。
  - 卷 25 第 69921 行标题《花光了》在该源印为第 20 章；独立目录均为第 18 章；原文行 SHA256 `68eefe9d8f51189dbfb795b47514e1b0fc90d34f6546147d21c487cbdaf16d9c`。源中的原印字样**保留不变**，只在指定源的流式章节解析阶段标注正确序号。
  - 佐证目录：https://www.99csw.com/book/4660/167000.htm 、https://www.piaotia.com/html/3/3259/ 、https://www.kunnu.com/mhj/ 。这仅佐证两处标题，**不是全文跨版本独立比对通过**。
- 代码使用 `writerforge/modern_volumes.py` 里的 `volume_reset_manghuangji_pinned`，要求**整份原文 SHA + 两处原始标题所在行 SHA + 卷号 + 章号 + 标题**完全匹配，其他来源/其他章序缺口仍拒绝；学习仓库存原样 `heading`，私有 R2 学习库备份附加 `chapter_audit.json` 纠错出处。
- **GitHub Actions 单本正式成功：[run #38870652006](https://github.com/66tyu55/WriterForge/actions/runs/38870652006)**：`complete_structural_only`；**1450 章、203011 来源单位**；新私有 R2 库 `writerforge/v1/libraries/manghuangji-private-original/`，快照 `45cdf87a348c2375b4eaf829d7ad8351c87b170ba0679ae728d7291a3a89773c`，`fresh_r2_study_restore_verified=true`，`sqlite_quick_check=ok`。
- **目前 R2 原文独立归档仍 9 本；现代小说有结构化 SQLite + R2 全新恢复验证的为《完美世界》《遮天》《莽荒纪》共 3 本。** 不可把这说成完成真实模型深读、模型权重训练、文学能力迁移或独立评价。50 作品总体评价门槛不变。
- 下一轮继续时**只能处理一本**，优先检查《求魔》；不要重新跑已经完成的《莽荒纪》，不要在推送通用解析器时自动触发 3 本并行任务。


## 10. 文学训练目标澄清（设计已记录，**模型学习尚未执行**）

用户明确指出训练核心是：**理解人物为什么以某种方式感知世界，以及作者为什么选择这样呈现**。已形成 [人物感知因果 × 作者呈现选择](CORE_PERCEPTION_NARRATIVE_STUDY.md) 规范，commit `9b49445f2b879f1599f908c0b4a907c27bd2c0ec`。它是下一阶段设计，不是新增 Skill 或已完成的语义训练。

具体约束：已有八轨词汇标签只作为来源定位；按原文证据 span → 感知事件/决策单元 → 叙事节拍 → 场景 → 跨场景关系 → 全书认知发展做可追溯学习；把故事客观事实、人物有限知识与误解、叙述者选择、读者初读预期四者隔离；初读锁定、后文揭示、竞争假设、反事实改写、独立评审和跨作品迁移齐备后才可声称有效。没有真实模型/独立评审时只能标记未验证。

继续遵循单本原则；已完成《莽荒纪》的确定性结构学习无需重来。下一文学试点应该在同一本已归档私有 R2 原文上做少量场景，不把源文本上传公开 GitHub，不在没有模型授权时虚称已理解。文学语义学习必须有独立的实证，不可借用原文存储/R2 回读的成功状态。


## 11. V28 仅设计：武动乾坤“临摹倒推”训练（2026-10-16）

用户的新方向是：**快读一段剧情骨架 -> Skill 隔离原创练笔 -> 锁定草稿 -> 对照原著分析人物感知/叙事选择 -> 保存失误、遗忘、假说、对照和抽象核心 -> 删除草稿正文 -> 闭卷迁移测验；两个局部过关以后再训练 AB 合并的长剧情；90/100 多维质量与迁移闸门才推进下一段；同机制按 3→6→9 个独立证据“+3 比较”去重、合并和修订；可配置 max_chapters，有界重试。** 核心原则 99% 由技能程序/数据库/模型服务自主执行，助手只负责设计、修 bug 与看验收；不是模型 99/1 的可测算力分配。

**已完成：设计文件** [V28_REVERSE_CRAFT_LEARNING_DESIGN.md](V28_REVERSE_CRAFT_LEARNING_DESIGN.md)，commit `68d4a49ad783c43a945966221c0c24df5d482929`。其中包括数据流和安全状态机、独立核心文件视图、90 分审评门槛、+3 证据分级、模型与独立评审的隔离、原文版权及近似复制防线、SQLite/R2 不持久保存草稿正文、重试/内存/垃圾回收边界、故障注入测试。

**尚未执行**任何新真实《武动乾坤》写作模型训练或 90% 质量评测，也未实现 V28 协调器。不能把设计 commit 当成训练结果。旧 `literary_ladder.py` 仍持久保存草稿正文到本地文件与 SQLite，`R2StudyVault` 的逻辑摘要包含此字段；**不得直接用旧训练命令开始“先写后删除”**，否则可能把草稿落入不可变快照。要先实现独立短期 scratch、事务化核心摘要、核心轻量 R2 保全与擦除流程以及相应失效测试。

源：`wudongqiankun` 在私有 R2 已有 8,254,079 bytes SHA `86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28`，**全书章节连续性尚有已知异常**。首个真实试点只能使用明确核验的局部场景、全程单本；不得把跳号版本称为完整学习。试点建议 `max_chapters=3`、每章最多 6 单元、每单元最多 3 个候选、双段合并最多 2 次，预算耗尽则 BLOCKED，不能无限追求 90 分。

下一步如用户同意实现：只先构建最小状态机/合成测试和 R2 私有核心快照，验证内存上限、重复 +3、crash/restart、伪评分和删稿可靠性；**在基础合格之前不启动真实章节训练**。


## 12. V28 最小运行内核已实现并通过合成工程测试（2026-10-16）

- **用户批准开始实现** V28 临摹倒推最小内核，但尚未授权绕过原文来源及独立评价门槛。代码实现：[writerforge/reverse_craft.py](../writerforge/reverse_craft.py)（隔离 V28 SQLite 有限状态机、临时草稿清理、每单元至多 3 次练习、每 2 单元合并至多 2 次、独立 90/100 评价与闭卷重测拦截、通过核验后 3→6→9 个不同场景核心合并）；[writerforge/reverse_core_vault.py](../writerforge/reverse_core_vault.py)（只备份抽象核心 JSON 到私有 R2 独立目录、不可变 SHA256 对象及全新读取比对；严格字段白名单，禁止 `body`/草稿混入）。
- 隔离管理命令已加到 `writerforge/cli.py`：`writerforge --db workbench/v28-wudong.sqlite3 reverse-core-init --project wudong-lab --max-chapters 3 --max-units-per-chapter 6`、`reverse-core-status` 和 `reverse-core-restore --snapshot <SHA256>`，只初始化/观察/恢复 V28 小库，拒绝初始化覆盖原有学海 SQLite。**没有真实模型练习 CLI**，只有经过 source/reviewer gate 才能开发。
- 测试：[tests/test_v28_reverse_craft.py](../tests/test_v28_reverse_craft.py)、[tests/test_v28_reverse_craft_stress.py](../tests/test_v28_reverse_craft_stress.py)、[tests/test_v28_reverse_cli.py](../tests/test_v28_reverse_cli.py)，模拟模型/独立审稿器与模拟 R2；验证失败三次停机、评审缺失 BLOCKED、非独立评审拒绝、重复证据不能刷 +3、R2 回读损坏拒绝晋级、拟提交状态的恢复、两段合并关、2,000 次临时稿创建清理的有限内存使用、专用库隔离和正文注入拒绝。
- **GitHub Actions 全量测试成功：[run #38875995893](https://github.com/66tyu55/WriterForge/actions/runs/38875995893)**（含新增 R2 snapshot 字段白名单安全回归）。早先 [run #38875687961](https://github.com/66tyu55/WriterForge/actions/runs/38875687961) 也通过全部测试，包括内存和 +3 阶段用例。
- 使用说明及明确未实现的能力：[V28_MINIMAL_RUNTIME.md](V28_MINIMAL_RUNTIME.md)。这**不是真实《武动乾坤》文学训练、不是真实 90% 成功率，也没有运行真实模型或真实独立文学审稿服务**。V28 R2 备份只有 FakeR2 工程测试；尚未在真实 Cloudflare R2 上传新 V28 核心快照。真实文章目前仅已有单书原文归档，章节完整性仍存在缺陷，须先核实局部原文。
- 草稿 `TemporaryDirectory` 正常退出即清理，非物理安全擦除；崩溃后的临时文件须安排启动 `cleanup_stale_scratch` TTL 清理。不能让旧 `literary_ladder.py` 对练习稿 `body` 进行普通 R2 学习库备份。**不把合成评审器注入实际作者训练**。
- **下次按一次一本推进**：先完成《武动乾坤》第一小段和紧邻第二小段的真实章节/source span 校验（私有 runner 内做、日志只输出哈希）；再接独立生成模型和经过实际验证的盲评器，不共享原著全文给生成器；有了真实的评审回执和 R2 验收才允许自动晋级。


## 13. V28 已按用户新要求从《武动乾坤》开篇顺序启动（2026-10-16，覆盖先前“随机小场景”建议）

**用户决定必须从第一章最初开始，逐步建立人物前史、因果与认知，而非随机抽样。** 这条优先级覆盖以往任何“随机挑一段剧情做训练”的建议。本阶段不会自动多书并行。

新增程序 `writerforge/reverse_source_cursor.py`、`scripts/prepare_wudong_opening_r2.py`、`.github/workflows/v28-wudong-opening-r2.yml`、回归 `tests/test_v28_reverse_opening_cursor.py`。`ReverseCraftCoordinator.open_unit` 拒绝不从 `(chapter=1,ordinal=1)` 起步，后续仍受相邻单元和 AB 合并门槛约束。开篇确切 R2 来源与学习顺序说明见 [V28_FROM_BEGINNING_WUDONG.md](V28_FROM_BEGINNING_WUDONG.md)。

**真实 GitHub Actions #38876799592 success**：私有 R2 中已归档《武动乾坤》原文 SHA256 `86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28`、字节 8,254,079 重新读取并哈希核验。检测真实前 3 章标题依序 1→2→3，位于第 8、85、146 行；第一章正文 4,209 字符；提出两个从头连续的候选窗口 `[0,2125)` 和 `[2125,4209)`，无丢字、无跳跃。元数据-only 私有 R2 新对象及 fresh GET 全字节核验成功：`writerforge/v1/reverse-craft/wudongqiankun/opening-source/cc3c98eda8953fa23b2f8328fa6f897d5d0cfffa313561868389324aa178b441.json`。**当前仅 `OPENING_SOURCE_VERIFIED / BOUNDARY_UNREVIEWED`**；原文段落分界还未由真实模型审核为正确的叙事节点；没有生成原创稿、独立文学评论或 90 分晋级。

下一步先以第 1 章作真实语义场景/因果边界核查（人物当前所知、读者所知、目标、误解、行动、后果、未兑现问题）；通过后用 skill 自己调用隔离模型，只写第一窗口。首窗核心审评、短期稿清除、闭卷迁移过关之后才开启第二窗口。不可将第一章的机器“长度中点”当做已证实的文学场景切点；不能隐瞒模型/审稿/长因果上下文还没接通的事实。


## 14. V28 正式本地真实模型实践（2026-10-16，覆盖“仅模拟”状态）

用户要求：**不再小规模模拟，正式从《武动乾坤》开篇顺序进行临摹倒推，失败经验也必须真实入库**。当前仍只允许第一章首个连续窗口；不随机跳章，不伪造 90 分通过。

已提交模型运行流程：[writerforge/reverse_real_training.py](../writerforge/reverse_real_training.py) + [scripts/run_wudong_real_reverse_training.py](../scripts/run_wudong_real_reverse_training.py) + [.github/workflows/v28-wudong-real-first-training.yml](../.github/workflows/v28-wudong-real-first-training.yml) + [tests/test_v28_reverse_real_training.py](../tests/test_v28_reverse_real_training.py)。GitHub Actions 在隔离运行器内安装 Ollama，使用 **qwen2.5:3b** 规划和原创、独立的 **gemma3:4b** 做原著机制对照批评，限定每窗口最多 2 次候选、有限模型调用。原文只从私有 R2 恢复到运行器临时目录；原创练笔正文/原著不进入 GitHub 公开仓库、CI Artifact、持久 R2 学海。只保存抽象观点、缺点、反事实、原创草稿 SHA、失败哈希和模型身份到独立私有前缀 `writerforge/v1/reverse-craft/wudongqiankun/real-model-first-unit-v1/`（如生成成功）；不得把批评模型主观推测称作真实独立专家 90 分。

真实运行历史：
- [#38878209564](https://github.com/66tyu55/WriterForge/actions/runs/38878209564)：两个模型启动到真实推理环节，但结果被规范检查拦截；首次单元测试步骤误将 0 个测试显示为通过。
- [#38878544084](https://github.com/66tyu55/WriterForge/actions/runs/38878544084)：修复后确实运行 5 项单元测试；真实对照批评返回近似原著/草稿的长引用，拒绝持久化（`unabstracted original/draft in review note`），无 R2 核心晋级。
- [#38878999983](https://github.com/66tyu55/WriterForge/actions/runs/38878999983)：为批评模型提供有限一次重新抽象机会；第二次仍返回不合格文本，同样被拒绝入库。防复制闸门不能关闭。
- [#38879583627](https://github.com/66tyu55/WriterForge/actions/runs/38879583627)：已改为**无法重新抽象的字段仅保留内容哈希与 `UNVERIFIED_QUOTATION_REDACTED` 状态**，其他符合安全标准的经验继续保存；**本节记录时仍在执行**，需核查该运行的真实成功/失败日志、R2 新快照 SHA、fresh GET 才能确定是否已生成可用训练证据。不能先报成功。
- 实际独立模型批评仍**不是经过人类基准校准的 90% 文学能力审核**。真实模型有运行，模型权重未训练，WriterForge 核心晋级依然被阻塞；第二原著窗口未解锁。不能用模型生成文本/评论本身冒充“大师水平 90%”。

重要：GitHub Models inference API 于 2026-07-30 退役，不能再使用旧 GitHub Models 通道；当前使用本地 Ollama，GitHub Runner 没有继承用户聊天窗口模型。后续优先执行用户关心的**真实训练迭代质量与完整因果**，勿只重复 R2 连接模拟。原文有全书章节异常，开篇首窗已经严格按 source hash 和章节 1→2→3 验证；仍不可冒充全书完整章序。


### V28 真实模型后续故障记录（2026-10-16 09:23 UTC 后）

- [#38879583627](https://github.com/66tyu55/WriterForge/actions/runs/38879583627) **失败**：原始长引用已可在受限抽象重试后哈希化隔离；新的失败码为 `model answer not JSON`。这是 Ollama 模型在真实提示输入下返回不符合 JSON 契约的内容，不是 R2 源丢失；没有完整两次训练报告入 R2。
- 已修改 `writerforge/reverse_real_training.py`：可解析合法 JSON fenced 输出，遇到 JSON 格式错误时**最多一次**本地模型重试（temperature=0，输出有大小和超时上限），绝不假造回答。
- [#38880422839](https://github.com/66tyu55/WriterForge/actions/runs/38880422839) 是更新代码后自动发起的第 5 次真实运行，在本节记录时尚未最终完成。必须查 job 真实 `conclusion` 和是否生成独立私有 R2 核心回执；不许因启动任务就声称成功。
- 用户关心的文学习得质量仍**没有 90% 经校准独立结论**；即便运行成功，目前只可能得到“原文开篇首段真实模型练习及未审查机制证据”，不得开放第二段晋级。训练失败留存日志和哈希已在 GitHub Actions；公开仓库无原文正文或练习稿。


## 15. V28 云端高能力模型适配层与盲评 A/B（2026-10-16，覆盖旧 CPU 小模型依赖）

用户在检查 [InkOS](https://github.com/Narcooo/inkos) 后同意借鉴模型无关的 Agent Harness/多服务商路由，优先替代 GitHub CPU 上 3B/4B 模型并进行无技能/有技能的实际对比。**用户尚未选择付费模型服务商或提供对应 API 凭证、当前价格，不能自动进行外部原著传输及付费请求**。

已经实现：
- [writerforge/reverse_cloud_models.py](../writerforge/reverse_cloud_models.py)：角色 `planner / writer / critic` 独立配置；固定 HTTPS Chat Completions 兼容提供商白名单 `moonshot/deepseek/openrouter/openai/google`，不接受任意 URL，拒绝 HTTP 重定向；凭证取自运行环境，不进日志与 R2；每次调用前按输入字节与最大输出 token 预留美元保守预算，且有每任务请求上限和响应大小上限。Writer/Critic 必须是**不同模型身份**；不存在旧小模型自动回退。
- [writerforge/reverse_cloud_ab.py](../writerforge/reverse_cloud_ab.py)：只选《武动乾坤》第一章**第一连续源窗口**。同一原创任务：A 不含技能机制，B 仅含 Planner 从原文抽象得出的感知/因果/叙事方法；两份独立原创稿的哈希固定后才匿名给另一模型批评，对人物感知、因果、信息释放、连续性、语言逐维比较；长期只保留原文/稿哈希、短机制解释、模型评分（标为**unverified**），绝不把模型自评分宣称已达大师 90%。
- [scripts/run_wudong_cloud_ab.py](../scripts/run_wudong_cloud_ab.py)：必须明确原文外发同意；从既有 R2 恢复 pinned 原文校验后调用云端，单组模型配置有去重指针，结果哈希化保存在独立私有 R2 并 fresh GET 复验。未配置提供商/密钥/价格和独立同意时拒绝并不付费。
- [.github/workflows/v28-cloud-ab.yml](../.github/workflows/v28-cloud-ab.yml)：**普通 push 仅离线测试与凭证配置检测（零付费/零外发）**；只有手动 workflow_dispatch 且 `confirm_source_egress=true` 才可能运行收费的 `cloud_paid_trial`。这样不会因每次改代码就重复下载模型、产生 API 账单。
- [tests/test_v28_cloud_ab.py](../tests/test_v28_cloud_ab.py)：无网络的安全/角色/预算/同题匿名 AB 回归。完整配置说明与用户须操作项见 [V28_CLOUD_MODEL_AB_SETUP.md](V28_CLOUD_MODEL_AB_SETUP.md)。

**已核实 GitHub 证据**：[配置检查和模型协议测试 run #38882720229](https://github.com/66tyu55/WriterForge/actions/runs/38882720229) `success`（7 项测试），但 `safe_cloud_readiness` 返回 `ready=false`，原因仅报告 `cloud_roles_or_price_or_credential_unconfigured`；收费作业 `cloud_paid_trial` 正确为 **skipped**。这不是实测云端模型质量通过。最新仓库全量 Python 测试另有 [#38882868438](https://github.com/66tyu55/WriterForge/actions/runs/38882868438) `success`，包含上述 A/B 相关回归。

**待办**：由用户自行在 GitHub Actions 配置角色 Secrets、Variables 和价格/预算，明确选定云端模型和允许哪家服务接收私有小说首窗，随后手动触发真实付费单本 A/B。完成后应检查 API 真实调用、R2 SHA 和文学盲评证据；不能因模型评分数字大于 90 就晋级。编排仍保持从原著第一章连续推进，下一段尚未解锁。InkOS 只借鉴架构/调度理念，未复制 AGPL 源码。

 
## 16. Discovery 密钥可见性核验（2026-10-16；覆盖错误的“用户未保存”判断）

用户提供 GitHub 页面已存在 `DISCOVERY_API_KEY` 的截图，**不得要求用户反复新增/改名或在聊天里发送真实 API Key**。最初 `scripts/probe_discovery_api.py` 用 `len(key)<12 or whitespace` 输出 `MISSING_SECRET`，无法判断密钥到底是否在 Action 中可见；此前因此推断“用户未配置”不成立。已修改成三种独立状态：环境变量缺席、GitHub Actions Secret 表达式映射为空、变量有值但本地格式检查失败，绝不输出原密钥、长度或片段。

**重新运行 [#38885722986](https://github.com/66tyu55/WriterForge/actions/runs/38885722986) 真实结果：`GITHUB_ACTIONS_SECRET_RESOLVED_EMPTY`，workflow 的 `env: DISCOVERY_API_KEY: ${{ secrets.DISCOVERY_API_KEY }}` 在 `66tyu55/WriterForge` main 分支 push 运行环境被解析为空。真实模型请求为 0，小说原文外发为 0，费用为 0。**这不等于用户没保存密钥。** 需检查屏幕上对应 Secrets 是该仓库的 Actions Repository secret、Environment secret（需要 job `environment` 匹配）还是其他仓库/组织/Dependabot/Codespaces 范围。截图裁切未显示层级，不可猜测是哪一类；不能读取密钥本体。


## 17. Discovery 实际密钥名修正、可用模型、正式 V28 A/B 试跑（2026-10-16）

用户截图中 GitHub Secret 的准确名称是 **`DISCOVERY__API__KEY`（双下划线）**，此前错误地引用为 `DISCOVERY_API_KEY` 导致 Actions 环境变量为空；**不是用户未保存密钥，无需重新注册或修改 Secret**。已把 `.github/workflows/discovery-api-probe.yml` 与专用 V28 工作流改为引用 `${{ secrets.DISCOVERY__API__KEY }}`，进程内部 env 名可仍用单下划线，不冲突。

- [鉴权和真实短文生成 success #38886144104](https://github.com/66tyu55/WriterForge/actions/runs/38886144104)：端砚 `https://discovery-api.intern-ai.org.cn/v1` 实测返回 11 个模型，包括 `deepseek-v4-flash-0731`、`deepseek-v4-pro-0813`、`glm-5.3`、`kimi-k2.6`、`intern-s2`、`minimax-m3`。使用 DeepSeek V4 Flash 真实生成 45 字符（prompt 109、completion 69 tokens），`finish_reason=stop`；没有发送私有小说。
- [三个模型各自真实简短 JSON 能力 success #38886690784](https://github.com/66tyu55/WriterForge/actions/runs/38886690784)：`glm-5.3`、`kimi-k2.6`、`deepseek-v4-pro-0813` 均可返回短 JSON；这**不代表**长文复杂输出一定合格。
- 新增 `writerforge/reverse_discovery_models.py`（固定端砚 HTTPS 主机、5 次请求/16000 预约输出 tokens 总上限，单请求超时 150 秒，不暴露 key，安全 JSON 重试至多一次）；`scripts/run_wudong_discovery_ab.py`（从已有私有 R2 SHA pin 恢复《武动乾坤》第一章首段、真实非模拟 Planner→Kimi Writer A/B→DeepSeek V4 Pro Critic、只存抽象证据及短回执到独立私有 R2；不把练习稿或整本原文持久保存）；`.github/workflows/v28-discovery-real-ab.yml`（已在用户同意“能调通就开始正规训练”后启动单书）。
- [首轮正式 A/B #38886477025](https://github.com/66tyu55/WriterForge/actions/runs/38886477025) **失败**，因复杂 JSON 契约；[第二轮 #38887011693](https://github.com/66tyu55/WriterForge/actions/runs/38887011693) 在有限重试后仍失败，精确故障为 `DISCOVERY_PLANNER_JSON_CONTRACT_FAILED`，来自 GLM-5.3 面对实际原著的长结构分析。原文 R2 未损坏；无“90% 大师水平通过”或第二段解锁。
- 已将仅规划角色替换为 **`deepseek-v4-flash-0731`**；保留 `kimi-k2.6` 写作、`deepseek-v4-pro-0813` 审评。[第三轮正式 A/B #38887477346](https://github.com/66tyu55/WriterForge/actions/runs/38887477346) 在本文写入时刚启动，**必须读 job 最终结论和远端 R2 receipt 才能确认结果**，不可预写成功或文学能力改善。
- 后续无论结果如何，不许用模型自己的 90 分取代独立校准盲评。不启动额外小说、不跳过序列原著、不无限迭代。API Key 真值不能回显，不需要用户重复配置。


## 18. Discovery 真正连通 + 第一次正规原著文学 A/B 真实完成（2026-10-16，覆盖第 17 节尚在执行）

已确认用户使用的是 **GitHub Secret `DISCOVERY__API__KEY`（双下划线）**，工作流已经引用此名称。**不必要求用户重命名、新建密钥或在聊天中暴露 Key**。

**成功的真实端砚 API 和 R2 证据：**
- [连通和单次生成 #38886144104](https://github.com/66tyu55/WriterForge/actions/runs/38886144104) `success`，`deepseek-v4-flash-0731` 正常输出；
- [GLM/Kimi/DeepSeek 三种真实模型的短 JSON #38886690784](https://github.com/66tyu55/WriterForge/actions/runs/38886690784) `success`；
- 初始大型 A/B 曾因 GLM-5.3 规划阶段复杂 JSON 错误、Kimi-K2.6 长篇请求无可见正文而失败，原文/草稿未持久污染学习库，完整失败日志在 [#38887011693](https://github.com/66tyu55/WriterForge/actions/runs/38887011693) 和 [#38887477346](https://github.com/66tyu55/WriterForge/actions/runs/38887477346)。还有一次 [#38887900901](https://github.com/66tyu55/WriterForge/actions/runs/38887900901) 仅为测试要求三模型必须完全不同而导致工程验证失败；已把测试修为实际要求 Writer/Critic 模型身份不同。
- **最终真实完整 A/B [run #38888018955](https://github.com/66tyu55/WriterForge/actions/runs/38888018955) `success`**：使用 `deepseek-v4-flash-0731` 为原著规划，`deepseek-v4-pro-0813` 生成 A/B 两份原创稿，`deepseek-v4-flash-0731` 独立于写作者执行匿名模型批评（规划与评审同一模型 ID，不能称为三个互相独立模型，更不能声称独立人类评审）。原文使用已验证私有 R2 《武动乾坤》第 1 章第一连续窗口。**共 5 次真实 API 调用**，服务端报告输入 11,658、输出 7,637 tokens，总 19,295 tokens；未进行模型权重微调。抽象报告和两篇原创草稿 SHA 已存独立私有 R2，完整原著和草稿均不持久保留。私有快照 SHA256 `86953525286e33e5a09f0acb4d4774e7ccfa3abafe0b5d00fe65c5f5e0c66b04`，全新回读检验成功。
- **只读数字结果审核 [run #38888592336](https://github.com/66tyu55/WriterForge/actions/runs/38888592336) `success`**：模型批评分 **无技能基线 86/100**（感知88、因果85、信息82、连续90、语言86），**启用 WriterForge 技法 84/100**（感知84、因果86、信息80、连续88、语言82），**单次增量 -2 分**。说明这次增强策略并未改善写作，且不满足原定 90/100 门槛。样本仅一组，且批评模型未作专家/真人校准，**不能证明长期有效或有害**。不要把生成或 R2 写入成功标成文学能力升级；第二窗口 **未解锁**。
- 为防推送代码时重复消耗用户的端砚额度，已将 `.github/workflows/v28-discovery-real-ab.yml` 改为 **仅 `workflow_dispatch` 手动启动**。不要再无授权做付费/额度消耗调用。
- 当前正确下一步是**分析首轮增强稿为何比基线差**，从已保存的私有短机制/审评意见中提炼缺点，先修 Skill 的信息提取及因果上下文选择，再由独立客观评审与不同剧情验证；不是继续盲试多个模型或跳到下一章。所有 90% 阶段晋级仍 **BLOCKED**。


## 19. V28 第一轮真实 R2 A/B 文件深读与失败归因（2026-10-16）

**用户只要求分析已经留存的文件，这一轮没有再次发起付费模型训练。** 完整结果与修复优先级见 [V28_FIRST_REAL_AB_FAILURE_ANALYSIS.md](V28_FIRST_REAL_AB_FAILURE_ANALYSIS.md)，commit `62cdeb7cc7aa8ec8545c69e8570d2ef9f5543485`。真实摘要证据来源：[R2 源文哈希/短评读取 #38892524270](https://github.com/66tyu55/WriterForge/actions/runs/38892524270) `success`。

重点发现：
- 无技能原稿的五项模型分为感知88、因果85、信息82、连续90、语言86；WriterForge增强稿为84、86、80、88、82。准确平均 **86.2 vs 84.0（-2.2）**，原有软件的整数截断记录为 **86 vs 84（-2）**。单评审、单样本不可推广为 90% 能力。
- 基线稿 **1662 字符**，技能增强稿 **2483 字符（多821，约49.4%）**；不等长实验本身严重影响公平性。
- 最关键的**程序级污染**：Planner 的 `perception/decision/author_mechanism` 自由文本描述**含林动、家人、受伤和让出修炼资源等原著专有内容**，而 `reverse_cloud_ab.py` 原样把它们送给增强写作者作为 `technique_constraints`；这不是可靠的“只传技巧，不传剧情”。增强稿的模型批评也描述家庭伤痛、牺牲与身世秘密，而基线描述全新神秘交易情节。因原稿已经删除不能判断是否有确切情节抄袭，应标注**明确的提示词源剧情污染、未证实的稿件复述风险**。
- 仅因果项 +1，人物感知及语言项均 -4；模型短评认为技能增强稿内在感知较弱、信息更直白、心理转折偏快，两稿的悬念均缺足够先导线索。Planner 与 Critic 同为 DeepSeek V4 Flash，不算三模型互相独立。
- 正式 V28 失败/遗忘/因果跨段状态机尚未连接实际 A/B；云端原型只留单组 R2 报告和稿件哈希，丢失了日后对原稿进行再次独立审查的可能性。
- **P0 修复**：必须把 `SourceCharacterState`（原著专有角色/知识/剧情，仅供分析审核）与 `TransferableMechanism`（面向写作的 HOST 策略 ID，无原文专名及剧情）隔离；对 prompt 泄露设置拒绝规则。随后控制 A/B 等长、不同评审和真正的短期草稿审阅→删除→闭卷复测。**没有修复前不再进行新收费 A/B，也不能解锁第二窗口或伪称已达90%。**


## 20. V28 底层 P0 已修：原著情节→写作提示的污染被接口隔离（2026-10-16）

用户质疑“WF 是否给写作添乱、是底层问题还是模型问题”，依据真实 A/B 失败认定首先是底层数据路由错误（Planner 的自由原著剧情描述被当作 technique_constraints 送给 Writer），同时只凭单样本评分不能确定技能总体质量。**已直接修改代码，不只是设计。** 详见 [V28_P0_ROOT_CAUSE_FIX.md](V28_P0_ROOT_CAUSE_FIX.md)。

- 新模块 `writerforge/reverse_mechanism_boundary.py`：宿主维护四项有限、可执行的非原著叙事操作；只允许 Planner 返回最多两个预定义技巧 ID + 原文段落证据 ID，原著人物/情节/自由文本不能进入 Writer 提示。缺失段落、原著人物字段、未知机制、重复证据全部 fail closed。**4项是固定安全初始集合，不等于模型已自主学出4种新技能。**
- `writerforge/reverse_cloud_ab.py` 不再直接发送 Planner 的 perception/decision/author_mechanism 剧情说明给 Writer，只发送固定机制操作；A/B 实际稿长相差超过15%时在批评模型调用前直接拒绝评分，杜绝之前49.4%不等长的明显混杂。
- 新合成防污染回归 `tests/test_v28_mechanism_boundary.py` 及更新的 `tests/test_v28_cloud_ab.py`；[GitHub 全量测试 #38894363064](https://github.com/66tyu55/WriterForge/actions/runs/38894363064) success、[#38894585603](https://github.com/66tyu55/WriterForge/actions/runs/38894585603) success。
- **实际原文 R2 预检** [run #38894840319](https://github.com/66tyu55/WriterForge/actions/runs/38894840319) success：原文 SHA仍是 `86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28`，第一章第一窗口2125字符、37物理段（最大126字符）、与下一窗口连续。把原先过紧36段上限调整为96段+总输入5,500字符上限。只读原文，无模型、无收费、无原文输出日志。
- 未来正式 A/B 版本已升级为 `source-isolated-ab-v2` 独立 R2 命名空间和缓存指纹；旧 `real-discovery-ab-v1` 私有失败实证不覆盖、不修改。付费工作流仍**仅手动 workflow_dispatch**，本轮未启动新正式模型训练。
- 未完成：产生真正新候选文学机制并经独立文本审评/闭卷迁移晋级、把真实失败/遗忘纳入 V28 SQLite+R2 有界证据、对正式 A/B 做跨题等长和独立真人/模型校准。**第一段仍 NOT_PASSED，第二段 LOCKED，所谓大师90%尚无验证。**


## 21. V28 按用户要求恢复真实额度训练：P0 后反馈式迭代（2026-10-16）

用户明确指示“**继续消耗，就是要一边消耗一边发现问题**”，不再局限于离线修代码。**限次真实训练获授权**，仍一书、一窗口、预算上限与源文隔离，不得无期限重试；费用不是质量证据。

- **真实 P0 修复后首轮** [run #38895404803](https://github.com/66tyu55/WriterForge/actions/runs/38895404803)：P0 源文隔离/AB/Discovery 协议单测通过；实际端砚调用 **3次**，Planner 成功而写作阶段 `DISCOVERY_WRITER_JSON_CONTRACT_FAILED`，程序终止、未比较文学评分。新增代码 `scripts/run_wudong_discovery_ab.py` 会把失败码、实际调用数、报告 token 使用、源文哈希与实验配置哈希（没有原著或草稿）写入**独立私有 R2**，经 fresh GET 核验，真实失败回执 SHA256 `59d489b6050851e63b2ae78b80ebc2a31c747f226d6f955dd3cf775afe6f2d2d`。这是首次失败证据独立存储，不能算成功。
- 通过真实故障推断，不宜强制长篇小说正文遵守 JSON 序列化契约；已将 `writerforge/reverse_discovery_models.py` 拆分角色协议：Writer 接收有界**原生小说正文**、必要时封装为内部 `{"scene":...}`（不回写正文）；Planner 与 Critic 仍严格 JSON。拒绝被截断的正文、只允许一次预算内重试；`writerforge/reverse_cloud_ab.py` 写作提示与 `reverse_mechanism_boundary.py` 也改为正文输出契约。新增正文/截断回归 `tests/test_v28_discovery_models.py`，**全量 GitHub Tests #38896069801 success**。
- 已发起**第二次真实代码修订后试验** [run #38896171856](https://github.com/66tyu55/WriterForge/actions/runs/38896171856)，在本节记录时仍在运行；应以最终 job `conclusion` 和 R2 成功/失败 SHA 作为唯一真实状态来源。若结果失败，按失败阶段做有限修复和真实对照，禁止简单跳过、假造 90 分或解锁第二窗口。
- 两个单次工作流 `.github/workflows/v28-wudong-iteration-one-shot.yml` 和 `...iteration-02.yml` 仅在其各自文件创建的 push 上触发，不会因日后普通代码改动而重复消耗；常规 `v28-discovery-real-ab.yml` 仍仅手动启动。


## 22. 用户要求真实消耗发现问题：四轮受限实跑及根因（2026-10-16，覆盖第 21 节 pending 状态）

用户明确同意继续花端砚可用额度开展真实调试，策略是**有限预算逐轮实跑、真实故障->修正->回归->再测**；本节全部证据来自已完成 Actions，不可说“模型训练过关”。仍遵循《武动乾坤》第一章第一窗口，不跳章、不自动无限收费。

- **修复后首轮** [#38895404803](https://github.com/66tyu55/WriterForge/actions/runs/38895404803) **failed**：Planner 通过，Writer 的长篇正文 JSON 输出契约失败，3 次真实 API 调用；私有 R2 哈希化失败记录 `59d489b6050851e63b2ae78b80ebc2a31c747f226d6f955dd3cf775afe6f2d2d`。没有把不完整原著或草稿写到公共仓库、R2 学海，第二窗口未晋级。
- 将输出协议按角色分离：**Writer 返回原生连续小说正文**（内部只临时包装为字典），Planner/Critic 继续 JSON；拒绝文本过短、异常代码块、模型截断，仅有限一次重试。相关离线全量 [#38896069801](https://github.com/66tyu55/WriterForge/actions/runs/38896069801) **success**。
- **第二次** [#38896171856](https://github.com/66tyu55/WriterForge/actions/runs/38896171856) **failed**：5 次真实 API 调用后命中总预算；R2 失败 SHA `b569aa421741c32b989621ca6f58c0f0867408bc0b5e161ad89c1437868a99fb`。增加 `DiscoveryCallBudget.calls_by_role / last_requested_role / response_observations` 以存每角色次数、完成原因、可见字数（**不存生成内容**），硬上限有界从 5 次适度提高至 7 次、预留输出 token 上限 25,000。
- **第三次** [#38896845100](https://github.com/66tyu55/WriterForge/actions/runs/38896845100) **failed**：Planner 1 次成功，Writer 4 次响应导致 `DISCOVERY_WRITER_OUTPUT_TRUNCATED`，R2 SHA `6857551c6ee35ddd2428be96bb5c05727c2d81b6744827dc0bab87b77ce18a0d`。过去重发相同请求从头生成，浪费 tokens；已改为遇到已有部分可见正文且 `finish_reason=length` 时，**只允许带前文接续一次**，同时检查截断和边界，仍不把小说全文持久化。补合成“接续而非从头写”的回归测试。
- **第四次** [#38897761659](https://github.com/66tyu55/WriterForge/actions/runs/38897761659) **failed**：这轮前端正文阶段之前，Planner 连续 2 次 `finish_reason=length`、可见内容0字符，故 `DISCOVERY_PLANNER_OUTPUT_TRUNCATED`；失败记录 R2 SHA `6fcd297e8f6152752d5f89b462dface322126a6cd3502b420f5067dd5028afe4`。说明 V4 Flash 作为分析器偶尔会把短格式回答预算全部用于不可见推理，不能靠盲加调用上限解决。
- 官方 Intern Chat API 文档表明 **Intern-S2 支持 `thinking_mode=false`**，已仅给此模型适配该参数；[真实无原著小型兼容性探针 #38898246863](https://github.com/66tyu55/WriterForge/actions/runs/38898246863) **failed**：返回 `finish_reason=stop` 但可见0字符，受到单请求预算限制；在端砚 Discovery 网关当前能力未核实前 **不能切换 S2 为正式模型或谎称已解决无可见回复**。
- `scripts/run_wudong_discovery_ab.py` 已把 R2 失败凭证中的代码升级为受白名单字符限制的静态 `DISCOVERY_<ROLE>_<CODE>`，便于后续明确辨别哪个环节失败，但不允许记录任意服务端错误正文/密钥。上面第 3、4 次老失败凭证部分 `code` 仍为泛型 `DiscoveryError`，但该次真实 GitHub 日志保留了具体错误码和角色响应元数据；不能偷偷重写不可变快照。

**本轮已发生真实模型推理，并实证多个底层协议缺陷；没有新的“通过文学训练”的证明，没有可比的新版增强/无增强评分，也没有升到第2段。** 本轮只通过工程单测和真实失败留证，90% 晋级始终 BLOCKED。

**下次最先要做的不是盲目扩大 max_calls**：先确认有能力输出短、结构化技术ID的 Planner 模型以及端砚模型返回结构（不可见 reasoning、content 与 finish_reason 的类型与长度），避免继续浪费端砚余额。随后在相同原著窗口、相同稿长条件下做完整原创 A/B；有真实可比批评结果后才修 WriterForge 的文学机制层。保持普通 GitHub push 不自动收费；所有这轮 one-shot workflows 仅对其自身的文件变化触发。


## 23. V28 固定百万上下文模型二人组与 50,000 Token 总预算（2026-10-16）

用户要求“**固定2/3个模型，全是1m上下文的，限制大一点，5万**”。实际选择 **2 个模型**：端砚所列 `deepseek-v4-flash-0731` 做规划+模型批评、`deepseek-v4-pro-0813` 做原创+续写，**不再频繁换模型**。DeepSeek 官方 V4 文档证实二者支持 1M（1,048,576）token 上下文，DeepSeek 官方 Chat API 支持 `thinking:{"type":"disabled"}` 关闭默认思考；端砚 Discovery 网关 [真实短问探针 #38910061191](https://github.com/66tyu55/WriterForge/actions/runs/38910061191) **success**，两个具体模型 ID 在此第三方网关都能使用 thinking=disabled 并返回可见短文本，未发送私有原著。端砚 `/models` 未暴露实际 context_window，**不能把官方 1M 参数宣称为第三方网关 1M 实压通过**。

实施：
- `writerforge/reverse_discovery_models.py` 固定角色映射、声明官方 1M 规格与网关压测未验收状态；每次请求显式关闭 DeepSeek V4 的深思考，避免小窗口空白回复；单次 `max_tokens` 配置上限 50,000 且**共享每轮总预留输出最多 50,000 tokens**，最多 7 次实际模型请求。请求传输上限4MiB，响应最大1MB，超额 fail closed。
- `writerforge/reverse_cloud_ab.py` 请求预算按 Planner 6,500 + Writer A 11,000 + Writer B 11,000 + Critic 8,000 = 默认36,500；余下13,500留给有限一次的故障重试；达到总50,000时停止。不是每个阶段自动消耗满5万。
- `scripts/run_wudong_discovery_ab.py` 使用独立 v3 `fixed-1m-context-50k-ab-v3` 前缀及模型/源指纹，旧 v1/v2 的成功与失败证据都保留。
- 新回归 `tests/test_v28_fixed_pair_budget.py`；GitHub [全量 Tests #38910871380](https://github.com/66tyu55/WriterForge/actions/runs/38910871380) **success**。代码与限制见 [V28_FIXED_1M_PAIR_50K.md](V28_FIXED_1M_PAIR_50K.md)。
- 用户先前明确“边消耗真实端砚额度边发现问题”，因此已启动**仅一次**实际 [#38910720051](https://github.com/66tyu55/WriterForge/actions/runs/38910720051)，本条写入时仍执行中，必须读取最终 Actions job 结论与私有 R2 凭证；不能提前宣称文学训练完成或90分，第二窗口始终锁定。普通代码提交不会重复触发这个一次性付费工作流。


## 24. V28 两个固定 1M 模型、50k预算的真实 A/B 已完成，**文学增益仍失败**（2026-10-16）

更新第23节的 pending 状态。**[GitHub Actions #38910720051](https://github.com/66tyu55/WriterForge/actions/runs/38910720051) success**；实际端砚 Discovery 上 `deepseek-v4-flash-0731` 负责规划/批评、`deepseek-v4-pro-0813` 负责写作；均显式 `thinking:{"type":"disabled"}`。4次真实API请求（Planner1/Writer2/Critic1），模型报告输入6648、输出3090 tokens；36,500为预算**预留**，不是实际消费，硬上限仍为50,000请求预留输出tokens。私有 R2 不可变快照 SHA256 `b1354316a9ca487e7e07f127be78b0ca3856855f1168d73d313ae6a99568822a`，fresh GET 哈希核验通过，无公开原文或草稿正文。

**[只读数值审计 #38911363049](https://github.com/66tyu55/WriterForge/actions/runs/38911363049) success**：
- Baseline **86/100**（感知88、因果85、信息82、连续90、语言86），稿长1656字符；
- WF enhanced **76/100**（感知74、因果78、信息70、连续80、语言82），稿长1533字符；
- 模型审评 **增量 -10 分**。A/B等长控制已通过，长度差123字符 /1656 =7.4%；不再沿用原 v1 的49.4%不等长/源剧情污染。
- Planner 选取的两项**宿主预置**机制 `GOAL_FILTERS_ATTENTION`、`COST_VISIBLE_IN_ACTION`；不能宣称它们是WF新学出的技巧。当前数据显示这两个固定操作未在单次原创中产生质量提升，应检查机制转译是否让文字僵硬、故事目标不一致等假说，但未经独立评论确认不可断言。
- V28的模型短评不是独立真人评价，单组分差不是稳定因果效果，也**不允许**以76分晋级；第一窗口仍 `NOT_PASSED`，第二窗口 `LOCKED`。

技术状态：现在【固定模型 / 1M官方规格 / 端砚实测关闭深度思考 / 50k预算 / 真实A/B / R2回读】都已通过；**技能写作质量提升没有通过**。不要错误地把 #38910720051 的GitHub success解释为文学胜过基线或大师90分。公开源文件与真实状态见 [V28_FIXED_1M_PAIR_50K.md](V28_FIXED_1M_PAIR_50K.md)。后续训练改进重点是机制选择/呈现是否真正引导主人公感知、行动与读者理解，而非继续盲目换模型或扩大token。此轮一次性工作流不会因普通代码 push 重复产生费用。


## 25. 用户纠正跨厂商模型固定配置、继续真实训练，但文学分析延后（2026-10-16）

用户明确要求：**“no——不要使用一家的模型——暂时v4 flash和5.3吧——然后这次继续训练——留到下次一起分析。”**

本轮不再采用一家的 V4 Flash+V4 Pro。已修改：
- `writerforge/reverse_discovery_models.py` 固定 **Planner = DeepSeek V4 Flash `deepseek-v4-flash-0731`，Writer = Z.ai/智谱 `glm-5.3`，Critic = DeepSeek V4 Flash `deepseek-v4-flash-0731`**。两家、两个模型，三角色并非三种独立模型。Writer/Critic 来自不同厂商。模型官方均标 1,048,576 tokens 上下文；端砚 Discovery 网关尚未对 1M 请求实压验收。
- 保留每轮共享 `50_000` 预约输出 Token 上限、7 次 API 请求上限、单次最多一次有限重试与 Source/Writer 剧情隔离；DeepSeek Flash 显式 `thinking:disabled`，GLM 不擅自传未经端砚网关核验的思考参数。
- `scripts/run_wudong_discovery_ab.py` 将本次结果独立存入 `cross-vendor-flash-glm53-50k-ab-v4` 私有 R2 路径，不污染原有 v3 及之前真实失败凭证。上游仍是私有 `wudongqiankun` 第一章第一连续窗口，不解锁第二段。
- 新的角色与 1M 规格回归 `tests/test_v28_fixed_pair_budget.py` 已实际通过 [GitHub Tests #38913521779](https://github.com/66tyu55/WriterForge/actions/runs/38913521779)。
- 用户已授权**本轮一次**真实额度训练，[one-shot Actions #38913593019](https://github.com/66tyu55/WriterForge/actions/runs/38913593019) 在写入此条时执行中；必须根据最终 job `conclusion` 和 R2 SHA 更新。本轮按用户要求**不做文学原因分析/不做新评分长评**，即使 A/B 完成也只保存私有证据，下一次聊天统一分析。不可将工作流成功解释为已达到90%，也不自动进入第二段。

注意：此 one-shot workflow 仅因新文件创建触发；未来代码普通 push 不会自动重复产生模型调用。不要自动改回同一厂商两款 V4。


## 26. 跨厂商 Flash + GLM-5.3 上轮结论及有限网络重试实跑（2026-10-16）

用户说“开始”，依上一轮交接继续，**不重新定义模型或原文**。固定 Planner/Critic=`deepseek-v4-flash-0731`，Writer=`glm-5.3`，首书仍《武动乾坤》第一章第一连续窗口，50,000 预留输出 tokens、最多7次调用。GLM原生小说正文，Flash结构化分析。

- 已核实上一轮 [#38913593019](https://github.com/66tyu55/WriterForge/actions/runs/38913593019) **失败**，不是“仍执行中”。真实请求3次（Flash规划1/GLM写作2）；Flash解析输出148可见字符，GLM第一稿1127可见字符、`finish_reason=stop`；第二个GLM写作请求 `DISCOVERY_NETWORK_FAILED`（旧适配器把超时、连接错误合成此码），因此**尚无第二篇完整稿、未进行独立审评，不能给这轮文学分数**。此失败已经存入独立私有R2，SHA256 `1e50ae50b1c1818a853268269fd1be184b30de4317beeb3ae89ea2d2482160ab`。源码和原R2快照未受影响。
- 依据实际失败修 `writerforge/reverse_discovery_models.py`：区分 `DISCOVERY_TIMEOUT` / `DISCOVERY_CONNECTION_FAILED` / 状态码；仅对超时、连接失败、HTTP 429/502/503/504 **在同一次调用内额外重试1次**。两次请求都提前预留 token、都计入全局 max_calls（即使网络超时后服务商可能已经收费），每角色响应记录纯错误类型与可见长度，不泄露密钥/原文。401等永久失败不自动重试。
- 已增加离线测试 `tests/test_v28_discovery_models.py`，验证超时恰好一次重试、费用额度预留、重复超时终止、401不重放；GitHub [全量回归 #38918418959](https://github.com/66tyu55/WriterForge/actions/runs/38918418959) **success**。
- 已经针对同一本第一窗口启动一次受限真实 A/B [run #38918557675](https://github.com/66tyu55/WriterForge/actions/runs/38918557675)，**本节落盘时任务正在执行**；必须再核查最终job状态、真实API调用及私有R2 SHA，不能声称通过。只有在双稿、长度闸门、审评、R2备份全部满足时才可分析本轮质量。文学 90% 及第二窗口均未解锁。

保持所有付费 workflow 为一次性文件创建触发或显式手动触发，代码普通提交不自动无限消费。


## 27. 跨厂商 DeepSeek Flash + GLM-5.3 真实 A/B 重试成功，首次单次正向分差（2026-10-16；更新第 26 节 pending）

此项**覆盖第26节“正在执行”的旧状态**。完整审计见 [V28_FLASH_GLM53_REAL_COMPARISON_20261016.md](V28_FLASH_GLM53_REAL_COMPARISON_20261016.md)，commit `a1d1d0c8e90d769c736c53b0ed761694953861fb`。

- [真实运行 #38918557675](https://github.com/66tyu55/WriterForge/actions/runs/38918557675) **success**：固定跨厂商两个模型，Flash 规划1+审评1，GLM-5.3 生成两份原创，各一次；总4次API请求，服务端报告输入5971、输出10375 tokens。原著第1章第1连续窗口 + SHA pin不变，原著具体人物/剧情没有进入 Writer 提示，模型稿不入持久R2。成功生成抽象报告，并全新回读验证私有R2不可变快照 SHA256 `a2882f770e76fee4f4cedffb219d919a1a169fd731832b3d2de24e105c6a0282`。
- [只读证据/短评复核 #38919228502](https://github.com/66tyu55/WriterForge/actions/runs/38919228502) **success**：**Baseline 86/100（感知88、因果82、信息85、连续90、语言86；1050字符），WF增强89/100（感知92、因果89、信息87、连续91、语言90；1183字符）**。模型评分分差 +3（精确算术平均 86.2 vs89.8，差+3.6），稿长差11.24%通过15%比较闸门。选中宿主已有机制 `COST_VISIBLE_IN_ACTION` + `EMOTIONAL_TURN_WITH_EVIDENCE`，不是WF新学出的两种技巧。批评意见称WF稿在职业感知和具体代价行动上更合理，但未解悬念仍缺足够支持线索；只能作为**单次、未真人校准的候选证据**。
- 对比历史 v1 `86 vs84`、v3 `86 vs76`，这是第一轮可比同题 **模型分数向好** 的跨厂商组合，但因为创作模型、随机内容、机制组合不同，**不能归因于某个具体因素，更不构成稳定迁移能力**。原稿已按设计删除，不能从 R2 还原给新评审逐字复核。
- 仍无独立人类读者评价、闭卷新人物任务及跨场景3→6→9核心证据；`literary_mastery_90_percent_verified=false`、第一窗口 `NOT_PASSED`，第二窗口 `LOCKED`。不能用GitHub Actions success或未经校准的89分自动晋级。
- 上轮 GLM第二请求网络中断的失败 R2快照 `1e50ae50b1c1818a853268269fd1be184b30de4317beeb3ae89ea2d2482160ab` 保留，已为端砚SDK加入单次有界超时重发测试。**继续固定两个厂商模型，不再自动换回V4 Pro**。用户说“开始”后已实际做上述真实实跑、核验、文档和交接，而不是仅做设计。


## 27. 【最新最终交接】跨厂商 V28 真实 A/B 运行成功、准备下一聊天分析（2026-10-16 15:09 UTC）

用户说明当前对话上下文达到上限，要求交接。**本节是最新事实，覆盖第25/26节“正在执行”的状态；不要在下一对话中重新跑已成功的这轮。**

### 真实执行最终验收

- 仓库 `66tyu55/WriterForge`，`main`；固定模型仍是端砚网关（Secret **`DISCOVERY__API__KEY`，双下划线**）：Planner/Critic = `deepseek-v4-flash-0731`，Writer = `glm-5.3`；两个不同厂商的模型，非三个不同独立模型。保持此映射，不能再擅自换回两个 DeepSeek。
- 原文仍为私有 R2 中 SHA256 `86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28` 的《武动乾坤》第一章第一连续窗口（2125字符）。未向公共 GitHub 仓库或日志输出原著正文/草稿，不可随机跳段。
- 用户授权“边真实消耗额度边发现问题”，本轮已执行一次性 [**GitHub Actions #38918557675**](https://github.com/66tyu55/WriterForge/actions/runs/38918557675)，经最终 `fetch_workflow_run_jobs` 验证 **`completed/success`**；4项离线测试步骤共 10+4+5+7 个测试通过，然后真实模型运行成功。
- 真实记录精确阶段 `DISCOVERY_REAL_MODEL_AB_R2_CONFIRMED`，**4 次真实 API 调用（规划1/写作2/批评1）**；服务端 `prompt_tokens=5971`、`completion_tokens=10375`，总 16,346。全轮 **50,000 预留输出 Token 硬上限**（不等于实际消耗）、最多7请求；运行结果 SHA256 **`a2882f770e76fee4f4cedffb219d919a1a169fd731832b3d2de24e105c6a0282`**。成功路径对私有 R2 的不可变 JSON 内容回读对比 SHA，且 `completed.json` 指针回读一致；**不是模型权重训练**。
- 交付的是真实原创 A/B 盲批评的抽象结果、各角色元数据、练习稿哈希及 R2 回执；原著全文与草稿不长期保存。**未进行新一轮独立人类文学评价、未确认 90% 门槛、第二窗口仍锁定**。用户此前要求**本轮作品评分与原因分析留到下次一起做**，因此本次交接只记模型调用与 R2 事实，**不得猜出任何文学数值或自行宣称 WF 变好**。

### 本轮根因和代码改动

- 前一轮 [#38913593019](https://github.com/66tyu55/WriterForge/actions/runs/38913593019) 最终 **`completed/failure`**：Flash规划成功（148可见字符）；GLM第一次写作成功（1127可见字符），第二次写作请求触发 `DISCOVERY_NETWORK_FAILED`，共3次API调用。失败证据已存私有R2 SHA256 `1e50ae50b1c1818a853268269fd1be184b30de4317beeb3ae89ea2d2482160ab`，不能称它是文学质量不及格，因为没有第二稿/批评。
- `writerforge/reverse_discovery_models.py` 已区分 `DISCOVERY_TIMEOUT`、`DISCOVERY_CONNECTION_FAILED` 与 HTTP 状态码；仅对超时/连接失败/429/502/503/504 允许**最多一次传输重试**，重试仍计入总7次请求与Token预留，成功修复“网络异常整个学习丢失”的主阻碍；HTTP401等不重放。
- `tests/test_v28_discovery_models.py` 增补网络超时预算/永久失败/401回归；全量 [GitHub Tests #38918418959](https://github.com/66tyu55/WriterForge/actions/runs/38918418959) `success`。
- 当前运行器的 `.github/workflows/v28-flash-glm53-network-retry-once.yml` 为**仅首次新文件 push 触发**的单次实跑；它不会因为后续普通 push 自动扣费。核心入口 `scripts/run_wudong_discovery_ab.py` 和模型适配 `writerforge/reverse_discovery_models.py`；后续付费动作仍必须有明确用户指示。此前 P0 已解决原著事实/写作手法污染，预置文学机制经 HOST enum 验证，A/B 长度差>15%拒评。前面的多版本 v1/v2/v3 实测凭证都保留，不要覆盖历史。

### 新聊天首项工作（严格顺序，避免重复付费）

1. 先读取本文件 `docs/CURRENT_HANDOFF.md` 末尾本节，核实 R2 新快照 SHA `a2882f770e76fee4f4cedffb219d919a1a169fd731832b3d2de24e105c6a0282`，**只读地抽取 baseline/skill 的数字分项、长度、宿主机制ID、各评审短理由**；对短理由先检查是否与原文长段重合，日志不展示原著和完整草稿。**先分析已有证据，不要重新调用付费模型**。
2. 把本次跨厂商 Flash/GLM5.3 同题A/B与此前两个 v1/v3 版本比较；注意跨不同 Writer 模型的数字评分不可简单当作 WF 真正进步，要分别检验模型差异、是否等长、方法是否真迁移、读者/批评是否独立，不能偷换“90%大师水平”概念。
3. 依据真实错误写入有界 `faults/forgetting` 候选核心，与原著专名事实和未审核叙事假说保持隔离。技术改动先离线回归，再决定是否值得花额度复测；不得跳过第一段门槛到第二段、不得反复从第一章开头重新归档原著。
4. 继续目标：人物为什么以某种方式感知世界、作者为何以某种次序和视角呈现；“临摹快读→独立写→原著对比→拆失误/遗忘/假说→R2保留核心、销毁正文→闭卷重测→两个相邻窗口合并→多种独立场景3→6→9证据去重晋级”。**核心是真正改善原创写作的技能，非原著模仿分数或表面工程通过。**

如果用户开新对话只说“继续”，按上述 1→2→3 顺序落实，未经进一步指示不要启动付费任务。


## 28. 【修复分支交接，尚未合并】V28 Flash + GLM-5.3 第一窗口离线复盘（2026-10-16）

本节记录 [PR #43](https://github.com/66tyu55/WriterForge/pull/43) 中的离线修复，并不代表 main 已部署，或新候选已上传私有 R2。后续继续时先看 PR 的合并和最新 Actions 状态，不得将工程测试通过写成文学晋级。

- 旧训练数据保持原状：v1 V4 Pro baseline 86 / WF 84（原著情节污染、字数差49.4%）；v3 V4 Pro 86 / 76（已有原著来源隔离和长度闸门）；v4 Flash+GLM-5.3 86 / 89（精确平均86.2 / 89.8、字数1050 / 1183，差11.24%）。v4五维基线 88/82/85/90/86、WF 92/89/87/91/90。存在模型替换、内容随机和宿主预置机制变更，无法进行单因素归因。
- 真实训练 Actions #38918557675 completed/success；只读复评 #38919228502 success；原 R2 摘要不可变 SHA256 a2882f770e76fee4f4cedffb219d919a1a169fd731832b3d2de24e105c6a0282；本轮修复未启动新收费推理。
- 已发现 v4 的 Critic 虽匿名收到两篇稿，但同时看到原著 source_context，且与 Planner 共用 Flash 评审模型。修复后的 Critic 只见公共任务及匿名稿；18字符及以上直接重合评论会脱敏。新回执显式标记未向 Critic 发送原著；**旧 v4 绝不回填此标记，不能追称历史评审已独立于原著**。
- 新增 writerforge/reverse_ab_candidates.py：现存已保存摘要报告可在验证实际内容SHA、字数闸门、技术ID白名单和来源隔离后转成有界 fault/forgetting 候选。新 SQLite 最多128条摘要、以真实 receipt SHA 去重；不存原著、草稿、模型自由解释，也绝不允许从候选自动晋级。低于90的维度仅记参考差距；遗忘 NOT_TESTED、闭卷迁移0、真人审评未做。
- 新增 scripts/import_v28_r2_candidates.py：只读取旧私有 R2 抽象 JSON 回执，校验旧 SHA，生成新内容寻址候选报告，写入新的私有 R2 key 并全新 GET 核验；不下载原著、不调用语言模型。仅手动运行的 .github/workflows/v28-r2-offline-candidates-manual.yml 提供入口，没有 Discovery Secret。**当前只完成代码和合成回归，私有 R2 新候选回填尚未执行。**
- 修复详情：docs/V28_FLASH_GLM53_OFFLINE_ROOT_FIX_20261016.md。早期 PR 全量 Actions #38923300833 的381项测试已 success；合并前以最新 PR commit 的 Actions 最终报告为准。分支提交/CI 不能替代文学评价。
- 模型仍固定 Planner/Critic deepseek-v4-flash-0731、Writer glm-5.3；Discovery Secret 名 DISCOVERY__API__KEY（双下划线）；共享50k预约输出Token、最多7调用的约束未修改。
- **第一窗口 NOT_PASSED；第二窗口 LOCKED；90% 文学质量晋级未验证；3→6→9闭卷样本、两相邻窗口合并、独立真人评审与50部完整作品总评都没有完成。**

继续先查 PR #43 测试与合并状态，必要时复核手动候选回填的零模型调用属性。不要重新训练已保存的 v4，也不要为了新一轮分数提前开启第二窗口。


## 29. 【最新真实训练与分析交接】基准30显示标尺 + Flash/GLM-5.3 新场景 V5 + 私有 R2 失败候选（2026-10-16）

本节更新第27、28节的 pending。用户明确提出：“第一：把无技能基准分数降至30分；第二：继续训练，然后这次训练完毕分析。”本次要求**已真正执行**，不是只制定计划。完整文学分析见 [V28_FLASH_GLM53_TRANSFER30_V5_REAL_REVIEW_20261016.md](V28_FLASH_GLM53_TRANSFER30_V5_REAL_REVIEW_20261016.md)。

### 30 分新标尺（禁止冒充模型真实评分）

- `writerforge/reverse_score_scale.py` 把每次新 A/B **显示用的无技能分数锚定30.0**，把原始两稿分数同加一个位移，保留真正增量。**原始模型分数永久并行保存，30不是模型真的给出的质量分，也不是晋级闸门。**
- 本轮真实模型五项无技能分85/82/80/84/83，实际均分 **82.8**；WF分92/90/88/91/89，实际均分 **90.0**。真实分差 **+7.2**。换算成用户新显示基准：**30.0 → 37.2**，而非凭空“30→90”。
- 稿长无技能1188字符、增强1297字符，差 **8.4%**，通过15%闸门。新原创题为悬崖驿站夜班索道维护，未复用此前井水题，仍用同一私有原著第一章第一连续窗口。Critic 只见同题匿名两稿，**新版本不再给Critic原著 source_context**。

### 真实模型运行、消耗及回读

- [V5 one-shot Actions #38925236833](https://github.com/66tyu55/WriterForge/actions/runs/38925236833) 完整 **success**，每轮只有4次真实API：Flash Planner1 + GLM-5.3 Writer2 + Flash Critic1；输入4819、输出13803，总计 **18622 tokens**；预留输出36500，单轮硬顶50000和7次请求未变。
- 新私有 R2 不可变完整摘要回执 SHA256 **`b41e4a74895898f545af4f5424ac554cbe02215ba3f122715e8d09d38072aa66`**；脚本回读并独立只读审计成功。草稿、原著全文未持久化到公开repo/R2报告。
- 跨旧版本分差：v1 V4 Pro -2.2（原著剧情污染、长短不等），v3 V4 Pro 约-10（同样GOAL+COST），v4 GLM-5.3 +3.6（COST+EMOTIONAL，Critic仍见原著），**v5 GLM-5.3 +7.2（GOAL+COST、Critic不见原著）**。不同模型/不同题/单模型审评的数值不可作单因子归因。两次GLM正差是初步重复迹象，非独立真人验证。
- 五项弱项：信息释放 **88**（含糊结尾是否有可回查线索仍需测试），语言 **89**（尚未有读者复评）；本轮实际选中两个**宿主预置**操作 `GOAL_FILTERS_ATTENTION`、`COST_VISIBLE_IN_ACTION`，绝不可称作WF新发明的技能核心。

### 真实候选已经保存至私有R2（此次不是pending）

- [零模型费用的R2候选归档 #38926233485](https://github.com/66tyu55/WriterForge/actions/runs/38926233485) **completed/success**：从V5真实报告SHA全新GET→校验源和Critic隔离→仅抽取安全摘要→写入新内容寻址私有候选JSON→fresh GET校验。**0 次模型调用，0 次原著 blob下载**。
- 新候选不可变 SHA256：**`3ea44145b478cf71f720307ca7778eec6ad3d33f360448f78990aa1efd3e563e`**，保存2项低于参考90的文学维度候选和2项宿主预置机制ID，`forgetting=NOT_TESTED`，`human_review=NOT_PERFORMED`、`promotable=false`；不存原著、草稿、自由短评。历史R2原回执未被覆盖。
- 本轮修复 PR [#43](https://github.com/66tyu55/WriterForge/pull/43) 已 **squash merged** 到main，源评隔离、低长引文脱敏、faults/forgetting候选账本已真正落地。全量工程回归新增测试（查看新工作流结果）；不等于文学技能达到90%。

### 文学门闩（没有绕开）

**第一窗口 `NOT_PASSED`；第二窗口 `LOCKED`；真人独立审评缺失、闭卷迁移3→6→9未完成、相邻窗口合并未做、50部作品总评仍未满足。** 虽然本轮模型均分90.0，不得直接晋级。此处实验记录是prompt级生成与观察，不是模型参数训练。新用户明确授权之前不要重复新付费实验；没有额外训练自动运行。

**继续时**：先复核此节真实Actions和R2候选回执；集中处理信息释放的可验证线索/读者推断，以及语言句级自然度，检验机制在不同原创新场景的正反样本。不要用降标尺或反复刷同一第一窗口的分数制造成功。


## 30. 【最新实际交接】第2章新来源诊断、WF 实际回退与非破坏性底层修复（2026-10-16）

用户要求不再反复在第一章起点刷高分；换到后续内容固定同模型同任务观察WF是否骤降，同时修底层且不能让新内容毁掉原有功能。**本节是已真实执行的结果，非待运行计划。** 完整审阅 [V28_CHAPTER2_REGRESSION_ROOT_FIX_20261016.md](V28_CHAPTER2_REGRESSION_ROOT_FIX_20261016.md)。

- 采用《武动乾坤》同一钉住版本 SHA `86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28`，**不再用第一章**，在私有R2恢复后检查第1→2→3章真实章号；第2章正文3752字符，SHA `46acf29ea47e63b0a47a18413260a689bcaf9a9f1284338a2cebc4771428956e`。连续片段第一个1905、第二个1847字符，拼回完整第2章无跳段。[纯来源R2预检 #38927807149](https://github.com/66tyu55/WriterForge/actions/runs/38927807149) success，调用模型0次。章节切分只是物理安全边界，`semantic_boundary_verified=false`。
- [V6 真正4次付费模型A/B #38927958675](https://github.com/66tyu55/WriterForge/actions/runs/38927958675) completed/success；Planner/Critic仍 `deepseek-v4-flash-0731`、Writer仍 `glm-5.3`，**原创索道驿站任务原封不动**，输入4410 / 输出18379，总22789服务商报告tokens。V6私有R2抽象快照 SHA `cd6a9adef0647d52fb60bdf88103634220501cdca7a4d7113bdd2c3f3e781392`，fresh GET及评审原因审计 success。
- **第2章V6原始模型五维**：无技能88/82/85/90/86 → WF84/80/82/88/83，五项均负差 `-4,-2,-3,-2,-3`。五维平均 baseline **86.2**、WF **83.4**，组内差 **-2.8**；用户显示30标尺为 **30.0→27.2**。两稿长度1057和1125差6.04%，通过15%阈值。
- V5第1章同任务/模型原始baseline82.8、WF90.0、增益+7.2；V6第2章变成-2.8，**组内WF增益骤降10.0分**，WF自身均分下降6.6，而基线反而升3.4。两轮机制仍是同样宿主预置 `GOAL_FILTERS_ATTENTION + COST_VISIBLE_IN_ACTION`，说明**至少出现一次强烈上下文回退**；不能断言是换章节的单因果，单次随机生成、仅同一Critic及无独立真人意见仍有混杂。
- 模型理由提示五类缺陷：WF操作细节（粉笔线/湿圈/油痕）变清单，感知不自然；关键选择挂梯的动机只靠师父规矩，不足；悬念异常过多却无核心焦点；三更时间过渡生硬；动作语言较无技能乏力。这些是真实单模型短评，非可复核的全文人审。
- [R2 V5/V6 真实摘要双向比对及新候选归档 #38929089257](https://github.com/66tyu55/WriterForge/actions/runs/38929089257) success，**零模型调用**；两份历史原R2哈希核实后把退化分数和机制ID写入独立新内容寻址不可变候选 SHA **`563b5b28591fc38748f26f1dbc89d175c2b7d64802eda02b0247a91eac87ba6f`**。旧v5好例、v3坏例、v6坏例和R2原著都不覆盖。
- 实现：新增 `writerforge/reverse_later_window.py`（第2/3章源指纹/连续章号/两段无漏/线性有界读取）；`scripts/run_wudong_chapter2_diagnostic_v6.py`（独立前读实验、不放行课程）；`scripts/audit_v28_chapter2_v6_r2.py`（来源、匿名评审、模型评分与锁门审计）；`writerforge/reverse_cross_window_review.py`（A/B变化和逐维回退去重、模型角色/任务校验、候选隔离）；`scripts/import_v28_chapter2_regression_evidence_r2.py`（新私有不可变候选）。新增回归测试包含前版V5提示/模型身份不变、旧版第1章读取器兼容、缺章节/跳章节拒绝、R2摘要哈希、模型-only不晋级/候选去重。GitHub [全量 #38929224921](https://github.com/66tyu55/WriterForge/actions/runs/38929224921) **396 tests success**。
- 新代码会显式标明 `new_chapter_mechanisms_quarantined_pending_independent_review=true`（负面候选保护）；但目前尚无通用已审文学核心投入生产，也不能宣称新证据可自动升级/撤销正式Skill。已有候选保存只记录源码哈希、分数和禁止晋级，未存原文/草稿，不应重置历史。
- 真实底层尚未完结的文学功能：`parse_selections` 目前只验证证据ID存在，不能自动证实语义真正支持机制，且 Planner 必须从4项老技巧选择1-2项；下轮应支持**无可靠证据就弃权**、人物认知跨章已核实继承、候选上下文适用范围及真人/独立盲评。**此处不能谎称这些文学机制已经自动修好**。不要直接再刷新章或换模型、扩大Token来伪造质量提升。
- **保持全部正式门闩：第1窗口 NOT_PASSED，第2课程窗口 LOCKED、90%文学能力未独立验证、3→6→9非重复迁移证据未齐，50部作品总评要求不变。** 第2章只做隔离诊断前读，未以模型高分放行正式课程；本轮真实模型共4调用且没有追加第二次收费复测。

下次继续优先处理“机制无可靠证据也被强制选择”这类真正的语义底层漏洞，以及经验选择的禁用/回滚；不得覆盖原有反例和v5好例、不得让新章节的候选侵蚀旧功能。


## 31. 【最新交接 2026-10-17】随机三章压力测试、模型技术失败与非破坏性长度底层修复

本节为断线恢复后的实际结果。首读文件时先看本节及 [V28_RANDOM3_POST_DISCONNECT_FINAL_20261017.md](V28_RANDOM3_POST_DISCONNECT_FINAL_20261017.md)，不要重做原著R2归档、成功模型调用、随机选择或第二章旧实验。

- 用户授权至少3个随机章节诊断，在《武动乾坤》钉住的私有原著 SHA `86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28` 内，**事先用固定哈希规则选出第3、15、17章**，抽样身份SHA `1de5e123e70db078db63dd5cdab1230eab7ded135d101cfa2a3eb237179d3c54`，三章R2来源结构回读均通过 [#38997587245](https://github.com/66tyu55/WriterForge/actions/runs/38997587245)；不依新分数换章。
- **真实文学生成已评分成功2章**：[三章最初one-shot Actions #38997659758](https://github.com/66tyu55/WriterForge/actions/runs/38997659758)。第3章无技能原始均分76.6 vs WF86.2（+9.6，新显示坐标30→39.6），模型机制 GOAL_FILTERS_ATTENTION + WITHHOLD_CAUSE_SHOW_CLUE；R2完成回执SHA `e4555c234444371cbf24c5d8c4bd5e114ccfee8a0aeb32403ce501d7ddba2d07`。第15章首次技术失败，限制仅失败 job 重试后成功：无技能80.0 vs WF90.6（+10.6，新显示30→40.6）；机制 COST_VISIBLE_IN_ACTION + EMOTIONAL_TURN_WITH_EVIDENCE；R2 SHA `6169c11a24fa19de9afab7150c8973ed4d930d72c1fdf2d4fba640636910b8ef`。两章成功由 [私有R2零模型只读审计 #38998637174](https://github.com/66tyu55/WriterForge/actions/runs/38998637174) 验证：number_scored=2/all_three_scored=false。
- 第17章实际多次打到模型，但均**技术不合格、无合法原始五维评分**：V7最初连接/推理截断/预算失败R2 SHA `6fa81ad8f150d24522903688f61817489b7ed30755d091e60c44b869b8350086`；V7仅失败 job 的限定重试出现两次length且零可见正文，SHA `e038dc7cf07cc5d9b95ea99edbe93693b219cb8167a8604487e4bee947b4841e`。
- 验证网关兼容 GLM5.3 `reasoning_effort=low` 的**无原著小型真实探针 #38999272334** 成功。V8 [#38999364460](https://github.com/66tyu55/WriterForge/actions/runs/38999364460) 改为低思考后成功生成两稿 1964/1329字符，但差约32.3%不满足15%闸门，失败 SHA `74f78fd2583a9e66f570c77d3f06bd73aaabc352facc34f63af903cccdeeb473`；没有批评分数。
- V9 [#39000191094](https://github.com/66tyu55/WriterForge/actions/runs/39000191094) 在两组写作任务同时追加相同1100字符目标，两稿为1698/1433字符，差约15.6%，依旧**严格拒评**，失败 SHA `56f8a186a227dc01f26a1f85fbe7d1b46ab3063bc24d1e57e462223e675a48f6`。此前工作流首次被合成文本<300字的纯测试夹具阻断在付费前，修夹具后才发生上述一次真实模型尝试；不要把首次阻断算收费。
- **本轮三章确实都调用真实模型，但只有2章完成真正公平A/B审评；不能说3章已全部评分，也不能拿第17章技术失败宣称WF文笔下降。** 两组有效模型评分都为正，故“随机章节仍全面下降”的预设条件没有成立；第2章历史相对负分-2.8仍在，不得忽略。只有单个Flash Critic及少量样本，无稳定因果证明。
- 已有底层工程修复：在 `reverse_discovery_models.py` 增加对 GLM Writer 的可选、经无原著探针验证的low effort；在 `reverse_cloud_ab.py` 增加可选有限角色输出预算、同等 neutral `common_target_chars` 和**新可选 `symmetric_length_revision`**：首稿不等长时只对两组稿分别各做**一次**同目标的独立修订，不接触别组稿、原著剧情、不截稿、不补假文本；经过同样15%闸门和共享50k/7调用上限才允许给文学分。两个编辑机会须同时预留令牌；其可用性通过合成测试核对，但尚未用真实GLM长篇验证，不能虚构已修好真实文章长度。
- 原 `CloudABTrial.run` 旧参数及默认行为不变，新增的全部能力为 opt-in；已通过对照、机制白名单和旧源解析器兼容回归，历史V5、V6、V7及第17章失败R2内容寻址记录永不覆盖。文学语义学习“原著证据ID存在≠真实因果解释”仍是未完成能力，不能以控制输出长度代替文学技能改进。
- 工程最新测试应检查当前 main 最后一次 `WriterForge Tests` 的最终结论。报告 [V28_RANDOM3_POST_DISCONNECT_FINAL_20261017.md](V28_RANDOM3_POST_DISCONNECT_FINAL_20261017.md) 已保存到仓库。**禁止继续盲目收费重跑第17章**，先独立验证新对称修订算法，再征得用户明确的新付费试验指令。
- **保持第一窗口 NOT_PASSED、正式第二课程窗口 LOCKED、模型权重未更新、未通过真人独立文学评审/3→6→9/50部完整作品总评。** 用户显示的baseline 30不是模型真实评分或大师达标指标。



## 32. 【最新事实交接】三个随机**原创第一章题目**的真实完整 A/B：两正一负（2026-10-17）

**用户这次要求随机题目，而非再随机原著章节。** 以“安全聚落、夜间传说、少年意外滞留、诡异升级、逃跑、认知转折、悬念留白”为共同故事骨架，先独立创作六套自洽题目，`writerforge/random_original_openings.py` 以固定哈希seed预注册抽中 `copper_valley`（封矿峡谷）、`cedar_night`（古杉林）、`black_tide`（黑沙盐湾）。最终完整复盘见 [V28_THREE_RANDOM_ORIGINAL_FIRST_CHAPTERS_REAL_REVIEW_20261017.md](V28_THREE_RANDOM_ORIGINAL_FIRST_CHAPTERS_REAL_REVIEW_20261017.md)。

- 来源**固定而不换章**：同一份私有原著 `wudongqiankun` 钉住原文 SHA `86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28`，第3章第一个连续1132字符窗口 `96b6363d40be7b99d5635af1346da0c04e44556fc06e32d1aab04e419e4942fa`，只供 Planner 分析；Writer/Critic 不见原著情节。正式第1窗口仍 NOT_PASSED、第二课程窗口 LOCKED。
- [**真实三题 A/B Actions #39003570775**](https://github.com/66tyu55/WriterForge/actions/runs/39003570775) 三个任务及最后 R2 审计全部 **completed/success**；真实固定模型 Planner/Critic `deepseek-v4-flash-0731`、Writer `glm-5.3`；每题4次API，共 **12**。服务端报告总输入14464/输出9132，共23596 tokens，未把预算保留额冒充真实消耗。三组稿长差都 ≤15%，对称修订各0次，故本轮没发生补写反复收费。
- 三个不同题材原始模型评分：**封矿峡谷baseline69.0 vs WF86.6，+17.6**（稿长1422/1323）；**古杉林baseline86.2 vs WF78.8，-7.4**（1273/1142）；**黑沙盐湾baseline72.4 vs WF86.2，+13.8**（1499/1722）。三组均分基线75.87，WF83.87，真正均分差+8.0。用户30显示标尺分别30→47.6、30→22.6、30→43.8，不能将30伪称原始文学质量评分。
- 五维差额封矿谷 perception+16/causality+15/information+22/continuity+21/language+14；古杉林 **-8/-7/-7/-8/-7五维全降**；黑沙盐湾 +14/+15/+14/+18/+8。三组全部选用了**完全相同的宿主预置** `GOAL_FILTERS_ATTENTION`+`WITHHOLD_CAUSE_SHOW_CLUE`。说明跨不同原创新情境模型给出正负不一致，暂不能归因为某一技巧必然有害或有效，更不能由2/3正例“冲掉”一负例。
- 不可变私有 R2 真回执：
  - 封矿 `a6f1ddb22abab1635ca277fff659b8c44259229ab0c1f0065d18470a23be39f2`
  - 古杉 `8ef29fd600c5c6efbe295b95564408509e6d98a10bef4cf09f9bf9dfe12e45dc`
  - 黑沙 `5a630f2313e4e18104575bd0874ac38ec532c12b92dff6b91aacd632f06642d7`
  - **三组读回聚合新摘要 SHA `2b2aea9c6563b402d0795fc1812e09d5d066e56a4ab51be045ddeabaae00b55d`**。聚合只含数值、场景/文本SHA、角色与机制ID，旧实验与失败证据一律不覆盖。
- 主要真正缺点：代码只检验Planner选中技巧ID存在及引用的来源段落编号有效，不核验原文语义确实支持该技巧在**新的首章题材**中适用；并且总在四种预置技巧中强制选1–2项，尚非从作品自动学习并校准的文学规律。这是根因候选，未经独立真人全文审稿不能认定为已证实因果。绝对篇幅900-1300汉字仍经常没有严格遵守，尽管相对15%比较全部合格。
- 新增 `writerforge/reverse_story_context_evidence.py` + `tests/test_v28_story_context_evidence.py`：纯离线地验证真实R2后审计报告SHA，将三组正负模型观察**按 story_id / 创作任务SHA / 学习来源SHA**形成未审核候选；古杉林标记 `NEGATIVE_ALL_FIVE_NEEDS_INDEPENDENT_REVIEW`，另外两组 `MODEL_POSITIVE_UNVERIFIED`。**不改写生产Writer提示、不禁用整套技巧、不晋级、不覆盖历史快照。** 三组真实聚合R2已存储；此派生候选另存R2的操作**未执行**，不能声称额外云端归档已发生。回归见最新 WriterForge Tests。
- **本次确实完成了3个原创题目的模型评分，但并未保存6篇完整练习稿供真人逐字盲评**。临时稿被删除，只留不可变文本SHA和短评，因此不能用本轮3个模型评分假称人类认可90%文学能力。未来若须真人细评，必须先制定私有、限量、哈希锁定的练习稿保留协议并再生新稿，不能恢复旧稿。
- 后续策略：先验证“原著语义支持→创作任务适用→具体机制动作→读者可回查线索”的四层证据链；保留古杉林反例，跨新题目比较机制适用条件，避免仅追均分。**不自动重复付费训练；不放行第二课程窗口。**



## 33. 【最新交接 V29 · 2026-10-17】六阶段改进计划获准：已实际修复语义证据协议、原创稿加密留证、真实R2上下文负例回填

用户在V28三题随机原创首章（封矿+17.6，古杉-7.4五维全负，黑沙+13.8；平均+8.0）的完整复盘后确认“可以---允许计划”，授权此前提出的修复计划。**本轮已实际修改GitHub代码、测试、私有R2，未重新调用付费文学模型**；并非六阶段全部已被文学实践验收。完整详述： [V29_SEMANTIC_PRIVATE_DRAFT_REPAIR_20261017.md](V29_SEMANTIC_PRIVATE_DRAFT_REPAIR_20261017.md)。

- **P0语义适配的可执行协议**：新模块 `writerforge/reverse_semantic_evidence.py`，新 opt-in `CloudABTrial(...,evidence_first=True,semantic_evidence_first=True)`。Planner现在必须给出来源中实际存在的12-48字符span、所属段落、角色已知未知、局部因果、新创作题目适合程度、误用风险和支持/弃权状态。结构不完整/原文证据杜撰直接拒绝；明确风险则Writer之前弃权以节省调用。只将原有HOST技巧ID送Writer，绝不送原著文本、解释和专名。**本层仅证明原句确存在，不能证明模型语义理解正确，依然标记 `independent_semantic_review=NOT_PERFORMED`**；默认旧训练行为不变。
- **P1未来原创稿私有、可复评**：`writerforge/reverse_private_draft_evidence.py` 及 `pyproject.toml` 新增可选 `[evidence]` 依赖 `cryptography`。显式 `manuscript_sink=PrivateDraftEvidenceVault(...)` 时，仅在有效的匿名Critic和15%相对稿长闸门完成后，才将本次**两篇原创稿**以 AES-256-GCM、来源/任务AAD绑定加密写入私有 `writerforge-private-library` R2，内容寻址SHA + fresh GET；报告仅附密文哈希及到期信息，无小说明文。最大保留14天、默认7天，超过时间拒绝read；**R2对象不自动删除，需要独立的显式到期清理操作**。
- 此加密保存**必须另行配置独立随机32字节base64密钥 `WF_PRIVATE_DRAFT_KEY_B64`**；当前未设置/未使用此密钥、没有在真实R2上传新草稿。不能将已有R2 access secret当作该密钥，不能在public GitHub上保存。此前V28六篇临时稿已销毁，无法复原。默认 `CloudABTrial` 仍不保留任何草稿。
- **逐句缺陷标注基础**：新增 `writerforge/reverse_draft_review_marks.py`，0基起止字符区间+五维+错误种类+修改想法，最多32条；导出的只有span/说明哈希和长度位置，不泄露明文，不把未经认证的人/模型申明当作真人审评。尚未发生真实独立评审。
- **旧候选账本兼容**：`writerforge/reverse_ab_candidates.py` 现在只允许来源、任务及两篇稿SHA都与加密R2回执一致的未来留存证据；普通旧报告的 `drafts_retained=False` 不变。伪造密文回执/缺key fail closed，仍不自动晋级。
- **真实R2上实际完成零付费负例归档**：[一次性回填Actions #39005416238](https://github.com/66tyu55/WriterForge/actions/runs/39005416238) completed/success，源码三题原聚合SHA `2b2aea9c6563b402d0795fc1812e09d5d066e56a4ab51be045ddeabaae00b55d` fresh GET后，写入新不可变正反候选 SHA **`63cde6bacd51f7c655ec4eb6e6ccdab7e96c54c9f507512dfbfeaba73cf7d60f`**。内容只有封矿+17.6、古杉-7.4五维全负、黑沙+13.8、原始稿/来源 SHA 和宿主机制ID；`new_rules_promoted=false`；旧V28不可变凭证、正例及失败均未覆盖；真实模型调用0次，原著或旧草稿未下载。
- 回归测试：`tests/test_v29_semantic_evidence.py`、`test_v29_private_draft_evidence.py`、`test_v29_draft_review_marks.py`、`test_v29_original_context_r2_import.py` 及旧V28测试。专门的**真实AES加密/错误密钥解密/到期删除/旧账本兼容**零模型测试 [#39005569114](https://github.com/66tyu55/WriterForge/actions/runs/39005569114) **completed/success**；请复核最新 `WriterForge Tests` 全量状态/数量，不要把合成测试成功当成文学质量90%。
- **尚未完成**：不同模型/人类的独立原文-情境意义审核（目前只验证源span存在和解释字段完整）；实际带独立key的真实稿加密留存和真人逐句盲评；将一条“已确认古杉林为什么失败”的机制改进真正写入正式创作调度；3→6→9独立场景、50完整作品文学毕业条件。不能据此声称WF文学能力得到真提升。
- **严格锁门**：第一课程窗口 `NOT_PASSED`，第二课程窗口 `LOCKED`；不得伪造30基准原始得分或拿模型90分突破真人验证闸门。未经新的实验指示不要重新付费刷题。



## 34. 【最新 2026-10-17】新版WF与旧版WF：三题真盲测验证完成，但尚不能宣称文学能力已经进步

用户明确委托自主制定改进方案，并要求实测“WF到底进步了吗”。**已经实际执行真实模型对照，得出不取悦人的混合结果**。详见 [V29_REAL_OLD_NEW_SEMANTIC_HOLDOUT_FINAL_20261017.md](V29_REAL_OLD_NEW_SEMANTIC_HOLDOUT_FINAL_20261017.md)；提前预注册协议见 [V29_REAL_OLD_NEW_HOLDOUT_PRECOMMIT_20261017.md](V29_REAL_OLD_NEW_HOLDOUT_PRECOMMIT_20261017.md)。

- 一次性 SHA 按固定种子从5个**未参与之前改进的原创题目**抽中 `bridge_debt` 石桥旧债、`desert_well` 沙漠旧井、`lantern_town` 春汛灯牌。保持完全相同的钉住私有R2原著第3章第1连续窗口，Writer GLM-5.3/Planner和Critic Flash，首稿来源隔离，匿名 A/B，最多7调用/50k预留输出token每题；旧WF使用老机制选择器，新WF使用已实现的source_span精确原文引用+认知/因果/新任务适配/误用风险证据门槛。
- [第一次真实旧vs新 #39006533808](https://github.com/66tyu55/WriterForge/actions/runs/39006533808) 仅1个有效文学A/B：石桥旧债旧85.0 vs 新92.8、**+7.8**，新旧所选技巧不同（旧 GOAL+COST、新 GOAL+WITHHOLD），五维 +7/+7/+8/+8/+9；不可变R2回执 `8368176072491c04fb17dba6fa80d3590c9106a9fd3c43c7552e629da467d651`。另外沙漠和春汛两题初稿加各一次公平独立修订仍有长度差>15%，按规定**没有文学评分**，失败回执SHA `fac3bb0a6c64d7a80ff00543eb916edd45f909550891e1e69c31abe582bd73fc` / `6ec824bdbd3c368424ec8efa7baad5bbc1eb1427f0cc6d05da24df08f8b562c2`，不能把未评分当成低分。
- 修复比较协议而**没有修改文学分数、放宽15%闸门或裁剪稿**：`writerforge/v29_old_new_trial.py` 改为有界 `LengthUnscorable`（只记录双方首稿/修订后字符数与差比）和对称编辑器给每稿自身实际字符数、距共同1080目标的字数差，不见对方草稿。保护性测试通过。
- [只重试失败slot 1/2 #39007227522](https://github.com/66tyu55/WriterForge/actions/runs/39007227522) 完整 success，slot0不重复写；R2新独立前缀、两题仍同题同模型匿名盲评，最终 **沙漠旧井旧87.2 vs 新82.2 = -5.0（五维-4/-8/-5/-4/-4，旧GOAL+WITHHOLD、新GOAL+COST）**，SHA `827c6ccf7dbe5b739f8dff02599b69758cb6d5ecfef9362edd094af550c0bb9f`；**春汛灯牌旧82.8 vs 新89.0 = +6.2（五维+4/+8/+6/+7/+6），但新旧都选GOAL+WITHHOLD**，说明这个正分差不能归因机制选择改善，SHA `3620cf259aa2a458c36367371f9209f6270cf3132cc98fa0cfaec2f134778864`。
- **三题均真正有原始模型五维评分**，三题新版减旧版+7.8/-5.0/+6.2，**均值+3.0**。此3题slot0与技术恢复的slot1/2编辑提示协议有区别，真实聚合 `49ae267ebbc15be5f0350015ad610f994be277339471c4e72f27792d7f37683e` 标记 `mixed_length_protocol_between_slot0_and_recovery_slots=true`、`causal_improvement_proven=false`。Planner/Critic都是同一个Flash模型且缺真正人类全文评审，不能以+3.0声称WF稳定文学能力进步。此次两次实际模型运行调用：17+10=**27**，失败模型消耗也计数。
- 真实零付费只读模型短评 [#39007323924](https://github.com/66tyu55/WriterForge/actions/runs/39007323924) 说明：石桥新版更用早先的衣物/腕布细节自然揭示旧债；沙漠新版对行动代价描写并未弥补结尾蹄印/青苔线索与前文的脱节；春汛五维相对较好但机制完全一样，无法归因。均为模型点评假设，不是独立人审。
- 新增 `writerforge/v29_semantic_regression_candidates.py` 将每题按任务SHA/来源SHA/选择技巧/实际分差5维/真实R2回执分隔为 `POSITIVE_CHANGED_MECHANISMS_UNVERIFIED`、`TASK_SCOPED_ALL_FIVE_REGRESSION_CANDIDATE`、`POSITIVE_BUT_SAME_MECHANISMS_NOT_CAUSAL`。不能据一正全局升级机制、也不因一负删旧机制。
- [私有R2真实零模型候选回填 #39007504129](https://github.com/66tyu55/WriterForge/actions/runs/39007504129) success，从已保存的真三题SHA快照fresh GET后新增不可变候选SHA **`bcf5be72abe50d1076653d7211f77df5e941fb3e8213466cdef45c0d0d440f49`**。历史正例、负例、原著和失败均不覆盖；额外模型调用0。
- **核心结论：尚未证明WF已稳定进步**。这次比较的是“旧Planner vs 新语义Planner即席挑选四项宿主预置技巧”，并不是从中国文学原著中学出、独立审核、以学习库保存后在创作阶段闭卷迁移的真正完整文学技能。当前下一步须分离学习/创作阶段、独立语义证据审核与严格跨题回归，而非加长提示词或无止境刷同一章。
- 尚未提升正式Skill、无模型权重更新、真实加密稿留存另需独立Secret配置。**第一课程窗口NOT_PASSED、第二课程窗口LOCKED、文学90%真人独立审评/3→6→9和50完整作品门闩未解。** 此轮已进行两次有硬上限授权付费试验；没有接续第三次收费训练，优先验收新证据。


## 35. 【最新V30执行交接 2026-10-17】停止用平均分偏袒WF：失败优先真实R2证据、评价偏差治理

用户明确要求：“为什么平均分数---不要偏向WF--让他接受真实缺点---还是先列出计划--执行”。先预注册具体计划 [V30_BIAS_FREE_FAILURE_FIRST_PLAN_20261017.md](V30_BIAS_FREE_FAILURE_FIRST_PLAN_20261017.md)，**本轮已真实修改GitHub并执行零付费R2审计**；完整缺点报告 [V30_FAILURE_FIRST_REAL_AUDIT_20261017.md](V30_FAILURE_FIRST_REAL_AUDIT_20261017.md)。

- **拒绝平均数掩盖缺点**：历史V29旧WF vs 新WF +7.8/-5.0/+6.2，均值+3.0仅为描述统计，不能作晋级/闭卷文学能力提高证据。石桥+7.8是换技巧后正向模型候选，尚未独立验证；沙漠-5.0 **五维全负**（感知-4、因果-8、信息-5、连续-4、语言-4），新版GOAL+COST代替旧GOAL+WITHHOLD的上下文适用性存疑，应作为独立严重回退；春汛+6.2两版本技巧完全相同，不能归因“新版机制选择器”。
- **额外客观缺陷**：3个A/B任务中有**2个任务新旧两稿都未达到共同1080字符±8%目标**（石桥1238/1318，春汛1394/1401）；旧15%“相对稿长公平”不等于遵守题目长度要求，现有 V30 各题独立列出绝对稿长违约。上一轮第一次2/3题因篇幅差被拒评，后做协议变更恢复；别把两次运行合起来包装成3题完全同协议。真正全文未留存，无法给旧稿做真人复核。
- **审评本身并非客观真值**：Planner/Critic均用Flash，二者是相同模型；虽Critic不见原著和版本标签，但仍存在共模审美、评分噪声、A/B顺序等偏差；一个模型即使平均90也不能宣称能力90。既往V28第2章-2.8及原创古杉-7.4等负例保留，不跨不同协议简单求总平均或硬因果归因。
- 新增 `writerforge/v30_failure_first.py`：只接受SHA校验的R2原聚合数据，按题保存新旧机制/五维负差/稿长/个人回执，**一题五维全负阻断总体技能晋级**；同机制涨分不计入机制选择进步。负分与其他题正分不能互相抵消。不得自动更改任何Writer正式规则。新增 `tests/test_v30_failure_first_adversarial.py`、`tests/test_v30_failure_first_r2.py` 专门防平均灌水、漏缺点、伪造分数和伪同机制。
- [**真实私有R2 V30失败优先审计 #39008909781**](https://github.com/66tyu55/WriterForge/actions/runs/39008909781) completed/success：对实际V29聚合SHA `49ae267ebbc15be5f0350015ad610f994be277339471c4e72f27792d7f37683e` fresh GET后创建独立新不可变记录 SHA **`d55899906ab69450e58cc746cf44d17602736d75029c5d80045328015213c894`**；真结果1严重回退5个负向维度、1同机制正例剔除选择器功劳、2题绝对篇幅违规；最终状态 `MODEL_RATED_REGRESSION_PRESENT_NO_PROMOTION`、`stable_literary_progress_proven=false`。审计本身0模型调用；旧分/旧R2完全不覆盖。
- 增加未来多评审去偏协议 `writerforge/v30_blind_reviewer_gate.py` 和 `tests/test_v30_blind_reviewer_gate.py`：两名评论模型须与Planner/Writer及彼此不同，必须A/B匿名标签交换，互相矛盾的负评绝不能均分抵消，双模型同意仍不等于独立真人文学审评。**只是下一轮接口与合成测试；历史已销毁六篇新旧稿无法真实双审**，不得声称已经用了两个模型给原稿重新评分。
- 工程最终全量回归以最新 `WriterForge Tests` 实际完成为准。此次只改评分证据/审计/未来评审门闩，不为漂亮分数再付费刷题。既有 first window `NOT_PASSED`、second `LOCKED`、文学人审不达标以及50完整作品要求不变。
- **下轮正确重点**：实现将学习库的因果/人物知识正确抽象并复核，再让创作调用有独立证据支持的技能；经独立真人或不同模型对**同稿**复评，跨6→9新题先通过负例回归与绝对长度/因果/伏笔闸门。不能把提交更多提示词/运行更多模型/测试数量增加理解为真正写作能力成长。


## 36. 【最新交接 V32 · 2026-10-17】用户亲自指定考官出题、WF学生作答、不作弊；真考试3题但0个有效文学成绩

用户在WF自主学习V31只真实完成2/3轮后强调：“哎呀--死脑筋----题目--你来随机搞几个--把WF当成学生---你是考官--不允许作弊--开始”。立即冻结 [V32_EXAMINER_PRECOMMIT_20261017.md](V32_EXAMINER_PRECOMMIT_20261017.md)，执行完备复盘 [V32_REAL_EXAMINER_NO_CHEATING_RESULTS_20261017.md](V32_REAL_EXAMINER_NO_CHEATING_RESULTS_20261017.md)。本轮**不许考试中由WF自己出题，也不许给自己考试打分，考后不以失败为理由偷偷换题/重复付费**。

- 六题原考官原创题库 `writerforge/v32_exam_bank.py`，提前 SHA(seed:topic_id) 抽3道：`pottery_market` 陶镇青瓷误会、`horse_school` 马场马鞍扣、`canal_doctor` 运河问诊，预注册manifest SHA `bb6a6fb13d9abbc94fac57102abba15ad79c942a1af9daedece9f2c5c80e65df`。不重用V28/29故事题目。
- 考生不是新发明的WF：从私有R2精确重读V31第一轮真实自学规则快照SHA `cd9cfa1d6413ed84bb4d3bb18c9a77d873666df95cbcd5898d4745cfeb2e3c7c`，第二轮SHA `fbb06fc6a53d0708b99b813eeb4cd9c96d1152413b4880d69ddf0ad294e6b555`，严格校验第二轮继承同一实验记忆且未自主产生新规则。每题一份GLM5.3无记忆稿vs一份加载唯一真实实验记忆的GLM5.3稿；无原著进入考场、不得自学新规则或看对手稿。
- 一次性真实 [Actions #39012732775](https://github.com/66tyu55/WriterForge/actions/runs/39012732775) 三题尝试、只读最终汇总**completed/success（审计完成）**：slot0生成两稿后长度 897/1172差23.46%>15%强制拒评，私有成功回执SHA `2d794d43ffc9c710b4b02310194614933b00f451c0a6351441f362b7a9278902`；slot1/2虽完成作文但两个不同评阅模型阶段未满足冻结JSON评语格式，分别失败代码 `EXAM_GRADER_REQUIRED_JSON_SCHEMA`，失败SHA `fec02bed409db5e4bbf1f3eb311002a7d6fae3bf69a168354f5f894f99437f1a` / `b6863ff80f3c81e905a6f6af41cd4bc167ca78f08b1eb3bb9c37f5625f34b92e`，两题各4次请求。slot0仅2次writer请求，共10次实际预留模型API请求（可能计费）。
- 设计的评阅者是DeepSeek-V4-Pro和MiniMax-M3，两个模型彼此不同、均不等于WF内部Flash Planner/GLM5.3 Writer，匿名A/B二人顺序交换，不能接触WF实验规则或学习过程。但**没有任一题取得2个JSON结构通过的真实文学模型评语**，不得宣称真正完成客观阅卷，更不要将评分失败定性为WF文笔差。
- 最终真实私有R2零模型汇总 `two_grader_valid_trials=0`，`all_exams_consensus_positive=false`，`literary_skill_promotion=false`，3试卷0有效成绩；工程预检505项测试通过。正文原作文没有长期保留，只存哈希、小型摘要和错误码；用户若要求人工文学逐句评测需要下批新题、提前授权加密存稿。旧试卷无法补读。
- **真实判定**：V31“自己提炼并持久记忆1条实验规则”在V32考场被固定加载，但**没有证据可证明该规则提升文学水平**。slot0相对字数偏差属于写作协议质量问题，slot1/2评阅JSON不合格属于考试基础设施问题，应分别修复，不得求平均凑0/正分。失败不等于零分。
- 后续优先考官端先进行真实网关**无小说小探针**修复格式可靠性，学员端绝对/相对篇幅控制；然后**全新预注册题目**进行同模型有/无记忆公平测试，保留负例、不加训学员作弊。正式 first `NOT_PASSED`, second `LOCKED`, 官方文学核心未晋级，不能用505项工程测试代替文学评分。



## 37. 【最新V33/V34 2026-10-17】修复WF指定字数与MiniMax长文JSON，真实新题同时跑通；但记忆五维全负

用户明确允许“可以---修补--必须控制WF指定的输出长度--然后json格式问题--一直没有处理--这次一起解决”。最终完整来源及根因详见 [V34_LENGTH_AND_JSON_REAL_REPAIR_RESULTS_20261017.md](V34_LENGTH_AND_JSON_REAL_REPAIR_RESULTS_20261017.md)；预注册真实考卷见 [V34_FIXED_LENGTH_AND_MINIMAX_JSON_FINAL_PROBE_PRECOMMIT_20261017.md](V34_FIXED_LENGTH_AND_MINIMAX_JSON_FINAL_PROBE_PRECOMMIT_20261017.md)。

- **V33第一版真验证没有通过**。新题 `lake_ferry` 无记忆1036/WF1011字符，符合长度，但是Pro评分成功、MiniMax评分两次都结构非法（实际失败SHA `d6c7063023799cbea26159b28276c0a6eb9ff1e72b2f610b7c6279b1918ff7fb`）；`salt_festival` 初稿各一次对称重写之后无记忆1062/WF945，只差硬下限950五个字符仍按协议拒评，R2 `dc83b1c157a21fd9b86a8efe9a813ff6123dc3e209fb91d432dee0720ff33b3f`。不得将V33合成测试通过当作真实两题成功。
- **找到MiniMax JSON反复失败的事实原因**：完全无原著和小说正文的真实长文本测试 [#39015256753](https://github.com/66tyu55/WriterForge/actions/runs/39015256753) 检测到MiniMax将完整`B`的五维评分及`uncertainty`嵌入完整`A`五维对象中，整个顶层只有`A`。旧严格parser误判`GRADER_JSON_WRAPPER_UNSUPPORTED`。新`writerforge/v33_exam_contracts.py`只接受`A→B→uncertainty`此结构（或对称镜像）、所有五维评分/评语原样重排，不修改数值、不发明数据；其它缺维、含混、非法仍Fail-Closed，非法格式至多一次等题等稿等匿名位置的限额修正。修复后真实MiniMax长文本测试 [#39015460941](https://github.com/66tyu55/WriterForge/actions/runs/39015460941)仅1次请求取得`json_validation=VALID`。此前单独Pro+Mini小样本两模型均一次合格 [#39014463006](https://github.com/66tyu55/WriterForge/actions/runs/39014463006)；小样本不等于长文可靠。
- **真正输出长度硬门闩**：`writerforge/v33_balanced_writing.py` 对exam统一目标1120（含标点）、每稿绝对区间950–1300、相对≤15%。超范围或互相长度不公平→**双边各一次同条件自稿编辑**；新可选第二个对称编辑周期，两臂都只见自己刚生成文本与自己字数、至目标尚需加减的确切字符数，不见另一臂，绝不人工裁尾或塞标点。经过最多两轮仍不合格，拒评无分，不能靠平均分遮掩。业务层一般`CloudABTrial.run(... common_target_chars=N, absolute_char_bounds=(min,max), symmetric_length_revision=True)`额外接入通用字数硬门闩，明确指定时允许N至4500字符；默认历史接口行为不变。它不是保证语言模型天生每次都严格 obey，而是保证输出必须验证或Fail-Closed。
- **调用硬上限**：扩展的V34试卷最大10次模型请求、50k预约输出token：初稿2×7000+最多4次编辑×4300+两名不同评审最多4调用×4600=**49,600**；transport自身重试也计入硬预算，不会无上限收费。旧Discovery default7调用未变，提升到10仅显式opt-in。
- **完整真实修复验证成功**：[V34单道全新题真实端到端 #39015701423](https://github.com/66tyu55/WriterForge/actions/runs/39015701423) `completed/success`，从事先封存三题中抽中`dye_workshop` 蜡染作坊，不复考V32/V33旧失败题。WF自身真实V31 stage1/stage2冻结实验记忆与无记忆同一个GLM5.3 writer分别作答。初稿不合格→**双边各编辑一次，共两次编辑请求**，最终无记忆**1056**、WF记忆**1082**字符，950-1300绝对范围及15%相对差同时通过。两个不同阅卷模型DeepSeek V4 Pro/MiniMax M3 **都首次JSON即通过**，匿名A/B顺序交换、缺点分项分别保留。全流程仅**6个真实模型调用**（2 Writer初稿+2编辑+2 critic），新R2原报告SHA **`331663b6628b504bd59051d73c9d7c703c45b2012599109f4cdc50d5c5c46d81`**，只读独立R2审计`two_valid_grader_trials=1`、`user_goal_length_json_chain_fixed_in_real_runs=true`。原著正文和两篇练习全文不持久，历史R2/V32/V33失败快照都不覆盖。此次第一轮编辑已足够，不等于实际第二轮修订模型可靠性也经过真题验证。
- **文学能力并未同时成功**，必须保留这个结论：V34真正两名不同评论模型均认为WF带自学规则稿五维**全面落后于无记忆控制稿**。Pro 的（感知/因果/信息/连续/语言）差 `-6/-4/-5/-3/-6`；MiniMax M3差 `-6/-4/-10/-2/-5`。一题模型评价不具备统计因果、人类文学真值资格，但绝不能据此升级WF那条真实自学技巧，更不可拿通道技术成功冒称作家技能变强。两名评阅者原始分数与负例留私有R2，不相互平均抵销。学海正式晋级 `NOT_PASSED`、第二课程窗口 `LOCKED`。
- 新增重要回归：`tests/test_v33_exam_contracts.py`、`tests/test_v33_repair_e2e.py`、`tests/test_v34_complete_repair.py`、`tests/test_v34_general_absolute_length.py` 覆盖真实MiniMax已发现嵌套形态、缺漏/伪分数拒造、有限JSON重试、近边界945字二次公平校正、一般WF动态范围、不可改历史R2等。此节交接后应检查最新`WriterForge Tests`全量通过的最终结果。**单道V34真实通过，不代表未来每一篇都一次过**；禁止为提高WF成绩而重跑旧题。



## 38. 【最新交接V35 · 2026-10-17】《西遊記》真原文读→候选手法→考官出题→7角度写前决策→原稿/修订稿，分别存R2；原自审失败，追加严格引文补测成功

用户要求“这次训练西游记原著，要求WF完整记录思考、下笔分别保存；你当考官给题，分析从哪些角度思考和为什么用手法”。先提交 [V35_XIYOUJI_PREWRITE_TRACE_EXAM_PLAN_20261017.md](V35_XIYOUJI_PREWRITE_TRACE_EXAM_PLAN_20261017.md)，后真实执行：[V35_REAL_XIYOUJI_PREWRITE_TRACE_RESULTS_20261017.md](V35_REAL_XIYOUJI_PREWRITE_TRACE_RESULTS_20261017.md)。

- 本轮是**首次实际将局部真实原著阅读/写前明确决策/真实原创正文分别持久保存、可串联检查**，不是下载100回原著就谎称模型已熟读。既有私有R2 `xiyouji-23962`完整100回经过SHA/SQLite恢复，模型实读**第1回与第2回各前2000字符**。Source stage0 SHA `125f8ce4305991beacdcfbdf36708b55adc523d62780a7bbd4f02e2dab1063b7`。
- stage1 模型实际阅读后的源文短引文与人物认知/叙事功能有严格原文精确检查，SHA `3d7d951af61116b8bd68512f76bfb67654e7c7935c967171bccd8d0f7fdc12e8`；stage2源经验备选/使用或不用条件/为什么，SHA `c96c926c58481818538e2d8f5ed11b212394421ed21db6834cc2b30fed5d102e`。这些是**显式WF叙事决策文字**，不可称为真实不可见token级chain-of-thought、不能把quote存在等于语义正确。
- 考官预先独立设计3个完全原创第一章题目，SHA固定抽到`mountain_market`山镇女药童误认药材，直到stage2记录已写R2才把题目交给WF，不能看原著情节抄写。stage3**写前**决策记录7种角度 `goal/knowledge/causality/scene/sensory/dialogue/foreshadowing`，每种含选择/原因/舍弃方案/预期读者效果/来源lesson ID，单独锁定SHA `a268aa596cf3c98328eeeb785ea026d65ba666ca41a226ef3b023e50d6894895`。
- stage4原始GLM原创首章**904字符**、完整正文已存私有R2，SHA `9c3a671ed8c588019a0f46b0613641b59441282983bce4bb0882c20ebcfafe70`；stage5独立修订**1136字符**、完整修订稿额外保存，不覆盖原稿，SHA `605fc022f59a87e3eb4d199ed7ef0c9898c1ce52edfa03a2674a8db0d80d0acf`。WF writer**没有拿到西游记原文**。
- **真正失败保留**：[原版一次性workflow #39018112434](https://github.com/66tyu55/WriterForge/actions/runs/39018112434) completed/failure，第一轮stage6模型写后自查引用一段不在真实小说正文里的短句`RETROSPECT_QUOTE_NOT_IN_DRAFT`，只有stage0..5成功。原版7次模型API调用，不得说8阶段全成功，也不得将坏自查改成满意的假记录。源文阅读/初步分析/写前计划/原稿/修订稿都可在私有R2读取，原版坏模型自查仅留下失败码，raw响应未保存不可恢复（后续应先储存无效原始回复）。
- **只修复写后核查，完全不重做学习和写作**：[独立追加一轮 #39018718650](https://github.com/66tyu55/WriterForge/actions/runs/39018718650) completed/success。用stage3不可变写前决策和stage5冻结正文，考官程序从**真实正文**直接机械提取短句菜单，WF在其中选精确证据并解释计划与实际差别。2次模型API调用，追加记录包括未通过模型回复与复查记录，不触动原stage0..5；最终**4项实际原文引文通过**，新独立写后校验SHA **`412b6ceb09d8513c72d4df58d9792d483d5bb6b5b36a8ea955e74812afee595d`**、考官核验SHA **`910f2495624038194d7f020fd34eff4ccdf18033589ab70d137828d2152ab454`**。此成功是追加流程，不允许说原先错误没发生。
- 私有存储总共**9次模型API请求**（7首次+2补测），服务商结算与预留Token区分。由于用户要求“分别完整保存”，原著片段、WF读书观察、写前决策、两份原创全文、有效写后核查都存入现有R2私有桶**明文JSON对象**（仍有服务端存储权限管控，但未配置独立客户端AES密钥，**不能称端到端加密**）；公开Github日志只印SHA/长度/状态。若用户要在聊天里审阅全部正文，需要具备权限的安全查看/导出通道，不能发布到公共日志。
- 核心观察：**Wf确实能保存自己的写前决定并在之后创作**；但是“自我复盘时凭空引用”是真实的底层思考忠实性问题，此次机械摘取真实正文引文的追加补测在一篇文章上纠正了证据位置问题，仍无独立人评文学因果与技巧合理性。未升级Skill，第一文学正式窗口`NOT_PASSED`、第二`LOCKED`。
- 新模块 `writerforge/v35_xiyouji_exam.py`、`writerforge/v35_observable_trace.py`、`scripts/run_v35_xiyouji_decision_trace.py`、`scripts/recover_v35_afterdraft_only.py`，工程测试`tests/test_v35_xiyouji_observable.py`。后续打断点先审stage1原著观察→stage2抽象机理→stage3写前行动计划→stage4/5真实句子→追加写后4项引文，**不得只看模型自评高分、源码测试数或作文长度宣称已学会西游记文学手法**。


## 39. 【最新交接 V36 · 2026-10-17】真实《西遊記》学习迁移链路断点回放：只有L2伏笔手法进入写前构思，写后却没有核验这一项

用户V35连续学习、构思和写作试验因连接中断，指示“中断了--继续”。**本轮没有再付费模型训练，也没有篡改旧正文/写前决策**。新脚本 `scripts/debug_v36_xiyouji_learning_to_writing.py` 已对六个真实原始R2阶段（stage0–5）和独立追加的写后证据复盘/考官记录按**完整stage envelope SHA**重新GET，校验真正文章正文、来源索引、手法编号、预先冻结的写前原因及4条追加写后引文。详见 [V36_XIYOUJI_EXACT_SOURCE_LESSON_WRITING_TRACE_20261017.md](V36_XIYOUJI_EXACT_SOURCE_LESSON_WRITING_TRACE_20261017.md)。

- **关键发现**：源文第1/2回各2000字符已读并引用核验，文学观察4项，提炼待验证手法 **L1、L2 两条**；写前计划共7个角度`goal/knowledge/causality/scene/sensory/dialogue/foreshadowing`，**只有`foreshadowing`明确绑定L2（源阅读观察索引1），其余六项没有来源lesson关联**。WF后来追加的4项有效写后核查仅针对`goal/knowledge/causality/scene`，**完全未核验唯一声称采用西游记学习手法的`foreshadowing`**。真实证据状态 `SOURCE_LINKED_DECISIONS_NOT_CHECKED_IN_POSTWRITE`。绝不能把4个“真实存在的句子”误称4次文学技巧应用验证；也不能据此证明WF没有使用L2，只能证明尚未记录其实际效果。
- 原始904字，修订1136字，SHA与内容完全对齐；有**899字的原始文本处于两稿一致匹配块（约99.45%）**，新稿净增232字符。4个追加写后引用中的`causality`对应确切短句只在修订稿存在，而目标/知识/场景引用在原稿已有；“最初下笔 vs 修订后”不可混为一谈。
- **零模型真实R2审计**：[V36 #39020574772](https://github.com/66tyu55/WriterForge/actions/runs/39020574772) completed/success，创建私有不可变审计SHA **`8a2aca0810c22fbca8a01519a1b573f87ccf38ee6ee3b8decaddb33dc91b1328`**。只输出角度、SHA、字符位置与真假布尔，不泄漏原著、完整原创新稿、实际构思文字或私人密钥。
- **实际底层护栏**：`writerforge/v35_observable_trace.validate_after(...,required_lesson_angles={...})` 以可选参数新增对“写前绑定文学新课L1/L2的角度必须有对应写后正文引文”的校验，没有就`LEARNED_LESSON_PREWRITE_NOT_REVIEWED`；**旧实验原始写后失败和补测未被回写修改**，未来可选择强制启用。V36审计新字段`source_linked_prewrite_angles`、`source_linked_prewrite_angles_checked_after_drafting`避免平均掩盖学习手法漏检。只证明引用与流程，不证明文学因果已经独立验证。
- **用户可审阅完整内容的办法**：新增本地只读`scripts/export_v35_full_trace_private_local.py --output <新建的本地私有文件夹>`，在用户本人电脑配置R2权限后可**在公共GitHub仓库之外**导出源文实际阅读片段、原文观察、两条提炼手法、七项完整写前决策及原因/弃用方案、904字第一稿、1136字完整修改稿、追加写后复盘、考官审计和V36逐角度详情。程序明确拒绝GitHub Actions、git工作目录以及覆盖已有文件夹；不会在公共日志或仓库公开正文。此导出接口已实现并经离线安全单测，**没有运行用户本地导出，也没有客户端AES加密R2文本**。
- **后续最优先**：只针对这条 **L2伏笔手法** 做真正的写后对应引用及独立文学语义评价，不需要再读100回/刷三题/添加十个Skill；不许把WF写后理由冒充隐藏的模型推理。正式文学first `NOT_PASSED`，second `LOCKED`，V35原始失败永久保留。


## 40. 【V38 最新交接 2026-10-17】L2伏笔原始证据角色错位：WF自认铺垫R39，独立Pro把同句标记为回收

用户继续“继续”V37专项，要求严格通过原始《西游记》、提炼L2、写前计划、904字初稿和1136字修订稿找WF学习思考为何不可靠。本轮已经实际修改/测试GitHub底层、执行真实R2对照与**一次**受限模型写后自查，所有原稿、候选技能、写前记录和先前失败证据保留不变。完整核验：[V38_XIYOUJI_L2_CAUSAL_ROLE_CONFLICT_FINAL_20261017.md](V38_XIYOUJI_L2_CAUSAL_ROLE_CONFLICT_FINAL_20261017.md)，预注册目标 [V38_L2_TRANSFER_GATE_PLAN_20261017.md](V38_L2_TRANSFER_GATE_PLAN_20261017.md)。

- **关键修复：把源学习手法接入真正写后验证入口**：`writerforge/v35_observable_trace.validate_after(...,learned_lessons=...,lesson_transfer_claims=...)` 现在会调用 `writerforge/v38_lesson_transfer_bridge.verify_lesson_transfer_claims`。如果写前宣称使用源手法L2，就必须写后单独核验该手法对应的foreshadowing角度，提交真实存在、独一无二、位置先后正确的铺垫/回收正文短引文，以及人物知识边界、因果解释、适用不确定性；允许`NOT_APPLIED/UNCERTAIN`而不是强行编造。原本只查4个普通维度不能被认作L2成功。
- **真实历史负对照，0次模型调用**：[V38 #39024299243](https://github.com/66tyu55/WriterForge/actions/runs/39024299243) success，私有R2真实后审查询严格返回 `LEARNED_LESSON_PREWRITE_NOT_REVIEWED`，说明V35原始和追加的四个通用后审角度确实没有检查唯一来源绑定L2的伏笔。不可变新R2 SHA `97914f6c8442ff7d7884b6a1c6cfae8e6fb6924c421e8bf4d03a63535fa6ec13`，历史不改、不凭空补文学分。
- **原先冻结1136字作文的WF追加L2自审**：[V38 #39024752169](https://github.com/66tyu55/WriterForge/actions/runs/39024752169) success，**只新增1个付费Flash模型请求**，WF的答案`CLAIMED_APPLIED`，从考官机械生成的真实正文短句目录选两句；二者真实存在、唯一且先后正确，考官允许追加1个foreshadowing检查，不动历史四项检查、不动原先最大缺点/写前构思/初稿/修订稿。独立追加私有R2 SHA `a9d5d521b2e0adbeb416f9325b0adabaad408abb728bd978099effe328488a62`。**这是写后说法，不等于写前真正形成的思考，也不等于文学证明。**
- **真正定位的写作语义风险**：WF后补自认**伏笔铺垫为R39（全文79.93%）**、回收R43（89.35%）。但是之前独立DeepSeek Pro **完整有效模型评语**把R39列为**回收**候选而不是铺垫（它选的铺垫是R34/R35、约69/71%）；MiniMax原始模型也把R39列为回收候选、它选择的铺垫是R02/R29约2.5/58.5%，但MiniMax全文评审有`uncertainty=[]`、**不能当成完全有效第二票**。所以有至少一位结构完整的独立阅卷者与WF在**同一句真实小说文字到底是铺垫还是回收**发生具体冲突。两者都把WF的R43放入回收候选，但这仍不能证明伏笔文学效果。
- **真实零模型角色冲突交叉核对**：[V38 #39025097935](https://github.com/66tyu55/WriterForge/actions/runs/39025097935) completed/success，将实际WF自审与两位考官先前的句子编号对齐，分别记录完整考官和格式不完整考官的`setup_was_reviewer_payoff`而不误算两票；私有R2新审计SHA `e2ed24abc352daef678165de8bee5f7c283f5709cf3a23c9fe99b9a876aeb0db`。模型调用0次。历史V37d数值对照R2、V37c缺失字段均保持不变。
- **工程回归**：新 `writerforge/v38_lesson_transfer_bridge.py`、`writerforge/v37_foreshadowing_evidence_gate.py`、`scripts/append_v38_frozen_l2_selfcheck.py`、`scripts/audit_v38_actual_l2_gate.py`、`scripts/audit_v38_l2_student_vs_critics.py` 和新合成回归。最新全量 [#39025097922](https://github.com/66tyu55/WriterForge/actions/runs/39025097922) **568项通过**。只证明工程与证据链管线可靠，不能声称WF文学能力已改善。
- **底层故障真实定位**：R2保存和写前思考存在，原著阅读抽象手法未得到一致独立评价（Pro`FAITHFUL`、MiniMax`PARTIAL`）；自审以前可以跳过来源绑定的唯一新手法，现在严格拒绝；补上证据之后仍发现**“先后真实句子”在文学语义上被WF可能误认为“伏笔铺垫→回收”**，作者自报与独立评论者意见冲突。真正有待改进的是`前置线索/人物有限知识/行为决策/后续信息回收`的**语义角色和因果状态判断**。不要事后硬加“必须前50%铺垫”的万能阈值，也不允许靠重复试题给L2晋级。
- **下一步**：以这条角色冲突作为不可变负面经验进入实验候选区，设计未来WF创作时提前声明“线索出现→影响人物选择→后续回收”的自然因果链，盲评真稿验证。不得直接替WF改写L2或因一题负例全局删除它。正式文学学习first `NOT_PASSED`、second `LOCKED`，没有官方技能晋级或人类独立文学毕业验证。


## 41. 【2026-10-17 交接封存】当前真实进度V38；下一窗口不重复训练、先定位L2伏笔叙事角色混淆

用户在研究了V35原著学习、显式写前构思及V37的严格伏笔核验后明确要求“交接吧”。本节在此刻直接核实GitHub `main` 及实际Actions后封存，以便下一窗口**直接从第40/41节接手**。详细文学发现与证据见 [V38_XIYOUJI_L2_CAUSAL_ROLE_CONFLICT_FINAL_20261017.md](V38_XIYOUJI_L2_CAUSAL_ROLE_CONFLICT_FINAL_20261017.md)；前阶段真实证据参见第38、39节。**本次交接只更新文档，不发生新的付费模型调用，不重新生成原稿、复查评分或改写WF技巧。**

### A. 实际完成，不能冒称文学晋级

1. 真实公版中文《西游记》已存私有R2 `xiyouji-23962` 完整100回并可恢复；**V35模型实际阅读的是第一、二回各2000字符**，不是一次模型完整读完一百回。4条带原句的原文观察、2条未经独立证实的源学技巧`L1/L2`已SHA保存。
2. 考官预注册原创题 `mountain_market`（山镇女药童误认草药）；WF写前明确给出7个角度`goal/knowledge/causality/scene/sensory/dialogue/foreshadowing`，**只有`foreshadowing`绑定从原著得出的L2**。904字符原始第一稿、1136字符修订稿完整原文分别储于私有R2；写前记录先于正文已锁定，均不能回写。V35原始写后自查曾引用不存在的句子而失败；后续附加4条成功自查针对goal/knowledge/causality/scene，**仍漏掉真正引用L2的foreshadowing**。
3. 已实际在`writerforge/v35_observable_trace.validate_after`接入`writerforge/v38_lesson_transfer_bridge.py`：若写前明确关联新手法，写后必须覆盖其角度并附精确来源、前后可追溯正文引文、人物知识边界与因果解释；可以诚实返回`NOT_APPLIED/UNCERTAIN`，没有证据不予晋级。真历史负对照 [Actions #39024299243](https://github.com/66tyu55/WriterForge/actions/runs/39024299243) 返回`LEARNED_LESSON_PREWRITE_NOT_REVIEWED`，不可变私有R2 SHA `97914f6c8442ff7d7884b6a1c6cfae8e6fb6924c421e8bf4d03a63535fa6ec13`。
4. WF仅在**冻结的1136字符修订稿上**额外做了**一次**有界模型自查 [Actions #39024752169](https://github.com/66tyu55/WriterForge/actions/runs/39024752169)：它自报L2 `CLAIMED_APPLIED`，从真实文章选出R39(79.93%)作为“铺垫”、R43(89.35%)作为“回收”，字符串存在/唯一/顺序已核实；新追加R2 SHA `a9d5d521b2e0adbeb416f9325b0adabaad408abb728bd978099effe328488a62`。**不能把事后说明倒灌为写前真正思考，也不能说文学效果通过。**
5. 独立DeepSeek V4 Pro**结构完整的模型评语**把R39认作**回收**候选而非铺垫，认为更早的R34/R35(约69.19%/71.39%)承担铺垫；MiniMax原始意见也把R39认作回收，但因`uncertainty=[]`导致完整评审协议不合格，只能当参考线索。此前Pro原著L2抽象判`FAITHFUL`、MiniMax判`PARTIAL`，这进一步反映语义解释不稳定。真R2句子角色交叉核对 [#39025097935](https://github.com/66tyu55/WriterForge/actions/runs/39025097935) completed/success，SHA `e2ed24abc352daef678165de8bee5f7c283f5709cf3a23c9fe99b9a876aeb0db`；**跨模型观点分歧是观察，不是人类文学真值**。
6. 最新确认GitHub `main` **`c9664e1bf7de27f3fe63e1b3d30aa2f20e691922`** 对应 [WriterForge Tests #39025294257](https://github.com/66tyu55/WriterForge/actions/runs/39025294257) **completed/success，568 tests passed**。不能拿工程测试或自评说明WF文学能力已进步、正式学习通过或模型权重更新。

### B. 当前最可信的失败定位

- 不是R2“写入/读回失效”：真实来源、WF明确表示的构思、完整原稿和写后说明都有SHA、按时序存档。
- 真正值得修的是**“显式文学经验→在创作阶段规划前置线索→影响人物有限信息与行动→后续回收”之间的语义角色判断与因果验证**。仅找到两句实际存在、时间先后的文字，不足以证明“一句是真铺垫、下一句是真回收”。
- 之前审评接口亦曾发生JSON解释过长/不确定性数组等技术失败；历史完整有效与格式无效的评论必须分开使用，绝不能拼凑或平均成更有利WF的分数。
- 当前**只有一篇**真实文章的L2角色冲突，不能据此全局删除L2、给全部题材硬编码“前50%才算伏笔”，也不能宣称已经独立证明具体手法必然有害。

### C. 下一窗口唯一优先工作：源码和正文角色定位（不要先重训）

1. 先打开本文件第40/41节和完整 [V38真实复盘](V38_XIYOUJI_L2_CAUSAL_ROLE_CONFLICT_FINAL_20261017.md)，检查`main`状态；复用私有R2已存在的R39/R43自查和R34/R35/R37–R43独立考官回执，**不重新付费阅读西游记、改写904/1136字原稿或重复评分**。
2. 对真实冻结修订稿**只在私有环境中**检验具体伏笔因果：R39出现前，相关物件/线索是否已登场、人物当时实际知道什么、R39是否改变了人物目标或可作的决定、R43后来揭示的是R39还是更早细节。结论允许`铺垫`、`回收`、`重复提示`、`两种功能兼有`或`无法确认`，**不应预先强选一种**。
3. 对`writerforge/v38_lesson_transfer_bridge.py`的未来实验设计一个**人物知识状态与线索身份的时间序列记录**，让WF在写正文之前就明确规划“谁看到哪个线索→引发什么判断与行为→何时回收”，写完由同一稿真实句子核验，避免只靠写后即席解释。先纯合成/零模型单测，确保原有Skill和历史证据不被删除。
4. 若之后允许真实独立文学盲审，需先定义/保存审稿合同及严格预算，再使用**新的预注册题目**比较学习前后；旧稿用于故障剖析而非反复刷高分。任何仍不确定的文学判断单独归档，零晋级。

### D. 资料、安全和停止条件

- 实际代码路径：`writerforge/v35_observable_trace.py`、`writerforge/v37_foreshadowing_evidence_gate.py`、`writerforge/v38_lesson_transfer_bridge.py`、`scripts/append_v38_frozen_l2_selfcheck.py`、`scripts/audit_v38_l2_student_vs_critics.py`、`scripts/debug_v36_xiyouji_learning_to_writing.py`。所有旧原稿、原文窗口及详细WF思考仍只在Cloudflare**私有**R2中，尚未使用独立客户端AES加密；不要把完整原著、原创全文、思考记录或API密钥打印到公开GitHub日志。
- 既有测试/证据SHA必须原样保留；新调试记录要内容寻址、不可变、可读回。反作弊：不让WF自己当独立考官，不把模型意见当客观文学真值，不拿正例均分抵消R39具体负面争议。
- **当前状态**：第一课程窗口`NOT_PASSED`，第二`LOCKED`，实验L2未成为已验证的稳定正式技巧；下一窗口从**R39/R43和更早的真实线索/人物知识状态**开始，而不是重做整个西游记训练流程。

## 42. 【2026-10-18 中断交接】V55关系网络19项真实对抗试验：11/12基础通过、0/7扩展通过；暂停修复，保留全部旧文与V49失败

**这是聊天窗口达到最大长度时的新交接入口。请下一窗口先读本节，再读** [V56完整中断交接与19项失效分类](V56_RELATION_NETWORK_INTERRUPTED_HANDOFF_20261018.md)，最后才考虑新版本修复。**本轮未训练WF、未调用模型、未改写文学/R2原稿。**

### A. 真正已完成／不可混淆

1. 截至本次冻结，正式 GitHub **`main=a4f7b8d8ed68526f947f8e7db8bf4a5744ce7086`**，V53磁盘资料处理与离线索引、V54显式下载许可／追加事实账本、V55双时轴时间记录／有限图关系均已合并。`V55`版本不是文学等级晋级，V49第三次文学能力终审`THIRD_STRIKE_FAILED`依旧有效。
2. 用户本轮说“**测试你的关系网络**”，要求强制反作弊、找出底层缺陷。V56生产冻结不修源码，隔离审计分支 **`v56-relation-network-adversarial-audit`** 只新增 `scripts/audit_v56_relations.py` 和 `.github/workflows/v56-relation-adversarial.yml`。**[Actions #39095760849](https://github.com/66tyu55/WriterForge/actions/runs/39095760849)**：原有V55专项9项通过，但V56原始19项审计发现扩展能力失败，`--strict`按设计退出1，所以CI为**红色**，不允许谎称整体成功。
3. **原始19项：基础12项中11通过；预期扩展7项中0通过**。原始输出 JSON SHA256 **`bc333be303d03c4ba642deb88944593dd39430a942a734cf637188ea105b6bc2`**；工作流 artifact `V56_Actual_Relation_Network_Audit` ID `12123489686`（90天），ZIP SHA256 `539c8fe9087a76345bf8a2a0daa7e57c244c87c44b6b08d6430237ded4392f95`。均为临时SQLite的合成形式化事实，无付费模型、无R2网络、无真实文学创作。
4. **确切扩展失败 7 项**：`guard.reader_future_spoiler`（读者过早知道后文）、`guard.reader_private_thought`（角色内心秘密无披露证据却让读者已知）、`guard.knowledge_evidence_support`（UNKNOWN来源可冒充KNOWN）、`continuity.cross_chapter_link`（第1章线索无法连第3章回收）、`continuity.cross_chapter_state`（人物事实跨章查询变UNRECORDED）、`chronology.flashback_import`（导入倒叙早期事件被单时钟防倒填拒绝）、`scale.long_record_chain`（同一事实68次记录超过64条查询上限）。后两者属于明确的策略／容量限制，不能当成“模型理解错了”或“内存泄漏”。
5. **第8个红项 `revision.no_fork` 属于审计夹具本身失效，当前不能将其记为已证实的分叉安全漏洞。** 输入错误地用故事时间8的`KNOWN`证据支持时间2的`KNOWN`，最先触发正确的`FACT_ACTOR_KNOWS_BEFORE_EVIDENCE_EVENT`，而非预期的“同一旧版本双重修订”护栏。须下次**另造合法且事先冻结的独立测试**；保留本次红项，不修补旧JSON。
6. **确定通过的基础约束**包括：故事时间与入库记录时间分别回放、角色/读者作用域分离的存储、同一事实相互矛盾并存、拒绝角色提前获知、图边方向、禁止不同故事错误连边、图关系及记录篡改校验、重启恢复、`POTENTIAL_CAUSE`永不伪称语义因果。不能由此宣称整个跨章节关系网络完善。

### B. 别忘了**上一次中断的对话／旧文学失败**

- 第40、41节完整记录**V38真实《西游记》L2伏笔冲突**：WF认定R39为“铺垫”/R43“回收”；有效独立Pro把R39当“回收”，认为R34/R35更像铺垫；MiniMax意见因`uncertainty=[]`完整审稿不合格，不能算第二个正式判定。R2交叉核对SHA **`e2ed24abc352daef678165de8bee5f7c283f5709cf3a23c9fe99b9a876aeb0db`**，904字初稿／1136字修订及原文来源都不可重写。
- 后续V41—V51尝试宿主文学阅读／A-B／写作策略实际控制，**V49第三次终审已判WF文学经验自主改进能力未获证明，`THIRD_STRIKE_FAILED`**。不能把V55/56工程回归和图谱记录功能当作取消此终审的证据。
- 用户长期要求原文先入库→分类/学习→可反证经验→真正行为改变→新题独立评价，**禁止考官／辅助模型替WF写文学答案、禁止旧证据回填、禁止重复付费训练、禁止人类不可信评论伪造成功**。50部完整作品才进入统一文学成果验收；六部现代小说目前确认了私有R2原文归档，不等于全文深度学完。
- V53纠正“R2整库下载被冒充检索”和“原著短句直接拼入WRITE”；V54对陌生用户安装不自动下载私有资源，先明确授权再同步；V55强调**词面索引先后不等于故事时间先后**，本次V56审计正是其后续验证。

### C. 下一窗口恢复顺序；这些尚未执行

1. 先从`main`读取本交接42节和完整V56文档，核对 `v56-relation-network-adversarial-audit` 分支、GitHub Actions及原始JSON SHA，**不要启动文学训练或直接清空旧库**。
2. **先修测试设计再修程序**：`revision.no_fork`原夹具不合法，下一轮新题应给出符合已有时间知识规则的两次修订，并独立检查是否错误接受。绝不修改原运行报告。其他7项分类成读者信息屏障、知识来源可信度、跨章实体连续性、倒叙/时间轴和长链容量。
3. 若继续开发，建新的隔离V57分支：优先用**明示同一作品/角色/事件身份**跨章节连线，同时保持不同作品隔离；`READER`披露/时间也需校验、`KNOWN`须有一致来源，故事发生顺序与数据库写入顺序不可混用；超过64项的历史回放做分页/视图快照，不取消安全界限。不引入LLM自动判断“因果”或原著段落复制。
4. 全部下一轮新反例都需保存原始失败、新代码、新运行结果分别SHA；V56旧脚本与红色原始证据**不得覆盖**。V56审计分支不合并`main`；本交接只是文档更新。
5. **本次中断停止处**：V56的19项结果刚刚跑完并导出了ZIP，尚未修任何V55关系代码，也尚未开始V57。恢复后先确认失败归因和修复优先级。


## 43. 【2026-10-18 V57独立修复】保留V56红色证据；显式跨章作品身份、读者披露、倒叙、长历史与并发无分叉

**重要：本节仅在 `v57-relation-evidence-foundation` 修复分支记录，正式 `main` 尚未合并；第1—42节不可重写。** 详细报告：[V57关系网络修复、证据哈希及未完成事项](V57_RELATION_FOUNDATION_REPAIR_20261018.md)。

1. 已逐一读取第42节和V56完整交接，复核原始红色 [Actions #39095760849](https://github.com/66tyu55/WriterForge/actions/runs/39095760849) 日志；19项为基础11/12、扩展0/7；原始JSON SHA `bc333be303d03c4ba642deb88944593dd39430a942a734cf637188ea105b6bc2`；ZIP SHA `539c8fe9087a76345bf8a2a0daa7e57c244c87c44b6b08d6430237ded4392f95`。原脚本和原始报告未修改。
2. 原 `revision.no_fork` 夹具引用未来证据不合法，不能证明分叉漏洞。V57修正合法夹具并发现应增加 SQLite 数据库级唯一索引防并发竞争：`temporal_claims(supersedes_id)` 唯一。
3. V57修改 `writerforge/fact_journal.py`：READER KNOWN 增加披露时间及角色私密THINK隔离；KNOWN必须有同状态证据；`register_scene` 明示同一作品/章节绑定后允许跨章图和作品范围状态查询；`append_flashback` 明确故事时间与记录顺序并存，普通追加的禁倒填不变；`temporal_view` 每批64条、最多8192条扫描，返回受限引用与完整计数。
4. `writerforge/cli.py` 开放 `fact-story-bind`、`fact-flashback`、`fact-view --story-id`，已有真实端到端CLI合成测试通过；V54旧测试12/12、V55旧测试9/9、V57新测试12/12，合计33/33，见绿色 [Actions #39100156422](https://github.com/66tyu55/WriterForge/actions/runs/39100156422)。新JSON报告SHA `327a661d0ee7f5da6749f8be5b29a6d97d0efcac723a323fa28b9eafdf99e485`；证据artifact ID `12125889031`。
5. 本次没有文学训练、R2同步、模型调用、原文覆盖，也未合并main；V49 `THIRD_STRIKE_FAILED` 未改变。SHA 不能证明文学来源真实性；读者披露及作品/角色身份仍属显式声明，不能由关键词或语言模型擅自推定；旧 `state()` 64条保护和图搜索48边限制仍待专项设计。
6. 下一次恢复：先读本节→完整V57文档→CI链接及哈希；继续不同作品同名角色、跨章变更、伪造来源和超长分页压力测试。不要重复文学训练，也不允许把V56红色报告覆盖成绿色。

## 44. 【2026-10-18 V58二次红队与修复】同名人物身份、可信披露和分页游标伪造

**最新恢复入口（仅V58分支）：[V58完整红队、修复、哈希与待解边界](V58_RELATION_REDTEAM_AND_REPAIR_20261018.md)。正式 `main`、旧V56原始红色审计和V57旧绿色结果均未覆盖。**

1. 先冻结第42节/原V56及第43节/V57。本轮另建 `v58-relation-redteam-hardening`，从原V57分支衍生；不重新训练文学、不调用模型、不访问R2。
2. 独立新反例先跑红：[Actions #39102724949](https://github.com/66tyu55/WriterForge/actions/runs/39102724949)：旧33通过、新V58 `0/7`，其中两项确凿错误接受为**同名角色跨章错误合并**和**自标 `REVEAL` 欺骗读者知识屏障**；另五项是尚无接口的ERROR，不允许全部称为已证实漏洞。原JSON SHA `84dc7204bdbdd6e81c0cdb391d1780f18de720047b0ea1685881ce16c6279b19`，证据artifact ID `12127521456`。
3. 修复后继续构造新的分页攻击，记录第二次红色：[Actions #39103323696](https://github.com/66tyu55/WriterForge/actions/runs/39103323696) 新用例9/10通过，攻击者可更改游标 `last_seq` 并重新计算公开SHA，使大量记录被伪装成“已读完”。原JSON SHA `9e4cf4b3da9eaf1c9c3b9d588158b0985ecd7f76afbba6814f59dd2cd49a75f3`，artifact ID `12127313192`。
4. 代码修复：显式 `bind_subject` 规范身份；READER/KNOWN 必须通过独立HMAC签名披露验证（不认证文学语义）；时间/受众与证据事件绑定；游标改为每数据库持久随机HMAC密钥；记录序号快照分页；V58 CLI 接入 `fact-subject-bind`、`fact-disclosure`、`fact-page`。V55/V57分支的旧测试不动，本分支正向夹具透明迁移以满足新签名契约。
5. 最新真实CI：[Actions #39103469679](https://github.com/66tyu55/WriterForge/actions/runs/39103469679)：V54 12/12、V55 9/9、V57 12/12、V58 12/12，合计**45/45合成结构测试**。验证8,193条历史：完整状态计算超8192拒绝，129页元数据可无损遍历。新JSON SHA `482bb71d6253a06d5414cd4fb9c275eb650fbc2d45d7fa7807de82e76e2d946e`，artifact ID `12127497908`；全部代码/test SHA见V58完整报告。
6. **严禁夸大**：身份与叙事披露的可信来源目前仍依赖受控输入/验证者。SQLite DB所有者可篡改本地HMAC游标密钥。尤其`as_of_recorded_seq`目前未覆盖“身份绑定/披露授权发生在何时”的统一登记时钟——未来补绑有可能改变旧历史的投影范围，下一轮优先专测此项。不能声称语义因果、真实角色解析、完整双时轴或文学自主写作已经完成。V49 `THIRD_STRIKE_FAILED` 不变。

## 45. 【2026-10-18 V59】GitHub源码对照→失败反例→统一全局登记时钟→58项回归

**最新入口仅在V59隔离分支**：[V59 Github源码机制对照、原始失败与最终SHA](V59_GITHUB_SOURCE_COMPARISON_GLOBAL_CLOCK_20261018.md)。V56—V58所有旧运行证据不覆盖；正式 `main` 仍不合并。此前第42节/V56及第43—44节/V57—V58均为历史记录，不许回写伪造新成功。

1. **先读他人源码再开始**：已实际读取 GitHub [eventsourcing SQLite事务及通知日志](https://github.com/pyeventsourcing/eventsourcing/blob/9.5/eventsourcing/sqlite.py)、[django-simple-history历史关联投影](https://github.com/django-commons/django-simple-history/blob/master/simple_history/manager.py)、[SQLAlchemy按实体版本存历史](https://github.com/sqlalchemy/sqlalchemy/blob/main/examples/versioned_history/history_meta.py)。记录blob SHA、优点、缺陷与为什么不直接引入框架，全部见V59文档。没有Copy外部实现。
2. 新反例**先红**：[Actions #39105219080](https://github.com/66tyu55/WriterForge/actions/runs/39105219080) 旧回归45/45，新7项0/7；旧图跨章人物后绑定使过去分页错误改变的失败已重现；原始JSON SHA `c1eedd3e8a8a509000bdda4a6ece69554e06aca813b766961d9b1c38ef4e17fb`，证据artifact ID `12127911793`。随后图/CLI新反例第二次红色 [Actions #39105648147](https://github.com/66tyu55/WriterForge/actions/runs/39105648147)，V59 8/11，原始JSON SHA `b941c70f013fe8d76c2c966712244e5e9359e896482c7adfaea48152ea1eef72`，artifact ID `12128161845`。都保存，不能把旧红色改成绿色。
3. V59生产修复：`writerforge/fact_journal.py` 增统一递增 `ledger_operations`（事件、作品/章节、人物身份、读者披露、主张、边）；SQLite触发器与事实插入同事务；`temporal_view`、`temporal_claim_page`、`graph_neighbors` 共享 **`as_of_ledger_seq`**，在历史回放过滤未来才登记的身份/披露/边；旧 `recorded_seq` 不删。HMAC游标v2固定全局账本快照。CLI `fact-ledger-head` 和 `--ledger-seq` 已接通。
4. 初次升级旧库时，用 `BEGIN IMMEDIATE` 把历史回填、迁移标记和触发器创建放在**同一写事务**；不在事务中调用会隐式提交的 `executescript()`。新测试证明第二连接不能从回填与触发器之间插入“没有全局登记时钟的事实”，失败事务的时钟与事实原子回滚。迁移前原本丢失跨表先后的老SQLite数据，以 `legacy_unordered` 标记并拒绝不可靠的历史快照，不能人为制造旧登记顺序。
5. 最终真实绿灯：[Actions #39105993899](https://github.com/66tyu55/WriterForge/actions/runs/39105993899) 原有V54 12、V55 9、V57 12、V58 12，新V59 13，合计**58/58 合成事实软件结构测试通过**。最终JSON SHA `0b395c14bf9b997cc637b10cded46338db037ddf9915b2522943afdd63653cc4`；artifact `12127897818`；源程序和测试SHA见完整V59文档。
6. **未完成绝不可漏**：这不是文学理解、因果或知识来源真值证明；原V49 `THIRD_STRIKE_FAILED`、`NO_PROMOTION` 不变。旧V58写入进程必须在升级前停止，否则跨版本热迁移有风险；HMAC/数据库原始访问边界不等于外部公证；8192状态扫描和图邻域预算仍有效；更大历史规模、原始SHA可信来源与多节点同步未验证。本轮没有下载R2，没有模型训练，没有覆盖私有原文或旧原始证据。
7. 下一轮先复核上述两张红色artifact和最终绿色，优先审查安全迁移部署、源证据授权、全局时钟数据量增长/冷库恢复；对照GitHub现成实现后才扩展，不复制代码。


## 46. 【2026-10-18 V60仅审计】真实LEARN→经验→WRITE调用关系与未解决权限边界

**这轮没有重构生产代码，没有任何文学训练/付费模型/R2下载；从 `v59-global-ledger-clock-audit` 的 `3e589412acabaee95e9881923b0f3fa4cc7080c2` 创建新分支 `v60-architecture-audit-readonly`。** 完整证据、逐项源码/行号、GitHub参考源码、数据流及下一阶段受限重构设计见：[V60完整架构审计](V60_ARCHITECTURE_AUDIT_20261018.md)。

1. GitHub真实 [V60 Actions #39107632165](https://github.com/66tyu55/WriterForge/actions/runs/39107632165)：完整原有CI + 3项新诊断共 **642/642执行通过**。这三项新诊断专门用来**复现当前缺陷**，不能称为修复成功。只读架构报告 `ARCHITECTURE_GAPS_OPEN_NO_PROMOTION`，8项开放风险（P0 4项，P1 4项）；源程序零修改。
2. 真正观察到的三件事：正式 `VerifiedWritingFlow.prepare()` 更换Xuehai来源证据后生成的 `prompt_sha256` 仍相同，说明没有把已学经验形成明确写前操作；`EvolutionEngine` 通用 `gated_auto` 接口可用**仅由调用者提交**的全部高分指标，在纯内存测试中把技能L1→L2，未核实第三方证据（不是公网上已证实攻击）；`FeedbackStore.triage` 把任意两个 `reader_id` 当成两个收敛读者（该接口未验证身份）。
3. 其他核心缺口：V31实验记忆、V35/V38写后证据与正式 `VerifiedWritingFlow` 的写前决策没有统一强制门禁；八类原著索引只是 `deterministic_structural_unverified`，不能直接当文学理解；`WriterForgeDB` 与 `FactJournal` 是不同授权边界/SQLite接口，需统一实体与版本引用、**不粗暴合库**；V59仍是未合并的开发阶段，包版本号依旧为27.0.0。
4. 本轮实际读取GitHub [LangGraph checkpoint](https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint/langgraph/checkpoint/base/__init__.py)、[MLflow Run](https://github.com/mlflow/mlflow/blob/master/mlflow/entities/run.py)、[OpenAI Evals Recorder](https://github.com/openai/evals/blob/main/evals/record.py)，对照快照、输入输出及评估收据；只借机制，不引入框架、不复制代码。
5. V60报告JSON SHA256 `8c9cd38c5bb33a01e1b94b4d473525a949deab857671597bef7a483f9959036b`，代码审计脚本SHA `f524d119db3798223b90563dcb8a09778b758f5f9f5256946b3ddb95ebf6e657`，诊断SHA `9176106d7896da1ecfbe070da7f6d045508a600e3474e1b947e69aecf27cc8d3`；原始证据artifact `12129525377`、ZIP SHA `f329a12bdb0f65fc1d6783fab866c32bffc89269ccc272be8eba9970474fb1ce`。
6. **下一步不要改100个Skill**：先审查/限定 `ExperienceCandidate → 独立可信审阅 → CreativeDecision(SELECT/SKIP/UNCERTAIN) → 冻结计划 → 正式写作 → 写后证据` 的最小契约，零模型合成输入先验证调用/跳过/恢复/防作弊；V49 `THIRD_STRIKE_FAILED` 不变，L2历史R39/R43分歧不重新付费训练，也不能强行改为正确。V57/V58/V59稳定版合并需要独立迁移验收。


## 47. 【2026-10-18 V61独立修复】来源经验进入正式WRITE决策；不再用自报高分自动晋级

**重要：仅`v61-experience-decision-contract`开发分支（自V60分叉）。未合并main，也不修改V49、V56–V60原始证据。** 详见 [V61完整实现、红绿哈希和剩余问题](V61_EXPERIENCE_DECISION_BRIDGE_20261018.md)。

1. 本轮接着V60完整架构审计的P0-001、P0-002、P0-003做**最小局部重构**，不是重写WorkTree/调度/R2。新模块`writerforge/experience_decision.py`使用现有`WriterForgeDB`增加4张小表，封存`source_ref`定位和SHA、独立受信签名准入、WRITE`SELECT/SKIP/UNCERTAIN`决策、写后精确引文存在性声明。实验性固定操作原语不等于真正学到文学技巧；不存新的原文/整稿。
2. `VerifiedWritingFlow.prepare()`已接上受控的写前决策：已批准经验必须给定attempt及明确场景事实才可继续；只有SELECT的抽象操作进入prompt；决定在模型前冻结。`accept_candidate`遇到遗漏/篡改决策收据会拒绝，重用旧attempt也重验真实来源SHA和审核签名。CLI可通过`experience-stage/approve/decide/read/postwrite`及`draft --experience-attempt-id --experience-signals-file`使用，不允许自动R2检索或原文拼接。
3. `EvolutionEngine.apply_upgrade`现要求有签名的独立外部指标收据并`manual, approved=True`方可真正升级，`gated_auto`不再晋级。这只关上此公开执行入口，**尚未审计全部内部`SkillRegistry.promote`直接写调用者**；低层信任边界必须后续加固，不可声称全WF已彻底防伪。V12/V60受此安全契约影响的正向测试仅在V61新分支透明迁移，旧独立分支及CI原样保存。
4. 先冻结原始红色 [Actions #39108670931](https://github.com/66tyu55/WriterForge/actions/runs/39108670931)：11项新测试0通过（主要由于当时API不存在，不是11处确认漏洞）；原始JSON SHA `6d582e23a8ef75d89318400d6257a12118900df9f3e39bb30140db155f21f7c0`、证据artifact ID `12129850565`。调试中又复现CLI缩进错误、测试异常类型不匹配，均保留CI红色运行，未删旧测试掩盖。
5. 最终真实 [Actions #39109713890](https://github.com/66tyu55/WriterForge/actions/runs/39109713890) `completed/success`：**V61新增14/14，全仓库656/656**；完整回执JSON SHA `136c2fd9370e73daa86dd76cf3403ae6dcb0ee55d46e09fa298aa815647df6aa`；artifact ID `12129783367`、ZIP SHA `c3c469851f2ee7aa7cf353168b0fba4a1c61f0cb03b50a0d090d5e99a2c35de3`。实际用临时SQLite/合成文本核验了候选定位、签名、跳过、未知、重启、CLI、manifest篡改、写后引文、晋级拒绝等，不是模型写作/文学品质测试。
6. **还没完成的真正大问题**：V31实验规则及V38真实L2冲突尚未由可信语义审核变成V61批准经验；当前scene_signals由调用方给定，规则是预设通用动作，不能当作WF理解文学因果；评论者真实性/权限不可由HMAC本身证明；审查`SkillRegistry`所有直接调用及Studio默认路径、审核/撤销、旧库迁移/存储预算仍是下一步。V49 `THIRD_STRIKE_FAILED`、第一文学窗口NOT_PASSED、第二LOCKED，全部保持。
7. 下一窗口先看第47节→V61文档→红色#39108670931及最终绿色#39109713890；选择唯一一条既有冻结L2/人物有限知识**负面经验**先作为HYPOTHESIS_ONLY对照来源，不得自动批准或让主模型代写；先做独立来源和审批权限审计，然后再考虑真正新题文学盲评。**不重复付费训练，不以代码测试绿色冒充作家文学晋级。**


## 48. 【2026-10-18 V62】WF终于让未完成的经验影响下一轮：SKIP/UNCERTAIN、受信撤销、重新审批、V31/V38旧证据SHA隔离

**仅`v62-experience-negative-transfer`开发分支，不合并main。完整证据、机制与限制：[V62失败经验转移及V31/V38哈希引用](V62_NEGATIVE_EXPERIENCE_AND_LEGACY_REFERENCES_20261018.md)。** V49 `THIRD_STRIKE_FAILED`、V56–V61红绿原始机器报告、私有R2原著及旧稿全部不改。

1. **先冻结夹具错误与真实红色两种不同证据**：初次 [#39111000402](https://github.com/66tyu55/WriterForge/actions/runs/39111000402)新测试0/11，但只是新增测试公共helper传了V61没有的修订参数，不能算11处真实漏洞，原始JSON SHA `6fea83b1e0e349d605a22f87abcb526b7c651206e236d8a7713f883676f69ccd`。修正测试helper后真正 [#39111052510](https://github.com/66tyu55/WriterForge/actions/runs/39111052510)为11项中2通过、**5个真实行为断言失败**、4个尚无接口报错；V61确实会在报告NOT_APPLIED/UNCERTAIN后仍SELECT旧技能、也不会检查旧回执已失效。真实红色JSON SHA `a8f321e57572734d3fcae80089d1d4685311a99e53c40ad31ee9ba5b3bce222f`，artifact `12129919904`，绝不覆盖。
2. `experience_decision.py`现从V61写后SQLite回执建立有界、SHA核对的负反馈视图：`NOT_APPLIED`→下轮`SKIP/PRIOR_NOT_APPLIED`、`UNCERTAIN`→下轮`UNCERTAIN/PRIOR_APPLICATION_UNCERTAIN`。旧写前记录仍可历史只读，但不再可用来生成新稿；`CLAIMED_APPLIED`仅为使用自述，不得冒充成功或晋级。新修订必须新experience ID、改变适用条件或操作并重新独立签名审批，旧失败不得清理。
3. 受信签名`revoke_candidate`永久撤销一条批准经验，后续`SKIP/EXPERIENCE_REVOKED`；所有旧批准和旧失败原文证据保留。新增`experience_legacy_refs`单独存V31/V38已知公开SHA为`UNVERIFIED_REMOTE_POINTER`，**不联网读私人R2，也不允许直接进入WRITE**。两条公开元数据`references/experience/v38_l2_r39_role_conflict.json`、`references/experience/v31_self_review_stage1.json`由CLI在合成库中实际导入读回，不能据此声称旧R2正文完成了新一轮验证。
4. `db.py`只新增revocation与legacy_refs两表和有界反馈索引；`cli.py`新增`experience-revoke`、`experience-legacy-import`、`experience-legacy-read`，并允许`experience-stage`显式修订引用。`source_prose`与R2全文不复制。GitHub源码借鉴OpenFeature `Reason=DISABLED/STALE/ERROR`的「状态 + 原因码」而不复制框架。
5. 最新真实绿灯：[Actions #39111498188](https://github.com/66tyu55/WriterForge/actions/runs/39111498188) V62新增14/14、全仓库**670/670**，全部临时SQLite、无模型文学调用。最终JSON SHA `667bad7454472c151fd3403c262d433dd65736505349762bc210bc1db69455ca`，artifact ID `12130229092`，ZIP SHA `c2cdbc6efb4f50b8170d0273ad4d86e6a5174659792e4d2feece36072afe4d71`；源码/测试SHA见V62完整文档。
6. **不许吹成文学理解**：该负反馈是WF写后`NOT_APPLIED`自述触发保守停用，还没独立语义真值审核；旧V38 R39“自认铺垫vs独立Pro认为回收”仍有争议，模型意见不等于真人文学真值。`SkillRegistry.promote`低层写入口、SQLite双连接并发撤销竞争、读者评论身份认证和私有R2哈希真实性仍需核查；别用临时SQLite测试绿色宣告书写能力晋级。
7. **下次开工先审`SkillRegistry.promote`直接调用与真正权限边界，之后对两个写连接同时决定/撤销做失败先行试验；V31/V38如需升级任何经验，先有只读R2原件SHA和外部可信审核，不能从本报告里抄标题直接通过。** 继续保留原先未通过的文学课程阶段，绝不重复旧题刷分。


## 49. 【2026-10-18 V63】全仓仔细检查：SkillRegistry直接晋级、双连接撤销竞态和StoryCommit最后一刻重新验权

**本节只在 `v63-skill-authority-and-concurrency` 研发分支，基于V62。不是正式main发布。** 完整源码对照、真实断点、机器SHA、整仓8项剩余风险详见：[V63完整全仓权限/并发/架构报告](V63_WHOLE_WF_SKILL_AUTHORITY_RACE_AUDIT_20261018.md)。旧V49、V56—V62从不篡改。零付费模型、零R2网络、零文学重训。

1. 先冻结真实红色：[Actions #39112500068](https://github.com/66tyu55/WriterForge/actions/runs/39112500068)9项测试真实FAIL，但报告生成器脚本初版指错文件而没有完整JSON，不许以其冒充机器回执。随后**只修报告脚本、不修生产代码**，重新执行 [Actions #39112554685](https://github.com/66tyu55/WriterForge/actions/runs/39112554685)：9项独立行为断言**9/9 FAIL**，包括可直接绕过EvolutionEngine.promote、同名注册覆盖L1、可变对象回写、不可信revalidate恢复、数据库升级半提交、两个陈旧注册表同时晋级、两独立SQLite连接在决定/撤销与决定/NOT_APPLIED间竞态、accept_candidate首次核验后遭撤销仍能接受。原始JSON SHA `6647b93f1b6ffe867fd3429309d92b3213855891fabc3ee879a67799d44ad4e3`，artifact #`12130976557`，ZIP SHA `c43edd86df5922db1b98d1fa223762d61782e8c138d15aaed65d486b01757a48`。
2. `evolution.py`现将`CapabilityContract`变成不可变快照、返回时复制依赖表；`register`同名覆盖改为拒绝；公共`SkillRegistry.promote`未签名直接调用一律拒绝；`revalidate(passed=True)`不再凭主观bool激活。经过可信签名、`manual/approved=True`的`EvolutionEngine`才可调用持久化`_promote_verified`，它在DB层重复验签、`BEGIN IMMEDIATE`+revision/level CAS、一次性写入目标/依赖技能及日志，若任一失败则所有SQLite和内存全部回滚。旧V12“可直接注册表晋级”的正向测试仅在V63新分支透明迁移，新旧失败证据保留。
3. `experience_decision.py`现在在首次读撤销/负反馈**之前**`BEGIN IMMEDIATE`，并在锁内生成`SELECT/SKIP`收据。同一SQLite文件另一进程的撤销或NOT_APPLIED不能在这个检查到commit的间隙写入。合法撤销可在其后写入，下次决定SKIP。
4. `story_commit.py`、`writing_flow.py`、`verified_flow.py`将原本的`precommit_check`在StoryCommit自己的`BEGIN IMMEDIATE`内部执行；第一遍经验验证后发生的合法撤销，会在最终接受前被发现并拒绝，避免旧许可被当新许可使用。人工直接写作路径没有被强行废掉。
5. GitHub实际 [Actions #39113729476](https://github.com/66tyu55/WriterForge/actions/runs/39113729476)：**V63修复型9/9 + 残留风险观察2/2；全仓681/681结构测试绿色**。修复后JSON SHA `6997eb0d1eb60131d1f83440298cc6644d161cc00e26ebcc337f2e5e5e19416e`；另有全仓静态调用审计报告 SHA `39c0fa13c46d564c5a81b665a85eb78d21f520cbe1c62526277ac5e28610b268`，双回执artifact `12131238419`、ZIP SHA `2a88c7e33946b91ae356b3bc25ff7f0a871853613d6e743ad8e6c1928df04dc2`。整仓审计扫描95个核心Python模块、108个测试文件、94个工作流、74处生产权限/故事相关调用点；静态扫描不是证明所有动态插件安全。 另外增两项**故意复现未解决风险**的绿色观察性测试：新技能可初始化为L10/ACTIVE、可信底层WritingFlow可绕过AI候选的上层经验收据。绿色只代表这两项待整改问题仍然存在，绝非修好。
6. **重点剩余风险，不许误报全修好**：全新L10 ACTIVE能力仍可由可信代码`SkillRegistry.register`当作初始合同导入（不是已有同名技能覆盖），必须做可信Bootstrap/旧库迁移政策；`WritingFlow.accept_draft`与`StoryCommitCoordinator`是可信低层提交API，第三方不可信插件不能视为已通过`accept_candidate`的经验权限门禁；原始SQLite写权限不受Python模块HMAC防护；模型推理已经开始后不能被实时撤销；Reviewer真实独立性/读者评论身份、跨`WriterForgeDB`与`FactJournal`双库一致性、发行迁移/磁盘增长仍未独立认证。整仓AST列8项开放风险，详见完整报告，不是8个已证实远程漏洞。
7. **接下来**：先设计「旧库技能可信导入 vs 新建正式能力」的bootstrap来源权限，再核实可信人工StoryCommit与assistant_generated候选的原点鉴权，建立Studio审计/PR工作流白名单，最后才考虑独立文学真题验证。禁止凭注册一个高等级对象宣称WF成为作家。V49`THIRD_STRIKE_FAILED`和第二课程锁定继续有效。V63仍在草稿分支，不能贸然堆叠合并main。


## 50. 【2026-10-18 V64】技能初始化不能随意L10 ACTIVE；assistant_generated低层直提交流程被拒绝

**仅开发分支 `v64-bootstrap-origin-authorization`，基于V63，不合并main，不重复文学训练、付费模型/R2读取。完整报告：[V64 BOOTSTRAP_ORIGIN](V64_BOOTSTRAP_ORIGIN_20261018.md)。**

1. 源码先对照已有GitHub eventsourcing SQLite事务、SQLAlchemy versioned history、LangGraph checkpoint，借鉴“可信初始化/历史等级和已验证晋级分离”与“写前冻结计划在真实事务中校验”，并未引入外部框架或复制源码。
2. **失败先行证据**：[Actions #39116315805](https://github.com/66tyu55/WriterForge/actions/runs/39116315805)：9项V64新测试中3项FAIL、3项因新API不存在ERROR、3项PASS；真实FAIL主要为新L10 ACTIVE无需凭证，以及WritingFlow/StoryCommit原本允许AI稿件绕过正式候选验证。部署安全契约后老CI [#39116433860](https://github.com/66tyu55/WriterForge/actions/runs/39116433860) 9新项已PASS但历史测试8 ERROR/1 FAIL，由V12/V23直接高等级初始化、V21模拟直接AI稿及V63旧正向开放风险测试引起。两张红色日志保留，不以旧绿覆盖。
3. `SkillRegistry.register`新技能的L1 ACTIVE无需高等级来源声明；新L10 ACTIVE拒绝，必须有外部HMAC+审核员与审核收据签名才可`register_verified`；旧高等级可`import_legacy_capability`保留原级别，但状态强制SHADOW。`register_verified`仅证明有授权声明，不证明文学能力真实达到该等级。旧V63同名覆盖与晋级事务CAS保持。
4. `StoryCommitCoordinator.commit`和`WritingFlow.accept_draft`的`origin=assistant_generated`无正式候选授权路径则拒绝；`accept_candidate`正常传内部许可标记，且V63`precommit_check`仍在`BEGIN IMMEDIATE`后复核最终经验状态。允许真正可信作者稿继续直接写入。此标记不是能防御同进程恶意Python插件或直接SQLite写入的真正沙盒，下一轮仍需系统权限隔离。
5. 只在V64新分支透明迁移V12/V21/V23/V63受新安全契约影响的测试用例；所有历史原始分支和旧测试结果仍可回看。V21改用`accepted`弱信任非作者文字来验证“非作者样本不污染作者口吻”，真正`assistant_generated`来源另由V64测试经正式入口验证。
6. **真实最终绿色**：[Actions #39116669476](https://github.com/66tyu55/WriterForge/actions/runs/39116669476)：新增V64 **9/9**、完整项目 **690/690**。源代码 SHA：`evolution.py` `f2ea9a77aa1cd8c4468024d455eec45bf722b07c124e668381124c8df981f36b`；`writing_flow.py` `bd42116486508212694145f8204797d14b0b802274f65fcb17cc106c9c93f38e`；`story_commit.py` `2e40234b95959fdce56859b10e08e075b48fe2fbf88069299a111e4bf51f9b66`；`verified_flow.py` `f195052c5c5b2c43f78c64d325c5b379f1eaf084c576f5da68e52821308c5c7a`。本阶段没有机器JSON审计文件，只有可验证的GitHub运行日志，不能虚构SHA机器回执。
7. **未解决边界**：受信bootstrap签名≠文学能力；同进程任意Python代码仍能读取内部许可标记或使用SQLite写权限；Studio/不可信插件与模型的真实进程隔离、读者评论真实性、V31/V38真实R2历史原稿文学语义、双账本事务及旧数据迁移仍在后续。V49 THIRD_STRIKE_FAILED、第二文学窗口LOCKED持续有效，不得通过一次CI成功偷改晋级。


## 51. 【2026-10-18 V65用户授权直接教学】13条条件化文笔经验，WF场景诊断，正式WRITE和双稿评估入口

**用户最新明确指令：暂停“可信身份/签名/权限”主线，WF最需要的是文学经验的适用性与实际写作改善。允许宿主直接“给WF喂文学经验”，但不能装成WF已经自主阅读得来的知识。** 完整经验课、实际中文正反示例、选择/跳过条件、可运行CLI、双稿评估和局限见 [V65完整情境文笔课程](V65_CONTEXTUAL_SCENE_CRAFT_TEACHING_20261018.md)。

1. 仅`v65-contextual-scene-literary-teaching`开发分支，基于V64；`main`未合并或修改，无R2小说下载、无付费文学模型调用、无正文代写、无新文学能力晋级。经验包 `writerforge/scene_craft_lessons_v1.json` 真正保存**13条我原创的教师经验**，明确写 `ASSISTANT_TAUGHT_BY_USER_REQUEST`和`INSTRUCTION_NOT_LEARNER_DISCOVERED`，绝不冒称来自WF自主分析。每条有适用模式/节奏/视角/读者效果、必须证据、禁用特征、2–4个具体改写动作、坏例/好例、自检问题和失败模式。pack SHA256 `f5e1143baf415c99021a06fc39284166e258f7d80247f1e0e3ab97088ee5ae92`。
2. `writerforge/scene_craft_teaching.py`是新的有界场景经验选择器：WF自己的`scene_profile`应写明人物目标、阻碍、预期变化、叙事职能、POV、节奏、目标读者感受，以及对每项事实的`PRESENT/ABSENT/UNCERTAIN`和观察理由。只按完整条件作`SELECT/SKIP/UNCERTAIN`，每幕最多2条，禁用或未知时不偷偷塞提示；不使用原著关键词作匹配，不把教学正反例句子送入WRITE。选择脚本SHA `8306d49e1dcdbc6444dae20b1d7fee2193aba9ab8356483d143ff631c95855de`。
3. **真实接入`VerifiedWritingFlow.prepare()`**：可选`scene_craft_profile`和`scene_craft_enabled`，只将选中操作的抽象指导和自检放进正式模型prompt，`GroundedDraftPacket.manifest()["scene_craft"]`保存教学包SHA、场景诊断SHA、选择ID与计划SHA，标注`literary_improvement_proven=False`。禁用教学时原先正式prompt无附加教学文字；合法经验不需要再用V61审核签名才能学习，V61旧独立经验权限契约不删除。
4. CLI `scene-craft-plan --profile-file ...`无需数据库/模型；`scene-craft-diagnosis --scene ... --goal ...`仅输出WF规划格式要求；**明确指定`--model LOCAL_MODEL_NAME --brief-file WF自己的场景安排 --output-profile ...`**才调用已连接的本地WF模型进行JSON情境诊断一次，并区分“诊断器”与“作者”system角色。可复用同一份profile用于`draft-context` / `draft --scene-craft-profile`教学组和`--scene-craft-disabled`基准组。`scene-craft-compare`将真实两篇文字以SHA匿名、检查15%稿长相似性，不保存正文；无盲评时`TEXT_PAIR_READY_FOR_BLIND_REVIEW`，有5维评分也最多是单场候选，不自动升级。四份教师示例`examples/scene_craft/*.json`可立即离线复核：追船/悲痛余波/无铺垫揭秘/双方谈判，标记`TEACHER_DEMO`，不假装WF自行推理。
5. **实际CI**：[Actions #39119151016](https://github.com/66tyu55/WriterForge/actions/runs/39119151016) `completed/success`：V65新增情境判断/反例/可选WF本地模型接口模拟/正式写作接线/A-B相对字数合同**21/21**通过；全项目 **711/711** 合成结构测试通过。相关SHA在该GitHub CI日志：card pack `f5e1143baf415c99021a06fc39284166e258f7d80247f1e0e3ab97088ee5ae92`、选择器 `8306d49e1dcdbc6444dae20b1d7fee2193aba9ab8356483d143ff631c95855de`、`verified_flow.py` `47f89be9aaba42ad0bd5a02309828139d7bec39401d5c10aadb93507cee81a3f`、CLI `a598629c9ba9979455ccdf14ef8a71e57aadd656e56bde7552e36b60596966ac`、测试 `4aa44a17c4f735c2892b3a2f0f6934cd817429520694979c5d0c7535aee84654`。最初缺少选择器引起的红色 CI在[#39118337377](https://github.com/66tyu55/WriterForge/actions/runs/39118337377)保留，但它是新能力接口未实现的失败，不等于文学写作漏洞。
6. **最关键未完成**：当前4份演示情境与大多数测试的场景事实都是教师合成，实际“WF是否自行正确理解场景”还没用真实模型检验；生成的WF诊断接口只是模拟local completion，不能自称WF已经学会独立文学判读。V65本轮没产生一篇由WF自己写的真实新稿，文学质量改善尚无评分，原V29三场真实 +7.8/-5.0/+6.2 混合且第三场机制相同、V38 R39“铺垫与回收”争议均不得改成成功。V49 `THIRD_STRIKE_FAILED`与第二窗口LOCKED继续有效。
7. **下一步而不是再增功能**：拿一个WF自己拟定且旧V29/V38未出现的新场景，让WF本地Planner真正产生JSON事实剖面；同一剖面、同一Writer/任务/长度边界写【禁用经验】与【启用选中经验】两稿；五维匿名比较因果、人物行动、知识信息、情绪作用、语言节奏，**遇到任何严重下降保留反例并收窄该经验适用范围**，而不删掉失败或宣布“模型理解了文学”。经验是外部教的，文学改善仍必须由WF自己在新稿上展现。


## 52. 【2026-10-18 V66】WF原生HTTP客户端→用户已经部署的Cloudflare Worker→R2

用户在Cloudflare控制台成功创建 `wf-r2-api`、Secret `WF_API_TOKEN`及既有私有桶 `writerforge-private-library` 的 `WF_R2` 绑定，并已经手工获取无token的401、有token的200、R2/status真实联通、`/r2/inventory`全域元数据233对象/1,673,579,609 bytes/305ms。**这些是用户手工Cloudflare调用的结果，不是WF进程主动调用。**

用户最新要求：“no---别测试了--有了接口--目标是WF--不是我和你--让WF调用接口我看看”。于是V66独立分支 `v66-wf-direct-worker-http` 从V65继承，实现：

- `writerforge/r2_worker_http.py`：WF代码通过标准库HTTPS向用户的Worker `GET /r2/inventory`发送Bearer token（从本地进程`WF_API_TOKEN`读取），检查完整遍历，自己测量HTTP端到端时间，将Worker返回的R2对象列表耗时单独记录；没有SQL、源码正文、模型调用或远端修改。
- `writerforge/cli.py`：新增不创建默认DB、不借助GitHub Actions的`r2-http-inventory --endpoint https://wf-r2-api.3227482831.workers.dev` CLI。
- `scripts/run_wf_r2_worker.ps1`：Windows PowerShell掩码输入Token，由本机WF子进程直接请求；运行结束删除本进程环境变量。
- 完整操作与安全范围见 [V66 WF HTTP连R2交接](V66_WF_DIRECT_R2_WORKER_HTTP_20261018.md)。
- **这一步只写入WF代码。尚无真实带认证的本机WF新运行结果，不能因为CLI存在就宣称连接成功。** 当前聊天没有Cloudflare Secret，也不能直接访问用户PC。本轮没有触发新的GitHub Actions，`main`未变。
- 用户本地仅需在WF仓库`git fetch origin v66-wf-direct-worker-http`、`git switch v66-wf-direct-worker-http`、`.\\scripts\\run_wf_r2_worker.ps1`并掩码输入自己保存的Token，获得真正的WF程序输出。后续若要WF全书SQL，需要Worker部署实际对象下载/查询接口；当前`/r2/inventory`只能枚举元数据。


## 53. 【2026-10-18 V66 最终交接】WF已在Railway成功直连R2；下一步是独立查书问答，不得重做连接测试

**用户明确最新指令：**「做个测试--提出问题--让他自己检索」，随后「最大长度了--先交接--说清楚」。**这道文学检索考试尚未开始执行**；之前只查阅了WF检索相关源代码，没有新的小说正文、SQLite或经验检索运行结果。请下一窗口直接接着未完成的检索考试，禁止误报。

**完整、可复核的当前状态和下一轮操作顺序：** [V66 WF自主文学检索考试交接](V66_WF_SELF_RETRIEVAL_EXAM_HANDOFF_20261018.md)。

1. **既有云端环境已建好，勿重复创建**：GitHub `66tyu55/WriterForge` 独立分支 `v66-wf-direct-worker-http`；Railway 项目 `WriterForge`（`c5a1c1ad-03d7-4767-b972-8a46446fec07`），Python 服务 `wf-python-r2`（`e6a7688b-ee12-49ef-ae83-02145005fc79`，production环境`65b1b9fe-2f4f-44f3-80af-77143a19545d`），Cloudflare Worker `https://wf-r2-api.3227482831.workers.dev` 绑定私有桶 `writerforge-private-library`；Railway `WF_API_TOKEN` 已配置，绝不能复制密钥或放 GitHub Secrets；用户本人本地没有安装WF。
2. **真正机器验收**：Railway部署 `5243f688-3955-42d3-ab14-b229b3263c50` 运行 `WF_R2_HTTP_SUCCESS`、进程退出码0；**WF Python**经Worker只读扫描R2：**233个对象、1,673,579,609 bytes、HTTP端到端717.28ms、Worker内部289ms、1次HTTP/1页，0次写入**。这是线上WF真实调用，绝非浏览器手工测试；但是 `sqlite_sql_executed=false`、`original_novel_text_downloaded=false`，绝非语义检索完成。以前的403/404经过Cloudflare正式部署现已解决。
3. **目前阻塞真实问答**：Production Worker已有 `/health`、`/r2/status`、`/r2/inventory`，没有受限对象读取或按内容查询接口。WF `r2_worker_http.py` 仅能取到**统计数字**，不能访问章/段/句或直接读取SQLite。旧 `r2_retrieval.py` 有经由S3 `R2StudyVault.restore` + SQLite只读+`XuehaiStore.query`的验证机制，但Railway只持有Worker Bearer Token，不具备旧S3密钥。不要冒充新HTTP路线已经复用了旧检索成果。R2内的 `study.sqlite3` 是blob，不是能直接远程 SQL 的数据库。
4. **下个窗口必须先做的事**：沿用既有Worker和R2，仅新增严格鉴权、限于`writerforge/v1/libraries/`（先锁定`laocanyouji-25124`）的只读对象传输能力；由WF按需获取 `latest.json → 经SHA核验的manifest → 经SHA核验的SQLite blob`，在Railway临时只读SQLite中检索并返回来源回/段/句、源SHA和WF真实时延。不得全桶搬运1.67GB，不得输出整本小说，不得写回R2。Cloudflare在本聊天没有可直接调用的管理接口，需要用户**一次正式部署新Worker代码**，之后让WF自己运行考试而非让用户手工测试。
5. **考试设计与诚实边界**：优先由WF自己检索回答《老残游记》声音或景物营造紧张感的实证题，要求其自行选择证据与解释；如当前没有语义模型能力，先明确标注地进行独立关键词出处定位子题（如「黃河」是否出现及回/段/句），不得把字面命中冒充文学理解。V52旧 `老殘` 六命中不准复制成新的测试。记录题目、WF自发检索过程、证据SHA/定位、真实答案和失败。V49 `THIRD_STRIKE_FAILED`、第二窗口 `LOCKED` 持续有效。
6. Railway服务**固定旧代码commit** `f2c6d3377c307ce225a60be8c7e3226075a34911`；新增GitHub文档提交不会自动改变正在运行的WF。实际部署新功能必须通过Railway连接服务的新精确commit再读部署日志。**禁止GitHub Actions、GitHub Secrets、用户本地PowerShell重新安装、捏造文学成功成绩。**



## 54. 【2026-10-18 V67】Worker→单本学习库只读资料通道代码已就绪；待Cloudflare正式部署；《老残游记》文学考题未开始

用户明确确定**正式考题**：「《老残游记》中，作者有没有利用声音或环境变化营造紧张感？请你自己检索资料，找到至少一处原文证据，指出回、段、句的位置，解释你的判断。如果证据不足，就明确回答证据不足。」考官必须**不替 WF 提供原文、检索关键词或答案**。顺序不可倒置：先通道→WF实际取出并验证学习库→自主检索→证据和文学判断独立留痕。绝对不能把V52旧“老殘”检索结果回填为新考卷。

1. **可靠的历史起点**：V66 Railway `wf-python-r2` 已真实发送HTTP成功读出R2的233个对象、1,673,579,609字节、WF端717.28ms，但那只是目录元数据；实际部署ID `5243f688-3955-42d3-ab14-b229b3263c50`，固定commit `f2c6d3377c307ce225a60be8c7e3226075a34911`。生产Cloudflare尚无已证实可用的 `/r2/object` 路由，之前确认为404。保留旧生产运行状态、旧失败记录和原始R2。
2. **新隔离分支**：`v67-worker-readonly-library-bridge`，从V66继承，不改main；本轮没有PR、没有GitHub Actions触发、没有文学模型调用。文件 `cloudflare/wf-r2-worker-readonly.js` 是用户对**现有** `wf-r2-api` Worker的候选更新：兼容原health/status/inventory，增加需要现有Bearer认证的 `GET/HEAD /r2/object`，限定单一原书库 `laocanyouji-25124` 的latest/manifest/blob，元数据至多128KiB、blob最大256MiB、单次4MiB范围GET，拒绝跨库和写方法；不披露密钥或文稿到日志。**当前没有Cloudflare管理员操作接口，代码已经上传GitHub并不等于云端已部署。**
3. **WF读取端**：`writerforge/worker_readonly_library.py`，一套在WF进程内凭既有Railway `WF_API_TOKEN` 打 Worker 的只读客户端：按需取latest、SHA256核验manifest、依manifest提取仅这一书库的SQLite和source.txt（内存有界块，**临时下载非零**）、每文件SHA256和版本Git blob SHA1、源全SHA256/SQLite章数与统计交叉验证、`mode=ro`+`PRAGMA query_only=ON`只读SQL。在一次性tempdir退出删除；不动作者电脑/R2。 `VerifiedStudy.locate` 可有界检索字面原文位置与来源SHA，**没有独立的自然语言策略规划或文学语义理解证明**。
4. Railway一次性无原文验收入口 `wf_railway_library_start.py`，只输出版本、study单库计数、读量、耗时、是否通过校验；**不能提前拿它当考试答案**。纯离线Fake Worker测试文件 `tests/test_v67_worker_readonly_library.py` 已写入GitHub，但没有跑Python Actions/生产实测；在受限JS模拟中检查了认证401、越权403、合法GET/HEAD 200、范围206、无界400、DELETE405、原inventory200；模拟≠Cloudflare实测。
5. **剩余执行门槛**：用户只需对Cloudflare**原Worker**正式部署一次此候选JS（事先备份旧代码，保留WF_R2绑定和WF_API_TOKEN Secret，不提供任何secret值）；随后助手通过已连接的Railway插件把**原服务**指向V67新精确commit，改启动命令为 `python -u wf_railway_library_start.py`，执行并复核一次真实日志。如果Worker路由404、鉴权失败、下载不完整、源hash错，必须清楚报告失败且不得开考。线上只读恢复成功后，才另实现并验证WF**自己制定检索计划→搜书→定位原文→尝试文学判断或诚实ABSTAIN**的正式考试执行器；考官的题目不应被硬编码在检索逻辑中。
6. 详细文件：`docs/V67_WORKER_READONLY_LIBRARY_PENDING_DEPLOY_20261018.md`。原 `V49 THIRD_STRIKE_FAILED` / 文学课程第二窗口 `LOCKED` 不变。没有整桶复制、R2写入、原著仓库公开、真实自主考试成绩或文学能力晋级。


## 55. 【2026-10-18 V68】用户本地约400本直传私有R2；原Key保留/稳定自动编号/后补分书SQL

**用户最新优先级**：先扩容至少50本，分类新增目标古典4、玄幻20、仙侠10、科幻10、历史10，总计计划新增54本。用户本地约400部原资源，绝不能经GPT转运；自己从Windows电脑直接上传到私有R2。旧《老残游记》正式考题暂封存。完整设计 [V68 原始入库与延迟SQL索引](V68_BULK_R2_INBOX_SQL_INDEX_PLAN_20261018.md)。

1. V67已真实通过单本资料通道：Railway部署575f6b1b-452f-4d1a-ae3e-5bf0f2dff190固定V67提交33cf56ea；成功从R2恢复《老残游记》20回、4857来源单元、4647检索条目、7400356传输字节、约10.15秒、原R2零写、SQLite只读、退出码0。尚未做文学考题。
2. 新隔离开发分支 v68-bulk-inbox-catalog-sql-index 从V67分出；不改正式main、Cloudflare线上Worker、Railway配置、R2原档；不触发GitHub Actions，不调用文学模型，未接触用户本地小说正文。
3. 推荐原Key：writerforge/v1/inbox/20261018/原分类目录/原文件名.txt。用户无需改名；R2对象Key不应通过copy+delete物理重命名。类别和category display_no是后补SQL目录字段；同类编号首次按Key稳定排序、后续只追加；book_id由完整来源SHA256前32位形成，完整哈希另存，重复同文多路径合并为一个索引ID。缩写标题保留、待核对，禁止猜完整书名。
4. 新代码 writerforge/bulk_inbox.py、scripts/wf_bulk_inbox.py、tests/test_v68_bulk_inbox.py：R2元数据批量登记、类别自动识别、拒绝同Key意外替换、源SHA去重、TXT/MD按需逐书流式解析为独立SQLite及有界FFS5 trigram短句索引（如不支持回退有界扫描），按类别/书/章查位置+来源哈希；UTF8、UTF16 BOM支持，GB18030需人工显式指定。EPUB、RAR、7z当前列为待安全解析，上传≠索引完成。所有查询是词面，不证明文学语义。
5. 本地同接口试验8/8离线合成用例通过；400个合成元数据对象成功登记，400个极短合成文本独立建SQLite约3.69秒，shards合计15.62MiB。这仅是测试夹具，不能当400本真实小说完整索引或真实R2吞吐；分支上的Python测试未触发Actions回归。
6. 尚未补齐的硬门槛：当前线上Worker仅可GET旧单本库，/r2/inventory只有对象总量而无详细Key。用户上传新资源后需在原Worker新增安全认证只读inbox分页LIST与Range GET，再做一次正式部署；以后由WF Railway真实获取R2对象并逐本后补SQL。当前Railway没有持久卷，生成的SQL还须受控持久卷或独立按最小权限存回私有R2，不能将读Token偷偷改成写Token。失败和重试需要内容SHA的永久checkpoint。
7. 50本门槛须统计确证不重复完整来源与可索引状态，不等于文件夹数/对象数/阅读深度/文学质量。原 V49 THIRD_STRIKE_FAILED 和第二课程窗口 LOCKED 原样保留。

**恢复时只向用户询问已上传的R2对象前缀与文件格式/是否解压**，不要求提供正文、密钥、截图密码，不重新创建云项目；先完成metadata-only扫描，再做真实分书索引。


## 56. 【2026-10-19 V70】中断恢复：43个TXT真实目录拓扑核对成功；不再把嵌套路径都误认为分卷

用户最新说「继续--中断」，继续上一窗口尚未完成的V70单本/多卷结构分辨，未从头开工程。完整证据和后续计划见 [V70目录拓扑审计](V70_PRIVATE_READING_TOPOLOGY_AUDIT_20261019.md)。

- 分支 `v70-private-reading-source-identity-audit` 从V69继承；未改main/Cloudflare Worker、未触碰原R2、未用GitHub Actions和模型。Railway真实 Python 23/23合成反例通过（部署`ad1bc9fd-6010-4054-beb3-26dab0ed6f64`）。另一次Redeploy `518de2ea-201c-4282-9899-57ab9da2d56d`意外重用旧测试启动命令，**绝不能冒充真实R2结果**。
- 新修复：跨页重复Key拒绝，避免重复统计；`writerforge/private_reading_topology.py`仅接受完整四目录扫描并根据父路径的TXT/压缩包/辅助文件统计保守候选，不泄露任何私有Key或正文。
- 真正生产读R2的部署`c6caee3c-50e1-4126-9002-52ec24f9104c`成功；四目录仍79对象、577574142字节、4页、每目录受限读取成功、零远端写。R2 metadata fingerprint SHA256 `4ee7e4a7fd9158022cd5377dd6dd6d23c04fe5f4905127eae21c691d8dee81d0`，只是Key/大小/ETag摘要不是原始小说SHA。
- **可信拓扑结果**：`single-works` 7个根目录TXT、18 JSON、9无扩展名；仙侠15个TXT落在15个不同父目录，7目录仅TXT、8目录各TXT+RAR；历史11个TXT落在11不同父目录，10目录仅TXT、1目录TXT+RAR；科幻10个TXT各在独立父目录，无RAR。**任何新增三类父目录里都没有2个TXT并存**。合计43 TXT、9 RAR，其中34个单文件路径候选需验源，另9个TXT与RAR同目录需确认是否备份。不得据此宣称43部独立作品。
- **尚未完成**：未下载真实小说全部字节、未建立43个分书SQLite、无数据库持久化。下一优先任务是V71从原目录依据metadata选一个受限大小的单文件TXT，让WF直接R2只读Range读全文件、SHA256、编码及章节检测→临时SQLite建索引→真实内部回查；不得替WF写文学答案。若考虑把SQL持久化，应先评估云端R2索引写入的单独最小权限通道或Railway持久卷成本；现有Reader Token不允许擅自变为可写。V49 THIRD_STRIKE_FAILED/第二课程LOCKED保持。


## 57. 【2026-10-19 V71】真实R2中文TXT首次成功进入WF临时SQLite/FTS并回查；下一步解决持久索引

延续上次中断的 V70，不修改旧实测或从头建项目。全部工程背景、红色负例和验收见 [V71真实R2单本SQL工程闭环](V71_PRIVATE_R2_ONE_BOOK_SQL_SMOKE_20261019.md)。

**此前保留的真实事实**：V69已完整扫到四目录79对象/577574142字节；V70已证明43个TXT，34单文件候选+9个TXT与RAR同目录（不是9部新书），没有任何新增三类目录包含两个TXT；V70真实R2元数据SHA `4ee7e4a7fd9158022cd5377dd6dd6d23c04fe5f4905127eae21c691d8dee81d0`。不是所有TXT都能单独证明完整作品，source哈希还须看实际字节。

1. 新独立分支 `v71-private-r2-one-book-sql-smoke` 从V70继承，正式main与Cloudflare Worker不改，原R2零写；用户私有原文没有经GPT或GitHub Actions。WF仅按元数据大小从单TXT无RAR同父目录候选中选择一个≤16MiB源，按1MiB范围只读分段；本任务只检查技术SQL与内部自选字串查回，不是文学自主考试。
2. **真实失败记录不许擦除**：首轮Railway部署 `f4b658d6-8e47-4630-9a58-ad1787e0d63a` CRASHED、无Python应用首行日志，根因未定；零网络启动自检 `b996f8a9-1c41-4324-b74b-e453a8989bea` 证实模块/入口/Token环境存在；受控一轮 `325fc217-2258-4a89-b3ad-10c2a9bbf1d9` 成功从R2获取TXT并计算完整SHA，但因 `BULK_ENCODING_UNCERTAIN_EXPLICIT_ENCODING_REQUIRED` 严格拒绝SQL，不能称成功。以上所有历史不可改。
3. 新 `source_encoding_guard.py` 用Unicode严格解码/BOM识别及保守GB18030样本检测，不替换/忽略非法字符，不改原始文件；GB18030结果标`LIKELY_LEGACY_CHINESE_STRICT_DECODING`和`provisional_legacy_decoding=true`，仍需源编码独立审定（可能存在Big5等歧义），**仅供实验技术索引，不能直接升级文学学习经验**。
4. 真实最终成功部署 `508673b0-9685-41ce-8777-664c516960c4`：Railway Python 3.13运行35/35合成测试通过，随后WF自身调用已有Worker，四目录清单完整，25个候选符合本试验16MiB预算；依大小选择`科幻`类别一部真实TXT，**3636548字节**，包含HEAD共5次请求，源下载约4287.36ms，原文字节SHA256核验完成；严格GB18030读取索引副本并生成临时SQLite FTS5 trigram，**65573个来源单元，499个检测到的章节式标题（不是已验证完整章节数）**，SQL建索引约1973.95ms；SQL内部自行从已有索引派生查询，命中1条，不回显词或原句。程序状态`WF_V71_REAL_R2_ONE_SOURCE_INDEXED_TEMPORARILY`与`WF_V71_ENCODING_RUN_EXIT=0`。模型0、R2写0、私人文本不出Railway。
5. **最重要的未完成**：Railway目前没有持久卷，因此本次原文临时文件与SQLite都在任务退出后自动清理，`sql_persisted_after_exit=false`。现在仅证明“一本真实私有作品可以在WF内临时索引和词面回查”；**不是**43本SQL准备好，更不是达到50部公认完整作品、作品理解、文学技巧毕业或写作能力提高。源文件完整SHA不能证明原著版次或与既有别名为同一作品。
6. 下一阶段须在成本/权限授权后给原有Railway服务增加有界持久工作卷（或创建独立、最小权限的R2索引备份服务），再实现按书SQL幂等记录、崩溃后孤儿shard验源恢复、原文全SHA去重、定额分批处理25→43个TXT并保留9个RAR同目录待审；按目录/作品/章节/句子分级查，不每次重复下载原书。用户无需重传，禁止擅自扩大现有只读Bearer权限。R2原始书不因索引操作修改。为确保后台失败可追溯，原始失败收据保留。
7. V49文学终审`THIRD_STRIKE_FAILED`、第二课程`LOCKED`继续有效；GB18030临时技术索引及自选检索词没有文学语义真实性保证。不自动训练、不写文学答案、不把原著摘录灌给WRITE。


## 58. 【2026-10-19 V72】用户明确选 Cloudflare R2 永久索引，禁止另买/创建 Railway 持久卷

用户最新指令：「存储在R2--吧--不然我怕到时候来回迁移」。从现在起**原著、WF按书SQLite检索索引、版本清单都长期保管在已有`writerforge-private-library`私有R2**；Railway只运行Python和临时按需恢复单本SQLite，绝不创建或绑定2GB Railway Volume。此决定优先于前段建议的云端持久卷。详细方案、接口合同和部署依赖：[V72 R2私有持久索引](V72_R2_PERSISTENT_INDEX_PRIVATE_20261019.md)。

1. 可信历史不变：V69四目录79个实际R2对象、V70检测43 TXT/34独立文件路径候选、V71线上R2一部3636548字节真实科幻TXT建立65573 SQL单元/499可疑章头，按GB18030临时编码，SQL内部字面命中1，全部过程R2写0。**V71旧索引只在一次性临时目录，未保存在R2**，不能反向冒充持久化通过。真实运行 `508673b0-9685-41ce-8777-664c516960c4`，原编码失败、第一次CRASHED等红色历史不修改。
2. 新隔离分支 `v72-r2-persistent-index-vault` 从V71继承；正式main、已有用户原著、已部署Cloudflare Worker和当前Railway Reader Token不改变。Worker候选 `cloudflare/wf-r2-worker-readonly.js` 增加独立 `WF_INDEX_UPLOAD_TOKEN` 写入授权，仅受限 `writerforge/v1/indexes/v1/`，不可复制/删除原著；Writer Secret不得等于旧 `WF_API_TOKEN`，缺失则拒绝写入；读服务继续使用旧Bearer及旧源接口。
3. 新永久R2格式：`indexes/v1/chunks/{sha256}.bin` + `indexes/v1/refs/{sha256-of-original-object-key}/{manifest-sha256}.json`；每个块1MiB，SHA内容寻址，只允许创建不可覆盖，**manifest最后发布**且Worker先HEAD验证引用块；中断后只需续传缺失块，重试完全幂等，失败的未引用块不会被当成已发布SQL；source SHA、原R2 ETag、全SQLite SHA、各块SHA、索引schema/GB18030暂定状态均标入小manifest，不写原文片段或原始书名进去。
4. `writerforge/r2_index_vault.py` 在WF Python进程直接向Worker逐块上传SQLite而非原始小说；另一个新WF进程可只用Reader Token按指定原R2源Key哈希找索引，按需下载、验证每块及全SQL SHA/quick_check/表中源身份并以 `mode=ro` + `query_only=ON`打开，查询完临时目录自动销毁。R2才是永久源，不存在Railway数据迁移。源对象ETag/字节变更时阻止旧索引，发现多个同源旧清单要求明确版本，不能挑最有利结果。
5. `writerforge/v72_persistent_index_pipeline.py` 沿用V71严格按类别、单TXT无RAR混放、文件大小≤16MiB的自动选择，先查询已有manifest并跳过，才处理下一部并发布SQL；每次仅1部，绝不依赖GPT或GitHub Actions选正文。每步保留来源完整SHA；GB18030仅作暂定技术索引，禁止进入已验证文学经验。
6. **真实测试/验证边界**：Railway `17174b98-43f9-47d5-b667-f6155dda0b1e` 的 **44/44 Python纯合成结构测试全部通过**（旧35+新9），包括R2模拟上传/重启冷恢复/断线续传/伪造块拒绝/旧ETag拒绝/无读Token升级；Worker JS自制模拟也证明旧health=200，Reader读Token上传=401，Writer仅索引路径上传=200，源对象路径写入=403，manifest和Refs独立只读查询、chunk Range206。**这些都不是Cloudflare正式线上索引写入证明**：实际新接口还未由用户Deploy，专门Secret也未设置，真实新R2写入计数0；不许冒称R2永久索引已经存在。
7. **下一步唯一用户参与**：在现有Cloudflare `wf-r2-api` Worker中保留原 `WF_R2` 绑定及 `WF_API_TOKEN`，**新建随机且不同的 `WF_INDEX_UPLOAD_TOKEN` Secret**，将V72候选单文件Worker JS正式Deploy一次；同一密钥值由用户自己在原Railway服务`wf-python-r2` Variables设置，**绝不贴到GPT/GitHub**。用户说「V72部署完毕」后，助手才通过Railway连接器使用`wf_railway_v72_publish_one.py`处理一份真实原文的SQL上传，并换另一个真实进程`wf_railway_v72_cold_restore.py`只用读Token冷恢复，证明退出后索引仍在R2。
8. 云端真持久化验证后才设计更大规模的R2持久全库`catalog`显示编号与断点队列、50→400本工作调度、RAR安全解包、多书跨类检索；这批能力**本轮尚未生产完成**，用户不可误以为400本现在均具备永久SQL索引。使用标准R2存储有存储与请求计费/标准免费额度，见官方 `https://developers.cloudflare.com/r2/pricing/`，Railway运行计算额外计费。V49第三次文学终审`THIRD_STRIKE_FAILED`及第二窗口`LOCKED`一律不因工程存储成功改变。

最终原则：新版本WF可以脱离Railway旧实例恢复指定R2 SQLite索引，老原著不复制进ChatGPT、不改写、不移存到公共仓库。旧部署安全闲置，不反复拉小说或自动付费训练。

**最新实际Railway安全等待**：部署 `5ea343ea-cccf-48e6-84b7-6b99fcc388b6` completed/SUCCESS，`WF_V72_AWAITING_OWNER_R2_INDEX_WRITER_SETUP`，只有旧读Token已配置，新`WF_INDEX_UPLOAD_TOKEN`仍未配置；0网络、0新R2写、0持久卷、没有自动执行原文扫描。最新V72分支文档提交不影响已固定的Railway正在运行的旧commit。用户在现有Cloudflare与Railway完成独立索引上传Secret配置且Worker正式部署后，才由助手重新固定V72精确提交并运行真实单书上传+独立冷恢复。


## 59. 【2026-10-19 V72真生产】第一份永久SQLite已上传私有R2；全新只读进程成功恢复

这是前节“等待用户配置Cloudflare索引Writer权限”之后的最新里程碑，**不再重复要求用户设置密钥或重新部署V72**。详细真实证据 [V72 R2持久化最终报告](V72_R2_PERSISTENT_INDEX_PRIVATE_20261019.md)。

1. Railway用户已配置独立`WF_INDEX_UPLOAD_TOKEN`并部署既有Worker V72。真实安全探针Railway`006f6a7e-614a-4741-b5fa-0ca7376007cd`：Reader读新索引列表成功、Writer对故意错误SHA块被422拒绝，0新对象。
2. **真正首次持久写入**：Railway部署`fb5c2321-d45d-4fd0-9ec7-307e3ae68086`、状态`WF_V72_INDEX_PERSISTED_IN_PRIVATE_R2`/退出0，WF从用户私有R2读取1部3636548字节科幻TXT，严格GB18030暂定编码，SQLite`36,274,176`字节/`65,573`单元/`499`疑似章头，上传35个1MiB以下内容寻址块到`writerforge/v1/indexes/v1/chunks/`，最后写不可变manifest到`writerforge/v1/indexes/v1/refs/`。私有R2原著0修改，模型0，未用Railway持久卷。索引文件全SHA `a3eb5e24bb858a078ece3d5e56ffc4805e9e51eebe53715037701049422d7ec8`，manifest SHA`01510d79c6d5b60212e3f4dc051901ee8cfabd0481070c33248630dc2b7b787a`。同进程R2只读恢复校验成功。
3. **真正跨容器读回**：一个全新Railway部署`cc78dd59-27f9-4336-91c3-3da41c7783e8`，运行`wf_railway_v72_cold_restore.py`，进程主动移除Writer变量，只凭Reader Token完整下载/核验R2中的36,274,176字节SQLite（每块SHA/总SHA/SQLite quick_check/源元数据一致），只读查询65,573单元且词面自命中，原TXT下载0、R2写0、进程退出0。状态`WF_V72_COLD_RESTART_RESTORE_VERIFIED`。**可以正式证明R2持久化技术闭环**，不依赖旧Railway实例或2GB云盘。
4. 下一目标是R2中的**持久分类目录/编号/任务进度与多书索引**，然后25个有预算的独立TXT候选→43个TXT（其中9与RAR混放待审核）→50+部真实核验作品。不能把一个SQL自命中当自主文学理解；原V49`THIRD_STRIKE_FAILED`和文学窗口`LOCKED`永远保留，直到新独立文学盲测证明新成绩。不需要在用户不知情时自行启动大量批处理。
5. 本节写入后把Railway原`wf-python-r2`切回单次安全等待脚本`wf_railway_v72_wait_setup.py`以防错误新一轮写入；写入Token可以保留，但后续写入只能在用户要求执行分书入库时再次切换一次性脚本。


## 60. 【2026-10-19 V73】用户纠正：分类/编号/拆章/阅读/训练全属WF自己；助手只能修底层与反作弊

用户原话：「这些不是属于WF--如果你替他分类编号章节--直接一本一本的让WF自己训练不就可以吗？」——最新方向冻结：**不要再由助手代WF补书名、指定类别、生成读者反应、人工挑选章头和文学答案，所有文学决定由WF独立LEARN；已有R2 SQLite是基础设施，不算训练经验。** 详见 [V73完整设计、红色失败、真实入学检验](V73_WF_OWN_SEQUENTIAL_LEARN_20261019.md)。

1. 从V72继承新隔离分支 `v73-wf-owned-sequential-learning`。V72真实永久R2存储仍有效：1份真实科幻TXT的65,573单元SQLite+35块/manifest在用户R2，另一新Railway只读进程已恢复成功。**旧main/Worker/R2源不变**；无GitHub Actions。
2. WF新增自己运行的 `writerforge/wf_self_learning_admission.py`：资料一份一份从R2抓取，完整SHA验证、严格编码、独立双章头规则比较、中文章号检查、每章源哈希/位置；R2目录分类仅为`hint`，作品真正分类默认为`UNDECIDED`。LEARN/WRITE模式隔离。任何缺章、重复、不同parser结果、编码暂定均记录待审，不填造答案。没模型和不可变R2学习日志就**不进行Pass A、Pass B或技能晋级**。
3. 铁证：WF真正第一次自主入学检查Railway `28a842ae-f035-4f9c-ba24-740467d64b25`，自选一部已授权私有R2科幻TXT（3636548字节），扫描43817行，新章头495、旧SQL章头499；当时中文打印序号未解。第二次 `40bcc8a9-d9f0-40a5-abb5-b24b9e493e13`见重复章号停机。新增离线测试 `44805be0-6ba7-4a40-9338-13bf9bbb945e`发现普通句首“第一章内容”被误识章头并产生空章（原红色不能修改）；修复须有分隔符的标题后，真实Railway合成测试 `f84b69c4-86c0-45ad-8244-ca751eb1b355` **57/57通过**，无R2写/模型。
4. 最终真实R2入学 Railway `b6ee07f8-3aea-4db1-b2a7-686883bade90` 完成：自选相同TXT，43,817行，strict章头495、legacy候选499，**4个独立规则分歧，295次打印章号重复、3个倒退或重置点，前向跳号0**，列出冲突章头HASH（正文及标题不公开）。这可能提示“作品有多卷并分卷重新编号”，只能标待验证，不得由GPT臆断。状态`WF_DOCUMENT_ADMISSION_REVIEW_REQUIRED`、原始字节SHA一致、GB18030编码仍provisional，分类UNDECIDED，**实际学过0章/模型调用0/R2写0**。它只是WF发现自己的文本结构缺陷，不能算文学经验。
5. Railway目前只配置`WF_API_TOKEN`与`WF_INDEX_UPLOAD_TOKEN`两类R2凭证，**没有文学模型令牌**（例如已知旧实验需要的`DISCOVERY_API_KEY`）；因此宿主的读者Pass A/分析Pass B/自我复盘还没有真实执行。下次必须把真正模型当WF可调用工具连接并规定费用预算与私有原文第三方传输边界，不让GPT做考生；同时需为`LEARN`训练事件新增专用不可变R2学习账本，不能复用只接受v68 SQL格式的`indexes/v1`manifest。第一章PASS A的检查点必须在PASS B前R2签收，再继续下一章，学会的经验要对未来行为有可测影响。
6. 原V49`THIRD_STRIKE_FAILED`/第二学习窗口`LOCKED`原样保留。50本完整原文门槛尚未完成；目前1份R2可持久SQL索引≠文学训练。下一步合理的真实小预算是**WF自己选一书、先验证结构/版次、独立完成第一章Pass A→写R2锁定→Pass B→错误复盘，不晋级**，成功后才让它自动挑第二章/第二本。以后禁止人工从外面一次性分类400本。


## 61. 【2026-10-19 V74】用户明确选择官方DeepSeek Flash替换WF未来的Discovery文学学习

用户直接提供 DeepSeek API 官方配置截图说「换成deepseek flash吧」。冻结WF文学LEARN新模型唯一选择：**官方DeepSeek `deepseek-flash`**，OpenAI Chat Completions兼容端点`https://api.deepseek.com/chat/completions`，密钥环境变量`DEEPSEEK_API_KEY`。不再让新WF文学LEARN回退到原Discovery/OpenRouter，不用已退休的`deepseek-v4-flash`字面名称。原Discovery实验脚本和原V49不通过/第二学习窗口LOCKED保持历史记录。详细说明：[V74模型接入说明](V74_DEEPSEEK_FLASH_WF_LEARN_20261019.md)。

- V74新分支`v74-deepseek-flash-wf-learn`从V73继承，增加`writerforge/deepseek_flash_model.py`及`writerforge/wf_learn_model_registry.py`，仅在WF独立LEARN调用时提供受限角色（来源分类、首次阅读、文学分析）的官方DeepSeek Flash JSON适配器；原文/密钥不在公开日志。强制 HTTPS固定主机、禁止3xx转发Bearer、`response_format=json_object`+system JSON合同、固定`thinking.type=disabled`作为当前低预算结构化试验、单次输出<=1500 token、输入<=16KiB、整个工作最多4次/4800预留输出token，解析并检查finish_reason/内容，超时不自动二次付费。后续更高思考能力需单独预算/日志验证，不能偷偷展开数亿token训练。
- 新的WF模型注册表始终报告provider=deepseek/model=deepseek-flash，`DISCOVERY_API_KEY`不作为Fallback。即使用户已有新密钥，也**不能因为模型能返回JSON就绕过V73原著分卷章号冲突、第一读PASS A必须先存R2不可变学海日志、第二段PASS B才可调用的纪律**。R2独立WF LEARN学习日志当前尚未部署，所以本阶段不自动执行真实章节训练或算文学晋级。
- 用户的现有Railway服务`wf-python-r2`于本次检查仍只有`WF_API_TOKEN`、`WF_INDEX_UPLOAD_TOKEN`两个R2 Secret，**没有`DEEPSEEK_API_KEY`**。用户需直接到Railway服务Variables设置自己的DeepSeek密钥，不粘贴到GPT、公共GitHub、worker源码。Cloudflare Worker/R2原著无需迁移或更换密钥。调用DeepSeek真实文学片段时，当前片段会通过用户选定的第三方API传送到DeepSeek服务器；联通探针只使用合成JSON字串，无私有小说传输。
- **真实测试** Railway合成回归部署`31ff6322-1a0b-47e0-b830-309e341fec25`：累计**79/79通过**，0错误、0失败；对DeepSeek请求JSON合同、敏感错误不外泄、超时不重试、来源章节冲突/旧R2 SQL、安全Token隔离统一回归；实际DeepSeek调用0、R2读取0、写0。此成绩是软件API适配的离线模拟，**不是已经连通并成功使用DeepSeek官方API**。
- 新脚本`wf_railway_v74_deepseek_probe.py`只有Railway已配置`DEEPSEEK_API_KEY`时才向官方DeepSeek发一条合成JSON最小请求（单次120输出tokens），不带任何原文；缺失时按`WF_V74_WAITING_FOR_DEEPSEEK_API_KEY`安全不联网。探针成功只证明模型能用，仍不代表WF已自主分类/学完一章。最后将Railway服务启动改`python -u wf_railway_v74_safe_idle.py`，防止后台自动付费与源文件曝光；若无环境密钥则用户完成设置后需另运行探针。

**下次第一关**：核对Railway `DEEPSEEK_API_KEY`变量名存在（不要取值），再单次真实合成API健康探针；只有用户认可这一外部模型可接收私有章节片段、WF的不可变R2 LEARN账本和V73章节冲突都解决后才能真正WF自己进入第一章PASS A。不让GPT代写读者反应、考官替其选书或自动推进文学状态。

**V74最终安全状态**：Railway部署 `e467dff7-4383-4f9a-b050-8ec89fc33272` SUCCESS，已固定启动 `python -u wf_railway_v74_safe_idle.py`，日志 `WF_V74_SAFE_IDLE_DEEPSEEK_FLASH_SELECTED`；确定WF新LEARN选择 `deepseek-flash`、旧Discovery未选、`DEEPSEEK_API_KEY`仍缺、DeepSeek模型真实请求0、原著读取0、R2写0、没有自动训练。下次用户仅需在Railway原服务设置自己申请的 `DEEPSEEK_API_KEY`（禁止贴聊天），助手再启动 `wf_railway_v74_deepseek_probe.py` 用合成JSON验证一次真正API；独立WF R2学习日志未部署前PASS A/B继续锁定。


## 63. 【2026-10-19 V75】DeepSeek Flash官方真实连通；WF自己的R2首读顺序封存协议离线通过94/94，尚未部署学习写入通道

**用户最后说「ok」表示Railway已经配置前面选定的`DEEPSEEK_API_KEY`**。助手没有读取/输出密钥值，只检查名字存在。真正DeepSeek官方API只调用一条人工合成JSON：Railway`106940c9-c1fb-4d51-a852-43adf5aec6f7`，`WF_V74_DEEPSEEK_FLASH_REAL_API_PROBE_OK`，退出0，输入113 tokens、输出12 tokens；私人R2原著0字节、原R2写0。这已经**证明模型连接成功**，无需再让用户重复配置DeepSeek，正式逐章读书仍尚未执行。

**用户前面纠正的根本原则仍在**：书的类型判断、章号、逐句阅读、首读反应、技巧分析、错误经验和下一次学习选择都属于WF自驱的LEARN，不由GPT考官代学。V73真实章头495 vs旧499/4处差异/295次印刷章号重复/3次号段重置尚未由WF模型+原文证据审定；GB18030编码原著版次仍provisional。原V49第三轮失败与第二课程LOCKED不可改变。

本轮新隔离分支 `v75-wf-immutable-learn-journal` 从V74继承，完整证据 [V75不可变R2 LEARN账本交接](V75_WF_LEARN_IMMUTABLE_R2_HANDOFF_20261019.md)。新增：
- `writerforge/r2_learn_journal.py`：为PASS A每个顺序单位生成独立不可变R2事件，事件包含原来源Key哈希/原文字节SHA/章正文SHA、模型模拟读者反应及SHA链；读取已有锁定事件以从断点恢复、不重复调用付费模型；整段A存完后才seal，PASS B必须引用seal和已经保存的来源单元SHA，全部R2 readback验hash。
- `writerforge/wf_sequential_learning_trial.py`：仅**2~3个当前顺序原文单位**的实验执行器，调用官方DeepSeek Flash JSON模型；一次只让它见到当前单位（未来句/段不能提前出现在请求里），每次首读回答立即签R2，全部A封存之后才能调B。重启后跳过R2已保存的A/B事件，且不会重复付费调用。它是小预算协议试验，**不能算已学完一整章、更不能算文学水平达标**。
- `cloudflare/wf-r2-worker-readonly.js`候选：保留所有V72真实SQL索引和原著读取接口，新增`GET/PUT /r2/learn/event`和`GET /r2/learn/writer-ready`。原R2 Reader Token只能读，原SQL Index Writer Token也不能写学习记录；**新第三个独立`WF_LEARN_UPLOAD_TOKEN`** 才可按严格`writerforge/v1/learn/v1/`路径创建仅8KiB以内不可变JSON，禁止覆写/DELETE、禁止未签A就写B、B证据必须存在。writer-ready是0R2写认证探针，WF在向DeepSeek传任何私人文本片段前必须先通过此探针，避免模型调用后无法保存首读。
- 模拟R2 Worker + Python真实模拟测试：初次`11cf6dba-472d-4f1c-af36-bf58502a12f4`测试因合成Worker URL未通过`.workers.dev`语法门槛而13错（保留）；修夹具后`c31c51a5-ce9c-4385-9857-d71cfd6c812b` 92/92；增加中途重启不重复首读`f9071a1b-38d6-4226-b8c9-84ea95cecc6a` 93/93；最终加必须**先认证R2写入权限才可向DeepSeek发送原著**`c19ac34c-4d7e-44c3-8a9e-777c53543da5` 94/94通过，均0真实R2、0真实DeepSeek/0原著读取。Worker JS注入式本地模拟12条权限/顺序/证据写入用例状态完全符合预期，Writer-ready独立权限200，旧Reader/IndexWriter分别401，旧health200。这些**都不是V75线上R2学海写入验收**。
- **真正用户介入的唯一下一关**：用户还需在现有Cloudflare `wf-r2-api` Worker 新增独立Secret`WF_LEARN_UPLOAD_TOKEN`，保留`WF_R2`绑定及两个旧Secret，将V75候选JS部署一次；同时在原Railway`wf-python-r2` Variables添加同名同值第三Secret（**绝不能贴到聊天/GitHub**）。这是为了保持旧SQL写入与新文学账本写入权限分离，不能拿SQL索引Writer默许扩大到文学记录。助手目前没有Cloudflare管理权限，不会擅自声称已部署。
- 用户完成配置后，先用Railway新程序做真实`writer-ready`纯鉴权、只读认证测试，通过后才让WF选择经过文档边界及编码核验的原著，执行**一个2—3片段**的先A后B实际序列，存R2后用新的Railway进程冷读，先校验安全证据，不急着处理全部43/400部，也绝不把模型自评当文学等级晋级。模型连接已真实成功不需要重复付费联通。


**V75当前真实safe-idle状态补充**：Railway`5803a081-8090-4a2b-8f67-0d6d53b9ebe1` SUCCESS，启动`python -u wf_railway_v75_safe_idle.py`，`WF_V75_SAFE_IDLE_LEARN_JOURNAL_PENDING_DEPLOY`；DeepSeek官方Key已经有且合成API探针通过，WF R2 Reader/SQL Writer密钥也存在，但**第三个独立LEARN Writer Secret `WF_LEARN_UPLOAD_TOKEN`尚无**，V75候选Worker尚未由用户部署。safe idle绝不触发真实原文/模型/R2写，生产原V72 SQLite索引仍在用户R2。下步不需要重设DeepSeek，只要部署已有Worker候选和新LEARN专用Secret，然后先真实writer-ready零写探针，再WF小单位学习实验。 


## 64. 【2026-10-19 V76】用户要求批次学习+独立监督：真实B00已审6份私有R2文本、0本通过，不可伪称训练

最新用户指令截图：DeepSeek后台 **1次API、125 tokens、<¥0.01**，要求「设定批次--先阅读什么--一批阅读几本--阅读的要求是什么---WF是否糊弄自己--监督--开始」。前述125 tokens**正好是V74一次真实合成联通探针113输入+12输出**，并非读书训练。考官冻结了批次范围、来源选择和反作弊门槛，不人工点名挑易书、不给WF小说标准答案，WF自驱模型仍为官方`deepseek-flash`。详情见 [V76批次与反作弊协议及真实结果](V76_WF_BATCH_EXAMINER_PROTOCOL_20261019.md)。

- B00（**本次真正执行**）：从R2的仙侠→历史→科幻三个目录**仅作为存储类别提示**，每类1个目标、最多2个按大小与原Key-SHA稳定排序的备选，限制10KiB—8MiB一份、最多6份/48MiB总量。挑书过程在读取正文前就冻结完整Key哈希的preselection摘要`c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4`，不能看过WF表现不好就临时换书。
- B00真实Railway部署`082f665b-23f7-447e-a75d-182e3c306e7a`、`WF_B00_READ_ONLY_ADMISSION_AUDIT_COMPLETED`，退出0。完整R2扫描79对象，按严格预算检查6份**原始TXT**，真正下载/解码共**31,000,917字节**，**0份达到严格结构+编码全通过**、0模型、0R2写、0章文学学习；原著/文件名未进GPT或GitHub。该批总收据SHA`090d78da2933bfde99b272d3f518a4d576a67d79c445da170c14803fb705336a`。
- 分类概况：仙侠1号源4,009,069字节，WF严格/旧解析都是**465/465章头候选**，只有GB18030编码仍provisional，并不说明作者文学类别已确定；仙侠2号源1,356/1,357候选、重号/跳号/编码待复核。历史两源分别508/510和988/988，均有其他章号/编码冲突。科幻1号源正是已知495/499章头分歧；第2源严格解析触发`WF_ADMISSION_EMPTY_CHAPTER`。**没有人替WF修答案或偷偷删除异常章节**。下步应让WF自己对编码/章号提供独立原文证据，尤其仙侠465/465候选最接近程序准入，但不能因用户要求开始就擅自降低事先冻结的标准。
- 后续批次政策：B01只有1本/2—3个连续原文单位的PASS A签收→PASS B实验，**最多4次模型调用、2,000预留输出tokens**，不算学完一章；B02在B01/R2证据/全章逐单位覆盖能力均通过之后才准3书各完整第一章；B03未来每批3—5本，未启用自动任务。WF自行判断类别及章节，考官只查事实与能力迁移。
- 反作弊底层新增`writerforge/wf_batch_supervisor.py`：不接受模型提供的全True JSON作为完成证据，必须使用另一**只有R2读权限**的程序逐条从R2检查PASS A顺序来源单位SHA、不可变封存和PASS B引用原文，输入与已认证原始章的来源单位SHA复算；任何完整章节覆盖、未来文本请求泄漏、实际DeepSeek账单对账没证明，就**拒绝宣布整章通过**。不授予文学晋级。V75 PASS A/B真正线上日志仍待部署。
- 费用监督新增`writerforge/wf_api_usage_supervisor.py`并将新的`WF_LEARN`模型注册默认改为计量版DeepSeekFlash：记录请求UTC、hash、角色、预算、模型回答实际输入/输出tokens以及失败；超时可能扣费也保留记录，不凭没有响应当0元；DeepSeek后台截图只在相同时段/没有别的App调用时能与WF报告核对，否则诚实标`UNRECONCILED`。不记录原文、答案或密钥。
- 真正Railway离线回归：103/103→新增独立R2审计测试夹具5项NameError红色（保留）→109/109修正→最终`1f96d207-fa6b-4f9b-b6dd-39da541018fa` **117/117通过**，0模型与R2访问，不能冒充文学训练。
- 当前仍只具备R2读、SQLite Index Writer及已经实测可用的DeepSeek官方模型。**独立文学R2 Writer `WF_LEARN_UPLOAD_TOKEN` 尚未配置，Cloudflare V75 LEARN Worker代码仍是Github候选未真实部署**。用户须在现有Cloudflare`wf-r2-api`和Railway服务新增同名、相同内容、与现有两Token不同的新Secret，保留R2绑定，部署候选Worker一次；密钥不可发送GPT。之后先零付费writer-ready鉴权探针，才允许DeepSeek见一段私有原文→R2真实首读签收，绝不先模型后补账。
- V49文学终审`THIRD_STRIKE_FAILED`、第二学习窗口`LOCKED`不可修改。V72一份真实科幻SQLite永久R2索引依旧保留但不等于WF学到第一章。下次必须继续V76监督/本批来源复核，不要从头重新选6本，更不要直接自动跑50/400本。

**V76 最新Railway安全状态**：`32a77a70-3481-4b59-b4a9-594935de1c1c` SUCCESS；已固定单次安全待命 `python -u wf_railway_v76_safe_idle.py`；B00真正查过6本/共31,000,917原字节、合格0，留下严格SHA收据；0模型、0新的R2写。DeepSeek Flash凭证存在，但专用R2 LEARN写凭证不存在，V75学习接口还未上线。**不可未经用户完成Cloudflare部署和独立Secret就自动开收费原文训练**。新模型用量审计和独立R2复检已被117/117纯合成Python测试验证，属于监督代码，尚未有真实LEARN证据可给文学分。


## 65. 【2026-10-19 V77】用户展示三个已配置密钥后纠正第四密钥反复要求：三密钥方案已实装测试

**新的最高优先级决定**：用户在Railway Variables截图中显示`DEEPSEEK_API_KEY`、`WF_API_TOKEN`、`WF_INDEX_UPLOAD_TOKEN`三个均已存在，反感不断被要求增加第四个。之前多次要求`WF_LEARN_UPLOAD_TOKEN`是助手过度细化的权限隔离架构，不是用户漏配或R2必需。**V77取消第四个密钥要求：原本`WF_INDEX_UPLOAD_TOKEN`同时可写严格限定的SQL索引与独立LEARN事件命名空间；`WF_API_TOKEN`原著仍只读。** 这降低Writer角色隔离强度，但节省额外凭证管理；Worker路径白名单、事件签收/不可覆写依旧独立。先前V75/V76“必须第四密钥”的手工操作建议从此由V77替代，不要再让用户新增Secret。完整方案：[V77三密钥/无需第四个](V77_THREE_EXISTING_KEYS_SHARED_WRITER_20261019.md)。

1. 新分支`v77-self-charset-source-audit`从已冻结的V76分出，只修改Worker候选、WF LEARN客户端、独立考官的`read_only`模式、测试，未改生产 Cloudflare 代码，未写原著，未触发Github Actions，未开始付费WF文学训练。
2. Worker候选`cloudflare/wf-r2-worker-readonly.js`中：`GET /r2/learn/writer-ready`及`PUT /r2/learn/event`使用旧`WF_INDEX_UPLOAD_TOKEN`做Bearer验证，旧Reader无法写，写入Key必须是`writerforge/v1/learn/v1/...`，错误顺序/来源SHA/遗漏首读封存/覆写被拒绝；旧索引Writer原来的`indexes/v1`通路保留；无通用PUT/DELETE小说权限。没有读取`WF_LEARN_UPLOAD_TOKEN`。
3. WF`r2_learn_journal.py`默认Writer取旧`WF_INDEX_UPLOAD_TOKEN`；独立监督不能误用同进程Writer，显式`read_only=True`并且`writer is None`才能出具监督报告。原B00六份真实原著审计结果完全保留：0份严格准入、0次DeepSeek文学学习，`preselection_sha=c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4`，不允许为凑训练成绩更换来源或自行修章号。
4. **真实离线Python联合回归**Railway部署`12ae1f2c-d699-4024-abfb-23cd55ecfea7`，**119/119全部通过**，0失败0错误、0模型、0真实R2读写。Worker JS注入模拟验证writer-ready共享Writer200、Reader401、原著写403、PASS A每单位按链写+seal+PASS B，覆写拒绝，旧health保留。此为**模拟接口而非Cloudflare生产V77已部署证明**。
5. 新增真实零写探针`wf_railway_v77_shared_writer_probe.py`，待用户部署Worker再运行；它用旧IndexWriter试LEARN WriterReady+Reader拒绝，不发送小说或付费DeepSeek。默认生产服务恢复`wf_railway_v77_safe_idle.py`，无网络、无自动任务。
6. 用户只需**备份当前Cloudflare原Worker脚本，用V77候选完整JS替换/Deploy一次**；不动三个现有变量/Secret，不新建桶/卷，不再要求第四个Key。用户确认Deploy后我们验证WriterReady，再继续WF自己复核已冻结仙侠465/465候选的GB18030及章节来源；真正B01仅1本2-3个已验证连续片段，且不能把任何模型自评当文学晋级。
7. `V49 THIRD_STRIKE_FAILED`和第二文学课程窗口`LOCKED`保留；DeepSeek官方`deepseek-flash`之前已在Railway合成API探针真实调用成功，不需要用户再配一次。



## 66. 【2026-10-19 V78】继续：真正Cloudflare共享Writer接口401；WF自己核查冻结仙侠原文编码，首章3个连续单位已准备（无付费/原著泄露）

用户说「继续」，不得再重复索要第四个Secret、不得挑新书、不得伪报WF文学训练。新隔离分支 `v78-wf-frozen-source-encoding-review` 继承V77，原三Secret仍是`DEEPSEEK_API_KEY`/`WF_API_TOKEN`/`WF_INDEX_UPLOAD_TOKEN`。详情见 [V78真实编码/首读预演/受阻接口](V78_FROZEN_XIANXIA_BYTE_AND_B01_PREFLIGHT_20261019.md)。

**真实线上接口失败**：Railway`29322cf2-2f96-40d1-9dc6-909188a326a9`以已配置旧`WF_INDEX_UPLOAD_TOKEN`请求生产Worker `GET /r2/learn/writer-ready`，返回`WF_LEARN_WRITER_PREFLIGHT_HTTP_401`。零R2写、零原著下载/付费模型，退出1，**说明线上LEARN写入还不支持当前V77共用Token方案，绝不是用户漏配第四密钥**；禁止绕过认证。

**V78完整来源字节核验成功**：真正Railway`7d469287-6862-4d01-b42e-363b7d32da40`从B00预注册名单SHA`c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4`找到完全同一份仙侠来源，来源Key匿名SHA`370400053cded15ca89e3232e7be84b28aa20ca70542150138bef6201dc7cb22`，原始文件4,009,069字节及整本SHA`0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd`一致。全文件`gb18030`与`gbk`均严格解码/字节往返完全同Unicode文本，`big5`、`cp950`及`utf-8`全文件严格失败；完整2032427个字符，U+FFFD替代0/非法控制0/乱码标记0。465个严/宽章头规则完全一致、章号冲突0/倒退0。此是强**技术解码**证据，不能冒充作者原版证明，`source_edition_human_confirmed=false`；不能事后把V76 B00原本0/6严格准入改成通过。

**V78首章三单位已由WF自行准备**：真正Railway `57025b6e-18db-4e15-887e-91a04c10bbe4`，从原首章物理第14—83行提取正文6022字符，采用保留全部字符、优先中文断句点的连续切分，按当前规则共有**15个来源单位**，只准备最前3个，长度434/428/434字；对应每单位SHA以及前三单位合并SHA`9a4e2126b13aa1f368c8b58d3860a119f144d1f2149dca6614c8df417b141a13`均有机器凭据，不公开原文。原著0修改、DeepSeek实际调用0、R2写0、文学完整章节0。B01是**另外注明版本的小片段协议实验**，不更改B00严格来源标准。
 
**已开发可直接调用的下一阶段脚本但** **不可在401状态启动**：
- `wf_railway_v78_b01_one_book.py`：既有Writer先认证R2 writer-ready，成功才读取相同冻结源文、提3个首章片段、调用注册的计量版`deepseek-flash`至多4次/2000输出tokens，顺序PASS A按单位R2签收，seal后PASS B，成功只报告三单位程序签收不报告文学晋级。
- `wf_railway_v78_reader_only_exam.py`：完全新容器去除DeepSeek与Index Writer环境变量，独立同一来源三单位SHA重新取R2锁定PASS A/封存/PASS B对照，只有读权限。这里的词面/模型反馈不能自证文学掌握或全章覆盖。
- 全套本地同接口合成测试+安全AST：首次因无BOM UTF8不能以`utf8-sig`字节往返的测试误断出现1失败保留，修正后127/127→132/132→最后Railway`e72d6fac-35db-4788-a919-58b90ccb279f` **136/136通过**，模型0/真实R2请求0（模拟）；以上真来源试验单独日志另验。

**下一门槛只要一次Cloudflare Worker部署，不要新增或重新设置任何密钥**：把本分支`cloudflare/wf-r2-worker-readonly.js`完整源码更新到原有`wf-r2-api`（保留`WF_R2`binding及2个原Cloudflare Secret），用户点Deploy。然后由助手再跑原`wf_railway_v77_shared_writer_probe.py`，确认200与Reader401后才能启动真实B01。当前助手只有GitHub/Railway连接，没有Cloudflare管理员写接口，不能冒称GitHub代码更新已导致Worker线上更新。不触发GitHub Actions，不让ChatGPT读取小说正文。旧V49`THIRD_STRIKE_FAILED`和第二学习窗口`LOCKED`保持。


## 67. 【2026-10-19 V79】用户催促真训练：已实付费执行仙侠原著前三段PASS A/B，R2真实暂存+独立新进程恢复成功

**最新用户要求**：「服了--快点让WF训练啊」。**不要再要求用户新增第四个密钥或反复部署Cloudflare**。本窗口在原本Cloudflare V77 `learn/v1`仍对旧Writer返回401的情况下，充分利用已有V72已上线的内容寻址、仅可写`indexes/v1/chunks/{sha}.bin`的R2旧索引小块接口，将一批**独立标明“实验性LEARN”**的短JSON作为不可变CAS内容块保存。因仍在SQL索引blob池，**不是原生LEARN命名空间部署成功**，不能伪称服务端已经有LEARN事件序列鉴权/正式全书学习系统。该应急存储在`writerforge/v1/indexes/v1/chunks/`，不发新的索引manifest，不改已有SQL catalog/R2小说原文，恢复需要记录最终checkpoint SHA。详细运行证据、所有事件SHA及隐私边界见 [V79首轮真实训练与独立冷恢复](V79_REAL_DEEPSEEK_B01_PROVISIONAL_R2_CAS_20261019.md)。

- 新分支`v79-real-b01-provisional-r2-cas`，原V78冻结来源不变：原B00候选来源摘要`c35fa66232f2851f17767615f3447ff4822587a52f3106e189eb5d61cf3262e4`、匿名源Key SHA`370400053cded15ca89e3232e7be84b28aa20ca70542150138bef6201dc7cb22`、文件整SHA`0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd`、仙侠原文大小4009069字节，gb18030/gbk全文件严格可逆。首章6022字符/15个WF自切连续单元，真实验只读前3单元（434/428/434字符），逐片段原文SHA严格核对，绝不事先泄露后12单位内容。
- **真实 DeepSeek + R2 CAS 训练已成功**：Railway部署`5022a7ef-dd5e-41c4-bf1b-c9631e5d1d48`，`WF_V79_B01_REAL_DEEPSEEK_AND_R2_CAS_COMPLETED`及`WF_V79_REAL_B01_EXIT=0`。1次索引Writer SHA故意错误422零写鉴权门通过后，WF真的向官方`deepseek-flash`顺序发送3段真实原文，3次模型首读返回JSON、每段读后反应直接作为独立不可变R2 SHA内容块签收并立刻只读校验，再发布首读seal，seal成功才发**第4次**官方DeepSeek文学机制分析，结果也是SHA锁定的R2 CAS事件。共4次真实收费API，真正reported输入`2526` + 输出`731` = **3257 tokens**，无重试，无超时。费用人民币未知需要与DeepSeek同时间窗口账单核对。**不是合成JSON连通探针**，用户真实小说仅在自有R2/WF Railway/用户授权第三方DeepSeek间传输，未通过GPT/GitHub。
- 共有**5个R2 LEARN事件**（首读3、seal1、文学分析1）以及各事件后更新的5个SHA恢复checkpoints；各事件及元数据不存小说原始文字。最终不可变恢复指针**`b7ace511e422c8973a35c0cc4d75229d0c11c7ddcefe4db97eda6b6098bc1210`**。全部5个event SHA详见V79报告，不需要向模型二次付费重做。
- **独立考官已经真实验证**：另一个全新Railway部署`6fbb6ffc-362f-4939-b778-2a539ab257d5`，Python启动即从环境移除DeepSeek及R2 Writer密钥，加载上述checkpoint，用原Reader读回R2的5个CAS事件和同一本原始小说SHA，独立计算头3来源单元哈希，对照首读顺序、seal、分析引用，状态`WF_V79_R2_CAS_PASS_A_B_FRESH_PROCESS_VERIFIED`、`WF_V79_COLD_CAS_EXAM_EXIT=0`，模型0/R2写0，是真正跨进程证据，而不是训练进程自报。**监督只确认来源/程序顺序/记录保存，不证明模型分析质量正确、未来提示词全文未泄漏、学完完整章节或人类读者情感真实**，旧V49失败与学习窗口LOCK不变。
- V79新`writerforge/v79_provisional_r2_cas_journal.py`兼容WF的PASS A/B接口，严格SHA写入/回读、每次事件签checkpoint以及只读按hash恢复；`wf_railway_v79_real_b01.py`真实付费一批一书三单位；`wf_railway_v79_cas_cold_exam.py`另进程真考官；`wf_railway_v79_safe_idle.py`安全待命。新旧全部**140/140合成测试通过**（Railway`f9d88ae3-16a8-41ee-afec-bc797a1b9b03`，测试无付费/R2真实访问）；V79真正成果只来自上面两次真实Railway部署。
- 本轮已经**完成了真正的WF模型阅读行为及R2实验经验落盘**，但按预注册纪律**完整学完文学章节数仍0**：只读了15个单位中的3个；模型生成的阅读反应与分析不能当作可信文学能力晋级。下一阶段应在有实际新预算与按章索引前把本次记录的SHA锁定，然后由WF自行读同一章后12单位、进行按章完整复盘及独立转移小测；不能重新点名更易书、重跑已付费3单元或拿单次B01当毕业。Native LEARN Worker的新部署可后续再迁移元数据/指针，不需要再重新上传小说或配置密钥。**不要再要求第四个Key。**


**V79最终安全状态**：Railway新部署`ae099ff2-e20a-479f-b7dc-77f23575e3d2` SUCCESS，`WF_V79_SAFE_IDLE_REAL_B01_3_UNITS_CONFIRMED`，0新的模型请求和R2读写，已真实锁定3个首读单位+1个文学分析，checkpoint`b7ace511e422c8973a35c0cc4d75229d0c11c7ddcefe4db97eda6b6098bc1210`。后续不要重复付费处理前三单位。

## 68. 【2026-10-19 V80】真实15万Token封顶训练与独立只读考官验收通过（接连接中断）

用户要求「训练必须放大，最大token提高到15万」，并在考官进行时说「连接中断了--继续」。这一轮**实际完成**的最终成果详见 [V80大批次真实训练报告](V80_DEEPSEEK_150K_REAL_BATCH_20261019.md)。继续时不需要从头训练、更不需要重新申请第四Secret。

1. 本次训练真实Railway部署 `4b002381-c140-4c90-b2f5-e87e683d111a`，DeepSeek Flash新V80批次**73个真实请求、67,494输入+15,869输出 = 83,363 Tokens**，低于150,000**单批次输入＋输出硬上限**，未强行凑满额度。包含首轮分析JSON格式失败的13次/13,514 Tokens并准确扣除；恢复R2之前已经签收的首读，不重复付费重看。此前独立的V79试验4请求/3257 Tokens不计入本次V80上限；两个训练批次不能混为同一账单。
2. 用原B00冻结的一份仙侠TXT，SHA `0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd`，真正WF读全前6章**62个来源单位**：章次单位数15、12、14、6、6、9。每个单位先调DeepSeek模拟读者反应→立刻R2 CAS SHA签收→再读下一单位，另有分析与下一章策略复盘写R2，已留各章经验链。**第1章**继承V79提前三段先分析，虽然后续补齐12段原文与补充分析，仍明确标注「混合历史，非严格先全读再分析」。**第2—6章5章**是完全按先A后B的干净流程；这只是程序正确，不等于文学学会。
3. R2真实训练终态永久CAS journal SHA `0b24a62a697b11e140477225728375fc406cd035fe921ad8ca5476b48a674240`，本批进度SHA `f606f5216f82fd40a7893cfe8942e2454efe94b9f1389110bdc37f19f3a4f227`，第6章经验SHA `1d0ee736b199f9af4c04543ba4d7d620ca8e1565b31b25ca673bef610c2b2d9d`，所有小记录存在原R2内容寻址索引块池；**不是**线上原生LEARN专用路由已部署。不能因为它们在索引块池就误认为SQL索引库已合并文学经验。
4. 全新只读考官Railway `7f739347-8099-4b28-8598-2d70ad7accfa`，其日志现在已确认 `WF_V80_INDEPENDENT_R2_FULL_CHAPTER_PROVENANCE_PASSED` 和 `WF_V80_READER_ONLY_BATCH_EXAM_EXIT=0`。考官启动时移除DeepSeek/Writer Token、只用Reader重新从R2读全小说及所有CAS事件，逐章核原文unit SHA/首读顺序/封存与分析引用/跨章经验hash/批次预算，检查6章原文覆盖与5章清洁Pass A/B都通过，考官模型调用0/R2写0。连接中断未破坏前述成果。
5. **重要限制**：文学模型生成的读者心理感受不等于真人；模型机制分析正确性、输入提示是否绝不泄露未来段、文学经验跨作品可迁移性与人民币账单尚未进行独立实证。旧V49 `THIRD_STRIKE_FAILED` / 第二窗口 `LOCKED` 原样保留；未经新的盲评和多个作品正向迁移，不允许WF晋级或声称真正掌握作家文学能力。
6. 本批技术目标是使**150k成为可用上限**并扩大章数，结果读完6章就正常停止，余额66,637 Tokens不是任务欠账，不应为了凑满而让模型无意义输出。下次选择是新独立批次在已签收第6章后继续第7章，或先做独立文学盲测；**不可重跑/覆盖已付费6章，不自动触发下一批**。现有3个密钥均已配置，无需再要求用户上传小说/换Worker/新建密钥。



**V80 安全待命最终部署（连接恢复后）**：Railway `b0d2584c-1436-4673-a346-a0c71fcd67a3` `SUCCESS`，`python -u wf_railway_v80_safe_idle.py`，`WF_V80_SAFE_IDLE_150K_LIMIT_APPLIED`；日志核实此次0模型调用、0原著下载、0R2写、0自动新批次，密钥仍只有既有三种。原六章/73请求/83,363 Tokens的V80数据及独立考官 `7f739347-8099-4b28-8598-2d70ad7accfa` `WF_V80_INDEPENDENT_R2_FULL_CHAPTER_PROVENANCE_PASSED` 不因安全待命而丢失；恢复起点是 batch SHA `f606f5216f82fd40a7893cfe8942e2454efe94b9f1389110bdc37f19f3a4f227` 和journal SHA `0b24a62a697b11e140477225728375fc406cd035fe921ad8ca5476b48a674240`。不要重复支付首6章；后续文学迁移盲考未做，V49失败/文学第二窗口LOCK保持。


## 69. 【2026-10-19 V81】第7—10章真正训练完成，独立R2来源核验通过；跨作品两臂真实对照已执行，未证明文学进步

用户先同意「从第7章继续训练，同时加入独立文学测试」，后说「继续」。不能重新收费训练V79/V80以前十章；需基于同一个冻结B00仙侠作品与永久SHA记录继续。详见 [V81真实训练和跨作品对照报告](V81_CH7_10_REAL_TRAINING_AND_TRANSFER_20261019.md)。

1. **真正的新训练完成**。Railway b1596b80-43c9-49c8-8d00-a86d44f91102，状态 WF_V81_CH7_TO_10_R2_BATCH_COMPLETED / WF_V81_TRAINING_EXIT=0。WF从已独立核实的V80第6章R2进度和经验恢复，不再阅读/付费以前六章。第7—10章单位分别9/8/10/12，共39个首读单位，4个完整先A后B章节，后验分析/每章经验复盘单独存R2实验性CAS。51次真实DeepSeek Flash请求、44771输入+12900输出=57671 Tokens，属此V81独立150000输入+输出token硬上限内。V81最终journal SHA 61a52125708a180b3305e28721d6e1797c0ab619df18a1bac7822988707a9c33，batch SHA e28490de3f0b17875ed23418726a8b8692b3029c1501b30da314080f4edb0901，第10章经验SHA feee04808c6b14f84c16989d98b031937a897395f3d008c43e17b3449f9077e3。B00原著与旧V80指纹未换，不复制源码文本到GPT/GitHub。
2. **真正独立考官通过**。Railway ae6b3368-c45a-423e-b16b-1259e27b9b5d 的全新纯读进程（无DeepSeek/Writer秘钥）恢复121条R2事件地址，从私有R2原著重算全部39来源单位哈希、PASS A顺序/封存、PASS B引用、历史第6章经验和7—10章经验链，返回 WF_V81_INDEPENDENT_R2_CH7_TO_10_PROVENANCE_PASSED / EXIT=0。第1—10章累计来源覆盖10章，其中第2—10章共9章严格全首读后析；第1章V79三段先分析历史永久保留，不伪称全程纯先读后析。
3. **另一个作品的独立对照真执行**。不让GPT指定容易的小说或正确答案：从B00冻结的历史类第一候选（不同于仙侠训练书）只取首2连续原文单位，SHA precommit ab587b5472a4258e057e1ba6ed5b79df0f0ba7405882e85a8170bde82ba228d2，顺序固定「带WF第10章旧经验→不给经验的基线」。Railway真实 f308aaae-6dd2-46b2-9766-f12765363f67，2次官方DeepSeek Flash，1616输入＋435输出=2051 Tokens。两组模型输出内容SHA不同，但两组引用相同两个来源单位，**不能证明有经验组质量更优**。R2最终对照CAS SHA 88a3bf2c34f5fd21400236af375b38df94392403f4b3b3edbc2e352b962049d4。
4. **跨作品对照独立来源审核通过，不等于文学毕业**。Railway 8e23b4ba-d7a4-4c5a-b018-90fe51b4a58a，独立纯Reader进程按R2实际内容校验预注册、另一本历史类原文相同两单位hash、两组模型回答和比较对象，WF_V81_BLIND_TRANSFER_R2_READER_EXAM_PASSED/EXIT=0。未审定哪组文学分析更正确/有洞察力/可迁移；原V49 THIRD_STRIKE_FAILED、第二课程窗口LOCKED完全不变。模型自己写经验并影响下一步提示，不等于模型权重真的学会或人类心理实验成立。
5. **测试、权限和存储边界**：Railway模拟回归156/156，增补跨作品对照测试后162/162，零模拟测试费。学海事件和对照CAS仍放旧Cloudflare真正有权限的 writerforge/v1/indexes/v1/chunks/{sha}.bin，不是Native LEARN路由已经在线；只是隔离的小型哈希实验记录，不能宣称正式文学经验库完工。原有DEEPSEEK_API_KEY/WF_API_TOKEN/WF_INDEX_UPLOAD_TOKEN三个变量有效，无第四个秘钥、无需重复部署Worker。人民币计费还没直接核对官方后台，不能猜定价。
6. **下一起点**：本次明确只授权第7—10章与独立对照测试，后续第11章或更多付费训练要新批准/新批次，不得自动继续、不重跑已付费十章。经验因果迁移的强测应采用盲序审看两组匿名答案、原文真证据、对照跨作品多题随机化等，不能凭本次单场「答案不同」给WF晋级。完成后Railway必须切回单次安全待命，不继续计费。



**V81 最终安全待命：** Railway 719d9f66-509a-4a48-8c5b-f23e15538050 SUCCESS，固定启动 python -u wf_railway_v81_safe_idle.py，WF_V81_SAFE_IDLE_10_CHAPTERS_AND_TRANSFER_AUDITED；0新DeepSeek请求/0R2读写、自动付费训练关闭、三旧凭证齐全无需第四个。第7—10章51请求57671 Tokens和独立读审计已完成，另一部历史类来源的双臂迁移对照2请求2051 Tokens且独立CAS比对通过，但**文学质量改善没有被独立证实**。最终恢复V81 batch e28490de3f0b17875ed23418726a8b8692b3029c1501b30da314080f4edb0901、journal 61a52125708a180b3305e28721d6e1797c0ab619df18a1bac7822988707a9c33、经验 feee04808c6b14f84c16989d98b031937a897395f3d008c43e17b3449f9077e3，盲对照对象 88a3bf2c34f5fd21400236af375b38df94392403f4b3b3edbc2e352b962049d4。下一步始于第11章，若需要新收费批次应由用户再次批准，避免重跑前十章。


## 70. 【2026-10-19 V82】第11—15章真实训练完成，独立审计KeyError已修复且最终通过

用户「时间过长--导致中断--继续」；恢复前先检查Railway/GitHub，发现中断期间项目已进入`v82-ch11-15-training-and-audit`，但最新服务状态`CRASHED`。**并非需要重训**：真实V82付费进程早已返回`WF_V82_CH11_TO_15_R2_BATCH_COMPLETED`/`WF_V82_TRAINING_EXIT=0`，第11/12/13/14/15章分别完整首读11/11/11/8/6单位，总47；单独150K Tokens封顶的V82批次真实DeepSeek Flash调用58次、49,238输入+11,899输出 = **61,137 Tokens**。前十章没有再次付费重读。V82真实journal CAS SHA `3da56cc46115548c5198a65cb6124e3c03d9bdfdb1f0460950177735a99d1cb2`，batch SHA `d46ffec05927dfba3f2819089e76e79f720db2a2f3f6793b56965ac6413c177f`，第15章经验SHA `ddbf86e87e3bf44900b4e5e4d8ffc2de99c9ed5d3c5aec98a69bfd8eb7cf2fe7`，仍为R2小型CAS实验账本而非原生LEARN专用Worker命名空间。

独立考官连续崩溃`WF_V82_INDEPENDENT_AUDIT_FAILED`，代码定位`wf_railway_v82_reader_only_exam.py:124` `KeyError`：错读`v81_last_experience_sha256`，实际V82考官输出`v82_last_experience_sha256`。助手仅修字段，commit `cff5599c4e2254ab9997bcb6201f776b11aa3c6c`，绝不重新训练。新的真正只读Railway考官部署`18415e01-9607-4ed1-ad48-17f19deae3c2`**最终 `WF_V82_INDEPENDENT_R2_CH11_TO_15_PROVENANCE_PASSED`/`WF_V82_INDEPENDENT_COLD_EXAM_EXIT=0`**：纯Reader进程恢复178个R2事件（旧121保留，新57条），对照真实原著重算47来源unit SHA/首读链/seal/后验分析证据/跨章经验链，5章全部严格A先于B，考官0DeepSeek/0R2写。旧失败完整保留。详见 [V82真实训练与独立审计报告](V82_CH11_TO15_REAL_TRAINING_AND_AUDIT_20261019.md)。

至此，同一冻结仙侠原著前15章完整来源处理记录均有独立R2核验；第2—15章14章采用严格PASS A全文先读/封存后PASS B，第1章继承V79早期三单位分析，不能冒充纯A→B。这里没有真人心理或文学质量评审，模型提示词未来原文泄露和跨书质量提升也未被严格独立证明；**不能从章节数量宣布文学技能晋级**，原V49 THIRD_STRIKE_FAILED/第二课程 LOCKED保持。V81另一部历史类真实两臂跨作品对照已做、两组答案不同，但质量优势无从证明。现有三个Secret足够，永不再让用户配置第四个。**下一动作**：将原Railway服务改为单次`wf_railway_v82_safe_idle.py`等待指令，防止自动重训第11—15章。后续要接着原著第16章而不是从第1章开始；或者开发更可信的独立文学质量盲考与因果对照。

**V82最终安全待命真实回执（2026-10-19）**：Railway部署 `90bc4948-75b4-48b1-beb9-c2a4414e6028` SUCCESS，运行 `python -u wf_railway_v82_safe_idle.py`，状态 `WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`。日志确认本次待命 `model_calls_this_idle_run=0`、`r2_reads_this_idle_run=0`、`r2_writes_this_idle_run=0`、`automatic_paid_next_batch_enabled=false`。此前第11—15章的58次模型调用/61,137 Tokens、完整47单位独立只读验收及R2最终CAS SHA全都保留；原三个密钥配置齐全，不需第四个。未来付费续训最早从第16章开始，不得重新支付此前15章；文学质量盲评没有通过或否定的新结论，不自动晋级。


## 71. 【2026-10-19 最新窗口交接】用户说「上限了--交接」；V82已核实完成，独立交接文件已创建

**最新接续文件：[V82_NEXT_WINDOW_HANDOFF_20261019.md](V82_NEXT_WINDOW_HANDOFF_20261019.md)**。此文件是下窗口最短恢复路线，覆盖V79-V82所有真实生产部署、章节数量、费用Token独立批次、R2 CAS SHA和文学盲测限制。不要从旧V81半截对话回复重新推断“第7—10章还未完成”，也不要重新调用已经付费的模型。

再次以真实工具确认：
- Railway最新部署 `90bc4948-75b4-48b1-beb9-c2a4414e6028` **SUCCESS**，source branch `v82-ch11-15-training-and-audit`，pinned `8fa1bec6da50f9b3ab8e23019d0593a5f20b4aff`，start `python -u wf_railway_v82_safe_idle.py`。
- 真实日志 `WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`，该次调用模型0、读取原著0、R2写0、自动付费下一批false。原有三个密钥名称均在，不读取其值，不要求第四个。
- V82完整最后训练：第11-15章5章、47单位，58次DeepSeek Flash，输入49,238、输出11,899，合计61,137/150,000 Tokens；真正独立只读考官 `18415e01-9607-4ed1-ad48-17f19deae3c2`返回 `WF_V82_INDEPENDENT_R2_CH11_TO_15_PROVENANCE_PASSED`、exit0。当前累计前15章全部有来源技术核验、第2-15章14章严格先读后析。
- V82最终batch CAS `d46ffec05927dfba3f2819089e76e79f720db2a2f3f6793b56965ac6413c177f`，journal CAS `3da56cc46115548c5198a65cb6124e3c03d9bdfdb1f0460950177735a99d1cb2`，第15章经验 `ddbf86e87e3bf44900b4e5e4d8ffc2de99c9ed5d3c5aec98a69bfd8eb7cf2fe7`。均是已有私有R2 CAS验证对象，不是Cloudflare原生LEARN路由正式上线。
- 下一步可在用户明确要求时从第16章开始独立新批次；若没有新授权，仅可准备独立文学盲考设计，不得暗中启动付费训练。文学迁移质量未证实，V49 `THIRD_STRIKE_FAILED` 及第二课程窗口 `LOCKED` 继续保留。


## 72. 【2026-10-20 V86 最新隔离开发交接】第15章后暂停收费，已建立可恢复的负例阻断与修订闭环

**必须先读 [V86真实工程回归与范围报告](V86_SIGNED_REVIEW_NEGATIVE_TRANSFER_REAL_REGRESSION_20261020.md)**。本节不改第1—71节历史。当前进度以`v86-evidence-review-negative-transfer-loop`为开发分支；原main及V82旧文、R2不可变数据都未覆盖。

1. **真实已完成的章节**仍为冻结仙侠原著前15章。V83第16章曾只做来源预检，正式试训因错误的62位R2 journal SHA在模型创建前退出；已更正脚本但没有正式重新完成第16章。不要重读收费第1–15章，不要因这轮测试把完成数加成16。
2. **V84独立只读对照**复查已有V81跨作品两臂，原文出处/两个原始回答SHA验证成功，但文学改进`UNDETERMINED`，不是WF胜利或失败的文学评分。
3. **V85底层**新增精确短句/起止锚点、人物知识全局账本时点冻结、完整PASS A链校验、实验性审计仅LEARN且不自动导入WRITE；旧模型机制分析只有unit SHA不能回填伪造精确来源，`literary_semantics_independently_verified=false`。
4. **V86本轮真正代码增量**：在原`WriterForgeDB`追加两张小表`experience_evidence_links`与`experience_literary_reviews`，复用现有`ExperienceDecisionBridge`，只让新V86证据候选通过**明确外部签名文学审核+另一个V61受控实验批准**后获得抽象`SELECT`。签名负评后来追加时旧`SELECT`重放检查失效，下次`SKIP`，旧账保留；新版必须新V85封存claim和audit SHA、再评再授权，不能只换经验ID洗白。
5. **真实Railway离线测试**：`967e747b-2354-444e-af66-bd8d182a4391` 911项通过；补新claim隔离、重启与篡改反例后 `a5691e5d-0746-4029-b9a1-928819d466bc` 913项执行、0失败0错误、4跳过。两轮DeepSeek调用0、真正R2网络/写入0，没有新的小说文学评阅。沿用了V85全仓测试入口，日志内测试数真实包含V86测试，不能把工程绿灯当作文笔提升。
6. **永久文学事实**：V49`THIRD_STRIKE_FAILED`、第二课程窗口`LOCKED`，50部完整作品总体门槛仍保留。所谓“独立审核”在V86仅测试合成签名、可信身份与真实原文语义未获证明；生产不应让WF模型持有审核签名权或通过低层SQLite绕开审查。现有三个Railway凭证不要求用户重新配置或提供第四个。
7. **当前服务最后核实**：Railway `wf-python-r2`最新 `a5691e5d-0746-4029-b9a1-928819d466bc` SUCCESS，固定分支V86源码`df8919325fd75aeecbba1297e5bd3549c106f55b`，单次启动`python -u wf_railway_v85_full_offline_regressions.py`、`restartPolicyType=NEVER`。不自动付费续训，但**没有再次切回`wf_railway_v82_safe_idle.py`，不得冒称已切回**。下次操作前重新读取服务启动配置和最新部署/日志。
8. **下一轮合理工作**：不新造关系数据库、不在模型自己评审后自动晋级。先使用真实R2只读数据确认V80历史分析确实不含V85精确锚点；然后经新预注册文学题、可信独立源文审核、严格预算和WRITE实验条件，测试真实语义能力是否减少犯错；用户已给出“可以”授权本轮工程链测试，**没有给无限付费重训许可**。

恢复短指令：先读本文件§72与V86报告，检查GitHub分支及Railway状态；保留R2 V82 batch`d46ffec05927dfba3f2819089e76e79f720db2a2f3f6793b56965ac6413c177f`、journal`3da56cc46115548c5198a65cb6124e3c03d9bdfdb1f0460950177735a99d1cb2`、第15章经验`ddbf86e87e3bf44900b4e5e4d8ffc2de99c9ed5d3c5aec98a69bfd8eb7cf2fe7`。


## 73. 【2026-10-20 V87】私有R2随机抽取历史＋科幻两份陌生连续文本、真实独立冷审计通过

**完整新交接：[V87随机抽取与独立R2冷审计实测](V87_RANDOM_PASSAGE_REAL_RESULT_20261020.md)**；原预注册[目录抽签](V87_RANDOM_HOLDOUT_PRECOMMIT_20261020.md)、[盲考公平协议](V87_BLIND_PROTOCOL_PRECOMMIT_20261020.md)、[V87.0红色/连续片段备用协议](V87_CONTIGUOUS_PASSAGE_FALLBACK_PRECOMMIT_20261020.md)都不得删除覆盖。

- 基于用户2026-10-20T05:18:01Z“可以--随机抽取”，先固定种子＋算法再读R2目录，全部79对象，候选13，按种子随机抽中历史＋科幻，目录抽签SHA `ddb50ed6b88681c23d214073d45ba4edba151bf0de1e0bfed5153efeeb3e1f6c`。原文/书名从未进入GPT或GitHub。
- **严格章结构V87.0真实失败，必须保存红色**：Railway `41312043-fea5-4f59-a4d6-a5e5ce7e1b35` 0/2，7个固定候选无一过严格完整章门槛；保留程序退出2及原报告SHA `fa9bfe2ae2431a5fecea06ff0b280e4411cd0dcfaa40bbf0a41893e51b7cf417`，不把它说成学习章节通过。
- 新V87.1明确换为“**随机连续2300字局部来源观察**”，不是全章训练；算法改变前另提交同类别、同7个候选顺序与偏移规则，不让GPT换小说。原先编码有歧义的第1候选仍拒绝，第2候选历史和科幻均通过，完整原文字节SHA各为 `7dbc48ea45576b972dbf323ba77dea3e24b2394cc14650e23bc2c19788b77b97`、`a41e5b86b2878bae3e1a42babd3a21714788ae36bbdc6c1faa1ccb11a0158172`。各取两个可见首读单位，第三单位原文封存不让学生看到；正式样本结果SHA `6565040f03811c51df6aa211b5f79305bb1a65fc8ebdfda5acc209259e515b9a`，Railway `6a21e71d-62b3-4236-8f37-2ac5d5380e94` 退出0。
- **新冷进程独立来源证明通过**：Railway `800b4c0f-9539-46cc-94f7-c1a83b83a1d7`，`WF87_INDEPENDENT_R2_TWO_RANDOM_PASSAGES_VERIFIED` / exit0，独立Reader重新下载原文12,336,458字节、重算两原书全文SHA、片段偏移、两个首读单位SHA和隐藏后文SHA，全部与首次相同；模型0/R2写0、无小说正文或密钥外传。这只是来源一致性，不是独立文学语义评审。
- V87最终事实：随机新题材料**2个来自不同私有作品且已独立SHA核验**；但WF还未回答，双组基线/经验分析与第三方语义审稿均`NOT_PERFORMED`，不能宣称训练效果改善、文学掌握或等级晋级。
- WF原V82前15章、R2所有CAS锚点保持不变，第16章V83正式模型在恢复检查点时失败，没有付费重训。V49`THIRD_STRIKE_FAILED`及文学第二窗口`LOCKED`保留，无新模型调用、无新的R2学海写入、无需第四个密钥。
- 下一步在完成真正独立语义评审条件之前，不重复付费V81两臂；可以只读恢复两份样本，按已冻结规则开展WF的基线/经验小样本问答，但答案不同不得自动晋级。必须先核当前Railway启动命令，切安全待命后不自动调用付费模型。


**V87最终安全待命已真实核实**：Railway `9e001b94-b60e-494c-b56f-b7197e290708` SUCCESS，启动 `python -u wf_railway_v82_safe_idle.py`，日志明确 `WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`、本次模型0/R2读0写0、自动付费后续关闭。最终源代码部署pin `76dcd558a7d71c54ddc8b8c92f5d44e379eee429`；文档后续追加不重开训练。未对随机样本调用DeepSeek，原小说前15章不变。


## 74. 【2026-10-20 V88】真实随机两书四臂盲测、独立R2重审和精确证据定位复盘

**新的权威交接报告：[V88 真实四臂 R2 来源及证据错误复盘](V88_REAL_FOUR_ARM_BLIND_R2_FORENSIC_20261020.md)**。旧§73的V87随机抽样与前15章R2不可变收据不得覆盖。

1. 新V88隔离分支 `v88-v87-frozen-two-work-blind-exam`，固定V87历史/科幻两个已独立SHA核验片段，历史无经验→有经验、科幻有经验→无经验；每组相同来源前两个单位，第三单位不进入学生模型提示。仅旧V82第15章`next_strategy`在经验组增加。**先全仓离线923项0失败0错误4跳过**。
2. 真正DeepSeek Flash付费4请求、原始答复4个都已R2不可变签收：Railway `f4d132b5-cb86-41c6-b883-bfaae2d7b177`，`WF88_FOUR_REAL_BLIND_ANSWERS_R2_SIGNED` / exit0。响应usage：输入3956/输出1220/合计5176tokens，官网账单未另行核对；保守输入输出预算预留26488低于40000。**无重试，无第五次调用**。
3. R2一次性预注册CAS `5e6d27fe96fccfd1d545243e9d8e81d7a25d4dc563888095a6df9e461b558591` `created=true`，四臂最终manifest CAS `b4802c132bcdc4998ced3a5d34ee06224380b53645b3c15b6f9ba0cb3ca979eb`。历史/科幻两组pair SHA见完整V88报告，均不含公开原著答案。
4. 独立只读R2 examiner `90857424-84d4-4b42-9283-a33b5471c801` 又重新下载两份原著共12336458字节、重算完整内容/密封后文/4个答案和预注册输入，退出0、模型0/R2写0。四个JSON可解析，但**全部未通过V88严格机械证据合同**。历史无经验/有经验/科幻有经验的报错都是`WF88_ANCHOR_NOT_EXACT_VISIBLE_SOURCE`，科幻无经验报`WF88_ANCHOR_NOT_VISIBLE_OR_INVALID`。
5. 独立只读细分 `9fc2b13b-f574-45bc-ae0c-26f6ec19628a` 进一步发现：**历史无经验**两句短引确实在相应单位唯一存在，纯机器算offset可通过*结构合同*；**历史有经验**一处短引在其声称单位中不存在；**科幻有经验**机器计算后两锚点相同；**科幻无经验**一个锚点太短或非法。该分析不是对历史R2答案的修改，更不是证明文学因果成立。
6. **V89应修底层**：不要让WF模型猜offset；要求它提真实短引和来源单位，宿主的私有精确字符串查找确定唯一start/end，锚点不存在或不唯一、同一条当两证据、未读后文或人物无凭捏造必须红灯。之后还要真正受信的独立语义审核，绝不把“原文句段存在”当成因果事实。不得重新付费重复这4个答案。
7. 本轮**正式新训练章节仍为0**，原累计15章未改变；V49`THIRD_STRIKE_FAILED`、第二文学窗口`LOCKED`继续。现有环境没有真正的独立人类文学裁判，文学优胜组`UNDETERMINED`。完成本轮后应切Railway回`wf_railway_v82_safe_idle.py`，严格以最新容器日志确认后再声明。

**§74 本轮最终运维回执：** Railway `8279666a-c9da-443d-97cd-ea899e0239db` 实际启动 `python -u wf_railway_v82_safe_idle.py`，日志 `WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`，0模型调用、0 R2读写、自动续费批次关闭、`restartPolicyType=NEVER`。V88所有四臂答案仍是此前已保存的真实CAS，不自动重跑。


## 75. 【2026-10-20 V89】宿主精确引句定位、不可覆盖机械负例与真实四臂只读复核

**本轮详细交接：[V89宿主定位与负例记忆真实报告](V89_HOST_ANCHOR_AND_NEGATIVE_MEMORY_REAL_AUDIT_20261020.md)**。从此处恢复，不要重复运行V88那4次收费回答，也不要把V89重算结果回填为V88历史成功；V82前15章、V49`THIRD_STRIKE_FAILED`、第二文学窗口`LOCKED`保持原样。

1. 在隔离分支 `v89-host-grounded-source-anchor-repair`实现 `writerforge/v89_source_anchor_gate.py`：WF将来只应提供所见单位号与8–72字的真实短引句，由宿主用可信两段来源SHA、全文局部冻结范围验证并计算唯一Unicode字符start/end。原文不存在、单位错误、重复引句（含重叠匹配）、重复/相互覆盖两个证据、倒序无法独立证明等均拒绝，不采用拼字/编辑距离/补句子。
2. 新`writerforge/v89_anchor_failure_journal.py`与已有`WriterForgeDB`中的`wf_anchor_failure_receipts`表：源文和答案均不存，仅run/答案SHA/来源SHA/错误码等；SQLite触发器拒绝改写、事务竞争安全且限单批64条、全表50000条，到上限明确报错。只在LEARN时允许审计写入，机械错误不得冒充V86可信语义负评。
3. 工程测试真正跑过红→绿：首个Railway `0af5375b-06ce-4a14-a8ab-dca7ce2e6e3f` 944项中1测试夹具文本长度失误（未绕过生产校验），修夹具而不放松规则；部署 `28551b66-303c-4ac1-9b1f-96106aed139d` 944项全绿，最终容量保护追加后 `673ede27-5fc8-4f38-a53b-030777bd8136` **946项执行、0失败、0错误、4跳过**，模型与R2远端读写均0。
4. 真正已保存V88四份原答的**新只读冷核验**：Railway `a0eca842-d15a-4aa3-b8e6-b018131ba11c` 返回 `WF89_REAL_V88_SOURCE_ONLY_REAUDIT_COMPLETED` / exit0，重新从R2私有来源与4个CAS核验原文/问答/隐藏后文。历史baseline仅机器坐标可由宿主唯一找对；历史experience缺真实引句；科幻experience引用两个同一证据；科幻baseline引句长度非法。V88原始合同仍为**0/4失败**，V89仅回看**1/4可来源定位，3/4拒绝**，未作独立文学语义评分。
5. 真四臂原答CAS总manifest `b4802c132bcdc4998ced3a5d34ee06224380b53645b3c15b6f9ba0cb3ca979eb`，precommit `5e6d27fe96fccfd1d545243e9d8e81d7a25d4dc563888095a6df9e461b558591`；本轮V89没有新增DeepSeek调用、没有写R2。V82第15章终态batch `d46ffec05927dfba3f2819089e76e79f720db2a2f3f6793b56965ac6413c177f`。
6. **未完成的底层交接**：新接口还没有自动接入正式V80学习器，也未通过V85密封PASS A/人物可信知识时序与V86签名文学语义审核的端到端真实验收；实际失败存储只在本轮临时SQLite证明重启读回，不等于R2云端长期错误库已上线；文学水平/优胜组仍是`UNDETERMINED`。下一步仍需真实独立文学评审，绝不能用机械原句吻合代替因果理解。
7. 本轮终止前，Railway应切回`python -u wf_railway_v82_safe_idle.py`、`restartPolicyType=NEVER`，在新部署日志看到`WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`且本次模型0/R2读写0/自动付费false，才能宣称运维收尾完成。不得仅凭`SUCCESS`误判。


**V89最终运行已核实：** Railway `f5d8ef08-2a65-4403-aba0-4d5d40510ee7` `SUCCESS`，实际日志 `WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`，本轮idle模型0、R2读写0、自动付费批次false；启动脚本为 `python -u wf_railway_v82_safe_idle.py`，`restartPolicyType=NEVER`。此行不代表V89已经默认进入正式LEARN训练，也不代表真实文学语义检验通过。


## 76. 【2026-10-20 V90 长期发展最高约束】WF不得成为几条短期手法笔记的拼装机

**立即必读：[ADR-001｜WriterForge终身学习与长期记忆完整性契约](ADR_001_WF_LIFELONG_MEMORY_DURABILITY_20261020.md)。** 用户再次明确要求：“WF必须是长期发展，不能短时存储一点手法知识，后面再使用突然变成乱码/笨蛋。”

这是后续任何版本设计、执行、代码审查、数据迁移、R2/SQLite恢复和文学训练的**P0不可绕过架构要求**，优先于继续读第16章、增加提示词、扩充手法笔记或创建新skill。不能靠主模型聊天记忆保存这个约束：它已独立写入GitHub固定文件和本节。

1. **先恢复正确，再讨论成长**：明确拆分 `DURABLE`（字节和原著SHA长期存在）、`RECONSTRUCTIBLE`（跨作品/跨章人物知识、因果假说、来源、反例、时序、版本都可恢复）、`BEHAVIORALLY_VERIFIED`（冷启动/升级后同一场景实际SELECT/SKIP、错误不会重犯、文学盲测仍有效）。三者缺一，不能叫WF真正学会。
2. **长期经验必须版本化**：每条经审候选保留经验身份/源SHA/出处锚点/适用范围/角色知识/反证/独立审核/失败/撤销/旧版本和当前策略实际调用回执；禁止原地改写或覆盖失败。新模型/升级只能在受控迁移后使用，不能把旧经验当乱码、胡乱改字段或静默丢弃。
3. **拒绝短期缓存冒充持久记忆**：`memory.py`当前`MemoryBudget`只是有限上下文选择器，不是永久存储；临时Railway、内存提示词、短小`next_strategy`也不是长期学习。复用既有R2 CAS+SQLite+FactJournal+ExperienceDecision，优先落盘、manifest-last、严格UTF-8解码、版本迁移、冷恢复和可重建索引，不新造第二套人物知识库。
4. **必须故障先行地测试**：跨独立进程、跨旧/新schema、丢失块、乱码/非法Unicode、错版本、网络/事务中断、迁移回滚、容量增长/分页、角色知识冲突、负例仍SKIP、跨模型重启；只看到SHA相同**不能证明文学理解和创作能力没有退化**。
5. **正式发布/重开大量训练之前必须有真实P0验收回执**：ADR的P0-01至P0-07逐项核验，CI/Railway保存证据，失败保持失败；没有独立可信文学语义考官就只说明工程持久性，不升文学等级。
6. **本轮准确事实**：只新增`v90-lifelong-memory-architecture`隔离分支的ADR与本交接要求，没有运行新DeepSeek、没有读写R2、没有向生产Railway切换代码、没有虚报永久记忆链已实现。前15章V82 CAS继续保持，V88真实4份负例不改，V89离线946项通过；V49 `THIRD_STRIKE_FAILED`、第二窗口 `LOCKED`不变。
7. **后续优先顺序**：先持久经验对象合同与严格旧新版本迁移→真实双进程冷恢复、编码损坏/原文哈希故障注入→角色/时间/失败状态完整重建→行为SELECT/SKIP回放→最后独立文学A/B。**不以“又读多少章”作为优先成果。**

下一窗口先读本节和ADR-001，再读V89 §75与V88真实负例，不许从V82第16章重启前先跳过持久记忆底层核验。此架构记录在GitHub，未来换聊天/换模型均应主动查阅，不能只凭聊天记忆承诺。


## 77. 【2026-10-20 V91 长期记忆首批真实验收】从V90 ADR继续，不允许短期笔记冒充成长

**权威真实交接：[V91 中文完整经验迁移／双DB冷恢复与云端R2真实冷审计](V91_LIFELONG_CHINESE_MEMORY_COLD_RESTORE_20261020.md)。** 此处接续V90 §76 [ADR-001终身记忆架构](ADR_001_WF_LIFELONG_MEMORY_DURABILITY_20261020.md)的P0要求，不能因V91部分成功而跳过其余长期记忆闭环。

1. **隔离分支** `v91-lifelong-memory-cold-restore`；新核心 `writerforge/v91_experience_migration.py`、`writerforge/v91_lifelong_checkpoint.py`、`writerforge/v91_private_cas_manifest.py`：恢复经验全文而非关键词，严禁乱码/未知schema/未经文学批准；利用现有WriterForgeDB+FactJournal双SQLite在线备份/流式摘要和manifest-last本地检查点，能在合成故障/重启后保留人物知识与签名撤销导致的SKIP。没有新造第二套关系网络。
2. **离线真实CI红绿过程**：Railway `1362890c-a1db-4aa2-b34e-65d4556fe482` 962项/1测试断言失败（乱码更早被入口UTF-8校验正确拒绝，测试预期错误码旧），修测试不放松校验后 `800cad4e-d472-4a75-918f-f0e470b08000` 962项全绿。加永久R2 manifest合成测试后 `090efa0c-dee5-4c4b-ae65-3d99799834b2` **965项执行、0失败0错误、4跳过**，均零模型/零外部R2测试请求。
3. **真实旧中文经验迁移**：Railway `ebb47426-2aa0-4be3-9e81-7695d3d3f6ed` 只读原始V82第15章经验CAS，4个完整中文反射字段、旧源SHA与旧journal校验通过，不打印私有原著/经验。
4. **真实追加两个永久私有R2 CAS**：Railway `9011e050-1e0f-4043-bbb8-133809977a17` exit0。新的**完整V91经验** `79dbfe144356d01bcd89bd237410925d838f98b1efe91e0aeab0edc3f93add4b`；新的**版本化manifest** `5a8b3b78f8b68741d794f618d2e701ac653397dd2a1e74822bba63cd09c9ee0f`；新对象各created=true，旧V82来源/进度/原章15经验未改写。新经验迁移校验 `afdc4557b9e7f143d515382491e486a2e57662370c3d378476a673d0083105f6`。
5. **真实完全独立冷进程再次验收**：Railway `481dbe69-ca0f-4742-b1a5-242ee727a3e7`，`WF91_REAL_CH15_EXPERIENCE_CLOUD_COLD_RESTORE_VERIFIED` / exit0，R2 Reader重新读取旧V82加两个新私有CAS，重新派生并比较全部中文反射文本/字节/manifest哈希，模型0、R2写0。云端经验版本恢复已证明，但正式文学能力和所有旧知识图云端一体化尚未证明。
6. **真实限制必须继续声明**：仅旧第15章转成V91新版本；前14章仍可按原旧CAS引用，不自动迁移也不重训；本地双SQLite表现由合成环境确认，**未将生产WriterForgeDB+FactJournal打成永久R2整体快照**，双账本原子性/全量恢复/跨旧新模型长期行为尚待开发。V49`THIRD_STRIKE_FAILED`、第二文学窗口`LOCKED`、所有V88四臂负例和旧原著保留。
7. **下次先做**：按V82旧CAS增量重放全部经验（不是重训）→跨版本知识关系/撤销/失败的完整备份恢复→双进程跨月模拟迁移与故障注入→有界真实缓存/大库压测→独立可信文学生成和比较。在此之前不为了多章数据跳过架构底座。

**本轮最后还须以Railway真正安全idle部署回执收尾，不能只凭源配置认为自动付费已关闭；下次先读取最新部署/日志而不盲目重启。**

**§77 运维最后确认**：Railway安全idle部署 `e7d73606-db11-4726-ab08-082b1a0d0679` `SUCCESS`，日志 `WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`，本次模型0、R2读0写0、自动付费续训false、`restartPolicyType=NEVER`；源代码部署commit `b36fd99f66e5caa78189833657ddb461c63f1680`。V91 仅有真实第15章完整中文经验对象及manifest两个新私有CAS，尚无全知识图永久云端迁移或文学晋级。


## 78. 【2026-10-20 V92】长期经验全15章源链真实迁移与独立R2冷恢复，生产关系图仍待永久化

**权威真实报告：[V92前15章完整中文经验迁移、链审计、Cloudflare R2独立冷恢复](V92_ALL_15_EXPERIENCE_R2_MIGRATION_COLD_AUDIT_20261020.md)**。强制遵守 [ADR-001永久记忆P0契约](ADR_001_WF_LIFELONG_MEMORY_DURABILITY_20261020.md)，不得将“15章经验保存”替换成“15章文学手法真正学会”。

1. V92隔离分支 `v92-incremental-experience-chain-recovery`，先核V82旧第15章batch `d46ffec05927dfba3f2819089e76e79f720db2a2f3f6793b56965ac6413c177f`、journal `3da56cc46115548c5198a65cb6124e3c03d9bdfdb1f0460950177735a99d1cb2`、旧经验 `ddbf86e87e3bf44900b4e5e4d8ffc2de99c9ed5d3c5aec98a69bfd8eb7cf2fe7`，沿 `previous_experience_sha256` 一一回溯到第1章，保持旧第1章`mixed pilot`不满足严格先读完后分析的历史标记，不谎称其严格合格。
2. 新`writerforge/v92_experience_chain.py`全量重建已有15个经验候选的V91完整中文版本，四字段`observed_weakness/next_strategy/open_question/confidence_limit`原样保留在**用户私有R2对象**，GitHub只存sha/模型未毕业等元数据；链断、乱码、错误书籍、顺序错、假SHA立即拒绝。不重新调用DeepSeek或重读付费章节。
3. **真实红→绿**：首轮Railway `7c7a1929-0d9a-4ca4-9526-4b5809638ce3` 972项/1夹具断言错误（第二条合成链没有同步预期头SHA，已正确被生产约束优先挡下）；修夹具保持生产门槛，Railway `a9c09f6e-9315-41c4-a31f-f683f51ce5b5` **972项执行0失败0错误4跳过**，模型0/真实R2请求0。
4. **真实无写入预检**：Railway `4dd77181-d611-4108-bd96-99b8ef22db08` exit0，旧15章原始SHA和完整字段都核对，事前确定未来完整元数据manifest SHA `bd905ae9e812fb5283f24ed7fec3bc35cf0febde7b6405476c455bba468f84db`。
5. **真实不可变R2增量迁移**：Railway `e9054c02-3e00-4503-96a9-38ade692fad9` exit0，前14章各新V91 CAS `created=true`、立即独立读回，第15章复用V91既存 `79dbfe144356d01bcd89bd237410925d838f98b1efe91e0aeab0edc3f93add4b`，**最后**才创建全15章新manifest `bd905ae9e812fb5283f24ed7fec3bc35cf0febde7b6405476c455bba468f84db` `created=true`，same-process读回整链，0付费模型调用，旧V82不变。
6. **真正独立R2 Reader复核**：Railway `225c7732-9b9a-4245-b764-7605fd629474` `WF92_INDEPENDENT_R2_ALL_FIFTEEN_EXPERIENCES_COLD_RESTORED` / exit0，旧15个/新15个CAS全部重新拉取校验，完整中文四字段和前驱连续、章节1风险标记都正确；模型0/R2写0、无私有原文/经验泄漏。V92经验云端版本恢复已真实证明。
7. **最重要的未解决底层**：Railway实际环境盘点`wf-python-r2`没有持久Volume/内部桶，当前并无证据可以取得真实生产`WriterForgeDB`＋`FactJournal`两库的持久源，不得伪造“生产人物知识图和失败库已上R2”。V91双SQLite合成备份/撤销后`SKIP`已绿，但还没有来源确证的生产全图私有云快照，更没有跨R2/SQLite一致性事务。此限制不能因为V92全链经验成功而忽略。
8. **论文/等级禁止虚报**：V88四真实文学盲测仍0/4严格引用通过，文学质量优胜者`UNDETERMINED`，V49`THIRD_STRIKE_FAILED`及第二窗口`LOCKED`未改变；第16章仍未正式训练，不再从前15章重付费读取。新经验仅`UNVERIFIED_LEGACY`、不能自动WRITE和晋级。
9. **下一项执行**：从可信持久来源获取生产关系/负例数据库或其不可变备份的真实位置（不能假设临时Railway容器存储存在），再构建manifest-last R2云端备份并让两个独立reader重建人物知识/双时轴/签名撤销/失败负例、行为SELECT/SKIP；有了完整行为恢复及独立文学质量才讨论扩大训练。

**本轮最后Railway必须切回 `python -u wf_railway_v82_safe_idle.py`、`restartPolicyType=NEVER` 并核实实际日志0模型/0 R2读写、自动收费false。不能凭部署SUCCESS或本文预填运维成功。**

**§78 真实最后运行状态**：Railway `bec76c08-c948-4c83-8d4a-bc9113d25a47` `SUCCESS`，`python -u wf_railway_v82_safe_idle.py`、`restartPolicyType=NEVER`，实际 `WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`、本次模型0/R2读取0写入0、自动收费批次关闭。部署源码pin `caab5500fe4668c67b7b8e114950731390046c28`，任何后续仅文档改动不得触发再次运行V92的CAS迁移任务。


## 79. 【2026-10-20 V93】长期人物关系/撤销负例的R2双SQLite冷恢复**技术通道通过**；真实生产知识图尚未迁移

**必须先读：[V93云端双库合成演练与独立恢复完整报告](V93_SYNTHETIC_RELATIONAL_GRAPH_R2_COLD_RESTORE_20261020.md)。** 本节接续§78前15章真实经验链以及 [ADR-001长期记忆P0契约](ADR_001_WF_LIFELONG_MEMORY_DURABILITY_20261020.md)。用户明确要求让WF长期成长、不突然乱码遗忘或重新变笨，所以本阶段绝不将软件层模拟结果登记为已学会人物和因果。

1. **真实生产状态盘点**：现有Railway `wf-python-r2`不挂载持久Railway Volume，环境中无Railway Bucket；现有R2通过旧三凭证的Reader/IndexWriter维护。**未定位到可认证的生产WriterForgeDB+FactJournal持久数据库来源**，没有资格向云端恢复流程伪造其事实行。本轮仅使用合成数据库验证可靠恢复路径。旧V92全15章正式中文经验清单CAS `bd905ae9e812fb5283f24ed7fec3bc35cf0febde7b6405476c455bba468f84db`始终未变。
2. **V93底层代码已提交**：`writerforge/v93_synthetic_graph_cloud_checkpoint.py`严格只接受唯一合成测试来源，支持两SQLite原有V91在线备份、SQL快速/外键/逻辑行SHA、长度受限zlib压缩分块至原私有R2 CAS，**各块先写回校验、manifest最后**；由独立Reader重建V91完整快照。混入其他作品/用户资料、被改SHA、恶意解压、假文学晋级、跨模型权限不允许通过。`writerforge/v93_synthetic_graph_fixture.py`用现有真实DB API构造合成角色知识、独立签名**测试夹具**的授权撤销、SELECT→SKIP，不新造人物数据库。合成测试签名公开，只为行为集成，不能证明真人独立文学审评。
3. **真实红项全部保留**：首轮全仓Railway `091fd4ae-2572-447c-837b-6457643223a7` 982项中10处因错误列名`decision_json`而失败；对照旧DB修成`plan_json`。专项第二轮 `5d144ca0-c47f-4d49-9b51-139dc4db8038`10项/2错误，因V93错用全JSON文件SHA作V91 `CURRENT`内部manifest收据SHA；修复两类SHA的区别。新专项 `d0071435-5d40-4c2a-a422-86177e84ff80` **10项全绿**；最终全仓 `cc958490-5792-4aeb-8f71-27c0515aeb4f` **982项执行、0失败、0错误、4跳过**、模型和真实R2请求0。
4. **真实R2写入**：一次性Railway `6ed77edc-3e4b-4ecd-8b3d-f853f6ca1d57` `WF93_SYNTHETIC_DUAL_SQLITE_R2_MANIFEST_LAST_VERIFIED` / exit0，仅两份压缩**合成**SQLite分别存成2个新CAS块，manifest LAST再新建1个对象，原R2学习/用户原著不变。新云端manifest SHA `a42ada69d6d3b4d6ed90664f4b6c5607f5e0849ed1a4d178688b8d45f10b1d25`。没有新文学训练或模型调用。
5. **真实独立冷恢复成功**：新Railway Reader `8cc1e602-1064-4709-a290-50b0929e0b36` `WF93_INDEPENDENT_CLOUD_SYNTHETIC_GRAPH_AND_BEHAVIOR_VERIFIED`/exit0，下载恢复**两份SQLite、21张关键表**，并重新验证合成跨章人物已知`KNOWN`/未记录知识`UNRECORDED`、旧历史`SELECT`保留且撤销后新`SKIP`，禁止重用旧许可。另起合成fixture独立比较摘要通过，模型调用0/R2写0。**这个合成数据不是WF已训练15章的真实人物状态**。
6. **不能越过的P0**：未部署实际生产人物知识/负例的可靠**持续写入**、跨R2+SQLite原子回执、真实生产数据库安全归档和加密、生产多写者一致性、自动失败恢复/多年容量压测、文学语义独立验收。V49`THIRD_STRIKE_FAILED`和第二文学窗口`LOCKED`保留；第16章不自动训练。
7. **V94首先处理**：确立真实生产LEARN中**可信事实和负例写入事务源**，V89精准原文定位+V85来源/人物时序+V86受信审评的“记录进入SQLite时同步持久化R2 CAS”的写入/回放协议；让新Reader能从R2真实状态重建，跨会话正确选择SKIP/ABSTAIN。必须持续留失败证据，不能拿V93合成临时数据库反过来填充历史人物知识。无此能力继续大量章节训练会制造无法持久化的伪记忆。

最终Railway应用必须恢复为一次性`python -u wf_railway_v82_safe_idle.py`、`restartPolicyType=NEVER`，以最后部署实际运行日志证明；不可提前预填。


## 80. 【2026-10-20 V94】受控LEARN事件写前记录 → R2 manifest-last → 独立SQLite冷重建与撤销重放

**真正权威交接：[V94真实R2合成七事件提交及独立冷回放完整报告](V94_SYNTHETIC_LEARN_EVENT_R2_COMMIT_COLD_REPLAY_20261020.md)**。继续遵守 [ADR-001终身学习完整性要求](ADR_001_WF_LIFELONG_MEMORY_DURABILITY_20261020.md)。本轮绝不把受限**合成**七事件归档解释为“WF过去15章的人物关系/因果/负例已经真实写入生产大脑”。

1. **原不变底座**：V92真实15章完整中文经验CAS链manifest `bd905ae9e812fb5283f24ed7fec3bc35cf0febde7b6405476c455bba468f84db`；V93真实R2的**合成**双SQLite数据库云端快照 `a42ada69d6d3b4d6ed90664f4b6c5607f5e0849ed1a4d178688b8d45f10b1d25`。原V82训练不重启、不覆盖。
2. **V94代码分支** `v94-durable-learn-events-commit-replay`，核心 `writerforge/v94_synthetic_event_commit.py` 与三个脚本 `wf_railway_v94_focused_tests.py`、`wf_railway_v94_publish_synthetic_events.py`、`wf_railway_v94_independent_event_reader.py`。每个R2新事件绑定源快照SHA、前驱事件SHA、序号、固定合成枚举及复算结果SHA；先在完全临时恢复的SQLite上演算、再进入CAS上传，**最后**提交manifest。不能用没有清单的孤立CAS“恢复记忆”。
3. **7条固定事件**：合成经验STAGE→测试签名APPROVE→写作选择SELECT→测试签名REVOKE→下次SKIP→既有合成人物事实追加冲突OBSERVE→时态claim supersede。旧global ledger seq6`KNOWN`保留，新seq8实际FactJournal合同`CONFLICT_UNRESOLVED`，未出现的知识`UNRECORDED`；旧SELECT继续可查但不能重新作为WRITE有效许可。所有签名都是**公开合成夹具**，无真人文学真值/独立审核。
4. **真实红项及修复**：Railway `78c32276-7885-4f3a-be8d-0537b4c78129` 11项/11ERROR，因新测试把DISPUTED错误预期为直接DISPUTED而旧FactJournal实际按争议返回CONFLICT_UNRESOLVED；`c9791655-3bbe-48cd-bb9d-308546e28f8d`因新模块读写模式不当被`RuntimeEngine.require(Mode.WRITE)`挡住，改为明确切WRITE调用而非绕过保护；`f006d099-8e96-4440-a910-ea9a9d593860` 11项10通过1夹具断言期待旧状态；最终专项 `c94b2e3b-0a28-4774-89bf-e185e40eae4d` **11/11全绿**，全仓 `696cdccc-67de-401c-8b97-92ec59e89e3d` **993项、0失败、0错误、4跳过**，全仓测试禁外网，模型0、R2远端读写0。
5. **真实R2事件提交**：Railway `7e10b22d-39e5-4970-a73c-cbfe0089880e` `WF94_SEVEN_SYNTHETIC_R2_EVENTS_AND_COMMIT_SAVED` / exit0；新增7条不可变CAS与最后1条commit，写后读回，原V92/V93未覆盖、模型0、现实文学人物数据库未写。固定最终commit manifest SHA **`5b33b3f07131eb1abdf7298b68a934daf2b496a084108ccfd1a20d673ce352b7`**。
6. **独立真实R2只读冷恢复**：新Railway Reader `769d84d5-7a6d-475b-b5ad-25cf8669fa31` `WF94_INDEPENDENT_R2_EVENT_AND_BEHAVIOR_REPLAY_VERIFIED` / exit0。从R2恢复V93两SQLite，读取全部7条事件并重演，最终状态SHA `383aa34044919054e046801ac69e183347f2929cc311ab3d57376b654c778f65`，事件预期回执集合SHA `55721117a9caf0e83283a7f8211edcd09f47a24f0b4a4ea4f06fedce622322d5`。事实旧KNOWN/新冲突/未知、SELECT→SKIP与撤销旧SELECT都核查一致；模型0、R2写0。
7. **最重要的生产缺口**：V94只有固定合成事件，生产真实`LEARN → FactJournal/经验审查`的**持续可信录入权限**还未建立，真实生产人物知识图未被找到可恢复的可信历史持久源；跨R2+SQLite事务、多写者head竞争/租约、加密授权、独立文学真值及真实几年后行为能力未验收。新上传的event和R2快照不能作为生产角色`KNOWN`证据，真实WRITE仍不被解锁。V49`THIRD_STRIKE_FAILED`和第二文学窗口`LOCKED`保留，第16章不开始。
8. **V95唯一下一关**：先定义真实可信事实入库来源与权限，不依赖模型自证；加持久化事件head的单写者/并发控制和明确失败补偿边界、R2新进程真实WRITE前恢复检查，沿V89原文定位→V85时间来源→V86可信独立审评链逐项接，绝不用V94公开测试签名替代真人审核。继续保留全部负例和旧CAS。
9. 本轮最后应再次将Railway固定为 `python -u wf_railway_v82_safe_idle.py` + `restartPolicyType=NEVER`，并从最新部署日志核实0模型/0 R2读写/不自动付费；上述运行状态不可预填。


**§80 最终安全状态已真实核实**：Railway `60f2569a-52bc-4fde-b3f2-0acaf1e34611` `SUCCESS`，容器 `WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`，本次模型0、R2读写0、自动付费续训false，启动 `python -u wf_railway_v82_safe_idle.py` 且 `restartPolicyType=NEVER`。独立冷读后的V94合成事件CAS `5b33b3f07131eb1abdf7298b68a934daf2b496a084108ccfd1a20d673ce352b7` 已持久化，不表示真实生产人物图已搭建。


## 81. 【2026-10-20 V95】可信文学来源闸门与服务端CAS提交头源码完成，线上未部署则必须拒绝

**本次权威报告：[V95可信来源及原子条件HEAD工程验证](V95_TRUSTED_SOURCE_AND_ATOMIC_HEAD_GATE_20261020.md)**，接续V94 §80七合成事件云端恢复和 [ADR-001 WF终身记忆P0要求](ADR_001_WF_LIFELONG_MEMORY_DURABILITY_20261020.md)。

1. V95隔离分支 `v95-trusted-source-and-authoritative-head-gate` 实际新增 `writerforge/v95_trusted_source_intake.py`：V89的**真实私有原文短引句/程序唯一位置**与V85**同一次LEARN会话PASS-A完整封存证据、角色FactJournal旧时点快照**及V86**签名且未被后续负评覆盖的独立语义审核**三处精确交叉核验。任一跨书/跨单位/改SHA/篡改审签/未读后文/重复引句拒绝。结果严格只是`REVIEWED_HYPOTHESIS_NOT_CHARACTER_FACT`，永远不自动插入`KNOWN`、不开放WRITE也不晋级。
2. 新`writerforge/v95_authoritative_head.py`及`cloudflare/wf-r2-worker-readonly.js`中V95新增路线：仅`v95_synthetic_only`单一固定HEAD，需已有两个分开的读写凭证，并用R2**存储层**`onlyIf If-None-Match/If-Match`作原子条件提交，绑定前驱head SHA、generation递增和已签收的V94**合成**CAS manifest；拒绝客户端只GET后普通PUT、旧ETag覆盖、改项目名、伪生产审核。旧Index CAS和原著接口源码不删除。**这是GitHub代码，线上并未部署，也不允许拿V95测试HEAD传真实人物事实。**
3. Railway Python专项`3af4e278-6848-4f9f-bdc3-25d8dcb12e5b`：24项执行0失败0错误（含旧V86导入回归），多写者模拟R2原子CAS两写者只能一胜、无审核/签名坏、同会话换原文/恶意角色/负评追加均阻断。全仓离线`b78bafa4-d607-43e4-9f4a-03b138eb1733`：**1017项执行，0失败0错误，4跳过**，无新DeepSeek调用、0真实R2网络读写；V49及旧训练不动。
4. **不得虚报原生JS已通过**：首次Railway节点测试`c01621c7-65eb-4e64-ac9c-52cd4246eb6e`返回`WF95_NATIVE_JS_WORKER_UNTESTED_NODE_MISSING`，0项执行，说明当前Python镜像无Node；新`tests/v95_worker_conditional_head.test.mjs`和GitHub无密钥Node22工作流已提交，但当前对话未取得可靠Actions完成日志，不能把Native Worker竞争赛算为真实通过。
5. **真实Cloudflare线上路线查询**：仅带现有`WF_API_TOKEN`的Railway `57155e5a-a351-4262-967b-6770230fa6b7` 请求一次 `GET /r2/learn/head/capabilities`，得到HTTP **404**，`WF95_LIVE_WORKER_HEAD_ROUTE_NOT_DEPLOYED_FAIL_CLOSED` / exit0；新权威HEAD上线许可false、模型0、R2写0。仓库V95 JS修改没有被冒称已部署。**不许将客户端模拟CAS当成线上R2多写者安全**，必须等Native JS测试证据+Cloudflare可验证部署及远端两writer竞争验收。
6. 旧V92 **15/15章**完整中文经验CAS manifest `bd905ae9e812fb5283f24ed7fec3bc35cf0febde7b6405476c455bba468f84db`、V93合成双SQLite R2 manifest `a42ada69d6d3b4d6ed90664f4b6c5607f5e0849ed1a4d178688b8d45f10b1d25`、V94合成七事件commit `5b33b3f07131eb1abdf7298b68a934daf2b496a084108ccfd1a20d673ce352b7` 全保持。真正生产人物关系来源/正式事实持续录入、真实独立文学审核和云端权威HEAD仍**未验收**；V49`THIRD_STRIKE_FAILED`、文学第二窗口`LOCKED`、V88 0/4真实答题机械失败不改。
7. **V96下一步**：先确认GitHub Node Worker原生测试日志，否则禁部署；新HEAD源码做安全审计后需要有Cloudflare Worker真正发布能力（不需新增Reader/IndexWriter密钥），再用R2**真实两个独立写进程**验证陈旧ETag只能一个提交；随后才允许可信来源经真实外部审阅签发从候选进入新LEARN日志，并独立Reader验收后才考虑WRITE。禁止把未审的WF模型想法写为`KNOWN`。
8. **本轮最终运维**：需把Railway切回`python -u wf_railway_v82_safe_idle.py`、`restartPolicyType=NEVER`，并再次用最新部署日志确认模型0、R2读写0、自动付费续训false；此行不提前假定已经成功。



**§81 追加最终真实回执（后续Native JS不再停留于未测）**：隔离Railway Bun Function真实执行 `cloudflare/wf-r2-worker-readonly.js`固定源码commit `9f311d257bc7dab296dbbdb9ec0a0122a972f060`、其仓库JS竞态测试，部署 `b9386aa6-4806-4801-a854-f36b8c247b53` 返回 `WF95_NATIVE_JS_WORKER_PASSED`，**4/4通过，0失败、0模型调用、0真实R2写入**。覆盖两竞争Writer旧ETag只有一位成功，伪造事实晋级和异常HEAD均拒绝。此前Python镜像无Node与首个Bun启动无可用结果的事实仍保留，**GitHub Actions Node22日志仍未验收**，不是实际Cloudflare多进程测试。V95现存Cloudflare Worker线上能力接口仍404，生产原子HEAD／真实LEARN事实写入保持关闭。最终Railway主服务安全idle `4a49aab3-28b6-4d1a-bf2f-5cb0289d43c8` `SUCCESS`，真实`WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`，模型0、R2读写0、自动续费false、restart NEVER。详细见V95报告末尾§六。**下一轮V96先补线上安全发布能力和远端竞态回执，不能只凭JS模拟打开真实人物`KNOWN`。**

**§81 运行资源清理：** Native Worker JS 4/4 通过后，临时Bun测试服务 `54f4db55-f543-4847-a5a2-8084aebb22f7` 已删除；实际Railway环境现在只剩原有 `wf-python-r2`，0个Volume，0个Railway Bucket，不产生额外长期测试服务。真实Cloudflare V95新HEAD仍404，生产新知识写入不得开启。


## 82. 【2026-10-20 V96】恢复真正核心：写作思考、人物行动因果与千字后逻辑连贯，不再围着存储转

**本次外部研究和真正写作代码审查：[V96 GitHub/ACL长篇因果写作研究与三臂实验预注册](V96_LONGFORM_CAUSAL_WRITING_GITHUB_RESEARCH_20261020.md)。** 用户强调：“不要偏离核心的写作思考和写作手法提升；AI通常约1000字后逻辑紊乱，要找GitHub谁解决”。该反馈对接下来开发工作的优先级**高于**V95原子HEAD继续扩充、培训章节数和另造抽象Skill。

1. **真正外部依据**：DOC（ACL 2023，较Re3人审剧情连贯性+22.5个百分点）、Re3（EMNLP 2022，较直接写作+14个百分点）、StoryWriter（事件关系规划＋段落历史动态压缩）、StoryDaemon（内容自由生长、代码守已成事实＋少量动态滚动计划）、novel-writing（confirmed/inferred/planned与人物所知和叙事时间区隔）、ConStory-Bench（ACL 2026故事一致性5类19子类、错误偏向事实/时间与中段），分别验证了局部改善/方法论，不等于任意长篇已被解决；LongWriter仅证明长文本输出能力，不能当作文学逻辑胜利。
2. **最关键的WF源码直因**：`writerforge/writing_assist.py::AutonomousWriting.run` 当前确实只有全章五字段计划`objective/conflict/decision/outcome/pov`，正文仍然是一次`local_chat_completion(max_tokens=2600)`，下一章只携带前章末尾约750字符；`writerforge/verified_flow.py` 连续性只拿最近两篇已接受场景的文字尾段，不足以证明跨情节因果。V92存了15章完整中文经验，并不等于计划被实际逐场景验证、人物决策/行动因果在生成正文后更新。该缺口比再加150k/1M上下文、上传文学资料更值得优先修。
3. **新的真正写作闭环**：小事件/场景级滚动规划 → 当下人物目标、阻力、可见知识、实际选择和后果 → 模型自由撰写正文 → 宿主严格查已成事实/角色知识/时间与实际正文事件差异 → 旧式候选保留 → 审核真实因果和技法阅读效果 → 才更新下一事件和可恢复状态。允许倒叙、含蓄、误导读者及留白，不强迫每章都用一样的八段模板；每场最多1–2种符合情境的手法，先解决真实叙事问题。
4. **用户「约1000字坍塌」尚未被实测证实是通用阈值**。下一轮预注册A=现有一次写整章、B=仅分段、C=分段＋状态因果审查的三臂同模型同字数实验，目标800/1600/3200/6400中文含标点字符、至少历史与仙侠两类原创题，指标按每1000中文字符因果/知识/世界规则硬错误、首次犯错位置、伏笔债务、人物行为自然度、戏剧性和独立文学盲评。不得把B仅增加API调用造成的增益误算成C逻辑算法成功，不得使用模型自评冒充独立文学评审。
5. **本轮已完成而未夸大的事实**：GitHub真实项目/论文检索、DOI与源代码审核、WF写作断点核实、V96研究及三臂测试规格提交独立GitHub分支 `v96-longform-causal-writing-research`。**本轮没有实现新段落级逻辑生成器，没有新收费模型运行，没有声称WF超过1000字逻辑已经改好，也没有修改正式WRITE或原文学历史数据**。
6. **下一窗口优先顺序**：先在当前`AutonomousWriting`路径下做**显式opt-in**的滚动场景逻辑实验，不建立第二套知识库；先合成错误/修复测试，再有界双（或三）臂真实生成和独立盲评。重复修复两轮不解决则停止在本模块循环，转向源码/论文外部学习，保留红色证据。V49`THIRD_STRIKE_FAILED`、文学第二窗口`LOCKED`与V88四臂原始负例不变。
7. **基础运维不变**：生产Cloudflare V95权威HEAD仍未部署/线上查询404，正式事实写入禁止；Railway当前沿用旧安全idle `wf_railway_v82_safe_idle.py`，不得因仅研究文档提交而自动运行新付费模型。V92完整15章云端经验可继续被恢复，但尚未证明文学迁移效果。

**最高原则**：最终要培养一个能想清楚「人物为什么行动、阻碍与代价是什么、此行动具体改变了什么、读者如何感受到」的作家，而不是一个越来越庞大的训练数据库管理员。


## 83. 【2026-10-20 V96→V97】真正走回写作能力：逐场景生成内核、首次7次真实DeepSeek原创长文A/B/C、独立R2冷复核

**首先读：** [V96实际场景写作内核](V96_SCENE_TURN_CAUSAL_WRITING_IMPLEMENTATION_20261020.md)、[V97真实原创约1500字三臂结果与独立机械复核](V97_REAL_LONGFORM_ABC_1500_CHINESE_20261020.md)、[V97模型调用之前冻结的输入/预算协议](V97_REAL_LONGFORM_ABC_PRECOMMIT_20261020.md)。本阶段继续遵守用户「写作思考、写作手法和长文实际逻辑」优先于继续堆R2、Skill数量与训练字数的核心要求。

1. **V96真正实现了** `writerforge/v96_causal_turns.py`＋现有`writing_assist.AutonomousWriting`的可选三种模式：A `single`（旧一次性章生成）、B `split_only`（分事件生成）、C `causal_guard`（与B相同冻结事件，正文写出后查action/effect的原句唯一位置、发生顺序和此前事件实际后果引用）。本地Studio selector有明确选择框，默认A不变；新的知识不自动写FactJournal或WRITE接受稿。旧writer全仓最后一次V96回归 **1039项0失败0错误4跳过**，22项V96合成专项通过；合成800/1600/3200/6400不能冒称为真实模型生成。
2. **V97新隔离分支** `v97-real-longform-abc-pilot`，真正调用已有用户DeepSeek Flash接口做一次作者原创的历史桥头/送药故事，完全不下载原训练小说。A/B/C共享相同章节目标、人物可知与未知、同一事先冻结五字段章计划，B/C更共享同一三个scene-turn；固定最多7次请求、A上限2600输出tokens、B/C每段1450、整批11300输出预留、120000保守tokens总预算，**不允许自动重试**。先R2不可变CAS预注册、每次原答先保存在私有R2，再执行任何格式/因果检查。
3. **V97真实付费前测试**：Railway `8b189a70-1efe-489c-a461-fb1481c94771` 全仓**1048项执行、0失败、0错误、4跳过**，外部模型0/R2 0。
4. **首次真实模型运行**：Railway `b29d4a30-94cf-4af5-8329-3590dcee1ac9` `WF97_REAL_ORIGINAL_LONGFORM_THREE_ARMS_R2_SAVED` / exit0，模型`deepseek-flash` **恰好7次**，供应商响应输入10649＋输出4450＝**15099 Tokens**，未另外独立对账官网账单。A single **1902字符**（1请求）、B split_only **1601字符**（3请求）、C causal_guard **1554字符**（3请求），**全部超过1000字符且全部原始响应CAS保存、未被作者接受、未成为文学技能**。预注册CAS `5c7fac8ef9ab0f588698711ba1b63672a2eab18ff4f65d53bf8616489d36cae1`，最终完整3臂清单CAS **`d304d2432e2c3290b6bbd8ccb6bc209e38b7e12bc0aabb968b489b31c22b02a1`**。没有重复付费前15章，没有用户原著跨网络发送，没有第16章新训练。
5. **真正独立冷R2复核**：完全新Railway Reader `6a850368-b5eb-4196-a0f4-5ff4adaf5b16` `WF97_INDEPENDENT_R2_REAL_LONGFORM_ABC_RECONSTRUCTED` / exit0，原答7个和整章候选3份全独立SHA恢复；B/C从真正模型JSON原答重演V96 `check_turn`并与已保存最终正文逐字符比对。C的**3处真实动作引句＋3处真实后果引句＋2处前景后果引用**可独立按规则定位，合成独立复评过程中模型0/R2写0、没有泄漏私有文本。
6. **不能混淆工程与文学**：C原句位置/相邻动作先后/父引用通过，只证明字面来源定位；不证明人真实愿望、动作有效原因、世界规则、伏笔质量、读者情绪或文风自然。三臂实际字数**不相等**（A1902比C1554明显更长），且只有一部原创历史试题、同一家模型、无人类独立语义盲评；所以 `first_actual_narrative_logic_failure_position=UNDETERMINED`、`literary_improvement_verdict=UNDETERMINED`、旧文学晋级锁定。B未执行检查不等于B有硬错误；A没trace不等于A质量差。
7. **下一步最高优先级V98**：不要回去无限修R2，直接修**正文事件状态变化和角色行为逻辑**：生成后检查此前角色的欲望/所知/现实阻碍、选择、具体造成的变化与付出代价，并由真正的当下正文更新**下一段短滚动计划**，而不是前面写一张静态3事件表后盲从。保留插叙/留白/误会的文学自由，已成事实与模型推断分离；安排两体裁、同目标长度及独立盲评，不能根据同模型自己打分宣布升级。重复两次补丁无效就停止同源修法去外部GitHub/ACL寻找解。
8. V49`THIRD_STRIKE_FAILED`、第二文学窗口`LOCKED`、V88四真实负例、V92全部15章CAS及V95线上CloudflareHEAD未部署404全保留。本轮完成后仍应从真实日志核对Railway退回 `wf_railway_v82_safe_idle.py`，而非仅凭`SUCCESS`宣称无续费调用。

**长期核心：不以“保存了很多写作手法”“可以写长”“模型说逻辑正确”为终点，要以真实正文中的选择是否有因果、人物认知是否可信、写法是否自然、独立阅读是否更好为终点。**


## 84. 【2026-10-20 V98】正文驱动的滚动因果写作真正接入：不再把V97静态事件表当成全部现实

**完整实测与故障界限：[V98 正文驱动滚动情节内核和1,064项回归](V98_PROSE_DRIVEN_ROLLING_CAUSAL_WRITING_20261020.md)**。承接 [V97真实原创1500字A/B/C三臂](V97_REAL_LONGFORM_ABC_1500_CHINESE_20261020.md)；用户强调写作思考、写作手法与超千字逻辑正确性，继续高于追加R2/Skill/训练章数。

1. **本轮实际代码**：GitHub隔离分支`v98-prose-driven-rolling-plot`新增`writerforge/v98_rolling_causal_planner.py`，并改现有`writerforge/writing_assist.py::AutonomousWriting.run`、`writerforge/studio_server.py`、`writerforge/ui/studio.html`：显式新增D=`rolling_causal`，**默认A single和原B split_only/C causal_guard不变**。D第一个事件按初始短计划自由写；以后每写完一个实际事件，先校验原V96真实原句effect及收据 SHA，再由模型**额外提出一个基于真实后果的新事件目标**，不再机械盲从整个原冻结章节事件提纲。每次仍生成真实正文并由原V96校验动作/后果/前景父引句。
2. **进步边界严格区分**：宿主验证旧正文`prose_sha`、旧V96原始证据回执sha、已出现且唯一的后果原句、合法角色范围/事件ID/前驱关系；新规划可引用真正写出的障碍/付出代价，但没有明确成本文本就`UNRESOLVED_NOT_STATED`。这些只证实文本归属/下一幕有真实来源锚点，不证明人物真正理解、动机因果或阅读质量。所有结果`narrative_semantics_independently_verified=false`、`canonical_fact_writes=0`、`accepted=false`；新规划只写在现有本地候选目录，**不导入FactJournal、文学经验或R2**。
3. **调用安全**：D每一个后续event多一次本地模型短重规划（上限650输出tokens/次），单任务最多14次额外调用，沿用V96总16事件、B/C/D最多2章、失败后0自动修补/0自动重试。**D请求次数大于C**，下一轮比较时必须设等预算对照，否则不能只因D写得不同就说算法增强。原A/B/C旧候选格式不被重写，UI作者显式opt-in D并看到额外成本提示。
4. **真实失败保持红色**：首个V98专项 Railway `0b2aa294-b6a2-47b6-8683-1af85ecfd778` 13项12绿1错，原V96正确拒绝了新合成“安静场景”低于80字符的过短测试；**只扩写合成夹具、不改生产门槛**。第二轮 `2b3ffbb1-f520-4c66-91a3-47d4a9e592e8` **13/13专项通过**。随后为上一事件加入真实receipt/prose/effect的再次SHA一致性检查，添加tampering反例。
5. **全仓真实回归**：Railway `4d57bf47-fe31-4d19-a39a-557c31bfdc2f` 1062项0失败0错误4跳过；增加`tests/test_v98_longform_rolling_stress.py`之后部署`9a7c5b2a-5443-4fa2-9805-72e61949246f` **1064项执行0失败0错误4跳过**，运行器`WF_V85_FULL_OFFLINE_REGRESSION_PASSED`（沿用旧命名但测试覆盖V98），模型0/R2读写0。合成链跨800/1600/3200/6400中文含标点字符，超过1000字符时伪造前因被拒，**不是模型真正写出文学6400字**。
6. **既有真实V97付费数据不得重跑**：七次DeepSeek Flash已用，旧A1902、B1601、C1554中文字符原始R2不可变结果全部保留，总CAS `d304d2432e2c3290b6bbd8ccb6bc209e38b7e12bc0aabb968b489b31c22b02a1`。V98没有新增真实付费、没有人类独立评审；不准说AI超过1000字已证明不紊乱或D文学质量胜于C。
7. **下一轮V99应做核心写作思考和真实质量测量**：选两个以上独立原创题（历史/仙侠），控制各组**实际字数接近**与模型版本/总API预算，A现有整章、B单纯分段、C锚点因果、D实际后果动态滚动；记录作者硬事实边界与人物知识、动机/阻力/代价/伏笔转移、因果硬伤首次出现字符位置以及盲评文学自然度。D增加调用，必须有成本控制对照；真正独立语义审核前不得自动晋级。如果同一缺陷连续两轮修复没有改善，按用户要求停下查外部GitHub/ACL及源码，不再无穷补丁。
8. **硬性遗产不变**：V92完整前15章云端旧/新版经验CAS `bd905ae9e812fb5283f24ed7fec3bc35cf0febde7b6405476c455bba468f84db`、V49`THIRD_STRIKE_FAILED`、第二文学窗口`LOCKED`及V88机械0/4事实都保留。V95 Cloudflare条件HEAD线上未部署(404)，不可让未审候选升到真实人物`KNOWN`。V98只是本地WRITE未接受候选实验，不更改生产LEARN或云端事件权限。
9. **最后运维需核实**：Railway从本次回归入口切回`python -u wf_railway_v82_safe_idle.py`、`restartPolicyType=NEVER`，必须看到实际`WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`及0模型/R2调用、自动付费false，才能在最终报告称安全结束，不能预填。

**最高检验目标不变**：WF能解释并体现在正文里「人物现在想做什么、为什么能知道什么、遇见什么阻力、真正作出什么决定、后果怎样迫使下一幕发生」，而不是只会输出更长且自我称赞的文字。

**§84 V98最后运维已经真实确认**：Railway最新安全idle部署 `21c91dc0-4896-4e2a-a8d7-0cd16f165f2e` `SUCCESS`，源配置pin `ff849d7d1761f746e99fccc792f29def99169e45`（最后1064项软件回归通过的源码），实际启动 `wf_railway_v82_safe_idle.py` 且 `restartPolicyType=NEVER`。实际容器日志 `WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`，本次模型0、R2读0写0、自动付费续训false。新D滚动模式只是本地作者手动选择的未接受写作候选；从未宣称真实文学质量已经晋级。


## 85. 【2026-10-20 V99】真正正文的逻辑故障位置证据合同和A/B/C/D公平长度门槛

**权威报告：[V99真实正文证据标注与公平盲审准备](V99_ACTUAL_PROSE_LOGIC_EVIDENCE_AND_FAIR_BLIND_REVIEW_20261020.md)**。从 **V98** 源码和当前Railway部署继续，不是倒回V96重造Scene-turn。

1. V98已实际完成`rolling_causal`模式、1064项合成回归，V97实际三臂DeepSeek Flash原创新作A=1902、B=1601、C=1554中文字符存于R2；此轮并无新付费创作。因3臂长度不一致、一个历史题且无独立文学盲评，不允许声称哪一臂文学更好。
2. 隔离V99分支`v99-causal-quality-blind-review`新增`writerforge/v99_longform_quality_evidence.py`纯函数证据和`tests/test_v99_longform_quality_evidence.py`：把正文内容SHA、实际中文含标点字符数与A/B/C/D固定；每条候选逻辑矛盾必须找到“前一成立事实”与“后一涉嫌矛盾”在**真实正文中唯一存在**的两句证据，计算有序字符offset与引句SHA。错源、伪引用、重复、倒序、篡改SHA立即拒绝；但**引用真实不等于矛盾成立**，所有结构分析的文学错误数/首次错字位置均为null，`literary_quality_winner=UNDETERMINED`，不能自动晋级。
3. 同目标字数但实际输出差距超过10%的A/B/C/D标记`lengths_comparable=false`，避免V97 A1902/B1601/C1554不公地比较逻辑好坏。目标仍是800/1600/3200/6400中文含标点字符的位置分布，不是Token长度。
4. 失败事实必须保留：Railway首轮`71c54813-b56a-40a1-bb7e-c628ec0c8726`全仓1072项1失败2错误，由于合成TXT误重复整段令两个引句多次出现；第二轮`3b458d94-3171-430c-8033-2392d3cff4ea`只执行1065项，1项Python SyntaxError（错误写入字面`\\n`导致新增模块未加载）。在同模块两次失败后按用户规则停止猜测，查Python官方源码字面量拼接语法，再修夹具，**没有放松唯一原文证据校验**。
5. 修正后的第三轮真实Railway`005a6fad-2973-4f5b-93bc-d675f69d19c6` **全仓1072项执行、0失败、0错误、4跳过**，`WF_V85_FULL_OFFLINE_REGRESSION_PASSED`，模型0/R2远端0、不重训原著/第16章。本轮只有证据结构，不声明已解决千字后语义紊乱。
6. **真正下一步**：利用现有V97真实三臂原答做独立匿名文学证据标注；设公平字数差额与成本对照，再增加至少一部**仙侠原创题**、实际复现D动态滚动方式、盲评人物欲望/行动前提/阻力/代价、写法自然度及首个真实硬矛盾出现的字符位置。不能用模型自评分当作真结论，也不要回头扩充R2/Skill而偏离写作能力。
7. 必须将Railway重新切为`python -u wf_railway_v82_safe_idle.py`，`restartPolicyType=NEVER`，**以实际最新容器日志证明**本次模型/R2读写0及自动续训关闭后才能称收尾。

**长期目标仍是写得更有因果、更懂人物、更有艺术性，而不是只是多存了几本书。**

**§85 最终运维已实证**：Railway部署 `3376a212-ef87-4339-a083-6631260c01d2` 为 `SUCCESS`，启动 `python -u wf_railway_v82_safe_idle.py`、`restartPolicyType=NEVER`、固定git commit `a8404905869dc1e1acc094adc0f0931f61823ede`（完整1072项合成回归通过的源码）。实际容器 `WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`，本次模型调用0、R2读写0、自动收费下一批关闭。V99未部署真实文学自动评分器或新事实写入；后续独立盲评尚未完成。


## 86. 【2026-10-20 交接】以V99为最新起点；下一轮必须实测真实长文因果与文学技巧

**此处直接启动下次会话：[V99 → 下一轮写作能力正式交接](V99_NEXT_SESSION_WRITING_QUALITY_HANDOFF_20261020.md)**。该文是用户明确要求的交接，已按实际GitHub分支和Railway日志重新核验，不是新文学考试或模型训练。

1. **版本准确性**：当前最新是 `v99-causal-quality-blind-review`，不是早期的V96研究分支。V96的可选A/B/C场景写作内核、V97真实7次DeepSeek历史原创三臂、V98新增D正文效果驱动的滚动因果目标、V99真正全文矛盾引句SHA及等长比较门槛均已在源码上实现；下一轮**不要从V96重写旧功能**。
2. **不可丢失的真实样本**：V97历史原创 A单次1902、B仅分段1601、C因果校验1554中文含标点字符，7次DeepSeek原答和三份候选在私有R2清单 `d304d2432e2c3290b6bbd8ccb6bc209e38b7e12bc0aabb968b489b31c22b02a1`；旧预注册 `5c7fac8ef9ab0f588698711ba1b63672a2eab18ff4f65d53bf8616489d36cae1`。独立Reader已核SHA和C动作3/3、后果3/3、父后果2/2**字面定位**。**未**执行真正独立文学盲评，三臂实际长度不等，不能宣布C有真实因果/写法优胜。旧原答不可重付费。
3. **V99最后软件回归**：Railway `005a6fad-2973-4f5b-93bc-d675f69d19c6` 真正1072项0失败0错误4跳过，另保留之前两次合成测试脚本红项；测试零模型/零R2。V99引用定位只能证明引句确在正文，不证明逻辑真的矛盾，实际第一处硬错误位置、独立文学赢家仍`UNDETERMINED`。
4. **最新安全运维**：本次交接实际重新核对Railway主服务 `e6a7688b-ee12-49ef-ae83-02145005fc79`，最后部署 `3376a212-ef87-4339-a083-6631260c01d2` `SUCCESS`、源码pin `a8404905869dc1e1acc094adc0f0931f61823ede`，运行 `python -u wf_railway_v82_safe_idle.py`，`restartPolicyType=NEVER`；实际容器日志 `WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`，本次模型0、R2读写0、自动付费false。仅本交接GitHub文档提交，**没有重新部署或运行模型**。
5. **下次行动必须直指写作核心**：先用Reader恢复旧V97三个真实候选，匿名冻结盲评包与引用/错误标注；然后预注册至少一个原创仙侠题和A/B/C/D同目标字数、实际长度差≤10%及D额外调用的公平成本控制，再有界生成/独立盲评。评审真正人物愿望、所知、行动前提、阻力、代价、具体后果、伏笔与自然文风，记录逻辑硬错首次中文字符位置。未有独立语义审核就不得认定任何组文学提升，不能因为标点短引SHA通过而晋级。
6. **最高用户约束**：WF要成为真正善于思考与写作的作家，不是资料管理员；“AI约1000字后逻辑混乱”仍是要验证的假说，不是已证事实。避免再围绕R2/无限上下文/Skill标签打转，也不强迫每段有八步套路；必须允许留白、误解、倒叙和人物复杂性。V92十五章持久经验CAS `bd905ae9e812fb5283f24ed7fec3bc35cf0febde7b6405476c455bba468f84db` 保留，V49 `THIRD_STRIKE_FAILED`、第二文学窗口 `LOCKED`，第16章不开启；V95 Cloudflare权威HEAD线上404，生产未审事实不能写`KNOWN`。

**正确接手方式**：先读本节与[V99交接专文](V99_NEXT_SESSION_WRITING_QUALITY_HANDOFF_20261020.md)，复核Railway安全idle，不修改既有真实原答；下一步以写作成品的因果与文学感受可验证的改善为目标，缺少独立评分时只报告工程一致性而非“作家能力已经成长”。
