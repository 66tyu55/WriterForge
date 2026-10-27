# WriterForge 0.BA｜实际 P0/P1 元 Skill 可信执行、宿主资源停止与公钥谱系迁移（2026-10-27）

> **这是已执行源码的审计交接，不是文学能力提升结论。** 唯一修改分支 \`refactor-unified-scene-delivery-audit\`。历史 0.BA「下次工作计划」和 0.AZ/0.AY 原始失败必须保留，不能把本报告视为新付费写作训练。

## 1. 现状、代码所有者与可证伪边界

WF 依附宿主经授权提供的推理/工具/上下文，而非拥有模型权重。跨宿主保留的是**经来源标识的认知过程、负例、版本、权限需求与停止条件**，不是模型隐藏推理、个人记忆、小说原著或 Canon。真正作家模型仍拥有文学正文、情节选择与自主删改决定权；V26/V98/V119 和唯一 NarrativeCore 没有变成元 Skill 的依赖。

本轮在原 owner 中完成：

- \`writerforge/evolution.py\`：新增 \`OptionalExecutionPermit\`，绑定 Registry 可信完整契约摘要、版本、所需依赖 revision、胶囊 SHA256、宿主权限和外部审阅签名。每次鉴权重新核对 SQLite 的实际状态（拒绝过时 Registry 缓存），SHADOW、RETIRED、NEEDS_REVALIDATION、未满足依赖、虚假签名、伪造 SHA 都 fail-closed。旧正式晋级规则仍由原 Evolution 控制。
- \`writerforge/scheduler.py\`：仅当 \`Capability(optional_habit=True)\` 且 \`enable_optional_habits=True\` 时接入上述权限。默认静态旧核心完整保留，尤其 \`runtime_guard\` 和 \`snapshot_guard\`，空 Registry 不关闭 WF。实际 \`select\`/\`batch_decision\`/\`flush_pending\` 均附稳定授权拒绝原因。
- \`writerforge/lane_scheduler.py\`：入队可选 Skill 与当时可信许可绑定；出队重新检查，撤销/变更 SHA/依赖/权限后任务不运行、不挤占核心任务预算。旧 core lane 任务无额外执行前提。
- **单次执行权限**：\`SkillScheduler.execute_optional\` 实行每次选择独立随机凭证、同 Scheduler 内锁保护一次性兑现；回调失败/重入/并发不能复用，最多保留 256 张未兑现凭证避免内存无限增长。
- **宿主有限资源**：\`OptionalHostResourceLease\` 由可信宿主**显式注入**，调用次数在共享实例中原子扣减，多个 Scheduler 并行不能超额；无租约可选 Skill fail-closed。\`OptionalHostResourceUnavailable("HTTP_429")\` 只能来自宿主适配器的**结构化资源失败**，立即把本次宿主租约的该 Skill 挂起，不自动重试；不影响别的 Skill/核心，也不自动退休 Registry 能力或把文学质量判差。

**非常重要的安全限制**：上述租约统计的是**被委托回调尝试次数**，不等于供应商的 token、账单、内部重试或跨多个进程的持久预算。任意不可信 Python 回调同进程运行并不构成权限沙箱。真实宿主必须独立实现 API 调用边界、预算、外部撤销与多工作进程原子计数；这些在本轮**没有宣称完成**。

## 2. P1 候选群落、隔离、迁移

仍在 \`writerforge/evolution.py\`，没有复制第二套小说记忆、没有装第三方不可信 Skill：

- \`PortableHabitCandidatePool\`：Skill A 可提出修改 Skill B 的**不可执行 SHADOW 候选字节**；锁定 parent SHA → candidate SHA、身份、revision、变更字段、真实证据指针。禁止改 \`authority\`、\`transfer\`、\`provenance\`、\`stopping\`，禁止修改测试真值/审稿配置/Canon/用户书稿、禁止变成 ACTIVE。
- \`HabitCompetitionEvidence\`：仅接受独立评价方的有签名结果、相同固定 heldout SHA、样本数/回归/成本参数。允许暂时比较候选，不准拿合成分数宣称真实文学进步，不自动晋级，更不让 proposer 自己签名判胜负。
- \`HabitQuarantineAttestation\`：确认污染后按 SHA 父子 DAG 隔离污染候选与**全部后代**，保留不相关兄弟；禁止隔离祖先继续派生。历史负证据不删除。
- \`export_manifest/from_manifest\`：导出 SHA 绑定的离线候选、签名评价与隔离记录，并要求**独立渠道提供整份 manifest SHA** 后重放。此 HMAC 机制用于本地受信治理，**不应该将其秘密 verifier/key 分享给一个不可信的独立宿主**。
- \`PortableHabitReleaseAttestation\` / \`verify_portable_habit_release\`：使用项目**原已有的可选** \`cryptography\` evidence 依赖里的 Ed25519。接收方只获事先信任的 **32 字节公钥**、独立固定 manifest SHA 和最低 release sequence；重新核查完整清单签名、候选内容字节 SHA、SHA 父子关系、受保护字段、保留/隔离后代及撤销历史。**没有私钥可供接收方自签**，只返回不可执行、不能晋级、未证文学收益的只读结果。

发行公钥检验目前用**临时合成测试密钥**完成，**没有**发布任何正式人工审阅生产发行版，也**没有**两个真实独立 Agent 应用之间的运行与文学评估。外部 Ed25519 发行的信任仍依赖人工验证发行者/公钥，不能把导入文件里的“自称公钥”当信任根。发行签名认证 curator 的整包决议，并不意味着另一宿主持有历史各 HMAC 评价者的签名密钥。

## 3. 完整真实 RED → GREEN 链

| 实现环节 | 真实 RED | 最新对应 GREEN |
|---|---|---|
| P0 Registry → Scheduler 可选权限 | [#40440541765](https://github.com/66tyu55/WriterForge/actions/runs/40440541765)：缺少 OptionalExecutionPermit | [#40440943410](https://github.com/66tyu55/WriterForge/actions/runs/40440943410)：1,883 tests、10 skipped、零失败 |
| P1 两候选/污染后代 | [#40441334121](https://github.com/66tyu55/WriterForge/actions/runs/40441334121)：缺少竞争接口 | [#40441693488](https://github.com/66tyu55/WriterForge/actions/runs/40441693488)：1,892 tests、10 skipped、零失败 |
| 完整 manifest / 重放隔离 | [#40442043330](https://github.com/66tyu55/WriterForge/actions/runs/40442043330)：缺少 export_manifest | [#40442248215](https://github.com/66tyu55/WriterForge/actions/runs/40442248215)：1,896 tests、10 skipped、零失败 |
| 一次性凭证/并发/429 消耗 | [#40442619333](https://github.com/66tyu55/WriterForge/actions/runs/40442619333)：重复执行等反例 | [#40442718121](https://github.com/66tyu55/WriterForge/actions/runs/40442718121)：1,902 tests、10 skipped、零失败 |
| 宿主共享调用次数/429 休眠 | [#40443012533](https://github.com/66tyu55/WriterForge/actions/runs/40443012533)：尚无 OptionalHostResourceLease | [#40443099752](https://github.com/66tyu55/WriterForge/actions/runs/40443099752)：1,908 tests、10 skipped、零失败 |
| 只持公钥验证/污染回滚约束 | [#40443425566](https://github.com/66tyu55/WriterForge/actions/runs/40443425566)：缺少公钥发行校验 | [#40443577341](https://github.com/66tyu55/WriterForge/actions/runs/40443577341)：**1,913 tests、6 skipped、零失败** |

新增定向合成门禁：\`tests/test_wf_0ba_optional_habit_dispatch.py\` **29 tests**；\`tests/test_wf_0ba_portable_habit_candidate_ecology.py\` **16 tests**。工作流 \`.github/workflows/wf-0ba-optional-habit-dispatch-offline.yml\` 默认无模型密钥、无 R2，只运行测试、旧 Studio JS 检查；使用现有 \`[r2,evidence]\` extras，因此与之前缺少 \`cryptography\` 时相比 skip 数从 10 降到 6。不要把 skip 变化当文学评分增长。

原 0.AZ 只读审查同时在 [#40443577515](https://github.com/66tyu55/WriterForge/actions/runs/40443577515) 再次全仓 **1,913 tests、6 skipped、零失败**，artifact 原三份 provider wire 来源重放成功，确认为**实际4次请求、3份有效正文、第4次 GLM HTTP 429**；本次新增模型调用 **0**，状态 \`DORMANT_HOST_RESOURCE / NOT_TESTED_INCOMPLETE\`，仍不能构造第四份 GLM habit 正文。

## 4. 原始 v1 与文学价值边界

\`.agents/skills/observe-before-next-choice/capsule.json\` 原始字节 SHA256：

\`42cad98118dea662cea472f708ef1de22f4bb139da3210b1f5c3c1f9ac12664d\`

v1 仍 **SHADOW**。即使恶意把 Registry 或签名凭证自称 ACTIVE，校验真实 capsule 内 lifecycle/revision 也会拒绝现有 v1。合成候选没有变更正式 v1；新版本“胜出”只是合成离线比较，不代表读者更爱读，也不代表任何正式生产升级。

源码签名、CI GREEN、跨 Python 函数的行为一致，只证明**机械信任链条**；原作者写得是否更好、主动自我修改是否变强、可迁移文学收益是否存在仍 **UNPROVEN**。

## 5. 接下来应做但不可伪称已完成

1. **P2 独立宿主实际许可与兼容性**：用一款真正不同的 Agent 应用加载标准独立 skill 包，并以其拥有的**独立授权**检查源字节、capabilities、输入/生成预算、真实 provider wire 与错误。现有两种 Python prompt envelope 不能充当两个独立 Agent；刚新增的 Ed25519 verifier 目前仍属于 WriterForge Python 包，**还不是独立宿主正式验收**。
2. **公开发行与活跃版本过门禁**：外部人工独立审阅来源/留出集/候选谱系；正式发行公钥必须通过可信路径预配，候选仍 SHADOW；任何真正 ACTIVE 版需现有 Registry 人工许可、变更 SHA、依赖再验证及宿主预算。必须把受污染的发行谱系绑定到真正运行时决策，不能把此文的纯离线隔离冒称完整生产隔离。
3. **进化是否值得继续**：新题材、合法重复、有限 POV、安静场景等负对照、独立读者与真实原始 provider 数据都必须得到同预算对照。无改善或成本高时能长期 DORMANT；429 仅暂停受影响宿主实验。不得为补完整对照重试旧 GLM 或重复旧付费文学实验。
4. **剩余技术风险**：租约仍是进程内授权回调计数，不是多进程强制资源计量；任意恶意第三方 Python 技能并未沙箱化；公钥发行不认证“文学质量”；迁移接收方须防旧签名 release 回滚、提示注入、无授权操作；未作生产持久化基准或多独立应用联合测试。

**红线继续有效**：只修改 \`refactor-unified-scene-delivery-audit\`；main/Railway/私有 R2 原著/正式 Canon 零修改；保留 V26/V98/V119、单一 NarrativeCore、作家 AI 的真正情节与改稿主权；旧实验回包、失败 SHA、反例冻结不覆盖；真实新增付费模型调用需用户重新明确授权和限额。
