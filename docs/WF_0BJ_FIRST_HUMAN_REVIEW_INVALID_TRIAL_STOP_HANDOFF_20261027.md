# WriterForge 0.BJ｜第一位真实读者直接否决盲评有效性，停止第二位与失败根因

2026-10-27。本轮只改 `refactor-unified-scene-delivery-audit`。不再重复生成模型正文、不自动补第二位读者、不改 main/Railway/R2 用户原著/Canon，V26/V98/V119、唯一 NarrativeCore 和正式 v1/v2 原始 SHA 不改动。

## 1. 真正接收到的材料，不能当文学胜率

用户实际上传了 `WF-independent-reading-reviewer_one.json`，它来自 0.BI 原匿名评阅包中的第一个读者席位，**并非经过外部签名的独立多读者证据**。其原始用户上传文件 SHA256 为 `1877fd037307b2881c9df1d68bcca63fe2c6ac8145f40d9b6404d62fe429a8d4`；规范 JSON SHA256 为 `298a808e676348acce3c70af73a68c39ce783bd405737b971dc47adb4422b480`。匿名 packet_id 为 `b5d59476e2635cb0a5249db0`，包本身 SHA256 为 `fbe6ad36c46c5d517ddf6d3f060e4ebdf403687b59a8721fd9a6c77595f51a9e`。

实际五项选择：**BOTH_BAD×1、TIE×1、A×3**。A/B 是每例被随机重新分配的匿名标签，**不能把“A 获选三次”算成 WF/v2 的三次胜利**。已将用户原件的纯 SHA、案例诊断类别和停止原因保存在 [0.BJ SHA-only 反馈记录](../experiments/wf_0bj_first_reader_pilot_stop_SHA_only_20261027.json)，**没有把原始用户评阅正文直接发布在 GitHub**。原始文字只保留在用户上传的文件里；对外记录的原因是概括与分析，不能冒充读者逐字签名证词。

其主要诊断不是“v1/v2 哪个文学分数高”：

- **HTTP 202 备份案例**，两个模型输出逐字完全相同，而且都复制前文，无法判定新增认知过程的效果；用户两篇都差并指出题目/生成方式不对。源字节核验也确认完全相同。
- **安静家庭**，两篇序列相似度约 0.867，差别主要在收尾词句；用户给了 TIE 并质疑比较价值。0.867 是简单的字符串序列相似，不是文笔评分。
- **合理重试、人物有限视角、武侠交接**，用户连续指出一方的幼稚重复、刻意制造“可能存在未知危险”、机械表述结论等文学问题。单个读者的主观意见有效指向这套实验的质量不足，但不足以形成跨读者、跨模型的 v2 功效结论。
- 特别是用户猜测某一篇更“像 WF”，但这轮原实验**两边都把静态 WF v1/v2 认知程序注入同一个本地模型提示**；根本没有裸模型对照，也没有实际执行完整 `AutonomousWriting.run / V26/V98/V119 / NarrativeCore` 创作闭环。不能把某一篇的 AI 痕迹归因于 WF 整套系统。协调者专用解盲映射中，用户怀疑为 WF 的武侠交接 B 是 **v1**，A 是 **v2**；这不能自动变成 v2 有益的证据。

用户明确表示“第二个我都不用看”，因此本轮**停止向第二个真人追索正式结果**，不消耗更多人类审阅时间。

## 2. 以实际冻结模型来源做客观有效性核查，不添加文学打分器

新增 [`experiments/wf_0bj_reader_trial_validity_gate.py`](../experiments/wf_0bj_reader_trial_validity_gate.py) 读取 0.BG Qwen3-0.6B 与 0.BH Qwen2.5-3B 的**十份真正封存输出**，先使用已有源 SHA 核验；只计算不需要文学判断的字节事实。

可证伪与复原的客观缺陷：

1. 一对原始回复文本逐字相同，且两个结果都只是直接复制原 source（HTTP 202 备份）。
2. 安静场景两篇正文约 86.7% 字符串序列重合，只作**诊断标志**，不能据此判文学好坏。
3. 在 3B 执行器已明确写入“直接续写120至220字”的条件下，**六份生成中的四份不足 120 字符**。这是 prompt 服从性/宿主能力不足的客观问题，不是证实 v2 失败。
4. 这次两组是不同本地模型及不同 prompt 模板，不能横跨合并成为 v2 全局胜率。唯一严格干预是往本地模型提示里注入不同长短的 procedure，**不是 WF 与裸模型的真实生产对照**。

因此纯来源审计返回 `DORMANT_EXPERIMENT_UNFIT_FOR_LITERARY_COMPARISON`，而不是 `DORMANT_NO_PROVEN_VALUE`（后者本应代表完整可信独立评价证明候选无收益）。没有调用新模型，没有退休或提升候选，也没有生成 v3。v1/v2 继续封存 SHADOW。

新增 `assess_single_unsigned_review` 允许接收第一份完整但未签名的匿名读者反馈，验证 case IDs、packet ID、五项选择结构，返回 `SINGLE_UNSIGNED_REVIEW_DIAGNOSTIC`、`authenticated_independent_readers=0`、`win_rate_computable=false`。没有第二份就停止，不伪造第二个账号或投票；实际用户原件只记录 SHA，不冒称被这条 CI 环境亲自读取过。

## 3. 真实 RED → GREEN

- [**0.BJ 初始 RED #40530963392**](https://github.com/66tyu55/WriterForge/actions/runs/40530963392)：缺少 trial validity gate；是新增接口真实失败。
- [0.BJ 第一轮 #40531264244](https://github.com/66tyu55/WriterForge/actions/runs/40531264244)：五项测试四项通过，一项要求明确报告 `new_cpu_model_calls=0`，已补齐接口字段。
- [**0.BJ 最终 GREEN #40531429362**](https://github.com/66tyu55/WriterForge/actions/runs/40531429362)：**2,021 tests、6 skipped、零失败**；完整源核验再次通过，零新模型调用、零新增真人评价，确认 `request_second_blind_reader=false`。本轮审查的是**试验资格**，不是添加一条简单审稿规则。

## 4. 下一轮不得重复的错误

不要为修复试验失败就把每句提到“回执”“未知”写进更长的 v3，或者让两个差的输出强行 PK。真正下一次值得花用户与模型资源的试验：

- 首先选择**足以完成基本续写**的作者模型，单臂输出需要满足预登记长度、不是照抄前文、能做下一步选择；达不到就停止实验，而不是强迫真人评更差的文本。
- 比较时必须把**裸模型（无 WF）**和**实际 `AutonomousWriting` 核心 WF 流程**作为真实基线，再测试 WF 携带 v1/v2 认知习惯的增量差异；不能再用单 prompt 注入假装整套 WF 进步。
- 仍应同任务、同模型、同总调用/token 预算和真实源证据，必须区分文学正文质量、增量成本和技术可靠性。读者需独立且不掌握来源身份，出具真正可验证结果。
- 对当前 0.BI 盲评，**第二位已经不必参与**。除非重新设计有意义的新实验、明确新的模型/预算/评价协议，不能重新让用户看无效文本，不自动恢复 0.AY GLM HTTP 429。

不碰用户 R2 原著或正式 Canon，不部署 Railway，不修改 main。依旧以独立作者模型自己的文学判断为主，WriterForge 不生成正文、不自行评文学、不编造提升。
