# WriterForge V87｜随机抽取真实陌生文学片段：结果与交接（2026-10-20）

## 一、不可修改的抽样历史

- 用户要求“可以--随机抽取”。目标从用户原有R2作品库抽2个不同类的新来源，绝不由助手人工指定书名或情节；原著全文只在R2及用户Railway临时进程内处理。
- 已在源文读取前提交`writerforge/v87_random_holdout.py`、`writerforge/v87_frozen_random_draw.py`、`docs/V87_RANDOM_HOLDOUT_PRECOMMIT_20261020.md`。用户消息UTC时间和原V86 HEAD固定种子SHA：`cb36891f420b045d6816f05f4bfe6de01779c0d05b9f3e7eee4dd1c3ba61dfe3`。
- 元数据-only真抽样Railway `d2f134a7-d7bd-44e0-963a-b7550e0c7ca1`：79个R2对象，13个符合单TXT/8MiB门槛；目录分类候选仙侠3、历史7、科幻3；固定抽中**历史＋科幻**；元数据源候选摘要`c1fdf9ac6e089ce2fffd78d4caf7cea2a186ef48016a9e076371baa1f4bc4e04`，完整抽签计划SHA`ddb50ed6b88681c23d214073d45ba4edba151bf0de1e0bfed5153efeeb3e1f6c`。没有读取小说原文正文，没有模型调用或R2写入。
- **原V87.0必须保留红色**：真实Railway `41312043-fea5-4f59-a4d6-a5e5ce7e1b35`，4个历史/3个科幻候选均无法通过严格整章结构门槛，成功数0/2，`WF87_RANDOM_SOURCE_VERIFY_EXIT=2`，报告SHA `fa9bfe2ae2431a5fecea06ff0b280e4411cd0dcfaa40bbf0a41893e51b7cf417`。不能将以下片段检查反写成V87.0章节通过。
- V87.1另行冻结`docs/V87_CONTIGUOUS_PASSAGE_FALLBACK_PRECOMMIT_20261020.md`及`writerforge/v87_contiguous_passage.py`，新试验仅为**来源可逆连续2300字符片段**，明确不能算学完一章。种子仍用旧的原抽签、同一候选顺序。编码有歧义的第1候选都明确拒绝，不因改口而放行乱码。

## 二、真实V87.1结果：两份不同来源、相同预注册随机规则

Railway真实只读部署：`6a21e71d-62b3-4236-8f37-2ac5d5380e94`，代码原部署commit `b510d12d322d352e901e59826a12e9790bee27eb`，日志 `WF87_RANDOM_PRIVATE_PASSAGE_AUDIT_COMPLETED`、`WF87_RANDOM_SOURCE_VERIFY_EXIT=0`。

最终不可变结果SHA：`6565040f03811c51df6aa211b5f79305bb1a65fc8ebdfda5acc209259e515b9a`。

| 仅匿名可见的项目 | 历史目录样本 | 科幻目录样本 |
|---|---|---|
| 按原冻结顺序采用候选 | 第2个 | 第2个 |
| 源对象Key匿名SHA | `7ade357517465167c6ea48fbaec2815f01c7e181603c3189157e9fb3adc6bbde` | `bf474a0bc98f78f3787393a5ef74f5771447962b13c20f042d32a53a0bb17380` |
| 原文全文SHA | `7dbc48ea45576b972dbf323ba77dea3e24b2394cc14650e23bc2c19788b77b97` | `a41e5b86b2878bae3e1a42babd3a21714788ae36bbdc6c1faa1ccb11a0158172` |
| 私有R2原字节 | 7,029,638 | 5,306,820 |
| 全书可逆解码字符数 | 3,568,011 | 2,682,864 |
| 随机片段起止字符 | 772579–774879 | 2016726–2019026 |
| 完整2300字片段SHA | `306239b74604419ccd06fbc6f4f5138d6cb59f919f8a886c44884d441e0062be` | `f19cce750e6b69c754740f38cdeaaaad56abc7865f840996f42d22188b28beda` |
| 确认的连续单元数 | 6 | 6 |
| 学生之后可见第1单位SHA | `71f5a2d7824ce9e5beb09c087f098515b1890c703cd940c71276fe1a2c9b6473` | `3602821bb53f0ab0d333ac276818268c61acdd6a3c1e09c9d6a0867ed1c39df9` |
| 学生之后可见第2单位SHA | `b054107ecbe2478243cf45956f8748511580ba843d061de9837318f60841c0c7` | `daeb096633538741448107a3329d7a7f7ebb13231c354ba0d6a0c87ac9b02d6c` |
| 密封未读第3单位SHA | `b841fa9d52d0716dd956665fc4708d5d47ee65ec6bd1f96f732df313c3eb3682` | `3fd848b44aa76f202afa2604eba938764105ca5a171b2d372564fd81cdbf66de` |
| 第1/2可见字符长度 | 416/414 | 431/382 |
| 第3密封字符长度 | 394 | 435 |

该运行只读总计`26,047,733`字节（含按固定候选顺序拒绝的两个第一候选），2个来源全文SHA不相同且均不同于V82训练原书和V81旧历史对照书。全文字节SHA、严格编码往返、随机片段精确范围/拼接、可见1/2单位以及密封第3单位SHA均由WF的真实Railway进程计算。**至此仅是由同一进程报告的真实SHA；还没有新启动独立冷进程重复验收，不能伪称跨进程独立通过。**

## 三、反作弊与文学能力限制

1. 随机算法使用用户消息时间+V86 HEAD构成确定性种子，这是**可复现伪随机抽样**，不是外部不可预测随机信标。用户也没有先看到原文再选书；抽样不是专业书目质量认证。
2. “历史”“科幻”是用户自己R2目录类别提示，不是自动文学分流模型真实成功，也未核书的作者、版次、版权身份；新抽中的样本不可宣称已经完成一章。
3. 未向任何学生模型输入正文：`new_model_calls=0`；没有新R2学习事件`r2_writes=0`，未创建独立文学评审`reviewer_quality_grade=null`。密封未来单位尚未用于任何判断，不会在公开渠道输出。
4. V85/V86人物事实/证据/独立签审的约束只在合成测试中通过，**尚没有从这两份真实片段自动生成可审文学假说**。既有V81两臂结果也无法证明经验带来文学质量提升。
5. 旧V49`THIRD_STRIKE_FAILED`、第二文学窗口`LOCKED`以及V82前15章R2不可变学习指针全保留。抽样只说明找到了两份真实随机文学局部测试材料。

## 四、下一阶段复现方法

后续应先通过新的纯R2 Reader进程重新从原R2文件SHA、种子与确切片段位置核实两个样本和密封后文；此时零模型调用。然后使用已冻结`docs/V87_BLIND_PROTOCOL_PRECOMMIT_20261020.md`做双臂首次阅读，严格不泄漏第三单位；回答封存后再由不同且真正受信的文学审核者给出`SUPPORTED/NEGATIVE/UNKNOWN`，所有证据位保留；只有新的真实对照能开始探讨文学进步。

**运维**：需要在本轮结束时将Railway改回单次`wf_railway_v82_safe_idle.py`，记录真实回执。不需要第四个密钥，也不可重复付费阅读第1—15章。


## 五、独立冷进程R2来源验收（2026-10-20，已真实完成）

新的、与抽样源检查不同的Railway只读部署 `800b4c0f-9539-46cc-94f7-c1a83b83a1d7` 真实执行 `python -u wf_railway_v87_independent_cold_reader.py`，日志返回：

- `WF87_INDEPENDENT_R2_TWO_RANDOM_PASSAGES_VERIFIED`
- `WF87_INDEPENDENT_COLD_READER_EXIT=0`
- 仅以 `WF_API_TOKEN` Reader访问既有R2；进程启动前移除模型及R2 Writer相关密钥。
- 独立重新下载两本全文合计 `12,336,458`字节（7,029,638历史类＋5,306,820科幻类），重算两份原始文件SHA、严格可逆解码、随机偏移、2300字符片段SHA、两条可见单位SHA和密封第三单位SHA，全部与上一部署 `6a21e71d-62b3-4236-8f37-2ac5d5380e94` 结果相符。
- 复查种子及元数据抽样SHA仍为 `ddb50ed6b88681c23d214073d45ba4edba151bf0de1e0bfed5153efeeb3e1f6c`，抽中来源非同一书。
- 独立进程 `paid_model_calls=0`、`r2_writes=0`、`student_has_not_seen_hidden_unit=true`，未输出书名、路径、章节正文、人物名或私有token。
- **核验范围是资料SHA和来源连续性，不是文学理解测试**：`independent_literary_semantic_grader_executed=false`、文学质量优胜组与技能晋级未判定。

至此可以把V87.1两个随机连续文本片段标成“`PRIVATE_R2_COLD_SOURCE_PROVENANCE_VERIFIED`”。不得把本状态表述成V87.0的完整章节验收通过，也不得当成有经验组文学水平高于基线的证明。之前V87.0全员拒绝红色报告继续保留。
