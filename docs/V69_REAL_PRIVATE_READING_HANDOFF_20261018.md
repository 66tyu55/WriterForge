# V69 · 已上传四目录 private-reading 的只读清点（2026-10-18）

用户已确认真实R2位置：`writerforge-private-library/writerforge/v1/private-reading/`，四个文件夹为 `single-works/`、`仙侠/`、`历史/`、`科幻/`。后三类是新增上传，single-works包含旧条目与新加入的中文名称文件。**只根据目前截图不能数出实际文件数或识别上传前后增量；第一次快照不得将single-works所有文件认作新书。**

新开发分支 `v69-private-reading-four-folders` 从V68继承，修改：
- `cloudflare/wf-r2-worker-readonly.js`：保留旧真实通过的单书 `/r2/object`、`/health`、`/r2/status`、`/r2/inventory`；新增Bearer认证的 `GET /r2/private-reading/list?folder=<四目录之一>&cursor=...`，每页上限64，仅返回Key/大小/ETag/时间；新 `GET/HEAD /r2/private-reading/object?key=...` 仅四目录、允许的扩展名、256MiB上限、每次最多4MiB范围读取，不提供写方法，拒绝遍历。所有私有信息只返回给已授权WF进程而不进入公开日志。
- `writerforge/bulk_inbox.py`：除了历史的 `writerforge/v1/inbox/`，直接支持真实 `writerforge/v1/private-reading/`。仙侠/历史/科幻按目录分类；single-works默认待分类，除非二级分类文件夹明确；未知的多层章节文件标待组装。所有原Key不改，类别编号和来源SHA独立记录，绝不靠缩写书名猜全名。
- `writerforge/private_reading_remote.py`：WF Python的分页元数据扫描，逐目录最多64页、总对象限10000；可以在临时SQLite登记并输出各类别文件数/字节数/扩展名/状态的汇总，不打印私有对象Key。每个分类选1个合法文件，仅试HEAD和1字节GET证明R2对象访问，不下载全文。临时结果明确`catalog_persisted_after_process_exit=false`，不能宣称数据库持久化。
- `tests/test_v69_private_reading.py`、`wf_railway_v69_offline_tests.py`：用真实Railway Python（非GitHub Actions）检查合成400对象分页、重复扫描、分类、越权和短字节访问；该测试不联网R2也不代表真实400部资料入库。

**Cloudflare生产Worker仍需用户打开原 `wf-r2-api` 按 `cloudflare/wf-r2-worker-readonly.js` 候选源正式部署一次。** 目前没有管理员连接能替其改Cloudflare配置。部署之前不得将Railway模拟输出当作新上传对象已清点。保留原 `WF_R2` 绑定和 `WF_API_TOKEN` secret，不要重新创建/公布它们。

真实云端清点入口应在部署后由助手改动现有Railway `wf-python-r2` 的一次性启动脚本，再读真实日志。第一轮仅元数据及每目录最多一字节读取，严格零正文输出；待真实书数、文件类型确认后，再按需分书建索引并解决Railway当前无volume导致的SQL持久化问题。资料入R2不等于WF已经完成全文学习；历史V49文学失败与第二窗口锁定不变。

## Railway 离线验证更新

Railway 部署 `95483fdd-37d6-4ef3-9c2a-f0ff3d3739a2`，运行 V69 Python 3.13 测试，共15项全部通过，错误0、失败0、跳过0，合成测试2.448秒。原首次部署 `94a4f629-c7cd-4b5d-87fd-47b099c59035` 因 unittest discover 夹具的 `top_level_dir` 不可导入而红色，修正测试启动器后成功；保留失败事实。**这两次都没有访问真实R2，不意味着四个目录已真实扫描成功**。用户下一步只需在现有Cloudflare Worker按此分支的JS文件更新正式部署一次；勿复制任何Secret或原著进入聊天。部署后由助手启动已写好的 `wf_railway_v69_private_scan.py` 做真实云端只读清点。
