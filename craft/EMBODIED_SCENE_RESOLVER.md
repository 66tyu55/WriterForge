# Embodied Scene Resolver｜场景具身解析层

这不是一个新的写作 Skill，也不负责“添加声音/温度/五感描写”。

它解决的是更底层的问题：**世界与角色正在发生什么，因此自然会产生什么可以被感知的现象。**

```text
World State
+ Entity Properties
+ Action / Contact
+ Body & Emotion State
        ↓
Physical / Behavioral Consequences
        ↓
Perceptual Affordance Pool
        ↓
POV Attention Filter
        ↓
0~少量可用细节
        ↓
Writer 自己写成正文
```

## 核心原则

### 1. 感官不是配额
禁止：

```text
这一段已经有视觉
→ 再补声音
→ 再补气味
→ 再补触觉
```

正确逻辑：

```text
野猪在林地拱食
→ 鼻吻接触土层
→ 呼吸/嗅探 + 土层扰动
→ 如果 POV 能注意到，才可能进入正文
```

### 2. 声音是动作/材质/环境的结果
例如：

- 人走在木地板 → footfall 候选；
- 脚踩碎石 → gravel shift；
- 雨落瓦面 → rain striking tile；
- 金属发生接触 → metal contact resonance；
- 衣料快速移动 → fabric rustle。

Resolver 只返回语义事件，不直接返回漂亮句子。

### 3. 温度是世界状态
寒冷不是“为了增加氛围写一句冷”。

`temperature_c` 是环境事实，它可以产生：
- cold_air_exposure；
- 极冷时可能出现 breath condensation；
- 后续再由人物装备、体质、动作决定具体身体影响。

### 4. 情绪不能套固定身体反应
禁止：

```text
害怕 → 心跳加快
愤怒 → 握拳
悲伤 → 喉咙发紧
```

这种一对一模板非常容易制造 AI 味。

情绪只能通过**该人物已经建立的具身倾向**进入 Resolver：

```text
沈青舟：anger -> clipped_speech
某角色：fear -> checks_exits
```

如果人物没有这种既定倾向，Resolver 不凭空制造症状。

### 5. POV 决定“哪些自然现象真正进入页面”
Resolver 可以得到十个真实现象，但 Writer 不需要写十个。

`PerceptionContext` 根据当前注意目标筛少量高价值 cue。没有“一种感官至少一个”的规则。

## 与 WriterForge 的关系

- World / Character / Action 提供原因；
- Embodied Scene Resolver 做轻量因果派生；
- `Perception & Description` 使用候选 cue；
- `perception_motivation` 决定 POV 为什么注意它；
- `telling_detail / detail_utility` 决定哪些值得真正写出来；
- Writer 最终决定句子。

因此它不是第六个 Craft Group，也不是常驻 Reviewer。

## 调度

只在以下依赖发生变化时重算：
- environment；
- relevant entity state；
- action/contact；
- POV attention。

同一状态 fingerprint 不变时直接复用。
