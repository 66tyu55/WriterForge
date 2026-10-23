# WriterForge 七类真实原创小说 — Atria SSE 配对测试交接

时间：2026-10-23。独立分支：`experiment-seven-literary-scenes-inkstone`。用户明确同意调用书生接口开展七类小说真实输出批次核验。

## 测试项目与透明边界

固定七类：剧情、高潮、打斗、计谋、恐怖、搞笑、心理。每类的同一个完全原创虚构开局、同样的当前场景问题和目标篇幅，使用**同一个 Atria-Dawn-Preview 模型**分别采集：

- **裸模型**：共同开局、当前目标和基础输出要求；
- **WF 引导**：上面所有共同信息不变，再加基于真正 WF V114/V117/unified narrative_core 图与 `_prepare_guarded_turn_packet` 的来源、人物知识和因果提示。

不同类别的场景目标不相同，类别之间不允许直接作模型优劣对照；对照只在同一类别同一模型的裸版与 WF 版内部成立。该实验验证**WF 调度提示和来源检查对首次生成的影响**，不等于生产 WF 完整学海检索、全书动态创作、自动修改、小说模型权重训练。

七类专题观察：剧情（选择与后果）；高潮（铺垫、爆发、转折的代价）；打斗（空间、动作、伤势、物品）；计谋（信息差与反制）；恐怖（未知与克制）；搞笑（误会的连锁反应）；心理（思想矛盾与可见行动改变）。共同指标：实际汉字长度、因果动作核对、人物认知边界、物品状态、节奏与文学真实性。逻辑软件警告不等于完整文学判断；不会把自动评分当作文学盲评。

## 为什么换流式

- 早期 Intern-S2 用 900 max_tokens 完全耗于 reasoning_tokens，返回 `finish_reason=length`、`content=null`；
- Atria-Dawn-Preview 的短请求可见文本，但约 900 汉字的 **非流式**响应在 115 秒超时；
- 经证实的 [SSE 单次真实原始小说样本](https://github.com/66tyu55/WriterForge/actions/runs/39936371137)：HTTP 200，926 汉字 / 1173 字符，980 SSE 事件，155.3 秒，`finish_reason=stop`，`[DONE]`；官方归还 Token usage 包括推理 Token。该样本仍只是单次剧情无 WF 基线，不算七类完整 A/B。

## 正式批次运行

代码：`experiments/seven_literary_scenes_inkstone_ab.py`（SSE，`stream_options.include_usage`，总字节限制，单次超时限制，严格响应成功判定）。
离线协议回归： [#39937591289](https://github.com/66tyu55/WriterForge/actions/runs/39937591289)，包括无网络 SSE 解析、`length` 截断拒绝、非 `[DONE]` 不算完成。

真实七类 matrix Run：[GitHub Actions #39937669584](https://github.com/66tyu55/WriterForge/actions/runs/39937669584)。
- 7 个彼此隔离的矩阵工作，每组 1 次裸版 + 1 次 WF 版；同一账户最多 2 组并行。
- 每组最多 2 次 SSE ChatCompletions 请求，`Atria-Dawn-Preview` 固定模型，`max_tokens=3100`；不自动重试 429、超时或空正文。
- 每篇保留完整原稿、章节 seed、完整输入 prompt、SHA、`finish_reason`、usage 和机械警告，记录在各自 GitHub Actions 隔离 artifact。
- 发生中断时某类别保留已产出的所有原稿及失败状态；未成对的类别不得记为 A/B 完成。
- 所有素材都是脚本原创合成虚构例子，没有发送用户私人小说、没有写入 R2/CANON、没有 Railway 部署或更改生产 main。

## 后续判定原则

只有以正文作品为依据的对照才能说某类别 WF 是否帮助写作；若剧情逻辑错误没被检测出来，必须记成**检查覆盖缺口**，不能夸大它已解决。最终盲评要先随机打乱样本 A/B 标签、封存映射，分别给出优点、缺点、准确字数和类别适配度，不能让长文篇幅或华丽辞藻掩盖逻辑缺陷。

模型生成时需要时间，不可把 GitHub run `in_progress` 写作通过；请读取该 run 最新 jobs/artifact，别把一个旧的成功流式基线冒充七类已完成。
