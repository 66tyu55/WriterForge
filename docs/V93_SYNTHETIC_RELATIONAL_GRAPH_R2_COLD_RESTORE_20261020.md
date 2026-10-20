# WriterForge V93｜人物关系与负例状态双数据库云端恢复工程实测

日期：2026-10-20；隔离开发分支 `v93-durable-relational-state-cold-restore`。依据 [ADR-001 终身学习与完整记忆约束](ADR_001_WF_LIFELONG_MEMORY_DURABILITY_20261020.md)。本报告是**真实 R2 数据块上传 + 独立冷恢复的工程证据**，不是 WF 历史人物关系数据迁移、文学理解验证或训练升级。

## 一、为何不能直接“把生产人物记忆迁走”

经 Railway `describe_environment` 和服务状态核实，当前项目只有 `wf-python-r2` 服务，无挂载 Railway 持久化 Volume，也无 Railway 项目存储桶。服务环境中已有的 `WF_API_TOKEN`（R2只读）、`WF_INDEX_UPLOAD_TOKEN`（R2既有不可变索引写权限）、`DEEPSEEK_API_KEY`（本轮未使用）完整保持。**当前没有定位到可以认证为真实历史生产 `WriterForgeDB` 和 `FactJournal` 的持久数据库文件或原始来源清单**。这不证明其他平台永不存在相关旧数据，但明确禁止从临时Railway容器、V92文学经验卡或测试夹具伪造正式人物事实图。

V92旧15章经验链云端 CAS清单 `bd905ae9e812fb5283f24ed7fec3bc35cf0febde7b6405476c455bba468f84db` 已真实独立验收，仍是原15章经验的权威来源；本次绝不覆盖或重新调用模型。

## 二、V93新增底层代码

### 1. `writerforge/v93_synthetic_graph_cloud_checkpoint.py`

- 重用现有 `WriterForgeDB`、`FactJournal` 和V91 SQLite 在线备份/不可变 `CURRENT` 指针、数据库完整文件 SHA、schema hash、21张关键表的逻辑摘要及外键检查。
- 仅接受**严格合成来源夹具**，包括固定的 `test://` 虚构作品源、唯一合成短句、1条候选实验、签名测试审批、签名测试撤销、两次历史决策、人物与故事双时轴记录；任何多余用户来源或预料外数据库表数据都拒绝发布。
- 两个SQLite分别采用有界zlib压缩、128KiB CAS分块、各块写后读回SHA、压缩/原始长度及SHA核对；所有块成功以后**最后**写不可变manifest。读者需要固定manifest SHA并从R2重新下载，解压强制长度上限，重建V91本地 `CURRENT` 并执行原有 `verify_checkpoint`。
- 完整清单明示 `snapshot_kind=SYNTHETIC_TEST_ONLY`、`production_graph_migrated=false`、`literary_semantics_verified=false`、`next_training_unlocked=false`。未把测试审查用的公开HMAC当成可信独立文学审核身份。
- **生产R2上传接口被源范围校验挡住**；V93不允许将真实用户小说片段或未知生产SQLite混入此合成通道。真实生产部署仍需独立数据来源证明、加密/权限与密钥轮换审计、跨R2/SQLite一致性协议。

### 2. `writerforge/v93_synthetic_graph_fixture.py`

使用原有实际SQLite类生成完全虚构测试数据库：已知知识 `KNOWN`，未记录的未来知识 `UNRECORDED`，一个实验曾经 `SELECT`，之后签名撤销使下一次 `SKIP`，旧SELECT收据保留但不可当作当前授权。签名key公开且仅用于程序回归；**无真实读者、真实文学审核者或真实小说人物知识被编造**。

### 3. 运行与反例脚本

- `tests/test_v93_synthetic_graph_cloud_checkpoint.py` 检查两数据库恢复、两次独立本地读回、重复幂等、块丢失和损坏、压缩膨胀、虚假晋级字段、额外用户数据、只读写入拦截及错误清单指针。
- `wf_railway_v93_focused_offline_tests.py` 和既有 `wf_railway_v85_full_offline_regressions.py` 进行禁外网的合成回归。
- `wf_railway_v93_publish_synthetic_graph.py` 实际上传**合成数据库**至用户已有私有R2的实验性不可变CAS池，没建新存储Bucket/Volume、没要求第四份凭证。
- `wf_railway_v93_independent_synthetic_cold_reader.py` 用另一个完全隔离的读权限进程在R2重构数据库，重新执行SELECT/SKIP和时序查询，并与该进程单独创建的标准合成夹具做摘要对照。

## 三、真实失败与红绿回归（不删除失败）

1. **首轮全仓红色**：Railway `091fd4ae-2572-447c-837b-6457643223a7`：982项执行，10个新用例在共同夹具初始化时失败；根因是新接口误认为现有 `experience_decisions` 字段名 `decision_json`，实际结构为 `plan_json`。已对照现有DB源码修正；没有更改旧数据库表。
2. **专项第二轮红色**：Railway `5d144ca0-c47f-4d49-9b51-139dc4db8038`：10项执行、2错误；V93 cloud读回重建 `CURRENT` 时误用整个V91 manifest JSON blob的SHA，而V91规则引用其**内部manifest收据SHA**。受信旧V91恢复器正确拒绝错指针。已修复，保留两个SHA各自身份。
3. **专项绿色**：Railway `d0071435-5d40-4c2a-a422-86177e84ff80`：**10/10通过**，0错误。
4. **最终离线全仓绿色**：Railway `cc958490-5792-4aeb-8f71-27c0515aeb4f`：**982项测试，0失败、0错误、4跳过**，模型0、真实R2读写0。
5. **真实合成R2写入端**：Railway `6ed77edc-3e4b-4ecd-8b3d-f853f6ca1d57`：`WF93_SYNTHETIC_DUAL_SQLITE_R2_MANIFEST_LAST_VERIFIED` / exit0，两个新的有界压缩CAS块 `created=true`、manifest `created=true`，源SQLite完整性/行为在同进程经R2读回成功。原V92经验链没有改动，DeepSeek调用0。
6. **真实全新R2 Reader端**：Railway `8cc1e602-1064-4709-a290-50b0929e0b36`：`WF93_INDEPENDENT_CLOUD_SYNTHETIC_GRAPH_AND_BEHAVIOR_VERIFIED` / exit0，只带原有R2 Reader凭证；独立恢复SQLite文件2份、校验关键表21张。跨章角色 `bridge_light` 知情仍 `KNOWN`、未知事实仍 `UNRECORDED`，恢复前旧 `SELECT` 收据SHA `77885887cf29b6ab49c58e868930f2ceb503d960d208ea63ef7b052bac65f8dc` 保留，但新决策仍 `SKIP`、撤销后收据SHA `b2d7294d15068443ff65cab81887dd3fcb74585a2ac22d911e73091a97b2a8cb` 保留，global ledger序列为6。独立进程重新创建另一套相同**合成**知识夹具，复算行为与旧SHA相同。DeepSeek0、R2写0。

**V93合成关系数据库云端manifest CAS：** `a42ada69d6d3b4d6ed90664f4b6c5607f5e0849ed1a4d178688b8d45f10b1d25`。

## 四、精确区分“已完成”与“尚未完成”

**真正完成的工程能力：** 已有WriterForgeDB+FactJournal结构的双SQLite镜像→用户私有R2不可变CAS→新进程只读恢复→逐字节和逻辑校验→恢复旧经验撤销/人物时间状态，已有真实网络传输和独立进程回执；没有重训、没有丢弃旧V92经验。

**未完成的生产条件：**
- 实际生产人物关系/因果/负例SQLite的持久来源，尚未确认/没有取得真实归档；合成云端manifest绝不能成为正式真实人物记忆。
- 尚没有WF真实LEARN流程把来源校验合格的人物事实与负例状态以可信事件链**持续写入**私有R2并驱动新数据库恢复；仅有批次文学经验CAS。必须先做写入时同步与故障隔离，再扩大训练。
- 尚未完成真实跨SQLite/R2强一致提交协议、多写者同步、网络分区补偿、长期分片归档、生产敏感文本加密策略和真实长期负载压测。
- 文学真值没有独立考官，V88四臂0/4严格证据合同历史失败仍有效；V49`THIRD_STRIKE_FAILED`，第二文学窗口`LOCKED`，第16章未重新训练。测试用公开签名不能证明真实评论独立性。

## 五、下一轮唯一正确方向

V94优先建立**真实事件写入边界**：先将经过可信来源核验的FactJournal/经验撤销写入与R2 CAS提交绑定到同一个受控操作协议，采用原始事件→CAS即时读回→manifest-last，再由独立Reader冷启动重建后重新验证时序和行为；失败时保留上一个完整快照并拒绝继续WRITE。不能让WF自己任意声明“人物知道”或让本地SQLite当永久真实知识库。

坚持ADR-001的固定晋级顺序：`持久 → 恢复 → 关系正确 → 行为可重放 → 独立文学语义验证`。本V93不提供任何自动文学晋级或继续收费训练许可。
