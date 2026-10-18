# WriterForge V59｜先对照 GitHub 源码，再修全局登记时间（2026-10-18）

> **仅隔离分支 `v59-global-ledger-clock-audit`**，从 V58 草稿分支建立；正式 `main`、V56—V58原始失败证据、V49文学终审不改。本次没有R2同步、付费模型、原著重训、小说创作或真实文学语义评判。

## 1. 先读过的开源实现与可复核源码

本次**先从 GitHub 读取源码**，再设计 V59 新反例。只对照机制，没有复制源码或引入第三方框架。以下为源码路径、读取时的 blob SHA（用于说明参照版本，并非 WriterForge 的 SHA）。

| 对照源码 | 真实机制 | 我们借鉴的原则 | 没有照搬的部分 |
|---|---|---|---|
| [pyeventsourcing/eventsourcing · eventsourcing/sqlite.py](https://github.com/pyeventsourcing/eventsourcing/blob/9.5/eventsourcing/sqlite.py)；blob `2cf6afe96045ad3dc2c432907b3a09cb53b2401d` | `SQLiteTransaction` 在同一事务内开始、提交或回滚；`SQLiteApplicationRecorder` 以通知ID分页回放 | 一次写入及其全局登记必须原子化；按记录序号而不是小说时间作为进度基准 | 不引入整个eventsourcing应用、领域聚合、快照、通知订阅系统；WF仅需本地独立关系账本 |
| [django-simple-history · simple_history/manager.py](https://github.com/django-commons/django-simple-history/blob/master/simple_history/manager.py)；blob `5fa404d93000a667422fac82af88d306d975319d` | `as_of(date)`约束历史数据；`latest_of_each`选择历史有效版本；相关对象采用历史作用域 | 查询历史主张，关联人物/章节/披露也必须在**同一历史时点可见** | 不引入Django ORM，不把墙上时钟或数据库导入顺序误当小说故事时间 |
| [SQLAlchemy versioned_history/history_meta.py](https://github.com/sqlalchemy/sqlalchemy/blob/main/examples/versioned_history/history_meta.py)；blob `ab6e3583dd6a4a2836c4d1738fc97cf9939c9d3a` | 单实体独立版本号、历史记录表及可选时间戳；版本列可辅助并发冲突判断 | 区分一个事实的版本次序和整个账本的变更次序，且历史不能被直接覆盖 | 不引入SQLAlchemy ORM、复制版本化mixin，也不把单表版本号当全局登记时间 |

### 取长补短结论

- WF自身 SQLite 已有 `temporal_claims.recorded_seq`，但它**只能排序主张**，不能还原当时有哪些作品、人物身份或读者披露。这是V58绿灯之后仍存在的错误窗口。
- 不仅采用事件队列的设计思想，还要参考历史外键的**同一时间快照传递**；两类机制组合才不会把事后关系冒充历史关系。
- 额外全局表/索引有硬盘开销，操作序号也不是文学因果证明；因此限制原文入库、保留8192上限和分页机制，避免因新架构无限占用内存。

## 2. 先冻结的新失败证据（不可覆盖）

### 第一轮：统一时间轴的历史漏洞

[Actions #39105219080](https://github.com/66tyu55/WriterForge/actions/runs/39105219080)：
- V54~V58旧回归 **45/45通过**。V59新增 **0/7通过**；**一项**确证了“游标回放可继承后绑定的跨章人物”；**六项**因全局时钟接口尚不存在或还未支持而报错，不能全算确证漏洞。
- 原始报告SHA256 `c1eedd3e8a8a509000bdda4a6ece69554e06aca813b766961d9b1c38ef4e17fb`。
- [原始红色 artifact #12127911793](https://github.com/66tyu55/WriterForge/actions/runs/39105219080/artifacts/12127911793)；ZIP SHA256 `515d29f70f2513e4d7d25c4a24ea8edcecb4cd3f92d243a459da133dbcf4e1ef`。

### 第二轮：图历史及CLI接口补充红队

[Actions #39105648147](https://github.com/66tyu55/WriterForge/actions/runs/39105648147)：
- V59新用例 **8/11通过**；补充的3个项目当时失败，针对历史图边/章节关系与CLI全局截止点入口。
- 原始报告SHA256 `b941c70f013fe8d76c2c966712244e5e9359e896482c7adfaea48152ea1eef72`。
- [二次红色 artifact #12128161845](https://github.com/66tyu55/WriterForge/actions/runs/39105648147/artifacts/12128161845)；ZIP SHA256 `c759f161d755c2f8f28250394f6d7eac9a59a0e49dda80037b47ebc535edca87`。

## 3. 根据反例修复底层，而非修改原失败报告

1. **单一全局账本**：新增 `ledger_operations(global_seq,operation,ref)`。SQLite插入触发器把 `EVENT`、`SCENE`、`SUBJECT`、`DISCLOSURE`、`CLAIM`、`LINK` 六类登记至同一递增时钟。仍保留既有 `temporal_claims.recorded_seq` 及 `story_tick`，三者用途互不混淆。
2. **历史关联相同截止点**：`temporal_view(...,as_of_ledger_seq=...)` 与 `temporal_claim_page(...,as_of_ledger_seq=...)` 不仅限制旧主张，也过滤截至该时点尚未登记的章节/人物绑定，保留真实历史冲突与状态。迟来的受信披露不能倒填并授权旧快照。
3. **游标冻结完整关系范围**：分页从 V58 v1游标升级至 v2，增加全局ledger快照字段，继续使用每个 SQLite 账本的 HMAC 保护，固定请求身份、时间、页面大小和序号。旧游标版本拒绝复用，调用方必须重新发起第一页，不能静默解释为新版本。
4. **图关系按登记时间重建**：`graph_neighbors(...,as_of_ledger_seq=...)` 不得回放未来才录入的关系边、证据事件或作品连接；`POTENTIAL_CAUSE` 一直标记为 **未验证**。
5. **命令行真实打通**：`fact-ledger-head` 返回当前统一时钟；`fact-view`、`fact-page`、`fact-graph` 接受 `--ledger-seq`，可完整指定历史快照，V59新增CLI端到端合成测试。
6. **首次迁移必须整体事务**：测试进一步发现如果先提交旧库回填、再安装触发器，两个连接可能钻过无触发器的窗口。调整为 `BEGIN IMMEDIATE` + 同一写事务创建登记表、回填、安装触发器；严禁在事务内使用可能隐式提交的 `executescript()`。任何异常完整ROLLBACK，不得留下未登记的主张。并发writer在安装时由SQLite写锁阻止。
7. **不可伪造缺失的旧登记顺序**：升级既有V58库时只做可检验的当前数据回填，`ledger_bootstrap` 标记 `legacy_unordered` 与迁移水位。任何需要重建迁移前跨表排序的历史关系快照明确报 `FACT_GLOBAL_LEGACY_ORDER_UNPROVABLE`，绝不把任意排序说成真实事件顺序；迁移后新的全局序号可正常使用。

代码全部为 WF 原有 Python + SQLite 逻辑，未安装新增ORM/事件框架，也没有复制外部源码。

## 4. GitHub 真实回归和哈希（V59最终现场）

[Actions #39105993899](https://github.com/66tyu55/WriterForge/actions/runs/39105993899)：CI `success`。

- V54 原12/12，V55 本分支9/9，V57 12/12，V58 12/12，V59 新增13/13。**合计58/58**，都是临时 SQLite 的合成结构化事实测试，不是文学分数。
- 额外新测试证明：事实提交失败时其时钟记录也原子回滚；首次升级期间的第二写连接被写锁阻止，无法插入未登记行；全局时钟重启恢复与双连接单调顺序成立。
- 最终JSON `v59_relation_regression_receipt.json` SHA256：`0b395c14bf9b997cc637b10cded46338db037ddf9915b2522943afdd63653cc4`。
- [最终 artifact #12127897818](https://github.com/66tyu55/WriterForge/actions/runs/39105993899/artifacts/12127897818) ZIP SHA256：`f593f1322770b32d1c7d6fb3575ef1e4f573ea8a42ace9311ddb4e90d0617c43`。
- `writerforge/fact_journal.py` SHA256：`116b563c0d182604a79bfac2c89ba2bb8d72355dd30d1d82c044f1b96c63837f`。
- `writerforge/cli.py` SHA256：`45611d7a19403d82ebaef6c5976b1e226709ac09faa8ba5746f3464217abf7e1`。
- `tests/test_v59_global_ledger_clock.py` SHA256：`48973d23db2b498f5892f3cdc2799d8366f9d4c07e60cb513bd145888e94129d`。
- `scripts/audit_v59_global_clock.py` SHA256：`a57dabc1f225dca4a55d585de5f30a15326ec962a44ca026c1ccd0b1c812e9f7`。

## 5. 明确还未解决，不能宣布 WF 整体完成

- HMAC/SQLite/SHA依然不能证明文学真值、真实角色身份、人物动机、伏笔是否确为回收；错误签名者也能签署错误断言。V49 `THIRD_STRIKE_FAILED` 和 `NO_PROMOTION` 原封不动。
- 全局登记顺序只证明**本地数据库记录的提交序**，不等于作品内部故事时间或公开文献证据真实性。默认程序尚未建立可信出版原文/独立外部签名体系。
- 初次升级前**必须停止旧V58及更早版本写进程**再部署V59；旧客户端没有V59触发器及历史契约，不能保证热迁移时跨版本写入的完整性。此限制要在发布/迁移检查中作为阻断条件。
- 老 `as_of_recorded_seq` 接口仍留作兼容，但推荐跨章历史依赖统一的 `--ledger-seq`；迁移前快照没有可考证的统一登记次序，宁可拒绝。
- 本地原始SQLite持有者能改变数据或密钥；防攻击边界是数据库API权限之外的外部调用者。跨节点同步、多设备时钟、备份恢复、全库密钥轮转、磁盘容量上限仍未覆盖。
- 8192条完整历史状态扫描预算保留；超过它不会输出伪完整状态，仍只能由分页枚举结构化事实。新增 `ledger_operations` 会带来磁盘写入成本，长期存储体积/索引清理须另做性能对照。
- 本阶段应继续**证据可信来源、冷库/长期迁移、分页快照一致性/并发压力和来源鉴权**，不是重复付费文学训练。

## 6. 今后固定的源码对照规则

每新增/改动一项核心机制，先在GitHub找2–3个独立成熟实现，读取**实际代码**、记录路径和版本；产出“解决的约束/未解决的风险/为何不复制”的矩阵；写独立失败测试并冻结红色运行SHA；只更改自己的最小底层代码；跑老回归+新反例+并发/迁移负面测试；冻结绿色SHA；最后更新此交接，不擅自取消文学失败结论。
