# WriterForge V40｜WF原生阅读功能零模型实测（2026-10-17）

**界限**：本轮不让其他模型或考官代答，只使用WF当前Python/SQLite与Skill代码；不是证明搭载固定宿主模型的WF永远不能理解文学。

## 实际考卷
- 原典：劉鶚《老殘遊記》第七回，Gutenberg #25124，目录锁定Git blob SHA1 8d20364de9813236c3ada3759b559b3945dc2a3d。
- 原文章节正文6321字符，保留第七回编号；文件 exams/wf_v40_reader_ch07/reader_packet.txt。manifest.json只有来源/指纹信息，EXAM.md只有考题，没有标准答案。
- 公共GitHub Actions #39029859109 已成功执行无模型测试，产生考试包和实测JSON回执（Artifacts，保存30天）。
- 原章SHA256 6a793df85516d7ac8b455cff0065fb4614ad3622ca565a93f8d6224db31134c3；最终读取包SHA256 57d94e288701f004a55c2293bd36a13a46447e3d67fd05a62a9bc22cbe21c13f。

## 真实WF边界和结果
- OriginalStudy.ingest真实执行，文本切分265单元，SQLite入库265源文跨度，学海可检索255条短片段，关闭重开成功。该章没有单元超过160字的截断。结构读取通过。
- ReaderLearningSession只保存调用方提交的ReaderReaction，并不自己生成首读人物分析：R-TRACE=BLOCKED。
- SceneLiteraryStudy.run要求外部model_call方能语义初读和深读：R-ANALYZE/R-CRAFT=BLOCKED。
- VerifiedWritingFlow负责生成prompt与引用，实际文学正文仍靠宿主生成：W-CLOSED=BLOCKED。
- 没有完整自写小说，R-REVIEW=BLOCKED。没有任何WF文学答案或考官补写范文。
- **这些是代码能力边界，不是WF对文学题作错了。** 无任何远端/本地语言模型调用，零Token消费；未证明文学改进，技能不晋级。

## 技术性修复
原parse_original只能接受从第一回开始连续编号，导致最初需要把独立第七回包装成考试槽位第一回。V40新增显式sequence_start与OriginalStudy.ingest(source_sequence_start=7)，保留第七回原样，旧完整原著默认首章1不变；修复后重跑同一原文，动作成功。全量测试 #39029910026 completed/success：571 tests，skip 4。测试数与其他分支独立。

## 后续实验反作弊标准
若验证“作为技能运行的WF确实学会了叙事”，必须固定同一个宿主模型，严格隔离裸体宿主、加载WF空记忆、加载WF冻结学习记忆三态，由WF真实学习与写作，再以冻结来源/写前/写后正文引用独立验证。不能改用不同模型分别帮助WF阅读、构思、写作或批评。若不运行宿主推理，单靠目前WF Python代码无法生成文学叙事分析或小说；绝不可把关键词入库冒充理解。

第一课程 NOT_PASSED，第二窗口 LOCKED，历史V35—V39不回写。
