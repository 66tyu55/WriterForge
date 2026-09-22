# 子技能 11：目标类型准入与“及时停止”门禁

## 目标
用户给出原著 TXT 后，不允许 AI 立刻“全书学习”。先判断：
- 用户真正想写的目标类型是什么；
- 当前原著是否足以支撑这个目标；
- 当前原著只能贡献哪些局部能力；
- 是否应该暂停继续学习并向用户报告“素材不足”。

## 关键原则
**类型判断也必须顺序阅读，禁止全书关键词扫描。**

不允许：
- 搜索“灵气、宗门、妖兽、修炼”等词来判断是不是玄幻；
- 用作品简介代替正文；
- 因为前几十页出现一个类型元素就宣布“足够”；
- 因为某一章没有目标类型元素就立即否定整本书。

## 准入流程

### Stage 0：用户目标
先建立 `target_profile`：

```yaml
primary_genre: 中国玄幻小说
secondary_genres: []
desired_effects:
  - 神秘
  - 热血
  - 恐怖
  - 轻松/搞笑
  - 愤怒
  - 仇恨
  - 压迫
  - 温情
  - 惊奇
world_requirements:
  - 超自然规则
  - 力量体系
  - 非现实世界结构
  - 超常生物/势力/空间中的至少若干项
```

注意：
“desired_effects”是**能力覆盖目标**，不是要求每一本原著都必须同时具备所有效果。

### Stage 1：顺序试读
按章顺序阅读，不跳章。

建议最小准入窗口：
- 至少 1 个完整章节；
- 更稳妥为连续 3 个章节；
- 如果第一章极短，则继续直到形成一个完整场景群。

### Stage 2：建立证据矩阵
每个章节只记录“正文中真实出现的证据”。

```yaml
chapter_evidence:
  genre_mechanics:
    supernatural_rule: none|weak|clear
    power_system: none|weak|clear
    nonreal_worldbuilding: none|weak|clear
    nonhuman_or_transcendent: none|weak|clear
  effects:
    horror: 0-3
    humor: 0-3
    anger: 0-3
    hot_blooded: 0-3
    hatred: 0-3
    mystery: 0-3
    tenderness: 0-3
    awe: 0-3
```

这里的分值只是“该章节证据强度”，不是文学评分。

### Stage 3：准入结论
只能得到以下结论之一：

1. `ACCEPT_CORE_SOURCE`
   - 可作为目标类型的核心学习源。

2. `ACCEPT_PARTIAL_SOURCE`
   - 不是完整目标类型，但某些能力值得学习。
   - 例如：普通历史小说可能很好地提供“古代环境、人物语言、政治冲突”，但不能独自承担玄幻世界构建。

3. `NEED_MORE_SEQUENTIAL_READING`
   - 当前连续章节证据不足，不做过早判断。

4. `STOP_INSUFFICIENT_FOR_TARGET`
   - 连续多个完整章节都没有足够的目标类型机制；
   - 继续学习只会让学海库向错误方向倾斜。

## “及时停止”的报告格式

```yaml
decision: STOP_INSUFFICIENT_FOR_TARGET
target: 中国玄幻小说
read_scope: 第1-5章，顺序阅读
what_source_can_teach:
  - 古代生活描写
  - 人物对白
  - 家族关系
what_source_cannot_support_well:
  - 稳定的超自然规则
  - 修炼/力量体系
  - 非现实空间与超常生物
recommendation:
  - 保留为“古代人物/环境辅助源”
  - 另加入至少一部玄幻核心源
```

## 禁止
不要说“这本书不好”。
这里只判断“它对当前目标是否足够”。
