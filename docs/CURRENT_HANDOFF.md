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
