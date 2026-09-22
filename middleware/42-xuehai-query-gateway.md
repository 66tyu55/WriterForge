# 42 Xuehai Query Gateway｜学海库只读网关

## 目标
WRITE 永远不能直接摸学海库底层。

所有查询通过本 Gateway。

## 只读
允许：
- query
- rank
- filter
- retrieve metadata
- retrieve abstract methods
- retrieve short evidence references

禁止：
- insert
- update
- delete
- reweight
- reclassify

## Snapshot Pinning
一次创作 Session 固定：

```yaml
xuehai_snapshot_id:
```

即使后台之后产生新学习版本，本次 WRITE 不自动切换。

这样保证同一章节不会写到一半“知识库性格变化”。

## 返回
优先返回：

```yaml
methods:
lexicon_domains:
effect_routes:
scene_functions:
source_diversity:
confidence:
```

而不是大段原著文本。
