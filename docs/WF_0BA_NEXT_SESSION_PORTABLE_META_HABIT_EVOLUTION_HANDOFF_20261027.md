# WF 0.BA｜下一会话正式交接：从弱小寄生式工具到可迁移、可停止、可证伪的认知习惯进化系统

日期：2026-10-27。本文件是**下一阶段实施方案和已验证状态**，不是 0.BA 新功能已经完成的声明。唯一可写分支：`refactor-unified-scene-delivery-audit`。撰写前实际 HEAD `adbf299ed3fcfe0f8fc76b5a1b47803505d34d85`；下次必须先重新检查当前 HEAD。

## 一、用户真正的目标

把 WF 当成没有大模型权重、没有自主获得资源能力的弱小寄生式认知系统：

1. **宿主给资源**：授权的模型推理、上下文、工具、文件和预算；WF 绝不能自行获取宿主凭证、隐私原稿或绕过运行权限。
2. **WF 带走习惯**：换宿主也能保留已验证的认知行为、可证伪条件、负例、版本和证据 SHA；带走的不是小说人物记忆、模型隐藏推理、训练权重或某家模型的提示词补丁。
3. **Skill 形成生态**：分工、互相提出修改、离线对照、保留互补、竞争淘汰、污染祖先/后代追踪，不允许任何 Skill 直接篡改另一个 Skill 的正式版本或评委/权限/测试真值。
4. **值得进化才进化**：允许等待、休眠、失败、退休和冻结成熟版本；资源不足不能当能力失败，无文学收益不能只凭高分冒充进化。
5. **真正写作 AI 保留作者主权**：WF 不代写情节或正文、不强迫删除；保留 V26、V98、V119 和唯一 NarrativeCore，不新设独立叙事记忆。

首个认知习惯 `observe-before-next-choice`：**先看到真实已写行动、人物信念和不确定性，再由模型作者自行选择下一步**；它不是“永远禁止重复动作”的文学检查器，合法反复尝试、留白与有限认知必须保留。

## 二、下次第一阅读顺序

1. `docs/CURRENT_HANDOFF.md` 顶端 0.BA；
2. 本文件；
3. `docs/WF_0AZ_REAL_HOST_429_HABIT_DORMANCY_SOURCE_FIRST_20261026.md`；
4. `docs/WF_0AX_META_SKILL_ECOLOGY_ACTUAL_CAPABILITY_AUDIT_20261026.md`；
5. `docs/WF_0AW_OPEN_SOURCE_SELF_EVOLUTION_CODE_REVIEW_20261026.md`；
6. `.agents/skills/observe-before-next-choice/` 的 `SKILL.md`、`capsule.json`、`scripts/portable.py`；
7. `writerforge/evolution.py`（现有 Registry/Evolution 与 0.AZ 停止函数），`writerforge/scheduler.py`（静态 DEFAULT_CAPABILITIES），`writerforge/reactive_runtime.py`、`writerforge/experience_decision.py` 和 `writerforge/db.py`；
8. `writerforge/v98_rolling_causal_planner.py`、`writerforge/writing_assist.py`、`tests/test_wf_0av_g_writer_original_prose_at_prose_stage.py`。

不要重复已完成的 0.AV《夜阀》、十类旧短稿、旧六段、15章旧训练。

## 三、不可覆盖或误称成功的真实成果

- **0.AX**：发现 Registry 已有版本、SQLite CAS、签名与 SHADOW/ACTIVE/RETIRED 管控，但 Scheduler 使用静态 `DEFAULT_CAPABILITIES`，没有形成真正的**Skill 已批准版本 ↔ 真实调度 ↔ 后续验证/退休**闭环。互相提议 patch、污染后代、真实跨应用宿主也尚未闭环。
- **0.AY**：创建首个独立标准技能 `.agents/skills/observe-before-next-choice/`，含 SHA 锁定的无记忆胶囊、两种封装适配与纯 Python 离线验证，工程 GREEN [#40352617638](https://github.com/66tyu55/WriterForge/actions/runs/40352617638)，1854 tests、10 skipped。胶囊完整 SHA256：`42cad98118dea662cea472f708ef1de22f4bb139da3210b1f5c3c1f9ac12664d`，必须保留旧 v1，不得重写内容后仍声称 SHA 一致。
- **0.AY 两模型付费实验**：[Actions #40354436598](https://github.com/66tyu55/WriterForge/actions/runs/40354436598)、artifact **12664209371**。同一 GitHub Actions Python 运行壳，DeepSeek Flash + Discovery GLM-5.3 两家**模型服务**；预登记最多八次调用。实际**尝试四次**，合法原始正文三份：DeepSeek control 253字、habit 214字、GLM control 267字；GLM habit 第四次 HTTP 429，**没有任何有效正文回包**，后续四次没有运行。7200 completion tokens 为请求预留，不是实际消费/账单。只有 DeepSeek 一组成对文稿，未做人类独立盲评，文学受益和跨模型价值 **UNPROVEN**，更**不是两个独立 Agent 应用宿主**。
- **0.AZ**：[真实源-only 回放 #40356733598](https://github.com/66tyu55/WriterForge/actions/runs/40356733598)，artifact **12665747871**。原三份 provider wire SHA、全部冻结请求和第四次缺失回包均核查。现有 `writerforge/evolution.py` 增加 `HabitTrialEvidence`、`HabitTrialDisposition`、`assess_habit_trial_continuation`，9 个新案例、全仓 **1868 tests、10 skipped、0 failures**，0 次新模型调用。
- **精确状态**：**本次实验会话** `DORMANT_HOST_RESOURCE / NOT_TESTED_INCOMPLETE`；**技能胶囊**仍为 `SHADOW`。0.AZ 是只读/离线建议，不自动改变 SkillRegistry，不重新调用 GLM，不证明技能被证伪或污染。
- V98 曾经只给规划模型先前正文、不给真正正文写作模型，导致 t05 重复信号切断；原 `v98_rolling_causal_planner.py` / `writing_assist.py` 已针对真实 RED 修复，[#40351122070](https://github.com/66tyu55/WriterForge/actions/runs/40351122070) 已验收。不可继续用旧题付费刷“新的”文学提升。

## 四、最终解决方案：两层协议、一条可证伪演化流

**Habit Capsule（有）**：保存行为过程、适用/禁用条件、反例、版本、源 SHA 指针、授权/资源上限与停止条件；独立于具体模型和小说。用户原著、私有 R2、模型思维链和个人记忆全部不随包迁移。小胶囊不能凭自己的 status 字段授权执行。

**Host Adapter（只有初版封装，还没有真实跨应用证明）**：宿主能力探测 → 验完整胶囊 SHA 和任务真实来源 → 按新宿主权限/上下文组织**同一核心行为合同** → 显式授权后最多一次执行 → 原始 provider wire、耗费或未知账单记录 → 可拒绝/休眠。两个不同 API 不等于两个独立宿主。

**Evolution（部分有）**：原文真失败 → 区分宿主容量/协议/上下文递送/习惯逻辑/不可靠文学评审 → 离线候选 → 冻结反例/留出集 → 可重现对照 → 独立评估 → 依据证据进入 SHADOW、批准 ACTIVE、保留互补、DORMANT、REVIEW_QUARANTINE_LINEAGE 或正式 RETIRED。无独立人类/读者锚点的审稿器分数不能自动决定文学技能晋级。

## 五、下一会话必须首先完成的 P0（不要同时开很多模块）

**任务：真实连接 SkillRegistry 的信任状态/版本与 SkillScheduler 的“可选认知习惯”执行决策。** 当前静态调度的断口是比扩充群落数量更根本的架构问题。

执行：
1. 核查 `SkillScheduler.select`、`batch_decision`、`enqueue_event/flush_pending`，以及 `SkillRegistry.get/all/revalidate` 的真实逻辑，先写能运行的 RED：SHADOW、RETIRED 或未经签名批准的“可选习惯”不能进入实际 execution；依赖不足、篡改 capsule SHA、状态入队后过期都不能悄悄通过。
2. **默认关闭**的新 Gate 只能作用于“明确声明为可选习惯”的部分。保留旧静态调度行为和最重要的 `runtime_guard`/`snapshot_guard` 等核心；**不能因为当前 Registry 为空就让整个 WF 停摆**。旧 V26/V98/V119 和唯一 NarrativeCore 绝不能变成该实验 Skill 的依赖。
3. 真正激活需满足可信 Registry ACTIVE（不是模型自报）、所需 revision / artifact digest 一致、依赖完成再验证、宿主权限/预算可用；SHADOW/RETIRED/NEEDS_REVALIDATION/隔离候选必须 fail-closed，只暴露稳定 skip reason。尤其需防缓存/队列内**已选中但后来撤销**的旧任务执行。
4. 先 RED→仅修改原 `scheduler.py` / `evolution.py` 的最小 owner + 必要测试→完整 `python -m unittest discover -s tests -q`→GitHub Actions 最新 run 日志 GREEN。0 次模型调用。测试需覆盖零 Registry 回归、身份/哈希伪造、正常激活、撤销、依赖滞后、竞态、预算和合法其他 Skill 不变。
5. 完成标准：真正 dispatch 路径能有效执行/拒绝可选 Skill，版本/来源/状态理由真实；**不是**新增几句说明/提醒/审稿器。只报工程进步，不冒称文学改善。

## 六、P0 完成后才逐步实施

**P1 最小群落候选和污染链（离线）**：Skill A 只能提出 B 的候选 patch（不可直接覆写）；记录 `parent_capsule_sha → candidate_sha`、改动目标/允许写入面、证据和独立 evaluator；用两个候选、一个后代的合成 fixture 演示有污染的祖先令子代进入重验证/隔离。不能修改测试真值、评分门槛、main、Canon、R2 或主动部署；旧失败证据必须保留。

**P2 真正的跨宿主（须新授权）**：独立 Agent 应用程序实际加载 v1 SHA、获得各自授权工具、读当前用户批准的来源；用全新小说题、多类型合法重复/有限认知负例进行同宿主 control/SHADOW-habit A/B；全部原始回包/费用/长度/失败公开可复验。不要靠换两个模型的 URL 冒充两个宿主。任何资源/429 问题先停止，并保留验证过的习惯历史。

**P3 值不值得进化**：只有实际跨新题/宿主稳定收益、回归无负迁移、独立读者证明文学改善且成本值得，才提议手动升格；失败次数有限且不值得花费时选择 DORMANT。成熟能力可以停止迭代，能力很强不等于永远改写自己。

## 七、必须坚持的边界

- 不改 main，不部署 Railway，不读写用户 R2 原著/正式 Canon，不重跑过去已经付费的小说稿或训练。
- WF 不替 AI 决定剧情/写正文/删句、不强制多轮改稿、不建立新叙事记忆，保留 V26/V98/V119/唯一 NarrativeCore。
- 来源 SHA 证明原字节一致，**不是**已证因果/作者身份/防 prompt injection；CI GREEN 不证明文学进步。
- 429 只证资源/当前请求失败，**不能**构造缺失 GLM habit 原稿，也不能宣称同一胶囊跨模型价值已经确认。
- 新模型调用必须明示权限与预算；失效时无重试。Skill 不能自修改 evaluator/晋级签名/固定留出集。
- 原 0.AZ stopping 函数是**建议**，不是已正式撤销/晋级；不要将 DORMANT_HOST_RESOURCE 错当 SkillRegistry 退休指令。

## 八、可直接复制进新对话的接续命令

继续 WriterForge 0.BA。先读最新 docs/CURRENT_HANDOFF.md、docs/WF_0BA_NEXT_SESSION_PORTABLE_META_HABIT_EVOLUTION_HANDOFF_20261027.md、0.AZ 真实 429/原始三份 provider wire 报告及 0.AX 元 Skill 源码审计；再查 .agents/skills/observe-before-next-choice/、writerforge/evolution.py 与 scheduler.py。只在 refactor-unified-scene-delivery-audit 工作。WF 是依靠宿主授权资源、不因换宿主而从零开始的认知习惯系统；不是某模型提示词补丁。首要任务 P0：让 Registry 的可信可选 Skill 状态/版本/依赖/胶囊 SHA 在 Scheduler 实际 dispatch 中生效；先可复现 RED、最小底层修复、全量 GREEN，零文学模型新调用，不影响旧运行时/小说。0.AY 的 GLM 429 必须休眠不重试；胶囊仍 SHADOW，文学跨宿主收益 UNPROVEN。P0 后再设计受控互提补丁、污染后代、竞争与真正两个独立应用宿主验证。禁止碰 main、Railway、R2 原著、正式 Canon、旧付费小说训练或第二叙事记忆。
