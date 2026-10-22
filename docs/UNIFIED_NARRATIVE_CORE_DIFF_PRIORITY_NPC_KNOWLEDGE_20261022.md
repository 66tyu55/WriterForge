# WriterForge — 统一叙事底层重构交接

日期：2026-10-22。分支：`refactor-unified-narrative-core`。非 V124/V125 的新专用剧情模块，目标是统一长期线索、人物认知、接触关系与路灯优先级。生产 main 不改，Railway 不部署。

## 为什么必须重构

V105 的长期代价、V117 的状态冲突、V118 的文学路灯和 V123 的单一复仇线分别存储和提示，有重复状态所有权。一次复仇可以加特判，但数百章节中的伏笔、误会、暗线、隐秘真相不能靠无数独立模块持续修补。将具体“复仇”泛化成稳定 ID 的 `THREAD` 节点，只写一个有来源证据的事件-状态边界。

## 整体写作顺序

```
[作者确认的来源 / 已写出的真实正文]
             |
             v
[可验证来源事件：一次性录入，未知保留未知]
             |
       [统一叙事快照]  <--- V117 已有带哈希的续写快照
        ├─ NODE: CHARACTER / FACT / THREAD
        ├─ EDGE: CONTACT / KNOWS / UNKNOWN / BELIEVES
        └─ PATCH: CONTENT / KNOWLEDGE / RELATION / THREAD / STATUS
             |
[变化标记 + 稳定键 diff；不同章节不需重读所有正文]
             |
[统一调度入口：实际 Novel Studio 物理约束
   > NPC 知识边界 > 相关旧伏笔 > 可选 CraftEngine 问题]
             |
[真实生成正文 -> 原文检查 -> 候选凭证 -> 下一章快照]
```

## 代码实际完成内容

- `writerforge/narrative_core.py`：不依赖新的模型、向量数据库或图数据库。可初始化/推进一个最多 96 节点、256 边的**有界快照**。每次推进要求章节连续，事件必须有原文唯一位置、哈希及作者明确确认，不能把模型计划、读者可见信息或空泛传闻视作已发生事件。
- `FACT` 允许秘密/公开来源区分；`THREAD` 是通用 GOAL / FORESHADOW / PROMISE / REVEAL / MYSTERY / MISUNDERSTANDING / RELATIONSHIP / OTHER，不能只用于复仇。THREAD_REVISE / THREAD_RESOLVE 仍须作者确认、原文可核验。
- `CONTACT` 代表“见过/交谈”，**不会派生 KNOWS**。人物对秘密的认知需要明确 `WITNESS` 或 `SHARE` 且知识提供者已有可靠出处。`UNKNOWN` 是作者明确否定知识状态；`BELIEVES` 不等于客观已知。演员、主角、读者以及第三个 NPC 之间绝不自动合并认知。
- `propose_source_interactions()` 对显式叙述的 NPC 见面或知识传递提出**仅供复核**的事件建议，保留 source span/quote hash，但绝不自动写入 KNOWS 或正典；梦境、传闻和对话中的提及不等于现实事件。
- `keyed_diff()` 对固定节点身份计算脏节点/按位变化标志；无相关状态变化的章节不会让历史节点反复变脏。参考 Vue 3 的 PatchFlags / scheduler 优先级思路，但没有复制 DOM diff 或 Vue 源码。
- `schedule()` 使用稳定、去重的优先级任务。真实受伤/物件约束仍由原 MIT Novel Studio 时态归约器负责；统一叙事图提供 NPC 认知和长期线索。最多点亮 3 条相关长线，更多相关未结伏笔在调度凭证中明确标记 `deferred_unresolved_thread_count`，**既不删除，也不擅自标记完成**。无关安静章节不点灯。
- `writerforge/writing_assist.py` 真正续写模式 `continuity_guard` 改为由既有 `_prepare_guarded_turn_packet` 一处调度硬约束 / NPC 认知 / 长期线 / V118 可选文学提示。原有正文实际事件和 Novel Studio 物理拦截维持其原校验权威；一个候选回合中的模型文字无法自动更新新图。
- `writerforge/v117_continuity_trace.py` 继续是唯一主续写快照封套。`unified_narrative_core` 是可选已审图；支持旧 V123 快照单独兼容，但同时携带 V123 专用复仇账本和新图被明确拒绝，避免两套长期记忆所有权互相冲突。
- `audit_candidate()` 狭义检查某 NPC 之前被明确登记“尚不知道”的事实被正文无依据写成“早已知道”；严格矛盾可拒绝候选，普通可能出现合理转折时只提示审查，而不是误杀文学创意。

## 验证与数据来源

实验分支 GitHub Actions：见 `unified-narrative-core.yml` 的最近成功记录；本文件仅陈述已落地机制，不声明模型文学质量已提升。

- 全仓库的旧 V96–V123 回归持续执行，特别要求旧复仇流程、V114 物件状态和人物伤势不能因合并而退化。
- 新 `tests/test_unified_narrative_core.py` 检查主角-NPC 接触绝不产生秘密认知；目击/明确分享有证据后才改变知识；秘密人物的误认与主角信念不同；多类型伏笔共用一张图；300 个合成无关章节没有脏节点膨胀；第 300 章相关时重新点亮；20+ 相关线的提示排序和延迟队列；篡改 / 跨项目 / 章节跳号拒绝；真实写作提示构造优先保留人物认知边界。
- `experiments/unified_narrative_core_cold_audit.py` 通过 R2 **只读**检查旧 951 和 964 字原始错误稿的 SHA，并用原 MIT Novel Studio 构建一次源状态基础；后续 300 章节为**人工构造的离线测试文本**，绝非真实 AI 创作 300 章。原始失败证据未篡改；模型调用 0、R2 写入 0、正典写入 0。

## 仍然需要明确承认的限制

1. 这是统一的基础设施原型及调用合并，不是“任意中文句子都能自动读懂”。知识、关系和伏笔结构化状态的变更目前要求具来源证据并获得作者确认；自动检测到的接触或传话只是候选提醒。
2. 原 V105、V117 和 V123 文件为了既有书稿与测试兼容仍保留，**新路径只允许统一图或旧 V123 专用账本二选一**，不能把“合并写作入口”夸大为历史源码全部删除。生产应用尚未切换默认模式。
3. SHA 保护意外漂移及跨调用的一致性，不代表具备对恶意独立修改者的密码学签名或用户身份认证。
4. 96 个热节点、256 边是一项可审计容量上限；超出明确失败，不能静默忘记。真正多卷/上千伏笔还需要与既有 R2 的冷线索分页索引打通，不能把所有历史事件永远塞进模型上下文。
5. Vue 是借鉴稳定键、位标记、批处理和优先级，而不是直接照搬其 JS diff 引擎；详细来源：
   https://github.com/vuejs/core/blob/main/packages/runtime-core/src/scheduler.ts
   https://github.com/vuejs/core/blob/main/packages/shared/src/patchFlags.ts
6. **真实写作质量未检验**：本轮不调用用户新获批的书生 token；需要以后同模型盲测近千字长段落、人物认知误报率和多章伏笔兑付质量。

核心原则：一条原文事实、一份更新来源、一次有界事件入账、一个统一叙事快照；模型可以自由推进故事，但不能靠自我解释改变认知或结案。