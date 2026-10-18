# WriterForge V62｜负面经验改变下一轮决策、受信撤销与V31/V38历史指针（2026-10-18）

> **仅 `v62-experience-negative-transfer` 隔离分支**，从V61 `v61-experience-decision-contract` 的 `d7d61608aa6694af3d9053b65dcc2d048ff4607b` 衍生。没有重跑小说训练、模型文学评估、付费推理或私人R2读取。V49 `THIRD_STRIKE_FAILED / NO_PROMOTION`、旧V56–V61原始运行、私有R2原著/作文全部未修改。主分支仍保持旧版。

## 1. 本次解决的确切缺口

V61已能将受控经验 `SELECT/SKIP/UNCERTAIN` 冻结并连到正式写作入口，但其 `report_postwrite` 只保存 `CLAIMED_APPLIED/NOT_APPLIED/UNCERTAIN`，**下一次决定不读取历史反馈**。也就是说WF明确表示“上次没做到”后，仍可能再次SELECT相同经验。

### V62：只将工程层可证明的失败变成后续选用约束

```text
已批准的实验性经验 E1
    -> WRITE冻结SELECT
    -> 原创稿/本次写后核查
       ├─ CLAIMED_APPLIED : 只确认引文存在，并非文学质量成功
       ├─ NOT_APPLIED     : 后续 E1 SKIP / PRIOR_NOT_APPLIED
       └─ UNCERTAIN       : 后续 E1 UNCERTAIN / PRIOR_APPLICATION_UNCERTAIN
                              |
                              v
                      旧版本永久保留
                              |
                       如有必要LEARN新建 E2
                        (必须改变操作/适用条件)
                              |
                       新独立审核签名后才可SELECT
```

如经受信签名撤销E1：新尝试必定 `SKIP/EXPERIENCE_REVOKED`，已冻结的历史决策仍可只读追溯，但旧SELECT不能再被验证为当前可执行。

**严格区分**：`NOT_APPLIED`与`UNCERTAIN`目前来自WF写后自陈，不等于独立文学裁判证实“方法有害”。系统采取保守停用，是避免重复未经复核的行为。它不自动获得更高写作水平，不修改模型权重，也不会用更多skill填充提示词。

## 2. 先读了哪类GitHub现成源码，取长补短

- [OpenFeature Python SDK `flag_evaluation.py`](https://github.com/open-feature/python-sdk/blob/main/openfeature/flag_evaluation.py)，读取时blob SHA `df47e7327a208cb72b9717a9e49cbf4cdb8969e3`，`Reason`明示`DISABLED/STALE/ERROR/UNKNOWN`等结果原因。WF借鉴「**结果 + 稳定原因码**」而不是用单一bool“有用/无用”决定；不安装OpenFeature，不复制实现。
- [eventsourcing SQLite](https://github.com/pyeventsourcing/eventsourcing/blob/9.5/eventsourcing/sqlite.py)，blob SHA `2cf6afe96045ad3dc2c432907b3a09cb53b2401d`，借鉴不可变记录与SQLite事务回滚；WF沿用已有 `WriterForgeDB` 而不引入整套事件平台。
- V60已核对[LangGraph checkpoint](https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint/langgraph/checkpoint/base/__init__.py) blob `c7cacc7bfd703f298427e870bd6d07b4aa395812`；WF沿用写前冻结和重启恢复机制，不建立第二个WorkTree。

## 3. 生产实现：真实落盘、无原著复制

### `writerforge/experience_decision.py`

- `_feedback_state(project_id,experience_id)`：从原V61 `experience_postwrites` **读取真正存储的历史回执**，逐项验证SHA及历史写前SELECT引用；最多128项，超过明确拒绝而不是悄悄丢老失败。
- `decide`：在已批准经验上读取反馈，并将负面记录/不确定记录优先于原正常条件；可用提示词仅来自正常SELECT的有界系统模板。
- `validate_live_decision`：历史结果可读；如果原SELECT被旧失败或撤销阻断，新生成/再提交不能重新借它授权。
- `stage_candidate(...,supersedes_experience_id=...)`：旧负面经验只允许以**新experience_id**、改动条件或操作、重新走签名审核作为实验新版本。旧经验和失败收据不可编辑。未关联旧失败时不得任意自称为“修复版本”。
- `revocation_payload` + `revoke_candidate`：已有审批签名对应的撤销，必须重新提交受信外部HMAC签名，绑定原批准SHA、审核身份、理由，且永久保留撤销墓碑。
- `register_legacy_reference` + `read_legacy_reference`：只存历史试验`SHA`元数据，**与经验候选/审批表分离**，状态永远标记`UNVERIFIED_REMOTE_POINTER`；不连R2、不复制原文、不可直接批准成文学能力。

### `writerforge/db.py`

增加 `experience_revocations`、`experience_legacy_refs` 两个小表，以及反馈检索索引；V61原有候选/审批/写前快照/写后证据四表原封保留。不增数据库实例，不建立全本原著副本。冻结旧数据库原本的V61经验hash不受更改，因为仅对新修订版本加字段。

### `writerforge/cli.py`

新命令 `experience-revoke`、`experience-legacy-import`、`experience-legacy-read`；原`experience-stage --file`允许**可选**`supersedes_experience_id`用于受控修订。CLI真实回归验证导入SHA、后续SKIP和签名撤销。签名秘钥仍须进程外 `WRITERFORGE_EXPERIENCE_REVIEW_VERIFY_KEY_HEX`，不可写入仓库。

### 公开仅包含旧证据哈希的指针文件

- `references/experience/v38_l2_r39_role_conflict.json`：旧WF声称R39是铺垫，真实独立Pro把R39列为回收候选；冻结V38自审SHA `a9d5d521b2e0adbeb416f9325b0adabaad408abb728bd978099effe328488a62` 与R2后续交叉验证报告SHA `e2ed24abc352daef678165de8bee5f7c283f5709cf3a23c9fe99b9a876aeb0db`。只作历史争议指针，没有新的文学判断或“自动认错”。
- `references/experience/v31_self_review_stage1.json`：指向原V31第一轮真实实验记忆 SHA `cd9cfa1d6413ed84bb4d3bb18c9a77d873666df95cbcd5898d4745cfeb2e3c7c`，并明确其本身没有独立审稿验证。
- 上述两个文件不是下载的R2原件。V62 CI在临时SQLite中用真实CLI登记并读回两个公开SHA指针，**不向WRITE授予任何新权限**。R2未经独立`GET+SHA`核对之前，不能宣称真实原始记录已在本轮验证。

## 4. 失败先留证，再独立修复

### 初次红色夹具本身的问题（不能当成11个已确认缺陷）

[V62 Actions #39111000402](https://github.com/66tyu55/WriterForge/actions/runs/39111000402)：V62新测试 `0/11`，但是通用测试helper向旧V61接口无条件传了新可选修订参数，导致所有测试提前ERROR；归档机器回执JSON SHA `6fea83b1e0e349d605a22f87abcb526b7c651206e236d8a7713f883676f69ccd`，artifact ID `12130228151`。这个失败**不证明11处漏洞**，不得隐藏或改造成成功结论。

### 修正夹具后的真正有效失败对照

[V62 Actions #39111052510](https://github.com/66tyu55/WriterForge/actions/runs/39111052510)：旧V61 真实运行，新增11项中 **2通过、5项已执行行为断言失败、4项缺少新API而ERROR**。已经复现：报告NOT_APPLIED后仍SELECT、报告UNCERTAIN后仍SELECT、重启后失败未生效、旧SELECT仍可继续使用，以及被篡改的负反馈未被决策器检测。原始红色JSON SHA `a8f321e57572734d3fcae80089d1d4685311a99e53c40ad31ee9ba5b3bce222f`；artifact ID `12129919904`，ZIP SHA `e66ba6e8cb58c1a1aa21fa789430542b657a14bebc9ca36a9ba2dd9fb02c6268`。两轮红色记录永久保留。

### 已通过的绿色工程回归

[V62 首批绿灯 #39111278888](https://github.com/66tyu55/WriterForge/actions/runs/39111278888)：新增11/11、全仓库667/667（原V61及更早均保留），机器JSON SHA `6f81179b84bcb19c763dc61d8b7e08ee512207c63ba3d6c22f20a2ebf980819c`，artifact ID `12130726877`。

[V62 最终绿灯 #39111498188](https://github.com/66tyu55/WriterForge/actions/runs/39111498188)：新增14/14，完整旧+新 **670/670** 通过（临时SQLite、真实CLI、无模型/R2）。机器JSON SHA `667bad7454472c151fd3403c262d433dd65736505349762bc210bc1db69455ca`，artifact ID `12130229092`、ZIP SHA `c2cdbc6efb4f50b8170d0273ad4d86e6a5174659792e4d2feece36072afe4d71`。最终代码/测试SHA：
- `writerforge/experience_decision.py`: `e59c0800226fc23864e277f9bb4334e4f4c76a5842e566a42110de67f32fad42`
- `writerforge/db.py`: `722af2c561de7583a0a476a6910d79ede45a26735aaa78c5a23263a5adbae1f3`
- `writerforge/cli.py`: `f8effc4f56c927bafed8ccc1825690ab2ea3f897fc78df050c7df51a576f6acd`
- `tests/test_v62_experience_negative_transfer.py`: `d8f2accc7421eb03c4653392fda8584f15a3c7be87b64644cd235db108729e68`
- `scripts/audit_v62_experience.py`: `784b2896689c89fd8ff3356b96bd38df8db750f8d3c4a7a0ecbbd163827b471a`

## 5. 不能把本轮宣称成真正的文学自主学习

1. 这轮验证的是**工程上后写失败影响下一次策略选择**，不是WF已经会独立理解原文、发现艺术性缺点或提高实际写作质量。最初的场景事实仍由调用方给出（V61剩余问题）。
2. 自述NOT_APPLIED会保守停用，不等于独立评论判定该文学经验不成立；可在新的`experience_id`版本和独立授权下复测，但**绝不删除先前反例**。
3. V31/V38的历史指针由公开报告中的SHA组合，没有在本轮GET真实私有R2文档。经第三方密钥签名的撤销只能说明持密钥者授权，不证明真人文学判断正确。
4. V61正式`EvolutionEngine.apply_upgrade`仍要求手动签名+明确人工批准；**但低层`SkillRegistry.promote`可能被可信内部调用者直接使用，尚未强制外部签名授权**，不要宣称整个WF晋级系统全封死。
5. 目前不做自我推理的“隐形Chain of Thought”提取；只保存显式操作、范围、状态、来源及可复盘证据。没有复制受版权保护原文句子或全文到公开仓库。
6. 内存/容量：每次单条经验最多检查128条写后回执，超限报错而非无限吃内存；每次最多8候选、最多2 SELECT。超大量历史的汇总/归档及多连接SQLite事务竞争尚未做V62独立压测，须下一轮优先测。
7. V49 `THIRD_STRIKE_FAILED`、正式文学第一窗口 `NOT_PASSED`、第二 `LOCKED` 持续有效；V57–V62草稿分支仍不能直接发为main正式版。

## 6. 下一步专注的一个点

先检查 `SkillRegistry.promote`的直接写权限和所有调用方，做失败先行的对抗测试；同时完善经验`SELECT`与`NOT_APPLIED`发生在两个SQLite写连接间的事务竞争，避免撤销刚发生时仍能生成新稿。之后从真实R2安全只读获取V38 L2源文/独立评审，才有条件让经验候选进入更深入语义判断。依旧不用重训旧章节，不让主模型替WF写作。
