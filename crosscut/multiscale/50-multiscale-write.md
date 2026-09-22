# 50B Multiscale Write｜多尺度创作约束

WRITE 不允许只有 Sentence Loop。

必须同时维护：

```yaml
book_intent:
arc_contract:
chapter_contract:
scene_contract:
paragraph_micro_goal:
sentence_function:
```

## 双向一致性
向下：
Book/Arc/Chapter 给 Scene/Paragraph/Sentence 约束。

向上：
若连续多个 Scene 产生同一新方向，允许生成 `UPWARD_SIGNAL`，
提示 Arc/Chapter 可能需要调整。

注意：
向上信号不是自动改计划。
