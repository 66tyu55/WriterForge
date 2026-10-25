# WriterForge 0.Y — 追查跨章真假签名组合：整章、分段时态、NarrativeCore 必须属于同一版本（2026-10-25）

**工程目的**：测试要击穿 **WF 自己**的漏检/误放行，不是测试 AI 愿不愿意改稿，也不是靠新模型改一段小说来拿绿灯。这轮只在 `refactor-unified-scene-delivery-audit` 改原来的 V114/V117/NarrativeCore/G；不改 main、Railway、私有 R2、Canon、已完成的原生小说训练或原提供商回包。**新增付费模型调用为 0**。

## 1. 原本已有跨章回改机制，但验收缺了一条关键证明

代码里早已有 `writing_assist._prepare_unaccepted_chapter_fork`、`_validate_unaccepted_fork_resume`、同原作家作出跨章 LOOK_BACK 后保存旧两章和重写两章的功能，不能把它说成完全没有回滚。

真正问题是 **两个各自哈希合法的不同故事版本可能被拼到一张 V117 resume 上**：V114 快照有自己的真实 source SHA，NarrativeCore 也有独立图 SHA 和最近保存原稿 SHA，但旧 `make_resume` 只比较章节编号，未必验证两者由同一组原稿分段、同一条 V114 事件父链构成。

更隐蔽的是：章节 3/4 字节可以与旧版本完全相同，可章节 2 的状态换了以后，章节 3/4 的 V114 **receipt SHA 和因果父链必须一起改变**；只比较正文 SHA、只比较单个签名都无法证明它们的父版本正确。

## 2. 先造红灯

- [原始 RED #40178442441](https://github.com/66tyu55/WriterForge/actions/runs/40178442441)：新增 `tests/test_wf_0y_cross_chapter_temporal_graph_binding.py`，两项失败、两项错误。原 `make_resume` 未绑定独立合法图/快照，原 `record_chapter_memory` 不接受已验证的章节分段 V114 快照清单。不是模型输出错误。
- 测试包含：错误第 1 章 V114 + 正确第 1 章 NarrativeCore；有两个真实短片段的整章不能用末段来源 SHA 伪装完整章节；旧第 2 章图不能挂第 2 章新 V114；第 2 章变动时第 3/4 章文字没变也必须重建真正时态父链与图父链；正确的新父版本允许重建。
- 另一条旧兼容漏洞：[额外 RED #40179563512](https://github.com/66tyu55/WriterForge/actions/runs/40179563512)：旧 graph 与新 V114 的**最后一章文字 SHA 一样**，但更早的历史来源不一样，G 居然开始向模型请求写下一章。若把“目前单章 SHA 相等”当成“祖先状态也一致”，会错用前史。

## 3. 修复的是既有代码和实际来源链，而不是让 AI 调整答案

- **V114 每个真正分段**：原 G 按 `external_temporal_step` 逐段获得的完整签名 CP 被纳入 `turn_external_checkpoints`。此前存在的 V96/graph/continuity rewind 在原 `tracked_rewind_lists` 中一起截断这个清单；删掉上一段后，不能复用它派生出来的 V114 候选。
- **NarrativeCore 当前签名增加来源链**：`record_chapter_memory` 可接收 `chapter_source_parts` 和 `chapter_temporal_checkpoints`。先核对原 `candidate.md` 文件字节 SHA、分段经 `"\\n\\n"` 合成是否逐字等于保存整章、每个分段的 V114 `source_sha256`、同章 V114 前后 CP receipt 链、上章最后的 temporal receipt 父链；再把绑定存于**唯一已有的** NarrativeCore 签名字段 `source_temporal_link`。绝不创建第二记忆库或新文章。
- **跨章父状态**：`advance_graph` 把上一章已签名 V114 末端身份作为 `source_temporal_parent_sha256`；新章的第一段归约父值若不匹配，`WFCORE_CROSS_CHAPTER_TEMPORAL_PARENT_MISMATCH`，即使后面文章字一模一样，也不能生成绿色的新图。
- **V117 连接签名和读入验证**：`make_resume/read_resume` 检查图当前来源绑定与 V114 签名是否一致；整章多段时，不能拿整章 SHA 与最后一段 SHA 生硬比较，必须有实际分段组装和逐段时态凭证。旧历数据没有完整来源链时仍允许**只读打开原归档**，但**不允许未经核查作为新 G 写作前史**。原跨章重写入口要求旧章节 `source_temporal_link` 为真，不接受两个各自有效却未真正证明同源的旧版本冒充合法 fork。
- **旧测试里的假阳性**：`test_unified_narrative_core` 曾用一段 `ORIGIN` CP 搭第 5 章图，`test_unified_r2_memory` 曾把第 1 章 CP 搭第 28 章图，`test_wf_discarded_event_state_replay` 曾把完全无关的一段 CP 搭第 4 章图，历史上错误地认为都是有效恢复。修成**真正按章推进的 V114 源数据**，而不是松开新检查。R2 测试仅用自身模拟 CAS 测试源，未实际连接用户 R2。
- 以前 WF 在本地已可将两章候选当成无 Canon 新分支重写。这次**没有**让原提供商再次写作品，`tests/test_wf_cross_chapter_candidate_fork.py` 直接走**真实 G 方法与模拟模型回包**，检查作者新写两章、前史章、图边父 SHA、V114 末端与整章正文、选择新 fork 后旧 resume 不能继续。合成题仅验证工程，不是“小说质量已经变好”。

## 4. 文学和历史边界

- 测试程序没有一字代写正式小说；不曾把旧《潮簿》《雨册》原作者的 `MOVE_ON` 改成 LOOK_BACK。文学自审、故事动机和作者真正要删的句子仍是 AI 的决定；WF 只能保护来源、时空和可归档的事实。
- 新来源绑定保护的是**后续候选不得偷偷嫁接另一个版本**。没有任何本轮付费“真实文学修订→重新生成多章→人类盲评”的新证据。
- 旧已保存且无分段时间来源清单的多章归档仍**可读取，不可直接冒充完整核验的续写前史**。将来若要继续旧归档，须从用户已存原字节/原厂回复和时间凭证离线核对，不能猜补、不能重跑原 15 章训练或强制重写；本次没有自动迁移。
- 该修复没有承诺把旧历史实体认知状态从所有远端副本直接删除；所有旧候选保留不可变历史，**被旧来源污染的下游只应在新 fork 的新父链里失效和重新产生**。后续仍要审计长篇冷档/旧摘要跨分支索引，不允许只因为部分绿灯就认为完整长篇已经绝对正确。

## 5. 版本与证据链接

- 工程测试：`tests/test_wf_0y_cross_chapter_temporal_graph_binding.py`；现有 `tests/test_wf_cross_chapter_candidate_fork.py` 补强，不引入新的付费模型或存储模块。
- 正式验收以 GitHub Actions 的**最新** `WF Unified Scene Delivery and Progression Audit` 全量输出为准；中途 CANCELLED 和 RED 均为历史证据，不应改写为通过。

## 6. 最终 0.Y 验收结果（真实工程，不是模型文学结果）

- [四章节源链全量 #40179359301](https://github.com/66tyu55/WriterForge/actions/runs/40179359301)：**1,671 项执行、7 项跳过、0 失败**。第 2 章修订后，第 3/4 章哪怕字节不变也必须经新 V114 父链重新构建，并绑定新 NarrativeCore 父链。
- [旧归档相同末章、不同祖先的 RED #40179563512](https://github.com/66tyu55/WriterForge/actions/runs/40179563512)：**1 个失败**。旧版 G 曾从一个分别签名合法、且最后章节正文一致、但前一章并非同一故事源的 V114/graph 组合进入模型调用。这是 WF 的真实错误，而不是用户或 AI 未按提示改稿。
- [引入严格来源续写门槛后的回归 #40179695324](https://github.com/66tyu55/WriterForge/actions/runs/40179695324)：4 个旧样例失败。原因是旧测试/试验入口自己未提供真正 V114 与 NarrativeCore 的同章绑定，却期望其可作为新 G 续写源。**没有放宽门槛**，而是检查并修正三个确实缺少来源凭证的构造入口：`test_wf_reader_first_original_author.py`、`test_wf_reader_source_attribution_G_integration.py`、`experiments/wf_real_new_scene_reader_first_control_20261025.py`。对应模拟章节须将真实原文 CP 作为 `chapter_temporal_checkpoints` 写进**唯一原图**；未补造旧模型文学回复。
- [最终完整回归 #40179955242](https://github.com/66tyu55/WriterForge/actions/runs/40179955242)：**1,672 tests run，7 skipped，0 failed**，Studio Node 脚本检查也通过；包含所有来源攻防、旧多章 fork、R2 模拟 CAS、原始候选存储和 legacy 兼容边界。
- 新的 legacy 来源限制：`read_resume` 可只读查看未录下完整源装配信息的旧签名归档；但当 `AutonomousWriting.run` 用其继续生成新正文时，`require_verified_ancestry=True` 在任何新模型调用之前拒绝。`WF117_GRAPH_TEMPORAL_SOURCE_UNBOUND` 绝不能被“最后一章恰好字节相同”洗白。若旧归档确需续写，必须离线从**真实源原文和历史签名**重建可信链，不能直接强迫 AI 重写旧书，不能补造来源。
- 当前保证范围是**新开发分支候选来源的 G/V117/NarrativeCore 绑定和新的分支重建**，不是已部署生产服务替用户删除了所有远端旧分支或“长期所有上下文语义正确”。旧副本保留为不可变档案，不误作当前新分支事实；新的模型作者自主文学修订/实际读者文笔改进依然**没有被本轮测试证明**。本轮新增付费模型0、Canon0、R2用户原著读写0、Railway部署0，`main` 不动。
