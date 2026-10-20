# WriterForge V88｜两部随机新作品真实盲测与精确证据故障复盘

日期：2026-10-20。隔离分支 `v88-evidence-anchor-forensics`。以下均为真实 Railway/R2 回执，**不是独立文学质量通过**。

## 不可变输入与运行

V87 随机抽中并由独立 Reader 复核的历史、科幻连续文本片段沿用不变；只向WF学生展示每篇前两个单位，第三单位作为密封后验原文。按历史 baseline→experience、科幻 experience→baseline 固定次序，同一 `deepseek-flash`、同一个答题 JSON 合同。经验组只读V82第15章已签收的 `next_strategy`；不重训原来的15章。

离线全仓测试：部署 `b88082a3-4f0d-4f90-99c1-021ee50c75c9`；923项执行，0失败、0错误、4跳过；模型0/R2远端读写0。

**真实四臂部署** `f4d132b5-cb86-41c6-b883-bfaae2d7b177`，`WF88_FOUR_REAL_BLIND_ANSWERS_R2_SIGNED`，退出0。模型恰好4个付费API请求，无自动重试；供应商响应报告输入3956、输出1220，总5176 Tokens，真实账单未另行对账。调用前保守预算预留26488低于40000上限。

R2预注册CAS `5e6d27fe96fccfd1d545243e9d8e81d7a25d4dc563888095a6df9e461b558591`，`created=true`为唯一执行门槛。最终四臂manifest CAS `b4802c132bcdc4998ced3a5d34ee06224380b53645b3c15b6f9ba0cb3ca979eb`。历史pair `07c70d513e2fb22a8674c95b16aa8ecdecdc62ee28166631bc008d7d64127613`；科幻pair `13a7688bea9217e51d5c2cf416a4dc7830865e0281d95b7049937f48657e14bd`。四份原模型回答均保存于私有R2 CAS，没有原著正文/答案贴入GitHub或ChatGPT。

## 独立只读来源和机械证据复核

全新只读 Railway `90857424-84d4-4b42-9283-a33b5471c801` 返回 `WF88_INDEPENDENT_READER_R2_FOUR_ARMS_VERIFIED` / exit0。考官重新下载两本原著共12336458字节，重算来源及隐藏单位SHA，重新恢复四份原始回答与输入哈希，无模型调用或R2写入。全部4个模型响应都是JSON对象，**但严格证据/回答合同通过数为0**：

| 样本/条件 | 原始合同错误 | 同一私有原文上的更细致只读检查 |
|---|---|---|
| 历史 baseline | WF88_ANCHOR_NOT_EXACT_VISIBLE_SOURCE | 两句短引皆在对应单位唯一存在，只是两个字符偏移均报错。用宿主自己计算唯一定位时，结构合同**可**通过；未改写原答 |
| 历史 experience | WF88_ANCHOR_NOT_EXACT_VISIBLE_SOURCE | 一句在对应单位不存在，不能靠移动字符坐标修复 |
| 科幻 experience | WF88_ANCHOR_NOT_EXACT_VISIBLE_SOURCE | 两处短引均在来源唯一出现，但宿主定位后竟指向**相同证据锚点**，不足以证明两个环节 |
| 科幻 baseline | WF88_ANCHOR_NOT_VISIBLE_OR_INVALID | 观察锚点长度不符合合同、原文位置无效；结果锚点的短引存在 |

独立无模型定位检查 `9fc2b13b-f574-45bc-ae0c-26f6ec19628a` 返回 `WF88_PRIVATE_SOURCE_ANCHOR_FORENSICS_COMPLETED` / exit0；没有输出私有短引句和小说原文，没有改动原答案。

**直接底层结论**：不能让语言模型自己猜Python字符偏移。WF应产生可信可核对的短原文引文及所属单位，宿主在私有内存中做逐字符唯一性检索，位置唯一才计算起止；短引不存在/重复/非法范围必须拒绝。宿主只证明“词句存在”，不能证明模型所说的因果/人物动机真实。不能为了提高通过率私自修改原来的四份盲测收据。

## 仍未完成与下一关

这两部只作为**连续局部片段**盲题，正式章节身份不成立；两臂输出改变不等于学会文学。独立真人或真正外部语义评审没有执行，结论：`literary_quality_winner=UNDETERMINED`，V49 `THIRD_STRIKE_FAILED`、第二文学窗口 `LOCKED` 全部不变。原前15章训练、来源与V82 CAS未被覆盖，第16章未新增训练。

下一步先修正 host-side 独立锚点定位，在离线合成正反例上测试“存在/唯一/同源/顺序/两个不同锚点/未读后文”后，再由独立审核员验证因果关系，不重复付费此轮的4个答案。独立文学评阅者的身份与权限须另外获得可信证明，不能让WF自签合格。

## 运行安全

四臂模型程序仅运行一次，模型运行结束后 Railway 已被切回原 `wf_railway_v82_safe_idle.py`，并有之前独立 `dbd87873-9285-4a5b-8a4c-685953e0a871` 的安全待命执行成功记录。本次取证流程结束后再次切回安全待命的新部署，需要以新日志再核验，不能提前说已完成。所有新GitHub材料都只在隔离分支；未合并main。


## 最终独立运行状态（2026-10-20）

取证后生产Railway部署 `8279666a-c9da-443d-97cd-ea899e0239db` 已真实返回 `SUCCESS`。实际容器运行 `python -u wf_railway_v82_safe_idle.py`，日志 `WF_V82_SAFE_IDLE_CHAPTER15_CHECKPOINT_PRESERVED`，本次`model_calls_this_idle_run=0`、`r2_reads_this_idle_run=0`、`r2_writes_this_idle_run=0`、`automatic_paid_next_batch_enabled=false`，`restartPolicyType=NEVER`。此次修复意见未被偷偷转换成第五次付费调用。原始V88整批最终CAS及四臂回答不会被重新训练。
