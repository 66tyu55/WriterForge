# 22 人物知识状态账本

## 目标
严格管理“谁知道什么”。

## 三态
```yaml
knows:
suspects:
does_not_know:
```

每条知识附：
```yaml
fact_id:
learned_at:
source:
confidence:
can_share:
```

## 强制检查
人物在说出、想到、利用任何关键信息前：
1. 是否已经知道；
2. 从哪里知道；
3. 什么时候知道；
4. 是否可能记错；
5. 是否正在撒谎。

## 阻塞错误
`KNOWLEDGE_LEAK`
