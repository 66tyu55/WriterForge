# WriterForge V114 · 已接入 Novel Studio 时态记忆后的真实追逐打斗测试（调用前冻结）

日期：2026-10-21。**在真实 V114 付费请求发生前注册**，不得用未来运行结果倒填预注册。原来 V113 951 字 WF 正文、Storyteller 1010 字、裸模型 1161 字及其失败记录全部保留。生产 Railway 完全不使用。

## 用户要求与硬问题

用户明确要求：如果 WF 自己的叙事连续性追踪失败，直接接入现成的文学记忆追踪。V114 的最小词面追踪曾把“沈渡取下剑穗并挂到锁魂索”的合法转移误判，**按触发条件启用**已在 GitHub 上固定 MIT 源码的 [Novel Studio](https://github.com/bbaz123/novel-studio/tree/b585a9ca4ce474fe2471bf3bb7f8c284c6e4104a/ai/story-state/temporal) 时态 reducer/schema，而不增另一模型、不接其他新数据库、不解锁长篇自动训练。

**可确认的零模型真实成果**：只读 GitHub Action [#39599663506](https://github.com/66tyu55/WriterForge/actions/runs/39599663506) 将原 V113 WF 951 字模型初稿从私有R2原样回读；剑穗从沈渡腰间未经实述转移到索钩的事件被两个检测器标为待复核；Novel Studio reducer 没有自动转移所有权，继续保留上一个候选持有人沈渡；候选风险进入后续 writer prompt。R2写0，模型调用0。**这不证明WF自己能写得更好。**

## V114 真正写作测试

**同一基准问题**：`给我一个追逐打斗的玄幻1000字`

- 使用用户已经连接的 GitHub Secret `DEEPSEEK`，映射给 `DEEPSEEK_API_KEY`，官方同名模型 `deepseek-flash`。S3 R2仅访问新的 `writerforge/v1/experiments/v114-matched-fantasy-chase/sha256` 私有CAS；不读旧小说库，不修改已存在R2其他文件。
- 唯一实验标识 `WF-V114-REAL-CONTINUITY-AND-NOVEL-STUDIO-20261021`；实验预注册CAS首次创建 `created=true` 后才允许模型请求，重跑相同身份必须拒绝。
- 真实WF程序 `AutonomousWriting(...).run(draft_mode="continuity_guard")`，使用已有V96严格分段先因后果引句合同；Novel Studio 原 MIT reducer 每次写完**真实段落**便执行状态更新，下一次 WF 写正文前使用该结果。只复用中性玄幻Xuehai软件连接数据，不声称原来15章文学经验已迁移。
- 同一模型自己先决定两个连续事件（一次规划模型请求），随后WF原章节计划一次，再写两个连续正文片段，每片要求450—550含标点中文字符。**最多4次真实DeepSeek请求**，输出预约上限5000tokens（1450+650+1450+1450），保守全输入输出预算135000。所有请求未验证前先预约CAS，所有原始HTTP wire均在JSON解码前CAS保存，每份原始JSON在WF软件检查前CAS保存。任何响应失败、短稿、引用格式错、追逐逻辑错均不付费重抽或软件修改原文。
- 引进Novel Studio的 `schema.mjs` 与 `reducer.mjs` 原文件必须与上游 commit `b585a9ca4ce474fe2471bf3bb7f8c284c6e4104a` 相符。MIT许可证同目录。原创写作仅选外部**确定性事件校验算法**，没有把 Novel Studio 作为额外模型/剧情构思。所有事件候选、人物心理和世界状态都未经过独立文学审查，永不得自动进入 `FactJournal KNOWN` 或正式技能库。
- 这不是公平于V113的完全等算力实验：本轮WF主动分段并有额外模型请求。只有真的得到原文后，按实际字数、招式位置、兵器持有人、资源来源、相对距离和损失余波审稿，避免仅以“发现错误率高”把长文生成通过误称为文学提升。V113旧稿作为只读历史对照，不能再收费重生成。
- 不强行自动修文；模型错误不因修正格式升为PASS。代码版本、SHA256、实际请求数和供应商usage按真实GitHub执行日志报告。任何人类文学评分（含助手的观察性评价）与独立盲评分开：这轮尚未有外部人类盲审，文学技能终点依然 LOCKED。

## 目前结果与退出条件

当前源文件：`experiments/v114_real_wf_continuity_once.py`，GitHub分支 `v114-chase-live-state-and-oss-fallback`，源代码全仓离线CI [#39600447883](https://github.com/66tyu55/WriterForge/actions/runs/39600447883) 为 SUCCESS；之后提交如引入测试，应再次核查最新CI。真实V114模型调用**尚未开始**（此文件创建时），新篇质量未知，旧 V49 THIRD_STRIKE_FAILED 与文学第二窗口 LOCKED 原样保留。

如果分段首步就因JSON格式失败，则用已存原答定位编码/合同问题，**只如实报告失败，不重播这次实验**。若两段真实输出完成，进入独立零模型冷回读和对照本轮同题文学判断，绝不自动解锁训练。
