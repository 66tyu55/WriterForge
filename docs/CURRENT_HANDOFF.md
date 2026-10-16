# WriterForge 当前交接记录 · 2026-10-16

> **本文件是新对话的唯一首读交接入口。** 每次继续项目前，先检查本文件并复核有关 GitHub Actions 运行结果；不要重建已完成的原文归档，不要将用户的聊天结论冒充 R2 中的真实数据。本文报告的是截至 **2026-10-16 06:08 UTC** 核实的状态，而不是当前实时桶扫描结果。

## 1. 已完成：六本现代小说的私有 R2 原文归档

目标存储桶：`writerforge-private-library`（**私有**）。

目标对象前缀：`writerforge/v1/private-reading/single-works/<work_id>/`。

每本独立保存内容寻址的原文 blob、不可变 manifest、latest 指针。成功标准为：**GitHub Actions 下载原文 → 校验实际字节与 SHA-256 → 上传新对象 → 全新 R2 下载 → SHA-256 一致**。无一需要 GPT 临时目录、Google Drive OAuth 或遗失的十三本合辑。

| 作品 | work_id | 归档原文大小（字节） | 原文 SHA-256 | 核验证据 |
|---|---|---:|---|---|
| 《星辰变》 | `xingchenbian` | 8,256,014 | `83da08694a5d5510124711c7bfcc7522be531cdb73e01790aa0d3076932ab5f0` | [单书上传与回读](https://github.com/66tyu55/WriterForge/actions/runs/38107901164)，[无需旧合集的再恢复](https://github.com/66tyu55/WriterForge/actions/runs/38852727960) |
| 《仙逆》 | `xianni` | 20,379,949 | `8174861b528c2781b4aa102670a363021fa97f8b0cfc358ee7ba08d3584dd14c` | [单书上传与回读](https://github.com/66tyu55/WriterForge/actions/runs/38108185835) |
| 《凡人修仙传》 | `fanrenxiuxian` | 15,079,878 | `2fc1698410418bf136448807335c6359bf515b75e6f9c1e1d1f443a1c928e6cc` | [网页固定版本下载、新上传、全新回读](https://github.com/66tyu55/WriterForge/actions/runs/38858109163) |
| 《斗破苍穹》 | `doupo` | 16,085,734 | `8d2e617d7ea4742452b765393bb66b0b0bb8546f63b9ff88dff9d3f6a779c0f6` | [三书独立归档：doupo job](https://github.com/66tyu55/WriterForge/actions/runs/38859398597) |
| 《武动乾坤》 | `wudongqiankun` | 8,254,079 | `86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28` | [三书独立归档：wudongqiankun job](https://github.com/66tyu55/WriterForge/actions/runs/38859398597) |
| 《完美世界》 | `wanmeishijie` | 14,053,175 | `322e84872b2259d9210f84de63efd70d901a412dfefbe9bb9d52168eea56d481` | [三书独立归档：wanmeishijie job](https://github.com/66tyu55/WriterForge/actions/runs/38859398597) |

**合计 6 本、82,108,829 字节原文（约 82.11 MB）。** 这个合计仅针对六份已归档原文，不包括 manifest、数据库，也不代表已经深度学习六部。

### 三本玄幻：实测新增快照

三个 GitHub Actions job 都报告 `new_private_archive=true`、`new_blob_uploaded=true`、`fresh_roundtrip=true`；整次 [运行 #38859398597](https://github.com/66tyu55/WriterForge/actions/runs/38859398597) 结论为 `success`。

- `doupo`: `8c8caa056005bc8eab3fa90177bcbd2d5caa37e1b88517537f057c7f7c66c08d`，标题模式命中 1,648 处。
- `wudongqiankun`: `a747f34425db5d0866f7804a432242e8f9f498376a9695cc820300377a9763aa`，标题模式命中 1,311 处。
- `wanmeishijie`: `ea3ca7b5bfa9eb2893edc890c737499a03d390048cd342782ebf4faaf0bd0256`，标题模式命中 2,015 处。

`fanrenxiuxian` 新快照为 `201d71349b90ba0067823509fd9b0076185b745338babcae0fe2a50ea0541ce5`，**2,451 处标题匹配不是完整、连续、无缺章的证明**。

**来源版本差异要保留**：《凡人修仙传》网页归档 15,079,878 字节；用户私有 Google Drive 同名 TXT 实测为 15,224,548 字节。两者不能声称字节相同，也不能用任一版本的哈希验证另一版本。

真正可复用的上传实现：

- [scripts/archive_web_fanren_r2.py](../scripts/archive_web_fanren_r2.py)
- [scripts/archive_three_xuanhuan_r2.py](../scripts/archive_three_xuanhuan_r2.py)
- [.github/workflows/fanren-pinned-web-r2.yml](../.github/workflows/fanren-pinned-web-r2.yml)
- [.github/workflows/three-xuanhuan-r2.yml](../.github/workflows/three-xuanhuan-r2.yml)
- [writerforge/single_work_runner.py](../writerforge/single_work_runner.py) 的 `verify_existing_single_work`

## 2. 已完成的古典原文结构化学习（与现代单书原文归档是两套不同目录）

已在 R2 `writerforge/v1/libraries/` 中有独立目录：

| work_id / 目录 | 说明 |
|---|---|
| `xiyouji-23962` | 《西游记》，经典原著结构化学习 |
| `honglou-24264` | 《红楼梦》，120 回；另有第三回场景的 **source_prepared** 证据，尚未执行真实模型深读 |
| `shuihu-23863` | 《水浒传》，结构化原著（含楔子） |
| `sanguo-23950` | 《三国演义》，120 回 |
| `jinghuayuan-25377` | 《镜花缘》，100 回 |
| `laocanyouji-25124` | 《老残游记》，20 回，新入库并全新恢复；4,857 个结构化来源单位 |

《老残游记》验收：[运行 #38853753144](https://github.com/66tyu55/WriterForge/actions/runs/38853753144)，原文 SHA-256 `273f4cbaecb4c4d396ecec7103b4761e62bde0c0f368185a1697c1880cfe9cf7`，R2 快照 `7fe1ceff8d637139d51b0b6bf2de6a7de220aeaea670247868fa17cc55270dd2`。

《红楼梦》场景来源证据入 R2 并恢复验收：[运行 #38848332025](https://github.com/66tyu55/WriterForge/actions/runs/38848332025)。状态仍为 `source_prepared`，不应谎称已进行模型文学理解或真人盲评。

## 3. 反复失败的根因（已实际定位；勿再循环排障）

- 旧的 13 部小说合辑 `WriterForge_PrivateReading_13Works_20261011.sqlite3` 曾可被读取，但后续原始键不可用。经 [只读全桶盘点 #38852072980](https://github.com/66tyu55/WriterForge/actions/runs/38852072980) 扫描当前桶 **85 个对象**，根目录源不存在，且全桶无同名、同大小对象；仅有 `xianni`、`xingchenbian` 单书独立入口（该次盘点发生在其余 4 本上传之前）。
- 早期单书传输流程在**上传之前**就因找不到旧合辑退出，典型错误 `root_size=None; matching_size_candidates=0; no upload attempted`。这不是 R2 普遍无法写入，也不是 8 MiB 上限。
- [PR #37](https://github.com/66tyu55/WriterForge/pull/37) 让已独立归档书籍直接按 latest→manifest→blob 下载验证，解除对旧合辑的重复依赖。
- Google Drive 连接器有访问用户私有 TXT 的授权，**GitHub Actions 没有继承该授权**；[Drive→R2 尝试](https://github.com/66tyu55/WriterForge/actions/runs/38855035159) 因缺 Google SA Secrets 在下载前终止。无须重试该失败路径。后续已证实网站→Actions→R2 可行。
- 用户明确要求：**停止依赖 13 本合辑；不再用 GPT 本地持久保存或 Google Drive 作为必需条件；不要重新争论、重新下载已经归档的书。**

## 4. 目前未完成、绝不可写成成功的工作

1. 现代六本小说目前是**独立原文归档**。标题正则命中数不等于严格章节数；未执行完整章节序列/分卷/番外兼容校验，未形成各自完整的 `libraries/<work_id>` SQLite 学习库。
2. `writerforge/modern_source.py` 已支持最大 32 MiB 原文、单章事务及断点式 SQLite 结构化写入，并通过 >8MiB 合成样本；但其第 1 章起连续编号、章节标题匹配约束，**不能不审原文就直接套用到六本不同卷制的现代小说**。
3. 原著学习的八轨结构标签属于词汇/启发式证据，不能冒充真正的文学深度理解或模型参数训练。文学场景学习 `writerforge/scene_learning.py` 初读锁定与解释程序存在，但原著《红楼梦》模型分析未执行，真人/独立评审未完成。
4. 既有《渡口无名簿》三章样稿为 **M0 对话生成的失败样稿**，不是 WriterForge 文学能力的有效 A/B 提升实证；可用于局部修订失败分析。文风基准 [PR #34](https://github.com/66tyu55/WriterForge/pull/34) 是可撤销的作者认可样段，**不是训练过的文笔模型**。
5. 用户决定辅助界面次要，自主创作能力优先；文学水平的 **50 部完整作品总体评价门槛**仍保留。现有已完成归档/结构证据不能算成 50 部真实文学能力掌握成果。

## 5. 下一对话推荐严格执行的顺序

**不要先加新 Skill，不要再重复三章写作测试。**

1. **从已有私有 R2 验证输入。** 选一本现代小说（建议先 `fanrenxiuxian`），在同一 GitHub Actions runner 使用现有 R2 Secrets 获取该书 `single-works/<id>/latest.json`、快照 manifest 和原文 blob，按 SHA-256 复核。源文件只在运行器临时目录，**不公开、不给 GPT 容器当中转**。如果发现确切缺源，仅报告和修复那一书。
2. **先严格核实章节语法和完整性。** 逐卷识别标题、重复序号、番外、章节缺失；留下带来源哈希的审计报告。若解析器不支持当前版本，就**修解析器并生成回归样例**，而不是修改原文去凑预计章节数。
3. **完成真正的现代单书结构化读取。** `learn-modern` 逐章写 SQLite、重跑可续、来源哈希不可混版；R2 `libraries/<work_id>` 新库备份＋干净环境恢复后校验章节数、来源单位数、原文 SHA256；这才是“现代小说原文入库 + 结构学习完成”，不是仅单书 blob 存在。
4. **再进行真实模型的场景深读**：先不剧透的读者假设锁定 → 后见揭示 → 逐条引用原文解释人物认知、信息释放、行为因果与表达取舍 → 独立复核后才可能迁移到创作。保存失败、修订和复评；无真实模型/审稿不能自称完成。
5. **质量门槛**：与无 Skill 同模型写作基线比较，帮助不了或写得更差的干预必须能够禁用；不要复制原著、不可让劣质 AI 样稿自动晋级为文风范例。

### 验收与日志约定

- **原文归档成功**：新 R2 blob / manifest / pointer 存在，远端全新下载 SHA-256 一致。
- **章节结构学习成功**：原文版本和完整章节证据、SQLite `PRAGMA quick_check`、整章记录、来源单位、R2 全新恢复全部一致。
- **文学语义学习有效**：真实模型输出、来源引文、独立评价和迁移对照均可追踪；无上述证据明确为“未验证”。
- 新增失败必须打印**失败在哪一步**（source、download、chapter、db、upload、restore、review）并保留可复核的 GitHub run URL；不要因聊天中断就宣称远端任务失败。
- 不记录 R2 Secrets、Google OAuth 密钥或私有整本原文到公开 repo、Issue、PR、Actions Artifact。
- 需要用户明确指定的任务继续执行，不必为已经商定的执行环境、目录、文件格式重复询问。

## 6. 给下一对话的最短启动指令

> 继续 GitHub 仓库 `66tyu55/WriterForge`。先读取 `docs/CURRENT_HANDOFF.md` 并核对引用的 Actions 成功证据。六本现代小说已在私有 R2 `writerforge/v1/private-reading/single-works/`，**不要重新下载原文**。从 `fanrenxiuxian` 做“私有 R2 原文恢复 → 真实章节语法核验 → 完整 SQLite 结构读取 → R2 全新恢复”这一阶段，一本一本来；先交付真实代码、日志、哈希。不要再拿存储架构和文学计划重复聊天。

——交接状态来源：项目 GitHub 代码、原有 Actions 日志、用户确认的 R2 控制台目录截图。每次实际继续应以最新日志和 R2 回读为准。
