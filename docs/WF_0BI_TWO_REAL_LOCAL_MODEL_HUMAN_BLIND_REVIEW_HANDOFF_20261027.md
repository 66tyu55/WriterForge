# WriterForge 0.BI｜真实十篇输出交给两名独立读者，而非 AI 自己判文学胜负

日期：2026-10-27。本阶段明确承认**截至此交接仍有 0 名真人读者完成评阅**。两份独立读者材料已由 SHA 锁定的真实 0.BG + 0.BH 原始本地模型输出生成，未产生新模型输出或文学评分。只操作开发分支 refactor-unified-scene-delivery-audit，不碰 main、Railway、用户 R2 原著或正式 Canon。

## 0. 现状结论

过去 0.BF 已提供独立签名评价门禁，但实际拥有的两个本地宿主只生成了两组（0.6B）和三组（3B）成对正文，且没有真人盲评。继续采样更多模型直到 v2 获胜，违反可证伪/主动停的寄生式习惯设计；无必要再发起付费模型调用。本轮做的是**让真正独立读者有可操作的入口**，并保留匿名映射可恢复。

## 1. 真正可交给读者的材料

源代码 [experiments/wf_0bi_genuine_blind_review_packet.py](../experiments/wf_0bi_genuine_blind_review_packet.py) 首先调用已有 0.BG/0.BH 两个真实来源审计函数：逐字节检查原始模型 JSON、模型身份、SHA、原任务和实际用量。发现无原始来源立即退出；不会编造人类评阅或触发新的模型调用。

然后一次性生成三个**彼此分开的** ZIP 工件：

- [GitHub Actions #40509345813](https://github.com/66tyu55/WriterForge/actions/runs/40509345813) 中的 **WF-0BI-HUMAN-READER-ONE-ANONYMOUS-REVIEW**，只含 `REVIEW.html`、`packet.json` 和简短说明。
- 同一运行的 **WF-0BI-HUMAN-READER-TWO-REVERSED-ANONYMOUS-REVIEW**，五题同源、同匿名标识，但每题的 A/B 顺序与第一份**恰好相反**，防止系统性偏好先看到的正文。
- **WF-0BI-CURATOR-ONLY-HOLD-BACK-UNBLIND-MAPPING**：含 `UNBLIND.json`，连接匿名病例及两个读者的 A/B 对应原 `v1/v2`、模型运行、真实源 SHA、实际 token 成本。这份文件只能交给负责协调的用户，**不能发给读者**。

两个读者各自直接在浏览器打开对应离线 `REVIEW.html`（无网络请求、不需登录、不上传数据），阅读五组独立原创前文、任务、两份真实文本，选择 **A 更好、B 更好、难分高下、两篇均差**，可补充最多 500 字理由，点击“导出评阅结果（JSON）”。浏览器只把 JSON 下载到本地，不提交服务器。

五对全部来自已封存的 0.BG（安静家庭、HTTP 202 备份）和 0.BH（合法重试、有限 POV、武侠交接）；0.BG 的备份组 v1/v2 **完全相同的正文**仍原样保留，绝不偷偷编辑其中一篇制造差异。读者材料不含模型名称、v1/v2 标签、资源成本和可用于简单对号入座的源文件名。公开仓库本身可被人工查询，因此**这是有操作约束的匿名呈现，不是密码学保证“无法识别来源”的绝对盲法**。读者须自愿不访问原仓库、不得交流 A/B 来源。

## 2. 工程验收与底层限制

新增 [tests/test_wf_0bi_genuine_blind_packet.py](../tests/test_wf_0bi_genuine_blind_packet.py) **9 项**：两组真实源原字节核对、两个读者完全反向展示、匿名映射独立封存、已有相同生成仍保留、导出结果结构校验、缺票/伪投票拒绝、未认证的所谓“两个人”不能产生文学结论，以及重复运行不得覆盖。它不是 9 个新文学规则，测的是独立人工评阅流程可信性。

[**#40509345813 整仓 GREEN**](https://github.com/66tyu55/WriterForge/actions/runs/40509345813)：**2,016 tests、6 skipped、零失败**。浏览器 JS 静态语法额外单独检查通过。新 provider / local model 推理调用 **0**；新真正人类评价 **0**。v2 继续 SHADOW，自动 ACTIVE 权限仍为关闭，0.AY GLM 429 仍是 DORMANT_HOST_RESOURCE。

**需要特别强调的限制**：当前评阅页导出的是未署名的人类 JSON；它尚不能满足 0.BF 的完整八组真实 provider HTTP wire + 两位独立可信公钥读者签名门槛。现有 `evaluate_signed_blind_ballots` 对未获得外部认证读者公钥的输入只给 `NOT_AUTHENTICATED_HUMAN_EVIDENCE`，不调用“文学胜者”或修改正式 Registry。这个 5 对本地小样本也不能混合两个不同模型/模板的结果就宣布全局 v2 有效/无效。

## 3. 下一项真正必需的人，而不是更多模型循环

将两个**不同 ZIP**分发给两名真正互不通气的独立读者；每名只需完成五对、不必知道模型或 v1/v2。提交两个原始 JSON 后再建立外部可核实的身份/签名，在协调者专用表里解除盲法，报告每个宿主队列内的对照偏好和分歧，不统一混算两个模型，更不自动给候选升级。没有两名可信独立评阅者，就继续保存 SHADOW 和局部负例、主动休眠。

用户如果希望再用远端付费强作者模型验证 0.BE 剩余案例，必须另行明确模型、调用次数与费用上限；本阶段未擅自使用 GitHub Secrets 或任何外部模型 API。
