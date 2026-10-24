# WF 跨窗口精简交接｜2026-10-24｜AI 自己决定何时及为何删稿

**接续顺序**：先读本文件，再读 [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md) 的最新首节 **0.P**，然后按需读 [WF_AI_WRITER_JUDGMENT_AND_REVISION_ARCHITECTURE_20261024.md](WF_AI_WRITER_JUDGMENT_AND_REVISION_ARCHITECTURE_20261024.md) 和 [WF_WRITER_SELF_EDIT_CORE_20261024.md](WF_WRITER_SELF_EDIT_CORE_20261024.md)。最后核验 GitHub 当前分支 HEAD 和 Actions，不从旧 V96–V123 训练或 API 配置重启。

## 最新 0.P：同一 AI 先独立读者重建实际正文，再作家式决定，首次真实 LOOK_BACK_NOW（2026-10-24）

**必须读的新证据**：[WF_READER_FIRST_SAME_AI_LITERARY_REAL_PILOT_20261024.md](WF_READER_FIRST_SAME_AI_LITERARY_REAL_PILOT_20261024.md)。[真正同一 DeepSeek 的 3 调用 #40108836214](https://github.com/66tyu55/WriterForge/actions/runs/40108836214) 和 [零新增模型原始 V119 回放 #40109306167](https://github.com/66tyu55/WriterForge/actions/runs/40109306167)；一切运行都在开发分支，现有 main / Railway / 作者 Canon / R2 原书不动、无新模型训练、无第二文学记忆模块。绝不能把单样本模型自评当作文学质量改善。

- **0.O 三次真实 `MOVE_ON` 仍作为负例原封不动**：用上次官方 DeepSeek 真正写出的 451 字候选，单独读、全句来源索引、V116 位置短句都未推动模型自发回改。新 0.P 不是第四次告诉模型答案，而是架构转向：**同一个模型先只看原文作为独立读者复述，严格区分“原文明确发生”与“需要读者自行推测的过渡”；随后作为原作者自行决定如何处理**。
- **真正写作 AI 的文学变化**：真实新读者阶段返回 8 个原文字面观察和 3 条有前后唯一原句锚点的推测，其中一条准确提到程九“从坐进船里到又在桩边”缺少明写动作；**同一 DeepSeek 原作者真正选择了 `LOOK_BACK_NOW`**，理由明确提及“位置和姿态转换没有落笔，读者只能自行补足”。它随后独立生成了补“跨回岸上”的 `REVISE` 新句。三阶段是真实供应商请求，旧 provider wire 与本次三个新 wire 皆留存；本轮新增 **3 次真实调用**，usage prompt 4,120 + completion 1,480 tokens、无自动重试。
- **严格不能夸大落稿成果**：新 V119 原回复多了 `type=json_object` 包装且给出超出原长度的错误 `start/end`；首先因 `WF_SELF_EDIT_SCHEMA_INVALID` 被拒，旧 451 字文逐字不变。离线 **0 新模型回放**仅精确剔除官方已观察格式标记、用模型给出的原文唯一引句恢复数字坐标，确实得到了 V119 私有来源锁定预览，但 V96 仍报 **`WF96_UNDECLARED_PREVIOUS_CAUSE`**：模型把本段“我留着”的对白冒充此前事件的 `parent_effect_quote`，即使原 beat 没有父事件也不能默许。**因此真正通过 V96/V114 的改稿数仍是 0**。私有预览还可能在“你留着？”问句之前就让程九回岸，新增对话和道具位置歧义；未经独立文学盲评不得称优。
- **代码只改本职工作范围**：`writing_assist.py` 新增 `_reader_separates_written_and_inferred`、`_reader_report_for_author`，仅校验原句唯一性和前后位置，把读者推测标为候选，不自动改稿。原 G `AutonomousWriting.run(reader_first_self_review=True)` 只有 `continuity_guard+self_edit_rounds>0+self_edit_timing=ai_decides` 可开启；`studio_server.py` 和原 `ui/studio.html` 新增**默认关闭**的同模型独立读者复述选项，读者模型请求计入**原每作业 8 次**自主审稿限额且优先保留原作者决定。历史 V26、V98、V114/V117、V119、唯一 NarrativeCore 与取消/回滚保护不变。
- **格式兼容严格并可追责**：只支持旧供应商真实出现的冗余 `type=json_object` 字段、及从**完全相同 SHA 源全文唯一引句**恢复错误 Unicode 坐标，原模型回复字节保留，错误来源、非唯一引句和任何伪造因果依旧拒绝。下一次 V119 模型调用的提示现在明确：没有 `causal_parent` 就应由模型自身返回 `trace.parent_effect_quote=null`，WF **绝不悄悄修正旧原始错误**。
- **无模型回归**：[本阶段 #40108338519](https://github.com/66tyu55/WriterForge/actions/runs/40108338519) 1,547 执行、4 skip、0 fail；[追加源坐标/模拟真实格式 #40109111936](https://github.com/66tyu55/WriterForge/actions/runs/40109111936) 1,551 项；[最新最终 #40109468598](https://github.com/66tyu55/WriterForge/actions/runs/40109468598) **1,552 tests executed、4 skipped、0 failed**。不要用这些软件绿灯替代真实文学盲评。
- **下阶段约束**：不再对这篇真实 451 字旧稿不断付费劝改；首先冻结旧稿、真实读者记录、作者新决定、新模型亲写但未验收的 private preview、V96 失败。下一轮若获用户新指示，换全新的不同情境做**真正完整通过 V119/V96 后的匿名盲评、跨章行为一致性对照**，而不是追求 LOOK_BACK_NOW 次数。不给 WF 新增文学审稿模型、第二记忆主人或固定剧情评分；作者始终能选择原样保留。

## 本轮最新 0.O：真实 DeepSeek 原稿复读三次，事实索引有用但 AI 仍为错误辩护（2026-10-24）

**先看新专项原始证据报告**：[WF_REAL_DEEPSEEK_451_BLIND_SOURCE_V116_20261024.md](WF_REAL_DEEPSEEK_451_BLIND_SOURCE_V116_20261024.md)。[盲读＋全句源索引实测 #40104976936](https://github.com/66tyu55/WriterForge/actions/runs/40104976936)，[V116 角色位置短句实测 #40105777757](https://github.com/66tyu55/WriterForge/actions/runs/40105777757)。本轮合计**新增 3 次真实官方 DeepSeek Flash 调用**（2+1），完整源原文 SHA、旧两次原始 wire 与旧 `MOVE_ON` 在付费前通过 GitHub 原件复核，原稿与坏例均按原样保留；不重复写 451 字原文、不重训、不触动 main/Railway/R2/Canon。

- **真正的文学结果是红灯**：第一次独立复读自己真实写下的 451 字，DeepSeek `MOVE_ON`；第二次提供**全文全部句子的中性来源偏移**，仍 `MOVE_ON`；第三次仅给现有 V116 从真实原文摘出并按先后排序的四条“姓名＋动作＋地点词”：`程九蹲在船头` → `程九已经坐进船里` → `顾翎跨上船` → `程九仍蹲在桩边`，仍 `MOVE_ON`。不存在一次 `LOOK_BACK_NOW`，所以 **0 次 V119 改稿、0 字新修改正文**，不能冒称文学修复成功。
- **第三次作者 AI 自我辩护值得研究**：真实回复明说“……读者能自然补出他回身留岸的动作；不点明反而贴合他在雾中沉默的选择”。但真正原文没有明确写程九从船里下船回到桩边。审美省略可以合理，然而“原文动线已经交代清楚”不等于事实完整。尤其是 AI **看到了**位置变化，仍把缺失动作转述成可凭想象补齐。
- **只新增读证据的能力，不新建记忆**：原 `writing_assist.py` 加读原文的 lossless 逐句索引；原 `v116_state_delta.py` 增 `source_only_character_place_mentions`，抽取显式角色与地点动作**真实短句和字节位置**，保守拒绝梦境/引述/传闻/否定，不判断对错、不自动写小说，也不把它作为 V114 reducer confirmed state。这些能力只有 opt-in 实验调用，**未默认塞进 G 或 Studio 写作提示**，因为真实试验尚未证明能改善自审。
- **新真实原件**：[三条件原句与完整解释](WF_REAL_DEEPSEEK_451_BLIND_SOURCE_V116_20261024.md)；第一阶段源回复 [Actions 附件 #12564063524](https://github.com/66tyu55/WriterForge/actions/runs/40104976936/artifacts/12564063524)，第二阶段位置复盘 [Actions 附件 #12564064911](https://github.com/66tyu55/WriterForge/actions/runs/40105777757/artifacts/12564064911)，原始创作回复 [旧附件 #12559689583](https://github.com/66tyu55/WriterForge/actions/runs/40094106486/artifacts/12559689583)。新增 3 calls 报告 usage prompt 5,055 + completion 527 tokens，不能虚构现金价格。
- **CI**：[最终无模型全量 #40105578908](https://github.com/66tyu55/WriterForge/actions/runs/40105578908) **1,539 tests run，4 skipped，0 failures**。包含来源字节和旧 provider wire 被篡改时拒绝推断、全句无损索引、V116 不把引述／假设当场景事实、新源码兼容老系统。
- **下步文学方向**：停止同稿多遍付费劝删，转向**同一写作 AI 的独立读者视角先重建“已写原文”和“只能猜到的动作”差异，再交回原作家自行决定 KEEP/LOOK_BACK_NOW**。WF 只保留 source-first 证据和 V119/114/117 事务，不靠美学评分自动否决 MOVE_ON。真正下一次样本要有独立匿名阅读、来源有界的真实模型修订、修改前后效果对照；新付费试验需用户另行指示。

## 本轮最新 0.N：三个现有真实模型试验（2026-10-24，最新）

**真实原件及正反例总览**：[WF_REAL_THREE_EXISTING_WRITER_MODELS_20261024.md](WF_REAL_THREE_EXISTING_WRITER_MODELS_20261024.md)。用户已明确授权从现有模型选几个做真实试验；开发分支单独触发两轮总计 **8 次真正供应商请求**。第一轮 [#40094106486](https://github.com/66tyu55/WriterForge/actions/runs/40094106486)，第二轮仅对超限者做推理参数/输出预算补测 [#40094721282](https://github.com/66tyu55/WriterForge/actions/runs/40094721282)；原始 wire、完整模型原创小说与同模型自己的决定分别保留在这两轮的 GitHub Actions 附件（30 天期限）。

- **三现有模型与相同新题**：DeepSeek 官方 `deepseek-flash`；现有 Discovery `glm-5.3` 与 `kimi-k2.6`。统一新原创“顾翎/程九、受伤左手、带血旧税簿、将断的渡索和对岸未知求救者”，由模型自己写小说；同一个写作模型自己选择 `MOVE_ON` 或 `LOOK_BACK_NOW` 并说出理由，只有有效 LOOK_BACK_NOW 才会进入原 V119 的精确修改。WF 没有替 AI 做文学判断、生成替代剧情或强迫它删稿。每模型一次成功链最多 3 次请求、网络错误不重试。
- **首次付费输出不可擦掉**：DeepSeek 完成真实小说 **451 字符**、V96/V114 源检查通过、自选 **MOVE_ON**；GLM/Kimi 初次各消耗 1,450 completion tokens，`finish_reason=length`，保留完整的截断 provider wire，不能算写作失败。仅为使真实返回完整而分开补测 GLM（`reasoning_effort=low` / 更大输出预算）和 Kimi（`thinking.type=disabled` / 更大预算）；不能把不同推理参数称为严格同计算公平对照。
- **最终结果**：GLM 真实原文 **360 字符**、V96/V114 PASS；模型原始文学决定为 `MOVE_ON`，却把真实 64 位 source SHA 复制成 **62 位**，WF 正确记 `INVALID_SIGNAL`，不能自动修成绿灯；Kimi 真实原文 **772 字符**、V96/V114 PASS，自选 `MOVE_ON`，但超过本次建议 **260–520 字符**长度。三者**没有一个**产生有效的自行 `LOOK_BACK_NOW`，V119 真实自动删改成功证据 **0**；原始结果不支持宣称已会人类式作家自我否定。
- **核心文学负例**：DeepSeek 原文写过“程九已经坐进船里”，最后又出现“程九仍蹲在桩边”，缺少下船过渡，自己却称两人的选择与代价已落地并决定 `MOVE_ON`。这证明来源格式 PASS 与模型自评满意都不能独立证明小说位置和因果一致性。今后应研究“AI 自己发现实际正文哪里错误并真的有效改好”，不能 WF 通过关键词、分数或强制删稿充当文学裁判。
- **安全验收**：[离线全量 #40094532271](https://github.com/66tyu55/WriterForge/actions/runs/40094532271) **1,531 tests run、4 skipped、0 failures**，验证真实实验白名单/次数/源锁/自主选择和两供应商参数。此前 0.M Studio 内同一 AI 的**章节边界 opt-in、候选版本分叉与冷重启**工程功能仍在，**本轮真实试验是单场景**，不是完整双章 Studio 真实验收。
- **后续范围**：先让人独立匿名阅读三份真实正文并定位错误，再以严格同篇幅/预算多类型新题试验模型何时会自然回头，尤其核查修改后人物空间/认知/物件真的改善。机械 source SHA 可考虑由已有工作台做来源确定性绑定，但不能改模型原始回答、抹掉失败或替 AI 判断文学。**本轮 8 次调用全部结束，未经用户再次授权不要自动启动其他付费推理。** main/Railway/R2 原著/Canon/已有 V26、V98、V119、V117/唯一图未改，不重复文学训练。

## 本轮最新 0.M：同一写作 AI 自主选择是否跨章回头，Studio 本地重启续写（2026-10-24）

**详细新增工程证据**：[WF_AI_STUDIO_CHAPTER_SELF_REVIEW_BRANCH_20261024.md](WF_AI_STUDIO_CHAPTER_SELF_REVIEW_BRANCH_20261024.md)。[最新完整无模型 CI #40090238474](https://github.com/66tyu55/WriterForge/actions/runs/40090238474)：**1,525 tests run、4 skipped、0 failed**，内含 Studio JavaScript 语法校验。依然只改开发分支，不重训、不改 main、不给 Railway/R2 部署或写原书。

- 已在原 writing_assist.py 实现一次 **同一模型真实请求的章节级 MOVE_ON/LOOK_BACK_NOW 选择点**：完整交付刚生成的两章原文、SHA 和作者目标，模型自己给出为什么保留或回看、唯一原句/缺失场景问题和预期读者感受；WF 不审文学、不会提供小说正文或要求必须删稿。只接受源锁定 JSON，任何非唯一原句、错 SHA、格式失败或完整原文超过 10k prompt 上限，均不强制重写、不中途假装已读。原始模型答复字节单独保留。
- StudioService.start_auto 现在有**默认关闭**的 ai_chapter_review。仅 G continuity_guard、明确接续已有签名未接受前章、恰好写两章、事件段 AI 自主判断开通且无人工逐段停顿；**用户只发送一次任务**，AI 在章节完成后可选保留或对第一章回改，再由原写作模型在新私有 job 重写受影响的双章。最多一次判断和一次重写；失败保留原稿，丢弃坏分支，不无限重新付费。
- 现有 Studio UI 提供选项、候选旧稿/新稿切换。原 Studio 本地项目目录新增非文学记忆的候选分支选择 SHA 元数据；选定新分支的后续 V117 恢复会拒绝旧分支下游。重启冷读原始 local manifest、每章候选**实际字节**、统一 graph 的源 SHA、V117 signed resume、fork 收据；来源改动或目录不合法就 fail-closed，不再只依赖进程内的一条路径。旧本地历史文件和人写原稿不动。
- 原始红灯 [#40089790688](https://github.com/66tyu55/WriterForge/actions/runs/40089790688) 是目录构造器错误把已校验内容视图当作签名目录，导致 WF_STUDIO_BRANCH_CATALOG_TAMPERED；修正返回契约而非放宽安全校验。 [#40089940484](https://github.com/66tyu55/WriterForge/actions/runs/40089940484) 1,523 绿；最终 #40090238474 1,525 绿，含 HTTP 令牌/跨 job 拒绝与模型重写失败退回原分支。
- **不能夸大**：这次供应商都是零付费 mock，原真实 DeepSeek 仍只有首段 INVALID_SIGNAL 和第二段 MOVE_ON（0.I）。**尚没有真实模型自己选跨章 LOOK_BACK_NOW 并成功提升作品**，没有独立文学盲评；适用范围还是有前缀签名的**两章**第一章回看，不是任意多章、逐字流式删改或 R2 跨设备全局事务。下一步才是有限同模型原始 wire 试验和文学盲测，需另外授权。

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

「继续 WriterForge。读取开发分支 refactor-unified-scene-delivery-audit 的 docs/WF_NEXT_SESSION_AI_WRITER_HANDOFF_20261024.md 和 CURRENT_HANDOFF.md 最新 0.N。核心是 AI 自己决定什么时候不满意、为什么删，WF 绝不能替 AI 计算文学意义或生成，保持 V26/V98/V119/V117/统一图。先核验最新 1525 测试（含 Studio AI 自主章节选择、签名版本选择、冷重启、HTTP 防护）与历史真实 6 次调用、零模型回放，保留首段 INVALID_SIGNAL 和第二段 MOVE_ON 的负例，再针对真正自发 LOOK_BACK_NOW 与下游状态回退做最小验证；禁止重复训练、增加记忆、改 main 或部署 Railway。」
