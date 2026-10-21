# V114B · 修正 DeepSeek 预算硬限制后的一次性真实 WF 时态记忆写作测试

日期 2026-10-21。**本预注册先于任何 V114B 真实模型调用。**

## 不能覆盖的 V114 原始失败

V114 原实验 `WF-V114-REAL-CONTINUITY-AND-NOVEL-STUDIO-20261021` 已在 GitHub Actions [#39601327157](https://github.com/66tyu55/WriterForge/actions/runs/39601327157) 用原不可变预注册创建一次性任务。它的第一请求意图 CAS `c6dcc51c018f5d289c0e3be7a02e039cfb66ac6fbd792084446cac6ec2af672d` 真实写入R2，然后 DeepSeek SDK 的 `FlashBudget.reserve` 拒绝预算配置 `MAX_TOTAL=135000`，因为底层API仅接受总预算**恰好150000**。**拒绝发生在任何 HTTP transport 之前**；原供应商用量0，未生成新正文。原失败manifest CAS `faa8f406a1960a34ef9d348d138456364e5fd56844526c899c5c8394e32f3941`。保留，绝不再以此EXAM重放或改成PASS。

## 新唯一实验身份

新执行文件 `experiments/v114b_real_wf_continuity_once.py`，独立EXAM `WF-V114B-FIXED-150K-REAL-CONTINUITY-20261021`。相同用户问题：**给我一个追逐打斗的玄幻1000字**；相同唯一 `deepseek-flash` 模型、真实 `AutonomousWriting.run(draft_mode="continuity_guard")` 写作入口、外部固定MIT `bbaz123/novel-studio` 时态归约器。

变更严格限于两项：
1. 使 `FlashBudget.max_total_tokens=150000` 满足执行器**精确值协议**。其他限制保持：总模型调用最多4次、输出预约 1450+650+1450+1450=5000tokens、单次HTTP无重试。
2. 明确章计划系统提示为严格JSON六字段，以满足 `DeepSeekFlashModel.ask_json` 的 `system` 必须包含字符串 `JSON` 的软件接口协议；不增加任何人物、玄幻规则或情节标准答案。第一和第二段正文仍由 WF 自己创作。

**绝不**修改旧V114脚本、旧V113原稿、V49失败、前15章真实阅读链或现有用户数据；唯一新R2写入为该实验CAS前缀内的新哈希内容。供应商HTTP原始字节在JSON解析前封存，解析JSON又在WF语义/长度检查前封存。失败零重试、原稿无自动改写、不训练也不晋级LiterarySkill。

## 评判目标和不虚报的限制

最重要的是，看 Novel Studio时态内核的物件和位置状态是否实际被写入**第二段**提示，而不是只在第一段之后保存。然后再审读新真实正文：逃跑路线、法器转手是否有场面动作、法力消耗后下一步有没有凭空恢复、受伤是否改变实际追逐方法、人物情感是否自然。对照之前已真实封存的V113 WF951字和Storyteller1010字；**由于V114B有额外事件规划和分段调用，不是等模型成本实验，不能用一篇作品判断架构胜出。**

只有完整原始两段实际完成，才可能进行文学审查；软件CI通过、原句校验PASS或模型调用成功均不能自动宣称文学改善。GitHub Actions执行，**不接Railway**。原文恢复将另用零模型密钥只读GitHub任务。
