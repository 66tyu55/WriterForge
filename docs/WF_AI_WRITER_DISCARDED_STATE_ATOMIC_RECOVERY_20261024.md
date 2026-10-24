# WriterForge｜删除真实来源后撤销物件、伤势、知情候选与失败原子恢复（2026-10-24）

**有效范围**：仅 GitHub 开发分支 `refactor-unified-scene-delivery-audit` 的 G `continuity_guard`，且 `self_edit_rounds>0`、`self_edit_timing="ai_decides"` 显式启用。其他 A–F、V26 选择续写与本地作者草稿、V98 滚动构思、V119 精确修订、V117 签名和现有唯一 NarrativeCore graph 不改。无新模型调用、无 R2/Canon 作者作品改写、无 Railway 部署或 main 更动。本轮是**确定性离线工程检验，不是模型文学训练或模型独立审稿能力证明**。

## 1. 原始问题：删除一句≠删除后果

一个未接受事件段可能产生 source SHA → V96 action/effect → V114 Novel Studio 物件/伤势临时 state → V117 连续性与开放债务 → 后段人物有限视角、来源提醒和最终热记忆。删掉前段“拿到火髓果”“右臂已经受伤”“告诉叶青梧秘密”后，倘若沿旧源继续，后段会无来源地拿着物件、继续残留伤势、把秘密当已知。这次不新增文学判决器，只让**原写作 AI 决定哪一段不满意**，然后原有 source-first 事务系统让状态从真实新稿重新建立。

## 2. 直接来源反例：每个断言都必须来自实际已写的新文

**新增 [test_wf_discarded_event_state_replay.py](../tests/test_wf_discarded_event_state_replay.py)** 五个纯离线用例：

- **物件转移**：先前真正得到 `火髓果` 于沈砚左手心，下一实际事件明确交到唐蜃手中。丢弃交付事件后，从上一个合法 V114 receipt 重新归约，持有人仍是沈砚；V116/V122 在传入明确角色 cast 后能阻断无交付却改称唐蜃持有。新的 V117 签名恢复后绝不以旧交付源 SHA 证明转移。
- **身体状态**：`沈砚右臂垂着` 的叙事事件产生 V116 候选“右臂受限”，删除之后重新归约不再含该状态；下一段使用右臂在旧版本被阻断，在新版本不会仅因已删掉的旧伤被阻断。**不等于程序证明医学合理性或人物是否该受伤**。
- **V117 开放债务**：原文本的剑穗无来源转移会形成 `UNPROVEN_ITEM_TRANSFER` 未偿候选；删掉该转移后仅从合法保留源重算，旧候选债务不继续带入新的 signed receipt。没有自动替人物“解决”债务。
- **统一人物知识**：经作者来源正式登记的 `UNKNOWN` 不可被未接受小说里“沈砚告诉叶青梧密令在井底”自动改成 `KNOWN`；删除该句后连非正式 disclosure proposal 也不应残留。统一 graph 的 hot memory 和 V117 resume 只锚定保留候选的源稿，仍由原同一个 graph 负责 FACT/UNKNOWN/THREAD。
- **全 G 循环**：人工模拟写作模型在第一段写实、第二段起草、主动 LOOK_BACK_NOW、提议 DELETE、第三次生成修正下游；以真正原 V114 reducer / V117 签名 / NarrativeCore 原 graph 验证新持有人、原正文与废稿存储隔离。模拟 reply 绝非 DeepSeek 实际文学选择。

补充：首次把齿间、手心、交付全部混入**同一次 Novel Studio 原子事件**导致 reducer 预条件拒绝。这一技术红灯如实保留，测试改为真正跨先后段的持有及交付链，**没有削弱或绕过原来的原子状态验证**。第一版模拟稿删句后少于现有 V96 80 字门槛亦被按真实文本范围纠正，未放宽限制。

## 3. 修订分支失败后的原子恢复

在原 `writerforge/writing_assist.py` 的 G 回路原地增加下列辅助函数，均不持久化独立叙事事实或生成一个字的正文：

- `_capture_unaccepted_turn_restore`：在确切 V119 回改前，快照当前尚未接受的上一段与本段界面所依赖的 V96 / V114 / V117 / 场景校验 / prompt / lamp / 计划审查已观察回执及前边界，不包括任何已正式接受作者的 Canon。
- `_rewind_unaccepted_turn_suffix`：只有原写作 AI 实际给出源锁定改稿，才暂时回到回改前的状态；AI 的重新写作必须从新原文出发。
- `_restore_unaccepted_turn_capture`：当重审后出错（明确的 V96、V114、V117、NarrativeCore、模型调用或来源预条件错误），将上一个**确实已观察、未被编辑的原候选**与所有下游回执一起恢复，再把原写作模型的当前原始答复重新经过原完整验证，不生成“替代正文”，不加一次请求来作弊过关。
- **原件安全**：原 `chapter-*-turn-*-raw.json` 不再被下游新生成覆盖。新分支回复另存 `-regenerated-01-raw.json`，原失败/替换提案、原模型答复 SHA、失效下一段原文留在 job 私有归档。失败不删除既有作者手稿，也不覆盖老实验。
- **计数**：`wf_self_edit_previous_turn_rewind_attempts` 记录真实尝试次数；`wf_self_edit_previous_turn_rewinds` 只数成功通过修订及下一段校验的回头。已经发出的模型请求永远计入原 job 总预算，失败不“退 token”、不偷偷重复调用。
- **取消权**：显式 WriterDraftCancelled 不被当作软件重试机会，继续保留作者中途取消/丢弃权。

**专项新增两个负例**：人为让修改后的上一段 V114 reducer 抛错，或让 AI 的下游重写回复不是合法 JSON；两条均在不新增模型调用下恢复旧第一段和旧第二段，V114 和最终 V117/graph 来源回到原候选，所提 V119 改稿只留在废稿私有记录，Canon 0。

## 4. 验收和全部红灯保留

- 第一轮负例 [#40075407455](https://github.com/66tyu55/WriterForge/actions/runs/40075407455)：1506 项中的两个红灯，分别来自错误合并原子物件事件和删句后文本长度不足；改为更真实的跨先后段源故事。
- 第二轮 [#40075680350](https://github.com/66tyu55/WriterForge/actions/runs/40075680350)：一个反例没有传入角色 cast，另一模型正文仍不足 V96 下界；两个失败均没有换成文学“放宽校验”。
- 真实的跨模块源删除与热记忆 [#40075791568](https://github.com/66tyu55/WriterForge/actions/runs/40075791568)：**1,506 项执行 / 4 skipped / 0 failures**。
- 第一次可逆事务全量 [#40076014846](https://github.com/66tyu55/WriterForge/actions/runs/40076014846) 与新增失败场景 [#40076099235](https://github.com/66tyu55/WriterForge/actions/runs/40076099235)：新增原子路径测试可以运行，但老 V121 检查源码精确缩进的结构性断言由于包裹 try/except 被触发失败；恢复对应行的非语义格式，**不改 V121 的来源/人物验证职责**。
- 最终 [#40076159662](https://github.com/66tyu55/WriterForge/actions/runs/40076159662)：**1,508 项执行、4 skipped、0 failures**；开发分支 workflow 的 `Do not use model credentials` 步骤通过，所有新答案均为人工编写的模拟供应商回答。

真实 DeepSeek 的旧结果仍是 [#40070821134](https://github.com/66tyu55/WriterForge/actions/runs/40070821134) 的第一段 prose+trace 非法时机回信、第二段有效文学原因却被 JSON wrapper 阻断，以及 [#40071088617](https://github.com/66tyu55/WriterForge/actions/runs/40071088617) 零新模型回放恢复第二段 MOVE_ON。**本轮没有新真实模型做过自发 LOOK_BACK_NOW / 删除 / 下游重写**，没有独立文学质量盲评。

## 5. 不得夸大的边界与下一步

1. 此次仅保护**同章紧邻上一事件段的 opt-in 一次回看**，并从该段到当下下一段做同步可逆恢复；不是任意先前两段/前章、多个角色在很久后返工的通用依赖图事务。
2. 可逆恢复覆盖 G 中 V96 / V114 / V117 / 统一图审查的**逐段验证失败**。若整章后续压缩、R2 私有归档或热/暖/冷跨章永久归档阶段出现外部异常，则仍遵循原 fail-closed；尚未证明所有这些磁盘/云端副作用可以做任意事务撤销。
3. 非流式 AI 仍只能在完成可观察事件段后作文学决定，不能宣称已经能读到隐藏计算中“写半句就反悔”。
4. 模拟用例验证来源一致性，不能证明写作 AI 真懂怎样删出更好的小说。下一步应继续研究更早已保存章节的 **StoryWorkTree/V117 依赖分支失效和中间故障的完整跨章原子性**，但需拒绝任何未获作者授权的旧 Canon 修改、R2 原书写入、自动新付费模型实验。
