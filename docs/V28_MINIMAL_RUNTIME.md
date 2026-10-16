# WriterForge V28 · 最小运行内核（工程验收，不是文学训练成绩）

**2026-10-16。此文是已提交实现的使用说明。** 总设计见 [V28_REVERSE_CRAFT_LEARNING_DESIGN.md](V28_REVERSE_CRAFT_LEARNING_DESIGN.md)，人物感知与叙事策略见 [CORE_PERCEPTION_NARRATIVE_STUDY.md](CORE_PERCEPTION_NARRATIVE_STUDY.md)。

## 已实现的组件

- `writerforge/reverse_craft.py`：专用 SQLite 事实源、单书限定、相邻单元、两单元合并才可推进、3 次候选上限、2 次合并上限、双阶段 90/100 + 关键项 85/100 检验、独立 reviewer 必需、抽象核心按不同 context_hash 分级 `candidate -> recurrent_3 -> retested_6 -> generalized_9`、临时文稿与限时孤儿目录清理、可重启状态/故障恢复。
- `writerforge/reverse_core_vault.py`：不调用现有 full-DB `R2StudyVault.backup`，只上传无练习正文的小型核心快照到原桶的**单独私有前缀** `writerforge/v1/reverse-craft/wudongqiankun/<project>/<edition>/snapshots/<sha>.json`；SHA256 内容寻址、已有对象不可覆盖、全新 GET 下载校验、按哈希恢复。默认不会执行任何 R2 写入；必须由显式 checkpoint 调用。
- `tests/test_v28_reverse_craft.py`、`tests/test_v28_reverse_craft_stress.py`、`tests/test_v28_reverse_cli.py`：全部使用**虚构短文 / 测试评审器 / 内存内模拟 R2**；不能代表真实独立文学评测，不调用《武动乾坤》原文，也不会产生真实的 R2 新学习记录。

### 命令行（不启用文学训练）

新建一个专用 V28 库（**不能指向现有学海 SQLite**）：

```bash
writerforge --db workbench/v28-wudong.sqlite3 reverse-core-init --project wudong-lab --max-chapters 3 --max-units-per-chapter 6
writerforge --db workbench/v28-wudong.sqlite3 reverse-core-status --project wudong-lab
```

在已配置私有 R2 且已取得**真实的 V28 抽象核心快照 SHA** 时，只读验证并恢复为全新文件：

```bash
writerforge --db workbench/v28-restored.sqlite3 reverse-core-restore --project wudong-lab --snapshot <verified-sha256>
```

**不能将旧 `literary_ladder.py` 当作 V28 训练运行。** 旧代码会把每次原始练习正文写入 SQLite `body` 字段、文件和潜在 R2 不可变快照；V28 的隔离是另一个没有 `body` 字段的专用小数据库，不复写旧学海、Canon、Writer Companion。

### 状态序列

`READY -> [RETRY | BLOCKED | REVIEW_BLOCKED | PERSIST_PENDING]`

`PERSIST_PENDING -> (private R2 fresh verified) -> RETEST_READY -> RETEST_PERSIST_PENDING -> (R2 fresh verified) -> PASS`

`PASS(A) + PASS(B) -> MERGE READY -> MERGE RETRY / BLOCKED / REVIEW_BLOCKED / MERGED_PASS`

`MERGED_PASS` 才允许继续下一训练窗口。可恢复 checkpoint 是**拟提交成功状态**的 JSON 快照；远端 SHA 验证通过后才在 SQLite 事务里采纳。上传成功但本地事务失败将只留下未引用的不可变 R2 对象，重新运行会按同一哈希幂等恢复。

在没有可信的独立评审适配器时，`reviewer_authority=None` 一律落入 `REVIEW_BLOCKED`；模拟审评器只存在单元测试中。

## 已知未完成、绝不可谎报成功

1. **《武动乾坤》全书章节语法/缺章未通过**：现有 R2 归档 SHA256 `86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28`、原文字节 8,254,079；V28 目前尚未从原著自动划分真实两段场景、调用写作模型。
2. 真正的**原文定位与剧情快读、模型写作 adapter、可靠的复制/近似重述检测、独立文学 critic 的签名/校准/盲评机制、长篇原创多段 A/B 测试** 尚未接通。**不能输出真实 90 分，也不能把模拟成功当作模型能力提升。**
3. 当前 `reverse_core_vault.py` 有模拟 R2 测试；尚未在真实 R2 中进行新 V28 核心快照的存取运行。数据库新接口和恢复命令需要在真实环境里再验。
4. 草稿使用系统临时目录，常规退出即删除；**进程崩溃可能留下孤儿临时文件**，提供了独立 `cleanup_stale_scratch(max_age_seconds=3600)` 例程，但需要部署者在启动时运行。删除普通文件不代表物理安全擦除；不得让系统对临时目录做意外的持续备份。
5. 固定本次试点上限 `max_chapters <= 3`、每章 <=6 个窗口、18 个总窗口；以后如扩大需另设清楚的总预算/性能评估。不是无限循环直到获得 90 分。

## 设计验收路径

1. 运行整个 GitHub Python 回归测试 `python -m unittest discover -s tests -q`。伪评审只证明状态流转、内存上限、R2 故障拒绝、证据去重和重启恢复。
2. 在严格读取 R2 `wudongqiankun` 原文、局部章节核验通过后，先添加一个**只读、哈希定位、单场景的 SOURCE_LOCKED 适配器**。
3. 再接真实隔离本地生成器和独立评审，测试新任务闭卷重写与反事实；不得在模型不存在时伪造运行成绩。
4. 真实测试从**两个相邻、小范围、已核验的场景**开始。两段各自达标、草稿清理、核心 R2 恢复校验、合并长剧情达标后才能推进第三单元。50 部完整作品的整体文学评价门槛仍保留。
