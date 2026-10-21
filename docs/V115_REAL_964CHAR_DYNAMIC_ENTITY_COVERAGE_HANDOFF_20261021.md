# WriterForge V115 续接交接 · 原始964字动态实体覆盖（2026-10-21）

用户发消息“中断了--继续”后核查 GitHub V114 最新HEAD 和运行记录，发现跳过消息期间 V114B 已用真实DeepSeek 生成一篇**964字符的第一段**，但由于违反V96分段字数合同被拒；第二段未生成。V114C 零模型完整原答冷验成功；V114D 在 [#39603459213](https://github.com/66tyu55/WriterForge/actions/runs/39603459213) 返回失败信号：**实际964字文本明写“火髓果”和“右臂”，却提取到零条物件状态观察，Novel Studio 时态归约器应用零事件。** 严格保持历史失败，不重调用或“补写”原稿。

## 这次已完成的 V115 修复（自研的不是第二个数据库）

- 新源码 `writerforge/v115_dynamic_entity_candidates.py`：从真实正文提取**动态名称候选**，不再完全依赖原来固定的 `TRACKED` 技能/器物名字表。具体识别“火髓果”、身体部位“右臂”，同时严格区分 `injury`（伤势附近出现某些词）和 `body_part_unresolved`（只是出现身体部位）两种假说。
- 每个候选附原始文字的字节SHA和Unicode字符区间；`holder: UNKNOWN`，绝不从名词存在推断人物持有它、已吃掉灵果或已经受伤、能量已补足。
- 已接进 `writerforge/v114_external_story_state.py`，所以候选连同外部MIT Novel Studio temporal reducer 的真实已验证事件一起被回执保留，**并在下一段WF写作提示中显示，而不是仅做离线审稿**。候选名词本身不得冒充temporal状态事件或FactJournal KNOWN，主 `single` 模式原样保留。
- 单元测试 `tests/test_v115_dynamic_entity_candidates.py` 抓到真实中文计量词“枚火髓果”误识别；调整最短原文词段后修复。测试和红项保留。
- 新的零模型 **真实原文冷审** [GitHub Actions #39608429389](https://github.com/66tyu55/WriterForge/actions/runs/39608429389) SUCCESS：动态发现 `火髓果=true`、`右臂=true`，原文恰好964字符，`coverage_pass=true`；没有原文改写、没有新DeepSeek、没有R2写入。

## 重要负面证据、绝不能夸大

**Novel Studio 本轮仍只接收到0个可执行状态事件！** 上述PASS只代表**真实原文的两个关键实体名词不再遗漏**，不代表本轮已经知道“谁拿走了火髓果”“谁的右臂受伤”“吃果后补回多少法力”，也没有证明新WF真实完成第二段创作。原来的 `TRACKED` 固定名字表仍不含“火髓果”，只是新的动态提取路径可以发现它；读者/作者的语义证据依然需要独立校核。

接下来应直接完善**动态实体 → 带正文锚点的状态事件提案 → MIT归约器前提校验 → 下一段可用状态**链，分辨“观察到物件”与“真正转移/消耗/伤势变化”。必须优先用原V113“剑穗从沈渡腰间跳到索钩”和V114B火髓果/右臂的真实负例复验。即使下一次软件CI绿色，也应继续保留文学成效`UNPROVEN`，不要为了凑出正常正文反复付费试错、也不要为追踪随意扩充无界内存。

外部Novel Studio来源 `bbaz123/novel-studio` MIT pinned `b585a9ca4ce474fe2471bf3bb7f8c284c6e4104a`，源码vendor在 `experiments/v114_fallback_novel_studio/`。所有旧文学失败记录/V49第二窗口锁定/前15章训练不变，铁路Railway不参与，本轮新模型调用0。


## 一、2026-10-21 最新核实快照（从 GitHub 真实运行日志交接）

- 最新开发HEAD（本次交接补充前）：`a124a3ea2e60a5ec96086168c1e4bb81efe1e7b5`。最新全仓 [GitHub Actions #39608654767](https://github.com/66tyu55/WriterForge/actions/runs/39608654767) **SUCCESS，1,225 项实际执行，4 skipped，0 failures**；其提交主要是保存V115动态实体交接。这个绿色只证明离线软件回归，不是文学能力晋级。
- V114原第一次付费入口 [#39601327157](https://github.com/66tyu55/WriterForge/actions/runs/39601327157)：实验预注册已占用、首请求意图已存CAS，但底层 FlashBudget 要求`max_total_tokens`严格为`150000`，原`135000`导致 `WF_FLASH_TOTAL_BUDGET_CONFIGURATION_INVALID`，**没有实际HTTP提供商响应、官方usage 0/0**。原失败manifest `faa8f406a1960a34ef9d348d138456364e5fd56844526c899c5c8394e32f3941`；不重启、也不伪装成功。
- V114B新唯一预注册 [#39602279326](https://github.com/66tyu55/WriterForge/actions/runs/39602279326)：**确实完成3次真实模型请求**：WF自主两事件提纲、WF章计划、WF首段正文。官方返回 input=1795、output=1317，共**3,112 tokens**。V114B原manifest CAS `c9d1ffea1319f27bbd530f2bb44da2ccf68feda2d49280ffdf548e81eb430ffc`，原初稿回答CAS `c49198a29fed64d8883393b3a2168e37011a09de32a9899986edfc148a499e88`，原始HTTP wire CAS `4ac42046aa4a45fc85c8572ca2828b938710041e15aa35b595deb37839f96bd8`。
- V114C冷读 [#39602776767](https://github.com/66tyu55/WriterForge/actions/runs/39602776767)核实：WF真实写出的**第一段有964个Unicode字符**，JSON根字段 `prose,trace` 和trace三字段都符合要求；真正拒绝点在 **`writerforge/v96_causal_turns.py` 的单段正文长度上限 `MAX_PROSE_CHARS=950`**（最少80），而不是故事没有正文、也不是三字段不全。该段仍`WF96_TURN_PROSE_OR_TRACE_SCHEMA_INVALID`、**未接受**；第二段**未生成**。只读原稿Artifact [#12347540294](https://github.com/66tyu55/WriterForge/actions/runs/39602776767/artifacts/12347540294)。
- V114D零模型原文覆盖测试第一轮 [#39603459213](https://github.com/66tyu55/WriterForge/actions/runs/39603459213)记录 **native观测0、Novel Studio真实已应用事件0**、遗漏“火髓果”和“右臂”状态。末轮 [#39608429389](https://github.com/66tyu55/WriterForge/actions/runs/39608429389)真实结果是 `dynamic_fire_fruit_mentioned=true`、`dynamic_right_arm_mentioned=true`、`coverage_pass=true`，但 `Novel_Studio_applied_source_events=0` 仍未改变。**当前正证据是“能从原文找到名词/身体部位”；负证据是“尚不能据此形成可信状态变化”。**
- 这一段文字未走到下一段的实际模型生成，所以**V114/V115尚未证明 Novel Studio 追踪状态真的帮助了下一段小说连续性**。不得把离线V113旧剑穗复现PASS与真实新写作毕业混为一谈。
- V115源码实际已接入 `writerforge/v114_external_story_state.py`：`discover_candidates(prose)` 提取源文字段，将`dynamic_source_entity_candidates`放进候选回执，`temporal_prompt`向下一段显示它们。无可信交接/损耗/受伤事件时，持有人仍`UNKNOWN`，事实写入仍`0`。

## 二、下一次接手先做什么（无需重复已有工作）

**首要任务不是再创造新的训练题或立刻付费。** 保持代码隔离分支，在不联网也不调用模型的条件下，以原V114B已锁定的964字初稿以及V113原951字剑穗案例做一次完整的**“原文 → 实体候选 → 状态变化事件提案 → MIT Novel Studio expected-old-value 校验 → 下一段可用但未升为正典的快照”**回归：

1. 把`火髓果`和`右臂`从名词提及细化为严格可区分的**位置、持有人、法力消耗、伤势**候选，但只在确有动作原句锚点时形成 reducer 事件；比如“吃掉/递给/掷出/复原”和“只是看见/听闻/梦到”必须分开。不得把原文名词出现当成已吃掉果子或右臂骨折。保留角色视角/作者叙述/推测之间的界线。
2. 先核准源文实际句子、因果次序、角色知识和原始引用唯一性，再尝试原归约器的前置状态校验。像已钉在山壁的飞剑再次挥舞、旧剑穗突然换人，应记`UNPROVEN_TRANSFER`，而不是自动把旧位置清掉。
3. 真正WF下次生成时应在**每段文字出炉后**由状态机整理已证变化与未知，下一段生成前从旧快照抽出精简、可信状态。依托现有FactJournal/StoryCommit和R2 CAS，不添加无界平行记忆系统，不能默默丢历史债。
4. 必须处理`V96 MAX_PROSE_CHARS=950`和“每段约450—550字”的实际偏离：优先核查提示、实际生成长度与存证，**不要截断964字的旧原稿、放宽闸门把旧红项洗成PASS、或重播已扣费请求**。新付费实验必须独立新预注册、明示总预算和调用数，在零模型端到端假响应回归稳定后才允许执行。
5. 用同题新完整1000字原文与V113已封存WF 951字、Storyteller 1010字对照，定位剑穗/武器位置和法力来源真正错误**首次出现位置**，同时看叙述节奏自然度。等模型、等实际字数和等预算的公平限制须显式记录；没有独立可信文学评审前维持`UNDETERMINED`。

**运行红线**：Railway继续不用；GitHub Actions已有 `DEEPSEEK`（大写）Secret、R2 S3四项Secrets，不能要求用户重新输入；V114原（预HTTP失败）与V114B的3次真实模型请求、V113旧4次与更早所有原答一律不重放；生产WF V99安全idle、前15章学习经验及V49第三次失败/第二文学窗口LOCKED全部保持不变。任何git软件CI全绿不等于WF文学水平进步。
