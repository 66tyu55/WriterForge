# 子技能 05：候选选择与反照搬门禁

## 目标
在 AI 选择候选或参考原著时，防止“换名词式抄写”。

## 高风险模式
以下任一种出现就拒绝候选：
- 原句语序基本相同；
- 只替换人物/地点/物品名称；
- 多个核心实词位置一致；
- 比喻结构和落点高度一致；
- 连续短语与来源重合过多；
- 原著句子被拆开后重新拼接。

## 候选评估
每个候选记录：
```yaml
source_similarity:
  lexical: low|medium|high
  syntax: low|medium|high
  image_structure: low|medium|high
decision: accept|rewrite|reject
```

只要 `syntax=high` 或 `image_structure=high`，默认重写。

## 正确参考方式
允许学习：
- “先写声响，后揭示人物出现”
- “动作之后追加一个触觉细节”
- “对白前不用心理解释”
- “长句后用极短句收尾”

不允许学习成：
- “把原著这句话换成我的人名再用”。

## 最终选择
选择的是“叙事策略”，不是“源句”。
