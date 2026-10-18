# V68｜400本私有作品批量入库：原名保留、自动编号、后补SQL索引（2026-10-18）

## 用户本轮要求与边界
用户本地约400份作品，截图中既有分类文件夹如玄幻、仙侠、科幻、历史等，以及若干缩写/不完整书名。目标**至少50部，类别增量计划为古典4、玄幻20、仙侠10、科幻10、历史10，合计54部**；这些数字是**计划目标**，并非R2中实际新增了54部，更非54部已学习。

**原始资源不能经过GPT或公共GitHub**。上传从用户本地Windows电脑 → 其自有**私有**Cloudflare R2。WF不需要先学习或生成SQLite才能存放原书。若用户无分享/存储相应材料的权利，需先解决授权；R2不得开放公共读权限。

## 一、此刻用户可以直接上传，不必手工重命名
建议对象Key结构（可以使用中文路径）：

```
writerforge/v1/inbox/20261018/01、玄幻/原文件名.txt
writerforge/v1/inbox/20261018/02、仙侠/原文件名.txt
writerforge/v1/inbox/20261018/03、科幻/原文件名.txt
writerforge/v1/inbox/20261018/04、历史/原文件名.txt
writerforge/v1/inbox/20261018/05、古典/原文件名.txt
```

也允许用户已上传到其他私有Key，届时需另做**只读扫描映射**，不强迫重传。目录层次建议保留；不支持用R2“原地重命名”作为数据库主键，因为R2 Key的更名实质上涉及对象复制/删除，破坏引用和幂等性。

若文件目前仍处于RAR/7z大压缩包，最佳方案是在本机解压（不要通过GPT）后递归上传一个个真实资源文件；如果已经存了单一压缩包，仍可保留原始备份，但必须另外执行受限、安全、用户授权的解包，不能直接把压缩包对象数当作品数。

**可选**无需WF的批量递归上传办法（需用户自己在rclone配置Cloudflare R2 S3写权限；千万不把key粘贴给GPT）：

```powershell
rclone copy "D:\Novels" "wf-r2:writerforge-private-library/writerforge/v1/inbox/20261018" --immutable --transfers 4 --checkers 8 --progress
```

选择 `copy` 而不是 `sync`：不会因本地删除文件而自动删除R2存储对象。`--immutable`要求现存远程同名但内容变化时拒绝覆盖，而不是静默覆盖。该命令仅示例，`D:\Novels` 与 `wf-r2` 是占位路径/用户自己配置的remote。Rclone Cloudflare参考：https://developers.cloudflare.com/r2/examples/rclone/ 。

## 二、编号为数据库虚拟编号，原始R2 Key不改

- `object_key`：永久保留真实原对象完整Key，禁止复制删除式批量重命名。
- `display_no`：每个类别首次发现时从1递增，一次批量发现按Key排序分配；后续新增只追加编号，**不重排已有作品**。
- `category`：只读取顶层分类文件夹；格式 `01、玄幻` 正规化成 `玄幻`，不从文学内容推断；未知目录标成 `待分类`。
- `raw_title`：保持文件名的真实干名。例如“FRXXZ”只能标“FRXXZ/待核对”，不能由GPT猜测完整书名；后续用可审计别名表审批，不改原Key。
- `book_id`：只有拿到**完整原始文件SHA256**后才分配 `b_<sha前32位>`，完整64位SHA独立保存；不能拿文件名或编号冒充同一作品。重复内容、多原文件路径映射同一索引ID。
- `status`：区分`RAW_ONLY_PENDING_SQL`、`EPUB_PENDING_PARSER`、`ARCHIVE_NEEDS_LOCAL_EXTRACTION`、`UNSUPPORTED_REVIEW`、`INDEXED_LEXICAL_ONLY`、`DUPLICATE_ALIAS`。上传成功≠可检索，更≠文学学习完成。

## 三、后补SQL流程（需要WF独立执行）
1. WF后续通过受限 Worker **只读分页枚举R2 inbox对象**，每次最多数百个Key，只登记metadata，不下载400部正文。**当前生产V67 Worker仅允许旧单本`laocanyouji-25124`下载，尚无inbox枚举/读取路由**；要打通下一段需要单独增加经过验证的权限受限只读路由，之后只要求用户再正式部署一次。不能拿已有 `/r2/inventory` 的对象总数当作品目录。
2. 每条新Key都入`assets`表；首次按类别分配UI编号，已有同名/etag/size变化按拒绝处理，登记异常并走版本审核。**本阶段SQL目录只存Key、分类、大小、状态、编号，不需要正文**。
3. 排队每次处理一部：WF按需从R2读取临时文件，计算SHA256，检测编码。当前V68的第一版索引器只支持TXT/MD的UTF-8/BOM，GB18030需要显式选定，EPUB、RAR、7z需独立安全解析器。不要按扩展名就断言是可读小说。
4. 逐行处理，辨认章节标题、章节/段/句位置；模糊章节记0，不编造回数。保持原文字节不变，索引副本才做NFKC和大小写/空白规范化，按200条一批刷磁盘。每本独立 `b_<sha>.sqlite3`，含元数据、序号、每句短原文、来源SHA；优先SQLite FTS5 trigram，回退有界字面查找。查询仍须限定类别与已索引的具体book_id，不能碰所有400部并自称一眼理解。
5. **数据持久化仍待接线**：生产 Railway 目前没有volume；索引器可在独立临时目录构建，但生产必须先选择受控Railway持久卷或由独立、严格限定只写`writerforge/v1/indexes/`的后端凭证进行内容寻址入R2。现有`WF_API_TOKEN`是Reader Token，不可偷偷改成可写。需要可靠的每书队列、持久checkpoint、崩溃恢复和索引快照签收后，才能宣称400部完整工程闭环。
6. WF检索分为【类别→作品目录→章节→短句】并隔离LEARN与WRITE。两字检索或数据库预算超限返回`SCAN_BUDGET_EXCEEDED/部分结果`，不说“全书没有”。真正文学“声音环境营造紧张感”的理解仍需独立考试，词面SQL不是文学能力。

## 四、本轮提交与真实测试边界
分支 `v68-bulk-inbox-catalog-sql-index` 从已真实验证的V67分出；**不改生产Worker、Railway服务或main**，不访问用户本地文件或R2实际正文、不启动GitHub Actions、不改历史私有书库和V49失败证据。

新增：
- `writerforge/bulk_inbox.py`：完整Key防穿越、分类别名、单调递增编号、SQLite元数据目录、同Key尺寸/etag变化拒绝、按完整源SHA去重、流式TXT索引、每书SQLite+trigram、真实来源短句定位、VM预算与诚实`LEXICAL_ONLY`声明；
- `scripts/wf_bulk_inbox.py`：独立运行的**本地纯元数据**文件夹预览、rclone `lsjson --recursive` 输出的离线导入及类别数量统计；不依赖用户本地安装WF、不会主动请求R2；SQL查询只在WF/本地机执行，不进入GPT；
- `tests/test_v68_bulk_inbox.py`：合成400 Key、中文类别、缩写原名保留、重传/篡改拒绝、同源别名/去重、编码错误、只读来源定位的纯离线用例。

本轮在独立的本地Python实验环境对初版同接口模块跑8/8离线单测；400个合成对象元数据登记耗时约0.016秒；额外400个极短**合成**TXT逐书建SQLite约3.69秒、shard磁盘占用约15.62MiB、tracemalloc峰值约1.03MiB。**这些不是用户400本真实小说规模的性能数据，也不是云端R2读取/上传性能**。GitHub分支新代码尚未有CI全仓回归验证；不要假装已生产上线。

## 五、正式下一阶段
用户上传完成后，先询问实际R2顶层前缀及文件是否已单独解压（只问路径和格式，不接收全文），再扩展已认证Worker只读inbox分页与Range GET→Railway metadata-only扫描→R2每书只读流式下载→持久SQLite队列/索引快照；每步保存真实对象数量、大小、失败原因、耗时、源SHA证据，绝不把小说正文复制进聊天或公共GitHub。

**验收口径**：R2真实对象数 ≠ 不重复独立书数 ≠ 可SQL检索书数 ≠ 完整学完书数；50本门槛以真实独立验证完整来源和可检索状态为基础，文学晋级依旧依独立评审。V49`THIRD_STRIKE_FAILED`、第二学习窗口`LOCKED`均不改变。
