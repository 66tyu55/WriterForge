# WriterForge V74｜WF 自己的文学学习模型切换为 DeepSeek Flash（2026-10-19）

## 本轮用户指令

用户提供 DeepSeek 官方 API 截图，并明确说「换成deepseek flash吧」。**最新选择**：WF 之后新启动的文学 LEARN 调用只选 DeepSeek 官方 `deepseek-flash`，不走 Discovery，也不退回已退役的 `deepseek-v4-flash`。原有 `writerforge/reverse_discovery_models.py` 和历史V31等不删除，以确保旧失败证据完整，但不再被新WF LEARN模型注册表调用。

经DeepSeek官方文档核对（2026-10-19）：
- OpenAI兼容 base URL `https://api.deepseek.com`
- Chat Completions `POST https://api.deepseek.com/chat/completions`
- 模型ID `deepseek-flash`（当前运行DeepSeek-V4.1-Flash-1017）。
- 密钥只能由用户自己在现有Railway服务 `wf-python-r2` → Variables 新建 `DEEPSEEK_API_KEY`，**不要把值粘贴给GPT/GitHub/聊天日志**。此变量与 Cloudflare R2 的`WF_API_TOKEN`、`WF_INDEX_UPLOAD_TOKEN`完全不同。
- DeepSeek 默认开启thinking；V74的 JSON-only 文学入门阶段明确 `thinking={"type":"disabled"}`，同时 `response_format={"type":"json_object"}`，并在system prompt中提供JSON要求；此处是为了可控结构化与小额试验，并非对深层文学推理强度的最终配置。官方帮助：https://api-docs.deepseek.com/zh-cn/api/create-chat-completion/ 、https://api-docs.deepseek.com/zh-cn/guides/json_mode/ 。

## 实现与安全门

隔离分支 `v74-deepseek-flash-wf-learn` 从V73真实WF入学检查分出，不修改main/已有Cloudflare Worker/R2源文/永久索引。不触发GitHub Actions。

1. `writerforge/deepseek_flash_model.py`：Python标准库HTTPS官方固定端点，不允许重定向、输入不超过16KiB、响应不超过64KiB、输出单次最多1500 tokens；强制系统 JSON 格式，解析并验证choices/finish_reason/内容JSON对象，`finish_reason=length`不能升级成功；没有供应商超时自动重试（超时可能已扣费）；原文和Bearer不能进日志。角色仅`genre_classification`、`first_read`、`craft_analysis`，不把模型自动当作者或独立考官。
2. `writerforge/wf_learn_model_registry.py`：新的WF LEARN默认注册唯一DeepSeek Flash；无新密钥便拒绝模型执行、不自动降级到Discovery。**即使DeepSeek密钥已配置**，V73之前发现的章节结构冲突以及尚未部署的**独立、不可变R2文学LEARN首读账本**仍须先解决，因此不会直接打开正式逐章训练。当前模型的选择和健康不代表已读书或文学能力晋级。
3. `wf_railway_v74_deepseek_probe.py`：用户在Railway配置密钥后，助手可以运行一次**仅合成JSON**的真实DeepSeek API探针，cap 120输出tokens、最多1次调用，不发送任何私有小说/封存考题。如果没有密钥，安全返回 `WF_V74_WAITING_FOR_DEEPSEEK_API_KEY`，不联网，也不尝试R2。此探针有可能发生少量DeepSeek API费用。
4. `wf_railway_v74_tests.py`：在真实Railway Python中先移除所有DeepSeek/R2写入/旧Discovery密钥，仅运行离线仿真；HTTP与JSON/OAuth端点/重定向拒绝/过长截断/预算限制/无自动重试/无隐式写作技能晋升、前面V68—V73的SQL与章次测试一起回归。
5. `wf_railway_v74_safe_idle.py`：选中 DeepSeek Flash 但**不自动调用付费API、不读原著、不写R2**；保持V49 `THIRD_STRIKE_FAILED`与文学第二窗口`LOCKED`。

## 与 WF 自学流程关系

用户已经纠正过职责：「分类、编号、章节、文学学习都该属于WF」。这一方向不变。V73真实R2发现这部私有科幻TXT有强规则495章、旧宽规则499章、4个冲突标题哈希、295次印刷章号重复、3处编号重置；WF必须自己检查这些证据而不是由GPT补正。引入DeepSeek Flash是给WF配备可调用的文学判断模型，不是让GPT替WF做分类和读者反应，更不是让模型出现JSON就把错误转换成真实文学经验。

将来逐章真实学习步骤：
1. WF自己在R2决定读哪本，确认来源哈希/字符编码/章头冲突状态；
2. **只把当前允许看的原文片段**交给自己授权的DeepSeek Flash模型（通过DeepSeek服务进行外部数据处理，模型服务商可能看到本次请求内容，需用户意识到此数据流）；
3. PASS A的原文片段和首次读者判断必须有不可变R2私有日志签收，再允许独立的PASS B分析；禁止提前看后文/编造已阅读内容；
4. 按章复盘错误和经验，验证经验是否改变下一章或下一本的决策，学习记录存R2，0章不得冒充500章；
5. 外部盲测与V49失败/LOCK保持独立，不能由同一模型给自己晋级。

**此版本首先只验证模型代码、用户密钥和合成接口。没有DeepSeek密钥不能测试真实API；没有R2文学学习事件日志不能把第一章训练说成已完成。**

## 当前执行回执

（Railway离线测试、真实DeepSeek探针状态和safe-idle部署须在后续日志实际出现后填写，绝不预写通过。）

## V74 已取得真实 Railway 回执（模型连接仍待用户API Key）

1. Railway真实Python离线回归部署 `31ff6322-1a0b-47e0-b830-309e341fec25` 成功，`WF_V74_OFFLINE_REPORT`：79/79 passed，0 error/failure，0 DeepSeek调用，0 Discovery调用、0真实R2读写；以合成JSON HTTP数据检验严格输出/截断/超时/权限/模型名。
2. Railway真实安全模型探针部署 `0149afea-973b-4115-a94a-a6e2759fdca4`成功，`WF_V74_WF_LEARN_MODEL_SELECTED` 显示`model=deepseek-flash`、`provider=deepseek`、`discovery_used=false`；随即`WF_V74_WAITING_FOR_DEEPSEEK_API_KEY`，`key_present=false`、`no_network_requests=true`、`model_calls=0`、`originals_sent_to_deepseek=false`、`R2_mutations=0`，程序退出0。**因此适配器与项目配置切换已完成，官方DeepSeek的真实API联通尚未验证，也没有启动WF文学PASS A/B。**
3. Railway服务变量列表只有原有 `WF_API_TOKEN` 和 `WF_INDEX_UPLOAD_TOKEN`；`DEEPSEEK_API_KEY` 是新增需求，必须用户自行申请官方API Key并仅在Railway `wf-python-r2` Variables里配置，不得给GPT/GitHub。Cloudflare的R2 Worker无须改动。即使Key上线，文学原著片段送DeepSeek前仍要先保护分卷/章节冲突和私有R2不可变首读学习日志。

模型迁移目标现已固定，切忌因为错误的API Key返回401就自动回退Discovery/OpenRouter。后续恢复时先查询Railway密钥**名称**是否存在，再手动执行一条仅合成文本的DeepSeek探针，绝不重复无意义地下载私有小说。

## V74 生产安全待命最终验收

Railway真正最新部署 `e467dff7-4383-4f9a-b050-8ec89fc33272` SUCCESS：`WF_V74_SAFE_IDLE_DEEPSEEK_FLASH_SELECTED`，`WF_LEARN_PROVIDER=deepseek`、`WF_LEARN_MODEL=deepseek-flash`、`discovery_model_selected=false`、`official_deepseek_key_present=false`、`paid_model_calls=0`、`real_source_books_read=0`、`R2_writes=0`、`WF_first_read_immutable_r2_journal_ready=false`。用户无需重传R2原文，也无需更改Cloudflare Worker，且不应向聊天提供密钥。
