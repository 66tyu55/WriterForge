# V112 · GitHub Actions 原生 DeepSeek × 3 臂玄幻追逐打斗测试（付费前预注册）

2026-10-21。用户核实 GitHub Secret 名字**恰好为大写 `DEEPSEEK`**。此前V111因Railway平台账号404／构建暂停无法部署，且用户已决定不用Railway。V111未执行新的三臂模型调用。本预注册沿用相同题目及被冻结的第三方GitHub Skill，将执行地点改为**GitHub Actions**，不依赖Railway服务或Cloudflare Worker写入Token。

## 单一冻结题目与真实对照

**给我一个追逐打斗的玄幻1000字**

同一官方 DeepSeek 接口及同一 `deepseek-flash` 模型：WF原 `AutonomousWriting.run(draft_mode=single)`、仅GitHub组加载MIT-Storyteller原版 `SKILL.md`、无Skill DeepSeek裸模型。每组正文生成 max_tokens=2600；WF另有一次规划 max_tokens=650，总预约 8450、至多4次请求。**不允许因长度不足或JSON失败重抽**。实际字符数、各臂调用次数与Token消耗分开报告；字数超过900—1100范围或三组差距超过10%则只作文学定性分析，不宣布公平排名。

第三方 Skill 来自 `xcrrr/claude-skills` commit `145342ceff6318d2f5ffe8f95473fecc8b27d1e9`，已安装在 `experiments/v111_peer/storyteller/`；版权 MIT，不允许加载进WF正式技能。WF使用原VerifiedWritingFlow，**仅一个明确标为synthetic的软件入口兼容样本，而非原15章真实学艺经验**。不使用第二个写作/评阅模型，原稿先存，评分后看，未验证文学质量不得晋级。

## GitHub Native 执行和不可变存储

- GitHub Actions 密钥检查 `#39582660149` 完成：`DEEPSEEK`、四个既有`WRITERFORGE_R2_...`凭据全部 `AVAILABLE`，0收费、没有打印或记录密钥。
- 工作流环境变量 **`DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK }}`**；仅供进程调用官方DeepSeek，不需重新设Secret。R2直接使用已有Cloudflare R2的S3客户端凭据；**完全绕开Railway和Cloudflare Worker写接口**。
- 全新CAS独立命名空间 `writerforge/v1/experiments/v112-matched-fantasy-chase/sha256/<prefix>/<sha256>`，仅访问这次实验的对象；使用IfNoneMatch条件创建，SHA256命名、独立回读校验；已有预注册created=false即拒绝再次计费。不会list/download旧小说库，也不覆写学海或其他CAS。
- V112唯一实验身份：`WF-V112-GITHUB-NATIVE-3WAY-DEEPSEEK-20261021`，与V111（未执行）和全部旧试验不同。
- 每次供应商请求前在R2写不可变预约；收到的原始HTTP响应字节在任何JSON解码之前持久化并记录CAS；成功JSON再次封存。任何错误不重试，不返工、不编辑WF原文。最后匿名三稿存私有R2，作者映射owner-only保存；GitHub Actions下载用artifact仅包含匿名原文，不包含哪组对应哪稿的揭盲映射。
- GitHub全仓无网络CI `#39583746395` SUCCESS，确认Skill来源、WF原软件入口、R2 S3纯函数及文本字数计算。真实模型调用尚未开始（本文件创建时）。
- 独立测试用真实API阶段仅允许明确一次性工作流在源分支首次新增时由GitHub push触发；竞争锁prevent duplicate concurrent paid runs，历史失败也保留。Workflow可以被手动 rerun，但永久预注册CAS会拒绝重计费；任何旧模型调用不许在这个任务里重复发起。

## 真实评价与长远原则

重点查逃跑路径、追与逃的相对位置、技能能耗与发动前提、攻击和防御真实因果、角色所知与主观误判、受伤和失去的真实代价、后续选择、语言节奏和画面自然度。盲审完整正文后再揭盲。评分不因测试JSON通过、字数长或技能标签好听而提高；如果只有模拟来源，不能宣称WF过去15章文学经验已迁移到写作。

生产RailwayV99安全待命不变；R2原库、V97七次、V103五次、V104十篇和全部历史红项原样保留。只有真实模型答复及可恢复CAS索引才能证明实验已发生；本文件不能提前声明哪组胜出。
