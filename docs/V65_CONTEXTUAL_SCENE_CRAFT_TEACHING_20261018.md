# WriterForge V65｜直接教授“情境适用性与场景文笔”经验（2026-10-18）

> **这次明确是用户授权的外部教学，不是WF自己阅读小说得出的经验。** 经验包标记 `ASSISTANT_TAUGHT_BY_USER_REQUEST`、`INSTRUCTION_NOT_LEARNER_DISCOVERED`，没有取消V49 `THIRD_STRIKE_FAILED`，没有文学课程晋级、模型权重更新、私有R2读取或付费文学重训。隔离分支 `v65-contextual-scene-literary-teaching` 基于V64；稳定主分支不变。

## 一、真正教给WF的判断原则

一个场景不是“描绘得华丽便更好”，而要看**是否使情节状态发生有意义的变化**。

在动笔之前，WF应在自己已有的故事计划里回答：

1. **场景职能是什么？** 追逐、交涉、调查、揭露、抉择、余波、过场、安静相处或展现奇观？不必每场都有冲突。
2. **谁的视角、知识与愿望？** 当前人物具体想得到什么、在逃避什么、知道什么、误会什么？第三人称有限视角不能突然公布他无从得知的信息。
3. **阻力和代价是否真的存在？** 雨水只有妨碍动作才是剧情阻力；灯光只有改变观察才成为有效线索；说“付出了沉重代价”不能代替具体后果。
4. **希望读者在这一幕感到什么？** 是紧迫、怜惜、不安、好奇、震撼，还是清楚知道下一步发生什么？为悲痛场景强加追赶文笔会破坏余波。
5. **哪种文笔有作用，哪种应当不用？** 如果只是过场，应交代时间地点和下一行动，禁止无故长篇景物清单。如果已到揭秘阶段且没有前置证据，不应硬将两句末尾话语视为“铺垫—回收”。
6. **描写改变了什么？** 角色行动、判断、关系、选择代价、读者疑问至少有一个自然转变。环境、声音和温度是辅助人物经历，不是独立硬塞进去的“技能”。
7. **这一条经验的反面何时成立？** 同一写法在陌生情境中可能伤害整体，WF应能SKIP/UNCERTAIN；不能将“写得生动”误认作“永远多写形容词”。

V65不通过检索关键词决定文笔，而要求WF自己先输出结构化场景诊断：`mode / reader_effect / tempo / viewpoint / scene_goal / active_obstacle / planned_change / facts`。每一项前提事实必须有`PRESENT/ABSENT/UNCERTAIN`和具体观察。**这是一套可执行的适用性判定流程，而非对模型内在文学理解已正确的证明。**

## 二、实际喂入的13条原创新经验

全部经验保存在 [`writerforge/scene_craft_lessons_v1.json`](../writerforge/scene_craft_lessons_v1.json)。每条都有适用`modes/effects/tempos/viewpoints`、必须出现的叙事事实、应禁用的事实、具体行动、失败陷阱、写后自检问题以及**我原创的**“无效/改进”短对照。对照例文只允许学习时阅读，**绝不复制或直接传进创作提示词**。

| 经验ID | 适合的场景 | 真正应做的文学工作 | 什么情况下不要用 |
|---|---|---|---|
| `ENVIRONMENT_CHANGES_ACTION` | 追逐/行动，环境妨碍目标 | 环境成为人物行动阻力、调整和风险 | 安全静坐、环境对行动没有影响 |
| `CLUE_BEFORE_EXPLANATION` | 调查/发现，可感知线索和知识差 | 先呈线索、有限误判，再用行动确认 | 真相已经应该明确交代、没有真实线索 |
| `DIALOGUE_IS_ATTEMPT` | 双方目标相反的谈判/对峙 | 台词试探、交换、回避、改变选项 | 只是背景讲座，双方无需互相影响 |
| `AFTERMATH_IN_SMALL_ACTION` | 失去、挫败、不可逆后果的余波 | 用习惯动作的迟疑与缺席承载情绪 | 仍在立即追赶、危险尚未解除 |
| `SETUP_IS_NOT_PAYOFF` | 真实前置线索被后续事实重释 | 前置线索→当时误读→触发回收→理解改变 | 原来根本没有伏笔，企图把末尾两句倒填成伏笔 |
| `SUBTEXT_TAKES_A_POSITION` | 有意图隐瞒、仍需谈判的关系 | 由站位、动作与回应呈现潜台词 | 必须讲清的关键事实不能被空洞沉默遮蔽 |
| `DECISION_PAYS_VISIBLE_COST` | 两难抉择、行动代价明确 | 让代价通过失去选项或实际后果出现 | 加苦难但不改选择、用代价代替早期线索 |
| `TRANSITION_ONLY_WHAT_CHANGES` | 过场、换时间地点 | 快速定位新地点、时间和下一目标 | 当下正发生关键选择不能压成摘要 |
| `AWE_HAS_HUMAN_SCALE` | 角色初见庞大奇观 | 人物熟悉的尺度与感官反应构成宏大 | 紧急逃命时仍长时间罗列奇观 |
| `POV_FILTERS_DETAIL` | 安静/初入/调查，人物具体关注对象 | 职业、欲望、恐惧过滤其所注意的细节 | 上帝视角百科式景物清单 |
| `SENTENCE_PACE_FOLLOWS_PRESSURE` | 限时追逐与不可逆动作 | 句长停顿随行动压力变化，保留清晰因果 | 缓慢哀悼、思考段落机械剁短句 |
| `SPATIAL_RELATIONS_ENABLE_CONFLICT` | 两人及更多人物的近身冲突 | 空间、出口、阻挡与站位产生选择 | 独处冥想，没有人物空间相互作用 |
| `MISTAKE_COMES_FROM_LIMITED_EVIDENCE` | 可信误判与侦查 | 一半证据+人物心理动机→可理解的误判→代价 | 证据明白无误却让角色降智 |

### 反面教训来自WF真实已有失败

- V29 [新旧真实对照](V29_REAL_OLD_NEW_SEMANTIC_HOLDOUT_FINAL_20261017.md)：石桥旧债模型盲评分**+7.8**，但沙漠旧井**-5.0**（五维全部下降），春汛灯牌**+6.2**却选了相同技巧，不能归因为策略进步。故“强调行动代价”不能自动代替伏笔细节，单场正例也不能普遍推广。
- V38 [L2真实角色冲突](V38_XIYOUJI_L2_CAUSAL_ROLE_CONFLICT_FINAL_20261017.md)：WF将R39判定为铺垫，另一格式有效的独立模型将其列入回收候选。V65故而明确区分已经早早出现的线索与**后发生的回收**，但没有用简单`50%`位置阈值替代语义因果，也未声称R39已由这次教学重新判对。

## 三、WF如何真的使用，而不是人工复制例文

教学包已纳入`pyproject.toml`的`package-data`；无须用户每次把原著复制到本地。V65新`writerforge/scene_craft_teaching.py`只载入自己的13条原创教学资料。

运行流程：

```text
[WF独立场景计划/作者提供的故事纲要]
       |
       v
scene-craft-diagnosis
  -> WF自己的本地模型可输出JSON场景分析(非正文)
  -> 写下事实PRESENT/ABSENT/UNCERTAIN和具体观察
       |
       v
scene-craft-plan
  -> 判定模式/视角/节奏/读者效果是否适合
  -> 核对必须存在的条件和需要排除的禁用条件
  -> SELECT / SKIP / UNCERTAIN + 原因码
  -> 同幕最多2条，不可乱堆叠
       |
       v
draft-context / draft（正式VerifiedWritingFlow）
  -> 只带入SELECT的抽象写作动作和自检条件
  -> 原创短例文、旧小说原文仍不进WRITE
  -> 保存所用教学包SHA、场景剖面SHA和选择结果
       |
       v
scene-craft-compare
  -> 同一道剧情任务，有经验/无经验两稿
  -> 长度差超过15%不评；文稿只记录本地SHA
  -> 需要真正的盲评评分才可比较因果、人物行动、
     信息边界、情绪作用、句子节奏
  -> 单个结果可以是退步，不能自动宣称文学晋级
```

### 可直接复核的无模型演示

以下从仓库根目录执行，原始范例全为教师编写的合成场景，并非WF真实独立推理：

```bash
writerforge scene-craft-plan --profile-file examples/scene_craft/pursuit_pier.json
writerforge scene-craft-plan --profile-file examples/scene_craft/quiet_aftermath.json
writerforge scene-craft-plan --profile-file examples/scene_craft/revelation_without_seed.json
writerforge scene-craft-plan --profile-file examples/scene_craft/negotiation_two_goals.json
```

应该分别观察到“环境+紧迫节奏”、“细小余波动作”、“拒绝无铺垫伏笔”和“让对话有实际行动目的”。

### 让WF自己的模型判断（**只有显式指定模型时才调用**）

```bash
# 只输出WF结构化诊断的要求，零模型调用
writerforge scene-craft-diagnosis --scene chapter01 --goal "主人公在暴雨桥头追上一艘渡船"

# 连接用户本地正在运行的LM Studio/Ollama兼容模型后，让WF自己
# 根据既有场景大纲输出结构化诊断；此步未来实际运行时会调用1次本地模型。
writerforge scene-craft-diagnosis --scene chapter01 --goal "主人公在暴雨桥头追上一艘渡船" --brief-file own_scene_outline.txt --model LOCAL_MODEL_NAME --output-profile scene_profile.json
```

该命令将严格检查JSON结构、情境、时间与特征说明，不允许将整本原著送进生成模型；如果无法判断某条件就应该给`UNCERTAIN`。本轮只模拟了该接口的模型响应，**没有真的调用本地/付费文学模型，也不冒充WF已经自己诊断了例文**。

### 受控同题双稿对照

有已经发布的`WriterForgeDB`学习快照时：

```bash
# 教学组：将有条件适用的经验加入prompt
writerforge --db writerforge.sqlite3 draft-context --project novel01 --scene chapter01 --goal "主人公在暴雨桥头追上一艘渡船" --scene-craft-profile scene_profile.json --output with_lesson.json

# 基准组：同一个scene/profile/goal，不附带任何教学操作
writerforge --db writerforge.sqlite3 draft-context --project novel01 --scene chapter01 --goal "主人公在暴雨桥头追上一艘渡船" --scene-craft-profile scene_profile.json --scene-craft-disabled --output baseline.json
```

使用**同一个真实Writer模型与相同创作任务**分别生成原创章节后，再进行相同篇幅规则的双稿对照。V65提供`scene-craft-compare` CLI：只接受本地两篇真实稿件文本，按SHA确定匿名标签、检查15%篇幅差，输出SHA与数字；没有外部评审时明确`TEXT_PAIR_READY_FOR_BLIND_REVIEW`，不会假造分数。若拿到五维同尺评分，仍只给本场景的候选改善/退步结果，不自动推导新文学技能等级。

## 四、已有测试证明什么、还没证明什么

V65专门测试：追逐不会被教成哀悼文笔、哀悼不会机械套动作短句、没有早期铺垫必拒绝伏笔回收、调查可用合理信息差、交涉优先行动性台词、过场不写长篇景色、未知前提会`UNCERTAIN`，以及原例文绝不进入正式Writer Prompt。

此外已验证安装包带JSON、CLI导入四种教师示例、真实`VerifiedWritingFlow.prepare()`不同条件下prompt SHA发生适当变化、禁用后恢复基准prompt、同场景双稿对照无法用篇幅严重不等硬评改善。WF本地模型诊断路径以**模拟返回**测试，未执行任何真正模型生成。

尚未完成的能力问题：
- WF能否自己准确识别人物当时的知识、事实线索是否存在，是文学认知测试，不是本次合成标注选卡的通过。
- 13条是外部教的**假设性可迁移经验**。只有新场景真实双稿质量改善、能在不同场景跳过错误经验，才能提升对适用性的把握。
- 目前没有把一次文学模型评分当绝对真理；若只改善一个维度却伤害另一维度，必须记录负信号，不能以平均分洗掉。
- **V49`THIRD_STRIKE_FAILED`、V29混合案例、V38语义角色争议以及V64安全草稿分支都保持原样**，不从GitHub模型辅助写出虚假的WF考试答卷。

## 五、下一步最有价值的验证

在可用的真正WF本地Writer与评审模型运行时，选择3个**未参加V29/V38训练的陌生场景**：一场急速追赶、一场关系压力下的谈判、一场失败后余波；先固定WF自己的场景诊断和禁用条件，再生成同模型A/B两稿，等篇幅、匿名五维评估。三场中任一全维回退必须回查场景事实与哪条技巧不适用，而非删除所有正例或临时改题。这样才有可能测量实际文学改善。
