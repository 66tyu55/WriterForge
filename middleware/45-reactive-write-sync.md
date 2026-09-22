# 45 Reactive Write Sync｜创作状态同步器

## 目标
这是最接近 Vue “响应式绑定”思想的部分。

WRITE 维护一个可观察的 story store。

```yaml
story_store:
  canon:
  scene:
  paragraph:
  characters:
  reader:
  promises:
  causality:
  draft:
```

当 WRITE 接受一句最终文本后：

1. 解析这句产生的状态变化；
2. 更新 story_store；
3. Observer 捕获变更；
4. Delta Detector 计算变化；
5. Retrieval Policy 判断依赖是否失效；
6. 若需要，Query Gateway 从固定 snapshot 拉取新知识；
7. Evidence Adapter 转换为下一句可用指导。

## 注意
这是“响应式循环”，不是数据库双向乱写。

正确：
`WRITE state -> middleware observe -> Xuehai read -> guidance -> WRITE`

错误：
`WRITE -> 修改 Xuehai`

学海库只由 LEARN 发布。
