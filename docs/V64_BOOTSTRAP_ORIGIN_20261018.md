# WriterForge V64｜初始技能来源权限与 AI 稿件来源隔离（2026-10-18）

> **隔离开发分支** `v64-bootstrap-origin-authorization`，继承V63。未合并`main`，不修改V49文学终审、V56–V63原始结果或私人R2。**本轮0文学模型调用、0文学训练、0正式文学晋级**。这里的9个新增用例全部是合成结构/权限测试。

## 1. GitHub源码对照后的目标约束

- [eventsourcing SQLite事务](https://github.com/pyeventsourcing/eventsourcing/blob/9.5/eventsourcing/sqlite.py)：授权条件与持久化状态要明确区分，异常原子回滚，复用WF现有SQLite而不引入第二套事件框架。
- [SQLAlchemy版本化历史](https://github.com/sqlalchemy/sqlalchemy/blob/main/examples/versioned_history/history_meta.py)：区分新实体的初始化与已经存在技能的等级升级、保留审计后的版本并阻止同名覆盖；不复制ORM。
- [LangGraph checkpoint](https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint/langgraph/checkpoint/base/__init__.py)：用明确的写前快照和写后收据约束入口；不新增图调度器。
- 参考V63审计未关闭的两项：`SkillRegistry.register`新建一个此前不存在的L10 ACTIVE技能，不需要文学资质凭证；`WritingFlow.accept_draft`／`StoryCommitCoordinator`可直接把任意稿件标为`assistant_generated`，绕过正式`accept_candidate`的来源验证。

## 2. 冻结失败先行证据（不能把缺失API算成全部漏洞）

- [GitHub Actions 初始红色 #39116315805](https://github.com/66tyu55/WriterForge/actions/runs/39116315805)：V64新增9项中**3个行为FAIL**、**3个新接口尚不存在ERROR**、3项PASS。三个已执行行为断言失败：未经核验的L10 ACTIVE初始化、普通WritingFlow直接接收`assistant_generated`、低层StoryCommit直接接收`assistant_generated`。旧分支测试/文档未改。
- 新增权限后第一次大回归 [#39116433860](https://github.com/66tyu55/WriterForge/actions/runs/39116433860)：新增9/9通过，但旧690套件发生8个ERROR/1个FAIL（历史高等级正向输入与旧模拟AI直提交流程违反新约束）；该红色运行同样保存，不能用旧绿色掩盖。
- 以上日志原样保留。V64 CI这一版本未生成单独的结构化红色JSON，所以**不能声称已经冻结机器JSON SHA**；真实原始日志由GitHub Actions留存。

## 3. 已实际落地的修改

### 能力初始化 `writerforge/evolution.py`

- 新技能一般`register(CapabilityContract)`只可直接建立默认L1 ACTIVE；不能靠`register(new,L10,ACTIVE)`把文学技能等级升满。
- 私有老项目能力可由`import_legacy_capability(...,provenance=...)`导入原声明等级，但必须`SHADOW`，不宣称已经验证或正式晋级，且重启后保持。
- 显式可信旧发行基线的初始化`register_verified`要求外部密钥 `bootstrap_verifier_key`／`WRITERFORGE_BOOTSTRAP_VERIFY_KEY_HEX`、审核者与审核收据ID，签名绑定技能ID、等级、状态、依赖、声明、revision。该签名证明**声明获授权**，不证明文学水平。
- 原V63`SkillRegistry.promote`公开直升禁用、签名manual`EvolutionEngine`晋级通道、SQLite CAS及旧失败证据仍保持。

### AI稿件来源边界 `story_commit.py`、`writing_flow.py`、`verified_flow.py`

- 本地低层`StoryCommitCoordinator.commit`及`WritingFlow.accept_draft`如果看到`ACCEPT_PROSE.origin="assistant_generated"`，没有正式候选的校验回调与内部许可标记则拒绝。
- 正式`accept_candidate`先验候选原文/manifest SHA、冻结写前决策、项目/场景/快照，之后传入内部许可标记。其`precommit_check`继续在`StoryCommitCoordinator`的`BEGIN IMMEDIATE`事务内重新确认撤销/状态，V63事务窗口保护仍有效。
- `author_written`和`author_edited`原有人工稿件仍可由可信宿主正常提交；旧的普通`accepted`属于**没有权威作者口吻证明的低可信标签**，不能因为通过就计算为真人作者声音。
- **明确安全边界**：内部Python许可标记不是无法伪造的系统级权限；与WF同一进程、具有任意代码执行权限的恶意插件可以导入/仿冒内部API并直接写SQLite。V64堵住的是**默认调用路径的遗漏**，不等于进程隔离或外部可信服务端鉴权。

### 旧测试夹具透明兼容迁移

- V12需要测试高等级技能依赖/晋级时，使用**合成签名可信初始基线**，不再偷用无凭证的高等级`register`。
- V23模拟旧项目恢复的高等级技能，改为显式`import_legacy_capability`并验`SHADOW`状态。
- V21以`accepted`这一旧的**非作者可信来源**保留陪伴系统的“非作者文字不会变成作者声音”测试，不再通过原始低层接口假冒`assistant_generated`。正式`assistant_generated`的合法路径单独由V64新增测试覆盖。
- V63此前两个故意保持开放的绿色观察测试，在V64中更新为应当拒绝的测试（**原V63原始运行仍不动**）；同名覆盖测试改为相同等级不同声明，确保仍真正触及IMMUTABLE合同。
- 不删除旧测试、不隐藏影响、不因为要凑绿而恢复漏洞。

## 4. GitHub真实测试

[Actions #39116669476](https://github.com/66tyu55/WriterForge/actions/runs/39116669476) `completed/success`：
- V64新增 **9/9**；全仓库包括旧测试在内 **690/690**（部分历史套件会按自身条件跳过）。
- SHA256：`evolution.py` `f2ea9a77aa1cd8c4468024d455eec45bf722b07c124e668381124c8df981f36b`；`writing_flow.py` `bd42116486508212694145f8204797d14b0b802274f65fcb17cc106c9c93f38e`；`story_commit.py` `2e40234b95959fdce56859b10e08e075b48fe2fbf88069299a111e4bf51f9b66`；`verified_flow.py` `f195052c5c5b2c43f78c64d325c5b379f1eaf084c576f5da68e52821308c5c7a`；`tests/test_v64_bootstrap_origin.py` `01c23067968225c5652d0dd9d74f40bf649b8b3e2f739e97eb8bf233f68c0923`。
- 本测试使用临时SQLite、合成来源/作文，没有读取模型私人会话，也未调用模型生成文本。

## 5. 仍不能冒充“WF成为作家”

1. 旧L10可以通过可信签署的发行基线登记，这表示系统管理员作出了授权声明，不表示独立文学审稿证实WF写作水平达到十级。
2. 对同进程任意代码执行、SQLite原始文件可写者，这类应用层许可仍不是安全沙盒；后续要通过独立进程、系统账户权限、受限RPC隔离插件。
3. Studio、旧批处理、外部插件是否直接运行不受信的故事写稿函数，仍需动态调用验收，不要把所有宿主操作直接叫模型自主创作。
4. Reader评论身份真实性、V31/V38私人R2文学原始证据语义分歧、跨WriterForgeDB/FactJournal双库事务、存储增长/迁移审批和发布流程依然待整改。
5. `main`依旧是历史正式版；V57–V64是叠加开发分支，不能无迁移设计地全部合并；V49`THIRD_STRIKE_FAILED`和第二文学窗口LOCKED不变。

## 6. 下一步

先完整审计Studio与原生宿主进程是否可信，并用受限IPC/独立进程权限模型替代同进程标记；然后接入独立真实读者审核权限，最后才有条件对V31/V38真实文学经验做独立盲评。绝不重复旧付费文学训练来冲数字。
