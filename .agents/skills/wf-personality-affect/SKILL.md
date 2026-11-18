---
name: wf-personality-affect
description: Independent character trait and momentary emotion learning, evidence-bound and cross-skill compatible. SHADOW only.
metadata:
  wf-skill-id: wf-personality-affect
  wf-lifecycle: shadow
  wf-version: "0.1"
---
# 人物情绪与性格（独立 Skill，未训练完成）

只负责人物长期性格倾向、眼前情绪、情绪触发与持续、外显反应及可能的自我矛盾。**性格≠每次行为，情绪≠世界事实，角色的自述≠叙述者已证明的原因**。同一人物可以反常、后悔、撒谎、忍耐。拒绝无来源的小数评分与自动选行动作。

输入：原著连续章节的私有源位置及原文；初步事件候选可以参考，但须回源独立核对。输出仅为本 Skill 独有的参数候选，标注人物、时间窗口、证据 ID、可观察表现、解释置信状态、反例及可修订条件。未明说的心理活动为 UNKNOWN。

可接收时间/空间/世界/人物认知 Skill 发来的**只读证据线索**，但外部意见不能直接成为本 Skill 已学参数；独立复核后才能更新自身候选。和外貌 Skill 的“脸色发白”等生理观察不可自动等同于恐惧。

训练验收：相同原著先独立阅读，再协同；随后屏蔽其他 Skill，独立还原未读片段中人物情绪和性格的变化，检查错误传播。当前只有定义，**没有训练成绩**。不碰 WF 正式作者、Canon、学海或 R2。