# WriterForge 0.BL｜P0 学海方法卡真正进入作者正文：实施与限制交接

日期：2026-10-28。只在 `refactor-unified-scene-delivery-audit` 实施。**这是检索和真实写作调用链的研发结果，不是文学能力增长证明。** 不修改 main、Railway、生产 Canon、私有 R2；未调用新的付费/小模型，也未导入古籍或任何现代表版权小说原文。

**最终综合 CI GREEN**：[WF 0.BL #40685907461](https://github.com/66tyu55/WriterForge/actions/runs/40685907461)：原16条待审卡 STAGING 子流程、来源/许可方法卡12项定向测试、真实G三臂脚本回包、整仓 **2,047 tests，6 skipped，0 failed**；使用的 writer/G mock 回包不算文学收益，未调用新付费模型。代码 GREEN 对应提交 `ff68c670`；后续文档提交不修改产品源码。\n\n## 一、真实源码检查与最初失败

阅读 `CURRENT_HANDOFF.md`、`WF_0BL_NEXT_SESSION_XUEHAI_WRITE_USE_HANDOFF_20261028.md`、`WF_0BL_XUEHAI_SCENE_ATLAS_AND_CLASSICAL_TEXT_PLAN_20261028.md`，审计 `XuehaiStore`、`VerifiedWritingFlow.prepare()` 及 `AutonomousWriting.run()` 的章节规划、single 正文、continuity_guard / V98 G 事件规划、滚动重构和真正正文回合。

最初 `XuehaiStore` 只保存来源证据和元数据，没有经来源/许可/审核约束的可迁移方法卡，更没有把这种方法送进真正模型正文。先提交 `tests/test_wf_0bl_xuehai_methods_write.py`，在 GitHub Actions [RED #40683363145](https://github.com/66tyu55/WriterForge/actions/runs/40683363145) 观察到缺少 `add_method_card` 的真实失败，而不是虚构 RED。

第一轮全量 [GREEN #40684256634](https://github.com/66tyu55/WriterForge/actions/runs/40684256634)：2,043 tests，6 skipped，零失败。这是离线代码回归，不是模型收益。

之后新增“裸模型 / 真正 G 核心 / G 核心+学海”的**脚本回包**机械路由测试。第二次 [RED #40685130126](https://github.com/66tyu55/WriterForge/actions/runs/40685130126) 真正发现了首次实现的跨通路污染：一次实际 G 中 5 个请求里，有 4 个包含了学海方法，包含非正文的事件规划和 V98 重规划；不能靠改断言或给规划模型硬塞技巧修复。

## 二、已实施的最小来源→方法→作者闭环

1. `writerforge/db.py` 在**原有 WriterForgeDB** 新增 `xuehai_method_cards`，按 entry_id 关联 `xuehai_entries`，记录 snapshot、work / source / unit SHA、来源定位、scene_type、scene_facets、目标体裁、触发细节、人物行为机制、可选写法、适用/不适用条件、有限 POV、反例、底本、rights / review / value 状态、审核凭证哈希、card_sha256、revoked_at。不新建第二套记忆。
2. `writerforge/xuehai.py` 增加 `add_method_card`、`query_methods`、`revoke_method_card`、genre_lineage。LEARN 限定 staging 添加、WRITE 限定已 published lineage 读取。要进入 WRITE，必须有实际 `OriginalStudy.ingest` 的 studied chapter + source span，与方法 entry 位置/版本/哈希相符，review= `PILOT_APPROVED`、rights= `RIGHTS_VERIFIED`、value= `UNPROVEN_PILOT`，没有撤销或篡改，也不允许用户私有 `r2://` / `s3://` 来源。纯参考、待审、未明确授权、未学、STAGING 方法全部 **NONE**。**PILOT_APPROVED 只意味着隔离测试资格，并非证实文学有效或正式人工评审已完成。**
3. 识别16类玄幻场景及其别名、scene_facets；体裁回退例 `修真→仙侠→玄幻→广义叙事`，不自动跨入志怪/古典时代文风。无触发则 NONE；有界检索先按场景过滤，再至多考虑128条候选，避免库存增长时未相关记录抢占候选窗口；最多选1—2张（同一作品不重复），新增方法上下文最多300字符。提示语明确“作者可自行选择不采用”，不复制来源原文。
4. `VerifiedWritingFlow.prepare(..., xuehai_methods_enabled=True)` 可直接交付可选方法及选/拒原因、snapshot/source/card SHA 的 manifest；默认 OFF。原作者写作核心 `AutonomousWriting.run(..., xuehai_methods_enabled=True)` 是**显式启用**，默认同样 OFF；保留 B 组完全不启用学海的实测对照。方法不会独立计算剧情或替模型删改。
5. 特别注意 **G 真实正文入口**：`body_base` 同时被用于本章事件 JSON 与 G/V98 滚动重规划。正确修复是基底不带学海；只在 single 的正文请求或分回合 G **第一条实际正文**给可选方法。G 使用现存的低优先级 creative cue 投递预算，不改变 `_prepare_guarded_turn_packet` 的来源 / 因果 / 角色状态优先级和已签名的 delivery receipt。预算不足就丢弃方法，写入 `NONE_OR_DROPPED`，不能假装使用。章节回执包含实际作者正文请求 SHA；JSON 规划不接受技巧上下文。
6. 实际作者送达属于 prompt / 回执的证据；**模型是否采纳**以及写得是否更好，目前都没有正面证据。

## 三、16条原创玄幻与古籍状态

- `experiments/wf_0bl_stage_original_xuanhuan_xuehai.py` 用**独立新 SQLite**关联16张 `AUTHOR_CREATED_DIAGNOSTIC` 方法假设，`review_status=PENDING`、`value_status=UNVERIFIED`，对应 xuehai_entries 仍为 STAGING，published=0、studied_chapters=0、WRITE可选=0；不得改写为“已学名著”或自动推进。
- 仅在**隔离单元测试**里调用 `OriginalStudy.ingest()` 摄取一份真正由 WF 新写的原创炼丹源或石桥源；派生子快照，并在该隔离 DB 做 `PILOT_APPROVED` 路由演示。它们不是从《凡人修仙传》或其他现代名著学习来的。
- 5组古籍参考目录仍是**待核准的篇章/底本/电子编辑层权利**，本轮古籍原文新增导入为0；现代小说私人 R2 未读取。

## 四、验收、反例和真实成本

代码测试集中在 `tests/test_wf_0bl_xuehai_methods_write.py` 与 `tests/test_wf_0bl_true_g_author_method_branch.py`。覆盖原始 LEARN→snapshot→WRITE、来源和卡 SHA、授权/审核隔离、STAGING不可用、体裁时代不混、无关家庭 NONE、撤销、作者显式关闭、提示词无原文连续14字符片段、规划与 G 重规划未受污染，以及真正 `AutonomousWriting.run(..., draft_mode="continuity_guard", g_rolling_author_planning=True)`、唯一 NarrativeCore 的执行与回执。

G 三臂**脚本回包**实际回放为：A bare 1次、B G核心 5次、C G核心+方法 5次，所有回包均为 `SYNTHETIC_TEST_ONLY`，因此 provider authenticated wire=0、真实 token/美元费用=未知、文学胜负=未定；不得把机械回归的数字写为真实文学能力评分。

需要真实三臂时，预先登记**同一真实合格作者模型、相同原创任务及同一源快照、同一最大请求/总 token 预算、同样的 G/V98/NarrativeCore/可选 V119 设置**，B 明确关闭方法，C 只开启允许使用的审核卡。若被拒/无命中，C 实际退化成 B，应标记不合格对照而不是捏造治疗。记录原始 provider request/response SHA、实耗 input/output token、实际计费与超限、中断及未投递/被拒绝的具体原因（无需隐藏重试）；检查原文复制和任务长度合规。先一个全新场景探索，再跨炼丹、阵法、宗门、交易、安静/有限POV等不同场景做人类独立盲评。评估因果真实、人物动机、细节作用、有限认知、自然度、新颖性及成本；出现复制/同文复述/显著退步/高成本立即停止，不以测试通过或“多了几张卡”宣称成功。

**停止闸门：现阶段没有获准用于新文学收益测评的真实作者模型/调用上限与费用**。所以仅能完成机械闭环；不擅自触发付费模型、旧GLM 429、弱小模型重测或自动晋升正式 Canon。

## 五、下次直接续接（别重复今天）

读取本文件、`CURRENT_HANDOFF.md` 和最新 P0 CI 状态。优先完成古籍正式底本+权利审计后**少量真正审查过的条件性方法卡**，不要批量灌16个未审诊断。若获得显式真实模型预算，再启动新的三臂文学实验，并**以是否有足够文学收益抵消方法上下文与额外模型费用**为主要取舍依据。不要重复今天的 RED 接口测试/静态三臂假结果，不修改 main/Railway/Canon/R2。
