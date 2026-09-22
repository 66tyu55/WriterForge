# 55 Actual Reader Critic｜真实长期读者评论技能

## 定位

这不是新的“写作生成 Skill”。

它是一个 **P2 Review Skill**：

```text
当前章节/Arc
↓
确定主类型
↓
确定风险信号
↓
只查该类型真实长期读者语料
↓
生成审稿问题
↓
审查当前正文
```

## 数据源

当前内置：
`data/actual_reader/`

只包含：
- 长期追更
- 数十/上百小时阅读
- 完结后回顾
- 二刷/多刷
- 弃坑→回归
- 明确前中后态度变化

短评、单句情绪、纯评分已排除。

## 强制隔离

```text
primary_genre
```

必须先匹配。

禁止：

```text
中文玄幻
← 直接套用 →
HP同人 / Worm / LitRPG
```

跨类型只允许方法研究，不允许直接作为当前 Reader Baseline。

## 评论如何“吸收”

评论不是训练样本直接喂给 WRITE。

先变成：

```text
Reader trajectory
Reader failure/success signal
长期阅读结果
可验证审稿问题
```

例如真实评论显示：

```text
某类反转前期有效
→ 后期反复使用
→ 长期读者产生疲劳
```

技能不会说：

“禁止反转。”

而会在当前作品出现相同风险时问：

```text
这个反转机制最近多少章已经使用过？
是否仍带来新的因果/人物意义？
长期读者会不会只看到套路重复？
```

## 与 V9 Reader-First 的关系

- Source Reader：学习原著第一次阅读体验。
- Predicted Reader：冷读当前作品。
- Actual Reader Critic：引用真实长期读者经验审查当前作品。
- Actual Beta Reader：当前作品真正的真人读者反馈。

优先级：

```text
当前作品 Actual Beta Reader
>
同类型 Actual Reader Corpus
>
Predicted Reader
```

## 效率

只在：
- Chapter Boundary
- Arc Boundary
- Major Revision
- 明确 Reader Risk

触发。

绝不每句调用。
