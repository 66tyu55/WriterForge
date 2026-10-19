# V77｜不再要求第四个密钥：复用现有 R2 索引写入凭证（2026-10-19）

## 用户纠正与决定

用户给出的 Railway Variables 截图明确存在：

- `DEEPSEEK_API_KEY`：WF 调用 DeepSeek Flash。
- `WF_API_TOKEN`：WF 通过现有 Worker 只读原著、SQLite、LEARN 记录。
- `WF_INDEX_UPLOAD_TOKEN`：此前 V72 已真正用于 R2 受限 SQL 索引上传，并可用于新的 LEARN 事件写入。

前段 V75/V76 多次要求用户额外配置 `WF_LEARN_UPLOAD_TOKEN`，**这是助手主动设计的更严格权限隔离，不是 DeepSeek 或 Cloudflare 的硬要求。用户没有遗漏密钥，也无需继续申请第四个**。V77 将它撤销，避免反复要求用户做配置。

安全权衡：WF 的 SQL 索引写入和 LEARN 学习日志写入共用现有 Writer Token，泄漏该Token会同时暴露这两个写入命名空间的修改风险；但是 Worker 对两类对象仍做完全独立的路径白名单、JSON/哈希/顺序/不可变创建校验，且**绝不开放R2原著的PUT、DELETE或任意前缀写入**。Reader Token 保持只读，独立监督必须使用 `read_only=True`，即使所在Railway进程配置Writer Token，也不自动继承。此架构是权衡简洁性与密钥隔离，不能声称拥有原来四个密钥的权限独立性。

## V77 真正代码变更

- `cloudflare/wf-r2-worker-readonly.js`：将 `GET /r2/learn/writer-ready` 和 `PUT /r2/learn/event` 鉴权统一改为现有 `WF_INDEX_UPLOAD_TOKEN`，仍拒绝与 `WF_API_TOKEN`相同的配置；旧 V72 `/r2/index/write`保持，LEARN 仅允许 `writerforge/v1/learn/v1/` 下规范事件，先PASS A按单位SHA链、后seal、再PASS B；不支持DELETE/改写已签收事件。**不再读取 `WF_LEARN_UPLOAD_TOKEN`。**
- `writerforge/r2_learn_journal.py`：默认Writer取 `WF_INDEX_UPLOAD_TOKEN`，新增显式 `read_only=True`。在只读模式下不会继承Writer环境变量，禁止传入Writer Token；普通WF实例需真实writer-ready鉴权通过再允许调用DeepSeek。
- `writerforge/wf_batch_supervisor.py`：独立考官验证时既检查 `writer.read_only=True` 也检查 `writer.writer is None`，拒绝“借了写权限的独立考官”。
- `wf_railway_v77_shared_writer_probe.py`：用户真正部署新 Worker 后，先进行**0写入**线上验证：共享Writer的`writer-ready`必须返回200，旧Reader必须被401拒绝，独立考官没有Writer；不下载小说，不调用DeepSeek。
- `wf_railway_v77_safe_idle.py`：服务默认不联网、不读小说、不调用付费模型、不写R2，确认现有三个变量即可。

## 已执行测试与未完成的部署

新V77 Python继承并运行 V68—V76 合成回归，真实Railway部署 `12ae1f2c-d699-4024-abfb-23cd55ecfea7`，**119/119通过**，0错误、0失败、0实际R2访问、0模型调用。新增共享写Token及强制只读监督测试通过。通过独立V8模拟运行新的候选Worker JS，验证共享Writer的`writer-ready=200`、Reader拒绝401、原著写拒绝403、LEARN PASS A顺序和seal/PASS B先后、事件不可覆写、原著路由原样存在；模拟JS**并非Cloudflare线上部署**。Delete使用Writer身份会被Reader权限拒绝401（同样不能删除），不是写入成功。

**尚未发生**：用户现有Cloudflare Worker尚未被证实部署V77候选源码；真实LEARN事件R2对象写入仍为0，真正DeepSeek朗读私有章节仍为0。B00首批六个真实R2 TXT全因编码暂定/章号等严格条件未过，不能为了“开始”擅自补成已通过或给WF一份考官代写的原文训练文。

## 用户唯一剩余的配置动作（不增添密钥）

打开 **Cloudflare 现有的 `wf-r2-api` Worker**，在不改任何R2绑定、变量和Secret的前提下，将原脚本备份并替换为V77完整源码，再点击 Deploy。**不需要**添加 `WF_LEARN_UPLOAD_TOKEN`、不需要修改Railway的三个密钥、也无需新建R2桶或Railway持久卷。候选Worker代码：

https://github.com/66tyu55/WriterForge/blob/v77-self-charset-source-audit/cloudflare/wf-r2-worker-readonly.js

用户告知“Worker已刷新”后，助手运行只读Writer权限探针以证明线上LEARN路由可用，然后由WF自行复核B00已冻结的仙侠465/465章节候选的全文编码与版次，决定何时进入小预算B01首读；不能再重复索要第四个凭证。V49 `THIRD_STRIKE_FAILED`与第二课程`LOCKED`继续有效。
