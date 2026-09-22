# LEARN Runtime｜学习运行时

## 唯一职责
顺序学习原著，构建并发布学海库。

## 模式锁
进入 `mode=LEARN` 后：

允许：
- 读取原著
- 顺序拆章/段/句
- 8 线分析
- 类型准入
- 跨作品比较
- 去重/分级/分类
- 写入 staging 学海库
- 发布新的学海库 snapshot

禁止：
- 创作小说正文
- 续写当前章节
- 修改 story_state
- 修改角色当前剧情状态
- 为了解决当前正文卡点而临时编写正文

## 输出
学习过程先写：
`xuehai_staging`

通过校验后执行 Publish：

```yaml
snapshot:
  id: xuehai-2026-09-22-001
  parent:
  created_at:
  source_batches: []
  taxonomy_version:
  schema_version:
  status: published
```

只有 `published` snapshot 可供 WRITE 使用。

## 结束学习时
生成：
- 新能力
- 新方法簇
- 新词域
- 新类型覆盖
- 重复/污染报告
- snapshot id

然后退出 LEARN。
