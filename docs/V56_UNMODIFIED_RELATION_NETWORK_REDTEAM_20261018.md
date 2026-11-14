# V56｜V55 正式关系网络的只读对抗测试：12/19，通过率不能冒充文学能力

日期：2026-10-18；被测正式生产提交固定为 `a4f7b8d8ed68526f947f8e7db8bf4a5744ce7086`。本审计只增加测试脚本、CI、报告，不修改 `writerforge/fact_journal.py`、`writerforge/structural_observer.py` 等正式运行模块；未修改任何原著、R2快照或文学失败记录，也没有调用语言模型。

## 规则

- 用不同临时SQLite数据库执行每个对抗场景；每个场景使用真实 `FactJournal`、`append_temporal_claim()`、`temporal_view()`、`link()`、`graph_neighbors()` 方法，不用伪造桩来模拟被测返回。
- 先执行既有V55的9项回归，仍然PASS。再执行19项独立挑战，记录每项实际输出并保存JSON。严格门槛要求19项全通过，未达到就令Actions明确FAIL，**不因既有测试全绿就给关系网络合格**。
- 案例中的人物、事件和结论是**审计器给出的结构化合成输入**，不能算WF已经从真实文学原著理解、拆解了剧情，也不能算自动获知人物意图。这里测试的是底层数据模型和校验机制。

## 最终真实结果

- GitHub Actions：[#39095860322](https://github.com/66tyu55/WriterForge/actions/runs/39095860322)，baseline 9 tests PASS，19项严格审计的 CI 保持红灯，原始 JSON artifact 使用 `if: always()` 保留。
- 19 项：核心稳定性12/12 PASS，进阶/长篇关系能力0/7 PASS，**总体12/19**。第一次Actions #39095760849 的审计因修订分叉负例先被不相关的“角色不可提前知道”守卫阻断；该首次机器证据已归档（JSON SHA `bc333be303d03c4ba642deb88944593dd39430a942a734cf637188ea105b6bc2`），第二轮仅修正**测试输入**以真正攻击分叉约束，未触碰产品代码。正式第二轮JSON SHA256：`d7c99d16913920b0f10b62b7390fe684815a2b6b4228b458c1363d44b0250115`。
- 结构稳定性：支持故事时间与记录序号查询、允许迟到证据产生可追溯历史更正；不同ACTOR/READER视图分离；同一故事时间冲突保留；角色已知不能早于明确的获知事件；跨不同故事阻止关系误串；边方向保留；POTENTIAL_CAUSE不宣称因果真值；词面索引不可冒充认知；关系/知识改写的字节级篡改被拒；来源回放、修订单继任约束与SQLite重启恢复。

## 7个未通过的对抗/能力场景

| ID | 实际行为 | 诊断 |
| --- | --- | --- |
| guard.reader_future_spoiler | 把story tick=20才出现的揭示作为tick=3读者KNOWN证据**接受** | 真实知识边界漏洞：Reader缺少获得消息的时间约束 |
| guard.reader_private_thought | 从角色未对读者公开的THINK事件直接形成Reader KNOWN，**接受** | 缺乏读者可见性/披露证据字段 |
| guard.knowledge_evidence_support | 来源证据明确UNKNOWN，却允许角色KNOWN主张 | 只校验身份与时间，没有检验证据状态是否支持断言 |
| continuity.cross_chapter_link | 第一章线索与第三章回收建立BEFORE时报`FACT_LINK_CROSS_SCENE_FORBIDDEN` | 当前事件关系被单一scene锁死，不具备跨章节作品级连通 |
| continuity.cross_chapter_state | 第一章人物已知，但第二章同一人物同一事实返回UNRECORDED | 场景作用域隔离，不提供作品级知识投影/继承 |
| chronology.flashback_import | 先记录tick20，再读到tick3同一事实，被`FACT_BACKDATED_REVISION_FORBIDDEN`拒绝 | 旧FactJournal仍强制某些输入按故事时间升序，不适应晚录入倒叙事件 |
| scale.long_record_chain | 同一事实68条有效主张，读取报`FACT_TEMPORAL_QUERY_BUDGET_EXCEEDED` | 有意的保守保护上限，但无法查询较长的历史链；不可当成无界长篇关系网络 |

第一次的revision.no_fork错误为测试夹具误将KNOWN设在过早时间，后改成FALSE以真正进入分叉检查；第二轮此测试通过。**这不是V55已被修复**。原始第一轮FAIL证据原封不动。

## 结论与升级次序

当前系统能严谨保存、比对和回放已有的结构化事实；它**还不是能可靠处理长篇跨章节连续性与读者信息差的完整关系网络**。尤其前三个知识越界需要在允许WRITE消费结构事实之前阻断。

若进入下一版V57，应优先修：A. 角色/读者证据授权与提前获知守卫（不从私有THINK直接给READER）；B. 真正的作品级身份与跨章节事件关系；C. 双轴处理晚录入倒叙；D. 以有界分页重构长历史查询，保留内存上限。先增加失败场景作为不可篡改的固定验收，再在隔离分支改代码，不得重写本报告。不能用词面索引或模型口头解释代替语义证据，也不能把工程关系连通当文学提升。

本审计严格结果：`V55_NETWORK_FULL_CAPABILITY = FAILED`，`CORE_TYPED_STORAGE=PASSED`，`LITERARY_SEMANTICS_NOT_TESTED`，`NO_SKILL_PROMOTION`。