# WriterForge 0.BG｜第一次真正本地模型 v1/v2 原始输出：可追溯负面信号与停止重复消耗

日期：2026-10-27。先读本文件，再读 0.BF 和 0.BE 的交接。**本轮首次使用真正的本地开源语言模型实际生成新的两组 v1/v2 文本，而非合成文本，且完全没有外部付费模型 API 请求。** 不能把一个 0.6B 模型上两组观察冒称完整 v2 文学能力裁决；也不能把 CPU 本地推理冒称两个 Agent 宿主。

## 1. 为什么选择本地真正的模型而不是不断增加审稿规则

此前 0.BD ChatGPT 基于真实 DeepSeek 原作提出新 v2 认知假设；0.BE 发现 v2 替换旧 v1 泛用步骤并增加上下文；0.BF 建立实际 provider wire/双独立评价证据核验。但是 **0.BE 八组场景只有未来提示，没有真实模型输出**。新付费调用尚未明确模型、次数和费用上限，所以必须首先从宿主已有的 GitHub Actions CPU 资源获得**无付费 API 的真实、严格来源锁定的小规模反例**，而非重用 0.AY 的付费 GlM 缺失回包或造句充当模型。

- 固定模型：Qwen3-0.6B 开源 GGUF Q4_K_M，来源为 Hugging Face `bartowski/Qwen_Qwen3-0.6B-GGUF` 的固定修订 `f9184d8b4c371cb52af5b8cb3d38e55e3cf0f4a0`，本地下载模型文件 SHA256 `9acfc1e001311f34b4252001b626f2e466d592a42065f66571bff3790d4e1b14` **先验证再推理**。实际引擎为 `llama-cpp-python==0.3.16`（本地 CPU、2 线程、0 GPU、ctx=3072）；固定 seed=20261027、temperature=0、每次最多 224 输出 token、4 次实际生成且无自动重试。模型来自第三方量化文件，文件 sha 由固定发布页面提供，源版本不能在后续分析中静默替换。
- 两组任务来自**上一轮冻结的8组新场景中的两个**：`quiet-household-pause`（安静文学、无需要通信的对方）与 `asynchronous-tool-return`（系统返回 HTTP 202，确认受理不等于备份完成）。四次均同模型、同同题源、相同生成 seed、相同每次输出上限，只改 v1/v2 认知步骤。其余 6 组没有运行；没有运行任何旧 0.AY 付费题材。
- `experiments/wf_0bg_first_local_open_weight_v1_v2_once.py` 只在独立 [Actions #40496101857](https://github.com/66tyu55/WriterForge/actions/runs/40496101857) 真的加载 SHA 对应 GGUF 后才调用本地 model 4 次。记录真实 llama.cpp 完整 `create_completion` JSON、completion SHA、提交输入 SHA、usage token 和逐次时间；中断保留部分真实结果并禁止用新调用补齐。它**不是提供商 HTTP 原始 wire**，不得放进 0.BF 声称“已核对 provider HTTP wire”。
- 另外 7 项离线测试证明无模型权重不得执行、同题 v1/v2 的输入身份、调用预算、伪造 fake engine 不能声称 real、失败只保留已完成结果。不把虚构 unittest 模型正文混入真实 4 次生成。

## 2. 具体第一次负面观察（已读四份真实模型输出，不造评分）

| 新案例 | v1 实际 prompt / completion / total | v2 实际 prompt / completion / total | 真实文本观察 |
|---|---:|---:|---|
| 安静家庭 / quiet-household-pause | 343 / 74 / **417** | 392 / 71 / **463** | 两个文本大部分相同，但最后一句措辞有差异（v2 比喻“无声的回应”）；没有独立读者质量偏好 |
| 备份 HTTP 202 / asynchronous-tool-return | 337 / 63 / **400** | 386 / 63 / **449** | **两组最终生成正文逐字相同（相同 text SHA）**，并且都是直接复述原先两段文字，并未提出明确下一项实际操作 |
| **总计** | **680 / 137 / 817** | **778 / 134 / 912** | v2 增加了 **98 输入 token、减少 3 输出 token、净多 95 total token**，但这两例没有经过真实读者盲评 |

这里 usage 是本地 llama.cpp 对其实际处理的 prompt/completion token 计数，**不是供应商付费账单**、不是 0.BE 的文档字符估计。第一次仓库预登记的“整份胶囊多 462 字符”也并非本地 prompt 直接消费的大小（本地只传 procedure，没传完整 falsifier）；两个数字不能混算。

**可客观证实的结论**：在这个 0.6B 小模型、备份 HTTP 202 案例中，v1/v2 完全输出了同一段文字，v2 只增加 49 输入 token。这是**一个真实局部没有可观察差异且资源成本更高的负面信号**。它不等于独立证伪全部习惯，也不等于“v1 文学水平更高”，因为模型可能根本太弱，连基线的下一步选择也没写出来。安静片段虽有措辞差异，也没有两位可信独立读者，因此不能自主给出 v2 胜或负的文学分。

## 3. 真实原始输出已经从 90 天 CI 工件转为永久开发分支 SHA 证据

- [四份原始本地模型 JSON 与 SOURCE_MANIFEST](../experiments/wf_0bg_local_cpu_actual_outputs_20261027/SOURCE_MANIFEST.json) 已全部按实际原字节永久保存到开发分支。它们标记模型权重 SHA、原始 Actions ID `40496101857`、工件 ID `12730279357`、源任务 SHA、prompt SHA、模型原始 `usage`、完整原始 output SHA、写作文本 SHA、无独立质量评价。
- [`experiments/wf_0bg_verify_real_local_value_observations.py`](../experiments/wf_0bg_verify_real_local_value_observations.py) 完全离线核验上述保留的四份原字节，匹配之前的固定原始输入 SHA、模型身份和使用量；自动计算逐字相同、复制旧来源、真实 token 差值，而**不是 AI 评分器**。结构化结果设置 `should_next_autonomous_revision_run=False`，仅表示这个局部小模型实验不应自动继续重复试错；不改变全局 v2 SHADOW、正式 Registry 或 Canon。
- [离线永久来源回放 #40497431449](https://github.com/66tyu55/WriterForge/actions/runs/40497431449) GREEN：5 项新真实文件 SHA 核验、全量 **1,995 tests、6 skipped、零失败**；独立复核 2 组/4 份完成，1 组 v1/v2 全文字节相同，备份场景两组都仅原文复述。该工作流**没有再次下载 GGUF 或推理任何模型**；它检验的是前一个真实任务留下的原始输出。
- 已把这次明确负面信号追加到 [0.BD 原 v2 SHA 候选 README](../experiments/wf_0bd_portable_habit_snapshots/0d43a023bc278ac12e3165e319d2acb73dcf40c0d9af453e623c786f3b476a10/README.md)，并未改动原 v2 capsule.json/portable_manifest.json 的字节或 SHA。

## 4. 明确停在什么程度

0.BG 的效果是从**真的宿主本地推理结果**获得一次可以跨下次会话重放的局部负面事实：“v2 多消耗实际 token，并不一定改变选择；弱宿主可能复述原文而不真正写下一步。”它是从原始模型生成文本中抽出的**可迁移实验经验**，有版本、有任务、有反例、有原始 SHA 和可重复的纯离线核验，不是向 v2 又加入一句审稿规则。

仍无：八组完整对照（目前仅2组）、真正独立双盲读者、强能力作者宿主、模型供应商 HTTP wire、真实进化胜利或正式 ACTIVE 生产批准。不能把 0.6B CPU local Llama instance 说成一个全功能独立 Agent；不能从这两个局部例子判断 v2 全局应 RETIRED 或 ACTIVE。可选择对这次弱宿主的后续重复试验保持 DORMANT，不为追求绿色多次无益抽样。

**下一阶段最有价值的是同一来源实验但换到能力足够的作者模型，以及真正独立阅读与证据签名**。新付费模型请求仍需单独明确的次数、费用和身份授权；不要自动使用 Github Secrets 重新跑 0.AY GLM 429 或已冻结的旧付费文学训练。现在的实验不能自动授予下一个宿主资源或替作者改稿。

安全红线：只开发分支 `refactor-unified-scene-delivery-audit`；main、Railway、用户私有 R2 原著、正式 Canon 不动；V26/V98/V119 和唯一 NarrativeCore 不变。
