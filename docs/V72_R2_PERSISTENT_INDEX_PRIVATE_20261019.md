# V72 · R2 为 WriterForge 索引的永久唯一存储（2026-10-19）

## 用户已选方案：永久资源与索引都放现有私有 R2

用户明确：「存储在R2吧，不然我怕到时候来回迁移」。**不创建 Railway 持久卷，也不购买额外的2GB存储。** 唯一已有桶继续使用 `writerforge-private-library`；R2永久保管原始小说与WF生成的分书SQLite索引，Railway只在工作期间临时拉取一本SQL分片执行`mode=ro` / `PRAGMA query_only=ON`。这不等于R2可以直接执行SQLite，也不意味着查询时绝无短暂网络传输。

真实历史：V71 Railway 部署 `508673b0-9685-41ce-8777-664c516960c4` 已完成一部真实科幻TXT(3636548 bytes)→65,573 SQL来源单元/499个疑似章节标题→内部自选词面命中；原始内容未进GPT/GitHub。**V71的SQL是临时的，不可当成已保存在R2的成绩**，旧失败记录不改。

## 核心路径/协议

```
现有R2私有源文:
writerforge/v1/private-reading/{仙侠,历史,科幻,single-works}/...

新增R2永久SQL索引:
writerforge/v1/indexes/v1/chunks/{chunk_sha256}.bin
writerforge/v1/indexes/v1/refs/{sha256_of_original_object_key}/{manifest_sha256}.json
```

Worker仍允许原V67/V69只读接口；新增路径：
- `PUT /r2/index/write?key=...` —— **必须是独立的 `WF_INDEX_UPLOAD_TOKEN`**。原有 `WF_API_TOKEN`（读权限）不能调用。只接受`indexes/v1/`下的内容寻址数据块和不可变manifest；绝不允许原文对象的PUT/DELETE。两个Token相同则Worker拒绝启用写权限。数据块单次≤1MiB，manifest≤64KiB，任意目录穿越/外部Key直接403。
- `HEAD/GET /r2/index/object?key=...&offset=...&length=...` —— 原有只读Token，按需读某一本书的索引，而不是扫描/下载400本。所有请求先校验R2对象元数据中的sha、响应长度、ETag；数据块必须Range GET。
- `GET /r2/index/refs?source_key_sha=<64位hash>` —— 只读逐页发现指定R2源对象的不可变索引清单。不会暴露用户原小说名称。

程序 `writerforge/r2_index_vault.py` 为独立可复用标准库HTTP访问层：
- 由WF自动计算SQL整个文件SHA256，切成1MiB块，逐块以SHA命名；
- 远端同名且digest一致时幂等跳过写入，内容不同则拒绝覆盖；
- 严格遵守**先全部数据块、再发布索引manifest**，每个manifest标注原对象Key哈希、原始文件SHA、R2 ETag与大小、SQLite全SHA、块列表与各SHA、书ID、检测章节数、索引单元数、编码状态以及`literary_verified=false`；
- Worker在最终发布manifest之前HEAD核对所有块的size与已认证SHA元信息（上限256块）。断线导致的未引用块不会被当成成功的SQL；下一轮按块SHA重试，无需删改R2原文；
- 任一新WF进程只凭原有读Token即可找到当前原文件对象对应的manifest、逐块恢复SQLite，并核验每块SHA、整库SHA、SQLite quick_check和book/source/parser/counts元信息，**只读打开**，临时文件离开进程自动清理；源对象ETag变化会拒绝使用旧索引；
- 旧源对象/索引永久不改；同一原对象存在多个可用manifest时**拒绝盲选一个**，需要显式版本钉住或后续可信catalog裁决。此时还不是完整并发提交服务。

`writerforge/v72_persistent_index_pipeline.py` 将V71成功的真实TXT来源选择、原文Sha、严格中文编码识别、SQLite建索引连接到新R2 writer：先metadata扫描，**跳过已有索引的对象**，才处理下一本≤16MiB的单TXT、安全分类，上传后立刻以只读Token从R2冷读取该索引并复验。新旧凭据与源内容只在WF运行环境中，不进聊天、公共GitHub和日志。GB18030仍是临时编码判断，只能用于技术SQL索引，**不能自动升级WF文学学习经验**。

## 当前测试及部署真实状态

- **已验证**：Railway真实Python合成测试部署 `17174b98-43f9-47d5-b667-f6155dda0b1e`，旧V68–V71与新增V72总计**44/44通过**，零失败。用内存中仿真R2执行了离线索引上传→新进程只读恢复→SQL查询、重启断点重试、同SHA零重复上传、分块篡改拒绝、原文ETag变化阻断、原文完整不变、读写Token相同拒绝。注意这是离线Mock，**没有新R2远端写入**。
- **Worker协议模拟**：原health读接口200、旧读Token对新上传接口401、新写Token内容寻址上传200、重传200幂等、写原文Key403、最终manifest上传200、只读refs200、chunk HEAD200/Range206；此处是注入WebCrypto替代校验的合成JS路由试验，**不是Cloudflare生产测试**。
- **尚未完成**：Cloudflare真实Worker尚未部署V72代码，用户尚未创建独立的 `WF_INDEX_UPLOAD_TOKEN`（Cloudflare Worker Secret + Railway Variable相同值），所以R2索引写权限**明确关闭**，R2中没有任何已证实由V72创建的永久SQLite对象。绝不把旧V71临时SQLite冒充R2永久索引。
- **无需新存储**：不创建Railway Volume。关于R2计费，见 Cloudflare官方文档 https://developers.cloudflare.com/r2/pricing/：Standard包括每月10 GB-month以及Class A/B请求免费额度，超过部分按R2实际使用结算；与Railway计算费用是两个计量维度，不承诺账户一定零费用。
- **持久化边界**：目前真正实现的是**每本SQL索引的持久对象+身份manifest**；跨400本的分类与显示编号`catalog`持久总表、跨作品语义索引、RAR/EPUB安全处理、分书>16MiB的建索引预算扩展、全库持久断点任务队列及多写者并发清算还需下一阶段专门设计。所有这些以后也只存R2，不回退Railway永久盘。

## 用户唯一需要手动完成的云端权限操作（不向GPT提供密钥）

1. 打开 Cloudflare 现有 Worker `wf-r2-api`，保留现有`WF_R2`绑定和原`WF_API_TOKEN`；**新增单独随机高强度的 Secret：`WF_INDEX_UPLOAD_TOKEN`**（不可与WF_API_TOKEN相同），将本分支的 `cloudflare/wf-r2-worker-readonly.js` 保存到该**已有Worker**并正式Deploy一次。
2. 在已有Railway项目 `WriterForge` → 服务 `wf-python-r2` → Variables，设置同名 `WF_INDEX_UPLOAD_TOKEN` 为**与Cloudflare相同的密钥**。值不要贴聊天/GitHub。现Railway连接可以读取是否存在变量名，但不能取回用户私密值。
3. 完成后告诉助手「V72已部署和设置写Token」，由助手在Railway让WF实际处理一份受限的真实作品，把index上传到R2，再使用**一个全新Python进程只读冷恢复**证明跨运行持久；确认无损后才批量处理25→43候选，不要先跑400本。

若不愿给Railway永久写Token，也可以以后使用手动短期授权临时设置再撤销；不擅自提升现有Reader Token的权限。

## 后续验收与安全界限

V49 `THIRD_STRIKE_FAILED`、第二课程窗口`LOCKED`不因完成R2存储而改变。本版本不调用文学模型、不写原著、不把检索摘录塞入WRITE，也不暗示已验证人工文学理解。冷恢复+SQL查询属于工程能力；真正意义上的独立文学回答须以后另外设计盲测。

## 安全等待模式的实际Railway机器结果（补录）

部署 `5ea343ea-cccf-48e6-84b7-6b99fcc388b6` 已真正在现有 `wf-python-r2` 服务运行，状态 SUCCESS：`WF_V72_AWAITING_OWNER_R2_INDEX_WRITER_SETUP`，`read_token_name_configured=true`、`separate_writer_token_name_configured=false`、`cloudflare_worker_routes_verified_live=false`、`index_written_to_real_r2=false`、`network_attempted=false`、`railway_volume_created=false`、`cloudflare_mutations=0`。当前固定启动指令 `python -u wf_railway_v72_wait_setup.py` 且restart policy NEVER，不会后台循环或触发真实R2上传。原本44/44合成测试通过的部署 `17174b98-43f9-47d5-b667-f6155dda0b1e`独立保留。

V72真实索引入R2尚须用户完成Cloudflare Worker一次部署、在Cloudflare和Railway各添加**同名且相同内容**的新写入Secret。没有Cloudflare管理接口能由GPT替用户安装该Secret；不可把用户新值粘贴聊天或公共GitHub。真实上传、持久恢复结果待未来两次独立Railway单次运行验证。

## 2026-10-19 真实路由与权限探针（新增证据）

用户说「试试吧」后，Railway变量名审计证明原`WF_API_TOKEN`和独立`WF_INDEX_UPLOAD_TOKEN`均已配置（不读取、不打印值）。新增 `wf_railway_v72_safe_live_probe.py`，由原Railway服务运行真正的Cloudflare Worker / R2认证接口测试；真实部署 `006f6a7e-614a-4741-b5fa-0ca7376007cd`：`WF_V72_LIVE_READER_AND_WRITER_ROUTES_VERIFIED`，退出0。真实reader身份访问空合成source hash的索引Refs返回成功；writer身份故意上传哈希不符的极短随机字节包，被Worker如预期返回422/拒绝，证明新写入Token已可认证、SHA校验启用；该探针0原著下载、0真实R2索引对象创建、0原著修改。**这只是写入权限/拒绝测试，不是正式持久索引发布结果**。

之后才允许调用单书`wf_railway_v72_publish_one.py`（带一书预算和索引写入），真实结果另记。紧接着必须另起一个**全新**Railway Python进程，以`wf_railway_v72_cold_restore.py`、仅reader凭证恢复索引并验SQLite，方可宣称永久存储完成。失败时保留错误并停止重复写入；不改真实R2源对象。

## 2026-10-19 V72 真实双进程生产验收（非Mock，永久索引已在用户私有R2）

用户回复「试试吧」后，先确认Railway的独立索引写入变量名已配置、和原有只读变量分开，不读取/回显密钥值。

1. 独立权限门槛，Railway `006f6a7e-614a-4741-b5fa-0ca7376007cd`：已用旧Reader成功读取空哈希索引清单，新的Writer Token身份向 **SHA错误的虚拟chunk key** 发送极短PUT，Worker正确返回422，0对象创建；`WF_V72_LIVE_READER_AND_WRITER_ROUTES_VERIFIED`、退出0。
2. 第一份真正R2永久索引发布，Railway部署 `fb5c2321-d45d-4fd0-9ec7-307e3ae68086`，程序 `wf_railway_v72_publish_one.py`：用户私有R2四目录扫描成功，从`科幻`类别依保守小文件规则选出一个真实TXT（3636548字节），原始文件 SHA256为`85a22ee62328f2948cd4c2239d9930a939d3b36d221b49510f9896e739e9d920`。WF创建36,274,176字节真实SQLite FTS5索引、65,573索引单元、499疑似章节标题，按1MiB切块，**新写入35块+不可变manifest**至用户现有私有R2。`index_sha256=a3eb5e24bb858a078ece3d5e56ffc4805e9e51eebe53715037701049422d7ec8`，`manifest_sha256=01510d79c6d5b60212e3f4dc051901ee8cfabd0481070c33248630dc2b7b787a`，以现有Reader路由成功恢复/检查SHA/SQLite，`WF_V72_INDEX_PERSISTED_IN_PRIVATE_R2`，`WF_V72_R2_PUBLISH_EXIT=0`。原著0写/模型0调用，无任何私有章节、书名正文到GPT/公共GitHub。编码仍为`provisional_legacy_charset=true`，不可计文学能力晋级。
3. **最关键的跨进程恢复**，另建Railway全新部署`cc78dd59-27f9-4336-91c3-3da41c7783e8`，程序`wf_railway_v72_cold_restore.py`启动时首先在该进程环境内 `os.environ.pop("WF_INDEX_UPLOAD_TOKEN",None)`，由真实日志确认`writer_token_available_to_this_process=false`，只留Reader Token。它从R2恢复完整**36,274,176字节**索引，验证原R2源ETag对应/manifest/所有数据块SHA/整库SHA/SQLite quick_check、读权限及65,573条单元，用内部自生成字面查询成功回读。状态`WF_V72_COLD_RESTART_RESTORE_VERIFIED`、`WF_V72_COLD_RESTORE_EXIT=0`；**0原始小说正文下载、0写入请求、未用Railway持久卷**。此证据正式证明：至少**一份**真实WF SQLite索引在用户私有R2存储后，跨Railway容器仍然可检索，且只读Token已足够完成恢复。
4. **停止条件**：以上只对应一部TXT，不说明目前已建立43或400部SQL。50部统一文学成果门槛及原V49 `THIRD_STRIKE_FAILED`/第二窗口`LOCKED`不变；未对文学语义做考试。下一阶段须把每类别递增编号/单源稳定索引等元数据持久化成安全R2 catalog、完成真正的跨书查询和批处理状态机，统一保障断点恢复、多版本裁决、无重复上传、原著变化后的索引失效。不许在未限定预算时批量建完400本。
