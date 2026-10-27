# WriterForge 0.BF｜可信 v1/v2 价值证据闸门：原始模型回包 + 独立盲评 + 停止无益进化

日期：2026-10-27。唯一修改分支 `refactor-unified-scene-delivery-audit`；不部署 Railway，不修改 main、R2 用户原著、正式 Canon 或原始 0.AY/0.AZ 付费源。继承 0.BE 预登记 8 个全新场景，不启动外部模型。

## 0. 本轮新发现的危险断口

`writerforge/evolution.py` 原 `HabitTrialEvidence` 有 `independent_literary_review`、`repeated_no_benefit_evidence`、`confirmed_literary_benefit` 等布尔输入。`assess_habit_trial_continuation` 只是纯粹 **advisory**，不能修改正式 Registry，但该入口**自己不验证这些布尔值来自什么原始模型回包、多少费用、哪个真正独立审阅人**。如果有人把 True 当成已经获取的实证，会形成虚假的“可证伪完成”。当前没有能力据这两个布尔字段直接修改技能。

不能再添加一句“请谨慎评价”作为修复；需要真正从来源证据计算结论。P0/P1/P2 和唯一 NarrativeCore 仍保持。0.BE 已封存 v1 / v2 的 v2 SHADOW SHA 为 `0d43a023bc278ac12e3165e319d2acb73dcf40c0d9af453e623c786f3b476a10`，父 v1 SHA 为 `42cad98118dea662cea472f708ef1de22f4bb139da3210b1f5c3c1f9ac12664d`，此次两者都没有升级。

## 1. 实际实现

在原 `writerforge/evolution.py` 内新增 `HostValueWireAttestation`、`IndependentBlindValueVote` 与 `adjudicate_portable_habit_value`，而不是改写已发表小说正文或添加自动文学审稿器。

- **来源**：只接受独立固定 SHA 的 0.BE 预登记试验，必须严格匹配 8 个 source/task、16 个 v1/v2 输入、同一真正 host/model/trial、每条输入完整字节和原始 HTTP completion **wire bytes**（在调用中瞬时核对）。数据总数有上限，不能重复同一 case/arm 或借旧 0.AY GLM 429 编造第 4 份答案。
- **签名**：宿主 Ed25519 公钥必须从可信调用方注入，不能从自称的元 Skill 中随意拿公钥。宿主签名绑定 case/arm、源 SHA、任务 SHA、真正交付给作者模型的语义输入 SHA、响应 wire SHA、文字 SHA、作者模型名称、宿主名称和真正 provider wire 报告的 prompt/completion/total tokens。完整 response 与 `usage` 缺失、错模型、非 stop、文字对不上、签名错误全部 fail-closed。这里的签名是**可信宿主签名，不是模型供应商自己的签名**。
- **两名独立评阅者**：需要外部预配的**两把不同可信 Ed25519 公钥**；与宿主不能共用公钥，不能用 Skill 提议者身份签。每例两名评阅者的公钥签名固定 A/B 两份实际模型正文的 SHA，只能给 A、B、TIE 或 BOTH_BAD。程序固定混排用于防简单位置偏差，但不能证明人类评阅者没通过其他渠道获知模型版本，**身份独立与真正阅读盲法仍需人工管理**。
- **价值决议**：缺真实 16 份模型回包：`DORMANT_INCOMPLETE_REAL_PAIRS`；缺两名签名评阅：`SHADOW_NEEDS_INDEPENDENT_READERS`；相互矛盾：`SHADOW_MIXED_READER_EVIDENCE`，绝不可硬判。若 8 例全部真实成对、每例两位一致、v2 没有一个赢且原 wire 报告的总 token 成本不低于 v1，才得出 advisory `DORMANT_NO_PROVEN_VALUE`；v2 有较多获认可的胜局，也仅 `SHADOW_REVIEW_FOR_VALUE_ONLY`，**不自动晋级**。
- **合成和真实完全分开**：测试中 16 条未来文学正文/使用量/两名评阅者都明确 `SYNTHETIC_TEST_ONLY`，即使引擎在合成 TIE 和成本劣势场景输出 DORMANT，也同时输出 `evidence_kind=SYNTHETIC_TEST_ONLY`、`production_actionable=false`、`literary_improvement_proven=false`。这不是“v2 真实被证伪”，也不是 provider 模型回包。当前本轮真实新付费调用 **0**。

此函数只返回基于输入证据的不可执行决策，不会写 SQLite、触发 Scheduler 或对生产版本退休、晋级、自动再训练。以后如需把某个已经**独立授权且非合成**的停止决议跨宿主持久化，应由签名策展人核实该决定并写入现有 Evolution 的审计轨迹；本轮不能凭已知合成示例向生产写一条假停止记录。

## 2. 真实 RED→GREEN

- [**RED #40488817209**](https://github.com/66tyu55/WriterForge/actions/runs/40488817209)：`HostValueWireAttestation` 与独立双审阅者证据入口完全缺失，测试明确 ImportError。
- [**0.BF 工程 GREEN #40489266740**](https://github.com/66tyu55/WriterForge/actions/runs/40489266740)：12 项合成源/签名/成本/读者对抗全部通过；**1,983 tests、6 skipped、0 failed**。完整回归包括此前 0.BE、0.BD、V26/V98/V119、单 NarrativeCore。
- [0.BA 交叉 GREEN #40489266803](https://github.com/66tyu55/WriterForge/actions/runs/40489266803)、[0.BE 交叉 GREEN #40489266755](https://github.com/66tyu55/WriterForge/actions/runs/40489266755)、[0.BD 交叉 GREEN #40489266715](https://github.com/66tyu55/WriterForge/actions/runs/40489266715)：相同代码 HEAD 跨不同 CI 覆盖。
- 0.AZ 交叉 CI 最初失败 [#40489266720](https://github.com/66tyu55/WriterForge/actions/runs/40489266720) 的唯一原因是原工作流把整仓测试放在下载 0.AY 原始 archive **之前**，导致 0.BD 的 8 项“缺少原始证据”失败；这不是文学失败。已更新 `.github/workflows/wf-0az-meta-habit-resource-stop-forensics.yml` 的顺序：**先按 40354436598 固定历史 Actions artifact 下载真正 DeepSeek/GLM 原件，再跑整仓回归与原 429 来源检查**。禁止生成假 wire 或跳过测试。 随后的 [**0.AZ 原件重放 GREEN #40489793627**](https://github.com/66tyu55/WriterForge/actions/runs/40489793627) 实际通过 **1,983 tests、6 skipped、0 failed**，来源仍为 4 次历史尝试、3 份真实回复、第 4 次 GLM HTTP 429 无模型正文、0 次新付费请求。

## 3. 真正已获得的能力与仍然没有的能力

WF 现在能**对外部独立署名的已完成 v1/v2 实际 A/B 工作**进行可核验来源、成本与双评阅合并，并得到不会自动操作正式状态的“停止或审阅”建议。**这是证据处理能力；仍没有产生新的真实 v2 对照正文。** v2 SHADOW、0.AY GLM HTTP 429 休眠、0.AZ 4 次历史尝试/3 份有效回包冻结不变。本阶段全部签名密钥和模型回包都属于 CI 合成；不能把签名本身当作真实质量或人格独立性的证明。零付费新模型调用。

下步真正“值得继续才进化”的价值检验，依然需要用户新的明确模型/次数/费用预算，以及两位不受模型结果作者控制的读者。先完成同宿主、同题、同资源预算的 v1-v2 **真实输出与原始使用量归档**；再把签名的负面/正面证据交给这条纯分析入口。若无价值，保留证据并停止；即使显示有增益，也不能自己提升级别或把结论写成 Canon。不要返回增加静态审稿规则、补造旧 GLM 缺失回包或把软件测试 GREEN 当成文学进步的旧方向。
