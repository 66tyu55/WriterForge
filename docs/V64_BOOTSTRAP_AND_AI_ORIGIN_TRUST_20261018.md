# WriterForge V64｜受信技能初始化与AI来源提交授权（2026-10-18）

> **范围：仅开发分支 `v64-trusted-bootstrap-ai-provenance`，基于V63 `v63-skill-authority-and-concurrency`。** 未合并`main`、未更改V49文学考试结论、未修改V56–V63冻结CI/R2证据。此轮全部合成SQLite与原有无付费模型的回归：**没有新的文学训练、没有新的原创文学评分、没有读取私人R2原件、没有能力晋级。**

## 1. 完整审计复核：修复的是两个真正不同的授权入口

V63已封住`SkillRegistry.promote()`直接晋级和`StoryCommit`内撤销竞态，但V63的2项特意保持绿色的未解决观察用例指出：

- **根权限/初始化**：新建此前不存在的Skill时，可信宿主`SkillRegistry.register(CapabilityContract(level=10,status=ACTIVE))`原来能够在没有文学证据的情况下将它标成正式L10。这与「把已存在的L1同名覆盖成L10」是两种完全不同的风险。签名来源必须绑定技能合同/范围/级别，否则宿主声明不能冒充学成。
- **源头/写作提交**：在未经过`VerifiedWritingFlow.accept_candidate`的情况下，低层`WritingFlow.accept_draft(origin='assistant_generated')`或`StoryCommitCoordinator.commit(ACCEPT_PROSE)`以前可以直接提交。可信人工编辑仍然需要该底层接口，因此解决方案是**只针对AI来源强制受信许可**，并非禁止人工写作。

额外检查`writerforge/studio_server.py`：本地Studio候选可以自动生成/预览，但原代码没有在其HTTP服务中调用`accept_candidate`将候选默认变为已接受正文；Studio服务还不是一个独立的真人签名/宿主授权机构。不能把网页预览或`explicitly_approved=True`的布尔参数单独当成身份证据。

### Github已有源码对照，借理念不复制

- [eventsourcing SQLiteTransaction](https://github.com/pyeventsourcing/eventsourcing/blob/9.5/eventsourcing/sqlite.py)，已读取blob `2cf6afe96045ad3dc2c432907b3a09cb53b2401d`：从显式事务内做真实性检查到最终收据入账应原子化；无需复制该框架。
- [SQLAlchemy versioned history](https://github.com/sqlalchemy/sqlalchemy/blob/main/examples/versioned_history/history_meta.py)，已读取blob `ab6e3583dd6a4a2836c4d1738fc97cf9939c9d3a`：技能初始声明/历史版本不可因一个数字就取得权限；但不引入ORM。
- [LangGraph checkpoint](https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint/langgraph/checkpoint/base/__init__.py)，已读取blob `c7cacc7bfd703f298427e870bd6d07b4aa395812`：冻结项目/版本/上下文身份、从旧状态恢复不能默默获得新授权；不建立第二调度。
- [OpenFeature evaluation reason enum](https://github.com/open-feature/python-sdk/blob/main/openfeature/flag_evaluation.py)，已读取blob `df47e7327a208cb72b9717a9e49cbf4cdb8969e3`：区分`STALE/DISABLED/ERROR`原因，不把“没通过”一概当文学失败；不安装SDK。

## 2. 先冻结原始失败，不能事后改测试冒充没有漏洞

[V64初次红色 Actions #39114944248](https://github.com/66tyu55/WriterForge/actions/runs/39114944248)：

- 12项新对抗用例**0/12通过**，其中**3项运行到错误接受行为、9项因新API尚未实现而ERROR**。不能把缺少新接口的9项都算成真实外部安全漏洞。
- 原始机器JSON SHA256：`607ffc257926c369b83a796bf4666971d7d04ba2105e2bc1921e357bb3e5c9e5`。
- 原始证据 [artifact #12132275387](https://github.com/66tyu55/WriterForge/actions/runs/39114944248/artifacts/12132275387) ZIP SHA256 `a5d9c76145a8239a374b6659f58ead92446e71cc67c6ee2448cc68983a5ebae2`。
- 期间旧V21/V23正向夹具因V64更严的AI来源签名或高等级Skill初始化被正确拦下，仅在**V64新分支**迁移为受信合成测试签名；它们原来的测试目标（AI文本不能训练出作者声音、训练/草稿可恢复）保持。V21/V23旧分支与红绿收据均不覆盖。

## 3. 底层实际修复：已实装，未复制他人代码

### A. `writerforge/evolution.py`：可信初始能力

1. `SkillRegistry.register`在`level>1`时**需要外部`bootstrap_attestation`**；HMAC签名绑定`scope`、完整`CapabilityContract`（技能名/当前级别/状态/原始版本/依赖）、来源收据SHA、签署者与审核ID；私有签署密钥经`WRITERFORGE_SKILL_BOOTSTRAP_VERIFY_KEY_HEX`配置或显式受信注入，不写进GitHub或SQLite。
2. 高级初始化合同与签名收据在同一次SQLite写事务中持久化到`skill_capabilities`和`skill_bootstrap_receipts`。已登记同名技能依旧不能被覆盖；伪签名、修改等级、换项目scope后复用旧签名均拒绝。
3. V64之前存在但**缺少可信初始化收据**的高等级旧技能不会被清除、降级覆盖或假造旧签名；从新的`SkillRegistry`读取时显示`SHADOW`，并可通过`bootstrap_verified()`判断目前是否获得可信初始化授权。对无法证明的旧初始化，至少不能将其当成正式`ACTIVE`等级。
4. 进一步补查到旧高等级虽是`SHADOW`但`lagging()`原先只比较数字，仍可能让L9未经验证记录满足L5前置依赖；V64改成**必须同时具备`ACTIVE`状态与足够级别**，未核验经验不能成为其他能力的升级基础。
5. **L1被允许作为不带高级证据的初始基线**，但`bootstrap_verified(name)==False`意味着这仍是“系统起点”，绝非已学会文学能力；不得以初始化作为晋级记录。已有L2–L10可信导入需要由用户控制的外部签署者审阅原始证据，并签发真实收据。

### B. `writerforge/ai_provenance.py`与正式写作提交流

1. 新增有界`issue_ai_commit_permit`/`validate_ai_commit_permit`。受信宿主签名绑定：项目、场景（支持小说中文和`novel.ch1.s1`等真实名字）、`commit_id`、**真实已发布**快照ID、稿件正文SHA与候选SHA、作者批准标记、可选写前决策ID+哈希、来源必须是`assistant_generated`以及`literary_quality_verified=False`。
2. 私有签署密钥经`WRITERFORGE_AI_COMMIT_VERIFY_KEY_HEX`从进程外提供，不能把任何真正使用的密钥上传到Github/R2回执/仓库。V64测试仅有显式标记的合成测试密钥。
3. 只有正式`accept_candidate`在验证真正候选文件、文件SHA、场景/快照、显式批准与经验冻结计划后签发Permit。低层`WritingFlow.accept_draft`传递给`StoryCommitCoordinator.commit`。
4. **最终`StoryCommitCoordinator.commit`**在自己的`BEGIN IMMEDIATE`事务里重新验证Permit、已发布快照、经验最新授权状态、绑定的正文/项目/scene/commit等；与业务内容、事务日志同事务写入`story_ai_provenance`。无签名、无宿主密钥、串场景、改正文、复用不同提交、伪称`author_written`并夹带AI permit，一律拒绝；确认现有AI候选不能仅靠文件manifest自称可信。
5. 人工写稿原有`author_written`/合法内部提交继续正常工作；`assistant_generated`必须由宿主提供证明。但**任何持有同一Python进程和可信私钥或SQLite原始写权限的恶意插件仍不构成隔离安全边界**。HMAC不能单独证明“真人亲自点击批准”，布尔`explicitly_approved`依旧由本地宿主声明：需要后续独立的用户身份/确认UI或系统级权限隔离。
6. 旧机器稿件历史没有可信签名，不追溯补签、删档或默默归因。重放要求相同的签名及同一原始提交标识；如果旧历史缺少凭证，则只能作为历史遗留接受情况另行审计，不是全新AI授权。

### 最新补充：有已审经验的 AI 许可也必须绑定真实冻结决策

新增一项完整正向/负向合成回归：先在学习模式登记真实SQLite来源定位，再用V61已有外部签名批准实验经验；只有AI来源许可还**绑定准确的`decision_sha256 + experience_attempt_id`**，StoryCommit才接受。即使Permit本身合法签名，若项目已存在批准经验但无冻结决策，仍然拒绝。这证明来源许可不会悄悄绕过V61–V63的受控经验链，**不等于独立文学效果验证**。

### C. `writerforge/db.py`：不添第二套存储

新增`skill_bootstrap_receipts`和`story_ai_provenance`两张表。现有SourceStudy/Xuehai/StoryCommit/FactJournal/R2正文存储原样保留；只记录摘要和权限证明，没有复制小说正文或生成整稿。此代码面向SQLite本地账本，不宣称持有原始数据库写权限的用户不可篡改。

## 4. GitHub最终回归与可重放SHA

[正式V64 CI #39116237730](https://github.com/66tyu55/WriterForge/actions/runs/39116237730)：`completed/success`。

- V64新增 **16/16** 合成安全契约测试，完整项目 **697/697** 工程测试通过；均无新的实际文学模型调用。
- V64新JSON机器回执SHA256：`30661fedbad08341931294fff5791253b13b29776d376fc70ec8bf60a6d60d4f`。
- [绿色证据 artifact #12131749143](https://github.com/66tyu55/WriterForge/actions/runs/39116237730/artifacts/12131749143)，ZIP SHA256 `7f1ae017191235b3c00a949c10bccb6d6c778ec4f222619289f7a7684b170fad`。
- 最终源码/测试 SHA：
  - `writerforge/evolution.py`：`0cb8b44818f8440b10751415801ad64ebb39cd3f6332db1ca148e347e411f92b`
  - `writerforge/story_commit.py`：`0cf4970dffec31ef61a227d6e64659f90ff6b22f97b284e9bde0e854a4c660f0`
  - `writerforge/verified_flow.py`：`1ee283f052949fc59b01112b9ae037b23fb521ea9fbf8eedc46bfc6c263ff76c`
  - `writerforge/ai_provenance.py`：`8e0baf36404d8010977e3d4f37fac3f0f0431921ec89698d56b4dd236fb18c23`
  - `tests/test_v64_bootstrap_provenance.py`：`45190ccee13b1805832d06fce00316a4ffac6227a2c9cab9023feed77da06858`
  - `scripts/audit_v64_trust.py`：`e51589a06e74f64a296f1bcbb7c36a4696b7e04ca1f46aac6c3851ab106952c4`
- 旧V12、V21、V23、V63测试受新许可契约影响的正向夹具只在V64分支显式迁移，原旧分支与历史机读报告不可覆盖；该差异必须在正式合并前仔细审查。

## 5. 绝不能声称完成的边界

1. **文学语义与真实写作进步未验证**：本轮源签名授权不构成人工文学水平评审，V49 `THIRD_STRIKE_FAILED`和第二文学窗口`LOCKED`不变。新数据结构不等于WF已经学会独立写作。
2. **真人身份没有证明**：HMAC说明某个持私钥的宿主确认这些字段，不证明这个宿主已真实完成独立真人审核。私钥必须离开不可信插件/语言模型进程，否则同进程攻击者能伪造签名；高信任生产应将签名动作放到隔离进程/安全操作系统服务。
3. **初始历史存量迁移未完全证明**：旧V63以及更早数据库如果高等级没有独立收据，新的API只以SHADOW/未核验态展示，不会凭空重建历史证据。但其他绕过API的旧代码或原始SQL仍可能直接读`skill_capabilities.level/status`。部署需要旧库备份、清单、逐个审批与跨版本迁移方案。
4. **人工origin仍依赖可信宿主**：低层人工写稿允许保留，但宿主若任意谎称`author_written`而不经过真人签名，Python API不可能单独判定真实作者是谁。Studio和第三方Agent的实际权限分离还需第二层系统级身份/流程。
5. **双账本与容量**：`WriterForgeDB`和`FactJournal`跨存储没有全局ACID；签名撤销/密钥轮换、有限反馈128上限、数据恢复、一百万历史记录磁盘增长仍需单独验证。
6. **安全性质仅限有界的受信API边界**：本轮pytest/unittest的绿色不意味着代码抵挡恶意操作系统用户、原始SQLite写入、偷取HMAC签名密钥或未经许可的第三方工作流。

## 6. 下一步最值得做的不是继续加Skill

V65应优先处理**可信签名能力与不可信写作Agent的进程隔离、可验证真人/宿主审核、旧高等级技能的只读迁移报告**。随后才是V31/V38原始R2证据的独立只读核验、来源许可与可靠读者评论。先把谁有权授予能力、谁能写入正式稿件说清楚，再启动任何新文学盲评，不能靠系统自测给自己晋级。
