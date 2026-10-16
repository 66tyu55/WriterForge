# WriterForge · 文笔与文风：先止损，再证明提升

## 动机

已有三章真实作品被反馈为质量不佳；重新“再写三章”不是修复。
现有原著学习是结构化证据、启发式标签，不是语义文学训练或模型微调。
直接把“结构类别、技法编号、原著摘录”灌入正文 prompt，会把文学表达变成任务清单。

参照项目： [PenglongHuang/chinese-novelist-skill](https://github.com/PenglongHuang/chinese-novelist-skill)。
只吸收**写作前的正文语态参照**和**最近场景衔接**，不照搬固定的对话百分比、
每章转折配额、自动挑选第一章最佳段落等做法。

## 已接到真实模型生成入口的行为

- `VerifiedWritingFlow.prepare`: 原著检索和结构技巧仍用于**来源审计**，默认不直接进入文学正文 prompt。
- `WritingCompanion`: 仅显式作者改稿偏好进入正文；“作者未参与的 AI 初稿节奏统计”不再被暗示为作者文风。
- 最近两段已接受正文尾部：仅作故事事实衔接，**不是**值得模仿的风格范例。
- `ProseStyleStore`: 一个项目只保存一段 120–1200 字且由作者**明确认可**的原创文字作为文风参照。
  没有参照就执行基础模型的自由创作，不自动从初稿、销量榜、原著拆解中挑“最佳文字”。
- `writerforge/writing_assist.py`: 真正的实时续写与自动章节生成把已认可文风样段放在
  **所有任务说明、事实背景和前文之后**；只输出 JSON 的情节规划步骤不受样段干扰。
- 通过 hash 追踪来源。若文风样段引用已接受章节，该章节被删改后样段自动失效；
  禁止直接复制其连续 24 字及以上的内容。
- 产物 manifest 记录 `prose_style.mode` 与样段 SHA256，
  不公开或复制样段正文，不把生成效果写成已经提高质量。

## 如何真正使用

第一步：以**作者明确评价合格**的原创新作片段制作一份 120–1200 字 UTF-8 文本，
不要从质量差的旧三章里自动抽取。

```bash
python -m writerforge.cli --db project.sqlite3 prose-style-approve \
  --project novel --file approved-style.txt --confirm-quality-reviewed
```

如果原文**已经在同项目的 accepted_prose 里**，可以加
`--source-scope scene-1`，这会校验文字确实存在于该场景并绑定其 SHA256。
之后改写这段场景时，旧参考自动停用。

查看生效状态（不打印正文）：

```bash
python -m writerforge.cli --db project.sqlite3 prose-style-status --project novel
```

不喜欢随时撤销：

```bash
python -m writerforge.cli --db project.sqlite3 prose-style-disable --project novel
```

仅当有可用的私有 R2 凭证与已经学过原文的 SQLite 时，`prose-style-approve` 或
`prose-style-disable` 可带 `--backup-r2`，使用原有 R2 vault 保存同一本项目数据库。
使用正常备份，不使用针对纯来源数据的 `--edition` 去重快捷路径。
不需要 Google Drive、GPT 临时存储或公开 GitHub 原文。

## 验收边界

已具备结构性单测：无默认证据污染、未获作者认可不启用、限额、跨项目隔离、
原稿改写失效、连续抄写拦截，以及模拟 R2 全新恢复。
CI 通过只证明工程接线；**没有真实模型的盲读结果，就不能声称文笔已经改善**。

下一次评估应直接用那份既有失败文本里的一个局部场景：
在**同一模型、同一事实设定、同等输出预算**下比较 A 原始模型、B 低干预、
C 显式认可文风，盲评人物真实感、因果、细节选择、语气自然度和继续阅读意愿。
效果差的处理路径必须能关闭，不能自动把差稿提升为训练材料。
