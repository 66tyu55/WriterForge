# WriterForge V61｜经验候选→授权实验→写前冻结→写后证据（2026-10-18）

> **开发隔离分支**：`v61-experience-decision-contract`，基于只读审计 `v60-architecture-audit-readonly`；尚未合并稳定主分支。V49 `THIRD_STRIKE_FAILED`、`NO_PROMOTION` 和 V56—V60 的原始审计、R2、小说正文全部保持原样。此轮没有模型生成、文学重训、R2读写或文学能力晋级。

## 1. 为什么实施，而不是继续加新的 Skill

V60在真实正式入口查到：`VerifiedWritingFlow.prepare()` 更换学海检索证据后，输出 `evidence` 变化、`prompt_sha256` 可以不变；V31实验规则、V38写后检验不构成正式入口的统一强制策略。通用 `EvolutionEngine.apply_upgrade(gated_auto)` 可凭调用者自报的高分在内存接口中升级技能。

本轮只修最小断点：
1. LEARN创建一个带**真实本地来源定位+精确SHA**的`HYPOTHESIS_ONLY`候选；
2. 受控的外部签名`CONTROLLED_WRITE_EXPERIMENT`准入，严格不等于文学真值认证；
3. WRITE依据明确给出的场景事实（True/False/Unknown）作`SELECT`、`SKIP`、`UNCERTAIN`，将选用操作记录到SQLite并在模型生成前冻结；
4. 只有被选中的**系统预设抽象动作模板**加入写作提示，不发送原著句子、模型自评或R2全文；
5. 写后提交真实稿件中的精确引文锚点，存SHA和声明状态，不宣称文学机制有效；
6. 禁止凭模型自评分升级正式 Skill，须外部签名评分收据+显式人工批准。

不是从头重写 WorkTree、Lane、StoryCommit、Xuehai、FactJournal 或R2。

## 2. GitHub现成源码对照，借鉴而不复制

- [LangGraph checkpoint](https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint/langgraph/checkpoint/base/__init__.py)（前轮核对的blob `c7cacc7bfd703f298427e870bd6d07b4aa395812`）：**借**冻结状态和回放时不偷换上下文；**不引入**其通用图调度或覆盖WF现有WorkTree。
- [MLflow Run](https://github.com/mlflow/mlflow/blob/master/mlflow/entities/run.py)（blob `3e44a6a97b31bcbec0b6242fdffbe7c0d9d71835`）：**借**运行输入/决策版本/输出分开留证；**不引入**整套实验跟踪栈。
- [OpenAI Evals Recorder](https://github.com/openai/evals/blob/main/evals/record.py)（blob `8e8ebe9ae62b4711817e08e668d4ac9a4b63cc23`）：**借**样本、事件、最终判断的记录隔离；**不把**机器测到的引文存在冒充文学质量分。

以上均为先前 V60 已实际读取的原始代码，不是在本轮复制第三方实现。V61只增加Python+SQLite的本地模块，且不安装新增框架。

## 3. 实际改动的代码与执行链

### A. `writerforge/experience_decision.py`

`ExperienceDecisionBridge` 内含：

- `stage_candidate(...source_ref,snapshot_id,required_tags,forbidden_tags,operation_code)`：只允许已经存于 `source_spans` 且对应有效已发布章节快照的`work_id/chapter/paragraph/sentence/source_sha256`；候选行永久含 `source_semantics_verified=False`，不存原文正文；原有来源行可复查。
- `approval_payload`、`approve_candidate`：通过进程外配置的可信HMAC验证密钥确认签名覆盖的候选哈希、审核ID和权限 `CONTROLLED_WRITE_EXPERIMENT`；禁止仅靠候选文本自称已审。签名的作用是**凭证持有者授权**，仍不能证明对方是真人文学专家或判断正确。
- `decide`：先要求 WRITE 模式+已发布快照，写入不可变的`project_id/attempt_id/request_sha/plan_sha`。确认需要标签为True、禁用标签为False才 SELECT；明确违反为 SKIP；缺失/未知则 UNCERTAIN；最多8个批准候选、最多2个本轮SELECT。
- `read_decision`：只回放已冻结快照，支持重启后按SHA核对；相同attempt换场景事实/目标会拒绝。
- `validate_live_decision`：历史可读不表示再执行许可；同一attempt再次生成前，重新核实来源SHA、已签审核、快照未改。
- `report_postwrite`：仅选中过的经验可声称使用，`CLAIMED_APPLIED`必须引用实稿中的唯一精确短引文；保存引文SHA、正文SHA和状态，仍写明`literary_effect_verified=False`。失败与修改不能覆盖已写的同一记录。

最小抽象动作只包括`CHECK_KNOWLEDGE`、`TRACE_CONSEQUENCE`、`DEFER_REVELATION`、`TRACK_PROMISE`、`VERIFY_FALSE_BELIEF`。它们是受限执行原语，不是模型训练出来的文学技巧，不允许来自未经审查的来源段落直接成为文本提示词。

### B. `writerforge/db.py`：不另建数据库

沿用现有`WriterForgeDB`，新增4张小型SQLite表：

- `experience_candidates`（带来源哈希的不可变候选）
- `experience_approvals`（授权审核者ID及签名）
- `experience_decisions`（生成前冻结的单次选择与跳过决策）
- `experience_postwrites`（写后实际稿件引用及状态）

新表不存小说原文或完整草稿。未触碰 R2、不迁移私人原稿。

### C. `writerforge/verified_flow.py`：正式写作入口真正参与

`VerifiedWritingFlow.prepare(...,experience_attempt_id,scene_signals,experience_enabled)`：

- 已有**批准候选**时不允许悄悄跳过冻结决定；缺少attempt或场景信号则拒绝。
- 正式生成前持久化`CreativeDecision`快照；仅SELECT的受限动作改变 prompt，SKIP/UNCERTAIN不会偷偷引导模型。
- `GroundedDraftPacket.manifest`新增写前收据的ID/SHA/已选动作ID，不复制原著内容。
- `accept_candidate`比对对应SQLite冻结计划、场景/快照/所选动作、审查密钥、来源新鲜度；篡改或删除原manifest中的计划引用时拒绝提交。
- 未配置/未批准实验经验的旧写作路径仍可照原样使用。

### D. `writerforge/cli.py`：实际可用而非仅单元函数

新命令：`experience-stage`、`experience-approve`、`experience-decide`、`experience-read`、`experience-postwrite`。

正式`draft-context`和`draft`增加`--experience-attempt-id`、`--experience-signals-file`、`--experience-disabled`。签名验证密钥从**运行环境**读取 `WRITERFORGE_EXPERIENCE_REVIEW_VERIFY_KEY_HEX`，不需将密钥写入GitHub代码或日志。审核签名必须由可信外部执行方形成；WF自身不能算独立审查者。

`draft-context`能够无模型地预览正式生成会使用的 prompt+决策收据；CLI端到端合成测试覆盖上述新命令。

### E. `writerforge/evolution.py`：修复通用晋级入口

原来`EvolutionEngine.apply_upgrade`接收调用者提交的`PromotionEvidence`数值，`requires_human_anchor`也由候选自己指定。V61保留独立数值门限供诊断，但**活跃正式晋级**需要：

- `WRITERFORGE_PROMOTION_VERIFY_KEY_HEX` 或隔离注入的受信验证密钥；
- 签名绑定技能ID、升级级别、能力声明、全部原始评分、审核员ID、审核收据ID和独立证据引用；
- `policy="manual"` 和调用方明确`approved=True`；
- `gated_auto` 即便附带签名也不得自动晋级；
- shadow-only提案绝不改变正式等级。

这封住了此前由`EvolutionEngine.apply_upgrade`暴露的数值自报自动晋级入口；但内部`SkillRegistry.promote`依旧是能修改注册表的低层可信写接口，下一轮必须审查/约束它的调用权限。这是一项**明确剩余缺口**，不能说整个晋级体系已经不可绕过。

## 4. 独立失败证据→修复→真实GitHub CI

### 原始红项冻结

[V61 初次红色 #39108670931](https://github.com/66tyu55/WriterForge/actions/runs/39108670931)：11个新契约用例全部尚无相应API实现而ERROR，**不是11个真实已确认漏洞**。原始JSON SHA256 `6d582e23a8ef75d89318400d6257a12118900df9f3e39bb30140db155f21f7c0`，artifact ID `12129850565`，ZIP SHA256 `fadcf450716e7d4d7b6b0b7cec4ae6370f4d33c80090324dc6d39b35f7b3d96f`，保持不覆盖。

执行中其他红色CI同样不删除：新CLI parser缩进曾导致测试加载错误，已定位修复，不靠关闭旧测试变绿；新增旧manifest篡改/过期来源及CLI端到端测试后再执行最终全套。

### 最终源码与真实通过证据

[V61 Actions #39109713890](https://github.com/66tyu55/WriterForge/actions/runs/39109713890) `completed/success`：
- V61新增 **14/14** 合成契约测试通过；
- 全仓库旧+新 **656/656** 自动化测试通过；
- V12、V60旧正向测试在**本分支**按新的强制签名权限作了透明输入迁移；原V12/V60旧分支及旧报告不变。
- `v61_relation_regression_receipt.json` SHA256 `136c2fd9370e73daa86dd76cf3403ae6dcb0ee55d46e09fa298aa815647df6aa`；
- [机器证据artifact #12129783367](https://github.com/66tyu55/WriterForge/actions/runs/39109713890/artifacts/12129783367) ZIP SHA256 `c3c469851f2ee7aa7cf353168b0fba4a1c61f0cb03b50a0d090d5e99a2c35de3`；
- `experience_decision.py` SHA256 `493561b7895270a73efd1af9d5a9f6bb24efcaf3373a690cc0d41ccfb5085bd9`；
- `verified_flow.py` SHA256 `dfe2f1726b21d495cd215cae8912269799890b9e196e633a9e7c314fd5cb3d6b`；
- `evolution.py` SHA256 `6d0f9a05f13b97b1a02f0b128cf4a7283132245a94ffc640fb3e6acb24b99b61`；
- `db.py` SHA256 `568faf10c97968f5143c48bf8d61be75ed3e4e2f6ef6f01efd62a191283b6f43`；
- 最终完整工作流回执中的其他文件/代码 SHA 保留于 GitHub Actions 日志。

**这些是结构性/权限/状态测试，并不是文学质量A/B，也没有真正调用AI写作模型。**

## 5. 尚未完成：下一轮 P0 和 P1 不得夸大

1. 真正的WF“独立理解文学”仍未证明。经验候选的结构化来源定位与自主判断的正确性不同，第三方签名仅验证许可的来源控制者，不是经真人验证的手法效果。
2. 本次`operation_code`属于少量**固定抽象执行原语**，只是验证经验选择/跳过能不能真正改变写前行为。尚未把V31自学规则和V38 L2 争议自动转成合格的候选；尤其V49 `THIRD_STRIKE_FAILED` 不得清除。
3. 当前`scene_signals`是真值由调用方明确提供的结构化证据位，而非WF自动从实际小说中认知人物知识、伏笔因果；不得把这样的合成决策当作阅读文学成功。
4. 读者反馈的两个任意ID可形成假收敛信号问题（V60-P1-006）未在V61改变；独立评论者身份未接入真实验证。
5. `SkillRegistry.promote`低层直接写入口及正式写作Studio中的无计划预览需要审查所有调用者和权限；V61封住的是通用`EvolutionEngine.apply_upgrade`的自报高分晋级渠道，**不能称“全WF晋级彻底防伪”**。
6. 还没有受信的经验撤销/过期状态、正式外部审核机构、跨账本原子提交或大规模存储压测。V61冻结的`attempt_id`不允许被改写，未来要求另建修订版本。
7. 在实际生产部署中，必须先冻结V57–V60合并/迁移策略，不能将V61草稿直接并入`main`，也不应让未经审核的经验控制已在产线运行的文稿。
8. 要验证文学效用，必须另外预注册新题、固定Writer/Planner/评审、保持绝对篇幅一致、比较同模型启用/禁用经验的行为和文字结果；模型意见不是人类文学真值。**本轮0付费训练，0正式晋级。**

## 6. 后续恢复顺序

1. 读`CURRENT_HANDOFF.md`第47节、V60第46节及本文件；复核V61新旧红绿 CI 原始SHA。
2. 先补独立/可信评论者审核权限、经验撤销/冻结快照的真实控制面，并审查SkillRegistry低层权限。
3. 再从V31/V38 **已有不可变证据**中挑一条真实尚未晋级的经验，映射成HYPOTHESIS_ONLY，逐项核查来源、人物知识、反例和何时SKIP，不能直接让它成为已审策略。
4. 仅在受控验收准备妥当后考虑文学真题，不复考V49失败原题、不调用模型替WF答题，也不以模拟结构测试取代独立文学评价。
