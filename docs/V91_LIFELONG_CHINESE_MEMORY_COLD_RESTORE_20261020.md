# WriterForge V91｜长期经验版本迁移、双SQLite冷恢复与真实R2独立验收

日期：2026-10-20。开发隔离分支：`v91-lifelong-memory-cold-restore`。

> **原始需求**：WF必须长期成长，不能只记几条文学手法，之后重启/升级变成乱码、遗忘、乱用经验。此版落实 ADR-001 的部分工程基础；**绝不宣称整个WF长期大脑、真正文学理解或写作能力已完成。**

## 1. 已在源码中落实的两类协议

### 1.1 旧V80中文经验 → V91完整版本化对象

- `writerforge/v91_experience_migration.py` 对旧 `wf.learn.experience.v80` R2对象逐字节校验原始CAS SHA及严格UTF-8/JSON。
- **保留完整经验字段的中文原值**：`observed_weakness`、`next_strategy`、`open_question`、`confidence_limit`，不是只保存标签、关键词、摘要或最终SHA。每字段完整回编、同一对象包含章节/源SHA/前版经验SHA/分析SHA/原始CAS、格式版本和独立验证状态。
- JSON重复键、未知schema、乱码/替换符、丢字段、字符串篡改、错误CAS SHA拒绝。原始V80字节不修改，改动必须生成新内容寻址版本；老版未经独立文学审核，一律`UNVERIFIED_LEGACY`，不得进入正式WRITE或自动晋级。
- `writerforge/v91_private_cas_manifest.py` 固定旧V82 batch/journal/experience三SHA与新的V91完整经验CAS，同时明确`local_sqlite_memory_snapshot_included=false`、`fact_journal_migrated_to_cloud=false`、`literary_skill_approved=false`，杜绝把部分迁移伪装成全部迁移。

### 1.2 复用现有WriterForgeDB + FactJournal的本地完整冷恢复

- `writerforge/v91_lifelong_checkpoint.py` 不建第二张记忆图；使用现有两个SQLite连接的在线备份API，支持WAL安全快照。每份验证完整文件SHA/字节、`PRAGMA quick_check`、外键检查、数据库schema SHA以及关键知识/经验/失败表的**流式记录数量和逻辑摘要**。
- 本地不可变目录：先备份和审计SQLite，最后写小manifest并发布 `CURRENT` 指针。中途断电模拟/中断不覆盖旧指针；冷恢复必须重新检验字节和关键表逻辑，不允许覆盖已有工作目录。
- 临时缓存/索引不是永久记忆；超限或损坏失败关闭。任何读失败/未知格式/乱码不得自动`errors=replace`或通过模型猜测恢复；不静默丢弃已存在的负例。
- 这是**受调用方停写管理**的两个独立SQLite的本地恢复原语，不具备跨R2＋SQLite的原子提交保证；测试阶段数据库备份位于一次性容器/测试目录，**没有作为完整长期关系网络上传R2**。

## 2. 真实测试轨迹（红色不删）

- 首轮全仓Railway `1362890c-a1db-4aa2-b34e-65d4556fe482`：962项，1项断言失败，0运行错误，4跳过。原因是乱码测试期待后面的反射字段错误码，真实程序更早就在严格UTF8/JSON入口拒绝了替换字符。只改测试预期，没有放宽生产校验。
- 更正测试后 `800cad4e-d472-4a75-918f-f0e470b08000`：**962项全绿，0失败/0错误/4跳过**，模型0/R2网络读写0。
- 增加R2新清单结构/未知版本/假晋级拒绝测试后 `090efa0c-dee5-4c4b-ae65-3d99799834b2`：**965项全绿，0失败/0错误/4跳过**，仍为零付费与零真实R2读写。
- 合成真实SQLite行为回归：先使V61受控经验`SELECT`，签名撤销后`SKIP/EXPERIENCE_REVOKED`，双DB快照再恢复到新工作目录，重新打开SQLite后下一次仍`SKIP`；旧SELECT历史仍可查，但不能作为当前授权。跨章人物身份和时间账本快照恢复后仍可查询。另测中断前保留旧`CURRENT`、未知版本、数据库字节被破坏、无效Unicode、复制目标禁止覆盖与运行时LEARN/WRITE互斥。**这只证明合成工程行为，不证明文学语义已经成长。**

## 3. 真实V82第15章中文经验无模型迁移与云端持久化

真实只读预检：Railway `ebb47426-2aa0-4be3-9e81-7695d3d3f6ed`，`WF91_REAL_V82_CH15_CHINESE_EXPERIENCE_MIGRATED_IN_MEMORY`，退出0，验证旧batch/journal/源SHA、原经验字节SHA，所有4个中文完整字段迁移后逐字节保持。只读，不写R2。

真实R2不可变存储：Railway `9011e050-1e0f-4043-bbb8-133809977a17`，`WF91_VERSIONED_PRIVATE_CAS_EXPERIENCE_MANIFEST_SAVED`，退出0。一次性追加**恰好两个新的不可变私有CAS对象**：

| 对象 | 永久恢复SHA256 |
|---|---|
| 完整V91中文经验对象 | `79dbfe144356d01bcd89bd237410925d838f98b1efe91e0aeab0edc3f93add4b` |
| 版本化R2清单 | `5a8b3b78f8b68741d794f618d2e701ac653397dd2a1e74822bba63cd09c9ee0f` |

迁移关系摘要 `afdc4557b9e7f143d515382491e486a2e57662370c3d378476a673d0083105f6`。

原始V82第15章经验CAS `ddbf86e87e3bf44900b4e5e4d8ffc2de99c9ed5d3c5aec98a69bfd8eb7cf2fe7`、旧journal `3da56cc46115548c5198a65cb6124e3c03d9bdfdb1f0460950177735a99d1cb2`、旧batch `d46ffec05927dfba3f2819089e76e79f720db2a2f3f6793b56965ac6413c177f`均未改写。

真实**独立新进程**冷读回：Railway `481dbe69-ca0f-4742-b1a5-242ee727a3e7`，仅带R2 Reader，移除DeepSeek和Writer凭证，`WF91_REAL_CH15_EXPERIENCE_CLOUD_COLD_RESTORE_VERIFIED` / `WF91_INDEPENDENT_COLD_R2_RESTORE_EXIT=0`。重新独立获取旧V82来源链及两个新对象、重新迁移中文经验并比较全部字节和四字段，manifest来源与新CAS全部一致。模型调用0、R2写入0，私有原句和经验正文没有输出到GitHub或聊天。

**已证明**：旧真实第15章中文经验完整保存、新版本完整性、有来源身份的R2私有持久对象、跨Railway进程无模型独立恢复。**没证明**：所有第1–15章经验全量迁移、永久云端SQLite知识图恢复、人物/因果独立文学真实性、跨多年/模型供应商的质量改善。

## 4. 当前仍未跨越的P0边界

1. **双账本持久化**：真实用户`WriterForgeDB`与`FactJournal`生产快照尚未永久发布R2（此次本地版本/行为测试完全是合成数据库）；两DB与R2没有跨存储原子性，生产需要标记受控停写窗口、manifest-last与一致性补偿、跨进程复核，不可宣称永久关系大脑建成。
2. **全部经验链**：这次只为V82第15章创建一个新版本；其前14章依旧按旧V82 CAS引用链可读，没有变成V91对象。下一步应做按SHA旧对象分段增量迁移、断点恢复与重复内容地址拒绝，不能每次都重训练原文。
3. **语义保持**：机械验证能保证文字、schema和策略选择不乱，但不能证明模型真的理解人物、伏笔、因果或者1年后的文字更好。正式晋级仍要独立可信文学盲评、负例检测与降级阻断；旧V49 `THIRD_STRIKE_FAILED`、第二文学窗口 `LOCKED`保持。
4. **性能**：本地双DB快照有大小/内存/行数上限，尚未对真实多年大体量训练库做压测；容量超过上限时主动停止而非静默漏掉后面的故事与经验。
5. **存储权限**：此次使用旧有的R2 Reader/Writer权限和`deepseek-flash`从未调用；没有新增密钥或迁移原著至公开GitHub。V91不是已自动开启的正式LEARN/WRITE生产服务。
6. **其他隐含依赖**：`memory.py`仅为上下文排序，不是长期知识保存。不能因为新V91有manifest就让旧memory.py无条件调用、仿佛真实文学生长已经自动接通。

## 5. 下一步优先路线

`增量搬迁已有经验链（不训练） → 生产两DB完整版本化快照与R2私有冷恢复 → 撤销/失败/人物身份跨进程行为回放 → 旧新版本兼容与乱码故障注入 → 长时容量压测 → 真实新作品独立文学盲评`。

**V91只是ADR-001长期记忆工程的第一个可复盘阶段，任何新增训练前必须先继续修复持久底层。**
