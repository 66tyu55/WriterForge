# 48B Taste Write｜审美决策端（V12）

## 目标

WRITE 面对多个都正确的候选时，以当前作品为单位做文学选择，而不是用统一“高级文笔”评分。

## 默认流程

只有 `hard_literary_choice / taste_review / major_revision` 才调用 Taste：

```text
A vs B
↓
Taste Argument：差异、效果、代价、条件
↓
选择
↓
交换顺序 B vs A 再判断
↓
一致：可形成候选 Taste Observation
翻票：JUDGE_UNSTABLE，不学习
```

## Project Taste Contract

```yaml
preferred:
avoid:
tolerated:
deliberate_exceptions:
```

## Taste Observation

```yaml
context:
preferred_id:
alternative_id:
reasons:
tradeoffs:
conditions:
source:
confidence:
```

禁止保存“结尾永远不要解释”之类无条件规则。

## 三层证据

- Source Taste Evidence：原著 LEARN。
- Actual Reader / Beta Reader：真实读者结果。
- Project Taste：当前项目和用户实际选择。

优先级与证据类型保持可见，不混成一个总分。
