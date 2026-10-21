# WriterForge V102：情感 × 因果 × 代价 × 后果的实际融合

2026-10-21。开发隔离分支 v102-emotion-cause-cost-consequence，基于已验证V101阅读内核。**这一轮做了真实GitHub源码改动与全仓无模型回归；尚未执行新的DeepSeek真实文学阅读、任何新R2训练写入、V97重播或独立文学评分。** V49 THIRD_STRIKE_FAILED、文学第二窗口LOCKED、V92前15章经验和V100三份匿名原文封存均保持不变。

## 一、融合的真正目标，不是保存四个标签

人物不是只会说“很悲伤”，故事不是加几个“因此/于是”。关注四条相互依赖的线索：

- **情感**：角色原来想要什么、害怕什么；哪句真实对话/哪件亲历事实刺激了它；随后出现什么可见反应；反应有没有改变人物的下一次选择。内心可有留白，模型不能把自己的心理分析冒充作者真实意图。
- **因果**：角色如何行动、受何阻碍、实际写出的后果是否在动作之后；此前没有写过的事实不得变成“既定前因”；倒叙和故意误判允许保留为未知。
- **代价**：实际失去的物品、时间、机会、关系、信任或能力应在正文有证据。声称“沉重代价”或“答应过某人”还不等于真的付出了代价；候选引句存在只说明来源存在，语义仍待阅读复核。
- **后果**：实际后果和未偿债务必须影响后续场景，不能在章节间悄悄消失；解除冲突需合理的可见行动，不能由模型自称“已经解决”即自动清零。

简单说明：一个人救下仇人的孩子，可能因此失去宗门许可；伙伴由敬重变成怀疑。写得好，后续对话、行动和人际关系应该被这个代价实质改变，而不只是重复“他付出了代价”。

## 二、源代码已经真实接入两条WF路线

### A：LEARN / 阅读

- [writerforge/v102_reader_emotion.py](../writerforge/v102_reader_emotion.py) 从已经按顺序读过且封存的章节中，要求WF自行提出人物感受前后变化、刺激原句、真实反应原句、可见损失、关联的剧情事件ID、关联的方向性人物关系ID、下一步可选行动的变化及另一种解释。
- 所有引用都必须在当前已读原文单位真实存在，宿主按原文计算位置/哈希；情感触发必须发生在反应之前；事件和关系ID必须确实出现在本章V101已有证据中，不允许使用未读章节或虚构角色；结果全是待验证的候选理解。
- [writerforge/v101_narrative_reader.py](../writerforge/v101_narrative_reader.py) 原有阅读JSON四字段在默认模式下不变；只有显式include_emotions=True才使用第五个emotions字段。同一DeepSeek文学分析调用即尝试四者结合，**不增加单独情绪分析的第二次调用**；后续章候选上下文里也允许带有限的情绪变化假说，但不得转为FactJournal KNOWN。
- [writerforge/v101_sealed_read_bridge.py](../writerforge/v101_sealed_read_bridge.py) 和 [writerforge/v80_large_chapter_batch.py](../writerforge/v80_large_chapter_batch.py) 在已有首读PASS-A来源签收、逐章封存和私有R2不可变CAS唯一预约保护下，把这个可选参数接入WF自己的LEARN调用。历史前15章不会被加上编造的V102理解分数，未重付费。

### B：WRITE / 真正创作

- [writerforge/v102_emotional_causality.py](../writerforge/v102_emotional_causality.py) 复用V96严格的动作/后果/前因原句核查和V98真实正文驱动滚动规划，每一幕额外允许一个affect候选：刺激、反应、当前感受、实付代价原句、和V96一致的正文后果原句、下一选择的压力。没有真实表达时affect=null，不为了过检测强迫每幕反转或加戏。
- [writerforge/writing_assist.py](../writerforge/writing_assist.py) 新增作者主动选择的draft_mode=emotion_rolling（E）。先写真正候选正文，再用其实际V96回执和V102情绪/压力轨迹调整下一幕目标；沿用D的滚动规划模型调用次数和限制，**不额外增加调用次数**，但提示词可能更长，实际tokens费用仍可能不同。所有E草稿仍是未接受候选、0正式人物事实写入、0经验升级。
- 在同一任务最多两章范围内，E会把第一章有证据的情绪变化、尚未解决的代价和未确认的事实作为**候选背景**传给第二章的计划、写作与审查，防止它悄悄忘掉上章的关键压力。这个连续性只针对同一候选job，**不是多个进程/数十章永久人物状态大脑已完成**。
- [writerforge/studio_server.py](../writerforge/studio_server.py)、[writerforge/ui/studio.html](../writerforge/ui/studio.html) 的真实Studio服务/页面都有新的E手动选项；旧A/B/C/D完全保留，默认仍为A。当前生产Railway没有部署这个新分支，用户现有安全idle不受影响。
- 新证据文件v102_emotional_causality.json只保存当前候选原稿锚点/哈希/未确认的情感推断，供作者复核，不把旧小说源原文公开，不另起第二套人物关系库。

## 三、工程核验的边界与永久留红

- [tests/test_v102_emotional_causality.py](../tests/test_v102_emotional_causality.py) 合成正文中真实动作→后果→人物感受→后文剩余压力，测试伪造不存在代价、把反应写在触发之前、角色不属于已出场名单、上章回执SHA被篡改、安静场景不强迫情绪，以及在真正AutonomousWriting/Studio写作路径中E与D的调用次数可比、无自动二次调用、草稿未接受、同一两章任务延续上章压力。
- [tests/test_v102_reader_emotion.py](../tests/test_v102_reader_emotion.py) 完整阅读模块的角色ID、剧情事件ID、人物关系ID、真实引文、情感触发先于反应、同一个原V101封存读权限及CAS唯一预约槽。假的损失/未来事件/虚构关系必须拒绝，模型不能独立自评“理解了”。
- 首次全仓运行 [39535471509](https://github.com/66tyu55/WriterForge/actions/runs/39535471509) **红色**：合成阅读适配器使用第二章来源封存，却沿用了第一章e000001事件编号，真实严格检查正确拒绝。这是测试夹具冲突而不是模型文学判断；仅修正测试第二章事件编号，**没有放宽**原事件来源检查。
- 修正后 [39535600713](https://github.com/66tyu55/WriterForge/actions/runs/39535600713) **success**，其中包括旧A/B/C/D和新增E阅读/创作反例。随后增加跨章节压力传递和人物关系—情绪关联回归。以当前HEAD最后一轮CI为最终结果，绝不把历史绿灯自动算作之后新增代码的通过。
- **本轮真实付费模型调用0；R2真实读写0；文学语义分数仍UNDETERMINED。** 只有引文定位、调用预算、防重试、候选连续性和软件约束可以凭离线测试验收。

## 四、为什么还不能说WF已经“理解情感和代价”

字符串里存在“他哭了”“救人”“失去了一块玉”，并不证明失去的是有分量的东西；一枚玉可能只是装饰品，也可能是整章真正的选择代价。系统只有人物的实际愿望、关系、世界规则、后续可选行动发生了可信变化，才能由文学评审判断为有效的代价。

这次新功能明确区分可由程序证明的**文字事实**和必须依靠阅读、反事实、独立评审证明的**文学语义**。下一道价值最高的真实考试：给WF一篇此前不认识的原创短篇，分三次按顺序揭露人物决定、情绪变化与不可逆的代价，让WF自行预测和纠错；之后在完全新故事中用同模型等字数写A基准/D滚动/E四因素稿，分别盲评真实动机、代价有无改变选择、句子自然度。未完成外部独立审查前，不能晋级。


## 五、最终集成回归与中途失败留档

- 增加同一个E任务跨两章压力衔接的回归后：[GitHub #39535805035](https://github.com/66tyu55/WriterForge/actions/runs/39535805035) SUCCESS，原A/B/C/D兼容不变。
- 人物关系ID联动情感的Schema扩展阶段出现中途CI失败：[GitHub #39535990033](https://github.com/66tyu55/WriterForge/actions/runs/39535990033)、[#39536005659](https://github.com/66tyu55/WriterForge/actions/runs/39536005659)。按旧签名运行的合成测试尚未携带新关系字段，不能把红项删除或提前写成通过；同步更新来源绑定、回读及测试数据后，[GitHub #39536032638](https://github.com/66tyu55/WriterForge/actions/runs/39536032638) 已 SUCCESS。
- **最终分支HEAD b00ac404fd7fdd3cceb57c3f6ce1d3cfd77f5b42** 的 [GitHub Actions #39536170180](https://github.com/66tyu55/WriterForge/actions/runs/39536170180) SUCCESS：实际运行 **1111 项** Python 测试，**4 skipped、0 failures、0 errors**；JavaScript语法检查和原有伴写Benchmark均通过。真实模型0、真实R2网络操作0。其后任何代码/文档变更都须重新验证当前HEAD的CI。
- 仍然缺少的是**真正模型读一篇新小说的情感判断质量、真实模型生成E模式的文学自然度、跨独立作业的情绪与债务长期回放、可信独立盲评**。原V101的阅读侧候选不允许未经证实直接注入正式WRITE；本轮的创作E模式首先追踪其自身实际生成候选中的情感和代价，不冒充“从原著学会了文学手法”。
