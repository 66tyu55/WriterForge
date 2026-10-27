# WF 0.BH｜第二种真实本地作者宿主：3B 模型对照与负面证据交接

日期：2026-10-27。唯一可写分支 refactor-unified-scene-delivery-audit。本报告记录真实模型原始回复和来源锁；**不是文学增益证明**。main、Railway、用户私有 R2 原著、正式 Canon、V26/V98/V119、唯一 NarrativeCore 均未改动。原 0.AY GLM HTTP 429 没有重试或编造正文。

## 1. 真实发生的实验

为区别于上一轮 Qwen3-0.6B 经常只复述前文的表现，本次使用明显更大的 Qwen2.5-3B-Instruct 本地量化权重，在 GitHub Actions CPU 上生成新的六份原始结果。

- [模型原始文件提交](https://huggingface.co/bartowski/Qwen2.5-3B-Instruct-GGUF/commit/254600e47ea694216f6108325376ce5b35d456a1)：bartowski/Qwen2.5-3B-Instruct-GGUF / Q4_K_M，发布文件 SHA256 为 9c9f56a391a3abbd5b89d0245bf6106081bcc3173119d4229235dd9d23253f94，约 1.93GB，实际先验证文件 SHA 再运行。使用 llama-cpp-python==0.3.16、2 CPU threads、0 GPU，seed=20261027，temperature=0，最多 320 输出 token。模型许可证标注 qwen-research。
- [真正执行器](../experiments/wf_0bh_stronger_local_writer_once.py) 只在 0.BE 冻结任务中选择三个之前 0.BG 没有执行过的场景：purposeful-second-attempt、bounded-eyewitness、custody-without-fulfillment。每题同任务/同源/同系统提示/同模型/同预算，只有 v1/v2 cognitive procedure 改变。总共六次本地模型调用，新增外部付费 API 调用为 0。
- [原始 Actions #40499625320](https://github.com/66tyu55/WriterForge/actions/runs/40499625320)，2,002 tests、6 skipped、0 failures；真实原始 JSON 工件 ID 12732213344，包含六份 response 和运行时 STATUS、FROZEN_INPUTS。这个 CPU 宿主**不是**另一个独立 Agent 软件，更不是 HTTP 模型供应商签名 wire。
- 六份真实原始回复已 [长期保存到 GitHub 开发分支](../experiments/wf_0bh_real_qwen25_3b_outputs_20261027/SOURCE_MANIFEST.json)，SHA、模型身份、宿主输入、实际 prompt/completion token 已逐份关联。不存在本次用假引擎结果替换真实回复的行为。

## 2. 六份生成具体发现

| 冻结案例 | v1 prompt/completion/total | v2 prompt/completion/total | 实际文本观察，非独立文学评价 |
| --- | ---: | ---: | --- |
| 条件改变后合理重复开启水闸 | 368/56/**424** | 417/46/**463** | 两版都再次尝试；v2 的“锁定灯迅速亮起”与前文锁定灯已灭之间可能产生状态矛盾，需审查灯号语义 |
| 门缝便条与人物有限认知 | 366/91/**457** | 415/94/**509** | v1 较多空泛比喻；v2 保留不确定性但在前文已经塞过便条后再次投递，没有交代新条件 |
| 武侠木盒已交女船夫但渡江目的未知 | 366/65/**431** | 415/42/**457** | v1 选择等待，v2 选择追问；v2 把原文用“她”称呼的卫蘅改写为“他”，是可直接观察的称谓连续性问题 |
| **合计** | **1100/212/1312** | **1247/182/1429** | v2 实际多 147 prompt token、少 30 completion token，合计多 117 total token |

两版均未稳定满足统一提示所要求的 120–220 字长度：v1 三个输出长度约 83/124/90 字符，v2 约 69/130/60 字符。3B 至少生成了新选择，而不像旧 0.6B 那样在工具场景直接复述原文；**因为案例与模型 chat template 都不同，不能据此归因到模型规模，不能夸大跨模型比较**。

v2 在这三个真实局部对照中增加了实际 CPU 模型 token，却没有可以客观宣称已被独立证明的质量收益。上述灯号、重复、指代问题都是候选诊断线索，不能直接归因于 v2 的一般作用。没有两位独立评审、没有全 8 对任务、没有 v2 的正式晋级条件。v2 继续 SHADOW，父 v1 仍保持原状态。

## 3. 严格 RED→GREEN 与防止污染原始证据

- [最初 RED #40499359484](https://github.com/66tyu55/WriterForge/actions/runs/40499359484)：新的 3B 执行模块缺失。新增 7 项合成**边界测试**覆盖模型权重、固定资源上限、失败部分保留、假的 engine 不可冒充真实。
- [真实生成 GREEN #40499625320](https://github.com/66tyu55/WriterForge/actions/runs/40499625320)：确实调用本地 Qwen2.5-3B 六次，2,002 tests、6 skipped、0 failures，没有外部付费推理。
- [首次来源审计 RED #40501147847](https://github.com/66tyu55/WriterForge/actions/runs/40501147847)：新的独立审计函数缺失。随后 [#40501766792](https://github.com/66tyu55/WriterForge/actions/runs/40501766792) 精确指出最初转存 SOURCE_MANIFEST 的第一条 prompt SHA 人工抄错一位：9 写成 8。**只纠正这条清单字段，六份模型原始 JSON 字节与原始 Actions 工件均不修改、更不重新推理**。
- [**零推理永久来源审计 GREEN #40501903317**](https://github.com/66tyu55/WriterForge/actions/runs/40501903317)：5 项合成敌手+真实原始字节 SHA 核验；全部 2,007 tests、6 skipped、0 failures。审计从六份长期保存的真实 JSON 与固定输入重新得出 v1 1312、v2 1429 的 token 总数，新增付费模型调用 0。此后旧 90 天工件过期也可由永久保留字节重放事实，不依赖原作者模型再生成。

审计程序：[wf_0bh_verify_stronger_local_origins.py](../experiments/wf_0bh_verify_stronger_local_origins.py)。它验证事实、模型身份、真实 local usage 和字节差异，**不是文学审稿器**。没有形成 production ACTIVE、没有修改正式 Registry，没有把有限本地负面信号推断为“跨宿主 v2 已被证伪”。

## 4. 下一步值得做什么，不值得做什么

本轮最重要的可迁移经验：**宿主容量不同，真实生成行为也会不同；更长的认知提示不自动换来更好的下一步写作，甚至可能增加 token 和连续性风险。** 事实范围仅限两次各自的本地采样，不能互相归因或证明文学价值。

目前应让该 v2 候选保持 SHADOW，停止同类本地实验反复抽样直到偶然获胜；不因没有赢家而扩写提示词或制造 v3。真正值得下一轮继续的前提是：独立授权的强作者宿主（模型、次数、费用上限明确）、冻结同题 v1-v2 及其完整原始提供商使用量、两名真正独立读者。0.BF 可信评审模块已经就位，不能靠其合成测试取得生产文学成绩。

**不变红线**：只开发分支，不改 main、不部署 Railway、不使用用户 R2 原著或正式 Canon、不重复旧付费实验，不碰 V26/V98/V119、唯一 NarrativeCore。0.AY 的 GLM HTTP 429 永远按真实宿主资源休眠处理。
