# 52B Rewrite Write｜整体重写引擎

## 目标
允许删掉“写得不错但整体不需要”的内容。

REVISION 分层：

```text
R5 Book/Arc
R4 Chapter
R3 Scene
R2 Paragraph
R1 Sentence
```

顺序必须：
`R5 -> R4 -> R3 -> R2 -> R1`

禁止先润色句子，再决定整章要不要删。

## 触发
- Emergence Proposal 被批准
- Promise/Payoff 结构失败
- Character Arc 断裂
- Reader Experience 长期失焦
- Ending Architecture 改变
- 章节功能重复

## Rewrite Plan
```yaml
scope:
keep:
cut:
move:
reframe:
new_required_material:
downstream_impacts:
```
