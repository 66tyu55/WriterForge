# WriterForge V75｜DeepSeek Flash 已真实联通；WF 自己的逐段首读与 R2 学习账本（2026-10-19）

## 最新用户交接

用户上一轮选定官方 `deepseek-flash` 作为 WF LEARN 模型，随后回复「ok」，表示已完成在原 Railway 服务设置 `DEEPSEEK_API_KEY`。不得让用户重复申请、贴出密钥或从头创建 R2 项目。

**已取得真实成功**：Railway `106940c9-c1fb-4d51-a852-43adf5aec6f7`，原 `wf-python-r2` 服务通过官方 DeepSeek 的 `/chat/completions` 实际调用 `deepseek-flash` 1 次；`WF_V74_DEEPSEEK_FLASH_REAL_API_PROBE_OK`、退出码0，prompt tokens 113、completion tokens 12，返回符合预注册合同的 JSON。探针只用了人工合成字符串，**没有发送任何小说、读取R2或开启文学学习**，没有回退Discovery。此后无需再让用户配置`DEEPSEEK_API_KEY`。

V73真实问题不变：WF 自主选择一份真实R2科幻TXT做文档入学检查，旧宽松规则499个章头，严格规则495，4个差异，295次印刷章号重复、3处重置或倒退，GB18030来源编码尚为暂定；WF正确停在`WF_DOCUMENT_ADMISSION_REVIEW_REQUIRED`，实际文学学习0章。不要由助手擅自判定真实500章/人工替其修编号。

## V75 将哪些责任正式交给 WF

独立开发分支 `v75-wf-immutable-learn-journal` 从V74继续，未修改 main、已部署Cloudflare Worker、真实R2原著与V72 SQL永久索引，也没有自动触发GitHub Actions。

- `writerforge/wf_sequential_learning_trial.py`：WF自己的**受限两至三原文单位协议演练**，每次只向 DeepSeek 发送**当前解锁片段**，不能在第一次读第一段时把第二段或下一章塞给模型。模型按固定JSON结构提交读者反应，WF检查结构后逐单位写私有R2；第一读全部单位签收并seal之前，不能向分析模型发源内容。签收后 PASS B 依据之前的真实来源hash提出机制假说，不允许将自评当正式毕业。
- `writerforge/r2_learn_journal.py`：全新WF私有LEARN日志客户端，支持按来源SHA、章节、单位序号构造不可变R2对象Key，客户端校验来源标识/React JSON/不回显原文；每次上传成功必须立刻通过旧读Token从R2校验SHA。重启时可依据原文单位SHA、上一个事件SHA检查既有锁定记录，**从未签收的下一个单位继续，不为已签收单位重复调用付费模型**；PASS B相同逻辑保留已锁定结果。
- `cloudflare/wf-r2-worker-readonly.js` 候选源码保留所有已上线V72 API，新加 `GET/PUT /r2/learn/event?key=...`，对象只允许 `writerforge/v1/learn/v1/` 下来源指纹与6位章号/单位序号；PASS A顺序必须引用前一个R2录入记录SHA；seal只接受真实存在的最后A单位；PASS B只有引用已签收seal且逐项来源单位hash与实际A单元吻合时才可写入。所有R2 LEARN事件单个最大8KiB、仅PUT创建、不DELETE、不覆盖已有不同内容，不允许保存整段原著/大正文。读端只用既有 `WF_API_TOKEN`。
- **单独WF LEARN写入凭证**：`WF_LEARN_UPLOAD_TOKEN` 必须与现有 `WF_API_TOKEN` 和 `WF_INDEX_UPLOAD_TOKEN` **都不同**，新建于原Cloudflare Worker Secret及原Railway `wf-python-r2` Variables。仅它有权限访问 `PUT /r2/learn/event`；索引Writer Token和原著Reader Token不能冒充。
- `GET /r2/learn/writer-ready` 使用**WF LEARN 写入令牌**进行一次纯权限确认（0 R2写），必须先成功，WF才可向DeepSeek发送任何私有章节片段，避免模型调用后没有证据落盘。即使验证成功，后续真实上传仍逐个R2签收，网络失败不冒充成功。
- 所有 PASS A 模型反应仅可被标记为**模型模拟读者反应**，不代表真实人类阅读测量；PASS B机制是**未审定假说**。即便真实PASS A/B完成，文学等级V49 `THIRD_STRIKE_FAILED`/第二窗口`LOCKED`仍不变。V75仅是**两三单位协议试验**，绝不算学完一个完整章节。

## 已执行测试及不能冒充的成果

1. **V74真实模型端点通过**：前述部署`106940c9-c1fb-4d51-a852-43adf5aec6f7`、一次合成JSON输入、113/12 tokens，确实发到了官方DeepSeek Flash，无R2源内容。
2. V75第一次Railway离线回归`11cf6dba-472d-4f1c-af36-bf58502a12f4`：92项合成测试发生13项初始化错误，原因测试夹具假Worker域名`.synthetic.invalid`未通过旧WF对`.workers.dev`的合法性校验。R2零写/DeepSeek零调用；这个失败应保留。修正假域名之后`c31c51a5-ce9c-4385-9857-d71cfd6c812b`真实Railway **92/92通过**。
3. 新增中途重启无重复模型调用回归后，Railway `f9071a1b-38d6-4226-b8c9-84ea95cecc6a`，真实Python **93/93离线合成测试全部通过**。随后增加“写入权限必须在模型发送原文前校验”，Railway `c19ac34c-4d7e-44c3-8a9e-777c53543da5`，**94/94通过**，R2实际调用0、DeepSeek实际调用0。本地Mock验证读者/索引Writer写LEARN均401、PASS B在封存前409、缺前一个first_read409、合法PASS A封存200、错误引用证据409、正确PASS B200、不可变覆写409、旧health200。第二次新的无写入权限ready端点模拟为：独立LEARN写令牌200，Reader及Index Writer各401，旧health200。JS模拟均**不是**Cloudflare线上新增LEARN路由实测。
4. **生产真实 R2 LEARN 对象目前写入0**：V75候选Worker尚未由用户部署，新`WF_LEARN_UPLOAD_TOKEN`还未在Cloudflare/Railway配置；不可宣称WF已完成文学原文首读、PASS A/B或学会一本书。已有V72真实R2中一部SQLite永久索引和跨新进程恢复的成功**原样有效**，但那是检索索引，不是学海训练记录。

## 下一次真实验收（必须由用户完成一次权限部署，密钥绝不发聊天）

1. 打开原Cloudflare `wf-r2-api`，备份旧V72 Worker源码，保留旧 `WF_R2` binding、`WF_API_TOKEN`、`WF_INDEX_UPLOAD_TOKEN`。将本分支 `cloudflare/wf-r2-worker-readonly.js` 作为新候选部署；添加新Secret `WF_LEARN_UPLOAD_TOKEN`，值为独立随机高强度秘钥（不能复用旧2个）。
2. 在原Railway `WriterForge` → `wf-python-r2` → Variables 添加同名`WF_LEARN_UPLOAD_TOKEN`、值与Cloudflare新Secret相同；不要提供给GPT、GitHub或其他网站。
3. 用户说「V75 Worker 已部署」，WF在Railway先执行**真实0 R2写的writer-ready/旧reader隔离探针**，确认新路由，不直接花DeepSeek额度或下载小说。下一步在正式获得用户认可的第三方API原文传输范围内，让WF自主选择**章次结构无冲突且编码可靠**的作品，一次仅2-3首读单位，按实际R2持久证据走PASS A→seal→PASS B；换新的WF进程按R2学习日志冷恢复，报告真实模型调用/实际费用、序列SHA与错误。无法找到无冲突来源则停机，不能让助手偷偷挑一个正确答案。
4. 技术试验成功后才扩展到每章完整来源单位、分类依据、八线、章后学习复盘及R2个人经验状态；后续需评估模型输出大小与R2操作次数/预算，不能一次付费学习400本。

**禁止变更**：不得上传原著至公共GitHub/GPT聊天；不得把自己设计好的分类作为WF已经理解；不得启动GitHub Actions邮件通知；不得因技术进度篡改V49失败/文学晋级状态。不需要再配置DeepSeek模型Token，那个连接已真实成功。


## 最终Railway安全待命生产证据

部署 `5803a081-8090-4a2b-8f67-0d6d53b9ebe1`，原`wf-python-r2`运行`wf_railway_v75_safe_idle.py`，真实`SUCCESS`与`WF_V75_SAFE_IDLE_LEARN_JOURNAL_PENDING_DEPLOY`。已有DeepSeek Key存在，官方API上一阶段`106940c9-c1fb-4d51-a852-43adf5aec6f7`已用一条合成JSON测试成功；原R2 reader/index writer存在，新的`WF_LEARN_UPLOAD_TOKEN`仍不存在，Cloudflare V75 LEARN接口未线上验证。这个safe idle运行费用模型调用0、R2读取0、R2写0、不执行任何文学训练，不创建Railway卷。V75代码已保存在独立分支而非已覆盖实际Cloudflare Worker。

用户后续明确确认Cloudflare部署和同名Railway LEARN专用Secret前，严禁偷偷调用真实小说进行PASS A/B。V49文学毕业历史失败/第二窗口LOCK仍保留。
