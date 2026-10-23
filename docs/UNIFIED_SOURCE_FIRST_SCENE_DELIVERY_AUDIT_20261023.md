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


## 2026-10-23 续接：统一 THREAD 的场景债务闭环（仍非文学质量证明）

**七类 Atria 实测证据均原样保留**：14 篇原稿／7 组配对；心理 WF 原稿长段逐字重播；喜剧裸版误拿雨伞反转较清楚；打斗、计谋规则猜测和字数问题；高潮与心理曾因 3,100-token 推理预算失败、再以 6,000-token 补测成功。两种额度不能当作公平总胜率。本次未重新调用书生模型，也未覆盖、公开或更改真实原稿。

### 从意图、候选正文到同一 THREAD 图

1. audit_scene_delivery 仍仅对实际正文做 SHA 源锚审计。THIS_SCENE 当场兑付、DEFERRED 有意延期分离，但模型自评、真实效果引句或未经作者认可的评论均不能独立证明文学兑现。
2. propose_scene_delivery_debt(graph,...) 在 AutonomousWriting.run(...,draft_mode="continuity_guard") 完成整章实文后提出只读建议，写入既有 v96_turn_evidence.json 的 unified_scene_debt_review_proposal；候选章返回 unified_scene_cross_chapter_debt_status、review receipt SHA，自动图写入次数为零。若未加载统一图，则显示 NO_UNIFIED_GRAPH_TO_REGISTER_DEBT，不能误报已经跨章追踪。
3. review_scene_delivery_on_graph 是作者**单独阅读真实候选**后才可执行的审阅操作；必须显式 author_confirmed=True 和 candidate_read=True，绑定 owner / target / 审阅理由，并匹配该章已有热缓冲里真实保存的候选原文 SHA。作者先前确认过要写某场景，只是写作意图，并不代表已经看过模型正文。
4. CARRY_FORWARD：在既有统一图写一条稳定 THREAD，truth_scope=AUTHOR_INTENT，保留作者故事问题、原始 due、开立章与逾期标志。这是**待审意图债务，不是故事事实/角色知识/正典**。THIS_SCENE 逾期不强制模型制造反转；DEFERRED 保持开放。
5. SETTLE_WITH_SOURCE：两条唯一、先行动或心理选择、后可观察或内在后果的真实原句必须通过原有 _anchor() 的来源检测；梦境、引语、假设及模型自报不算。状态为 SETTLED_AUTHOR_REVIEW_ONLY，仅保存引句哈希，independent_literary_payoff_verified=False。心理选择可以没有物理行动。
6. ABANDON_BY_AUTHOR：作者明确放弃原故事问题，状态为 ABANDONED_AUTHOR_REVIEW_ONLY，not_a_payoff=True，不把放弃、转向、未决误算成兑现。所有写入仍是统一图的同章新签名快照，无第二个状态所有者、额外数据库或 Canon 写入。
7. 相关后续章节仍由统一 schedule() 的 LONG_THREAD 优先 lane 有界提醒，限最多三条相关线，压不进提示的债务保留。只有 owner 视角得到具体作者意图；其他视角不因交集就获悉秘密。人物可按独立认知、恐惧、欲望与代价改变既定方案。静场和无关章节不强制结案。

### 审阅入口与边界

对新生成章节保留作者合同、章节目标、原 candidate.md 的真实字节、同一 V117 resume，然后调用 narrative_core.review_scene_delivery_resume(resume,project_id=...,scene_id=...,prose=...,scene_goal=...,scene_kind="chapter",author_delivery_contract=...,author_review=...)。此函数**返回**新签名候选 resume，不会自行覆盖旧 R2 对象、部署服务、触碰 Canon 或消耗模型配额。

author_review 精确包含八个键：decision（CARRY_FORWARD / SETTLE_WITH_SOURCE / ABANDON_BY_AUTHOR）、author_confirmed=True、candidate_read=True、owner、target、reason、action_quote、outcome_quote。只有 SETTLE_WITH_SOURCE 需要两条不为空的来源引句，其他决定必须用 None。已有稳定 ID 不得改写问题来替换前人承诺；源文哈希不匹配、复评重复、合同不一致都需明确失败。新签名恢复封套仍注明 author_accepted=False、canon_writes=0，不能把作者接受单条审阅意见冒充整篇正文已成为正典。

### 工程验收与独立文学盲评边界

tests/test_unified_scene_delivery.py 使用合成原创微场景覆盖只读提议、审稿权限、候选保存、完整的跨两章 carry→settle、人物自主心理选择、不同 POV 不泄密、延期和取消不冒充兑付。CI 执行全仓库原有回归，但不再重新训练或配置 V96–V123。此工程回归不是七类文本艺术效果改善的证据；独立盲评仍未完成。


### 七类原始失败证据索引（不覆写原稿、不当作文学生成评分）

| 场景 | 源观察或首轮失败 | 对本闭环的警示 |
|---|---|---|
| 剧情 | 裸版较快推进线索，WF 版更细描写透露秘密的选择 | 场景长度增加不是实际进展 |
| 高潮 | 首轮 WF 的 3,100 max_tokens 全消耗在推理，正文 0；6,000-token 另批补测成功 | 无可见正文时不能签效果结论；跨预算不混算 |
| 打斗 | WF 比裸版冗长，新增“火髓果汁遇风即燃”的未立来源规则 | 不能把临时设定写成已有世界事实 |
| 计谋 | WF 版较长，把“回答太快”作为战术怀疑 | 人物猜想与来源事实必须分离 |
| 恐怖 | WF 增加未解异象，但台阶方位指示含混 | 氛围铺垫不能代替空间因果 |
| 搞笑 | 裸版误拿唐蜃／巡察使雨伞形成明确反转，WF 版尴尬延长但不清楚兑现 | 被模型引句命中不等于包袱成立 |
| 心理 | 首轮裸版 3,100-token 推理耗尽、正文 0；6,000-token 补测后 WF 原稿出现约 964 字符原段重播 | 精确长段硬拒与心理语义判断需分开 |

证据源：[初始七类 Atria Run #39937669584](https://github.com/66tyu55/WriterForge/actions/runs/39937669584)、[高潮／心理 6,000-token 补测 #39939718654](https://github.com/66tyu55/WriterForge/actions/runs/39939718654)、[七类首轮原稿说明](https://github.com/66tyu55/WriterForge/blob/experiment-seven-literary-scenes-inkstone/docs/SEVEN_GENRES_FIRST_ACTUAL_PROSE_RESULTS_20261023.md)。心理 WF 重播原稿 SHA-256 为 272557d79b55f4b6790591afcc0817d61feedf2deb11f25fcbacf3dee4dedbac。以上仅记录既有运行中真实原稿的编辑观察；没有执行新的盲评或统计推论。


## 七类原稿防过期归档：真实私有 R2 上传及 fresh GET（本轮后续）

在实现场景债务闭环后，现场检查了初次实验 Actions #39937669584 与补测 #39939718654。GitHub 仍保存九份原始附件，但返回 expires_at 为 **2026-11-06**。仅把 GitHub 链接写入手册不能长期保全来源，于是在同一开发分支加入**证据保全工具**（不属于小说长期叙事记忆模块）：

- [scripts/preserve_atria_artifacts_r2.py](../scripts/preserve_atria_artifacts_r2.py) 和 [.github/workflows/atria-evidence-private-r2.yml](../.github/workflows/atria-evidence-private-r2.yml)。读取原始 GitHub API 附件元数据，逐项比对 run ID / artifact ID / 名称 / SHA256 / 未过期状态；下载 ZIP 受有界字节限制，核验 GitHub ZIP SHA256 与 CRC，然后仅向**现有私有** writerforge-private-library 桶中 writerforge/v1/private-evidence/atria-seven-genres-20261023/ 的 SHA 内容键写入，不允许覆写不一致数据，逐一重新 GET 比对完整字节。
- **真实 GitHub Actions success：[#39953107366](https://github.com/66tyu55/WriterForge/actions/runs/39953107366)**。运行记录返回 preserved_original_github_artifacts=9，private_r2_fresh_get_success=9，new_model_calls=0，canon_writes=0，source_copies_logged_or_published=false。
- 不可变私有清单 SHA256：14e0e957f2564af71ee0ee3b8f74bf743948f6e06fa59e750b58387a5b74650e；保存九份 ZIP 的来源记录、来源实验与补测预算分类，保留原有失败、没有重新生成或重打分。备份仅为原始附件封存，不是新作学习、不等于文学进步，也不触发生产 Railway。状态附件只有哈希/数量，没有原稿正文。
- 与本文早先的“本轮没有 R2 写入”历史基线须区分：**统一叙事闭环代码和 1,420 项软件回归**没有对 R2 写入；**本次后续防过期归档**确实向私有 R2 写入了九个封存 ZIP 与一份不可变 manifest。未覆盖任何现有小说原稿、R2 学习库、Canon 或主分支。


### 最后来源回查保护（最新源码回归）

作者审阅不再只检查 HOT buffer 中的 source_sha256 与用户传入 prose 相同。review_scene_delivery_on_graph / review_scene_delivery_resume 在作出任一 CARRY_FORWARD / SETTLE_WITH_SOURCE / ABANDON_BY_AUTHOR 决定之前，还会调用现有 _verify_source_file 对保存的本地 candidate.md **重新读取原字节 SHA**；若是私有 r2:// 来源，必须显式传入现有私有 R2 source_reader 实际 GET，缺失读取器或对象字节变更就 fail closed。没有新增记忆模块和正文复制库。

新增两个对抗回归：候选文件落盘后被篡改不能继续审结；R2 路径没有真实读取器不能审结，提供能回读且 SHA 匹配的 R2 reader 后才允许。**最新完整功能与测试提交 cb704a845ac2bc90c5609ab704b65ae28f915842；Actions [#39953606339](https://github.com/66tyu55/WriterForge/actions/runs/39953606339) success：1,422 tests run、4 skipped、0 failures。**之前 #39952000380 的 1,420 为历史绿色中间状态，非最终本轮测试数。另行做过的九件私有 R2 原稿归档只用于防原始附件过期，不是此文学语义测试的新模型调用。
