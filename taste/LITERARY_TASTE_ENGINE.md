# Literary Taste Engine｜小说家的审美选择

Taste 解决的问题不是“这一段有没有错误”，而是：多个版本都成立时，为什么当前作品应该选择其中一个。

## 不做绝对评分

禁止把文学性简化成 `A=91, B=88`。

Taste 默认使用 pairwise comparison：

```text
Candidate A vs Candidate B
↓
先解释差异与代价
↓
给出当前作品下的偏好
↓
交换顺序 B vs A 再判一次
```

如果交换顺序后结果翻转：`JUDGE_UNSTABLE`，该判断不得写入 Taste Memory。

## 判断维度（不是固定权重）

- Reader Effect
- Character Truth
- Narrative Pressure
- Specificity
- Restraint
- Surprise + Inevitability
- Voice
- Aftertaste
- Novelty
- Long-term Echo

具体场景可以只关心其中 2-4 个。禁止全维度打卡。

## 三种证据保持分层

1. `Source Taste`：原著顺序阅读中观察到的真实选择及其代价。
2. `Actual Reader Taste`：同类型长期读者与当前 Beta Reader 的真实反应。
3. `Project Taste`：当前作品逐渐形成的审美契约与用户选择。

它们可以共同支持判断，但不能混成一个总分，也不能把某位经典作者的选择宣布为普遍真理。

## Taste Memory

保存条件性判断，而不是“规则”：

```yaml
context:
preferred:
alternative:
reasons:
tradeoffs:
conditions:
source:
confidence:
```

例如：“不可逆动作已经完成情绪表达时，继续解释常降低余味”只是有条件观察；如果认知转变本身就是高潮，明确说出也可能成立。

## Writer / Judge 隔离

- Writer 不评价自己的 Candidate。
- Taste Judge 不看候选生成顺序、模型身份、token/成本等无关信息。
- Judge 只看当前 Scene Contract、必要前文和候选正文。
- Taste Promotion 必须有外部读者锚点。
