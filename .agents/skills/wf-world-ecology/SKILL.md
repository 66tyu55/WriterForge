---
name: wf-world-ecology
description: SHADOW living-world ecology coordinator; each character receives an isolated viewpoint, makes a private decision, and may act off-screen while the author selects few or no observable traces. Never confuse physical feasibility with thinking or verified literary quality.
compatibility: Python 3.10+, standard library, isolated experiments only
metadata:
  wf-skill-id: wf-world-ecology
  wf-lifecycle: shadow
  wf-version: "0.1"
---

# WF 世界生态 Skill｜世界先活着，再让作者写

**核心目标**：每个人都有自己的生活、利益、害怕、思考和故事。主角不在，人物依然可能做事；主角没有触发事件，天气、制度、商贸和其他人的关系仍然变化。**但是读者不必看见这些，也不需要每个人成为伏笔、反派或阴谋家。**

**注意实证等级：** 0.1 是可运行的标准库 Python **SHADOW 力学内核**。使用者提供的 `chooser(actor_view)` 才是真正作决定的主体。本次离线 fixture 使用人工写定的决策函数，没有连接大语言模型、没有真正的多角色独立模型思考、没有文学盲评。不能把程序通过写成“人物真的有意识”“WF 文学进步”。

## 世界生态三层，不可混为一谈

1. **人物私有层**：眼下所求、恐惧、性格倾向、手头资源、自己的见闻、听说的传言。人物并不读得到别人的私心和未知的未来。目标可以变化；行为可以冲动、不经济、失误、甚至什么都不做。
2. **客观世界层**：河水上涨、行路是否可达、库存是否存在、谁确实交出了东西、谁实际到达哪里；世界规则只审查行动是否可行，不替人物选择、不保证每个愿望实现。真实发生的行动按时间推进，失败行动不能变为已发生的剧情。自然/社会条件可以不因主角在场而暂停。
3. **读者呈现层**：当前人物视角仅能得到可能观察到的少量结果，仍由作者自由选择写0条、1条或少数痕迹。**作者只用 `reader_slice` 产生候选，不得直接把私有世界 JSON 投给正文模型。**每个人的内心不需要宣告，场外变化甚至可以始终不写。

## 操作接口

源文件：`.agents/skills/wf-world-ecology/scripts/ecology_shadow.py`，主要纯函数：

- `new_world(places, roads, actors, water_level=0)`：创建一个**人工供应**、仅本次实验可用的场景状态。各演员拥有私人欲望与已知/传闻，不代表从原著自动学来。
- `actor_view(world, actor_id)`：只抽取**该人物当时有机会知道**的状态（自身愿望、事实、传言、当前位置、可见路线等），不含其他演员的私有目标、秘密、资源和离场行为。
- `step(world, chooser, rain=..., water_delta=...)`：先让环境发生明确输入的变化，再从同一个冻结时刻分别询问各人物 `chooser(own_view)`；最后按固定顺序尝试动作并产生真实结果。**真正模型适配器需对每个 actor 分别调用，并计入全部费用；本内核未实现该适配器。**
- `reader_slice(world, viewpoint='azhi', selected_event_ids=())`：只返回该视角可能观察到、且作者主动选中的事件。空列表是有效输出。任何场外未目击事件强行入文将被拒绝。
- `validate(world)`：校验本次快照 SHA、大小与主体/时间范围，**不是原著语义真实性审计**。

人物动作：`WAIT`（无外显）、`MOVE`（需要现实可通行路径）、`SECURE`（护住自身货物并消耗体力）、`OFFER`（提出资源转移、暂不转移）、`ACCEPT`/`DECLINE`（由接收者自己决定）、`TELL`（消息进入对方“听说”而不是升级为客观事实）。每个行动可附 `next_goal` 更新私人目标；**即使物理行动失败，人物仍允许在心里改变计划**。每人每回合最多一个动作，不允许瞬移、凭空增加库存、越权替别人决定。

## 本轮复现

```bash
python -m unittest discover -s tests -p test_wf_world_ecology_shadow.py -v
python .agents/skills/wf-world-ecology/scripts/ecology_demo.py
```

注意：本 Skill 的 13 项合成测试依赖独立实验分支下的文件，**不依赖安装模型或云服务**。示例：阿芷在家给母亲抓药，庄二自己收好米、渡娘在涨水前去西岸；次轮渡口因水位上涨无法返回，渡娘可以改变私人目标。阿芷没在场，`reader_slice(..., selected_event_ids=())` 可以零痕迹。输出不把世界事件自动等同于小说正文。

## 与现有 WF 的关系

- 旧 `NarrativeCore` 继续是**唯一**经作者审核的长期叙事、关系、认知与悬线记录；V114/V116/V117 继续管有来源的物件、位置、时间候选。生态是其**可插拔独立决策试验层**，不是再建第二套 Canon/数据库或第八个强制前置写作门槛。
- 一切未经作者与原文核查的生态模拟只能留在实验区，不能直接提升为 `NarrativeCore` 的 `FACT`、`KNOWS` 或其他真相。未来写作经作者批准、实际写入正文并有字句锚点后，才走原本的 `advance_graph` 复核链。
- 场外人口可分层调度：重要人可能周期性自主选择；普通人只在生计、消息或环境变化有关时行动；未出场的人无需每回合都调用模型。**不为所有 NPC 批量制造剧情、复杂心机或虚假的命运。**
- 世界能同时包含持续稳定的客观条件和偶然、冲动、无知、谎言、无作为；不得把任何人的行为设计成必然围绕主角。
- 0.1 `potential_witnesses` 只是“可能看见”的候选，不是实际看见、理解或者知情；谈话可能不被旁人听到。商品提议未处理取消/过期及所有现实社会规则；环境变化由外部给定，非自动气象推理。人物模型适配器、真实长篇表现与盲评仍 **NOT DONE**。

**绝不改动 main、正式 WF 写作入口、Xuehai、R2、Canonical 或 Railway。**
