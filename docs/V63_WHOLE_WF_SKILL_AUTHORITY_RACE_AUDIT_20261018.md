# WriterForge V63｜整仓权限、双SQLite并发与整体架构审计（2026-10-18）

> **仅在隔离分支 `v63-skill-authority-and-concurrency`**，基线为 `v62-experience-negative-transfer` HEAD `4bda7acd78899891a4b662d7c95031a887984e16`；未合并主分支。此轮零付费/文学模型、零R2网络、零小说重训，旧V49 `THIRD_STRIKE_FAILED`/第二课程`LOCKED`及所有V56–V62红绿证据保持不变。本文结构测试、静态调用审计**不证明文学理解或文学质量增长**。

## 0. 正式范围：先定位风险，再冻结真实失败

V62成功将 `NOT_APPLIED` / `UNCERTAIN` 持久化并影响下一轮SKIP，但查到两类尚未处理的实际问题：

1. `writerforge/evolution.py` `SkillRegistry.promote()` 未检查签名或人工批准；同名`register`可覆盖合同；`get()/all()`返回内部可变对象；`revalidate(passed=True)`可凭布尔参数让SHADOW回ACTIVE。原实现还有`_persist`内部多次commit、先更改内存后写数据库等风险。
2. `writerforge/experience_decision.py` `decide()`先用普通SELECT分别读审批/撤销/失败状态，后才INSERT冻结选择。在两独立SQLite写连接之间，第二个连接能在读取与提交间写入撤销或NOT_APPLIED，导致第一个连接持久化已过期的`SELECT`。正式`accept_candidate`在`StoryCommitCoordinator.commit()`前验证一次，也可能因并发撤销形成`check→commit`窗口。

### 原始证据（不修改原报告）

- 初始 [Actions #39112500068](https://github.com/66tyu55/WriterForge/actions/runs/39112500068) 9项断言失败，但此时审计脚本生成JSON时用了错误测试文件名，**无完整artifact**，不能把它冒充有效机器回执。历史CI保留。
- 修正**审计收据脚本而不修改生产代码或原测试**后，正式红色 [Actions #39112554685](https://github.com/66tyu55/WriterForge/actions/runs/39112554685)：**9/9全部断言失败**，不是缺少接口的测试错误。其中真实重现两条并发竞态、旧技能对象可被修改、同名重登记覆盖、同线程直升、退回SHADOW后任意revalidate、两数据库陈旧版本重复晋级、错误写事务留下部分状态、最终接受前撤销逃逸。
- 原始JSON SHA256 `6647b93f1b6ffe867fd3429309d92b3213855891fabc3ee879a67799d44ad4e3`；[原始红色artifact #12130976557](https://github.com/66tyu55/WriterForge/actions/runs/39112554685/artifacts/12130976557) ZIP SHA `c43edd86df5922db1b98d1fa223762d61782e8c138d15aaed65d486b01757a48`。

## 1. 真正读取并对照的GitHub成熟机制

本轮读取了以下现成GitHub源码，只取思想，不copy/安装它们：

| 开源源码 | 真实对照点 | 借鉴的约束 | 不照搬的原因 |
|---|---|---|---|
| [eventsourcing SQLiteTransaction](https://github.com/pyeventsourcing/eventsourcing/blob/9.5/eventsourcing/sqlite.py)，blob `2cf6afe96045ad3dc2c432907b3a09cb53b2401d` | 事务显式开始，异常时完整ROLLBACK；原子提交后记录可见 | `BEGIN IMMEDIATE`必须包住「授权读 + 生成SELECT收据」；最终接受的验证必须在提交锁内 | WF已有小型SQLite与StoryCommit，不需要再装整套事件框架 |
| [SQLAlchemy versioned history example](https://github.com/sqlalchemy/sqlalchemy/blob/main/examples/versioned_history/history_meta.py)，blob `ab6e3583dd6a4a2836c4d1738fc97cf9939c9d3a` | 实体version用在历史变更与并发检查 | 已加载技能的`revision/level`须与DB当前行匹配；陈旧连接不能重复改版本 | 不引入ORM或搬移别人的历史表实现 |
| [LangGraph checkpoint protocol](https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint/langgraph/checkpoint/base/__init__.py)，blob `c7cacc7bfd703f298427e870bd6d07b4aa395812` | channel_versions、versions_seen与状态快照 | 冻结草稿/技能对象的历史版本，不能仅凭旧计划重复执行 | 不创建第二个调度器 |
| [OpenFeature evaluation reasons](https://github.com/open-feature/python-sdk/blob/main/openfeature/flag_evaluation.py)，blob `df47e7327a208cb72b9717a9e49cbf4cdb8969e3` | DISABLED/STALE/ERROR/UNKNOWN等解释性原因 | 保留先前V62的`SKIP/PRIOR_NOT_APPLIED`等稳定原因码与负证据 | 无需引入通用特性旗标系统 |

## 2. V63修复范围与交易边界

### A. `writerforge/evolution.py`

- `CapabilityContract`冻结为frozen dataclass，初始化依赖表与返回的`get/all`都复制，不能靠修改返回对象偷改真实能力级别。
- `SkillRegistry.register`同名只能完全一致地幂等重放，不能以同名合同从L1覆盖成L10；新声明仍是可信宿主的**初始注册**，不能由此说明文学能力真实获得验证（见剩余风险）。
- 公共 `SkillRegistry.promote`不再提供无签名直接晋级；当前唯一官方活跃级别变更通过 `EvolutionEngine.apply_upgrade(...,policy="manual",approved=True,attestation=...)`，在真正`SkillRegistry._promote_verified`存储边界**再次检查同一外部HMAC凭证及数值门槛**。
- 对升级目标/受影响依赖技能一次性创建新不可变合同；先`BEGIN IMMEDIATE`，核对`scope,level,revision,status,statement`旧版本，按CAS条件更新，插入同事务升级日志，**只有数据库commit成功后**才替换内存字典。审核日志插入失败，全部SQLite/内存保持原样。
- `revalidate(passed=True)`原布尔接口不能重新激活SHADOW，允许`passed=False`保守降为SHADOW；日后恢复原等级必须设计可信独立审核/恢复接口，不可凭一个布尔参数通过。
- `tests/test_v12_evolution_taste.py`中原来的“直接SkillRegistry.promote视为正例”**仅在V63分支修改夹具**为独立签名+manual审核；此前V12/V62源分支和CI证据不动。没有通过删除该测试来凑绿。

### B. `writerforge/experience_decision.py`

- `decide()`新增围绕整次查询的`BEGIN IMMEDIATE`，把最新revocation、postwrite负反馈、候选签名检查与持久化`SELECT`放入同一次SQLite写事务。同一文件的第二写连接只可能在其前或后提交，不能在中间插入撤销。
- 老的`attempt_id`只允许哈希一致回放，但`validate_live_decision`仍重新核查撤销、失败与来源新鲜度。新的事务失败完整回滚。
- 两个**真实独立的`WriterForgeDB`连接**、非预先伪造的SQLite错误模拟，在读取审批状态时试图签名撤销和写入历史NOT_APPLIED；新程序用真实SQLite写锁阻止中途提交，待第一条操作完成后新事件可以提交，下一次选择正确SKIP。

### C. `writerforge/story_commit.py`、`writing_flow.py`、`verified_flow.py`

- 正式`accept_candidate`保留原先早期检查，但在调用`WritingFlow.accept_draft`时传递额外`precommit_check`，并由`StoryCommitCoordinator.commit`在其既有`BEGIN IMMEDIATE`**后**、写入任何`story_commit_receipts` **前**执行。
- 如果另一个连接在首次验证通过后立即写入signed revoke，最终StoryCommit事务会再次核对已冻结`decision_sha256`、来源快照和是否SELECT仍然有效，并拒绝接受。原稿及旧决策历史仍保留。
- 注意：低层`WritingFlow.accept_draft`本身仍允许可信宿主写入手工稿件。它不是完全零信任服务端；不允许未经审查的插件把`origin=assistant_generated`当成自动授权（见剩余问题）。

## 3. 修复后GitHub独立运行结果

[Actions #39113729476](https://github.com/66tyu55/WriterForge/actions/runs/39113729476)：V63新增 **9/9** 修复型真实对抗通过，另有 **2/2** 特意演示仍未解决边界的观察性测试（绿色表示风险已复现）。V12、V61、V62旧契约回归成功；全仓库 **681/681** 合成工程测试通过。该成功只代表代码依照合约行为执行，**绝不代表WF文学写作进步**。

- V63测试JSON SHA256 `6997eb0d1eb60131d1f83440298cc6644d161cc00e26ebcc337f2e5e5e19416e`。
- 第二份**全仓库AST审计**JSON SHA256 `39c0fa13c46d564c5a81b665a85eb78d21f520cbe1c62526277ac5e28610b268`。
- [双报告绿灯 artifact #12131238419](https://github.com/66tyu55/WriterForge/actions/runs/39113729476/artifacts/12131238419) ZIP SHA `2a88c7e33946b91ae356b3bc25ff7f0a871853613d6e743ad8e6c1928df04dc2`。
- `evolution.py` SHA256 `44bb20a6dfd6a4b6f51100062fe6eb6685be7adfb19f0719434d005044db6a6e`。
- `experience_decision.py` SHA256 `85f059489decf3a807b2b7f87ae708c399dc0df3009795ce7134ff858b78b456`。
- 源与测试运行详细SHA在该Actions日志中，可按文件逐一复核。文件修改都只在V63开发分支，没有重写V49旧文学记录。

## 4. 「整体仔细检查」的范围与明确证据分级

新增 `scripts/audit_v63_full_architecture.py` 使用Python AST遍历仓库的`writerforge/`、`scripts/`、`tests/`代码，并列出生产核心调用点/行号、受控API和仓库SQLite表。实际统计：**95个Python核心模块、108个测试文件、94个工作流、74处生产权限/故事相关调用点**，静态源码哈希留机器报告。机器状态标记 `STRUCTURAL_REVIEW_REQUIRES_HUMAN_AND_FURTHER_TESTS`。

### 已经由实际CI动态支持

- 同名技能重注册不能覆盖高等级；
- 直接调用`SkillRegistry.promote`遭拒；
- 返回对象不能通过普通属性修改真实技能；
- `revalidate(passed=True)`不能任意恢复；
- 审核日志插入失败不留部分升级；
- 两个技能写连接旧revision不能重复晋级；
- 两个经验写连接中途撤销/负反馈不会抢写；
- 仅第一次检查通过但正式提交前撤销，最终接受仍被拒。

### 额外实测：两个仍未关闭的受信入口

`tests/test_v63_remaining_trust_boundaries.py` 两项观察性测试均通过，但其**绿色表示风险仍然可以复现**：

- 对一个全新ID，`SkillRegistry.register(CapabilityContract(level=10,status=ACTIVE))`仍接受为高等级主动技能。这不是已存在同名技能的覆盖，也不是文学能力经评审提升；要区分「可信导入一个基线」与「已经学到这个技能」。
- 已有真实合成来源定位且受信签名的实验策略，仍可以从**可信宿主低层**`WritingFlow.accept_draft(...origin="assistant_generated")`直接提交，而未经过上层`accept_candidate`的经验方案。该入口也供人工写作使用，不是原本设计给不可信插件的公开鉴权API；第三方宿主运行隔离与助手生成稿授权仍需分离。

这两项故意保留为**未解决问题的观察证据**，不列入V63九个修复成功项。全仓机器报告的`open_boundary_observation_tests`亦分别指向它们。

### 整体扫描后**尚未关闭的8项风险**

| ID | 状态/优先级 | 具体还缺少什么 |
|---|---|---|
| WF63-RISK-ROOT-BOOTSTRAP | **P0 / 正式能力声明** | `SkillRegistry.register`仍允许可信宿主**创建一个全新的高等级ACTIVE技能**而无需文学实证；这与阻止「覆盖同名已存在技能」不同。新初始等级及老库导入需要专门的受信bootstrap/权限管理，不应把它算成学会作家技能。 |
| WF63-RISK-RAW-STORY-COMMIT | **P0 / 执行边界** | 直接使用低层`WritingFlow`／`StoryCommitCoordinator`写作时，不会自动执行与`accept_candidate`相同的实验经验签名检查；可信宿主/人工编辑必须与AI生成来源明确区分。不能把原本为可信内部代码设计的API误称为沙盒。 |
| WF63-RISK-NATIVE-SQLITE | P1 | 拥有SQLite原始写权限者可直接UPDATE技能与审批表；模块级HMAC不是独立数据库公证和系统级权限隔离。 |
| WF63-RISK-MODEL-INFLIGHT | P1 | 模型收到提示后如中途撤销，该请求仍可能运行；现在可以拒绝后续接受，但对远程/本地推理进行即时取消尚未验证。 |
| WF63-RISK-EXTERNAL-IDENTITIES | P1 | HMAC只说明密钥持有者签过声明，不能证明评审员是独立的人类，或语义/来源许可正确。 |
| WF63-RISK-LOCALE-TWO-DBS | P1 | `WriterForgeDB`与`FactJournal`仍为独立账本，跨库身份映射、失败补偿、统一快照/持久迁移尚未闭环。 |
| WF63-RISK-READER-SOURCE | P1 | 同一读者可填两个`reader_id`，评论URL只提供线索；真实评论者独立性与证据撤回未完成。 |
| WF63-RISK-RELEASE | P2 | 软件包版本`27.0.0`、V57–V63仍为层叠开发分支，93个历史工作流混合常规CI、公共经典原文结构验收及一次性训练；大规模磁盘压测、升级/回滚方案待独立验收。 |

**特别提示**：本次AST扫描不等于完整运行时追踪。动态导入、外部宿主插件、原生SQLite管理权限可能不在静态图中。8项是架构待审/边界声明，**并不代表8处已经可被外部远程攻击的安全漏洞**。

## 5. 现在不应继续盲目扩功能

建议V64从两个优先缺口开工：
1. **技能创建本身的可信来源**：不能在启动时`register(new,level=10,status=ACTIVE)`就声称WF已经会写作；先建立旧库存量迁移与初始技能权限的可信证明，同时不要破坏老能力来源。
2. **写作入口信任隔离**：保留人工稿件直接StoryCommit的功能，但助手/模型生成稿必须带不可伪造的决定/来源/作者接受收据；审查Studio与宿主插件的真实调用路径，避免UI绕过。

此外继续测试撤销/晋级时的数据库磁盘容量、并发冲突和故障恢复，逐步整改评论者真实性、R2可信来源与双SQLite版本映射。

**文学最终事实继续保持不变**：V49 `THIRD_STRIKE_FAILED`/未晋级。V31/V38旧经验的SHA只是未验证私有R2远程指针；本轮没有新的真实源文获取，没有证明语义因果，也没有新的正式文学评分或模型训练。
