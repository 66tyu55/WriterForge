# WriterForge 当前交接记录 · 2026-10-16

> **本文件是新对话的唯一首读交接入口。** 每次继续项目前，先检查本文件并复核有关 GitHub Actions 运行结果；不要重建已完成的原文归档，不要将用户的聊天结论冒充 R2 中的真实数据。本文报告的是截至 **2026-10-16 06:08 UTC** 核实的状态，而不是当前实时桶扫描结果。

> **最新更新（2026-10-18）：V57修复分支请先看第43节；V55/V56关系网络原始中断证据见第42节；第1—41节是不可覆盖的历史记录。** 本次不训练、不修改原始失败证据。\n\n## 1. 已完成：六本现代小说的私有 R2 原文归档

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


## 7. 本轮续接实际结果 · 2026-10-16（此节比上方 06:08 UTC 历史状态更新）

**本节为新一轮真实 Actions 的结果；第 1 节的六本数字是历史快照，不再是全部归档数量。**

- **已从私人 R2 独立完成《完美世界》的原文恢复、2015 章确定性 SQLite 结构学习（249612 个来源单位）、新 R2 学习库备份、全新下载恢复、原文哈希及 SQLite quick_check 验收。** 新库：`writerforge/v1/libraries/wanmeishijie-private-original/`；快照 `fe0fd571c97a7a59f7f38c74408a85ec3a55b31abb90db343505e9aff1de2bfc`；[真实运行 #38866296144](https://github.com/66tyu55/WriterForge/actions/runs/38866296144) 的 `wanmeishijie` job **success**。结构化学习不代表模型参数训练、真实场景深读或独立文学评价。
- **新增且与此前六本不重复的三本玄幻已在私人 R2 独立原文归档、全新下载比对 SHA 成功**：
  - 《遮天》 `zhetian`：13,455,412 bytes，SHA256 `9cbf8da97daceb36fbd85edd84e2874a9ceac28252c18386fecf167d5a95660b`，归档快照 `c64901291446fd847757a4396d9a1d76462f645c98751c0f1874ee4a4083e357`。
  - 《莽荒纪》 `manghuangji`：8,961,764 bytes，SHA256 `f7aee869e201b4171e40a3ff9230e794f01fdc959d372017b8982635668be3d5`，归档快照 `02e5fd3c958c925e8c0426339a8a25465bea061713c8c4aa728153a358b82798`。
  - 《求魔》 `qiumo`：9,437,806 bytes，SHA256 `210acebeef123f2c369d57d95d2ea5ee5a1c15716b859db15696c48294bcd687`，归档快照 `5dfbb317e6028d66dbe8ea151821b59d3de9a5ec2bddceabcfac7468f296a779`；此版本卷名在章名前，独立安全识别到 1476 处卷限定标题，不能将“标题数”冒充完整章节。
  - 以上新三本共 **31,854,982 bytes**，新增前六本 **82,108,829 bytes**，累计归档 **9 本、113,963,811 bytes**（仅原文体积）；[三本独立归档 R2 回读均 success #38867522198](https://github.com/66tyu55/WriterForge/actions/runs/38867522198)。原文私有路径 `writerforge/v1/private-reading/single-works/<work_id>/`。
- **存在真实失败，不能抹去：** [章节审计 #38866296144](https://github.com/66tyu55/WriterForge/actions/runs/38866296144)：《凡人修仙传》匹配 2451 处但于 1754→1747、另有跳号；《武动乾坤》有 248→449→250 等异常；《斗破苍穹》安全诊断为 1648 个连续的 1..1648 标题，但现有严格解析器无法识别首章，需验证实际标题语法后修解析器。这三本**本轮没有新的结构学习成功或 R2 学习库**。不要改动原著、强行补齐缺章、用推测章节数宣称完成。
- 新增原文归档实现：[scripts/archive_next_three_xuanhuan_r2.py](../scripts/archive_next_three_xuanhuan_r2.py)、[归档 workflow](../.github/workflows/next-three-xuanhuan-r2.yml)；新结构学习执行器 [scripts/learn_archived_modern_r2.py](../scripts/learn_archived_modern_r2.py)、[结构学习 workflow](../.github/workflows/next-three-modern-study-r2.yml)、[已归档旧小说结构学习 workflow](../.github/workflows/modern-archive-study-r2.yml)。
- 新三本实际章节结构学习的 [run #38867581785](https://github.com/66tyu55/WriterForge/actions/runs/38867581785) **在本节记录时仍在运行**；不可预写成功结论。需逐个核对 job log 的 `complete_structural_only`、`fresh_r2_study_restore_verified=true`，才可计入。若不通过，保留失败并针对确实存在的章节格式改解析器与回归，而非跳过验证。

**截至本节已验证门槛：** 私有 R2 原文归档 9 本；有完整 SQLite + R2 回读证据的现代小说至少《完美世界》1 本。文学深读与独立评审仍未证实，保持 50 部完整作品总评门槛。



## 8. 三本新增玄幻真实结构学习验收 · 2026-10-16 07:39 UTC（覆盖第 7 节“仍在运行”记载）

- [第一次三本结构学习 #38867581785](https://github.com/66tyu55/WriterForge/actions/runs/38867581785)：**《遮天》success**；《莽荒纪》与《求魔》因旧解析器不了解卷制而失败。已根据原 R2 数据独立校核真实卷章格式，而非用推测补齐章节。
- [只输出数字、不记录原文的卷章实测 #38868040071](https://github.com/66tyu55/WriterForge/actions/runs/38868040071)：
  - 《莽荒纪》45 个顺序卷标记、1449 个严格章标题，其中 44 次章号回到 1 都与新卷吻合；**另有 3 处卷内异常**：第 22 卷 2→4、第 25 卷 17→20→19（章数与完整性不能无条件判定）。
  - 《求魔》1476 个“第 n 卷 … 第 m 章”同一行的章标题；其章号是**全书累计**而非每卷重置，至少有 5 个实测跳号或重号，例如 103→106、1304→1304。
- 已新增严格 `writerforge/modern_volumes.py` 双卷制流式解析器、合成回归 `tests/test_v34_modern_volumes.py`；`writerforge/modern_source.py` 的 `chapter_scheme` 支持 `continuous`、`volume_reset`、`volume_prefix_global`。原文 SHA 校验、字节限制、单章事务及恢复验收继续适用，**发现原文序号异常必须失败停止**。主仓库 GitHub Tests 运行 [#38868398691](https://github.com/66tyu55/WriterForge/actions/runs/38868398691) **success**。
- [新三本最终真实来源试跑 #38868398653](https://github.com/66tyu55/WriterForge/actions/runs/38868398653)：
  - 《遮天》`zhetian-private-original` **success**：1821 章，226655 个结构化来源单位，原文验证、R2 学习库备份和全新恢复、SQLite `quick_check=ok` 均完成。快照 `6027a1b657f219369d8980cc600a9f6dcf4a285268567bdf54f1abb2d14e45a6`。
  - 《莽荒纪》按真实分卷后 **真实失败在卷 22、预计第 3 章却遇到第 4 章**，原文 `f7aee...` 已保存在私有 R2，**没有完整结构学习 R2 库**。
  - 《求魔》按真实卷+全书累计章号后 **真实失败在预计第 104 章却遇到第 106 章**，原文 `210ace...` 已保存在私有 R2，**没有完整结构学习 R2 库**。
- **九本现代书仍有九份 R2 原文归档**，其中现代原文有严格结构学习与 R2 SQLite 全新恢复证据的为《完美世界》《遮天》**2 本**。其他七本（包括未在本节完成结构学习者）不可计入“完整结构已学习”。真实模型文学深读、独立评价和创作能力提升仍未验收。
- **后续明确路线**：对《莽荒纪》卷 22/25 和《求魔》103→106 等异常，先在**私有 R2 原文**检查该区间是否有标题异常、正文夹带的假标题、或原来源版本缺章，生成仅哈希/数字的核验记录；不能直接改号、忽略缺章或以“不完整训练完成”冒充全部成功。待原文严格通过才能使用现有 `scripts/learn_archived_modern_r2.py` 与 `.github/workflows/next-three-modern-study-r2.yml` 继续做 SQLite 与 R2 验收。如果来源确实缺章，只报告该来源未达到完整性门槛，另选经核验的版本并保留版本哈希区别。


## 9. 单本执行：莽荒纪结构学习成功 · 2026-10-16（覆盖第 8 节的失败状态）

用户要求改为**一次只处理一本**。本轮只针对《莽荒纪》，不再自动并行其他新书。已把 `.github/workflows/next-three-modern-study-r2.yml` 改为仅手动触发。

- 私有 R2 单书原文 SHA-256：`f7aee869e201b4171e40a3ff9230e794f01fdc959d372017b8982635668be3d5`，8,961,764 bytes。未重写原文、未依赖旧 13 本合辑。
- [仅元数据的缺章审计 #38869855383](https://github.com/66tyu55/WriterForge/actions/runs/38869855383)、[精确标题佐证 #38870323360](https://github.com/66tyu55/WriterForge/actions/runs/38870323360) 实测：
  - 卷 22 第三章实际在私有源第 60160 行，但带非标准前缀，旧 parser 漏识别；标题与独立目录吻合，行 SHA256 `8af3b3af69a68e1d2b0f72f8c541fc8a2cdb4f3e6ef324842599e2e8e74f1f9c`。
  - 卷 25 第 69921 行标题《花光了》在该源印为第 20 章；独立目录均为第 18 章；原文行 SHA256 `68eefe9d8f51189dbfb795b47514e1b0fc90d34f6546147d21c487cbdaf16d9c`。源中的原印字样**保留不变**，只在指定源的流式章节解析阶段标注正确序号。
  - 佐证目录：https://www.99csw.com/book/4660/167000.htm 、https://www.piaotia.com/html/3/3259/ 、https://www.kunnu.com/mhj/ 。这仅佐证两处标题，**不是全文跨版本独立比对通过**。
- 代码使用 `writerforge/modern_volumes.py` 里的 `volume_reset_manghuangji_pinned`，要求**整份原文 SHA + 两处原始标题所在行 SHA + 卷号 + 章号 + 标题**完全匹配，其他来源/其他章序缺口仍拒绝；学习仓库存原样 `heading`，私有 R2 学习库备份附加 `chapter_audit.json` 纠错出处。
- **GitHub Actions 单本正式成功：[run #38870652006](https://github.com/66tyu55/WriterForge/actions/runs/38870652006)**：`complete_structural_only`；**1450 章、203011 来源单位**；新私有 R2 库 `writerforge/v1/libraries/manghuangji-private-original/`，快照 `45cdf87a348c2375b4eaf829d7ad8351c87b170ba0679ae728d7291a3a89773c`，`fresh_r2_study_restore_verified=true`，`sqlite_quick_check=ok`。
- **目前 R2 原文独立归档仍 9 本；现代小说有结构化 SQLite + R2 全新恢复验证的为《完美世界》《遮天》《莽荒纪》共 3 本。** 不可把这说成完成真实模型深读、模型权重训练、文学能力迁移或独立评价。50 作品总体评价门槛不变。
- 下一轮继续时**只能处理一本**，优先检查《求魔》；不要重新跑已经完成的《莽荒纪》，不要在推送通用解析器时自动触发 3 本并行任务。


## 10. 文学训练目标澄清（设计已记录，**模型学习尚未执行**）

用户明确指出训练核心是：**理解人物为什么以某种方式感知世界，以及作者为什么选择这样呈现**。已形成 [人物感知因果 × 作者呈现选择](CORE_PERCEPTION_NARRATIVE_STUDY.md) 规范，commit `9b49445f2b879f1599f908c0b4a907c27bd2c0ec`。它是下一阶段设计，不是新增 Skill 或已完成的语义训练。

具体约束：已有八轨词汇标签只作为来源定位；按原文证据 span → 感知事件/决策单元 → 叙事节拍 → 场景 → 跨场景关系 → 全书认知发展做可追溯学习；把故事客观事实、人物有限知识与误解、叙述者选择、读者初读预期四者隔离；初读锁定、后文揭示、竞争假设、反事实改写、独立评审和跨作品迁移齐备后才可声称有效。没有真实模型/独立评审时只能标记未验证。

继续遵循单本原则；已完成《莽荒纪》的确定性结构学习无需重来。下一文学试点应该在同一本已归档私有 R2 原文上做少量场景，不把源文本上传公开 GitHub，不在没有模型授权时虚称已理解。文学语义学习必须有独立的实证，不可借用原文存储/R2 回读的成功状态。


## 11. V28 仅设计：武动乾坤“临摹倒推”训练（2026-10-16）

用户的新方向是：**快读一段剧情骨架 -> Skill 隔离原创练笔 -> 锁定草稿 -> 对照原著分析人物感知/叙事选择 -> 保存失误、遗忘、假说、对照和抽象核心 -> 删除草稿正文 -> 闭卷迁移测验；两个局部过关以后再训练 AB 合并的长剧情；90/100 多维质量与迁移闸门才推进下一段；同机制按 3→6→9 个独立证据“+3 比较”去重、合并和修订；可配置 max_chapters，有界重试。** 核心原则 99% 由技能程序/数据库/模型服务自主执行，助手只负责设计、修 bug 与看验收；不是模型 99/1 的可测算力分配。

**已完成：设计文件** [V28_REVERSE_CRAFT_LEARNING_DESIGN.md](V28_REVERSE_CRAFT_LEARNING_DESIGN.md)，commit `68d4a49ad783c43a945966221c0c24df5d482929`。其中包括数据流和安全状态机、独立核心文件视图、90 分审评门槛、+3 证据分级、模型与独立评审的隔离、原文版权及近似复制防线、SQLite/R2 不持久保存草稿正文、重试/内存/垃圾回收边界、故障注入测试。

**尚未执行**任何新真实《武动乾坤》写作模型训练或 90% 质量评测，也未实现 V28 协调器。不能把设计 commit 当成训练结果。旧 `literary_ladder.py` 仍持久保存草稿正文到本地文件与 SQLite，`R2StudyVault` 的逻辑摘要包含此字段；**不得直接用旧训练命令开始“先写后删除”**，否则可能把草稿落入不可变快照。要先实现独立短期 scratch、事务化核心摘要、核心轻量 R2 保全与擦除流程以及相应失效测试。

源：`wudongqiankun` 在私有 R2 已有 8,254,079 bytes SHA `86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28`，**全书章节连续性尚有已知异常**。首个真实试点只能使用明确核验的局部场景、全程单本；不得把跳号版本称为完整学习。试点建议 `max_chapters=3`、每章最多 6 单元、每单元最多 3 个候选、双段合并最多 2 次，预算耗尽则 BLOCKED，不能无限追求 90 分。

下一步如用户同意实现：只先构建最小状态机/合成测试和 R2 私有核心快照，验证内存上限、重复 +3、crash/restart、伪评分和删稿可靠性；**在基础合格之前不启动真实章节训练**。


## 12. V28 最小运行内核已实现并通过合成工程测试（2026-10-16）

- **用户批准开始实现** V28 临摹倒推最小内核，但尚未授权绕过原文来源及独立评价门槛。代码实现：[writerforge/reverse_craft.py](../writerforge/reverse_craft.py)（隔离 V28 SQLite 有限状态机、临时草稿清理、每单元至多 3 次练习、每 2 单元合并至多 2 次、独立 90/100 评价与闭卷重测拦截、通过核验后 3→6→9 个不同场景核心合并）；[writerforge/reverse_core_vault.py](../writerforge/reverse_core_vault.py)（只备份抽象核心 JSON 到私有 R2 独立目录、不可变 SHA256 对象及全新读取比对；严格字段白名单，禁止 `body`/草稿混入）。
- 隔离管理命令已加到 `writerforge/cli.py`：`writerforge --db workbench/v28-wudong.sqlite3 reverse-core-init --project wudong-lab --max-chapters 3 --max-units-per-chapter 6`、`reverse-core-status` 和 `reverse-core-restore --snapshot <SHA256>`，只初始化/观察/恢复 V28 小库，拒绝初始化覆盖原有学海 SQLite。**没有真实模型练习 CLI**，只有经过 source/reviewer gate 才能开发。
- 测试：[tests/test_v28_reverse_craft.py](../tests/test_v28_reverse_craft.py)、[tests/test_v28_reverse_craft_stress.py](../tests/test_v28_reverse_craft_stress.py)、[tests/test_v28_reverse_cli.py](../tests/test_v28_reverse_cli.py)，模拟模型/独立审稿器与模拟 R2；验证失败三次停机、评审缺失 BLOCKED、非独立评审拒绝、重复证据不能刷 +3、R2 回读损坏拒绝晋级、拟提交状态的恢复、两段合并关、2,000 次临时稿创建清理的有限内存使用、专用库隔离和正文注入拒绝。
- **GitHub Actions 全量测试成功：[run #38875995893](https://github.com/66tyu55/WriterForge/actions/runs/38875995893)**（含新增 R2 snapshot 字段白名单安全回归）。早先 [run #38875687961](https://github.com/66tyu55/WriterForge/actions/runs/38875687961) 也通过全部测试，包括内存和 +3 阶段用例。
- 使用说明及明确未实现的能力：[V28_MINIMAL_RUNTIME.md](V28_MINIMAL_RUNTIME.md)。这**不是真实《武动乾坤》文学训练、不是真实 90% 成功率，也没有运行真实模型或真实独立文学审稿服务**。V28 R2 备份只有 FakeR2 工程测试；尚未在真实 Cloudflare R2 上传新 V28 核心快照。真实文章目前仅已有单书原文归档，章节完整性仍存在缺陷，须先核实局部原文。
- 草稿 `TemporaryDirectory` 正常退出即清理，非物理安全擦除；崩溃后的临时文件须安排启动 `cleanup_stale_scratch` TTL 清理。不能让旧 `literary_ladder.py` 对练习稿 `body` 进行普通 R2 学习库备份。**不把合成评审器注入实际作者训练**。
- **下次按一次一本推进**：先完成《武动乾坤》第一小段和紧邻第二小段的真实章节/source span 校验（私有 runner 内做、日志只输出哈希）；再接独立生成模型和经过实际验证的盲评器，不共享原著全文给生成器；有了真实的评审回执和 R2 验收才允许自动晋级。


## 13. V28 已按用户新要求从《武动乾坤》开篇顺序启动（2026-10-16，覆盖先前“随机小场景”建议）

**用户决定必须从第一章最初开始，逐步建立人物前史、因果与认知，而非随机抽样。** 这条优先级覆盖以往任何“随机挑一段剧情做训练”的建议。本阶段不会自动多书并行。

新增程序 `writerforge/reverse_source_cursor.py`、`scripts/prepare_wudong_opening_r2.py`、`.github/workflows/v28-wudong-opening-r2.yml`、回归 `tests/test_v28_reverse_opening_cursor.py`。`ReverseCraftCoordinator.open_unit` 拒绝不从 `(chapter=1,ordinal=1)` 起步，后续仍受相邻单元和 AB 合并门槛约束。开篇确切 R2 来源与学习顺序说明见 [V28_FROM_BEGINNING_WUDONG.md](V28_FROM_BEGINNING_WUDONG.md)。

**真实 GitHub Actions #38876799592 success**：私有 R2 中已归档《武动乾坤》原文 SHA256 `86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28`、字节 8,254,079 重新读取并哈希核验。检测真实前 3 章标题依序 1→2→3，位于第 8、85、146 行；第一章正文 4,209 字符；提出两个从头连续的候选窗口 `[0,2125)` 和 `[2125,4209)`，无丢字、无跳跃。元数据-only 私有 R2 新对象及 fresh GET 全字节核验成功：`writerforge/v1/reverse-craft/wudongqiankun/opening-source/cc3c98eda8953fa23b2f8328fa6f897d5d0cfffa313561868389324aa178b441.json`。**当前仅 `OPENING_SOURCE_VERIFIED / BOUNDARY_UNREVIEWED`**；原文段落分界还未由真实模型审核为正确的叙事节点；没有生成原创稿、独立文学评论或 90 分晋级。

下一步先以第 1 章作真实语义场景/因果边界核查（人物当前所知、读者所知、目标、误解、行动、后果、未兑现问题）；通过后用 skill 自己调用隔离模型，只写第一窗口。首窗核心审评、短期稿清除、闭卷迁移过关之后才开启第二窗口。不可将第一章的机器“长度中点”当做已证实的文学场景切点；不能隐瞒模型/审稿/长因果上下文还没接通的事实。


## 14. V28 正式本地真实模型实践（2026-10-16，覆盖“仅模拟”状态）

用户要求：**不再小规模模拟，正式从《武动乾坤》开篇顺序进行临摹倒推，失败经验也必须真实入库**。当前仍只允许第一章首个连续窗口；不随机跳章，不伪造 90 分通过。

已提交模型运行流程：[writerforge/reverse_real_training.py](../writerforge/reverse_real_training.py) + [scripts/run_wudong_real_reverse_training.py](../scripts/run_wudong_real_reverse_training.py) + [.github/workflows/v28-wudong-real-first-training.yml](../.github/workflows/v28-wudong-real-first-training.yml) + [tests/test_v28_reverse_real_training.py](../tests/test_v28_reverse_real_training.py)。GitHub Actions 在隔离运行器内安装 Ollama，使用 **qwen2.5:3b** 规划和原创、独立的 **gemma3:4b** 做原著机制对照批评，限定每窗口最多 2 次候选、有限模型调用。原文只从私有 R2 恢复到运行器临时目录；原创练笔正文/原著不进入 GitHub 公开仓库、CI Artifact、持久 R2 学海。只保存抽象观点、缺点、反事实、原创草稿 SHA、失败哈希和模型身份到独立私有前缀 `writerforge/v1/reverse-craft/wudongqiankun/real-model-first-unit-v1/`（如生成成功）；不得把批评模型主观推测称作真实独立专家 90 分。

真实运行历史：
- [#38878209564](https://github.com/66tyu55/WriterForge/actions/runs/38878209564)：两个模型启动到真实推理环节，但结果被规范检查拦截；首次单元测试步骤误将 0 个测试显示为通过。
- [#38878544084](https://github.com/66tyu55/WriterForge/actions/runs/38878544084)：修复后确实运行 5 项单元测试；真实对照批评返回近似原著/草稿的长引用，拒绝持久化（`unabstracted original/draft in review note`），无 R2 核心晋级。
- [#38878999983](https://github.com/66tyu55/WriterForge/actions/runs/38878999983)：为批评模型提供有限一次重新抽象机会；第二次仍返回不合格文本，同样被拒绝入库。防复制闸门不能关闭。
- [#38879583627](https://github.com/66tyu55/WriterForge/actions/runs/38879583627)：已改为**无法重新抽象的字段仅保留内容哈希与 `UNVERIFIED_QUOTATION_REDACTED` 状态**，其他符合安全标准的经验继续保存；**本节记录时仍在执行**，需核查该运行的真实成功/失败日志、R2 新快照 SHA、fresh GET 才能确定是否已生成可用训练证据。不能先报成功。
- 实际独立模型批评仍**不是经过人类基准校准的 90% 文学能力审核**。真实模型有运行，模型权重未训练，WriterForge 核心晋级依然被阻塞；第二原著窗口未解锁。不能用模型生成文本/评论本身冒充“大师水平 90%”。

重要：GitHub Models inference API 于 2026-07-30 退役，不能再使用旧 GitHub Models 通道；当前使用本地 Ollama，GitHub Runner 没有继承用户聊天窗口模型。后续优先执行用户关心的**真实训练迭代质量与完整因果**，勿只重复 R2 连接模拟。原文有全书章节异常，开篇首窗已经严格按 source hash 和章节 1→2→3 验证；仍不可冒充全书完整章序。


### V28 真实模型后续故障记录（2026-10-16 09:23 UTC 后）

- [#38879583627](https://github.com/66tyu55/WriterForge/actions/runs/38879583627) **失败**：原始长引用已可在受限抽象重试后哈希化隔离；新的失败码为 `model answer not JSON`。这是 Ollama 模型在真实提示输入下返回不符合 JSON 契约的内容，不是 R2 源丢失；没有完整两次训练报告入 R2。
- 已修改 `writerforge/reverse_real_training.py`：可解析合法 JSON fenced 输出，遇到 JSON 格式错误时**最多一次**本地模型重试（temperature=0，输出有大小和超时上限），绝不假造回答。
- [#38880422839](https://github.com/66tyu55/WriterForge/actions/runs/38880422839) 是更新代码后自动发起的第 5 次真实运行，在本节记录时尚未最终完成。必须查 job 真实 `conclusion` 和是否生成独立私有 R2 核心回执；不许因启动任务就声称成功。
- 用户关心的文学习得质量仍**没有 90% 经校准独立结论**；即便运行成功，目前只可能得到“原文开篇首段真实模型练习及未审查机制证据”，不得开放第二段晋级。训练失败留存日志和哈希已在 GitHub Actions；公开仓库无原文正文或练习稿。


## 15. V28 云端高能力模型适配层与盲评 A/B（2026-10-16，覆盖旧 CPU 小模型依赖）

用户在检查 [InkOS](https://github.com/Narcooo/inkos) 后同意借鉴模型无关的 Agent Harness/多服务商路由，优先替代 GitHub CPU 上 3B/4B 模型并进行无技能/有技能的实际对比。**用户尚未选择付费模型服务商或提供对应 API 凭证、当前价格，不能自动进行外部原著传输及付费请求**。

已经实现：
- [writerforge/reverse_cloud_models.py](../writerforge/reverse_cloud_models.py)：角色 `planner / writer / critic` 独立配置；固定 HTTPS Chat Completions 兼容提供商白名单 `moonshot/deepseek/openrouter/openai/google`，不接受任意 URL，拒绝 HTTP 重定向；凭证取自运行环境，不进日志与 R2；每次调用前按输入字节与最大输出 token 预留美元保守预算，且有每任务请求上限和响应大小上限。Writer/Critic 必须是**不同模型身份**；不存在旧小模型自动回退。
- [writerforge/reverse_cloud_ab.py](../writerforge/reverse_cloud_ab.py)：只选《武动乾坤》第一章**第一连续源窗口**。同一原创任务：A 不含技能机制，B 仅含 Planner 从原文抽象得出的感知/因果/叙事方法；两份独立原创稿的哈希固定后才匿名给另一模型批评，对人物感知、因果、信息释放、连续性、语言逐维比较；长期只保留原文/稿哈希、短机制解释、模型评分（标为**unverified**），绝不把模型自评分宣称已达大师 90%。
- [scripts/run_wudong_cloud_ab.py](../scripts/run_wudong_cloud_ab.py)：必须明确原文外发同意；从既有 R2 恢复 pinned 原文校验后调用云端，单组模型配置有去重指针，结果哈希化保存在独立私有 R2 并 fresh GET 复验。未配置提供商/密钥/价格和独立同意时拒绝并不付费。
- [.github/workflows/v28-cloud-ab.yml](../.github/workflows/v28-cloud-ab.yml)：**普通 push 仅离线测试与凭证配置检测（零付费/零外发）**；只有手动 workflow_dispatch 且 `confirm_source_egress=true` 才可能运行收费的 `cloud_paid_trial`。这样不会因每次改代码就重复下载模型、产生 API 账单。
- [tests/test_v28_cloud_ab.py](../tests/test_v28_cloud_ab.py)：无网络的安全/角色/预算/同题匿名 AB 回归。完整配置说明与用户须操作项见 [V28_CLOUD_MODEL_AB_SETUP.md](V28_CLOUD_MODEL_AB_SETUP.md)。

**已核实 GitHub 证据**：[配置检查和模型协议测试 run #38882720229](https://github.com/66tyu55/WriterForge/actions/runs/38882720229) `success`（7 项测试），但 `safe_cloud_readiness` 返回 `ready=false`，原因仅报告 `cloud_roles_or_price_or_credential_unconfigured`；收费作业 `cloud_paid_trial` 正确为 **skipped**。这不是实测云端模型质量通过。最新仓库全量 Python 测试另有 [#38882868438](https://github.com/66tyu55/WriterForge/actions/runs/38882868438) `success`，包含上述 A/B 相关回归。

**待办**：由用户自行在 GitHub Actions 配置角色 Secrets、Variables 和价格/预算，明确选定云端模型和允许哪家服务接收私有小说首窗，随后手动触发真实付费单本 A/B。完成后应检查 API 真实调用、R2 SHA 和文学盲评证据；不能因模型评分数字大于 90 就晋级。编排仍保持从原著第一章连续推进，下一段尚未解锁。InkOS 只借鉴架构/调度理念，未复制 AGPL 源码。

 
## 16. Discovery 密钥可见性核验（2026-10-16；覆盖错误的“用户未保存”判断）

用户提供 GitHub 页面已存在 `DISCOVERY_API_KEY` 的截图，**不得要求用户反复新增/改名或在聊天里发送真实 API Key**。最初 `scripts/probe_discovery_api.py` 用 `len(key)<12 or whitespace` 输出 `MISSING_SECRET`，无法判断密钥到底是否在 Action 中可见；此前因此推断“用户未配置”不成立。已修改成三种独立状态：环境变量缺席、GitHub Actions Secret 表达式映射为空、变量有值但本地格式检查失败，绝不输出原密钥、长度或片段。

**重新运行 [#38885722986](https://github.com/66tyu55/WriterForge/actions/runs/38885722986) 真实结果：`GITHUB_ACTIONS_SECRET_RESOLVED_EMPTY`，workflow 的 `env: DISCOVERY_API_KEY: ${{ secrets.DISCOVERY_API_KEY }}` 在 `66tyu55/WriterForge` main 分支 push 运行环境被解析为空。真实模型请求为 0，小说原文外发为 0，费用为 0。**这不等于用户没保存密钥。** 需检查屏幕上对应 Secrets 是该仓库的 Actions Repository secret、Environment secret（需要 job `environment` 匹配）还是其他仓库/组织/Dependabot/Codespaces 范围。截图裁切未显示层级，不可猜测是哪一类；不能读取密钥本体。


## 17. Discovery 实际密钥名修正、可用模型、正式 V28 A/B 试跑（2026-10-16）

用户截图中 GitHub Secret 的准确名称是 **`DISCOVERY__API__KEY`（双下划线）**，此前错误地引用为 `DISCOVERY_API_KEY` 导致 Actions 环境变量为空；**不是用户未保存密钥，无需重新注册或修改 Secret**。已把 `.github/workflows/discovery-api-probe.yml` 与专用 V28 工作流改为引用 `${{ secrets.DISCOVERY__API__KEY }}`，进程内部 env 名可仍用单下划线，不冲突。

- [鉴权和真实短文生成 success #38886144104](https://github.com/66tyu55/WriterForge/actions/runs/38886144104)：端砚 `https://discovery-api.intern-ai.org.cn/v1` 实测返回 11 个模型，包括 `deepseek-v4-flash-0731`、`deepseek-v4-pro-0813`、`glm-5.3`、`kimi-k2.6`、`intern-s2`、`minimax-m3`。使用 DeepSeek V4 Flash 真实生成 45 字符（prompt 109、completion 69 tokens），`finish_reason=stop`；没有发送私有小说。
- [三个模型各自真实简短 JSON 能力 success #38886690784](https://github.com/66tyu55/WriterForge/actions/runs/38886690784)：`glm-5.3`、`kimi-k2.6`、`deepseek-v4-pro-0813` 均可返回短 JSON；这**不代表**长文复杂输出一定合格。
- 新增 `writerforge/reverse_discovery_models.py`（固定端砚 HTTPS 主机、5 次请求/16000 预约输出 tokens 总上限，单请求超时 150 秒，不暴露 key，安全 JSON 重试至多一次）；`scripts/run_wudong_discovery_ab.py`（从已有私有 R2 SHA pin 恢复《武动乾坤》第一章首段、真实非模拟 Planner→Kimi Writer A/B→DeepSeek V4 Pro Critic、只存抽象证据及短回执到独立私有 R2；不把练习稿或整本原文持久保存）；`.github/workflows/v28-discovery-real-ab.yml`（已在用户同意“能调通就开始正规训练”后启动单书）。
- [首轮正式 A/B #38886477025](https://github.com/66tyu55/WriterForge/actions/runs/38886477025) **失败**，因复杂 JSON 契约；[第二轮 #38887011693](https://github.com/66tyu55/WriterForge/actions/runs/38887011693) 在有限重试后仍失败，精确故障为 `DISCOVERY_PLANNER_JSON_CONTRACT_FAILED`，来自 GLM-5.3 面对实际原著的长结构分析。原文 R2 未损坏；无“90% 大师水平通过”或第二段解锁。
- 已将仅规划角色替换为 **`deepseek-v4-flash-0731`**；保留 `kimi-k2.6` 写作、`deepseek-v4-pro-0813` 审评。[第三轮正式 A/B #38887477346](https://github.com/66tyu55/WriterForge/actions/runs/38887477346) 在本文写入时刚启动，**必须读 job 最终结论和远端 R2 receipt 才能确认结果**，不可预写成功或文学能力改善。
- 后续无论结果如何，不许用模型自己的 90 分取代独立校准盲评。不启动额外小说、不跳过序列原著、不无限迭代。API Key 真值不能回显，不需要用户重复配置。


## 18. Discovery 真正连通 + 第一次正规原著文学 A/B 真实完成（2026-10-16，覆盖第 17 节尚在执行）

已确认用户使用的是 **GitHub Secret `DISCOVERY__API__KEY`（双下划线）**，工作流已经引用此名称。**不必要求用户重命名、新建密钥或在聊天中暴露 Key**。

**成功的真实端砚 API 和 R2 证据：**
- [连通和单次生成 #38886144104](https://github.com/66tyu55/WriterForge/actions/runs/38886144104) `success`，`deepseek-v4-flash-0731` 正常输出；
- [GLM/Kimi/DeepSeek 三种真实模型的短 JSON #38886690784](https://github.com/66tyu55/WriterForge/actions/runs/38886690784) `success`；
- 初始大型 A/B 曾因 GLM-5.3 规划阶段复杂 JSON 错误、Kimi-K2.6 长篇请求无可见正文而失败，原文/草稿未持久污染学习库，完整失败日志在 [#38887011693](https://github.com/66tyu55/WriterForge/actions/runs/38887011693) 和 [#38887477346](https://github.com/66tyu55/WriterForge/actions/runs/38887477346)。还有一次 [#38887900901](https://github.com/66tyu55/WriterForge/actions/runs/38887900901) 仅为测试要求三模型必须完全不同而导致工程验证失败；已把测试修为实际要求 Writer/Critic 模型身份不同。
- **最终真实完整 A/B [run #38888018955](https://github.com/66tyu55/WriterForge/actions/runs/38888018955) `success`**：使用 `deepseek-v4-flash-0731` 为原著规划，`deepseek-v4-pro-0813` 生成 A/B 两份原创稿，`deepseek-v4-flash-0731` 独立于写作者执行匿名模型批评（规划与评审同一模型 ID，不能称为三个互相独立模型，更不能声称独立人类评审）。原文使用已验证私有 R2 《武动乾坤》第 1 章第一连续窗口。**共 5 次真实 API 调用**，服务端报告输入 11,658、输出 7,637 tokens，总 19,295 tokens；未进行模型权重微调。抽象报告和两篇原创草稿 SHA 已存独立私有 R2，完整原著和草稿均不持久保留。私有快照 SHA256 `86953525286e33e5a09f0acb4d4774e7ccfa3abafe0b5d00fe65c5f5e0c66b04`，全新回读检验成功。
- **只读数字结果审核 [run #38888592336](https://github.com/66tyu55/WriterForge/actions/runs/38888592336) `success`**：模型批评分 **无技能基线 86/100**（感知88、因果85、信息82、连续90、语言86），**启用 WriterForge 技法 84/100**（感知84、因果86、信息80、连续88、语言82），**单次增量 -2 分**。说明这次增强策略并未改善写作，且不满足原定 90/100 门槛。样本仅一组，且批评模型未作专家/真人校准，**不能证明长期有效或有害**。不要把生成或 R2 写入成功标成文学能力升级；第二窗口 **未解锁**。
- 为防推送代码时重复消耗用户的端砚额度，已将 `.github/workflows/v28-discovery-real-ab.yml` 改为 **仅 `workflow_dispatch` 手动启动**。不要再无授权做付费/额度消耗调用。
- 当前正确下一步是**分析首轮增强稿为何比基线差**，从已保存的私有短机制/审评意见中提炼缺点，先修 Skill 的信息提取及因果上下文选择，再由独立客观评审与不同剧情验证；不是继续盲试多个模型或跳到下一章。所有 90% 阶段晋级仍 **BLOCKED**。


## 19. V28 第一轮真实 R2 A/B 文件深读与失败归因（2026-10-16）

**用户只要求分析已经留存的文件，这一轮没有再次发起付费模型训练。** 完整结果与修复优先级见 [V28_FIRST_REAL_AB_FAILURE_ANALYSIS.md](V28_FIRST_REAL_AB_FAILURE_ANALYSIS.md)，commit `62cdeb7cc7aa8ec8545c69e8570d2ef9f5543485`。真实摘要证据来源：[R2 源文哈希/短评读取 #38892524270](https://github.com/66tyu55/WriterForge/actions/runs/38892524270) `success`。

重点发现：
- 无技能原稿的五项模型分为感知88、因果85、信息82、连续90、语言86；WriterForge增强稿为84、86、80、88、82。准确平均 **86.2 vs 84.0（-2.2）**，原有软件的整数截断记录为 **86 vs 84（-2）**。单评审、单样本不可推广为 90% 能力。
- 基线稿 **1662 字符**，技能增强稿 **2483 字符（多821，约49.4%）**；不等长实验本身严重影响公平性。
- 最关键的**程序级污染**：Planner 的 `perception/decision/author_mechanism` 自由文本描述**含林动、家人、受伤和让出修炼资源等原著专有内容**，而 `reverse_cloud_ab.py` 原样把它们送给增强写作者作为 `technique_constraints`；这不是可靠的“只传技巧，不传剧情”。增强稿的模型批评也描述家庭伤痛、牺牲与身世秘密，而基线描述全新神秘交易情节。因原稿已经删除不能判断是否有确切情节抄袭，应标注**明确的提示词源剧情污染、未证实的稿件复述风险**。
- 仅因果项 +1，人物感知及语言项均 -4；模型短评认为技能增强稿内在感知较弱、信息更直白、心理转折偏快，两稿的悬念均缺足够先导线索。Planner 与 Critic 同为 DeepSeek V4 Flash，不算三模型互相独立。
- 正式 V28 失败/遗忘/因果跨段状态机尚未连接实际 A/B；云端原型只留单组 R2 报告和稿件哈希，丢失了日后对原稿进行再次独立审查的可能性。
- **P0 修复**：必须把 `SourceCharacterState`（原著专有角色/知识/剧情，仅供分析审核）与 `TransferableMechanism`（面向写作的 HOST 策略 ID，无原文专名及剧情）隔离；对 prompt 泄露设置拒绝规则。随后控制 A/B 等长、不同评审和真正的短期草稿审阅→删除→闭卷复测。**没有修复前不再进行新收费 A/B，也不能解锁第二窗口或伪称已达90%。**


## 20. V28 底层 P0 已修：原著情节→写作提示的污染被接口隔离（2026-10-16）

用户质疑“WF 是否给写作添乱、是底层问题还是模型问题”，依据真实 A/B 失败认定首先是底层数据路由错误（Planner 的自由原著剧情描述被当作 technique_constraints 送给 Writer），同时只凭单样本评分不能确定技能总体质量。**已直接修改代码，不只是设计。** 详见 [V28_P0_ROOT_CAUSE_FIX.md](V28_P0_ROOT_CAUSE_FIX.md)。

- 新模块 `writerforge/reverse_mechanism_boundary.py`：宿主维护四项有限、可执行的非原著叙事操作；只允许 Planner 返回最多两个预定义技巧 ID + 原文段落证据 ID，原著人物/情节/自由文本不能进入 Writer 提示。缺失段落、原著人物字段、未知机制、重复证据全部 fail closed。**4项是固定安全初始集合，不等于模型已自主学出4种新技能。**
- `writerforge/reverse_cloud_ab.py` 不再直接发送 Planner 的 perception/decision/author_mechanism 剧情说明给 Writer，只发送固定机制操作；A/B 实际稿长相差超过15%时在批评模型调用前直接拒绝评分，杜绝之前49.4%不等长的明显混杂。
- 新合成防污染回归 `tests/test_v28_mechanism_boundary.py` 及更新的 `tests/test_v28_cloud_ab.py`；[GitHub 全量测试 #38894363064](https://github.com/66tyu55/WriterForge/actions/runs/38894363064) success、[#38894585603](https://github.com/66tyu55/WriterForge/actions/runs/38894585603) success。
- **实际原文 R2 预检** [run #38894840319](https://github.com/66tyu55/WriterForge/actions/runs/38894840319) success：原文 SHA仍是 `86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28`，第一章第一窗口2125字符、37物理段（最大126字符）、与下一窗口连续。把原先过紧36段上限调整为96段+总输入5,500字符上限。只读原文，无模型、无收费、无原文输出日志。
- 未来正式 A/B 版本已升级为 `source-isolated-ab-v2` 独立 R2 命名空间和缓存指纹；旧 `real-discovery-ab-v1` 私有失败实证不覆盖、不修改。付费工作流仍**仅手动 workflow_dispatch**，本轮未启动新正式模型训练。
- 未完成：产生真正新候选文学机制并经独立文本审评/闭卷迁移晋级、把真实失败/遗忘纳入 V28 SQLite+R2 有界证据、对正式 A/B 做跨题等长和独立真人/模型校准。**第一段仍 NOT_PASSED，第二段 LOCKED，所谓大师90%尚无验证。**


## 21. V28 按用户要求恢复真实额度训练：P0 后反馈式迭代（2026-10-16）

用户明确指示“**继续消耗，就是要一边消耗一边发现问题**”，不再局限于离线修代码。**限次真实训练获授权**，仍一书、一窗口、预算上限与源文隔离，不得无期限重试；费用不是质量证据。

- **真实 P0 修复后首轮** [run #38895404803](https://github.com/66tyu55/WriterForge/actions/runs/38895404803)：P0 源文隔离/AB/Discovery 协议单测通过；实际端砚调用 **3次**，Planner 成功而写作阶段 `DISCOVERY_WRITER_JSON_CONTRACT_FAILED`，程序终止、未比较文学评分。新增代码 `scripts/run_wudong_discovery_ab.py` 会把失败码、实际调用数、报告 token 使用、源文哈希与实验配置哈希（没有原著或草稿）写入**独立私有 R2**，经 fresh GET 核验，真实失败回执 SHA256 `59d489b6050851e63b2ae78b80ebc2a31c747f226d6f955dd3cf775afe6f2d2d`。这是首次失败证据独立存储，不能算成功。
- 通过真实故障推断，不宜强制长篇小说正文遵守 JSON 序列化契约；已将 `writerforge/reverse_discovery_models.py` 拆分角色协议：Writer 接收有界**原生小说正文**、必要时封装为内部 `{"scene":...}`（不回写正文）；Planner 与 Critic 仍严格 JSON。拒绝被截断的正文、只允许一次预算内重试；`writerforge/reverse_cloud_ab.py` 写作提示与 `reverse_mechanism_boundary.py` 也改为正文输出契约。新增正文/截断回归 `tests/test_v28_discovery_models.py`，**全量 GitHub Tests #38896069801 success**。
- 已发起**第二次真实代码修订后试验** [run #38896171856](https://github.com/66tyu55/WriterForge/actions/runs/38896171856)，在本节记录时仍在运行；应以最终 job `conclusion` 和 R2 成功/失败 SHA 作为唯一真实状态来源。若结果失败，按失败阶段做有限修复和真实对照，禁止简单跳过、假造 90 分或解锁第二窗口。
- 两个单次工作流 `.github/workflows/v28-wudong-iteration-one-shot.yml` 和 `...iteration-02.yml` 仅在其各自文件创建的 push 上触发，不会因日后普通代码改动而重复消耗；常规 `v28-discovery-real-ab.yml` 仍仅手动启动。


## 22. 用户要求真实消耗发现问题：四轮受限实跑及根因（2026-10-16，覆盖第 21 节 pending 状态）

用户明确同意继续花端砚可用额度开展真实调试，策略是**有限预算逐轮实跑、真实故障->修正->回归->再测**；本节全部证据来自已完成 Actions，不可说“模型训练过关”。仍遵循《武动乾坤》第一章第一窗口，不跳章、不自动无限收费。

- **修复后首轮** [#38895404803](https://github.com/66tyu55/WriterForge/actions/runs/38895404803) **failed**：Planner 通过，Writer 的长篇正文 JSON 输出契约失败，3 次真实 API 调用；私有 R2 哈希化失败记录 `59d489b6050851e63b2ae78b80ebc2a31c747f226d6f955dd3cf775afe6f2d2d`。没有把不完整原著或草稿写到公共仓库、R2 学海，第二窗口未晋级。
- 将输出协议按角色分离：**Writer 返回原生连续小说正文**（内部只临时包装为字典），Planner/Critic 继续 JSON；拒绝文本过短、异常代码块、模型截断，仅有限一次重试。相关离线全量 [#38896069801](https://github.com/66tyu55/WriterForge/actions/runs/38896069801) **success**。
- **第二次** [#38896171856](https://github.com/66tyu55/WriterForge/actions/runs/38896171856) **failed**：5 次真实 API 调用后命中总预算；R2 失败 SHA `b569aa421741c32b989621ca6f58c0f0867408bc0b5e161ad89c1437868a99fb`。增加 `DiscoveryCallBudget.calls_by_role / last_requested_role / response_observations` 以存每角色次数、完成原因、可见字数（**不存生成内容**），硬上限有界从 5 次适度提高至 7 次、预留输出 token 上限 25,000。
- **第三次** [#38896845100](https://github.com/66tyu55/WriterForge/actions/runs/38896845100) **failed**：Planner 1 次成功，Writer 4 次响应导致 `DISCOVERY_WRITER_OUTPUT_TRUNCATED`，R2 SHA `6857551c6ee35ddd2428be96bb5c05727c2d81b6744827dc0bab87b77ce18a0d`。过去重发相同请求从头生成，浪费 tokens；已改为遇到已有部分可见正文且 `finish_reason=length` 时，**只允许带前文接续一次**，同时检查截断和边界，仍不把小说全文持久化。补合成“接续而非从头写”的回归测试。
- **第四次** [#38897761659](https://github.com/66tyu55/WriterForge/actions/runs/38897761659) **failed**：这轮前端正文阶段之前，Planner 连续 2 次 `finish_reason=length`、可见内容0字符，故 `DISCOVERY_PLANNER_OUTPUT_TRUNCATED`；失败记录 R2 SHA `6fcd297e8f6152752d5f89b462dface322126a6cd3502b420f5067dd5028afe4`。说明 V4 Flash 作为分析器偶尔会把短格式回答预算全部用于不可见推理，不能靠盲加调用上限解决。
- 官方 Intern Chat API 文档表明 **Intern-S2 支持 `thinking_mode=false`**，已仅给此模型适配该参数；[真实无原著小型兼容性探针 #38898246863](https://github.com/66tyu55/WriterForge/actions/runs/38898246863) **failed**：返回 `finish_reason=stop` 但可见0字符，受到单请求预算限制；在端砚 Discovery 网关当前能力未核实前 **不能切换 S2 为正式模型或谎称已解决无可见回复**。
- `scripts/run_wudong_discovery_ab.py` 已把 R2 失败凭证中的代码升级为受白名单字符限制的静态 `DISCOVERY_<ROLE>_<CODE>`，便于后续明确辨别哪个环节失败，但不允许记录任意服务端错误正文/密钥。上面第 3、4 次老失败凭证部分 `code` 仍为泛型 `DiscoveryError`，但该次真实 GitHub 日志保留了具体错误码和角色响应元数据；不能偷偷重写不可变快照。

**本轮已发生真实模型推理，并实证多个底层协议缺陷；没有新的“通过文学训练”的证明，没有可比的新版增强/无增强评分，也没有升到第2段。** 本轮只通过工程单测和真实失败留证，90% 晋级始终 BLOCKED。

**下次最先要做的不是盲目扩大 max_calls**：先确认有能力输出短、结构化技术ID的 Planner 模型以及端砚模型返回结构（不可见 reasoning、content 与 finish_reason 的类型与长度），避免继续浪费端砚余额。随后在相同原著窗口、相同稿长条件下做完整原创 A/B；有真实可比批评结果后才修 WriterForge 的文学机制层。保持普通 GitHub push 不自动收费；所有这轮 one-shot workflows 仅对其自身的文件变化触发。


## 23. V28 固定百万上下文模型二人组与 50,000 Token 总预算（2026-10-16）

用户要求“**固定2/3个模型，全是1m上下文的，限制大一点，5万**”。实际选择 **2 个模型**：端砚所列 `deepseek-v4-flash-0731` 做规划+模型批评、`deepseek-v4-pro-0813` 做原创+续写，**不再频繁换模型**。DeepSeek 官方 V4 文档证实二者支持 1M（1,048,576）token 上下文，DeepSeek 官方 Chat API 支持 `thinking:{"type":"disabled"}` 关闭默认思考；端砚 Discovery 网关 [真实短问探针 #38910061191](https://github.com/66tyu55/WriterForge/actions/runs/38910061191) **success**，两个具体模型 ID 在此第三方网关都能使用 thinking=disabled 并返回可见短文本，未发送私有原著。端砚 `/models` 未暴露实际 context_window，**不能把官方 1M 参数宣称为第三方网关 1M 实压通过**。

实施：
- `writerforge/reverse_discovery_models.py` 固定角色映射、声明官方 1M 规格与网关压测未验收状态；每次请求显式关闭 DeepSeek V4 的深思考，避免小窗口空白回复；单次 `max_tokens` 配置上限 50,000 且**共享每轮总预留输出最多 50,000 tokens**，最多 7 次实际模型请求。请求传输上限4MiB，响应最大1MB，超额 fail closed。
- `writerforge/reverse_cloud_ab.py` 请求预算按 Planner 6,500 + Writer A 11,000 + Writer B 11,000 + Critic 8,000 = 默认36,500；余下13,500留给有限一次的故障重试；达到总50,000时停止。不是每个阶段自动消耗满5万。
- `scripts/run_wudong_discovery_ab.py` 使用独立 v3 `fixed-1m-context-50k-ab-v3` 前缀及模型/源指纹，旧 v1/v2 的成功与失败证据都保留。
- 新回归 `tests/test_v28_fixed_pair_budget.py`；GitHub [全量 Tests #38910871380](https://github.com/66tyu55/WriterForge/actions/runs/38910871380) **success**。代码与限制见 [V28_FIXED_1M_PAIR_50K.md](V28_FIXED_1M_PAIR_50K.md)。
- 用户先前明确“边消耗真实端砚额度边发现问题”，因此已启动**仅一次**实际 [#38910720051](https://github.com/66tyu55/WriterForge/actions/runs/38910720051)，本条写入时仍执行中，必须读取最终 Actions job 结论与私有 R2 凭证；不能提前宣称文学训练完成或90分，第二窗口始终锁定。普通代码提交不会重复触发这个一次性付费工作流。


## 24. V28 两个固定 1M 模型、50k预算的真实 A/B 已完成，**文学增益仍失败**（2026-10-16）

更新第23节的 pending 状态。**[GitHub Actions #38910720051](https://github.com/66tyu55/WriterForge/actions/runs/38910720051) success**；实际端砚 Discovery 上 `deepseek-v4-flash-0731` 负责规划/批评、`deepseek-v4-pro-0813` 负责写作；均显式 `thinking:{"type":"disabled"}`。4次真实API请求（Planner1/Writer2/Critic1），模型报告输入6648、输出3090 tokens；36,500为预算**预留**，不是实际消费，硬上限仍为50,000请求预留输出tokens。私有 R2 不可变快照 SHA256 `b1354316a9ca487e7e07f127be78b0ca3856855f1168d73d313ae6a99568822a`，fresh GET 哈希核验通过，无公开原文或草稿正文。

**[只读数值审计 #38911363049](https://github.com/66tyu55/WriterForge/actions/runs/38911363049) success**：
- Baseline **86/100**（感知88、因果85、信息82、连续90、语言86），稿长1656字符；
- WF enhanced **76/100**（感知74、因果78、信息70、连续80、语言82），稿长1533字符；
- 模型审评 **增量 -10 分**。A/B等长控制已通过，长度差123字符 /1656 =7.4%；不再沿用原 v1 的49.4%不等长/源剧情污染。
- Planner 选取的两项**宿主预置**机制 `GOAL_FILTERS_ATTENTION`、`COST_VISIBLE_IN_ACTION`；不能宣称它们是WF新学出的技巧。当前数据显示这两个固定操作未在单次原创中产生质量提升，应检查机制转译是否让文字僵硬、故事目标不一致等假说，但未经独立评论确认不可断言。
- V28的模型短评不是独立真人评价，单组分差不是稳定因果效果，也**不允许**以76分晋级；第一窗口仍 `NOT_PASSED`，第二窗口 `LOCKED`。

技术状态：现在【固定模型 / 1M官方规格 / 端砚实测关闭深度思考 / 50k预算 / 真实A/B / R2回读】都已通过；**技能写作质量提升没有通过**。不要错误地把 #38910720051 的GitHub success解释为文学胜过基线或大师90分。公开源文件与真实状态见 [V28_FIXED_1M_PAIR_50K.md](V28_FIXED_1M_PAIR_50K.md)。后续训练改进重点是机制选择/呈现是否真正引导主人公感知、行动与读者理解，而非继续盲目换模型或扩大token。此轮一次性工作流不会因普通代码 push 重复产生费用。


## 25. 用户纠正跨厂商模型固定配置、继续真实训练，但文学分析延后（2026-10-16）

用户明确要求：**“no——不要使用一家的模型——暂时v4 flash和5.3吧——然后这次继续训练——留到下次一起分析。”**

本轮不再采用一家的 V4 Flash+V4 Pro。已修改：
- `writerforge/reverse_discovery_models.py` 固定 **Planner = DeepSeek V4 Flash `deepseek-v4-flash-0731`，Writer = Z.ai/智谱 `glm-5.3`，Critic = DeepSeek V4 Flash `deepseek-v4-flash-0731`**。两家、两个模型，三角色并非三种独立模型。Writer/Critic 来自不同厂商。模型官方均标 1,048,576 tokens 上下文；端砚 Discovery 网关尚未对 1M 请求实压验收。
- 保留每轮共享 `50_000` 预约输出 Token 上限、7 次 API 请求上限、单次最多一次有限重试与 Source/Writer 剧情隔离；DeepSeek Flash 显式 `thinking:disabled`，GLM 不擅自传未经端砚网关核验的思考参数。
- `scripts/run_wudong_discovery_ab.py` 将本次结果独立存入 `cross-vendor-flash-glm53-50k-ab-v4` 私有 R2 路径，不污染原有 v3 及之前真实失败凭证。上游仍是私有 `wudongqiankun` 第一章第一连续窗口，不解锁第二段。
- 新的角色与 1M 规格回归 `tests/test_v28_fixed_pair_budget.py` 已实际通过 [GitHub Tests #38913521779](https://github.com/66tyu55/WriterForge/actions/runs/38913521779)。
- 用户已授权**本轮一次**真实额度训练，[one-shot Actions #38913593019](https://github.com/66tyu55/WriterForge/actions/runs/38913593019) 在写入此条时执行中；必须根据最终 job `conclusion` 和 R2 SHA 更新。本轮按用户要求**不做文学原因分析/不做新评分长评**，即使 A/B 完成也只保存私有证据，下一次聊天统一分析。不可将工作流成功解释为已达到90%，也不自动进入第二段。

注意：此 one-shot workflow 仅因新文件创建触发；未来代码普通 push 不会自动重复产生模型调用。不要自动改回同一厂商两款 V4。


## 26. 跨厂商 Flash + GLM-5.3 上轮结论及有限网络重试实跑（2026-10-16）

用户说“开始”，依上一轮交接继续，**不重新定义模型或原文**。固定 Planner/Critic=`deepseek-v4-flash-0731`，Writer=`glm-5.3`，首书仍《武动乾坤》第一章第一连续窗口，50,000 预留输出 tokens、最多7次调用。GLM原生小说正文，Flash结构化分析。

- 已核实上一轮 [#38913593019](https://github.com/66tyu55/WriterForge/actions/runs/38913593019) **失败**，不是“仍执行中”。真实请求3次（Flash规划1/GLM写作2）；Flash解析输出148可见字符，GLM第一稿1127可见字符、`finish_reason=stop`；第二个GLM写作请求 `DISCOVERY_NETWORK_FAILED`（旧适配器把超时、连接错误合成此码），因此**尚无第二篇完整稿、未进行独立审评，不能给这轮文学分数**。此失败已经存入独立私有R2，SHA256 `1e50ae50b1c1818a853268269fd1be184b30de4317beeb3ae89ea2d2482160ab`。源码和原R2快照未受影响。
- 依据实际失败修 `writerforge/reverse_discovery_models.py`：区分 `DISCOVERY_TIMEOUT` / `DISCOVERY_CONNECTION_FAILED` / 状态码；仅对超时、连接失败、HTTP 429/502/503/504 **在同一次调用内额外重试1次**。两次请求都提前预留 token、都计入全局 max_calls（即使网络超时后服务商可能已经收费），每角色响应记录纯错误类型与可见长度，不泄露密钥/原文。401等永久失败不自动重试。
- 已增加离线测试 `tests/test_v28_discovery_models.py`，验证超时恰好一次重试、费用额度预留、重复超时终止、401不重放；GitHub [全量回归 #38918418959](https://github.com/66tyu55/WriterForge/actions/runs/38918418959) **success**。
- 已经针对同一本第一窗口启动一次受限真实 A/B [run #38918557675](https://github.com/66tyu55/WriterForge/actions/runs/38918557675)，**本节落盘时任务正在执行**；必须再核查最终job状态、真实API调用及私有R2 SHA，不能声称通过。只有在双稿、长度闸门、审评、R2备份全部满足时才可分析本轮质量。文学 90% 及第二窗口均未解锁。

保持所有付费 workflow 为一次性文件创建触发或显式手动触发，代码普通提交不自动无限消费。


## 27. 跨厂商 DeepSeek Flash + GLM-5.3 真实 A/B 重试成功，首次单次正向分差（2026-10-16；更新第 26 节 pending）

此项**覆盖第26节“正在执行”的旧状态**。完整审计见 [V28_FLASH_GLM53_REAL_COMPARISON_20261016.md](V28_FLASH_GLM53_REAL_COMPARISON_20261016.md)，commit `a1d1d0c8e90d769c736c53b0ed761694953861fb`。

- [真实运行 #38918557675](https://github.com/66tyu55/WriterForge/actions/runs/38918557675) **success**：固定跨厂商两个模型，Flash 规划1+审评1，GLM-5.3 生成两份原创，各一次；总4次API请求，服务端报告输入5971、输出10375 tokens。原著第1章第1连续窗口 + SHA pin不变，原著具体人物/剧情没有进入 Writer 提示，模型稿不入持久R2。成功生成抽象报告，并全新回读验证私有R2不可变快照 SHA256 `a2882f770e76fee4f4cedffb219d919a1a169fd731832b3d2de24e105c6a0282`。
- [只读证据/短评复核 #38919228502](https://github.com/66tyu55/WriterForge/actions/runs/38919228502) **success**：**Baseline 86/100（感知88、因果82、信息85、连续90、语言86；1050字符），WF增强89/100（感知92、因果89、信息87、连续91、语言90；1183字符）**。模型评分分差 +3（精确算术平均 86.2 vs89.8，差+3.6），稿长差11.24%通过15%比较闸门。选中宿主已有机制 `COST_VISIBLE_IN_ACTION` + `EMOTIONAL_TURN_WITH_EVIDENCE`，不是WF新学出的两种技巧。批评意见称WF稿在职业感知和具体代价行动上更合理，但未解悬念仍缺足够支持线索；只能作为**单次、未真人校准的候选证据**。
- 对比历史 v1 `86 vs84`、v3 `86 vs76`，这是第一轮可比同题 **模型分数向好** 的跨厂商组合，但因为创作模型、随机内容、机制组合不同，**不能归因于某个具体因素，更不构成稳定迁移能力**。原稿已按设计删除，不能从 R2 还原给新评审逐字复核。
- 仍无独立人类读者评价、闭卷新人物任务及跨场景3→6→9核心证据；`literary_mastery_90_percent_verified=false`、第一窗口 `NOT_PASSED`，第二窗口 `LOCKED`。不能用GitHub Actions success或未经校准的89分自动晋级。
- 上轮 GLM第二请求网络中断的失败 R2快照 `1e50ae50b1c1818a853268269fd1be184b30de4317beeb3ae89ea2d2482160ab` 保留，已为端砚SDK加入单次有界超时重发测试。**继续固定两个厂商模型，不再自动换回V4 Pro**。用户说“开始”后已实际做上述真实实跑、核验、文档和交接，而不是仅做设计。


## 27. 【最新最终交接】跨厂商 V28 真实 A/B 运行成功、准备下一聊天分析（2026-10-16 15:09 UTC）

用户说明当前对话上下文达到上限，要求交接。**本节是最新事实，覆盖第25/26节“正在执行”的状态；不要在下一对话中重新跑已成功的这轮。**

### 真实执行最终验收

- 仓库 `66tyu55/WriterForge`，`main`；固定模型仍是端砚网关（Secret **`DISCOVERY__API__KEY`，双下划线**）：Planner/Critic = `deepseek-v4-flash-0731`，Writer = `glm-5.3`；两个不同厂商的模型，非三个不同独立模型。保持此映射，不能再擅自换回两个 DeepSeek。
- 原文仍为私有 R2 中 SHA256 `86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28` 的《武动乾坤》第一章第一连续窗口（2125字符）。未向公共 GitHub 仓库或日志输出原著正文/草稿，不可随机跳段。
- 用户授权“边真实消耗额度边发现问题”，本轮已执行一次性 [**GitHub Actions #38918557675**](https://github.com/66tyu55/WriterForge/actions/runs/38918557675)，经最终 `fetch_workflow_run_jobs` 验证 **`completed/success`**；4项离线测试步骤共 10+4+5+7 个测试通过，然后真实模型运行成功。
- 真实记录精确阶段 `DISCOVERY_REAL_MODEL_AB_R2_CONFIRMED`，**4 次真实 API 调用（规划1/写作2/批评1）**；服务端 `prompt_tokens=5971`、`completion_tokens=10375`，总 16,346。全轮 **50,000 预留输出 Token 硬上限**（不等于实际消耗）、最多7请求；运行结果 SHA256 **`a2882f770e76fee4f4cedffb219d919a1a169fd731832b3d2de24e105c6a0282`**。成功路径对私有 R2 的不可变 JSON 内容回读对比 SHA，且 `completed.json` 指针回读一致；**不是模型权重训练**。
- 交付的是真实原创 A/B 盲批评的抽象结果、各角色元数据、练习稿哈希及 R2 回执；原著全文与草稿不长期保存。**未进行新一轮独立人类文学评价、未确认 90% 门槛、第二窗口仍锁定**。用户此前要求**本轮作品评分与原因分析留到下次一起做**，因此本次交接只记模型调用与 R2 事实，**不得猜出任何文学数值或自行宣称 WF 变好**。

### 本轮根因和代码改动

- 前一轮 [#38913593019](https://github.com/66tyu55/WriterForge/actions/runs/38913593019) 最终 **`completed/failure`**：Flash规划成功（148可见字符）；GLM第一次写作成功（1127可见字符），第二次写作请求触发 `DISCOVERY_NETWORK_FAILED`，共3次API调用。失败证据已存私有R2 SHA256 `1e50ae50b1c1818a853268269fd1be184b30de4317beeb3ae89ea2d2482160ab`，不能称它是文学质量不及格，因为没有第二稿/批评。
- `writerforge/reverse_discovery_models.py` 已区分 `DISCOVERY_TIMEOUT`、`DISCOVERY_CONNECTION_FAILED` 与 HTTP 状态码；仅对超时/连接失败/429/502/503/504 允许**最多一次传输重试**，重试仍计入总7次请求与Token预留，成功修复“网络异常整个学习丢失”的主阻碍；HTTP401等不重放。
- `tests/test_v28_discovery_models.py` 增补网络超时预算/永久失败/401回归；全量 [GitHub Tests #38918418959](https://github.com/66tyu55/WriterForge/actions/runs/38918418959) `success`。
- 当前运行器的 `.github/workflows/v28-flash-glm53-network-retry-once.yml` 为**仅首次新文件 push 触发**的单次实跑；它不会因为后续普通 push 自动扣费。核心入口 `scripts/run_wudong_discovery_ab.py` 和模型适配 `writerforge/reverse_discovery_models.py`；后续付费动作仍必须有明确用户指示。此前 P0 已解决原著事实/写作手法污染，预置文学机制经 HOST enum 验证，A/B 长度差>15%拒评。前面的多版本 v1/v2/v3 实测凭证都保留，不要覆盖历史。

### 新聊天首项工作（严格顺序，避免重复付费）

1. 先读取本文件 `docs/CURRENT_HANDOFF.md` 末尾本节，核实 R2 新快照 SHA `a2882f770e76fee4f4cedffb219d919a1a169fd731832b3d2de24e105c6a0282`，**只读地抽取 baseline/skill 的数字分项、长度、宿主机制ID、各评审短理由**；对短理由先检查是否与原文长段重合，日志不展示原著和完整草稿。**先分析已有证据，不要重新调用付费模型**。
2. 把本次跨厂商 Flash/GLM5.3 同题A/B与此前两个 v1/v3 版本比较；注意跨不同 Writer 模型的数字评分不可简单当作 WF 真正进步，要分别检验模型差异、是否等长、方法是否真迁移、读者/批评是否独立，不能偷换“90%大师水平”概念。
3. 依据真实错误写入有界 `faults/forgetting` 候选核心，与原著专名事实和未审核叙事假说保持隔离。技术改动先离线回归，再决定是否值得花额度复测；不得跳过第一段门槛到第二段、不得反复从第一章开头重新归档原著。
4. 继续目标：人物为什么以某种方式感知世界、作者为何以某种次序和视角呈现；“临摹快读→独立写→原著对比→拆失误/遗忘/假说→R2保留核心、销毁正文→闭卷重测→两个相邻窗口合并→多种独立场景3→6→9证据去重晋级”。**核心是真正改善原创写作的技能，非原著模仿分数或表面工程通过。**

如果用户开新对话只说“继续”，按上述 1→2→3 顺序落实，未经进一步指示不要启动付费任务。


## 28. 【修复分支交接，尚未合并】V28 Flash + GLM-5.3 第一窗口离线复盘（2026-10-16）

本节记录 [PR #43](https://github.com/66tyu55/WriterForge/pull/43) 中的离线修复，并不代表 main 已部署，或新候选已上传私有 R2。后续继续时先看 PR 的合并和最新 Actions 状态，不得将工程测试通过写成文学晋级。

- 旧训练数据保持原状：v1 V4 Pro baseline 86 / WF 84（原著情节污染、字数差49.4%）；v3 V4 Pro 86 / 76（已有原著来源隔离和长度闸门）；v4 Flash+GLM-5.3 86 / 89（精确平均86.2 / 89.8、字数1050 / 1183，差11.24%）。v4五维基线 88/82/85/90/86、WF 92/89/87/91/90。存在模型替换、内容随机和宿主预置机制变更，无法进行单因素归因。
- 真实训练 Actions #38918557675 completed/success；只读复评 #38919228502 success；原 R2 摘要不可变 SHA256 a2882f770e76fee4f4cedffb219d919a1a169fd731832b3d2de24e105c6a0282；本轮修复未启动新收费推理。
- 已发现 v4 的 Critic 虽匿名收到两篇稿，但同时看到原著 source_context，且与 Planner 共用 Flash 评审模型。修复后的 Critic 只见公共任务及匿名稿；18字符及以上直接重合评论会脱敏。新回执显式标记未向 Critic 发送原著；**旧 v4 绝不回填此标记，不能追称历史评审已独立于原著**。
- 新增 writerforge/reverse_ab_candidates.py：现存已保存摘要报告可在验证实际内容SHA、字数闸门、技术ID白名单和来源隔离后转成有界 fault/forgetting 候选。新 SQLite 最多128条摘要、以真实 receipt SHA 去重；不存原著、草稿、模型自由解释，也绝不允许从候选自动晋级。低于90的维度仅记参考差距；遗忘 NOT_TESTED、闭卷迁移0、真人审评未做。
- 新增 scripts/import_v28_r2_candidates.py：只读取旧私有 R2 抽象 JSON 回执，校验旧 SHA，生成新内容寻址候选报告，写入新的私有 R2 key 并全新 GET 核验；不下载原著、不调用语言模型。仅手动运行的 .github/workflows/v28-r2-offline-candidates-manual.yml 提供入口，没有 Discovery Secret。**当前只完成代码和合成回归，私有 R2 新候选回填尚未执行。**
- 修复详情：docs/V28_FLASH_GLM53_OFFLINE_ROOT_FIX_20261016.md。早期 PR 全量 Actions #38923300833 的381项测试已 success；合并前以最新 PR commit 的 Actions 最终报告为准。分支提交/CI 不能替代文学评价。
- 模型仍固定 Planner/Critic deepseek-v4-flash-0731、Writer glm-5.3；Discovery Secret 名 DISCOVERY__API__KEY（双下划线）；共享50k预约输出Token、最多7调用的约束未修改。
- **第一窗口 NOT_PASSED；第二窗口 LOCKED；90% 文学质量晋级未验证；3→6→9闭卷样本、两相邻窗口合并、独立真人评审与50部完整作品总评都没有完成。**

继续先查 PR #43 测试与合并状态，必要时复核手动候选回填的零模型调用属性。不要重新训练已保存的 v4，也不要为了新一轮分数提前开启第二窗口。


## 29. 【最新真实训练与分析交接】基准30显示标尺 + Flash/GLM-5.3 新场景 V5 + 私有 R2 失败候选（2026-10-16）

本节更新第27、28节的 pending。用户明确提出：“第一：把无技能基准分数降至30分；第二：继续训练，然后这次训练完毕分析。”本次要求**已真正执行**，不是只制定计划。完整文学分析见 [V28_FLASH_GLM53_TRANSFER30_V5_REAL_REVIEW_20261016.md](V28_FLASH_GLM53_TRANSFER30_V5_REAL_REVIEW_20261016.md)。

### 30 分新标尺（禁止冒充模型真实评分）

- `writerforge/reverse_score_scale.py` 把每次新 A/B **显示用的无技能分数锚定30.0**，把原始两稿分数同加一个位移，保留真正增量。**原始模型分数永久并行保存，30不是模型真的给出的质量分，也不是晋级闸门。**
- 本轮真实模型五项无技能分85/82/80/84/83，实际均分 **82.8**；WF分92/90/88/91/89，实际均分 **90.0**。真实分差 **+7.2**。换算成用户新显示基准：**30.0 → 37.2**，而非凭空“30→90”。
- 稿长无技能1188字符、增强1297字符，差 **8.4%**，通过15%闸门。新原创题为悬崖驿站夜班索道维护，未复用此前井水题，仍用同一私有原著第一章第一连续窗口。Critic 只见同题匿名两稿，**新版本不再给Critic原著 source_context**。

### 真实模型运行、消耗及回读

- [V5 one-shot Actions #38925236833](https://github.com/66tyu55/WriterForge/actions/runs/38925236833) 完整 **success**，每轮只有4次真实API：Flash Planner1 + GLM-5.3 Writer2 + Flash Critic1；输入4819、输出13803，总计 **18622 tokens**；预留输出36500，单轮硬顶50000和7次请求未变。
- 新私有 R2 不可变完整摘要回执 SHA256 **`b41e4a74895898f545af4f5424ac554cbe02215ba3f122715e8d09d38072aa66`**；脚本回读并独立只读审计成功。草稿、原著全文未持久化到公开repo/R2报告。
- 跨旧版本分差：v1 V4 Pro -2.2（原著剧情污染、长短不等），v3 V4 Pro 约-10（同样GOAL+COST），v4 GLM-5.3 +3.6（COST+EMOTIONAL，Critic仍见原著），**v5 GLM-5.3 +7.2（GOAL+COST、Critic不见原著）**。不同模型/不同题/单模型审评的数值不可作单因子归因。两次GLM正差是初步重复迹象，非独立真人验证。
- 五项弱项：信息释放 **88**（含糊结尾是否有可回查线索仍需测试），语言 **89**（尚未有读者复评）；本轮实际选中两个**宿主预置**操作 `GOAL_FILTERS_ATTENTION`、`COST_VISIBLE_IN_ACTION`，绝不可称作WF新发明的技能核心。

### 真实候选已经保存至私有R2（此次不是pending）

- [零模型费用的R2候选归档 #38926233485](https://github.com/66tyu55/WriterForge/actions/runs/38926233485) **completed/success**：从V5真实报告SHA全新GET→校验源和Critic隔离→仅抽取安全摘要→写入新内容寻址私有候选JSON→fresh GET校验。**0 次模型调用，0 次原著 blob下载**。
- 新候选不可变 SHA256：**`3ea44145b478cf71f720307ca7778eec6ad3d33f360448f78990aa1efd3e563e`**，保存2项低于参考90的文学维度候选和2项宿主预置机制ID，`forgetting=NOT_TESTED`，`human_review=NOT_PERFORMED`、`promotable=false`；不存原著、草稿、自由短评。历史R2原回执未被覆盖。
- 本轮修复 PR [#43](https://github.com/66tyu55/WriterForge/pull/43) 已 **squash merged** 到main，源评隔离、低长引文脱敏、faults/forgetting候选账本已真正落地。全量工程回归新增测试（查看新工作流结果）；不等于文学技能达到90%。

### 文学门闩（没有绕开）

**第一窗口 `NOT_PASSED`；第二窗口 `LOCKED`；真人独立审评缺失、闭卷迁移3→6→9未完成、相邻窗口合并未做、50部作品总评仍未满足。** 虽然本轮模型均分90.0，不得直接晋级。此处实验记录是prompt级生成与观察，不是模型参数训练。新用户明确授权之前不要重复新付费实验；没有额外训练自动运行。

**继续时**：先复核此节真实Actions和R2候选回执；集中处理信息释放的可验证线索/读者推断，以及语言句级自然度，检验机制在不同原创新场景的正反样本。不要用降标尺或反复刷同一第一窗口的分数制造成功。


## 30. 【最新实际交接】第2章新来源诊断、WF 实际回退与非破坏性底层修复（2026-10-16）

用户要求不再反复在第一章起点刷高分；换到后续内容固定同模型同任务观察WF是否骤降，同时修底层且不能让新内容毁掉原有功能。**本节是已真实执行的结果，非待运行计划。** 完整审阅 [V28_CHAPTER2_REGRESSION_ROOT_FIX_20261016.md](V28_CHAPTER2_REGRESSION_ROOT_FIX_20261016.md)。

- 采用《武动乾坤》同一钉住版本 SHA `86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28`，**不再用第一章**，在私有R2恢复后检查第1→2→3章真实章号；第2章正文3752字符，SHA `46acf29ea47e63b0a47a18413260a689bcaf9a9f1284338a2cebc4771428956e`。连续片段第一个1905、第二个1847字符，拼回完整第2章无跳段。[纯来源R2预检 #38927807149](https://github.com/66tyu55/WriterForge/actions/runs/38927807149) success，调用模型0次。章节切分只是物理安全边界，`semantic_boundary_verified=false`。
- [V6 真正4次付费模型A/B #38927958675](https://github.com/66tyu55/WriterForge/actions/runs/38927958675) completed/success；Planner/Critic仍 `deepseek-v4-flash-0731`、Writer仍 `glm-5.3`，**原创索道驿站任务原封不动**，输入4410 / 输出18379，总22789服务商报告tokens。V6私有R2抽象快照 SHA `cd6a9adef0647d52fb60bdf88103634220501cdca7a4d7113bdd2c3f3e781392`，fresh GET及评审原因审计 success。
- **第2章V6原始模型五维**：无技能88/82/85/90/86 → WF84/80/82/88/83，五项均负差 `-4,-2,-3,-2,-3`。五维平均 baseline **86.2**、WF **83.4**，组内差 **-2.8**；用户显示30标尺为 **30.0→27.2**。两稿长度1057和1125差6.04%，通过15%阈值。
- V5第1章同任务/模型原始baseline82.8、WF90.0、增益+7.2；V6第2章变成-2.8，**组内WF增益骤降10.0分**，WF自身均分下降6.6，而基线反而升3.4。两轮机制仍是同样宿主预置 `GOAL_FILTERS_ATTENTION + COST_VISIBLE_IN_ACTION`，说明**至少出现一次强烈上下文回退**；不能断言是换章节的单因果，单次随机生成、仅同一Critic及无独立真人意见仍有混杂。
- 模型理由提示五类缺陷：WF操作细节（粉笔线/湿圈/油痕）变清单，感知不自然；关键选择挂梯的动机只靠师父规矩，不足；悬念异常过多却无核心焦点；三更时间过渡生硬；动作语言较无技能乏力。这些是真实单模型短评，非可复核的全文人审。
- [R2 V5/V6 真实摘要双向比对及新候选归档 #38929089257](https://github.com/66tyu55/WriterForge/actions/runs/38929089257) success，**零模型调用**；两份历史原R2哈希核实后把退化分数和机制ID写入独立新内容寻址不可变候选 SHA **`563b5b28591fc38748f26f1dbc89d175c2b7d64802eda02b0247a91eac87ba6f`**。旧v5好例、v3坏例、v6坏例和R2原著都不覆盖。
- 实现：新增 `writerforge/reverse_later_window.py`（第2/3章源指纹/连续章号/两段无漏/线性有界读取）；`scripts/run_wudong_chapter2_diagnostic_v6.py`（独立前读实验、不放行课程）；`scripts/audit_v28_chapter2_v6_r2.py`（来源、匿名评审、模型评分与锁门审计）；`writerforge/reverse_cross_window_review.py`（A/B变化和逐维回退去重、模型角色/任务校验、候选隔离）；`scripts/import_v28_chapter2_regression_evidence_r2.py`（新私有不可变候选）。新增回归测试包含前版V5提示/模型身份不变、旧版第1章读取器兼容、缺章节/跳章节拒绝、R2摘要哈希、模型-only不晋级/候选去重。GitHub [全量 #38929224921](https://github.com/66tyu55/WriterForge/actions/runs/38929224921) **396 tests success**。
- 新代码会显式标明 `new_chapter_mechanisms_quarantined_pending_independent_review=true`（负面候选保护）；但目前尚无通用已审文学核心投入生产，也不能宣称新证据可自动升级/撤销正式Skill。已有候选保存只记录源码哈希、分数和禁止晋级，未存原文/草稿，不应重置历史。
- 真实底层尚未完结的文学功能：`parse_selections` 目前只验证证据ID存在，不能自动证实语义真正支持机制，且 Planner 必须从4项老技巧选择1-2项；下轮应支持**无可靠证据就弃权**、人物认知跨章已核实继承、候选上下文适用范围及真人/独立盲评。**此处不能谎称这些文学机制已经自动修好**。不要直接再刷新章或换模型、扩大Token来伪造质量提升。
- **保持全部正式门闩：第1窗口 NOT_PASSED，第2课程窗口 LOCKED、90%文学能力未独立验证、3→6→9非重复迁移证据未齐，50部作品总评要求不变。** 第2章只做隔离诊断前读，未以模型高分放行正式课程；本轮真实模型共4调用且没有追加第二次收费复测。

下次继续优先处理“机制无可靠证据也被强制选择”这类真正的语义底层漏洞，以及经验选择的禁用/回滚；不得覆盖原有反例和v5好例、不得让新章节的候选侵蚀旧功能。


## 31. 【最新交接 2026-10-17】随机三章压力测试、模型技术失败与非破坏性长度底层修复

本节为断线恢复后的实际结果。首读文件时先看本节及 [V28_RANDOM3_POST_DISCONNECT_FINAL_20261017.md](V28_RANDOM3_POST_DISCONNECT_FINAL_20261017.md)，不要重做原著R2归档、成功模型调用、随机选择或第二章旧实验。

- 用户授权至少3个随机章节诊断，在《武动乾坤》钉住的私有原著 SHA `86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28` 内，**事先用固定哈希规则选出第3、15、17章**，抽样身份SHA `1de5e123e70db078db63dd5cdab1230eab7ded135d101cfa2a3eb237179d3c54`，三章R2来源结构回读均通过 [#38997587245](https://github.com/66tyu55/WriterForge/actions/runs/38997587245)；不依新分数换章。
- **真实文学生成已评分成功2章**：[三章最初one-shot Actions #38997659758](https://github.com/66tyu55/WriterForge/actions/runs/38997659758)。第3章无技能原始均分76.6 vs WF86.2（+9.6，新显示坐标30→39.6），模型机制 GOAL_FILTERS_ATTENTION + WITHHOLD_CAUSE_SHOW_CLUE；R2完成回执SHA `e4555c234444371cbf24c5d8c4bd5e114ccfee8a0aeb32403ce501d7ddba2d07`。第15章首次技术失败，限制仅失败 job 重试后成功：无技能80.0 vs WF90.6（+10.6，新显示30→40.6）；机制 COST_VISIBLE_IN_ACTION + EMOTIONAL_TURN_WITH_EVIDENCE；R2 SHA `6169c11a24fa19de9afab7150c8973ed4d930d72c1fdf2d4fba640636910b8ef`。两章成功由 [私有R2零模型只读审计 #38998637174](https://github.com/66tyu55/WriterForge/actions/runs/38998637174) 验证：number_scored=2/all_three_scored=false。
- 第17章实际多次打到模型，但均**技术不合格、无合法原始五维评分**：V7最初连接/推理截断/预算失败R2 SHA `6fa81ad8f150d24522903688f61817489b7ed30755d091e60c44b869b8350086`；V7仅失败 job 的限定重试出现两次length且零可见正文，SHA `e038dc7cf07cc5d9b95ea99edbe93693b219cb8167a8604487e4bee947b4841e`。
- 验证网关兼容 GLM5.3 `reasoning_effort=low` 的**无原著小型真实探针 #38999272334** 成功。V8 [#38999364460](https://github.com/66tyu55/WriterForge/actions/runs/38999364460) 改为低思考后成功生成两稿 1964/1329字符，但差约32.3%不满足15%闸门，失败 SHA `74f78fd2583a9e66f570c77d3f06bd73aaabc352facc34f63af903cccdeeb473`；没有批评分数。
- V9 [#39000191094](https://github.com/66tyu55/WriterForge/actions/runs/39000191094) 在两组写作任务同时追加相同1100字符目标，两稿为1698/1433字符，差约15.6%，依旧**严格拒评**，失败 SHA `56f8a186a227dc01f26a1f85fbe7d1b46ab3063bc24d1e57e462223e675a48f6`。此前工作流首次被合成文本<300字的纯测试夹具阻断在付费前，修夹具后才发生上述一次真实模型尝试；不要把首次阻断算收费。
- **本轮三章确实都调用真实模型，但只有2章完成真正公平A/B审评；不能说3章已全部评分，也不能拿第17章技术失败宣称WF文笔下降。** 两组有效模型评分都为正，故“随机章节仍全面下降”的预设条件没有成立；第2章历史相对负分-2.8仍在，不得忽略。只有单个Flash Critic及少量样本，无稳定因果证明。
- 已有底层工程修复：在 `reverse_discovery_models.py` 增加对 GLM Writer 的可选、经无原著探针验证的low effort；在 `reverse_cloud_ab.py` 增加可选有限角色输出预算、同等 neutral `common_target_chars` 和**新可选 `symmetric_length_revision`**：首稿不等长时只对两组稿分别各做**一次**同目标的独立修订，不接触别组稿、原著剧情、不截稿、不补假文本；经过同样15%闸门和共享50k/7调用上限才允许给文学分。两个编辑机会须同时预留令牌；其可用性通过合成测试核对，但尚未用真实GLM长篇验证，不能虚构已修好真实文章长度。
- 原 `CloudABTrial.run` 旧参数及默认行为不变，新增的全部能力为 opt-in；已通过对照、机制白名单和旧源解析器兼容回归，历史V5、V6、V7及第17章失败R2内容寻址记录永不覆盖。文学语义学习“原著证据ID存在≠真实因果解释”仍是未完成能力，不能以控制输出长度代替文学技能改进。
- 工程最新测试应检查当前 main 最后一次 `WriterForge Tests` 的最终结论。报告 [V28_RANDOM3_POST_DISCONNECT_FINAL_20261017.md](V28_RANDOM3_POST_DISCONNECT_FINAL_20261017.md) 已保存到仓库。**禁止继续盲目收费重跑第17章**，先独立验证新对称修订算法，再征得用户明确的新付费试验指令。
- **保持第一窗口 NOT_PASSED、正式第二课程窗口 LOCKED、模型权重未更新、未通过真人独立文学评审/3→6→9/50部完整作品总评。** 用户显示的baseline 30不是模型真实评分或大师达标指标。



## 32. 【最新事实交接】三个随机**原创第一章题目**的真实完整 A/B：两正一负（2026-10-17）

**用户这次要求随机题目，而非再随机原著章节。** 以“安全聚落、夜间传说、少年意外滞留、诡异升级、逃跑、认知转折、悬念留白”为共同故事骨架，先独立创作六套自洽题目，`writerforge/random_original_openings.py` 以固定哈希seed预注册抽中 `copper_valley`（封矿峡谷）、`cedar_night`（古杉林）、`black_tide`（黑沙盐湾）。最终完整复盘见 [V28_THREE_RANDOM_ORIGINAL_FIRST_CHAPTERS_REAL_REVIEW_20261017.md](V28_THREE_RANDOM_ORIGINAL_FIRST_CHAPTERS_REAL_REVIEW_20261017.md)。

- 来源**固定而不换章**：同一份私有原著 `wudongqiankun` 钉住原文 SHA `86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28`，第3章第一个连续1132字符窗口 `96b6363d40be7b99d5635af1346da0c04e44556fc06e32d1aab04e419e4942fa`，只供 Planner 分析；Writer/Critic 不见原著情节。正式第1窗口仍 NOT_PASSED、第二课程窗口 LOCKED。
- [**真实三题 A/B Actions #39003570775**](https://github.com/66tyu55/WriterForge/actions/runs/39003570775) 三个任务及最后 R2 审计全部 **completed/success**；真实固定模型 Planner/Critic `deepseek-v4-flash-0731`、Writer `glm-5.3`；每题4次API，共 **12**。服务端报告总输入14464/输出9132，共23596 tokens，未把预算保留额冒充真实消耗。三组稿长差都 ≤15%，对称修订各0次，故本轮没发生补写反复收费。
- 三个不同题材原始模型评分：**封矿峡谷baseline69.0 vs WF86.6，+17.6**（稿长1422/1323）；**古杉林baseline86.2 vs WF78.8，-7.4**（1273/1142）；**黑沙盐湾baseline72.4 vs WF86.2，+13.8**（1499/1722）。三组均分基线75.87，WF83.87，真正均分差+8.0。用户30显示标尺分别30→47.6、30→22.6、30→43.8，不能将30伪称原始文学质量评分。
- 五维差额封矿谷 perception+16/causality+15/information+22/continuity+21/language+14；古杉林 **-8/-7/-7/-8/-7五维全降**；黑沙盐湾 +14/+15/+14/+18/+8。三组全部选用了**完全相同的宿主预置** `GOAL_FILTERS_ATTENTION`+`WITHHOLD_CAUSE_SHOW_CLUE`。说明跨不同原创新情境模型给出正负不一致，暂不能归因为某一技巧必然有害或有效，更不能由2/3正例“冲掉”一负例。
- 不可变私有 R2 真回执：
  - 封矿 `a6f1ddb22abab1635ca277fff659b8c44259229ab0c1f0065d18470a23be39f2`
  - 古杉 `8ef29fd600c5c6efbe295b95564408509e6d98a10bef4cf09f9bf9dfe12e45dc`
  - 黑沙 `5a630f2313e4e18104575bd0874ac38ec532c12b92dff6b91aacd632f06642d7`
  - **三组读回聚合新摘要 SHA `2b2aea9c6563b402d0795fc1812e09d5d066e56a4ab51be045ddeabaae00b55d`**。聚合只含数值、场景/文本SHA、角色与机制ID，旧实验与失败证据一律不覆盖。
- 主要真正缺点：代码只检验Planner选中技巧ID存在及引用的来源段落编号有效，不核验原文语义确实支持该技巧在**新的首章题材**中适用；并且总在四种预置技巧中强制选1–2项，尚非从作品自动学习并校准的文学规律。这是根因候选，未经独立真人全文审稿不能认定为已证实因果。绝对篇幅900-1300汉字仍经常没有严格遵守，尽管相对15%比较全部合格。
- 新增 `writerforge/reverse_story_context_evidence.py` + `tests/test_v28_story_context_evidence.py`：纯离线地验证真实R2后审计报告SHA，将三组正负模型观察**按 story_id / 创作任务SHA / 学习来源SHA**形成未审核候选；古杉林标记 `NEGATIVE_ALL_FIVE_NEEDS_INDEPENDENT_REVIEW`，另外两组 `MODEL_POSITIVE_UNVERIFIED`。**不改写生产Writer提示、不禁用整套技巧、不晋级、不覆盖历史快照。** 三组真实聚合R2已存储；此派生候选另存R2的操作**未执行**，不能声称额外云端归档已发生。回归见最新 WriterForge Tests。
- **本次确实完成了3个原创题目的模型评分，但并未保存6篇完整练习稿供真人逐字盲评**。临时稿被删除，只留不可变文本SHA和短评，因此不能用本轮3个模型评分假称人类认可90%文学能力。未来若须真人细评，必须先制定私有、限量、哈希锁定的练习稿保留协议并再生新稿，不能恢复旧稿。
- 后续策略：先验证“原著语义支持→创作任务适用→具体机制动作→读者可回查线索”的四层证据链；保留古杉林反例，跨新题目比较机制适用条件，避免仅追均分。**不自动重复付费训练；不放行第二课程窗口。**



## 33. 【最新交接 V29 · 2026-10-17】六阶段改进计划获准：已实际修复语义证据协议、原创稿加密留证、真实R2上下文负例回填

用户在V28三题随机原创首章（封矿+17.6，古杉-7.4五维全负，黑沙+13.8；平均+8.0）的完整复盘后确认“可以---允许计划”，授权此前提出的修复计划。**本轮已实际修改GitHub代码、测试、私有R2，未重新调用付费文学模型**；并非六阶段全部已被文学实践验收。完整详述： [V29_SEMANTIC_PRIVATE_DRAFT_REPAIR_20261017.md](V29_SEMANTIC_PRIVATE_DRAFT_REPAIR_20261017.md)。

- **P0语义适配的可执行协议**：新模块 `writerforge/reverse_semantic_evidence.py`，新 opt-in `CloudABTrial(...,evidence_first=True,semantic_evidence_first=True)`。Planner现在必须给出来源中实际存在的12-48字符span、所属段落、角色已知未知、局部因果、新创作题目适合程度、误用风险和支持/弃权状态。结构不完整/原文证据杜撰直接拒绝；明确风险则Writer之前弃权以节省调用。只将原有HOST技巧ID送Writer，绝不送原著文本、解释和专名。**本层仅证明原句确存在，不能证明模型语义理解正确，依然标记 `independent_semantic_review=NOT_PERFORMED`**；默认旧训练行为不变。
- **P1未来原创稿私有、可复评**：`writerforge/reverse_private_draft_evidence.py` 及 `pyproject.toml` 新增可选 `[evidence]` 依赖 `cryptography`。显式 `manuscript_sink=PrivateDraftEvidenceVault(...)` 时，仅在有效的匿名Critic和15%相对稿长闸门完成后，才将本次**两篇原创稿**以 AES-256-GCM、来源/任务AAD绑定加密写入私有 `writerforge-private-library` R2，内容寻址SHA + fresh GET；报告仅附密文哈希及到期信息，无小说明文。最大保留14天、默认7天，超过时间拒绝read；**R2对象不自动删除，需要独立的显式到期清理操作**。
- 此加密保存**必须另行配置独立随机32字节base64密钥 `WF_PRIVATE_DRAFT_KEY_B64`**；当前未设置/未使用此密钥、没有在真实R2上传新草稿。不能将已有R2 access secret当作该密钥，不能在public GitHub上保存。此前V28六篇临时稿已销毁，无法复原。默认 `CloudABTrial` 仍不保留任何草稿。
- **逐句缺陷标注基础**：新增 `writerforge/reverse_draft_review_marks.py`，0基起止字符区间+五维+错误种类+修改想法，最多32条；导出的只有span/说明哈希和长度位置，不泄露明文，不把未经认证的人/模型申明当作真人审评。尚未发生真实独立评审。
- **旧候选账本兼容**：`writerforge/reverse_ab_candidates.py` 现在只允许来源、任务及两篇稿SHA都与加密R2回执一致的未来留存证据；普通旧报告的 `drafts_retained=False` 不变。伪造密文回执/缺key fail closed，仍不自动晋级。
- **真实R2上实际完成零付费负例归档**：[一次性回填Actions #39005416238](https://github.com/66tyu55/WriterForge/actions/runs/39005416238) completed/success，源码三题原聚合SHA `2b2aea9c6563b402d0795fc1812e09d5d066e56a4ab51be045ddeabaae00b55d` fresh GET后，写入新不可变正反候选 SHA **`63cde6bacd51f7c655ec4eb6e6ccdab7e96c54c9f507512dfbfeaba73cf7d60f`**。内容只有封矿+17.6、古杉-7.4五维全负、黑沙+13.8、原始稿/来源 SHA 和宿主机制ID；`new_rules_promoted=false`；旧V28不可变凭证、正例及失败均未覆盖；真实模型调用0次，原著或旧草稿未下载。
- 回归测试：`tests/test_v29_semantic_evidence.py`、`test_v29_private_draft_evidence.py`、`test_v29_draft_review_marks.py`、`test_v29_original_context_r2_import.py` 及旧V28测试。专门的**真实AES加密/错误密钥解密/到期删除/旧账本兼容**零模型测试 [#39005569114](https://github.com/66tyu55/WriterForge/actions/runs/39005569114) **completed/success**；请复核最新 `WriterForge Tests` 全量状态/数量，不要把合成测试成功当成文学质量90%。
- **尚未完成**：不同模型/人类的独立原文-情境意义审核（目前只验证源span存在和解释字段完整）；实际带独立key的真实稿加密留存和真人逐句盲评；将一条“已确认古杉林为什么失败”的机制改进真正写入正式创作调度；3→6→9独立场景、50完整作品文学毕业条件。不能据此声称WF文学能力得到真提升。
- **严格锁门**：第一课程窗口 `NOT_PASSED`，第二课程窗口 `LOCKED`；不得伪造30基准原始得分或拿模型90分突破真人验证闸门。未经新的实验指示不要重新付费刷题。



## 34. 【最新 2026-10-17】新版WF与旧版WF：三题真盲测验证完成，但尚不能宣称文学能力已经进步

用户明确委托自主制定改进方案，并要求实测“WF到底进步了吗”。**已经实际执行真实模型对照，得出不取悦人的混合结果**。详见 [V29_REAL_OLD_NEW_SEMANTIC_HOLDOUT_FINAL_20261017.md](V29_REAL_OLD_NEW_SEMANTIC_HOLDOUT_FINAL_20261017.md)；提前预注册协议见 [V29_REAL_OLD_NEW_HOLDOUT_PRECOMMIT_20261017.md](V29_REAL_OLD_NEW_HOLDOUT_PRECOMMIT_20261017.md)。

- 一次性 SHA 按固定种子从5个**未参与之前改进的原创题目**抽中 `bridge_debt` 石桥旧债、`desert_well` 沙漠旧井、`lantern_town` 春汛灯牌。保持完全相同的钉住私有R2原著第3章第1连续窗口，Writer GLM-5.3/Planner和Critic Flash，首稿来源隔离，匿名 A/B，最多7调用/50k预留输出token每题；旧WF使用老机制选择器，新WF使用已实现的source_span精确原文引用+认知/因果/新任务适配/误用风险证据门槛。
- [第一次真实旧vs新 #39006533808](https://github.com/66tyu55/WriterForge/actions/runs/39006533808) 仅1个有效文学A/B：石桥旧债旧85.0 vs 新92.8、**+7.8**，新旧所选技巧不同（旧 GOAL+COST、新 GOAL+WITHHOLD），五维 +7/+7/+8/+8/+9；不可变R2回执 `8368176072491c04fb17dba6fa80d3590c9106a9fd3c43c7552e629da467d651`。另外沙漠和春汛两题初稿加各一次公平独立修订仍有长度差>15%，按规定**没有文学评分**，失败回执SHA `fac3bb0a6c64d7a80ff00543eb916edd45f909550891e1e69c31abe582bd73fc` / `6ec824bdbd3c368424ec8efa7baad5bbc1eb1427f0cc6d05da24df08f8b562c2`，不能把未评分当成低分。
- 修复比较协议而**没有修改文学分数、放宽15%闸门或裁剪稿**：`writerforge/v29_old_new_trial.py` 改为有界 `LengthUnscorable`（只记录双方首稿/修订后字符数与差比）和对称编辑器给每稿自身实际字符数、距共同1080目标的字数差，不见对方草稿。保护性测试通过。
- [只重试失败slot 1/2 #39007227522](https://github.com/66tyu55/WriterForge/actions/runs/39007227522) 完整 success，slot0不重复写；R2新独立前缀、两题仍同题同模型匿名盲评，最终 **沙漠旧井旧87.2 vs 新82.2 = -5.0（五维-4/-8/-5/-4/-4，旧GOAL+WITHHOLD、新GOAL+COST）**，SHA `827c6ccf7dbe5b739f8dff02599b69758cb6d5ecfef9362edd094af550c0bb9f`；**春汛灯牌旧82.8 vs 新89.0 = +6.2（五维+4/+8/+6/+7/+6），但新旧都选GOAL+WITHHOLD**，说明这个正分差不能归因机制选择改善，SHA `3620cf259aa2a458c36367371f9209f6270cf3132cc98fa0cfaec2f134778864`。
- **三题均真正有原始模型五维评分**，三题新版减旧版+7.8/-5.0/+6.2，**均值+3.0**。此3题slot0与技术恢复的slot1/2编辑提示协议有区别，真实聚合 `49ae267ebbc15be5f0350015ad610f994be277339471c4e72f27792d7f37683e` 标记 `mixed_length_protocol_between_slot0_and_recovery_slots=true`、`causal_improvement_proven=false`。Planner/Critic都是同一个Flash模型且缺真正人类全文评审，不能以+3.0声称WF稳定文学能力进步。此次两次实际模型运行调用：17+10=**27**，失败模型消耗也计数。
- 真实零付费只读模型短评 [#39007323924](https://github.com/66tyu55/WriterForge/actions/runs/39007323924) 说明：石桥新版更用早先的衣物/腕布细节自然揭示旧债；沙漠新版对行动代价描写并未弥补结尾蹄印/青苔线索与前文的脱节；春汛五维相对较好但机制完全一样，无法归因。均为模型点评假设，不是独立人审。
- 新增 `writerforge/v29_semantic_regression_candidates.py` 将每题按任务SHA/来源SHA/选择技巧/实际分差5维/真实R2回执分隔为 `POSITIVE_CHANGED_MECHANISMS_UNVERIFIED`、`TASK_SCOPED_ALL_FIVE_REGRESSION_CANDIDATE`、`POSITIVE_BUT_SAME_MECHANISMS_NOT_CAUSAL`。不能据一正全局升级机制、也不因一负删旧机制。
- [私有R2真实零模型候选回填 #39007504129](https://github.com/66tyu55/WriterForge/actions/runs/39007504129) success，从已保存的真三题SHA快照fresh GET后新增不可变候选SHA **`bcf5be72abe50d1076653d7211f77df5e941fb3e8213466cdef45c0d0d440f49`**。历史正例、负例、原著和失败均不覆盖；额外模型调用0。
- **核心结论：尚未证明WF已稳定进步**。这次比较的是“旧Planner vs 新语义Planner即席挑选四项宿主预置技巧”，并不是从中国文学原著中学出、独立审核、以学习库保存后在创作阶段闭卷迁移的真正完整文学技能。当前下一步须分离学习/创作阶段、独立语义证据审核与严格跨题回归，而非加长提示词或无止境刷同一章。
- 尚未提升正式Skill、无模型权重更新、真实加密稿留存另需独立Secret配置。**第一课程窗口NOT_PASSED、第二课程窗口LOCKED、文学90%真人独立审评/3→6→9和50完整作品门闩未解。** 此轮已进行两次有硬上限授权付费试验；没有接续第三次收费训练，优先验收新证据。


## 35. 【最新V30执行交接 2026-10-17】停止用平均分偏袒WF：失败优先真实R2证据、评价偏差治理

用户明确要求：“为什么平均分数---不要偏向WF--让他接受真实缺点---还是先列出计划--执行”。先预注册具体计划 [V30_BIAS_FREE_FAILURE_FIRST_PLAN_20261017.md](V30_BIAS_FREE_FAILURE_FIRST_PLAN_20261017.md)，**本轮已真实修改GitHub并执行零付费R2审计**；完整缺点报告 [V30_FAILURE_FIRST_REAL_AUDIT_20261017.md](V30_FAILURE_FIRST_REAL_AUDIT_20261017.md)。

- **拒绝平均数掩盖缺点**：历史V29旧WF vs 新WF +7.8/-5.0/+6.2，均值+3.0仅为描述统计，不能作晋级/闭卷文学能力提高证据。石桥+7.8是换技巧后正向模型候选，尚未独立验证；沙漠-5.0 **五维全负**（感知-4、因果-8、信息-5、连续-4、语言-4），新版GOAL+COST代替旧GOAL+WITHHOLD的上下文适用性存疑，应作为独立严重回退；春汛+6.2两版本技巧完全相同，不能归因“新版机制选择器”。
- **额外客观缺陷**：3个A/B任务中有**2个任务新旧两稿都未达到共同1080字符±8%目标**（石桥1238/1318，春汛1394/1401）；旧15%“相对稿长公平”不等于遵守题目长度要求，现有 V30 各题独立列出绝对稿长违约。上一轮第一次2/3题因篇幅差被拒评，后做协议变更恢复；别把两次运行合起来包装成3题完全同协议。真正全文未留存，无法给旧稿做真人复核。
- **审评本身并非客观真值**：Planner/Critic均用Flash，二者是相同模型；虽Critic不见原著和版本标签，但仍存在共模审美、评分噪声、A/B顺序等偏差；一个模型即使平均90也不能宣称能力90。既往V28第2章-2.8及原创古杉-7.4等负例保留，不跨不同协议简单求总平均或硬因果归因。
- 新增 `writerforge/v30_failure_first.py`：只接受SHA校验的R2原聚合数据，按题保存新旧机制/五维负差/稿长/个人回执，**一题五维全负阻断总体技能晋级**；同机制涨分不计入机制选择进步。负分与其他题正分不能互相抵消。不得自动更改任何Writer正式规则。新增 `tests/test_v30_failure_first_adversarial.py`、`tests/test_v30_failure_first_r2.py` 专门防平均灌水、漏缺点、伪造分数和伪同机制。
- [**真实私有R2 V30失败优先审计 #39008909781**](https://github.com/66tyu55/WriterForge/actions/runs/39008909781) completed/success：对实际V29聚合SHA `49ae267ebbc15be5f0350015ad610f994be277339471c4e72f27792d7f37683e` fresh GET后创建独立新不可变记录 SHA **`d55899906ab69450e58cc746cf44d17602736d75029c5d80045328015213c894`**；真结果1严重回退5个负向维度、1同机制正例剔除选择器功劳、2题绝对篇幅违规；最终状态 `MODEL_RATED_REGRESSION_PRESENT_NO_PROMOTION`、`stable_literary_progress_proven=false`。审计本身0模型调用；旧分/旧R2完全不覆盖。
- 增加未来多评审去偏协议 `writerforge/v30_blind_reviewer_gate.py` 和 `tests/test_v30_blind_reviewer_gate.py`：两名评论模型须与Planner/Writer及彼此不同，必须A/B匿名标签交换，互相矛盾的负评绝不能均分抵消，双模型同意仍不等于独立真人文学审评。**只是下一轮接口与合成测试；历史已销毁六篇新旧稿无法真实双审**，不得声称已经用了两个模型给原稿重新评分。
- 工程最终全量回归以最新 `WriterForge Tests` 实际完成为准。此次只改评分证据/审计/未来评审门闩，不为漂亮分数再付费刷题。既有 first window `NOT_PASSED`、second `LOCKED`、文学人审不达标以及50完整作品要求不变。
- **下轮正确重点**：实现将学习库的因果/人物知识正确抽象并复核，再让创作调用有独立证据支持的技能；经独立真人或不同模型对**同稿**复评，跨6→9新题先通过负例回归与绝对长度/因果/伏笔闸门。不能把提交更多提示词/运行更多模型/测试数量增加理解为真正写作能力成长。


## 36. 【最新交接 V32 · 2026-10-17】用户亲自指定考官出题、WF学生作答、不作弊；真考试3题但0个有效文学成绩

用户在WF自主学习V31只真实完成2/3轮后强调：“哎呀--死脑筋----题目--你来随机搞几个--把WF当成学生---你是考官--不允许作弊--开始”。立即冻结 [V32_EXAMINER_PRECOMMIT_20261017.md](V32_EXAMINER_PRECOMMIT_20261017.md)，执行完备复盘 [V32_REAL_EXAMINER_NO_CHEATING_RESULTS_20261017.md](V32_REAL_EXAMINER_NO_CHEATING_RESULTS_20261017.md)。本轮**不许考试中由WF自己出题，也不许给自己考试打分，考后不以失败为理由偷偷换题/重复付费**。

- 六题原考官原创题库 `writerforge/v32_exam_bank.py`，提前 SHA(seed:topic_id) 抽3道：`pottery_market` 陶镇青瓷误会、`horse_school` 马场马鞍扣、`canal_doctor` 运河问诊，预注册manifest SHA `bb6a6fb13d9abbc94fac57102abba15ad79c942a1af9daedece9f2c5c80e65df`。不重用V28/29故事题目。
- 考生不是新发明的WF：从私有R2精确重读V31第一轮真实自学规则快照SHA `cd9cfa1d6413ed84bb4d3bb18c9a77d873666df95cbcd5898d4745cfeb2e3c7c`，第二轮SHA `fbb06fc6a53d0708b99b813eeb4cd9c96d1152413b4880d69ddf0ad294e6b555`，严格校验第二轮继承同一实验记忆且未自主产生新规则。每题一份GLM5.3无记忆稿vs一份加载唯一真实实验记忆的GLM5.3稿；无原著进入考场、不得自学新规则或看对手稿。
- 一次性真实 [Actions #39012732775](https://github.com/66tyu55/WriterForge/actions/runs/39012732775) 三题尝试、只读最终汇总**completed/success（审计完成）**：slot0生成两稿后长度 897/1172差23.46%>15%强制拒评，私有成功回执SHA `2d794d43ffc9c710b4b02310194614933b00f451c0a6351441f362b7a9278902`；slot1/2虽完成作文但两个不同评阅模型阶段未满足冻结JSON评语格式，分别失败代码 `EXAM_GRADER_REQUIRED_JSON_SCHEMA`，失败SHA `fec02bed409db5e4bbf1f3eb311002a7d6fae3bf69a168354f5f894f99437f1a` / `b6863ff80f3c81e905a6f6af41cd4bc167ca78f08b1eb3bb9c37f5625f34b92e`，两题各4次请求。slot0仅2次writer请求，共10次实际预留模型API请求（可能计费）。
- 设计的评阅者是DeepSeek-V4-Pro和MiniMax-M3，两个模型彼此不同、均不等于WF内部Flash Planner/GLM5.3 Writer，匿名A/B二人顺序交换，不能接触WF实验规则或学习过程。但**没有任一题取得2个JSON结构通过的真实文学模型评语**，不得宣称真正完成客观阅卷，更不要将评分失败定性为WF文笔差。
- 最终真实私有R2零模型汇总 `two_grader_valid_trials=0`，`all_exams_consensus_positive=false`，`literary_skill_promotion=false`，3试卷0有效成绩；工程预检505项测试通过。正文原作文没有长期保留，只存哈希、小型摘要和错误码；用户若要求人工文学逐句评测需要下批新题、提前授权加密存稿。旧试卷无法补读。
- **真实判定**：V31“自己提炼并持久记忆1条实验规则”在V32考场被固定加载，但**没有证据可证明该规则提升文学水平**。slot0相对字数偏差属于写作协议质量问题，slot1/2评阅JSON不合格属于考试基础设施问题，应分别修复，不得求平均凑0/正分。失败不等于零分。
- 后续优先考官端先进行真实网关**无小说小探针**修复格式可靠性，学员端绝对/相对篇幅控制；然后**全新预注册题目**进行同模型有/无记忆公平测试，保留负例、不加训学员作弊。正式 first `NOT_PASSED`, second `LOCKED`, 官方文学核心未晋级，不能用505项工程测试代替文学评分。



## 37. 【最新V33/V34 2026-10-17】修复WF指定字数与MiniMax长文JSON，真实新题同时跑通；但记忆五维全负

用户明确允许“可以---修补--必须控制WF指定的输出长度--然后json格式问题--一直没有处理--这次一起解决”。最终完整来源及根因详见 [V34_LENGTH_AND_JSON_REAL_REPAIR_RESULTS_20261017.md](V34_LENGTH_AND_JSON_REAL_REPAIR_RESULTS_20261017.md)；预注册真实考卷见 [V34_FIXED_LENGTH_AND_MINIMAX_JSON_FINAL_PROBE_PRECOMMIT_20261017.md](V34_FIXED_LENGTH_AND_MINIMAX_JSON_FINAL_PROBE_PRECOMMIT_20261017.md)。

- **V33第一版真验证没有通过**。新题 `lake_ferry` 无记忆1036/WF1011字符，符合长度，但是Pro评分成功、MiniMax评分两次都结构非法（实际失败SHA `d6c7063023799cbea26159b28276c0a6eb9ff1e72b2f610b7c6279b1918ff7fb`）；`salt_festival` 初稿各一次对称重写之后无记忆1062/WF945，只差硬下限950五个字符仍按协议拒评，R2 `dc83b1c157a21fd9b86a8efe9a813ff6123dc3e209fb91d432dee0720ff33b3f`。不得将V33合成测试通过当作真实两题成功。
- **找到MiniMax JSON反复失败的事实原因**：完全无原著和小说正文的真实长文本测试 [#39015256753](https://github.com/66tyu55/WriterForge/actions/runs/39015256753) 检测到MiniMax将完整`B`的五维评分及`uncertainty`嵌入完整`A`五维对象中，整个顶层只有`A`。旧严格parser误判`GRADER_JSON_WRAPPER_UNSUPPORTED`。新`writerforge/v33_exam_contracts.py`只接受`A→B→uncertainty`此结构（或对称镜像）、所有五维评分/评语原样重排，不修改数值、不发明数据；其它缺维、含混、非法仍Fail-Closed，非法格式至多一次等题等稿等匿名位置的限额修正。修复后真实MiniMax长文本测试 [#39015460941](https://github.com/66tyu55/WriterForge/actions/runs/39015460941)仅1次请求取得`json_validation=VALID`。此前单独Pro+Mini小样本两模型均一次合格 [#39014463006](https://github.com/66tyu55/WriterForge/actions/runs/39014463006)；小样本不等于长文可靠。
- **真正输出长度硬门闩**：`writerforge/v33_balanced_writing.py` 对exam统一目标1120（含标点）、每稿绝对区间950–1300、相对≤15%。超范围或互相长度不公平→**双边各一次同条件自稿编辑**；新可选第二个对称编辑周期，两臂都只见自己刚生成文本与自己字数、至目标尚需加减的确切字符数，不见另一臂，绝不人工裁尾或塞标点。经过最多两轮仍不合格，拒评无分，不能靠平均分遮掩。业务层一般`CloudABTrial.run(... common_target_chars=N, absolute_char_bounds=(min,max), symmetric_length_revision=True)`额外接入通用字数硬门闩，明确指定时允许N至4500字符；默认历史接口行为不变。它不是保证语言模型天生每次都严格 obey，而是保证输出必须验证或Fail-Closed。
- **调用硬上限**：扩展的V34试卷最大10次模型请求、50k预约输出token：初稿2×7000+最多4次编辑×4300+两名不同评审最多4调用×4600=**49,600**；transport自身重试也计入硬预算，不会无上限收费。旧Discovery default7调用未变，提升到10仅显式opt-in。
- **完整真实修复验证成功**：[V34单道全新题真实端到端 #39015701423](https://github.com/66tyu55/WriterForge/actions/runs/39015701423) `completed/success`，从事先封存三题中抽中`dye_workshop` 蜡染作坊，不复考V32/V33旧失败题。WF自身真实V31 stage1/stage2冻结实验记忆与无记忆同一个GLM5.3 writer分别作答。初稿不合格→**双边各编辑一次，共两次编辑请求**，最终无记忆**1056**、WF记忆**1082**字符，950-1300绝对范围及15%相对差同时通过。两个不同阅卷模型DeepSeek V4 Pro/MiniMax M3 **都首次JSON即通过**，匿名A/B顺序交换、缺点分项分别保留。全流程仅**6个真实模型调用**（2 Writer初稿+2编辑+2 critic），新R2原报告SHA **`331663b6628b504bd59051d73c9d7c703c45b2012599109f4cdc50d5c5c46d81`**，只读独立R2审计`two_valid_grader_trials=1`、`user_goal_length_json_chain_fixed_in_real_runs=true`。原著正文和两篇练习全文不持久，历史R2/V32/V33失败快照都不覆盖。此次第一轮编辑已足够，不等于实际第二轮修订模型可靠性也经过真题验证。
- **文学能力并未同时成功**，必须保留这个结论：V34真正两名不同评论模型均认为WF带自学规则稿五维**全面落后于无记忆控制稿**。Pro 的（感知/因果/信息/连续/语言）差 `-6/-4/-5/-3/-6`；MiniMax M3差 `-6/-4/-10/-2/-5`。一题模型评价不具备统计因果、人类文学真值资格，但绝不能据此升级WF那条真实自学技巧，更不可拿通道技术成功冒称作家技能变强。两名评阅者原始分数与负例留私有R2，不相互平均抵销。学海正式晋级 `NOT_PASSED`、第二课程窗口 `LOCKED`。
- 新增重要回归：`tests/test_v33_exam_contracts.py`、`tests/test_v33_repair_e2e.py`、`tests/test_v34_complete_repair.py`、`tests/test_v34_general_absolute_length.py` 覆盖真实MiniMax已发现嵌套形态、缺漏/伪分数拒造、有限JSON重试、近边界945字二次公平校正、一般WF动态范围、不可改历史R2等。此节交接后应检查最新`WriterForge Tests`全量通过的最终结果。**单道V34真实通过，不代表未来每一篇都一次过**；禁止为提高WF成绩而重跑旧题。



## 38. 【最新交接V35 · 2026-10-17】《西遊記》真原文读→候选手法→考官出题→7角度写前决策→原稿/修订稿，分别存R2；原自审失败，追加严格引文补测成功

用户要求“这次训练西游记原著，要求WF完整记录思考、下笔分别保存；你当考官给题，分析从哪些角度思考和为什么用手法”。先提交 [V35_XIYOUJI_PREWRITE_TRACE_EXAM_PLAN_20261017.md](V35_XIYOUJI_PREWRITE_TRACE_EXAM_PLAN_20261017.md)，后真实执行：[V35_REAL_XIYOUJI_PREWRITE_TRACE_RESULTS_20261017.md](V35_REAL_XIYOUJI_PREWRITE_TRACE_RESULTS_20261017.md)。

- 本轮是**首次实际将局部真实原著阅读/写前明确决策/真实原创正文分别持久保存、可串联检查**，不是下载100回原著就谎称模型已熟读。既有私有R2 `xiyouji-23962`完整100回经过SHA/SQLite恢复，模型实读**第1回与第2回各前2000字符**。Source stage0 SHA `125f8ce4305991beacdcfbdf36708b55adc523d62780a7bbd4f02e2dab1063b7`。
- stage1 模型实际阅读后的源文短引文与人物认知/叙事功能有严格原文精确检查，SHA `3d7d951af61116b8bd68512f76bfb67654e7c7935c967171bccd8d0f7fdc12e8`；stage2源经验备选/使用或不用条件/为什么，SHA `c96c926c58481818538e2d8f5ed11b212394421ed21db6834cc2b30fed5d102e`。这些是**显式WF叙事决策文字**，不可称为真实不可见token级chain-of-thought、不能把quote存在等于语义正确。
- 考官预先独立设计3个完全原创第一章题目，SHA固定抽到`mountain_market`山镇女药童误认药材，直到stage2记录已写R2才把题目交给WF，不能看原著情节抄写。stage3**写前**决策记录7种角度 `goal/knowledge/causality/scene/sensory/dialogue/foreshadowing`，每种含选择/原因/舍弃方案/预期读者效果/来源lesson ID，单独锁定SHA `a268aa596cf3c98328eeeb785ea026d65ba666ca41a226ef3b023e50d6894895`。
- stage4原始GLM原创首章**904字符**、完整正文已存私有R2，SHA `9c3a671ed8c588019a0f46b0613641b59441282983bce4bb0882c20ebcfafe70`；stage5独立修订**1136字符**、完整修订稿额外保存，不覆盖原稿，SHA `605fc022f59a87e3eb4d199ed7ef0c9898c1ce52edfa03a2674a8db0d80d0acf`。WF writer**没有拿到西游记原文**。
- **真正失败保留**：[原版一次性workflow #39018112434](https://github.com/66tyu55/WriterForge/actions/runs/39018112434) completed/failure，第一轮stage6模型写后自查引用一段不在真实小说正文里的短句`RETROSPECT_QUOTE_NOT_IN_DRAFT`，只有stage0..5成功。原版7次模型API调用，不得说8阶段全成功，也不得将坏自查改成满意的假记录。源文阅读/初步分析/写前计划/原稿/修订稿都可在私有R2读取，原版坏模型自查仅留下失败码，raw响应未保存不可恢复（后续应先储存无效原始回复）。
- **只修复写后核查，完全不重做学习和写作**：[独立追加一轮 #39018718650](https://github.com/66tyu55/WriterForge/actions/runs/39018718650) completed/success。用stage3不可变写前决策和stage5冻结正文，考官程序从**真实正文**直接机械提取短句菜单，WF在其中选精确证据并解释计划与实际差别。2次模型API调用，追加记录包括未通过模型回复与复查记录，不触动原stage0..5；最终**4项实际原文引文通过**，新独立写后校验SHA **`412b6ceb09d8513c72d4df58d9792d483d5bb6b5b36a8ea955e74812afee595d`**、考官核验SHA **`910f2495624038194d7f020fd34eff4ccdf18033589ab70d137828d2152ab454`**。此成功是追加流程，不允许说原先错误没发生。
- 私有存储总共**9次模型API请求**（7首次+2补测），服务商结算与预留Token区分。由于用户要求“分别完整保存”，原著片段、WF读书观察、写前决策、两份原创全文、有效写后核查都存入现有R2私有桶**明文JSON对象**（仍有服务端存储权限管控，但未配置独立客户端AES密钥，**不能称端到端加密**）；公开Github日志只印SHA/长度/状态。若用户要在聊天里审阅全部正文，需要具备权限的安全查看/导出通道，不能发布到公共日志。
- 核心观察：**Wf确实能保存自己的写前决定并在之后创作**；但是“自我复盘时凭空引用”是真实的底层思考忠实性问题，此次机械摘取真实正文引文的追加补测在一篇文章上纠正了证据位置问题，仍无独立人评文学因果与技巧合理性。未升级Skill，第一文学正式窗口`NOT_PASSED`、第二`LOCKED`。
- 新模块 `writerforge/v35_xiyouji_exam.py`、`writerforge/v35_observable_trace.py`、`scripts/run_v35_xiyouji_decision_trace.py`、`scripts/recover_v35_afterdraft_only.py`，工程测试`tests/test_v35_xiyouji_observable.py`。后续打断点先审stage1原著观察→stage2抽象机理→stage3写前行动计划→stage4/5真实句子→追加写后4项引文，**不得只看模型自评高分、源码测试数或作文长度宣称已学会西游记文学手法**。


## 39. 【最新交接 V36 · 2026-10-17】真实《西遊記》学习迁移链路断点回放：只有L2伏笔手法进入写前构思，写后却没有核验这一项

用户V35连续学习、构思和写作试验因连接中断，指示“中断了--继续”。**本轮没有再付费模型训练，也没有篡改旧正文/写前决策**。新脚本 `scripts/debug_v36_xiyouji_learning_to_writing.py` 已对六个真实原始R2阶段（stage0–5）和独立追加的写后证据复盘/考官记录按**完整stage envelope SHA**重新GET，校验真正文章正文、来源索引、手法编号、预先冻结的写前原因及4条追加写后引文。详见 [V36_XIYOUJI_EXACT_SOURCE_LESSON_WRITING_TRACE_20261017.md](V36_XIYOUJI_EXACT_SOURCE_LESSON_WRITING_TRACE_20261017.md)。

- **关键发现**：源文第1/2回各2000字符已读并引用核验，文学观察4项，提炼待验证手法 **L1、L2 两条**；写前计划共7个角度`goal/knowledge/causality/scene/sensory/dialogue/foreshadowing`，**只有`foreshadowing`明确绑定L2（源阅读观察索引1），其余六项没有来源lesson关联**。WF后来追加的4项有效写后核查仅针对`goal/knowledge/causality/scene`，**完全未核验唯一声称采用西游记学习手法的`foreshadowing`**。真实证据状态 `SOURCE_LINKED_DECISIONS_NOT_CHECKED_IN_POSTWRITE`。绝不能把4个“真实存在的句子”误称4次文学技巧应用验证；也不能据此证明WF没有使用L2，只能证明尚未记录其实际效果。
- 原始904字，修订1136字，SHA与内容完全对齐；有**899字的原始文本处于两稿一致匹配块（约99.45%）**，新稿净增232字符。4个追加写后引用中的`causality`对应确切短句只在修订稿存在，而目标/知识/场景引用在原稿已有；“最初下笔 vs 修订后”不可混为一谈。
- **零模型真实R2审计**：[V36 #39020574772](https://github.com/66tyu55/WriterForge/actions/runs/39020574772) completed/success，创建私有不可变审计SHA **`8a2aca0810c22fbca8a01519a1b573f87ccf38ee6ee3b8decaddb33dc91b1328`**。只输出角度、SHA、字符位置与真假布尔，不泄漏原著、完整原创新稿、实际构思文字或私人密钥。
- **实际底层护栏**：`writerforge/v35_observable_trace.validate_after(...,required_lesson_angles={...})` 以可选参数新增对“写前绑定文学新课L1/L2的角度必须有对应写后正文引文”的校验，没有就`LEARNED_LESSON_PREWRITE_NOT_REVIEWED`；**旧实验原始写后失败和补测未被回写修改**，未来可选择强制启用。V36审计新字段`source_linked_prewrite_angles`、`source_linked_prewrite_angles_checked_after_drafting`避免平均掩盖学习手法漏检。只证明引用与流程，不证明文学因果已经独立验证。
- **用户可审阅完整内容的办法**：新增本地只读`scripts/export_v35_full_trace_private_local.py --output <新建的本地私有文件夹>`，在用户本人电脑配置R2权限后可**在公共GitHub仓库之外**导出源文实际阅读片段、原文观察、两条提炼手法、七项完整写前决策及原因/弃用方案、904字第一稿、1136字完整修改稿、追加写后复盘、考官审计和V36逐角度详情。程序明确拒绝GitHub Actions、git工作目录以及覆盖已有文件夹；不会在公共日志或仓库公开正文。此导出接口已实现并经离线安全单测，**没有运行用户本地导出，也没有客户端AES加密R2文本**。
- **后续最优先**：只针对这条 **L2伏笔手法** 做真正的写后对应引用及独立文学语义评价，不需要再读100回/刷三题/添加十个Skill；不许把WF写后理由冒充隐藏的模型推理。正式文学first `NOT_PASSED`，second `LOCKED`，V35原始失败永久保留。


## 40. 【V38 最新交接 2026-10-17】L2伏笔原始证据角色错位：WF自认铺垫R39，独立Pro把同句标记为回收

用户继续“继续”V37专项，要求严格通过原始《西游记》、提炼L2、写前计划、904字初稿和1136字修订稿找WF学习思考为何不可靠。本轮已经实际修改/测试GitHub底层、执行真实R2对照与**一次**受限模型写后自查，所有原稿、候选技能、写前记录和先前失败证据保留不变。完整核验：[V38_XIYOUJI_L2_CAUSAL_ROLE_CONFLICT_FINAL_20261017.md](V38_XIYOUJI_L2_CAUSAL_ROLE_CONFLICT_FINAL_20261017.md)，预注册目标 [V38_L2_TRANSFER_GATE_PLAN_20261017.md](V38_L2_TRANSFER_GATE_PLAN_20261017.md)。

- **关键修复：把源学习手法接入真正写后验证入口**：`writerforge/v35_observable_trace.validate_after(...,learned_lessons=...,lesson_transfer_claims=...)` 现在会调用 `writerforge/v38_lesson_transfer_bridge.verify_lesson_transfer_claims`。如果写前宣称使用源手法L2，就必须写后单独核验该手法对应的foreshadowing角度，提交真实存在、独一无二、位置先后正确的铺垫/回收正文短引文，以及人物知识边界、因果解释、适用不确定性；允许`NOT_APPLIED/UNCERTAIN`而不是强行编造。原本只查4个普通维度不能被认作L2成功。
- **真实历史负对照，0次模型调用**：[V38 #39024299243](https://github.com/66tyu55/WriterForge/actions/runs/39024299243) success，私有R2真实后审查询严格返回 `LEARNED_LESSON_PREWRITE_NOT_REVIEWED`，说明V35原始和追加的四个通用后审角度确实没有检查唯一来源绑定L2的伏笔。不可变新R2 SHA `97914f6c8442ff7d7884b6a1c6cfae8e6fb6924c421e8bf4d03a63535fa6ec13`，历史不改、不凭空补文学分。
- **原先冻结1136字作文的WF追加L2自审**：[V38 #39024752169](https://github.com/66tyu55/WriterForge/actions/runs/39024752169) success，**只新增1个付费Flash模型请求**，WF的答案`CLAIMED_APPLIED`，从考官机械生成的真实正文短句目录选两句；二者真实存在、唯一且先后正确，考官允许追加1个foreshadowing检查，不动历史四项检查、不动原先最大缺点/写前构思/初稿/修订稿。独立追加私有R2 SHA `a9d5d521b2e0adbeb416f9325b0adabaad408abb728bd978099effe328488a62`。**这是写后说法，不等于写前真正形成的思考，也不等于文学证明。**
- **真正定位的写作语义风险**：WF后补自认**伏笔铺垫为R39（全文79.93%）**、回收R43（89.35%）。但是之前独立DeepSeek Pro **完整有效模型评语**把R39列为**回收**候选而不是铺垫（它选的铺垫是R34/R35、约69/71%）；MiniMax原始模型也把R39列为回收候选、它选择的铺垫是R02/R29约2.5/58.5%，但MiniMax全文评审有`uncertainty=[]`、**不能当成完全有效第二票**。所以有至少一位结构完整的独立阅卷者与WF在**同一句真实小说文字到底是铺垫还是回收**发生具体冲突。两者都把WF的R43放入回收候选，但这仍不能证明伏笔文学效果。
- **真实零模型角色冲突交叉核对**：[V38 #39025097935](https://github.com/66tyu55/WriterForge/actions/runs/39025097935) completed/success，将实际WF自审与两位考官先前的句子编号对齐，分别记录完整考官和格式不完整考官的`setup_was_reviewer_payoff`而不误算两票；私有R2新审计SHA `e2ed24abc352daef678165de8bee5f7c283f5709cf3a23c9fe99b9a876aeb0db`。模型调用0次。历史V37d数值对照R2、V37c缺失字段均保持不变。
- **工程回归**：新 `writerforge/v38_lesson_transfer_bridge.py`、`writerforge/v37_foreshadowing_evidence_gate.py`、`scripts/append_v38_frozen_l2_selfcheck.py`、`scripts/audit_v38_actual_l2_gate.py`、`scripts/audit_v38_l2_student_vs_critics.py` 和新合成回归。最新全量 [#39025097922](https://github.com/66tyu55/WriterForge/actions/runs/39025097922) **568项通过**。只证明工程与证据链管线可靠，不能声称WF文学能力已改善。
- **底层故障真实定位**：R2保存和写前思考存在，原著阅读抽象手法未得到一致独立评价（Pro`FAITHFUL`、MiniMax`PARTIAL`）；自审以前可以跳过来源绑定的唯一新手法，现在严格拒绝；补上证据之后仍发现**“先后真实句子”在文学语义上被WF可能误认为“伏笔铺垫→回收”**，作者自报与独立评论者意见冲突。真正有待改进的是`前置线索/人物有限知识/行为决策/后续信息回收`的**语义角色和因果状态判断**。不要事后硬加“必须前50%铺垫”的万能阈值，也不允许靠重复试题给L2晋级。
- **下一步**：以这条角色冲突作为不可变负面经验进入实验候选区，设计未来WF创作时提前声明“线索出现→影响人物选择→后续回收”的自然因果链，盲评真稿验证。不得直接替WF改写L2或因一题负例全局删除它。正式文学学习first `NOT_PASSED`、second `LOCKED`，没有官方技能晋级或人类独立文学毕业验证。


## 41. 【2026-10-17 交接封存】当前真实进度V38；下一窗口不重复训练、先定位L2伏笔叙事角色混淆

用户在研究了V35原著学习、显式写前构思及V37的严格伏笔核验后明确要求“交接吧”。本节在此刻直接核实GitHub `main` 及实际Actions后封存，以便下一窗口**直接从第40/41节接手**。详细文学发现与证据见 [V38_XIYOUJI_L2_CAUSAL_ROLE_CONFLICT_FINAL_20261017.md](V38_XIYOUJI_L2_CAUSAL_ROLE_CONFLICT_FINAL_20261017.md)；前阶段真实证据参见第38、39节。**本次交接只更新文档，不发生新的付费模型调用，不重新生成原稿、复查评分或改写WF技巧。**

### A. 实际完成，不能冒称文学晋级

1. 真实公版中文《西游记》已存私有R2 `xiyouji-23962` 完整100回并可恢复；**V35模型实际阅读的是第一、二回各2000字符**，不是一次模型完整读完一百回。4条带原句的原文观察、2条未经独立证实的源学技巧`L1/L2`已SHA保存。
2. 考官预注册原创题 `mountain_market`（山镇女药童误认草药）；WF写前明确给出7个角度`goal/knowledge/causality/scene/sensory/dialogue/foreshadowing`，**只有`foreshadowing`绑定从原著得出的L2**。904字符原始第一稿、1136字符修订稿完整原文分别储于私有R2；写前记录先于正文已锁定，均不能回写。V35原始写后自查曾引用不存在的句子而失败；后续附加4条成功自查针对goal/knowledge/causality/scene，**仍漏掉真正引用L2的foreshadowing**。
3. 已实际在`writerforge/v35_observable_trace.validate_after`接入`writerforge/v38_lesson_transfer_bridge.py`：若写前明确关联新手法，写后必须覆盖其角度并附精确来源、前后可追溯正文引文、人物知识边界与因果解释；可以诚实返回`NOT_APPLIED/UNCERTAIN`，没有证据不予晋级。真历史负对照 [Actions #39024299243](https://github.com/66tyu55/WriterForge/actions/runs/39024299243) 返回`LEARNED_LESSON_PREWRITE_NOT_REVIEWED`，不可变私有R2 SHA `97914f6c8442ff7d7884b6a1c6cfae8e6fb6924c421e8bf4d03a63535fa6ec13`。
4. WF仅在**冻结的1136字符修订稿上**额外做了**一次**有界模型自查 [Actions #39024752169](https://github.com/66tyu55/WriterForge/actions/runs/39024752169)：它自报L2 `CLAIMED_APPLIED`，从真实文章选出R39(79.93%)作为“铺垫”、R43(89.35%)作为“回收”，字符串存在/唯一/顺序已核实；新追加R2 SHA `a9d5d521b2e0adbeb416f9325b0adabaad408abb728bd978099effe328488a62`。**不能把事后说明倒灌为写前真正思考，也不能说文学效果通过。**
5. 独立DeepSeek V4 Pro**结构完整的模型评语**把R39认作**回收**候选而非铺垫，认为更早的R34/R35(约69.19%/71.39%)承担铺垫；MiniMax原始意见也把R39认作回收，但因`uncertainty=[]`导致完整评审协议不合格，只能当参考线索。此前Pro原著L2抽象判`FAITHFUL`、MiniMax判`PARTIAL`，这进一步反映语义解释不稳定。真R2句子角色交叉核对 [#39025097935](https://github.com/66tyu55/WriterForge/actions/runs/39025097935) completed/success，SHA `e2ed24abc352daef678165de8bee5f7c283f5709cf3a23c9fe99b9a876aeb0db`；**跨模型观点分歧是观察，不是人类文学真值**。
6. 最新确认GitHub `main` **`c9664e1bf7de27f3fe63e1b3d30aa2f20e691922`** 对应 [WriterForge Tests #39025294257](https://github.com/66tyu55/WriterForge/actions/runs/39025294257) **completed/success，568 tests passed**。不能拿工程测试或自评说明WF文学能力已进步、正式学习通过或模型权重更新。

### B. 当前最可信的失败定位

- 不是R2“写入/读回失效”：真实来源、WF明确表示的构思、完整原稿和写后说明都有SHA、按时序存档。
- 真正值得修的是**“显式文学经验→在创作阶段规划前置线索→影响人物有限信息与行动→后续回收”之间的语义角色判断与因果验证**。仅找到两句实际存在、时间先后的文字，不足以证明“一句是真铺垫、下一句是真回收”。
- 之前审评接口亦曾发生JSON解释过长/不确定性数组等技术失败；历史完整有效与格式无效的评论必须分开使用，绝不能拼凑或平均成更有利WF的分数。
- 当前**只有一篇**真实文章的L2角色冲突，不能据此全局删除L2、给全部题材硬编码“前50%才算伏笔”，也不能宣称已经独立证明具体手法必然有害。

### C. 下一窗口唯一优先工作：源码和正文角色定位（不要先重训）

1. 先打开本文件第40/41节和完整 [V38真实复盘](V38_XIYOUJI_L2_CAUSAL_ROLE_CONFLICT_FINAL_20261017.md)，检查`main`状态；复用私有R2已存在的R39/R43自查和R34/R35/R37–R43独立考官回执，**不重新付费阅读西游记、改写904/1136字原稿或重复评分**。
2. 对真实冻结修订稿**只在私有环境中**检验具体伏笔因果：R39出现前，相关物件/线索是否已登场、人物当时实际知道什么、R39是否改变了人物目标或可作的决定、R43后来揭示的是R39还是更早细节。结论允许`铺垫`、`回收`、`重复提示`、`两种功能兼有`或`无法确认`，**不应预先强选一种**。
3. 对`writerforge/v38_lesson_transfer_bridge.py`的未来实验设计一个**人物知识状态与线索身份的时间序列记录**，让WF在写正文之前就明确规划“谁看到哪个线索→引发什么判断与行为→何时回收”，写完由同一稿真实句子核验，避免只靠写后即席解释。先纯合成/零模型单测，确保原有Skill和历史证据不被删除。
4. 若之后允许真实独立文学盲审，需先定义/保存审稿合同及严格预算，再使用**新的预注册题目**比较学习前后；旧稿用于故障剖析而非反复刷高分。任何仍不确定的文学判断单独归档，零晋级。

### D. 资料、安全和停止条件

- 实际代码路径：`writerforge/v35_observable_trace.py`、`writerforge/v37_foreshadowing_evidence_gate.py`、`writerforge/v38_lesson_transfer_bridge.py`、`scripts/append_v38_frozen_l2_selfcheck.py`、`scripts/audit_v38_l2_student_vs_critics.py`、`scripts/debug_v36_xiyouji_learning_to_writing.py`。所有旧原稿、原文窗口及详细WF思考仍只在Cloudflare**私有**R2中，尚未使用独立客户端AES加密；不要把完整原著、原创全文、思考记录或API密钥打印到公开GitHub日志。
- 既有测试/证据SHA必须原样保留；新调试记录要内容寻址、不可变、可读回。反作弊：不让WF自己当独立考官，不把模型意见当客观文学真值，不拿正例均分抵消R39具体负面争议。
- **当前状态**：第一课程窗口`NOT_PASSED`，第二`LOCKED`，实验L2未成为已验证的稳定正式技巧；下一窗口从**R39/R43和更早的真实线索/人物知识状态**开始，而不是重做整个西游记训练流程。

## 42. 【2026-10-18 中断交接】V55关系网络19项真实对抗试验：11/12基础通过、0/7扩展通过；暂停修复，保留全部旧文与V49失败

**这是聊天窗口达到最大长度时的新交接入口。请下一窗口先读本节，再读** [V56完整中断交接与19项失效分类](V56_RELATION_NETWORK_INTERRUPTED_HANDOFF_20261018.md)，最后才考虑新版本修复。**本轮未训练WF、未调用模型、未改写文学/R2原稿。**

### A. 真正已完成／不可混淆

1. 截至本次冻结，正式 GitHub **`main=a4f7b8d8ed68526f947f8e7db8bf4a5744ce7086`**，V53磁盘资料处理与离线索引、V54显式下载许可／追加事实账本、V55双时轴时间记录／有限图关系均已合并。`V55`版本不是文学等级晋级，V49第三次文学能力终审`THIRD_STRIKE_FAILED`依旧有效。
2. 用户本轮说“**测试你的关系网络**”，要求强制反作弊、找出底层缺陷。V56生产冻结不修源码，隔离审计分支 **`v56-relation-network-adversarial-audit`** 只新增 `scripts/audit_v56_relations.py` 和 `.github/workflows/v56-relation-adversarial.yml`。**[Actions #39095760849](https://github.com/66tyu55/WriterForge/actions/runs/39095760849)**：原有V55专项9项通过，但V56原始19项审计发现扩展能力失败，`--strict`按设计退出1，所以CI为**红色**，不允许谎称整体成功。
3. **原始19项：基础12项中11通过；预期扩展7项中0通过**。原始输出 JSON SHA256 **`bc333be303d03c4ba642deb88944593dd39430a942a734cf637188ea105b6bc2`**；工作流 artifact `V56_Actual_Relation_Network_Audit` ID `12123489686`（90天），ZIP SHA256 `539c8fe9087a76345bf8a2a0daa7e57c244c87c44b6b08d6430237ded4392f95`。均为临时SQLite的合成形式化事实，无付费模型、无R2网络、无真实文学创作。
4. **确切扩展失败 7 项**：`guard.reader_future_spoiler`（读者过早知道后文）、`guard.reader_private_thought`（角色内心秘密无披露证据却让读者已知）、`guard.knowledge_evidence_support`（UNKNOWN来源可冒充KNOWN）、`continuity.cross_chapter_link`（第1章线索无法连第3章回收）、`continuity.cross_chapter_state`（人物事实跨章查询变UNRECORDED）、`chronology.flashback_import`（导入倒叙早期事件被单时钟防倒填拒绝）、`scale.long_record_chain`（同一事实68次记录超过64条查询上限）。后两者属于明确的策略／容量限制，不能当成“模型理解错了”或“内存泄漏”。
5. **第8个红项 `revision.no_fork` 属于审计夹具本身失效，当前不能将其记为已证实的分叉安全漏洞。** 输入错误地用故事时间8的`KNOWN`证据支持时间2的`KNOWN`，最先触发正确的`FACT_ACTOR_KNOWS_BEFORE_EVIDENCE_EVENT`，而非预期的“同一旧版本双重修订”护栏。须下次**另造合法且事先冻结的独立测试**；保留本次红项，不修补旧JSON。
6. **确定通过的基础约束**包括：故事时间与入库记录时间分别回放、角色/读者作用域分离的存储、同一事实相互矛盾并存、拒绝角色提前获知、图边方向、禁止不同故事错误连边、图关系及记录篡改校验、重启恢复、`POTENTIAL_CAUSE`永不伪称语义因果。不能由此宣称整个跨章节关系网络完善。

### B. 别忘了**上一次中断的对话／旧文学失败**

- 第40、41节完整记录**V38真实《西游记》L2伏笔冲突**：WF认定R39为“铺垫”/R43“回收”；有效独立Pro把R39当“回收”，认为R34/R35更像铺垫；MiniMax意见因`uncertainty=[]`完整审稿不合格，不能算第二个正式判定。R2交叉核对SHA **`e2ed24abc352daef678165de8bee5f7c283f5709cf3a23c9fe99b9a876aeb0db`**，904字初稿／1136字修订及原文来源都不可重写。
- 后续V41—V51尝试宿主文学阅读／A-B／写作策略实际控制，**V49第三次终审已判WF文学经验自主改进能力未获证明，`THIRD_STRIKE_FAILED`**。不能把V55/56工程回归和图谱记录功能当作取消此终审的证据。
- 用户长期要求原文先入库→分类/学习→可反证经验→真正行为改变→新题独立评价，**禁止考官／辅助模型替WF写文学答案、禁止旧证据回填、禁止重复付费训练、禁止人类不可信评论伪造成功**。50部完整作品才进入统一文学成果验收；六部现代小说目前确认了私有R2原文归档，不等于全文深度学完。
- V53纠正“R2整库下载被冒充检索”和“原著短句直接拼入WRITE”；V54对陌生用户安装不自动下载私有资源，先明确授权再同步；V55强调**词面索引先后不等于故事时间先后**，本次V56审计正是其后续验证。

### C. 下一窗口恢复顺序；这些尚未执行

1. 先从`main`读取本交接42节和完整V56文档，核对 `v56-relation-network-adversarial-audit` 分支、GitHub Actions及原始JSON SHA，**不要启动文学训练或直接清空旧库**。
2. **先修测试设计再修程序**：`revision.no_fork`原夹具不合法，下一轮新题应给出符合已有时间知识规则的两次修订，并独立检查是否错误接受。绝不修改原运行报告。其他7项分类成读者信息屏障、知识来源可信度、跨章实体连续性、倒叙/时间轴和长链容量。
3. 若继续开发，建新的隔离V57分支：优先用**明示同一作品/角色/事件身份**跨章节连线，同时保持不同作品隔离；`READER`披露/时间也需校验、`KNOWN`须有一致来源，故事发生顺序与数据库写入顺序不可混用；超过64项的历史回放做分页/视图快照，不取消安全界限。不引入LLM自动判断“因果”或原著段落复制。
4. 全部下一轮新反例都需保存原始失败、新代码、新运行结果分别SHA；V56旧脚本与红色原始证据**不得覆盖**。V56审计分支不合并`main`；本交接只是文档更新。
5. **本次中断停止处**：V56的19项结果刚刚跑完并导出了ZIP，尚未修任何V55关系代码，也尚未开始V57。恢复后先确认失败归因和修复优先级。


## 43. 【2026-10-18 V57独立修复】保留V56红色证据；显式跨章作品身份、读者披露、倒叙、长历史与并发无分叉

**重要：本节仅在 `v57-relation-evidence-foundation` 修复分支记录，正式 `main` 尚未合并；第1—42节不可重写。** 详细报告：[V57关系网络修复、证据哈希及未完成事项](V57_RELATION_FOUNDATION_REPAIR_20261018.md)。

1. 已逐一读取第42节和V56完整交接，复核原始红色 [Actions #39095760849](https://github.com/66tyu55/WriterForge/actions/runs/39095760849) 日志；19项为基础11/12、扩展0/7；原始JSON SHA `bc333be303d03c4ba642deb88944593dd39430a942a734cf637188ea105b6bc2`；ZIP SHA `539c8fe9087a76345bf8a2a0daa7e57c244c87c44b6b08d6430237ded4392f95`。原脚本和原始报告未修改。
2. 原 `revision.no_fork` 夹具引用未来证据不合法，不能证明分叉漏洞。V57修正合法夹具并发现应增加 SQLite 数据库级唯一索引防并发竞争：`temporal_claims(supersedes_id)` 唯一。
3. V57修改 `writerforge/fact_journal.py`：READER KNOWN 增加披露时间及角色私密THINK隔离；KNOWN必须有同状态证据；`register_scene` 明示同一作品/章节绑定后允许跨章图和作品范围状态查询；`append_flashback` 明确故事时间与记录顺序并存，普通追加的禁倒填不变；`temporal_view` 每批64条、最多8192条扫描，返回受限引用与完整计数。
4. `writerforge/cli.py` 开放 `fact-story-bind`、`fact-flashback`、`fact-view --story-id`，已有真实端到端CLI合成测试通过；V54旧测试12/12、V55旧测试9/9、V57新测试12/12，合计33/33，见绿色 [Actions #39100156422](https://github.com/66tyu55/WriterForge/actions/runs/39100156422)。新JSON报告SHA `327a661d0ee7f5da6749f8be5b29a6d97d0efcac723a323fa28b9eafdf99e485`；证据artifact ID `12125889031`。
5. 本次没有文学训练、R2同步、模型调用、原文覆盖，也未合并main；V49 `THIRD_STRIKE_FAILED` 未改变。SHA 不能证明文学来源真实性；读者披露及作品/角色身份仍属显式声明，不能由关键词或语言模型擅自推定；旧 `state()` 64条保护和图搜索48边限制仍待专项设计。
6. 下一次恢复：先读本节→完整V57文档→CI链接及哈希；继续不同作品同名角色、跨章变更、伪造来源和超长分页压力测试。不要重复文学训练，也不允许把V56红色报告覆盖成绿色。
