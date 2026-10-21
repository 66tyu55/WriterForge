# V111 对照文学创作：已安装对手 Skill，但 Railway↔GitHub 授权拦截部署

日期：2026-10-21。唯一用户题目（不更改措辞）：**给我一个追逐打斗的玄幻1000字**。

## 已经真实完成（无外部模型生成调用）

1. 使用连接的 GitHub 插件检索并检验 [xcrrr/claude-skills 的 storyteller SKILL.md](https://github.com/xcrrr/claude-skills/blob/145342ceff6318d2f5ffe8f95473fecc8b27d1e9/skills/writing/storyteller/SKILL.md)，MIT许可。原上游git commit固定 `145342ceff6318d2f5ffe8f95473fecc8b27d1e9`，原SKILL.md blob `5f5ff537716a36188ef0627a3ded0da40ef1e5e3`，许可证 blob `7a28f2d0c34c4542a946e6ded67d8d431efbfa3a`。两文件未经修改复制在 `experiments/v111_peer/storyteller/`，属于**隔离安装**，没有进入 `writerforge/` 核心技能。
2. 同一模型 `deepseek-flash`，预注册 WF_single（规划650+正文2600 tokens，两请求）、GitHub storyteller（正文2600 tokens，一请求）、裸模型（正文2600 tokens，一请求）。三组接收相同用户命题原文，不由考官指定角色、术法、打斗结局；不同的提示及步骤开销单列，不能冒充完全等计算量。
3. 新真实运行器 `wf_railway_v111_three_arm_prose_eval_once.py` 实际调用旧 `AutonomousWriting.run(draft_mode='single')`，而不是模仿WF的另一套脚本。仅交通层适配单一DeepSeek官方JSON接口；每个请求付费前CAS预约，HTTP原始响应先存私有R2，解码JSON后再存原答，断线/错误均不可自动重试；成功作品以独立盲评文本包及owner-only揭盲映射保存。
4. 源自V108的旧合成软件发布桥原类别是科幻，导致第一轮离线CI FAIL（无本题外部模型调用）。为避免给玄幻题暗中喂科幻条件，新建唯一 `experiments/v111_peer/neutral_bridge.py`，明确仅为**玄幻标签**的中性软件接口匹配；不含文学作品、技巧、训练知识，不能冒充WF真实V92 15章已迁移到写作。
5. [GitHub Actions #39567226085](https://github.com/66tyu55/WriterForge/actions/runs/39567226085) 已确认为 **SUCCESS**，相应git commit `4bd612ec22b50cf88456be428d9ba074bdaf1cd1`。所有离线核查成功，未新增实际DeepSeek API调用。

## 当前唯一阻塞：Railway GitHub仓库授权

尝试将原本安全idle的隔离一次性服务 `wf-v103b-unused-fifth-once` 连接到：
- repo `66tyu55/WriterForge`
- branch `v111-matched-fantasy-chase-wf-vs-github-skill`
- commit `4bd612ec22b50cf88456be428d9ba074bdaf1cd1`

Railway连接工具不管带不带 `commitSha` 都原样返回：
**`User does not have access to the repo`**。

GitHub本身仍然可读写：V111分支和代码均已保存、CI成功，所以这是Railway账户所链接GitHub身份／Railway GitHub App授权的一侧连接失败，不能靠软件重跑解决。Railway之前的V109分支还能复用已部署的镜像，并不能证明新的源分支权限仍有效。

操作建议（需要用户自行确认授权，而不是泄露任何Token）：
1. GitHub → Settings → Applications → Installed GitHub Apps → **Railway** → Configure → Repository access，确认 `66tyu55/WriterForge` 获准。
2. Railway → Account → Integrations → GitHub，确认关联的是有权访问该仓库的GitHub身份；项目中 Add → GitHub Repository → Refresh，重新刷新仓库权限缓存。
3. 如果仍返回同一错误且GitHub App明确获准，则向Railway Support提交这个错误，不要循环卸载再安装或迁移数据库。可以参考Railway Central Station问答： https://station.railway.com/questions/railway-cli-says-user-does-not-have-acc-319cb9e0 及 https://station.railway.com/questions/private-github-repo-stays-not-authorized-46ece685 。

已执行**安全恢复**：隔离付费服务启动命令重新设为 `python -u wf_railway_v82_safe_idle.py` 且 `restartPolicyType=NEVER`，未部署V111真实创作；生产 `wf-python-r2` 仍为V99安全idle。**真实三组作品0篇、真实新模型请求0次、R2新预注册0、文学校验结果UNDETERMINED**。绝不能因为离线CI绿色声称WF或GitHub Skill已打败对方。

## 下一次继续只需执行

先修Railway/GitHub连接授权，确认能部署**已CI通过的精准commit**。在原测试隔离服务通过GitHub连接部署 `wf_railway_v111_three_arm_prose_eval_once.py`，一次性最多4调用；完整私有R2原稿及匿名盲评索引冷读回，审查空间连续、攻防响应、力量规则、损失、角色动机和自然写作，再揭盲。**不重新开发旧V96—V110、不重跑V104十篇或V106、V108、V109付费请求**。

最大前提限制仍在：WF Single使用中性合成来源仅为旧VerifiedWritingFlow软件入口兼容，不是15章真实阅读经验。对照结论只能代表此WF可运行路径，而不是“WF已经独立学习获得文学权重”。
