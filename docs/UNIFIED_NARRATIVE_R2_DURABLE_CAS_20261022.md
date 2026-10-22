# WF 统一叙事核心 — 私有 R2 原文、冷索引及跨机器续写

日期：2026-10-22。开发分支：`unified-core-r2-durable-memory`，从 `refactor-unified-narrative-core` 派生。生产 `main` 未修改，Railway 未部署。

## 目标和真实实现

原本 WriterForge 的 3 章热缓冲、8 章温记忆与本地冷 CAS 能保存原稿，依旧依赖当时运行机器的 `candidate.md` 文件。重启机器、跨运行器续写时，冷记忆即使存在索引也无法验证/恢复原文。

本轮 **不增加新数据库或新叙事状态拥有者**，直接扩展旧的 `writerforge/r2_storage.py` 和 `writerforge/narrative_core.py`：

1. `R2NarrativeMemoryStore` 继续复用旧 R2Config 和 R2StudyVault S3 私有客户端。所有新对象只存在 `writerforge/v1/narrative-memory/v1/<scope SHA>/`，项目/场景被稳定哈希隔离，原有 R2 library/index/小说原著对象没有覆盖。章节原文放 `sources/<sha>.txt`，冷页放 `capsules/<sha>.json`，完整 V117 带图续写快照放 `resumes/<sha>.json`。每一个对象写完必须通过独立完整远端 GET 与 SHA 校验才能生成引用，不使用不可信任的 `latest` 可变指针。
2. 原有 `record_chapter_memory()` 接受可注入的 `source_writer,source_reader,archive_writer,archive_reader`。先验证本地已保存候选，再上传整个原文；热记忆/温记忆只保存有 SHA 的私有 R2 locator，仍不把压缩文本当事实。如果远端上传或读回失败，抛错，原始 candidate.md 保留；只允许内容地址的重试，绝不能虚报已持久化。
3. `recall_original()` 和 `relevant_history_context()` 在新的独立进程中，利用同项目同场景的 R2 读取器回到原文；跨项目、跨桶、SHA 篡改、未配置 R2 backend 都 fail closed。原来本地内存档案保持兼容，不强制所有用户使用 R2。
4. 除原有全链 `cold_head`，当前新增**按稳定叙事节点 keyed 的 cold_node_heads**；归档时单个冷页存节点上一次相关归档指针 `node_previous`，旧伏笔回归时只按对应节点的页链检索。临时页缓存在一次请求内，避免重复下载。已有不带节点索引的历史快照被迁移为 `cold_index_complete=false`，保留旧链全扫描回退，绝不能把缺少索引当成不存在的伏笔。
5. `AutonomousWriting.run(..., narrative_memory_backend='r2')` 仅在作者选择带统一图的 `continuity_guard` 时开启云端记忆。章节完稿后由既有 WriterForge 代码保存原稿，再持久化源文和有 SHA 的 V117 resume。下一次调用可将上一个 `v117_r2_private_resume_ref` 作为 `resume_story_checkpoint` 参数，在任意装有正确配置的私有 WF 实例续写。没有 R2 认证不能读取私有远端引用；密钥绝不写入原文或 resume。
6. 补充 `tests/test_unified_r2_memory.py`：模拟 R2 存储 28 章后删除所有本地原稿；新客户端恢复 V117 + graph + 第 1 章原文，按节点回查不应下载十余页无关冷档；错误桶/跨项目/篡改/失败写入必须拒绝；旧本地历史索引也应保持可读。
7. 真正私有 R2 冒烟验证脚本 `experiments/unified_core_r2_live_smoke.py`：只上传隔离运行 ID 下的**完全合成**一章、一个冷页、一个 V117 resume；再由独立客户端读取。严格要求已知 WF 私有 bucket 名，绝不复制现有私人作品和其它书库，脚本公开日志只输出固定白名单字段和合成文本 SHA。

## 已观察测试与效能（不要混淆测试版本）

最早的云端功能验证 CI：https://github.com/66tyu55/WriterForge/actions/runs/39792584714
两个 job 成功：
- live R2：真实私有 R2 已上传并经另一个新客户端读回合成原文、冷页、V117 恢复凭证，3/3；
- offline full regression：1384 tests run，4 skipped，0 failures。

**注意：该运行对应初始 R2 接入版本，并不包含后来新增的 per-node 冷索引与旧快照兼容优化。**最新索引版本必须以它自己的分支 HEAD 全回归结论为准，不能借旧绿灯认证新源码。GitHub 并发组配置为 `cancel-in-progress: true`，以避免每次推送都消耗一轮测试性 R2 存储请求。

## 重要边界

- 这是私有云**持久存储与来源回查**，不是“已自动理解任意百万字中文小说”。人物动机、秘密、道具、伏笔等可靠更新仍需要明确原文证据及按授权边界复核；不能靠 AI 自评把摘要升级为文学事实。
- 当前热/温缓存仍采用既有边界：3 章热缓冲、8 章温记忆。冷页面可在既有可校验列表中增长，但是热图依然最多 96 节点、256 关系，超限拒绝而非悄悄丢弃。大型多卷小说需要进一步分卷热图/冷图分片，不应把全部节点都塞入单个模型提示。
- 新的 R2 `r2://...` 是**私有 CAS 引用**，不是公网文件地址，也不应放到公开 GitHub README 或日志里。历史原稿仍保留完整、并以 SHA 按需读取。SHA 检测数据变化，但不是账号访问授权；权限由原有 R2 私有凭证控制。
- 模型端的云接入与 R2 是独立问题：已有 WF WriterForge `local_chat_completion` 仍默认只允许本地 HTTP loopback；不要误称切到 R2 就能让其使用 Discovery 云 API。前一次真实 Discovery 压缩小试验中 intern-s2 超时、DeepSeek 返回 HTTP 429，因此没有可验证摘要；未来如要做真实章节压缩，应单独处理明确授权的云模型调用预算。
- 本轮绝未写入老 R2 书库索引或旧模型原稿；只允许上述独立前缀的合成烟雾测试对象。没有 Railway 部署，没有生产 main 更改；所有真实 AI 调用本轮为 0。

## 索引优化终态离线验证

新增后续 per-node 冷索引、Legacy fallback 及 28 章独立私有 R2 模拟客户端回归。完整脱敏离线校验：
https://github.com/66tyu55/WriterForge/actions/runs/39793854484
（`full-regression-offline` job 1,385 tests run、4 skipped、0 failures；`isolated-live-private-r2-synthetic` job 同样已完成 success，三类合成 CAS 对象均完成远端 readback）。对 17 页无关冷页、1 页真正相关的合成场景，用节点链约束旧线索回查 R2 GET 次数不超过 4；旧快照缺少节点索引时依然走有界历史链，不把索引缺失判为故事事实消失。

上述最后一轮 live R2 smoke 已实际成功，报告所有三类合成 CAS 都通过远端读取验证；早期 #39792584714 也已通过。两个 GitHub CI jobs 均为 success；生产 main 与 Railway 均未修改。
