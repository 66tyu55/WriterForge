# WF 生态 Skill：独立人物实际模型实验首个请求 FAILED（2026-11-18）

**终态：FAILED_PARTIAL_UNACCEPTED / 未得到任何角色或作者内容。严禁声称已实现 NPC 独立思考或文学增益。**

## 已真实发生的操作

先前免费预检：
- [GitHub Actions #44306615962](https://github.com/66tyu55/WriterForge/actions/runs/44306615962)：源与闸门单元测试、旧生态隔离测试、脚本 dry run 全部 **SUCCESS**；这只证明规则/输入隔离和脚本入口。

一次性真实请求：
- [GitHub Actions #44306921344](https://github.com/66tyu55/WriterForge/actions/runs/44306921344) 的动作已发生，作业 **FAILURE**。
- 唯一收到的提供方错误是 **`DISCOVERY_HTTP_404`**（来自已有 `writerforge.reverse_discovery_models.DiscoveryModel` 的报错代码，不包含模型正文）。
- 第一个角色 B（茶棚掌柜）的独立请求已准备并发出；**模型结果 0**，所以角色 B/C/D 的有效独立决策 **0/3**，作者 A/B 完整正文 **0/2**。未进入角色整合，也未作文学评价。
- 确认真实计入本地请求预算的 **1 次 HTTP 请求、550 个预留输出 token**。提供方回复没有返回可统计的 prompt/completion token 用量，**不能将550个预留 token 冒称已消费 token 或积分数**。
- 失败工件（7日保留）：`wf-ecology-real-npc-ab-private-unaccepted-20261118`，artifact ID **14429320349**，含 `run_report.json`、`frozen_preflight.json`、`wire_01_request.json`。**没有返回体**，不能制造模型原话。
- `run_attempt==1` 和指定一次性 commit message 的硬闸成功执行一次；此作业不自动重试，亦未切换另一模型补跑。

## 404 的边界解释

书生·端砚 TokenPlan 在线公开模型清单仍列 `deepseek-v4-pro-0813` 和 ChatCompletions API，但这**不证明这一个用户 API Key 的个人模型权限、可用额度、路由或具体业务状态**。故目前只记录 `HTTP 404`；不编造“服务商明确移除了模型”或“密钥必然失效”的原因。遗留故障和用户过去的体验不能代替本次 HTTP 原始错误消息。

## 可复核的工程成果

- `experiments/wf_living_ecology_real_ab_once_20261118.py`：3个**彼此隔离**的小镇 NPC 提示词；各允许 WAIT，生活目标只在自己的提示词出现；有限选择的即时世界结果；一份只给出 POV 可见结果的作者提示词；同模型 A/B 正文；输出上限及完整原始 wire 请求/返回归档逻辑。
- `tests/test_wf_living_ecology_real_ab_once_20261118.py`：仅离线合成预检。**不证明模型智力。**
- 一次性付费 workflow：`.github/workflows/wf-ecology-real-npc-writer-ab-one-shot.yml`，现只保留失败历史，防止高成本盲重试。
- `docs/WF_20261118_ECOLOGY_REAL_AB_EXPERIMENT_GATE.md`：试验约束及合成与真正实验的区分。

## 暂停门槛

不得增加模型调用以制造阳性结果。只有在**通过不生成正文的 provider 路由/模型访问可用性检查，并重新确定一次性费用许可**后，才有资格启动**新的、有明确区别的模型实验**。真实对照仍需冻结 3 人有限认知，区别于作者把全知材料重新排成“伏笔”的失败路径；真正成功需产出模型独立决策原始回包和原始两版正文，且经独立匿名读者检查“编排感”。

**没有 main merge、没有正式 WF 作者/Canon/R2/Xuehai 变更、没有 Railway deploy。**
