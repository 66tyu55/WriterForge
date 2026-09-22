# 53 Reader-First Learning｜读者先行学习

## 根本规则

学习原著时必须分成两个不可颠倒的 Pass：

```text
PASS A：第一次阅读者
        ↓ 锁定
PASS B：文学分析者
```

绝对禁止：

```text
先知道后文
→ 再假装自己第一次读
```

否则产生的是“作者视角解释”，不是读者体验。

---

## PASS A：Cold First Read

只允许看到：
- 已读过的正文
- 当前新句/新段/新场景

禁止看到：
- 后续章节
- 结局
- 全书摘要
- 作者意图分析
- 学海库对该段的已有解释

每个阅读单位记录：

### 注意力
- attention 0-5
- urge_to_continue 0-5
- cognitive_load 0-5
- confusion 0-5

### 好奇
- curiosity 0-5
- 当前问题
- 当前预测
- 哪一个问题最想知道答案

### 情绪
分别记录：
- fear
- humor
- anger
- awe
- sadness
- warmth
- disgust
- excitement
- tension

不是只打一个“情绪标签”。

### 人物
- 当前喜欢/厌恶/担心谁
- 对人物第一印象
- 人物是否值得继续关注

### 当前变化
- 这一句/段让读者知道了什么
- 改变了什么预测
- 新增了什么问题
- 关闭了什么问题

---

# 妖兽/人物/重要物件第一次登场协议

例如 XX 妖兽第一次出现，必须记录：

```yaml
before_reveal:
  reader_knows:
  reader_expects:
  open_questions:

first_contact:
  first_visible_detail:
  first_sound:
  first_action:
  name_given_when:
  full_form_revealed_when:

reader_reaction:
  fear:
  awe:
  curiosity:
  threat_estimate:
  familiarity:
  mystery:

after_reveal:
  new_question:
  prediction:
  urge_to_continue:
```

关键不是：

“作者描写了妖兽。”

而是：

“妖兽出现的第一个瞬间，读者脑子里发生了什么。”

---

# PASS B：Analyst

只有 PASS A 锁定之后才能开始。

分析：

```text
文本刺激
↓
读者反应
↓
是什么技巧造成的
```

例如：

```yaml
observed_effect:
  恐惧 + 好奇

reader_evidence:
  fear: 4
  curiosity: 5
  urge_to_continue: 5

craft_mechanism:
  先出现声音
  不给全貌
  人物先停住
  三句后才给名称
```

这样学海库存的是：

**什么写法 → 让第一次阅读者产生了什么变化**

而不只是：

**作者用了什么词。**

---

# 章节级 Reader Arc

读完一章后分析：

```text
Attention Curve
Curiosity Curve
Emotion Curve
Attachment Curve
Cognitive Load
Question Open/Close
Urge-to-Continue Curve
```

特别找：

- 哪儿开始想停
- 哪儿重新被抓住
- 哪儿期待被满足
- 哪儿满足后产生更大问题
- 哪儿信息太多
- 哪儿情绪没有建立就要求读者共鸣
