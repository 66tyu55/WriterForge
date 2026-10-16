# V28 云端模型 A/B 工作流

工程状态：云端模型适配器与 A/B 测试代码已提交，GitHub 离线测试已通过。目前缺少模型提供商密钥与价格参数；未执行付费模型 A/B。

## 架构

首章连续窗口由私有 R2 哈希验证。Planner 读取该窗口并提出人物感知与叙事机制假设。Writer 对相同原创写作任务分别生成不使用机制和使用机制的两份全新稿件。不同模型的 Critic 不知道哪一稿启用技能，分项比较感知可信度、人物因果、信息释放、连续性及语言表现。结果保存到私有 R2 时，只保存模型标识、原文与稿件哈希、抽象假设、评语和预算信息。不得保存整段原著和练习正文。模型评分不等于 90% 大师水平，更不能自动解锁第二段。

## GitHub Actions 设置

在 66tyu55/WriterForge 仓库的 Settings → Secrets and variables → Actions 下配置：

Secrets：WF_V28_PLANNER_API_KEY、WF_V28_WRITER_API_KEY、WF_V28_CRITIC_API_KEY。只在 Secrets 内填写已有 API 服务密钥；不要在代码或对话中发布。若使用统一聚合平台，可以给不同角色配置同一平台密钥，但 Writer 与 Critic 的模型 ID 必须不同。

Variables：为 PLANNER、WRITER、CRITIC 三个角色分别配置 WF_V28_角色_PROVIDER、WF_V28_角色_MODEL、WF_V28_角色_INPUT_USD_PER_M、WF_V28_角色_OUTPUT_USD_PER_M。provider 仅支持 moonshot、deepseek、openai、google、openrouter 的 Chat Completions 兼容接口，型号须从真实服务商核对。价格单位为每百万输入/输出 tokens 的美元单价。

另设 WF_V28_MAX_USD 和 WF_V28_MAX_CALLS，例如单次最大预算 1 美元、最多 6 次请求。程序在发起请求前根据最坏情况预留预算，但仍必须在服务商账户设置计费上限。ChatGPT 订阅本身不提供第三方 API 密钥。

## 运行

入口：.github/workflows/v28-cloud-ab.yml。

普通 GitHub push 只做不收费的 readiness 检查，不向外部模型发送任何原著。只有主动从 GitHub Actions 手动触发 workflow_dispatch，并明确选择 confirm_source_egress=true，才可让已哈希验证的第一章首窗发送给选择的云端模型。已授权一次不意味着允许所有小说或自动循环。

成功的精确标准是：单次 A/B 云端真实模型调用完成，得到两稿哈希和模型评审证据，私有 R2 回读 SHA256 完全一致。工程成功并非文学 90 分合格。后续多章节、双段合并、独立人类盲评尚未解锁。

## 代码

- writerforge/reverse_cloud_models.py：不同云端提供商、角色与美元/调用上限，禁止重定向。
- writerforge/reverse_cloud_ab.py：同题对照、匿名评分、保留短摘要。
- scripts/run_wudong_cloud_ab.py：私有 R2 原文核验，运行结果内容寻址备份。
- tests/test_v28_cloud_ab.py：完全不发网的伪响应故障测试。

上述代码为针对 WriterForge 独立实现，借鉴 InkOS 设计思路，并未直接复制其 AGPL-3.0 源代码。
