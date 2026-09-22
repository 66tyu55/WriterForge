# 20 因果故事引擎

## 目标
禁止“因为作者需要，所以事情发生”。

## 每个重要事件必须回答
```yaml
event:
cause:
trigger:
character_choice:
opposition:
immediate_result:
unexpected_consequence:
long_term_consequence:
opens:
closes:
```

## 因果链
推荐检查：
`因为 A -> 所以 B -> 但是 C -> 因此 D`

避免：
`A -> 然后 B -> 然后 C`

## 无因果事件
以下情况必须阻塞：
- 新敌人突然出现但无法说明如何找到主角；
- 人物突然改变立场但无触发；
- 道具突然具有新能力；
- 角色突然知道未知信息；
- 事件只为推动下一章而存在。

## 每章结束
输出：
- 本章产生的直接后果；
- 延迟后果；
- 下一章必须承接的至少一项后果。
