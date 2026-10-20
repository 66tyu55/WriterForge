# V84 · V81 已保存跨作品双臂答案的私有只读证据审计（2026-10-20）

## 1. 真实审计，不新增模型训练

- 分支：`v84-v81-private-readonly-evidence-audit`，从V83分出，不修改 main 或 V81/V82 的任何旧证据。
- Railway生产项目/服务：WriterForge / wf-python-r2。
- 本次独立只读审计部署：`bb77f759-734a-4866-be80-8eb4a36300bc`，状态 `SUCCESS`。
- 实际审计脚本：`wf_railway_v84_private_evidence_audit.py`。
- 真实程序日志：`WF_V84_V81_PAIR_SOURCE_AUDIT_COMPLETED_LITERARY_UNPROVEN`，`WF_V84_PRIVATE_AUDIT_EXIT=0`。
- **DeepSeek调用0，R2写入0**。启动前移除DeepSeek和R2 Writer环境密钥，只有既有Reader被使用。
- 只读读取V81已经冻结的跨作品原始双臂 CAS `88a3bf2c34f5fd21400236af375b38df94392403f4b3b3edbc2e352b962049d4`，两臂SHA和原文来源双单位哈希已重新核验。其来源全文SHA `e3fb51aa6d9ed50f79c7c9d60361a366c4a168b8593d1cdaaec65784e46f8cd8` 不同于训练仙侠书。**原文与答案只在Railway临时内存/临时目录中处理，没有写回R2、GitHub或GPT，也没有输出原文章句。**

## 2. 不得冒充文学评判的数值诊断

下表表示各字段中文3字连续片段中，有多少百分比与本次允许阅读的两段原文一致。它仅是词面重合检验，不能代表证据解释正确率、写作水平或真实文学理解。

| 现有模型答案字段 | 无经验组 source 3-gram重合 | 有经验组 | 两臂答案文本相似度 |
|---|---:|---:|---:|
| question | 0.0% | 1.5% | 28.0% |
| hypothesis | 2.4% | 0.0% | 18.3% |
| uncertainty | 0.0% | 0.0% | 24.5% |
| focus | 0.0% | 4.5% | 21.6% |

- 两组均引用来源单位 `[1,2]`，两臂来源引用没有变化。
- 原稿字段字符长度：无经验组question 60/hypothesis 103/uncertainty 77/focus 46；有经验组question 90/hypothesis 126/uncertainty 86/focus 28。
- 原文最长逐字段字面匹配无经验组2/4/2/2、有经验组3/2/2/3字符（顺序为question/hypothesis/uncertainty/focus）。**没有证据说明一方的文学因果解释更正确。**
- 有经验组的hypothesis三字重合为零是需要后续人工/独立语义审评的风险线索，**不是幻觉或语义错误的确定证据**；无经验组2.4%也不是成功证据。词面重合可奖赏抄袭、惩罚合理复述和抽象推理。
- 两臂确实回答不同：已保存原始回答的哈希不相同，但这也可以完全由提示词条件变化造成。只有**一组**对照，未做次序换位重复、多作品稳定性分析或独立文学评论。

## 3. 真正的能力与证据缺口

- V81原答中虽有 `question/hypothesis/uncertainty/focus/evidence_units` 五字段，但没有把每条人物/因果断言对应到可验证的**原文短句与精确位置、时间和知识边界**。
- 现有检查只证明原文单位编号有效、来源哈希未被替换、JSON协议符合要求；其 `per_claim_exact_source_quote_offsets_available=false`。
- 仅凭数值特征，不能独立判断真因果、情绪机制、角色知识、是否抢先知道后文、假说是否可证伪、哪组的语言表现更好，也不能估算有经验的**因果**增益。
- 因此 `overall_quality_winner=UNDETERMINED`、`independent_literary_judgement_performed=false`、`promotion_allowed=false`。继续保留V49的 `THIRD_STRIKE_FAILED` 和第二文学窗口 `LOCKED`。这不等于文学质量已独立证明为失败，只是**缺少合格的独立验收证据**。

## 4. 下一个真正有用的试验（本轮没有开展收费模型审稿）

1. 新题预注册：从没读过的新书选择真实窗口，同时冻结答案形成之前的后续“真值查证”片段（不向作答模型泄漏）。同一模型相同长度和提示约束，除经验策略外两组条件一致，匿名随机执行，尽量更换顺序。
2. WF每条因果/伏笔假说必须填 `claim_id, actor, actor_known_before, source_unit, source_span, observation, hypothesis, alternative, falsifier, uncertainty`。程序先对span唯一性及已读时点验证；正文不会进入公开仓库。
3. 单独的独立考官**不得看到哪组用了WF经验**，按来源忠实度、角色知识边界、因果机制、信息释放、证据支持及是否主动弃权等逐项核对；发现无法裁定必须能判 UNKNOWN。
4. 事先冻结评分标准和最小重复数量，不让WF作为自己的唯一评委。负例留存，不把模型自评高分提升为文学等级。
5. 在质量收益获得真正证据前，暂停增加第17—20章训练。第16章V83因误写62位journal SHA在任何收费模型调用前失败，已修复源代码但**没有重新付费训练**；V82前15章仍是已核实的历史上限。
6. 在实际服务恢复`wf_railway_v82_safe_idle.py`后，单独确认新部署确实执行了该入口并记录0模型/0 R2写入；不能只看Railway部署SUCCESS。

## 5. 可复核代码

- `writerforge/v83_evidence_diagnostics.py`：词面和两臂相似度的纯本地计算，永不返回答案或原著字符串。
- `wf_railway_v84_private_evidence_audit.py`：恢复V81冻结CAS与历史原著双单位，复算所有来源SHA和机械对照；再执行只读文本诊断。
- `tests/test_v83_evidence_diagnostics.py`：合成文本单测（**本次未启动GitHub Actions或宣称其正式CI通过**）。

**裁决**：已验证经验改变答案及来源签收链；尚无证据可以认定文学质量变好。继续累积章数不能替代独立语义因果评判。
