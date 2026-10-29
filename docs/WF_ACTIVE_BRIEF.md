# WriterForge 最新轻量交接｜0.CR｜2026-10-29

**下一聊天只需先读本页，不要完整拉取冗长的 `CURRENT_HANDOFF.md`。** 开发分支 `refactor-unified-scene-delivery-audit`。目标是 WF 自己能更可靠地组织、检索、提供真实文学读本，长期积累而非每次证明宿主模型“写作水平提高”。宿主作者模型自主 USE/SKIP；不训练模型、不新建学习/记忆/评分器，不触碰 main、Railway、正式 Canon，保留 V26/V98/V119 与唯一 NarrativeCore。

## 0.CR 修复：心得“假设性问题”不能单独作为荐文证据

- 先冻结 9 道跨题（承诺/风险、猴群玩笑、花田、市井负例与技术拒荐）：`experiments/wf_0cr_frozen_author_reading_cases_20261029.json`，冻结提交 `c91399d2bf04aa31d2f7c94de440902d491391d4`，此时**未修改生产检索器**。真实 R2 145/97 首次只读观察 [#40888929745](https://github.com/66tyu55/WriterForge/actions/runs/40888929745)：一次“危险下守诺”错误选《西游记》猴群游戏立约；“渡船接人又遇追兵”选到《老残游记续集》赏花闲谈；其他跨作品选择也有可争议处。诊断脚本 `experiments/wf_0cr_source_only_mismatch_probe.py` 只读 source ID、小词面证据，不给文学质量真值。
- 根因之一已经有原始证据：猴群读本与守诺题共同的“以后、承诺、遵守”**全部来自心得的假设性追问，实际三条批注零直接词面联系**。固定真实《西游记》与《世说新语》完整原文＋批注＋心得的测试 `tests/test_wf_0cr_anchored_annotation_selection.py`，首次 [#40889432425](https://github.com/66tyu55/WriterForge/actions/runs/40889432425) **2 RED**。保留游戏式猴群探险本应选《西游记》、技术任务不荐文学的正确对照。
- 只在原 `writerforge/xuehai.py` 候选选取及验收中加入**至少 1 条来自真正批注的独立文本证据**；心得仍参与匹配、不能单独支持。早先试用“至少2条批注证据”使旧0.CI《老残游记》观众期待场景误失，历史 [#40889569819](https://github.com/66tyu55/WriterForge/actions/runs/40889569819) RED，**已退回更保守的1条限制**并真正回归。小测5项 [#40889839898](https://github.com/66tyu55/WriterForge/actions/runs/40889839898) GREEN；旧0.CI [#40889839887](https://github.com/66tyu55/WriterForge/actions/runs/40889839887)、0.CJ/CK/CL/CO/CN 全绿，[全仓 #40889840050](https://github.com/66tyu55/WriterForge/actions/runs/40889840050) **2106 tests / 8 skipped / 0 failures**。
- **没有假称底层已学懂语义**：在完整真实145篇内容的原冻结9题回归里，旧猴群错荐虽被移除，但“危险下守诺”仍可能选到《子不语》或其他弱关联读本，真实渡船题仍可能选赏花读本。旧反例和当前残留都保留；不要为了本次9题追绿继续添加中文停词、书名→技法表或降低归因门槛。优先多来源新证据，必要时允许NONE。

## 0.CR 新内容与持久保存

- 在此前已锁公版原文中新增三篇完整三段式阅读，原文+3条贴句批注+开放心得，文件 `experiments/wf_0cr_three_courtesy_childhood_mourning_readings_20261029.json`：
  - 《浮生六记》夫妻间礼貌与玩笑的争执：不是把“尊重”判对错，而是看原话如何使日常关系变化；
  - 《浮生六记》儿童蹲在草间，蚊成鹤、蛤蟆成怪：实际视角与幻想交错；
  - 《世说新语》王戎、和峤丧礼：悲痛的仪式与身体损耗不能直接等同。
- 沿用**唯一原有 XuehaiStore/DB/R2StudyVault** 的现成追加器 `experiments/wf_source_pinned_literary_incremental.py`，只扩充为兼容两个**事先固定格式**的内容包、修复新增 ID 与旧 ID 区分，未新建文学模块。原著 GITenberg commit／blob SHA 仍逐字节验证，旧145条文学内容SHA未变；从 **145→148 条、97→100 篇完整阅读**，旧 R2 版本保持可用。
- 新独立 R2 库 `wf-0cr-xuehai-literary-148-20261029-v1`，snapshot **`20d92659e1c4b6c53acd25ca3817903275a2110651fdb9d48c6996227d05f428`**；全部148文学内容 SHA **`0a4ea0f0c70491b219665f40e4169cf30e7f9c8206cca20a12bbda394cee14db`**。新库成功发布、全部原始文学／100篇三段式读回、独立新 runner 冷恢复 [#40890706819](https://github.com/66tyu55/WriterForge/actions/runs/40890706819) 全绿；旧0.CQ 145/97 新增器 [#40890706939](https://github.com/66tyu55/WriterForge/actions/runs/40890706939) 再次回归全绿。0模型调用/付费、0旧 R2 覆盖、0正式 Canon 写入。**正式作者环境尚未自动切换到148/100**。

## 下一轮：继续小批量内容，错误自然收集

每轮再加3–5篇不同体裁真实古籍／原创不同细节，必须完整连续原文、贴句批注、开放心得与真实来源SHA；保留真实文学的不同可能解释，不让WF代替模型判断文学好坏。若研究同舟错荐，只能在**新冻结、不同作品问题**上验证是否存在可迁移的通用修复；不要反复用0.CR九题刷全绿。其他历史见前轮 `docs/WF_0CL_GENUINE_CLASSICS_ROUTING_AND_STOP_EVIDENCE_20261029.md` 与旧 `CURRENT_HANDOFF.md`。