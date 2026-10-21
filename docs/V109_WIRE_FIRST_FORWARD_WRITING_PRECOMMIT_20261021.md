# WriterForge V109：供应商原始响应先保存，再执行 F 写作（2026-10-21）

**本文件先于任何V109新模型请求完成。** V106首模型提纲结构红色、V108原始5次调用的E/F缺陷都不可覆盖、不可重复消费；原生产Railway持续安全idle。

## 1. 从 V108 真实失败读到了什么

V108共享两事件WF模型提纲来自私有R2 CAS `718a76ff2816ced4cf2f5780d56718ea928888be14d6c2c1bc185b321bec168f`，已通过V96。真实总清单 `dc5b6095174acb350426192c44159783026cb647e0dce21bc528eba8111f2f6e`；5次真实请求报告输入3087 + 输出2040 tokens。

E第一次正文原始CAS `cbd9af5fdb29c193af093a51dba2972a06a3b08da0e20642ad4d3d5ff5ad8f9e`，471含标点码位。E正文含有可见行动与情绪，但V96拒绝原因不是句子有错，而是同一次JSON `trace.parent_effect_quote` 引用了“站长选择切断矿钻供电，优先供给通风与生命维持”这样的**章节计划总结**。这不是前一个真实写出事件，因为第一段没有前件。拒绝状态 `WF96_UNDECLARED_PREVIOUS_CAUSE` 必须留红，不能悄悄把模型JSON字段改成null冒充真回答。

F章计划也合法地输出 `horizon.choices` 两条未来；F首个正文请求进入 `WF_FLASH_INVALID_JSON_RESPONSE`，旧DeepSeekFlashModel未对**无法被JSON解析的供应商HTTP响应**提供原样CAS封存回调，故该次真实付费回复缺完整字节证据。不能猜它是否JSON破损、finish_reason异常还是输出了自由文本。

独立读取证已在隔离Railway部署 `246de149-69e9-4fad-a094-47e3e9fa4234` 返回 `WF108A_FIVE_PAID_ATTEMPTS_FOUR_JSON_REPLIES_COLD_VERIFIED`，模型0调用、R2写0。

## 2. V109底层修复与新一次性实验

修改 `writerforge/deepseek_flash_model.py`：仅在调用方显式传入 `on_response_wire` 回调时，供应商transport返回原始字节后、**任何JSON解析、完成原因和模型答复结构校验之前**调用，供私有R2 CAS写入和SHA验证。默认没设置回调时，所有旧V74+学习程序行为完全不变。测试覆盖无效JSON、finish_reason=length、有效JSON、传输超时无响应、私有写入失败不重试。

修改V96候选写作指令：首段没有causal_parent时 `trace.parent_effect_quote=null`，不能把计划概括当成已经写出的后果；后续段落必须引用真实前幕效果，原严格校验没有放宽，不代替WF设计小说情节。

为控制额度，本轮不重复生成E，也不再要求WF付费重做已经有效的公共两事件提纲。新唯一实验 `WF-V109-F-ONLY-WIRE-FIRST-UNIQUE-20261021` 使用**由WF自己生成且已冷验证的原共享两事件**，固定相同深海场景/设备限制，仅执行新的F文学前瞻创作链，最多4次新DeepSeek Flash调用：章规划2400、首段1450、滚动规划650、次段1450，总输出预约5950，保守总预算150000，不能自动重试或返工。旧V106/V108付费请求原样保存。

每一次调用必须先把request intent私有CAS和地址写入日志，然后真实模型返回HTTP wire时即时存私有CAS并写SHA；当wire不能解码时仍留原完整响应供事后零模型读取。不管是否能解码，均不根据本轮单一样本宣布文学改进。若完整正文可生成，只是一个未接受的F真实候选，随后独立检查是否真的遵守能源、人物信息、行动选择、代价与后果，而不只看结构字段。

**实验局限**：调用本身仍依赖同一家DeepSeek Flash的预训练能力。临时published snapshot仅用于兼容WF现有local VerifiedWritingFlow接口，是一条中性的synthetic软件连接数据，绝非原15章已学会写作的证据；当前不能证明跨作品迁移。F没有同步E等资源对照，不能宣布F胜利；独立文学盲评仍未执行。

## 3. 安全约束

用户原私有小说、前15章、V49第三次失败、第二文学窗口LOCKED、V97七次、V103五次、V104十一、V106一次和V108五次都不改、不重播。本轮尚未执行新模型付费请求（写本文件时），CI必须先全绿才可动隔离一次性Railway服务；原生产 `wf-python-r2` 不更改。
