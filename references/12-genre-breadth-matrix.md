# 子技能 12：类型广度矩阵与反狭隘控制

## 目标
防止 AI 把“玄幻、恐怖、搞笑、热血”等标签当成单一写法，最后所有场景都一个味道。

## 核心思想
一个长篇类型小说通常包含多种“场景功能”和“情绪效果”。
例如玄幻可以同时出现：
- 神秘
- 恐怖
- 热血
- 愤怒
- 仇恨
- 轻松
- 搞笑
- 温情
- 羞辱
- 希望
- 绝望
- 惊奇
- 平静
- 日常
- 悬疑
- 敬畏

但**不是要求每本书必须拥有全部标签**。
本技能关注的是：
> 学海库是否被某一种效果垄断，从而让 AI 误以为“玄幻 = 永远热血”或“恐怖 = 永远阴森”。

## 建立“类型能力矩阵”

```yaml
genre: 中国玄幻小说
dimensions:
  worldbuilding:
    rule_reveal:
    power_gap:
    strange_space:
    faction_order:
  conflict:
    duel:
    siege:
    humiliation:
    revenge:
    negotiation:
  emotional_effect:
    horror:
    humor:
    anger:
    hot_blooded:
    hatred:
    tenderness:
    awe:
    mystery:
    grief:
  pacing:
    quiet:
    buildup:
    burst:
    aftermath:
  social_scene:
    family:
    master_disciple:
    market:
    sect:
    court:
    wilderness:
```

每个单元格记录：
- 是否有真实原著证据；
- 来自哪部作品；
- 来自哪个章节；
- 使用了什么技法；
- 当前库存是否过度集中。

## 防止标签化
当某类库存占比过高时，例如：
- “热血战斗”占玄幻库存 70%；
- “恐怖”全部都是黑暗/血腥/尖叫；
- “搞笑”全部都是插科打诨；

必须触发：
`BREADTH_WARNING`

并暂停继续吸收同质案例，优先寻找：
- 同目标、不同处理；
- 同类型、不同场景；
- 同情绪、不同强度；
- 同效果、不同感官通道。

## 输出
不是说“玄幻必须这样写”，而是告诉总控：
- 当前学海库在哪些维度有能力；
- 哪些维度缺失；
- 哪些维度已被单一路径污染。
