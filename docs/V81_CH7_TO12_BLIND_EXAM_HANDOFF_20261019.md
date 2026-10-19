# V81 · 从第7章续训 + 独立文学经验对照（2026-10-19）

## 用户许可与冻结的预算

V80已完成同一部私有仙侠TXT的前6章（其中第1章有旧V79三单位先分析的混合历史），真实73次DeepSeek Flash请求、83,363输入+输出Tokens，独立只读R2考官已确认62个单位完整来源覆盖及第2—6章5个严格先A后B。第6章经验不可变SHA：`1d0ee736b199f9af4c04543ba4d7d620ca8e1565b31b25ca673bef610c2b2d9d`，V80训练进度SHA：`f606f5216f82fd40a7893cfe8942e2454efe94b9f1389110bdc37f19f3a4f227`，R2 journal SHA：`0b24a62a697b11e140477225728375fc406cd035fe921ad8ca5476b48a674240`。用户对“从第7章继续，同时加入独立文学测试”回复「可以」。

WF新批次 `WF-V81-150K-20261019-CH7-12` 不重新调用模型读前6章，先从R2完整校验V80 source、batch、chapter6经验卡SHA，读取经验中 `next_strategy`（不在日志公开内容），将它作为第7章的阅读策略输入。仍然只使用早已有的三个环境变量`DEEPSEEK_API_KEY`/`WF_API_TOKEN`/`WF_INDEX_UPLOAD_TOKEN`，不需要第四个Token、Cloudflare新Worker部署或原著经过GPT。

**真实零付费来源先验检查**：Railway `21111116-d487-422d-99fb-bcb8e3b4eb28` `WF_V81_LARGE_BATCH_SOURCE_PLAN_VERIFIED`，原B00 cohort、单本小说SHA与原R2对象不变，严格GB18030解码且两套章头规则一致。第7—12章原文字符数/来源单元数分别为：
- 第7章：3727字符，9单元，SHA `5c3ce522fe014b5d0a6c2cdcd9f872bf2841773d07a29a0939489a6062a82771`
- 第8章：3295字符，8单元，SHA `80ec84e17807cf8d344c7a21402b7bd3222aeee0689c5ef7368336124f75874d`
- 第9章：4004字符，10单元，SHA `1fe46188c71b697f3bfc14b81327f0c7bd8184e124275aedde38c86e4010755f`
- 第10章：4567字符，12单元，SHA `bd878e804a0e0152127f3ff23f2a951f50ccf68ac819efc2a695ccb47ca3d9e5`
- 第11章：4480字符，11单元，SHA `a7f3bbabc8dc23661dd5150ab4af5cce3b0dd0e65f3a0bb75a0d8db7715fbfac`
- 第12章：4359字符，11单元，SHA `1b3174a076d51ea4beafcfda8e096db7b854c3b19af27034175ba88015d4b6c1`
合计61个新的连续顺序单位。最大**150,000 Tokens**指V81独立批次输入＋输出总限额，最多96次模型调用，原V80花费不混入新批次；收到usage后记实报、失败/超时保留预算占用，绝不暗中重试。达到任意一个上限或模型出错就按R2 CAS最后签收点停机，不能抹除红色。

## 训练之前预冻结的独立小型迁移考试

完整冻结考题与固定评分实现：`writerforge/v81_frozen_blind_ablation.py`，GitHub在V81真正付费续训启动前提交，SHA协议值 `008379841502a85ee981fe9a5c78c5a363376e94eb9b3ca1c444e2aafce486f7`。三段人造短场景分别覆盖声音/环境、人物知道的信息差、因果疑点，均**不来自用户私有小说**。考官答案关键字在冻结文件中，但不会放进DeepSeek测试消息或WF学习模型的阅读上下文。两组DeepSeek Flash回答六次，同样的合成新题、系统prompt、允许选项，唯一变化是“是否传入第12章WF自己保存的`next_strategy`”。按预先固定的`case focus`与“原文引用必须是合成场景精确连续字串”核查，另一不带模型写入权限的独立新进程再从R2重算评分。

考试只衡量这三个样例里的表现差异，不代表人类文学判断、训练效果已因果证明、真正作品风格掌握或晋级。若带经验的输出与无经验一样，必须如实写“未观察到改善”，而非事后调整问题或权重。该考试另设**最多6次请求、2700输出token预留**，与V81的15万真实学习批次分别记账，不得藏进WF训练Token报告中。

## 正在执行的真实训练

1. Railway 既有部署 `b0d2584c-1436-4673-a346-a0c71fcd67a3` 是V80 safe idle，0自动收费。
2. V81无付费来源预验 `21111116-d487-422d-99fb-bcb8e3b4eb28` SUCCESS。
3. V81全套继承安全模拟回归 `062c712d-1d64-4322-84a6-ba3ceb148116` **154/154通过**，0模型调用/0 R2写。
4. V81真实继续训练Railway `3ed00ee1-d24b-42e4-88dc-800e475c5553` 已启动，读回此前74个R2学习事件，验证第6章经验SHA，首章第7章逐单元签收已开始。此文件建立时仍在运行，需以后续实际日志为准，**不要提前填成功结果**。
5. 真正独立考官`writerforge/v81_independent_r2_exam.py`、`wf_railway_v81_reader_only_exam.py`已准备：另启动新的只读Railway容器，原R2文件完整SHA、逐章所有unit SHA、A seal、B引用和每章经验链及第6章上一轮关联均须一致；固定真实V81最后batch SHA后才能执行。
6. 预冻结独立小测试执行器`wf_railway_v81_blind_transfer_exam.py`在训练成功后挂第12章经验SHA，6次模型请求后把原始模型JSON和固定代码评分以CAS不可变存R2；`wf_railway_v81_blind_reader_only_exam.py`用另一个无模型/无Writer Token进程重新计算评分和来源引用。**盲测结果还不存在时不得预填“经验已迁移”。**

完成训练、考官和盲测后恢复Railway safe idle，写入真实新指针；不重训任何已付款章节。V49`THIRD_STRIKE_FAILED`与第二学习窗口`LOCKED`保持。
