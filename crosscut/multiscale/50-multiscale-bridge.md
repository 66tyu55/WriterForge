# 50C Multiscale Bridge｜尺度桥

Middleware 做两种检查：

1. Downstream relevance
   - 当前句是否仍服务段落
   - 段落是否服务场景
   - 场景是否服务章节

2. Upstream emergence
   - 多个低层变化是否持续指向新主题/人物弧/情节方向

返回：
```yaml
alignment:
drift:
upward_signals:
```

避免每写一句都重算整本书；只在章节/场景边界或明显 drift 时触发高层检查。
