# WriterForge V101：人物关系、剧情理解与好坏鉴赏内核

2026-10-21，隔离分支 v101-narrative-understanding-relationship-core。**本轮有真实代码及离线CI；没有发起新的DeepSeek请求、没有阅读新原著、没有人类文学盲评，也没有从V80旧阅读结果凭空补出真正理解。** 前15章R2经验、V97已完成七次模型请求、V100匿名文稿封存、V49 THIRD_STRIKE_FAILED / 第二文学窗口LOCKED均保持原样。

## 一、调研的可复用前辈

| 方案 | 借鉴内容 | 限制和决定 |
|---|---|---|
| [StoryWeave](https://github.com/Shashank-ssls/StoryWeave) (MIT) | 按阅读章节限制人物、身份、关系的可见范围；引句出处 | 直接安装有GB级NLP模型依赖，隐含社会关系召回仍不高；仅借鉴阅读边界与证据约束 |
| [清华 StoryWriter](https://github.com/THU-KEG/StoryWriter) | 情节事件和事件关系、后续章计划受旧事件影响 | 面向生成的研究原型，不直接复制其代码或称它能验证文学真实因果 |
| [Story Engine](https://github.com/jinwanyaozaoshui/story-engine) (MIT) | 人物目标、阻力、选择、代价、行动反馈、跨章剧情债务、删除事件后的反事实 | 是情节推进诊断框架，不是文学鉴赏替代品 |
| [ConStory-Bench](https://github.com/Picrew/ConStory-Bench) (MIT) | 人物认知、剧情时间与因果、世界规则、写作视角错误及其位置 | 是外部评测体系，不能当学习软件的自我颁奖证书 |
| [WritingPreferenceBench](https://github.com/WritingPreferenceBench/Writing-Preference-Bench) (ODC-BY) | 600组中文专家偏好对，用以测试文学表达好坏 | 未把公开数据下载到WF。公开中文选好/选差平均篇幅存在差异；必须逐题核对长度、标签与授权 |
| [BookNLP](https://github.com/booknlp/booknlp) | 人物共指、对话归属、事件提取设计 | 主要为英文训练，不直接用于WF中文长篇 |

采用方法思想，没有复制外部代码；不新建大数据库、不加载外部GB级模型。

## 二、实际代码与边界

1. [writerforge/v101_narrative_reader.py](../writerforge/v101_narrative_reader.py)：严格绑定同一作品ID、私有原文SHA、已读章节和当前原文单位。WF提出人物ID/意图/知道与猜测；有方向的人物关系、后续关系变更；情节中的目标/阻碍/动作/可见后果/实际代价候选/未兑现问题；好句和弱句的文字效果/反事实改写/另一种解释。所有直接原文引用必须唯一实际存在，宿主计算偏移和SHA；不同作品的同名人物不能自动并为同一身份，同作品同名但不同ID、同ID不同名拒绝未审合并。关系、动机、因果及好坏仍是未验证候选，不生成KNOWN。
2. [writerforge/v101_sealed_read_bridge.py](../writerforge/v101_sealed_read_bridge.py)：复用老V79/V80真实PASS A首读R2账本，先按每个单位及最终seal验证真实读过，才显式多运行一次WF的模型文学理解；失败不自动重试，原始模型JSON优先保留私有CAS，再校验文学候选。单份源+章节+源key有一条唯一不可变预约槽，即使提示词/预算/运行重启改变也不默默重复付费。
3. [writerforge/v80_large_chapter_batch.py](../writerforge/v80_large_chapter_batch.py)：新增明确选择的 complete_with_narrative_reading 流程。按先前私有CAS封存的关系/情节候选生成最多2300字符的阅读视角投影，注入下一章首次读提示，然后仍用旧V80完整逐段阅读、封存、分析并进行V101额外鉴赏。原 complete 默认行为和历史训练调用不改。旧学习课程不会自动多付费，不能在未授权时开启第16章。
4. [writerforge/v101_quality_calibration.py](../writerforge/v101_quality_calibration.py)：好坏不能只发“有文采”的标签，必须同时引用真实A/B原句、解释理由、替换表达的损益和可信反对理由。实际长度差超过10%则拒绝公平比分；只有外部标签才计算候选一致性。外部评委身份真实性无法从用户自填布尔值证明，因此所有返回都不允许文学晋级。
5. [tests/test_v101_narrative_reader.py](../tests/test_v101_narrative_reader.py)：合成仙侠故事的跨章人物关系变化、真实行动/后果、反事实句法、未来知识泄漏、跨书同名、角色伪造、重复/不在原文中的引句、质量长度偏差等反例。

### 真实源码可调用路径（当前只供未来明确授权实验）

- WF在自己的LEARN运行模式读取章节，并以原V80真实R2的逐单位first_read→seal→analyse→reflection完成每章。
- 调用新的 complete_with_narrative_reading，在原R2已签收后执行新的最多一次DeepSeek craft_analysis，单次预约输出不超过4100 tokens，使用原150000批次总预算，无自动重试。
- 返回的模型原答和关系/剧情/文笔候选仅存原私有R2不可变CAS。后一章仅从先前候选建有界视图；观点一律是待核验假说，不抄旧原著进WRITE，不自动生成新人物KNOWN。
- 该接口**本轮未在真实模型上执行**。这说明软件入口和源验证能工作，不是WF已经通过真实文学理解考试。

## 三、工程CI状态与不可掩盖的失败

- 首次V101源码全仓回归成功：https://github.com/66tyu55/WriterForge/actions/runs/39530827318
- 新的PASS A接线与跨章身份证据回归成功：https://github.com/66tyu55/WriterForge/actions/runs/39531043285
- 一次真实红色：https://github.com/66tyu55/WriterForge/actions/runs/39531169288 。新增合成的好坏字数负例不慎复制整个B文本三次，导致一个评语引句不再唯一；生产引句校验正确拒绝。随后只调整测试文本为保留唯一引用、仅扩充不含引用的普通句子，生产校验无放宽。
- 修订回归成功：https://github.com/66tyu55/WriterForge/actions/runs/39531220910
- 防止同章不同提示重试再次收费的唯一预约槽版本成功：https://github.com/66tyu55/WriterForge/actions/runs/39531305512

这是离线工程验收：**0新模型请求、0真实文学语义验证、0新学习章节**。不可凭单元测试或引文存在自称文学能力成长。后续代码修改的最终CI要以最后一份运行结果为准。

## 四、必须通过的下一道文学考试

WF自己用明确允许的新中国原创故事逐章阅读。首章让WF提出人物愿望/关系猜测；次章用真实动作或对白改变关系并造成后续可见代价；第三章以反转或新证据检验此前WF的判断；考核它能否修正错误解释，不把人物撒谎当真相。再从真实段落选一好一弱的表达并比较替换写法对情绪、人物和叙事效果的损失。可信独立评委判因果、代价、剧情债务和好坏是否准确，错误及负例永久保留。最后用未知原创情境做同模型等字数写作对照。没有这些真实成绩，文学能力维持 UNDETERMINED。

**用户长期目标不变：WF成为理解人物、关系、剧情、语言并能自然写作的作家，不是加一个索引或凭软件PASS宣布学会。**
