---
name: wf-appearance-body
description: Independent source-evidenced appearance, injuries, physical condition and observed body changes. SHADOW only.
metadata:
  wf-skill-id: wf-appearance-body
  wf-lifecycle: shadow
  wf-version: "0.1"
---
# 外貌与身体状态（独立 Skill，未训练完成）

负责外貌辨识、体貌变化、伤势、疲惫、可观察生理限制及恢复状态。**外貌印象不等于人物身份；受伤≠已痊愈；神情变化不等于确切心理**。同一人物的外貌在不同时间和视角可有差异。

保留私有原文证据、观察者、人物候选 ID、部位/状态、是否亲见、可逆性与未知项。伤口是否愈合、药物是否有效，必须由证据支持。年龄数值、修炼时间、寿元消耗等仍由时间 Skill 负责，不通过外貌自动生成岁数和寿命。

可接收空间 Skill 的环境线索和人物 Skill 的身份线索，但只能以只读意见形式进入待核对队列；来源和自身参数所有权不变。独立与联合训练都必须能追踪同一身体状态的前后版本，而非用后来信息改写过去。

训练验收需要未见章节上的外貌/伤势连续性及身份盲测。当前仅定义，**无真实参数训练通过记录**。不接入正式 WF。