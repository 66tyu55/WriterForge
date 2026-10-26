# WriterForge 0.AX｜元 Skill 群落生态能力源码审计（2026-10-26）

## 0. 结论和证据边界

**WF 已有受控元能力内核，但不是能自主分工、提出补丁、验证、竞争淘汰并跨宿主搬运的完整 Skill 群落。**

检查基线：开发分支 refactor-unified-scene-delivery-audit，读取 HEAD 42497f0c8df546c5c699387f9c536074fced11b9；用户这次要求“看看”，本文只核查源代码和既有测试，不擅自引入依赖、改变 main、安装未知 Skill、修改 Railway、R2 原著或 Canon。本审计**没有执行新的文学模型调用或跨宿主实测**。当前 HEAD 正带有先前 0.AV 单独新增的故意 RED 测试，不能借本报告把当前 HEAD 宣称为全量 GREEN。

分清三个概念：
- **作家能力**：写作模型根据正文做选择、伏笔、对话、删改。WF 不能替作者决定。
- **元 Skill 内核**：WF 能持久化和审阅 Skill 能力合同、依赖、升级与失效。
- **元 Skill 生态**：多个可执行/可加载 Skill 可受控提出候选、互相建议补丁、验证交互影响、竞争退役、记录污染谱系，并可在别的 AI 宿主运行。现有 WF **不具备完整第三项**。

## 1. 六维查实状态

| 能力 | 核查状态 | 源码证据 | 仍缺的执行闭环 |
|---|---|---|---|
| 元技能总控与持久化 | **有真实基础** | writerforge/evolution.py SkillRegistry/CapabilityContract/EvolutionEngine; writerforge/db.py skill_capabilities/skill_upgrade_events/evolution_failures; tests/test_v12_evolution_taste.py、test_v64_bootstrap_origin.py | 升级的是能力等级、描述、依赖，不是可执行 Skill 内容或独立包 |
| 群落分工与协作 | **部分有** | writerforge/scheduler.py 默认 REACTIVE/BOUNDARY/OFFLINE 等 29 左右固定 Capability；craft_engine.py 五类技能；reactive_runtime.py 依赖指纹、局部失效、缓存与 singleflight | 调度列表 DEFAULT_CAPABILITIES 是静态的，未根据 SkillRegistry 的 ACTIVE/SHADOW/RETIRED/版本自动更换实现；无技能相互作用的生产追踪矩阵 |
| Skill 互改/共同演化 | **缺失实际闭环** | evolution.py 的 UpgradeCandidate 仅有 skill、新级别、statement、证据/数值；SkillBirthGate.decide 只是返回 MERGE/CREATE 判定 | 无候选 Skill 文件/代码 diff、所属 owner 授权、提议/审阅分离、工具与 Skill 的原子联合改动及对比验证；禁止同级技能互相直接写生产代码 |
| 竞争、淘汰与保留 | **有门槛和状态，未形成生态选择** | PromotionGate 检查 heldout/transfer/regression/judge 稳定度/运行成本；SkillStatus 有 SHADOW/RETIRED；SkillBirthGate 控制重复诞生 | 无主动生成多候选、同题配对对照、多技能联合启用实验、互补/冲突评分、实际 winner 切换、胜出对照、过期无贡献 Skill 的自动退役流程；默认静态调度没有读退役状态 |
| 污染与负迁移 | **来源侧做得较扎实，但 Skill 生态污染未闭环** | experience_decision.py source SHA、审批/撤销、NOT_APPLIED/UNCERTAIN/NEGATIVE 阻隔；V63/V64 注册/晋级签名、SQLite CAS 和 AI 来源限制；research/skill_ecosystem 手工 intake | 无外部 Skill 权限/副作用审计（同进程 Python 不构成沙箱）、不可信指令注入检查、Skill 内容及引用资源签名链、祖先污染->后代撤销/重新验证、训练泄露与宿主环境不兼容检验 |
| 跨宿主可迁移习惯 | **只有根 SKILL.md，未证实跨宿主** | 根 SKILL.md 以 writer-forge-v27 名义给出完整大框架；pyproject.toml 只安装 writerforge* 包并暴露 writerforge CLI；research/skill_ecosystem 手工指派上游 Skill owner | 无规范的独立 SKILL.md 目录包导出/导入验证；当前 root SKILL.md 的 name 与仓库目录名不一致；无兼容声明、无适配器协议/权限协商、无至少两宿主的相同行为回归 |

注意：有一条**真实强项**不应埋没：SkillRegistry 的签名、限制初始等级、升版时 SQLite 原子核验及依赖者 NEEDS_REVALIDATION、禁止 SHADOW 任意自激活，已经有合成测试。它解决**形式权限、陈旧写入和篡改问题**，但不代表跨宿主真实文学可移植性或 Skill 内容防污染。

## 2. 代码和测试定位

- writerforge/evolution.py: SkillStatus, CapabilityContract, SkillRegistry, FailureClusterer, CurriculumPlanner, SkillBirthGate, PromotionGate, UpgradeCandidate, EvolutionEngine。SkillBirthGate 的“三集合 Jaccard 相似度”只返回 create/merge 建议；EvolutionEngine 没有真正的 patch 生成或候选执行回调。当前文档 evolution/EVOLUTION_ENGINE.md 的完整训练/留出/晋级闭环是预期方案，不代表全自动已运行。
- writerforge/scheduler.py: DEFAULT_CAPABILITIES 为**代码固定列表**。SkillScheduler.select / flush_pending 选择能力**名称**并进行预算调度，但构造函数不接受 SkillRegistry，也不读取 SQLite skill_capabilities 表。因此“退役自动不进入运行时 / 升级马上切换新技能”不是现有源码保证。
- writerforge/craft_engine.py 与 scene_craft_teaching.py: 有阶段性 technique cards、按场景选择和来源限额；它们不是任意第三方 SKILL.md 生成器或自治共进化策略。
- writerforge/experience_decision.py: 冻结可信 experiment 入口，接受负反馈、撤销、暂停；明言“no skill level promotion occurs here”。不能把原小说素材记忆/训练索引当作已证明的可迁移技能。
- writerforge/db.py: skill_capabilities 表存 skill name/level/status/revision/statement/dependencies；skill_upgrade_events 存等级变化；当前**不存**可执行技能包内容哈希、互改提议、parents、host compatibility、单技能/组合试验胜负，或污染子孙闭包。
- research/skill_ecosystem/README.md、UPSTREAM_SKILL_MAP.md、integration/HOT_SKILL_ASSIMILATION.md: 122份上游 Skill 收件、ADOPT/MERGE/WATCH/REJECT 人工映射；**显式不在生产运行时**。这是一套合理防止直接装大依赖的准入纪律，不是运行的群落。

**现有测试**：test_v12_evolution_taste.py 覆盖受控晋级、依赖影响、失败聚类、出生合并、留出/迁移门槛与缓存；test_v64_bootstrap_origin.py 覆盖签名初始化、老等级 SHADOW、模型稿来源隔离。均以**合成数据**为主，不能证明多 AI 宿主真实执行一致或文学质量提升。

## 3. 从最近研究看，缺口的性质

研究材料（只借设计思想，未复制/安装）：
- SkillSmith（arxiv.org/abs/2606.01314）：技能与工具可以成组修改、分裂/合并/退役；依据真实执行追踪估算互补与冲突、竞争上下文预算。WF 现在只有静态分工，没有这些交互反馈。
- When Self-Evolution Backfires / VaG（arxiv.org/abs/2608.05810）：坏 Skill 进入之后可能继续污染后代，**事后删掉上游并不自动撤销下游**；需要先验结构/行为/语义门禁、记录污染谱系与组合增益。WF 的原文 SHA/负反馈是基础，但不是已实现的 Skill 子孙隔离。
- WikiSkill（arxiv.org/abs/2608.27454）：将原始轨迹、可回顾的经验知识、被验证的可执行 Skill 三层分离。WF 已经有文学来源/经验分流和唯一 NarrativeCore，应借**边界与传递机制**，不新建第二个小说情节记忆主人。
- Agent Skills 正式规范（agentskills.io/specification）：独立 skill-name/SKILL.md、可选 scripts/references、名称匹配、兼容性/许可描述、渐进加载。根 SKILL.md 的路径和名称不是现成可装的跨宿主子 Skill 包；仅将 Python 项目 pip install 不等于安装任意 Skill 主机适配。

以上外部论文的工作负载主要是 agent/task/benchmark，并**不能推导中文长篇文学直接收益**。

## 4. 推荐的最小底层路径：不是另加一套审稿 Agent

**P0（解决“技能是否真的工作”）**：从现有 SkillRegistry 出发为 Scheduler 加可选 verified ACTIVE 快照/版本引用，且保留默认旧行为。先以离线合成对抗证明退役/被污染 Skill 不被 dispatch，未经过人工签名的候选只能 shadow，依赖变更重验证而不是改写小说；留原 SQLite 作为持久事实来源。

**P1（候选生态，隔离文学创作）**：给离线 Evolution 受控的 Proposal API：某个 Skill 可提出修改另一个 Skill 的候选，但其写权限只有 proposal artifact（签名哈希、patch、预期依赖影响、行为可验证回归）；不能改 evaluator、保护阈值、Canon、正文、R2 作品或主分支；另一角色在固定留出集验证，不可由 proposer 的打分自批准。实际 novel writing 模型自主选择情节和删改；meta Skill 只能更好地递送原文或实现回滚/预算。

**P2（真群落竞争与防污染）**：离线用新原创题及已经冻结的小说片段/反例，比较 单Skill/组合/无Skill 三种调用，记录通过率、文学读者盲评、角色选择变化、重复动作、篇幅、成本和失败。不能只按百分制消灭擅长留白的技巧；对冲突 Skill 可以保留不同生态位，不需要强制 winner-takes-all。记录父子派生 SHA；若一版污染进入后代，应阻止后代进 runtime，并重做对照而不是仅删祖先文件。

**P3（跨宿主“习惯”而非复制小说记忆）**：每个经过真实证据验证的通用习惯可以尝试导出标准目录，含 SKILL.md、行为合同（触发/禁用条件、前置能力、预算/权限、退路）、工具中立引用、可复现实验SHA、兼容性声明及最小 conformance fixtures。小说人物事实/原著片段/私有密钥**永不随习惯打包**。用至少两个真实不同宿主进行真实执行 + source SHA 对照 + 失败隔离测试，尚未验证前标 NOT_PORTABLE_VERIFIED。永远不要保证“所有宿主无问题”。

最先适合做成可迁移习惯的不是“金庸式对白模板”，而是 **“写下一段前，把已经写过的准确动作原句及出处交给作者，让作者选择下一步；不得把缺失后果臆造为事实”**。它是可以在多个题材测试的写作过程能力；不是替原作者选择人物命运。

## 5. 不可回避的原则

1. 元 Skill 生态只在 OFFLINE 或单独隔离候选通道自进化，**不新增第二小说记忆**。
2. 外部 Skill/项目的 prompt、脚本和参考材料不因 GitHub stars 或通过语法校验就获写作权限。
3. 允许 Skill “互相提出修改”；**不允许**无审核的互改、无租界地共同运行 Python 或直接拿自己的评分自行晋级。
4. 只有真实证据说明 WF 辅助写作变好，才能说文学技能获得提升；当前工程框架相对完整但此结论仍 UNPROVEN。

本文件是结构审计，不是新工程修复/新的实际模型训练结果。
