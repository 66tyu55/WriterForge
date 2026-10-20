# WriterForge V94｜合成事实与经验撤销的R2事件先写后提交、独立冷重放

日期：2026-10-20；开发隔离分支 `v94-durable-learn-events-commit-replay`。贯彻 [ADR-001｜长期记忆完整性架构](ADR_001_WF_LIFELONG_MEMORY_DURABILITY_20261020.md)：不仅恢复字节，还必须恢复时序、人物知识、失效经验和下一次真实软件选择。**V94是受限合成事件流集成验证，不是实际文学认知进入正式生产LEARN。**

## 1. 继承的真实云端基础

- V92：15份旧+15份新完整中文经验CAS与manifest经独立R2 Reader验证，最终 `bd905ae9e812fb5283f24ed7fec3bc35cf0febde7b6405476c455bba468f84db`。
- V93：实际R2仅存**合成**双SQLite图的不可变CAS（WriterForgeDB+FactJournal），经新Reader冷恢复21张关键表并重放撤销，基础manifest `a42ada69d6d3b4d6ed90664f4b6c5607f5e0849ed1a4d178688b8d45f10b1d25`。原生产人物关系图未被定位到可信持久来源，绝不能用这个合成快照代替真实文学记忆。
- Railway最终安全待命上一版本 `6d8472d8-95e8-459e-b6db-c3325a10fa21` 的实际日志为 `WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`，本次模型0/R2读写0；V94启动时核实为 `restartPolicyType=NEVER`。

## 2. 新增代码与实际事务路径

`writerforge/v94_synthetic_event_commit.py` 明确限定七条常量合成事件，**不接受任意模型声明的事实**，不使用真实用户或小说。重建V93云端快照后，通过既有WriterForgeDB、FactJournal、RuntimeEngine、ExperienceDecisionBridge逐项执行：

1. STAGE：创建新的合成实验经验 `lesson_v94`，引用V93的合成来源；非文学真实性证明。
2. APPROVE：使用公开测试密钥签出固定合成实验许可，仅测试现有签名校验。
3. BEFORE_REVOKE_DECISION：旧V93经验已有撤销，保持 `SKIP`；新增合成经验按允许条件 `SELECT`，保存原始决策SHA。
4. REVOKE：合成签名撤销新实验经验，永久保留既有候选和审批历史。
5. AFTER_REVOKE_DECISION：新、旧两个候选均 `SKIP`，写作指导为空；旧第3步SELECT之后不能再当作当前有效授权。
6. FACT_EVENT：既有合成角色的一个已知事实有了另一条冲突观察，仅作为合成事件，不能证明人物真正知道或不知道什么。
7. FACT_SUPERSEDE：新增不可变双时轴时态断言，指向第6步的合成证据并supersede旧断言。原global ledger时点6仍为`KNOWN`，最新时点8按FactJournal真实合同返回 `CONFLICT_UNRESOLVED`，从未出现的未来事实仍为`UNRECORDED`。

每条CAS事件记录固定版本、链ID、前一事件SHA、序号、操作枚举、已复算的预期结果SHA、基础云端快照SHA；源代码只允许固定测试夹具。事件预提交时先用**全新R2冷恢复的临时本地SQLite**完整执行、逐结果算SHA，写端再独立运行一遍检查全部事件和最终状态，**在发布任何新CAS之前拒绝不一致**；确认后逐条R2 CAS上传和立即读回，最后发布含全部7个事件SHA/预期最终状态SHA的不可变提交manifest（manifest-last）。读端只认预先固定且真实存在的commit SHA，孤立已上传但没有manifest的事件不能升级成持久可用记忆。

`tests/test_v94_synthetic_event_commit.py` 覆盖不同Reader冷重演、事件未提交、分块缺失/篡改、重排/重复、伪造文学审核、旧撤销许可拒绝、读者写权限、幂等重试、伪造未来事件与全部SHA核验；`wf_railway_v94_focused_tests.py`与`wf_railway_v85_full_offline_regressions.py`禁止真实模型及外部R2请求，测试过程中没有新增收费。

## 3. 真实红色记录与绿灯（不能抹除）

- Railway `78c32276-7885-4f3a-be8d-0537b4c78129`：11项/11 ERROR。根因第一版把FactJournal的`DISPUTED`误期待为返回`DISPUTED`，但真正接口会归纳为`CONFLICT_UNRESOLVED`。修复新协议与合成预期，旧FactJournal生产合同不动。
- Railway `c9791655-3bbe-48cd-bb9d-308546e28f8d`：重复的合成准备阶段仍失败，定位到撤销旧SELECT校验未进入WRITE模式；应由V94显式进入WRITE再执行 `validate_live_decision`，不能绕过现有LEARN/WRITE权限。
- Railway `f006d099-8e96-4440-a910-ea9a9d593860`：11项中10通过、1断言失败，只是另一个读者测试仍期待错误的`DISPUTED`字样。更正夹具，不降低老系统冲突保护。
- Railway `c94b2e3b-0a28-4774-89bf-e185e40eae4d`：**V94专项11项，0失败0错误**。
- Railway `696cdccc-67de-401c-8b97-92ec59e89e3d`：全仓离线 **993项执行、0失败、0错误、4跳过**，真实模型0、真实R2读写0，V49失败状态保留。

## 4. 真实Cloudflare R2 CAS事件持久化与独立冷重演

- 写入端 Railway `7e10b22d-39e5-4970-a73c-cbfe0089880e`（源码固定commit `71abec5e10649378c3a13570029e6d4eea876a75`）：`WF94_SEVEN_SYNTHETIC_R2_EVENTS_AND_COMMIT_SAVED` / `WF94_R2_SYNTHETIC_EVENT_COMMIT_EXIT=0`，**新建7条事件CAS+1个manifest**，每份写后读回，上传前完整重演，全程DeepSeek0；没有动原V92、V93对象、原著、15章训练笔记或生产人物图。
- **真正独立Reader** Railway `769d84d5-7a6d-475b-b5ad-25cf8669fa31`（新源码commit `4e8c08d520ceea6455f29a1205825b89e75b7d12`）：`WF94_INDEPENDENT_R2_EVENT_AND_BEHAVIOR_REPLAY_VERIFIED` / `WF94_COLD_R2_EVENT_REPLAY_EXIT=0`。R2 Reader权限，进程启动时移除DeepSeek/R2 Writer凭证；恢复旧V93合成SQLite、重读并校验7条SHA、重新执行受控事件，重新检查所有预期操作结果摘要与最终状态摘要。旧`KNOWN`（global seq6）、新`CONFLICT_UNRESOLVED`（seq8）、未知未来`UNRECORDED`、合成SELECT→SKIP均保持。模型0、R2写0。
- 真实R2 V94最终提交清单CAS：**`5b33b3f07131eb1abdf7298b68a934daf2b496a084108ccfd1a20d673ce352b7`**
- 独立重放最终状态SHA：`383aa34044919054e046801ac69e183347f2929cc311ab3d57376b654c778f65`
- 独立各事件结果SHA集合摘要：`55721117a9caf0e83283a7f8211edcd09f47a24f0b4a4ea4f06fedce622322d5`
- 合成签名使用**公开测试密钥**，只能验证现有程序接口的协议，不构成人类文学审核，也不证明模型真正理解因果。

## 5. 不可虚报的长期架构边界

1. **这次确实证明**：一条受限合成事实/实验操作的R2事件流，可以先提交事件、最后发布manifest，由另一全新进程完整重建SQLite，再次执行人物时间和撤销后写作策略选择。无manifest不承认事件提交；原快照与旧知识不被覆盖。
2. **没有证明**：真实生产LEARN持续写入接口已上线、原实际人物关系来源存在且真实、V89→V85→V86的可信语义审评全链已自动持续入R2。V94操作完全是七个写死的合成枚举，生产调用必须默认拒绝外部模型事实。
3. **没有证明**：跨云端多写者线性化/互斥租约与可变当前HEAD安全切换、R2+SQLite真正分布式事务、网络分区下自动补偿、敏感作者/人物数据的独立密钥加密与授权、长期垃圾清理/容量与数年后的文学效用。在这些P0未验收前，不允许用V94合成许可代表真实WRITE生产授权。
4. **文学状况不变**：V49 `THIRD_STRIKE_FAILED`、第二文学窗口 `LOCKED`；V88四个真实回答精确锚点0/4通过的历史事实不改；WF正式已读作品仍是V82前15章，第16章未重新付费训练。V92所有旧15章原始和V91新版中文经验CAS完整保留。

## 6. 下一阶段正确方向

V95只在取得可信生产事实录入源和独立审核权后，设计基于R2事件的**单一权威提交头/多写者安全控制/生产恢复入口**；绝不由临时Railway SQLite或未审的WF模型原话自发制造`KNOWN`。在此之前先评估V93/V94代码的真实生产隔离与索引权限，并持续做有界故障注入、旧版本回放与WRITE前恢复状态检查。若生产数据库不存在，应首先实现来源可信的**全新事实进入路径**，不是伪造过去15章学过的人物记忆。

## 7. V94 最终真实运维回执

V94事件写入、独立R2 Reader重放、GitHub文档冻结后，最后Railway部署 `60f2569a-52bc-4fde-b3f2-0acaf1e34611` 已 `SUCCESS`，实际启动命令 `python -u wf_railway_v82_safe_idle.py`，`restartPolicyType=NEVER`，当前部署源码commit `174a00545993390cbdd2ab22b8d4b91dcd097349`；容器日志 `WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`、本次模型0/R2读取0/R2写入0、`automatic_paid_next_batch_enabled=false`。没有自动重复七事件写入，也没有启动第16章。后续仅文档更新不等于重新部署收费代码。
