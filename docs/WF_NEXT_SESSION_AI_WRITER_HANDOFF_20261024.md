# WF 跨窗口精简交接｜2026-10-24｜AI 自己决定何时及为何删稿

**接续顺序**：先读本文件，再读 [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md) 的最新首节 **0.L**，然后按需读 [WF_AI_WRITER_JUDGMENT_AND_REVISION_ARCHITECTURE_20261024.md](WF_AI_WRITER_JUDGMENT_AND_REVISION_ARCHITECTURE_20261024.md) 和 [WF_WRITER_SELF_EDIT_CORE_20261024.md](WF_WRITER_SELF_EDIT_CORE_20261024.md)。最后核验 GitHub 当前分支 HEAD 和 Actions，不从旧 V96–V123 训练或 API 配置重启。

## 本轮最新 0.L：AI 回改整章后的新 V117 分支与热暖冷引用（2026-10-24）

**全文**：[WF_AI_CROSS_CHAPTER_BRANCH_FORK_20261024.md](WF_AI_CROSS_CHAPTER_BRANCH_FORK_20261024.md)。[最终无模型回归 #40083326608](https://github.com/66tyu55/WriterForge/actions/runs/40083326608)：**1,516 tests run，4 skipped，0 failures**。仅开发分支，旧 `main` / Railway / R2 / 已接受作者文本未动，没有新模型请求或再次训练。

- `writing_assist.py` 原位置现有 opt-in `cross_chapter_fork` 和 `selected_fork_receipt`：接受**由写作 AI 提出的**明确 `LOOK_BACK_NOW`、需要重审的章号、源正文 SHA、唯一真实原句/场景缺口和原因；WF 不判断小说为什么坏、不会生成正文。**重要限制**：还没有让真实写作模型自己在章节边界发起此请求，当前输入只是外部提供的 `writer_decision_reply`，无提供商真实性证明。
- 最小安全适用范围：原本 G 本地 job 恰好 2 个**未接受**章节，修改目标是二者第一章，且已有目标之前一章的合法 V117 signed resume（不是无前史书的第1章）；完整模型+资料快照+本地 source SHA+统一 NarrativeCore graph 的 parent SHA 链先验核查，不通过就连新 job 都不建、不扣费。原作品是否在其他外部客户端已经接受，尚需该客户端另外确认。
- 模型在**不同**新 job 重新独立规划、写两章，V96/V114/V117 与旧唯一 graph 重新计算；不把旧第二章冒充新故事事实。首章没有实际 source 变化则拒绝标记成功；最后生成新分支的 SHA 封口 receipt，旧文件不修改，旧模型原文留存；新分支选择后旧下游 resume 必须拒绝，合法新 resume 可以继续生成下一章。
- 热/暖/冷仅继承分叉前合法前缀及其冷索引，不引入旧后代的 source SHA；本地 13 章压缩前缀的 3 热/8 暖/冷库延续已用离线反例验证；**并不删除旧存储字节，仍未实现跨任意章节/R2/多分支的全局失效或完整工作树事务**。
- 保留 [首次红灯 #40083002707](https://github.com/66tyu55/WriterForge/actions/runs/40083002707)：测试模型引用旧章重复短语，被唯一性校验拒绝；另外热暖冷单测变量遮蔽。修正真实引用和 Python 测试变量，不放宽 V119 或 V117。 [第一轮绿色 #40083135333](https://github.com/66tyu55/WriterForge/actions/runs/40083135333) 1,514 项；最终 #40083326608 1,516 项（新增第三章合法沿新头续写、重写后一章失败时旧双章完整不动且不生成成功收据）。
- **下阶段**：给同一个正在写的 AI 一次作者请求内的真实“是否跨章回头”发起机会，将 Studio 现有版本选择与 `selected_fork_receipt` 连接；先离线校验，再另行授权有限真实创作探针。禁止以 mock LOOK_BACK_NOW 冒充付费模型成功，禁止新增文学评判模型或记忆模块，保持 V26/V98/V119/统一图、A–F 与已有废稿/失败原件。

## 本轮最新 0.K：废稿来源不污染 V114/V117 与失败原子恢复（2026-10-24）

**工程证据入口**：[完整原件与负例](WF_AI_WRITER_DISCARDED_STATE_ATOMIC_RECOVERY_20261024.md)，[最终无模型 Actions #40076159662](https://github.com/66tyu55/WriterForge/actions/runs/40076159662)：**1,508 tests run、4 skipped、0 failed**。开发分支无新付费模型、无训练、无 Railway、无 main 修改。

- 零模型反例已覆盖：原文删掉真正的火髓果交付，V114/V122 将持有者恢复为原合法持有者；删除“右臂垂着”后临时伤势不可凭废稿继承；剑穗虚假跨物件转移产生的 V117 未偿候选从新源重演后消失；删除尚未被作者证实的秘密披露，统一 FACT/UNKNOWN/THREAD 图保持作者明确 UNKNOWN，不允许模型冒称已知；最终 V117 签名与唯一 graph 热记忆源 SHA 指向真正保留稿件。
- 原 `writerforge/writing_assist.py` 有界 G 回看新增可逆候选边界：AI 仍负责想法、选择、源原句、实际改稿；WF 仅临时冻结前段及下游状态，旧 V119 成功后由同一写作 AI 重写下段。若随后 V96/V114/V117 失败，直接恢复旧前段和旧下段的确切源回包，重新经过校验，不追加新模型重试；旧模型答复永久在私有 job 中不被 regenerated-raw 覆盖，尝试次数和成功次数分开报告。
- 本轮真实红灯如实保留：[第一组 #40075407455](https://github.com/66tyu55/WriterForge/actions/runs/40075407455) 不合理同一原子事件与短于 V96 下界、[第二组 #40075680350](https://github.com/66tyu55/WriterForge/actions/runs/40075680350) 漏角色 cast / 短原文、[原子事务构造期 #40076014846](https://github.com/66tyu55/WriterForge/actions/runs/40076014846) V121 原结构测试要求固定缩进。无一通过削弱来源校验或假文学评分绕过。
- **尚无真正模型主动 LOOK_BACK_NOW 成功证据**，仍只在 G opt-in 且同章紧邻上一段、每 job 最多一次。整个章末/跨章归档的外部失败仍 fail-closed、并非通用 StoryWorkTree 依赖回滚；非流式生成也不能声称半个 token 自我删改。原 V26 两种续写+选择、V98 文本驱动构思、V119、V117 和统一 graph 原职责未变；A–F 无新增行为。
- 下一步优先**检查跨章已保留候选 / 热暖冷记忆的依赖撤销，不得更改作者确认文本**，后续需有限真实同写作模型自发 LOOK_BACK_NOW 原件与独立文学盲评才可称文学能力获得进步。无授权不主动付费实验。

## 本轮最新 0.J：自主回看上一段与有界下游撤销（2026-10-24）

- **新入口/证据**：[上一段事务说明](WF_AI_WRITER_PREVIOUS_TURN_TRANSACTION_20261024.md)。开发分支 `writerforge/writing_assist.py` 新增有界 `_rewind_unaccepted_turn_suffix`，同一原创 AI 在 G 的 opt-in `ai_decides` 决定 `target_turn="previous"` 后，才会以旧 V119 源锁和旧 model 原完整 `prose+trace` 回复修订上一段。
- 修订成功时，先私有保存被抛弃的下一段，再整体撤销 V96/场景/人物/计划/审修临时候选回执，恢复 V114 物件时态和上一事件段前的状态，让模型依据新原文重新生成下游；统一 graph 和上章签名、原先已确认 Canon **不会被自动改写**。单次 job 最多一次回上一段，8 次额外模型请求总上限不变，默认旧 V26/V98/A–F 关闭此功能。
- **原始失败不抹除**：[首次加完整线的红灯 #40074029791](https://github.com/66tyu55/WriterForge/actions/runs/40074029791) 检出 V96 摘要无完整 trace，已改用每次任务的 `selected_turn_raws` 保存经过普通校验的真实完整模型答复；[复归绿色 #40074160492](https://github.com/66tyu55/WriterForge/actions/runs/40074160492) **1,501 执行、4 跳过、0 失败**；[进一步校验 V114 必须使用修改后的原文重归约 #40074298398](https://github.com/66tyu55/WriterForge/actions/runs/40074298398) 同样全绿；[在现有统一叙事 graph 上执行 AI 回改与下游状态重新归约 #40074549545](https://github.com/66tyu55/WriterForge/actions/runs/40074549545) **1,501 执行、4 跳过、0 失败**，且旧统一叙事图仍是唯一记忆主人。以上全为**人工构造回复的无付费模型工程测试**。
- 原有真正 DeepSeek 证据不变：第一段 INVALID_SIGNAL、第二段经零模型回放后真正 MOVE_ON。**没有真正模型的 LOOK_BACK_NOW → 上一段改稿 → 重新下游成功原件**。也未支持跨前两段、跨章、逐字删写、通用状态依赖树撤销、部分后续校验失败时回到先前完整任务。不可称有文学质量进步证明。
- **继续顺序**：检验更强的“删除得物/知情/伤势”后 V114/V117/统一叙事所有下游失效及冷重启，做好失败时整段复位，再审议是否授权有限的真实同模型探针；不重新训练、不改 main 或 Railway，不新设记忆/文学裁判。

## 不得偏离的创作目标和职责

用户强调：**WriterForge 绝对不能代替 AI 思考、选择文学意义、生成正文。** 同一个写作 AI 才是小说作家，应像真人那样主动决定继续写，还是回头删一句、删段、推翻某场。只给一次作者请求，AI 应自行反复构思/删改，用户不用连续重发请求。WF 是原有写作工作台，负责提供已有真实上下文、事件段/小稿片的可观察停顿机会、私有版本保存、唯一原句定位与安全回退；不能用关键词、模板、软件文学分数替 AI 的写作判断，也不能派其他 AI 代写。

**必须保留的最初核心**：V26 两种候选续写 + 作者 Ctrl+1/Ctrl+2 采用或忽略 + 自动保存；A–F 现有分段、D/E/F 动态重新规划、V98 正文驱动；G 统一叙事源视角、V96 原句因果、V114 物件/时间、V117 跨章签名、现有 FACT/UNKNOWN/THREAD；V119 基于唯一来源与 SHA 的精确局部删改；作者可在生成中取消、逐段选择继续或删除本任务候选。全部沿原模块，不新建第二个文学记忆或事实主人。

## 当前已实现，仍可运行但不能夸大

- `writerforge/writing_assist.py`：G `continuity_guard` 的 `self_edit_rounds=0/1/2` 明确可选，默认关闭；同写作模型先写真实事件段，再可选择 KEEP / DELETE / REVISE / REPLACE_SCENE；通过现有 V119 和 V96/Novel Studio/统一图后，才以修订后**未被正式接受**的候选继续创作。每段最多 2 轮、每 job 合计最多 8 次额外模型调用；失败回滚、不无限重试；原稿与弃稿在当次私有 job 中保存。
- 追加 `self_edit_timing="ai_decides"` 的 opt-in：`_ai_decides_when_to_revisit` 在**已经写完的可见事件段后**将原文及人物/因果上下文交给**同一个写作 AI**，AI 自己输出 MOVE_ON 或 LOOK_BACK_NOW，以及 `why_now`、源引句或缺失的场景效果、`what_goes_wrong_if_unchanged` 和 `intended_reader_effect`。只有 AI 决定 LOOK_BACK_NOW 才进入 V119 局部修订；若 MOVE_ON，WF 不应强制删稿。默认兼容旧 `always_offer`，A–F 不变；Studio G 有作者选择入口。
- **边界**：非流式 API 下目前只能在真实事件段写完时交还选择，不是模型在隐形推理或半个 token 中自发擦字；往前发展需由 AI 分成可观察句群/自然段或接流式可取消写作。尚没有跨前两段/前章推翻时对所有下游暂存状态的完整回滚，必须复用 V117/StoryWorkTree 实现。
- 主体 AI 的「觉得不好」不是已证文学品质；程序只验证来源唯一、SHA、编辑范围和可观察的状态，不能自证美感，也不能凭模型 KEEP 认定完美。

## 原件与验收——清楚区分原始失败和后续零模型解释

1. [第一次真实自主修订 #40068690550](https://github.com/66tyu55/WriterForge/actions/runs/40068690550)：DeepSeek Flash 真正执行 6 次请求（2 规划 + 2 小说正文 + 2 模型修订）；两条均因模型 Unicode 字符偏移错误暂被回滚，废稿与原始回答保留。 [零新模型调用原提案重验 #40069059042](https://github.com/66tyu55/WriterForge/actions/runs/40069059042)：唯一逐字原句允许确定性定位，第一段改稿成功，第二段因 `WF96_PARENT_CAUSE_NOT_ANCHORED_IN_PREVIOUS_PROSE` 继续拒绝。**不代表文学质量提高。**
2. [真实写作 AI 自己判断何时回头 #40070821134](https://github.com/66tyu55/WriterForge/actions/runs/40070821134)：共 6 次真实 DeepSeek 请求（2 规划 + 2 原文 + 2 时机判断），没有第三方代写或作者重复发稿。原第一段判断回复错误地变成了 prose+trace，不是有效决策；第二段实际返回 MOVE_ON，具体理由涉及父亲遗信、无名孩子和复仇情绪转向，但多一个模型包装字段而被最初软件记为 INVALID_SIGNAL。
3. [真实原始判断零新模型回放 #40071088617](https://github.com/66tyu55/WriterForge/actions/runs/40071088617)：只兼容严格的多余 `type=json_object` 包装字段，原第一段仍 INVALID_SIGNAL，第二段真实决定恢复为 **MOVE_ON，维持正文不删**。这证明 AI 发过真实“继续/回头”的决定，**迄今没有真实完成一次有效的 LOOK_BACK_NOW→修订的整条链路**，严禁假称已证。
4. [全量绿色回归 #40070986328](https://github.com/66tyu55/WriterForge/actions/runs/40070986328)：**1,495 项测试执行、4 项跳过、0 失败**，仅证明工程机制；零模型原始回放另有 9 项专项通过。先前所有技术红灯和七类 Atria 真实文学负例保留。

## 下个窗口行动顺序

先校验 HEAD/代码/工作流状态，然后**先研究能让 AI 稳定输出有效的回头时机与自然语言写作理由，而不是继续给 WF 添加文学判断规则**：对具体新原创短场景做有限真实同模型探针，保留 MOVE_ON、格式失败、真正 LOOK_BACK_NOW 各原件；不得为了得到 LOOK_BACK_NOW 而把剧情写死或默认强制重写。改动必须由 V119 在唯一原句上执行，保留废稿与后续影响；若先前段落事件被删，统一因果、人物认知、物件/时态等下游未接受状态要重新推导，不得从已删除废稿继续。

**不要冒进**：没有独立文学盲评，尚不能证明模型的主观「why」判断可靠；不要改 A–F 默认行为、不要创建新记忆模块、不要重复已完成15章/V96–V123文学训练或 API setup、不要向 Atria/R2 原库乱写、不要动生产 `main` 或 Railway 部署。所有真实付费实验只有用户授权的有限批次，已完成自动触发的 workflow 保持 manual-only。

## 下个对话可直接发

「继续 WriterForge。读取开发分支 refactor-unified-scene-delivery-audit 的 docs/WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md 和 CURRENT_HANDOFF.md 最新 0.L。核心是 AI 自己决定什么时候不满意、为什么删，WF 绝不能替 AI 计算文学意义或生成，保持 V26/V98/V119/V117/统一图。先核验最新 1516 测试（含双章新分支、源父 SHA、热暖冷、旧支拒绝与失败完整保留）与历史真实 6 次调用、零模型回放，保留首段 INVALID_SIGNAL 和第二段 MOVE_ON 的负例，再针对真正自发 LOOK_BACK_NOW 与下游状态回退做最小验证；禁止重复训练、增加记忆、改 main 或部署 Railway。」
