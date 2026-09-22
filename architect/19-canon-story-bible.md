# 19 Canon Story Bible / 故事总典

## 目标
建立“什么已经成为事实”的唯一可信来源，防止长篇中设定漂移。

## Canon 分层
```yaml
canon:
  immutable:
  mutable:
  planned:
  deprecated:
```

### immutable
已经在正文明确成立，除非正式 retcon，否则不能改。

### mutable
已经成立但允许自然变化，例如人物关系、伤势、持有物。

### planned
未来计划，还未发生，不得当作当前事实。

### deprecated
已废弃设定，任何后续检索必须排除。

## 每条 Canon
```yaml
canon_id:
type: character|world|location|item|rule|relationship|event
statement:
status:
established_at:
last_verified_at:
depends_on: []
conflicts_with: []
```

## 强制规则
- 正文写入前先查 Canon。
- 候选句不能直接写入 Canon。
- 只有“最终接受句”才更新 Canon。
- 修改旧设定必须产生 `canon_patch`。
