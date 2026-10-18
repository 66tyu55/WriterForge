# WriterForge V60｜只读全链路架构审计：从阅读到创作的真实断点（2026-10-18）

> **本文件不是文学训练、代码重构或版本晋级。** 审计基线为 `v59-global-ledger-clock-audit`，HEAD `3e589412acabaee95e9881923b0f3fa4cc7080c2`。V60在新分支 `v60-architecture-audit-readonly` 仅新增审计脚本、独立诊断测试、CI及文档，不修改 `writerforge/` 生产代码、R2、读者档案或既有证据。V49 `THIRD_STRIKE_FAILED`、`NO_PROMOTION` 未改变。

## 0. 审计范围与执行证据

- 核验的是**当前可访问的 GitHub 分支源码**，不等于用户私人R2中每项作品的真实训练深度，也不等于对语言模型内部推理的证明。
- `main` 在审计时为 `d6ca4b769faa2ef2b47da91fb623a417be49de17`；V57、V58、V59依次是待审的独立/叠加草稿分支，不能说这些已正式发布。
- 被检查的项目规模：V59树615个文件，`writerforge/*.py` 约94个核心Python模块，`tests/test_*.py` 103个既有测试模块，约90个工作流。V60新增审计工作流，不删原历史动作。
- [V60首次 Actions #39107632165](https://github.com/66tyu55/WriterForge/actions/runs/39107632165)：audit程序正确完成，审计对象标记 `ARCHITECTURE_GAPS_OPEN_NO_PROMOTION`；新增的3个诊断全部**复现当前缺口**；加上它们的完整仓库自动化回归 **642/642通过**。注意诊断绿色≠问题已修复。
- 独立回执 `v60_architecture_audit_receipt.json` SHA256 `8c9cd38c5bb33a01e1b94b4d473525a949deab857671597bef7a483f9959036b`；[V60机器证据 Artifact #12129525377](https://github.com/66tyu55/WriterForge/actions/runs/39107632165/artifacts/12129525377) ZIP SHA256 `f329a12bdb0f65fc1d6783fab866c32bffc89269ccc272be8eba9970474fb1ce`。
- 审计器SHA256 `f524d119db3798223b90563dcb8a09778b758f5f9f5256946b3ddb95ebf6e657`，诊断测试SHA256 `9176106d7896da1ecfbe070da7f6d045508a600e3474e1b947e69aecf27cc8d3`。
- 完整机器报告列出 **8个未完成的结构问题（P0 4，P1 4）**，携带源码路径/行号/当时SHA和局限声明。不要把“P0”理解为8个已证明可利用的安全漏洞，其中部分是未打通的能力边界。

## 1. 真实调用链拆开画，而不是按模块名字猜

### A. 原文与学海（已有正常工程路径）

```text
合法原文/已获授权R2资料
   ├─ SourceStudy / OriginalStudy
   │    -> chapter -> paragraph -> short source unit
   │    -> source_spans / studied_chapters / Xuehai snapshots
   │    -> 8条预定义词面/结构线索 (deterministic_structural_unverified)
   └─ V53 corpus_foundation
        -> 明示授权的R2-SYNC + 校验 + 本地磁盘索引
        -> corpus-find离线位置比较
        -> structural_observer写入单独的FactJournal
             [INDEX_WITNESS不得冒充故事人物/读者的真知识]
```

真实依据：
- `writerforge/source_study.py` 采用 `SOURCE_SIGNALS`，约束 `MAX_EXCERPT=160`，并把标签标为 `deterministic_structural_unverified`。
- `writerforge/corpus_foundation.py` 的同步和本地检索边界正确分离；`writerforge/structural_observer.py` 明确 `candidate_eligible_for_creative_execution=False`。
- 以上**证明原文位置与数据组织**,不意味着WF已经读懂人物动机、铺垫/回收或作者意图。

### B. 当前正式创作（实际代码调用，不是训练口号）

```text
LEARN published snapshot -> RuntimeMode.WRITE
   -> VerifiedWritingFlow.prepare(scene,goal)
       -> XuehaiStore.query() 返回来源位置/检索证据
       -> CraftEngine.plan(needs=concerns)
       -> 近2个被接受场景的文本尾部/显式作者偏好
       -> GroundedDraftPacket(evidence,craft_ids,prompt)
   -> local_chat_completion(packet, 配置的本地模型)
   -> save_candidate() 保存候选，不自动接受
   -> 显式 accept_candidate()
   -> WritingFlow.accept_draft -> StoryCommitCoordinator
```

真正断点：`writerforge/verified_flow.py` 的 `prepare()` 用学海证据作为合法输入和元数据，但**并未把某一条经验的使用条件、反条件、选择动作、来源置信度和失败案例编成正式写前决策**。`craft_ids` 记录于证据包而非证明已经在创作前执行技能。

**零模型实测**：替换两条不同学海检索记录，输出 `evidence` 字段发生变化而 `prompt_sha256` 不变。见 `tests/test_v60_architecture_diagnostics.py::test_source_retrieval_changes_receipt_but_not_creative_prompt`。此现象是现有设计实际行为，不能简单改成“直接把原文句子塞进prompt”——那会倒退到V53已禁止的抄录路径。

### C. 自主实验、后审和评论（均存在，但责任分离）

```text
V31 自学实验: v31_autonomous_core / scripts/run_v31_autonomous_wf.py
  -> 自拟实验rule cards -> writer_instruction()
  -> 仅在实验写作中对比；正式自我文学升级未通过
V35/38: stage预存 -> plan -> draft -> validate_after(...)
  -> v38 lesson_transfer_bridge 只有提供可核对的learned_lessons/claims才检查
  -> 检查引文存在及合同格式，并不证明文学因果或经验有效
读者库: actual_reader.py -> 保存的JSONL评论描述/链接 -> review_plan问题
  / feedback.py -> 接受reader_id/category/comment -> DISTINCT(reader_id)合并信号
进化: evolution.py -> PromotionEvidence(数值) -> PromotionGate -> SkillRegistry
事实关系: FactJournal / V59 SQLite时钟与故事作用域，由CLI或structural_observer单独操作
```

并非所有这些模块都理应自动接通：例如外部评论与自评不能自动成为正式升级证据。当前真正缺失的是**有类型、有授权、有可重复核查的控制面**，把允许进入WRITE的经验与不得进入WRITE的假设严格分离。

## 2. 逐项缺口与修复方向

| ID | 优先级 | 源码佐证 | 已确认现象 | 动作 |
|---|---|---|---|---|
| WF60-P0-001 | P0 | `verified_flow.py:153–176,198–217` | 两个不同Xuehai证据集，写作Prompt不变；经验并未参与可核查的正式创作策略选择 | 新建最小 `CreativeDecision` 选择/跳过契约，而不是将原句放进提示词 |
| WF60-P0-002 | P0 | `v31_autonomous_core.py:130–146`；`v35_observable_trace.py:123–176`；`v38_lesson_transfer_bridge.py:29–107` | 实验规则与写后引用验证在各自路径运行；检查到的正式 `VerifiedWritingFlow.prepare` 没有强制执行这层经验合同 | 实验记忆与正式文稿只在显式证据门禁下建立桥梁 |
| WF60-P0-003 | P0 | `evolution.py:260–400` | **临时内存实测**：人工构造全部高分的 `PromotionEvidence`，设置 `requires_human_anchor=False`，通用 `gated_auto` 接口能把技能从L1提升到L2；没有签名或独立报告核验。不是已证明远程可利用漏洞。 | 文学主观技能强制冻结外部证据+来源权限，禁用可绕开的非人审晋级入口 |
| WF60-P0-004 | P0 | `source_study.py:42,226–252` | 八类结构标签属于确定性词面标注、`analysis_level=deterministic_structural_unverified`；`published` 数据不等于已理解文学 | 经验候选状态应分开SOURCE/OBSERVATION/HYPOTHESIS/REVIEWED |
| WF60-P1-005 | P1 | `db.py`、`fact_journal.py:70–91`；`cli.py:53,127–131` | 写作主数据库与事实账本各自可以打开SQLite，CLI使用`--db`、`--journal`；检查的路径没有跨库原子提交合同 | 不粗暴合库；先建立统一`work_id/scene_id/subject_id`映射、版本pin和失败补偿 |
| WF60-P1-006 | P1 | `feedback.py:9–29` | **临时SQLite实测**：传两个任意不同的reader_id，`convergent_signals`认为两人收敛；此层没有验证真人身份。不是证明数据必定伪造 | 读者评价身份、同一来源去重、独立性验收单独设权限 |
| WF60-P1-007 | P1 | `actual_reader.py:31–49`、`scene_learning.py` | 评论 `source_url` 与模型提出的文学分析均不提供自动第三方真值保证 | 引入来源核验等级、可重复定位、真实性未核验状态和撤回 |
| WF60-P1-008 | P1 | `pyproject.toml` / `VERSION` / `README.md` | 软件包仍是27.0.0；V59只是分支阶段，尚未main正式发布；大量一次性workflows混杂长期CI | 增加发布/迁移/持续CI清单；不为整洁删除历史失败工作流 |

### 注意审计的证据强度

- **动态复现**：P0-001、P0-003、P1-006（确实运行各自的小型Python/SQLite诊断）。
- **直接代码观察**：P0-004、P1-005、P1-007、P1-008。
- **静态入口依赖检查**：P0-002。AST import扫描无法证明运行时注入或第三方宿主一定不能调用模块，因此报告严格写成“已检查的正式写作入口缺少强制调用”，不是宣布模块全局不可达。
- 三项绿色诊断的含义是“当前缺口复现成功”，不能包装成“新增三项修复通过”。

## 3. GitHub别人成熟源码对照：借机制、不复制

V59已检查 [pyeventsourcing SQLite事务/事件通知](https://github.com/pyeventsourcing/eventsourcing/blob/9.5/eventsourcing/sqlite.py)、[django-simple-history历史快照](https://github.com/django-commons/django-simple-history/blob/master/simple_history/manager.py)、[SQLAlchemy实体版本](https://github.com/sqlalchemy/sqlalchemy/blob/main/examples/versioned_history/history_meta.py)；V60针对学习与评价链路又读取：

| 实际源码 | 重要机制 | WF未来只借的设计启发 | 为什么不直接copy |
|---|---|---|---|
| [LangGraph checkpoint base](https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint/langgraph/checkpoint/base/__init__.py) blob `c7cacc7bfd703f298427e870bd6d07b4aa395812` | `Checkpoint` / `CheckpointTuple` + `pending_writes`、有类型的checkpoint读取、写入边界 | 将WF写前选择及版本封为可恢复快照，拒绝运行中经验热替换 | LangGraph的通用图执行器与已有WorkTree、StoryCommit重叠，复制将引入第二调度系统 |
| [MLflow Run](https://github.com/mlflow/mlflow/blob/master/mlflow/entities/run.py) blob `3e44a6a97b31bcbec0b6242fdffbe7c0d9d71835` | 单个Run结构上区分 `info/data/inputs/outputs` | WF先固定输入源和决策版本，再保存结果/失败；避免事后变更题目和经验 | 不需要安装整套追踪平台；它本身也不能证明文学评分的真伪 |
| [OpenAI Evals Recorder](https://github.com/openai/evals/blob/main/evals/record.py) blob `8e8ebe9ae62b4711817e08e668d4ac9a4b63cc23` | RunSpec、事件、样本与最终评估分别记录 | 将文学试验协议、单轮答卷、独立评价、最终归因分别冻结 | 只借事件收据的职责分离，不接受任何模型评语自动成为作者真值 |

源码版本和路径已实际核对；**不引入LangGraph/MLflow/Evals，不移植版权代码**。

## 4. 重构边界：只拆真正断裂的部分

建议下一支 `v61-experience-decision-contract`（本V60轮**不创建、不修改生产实现**）。

### 应增一个很小的“经验政策控制面”，而不是巨型Agent

```text
LEARN: 原始SourceRef(只存位置/SHA)
  -> Observation(可复查的结构事实，非文学真值)
  -> Hypothesis(某种手法/经验候选)
  -> ExternalReview(带来源权限、原始反例、状态、版本)
  -> EligibleExperience(通过规则门禁后的操作合同)
                        |
              [冻结可审核 snapshot]
                        v
WRITE:  scene facts + protagonist bounded knowledge + goal
  -> CreativeDecision(SELECT/SKIP/UNCERTAIN + 条件/理由/替代/规则ID)
  -> DraftPlan(执行前锁定)
  -> 现有模型生成器/StoryCommit保持不变
  -> PostwriteEvidence(实际有无做到; 不以引用存在等于技巧成功)
  -> independent holdout评判, 失败入反例库
```

关键约束：
- 原文检索只作定位、印证与对比；不将句子copy进WRITE。
- 失败经验首先影响SELECT/SKIP决策，不是无条件插入prompt。
- 不改现有模型权重、不要求学习与创作同时启动。
- 经验状态与源证据验证权限**不可通过模型自称approved进行升级**。
- 一次语义争议（如V38 L2 R39/R43）不允许硬编码为所有文学情形的万能规则。
- P0首先做**零模型合成试验**：独立经验启动/禁用下，审计写前决策是否不同；负例必须SKIP；陈旧证据必须拒绝；重启能回放旧版；损坏/伪造评分不能晋级。通过后才考虑新的预注册文学盲评，旧私人R2正文只复核不重训。

### 保持不动

已有 WorkTree/Lane调度、正式 StoryCommit、来源许可与R2存储、历史V49证据、V56–V59事实审计分支。合并前做独立备份与迁移检验；不因结构功能数量增加宣布正式作家级升级。

## 5. 下一阶段通过标准，而不是循环造功能

1. **选择改变**：启用不同已审经验，写前实际选择有内容/操作差异；禁用不留下隐形作用；不只是写作Prompt长度变化。
2. **知道何时不使用**：某技能必须有触发条件及反例，污染或不适用时`SKIP`且不借机改作者设定。
3. **过程可重放**：来源版本→明确规则→写前决策→稿件→写后审计，每一步独立记录SHA与来源权限；崩溃恢复仍一致。
4. **外部验收不伪造**：真读者评论/评论模型/考官的权利来源、匿名性与利益冲突必须核验，模型自评分不作晋级依据。
5. **持续退化阻断**：一轮被明确指出的问题不能被“平均质量分”抵消；V49失败不取消。

当前结论是 **P0局部重构：经验转移与决策、权限与晋级门禁**，非全库重写，更不重头训练。项目工程测试广泛，但文学独立改进仍未证明。
