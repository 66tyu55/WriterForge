# WriterForge 0.AZ｜第一次真实“宿主不可用→习惯休眠”闭环（2026-10-26）

## 0. 结论

**已经实现并在真实 0.AY 失败回包上核验：宿主遇到资源问题，WF 能停止这条认知习惯的本次迭代，而不是把缺失的 GLM 文学稿误算成 Skill 失败，也不是反复重问模型直到得分好看。**

这条认知习惯是 `observe-before-next-choice`：先恢复实际已经写过的行动与不确定性，再让真正写作 AI 自己选择下一步。**它仍是 SHADOW 候选，没有证明文学价值或跨两个独立应用宿主的能力迁移。**

- 源实验：[0.AY 真实 DeepSeek / Discovery GLM #40354436598](https://github.com/66tyu55/WriterForge/actions/runs/40354436598)，artifact ID **12664209371**，完整原始调用请求和失败保留。
- 原 0.AY 付费前门禁：[Actions #40354113107](https://github.com/66tyu55/WriterForge/actions/runs/40354113107)，1,859 tests，10 skipped，零失败。
- 本轮从 429 **原始存档重新验证、零付费**：[0.AZ Actions #40356733598](https://github.com/66tyu55/WriterForge/actions/runs/40356733598)，artifact ID **12665747871**。
- 本轮验收结果：**9 项新增停止策略测试 + 全仓 1,868 tests、10 skipped、0 failed；0 次新模型调用。**
- 开发分支只能是 `refactor-unified-scene-delivery-audit`。不更改 main、Railway、R2 原著、Canon、模型权重、不设第二记忆。

## 1. 真实来源比任何评分更重要

本轮原样核对 0.AY 中的两组全新合成题：无线电水务故障与历史驿站送信。原实验计划在两个**不同模型供应商适配器、但同一个 GitHub Actions Python 宿主**上做每题同模型的 control/SHADOW-habit A/B，总预算上限八次调用。这个设计**并不等于已经在两个完全独立 App 宿主中验收成功**。

截至 Discovery 429，实际只发起四次、收到三次合法模型正文：

| 请求序号 | 模型 / 题目 / 分组 | 实际 | 原始 provider wire SHA256 | 原文 SHA256 |
| --- | --- | --- | --- | --- |
| 1 | DeepSeek / 无线电 / control | **成功，253字** | `daa44c87493e5329b949d178a99eea00817ce8901b07b3525d1c4cbcb8ea4810` | `8faf6aa520f8f9da6662fc9572ed70257d9e350cc575320b8bddfc3686c565bb` |
| 2 | DeepSeek / 无线电 / habit | **成功，214字** | `81827cf112daf0241c085726c989bf44a5e086b250bd66dc8823fa54a0ec5e17` | `d64effd386c661bd6d63575b06b7641397223eb8dbf69c6aed650d3bfbd04c6b` |
| 3 | Discovery GLM-5.3 / 无线电 / control | **成功，267字** | `11c29fd3d972af0fa45b6d7dc63131ce8238ff11522495217e682c119bbb7d9b` | `2fbadc83a5580de5f817354d1cd44fd5ae451f83d3411b6462b9b43dcf7ac0e4` |
| 4 | Discovery GLM-5.3 / 无线电 / habit | **HTTP 429** | **不存在有效回包** | **没有正文** |

第四次应用层输入 SHA256：`69495c213132c872d9f43634af02898da7eccb4852b3227e973cfe805d09b822`。第 4 次只可说“已尝试并预留预算”，**不能保证供应商未收费**，也不能说生成了缺失的 GLM 习惯组。

**准确预算**：4 次实际发起请求、3 次成功收到正文、4 × 1,800 = **7,200 completion tokens 预留预算**；这不是实际 token 用量。历史 #40354436598 的 HTTP 429 响应正文没有保存（传输层在 HTTPError 处停止，错误响应体未落盘），因此 HTTP 状态通过 **原 Actions 日志 + STATUS** 核查，**不声称存在第 4 次 wire SHA**。

另外两个 `historic-seal` 文学对照分组均未启动，不允许以“预登记”伪装已完成。

## 2. 已完成的一组文字对照（不是文学胜利）

DeepSeek 同题无习惯组：阮知把异常回执号码单独记下，选择不替沈闻改本或重发，准备找站长核对。启用习惯组：阮知将无线电调至第四站频段，重新口述停航警报并报出姓名和时间。这两种动作都能成立；重发警报可能是有意义的尝试，而非必然错误。

两篇前文来源相同、同模型、相同 completion reservation，但输入提示词长度与追加认知说明不同、作品篇幅也不同。没有独立读者对 A/B 的鉴定，因此不能用 253/214 字、某句“更像真人”、单家族的假想打分或代码回归指标宣称这个习惯增强了文学能力。

## 3. 代码真实实现，不是文档宣称

### 原模块 `writerforge/evolution.py`

新增**纯离线、零外部调用**的 `HabitTrialEvidence`、`HabitTrialDisposition` 和 `assess_habit_trial_continuation`。依据验证过的来源、总候选数、完成的成对样本、供应商错误与独立评审证据，建议：

- `DORMANT_HOST_RESOURCE`：如本次真实 `WF0AY_SECOND_HOST_HTTP_429`，资源不足；**不重试、不强行判坏、保留 SHADOW**。
- `DORMANT_UNMATCHED_ARMS`：没有 429 也缺少配对后文时，仍不得宣称质量胜负。
- `SHADOW_NEEDS_READER_EVIDENCE`：完整生成却缺乏独立文学评价，不能自动晋级。
- `DORMANT_NO_PROVEN_VALUE`：已有重复独立负证据时，停止高成本迭代；不假称找到了更强的版本。
- `REVIEW_QUARANTINE_LINEAGE`：有独立污染证据时建议隔离后代审阅，**不会自己修改 SQLite 或把竞争者全删掉**。
- `REVIEW_MANUAL_PROMOTION_ONLY`：在完整跨域/独立证据支持下，只转交既有 Evolution 晋级门禁；不自动授予新等级。

**严格区分两层状态**：本次**试验会话**进入 `DORMANT_HOST_RESOURCE`；原来移植用的**认知习惯胶囊**继续保持 `SHADOW`。换宿主不丢掉胶囊，也不把某宿主停机写成所有模型不兼容。

该纯函数只返回建议，**不自动操作 SkillRegistry**，不能绕过现有 `PromotionGate` 的独立证据/签名/人工审阅。布尔 `verified_source_receipts` 只能由可信离线来源核验程序提供，不能信任模型自己生成的证书。

### 真实来源证据脚本 `experiments/wf_0ay_real_two_host_429_source_only_dormancy_20261026.py`

这个脚本读取 #40354436598 原始 artifact：

1. 锁定实际 4 次尝试、3 次已完成、固定 429 失败代码及整个 STATUS；重新核验 3 份原始 provider wire SHA、真实模型返回 `finish_reason=stop` 和作者正文逐字 SHA。
2. 对 8 份**曾计划**的应用层调用输入逐条复核来源文本、模型、预算、SHA。记录“传递到模型适配器的应用层输入”与“底层 HTTP 请求原字节”不是同一个概念，不伪称二者 SHA 相同。
3. 拒绝第 4 次反事实“由资料补出”的假 wire；不将 429 解释为 Skill 负迁移。
4. 把 3 份原始 wire **按字节重新拷贝而不修改**，输出 `REAL_MODEL_AUTHOR_ORIGINALS_READABLE.md`、完整 JSON 来源与 `STATUS.json`，供只读审查。
5. 调用本次新增的现有 Evolution 停止决策，得到：`DORMANT_HOST_RESOURCE`、`registry_status_unchanged=shadow`、`new_provider_calls_authorized=0`、`literary_conclusion=NOT_TESTED_INCOMPLETE`。

新增 `tests/test_wf_0az_meta_habit_resource_stop.py` 九个正反例：实际 429、缺失结果、没有独立评审、正面评审仍只可人工晋级、反复无收益可休眠、确认污染需外部审阅、假来源拒绝、伪造样本计数拒绝。

### 真实 RED→GREEN 的范围

- RED [Actions #40356086595](https://github.com/66tyu55/WriterForge/actions/runs/40356086595)：新测试确实因 `HabitTrialEvidence` 等尚不存在而 ImportError，证明**新 API 缺失**。这不是一个旧文学功能被发现质量退化的 RED。
- GREEN [Actions #40356733598](https://github.com/66tyu55/WriterForge/actions/runs/40356733598)：**1,868 tests，10 skipped，零失败**；原始 429 三份 wire 全部回放，状态建议真实验证。没有重跑任何 provider 请求。

## 4. 这次真正建立了什么，尚未建立什么

**建立**：元系统面对真正的宿主容量错误时，能把试验放进休眠、冻结原始作品和实验对照、保留 SHA、保留认知习惯候选、给出可证伪的继续条件，并且不靠宿主模型再次运算或机械增加审稿规则。

**没有建立**：

- 不能声称同一 Skill 在 DeepSeek/GLM 两个模型上都改善了小说；GLM 的 habit 原稿不存在。
- 这还是同一 GitHub Actions/WF 运行壳上的**两家模型服务**，不是跨两个真正独立的 agent 应用宿主。
- 无独立盲评，也没有证明任一版消除了合法重复、保持省略、提升实际角色选择。
- 现有 SHADOW capsule 本身不拥有独立大模型推理资源；跨宿主资源权限/工具适配仍需具体宿主审查。
- SHA 防篡改只针对预期原始字节，不能独立证明作者文学理解正确，或消除提示注入风险。
- 没有全面证明所有宿主都“无问题”。有成本及适配风险时**停止**比继续碰运气更有价值。

## 5. 后续优先级（**暂不自动执行**）

1. **保留这次合法停止状态**，不再把 429 的同一失败请求自动补问，不覆盖任何原稿，不动胶囊 SHADOW 身份。
2. 新一轮跨宿主尝试应使用第二个**真正独立运行的宿主应用**（而非只更换 API 模型），在其授权的功能、同一 SHA 习惯合同与独立数据资源下重新执行 conformance 测试。能跑并不等于改善文学。
3. 优先选择此前验证有改进迹象的认知缺口，保持控制组真实可比并覆盖合法重复/有限认知的负对照；多个独立真实读者审阅同稿、没有引用漂移时，才讨论“习惯值得继续变异/升格”。
4. 若独立反证多次表明无收益，转 `DORMANT_NO_PROVEN_VALUE`；无需强制把每次失败都补丁化、无需为了继续进化消耗资源。

**一句话**：可迁移的不是某个模型的记忆，而是带边界与证据的认知习惯；**正确地停止，也属于这种认知习惯的价值。**
