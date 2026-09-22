# 子技能 18：多原著语料覆盖规划器

## 目标
当单本原著不足以支撑目标时，决定“还缺什么”，而不是盲目继续喂书。

## 输入
- target_profile
- 当前学海库能力矩阵
- 已学习作品及其角色（core/auxiliary）

## 输出缺口

```yaml
coverage_gaps:
  genre_mechanics:
    power_system: high
    supernatural_rule: medium
  effects:
    humor: high
    horror: medium
  scene_types:
    sect_daily_life: high
    aftermath: medium
```

## 选择下一本原著的原则
不是“再找一本玄幻”，而是：
- 找能补当前缺口的来源；
- 避免与已有来源高度同质；
- 优先形成“同效果不同处理”的对照组。

## 饱和判断
当某一个能力：
- 已有 >= 3 个不同作品提供证据；
- 至少存在 2 种不同实现机制；
- 新来源连续多个章节没有提供新方法；

则标记：
`SATURATED_FOR_NOW`

暂停继续向该能力堆素材。

## 结果
让学海库从“素材仓库”变成“能力地图”。
