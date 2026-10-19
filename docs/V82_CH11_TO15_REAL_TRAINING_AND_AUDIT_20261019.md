# V82｜第11～15章真实续训、故障修复与独立核验（2026-10-19）

## 原有V81成果保持

用户在V81跨作品测试后因运行时间过长要求继续；历史已完成第1～10章的来源一致性独立审计。其中第1章继承早期3段先分析的混合历史，严格先全读后析的是第2～10章9章。V81新增第7～10章，51次官方DeepSeek Flash，57,671 Tokens；另以不同未训练历史类作品首2个连续片段完成两臂（基线/带经验）对照，2次请求2,051 Tokens，真实R2对照结果 `88a3bf2c34f5fd21400236af375b38df94392403f4b3b3edbc2e352b962049d4` 已经由独立只读进程核验；两臂答案不同≠经验有效或文学掌握。

## V82第11～15章已真实完成，不得重新付费重读

- 原冻结仙侠源SHA：`0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd`。本轮WF从V81第10章R2经验SHA `feee04808c6b14f84c16989d98b031937a897395f3d008c43e17b3449f9077e3` 接续，不重看第1～10章。
- Railway真实日志 `WF_V82_CH11_TO_15_R2_BATCH_COMPLETED` / `WF_V82_TRAINING_EXIT=0`：第11章11单位、第12章11、第13章11、第14章8、第15章6，**共47个顺序首读单位**。每章记录完整Pass A签收、seal、来源证据绑定的Pass B，以及经验卡/下一章策略，模型自评不算文学鉴定。
- 真实官方DeepSeek Flash：**58个请求、49,238输入＋11,899输出＝61,137 Tokens**，属于新的单批次150,000输入＋输出上限；没有不明usage的模型调用。人民币费用暂未与用户DeepSeek后台核对，不能凭token猜价格。
- 本轮最终R2 CAS batch SHA：`d46ffec05927dfba3f2819089e76e79f720db2a2f3f6793b56965ac6413c177f`；最终R2 journal SHA：`3da56cc46115548c5198a65cb6124e3c03d9bdfdb1f0460950177735a99d1cb2`；第15章模型经验卡SHA：`ddbf86e87e3bf44900b4e5e4d8ffc2de99c9ed5d3c5aec98a69bfd8eb7cf2fe7`。
- 学习日志仍是`writerforge/v1/indexes/v1/chunks/{sha}.bin`中的私有不可变CAS实验对象，**不是原生Cloudflare LEARN写接口正式部署**，用户无需新增第四密钥、迁移原著或重复上传。

## 独立考官V82发生真实失败以及修复

- 真正独立考官首次运行显示`WF_V82_INDEPENDENT_AUDIT_FAILED`，安全诊断输出`KeyError`，发生于 `wf_railway_v82_reader_only_exam.py` 第124行：错误访问 `report["v81_last_experience_sha256"]`；V82真实审计器输出字段实际为`v82_last_experience_sha256`。这属于**考官脚本变量名错配**，不能据此删除既有R2经验，不应重训第11～15章。
- 已在独立分支`v82-ch11-15-training-and-audit`修补上述字段，commit `cff5599c4e2254ab9997bcb6201f776b11aa3c6c`，只更改考官只读脚本，不接触训练代码/原著。
- 重新部署只读考官 `18415e01-9607-4ed1-ad48-17f19deae3c2`，最新已确认从R2恢复178条事件（原121条完全沿用，新增57条需逐条核对）。考官进程移除DeepSeek和Writer密钥，0 paid API、0 R2 writes；**不能凭“恢复178个事件地址”便宣布57个新增事件都已审查通过**。
- 独立考官最终是否通过、部署安全待命以及真实日志在本报告后续追加；在拿到`WF_V82_INDEPENDENT_R2_CH11_TO_15_PROVENANCE_PASSED`／退出0以前，不写“文学学习通过”。更不因日志里的“模型输出有差异”推断人类审读或跨书文学能力提高。

## 下一项

1. 等真正V82只读审计完成：逐章比对新47个来源单位、A SHA链、seal、B证据和跨章经验，校验模型用量没有超过150k。
2. 切回`wf_railway_v82_safe_idle.py`，避免重新付费或无休止读取R2。
3. 后续训练若继续，从第16章开始；**第1～15章已付费，不得从头再跑**。文学质量应另设新的独立盲考与真实负例；原V49 `THIRD_STRIKE_FAILED`、第二学习窗口`LOCKED`仍保持。

## V82 真实独立验收最终结果

修复后的新Railway独立考官部署 `18415e01-9607-4ed1-ad48-17f19deae3c2` 最终真实日志：
`WF_V82_INDEPENDENT_R2_CH11_TO_15_PROVENANCE_PASSED`、`WF_V82_INDEPENDENT_COLD_EXAM_EXIT=0`。

- 从用户既有Cloudflare R2只读恢复 `178` 条事件地址，保持旧V81的121条不变，独立核验57条V82新增事件；进程移除了模型和R2 Writer变量。
- 第11/12/13/14/15章独立验证来源单元分别为 **11/11/11/8/6**（合计47），全部匹配原著原始SHA、顺序上一个事件SHA、封存与分析引用，以及第10章经验至第15章经验链。
- **5章均严格先Pass A全文首读封存，再做Pass B分析**，与V82原批次最终R2 Journal SHA `3da56cc46115548c5198a65cb6124e3c03d9bdfdb1f0460950177735a99d1cb2` 和Batch SHA `d46ffec05927dfba3f2819089e76e79f720db2a2f3f6793b56965ac6413c177f` 逐项一致。
- 训练方R2历史进度供应商用量 `49238`输入＋`11899`输出，合计 `61137` Tokens，不超150000；独立考官**模型0次、R2写入0次**。
- **未验证**：文学机制解释的实际正确性、模型请求是否绝未包含未来正文、经验是否真正提升跨书文学质量、人民币实际账单。继续`literary_promotion_approved=false`，历史V49 THIRD_STRIKE_FAILED和第二训练窗口LOCKED均不变。

前两次V82只读考官失败是Python脚本读取旧版`v81_last_experience_sha256`造成的KeyError，修正为`v82_last_experience_sha256`后才取得以上真结果。**不得抹除失败审计，也无需重新付费训练第11—15章**。

本批完成后，WF在此仙侠来源中累计处理前15章，严格先读后析的为第2—15章14章，第1章因V79提早分析永久保留混合历史。后续可由已经冻结的第15章CAS经验开始新批次第16章，但在没有新的指令前不能自动续跑更多付费请求。

**V82最终安全待命真实回执（2026-10-19）**：Railway部署 `90bc4948-75b4-48b1-beb9-c2a4414e6028` SUCCESS，运行 `python -u wf_railway_v82_safe_idle.py`，状态 `WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`。日志确认本次待命 `model_calls_this_idle_run=0`、`r2_reads_this_idle_run=0`、`r2_writes_this_idle_run=0`、`automatic_paid_next_batch_enabled=false`。此前第11—15章的58次模型调用/61,137 Tokens、完整47单位独立只读验收及R2最终CAS SHA全都保留；原三个密钥配置齐全，不需第四个。未来付费续训最早从第16章开始，不得重新支付此前15章；文学质量盲评没有通过或否定的新结论，不自动晋级。
