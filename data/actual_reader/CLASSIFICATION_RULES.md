# Reader Comment Genre Isolation Rules

## 强制规则
1. 每条真实读者评论只有一个 `primary_genre` 主归档。
2. 不跨主类型复制同一评论，避免训练/统计重复。
3. 混合类型只使用 `secondary_genre_tags`，供 Middleware 二次筛选。
4. WRITE 查询真实读者库时，默认先锁定当前小说 `primary_genre`。
5. 只有明确的跨类型研究任务，才允许跨库比较。
6. 中文玄幻/仙侠与英文 Progression Fantasy 分库；不能因为都有“升级”就直接混学。
7. 同人与原创分库；同人读者特别关注原作角色保真，不能把该指标强加给原创小说。
8. 快穿/无限流/时间循环分别保留自己的结构约束，不能因为都有“多单元”而合并。
9. 评论的长期价值标签（追更、二刷、弃坑回归等）保留在各类型内部比较。

## 查询顺序
`primary_genre -> reader_status -> trajectory -> signals -> secondary_genre_tags`

而不是：
`全库 -> 找关键词相似评论`

## 跨类型调用
仅允许用于“方法比较”，例如：
- 玄幻与 Progression Fantasy 如何表现成长体感；
- 无限流与 Time Loop 如何管理重复疲劳。

跨类型数据不能直接作为当前类型的 Reader Baseline。
