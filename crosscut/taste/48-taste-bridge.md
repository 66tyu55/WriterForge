# 48C Taste Bridge｜审美桥（V12）

## 数据分层

1. Source Taste Evidence：只来自原著 LEARN。
2. Actual Reader Taste：同类型长期读者与当前 Beta Reader。
3. Project Taste：当前项目已接受/拒绝的选择。

三者可以共同提供论据，但不能压成“taste score”。

## 响应式监听

观察：
- 用户反复选择/删除哪类版本；
- Reader Effect 与某种 craft move 的长期关联；
- 某种文学路线是否过度使用；
- deliberate exception 是否真的产生预期效果。

只有在 `hard_literary_choice / taste_review / major_revision` 时才启动完整 Taste Compare。

## 输出

Middleware 只返回少量条件性证据：
- 当前作品审美契约；
- 与当前问题相关的 Source / Reader evidence；
- 最近过度使用路线；
- 可比较的对立候选。
