# WriterForge V50 / 28.0.0rc1 — 不进行文学训练的底层工程升级

版本说明：本版本基于V49 Third Strike FAIL之后的研究分支。旧正式main仍为27.0.0；本版本为候选版28.0.0rc1，须审查合并后才会成为仓库稳定版本。**只升级运行机制，不将文学能力判为提升。**

## 冻结的失败证据与根因

- V49永久FAIL：3个纯景物/自然过程/物件纹理任务全部被无条件注入不适用的人物责任与代价经验，经验适用性0/3。
- V48旧的无经验对照基线本身已含“让人物根据已知信息、欲望和风险作出有后果的选择”，不是真正中性的比较。
- V47宿主技能 `_packet` 仅凭 learned 布尔值提取第一条模型总结并拼进提示词，不检验文学源审查与场景事实，更没有可靠的不适用状态。
- 经验来自模型产出的假说不等于WF真的理解，`SceneLiteraryStudy.review(...,reviewer_confirmed=True)`本身只是调用者声称复核；即使有 approved，也不是独立文学真值。这些事实不允许通过程序升级而抹去。

## V50实际修改

1. 新增 `writerforge/experience_applicability.py`：接入WF已经存在的literary_scene_trials、causal_events、character_state。默认只读、局部SQL查询且上限128事件、48条事实，绝不在WRITE中添加学海知识。不再把一条文学候选用于所有场景。
2. 若没有事先属于当前scene_id的 typed character_choice 事件及真正有区分的已知/未知事实，或因果线索被确认回收、来源审查未签收、文献解释hash与冻结来源不一致，就明确ABSTAIN，附带 reason、来源/适用性SHA，完全不注入经验。
3. `writerforge/skill_host_session.py`：完成BASELINE后，如experience不适用，直接终止本轮经验稿生成，数据库记录stage=abstained和原因，不再让另一个模型回答相同问题后谎称经验生效。适用时仅在experiment sandbox请求加入有界经验指导，明确 `literary_improvement_verified=false`。
4. `VerifiedWritingFlow.prepare(...,evaluation_neutral=True)`：在有控制的文学对照里取消旧默认写作提示中已预载的“人物信息/风险/后果”目标技巧。普通正式WRITE调用默认不变，避免伤及已经工作的创作流程。
5. `VERSION`、`pyproject.toml`、`manifest.json`与正式 `SKILL.md` 统一为 **28.0.0rc1**；标题称V50运行内核候选版，不把实际作者成熟度同时升级。旧V35-V49原稿、R2、评审报告与SHA一律不动。

## 证明范围

V50 只进行无需模型的底层回归。三个与V49类似的非人物故事测试须明确ABSTAIN、实际不产生经验稿；人物已知事实矛盾与已回收线索应拒绝；未审核的源分析不可进入创作；从假设、来源回执、角色状态之间完成匹配才能进入隔离实验。正例由合成数据库状态完成，只证明接口符合约束，**不是文学正确性**。

本版未进行原著训练、没有生成新小说、没有运行新的付费模型、没有根据已知答案增加硬编码文学模板。所有上一版失败保留，其结论不随本次CI通过而改变。

## 更重要的剩余底层问题

- 真正的语义等价、错觉、行动导致后果无法由Python的ID集合与字符串校验独立证明；必须通过严谨的宿主推理和外部文学实证，而非借哈希自动晋级。
- `review_status=approved` 仍缺独立认证；V50把它定义为已签收候选的工程适用资格，**绝不等于已通过文学盲审**。项目状态若是他人伪造，工程检查不能判断其事实真假。
- 宿主自然语言生成仍来自基础模型，普通Skill版本升级并不能修改模型权重。
- V50修的是经验**该不该进入生产创作、为何缺席以及实验是否公平**，不证明它能提高文字质量；最终文学第三次终审FAIL仍然生效。

## 升级判定

通过门槛：工程CI + 旧版回归成功、旧文件未修改、版本号四处一致、无模型请求；不再用“测试全绿”冒充文学生长。版本状态 `ENGINEERING_RELEASE_CANDIDATE`；文学状态保持 `THIRD_STRIKE_FAILED / LITERARY_SELF_IMPROVEMENT_NOT_PROVEN / NO_PROMOTION`。