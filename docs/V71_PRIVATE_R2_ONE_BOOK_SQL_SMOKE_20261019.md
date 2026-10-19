# V71｜直接R2单TXT → WF流式读取 → 临时SQLite → 内部检索回读（2026-10-19）

## 背景与固定可信来源

用户真实私有R2路径为 `writerforge/v1/private-reading/` 四目录。V69真实扫描79对象、共577574142字节。V70真实拓扑 `c6caee3c-50e1-4126-9002-52ec24f9104c` 发现43个TXT：34个单TXT路径候选、9个TXT与RAR同目录，没有任何父目录下有两个TXT。**这里只是文件候选，还没验证完整小说/去重。**

## 实现（单本小预算、绝无模型）

- 新开发分支 `v71-private-r2-one-book-sql-smoke` 从V70独立继承，不改main/现有Cloudflare Worker/R2书库。继续复用已部署的受限 LIST/HEAD/Range GET Bearer Token，只读授权不升级为写入。
- `writerforge/private_r2_sql_smoke.py`：WF仅按四目录元数据和大小选择一个 `历史/仙侠/科幻` 类目录下**只有一个TXT且没有RAR或其他同目录文件**的候选；选择顺序为文件小→稳定哈希，不读取文件名含义、不由宿主挑选原文或检索词。源大小范围10KiB至16MiB，每次Range GET最多1MiB，总请求数≤17、只下载一份文件。
- 每个Range响应验证Content-Range、Content-Length、ETag和总长度一致，分块写入Railway的独立临时目录，计算原文完整SHA256（完整性检查，**不是版权版次或文学来源认证**）；再用已有V68 `BulkCatalog.index_text_file` 生成SHA命名的临时按书SQLite，按章/段/句建立字面索引。这个过程中用户原文件只在用户R2与WF的Railway临时运行环境，**不会经GPT或公共GitHub传输正文**。
- 最后 WF 在临时索引里自行选一个内部出现的字串，仅验证 SQL词面回读命中且无误；不公开检索词/小说原句。**这不是未见问题的盲测，也不证明文学理解。**
- Railway没有卷，临时SQLite和源文件退出后自动销毁；明确报告 `sql_persisted_after_exit=false`。持续50—400本的可检索库仍必须设计独立持久化。
- TXT编码当前支持UTF8/BOM及明确指定格式；遇到未知编码会诚实退出，**不对用户小说猜GBK或当成解析成功**。不自动把RAR当一部新书，也不下载压缩包。

## 已通过反例测试及历史留痕

新增 `tests/test_v71_private_r2_sql_smoke.py` 与 `wf_railway_v71_tests.py`。Railway真实Python部署 `e666b3e2-865f-4f8b-9b9a-7c4dad6dc19d` 运行累计**29项合成单测通过、0失败0错误0跳过**。新项包括选择不混RAR的父目录、跨1MiB分块、断块/ETag变化拒绝、SHA验源、真实SQLite短句索引和内部只读字面回读。**测试本身未连接真实R2**，不可算实际小说完成索引。

## 待填写的真实R2结果

下一步将把既有Railway `wf-python-r2` 一次性启动命令切换成 `python -u wf_railway_v71_one_source.py`，必须通过新固定提交SHA触发新建构建（Railway原`redeploy`曾复用旧启动脚本，不能重复犯错）。正式运行时只输出文件类别、字节量、原文字节SHA256、索引句段计数、耗时、内部命中数以及临时文件销毁/写入0/模型0，不输出标题、private Key或原文。

未经真实日志不得声称V71线上成功、已完成50本或已解决索引持久化。文学终审V49 `THIRD_STRIKE_FAILED` 和第二学习窗口锁定不变。

## 真实部署故障留痕（不把退出码冒充成功）

V71 首次实际R2读取试跑：Railway部署 `f4b658d6-8e47-4630-9a58-ad1787e0d63a`，固定提交 `55d1a7889cc2ab015b997347c0fcef8087f55bea`，服务启动配置 `python -u wf_railway_v71_one_source.py`。生产容器 **CRASHED**，相关部署日志仅 `Starting Container`，**没有打印** Python源码最前面的 `WF_V71_ONE_SOURCE_SQL_RUN_STARTED`，没有成功、失败JSON或完整文件SHA。Railway自动诊断为空；没有证据证明本次进程真正完成了原文下载、SQL或异常处理。此运行**不能算成功**。

Railway资源快照显示内存峰值约0.018 GB、CPU很低，未见明确OOM证据，但这不构成完整根因证明。为免盲目反复读取私人小说，新增 `wf_railway_v71_boot_check.py` 作为**不联网R2**的启动/日志双通道探针，只检查部署源码文件存在、环境Token变量名存在（不打印值）和Python版本，确保启动路径后再决定是否重新运行真实索引。原先23/29测试绿色不动。


## 非联网启动自检结果与一次受控重试

Railway新的独立Python自检部署 `b996f8a9-1c41-4324-b74b-e453a8989bea` 真正输出 `WF_V71_BOOT_SANITY_OK`，同时stderr独立 marker 出现，退出成功；Python 3.13.16，目标 `wf_railway_v71_one_source.py` 文件真实存在，模块存在，既有 `WF_API_TOKEN` 环境变量名配置存在。此次 **0 网络请求/0原著读**。这说明基础启动环境可工作，但不足以解释上次CRASHED的全部原因。

接下来在源代码加入**阶段性安全收据**（inventory开始/完成、候选选择、Range下载开始/哈希完成、SQL构建开始/完成、内部查询完成），仅显示固定状态码不输出小说文件名或文本；运行入口开头stdout+stderr双标记。只进行**一次**新的受控试跑，首次不明崩溃历史原样保留；若再出现不明CRASHED，则停止无证据重试、转入更底层的Railway启动诊断。
