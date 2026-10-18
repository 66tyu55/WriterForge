# V66｜WF 自己调用用户 Cloudflare Worker → R2（2026-10-18）

**用户要求：停止我和用户在 Cloudflare 测试页面不断手工请求；目标是 WriterForge 程序作为客户端主动调用已经建好的 wf-r2-api。不要启动 GitHub Actions。**

## 当前实际已完成

- 独立开发分支：`v66-wf-direct-worker-http`，继承V65；没有修改main。
- `writerforge/r2_worker_http.py`：基于 Python 标准库的 `WFWorkerR2Client`，仅向用户指定的 HTTPS Worker 发送只读 `GET /r2/inventory`。从本地 WF 进程变量 `WF_API_TOKEN` 获取 Bearer Token；不保存、不打印、不写入源码或 GitHub。禁止跨域重定向转发密钥。检查完整返回结构，游标重复/分页不全严格失败。
- `writerforge/cli.py`：新增 `writerforge r2-http-inventory --endpoint https://wf-r2-api.3227482831.workers.dev` 入口。**无需创建默认SQLite、无需 S3 SDK、无需 GitHub**。
- `scripts/run_wf_r2_worker.ps1`：Windows PowerShell 从 WF 项目根目录运行，交互掩码输入 Token，只在子进程运行期间设置环境变量，最后清除。
- 输出由 WF 进程自身计算 `wf_http_end_to_end_ms`，同时列出云端 `worker_metadata_query_ms_sum`、对象数、字节数、HTTP 请求数、起止 UTC 时间，标记 `sqlite_sql_executed=false`。
- **无额外 GitHub Actions、无文学模型、无 R2 下载、无 R2 写入**。这是实现代码和启动入口，不代表本地机已完成真实认证调用。

## 用户 Windows 电脑如何真正让 WF 调用

在已有的本地 WriterForge 仓库中启动 PowerShell：

```powershell
git fetch origin v66-wf-direct-worker-http
git switch v66-wf-direct-worker-http
.\scripts\run_wf_r2_worker.ps1
```

启动器会掩码要求填写原 `WF_API_TOKEN`（输入不会回显），由 WF 的 Python 进程调用 Worker。PowerShell 若禁止 `.ps1`，按本机执行策略调整或直接在已有的受控环境中设置 `WF_API_TOKEN` 后运行：

```powershell
python -m writerforge.cli r2-http-inventory --endpoint https://wf-r2-api.3227482831.workers.dev
```

不要将 Token 写在命令行参数或聊天中，不要截图含 Token 的控制台内容。

## 哪些是已知历史结果，哪些尚未发生

- 用户此前自己在 Cloudflare 控制台调用 Worker `/r2/inventory`，得到 `233` 个对象、合计 `1673579609` bytes、Worker `305 ms`、`complete=true`。这不是由 V66 的 WF Python 进程产生，不得冒充新验证。
- V66 真实本地运行之后，WF 将在 stdout 给出自生成 JSON，值可能已因新增对象变化。若用户提供这份 JSON 才能宣称独立 HTTP 调用成功。
- 当前 Worker 只确认部署了 `/health`、`/r2/status`、`/r2/inventory`。**尚无已部署的云端 SQL 执行或完整 SQLite 下载路由**。`r2-http-inventory`仅做对象元数据全范围遍历，不等于全书章节 SQL 检索。
- 现存 `R2StudyVault` 使用 S3 API，Worker 代理是另一条可选读取传输路线，不替换旧代码。
- 没有对 V66 启动 Actions 或伪造合成成功日志。文学状态仍为V49 `THIRD_STRIKE_FAILED`，不晋级。
