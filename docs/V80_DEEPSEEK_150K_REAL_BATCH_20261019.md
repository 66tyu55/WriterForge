# V80｜WF 正式扩大到 150,000 Tokens 批次预算（2026-10-19）

## 用户指令与实现边界

最新用户指令：「这样不行--训练必须放大---最大token提高到15万」。旧V79确实只读了仙侠第一章首3/15单位，并耗费4次DeepSeek Flash API、3,257 Tokens，完整文学章数0。用户要求放大真实训练并明确上限：本轮按**单批次输入+输出总计150,000 Tokens**作为硬上限，不再被旧4次调用/2000输出限额阻断；官方DeepSeek Flash当前公布1M上下文、单请求最大输出384K，150K范围在API允许之内。官方参见 https://api-docs.deepseek.com/quick_start/pricing/ 与 https://api-docs.deepseek.com/api/create-chat-completion/ 。**150K是预算上限，不是必须生成150K没意义的文字或保证恰好扣费150K。**

原R2来源、书籍ID、三个Secret不变：`DEEPSEEK_API_KEY`、`WF_API_TOKEN`、`WF_INDEX_UPLOAD_TOKEN`。没有第四个学习Token、没有重新部署Cloudflare Worker、不把原著传给GPT/GitHub、不启动GitHub Actions，也不覆盖原著或既有SQLite。

### 真正扩大训练的顺序

本批仍为旧B00冻结的一部仙侠原著（source file SHA `0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd`，4009069字节）。WF无需再换书/复制到本地；V80字节审计程序检查前6章的源hash和顺序：
- 第1章6022字符/15单位；
- 第2章4992字符/12单位；
- 第3章5707字符/14单位；
- 第4章2370字符/6单位；
- 第5章2246字符/6单位；
- 第6章3607字符/9单位。
总计62个真实首读单位，第1章首3个已在V79付费读过，V80只应新读后59个，不得给已签收记录重扣费。

每个单位先提交DeepSeek Flash首读（JSON注意力、困惑、疑问、预测、变化）；WF立即存R2不可变小CAS及校验，才开放下一单位。全章读完后封存A再用模型在真实已读source_unit SHA和原文上解释文学机制，另调用复盘模块找错误、下一章策略、未解问题，将经验CAS保存，并把策略输入下一章首读。**第1章V79在只读3单位时已提前调用过一次B分析，不能假装这一章所有A都早于任何B；V80保留旧seal、早期analysis和新的混合历史完整章补充分析，标不纯。第2章之后才是清洁的完整PASS A→B。**

### 模型预算和反作弊修改

- `writerforge/deepseek_flash_model.py` 支持显式`FlashBudget(max_calls=96, max_reserved_output_tokens=150000, max_total_tokens=150000)`；实际DeepSeek接口可接受单请求参数max_tokens至150k，但章节分工仍合理使用每单位900输出、全章分析3500输出、复盘1600输出。**不把大额度等同强制长文本输出**。默认旧用例保持4800输出预算、4次请求，不会因为新全局能力误给全部任务大额度。
- 每个请求发送前按Unicode UTF8请求字节+协议余量+最大可能输出**保守占用150k预算**；收到可信供应商usage才换成实报prompt/completion Tokens；网络超时/失去usage不退回上限，防隐形重复扣费。超过150k（或96次预注册调用）就自动停止、不重试。
- `writerforge/wf_api_usage_supervisor.py` 仍输出请求时间、role、token、哈希、失败原因；**不输出原文、密钥和文学答案**。
- `writerforge/v79_provisional_r2_cas_journal.py` 原有R2内容寻址存储只允许旧SQL索引小块前缀，未冒称Cloudflare真正部署的原生LEARN事件目录；V80可追溯地允许V79试验所封存首3单位之后第4—15单位继续，旧seal及分析不可改，新章另起干净的完整passA/B CAS链。扩大checkpoint事件上限到320。
- `writerforge/v80_large_chapter_batch.py` 每章写R2不可变首读、封存、后验机制、WF自己提出的经验策略和批次进度CAS; 学习跨章行为变化仅指**WF确实把上一章自己的策略作为下一章阅读输入**，未证明它正确或作者认可，不能直接晋级。原V49 THIRD_STRIKE_FAILED/第二窗口LOCKED保持。

## 执行状态与失败证据（运行中）

1. 新`wf_railway_v80_source_plan.py`真实Railway `2de3fa17-14a0-457a-ba3c-1d5b6c187e21` 验证前六章的SHA/字符数/单位数，原文不出Railway，模型0、R2写0。
2. 首次新模型预算回归Railway`00ac7b75-db1a-42fd-ac66-53ff3500a28f`，145项中1项红色：旧model默认不小心继承150k可输出额度，破坏旧防超额测试。**已保留原红色证据**；改为小试验默认4800、明确启用新150k后，Railway `cd37482a-ac70-46c2-99e5-9f156072d6fc` **145/145通过**（无实际模型/R2访问）。
3. 首次真正V80训练 `9afc913e-ea3a-49d1-8afa-9e32e8df7949`：从V79最后R2 CAS恢复旧5记录，真正WF续读第一章第4—15单位并全部存R2；进入全章分析时DeepSeek返回有效JSON但是不合固定schema，WF诚实返回`WF_V80_ANALYSIS_RESPONSE_NOT_BOUNDED`并暂停，真实调用13次/已扣实报**11243输入+2271输出=13514 tokens**（包括失败分析，不抹除）。当时最新R2 checkpoint SHA `3d12c9e555cfa7b1dd0ce5074e57ec3473bc6d22735e0677b8808b3d953f9e49`，**此前15个单位不允许重读收费**。
4. 已修复分析JSON包装与来源绑定规范化，若合法JSON形状不规则只允许一次**另计费的格式修订调用**（不会偷偷重试超时请求，也不让WF编造未阅读来源）；下轮模型预算初始化从上一轮13次、13514真实Tokens扣除，相关R2 CAS恢复SHA固定。真实Railway离线`b7c55010-fce2-458a-813f-de42585fa9ab` **147/147通过**。重新训练部署 `4b002381-c140-4c90-b2f5-e87e683d111a` 于本文件写入时仍在运行，结果须以其最终日志核实、不得预写成功。真实已看日志表明第1章15单位全部存R2并生成新的全章补充分析与经验卡，第2/3章已经开展首读；完整结论稍后补充。
5. 预先新增`writerforge/v80_independent_exam.py` 和`wf_railway_v80_reader_only_exam.py`：待训练完成/暂停后，必须另启动全新只读Railway进程，重新下载同一原文计算每章每单位SHA，与R2 CAS日志逐个对照、核验封存→分析引用→跨章经验链、保留V79首章早析例外。考官必须移除模型和R2 Writer变量，不能直接采信WF自己的“All good”布尔声明，也不能因此评文学等级。
6. 本批 **会自动停在第6章或15万输入+输出上限/96个调用中最先发生的条件**；即使中途有原著章次或模型格式/网络故障也会输出最后R2 checkpoint，绝不自动再付费重试。训练成功多少章都不等于完成古典、玄幻等其他类别。 
