# V28 固定百万上下文模型对与每轮 50k 输出预算

日期：2026-10-16。用户要求固定 2/3 个真正具有约百万上下文的模型、提高预算至 50,000 tokens，不再频繁切换低质量小模型。

## 固定路由

- Planner／Critic：`deepseek-v4-flash-0731`
- Writer：`deepseek-v4-pro-0813`
- 实际模型 ID 共 **2 个**；三个角色不等于三个独立模型，Planner 与 Critic 共享 Flash。独立的人类审评仍未完成。

DeepSeek 官方 V4 API 文档说明 Flash/Pro 的 1M 上下文；当前端砚 Discovery 的 `/models` 实际返回以上两个 ID，但**没有**返回 context window、max output 等上限元数据。官方模型规格不是第三方网关已承载 1M 的压测证明。因此代码设置 `FIXED_MODEL_CONTEXT_TOKENS=1_048_576` 同时明确 `DISCOVERY_GATEWAY_1M_LOAD_VERIFIED=False`。

模型规格证据：
- https://api-docs.deepseek.com/quick_start/pricing/
- https://api-docs.deepseek.com/zh-cn/news/news260424/
- https://api-docs.deepseek.com/guides/thinking_mode/

端砚兼容性无原文真实测试： [#38910061191](https://github.com/66tyu55/WriterForge/actions/runs/38910061191) success。对 Flash 和 Pro 都使用 `thinking:{"type":"disabled"}`；两个请求均 `finish_reason=stop`，有可见文本，不能据此断言 1M 网关上下文承载已验证。

## 硬预算与安全

- 单轮所有角色请求总预留输出上限 **50,000 tokens**；单次输出 token 配置上限也为 **50,000**，但同一轮仍受共享总额约束，超限时在请求发出前拒绝。
- 默认允许最多 7 次模型请求，含失败重试；每请求至多一次修复尝试，无无限重试。
- 当前训练阶段分配：Planner **6,500**；Writer A **11,000**、Writer B **11,000**；Critic **8,000**，基础总预留 **36,500**，余下 **13,500** 供有限修复请求，并非强制将总额全部消耗。
- 单请求传输输入字节上限 **4MiB**，返回 JSON 响应字节上限 **1,000,000**。这是输送缓冲硬限制，不是承诺一次把 1M tokens 送进上下文；目前仍从《武动乾坤》第1章第一连续原著窗口开始，绝不跳章或一次吞全书。
- 所有模型仅通过端砚 HTTPS；私有 R2 长期只记录哈希、失误和有限抽象结构，不能保存完整练笔正文/原著段落。
- Planner 只选择宿主固定写作方法 ID 加来源证据编号；Writer 不收到原著角色和事件，避免过去源剧情污染；两稿长度差超过15%禁止进入文学评分。
- 模型评分不代表已达到 90% 大师水平；第2段仍需真正的合格晋级，不能把工程成功当文学成功。

## 对应实现

- `writerforge/reverse_discovery_models.py`：百万上下文模型身份说明、显式关闭 DeepSeek 深思考、50k 总输出 token 上限、响应大小限制。
- `writerforge/reverse_cloud_ab.py`：6.5k+11k+11k+8k 的阶段性输出配额。
- `scripts/run_wudong_discovery_ab.py`：新的 `fixed-1m-context-50k-ab-v3` 互不覆盖私有 R2 前缀，保护历史 v1/v2 失败报告。
- `tests/test_v28_fixed_pair_budget.py`：两模型路由、1M 官方模型规格/网关未压测状态、50k 总额上限的离线测试。
- `.github/workflows/v28-wudong-fixed-1m-50k-one-shot.yml`：**仅文件首次提交触发的一轮**正式原著试验；正常修改其他代码不自动重跑。
