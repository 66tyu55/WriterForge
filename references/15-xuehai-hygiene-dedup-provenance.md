# 子技能 15：学海库卫生、去污染、去重复与来源追踪

## 目标
学海库不是“越大越好”，而是必须可追踪、可分离、可去重、可撤销。

## 三类污染

### 1. 来源污染
把不同作品的表达混成“作者自己的语言”。

解决：
每一条库存必须保留：
- work_id
- chapter
- paragraph
- sentence
- source_span_id

### 2. 分类污染
例如西方奇幻中的称谓、宗教结构、建筑语言直接混入“中国玄幻”默认词域。

解决：
每条库存必须有：
```yaml
library_class:
culture:
period:
genre:
subgenre:
```

### 3. 重复污染
同一句、相邻近似句、重复章节、不同版本文本重复进入。

## 去重层级

### Exact duplicate
文本标准化后 hash 相同：
直接合并来源，不新增库存项。

### Near duplicate
短语结构和语义高度近似：
保留一个主条目，其他作为 `evidence_refs`。

### Functional duplicate
表达不同，但技法和作用相同：
不删除，但进入同一个 `method_cluster`，避免 AI 把 50 条近似案例当成 50 种方法。

## 入库前检查

```yaml
ingest_check:
  provenance_complete: true
  class_assigned: true
  exact_duplicate: false
  near_duplicate: false
  method_cluster:
  conflict_with_existing: false
```

任何来源不明条目：
`QUARANTINE`

不得进入正式学海库。

## 可撤销
每一批学习都保存 batch_id。
如果之后发现来源错、分类错、文本版本有问题，可以整批撤销。
