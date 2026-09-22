# 44 Learning Gap Queue｜学习缺口队列

## 目标
实现“创作发现不足，但不在创作时学习”。

WRITE 可以提出需求，但不能执行学习。

## 写入格式

```yaml
gap_id:
requested_at:
requested_by:
capability:
genre:
culture:
scene_context:
why_missing:
priority:
status: pending
```

## LEARN 下次启动时
可以读取 pending gaps，决定：
- 哪些值得补；
- 需要什么类型的原著；
- 当前已有来源是否足够；
- 是否拒绝这个需求。

处理后：
`status = resolved | rejected | deferred`

## 这就是受控反馈
WRITE -> 提交缺口
LEARN -> 下次处理
但两者永不并发。
