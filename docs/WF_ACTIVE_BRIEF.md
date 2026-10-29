# WriterForge 轻量最新交接｜0.CN｜2026-10-29

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
