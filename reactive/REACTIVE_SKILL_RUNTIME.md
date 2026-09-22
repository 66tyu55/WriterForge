# Reactive Skill Runtime｜文学 Skill 的增量运行时

目标：Skill Library 可以继续增长，但一次创作只运行真正依赖当前变化的极少节点。

## 核心规则

`Compute twice is okay. Commit twice is a bug.`

1. Craft / Taste / Reader / Planner 的计算阶段必须尽量纯：不能直接改 Canon、人物状态或长期记忆。
2. 每次计算绑定 dependency fingerprint。
3. 依赖未变化：直接复用缓存。
4. 单个依赖变化：只失效读取过它的节点。
5. 同一 fingerprint 的并发请求：single-flight，只真正计算一次。
6. Candidate 可以丢弃；只有 Commit Boundary 可以产生长期副作用。
7. 同一个 `commit_id` 对同一正文幂等；试图用同一 id 提交不同正文必须报错。

## Scene Craft Contract

Craft Router 不在每句话重新运行。场景开始或相关依赖变化时生成：

```yaml
scene_id:
contract_id:
technique_ids: []   # 通常 0-2
questions: []
dependency_fingerprint:
```

场景写作期间 Writer 继续执行这份 contract；只有 Character State、Scene Plan、POV、Reader Question 等真实依赖变化才重算。

## Dirty propagation

升级/修改一个 Skill 后也遵循同样原则：

`upstream contract changed -> direct dependents NEEDS_REVALIDATION -> unaffected skills stay clean`

禁止“一处改动，全系统所有 Skill 全量重跑”。
