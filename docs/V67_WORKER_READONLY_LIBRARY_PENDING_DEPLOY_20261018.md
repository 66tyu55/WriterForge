# V67｜先完成 Worker→学习库只读通道，再进行《老残游记》正式考试

日期：2026-10-18。开发分支 `v67-worker-readonly-library-bridge` 从 V66 继承；仅修改隔离分支，`main`、Railway 当前运行实例和私有 R2 不变。

## 一、为什么还不能宣称考试开始

已有线上成功是 Railway WF Python → Worker HTTPS → R2 **233 对象目录统计**，不是书中章/段/句检索。原 Railway 部署 `5243f688-3955-42d3-ab14-b229b3263c50`、固定 commit `f2c6d3377c307ce225a60be8c7e3226075a34911`，V66 后的代码提交不会自动作用于该运行实例。

Worker 生产端此前只验证了 `/health`、`/r2/status`、`/r2/inventory`。此时还**没有已确认部署**的 `GET/HEAD /r2/object`。没有 Cloudflare 管理工具可代表用户直接发布，所以 V67 只是“可供部署的完整源代码+待线上验收的WF客户端”，不是生产闭环成功。

## 二、已经写入的底层改动（不预写答案）

- `cloudflare/wf-r2-worker-readonly.js`：可置入**现有** `wf-r2-api` 的独立 Worker 代码。沿用现有 `WF_R2` 桶绑定和 `WF_API_TOKEN` Secret。兼容 V66 健康、单页 R2 status、全目录 inventory JSON；新增 `GET/HEAD /r2/object`，仅允许 `writerforge/v1/libraries/laocanyouji-25124/` 下的 `latest.json`、`snapshots/{64位SHA}.json`、`blobs/{64位SHA}`；不允许其他作品、任何 Put/Delete、转移授权、未限制的大文件直读。JSON最大128KiB，单对象上限256MiB，单段4MiB，206 Content-Range与源大小显式核对。
- `writerforge/worker_readonly_library.py`：WF 自己带既有 Bearer Token 读取小指针与 manifest、核验快照 manifest 的 SHA256；只分段取**当前这一本**的 SQLite blob 与 source blob，逐段限定时空预算、整文件 SHA256。恢复文件仅放在 Railway **一次性临时目录**，查询结束自动删除。使用源码已有古典图书目录的 Git blob SHA1 验证原文版次、学习源全 SHA256 与 `studied_works` 对齐，再校验 SQLite quick_check/源章数/统计，连接强制 `mode=ro` 与 `PRAGMA query_only=ON`。
- `VerifiedStudy.locate(terms,limit)`：提供 WF 可自行调用的有界字面证据定位入口，输出 work_id绑定后的回/段/句、最多100字原文短摘和 SHA。但目前这只证明检索定位，**不代表声音/环境与紧张感的文学语义已经理解**。正式题目、预选关键词及答案不写到代码里。
- `wf_railway_library_start.py`：Railway 单次校验入口，报告是否能恢复原始源与 SQLite、章/段数量、真实耗时/传输字节数；不打印正文、token或题目、不跑文学模型。只有等Worker已部署后，才应把既有 Railway 服务绑定到V67精确提交和这个启动入口。
- `tests/test_v67_worker_readonly_library.py`：已提交纯离线 Fake Worker 反例测试，覆盖原文/manifest/Blob SHA篡改、404缺路由、越权Key、下载清理、SQLite禁止写入、结果定位。**测试文件已写入，不等于这批 Python 单测已经执行。**

已通过纯 Mock 的 Worker JavaScript 路由功能测试：`/health`与`/r2/inventory`=200；合法metadata GET=200、Blob HEAD=200、Blob Range GET=206；越权Key=403、未带Token=401、DELETE=405、无界Blob请求=400。此测试不是 Cloudflare 生产服务验收；Python/真实R2闭环仍未跑。

官方依据：[Cloudflare R2 Workers API](https://developers.cloudflare.com/r2/api/workers/workers-api-reference/) 支持原生 `head/get`、按 offset/length 范围读取、以 ReadableStream 返回，R2本身**不是**可执行SQL的服务。

## 三、线上一次发布的明确剩余动作

1. 用户**只需在原来的 Cloudflare 控制台打开现有 Worker `wf-r2-api`，备份/查看现有代码后，用该分支 `cloudflare/wf-r2-worker-readonly.js` 更新代码并正式 Deploy 一次**；保留 `WF_R2` 指向 `writerforge-private-library`，保留已有 Worker Secret `WF_API_TOKEN`。不需要重新生成Token、不需要复制 Token 到任何聊天或 GitHub。此步当前工具无管理接口，不能假装助手已替用户部署。
2. **发布完成后**，使用 Railway 插件调整原项目 `c5a1c1ad-03d7-4767-b972-8a46446fec07` 原服务 `e6a7688b-ee12-49ef-ae83-02145005fc79` 的源代码精确 SHA，启动命令 `python -u wf_railway_library_start.py`，运行**一次**。读部署日志检查实际 `WF_V67_LIBRARY_VERIFIED_READONLY` 与退出码 0；404/401/SHA不符则保留原失败，不重复拉全桶，也不把失败视为测试通过。
3. **上述验收为真后** 才启动正式考试（考官不选原文、不交关键词、不写答案）：《老残游记》中，作者有没有利用声音或环境变化营造紧张感？请 WF 自己检索资料，找至少一处原文，给出回/段/句位置和判断依据；查不到或没有能力核实文学因果关系必须返回“证据不足”。WF已有 `locate` 基础入口，但从自然语言问题到自主查询计划/文学解释的能力仍待单独接线验证，不能把这一步自动冒充完成。

## 四、严格边界

- **真正的按需初次恢复会把这一本书的 SQLite 和源文件暂存到 Railway**；这不是“无需传输原文的在线SQL”，但与整桶下载 1.67GB 有实质区别。Worker本身不执行SQLite，避免虚构数据库能力。只有在确认可重复只读检索后，再考虑已有缓存或远程索引，不预建第二套私有材料。
- 没有触发 GitHub Actions、没有复制旧 V52 `老殘` 六条检索结果、没有调用任何文学模型、没有WF新的考试成绩、没有R2写操作或作者本地安装。
- V49第三次文学终审 `THIRD_STRIKE_FAILED`、第二课程窗口 `LOCKED` 原样保留；工程读取成功绝不能自动晋级文学能力。
