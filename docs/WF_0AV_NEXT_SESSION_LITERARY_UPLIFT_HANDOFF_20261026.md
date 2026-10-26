# WriterForge 0.AV｜正式交接：从检查正确性转向真实提升小说写作

日期：2026-10-26。唯一工作分支：refactor-unified-scene-delivery-audit。
核对时最新 HEAD：0c287d488d85（0.AU 的文档交接提交，下一窗口必须重新核实）。
最近已验证的完整无模型回归：[GitHub Actions #40279156590](https://github.com/66tyu55/WriterForge/actions/runs/40279156590)：**1,808 tests，10 skipped，0 failed**，对应代码提交 b13d1070f42a。
本文件只是交接，不表示0.AV已经做了任何新付费写作或文学质量A/B。

## 1. 下一窗口严格按照此顺序读取

1. docs/CURRENT_HANDOFF.md 最顶部的0.AU、0.AR—0.AT；较老章节是历史，不能把过时的“未测试”等说法当现状。
2. docs/WF_0AV_NEXT_SESSION_LITERARY_UPLIFT_HANDOFF_20261026.md（本文件）。
3. docs/WF_0AU_G_V98_PROSE_DRIVEN_WRITER_PLANNING_20261026.md。
4. docs/WF_0AR_0AS_0AT_REAL_WRITER_REVIEW_STAGE_LITERARY_UPLIFT_20261026.md。
5. 需要复原早期失败时：docs/WF_0AP_0AQ_REAL_DEEPSEEK_G_SOURCE_DEBT_AND_REPLAY_20261026.md。

核心实现：writerforge/writing_assist.py 中 AutonomousWriting.run；writerforge/v98_rolling_causal_planner.py 中 g_source_replan_eligibility；以及 V96、V119、V114、V117 和唯一 narrative_core.py。新测试：tests/test_wf_0au_g_rolling_author_planning.py。

## 2. 已被真实证据证实的成果与限制

**0.AG—0.AL：十类微段已实测。** 武侠、恐怖、计谋、仙侠、历史、喜剧、言情、科幻、日常、抒情，总计20份作者原稿。许多组存在长度失衡；写作模型与评委属同家族，缺少独立人类验收。不能平均十组正差值后宣称文学水平大幅提高，禁止重复旧15章训练。

**0.AQ：真实六段、不是作家修稿成功。** [DeepSeek Flash 真实G #40264287305](https://github.com/66tyu55/WriterForge/actions/runs/40264287305)：复用前期真实来源、两份模型规划及八份原模型回复后，仅新生成第五/六段，最终2269字符，全文 SHA256 d1b86f2b6430b80bdb70df70199b9644e0a0b041ab842a81abc0a625c29cb0e3。V114/V117/唯一NarrativeCore保存了未接受候选的签名来源链。**真实AI自主回改旧段：0次**；不能声称真实“删废稿—重写下游”已完成。

**0.AR：物品因果审查是辅助而非文学判决。** 真实稿中周卒带册离开，秦渊后来封装疑似同一本册子。它可能是不同副本、文学省略或倒叙。原V122/V116/V114经RED→修原模块→GREEN保存可传承的带原句及双SHA疑问，仅SOURCE REVIEW，不能代替AI编造交还、写成已知事实或强制修改。[完整回归 #40273050833](https://github.com/66tyu55/WriterForge/actions/runs/40273050833)：1802测试，10跳过，0失败。

**0.AS：写后自审协议变可靠，不等于文学变好。** 原G同时传入写正文 prose/trace 与选择回改的两个冲突JSON请求，真实六次只有2次回答有效。修复为独立 ONLY_REVIEW_DECISION 后，同一DeepSeek在 [真实自审 #40272430331](https://github.com/66tyu55/WriterForge/actions/runs/40272430331) 上由有效2/6升至6/6；没有新小说生成。六次均为 MOVE_ON，真实自主回改0次。这是输入任务/解析层面的工程改善。

**0.AT：带真实来源疑点的两次审稿仍未触发修订。** [真实同作者复核 #40273633246](https://github.com/66tyu55/WriterForge/actions/runs/40273633246)：原作者看到带SHA的册子去向原句，2/2仍选择 MOVE_ON，可以是认可合理留白。不能强迫作家修改，也不能把它算作文学进步。完整回归 #40273430253：1805测试、10跳过、0失败。

**0.AU：当前最新工程主线，尚无真实文学A/B。** G线路 continuity_guard 已加入默认关闭的 g_rolling_author_planning=False。启用时，复用原V98，由原写作AI基于上一段真实已写出的动作/后果自主重规划下一beat；WF仅核来源、SHA、人物范围，不产生小说、剧情结果或艺术评价。若前段只属 TRACE_REJECTED 或无可观察后果的 quiet，则不跳过它偷用更早的“确定前因”，而是将本次重规划标 SKIP，保留可审计回执。旧G不受影响，作者回改后滚动计划衍生列表随旧G快照回滚。最新[全量GREEN #40279156590](https://github.com/66tyu55/WriterForge/actions/runs/40279156590)有1808测试/10跳过/0失败。**尚未让新的G+V98开关完成真实DeepSeek创作，也没有任何证明它改善文学水平的A/B。必须保持默认关闭。**

## 3. 用户本次强调的最高优先级

**重点提升 WF 对实际文学创作的帮助，不是堆积新错误码、审稿模块、检查器和提醒话术。**

WF必须让AI像作家一样：真正根据已有情节推理人物知情程度、目的和冲突；已经行动过的事不机械重演；依照新写出的后果重新构思下一步；能主动判断哪里不满意、为什么改、删多少；只在真正需要时撤销旧稿及后代、让同一作者重新写。WF绝不能取代AI决定文学好坏、编故事、替AI写句子或强制修订。

目前核心待证假设：G在章节开头冻结整组六个beat，以致后面机械重复封套、换马和传令。0.AU的V98融合是针对这个假设的**可反驳工程尝试**，不是成功证据。

## 4. 下一窗口必须先做的 0.AV 真实文学 A/B

1. 先重新核实仓库HEAD、0.AU源码、全部原始模型provider回包及全量无模型回归；确认最新G+V98开关仍默认False，绝不擅自部署或修改main。
2. 事先冻结一个**全新**原创连续场景任务，然后以同一个DeepSeek Flash写作模型做对照。A为原G冻结多beat，B为G加 g_rolling_author_planning=True；双方相同人物前史、真实知识边界、创作任务、系统指令、正文输出上限及相近篇幅。B多出的V98规划请求必须单独记真实调用次数/总tokens；**不得谎称成本相同**。
3. 作者负责自己的构思、模型回复、事件选择、正文与是否回改；WF不得宿主生成计划内容或替模型补出“正确”因果。所有provider wire、prompt SHA、正文SHA、签名候选、实际V98新beat与SKIP原因、V119回滚来源完整保存。付款调用有严格硬上限，失败不覆盖原件。
4. **预登记文学效果指标**，不是只有状态GREEN：已写行为是否重复，前文后果是否真的推进人物选择，物件/时间/视角的连续性，是否为了满足prompt机械复述，小说语言、张力、人物真实性，安静留白是否仍自然。最重要：具体列出模型因前段真实动作而改变的next beat，并展示新后文是否比A更有文学价值。
5. 用真实可读文段并排对照，若篇幅可比则做双顺序盲评、明确单模型家族评委局限；评估应分开“文学百比分”和“来源/因果证据”。篇幅失衡或顺序大波动标 NOT_COMPARABLE，绝不拿正分奖励模型修稿。
6. **真正风险**：若上一段TRACE_REJECTED过多，0.AU会大量SKIP，最终G+V98可能根本不能滚动。必须统计真正执行V98次数和跳过比率，不可从更早的旧片段偷因果使绿灯看似漂亮。若原作家仍可在未知状态下思考“下一步可能怎么做”，应由同一模型提出明确未证的候选，而非自动升级KNOWN或强迫每次触发V98。
7. 先小批次1～2个任务检验有效性，成功后再扩不同类型；任何真实失败都保留 provider wire，以 RED→改原模块→GREEN 修系统问题，同时重新验证**文学表现**。不得重复0.AQ旧六段、旧十类原稿或原著15章。
8. 只有真实模型自己选择 LOOK_BACK_NOW、真正通过 V119 编辑实际上一段，且V114/V117/唯一NarrativeCore撤回旧后代、从新原文写出后文，才能写“真实自主回头闭环已验证”。模型选择 MOVE_ON 必须尊重；不准为了刷出修订而强迫改。

## 5. 硬边界与结果报告方式

- **只改** refactor-unified-scene-delivery-audit；不修改 main，不部署 Railway，不写用户 R2 原著，不写正式 Canon，不重复旧15章训练，不新增独立文学记忆/自动评分奖励模块。保留V26选择式写作、V98滚动构思、V119精确修订和唯一NarrativeCore。
- 区分三个层次：软件CI的GREEN、真实模型是否实际执行、文学质量是否可比地提升。只能按对应证据认领，不能相互替代。
- 一轮结论必须回答：WF到底改变了AI的哪一个文学思考行为？哪一段具体原稿体现了进步或退步？对照公平吗？若没有显著变化，哪个现有模块仍妨碍真实作家推进，而不是再增加一张提醒卡。

## 下一会话可以直接发送的指令

> 继续 WriterForge。先按顺序读取 docs/CURRENT_HANDOFF.md、docs/WF_0AV_NEXT_SESSION_LITERARY_UPLIFT_HANDOFF_20261026.md、docs/WF_0AU_G_V98_PROSE_DRIVEN_WRITER_PLANNING_20261026.md、docs/WF_0AR_0AS_0AT_REAL_WRITER_REVIEW_STAGE_LITERARY_UPLIFT_20261026.md。只在refactor-unified-scene-delivery-audit工作。重点立即实测0.AU G+V98是否让同一个模型在新的连续小说场景里真正写得比旧G好，优先比较实际行动重复、人物选择、真实后果、文学节奏，不再只增加提醒/检测。预登记同题同模型预算与原始证据SHA；发现系统错误走RED→修原模块→GREEN，同时验证文本表现。不复制重写0.AQ原稿，不重复十类、15章训练，不动main、Railway、R2原著、正式Canon，不让WF代AI写正文或下艺术评判。