---
name: wf-living-ecology
description: SHADOW Skill for independently motivated people and offstage life; keep actor-private intentions out of writer/reader views. Every character can have ordinary life and a history without being a plot device.
compatibility: Python 3.10+, standard library, optional isolated candidate protocol.
metadata:
  wf-skill-id: wf-living-ecology
  wf-lifecycle: shadow
  wf-version: "0.1"
---

# WF 人物生态 Skill：众人各活各的

**不是“给每个 NPC 安排一条支线”。** 不要求人人有秘密、阴谋或成长弧，更不要求正文显露心理。角色可以不行动、做琐事、犯错、临时改主意、只顾眼前，也可以永远不再出现。世界不会因为主角缺席而冻结。

## 目标：真实独立行动，而非编排好的痕迹

1. 先读已有 `NarrativeCore` 事实、关系、世界压力和 V114/V117 时间物件状态，**复用已有 Canon/存储**；不另建第二数据库。所有无证据的设想标为 PROVISIONAL。
2. 每个人拿到独立的 **私有视角包**：自己的当前关注、亲身已知、听说、误信、能力/资源、限制和时间窗口；其他人的秘密、作者大纲和未来结果都不能进入。
3. 人物可以自主选择 **WAIT / ACT / RECONSIDER / DECLINE**。模型可能提出选择，但必须保存真实原始回复、输入视野和理由；没有模型调用的程序只能验证协议，不能冒称自主思考。
4. 世界只接纳满足实际条件的动作与可观察后果。人物选择 ≠ 事件成功；想做坏事 ≠ 必然成功。动作可以在场外发生，也可以永远与主角无交集。
5. 为作者生成 POV **可见视图**：主角亲眼看见 / 听见的事件、公开结果、允许的传闻。**绝不把其他角色的私有心思、隐藏理由或尚未揭露的活动原样送给写作模型。** 其后续可能留下极少或零痕迹。
6. 正文自由写，不为后台每一步都补一个预告、伏笔或答案。有人离开后不再出现、物品只是普通物品、未说出的事可以永远不说。
7. 任意变化都以事件或未知状态收束。换主角性格，只改变与其相关的行动，独立经济/天气/邻人目标继续存在；不要重放原著后续剧情。

## 最小状态

每人可以有：
- `actor_id`（匿名稳定 ID，可匿名无名人物）、`time_ref`（时间 Skill 的不透明引用）、`location`、`concern`、`constraints`、`resources`；
- `knows`（见闻证据）、`believes`（传闻/误判可与客观冲突）、`private_plan`（只给此人）；
- `choice`、`attempt`、`outcome`（三者不能混同），`evidence_refs`（原著或正文来源），`unresolved`。

不强迫每人填满；不允许“作者全知设定”未经证明自动写入任一人物视角。**一段故事可有大量人物，却只需要处理当前环境中确实受影响的少数人。**

## 最小执行入口（只验证数据访问隔离）

- `python .agents/skills/wf-living-ecology/scripts/ecology_shadow.py`：运行合成四人示范，输出匿名摘要，**0模型调用**；
- `python -m unittest discover -s tests -p test_wf_living_ecology_shadow.py -v`：隔离/无后台泄露等机械测试（如后续运行环境可用）。
- `docs/WF_20261118_OFFSTAGE_AGENCY_SHADOW.md`：小场景展示与批判。
- `docs/WF_20261118_MINIMAL_CONTINUITY_SHADOW_RESULT.md`：前一轮轻量连续性证据。

该脚本不是小说引擎，不执行语义推理、不决定人心、不自动推进正典、不调用 API。真正实验要求**角色分别读到不同证据后独立产生决策**，将输出合并成私有世界事件，再由相同强作者模型只看 POV 公共视图写作；A/B 同题、同预算，记录所有调用成本、独立读者盲评，允许得出没有帮助或有害。

## 闸门

本 Skill 停在 SHADOW，不接到正式 WriterForge 写作生成链，除非完成：视角泄露检查；角色选择随环境变化实测；多位角色互相冲突/误判/改变主意；普通人物不被强制变伏笔；主角缺席世界照样变化；真实长篇续写自然度不下降、连续性确有改进。不能凭 synthetic PASS 宣称生态或文学成功。
