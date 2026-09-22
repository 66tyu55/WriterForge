# 40 Delta Detector｜变化差异检测器

## 目标
防止每写一句都重新扫描整个学海库。

比较：

`previous_write_state`
vs
`current_write_state`

只输出 delta。

## 示例

旧：
```yaml
scene.location: 山门外
scene.tension: 1
character.emotional_state: 克制
```

新：
```yaml
scene.location: 戒律堂
scene.tension: 3
character.emotional_state: 愤怒但不能发作
```

Delta：
```yaml
changed:
  - scene.location
  - scene.tension
  - character.emotional_state
```

随后由 Retrieval Policy Engine 决定是否需要新知识。

## 不触发
纯文字润色但故事状态没变时，不应刷新所有检索。
