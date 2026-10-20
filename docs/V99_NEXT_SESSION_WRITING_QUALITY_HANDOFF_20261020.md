# WriterForge V99 → 下一轮正式交接｜以真实写作逻辑和文学手法为核心

日期：2026-10-20。**本文件是交接，不是新一轮测试或付费授权。** 后续先读本文件，再读 [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md) §82–85 与 [V99证据合同报告](V99_ACTUAL_PROSE_LOGIC_EVIDENCE_AND_FAIR_BLIND_REVIEW_20261020.md)。

## 一、核实过的最新版本，不许误回到V96

- **当前GitHub开发分支**：`v99-causal-quality-blind-review`。交接前GitHub HEAD `6f3b7987c2c826ddf90d6672b41c29fb9b03181a`（本交接新增GitHub提交会使HEAD向前移动）。
- **当前Railway主服务**：项目 `c5a1c1ad-03d7-4767-b972-8a46446fec07`，服务 `e6a7688b-ee12-49ef-ae83-02145005fc79`，环境 `65b1b9fe-2f4f-44f3-80af-77143a19545d`。最新已核实部署 `3376a212-ef87-4339-a083-6631260c01d2`，状态`SUCCESS`，源码固定 `a8404905869dc1e1acc094adc0f0931f61823ede`，运行 `python -u wf_railway_v82_safe_idle.py`，`restartPolicyType=NEVER`。真实日志 `WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`，本次模型0、R2读0写0、`automatic_paid_next_batch_enabled=false`。只改GitHub交接文件**不要重新部署**。
- **V99全仓实际绿灯**：Railway `005a6fad-2973-4f5b-93bc-d675f69d19c6` 运行`1072`项，`0`失败、`0`错误、`4`跳过，`WF_V85_FULL_OFFLINE_REGRESSION_PASSED`；该轮模型0/R2网络0。红项见V99报告：第一次重复原文引句导致1失败2错误；第二次字符串源码转义SyntaxError只跑1065项；之后研究Python字面量语法再修复，不能删除失败证据。
- **不变的长期基础**：V92 15/15旧/新版中文经验R2清单 `bd905ae9e812fb5283f24ed7fec3bc35cf0febde7b6405476c455bba468f84db`，无付费重训。V49 `THIRD_STRIKE_FAILED`、第二文学窗口 `LOCKED`、V88真实4臂原文锚点0/4严格验收失败仍保留。Cloudflare V95权威HEAD线上未部署（之前Reader GET返回404），不能偷写新的正式人物`KNOWN`事实。

## 二、真正已做的写作内核（V96–V99）

1. **V96：** `writerforge/v96_causal_turns.py` 改造原`writerforge/writing_assist.py::AutonomousWriting`，提供A `single`（旧单次）、B `split_only`、C `causal_guard`（B同样冻结场景分段，但事后按真实原文短引句检查action→effect唯一位置、先后和前景父证据）。UI作者手动选择，默认A不变，不能把机器引句匹配称为文学因果证明。源码与报告 [V96实际实现](V96_SCENE_TURN_CAUSAL_WRITING_IMPLEMENTATION_20261020.md)。
2. **V97：首次真实原创长文对照**。历史「渡桥送药」原创试题，**仅一题且仅DeepSeek Flash一家**。固定A/B/C共7次付费请求、官方响应usage输入10649＋输出4450＝15099 tokens；A=1902、B=1601、C=1554中文含标点字符，**长度不同，不可直接排名**。所有7份模型原始答案和3份候选全文存在用户私有R2，预注册CAS `5c7fac8ef9ab0f588698711ba1b63672a2eab18ff4f65d53bf8616489d36cae1`；最终清单CAS `d304d2432e2c3290b6bbd8ccb6bc209e38b7e12bc0aabb968b489b31c22b02a1`。全新Reader `6a850368-b5eb-4196-a0f4-5ff4adaf5b16` 验证模型原答、正文及C的3个动作、3个后果、2个父后果引文的SHA；这只证明字面证据链存在。见 [V97真实试验报告](V97_REAL_LONGFORM_ABC_1500_CHINESE_20261020.md)。
3. **V98：** `writerforge/v98_rolling_causal_planner.py` 与原`AutonomousWriting.run`、Studio选择器新增D `rolling_causal` opt-in。正文写出后才根据真实效果更新下一幕滚动目标；不盲从整章一次冻结大纲。上一正文`prose_sha`、真实效果span和V96 receipt均需吻合；不把猜测动机自动变人物真值。D增加额外规划调用，后续比较必须控制调用/Token预算。最后离线1064项绿，**D尚未有新的真实模型写作与文学盲评结果**。见 [V98源码实测](V98_PROSE_DRIVEN_ROLLING_CAUSAL_WRITING_20261020.md)。
4. **V99：** `writerforge/v99_longform_quality_evidence.py` 与`tests/test_v99_longform_quality_evidence.py` 为已写出的全文冻结SHA/实际字符数；每项候选逻辑矛盾必须有两个来自真正正文、唯一存在、前后可定位的短引句与SHA。错误引用/重叠/倒序/正文版本变动拒绝。**但引句真实≠两句一定矛盾**；`verified_hard_contradictions=null`、`first_verified_logic_failure_character=null`、`literary_quality_winner=UNDETERMINED`，不会把机器检测写成文学结论。实际字数差超过10%标记不可比。该版本仅完成软件规范与1072项回归，未新增模型调用或独立文学评审。

## 三、必须保留的研究依据与写作核心

用户要求：不要偏离WF**写作思考、写作手法提升**；AI「约1000字后逻辑紊乱」是应实测的问题，不应把1000当所有模型的确定阈值。前期GitHub/ACL比较见 [V96研究](V96_LONGFORM_CAUSAL_WRITING_GITHUB_RESEARCH_20261020.md)：DOC/Re3（分层叙事计划、逐段控制与核事实）、StoryWriter（人物/事件因果关系）、StoryDaemon（内容自由生长＋小范围滚动计划）、novel-writing（已确认/推测/作者计划分离）、ConStory-Bench（可标注的长故事事实/时间/人物/逻辑错误）。LongWriter能输出更多字，不等于小说逻辑更好。

**写作评价必须双轴**：一轴为人物身份、角色所知与读者所知、前因、行为、现实后果、时间/物品/能力硬连续；另一轴为人物声音、对白可信、张力、代价、伏笔、节奏、留白、文风自然与技法实效。不能只过程序规则却把书写成机械说明书。倒叙、误导、悬念、歧义允许保留为`UNKNOWN/INTENTIONAL`，不得自动算硬伤。

## 四、下一窗口实际优先任务（不要重新做V96-V98）

**优先A：拿既有V97真实A/B/C私有R2原文，准备匿名盲读材料和证据标注。** 不重跑旧7次付费模型，不把来源/原答全文贴到公开仓库；仅在受控Reader读取并冻结每组实际长度、文件SHA、匿名组号及评价指标。真正独立读者的权限/身份未验证时可以做材料准备，但不得声称语义评分已执行。旧长度不一致，严格标记`lengths_comparable=false`。

**优先B：补足更公平的真实写作对照，而不是修存储。** 至少新增另一部原创仙侠因果冲突题；争取A/B/C/D四臂、同一模型、相似初始设定、目标800/1600/3200/6400中文含标点字符，**实际输出长度差原则上≤10%**；D额外规划调用必须设等预算对照或单列性价比，不能靠更多调用夺冠。固定总调用和token上限、模型版本、顺序、题目和失败处理，**先预注册再付费**；不自动重试或填充废话凑长度。

**优先C：真正识别并评价逻辑问题与写作技巧实效。** 人物目标→阻力→已知信息→行动→代价→具体后果→下一场景状态，逐条用正文反证/替代解释检查。V99只能自动定位两处短引文字，文学矛盾真实性必须由独立可信评阅者判定；记录第一处硬错误的中文字符位置、每千字错误密度、文学自然度与叙事张力。没有审核时维持`UNDETERMINED`，不把`null`写成零错误。

**优先D：再针对真实负例调整滚动规划机制。** 如果C/D只写出“因此、于是”而没有发生真实行为改变，必须作为文学失败，即使SHA吻合也不能PASS。滚动计划应追踪角色欲望、障碍、情节债务、能力/物品变化，但不要重造第二套人物知识库；只复用现有FactJournal/StoryWorkTree/候选写作结构，并且保持旧A/B/C回退能力与原始候选。

## 五、验收和安全红线

- 不再反复升级R2、无限加Skill、扩大模型上下文来替代创作能力；不能根据自己写的计划/自己评分证明自己写得好。
- 旧V92 15章经验永久备份需要保留，**不是继续重训或重新阅读前15章的理由**。V88失败案例仍保留，第16章不启动。
- V95线上权威head未部署，真实事实不能自发写入`KNOWN`、也不允许新WRITE自动授权。V93/V94合成CAS只是恢复技术验收，不可冒充学过的真实人物。
- 实际Railway Python服务处于安全idle；下一轮要先核`describe_service`＋最新部署日志，避免误以为部署源是V96。真实新模型测试若将启动，先冻结凭证权限、预算/唯一性预注册、独立读回和禁重试，并只操作明示候选，不改变正式章节/文学晋级。
- 如果同一个逻辑缺陷修两轮仍无法改善，停止临时补丁，返回相关GitHub/ACL方案及独立负例分析。
- **不得宣称**“WF已经解决AI超1000字逻辑紊乱”。当前进度是：工程场景闭环+初次真实A/B/C+滚动D候选机制+真实引用证据合同，但**缺少D真实同条件对照、等长多题材样本、独立文学盲评与真实叙事因果提升证明**。

**下一轮正确开场动作**：从GitHub `v99-causal-quality-blind-review` 的`writerforge/v96_causal_turns.py`、`writerforge/v98_rolling_causal_planner.py`、`writerforge/v99_longform_quality_evidence.py` 和V97清单CAS入手；优先准备既有三臂盲评与公平第二题的实验预算，而不是新写一整套WriterForge。
