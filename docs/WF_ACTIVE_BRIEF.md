# WriterForge 轻量最新交接｜0.CP｜2026-10-29

**下次先读本页前半部分，不要全文读取庞大的 `CURRENT_HANDOFF.md`。** 所有新代码与 R2 都只在开发分支 `refactor-unified-scene-delivery-audit`；main、正式 Canon、Railway 不动。宿主作者模型最终自行 USE/SKIP，不训练宿主、不重复建设存储/规则/文学评分体系。V26/V98/V119 和唯一 NarrativeCore 不变。

## 最新 0.CO—0.CP（2026-10-29）

- **0.CO 真实 bug**：`writerforge/xuehai.py` 过去先根据全局新旧顺序按角色取32条，古籍实际56篇导致24篇在文学问题比较前被排除。原 136/88 R2 实测 [#40883463393](https://github.com/66tyu55/WriterForge/actions/runs/40883463393) 确认。以既有《红楼梦》第三回饭席原文＋批注＋心得为真实来源、再插40条无关测试材料，旧代码 [#40884257009](https://github.com/66tyu55/WriterForge/actions/runs/40884257009) RED（相关旧读本被屏蔽）。
- **修复**：继续复用原 `XuehaiStore._candidate_rows` 的 SQL 有界池（每类最多512行），先用实际**批注＋心得**的独立文本证据做候选预选，再只交付最多32篇经过现有来源哈希、三段式与长度验证的完整阅读。保留每作品8篇限制、不用书名映射、不改原文、不降低三条独立证据门槛；超出有界池仍可能保守NONE，未来扩容应另核实而非不受限扫描。回归 [#40884556007](https://github.com/66tyu55/WriterForge/actions/runs/40884556007) GREEN；0.CI—0.CN 原有 CI 回归正常，[全仓 #40884556013](https://github.com/66tyu55/WriterForge/actions/runs/40884556013) **2101 tests，8 skipped，0 failures**。
- **安静照顾仍允许不荐**：0.CO 新旧真实读本核验显示王冕母子的文本确实在候选中，但原特定问题只有**两处**独立批注/心得词面关联；同类问题改写后有三处而可召回。不能为了刷该题把阈值从3降低、强制推荐或宣称“文学理解已提高”。
- **0.CP 内容新增**：`experiments/wf_0cp_four_lao_can_sequel_social_close_readings_20261029.json` 四篇《老殘遊記續集》原著连续片段＋12条具体批注＋4段开放心得：①高人道号的雅俗辩论；②客人猜错逸云与靓云的身份；③逸云谈去留、旧人情与旅行约定；④老残与姊丈赏花、作诗、打趣。共新增**2727 字连续原文**；GITenberg `lao-can-you-ji-xu-pian_56291` 固定 Git commit `bc807d8364509c7d682ed62ae46c2808cf6dc7b2`，原始 blob SHA `1c232e716d7b4fae637e1c209d8a45aa982cfc18`，只做匹配校验，不改动原文的疑似转录瑕疵。美国公版，其他法域版权另核。
- **实际学海持久增量 136/88 → 140/92**，只复用现有 `WriterForgeDB`、`XuehaiStore`、R2StudyVault，旧136条内容SHA与所有旧原文未变。新独立 R2 库 `wf-0cp-xuehai-literary-140-20261029-v1`，snapshot **`e425a2fe3809905b6d12c7c1c36e8f7647c2c4efd310364dc4ebe3b010de6ac8`**，内容 SHA **`5877223c8189e5136ebfb74ae4782845d0f67028c5784f1c223905de9dcabdf5`**。源锁定、旧源内容对比、92篇三段式全量读回以及全新 CI 冷进程只读 R2 恢复 [#40885794902](https://github.com/66tyu55/WriterForge/actions/runs/40885794902) 均 SUCCESS。0模型调用、0付费请求、0正式 Canon写入、0旧 R2 库覆盖；**未切换正式作者生产环境到新140/92**。
- 下轮只读 `docs/WF_ACTIVE_BRIEF.md` + 当前需要的源码片段即可，**不要重跑历史原始 RED、不反复付费实测、也不要为追求局部全绿调整文学口味**。若要补下一批内容，选不同题材公版原文3–5篇，贴字批注、开放心得；若要测作者写作辅助，只测读本是否如实送达和明显错荐，作者仍USE/SKIP，不能把工程正确等同文学品质成长。

---

## 上一轮 0.CN 历史记录（保留，不必在每次新聊天读取）


**换聊天优先读本页（约 3 KB），不要全文拉取 32 万字符的 `CURRENT_HANDOFF.md`。** 如须调查旧错误，再用 GitHub `fetch_file(start_line,end_line)` 局部读对应源码／实验及失败日志。当前开发分支：`refactor-unified-scene-delivery-audit`。

## 0.CN：本轮真实完成

- 按用户要求，停止反复宣称“文学能力提高”。**先补真实文学内容，再小修确有证据的 WF 调度错误**；不训练或替代宿主作者模型，不新增独立存储/元规则/评分器。V26/V98/V119 与唯一 NarrativeCore 保留，最终 USE/SKIP 权在作者。
- 文学新增材料：`experiments/wf_0cn_five_daily_life_classics_20261029.json`，**5 篇连续真实古籍片段＋15 条具体批注＋5 段开放心得**，分别为《儒林外史》王冕母子照料、第二十七回新婚厨房礼俗、第三十三回杜少卿夫妻春游、第四十六回虞博士送别，以及《子不语》第六卷《人同》异兽与主人离别。共 2,116 个原文字码（含选段边界），文字来源真实、未经过改写。来源固定 Git commit＋blob SHA，CI 原文件逐字节校验。美国公版；其他法域另核版权。
- 新增条目使用的仍是 **同一个现有 WriterForgeDB/XuehaiStore**，不是另一套方法卡或文学规则库：**131 → 136 条文学内容，83 → 88 篇完整三段式阅读**。追加脚本 `experiments/wf_0cn_append_daily_classics.py`（只读恢复 0.CM 后复制临时 SQLite，创建后继 published snapshot，检验前 131 条全文 SHA 不变）。
- 新的不可变 R2 库 `wf-0cn-xuehai-literary-136-20261029-v1`：snapshot **`ae522ac98ae083a7c59f1bf0823f712c5d757a9bec144bd91defd235938a2e2a`**；全部136文学内容 SHA **`6d48800a611834546107dea3c22aab50bee56b2824121abfc75a466c3ddd09ce`**。新旧全部 88 篇均用现有三段式读回接口检查；全新 CI 进程独立 R2 冷恢复成功。[最终 0.CN CI #40881854071](https://github.com/66tyu55/WriterForge/actions/runs/40881854071) SUCCESS。旧 0.CF 126/78、0.CM 131/83 R2 快照及其原文不动；main、正式 Canon、Railway 均未修改。
- **小型真实程序 RED→GREEN**：第一次使用现有只读 `_QueryOnlyDb` 查询作者推荐时报 `fts_enabled` 属性缺失（不是来源坏），仅在 0.CN 只读适配器关闭 FTS，保留原来正式 DB 功能；失败 [#40881311651](https://github.com/66tyu55/WriterForge/actions/runs/40881311651)。然后实际作者问题“怎样写不多言的照顾？用饭菜、衣着、劳作……带出人物之间的感情”因问号分隔，导致 `_author_craft_scope` 完全丢弃意图，首次固定 test [#40881698951](https://github.com/66tyu55/WriterForge/actions/runs/40881698951) RED。只在原 `writerforge/xuehai.py` 把**紧邻、确有叙事细节的写作要求**按语法连接，不增加书名规则。四项局部测试 GREEN，原 0.CL/CJ/CK/CI 全部 GREEN；[0.BL 全仓 #40881853975](https://github.com/66tyu55/WriterForge/actions/runs/40881853975) **2,100 项执行，8 跳过，0 失败**。
- **阅读调度真实观察而非“升级成绩”**：同一新版 R2 学海运行 `select_literary_reading_for_author`，按顺序「灶间安静照顾、师友送别、婚宴做鱼礼俗」返回 **`[NONE, classic-0cn-rl-04, classic-0cn-rl-02]`**。第二/第三题实际得到完整原文＋批注＋心得；第一题在修复分句范围后仍 NONE，属**仍未解决的弱证据检索/保守弃荐**，不可强称已召回王冕母子。确认源内容实际存在，保留本次 NONE 作为下一轮可能研究的负例；不要为凑齐 3/3 添加专属书名→技法、禁词表或增益评级。
- 本轮 0 个新作者模型 API、0 付费调用、0 模型训练、0 Canon 写入，不修改正式服务。以上只是来源、工程及调度实际行为，不是文学作品质量提升证明。

## 上一轮 0.CM 及历史定位

- 0.CM 已成功保存 **131/83**，R2 library `wf-0cm-xuehai-literary-131-20261029-v1`；snapshot `d5faee67a3ce4379b8790831ca4ad09314a6ed52cff493306467e20098d830af`，文学内容 SHA `521386ca1c404cff6bdc81b9afa2132b5f54290f1c60af975a95b236fc69fb56`；原文／心得来自《韩湘子全传》2、《子不语》3，见 `experiments/wf_0cm_five_genuine_classics_original_annotation_reflection_20261029.json`。
- 0.CL 《镜花缘》衣服揭势利漏检及安静日常误荐修复详见 `docs/WF_0CL_GENUINE_CLASSICS_ROUTING_AND_STOP_EVIDENCE_20261029.md`；《韩湘子全传》花草讽喻错荐原创补衣题仍未修复，**禁止追绿过拟合**。
- 当前**新的 136/88 并未自动切换正式作者运行时的默认库**。实验可以用 0.CN 新 library＋snapshot 显式恢复至相同 `XuehaiStore`/WRITE；原 0.CF 实验源应保持历史锁定。

## 下次继续（不要先造系统）

优先扩充 **另外一两个真实古籍来源**、多个不同日常/人情/对话/社会差序场景，每轮 3–5 篇连续原文＋贴字批注＋开放心得；只用已锁 SHA 的公版材料并验证原文。然后从作者实际构思入口读取 136/88（或其后续版本），自然观察能否找到有价值的读本。仅有可复现的跨例源码缺陷才小修 WF；不做文学品质绩效表，也不对少量留出题逐次调阈值。既有元 Skill 的可迁移、可证伪、可停止/休眠原则不变。
