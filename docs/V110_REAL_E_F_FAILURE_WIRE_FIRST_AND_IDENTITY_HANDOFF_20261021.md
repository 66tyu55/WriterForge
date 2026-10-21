# WriterForge V110 · 真实E/F故障、供应商原始响应封存与未来分支身份隔离交接（2026-10-21）

> **状态**：V108 / V109 确实调用过原WF已注册的 DeepSeek Flash；V110是零模型调用的底层修复与离线反例。**没有产生可公平比较的完整E/F文学正文、没有模型文学质量胜者、没有正式技能晋级**。全部历史失败照旧保留，生产Railway安全idle。

## 1. 本次从 V107 后实际执行的试验

### V108 新实验，未重播 V106

- GitHub分支：`v108-new-locked-e-f-literary-trial`。一次性Railway部署 `0c08ae7e-7727-4811-a19f-44b1f7031ab9`，真实运行日志结尾 `WF106_REAL_E_F_CAUSAL_SMOKE_PRIVATE_R2_SAVED`（旧状态常量未随V108独立实验改名，不代表重跑V106）。
- **新的真实冻结预注册CAS** `6a5b713768bdf6e8d78f1600b17d0745f40999cdad54d514f6d784e866a22631`，共同WF自行生成的合法两段事件提纲CAS `718a76ff2816ced4cf2f5780d56718ea928888be14d6c2c1bc185b321bec168f`，真实总清单CAS `dc5b6095174acb350426192c44159783026cb647e0dce21bc528eba8111f2f6e`。
- 真实DeepSeek Flash **5次**、服务端已返回的usage输入3087+输出2040=5127 tokens。WF的共享提纲通过V96，E章节计划成功；E第一段正文得到471含标点字符，但第一段不存在已写前因，却提交了一句总结性 `trace.parent_effect_quote`，V96拒绝 `WF96_UNDECLARED_PREVIOUS_CAUSE`，**不能靠静默删字段将其变成通过**。E原始正文回答CAS `cbd9af5fdb29c193af093a51dba2972a06a3b08da0e20642ad4d3d5ff5ad8f9e`。
- F同样章计划通过，具有两条未来分支；首段DeepSeek答复无法完成JSON解析，报 `WF_FLASH_INVALID_JSON_RESPONSE`。V108的DeepSeek传输层在解析失败前还没持久化HTTP原始响应，故第5次的原始wire缺CAS。不得猜字段或伪造正文。
- 只读Railway冷恢复部署 `246de149-69e9-4fad-a094-47e3e9fa4234` 完整核实4份成功解析的原始模型JSON及共同两事件提纲；**0新模型调用，0 R2写**。以上5次旧请求不重播。V108没有得到两篇完整小说，因此公平文学结论为 `UNDETERMINED`。

### V109 硬修复与新的F单组小试

- [writerforge/deepseek_flash_model.py](../writerforge/deepseek_flash_model.py) 新增**可选**私有 `on_response_wire` 回调：收到供应商HTTP body后、在任何JSON解析/finish_reason校验**之前**原样捕获字节；默认不启用时不改变既有LEARN/WRITE模型调用方式。无效JSON、finish_reason=length、有效JSON、超时、R2 sink失败均有离线回归。
- [writerforge/v96_causal_turns.py](../writerforge/v96_causal_turns.py) 明确指导首段的 `parent_effect_quote` 必须 `null`，不能抄计划当已发生因果；**原V96严格校验没有放宽**。
- 新唯一F预注册 `104d497ebe71d6901dfc81d14d3747f9aee98455aed7576db1a6bfa1622b8bac`，仍使用V108原合法两事件，不额外生成“新作者答案”。[wf_railway_v109_real_f_wire_first_once.py](../wf_railway_v109_real_f_wire_first_once.py) 真正复用原 `AutonomousWriting.run(draft_mode=foresight_rolling)`，但在R2留下原始HTTP线报，max4次、无重试。
- 真实隔离Railway部署 `79e95f6a-6956-49f0-b757-43a792c75368` 实际**只调用1次**章计划：报告输入904、输出1004，合计1908tokens。供应商HTTP wire原始私有CAS `757d2d66e28767f61785b13c2ec2d5de56b9b0272c725b23e5c39cff9c19069d`；已解析且未更改的模型回答CAS `2cfe3842323e195a35f9b4decf0517d3cd98716dcaac7e8faa27e23f3efc9d9d`；最后一次真实运行manifest `cf8e367ee7676cabe158a5e5516fe345b583015fbbf423b44c82f855a06c557b`。
- 这次模型在前瞻 `horizon` 里给两个备选分支使用同一ID，宿主原 `validate_horizon` 报 **`WF105_BRANCH_ID_NOT_UNIQUE`**，未开始任何F正文。尽管模型回应有实际body、CAS与使用量均已封存，**还未通过零模型远端冷恢复读取出两条未来的具体动作是否实质不同**。没有证据证明两个分支只是撞名还是两个内容也重复，不可猜测或自称F已通过。
- 为做只读调查，新增 [wf_railway_v109a_readonly_horizon_inspect.py](../wf_railway_v109a_readonly_horizon_inspect.py)，能够回读原HTTP wire与原解码JSON，并在内存里尝试**仅改分支身份标签的诊断**，但绝不发起模型请求、写入R2或将尝试修补后的数据当作原始回复。尝试在Railway原只读隔离服务切换到V109最新提交时，连接器连续两次返回 **`User does not have access to the repo`**。GitHub仓库/提交本身存在；此处是Railway GitHub部署授权/连接限制。**V109A的实际远端冷读调查尚未运行，不能报告“动作内容确实不同”。**
- 为保证安全，隔离只读服务恢复为原来可运行的 `wf_railway_v108a_readonly_cold_exam.py`；一次性付费测试服务改回 `wf_railway_v82_safe_idle.py`、restartPolicyType=NEVER。**未触及原生产服务。**

## 2. V110：不让软件字段替WF决定故事

源码：[writerforge/v110_host_branch_identity.py](../writerforge/v110_host_branch_identity.py)。

软件的 `horizon.choices[*].id` 仅是路由标识，不是WF判断人物心理或两条命运是否不同的依据。V110没有放松旧 `validate_horizon`：
1. 如果它因 `WF105_BRANCH_ID_NOT_UNIQUE` 失败，**只**允许在收到完整两个/三个合法选择容器、所有原ID合法、行动事件步骤确实不同的前提下，复制一份**派生**视图；为每个位置生成内部路由ID。原始模型JSON始终保留，字节/SHA不改。
2. 如果两个分支的实质步骤逐字相同，则 `WF110_SAME_SUBSTANTIVE_FUTURE_NOT_ALTERNATIVES`，**拒绝伪造多条未来**；如果其他内容缺字段、非法步骤、同一资源被重复使用等，继续依赖V105旧规则拒绝，没有任何自动故事改写。
3. 只有派生视图会进入原 `validate_horizon`；后续仍必须满足资源、时间、人物知情与不可逆债务限制。转换回执独立保存 `v110_host_only_branch_identity.json`，元信息明确 `only_routing_identifiers_changed`、`literary_causal_quality_verified=false`。
4. 没有额外模型调用、没有改旧V104/V108/V109小说正文或CAS，未晋级FactJournal KNOWN和写作技能。即使字面动作不同也不能证明文学方向真正不同，需要独立读者验证。

实测：[tests/test_v110_host_branch_identity.py](../tests/test_v110_host_branch_identity.py) 使用真实WF原 `AutonomousWriting.run` 调用图的**模拟模型回答**，核查路由标签修复、原计划不变、两段正文接线、内部能源条件继续生效、复制同一未来禁止“伪两分支”、原模型答复在校验前保存、无自动重试。

全仓 [GitHub Actions #39561495831](https://github.com/66tyu55/WriterForge/actions/runs/39561495831) 为 **SUCCESS**，**1183项测试执行，4 skipped，0 failures**。**仅是软件级复验，并不代表F的真实文学改善已证实**。

## 3. 长期写作主线、下次恢复准则

- **首先解决Railway→GitHub最新提交的部署访问权限**，不得让用户重新提供私有DeepSeek密钥，不能为绕过授权污染生产服务；不能把尚未执行的V109A冷读核验写为成功。
- 采用已保存的V109原始HTTP wire + JSON，先确认重复分支ID下的真实事件内容是否不同。零模型调用；禁止对原模型作品本体“修正”。
- 下一次真正的F完整文学实验必须是**全新预注册**并使用host稳定身份，对正文篇幅、真实调用次数、成本、逻辑首错位置和自然度留痕；不能按无效元数据不断付费重抽。V106/V108/V109已消耗的全部请求永远不重跑。
- 继续保持V105前瞻因果的真正目标：角色每次选择会改变以后可用的资源、人物信任、未偿债务与可行路线；可安静、含蓄，不强迫牺牲或每幕反转。事实通过与故事好看是两种能力，必须分开验证。
- 持久层仍只通过原FactJournal/StoryCommit审核后的已证事实进入创作，V105/V110回执是候选，不是权威真相。超过48未解债务应经授权结算/归档，不允许静默删失。原15章学习链、V49第三次失败、文学第二窗口LOCKED全部保持。

## 4. 安全收口

原生产Railway `wf-python-r2` 仍为V99部署 `SUCCESS`，入口 `python -u wf_railway_v82_safe_idle.py`、restartPolicyType=NEVER。V110没有任何新的付费模型请求，原始V108五次和V109一次没有重播。最新V110源码在GitHub独立分支，**尚未部署为生产WF**。
