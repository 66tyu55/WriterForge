# WriterForge 0.BD｜第一个认知习惯假设的真实来源、SHADOW 留存与离开宿主复原（2026-10-27）

**这份报告是源码与 CI 的真实验收，不是文学改善的证明。** 只操作 `refactor-unified-scene-delivery-audit`，不修改 main、不部署 Railway、不接触用户 R2 原著或正式 Canon、不重试 GLM 429。V26/V98/V119 与唯一 NarrativeCore 不变。

## 0. 先区分三个主体，避免宣传“假寄生”

1. **原始任务提供宿主：DeepSeek**。来源是 0.AY 原付费运行 [Actions #40354436598](https://github.com/66tyu55/WriterForge/actions/runs/40354436598) 中同题两份真实 control/habit 回包，各有完整 provider wire SHA。GLM 的旧 control 另有真稿，而 GLM habit 第四次只有 HTTP 429、没有有效正文。
2. **本次提出元认知假设的宿主：ChatGPT GPT-6（当前用户授权对话）**。模型在读取两份真实续写后，提出一个步骤更具体的候选。但是本次对话**没有独立可验证的 ChatGPT API 原始响应 wire**；把这个提议写成源文件是可追溯的会话贡献，并不是外部提供商签名的自动学习事件。
3. **WF 核心**仍不写正文、不替作家选下一段、不伪造读者评价。仅对已保存 DeepSeek 原作按原始 SHA 反复核实，然后在隔离的 Evolution candidate pool 中生成一个新**SHADOW** capsule，保留其祖先、证据与来源类型。旧 0.AY 的 DORMANT_HOST_RESOURCE 不复活。

## 1. 新吸收的认知假设到底是什么？

**`observe-before-next-choice` v2 的新增候选**：当场景涉及传达、交接、承诺或工具调用时，先从已写来源分别核实三个层级：①行动是否尝试；②接收方是否被证据证明已确认；③预期后果是否真的发生。收到回执或工具响应不自动等于目的实现。人物后续可以核验、等待、改用其他渠道、再次尝试，WF 不把有意重复自动判错，也不代替作者做文学选择。

为什么提出：原 DeepSeek control 保存异常号码准备核实；habit 重发警报并说明身份；**两条行动在已知事实上都可能有效**，两份回复都没有证实最终接收或船只获得警报。旧 v1 已区分已发生与未知；新 v2 **可能只是更详细的表述而没有增益**。这是需要新场景证伪的假设，不能把行为差异当文学胜利。

固定候选 SHA256：`0d43a023bc278ac12e3165e319d2acb73dcf40c0d9af453e623c786f3b476a10`  
原 v1 SHA256：`42cad98118dea662cea472f708ef1de22f4bb139da3210b1f5c3c1f9ac12664d`  
便携清单 SHA256：`6bb2c9507edbe8be95e79bb098dca210f87da085e04c7bb2a2650a683b01956f`

## 2. 已实施与真实运行的文件

- **当前模型提议原件**：[`experiments/wf_0bd_chatgpt_first_host_cognitive_proposal_20261027.json`](../experiments/wf_0bd_chatgpt_first_host_cognitive_proposal_20261027.json)，注明 ChatGPT 对话生成、meta provider wire 未独立验证、没有读者审稿、未获 ACTIVE 权限。
- **真正原稿核对与 SHADOW 形成代码**：[`experiments/wf_0bd_chatgpt_first_host_source_reanalysis_20261027.py`](../experiments/wf_0bd_chatgpt_first_host_source_reanalysis_20261027.py)。每次使用旧 artifact，逐字 SHA 核对当年 DeepSeek 控制/习惯组、已写两段原文与冻结任务；不能生成 GLM 缺失正文。把 DeepSeek 源证据写入原 WriterForgeDB 的 SHA-only 观察表，再由已有 PortableHabitCandidatePool 形成来自 **chatgpt-interactive**、而非声称来自 DeepSeek 的新元认知 SHADOW。没有 `acquire_once` 回放伪装成新 provider 请求：`new_paid_provider_calls=0` 且 `replayed_host_model_callbacks=0`。
- **独立永久文件（非 90 天 CI 工件）**：[`experiments/wf_0bd_portable_habit_snapshots/0d43.../capsule.json`](../experiments/wf_0bd_portable_habit_snapshots/0d43a023bc278ac12e3165e319d2acb73dcf40c0d9af453e623c786f3b476a10/capsule.json) 和同目录 `portable_manifest.json`、`README.md`，均在开发分支永久保留。程序验证这两者与当次 CI 真正产生的字节和 SHA 一致，不依赖模型重新生成。
- **离线测试**：[`tests/test_wf_0bd_first_live_chat_meta_proposal.py`](../tests/test_wf_0bd_first_live_chat_meta_proposal.py) 8 项源锁对抗：伪造 wire、伪造 GLM 429 完成、ChatGPT 冒充已签名、旧正文复制、错来源配对、旧文件覆盖都必须失败。[ `tests/test_wf_0bd_candidate_archive_persistence.py` ](../tests/test_wf_0bd_candidate_archive_persistence.py) 4 项真正离宿主恢复：**在 Actions 下载原 DeepSeek 工件之前**，仅靠源码仓库的 v1/capsule/manifest 恢复同一 SHA 与 SHADOW，错签或缺外部 SHA 不能恢复。

## 3. 真实工程 GREEN

| 证据 | 结果 |
|---|---|
| [#40457219260](https://github.com/66tyu55/WriterForge/actions/runs/40457219260) | 已核验 DeepSeek 同题两份真 wire；当前 ChatGPT 建议转成 SHA `0d43a023...`、未审核 SHADOW，**1,952 tests、6 skipped、0 errors** |
| [#40457864844](https://github.com/66tyu55/WriterForge/actions/runs/40457864844) | 首先不带旧 provider artifact 完成四项恢复测试；然后下载原作核对并跑 8 项源锁对抗；最后**1,956 tests、6 skipped、0 errors** |
| 原 0.AZ [#40454231888](https://github.com/66tyu55/WriterForge/actions/runs/40454231888) | 真实 4 次请求、3 份有效回包、GLM habit 429，没有新付费请求，旧源及原 SHADOW 没有修改 |

0.BD 没有新模型 API 调用，没有真实 independent heldout，没有实验评分，没有真实的第二个独立 Agent 文学收益。这个候选的“生存”成功是**存储与重新导入**，不是文学质量得到证明。

## 4. 接下来的真正证伪，不加审稿规则凑成绩

候选现在**必须停在 SHADOW**，原因是旧 v1 可能本来就能正确区分行动和结果。只有一个领域中两条合法续写不足以证明新三层方案有价值。下一轮需要新任务、同模型、同成本**旧 v1 vs v2** 的成对实验，不能继续重复旧无线电文学原稿。在独立留出集上至少包括：

- 对方已经明确确认且真正完成的行动——v2 不得制造多余的不确定性或逼作者反复核验。
- 合法、目的明确的重复尝试——不能因为重复就自动判失败；对真正重复无变化的行动也不能奖励空转。
- 安静文学片段、刻意省略、人物有限认知——不强制硬核工程式状态账本毁掉文学节奏。
- 非无线电任务（物件交接、承诺兑现或工具调用）——检验习惯跨情境的可迁移性，而不是背诵旧例。

预先固定文本、轮次、token/call上限、独立盲评与失败规则。只有 source-verified、同预算并得到独立质量/成本证据才考虑**人工批准**；无增益、负迁移或成本过高便 DORMANT。**新付费模型实验仍须用户提供明确模型/次数/金额预算，不偷偷使用 GH Secrets。**

## 5. 仍然缺失

没有证据说明 WF 已凭自身单独“发明”了一项被验证有效的习惯；此次元提案来自在本会话中真实推理的 ChatGPT、而非 DeepSeek 自主元反思回包。没有 raw ChatGPT provider wire，不能称为外部可密码学验证的第一次元认知学习；没有独立评审，也不能把 CI GREEN 变成文学分数。首宿主资源失效可休眠、候选可保存、下一个可信宿主可重新加载检查——这只是开始。

下个窗口必须先读取本文件和最新 `docs/CURRENT_HANDOFF.md`，不允许再次绕回只增加权限、审稿器或空文档来冒充成长。
