# Actual Reader Corpus Integration

## 目标

让 WriterForge 不再只由 AI 自己判断“读者会不会喜欢”。

## 数据链

```text
真实长评
↓
Genre Isolation
↓
Reader Trajectory
↓
Signals
↓
ActualReaderCritic
↓
Review Questions
↓
当前章节审查
```

## 不做的事情

- 不把评论当文学真理。
- 不因一条负评修改作品。
- 不把评论原话拼进正文。
- 不跨类型直接套偏好。
- 不让评论库常驻上下文。

## 证据等级

高：
- 同一读者长期追评
- 二刷/多刷
- 明确阅读数十/上百小时
- 明确弃读点/回归点
- 具体指出 Arc/角色/伏笔长期影响

中：
- 完结长评但缺少阅读轨迹

低：
- 单次泛泛长评

当前内置库优先使用高等级证据。
