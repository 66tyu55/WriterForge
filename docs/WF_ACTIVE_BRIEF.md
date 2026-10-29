# WriterForge 低上下文研发入口｜0.CM｜2026-10-29

**下个聊天先读本页，不要一次拉取 32 万字 `CURRENT_HANDOFF.md`。** 需要历史争议再按文件与行号局部读取，旧真实失败不能覆盖。

## 当前已实现

- 开发分支：`refactor-unified-scene-delivery-audit`；main、生产 Railway、正式 Canon 均未改。
- WF 负责文学阅读选择和写作辅助组织；宿主作者模型自主 USE/SKIP。不要训练宿主，不建立独立记忆/规则库/评价器，不替作者判断文学好坏。V26/V98/V119、唯一 NarrativeCore 不变。
- 0.CL 曾修复《镜花缘》衣着误检、安静日常误荐，真实过程见 `docs/WF_0CL_GENUINE_CLASSICS_ROUTING_AND_STOP_EVIDENCE_20261029.md`。仍有《韩湘子全传》花草讽喻错荐原创补衣场景的未解决负例，**不为刷分继续调硬编码**。
- **本轮 0.CM 内容增量**：五篇新古籍连续原文＋三条贴句批注＋开放心得：`experiments/wf_0cm_five_genuine_classics_original_annotation_reflection_20261029.json`，两篇《韩湘子全传》、三篇《子不语》，新原文 3,475 字（原资料末尾换行包含在原始片段中）。来源是 GITenberg 固定 commit/blob，必须按源 SHA 校验；非美国版权法辖区须重新核查使用范围。
- 用现有 Xuehai 追加五条：**126→131 条文学内容，78→83 篇完整三段式阅读**；追加脚本 `experiments/wf_0cm_append_five_source_pinned_readings.py`。源文件不改，旧 126 条的内容 SHA 保留，使用新 published 子快照而非第二套库。
- 0.CM 新持久 R2 库：`wf-0cm-xuehai-literary-131-20261029-v1`；snapshot SHA：`d5faee67a3ce4379b8790831ca4ad09314a6ed52cff493306467e20098d830af`；文学内容 SHA：`521386ca1c404cff6bdc81b9afa2132b5f54290f1c60af975a95b236fc69fb56`。旧 0.CF 库/快照仍然不变。CI [0.CM 新库发布与独立只读冷恢复 #40877467126](https://github.com/66tyu55/WriterForge/actions/runs/40877467126) SUCCESS。此前一次 RED [#40877060381](https://github.com/66tyu55/WriterForge/actions/runs/40877060381) 是旧 DB 附带非文学行导致错误地检查了“全库总行数=126”，随后改成仅统计文学 source_role，未修改古籍及取舍算法。
- **重要使用边界**：这是开发分支保存的新版 R2 学海快照；旧 `experiments/wf_0cg_existing_r2_to_real_writer_offline.py` 的 0.CF 固定实验引用仍保留作历史对照。**未切换正式运行时默认 R2 来源**，不能说生产写作端已自动读取 131 条。开发者可显式使用新 library/snapshot 恢复到原 DB，再沿原 `XuehaiStore`/WRITE 入口调用。

## 下一轮怎么继续（少而实）

1. **先内容**：每轮选 3–5 段真正不同的原文，尤其补生活、安静日常、人物关系、喜剧、社会琐事，不只继续堆志怪和仙术；来源连续、可原样校验，批注不空泛，心得允许质疑、反证、多解释。仅在既有 Xuehai 追加，保留旧版本。
2. **再可用性**：用新版 131/83 原 Xuehai 对真实作者创作问题试一次阅读投递；只看「有没有把完整相关文本交给作者、避免明显错荐」，不做另一套文学成绩表。发现真正失败才动 `xuehai.py`，不为每题 GREEN 调参。
3. **最后停止**：无可靠证据的新检索策略保持 NONE、未晋级或休眠；不启动模型重训／未知付费 API。工作记录只写本页短摘要；详细失败和证据写原实验文件，避免再次读完整多年历史。

**上下文节约**：用 GitHub `fetch_file(start_line,end_line)` 只读必要区间；CI 日志只取 ERROR/关键结果行；不要打印工具全 schema、原始 JSON 全文或数百 KB 交接。下一次会话用本页和最新变更文件即可。
