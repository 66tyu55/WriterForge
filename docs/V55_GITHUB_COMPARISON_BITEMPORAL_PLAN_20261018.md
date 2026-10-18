# WriterForge V55 · 先查成熟架构，再最小改造现有事实账本

日期：2026-10-18。仓库基线 main `dbda27f5fd6cbe1aa8b392296e85c744ea421926`。本轮没有文学训练、没有任何语言模型调用、没有删除或修改旧 R2/V49 失败记录，也没有安装任何第三方图数据库。

## 冻结后的 GitHub 源码对照

| 参考项目 | 已核查的真实实现 | 适用于WF | 暂不引入 |
| --- | --- | --- | --- |
| getzep/graphiti（Apache-2.0） | graphiti_core/nodes.py 的 Episode/Entity 节点以及 edges.py EntityEdge 中valid_at/invalid_at、episode关联 | 把事实在故事中成立的时间与系统何时记录独立，引用真实来源 | 数据库驱动、LLM关系抽取、embedding、Neo4j/FalkorDB依赖与大型图维护 |
| danjdewhurst/story-skills（MIT） | docs/project-format.md 的 knowledge-state/learned-in，角色知道但读者尚未看到的标记，以及连续性测试 | 角色与读者独立知识、跨章节时点校验、刻意错误的负例 | 整套24 Skills、YAML/Markdown文件库和完整出版系统 |
| pyeventsourcing/eventsourcing（BSD-3-Clause） | README 的aggregate/domain event/snapshot/upcaster设计 | append-only与as-of投影，以及不可覆盖的变更历史 | 新增独立服务/ORM/第三方事件存储框架 |
| ace-agent/ace（Apache-2.0） | README的增量delta、helpful/harmful记录及版本维护 | 候选经验将来仅增量修订、保留错误轨迹 | 模型驱动Reflector/Curator、自评分即升级与大规模上下文手册 |
| microsoft/graphrag（MIT） | 索引流程将TextUnit→Entity/Relation→Community等分层；标准抽取需要LLM | 文档和结构化主张分层的设计思想 | 付费LLM抽取/摘要、embedding/向量库、大规模完整图构建 |

以上借鉴的是**原理和数据界限**，不是复制任何第三方源代码。许可证已核查，依赖没有改变。

## 对照发现的现有WF根因

- V54 `FactJournal.fact_events`仅有一个`tick`，在不同场景下易混用：故事内部时间、记录入库顺序、人物在何时知道信息，甚至源码扫描先后。`state()`只能按同一个tick取记录；如果现实里后来才掌握修正证据，旧时点的叙事认知与新推断容易混淆。
- V54 `structural_observer.observe_corpus`按索引返回次序生成BEFORE事件边。这是**严格错误的抽象**：同一术语在小说文本先后出现，不意味着被描述的事件先后发生；倒叙、多线叙事、人物回忆都构成反例。
- V54有潜在因果关系`POTENTIAL_CAUSE`但没有独立因果真值，不能从书目词频或图边自动晋级文学技能。
- 让候选经验直接修改核心代码/写作请求会重复V49第三次终审的错误，因此V55图谱仅供证据管理，不开放写作自动资格。

## 最小代码修改（不引入新服务）

1. 只在既有`FactJournal` SQLite增加一张`temporal_claims`及复合索引。不覆盖现有`fact_events/fact_links/pattern_versions`，因此旧V54数据仍可原样查询。`recorded_seq`表示WF实际入库顺序，`story_from/story_until`表示在故事时间中声称成立的区间；这**不是LLM推理的事实有效期**，是由调用方明确提交的有界结构记录。
2. 支持`ACTOR`与`READER`独立知识域，前者必须引用同一人物的真实已有`fact_events`事件ID；`KNOWN`不能早于它的学习证据事件；索引机器`index_witness`只能证明文本出现，不能冒充人物或读者真的知道剧情。
3. `append_temporal_claim()`只追加：后来的记录可`supersedes_id`修订过去相同作用域/时间区间的主张；旧版本不删除。`temporal_view(story_tick,as_of_recorded_seq)`支持在指定故事时间、指定入库版本双轴查询，未消解冲突返回CONFLICT_UNRESOLVED；不会把读者和角色知识混合。
4. 复用已有`FactJournal.link()`存储BEFORE/POTENTIAL_CAUSE/CONTRADICTS，新增有界`graph_neighbors(depth<=3)`查询和边/事件SHA完整性检查。任何潜在因果边的返回均明确`narrative_causality_verified=false`，不会生成文学解释。
5. 修订`structural_observer.py`：删除由索引命中顺序生成BEFORE的逻辑。只保留源文结构事件及SHA定位；原始词面事实不能自动形成故事时间关系。
6. 正式CLI增加 `fact-claim`、`fact-view`、`fact-graph`，保留旧`fact-record/state/link/candidate`接口不变。用户若没有显式提交结构化事实，不会从任意原著文本靠模型自动猜测人物意图。

## 测试合格线

- 迟到的证据修正过去故事区间但能按旧记录版本还原历史；同一时间同一事实独立反证不被自动消除。
- 读者知道/角色不知道分别查询，拒绝未获知事件提前泄露；来自文本关键词索引的假知识必须拒绝。
- 关系图能递归检索实际已记事件的联系，越界关系/篡改日志或边均拒绝，因果真值始终未验证。
- V54基于原著、真实SQLite与资源许可的测试不退化；不重训任何原著，原始证据不重写。

## 尚不能声称完成的能力

当前只管理**被形式化提交的数据**。没有模型无法从任意自然中文小说中准确生成角色动机、复杂因果和伏笔真实语义；索引位置也不能自动当剧情时间。读取时检查的SHA不是外部认证签名，不能阻止完全控制本机SQLite且重新计算所有SHA的攻击者。尚未支持交错叙事分支的完整拓扑继承、共指消解、歧义语义归并和独立文学质量评价。

新技能升级状态仍然只是底层工程候选；V49 `THIRD_STRIKE_FAILED`、文学能力未通过证明、技能不自动晋级的判定保持。