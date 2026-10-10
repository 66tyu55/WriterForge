# V23：让《西遊記》100 回中文原著学习、真实写作、独立审稿工作

V23 执行链：下载中文原著 -> 分章顺序入库 -> 发布学海快照 ->
重启恢复 -> 真实本地模型生成接口 -> 原稿与来源留痕 -> 作者选择接受。
评价只选 lit-critic，审稿无法自动改作品。

## 原著与版权

- 繁体中文《西遊記》，完整 100 回，**不是英文译本**。
- 原文 [Project Gutenberg EBook #23962](https://www.gutenberg.org/ebooks/23962)，
  [GITenberg 原文镜像](https://github.com/GITenberg/---_23962/blob/master/23962-0.txt)。
- CI 下载完整原文及 Project Gutenberg 发行条款，
  同时记录下载原始文件与解码正文的 SHA256。
- 原著正文和训练库不会 commit 进入源码仓库；CI Artifact 保留 30 天。
  使用原著公共领域内容时仍须遵守该发行版本商标/许可证条款与所在地法律。

## Windows 安装、实际学习

安装 Python 3.11，打开 WriterForge 项目目录并执行：

    python -m pip install -e .
    writerforge --db writerforge.sqlite3 fetch-xiyouji --output corpus/xiyouji_23962_original.txt
    writerforge --db writerforge.sqlite3 learn --source corpus/xiyouji_23962_original.txt
    writerforge --db writerforge.sqlite3 status

完成时显示 100/100 回已学习、源单位数、已发布快照等。
每一回使用独立 SQLite 事务；中断后可重跑，已完成回目不会重复导入。
来源文件版本校验和变化时拒绝静默混用。

数据库文件在本地，原著正文另存在 corpus 目录。
未来加载其他版本需使用新的 work-id 与 source-uri；
allow-partial 只能用于受控测试，不得自称完成全书。

## 真正写作：需要本地模型

只生成有来源的上下文，不生成小说：

    writerforge --db writerforge.sqlite3 draft-context \
      --project my-wuxia --scene ch01.scene01 \
      --goal "古渡口一名少年救人后失去通行证" \
      --concerns dialogue,description \
      --output draft_context.json

必须准备实际本地模型服务。例如使用 LM Studio，
确认模型已加载并监听 http://127.0.0.1:1234/v1 ：

    writerforge --db writerforge.sqlite3 draft \
      --project my-wuxia --scene ch01.scene01 \
      --goal "古渡口一名少年救人后失去通行证" \
      --concerns dialogue,description \
      --model "LMStudio中实际加载的模型标识" \
      --api-base http://127.0.0.1:1234/v1 \
      --output-dir writing_runs

生成一个新的 candidate.md 和 run.json，记录模型、
已发布快照、原著来源引用、提示词 SHA256、原稿 SHA256、
技巧标签及是否被作者接受。所有检索证据仅用于方法，
不得重写《西游记》故事、人物或原句。

只有作者明确审核并接受才写入作品数据库：

    writerforge --db writerforge.sqlite3 accept \
      --project my-wuxia \
      --manifest writing_runs/实际输出目录/run.json \
      --commit-id project-ch1-scene1-approved \
      --confirm-accept

生成稿标记为 assistant_generated，不能冒充作者亲自写作。
没有本地模型或真实原著训练库，程序拒绝假装写作成功。

## 唯一外部评价：lit-critic

请在项目之外安装 [lit-critic](https://github.com/lit-pack/lit-critic)，
按原项目说明设置 VS Code/本地 REST 服务及
Anthropic 或 OpenAI 模型 API Key。lit-critic 自身使用
每个项目的 .lit-critic.db 保存评论和讨论历史。
小说工程需有 CANON.md、STYLE.md 和场景文本。
启动本地服务后：

    writerforge review \
      --project-path C:/Novels/MyWuxia \
      --scene C:/Novels/MyWuxia/scene-01.txt \
      --output-dir reviews --mode quick \
      --api-base http://127.0.0.1:8000/api

适配器只允许 loopback；调用官方 /api/analyze、
/api/sessions、/api/sessions/{id}。
只有获取唯一新审稿会话与真实 findings 才生成两份文件：

- litcritic_会话ID_正文哈希.json：模型审稿证据、影响、行号、
  原稿哈希及作者未处理的决定字段；
- 同名 .md：可阅读的编辑审稿报告。

审稿器不改接受稿、Canon、Skill 优先级，也不把自评直接当训练。
**CI 仅用受控模拟本地服务测试 API 通路**，真实评价必须
用户本地启动 lit-critic 和提供模型服务，目前没有真实评比分数。

## 内存与无限增长风险处理

| 风险 | V23 防护 |
|---|---|
| 每章整库复制前一快照、造成二次方增长 | 全量根 + 99 个增量快照，通过 SQL 祖先检索 |
| 检索一次读取几万句 | SQL 限 512 条候选，返回最多 32 条 |
| 异常巨大原文下载 | 最大 8MB，64KB 流式分块下载并原子替换 |
| 单章巨大输入与来源行 | 最多 180,000 字符、8000 个源单位/回、每章独立事务 |
| SQLite 内部缓存过大 | 约 8MiB 数据页缓存、临时数据落盘 |
| 读者反馈/轨迹无限读入内存 | SQL 汇总并分页、每次 500 条封顶 |
| 文学 Taste/Failure 记录无界积累 | 进程无数据库 fallback 限 256，有数据库则分页或限量恢复 |
| EventBatcher 和 LaneTaskQueue 持续入队 | 作用域、事件名、任务量设硬上限；溢出在写入前拒绝 |
| WorkTree 巨型 JSON 检查点 | 最多约 8MB/20000节点/64层深度/每节点16 pending |

硬上限能避免已知数据结构无界扩张，不保证所有外部模型
内存/显存/网路资源不泄漏。SQLite 文件长期增大是磁盘增长，
不是 Python 内存泄漏；多书持续训练需要磁盘容量、备份与归档。

## 验收条件及目前限制

GitHub CI 已在真实 100 回原著上生成报告和 SQLite Artifact，
并重启数据库验证源引用确实进入写作上下文。
**结构拆解不等于文学深度学习，更不等于模型参数微调**。

Reader-First 首次阅读、小说高级技巧标注、真实作者选择、
文学盲测都需要另行验证，不能凭文本关键字自动填充情绪打分。
先做到真实来源、真实路径、真实失败也留痕，再谈创作质量提升。
