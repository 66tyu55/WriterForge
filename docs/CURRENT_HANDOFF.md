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
