# 41 Retrieval Policy Engine｜检索策略引擎

## 目标
根据“发生了什么变化”决定该向学海库要什么。

不是关键词搜索器。

## 事件到查询意图

### scene.location changed
查询：
- 同文化/同类型地点描写方法
- 环境词域
- 空间行动方式

### scene.tension changed
查询：
- 相同张力阶段的方法
- buildup / burst / recovery 案例方法

### character.emotional_state changed
查询：
- 相同情绪但不同表达机制
- 动作、感官、对白处理
禁止只查“愤怒”这个词。

### paragraph.micro_goal changed
查询：
- 相同段落功能
- 承接方式
- 句尾落点

### draft.blocked = true
查询：
- 相同 sentence_function
- 相同前后状态转换
- 3–5 个方法候选

### new entity requested
查询：
- taxonomy
- naming patterns
- lexicon gate

## 查询格式

```yaml
query_intent:
  target_function:
  culture:
  genre:
  scene_type:
  emotional_effect:
  pacing_phase:
  sensory_channel:
  exclusions:
```

不直接传“关键词列表”作为主要检索逻辑。
