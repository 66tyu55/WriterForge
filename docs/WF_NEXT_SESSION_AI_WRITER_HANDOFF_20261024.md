# WF 跨窗口精简交接｜2026-10-24｜AI 自己决定何时及为何删稿

**接续顺序**：先读本文件，再读 [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md) 的最新首节 **0.J**，然后按需读 [WF_AI_WRITER_JUDGMENT_AND_REVISION_ARCHITECTURE_20261024.md](WF_AI_WRITER_JUDGMENT_AND_REVISION_ARCHITECTURE_20261024.md) 和 [WF_WRITER_SELF_EDIT_CORE_20261024.md](WF_WRITER_SELF_EDIT_CORE_20261024.md)。最后核验 GitHub 当前分支 HEAD 和 Actions，不从旧 V96–V123 训练或 API 配置重启。

## 本轮最新 0.J：自主回看上一段与有界下游撤销（2026-10-24）

- **新入口/证据**：[上一段事务说明](WF_AI_WRITER_PREVIOUS_TURN_TRANSACTION_20261024.md)。开发分支 `writerforge/writing_assist.py` 新增有界 `_rewind_unaccepted_turn_suffix`，同一原创 AI 在 G 的 opt-in `ai_decides` 决定 `target_turn="previous"` 后，才会以旧 V119 源锁和旧 model 原完整 `prose+trace` 回复修订上一段。
- 修订成功时，先私有保存被抛弃的下一段，再整体撤销 V96/场景/人物/计划/审修临时候选回执，恢复 V114 物件时态和上一事件段前的状态，让模型依据新原文重新生成下游；统一 graph 和上章签名、原先已确认 Canon **不会被自动改写**。单次 job 最多一次回上一段，8 次额外模型请求总上限不变，默认旧 V26/V98/A–F 关闭此功能。
- **原始失败不抹除**：[首次加完整线的红灯 #40074029791](https://github.com/66tyu55/WriterForge/actions/runs/40074029791) 检出 V96 摘要无完整 trace，已改用每次任务的 `selected_turn_raws` 保存经过普通校验的真实完整模型答复；[复归绿色 #40074160492](https://github.com/66tyu55/WriterForge/actions/runs/40074160492) **1,501 执行、4 跳过、0 失败**；[进一步校验 V114 必须使用修改后的原文重归约 #40074298398](https://github.com/66tyu55/WriterForge/actions/runs/40074298398) 同样全绿。以上全为**人工构造回复的无付费模型工程测试**。
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

「继续 WriterForge。读取开发分支 refactor-unified-scene-delivery-audit 的 docs/WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md 和 CURRENT_HANDOFF.md 最新 0.J。核心是 AI 自己决定什么时候不满意、为什么删，WF 绝不能替 AI 计算文学意义或生成，保持 V26/V98/V119/V117/统一图。先核验最新 1501 测试（含上一段回看与 V114 重归约）与历史真实 6 次调用、零模型回放，保留首段 INVALID_SIGNAL 和第二段 MOVE_ON 的负例，再针对真正自发 LOOK_BACK_NOW 与下游状态回退做最小验证；禁止重复训练、增加记忆、改 main 或部署 Railway。」
