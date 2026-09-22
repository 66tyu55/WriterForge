# 39 Reactive Context Observer｜响应式上下文观察器

## 目标
像响应式系统监听状态变化一样，监听小说创作状态。

它不写小说，也不学习原著。

## 被观察对象

```yaml
watch:
  scene.goal:
  scene.location:
  scene.time:
  scene.pov:
  scene.tension:
  paragraph.micro_goal:
  character.current_desire:
  character.emotional_state:
  character.knowledge:
  reader.questions:
  promises.open:
  draft.blocked:
  draft.last_sentence_function:
```

## Change Event

```yaml
event_id:
path:
old_value:
new_value:
cause:
scene_id:
timestamp:
```

只有真实变化才触发事件。

## 依赖追踪
Middleware 记录“当前写作依赖了哪些知识类型”。

例如：

```yaml
dependencies:
  scene.location:
    - environment_lexicon
    - location_methods
  scene.tension:
    - pacing_methods
  draft.blocked:
    - sentence_transition_methods
```

状态没变时，不重复检索。
