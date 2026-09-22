# 子技能 09：长文本剧情记忆与幻觉抑制

## 目标
降低长文本中的遗忘、角色漂移、世界规则冲突和未来伏笔丢失。

## 两层记忆

### A. 已完成事实（不可随意改）
```json
{
  "fact_id": "F001",
  "type": "plot|character|location|item|rule|relationship",
  "statement": "...",
  "established_at": "ch2-sc3",
  "confidence": "confirmed"
}
```

### B. 未来走向（尚未发生）
```json
{
  "beat_id": "B014",
  "target": "ch4",
  "event": "...",
  "preconditions": [],
  "must_not_happen_before": [],
  "status": "planned"
}
```

## 每句写作前读取
只取与当前场景直接相关的：
- 最近已发生事件；
- 当前人物状态；
- 当前地点；
- 当前持有物品；
- 当前未解决线程；
- 最近的未来节点。

## 每句写作后更新
只有最终接受的句子才能写入记忆。
候选和已删除句不写入事实库。

## 事实冲突
若新句与 confirmed fact 冲突：
- 禁止输出为定稿；
- 标记冲突；
- 交给总控决定是修句还是正式改设定。

## 场景结束快照
每个场景保存：
- 谁在场；
- 每个人最后位置；
- 每个人知道什么；
- 受伤/物品/关系变化；
- 新出现问题；
- 已回收问题；
- 下一场景必须承接什么。
