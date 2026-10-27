# WriterForge 0.BC｜第一个宿主：真实工作源 → 有限认知提炼 → 可恢复 SHADOW 胶囊

日期：2026-10-27。**这次是代码和真实原件回放结果，不是声称已从真实 DeepSeek/GLM 形成有质量收益的新认知习惯。** 开发分支仅限 refactor-unified-scene-delivery-audit。

## 1. 为什么做 0.BC

此前 0.BA/0.BB 已有技能权限、外部签名、竞争、污染隔离、公钥发行和 Scheduler 闸门，但那些措施主要在**保护已存在的技能**。用户真正要的是“像寄生虫第一次汲取宿主资源，把经过证据支持的行为过程保存下来、下次不从卵开始”，不是再包一层审稿器。

0.AY 真实经历：在**同一个 GitHub Actions Python WF 宿主**中，两家模型服务总共尝试四次、获得三份实际续写，第四次 GLM habit 是 HTTP 429、没有有效正文。模型回包中的 chosen_step 是角色文学选择，**不能冒称模型已提出元认知 Skill 补丁**。当时也没有独立读者能证明哪份写得更好。

## 2. 本次原有 owner 中完成的功能

### 真实宿主观察与持久保存（writerforge/evolution.py + db.py）

- 新增 HostNutrientObservation / FirstHostNutrientLoop，**调用者须提交真实 source/request/provider wire/原作者 prose 的原字节**；校验模型名、finish_reason、原 response 中真实逐字小说正文与外部可信离线核验者签名。伪造 SHA、伪造额外 429 回包、同一个 observation_id 重复输入一律拒绝。
- SQLite 原有 WriterForgeDB 中新增 host_nutrient_observations、host_nutrient_attempts、host_nutrient_candidates。观察事件使用不可 UPDATE/DELETE 的 append-only 触发器；**只存任务/宿主、SHA256、真实供应商结果状态及来源签名，不保存故事前文、供应商原始回包、隐藏推理或密钥**。候选存放的是不包含原著的简短认知程序字节。观察每个 scope 最多 128 条、宿主提议尝试最多 32 次，不无限积累内存/数据库。
- 本次真实 [0.AZ 原件回放 #40454231888](https://github.com/66tyu55/WriterForge/actions/runs/40454231888) 将原有 artifact 的三份真实 provider wire 和第四次**缺失正文**一起源锁核验后，写入新的 **SHA-only SQLite**，作为 Actions artifact 中 WF0BC_FIRST_HOST_OBSERVATIONS_SHA_ONLY.sqlite 保存。输出 WF0BC_FIRST_HOST_NUTRIENT_INGEST_STATUS.json，结果：4 条已验证观察、3 份回包、1 条 HTTP 429、0 次新模型请求、0 个真实新认知候选。这个 HMAC 是**当次离线法证核验者重新出具的校验回执**，不是历史提供商自己签署的声明。
- 真实历史状态保持 DORMANT_HOST_RESOURCE / NOT_TESTED_INCOMPLETE。原 observe-before-next-choice v1 SHA256 42cad98118dea662cea472f708ef1de22f4bb139da3210b1f5c3c1f9ac12664d，仍 SHADOW。

### 由宿主受控提出新的认知候选（同一 evolution.py，不是另一模型）

- acquire_once 不会自主寻找模型密钥，不从原已付费回复中擅自生成下一次请求。先要求**同一个宿主、同一任务、相同来源的 control 和 habit 真实有效成对观察**；若本次实验记录任何 HTTP 429，直接 DORMANT，不会偷用别家的成功回包去补原缺失。
- 只有宿主**显式注入** OptionalHostResourceLease 中的 nutrient_acquisition 调用次数，且交付当前任务与两份原稿的完整可信原字节，才可调用一次授权的 host_call。输入来源 SHA 重新核对；若只有 SHA 没有真实前文和两份续写，进入 DORMANT_SOURCE_NOT_DELIVERED，**不得假装认知学习**。原文窗口只在调用时临时提供，三块内容均标记 untrusted data；不写入迁移胶囊。
- 实际宿主模型应输出严格的 wf.host-nutrient-proposal.v1 JSON，包括哪条现有认知步骤需要怎么改、什么反例可以证伪及真实源 observation_ids。WF 只是据此对现有 immutable v1 的 procedure/falsifiers 生成有限的 **SHADOW 候选**，交由原 PortableHabitCandidatePool.propose 对受保护字段再做审查，存储 SHA、origin、candidate bytes。**文学正文、删除和人物选择继续由创作模型自己决定。**
- callback 出现结构化 HTTP 429，即使模型不返回任何习惯建议，也把本次宿主调用记成已经耗费且 DORMANT；禁止自动重试。无效 JSON、小说正文冒充元提议、自称晋级、超出范围和已用过的同一宿主任务也只能停下。
- 首次合成测试用“宿主确实给了新的步骤与可证伪条件”模拟源数据，真实持久化 SHADOW 候选并在新 DB 实例中按 SHA 恢复；**这证明流程可执行，不证明历史 DeepSeek 真实提出过这个建议。**
- 实际新候选的两个字段还需通过与真实 source/control/habit 的逐字最长片段对比；存在 18 字符及以上直接连续复用会被拒绝，避免把原著大段装进可迁移程序。此门槛**不能保证发现改写式泄漏、隐含敏感信息或提示注入**，在独立宿主带走前仍须独立审查。

### 真正作者调用点捕获（原 writerforge/writing_assist.py）

- AutonomousWriting.run 新增默认关闭的 host_nutrient_observer callback，**在已有一次 local_chat_completion 返回之后**发出应用层 request/response SHA、模型名与 completion token 上限预留字段；不新增推理请求，也不暴露原提示词/正文给观察器。观察器出错只记录失败数，不会触发生成重试/删除原作者候选。单章实际用两次合成模型回包验证，调用次数严格不变。
- **特别区别**：这个实时候选回执仅证明 WF 收到 application payload，明确标记 provider_wire_verified=False；它尚不能独立充当 FirstHostNutrientLoop 所要求的真实 provider wire。真正直播来源核验还需要当前宿主 adapter 自己提供可信原始 wire，不可把软件内部 hash 冒充实际供应商回包。该路径默认没有自动接入 Evolution 晋级，也不修改 NarrativeCore。

## 3. 实际 RED / GREEN 来源

| 阶段 | 真实结果 |
|---|---|
| 入口缺失 RED | [#40452250152](https://github.com/66tyu55/WriterForge/actions/runs/40452250152)，缺少 HostNutrientObservation |
| 元习惯提议 429 重试漏洞 | [#40452654017](https://github.com/66tyu55/WriterForge/actions/runs/40452654017)，观察后宿主提议失败的持久休眠未生效，已修复 |
| 真实原 0.AY 历史回放初次 GREEN | [#40452977371](https://github.com/66tyu55/WriterForge/actions/runs/40452977371)，4 原始观察、1 宿主 429、0 新 provider 调用 |
| 实时写作挂接 GREEN | [#40453419032](https://github.com/66tyu55/WriterForge/actions/runs/40453419032)，1,941 tests、6 skipped，零失败 |
| 只有哈希就允许学习 RED | [#40453792267](https://github.com/66tyu55/WriterForge/actions/runs/40453792267)，改为要求真实 source/control/habit 字节再验 |
| 从来源复制小说到 Skill 漏洞 RED | [#40454156077](https://github.com/66tyu55/WriterForge/actions/runs/40454156077)，模型可把小说片段塞进认知程序，现增加字面泄漏拒绝 |
| **最新完整 GREEN** | [#40454231887](https://github.com/66tyu55/WriterForge/actions/runs/40454231887)，**1,944 tests、6 skipped、0 failed**（0.BC 源码定向 14 + 实时写作 3） |
| **同基线来源 429 GREEN** | [#40454231888](https://github.com/66tyu55/WriterForge/actions/runs/40454231888)，同样 1,944 tests、源核验成功、零新增付费 |
| 其他旧工作流 CI 依赖修复 | [旧 0.AY offline GREEN #40453654314](https://github.com/66tyu55/WriterForge/actions/runs/40453654314)、[Unified full regression GREEN #40453659202](https://github.com/66tyu55/WriterForge/actions/runs/40453659202)：原工作流新增使用现存 [evidence] extra 安装 Ed25519 测试所需的 cryptography；不涉及小说改动 |

## 4. “寄生虫汲取营养”准确完成度

**已真正具备**：从真实既有宿主工作的逐字来源核验 → 无正文保存的观察记录 → 持久状态/429 正确停止 → *在宿主明确授权和实际源全文具备时* 单次请求宿主提出具体认知过程改动 → 安全 SHADOW staging → 下次可按 SHA 恢复候选。其代码与合成对抗测试通过。

**尚未发生**：在本轮利用真实宿主模型额外推理提出一个新有效候选；独立读者判断新认知习惯文学有效；可迁移版本获得人工正式 ACTIVE；第二个真实 Agent 应用独立运行并具有积极效果。尤其 **0.AY 的历史 GLM 429 必须休眠，不能自动补问**。

下一阶段真正第一宿主“吃到新的认知营养”应该在新的、明示有限预算内，通过实际能返还结构化 meta-proposal 的宿主调用，记录完整真实 provider wire + 文学对照与反例，再由独立评估者证伪或保留。不能从旧 DeepSeek 角色 chose_step 硬编一个已学会的技巧；未证则继续 SHADOW/DORMANT，不为了“继续进化”重复消耗宿主。

**不变边界**：只 refactor-unified-scene-delivery-audit；main/Railway/R2 私有原著/正式 Canon 不动；不得重跑旧有付费文学训练，不部署、不偷用凭证、不新增第二叙事记忆。唯一 NarrativeCore 与 V26/V98/V119 作者选择、逐段规划和修订事务全部保留。
