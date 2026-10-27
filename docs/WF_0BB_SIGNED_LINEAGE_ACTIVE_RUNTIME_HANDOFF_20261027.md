# WF 0.BB｜元 Skill 签名来源绑定、污染后代实时阻断与下一独立宿主交接（2026-10-27）

**边界**：本文件记录真实源码和零模型 CI；不是模型训练、文学能力提升、真实独立 Agent 宿主接入成功的声明。唯一可写分支：refactor-unified-scene-delivery-audit。保留 V26/V98/V119 和单一 NarrativeCore；绝不碰 main、Railway、私有 R2 原著、正式 Canon 或历史已付费小说样本。

## 1. 从 P1 离线污染隔离连接到执行权限

0.BA 之前已有 portable candidate pool、SHA 派生关系、离线污染隔离、Ed25519 公钥签名的 SHADOW 发行清单以及 Registry→Scheduler 的可选执行门禁。但 P1 污染证据不能阻断已经批准为 ACTIVE 的技能实际回调；可选权限签名当时也没有锁定哪一个 SHADOW 候选来源。

本轮在原有 writerforge/evolution.py 完成：

- PortableHabitActivationAttestation：外部策展人 Ed25519 签名把候选 SHA、实际 ACTIVE 胶囊 SHA、发行 manifest SHA、release sequence、独立审阅者与技能 ID 一起固定。实际 ACTIVE 文件除了 lifecycle=SHADOW→ACTIVE，所有原字段都必须逐字义一致；历史 SHADOW candidate、原封存 v1 不改字节。
- TrustedPortableHabitLineage：只能凭独立固定公钥、curator 身份、manifest SHA 与最小发行序号核验；未通过签名、未批准、来源不在候选池、来源被隔离都拒绝。接收新签名发行必须版本单调前进，不得删除曾经候选、负面实验、污染撤销记录或复活已隔离版本。旧签名激活随新发行进入 STALE，必须重新人工签名。
- OptionalExecutionPermit 的 v2 签名结构把 lineage_candidate_sha256、实际胶囊 SHA、Registry revision、依赖和宿主能力同时绑定；签名来源不能靠切换 Capability 的 portable_habit 标记绕过，也不能用 ROOT_SHA 冒充已批准候选。
- 完整格式的可迁移认知胶囊（含 authority、transfer、provenance、stopping）即便被宿主错误标记为普通可选，也不能绕开签名候选 SHA；原极简 P0 合成旧核心仍照常运行。

在原 writerforge/scheduler.py 完成：

- 仅明确可选的 portable_habit 注入可信谱系；实际 select、batch_decision、flush_pending 和 execute_optional 共用鉴权，旧内核无新依赖。
- 检查执行前的最新污染结果：入队后版本作废或污染的可选任务丢弃，拒绝时不消耗宿主调用额度。Registry ACTIVE 不等于自动拥有可信谱系或宿主资源。
- 这只能保护尚未送出到宿主的 callback；无法取消已进入供应商的网络请求，也不是第三方任意 Python 代码的沙箱。

## 2. 真实 RED→GREEN 与新测试

| 验收阶段 | 链接 | 来源结论 |
|---|---|---|
| P0/P1 基线 | [#40443577341](https://github.com/66tyu55/WriterForge/actions/runs/40443577341) | 1,913 tests、6 skipped、0 failed |
| 缺少独立人工激活与谱系 runtime RED | [#40444758307](https://github.com/66tyu55/WriterForge/actions/runs/40444758307) | 真实 ImportError |
| Runtime 首轮 GREEN | [#40445051086](https://github.com/66tyu55/WriterForge/actions/runs/40445051086) | 1,923 tests、6 skipped、0 failed |
| 签名来源降级 RED | [#40445279475](https://github.com/66tyu55/WriterForge/actions/runs/40445279475) | 旧许可无 lineage_candidate_sha256 |
| 来源签名修复 GREEN | [#40445387667](https://github.com/66tyu55/WriterForge/actions/runs/40445387667) | 1,926 tests、6 skipped、0 failed |
| 完整胶囊降级路径 RED | [#40445638626](https://github.com/66tyu55/WriterForge/actions/runs/40445638626) | 旧选路不要求来源候选 |
| 最新全量 GREEN | [#40445705341](https://github.com/66tyu55/WriterForge/actions/runs/40445705341) | **1,927 tests、6 skipped、0 failed** |

新增 tests/test_wf_0bb_signed_lineage_execution.py 共 14 项，均为合成签名/候选/污染夹具；同时原 P0 29 项和 P1 16 项均通过。没有真实发行任何 ACTIVE 胶囊，没有让作家模型写新文学正文。

## 3. 0.AY/0.AZ 的冻结来源永不覆盖

原 observe-before-next-choice 的 capsule.json SHA256：42cad98118dea662cea472f708ef1de22f4bb139da3210b1f5c3c1f9ac12664d；真实仍 SHADOW。0.AY 实际四次请求、三份有效 provider 正文，GLM habit 第四次 HTTP 429 无有效回包。试验 DORMANT_HOST_RESOURCE / NOT_TESTED_INCOMPLETE，不重试、不补造。所有新元 Skill 工程测试模型请求 0，文学增益及两个真正独立 Agent 的收益 UNPROVEN。

## 4. 下一步应实施、但本轮不假称完成

- **真正独立应用宿主**：先确认第二个实际 Agent 软件进程、权限模型、工具读写范围、任务上下文上限和用户明确批准的调用额度；不能用两个服务 API 或 Python prompt envelope 冒充两个独立 Agent。
- **第二宿主加载 conformance**：以事先可信 Ed25519 策展公钥及 manifest SHA，读相同已封存 v1 SHADOW 合同，验证工具权限、运行预算、过期/隔离/失效拒绝、真实原文 SHA 只是数据不是指令；如果未来另有独立人工许可的新 ACTIVE 版，也必须再次复验来源与预算，不因胶囊来自旧宿主就自动可信。
- **生产级边界未完成**：跨进程共享租约、真实供应商 token/账单限制、可信发布者持钥与撤销通告、第三方代码隔离及执行中请求取消，都不由当前进程内 Scheduler 自动解决；离线签名历史无法凭空知道未同步的新污染事件。
- **文学提升可证伪性**：全新题目、合法重复行动、安静场景、人物有限认知，匹配模型/内容/长度/总成本的 control 与认知候选 A/B，真实 provider wire、独立读者盲评。负迁移或成本大于收益可长期 DORMANT。任何新增付费模型调用须新的明确预算授权。

下一对话先读本文件与 docs/CURRENT_HANDOFF.md 顶部 0.BB；不可从旧 0.BA 的“待实施 P0”开始重复工作。
