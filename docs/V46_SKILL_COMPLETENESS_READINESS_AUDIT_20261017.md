# WriterForge V46｜Skill 自身是否完善：只读准入审计（2026-10-17）

## 审计边界

目标是回答“WF 是不是一个已经完善且真的会成长的文学 Skill”，不是重新统计单元测试数量，更不是修补 V35—V45 旧证据。此分支仅新增只读验收脚本、其专项测试、Actions 工作流和本报告；默认正式 `SKILL.md`、`manifest.json` 和 V45 原有写作代码均不更改。

真实执行：GitHub Actions [#39041358013](https://github.com/66tyu55/WriterForge/actions/runs/39041358013)，6 项专项诚信验收测试通过，审计 JSON `skill_complete=false`，`model_calls=0`。这份审计是代码结构与已完成实验的状态判定，不构成已安装宿主环境中的完整技能 E2E。

## 发现：它现在“完整”到了哪一层

| 层次 | 状态 | 可核查事实 |
| --- | --- | --- |
| Skill 包形式 | PASS | 仓库根目录有 YAML frontmatter 的 SKILL.md，manifest.json 和 pyproject.toml 同为 27.0.0，CLI 指向 writerforge.cli:main，SKILL.md 内相对文件链接没有缺失 |
| LEARN/WRITE 模式隔离 | IMPLEMENTED | RuntimeEngine 实现互斥、固定快照 |
| 原著读取、切章/段/句、结构学海 | IMPLEMENTED STRUCTURAL | source_study 明确标 deterministic_structural_unverified，禁止称为深度文学理解 |
| Reader-First 的真实文学预测 | NOT PROVEN END-TO-END | ReaderLearningSession 保存调用者反应，SceneLiteraryStudy.run 需要 model_call；并未由 Skill 自己独立完成无需宿主的文学认知 |
| 来自真实原著的新文学经验自动形成 | NOT PROVEN | V45 规则是预先指定的 V38 角色冲突候选，项目人物/事件测试状态由测试脚本种入。不能把它称作WF已经自学一条文学规律 |
| 学习阶段语义经验进入正式创作 | NOT PROVEN | VerifiedWritingFlow.prepare 没有直接读取 scene_learning 的 analysis_json；V45 opt-in 只将已有项目状态编译为指导，不等于 LEARN 的方法自动跨模式迁移 |
| 项目级经验真实改变写作执行 | IMPLEMENTED OPT-IN | V45经测试6组真实WRITE请求与无经验不同，约束来自SQLite character_state/causal_events；不能外推为文学质量有效 |
| V45 能从标准CLI直接使用 | NOT EXPOSED | 实验参数存在Python API但未注册为writerforge CLI命令；尚不能算用户开箱可用的稳定Skill能力 |
| 在当前ChatGPT会话已安装并自动触发 | NOT VERIFIED | 本会话的已连接Skill目录未列出WriterForge；GitHub代码可读与Skill被安装/运行是不同概念。这不代表用户的其他本地宿主也未安装 |
| 无/有经验的真实小说完整对照 | NOT PERFORMED | V44/V45的六情境测试没有同模型创作六篇完整小说，不能称为文学AB |
| 独立文学评审证明质量提升 | NOT PERFORMED | V45反例仍存在“同一人物/线索名称一致但行动和后果无因果”假阳性 |
| 自我更新、反例筛选与真实晋级 | NOT PROVEN | 有候选门控和退回接口；尚无新学经验反复改进文学质量的完整证据 |

### 特别注意的版本问题

根目录 SKILL.md、manifest.json、pyproject.toml仍保持 V27，这是目前**正式稳定技能的声明**，而 V45 仍是隔离 Draft PR。未合并实验不应擅自修改正式版本为V45，否则会冒充能力已正式交付。需要后续在完整验收时同步升级Skill说明、真正可运行的技能入口、参考文档和测试收据。

### 不能用传统软件单测代替的四个条件

1. **加载：** 在目标宿主真的安装/选择WriterForge，触发一次LEARN与WRITE，而不是考官直接用Python调用底层类。
2. **自学：** WF使用真实新章节，通过宿主自身语言认知提炼候选经验，记录完整来源、适用条件、反例，**经验产生不可由考官提前填好**。
3. **迁移：** 新写作任务下，WF自己在正确情况下选择经验，也能拒绝不适用的经验；记录前置决策、恢复的学海经验ID、实际稿和反证。
4. **文学：** 同一宿主同一任务对照 空学海 / 加载自学学海；采用未见题材并有独立读者质量意见。与现有 V45 的“临时实验条件改变prompt”不是一回事。

只完成1—3可称技能工程闭环；只有4获得足够跨题材正向结果，才可以说文学经验产生实际作用。未经确认的进步、模板生成、修补旧日志都禁止算数。

## 迭代准入结论

**SKILL包结构基本齐备，但离一个能通过宿主可靠运行、自发积累文学经验并稳定改善小说的成熟Skill仍有差距。** 本轮判定 `skill_complete=false`，不是建议再开发更多独立文学子Skill；优先修复宿主可加载/可观察入口以及LEARN→经验→WRITE真正自主运行的缺失连接。V46只读审计不自动晋级任何文学能力、不改历史R2、不合并正式main。

此后每次报告同时列出：（A）Skill运行完整度，（B）WF自主经验与策略进化完整度，（C）文学盲测质量，有一项缺证据则不得宣布 WF 全面完善。
