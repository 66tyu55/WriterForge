# 47 Literature Middleware Orchestrator｜文学中间件总控

## 职责
Middleware 只做 5 件事：

1. Watch：观察 WRITE 状态
2. Diff：判断发生什么变化
3. Decide：判断是否需要查询学海库
4. Retrieve：只读查询固定 snapshot
5. Adapt：把学习成果转成原创写作指导

它不：
- 学习原著
- 写正式正文
- 修改学海库
- 修改 Canon 决策

## 主循环

```text
WRITE accepts sentence
        ↓
story_store changes
        ↓
Observer
        ↓
Delta Detector
        ↓
Retrieval Policy
   ↙             ↘
no query       query needed
   ↓              ↓
continue      Xuehai Gateway
                  ↓
            Evidence Adapter
                  ↓
             guidance cache
                  ↓
            WRITE next sentence
```

## 卡住时

```text
WRITE blocked
  ↓
Middleware query existing Xuehai
  ↓
有能力 -> 返回方法候选
无能力 -> MISSING_LIBRARY_CAPABILITY
  ↓
写入 Learning Gap Queue
  ↓
WRITE 使用现有能力继续/调整场景
```

绝不自动切入 LEARN。


# V5 Cross-cut Signals

Middleware 额外监督五类跨层信号：

- `TASTE_DECISION`
- `ENTER_DISCOVERY_WINDOW`
- `UPWARD_SIGNAL`
- `EMERGENCE_PROPOSAL`
- `REWRITE_IMPACT`

这些信号只连接 LEARN 已发布知识与 WRITE 项目状态，
不允许 LEARN/WRITE 并发。
