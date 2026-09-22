# 21 角色生命线 / Character State Engine

## 目标
角色不是静态卡片，而是持续变化的状态机。

## 每个重要角色维护
```yaml
identity:
long_term_desire:
current_desire:
fear:
belief:
misbelief:
secret:
current_goal:
current_obstacle:
physical_state:
emotional_state:
knowledge:
inventory:
relationships:
promises:
recent_change:
```

## 角色变化
每个场景结束至少检查：
- 欲望是否变化；
- 信任是否变化；
- 知识是否增加；
- 身体状态是否变化；
- 是否形成新误解；
- 是否做出不可逆选择。

## 禁止
- “性格冷酷”成为所有场景的唯一反应规则；
- 角色无论经历什么都不变化；
- 人物行为只服务剧情，不服务自己的欲望。
