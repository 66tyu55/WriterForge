# 46 Cache & Version Manager｜缓存与版本管理

## 目标
控制检索频率与知识版本。

## Cache Key
建议：

```text
snapshot_id
+ genre
+ culture
+ scene_type
+ function
+ effect
+ pacing_phase
```

## 失效条件
只有依赖字段发生变化才失效缓存。

例如：
- 只是换了一个普通形容词，不失效；
- Scene Goal 变了，失效；
- POV 变了，失效；
- 情绪阶段从压抑变爆发，失效。

## Snapshot
WRITE 开始时 pin 一个 snapshot。
结束章节后才允许用户显式切换到新 snapshot。
