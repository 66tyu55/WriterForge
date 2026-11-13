# WriterForge V57｜关系网络证据复核、底层修复与非文学回归（2026-10-18）

> 此文档只描述当前独立分支 `v57-relation-evidence-foundation` 的工程事实。正式 `main` 未合并；没有运行小说训练、R2 同步、模型、真实文学评价，也没有改写 V56 失败证据。

## 一、先核对未篡改的原始证据

- 入口：`docs/CURRENT_HANDOFF.md` 第42节和 `docs/V56_RELATION_NETWORK_INTERRUPTED_HANDOFF_20261018.md`。
- 原始 Actions [#39095760849](https://github.com/66tyu55/WriterForge/actions/runs/39095760849)：V55 9/9，V56 19项中核心11/12、扩展0/7，8个红项，严格检查按设计返回非零。
- 原始 V56 报告 JSON SHA256：`bc333be303d03c4ba642deb88944593dd39430a942a734cf637188ea105b6bc2`。
- 原始 ZIP SHA256：`539c8fe9087a76345bf8a2a0daa7e57c244c87c44b6b08d6430237ded4392f95`；Actions artifact ID：`12123489686`，原样保留于 [V56 artifact](https://github.com/66tyu55/WriterForge/actions/runs/39095760849/artifacts/12123489686)。
- `revision.no_fork` 原夹具违法引用未来时间8证据来声称时间2的 KNOWN，因此先触发正确时间护栏。原红项不改，V57新增合法的独立正反例，另添加数据库级竞争写入验证。
- 复核时主分支 HEAD 为 `d6ca4b769faa2ef2b47da91fb623a417be49de17`：在交接记录的 `a4f7b8d...` 之上仅增 docs-only 交接提交。V56 审计分支与正式 main 均未作为此次修复目标。

## 二、源码修复和可执行接口

实际修改 `writerforge/fact_journal.py` 和 `writerforge/cli.py`：

1. `KNOWN` 必须引用状态为 `KNOWN` 的已存在事实事件。ACTOR继续检查对应人物及故事时间；READER 除故事时间外，必须有明确叙述披露：事件 `REVEAL` 或叙述者 `narrator` 的 `OBSERVE`。私密 `THINK` 不自动视为对读者公开。
2. `register_scene(story_id,scene_id,chapter_index)` 建立显式、不可悄然换写的作品与章节绑定。不同场景仅在同一明确绑定作品时可连图边；未绑定或不同作品仍拒绝。作品级 `temporal_view(...,story_id=...)` 用显式相同 `subject_id/fact_id` 查询跨章知识；普通 `scene` 查询仍保持原来隔离。
3. `append_flashback(...,story_id=...)` 是单独、必须先绑定作品的写入 API，允许真实故事时序早于先前导入的事件，却从不改写事件；数据库记录摄入序号与故事时间分别保存。原普通 `append()` 的禁止倒填规则继续有效。
4. `temporal_view` 使用64条批量扫描，最多检查8192条、输出每类最多64个引用，同时计算完整的被检查状态集合与有效数量；大于预算依旧拒绝，不能用截断记录给出虚假无冲突结论。V55原始同时间矛盾、版本记录时间回放仍保留。
5. `temporal_claims(supersedes_id)` 增加 SQLite 部分唯一索引，防止两个连接绕过先检查再插入的竞争窗口；与原有追加不可覆写规则叠加。数据库里的既有非法分叉会在迁移建索引时暴露，而不应被悄悄抹平。
6. CLI 已开放 `fact-story-bind`、`fact-flashback` 和 `fact-view --story-id`；新增端到端测试证明并非只在测试层有新函数。

示例（仅结构化元数据，命令不会下载 R2 或运行文学训练）：

```bash
writerforge fact-story-bind --journal data/relations.sqlite3 --story-id novelA --scene chapter01 --chapter-index 1
writerforge fact-story-bind --journal data/relations.sqlite3 --story-id novelA --scene chapter03 --chapter-index 3
writerforge fact-record --journal data/relations.sqlite3 --file typed-event.json
writerforge fact-claim --journal data/relations.sqlite3 --file typed-claim.json
writerforge fact-view --journal data/relations.sqlite3 --story-id novelA --scene chapter03 --scope ACTOR --subject hero --fact seal --story-tick 25
writerforge fact-flashback --journal data/relations.sqlite3 --story-id novelA --file typed-earlier-event.json
```

## 三、真实CI、代码哈希与未覆盖证据

新分支 GitHub Actions [#39100156422](https://github.com/66tyu55/WriterForge/actions/runs/39100156422) `success`：

- V54原有12项通过；V55原有9项通过；V57新关系网络12项通过：**33/33 合成结构性回归通过**。
- 新报告 `v57_relation_regression_receipt.json` SHA256：`327a661d0ee7f5da6749f8be5b29a6d97d0efcac723a323fa28b9eafdf99e485`。
- `writerforge/fact_journal.py` SHA256：`41163dc6002ac4b6c5e79f28acb7f580c2fea5ee5f20bfb0794205d1f42b6ad4`。
- `writerforge/cli.py` SHA256：`7c98a1b5bfc308716f0926a827efa705040b768e6d79c26d3499a0f268977ea3`。
- `tests/test_v57_relation_foundation.py` SHA256：`8a3e98007fbfc5609f6e1bb7ac2684fd401f5909edad6d7792b96e52c353bc1f`。
- `scripts/audit_v57_relations.py` SHA256：`f2e71f67450b4530ee4a8c78db864d9de368aae52324a1ee436e98a035de269b`。
- [V57 新证据 artifact](https://github.com/66tyu55/WriterForge/actions/runs/39100156422/artifacts/12125889031)：ID `12125889031`，ZIP SHA256 `7b40250e3262a01a02d50563913b66bfa5e5c5196a8ee546e804b6eac6dc67ff`。
- 第一轮 V57 红色运行 [#39099818429](https://github.com/66tyu55/WriterForge/actions/runs/39099818429) 保留：新测试曾错误使用单字母事件ID，违反原本的ID最小长度规则；修正新夹具后才通过。此前报告不覆盖。

V56 冻结脚本在原隔离审计分支仍然保留、严格检查仍代表**旧接口下的原始失败事实**。新 V57 需求中，跨章及倒叙必须有显式作品身份与导入调用，因此绝不把原V56缺少这些输入的失败改写为 PASS。

## 四、未解决/不许冒称完成

- 以上全部是合成的结构化事实和代码行为。没有检验真实小说中人物指代、伏笔/回收、动机或因果关系的独立文学语义。`POTENTIAL_CAUSE` 仍然只是未证实关系。
- `narrator`、`REVEAL`、`story_id`、`subject_id` 是经明确输入的**声明**，不能由 SHA 证明陈述可信，更不能从关键词索引自动推断它们；未来需要来源签名/审阅权限与披露证据鉴别。
- V57 `temporal_view` 的8192条扫描保护仍可能拒绝超长历史；旧 `state()` 的64条保护和图邻域48边/最多3跳保护未改。若要继续扩容，必须进一步采用稳定分页游标与证明完备的流式归并/快照，不能直接删除安全预算。
- 已登记的跨章场景不等于角色身份真实解析；未知跨章指代、同名人误合并、跨章节事件修订、跨作品迁移仍需新的反例。
- V49 的 `THIRD_STRIKE_FAILED` / `NO_PROMOTION` 持续有效。未训练R2、未请求模型、未触碰原著、未合并 main；不能借工程回归授予自主文学写作晋级。

## 五、后续顺序

保留以上新旧哈希，对V57先做安全审查及更多负面反例（不同作品同名角色、跨章多次状态变化、结构化来源伪造、长历史分页游标）。待明确审核后才能讨论是否合并；不要重复任何旧付费文学训练。
