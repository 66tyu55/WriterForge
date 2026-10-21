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
