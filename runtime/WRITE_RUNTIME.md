# WRITE Runtime｜创作运行时

## 唯一职责
使用已经发布的学海库进行小说设计、创作、回读、修订与审稿。

## 模式锁
进入 `mode=WRITE` 后：

允许：
- 读取 published 学海库 snapshot
- 读取 Canon / Character / Scene / Reader / Promise 状态
- 通过 Middleware 查询学习成果
- 写正文
- 修正文
- 更新小说状态
- 产生“学习缺口请求”

禁止：
- 直接读取原著全文进行新学习
- 修改学海库内容
- 把当前写作生成的句子写回学海库
- 在 WRITE 中重新给原著打分、分类、加权
- 因为当前句不会写而临时“学习几章原著”

## 学习能力不足
若中间件返回：
`MISSING_LIBRARY_CAPABILITY`

WRITE 不得偷偷进入 LEARN。

只写入：
`learning_gap_queue.jsonl`

例如：

```yaml
gap:
  capability: 宗门内部低烈度政治冲突
  context: 当前卷需要
  priority: medium
  requested_by: scene_023
```

下次进入 LEARN 模式时再处理。
