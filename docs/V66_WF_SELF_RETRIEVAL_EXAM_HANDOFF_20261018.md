# WriterForge V66 · 云端直连已通过，但 WF 自主检索文学问题尚未执行（2026-10-18 交接）

## 0. 本次会话最后指令及准确状态

用户最后提出：**「做个测试--提出问题--让他自己检索」**，紧接着因上下文长度限制要求：**「最大长度了--先交接--说清楚」**。

**本轮已查阅 GitHub 当前代码，但没有给 WF 执行文学问答考试，也没有读取作品正文、SQLite 或文学经验。** 不得拿曾经的 V52 老查询结果或 V66 的 233 对象数量冒充本次文学自主检索。下一窗口直接接着完成考试，禁止重新开工程、重新创建密钥或重复手动部署连接测试。

## 1. 已建立、正在使用的真实架构

- GitHub 源码：`66tyu55/WriterForge`，开发分支 `v66-wf-direct-worker-http`；它从 V65 继承，**main 仍未合并**。请在下一窗口首先读本文件与 `docs/CURRENT_HANDOFF.md` 第53节。
- Railway 私有项目：`WriterForge`，项目 ID `c5a1c1ad-03d7-4767-b972-8a46446fec07`，production 环境 `65b1b9fe-2f4f-44f3-80af-77143a19545d`。
- Railway Python 服务：`wf-python-r2`，服务 ID `e6a7688b-ee12-49ef-ae83-02145005fc79`；一轮运行命令 `python -u wf_railway_start.py`，重启策略 `NEVER`，没有公共服务域名。
- **Railway 服务源码已固定 commit `f2c6d3377c307ce225a60be8c7e3226075a34911`**。GitHub 分支之后有文档提交时，不要假定 Railway 已自动运行最新 SHA；如要实际部署新 Python 功能，必须明确重新绑定代码 SHA 并查看其实际运行日志。
- Cloudflare Worker：`https://wf-r2-api.3227482831.workers.dev`，R2 变量绑定 `WF_R2`，私有桶 `writerforge-private-library`，Worker Secret `WF_API_TOKEN`。
- Railway 运行环境已经配置同名 `WF_API_TOKEN`，不要向聊天、GitHub、日志泄露其**值**，也不需要 GitHub Secrets。用户个人电脑**没有安装 WF**，此前的本地 PowerShell 方案已放弃。
- 实际 Cloudflare Worker Production 已确认 `GET /health`、`GET /r2/status`、`GET /r2/inventory`。没有代码证据支持 Production 部署了 `/r2/object`、`/r2/query`、SQLite 查询或任意小说搜索路由。
- 现有 WF HTTP 代码：`writerforge/r2_worker_http.py`，Cloud Railway 运行 `writerforge/railway_runner.py`、`wf_railway_start.py`，Railway 配置 `railway.json`；其他旧式 R2 代码为 `writerforge/r2_storage.py`、`writerforge/r2_retrieval.py`、`writerforge/xuehai.py`、`writerforge/db.py`。旧 S3/Boto3 路线与新的 Worker HTTP 路线是**两条不同路线**。

## 2. 已有的真实 WF→Worker→R2 接通机器证据

用户此前 Cloudflare 编辑器里查询 `/r2/inventory`，得到 233 对象、1,673,579,609 字节、Worker 305ms；**这个是用户浏览器手工测试，不是 WF**。

后来通过 Railway 插件真实触发 **WF Python** 一次独立 HTTPS 查询，部署 ID：

`5243f688-3955-42d3-ab14-b229b3263c50`

Railway deployment logs 中 `status = WF_R2_HTTP_SUCCESS`；内部结果：

`objects_scanned: 233`、`total_object_bytes: 1673579609`、`complete: true`、`r2_pages_scanned: 1`、`http_requests: 1`、`worker_metadata_query_ms_sum: 289`、`wf_http_end_to_end_ms: 717.28`、`sqlite_sql_executed: false`、`original_novel_text_downloaded: false`、`remote_writes_performed: 0`，进程 `WF_RAILWAY_RUNNER_EXIT_CODE=0`。记录 UTC `2026-10-18T13:39:50` 附近。

这一结果**严格证明 WF 直接列举了私有 R2 对象元数据**，**不证明 WF 阅读了文学、恢复 SQLite、搜索正文或形成文学经验**。没有任何新的文学考试成绩。

## 3. 上一阶段的 403 / 404 已经解决，不要重查

Railway 初期 `GET /r2/inventory` 曾见 403，再为 404；WF 带密钥 `GET /health` 返回成功，但 status/inventory 路由 404。之后用户检查并在 Cloudflare 部署完整 Worker（含 `/r2/status`、`/r2/inventory`），Railway V66 重新运行时成功得到上面的 233 对象。

**该问题已解决。** 不要再向用户索取 API Token、让用户搜索安全事件、重建 R2、重建 Railway 服务。Cloudflare 的平台安全权限问题不是当前主要阻塞。

## 4. 真正阻塞「WF 自己检索文学问题」的点

现 Worker 仅支持查看服务健康、对 R2 列 1 个对象、或分页列举 `writerforge/v1/` 的对象总量与字节数，不返回对象 Key、作品内容、SQLite 数据，更没有远程 SQL。WF 客户端 `WFWorkerR2Client.inventory()` 只能获取统计，不含作品中的句段出处。

**WF 原本有一个旧的真正检索实现** `writerforge/r2_retrieval.py` 中 `R2SourceGateway.search`：使用 `R2StudyVault.restore` 访问 S3/R2 下载并核验备份 manifest/SQLite/源档，之后对只读 SQLite `PRAGMA query_only=ON`、`XuehaiStore.query`、`source_spans` 进行字面检索和原句哈希交叉核对。老实现需要 `WRITERFORGE_R2_ACCOUNT_ID` / `WRITERFORGE_R2_BUCKET` / `WRITERFORGE_R2_ACCESS_KEY_ID` / `WRITERFORGE_R2_SECRET_ACCESS_KEY` 等 S3 凭据。**目前 Railway 只有 Worker 的 API Token，不具备旧 S3 路线的访问凭据**。不要暗中声称已经由新 Worker HTTP 路线调用了此旧搜索模块。

旧 V52 曾在历史 GitHub Actions 中用 `laocanyouji-25124` 库查询 `老殘`，检索到 6 条，见 `docs/V52_R2_NATIVE_RETRIEVAL_LIVE_20261018.md`。**这份历史成绩不能复制为新的独立考试成绩。**

R2 保存格式真实为：
- `writerforge/v1/libraries/{library}/latest.json`
- 指针字段 `format` / `library` / `snapshot` / `manifest_sha256`
- `writerforge/v1/libraries/{library}/snapshots/{sha256}.json`
- manifest `files["study.sqlite3"].sha256` 指向 `writerforge/v1/libraries/{library}/blobs/{blob_sha}`
- 实际快照属于不可变内容寻址对象，不是「R2 可直接执行 SQL」。
- 源语义记录位置表：`source_spans(work_id,chapter,paragraph,sentence,excerpt,source_sha256,tracks_json,craft_json)`；学习检索 `xuehai_entries`。

## 5. 下一窗口操作顺序（先补最小接口，然后立刻考试）

**不要再做对象 inventory 重复测试**，也不要把 1.67GB 小说整体复制给用户、上传 GitHub 或偷偷复制给模型。

1. **最小只读传输桥**：优先让 Cloudflare Worker 增加**受限的 `GET /r2/object`**，要求携带现有 Bearer Token，只允许 `writerforge/v1/libraries/` 下的对象 Key；最好进一步约束为白名单单个学习库（先 `laocanyouji-25124`）及 `latest.json`、`snapshots/{sha}.json`、`blobs/{sha}`。为对象提供 Content-Length/大小上限、合理 Range 或流式返回、校验 Object Key、禁止 LIST 越权、禁止 Put/Delete，避免响应正文出现在日志。Cloudflare 管理接口目前没有连接，必要时**只需要用户将最后的 Worker 修改部署一次**；不要让用户继续人工进行多轮 HTTP 测试。备选研究 Cloudflare D1 只读索引、或在 Railway 临时按需下载单个学习 SQLite；切忌声称 Worker 可以原生 SQL 查 R2 blob。
2. **WF 自己取得资料**：在 Railway 的 WF 中添加只读 `read_object(key)`、manifest SHA256 验证、按需单库抓取 `study.sqlite3`（不抓取全桶、不永久存到用户电脑）；必要的 `source.txt` 要先按用户认可的资源预算与来源验证，再由 WF 自己恢复数据库到临时目录。复用旧 `r2_retrieval.py` 的来源/句段/哈希核验思想。WF 执行 SQL 使用 SQLite `mode=ro` / `PRAGMA query_only=ON`，禁止写回 R2，优先仅在 Railway 任务执行期用内存/临时盘并清理。此处「检索」是按需读取，不是用户本地资源下载，也不是模型 copy 原文。
3. **由 WF 自己完成考题，不由宿主写答案或人工塞入结果**。建议考试题：「《老残游记》中，作者有没有利用声音或环境变化营造紧张感？请自行寻找至少一处真正的原文证据，准确报告回/段/句位置、简短原文核对信息，并说明哪部分证据支持哪一判断；检索不到就说证据不足。」如果现阶段没有真实文学语义能力或模型，先进行清晰标记的**检索定位子题**，如「《老残游记》中『黃河』是否出现？在哪几回？提供准确出处」，不预设命中率/位置。不能把子题的关键词命中冒充文学理解。
4. 记录**真实证据链**：考题、WF 自己给出的检索计划、调用路由与查询耗时、库/版本/章回/段/句、源哈希校验结果、WF 自己的答案、答题是否独立完成、失败/未知。不得预写答卷，也不能直接使用 V52 `老殘` 六条结果回填本次。
5. Railway 部署使用 `mcp__Railway__connect_service_source` 指定 V66 **新提交的精确 commit SHA**，保证实际代码更新到 `wf-python-r2`；通过 `get_logs` 查看真正成功/失败、计时和鉴权结果。用户没有本地 WF，也不需要让用户打开本地 PowerShell。尽量保持单次运行以节约费用，不自动反复轮询，不触发 GitHub Actions。

## 6. 边界与沟通要求

- 2026-10-18 上一个会话最后已完成**代码查阅**：`r2_storage.py`、`r2_retrieval.py`、`xuehai.py`、`db.py`；尚未开始新的「文学检索」实现、没有对应 Railway 新部署。请从这里直接继续，先方案比对后实现。
- 不能为了答卷无中生有：检索失败就是失败，未知就是未知。文学知识需通过来源核对与实际读写表现验证，不能靠自动关键词排序宣称理解文学技巧或文学等级晋升。历史 V49 `THIRD_STRIKE_FAILED`、第二窗口 `LOCKED` 均未发生改变。
- 不要从 GitHub Actions 运行：用户特别强调 Actions 会触发邮箱通知。Railway 部署和 Cloudflare Worker 手工部署是当前运行链路。
- 不重复创建项目、不重新配置 Token、不把密钥提交 GitHub、不改 main、不把本次交接当作功能实现。
