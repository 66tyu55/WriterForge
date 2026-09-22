# Evolution / Literary Assimilation Map

V12 不复制外部仓库文本，只吸收可独立实现的机制。

## 自我迭代机制

- SkillOpt 类思想：Rollout -> Reflect -> Aggregate -> Select -> bounded Update -> Validation Gate。
- Skill Self-Play 类思想：按当前能力边界设计新训练任务，并用独立 verifier 筛掉无效/过易/泄题任务。
- Ratchet 类思想：从反复失败簇中诞生/修改 Skill；无效 Skill 退休而不是无限堆积。
- Co-evolution / fresh-eval 思想：训练者与验证者隔离，最终用 held-out / transfer 任务验证。
- Skill evolution benchmark 思想：必须同时看 transfer、regression、adversarial/variant，而不能只看当前任务表现。

## 小说文学机制

- Literary craft-engine 思想：Skill 学机制，不学作者表面模仿；近重复能力应合并。
- Pairwise writing preference 思想：Taste 更适合 A/B 比较而非绝对打分；保留人工/读者锚点。
- Writer/Judge isolation：写作和审美判断分离，避免自偏好。
- Scene/Summary/Omission、Free Indirect Voice、Motif Return、Detail Utility、Strategic Reversal 被吸收为现有 Craft Engine 内部 Technique Card，不新增常驻大 Skill。

## 我们自己设计的部分

- Writer Maturity L1-L10：只有能力质变才能晋级。
- Capability Contract / CAPABILITY_LAG / SKILL_DEBT。
- Pairwise order-swap stability：翻票的 Taste 判断不学习。
- Reactive Skill Runtime：dependency fingerprint + selective stale propagation + single-flight + idempotent commit。
- Story Sense Router：一次只处理 dominant literary problem，防 checklist tyranny。
